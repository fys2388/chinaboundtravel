#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
social_content_agent.py - ChinaBound 社媒增长引擎核心 Agent
=================================================================

目标：把站内存量文章转化为可持续发布的社媒内容（内容资产库 → AI 拆解生成
→ 双账户分发 → 数据回流），不依赖新文章也能每日更新。

四大模块：
  1. Inventory   : content/social/inventory.json 内容资产库（JSON 底层）
  2. Generator   : 拆解 Top-N 高价值文章，每篇生成 5 条（5 种 type）素材，
                   平台适配 + 品牌校验（brand_identity_audit，最多 3 轮重写）
  3. Distributor : 打通双 Buffer Worker（Account-A 非 Pin / Account-B Pin），
                   支持自动 / 半自动发布，发布结果回写 metrics
  4. Feedback    : 日报社媒板块 / 周报社媒增长复盘 / 数据沉淀到资产库

设计原则：
  - 复用 scripts/social_backfill.py 的解析、UTM、品牌校验、Worker 调用逻辑
  - 复用 scripts/logger.py、scripts/error_handler.py、飞书推送、错误降级
  - 图片生成 / LLM 文案增强均为「预留接口」：配置了对应 key 才调用，
    否则降级到确定性模板生成（保证离线可复现、测试全绿）

用法（CLI）：
  python scripts/social_content_agent.py build-inventory            # 批量生成素材入库
  python scripts/social_content_agent.py list --platform ig         # 列出素材
  python scripts/social_content_agent.py plan --date 2026-08-20     # 生成排期
  python scripts/social_content_agent.py publish --auto             # 自动发布
  python scripts/social_content_agent.py publish --manual           # 半自动（人工确认）
  python scripts/social_content_agent.py backfill-metrics --file X.json  # 数据回流
  python scripts/social_content_agent.py report daily|weekly        # 社媒日报/周报
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

sys.stdout.reconfigure(encoding="utf-8")

SCRIPT_DIR = Path(__file__).resolve().parent
BLOG_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(BLOG_ROOT / ".env")
except Exception:
    pass

import requests  # noqa: E402
# P0: Social media image validation + optimization
try:
    from social_image_validator import validate_image
    from social_image_optimizer import optimize_image
    IMAGE_VALIDATOR_AVAILABLE = True
    IMAGE_OPTIMIZER_AVAILABLE = True
except ImportError:
    IMAGE_VALIDATOR_AVAILABLE = False
    IMAGE_OPTIMIZER_AVAILABLE = False


from brand_identity_audit import scan_text  # noqa: E402
from logger import setup_logger, log_section, log_task  # noqa: E402
from error_handler import ErrorHandler  # noqa: E402

# 复用 social_backfill 的解析与工具函数（避免重复实现）
from social_backfill import (  # noqa: E402
    ACCOUNT_A_URL,
    ACCOUNT_B_URL,
    SITE_DOMAIN,
    _extract_cover,
    build_utm,
    discover_articles,
    parse_article,
    load_ga4_pageviews,
    truncate,
)

# P1-OPS-04: 文案清理兜底（shortcode 剥离、描述去标题前缀、发布前校验）
from social_text_utils import first_meaningful_desc, strip_shortcodes, validate_social_copy  # noqa: E402

# P1-AI-OPS-02: Social Learning闭环 - 加载学习策略（最佳时间/Hook/CTA）
try:
    from social_strategy_loader import SocialStrategyLoader
    _strategy_loader = SocialStrategyLoader()
    _strategy_available = True
except Exception as _e:
    _strategy_loader = None
    _strategy_available = False

logger = setup_logger("social_agent", level="INFO", log_file="social_content_agent.log")

if _strategy_available:
    logger.info("Social Strategy Loader 已加载，版本: %s", _strategy_loader.get_strategy_version())
else:
    logger.warning("Social Strategy Loader 未加载，使用默认策略")

# ============================================================
# 路径 / 配置
# ============================================================

INVENTORY_DIR = BLOG_ROOT / "content" / "social"
INVENTORY_FILE = INVENTORY_DIR / "inventory.json"
REPORTS_DIR = BLOG_ROOT / "reports"
SOCIAL_REPORTS_DIR = BLOG_ROOT / "reports" / "social"
SOCIAL_IMG_OUTPUT_DIR = str(BLOG_ROOT / "static" / "img" / "china-dest" / "social")
MANIFEST_MAIN = BLOG_ROOT / "manifest.json"

SCHEMA_VERSION = 1
TYPES = ("knowledge", "tip", "story", "visual", "conversion")
PLATFORMS = ("ig", "pinterest", "x", "fb")

# P1-AI-OPS-02: Social Learning闭环 - 策略指导函数
def get_strategy_guidance(platform: str) -> dict:
    """获取特定平台的策略指导（基于Social Learning闭环学习结果）"""
    if not _strategy_available or _strategy_loader is None:
        return {}
    try:
        platform_map = {"ig": "instagram", "pinterest": "pinterest", "x": "x", "fb": "facebook"}
        actual_platform = platform_map.get(platform, platform)
        return _strategy_loader.generate_content_guidance(actual_platform)
    except Exception as e:
        logger.warning("获取策略指导失败: %s", e)
        return {}


def get_best_publish_times(platform: str) -> list:
    """获取特定平台的最佳发布时间"""
    if not _strategy_available or _strategy_loader is None:
        return []
    try:
        platform_map = {"ig": "instagram", "pinterest": "pinterest", "x": "x", "fb": "facebook"}
        actual_platform = platform_map.get(platform, platform)
        return _strategy_loader.get_best_times(actual_platform)
    except Exception as e:
        logger.warning("获取最佳发布时间失败: %s", e)
        return []


def apply_strategy_to_caption(caption: str, platform: str, content_type: str) -> str:
    """将学习策略应用到文案生成（真正注入推荐Hook/CTA，去重+失败安全）"""
    if not _strategy_available:
        return caption
    try:
        guidance = get_strategy_guidance(platform)
        if not guidance:
            return caption
        hooks = guidance.get("recommended_hooks", []) or []
        ctas = guidance.get("recommended_ctas", []) or []
        applied = []
        result = caption
        if hooks:
            best_hook = str(hooks[0]).strip()
            if best_hook and best_hook.lower() not in result.lower():
                result = "\U0001f525 " + best_hook + "\n\n" + result
                applied.append("hook=" + best_hook)
        if ctas:
            best_cta = str(ctas[0]).strip()
            if best_cta and best_cta.lower() not in result.lower():
                result = result + "\n\n\U0001f449 " + best_cta
                applied.append("cta=" + best_cta)
        if applied:
            logger.info("策略已应用到 %s 文案: %s (version=%s)",
                        platform, ", ".join(applied),
                        guidance.get("strategy_version", "unknown"))
        return result
    except Exception as e:
        logger.warning("应用策略到文案失败，返回原文案: %s", e)
        return caption


# 每日排期：美东黄金时段 08:00 / 18:00 / 22:00（UTC 映射见 schedule_slots）
US_EAST_OFFSET = 4  # EDT (夏令时)；非夏令时脚本内统一按 -4 处理并在文档说明

DEFAULT_TOP_N = 20        # 首批拆解 Top20 篇
ITEMS_PER_ARTICLE = 5     # 每篇 5 条（覆盖 5 种 type）
REWRITE_ATTEMPTS = 3      # 品牌校验失败自动重写轮数
COOLDOWN_DAYS = 7         # 同篇 7 天内不重复发布
REUSE_COOLDOWN_DAYS = 7    # 已发布素材 7 天后复活重新排期（存量循环：无新文章也每天有内容发）

# P2-SOCIAL-01: 单平台每日发布上限 + 智能时间分布
MAX_PER_PLATFORM_PER_DAY = 5  # 每个平台每天最多5条
DAILY_SOCIAL_LIMIT = 5     # 每日社媒发布总量上限（与 manifest / social_publisher 统一为 5）
# 每个平台的发布时间窗口（美东时间 EST），均匀分布到3个活跃窗口：
#   morning 08:00-10:00 / lunch 12:00-14:00 / prime 20:00-22:00
# 各平台时间错开，避免同一时间集中发布
PLATFORM_DAILY_SLOTS = {
    "ig":        [(8, 0),  (12, 0),  (18, 0),  (20, 0),  (21, 0)],
    "fb":        [(8, 30), (12, 30), (18, 30), (20, 30), (21, 30)],
    "x":         [(9, 0),  (13, 0),  (19, 0),  (20, 0),  (22, 0)],
    "pinterest": [(9, 30), (13, 30), (19, 30), (21, 0),  (22, 0)],
}

VALID_STATUS = ("待审核", "已排期", "已发布")
VALUE_TYPES = ("knowledge", "tip", "story")   # 80% 价值型
CONVERSION_TYPES = ("conversion",)            # 20% 转化型

# 账户路由：非 Pin(ig/x/fb) -> Account-A；Pin -> Account-B
def account_url(platform: str) -> str:
    return ACCOUNT_A_URL if platform != "pinterest" else ACCOUNT_B_URL

# ============================================================
# Inventory 读写
# ============================================================


def empty_inventory() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "items": [],
    }


def load_inventory(path: Path = INVENTORY_FILE) -> dict:
    if not path.exists():
        return empty_inventory()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "items" not in data:
            return empty_inventory()
        return data
    except (OSError, json.JSONDecodeError):
        return empty_inventory()


def save_inventory(data: dict, path: Path = INVENTORY_FILE) -> Path:
    data["updated_at"] = datetime.now().isoformat(timespec="seconds")
    data["schema_version"] = SCHEMA_VERSION
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def next_item_id(data: dict) -> str:
    n = len(data.get("items", [])) + 1
    return f"soc-{n:06d}"


def item_signature(item: dict) -> str:
    """同篇同平台同类型的去重签名。"""
    raw = "|".join([
        item.get("source_article", ""),
        item.get("platform", ""),
        item.get("type", ""),
    ])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def existing_signatures(data: dict) -> set:
    return {it.get("_sig") for it in data.get("items", []) if it.get("_sig")}

# ============================================================
# 平台适配文案生成（确定性模板 + 可选 LLM 增强）
# ============================================================


def _article_keywords(article: dict) -> list:
    """从文章标题/描述提取主题关键词，用于生成文章相关的 hook。"""
    hay = f"{article.get('title','')} {article.get('description','')}".lower()
    kws = []
    for kw in ["visa","144-hour","panda","hotpot","tea","great wall","terracotta",
               "west lake","guilin","zhangjiajie","high-speed","subway","food","packing",
               "bargain","remote","photography","alipay","wechat","insurance","itinerary",
               "language","transport","etiquette","shanghai","beijing","xian","chengdu",
               "yunnan","accommodation","safety","internet","payment","train"]:
        if kw in hay:
            kws.append(kw)
    return kws[:3]


def _article_hook(article: dict, ctype: str) -> str:
    """基于文章内容生成 hook（P1修复：替代按类型硬编码的无关通用句）。"""
    title = article.get("title", "China Travel").strip()
    kws = _article_keywords(article)
    kw_str = kws[0].replace("-", " ").title() if kws else "China travel"
    if ctype == "conversion":
        return f"Everything you need to know about {kw_str} — in one practical guide."
    if ctype == "visual":
        return f"Visual guide to {kw_str}: what to see and capture."
    if ctype == "story":
        return f"What travelers discover about {kw_str} — practical lessons from the ground."
    if ctype == "tip":
        return f"Essential {kw_str} tips most first-time visitors miss."
    return f"Research-backed facts about {kw_str} every traveler should know."


def _type_hook(article: dict, ctype: str, platform: str = "") -> str:
    """基于文章标题 / 题材 / 平台的 hook 开头（2.0 Editorial Voice）。
    P1修复：增加平台差异化前缀，避免四平台同句重复。"""
    base = _article_hook(article, ctype)
    # 平台差异化前缀（X 极短不加前缀，其余平台加风格化引导）
    prefixes = {
        "ig": "",
        "pinterest": "",
        "fb": "💡 ",
        "x": "",
    }
    return prefixes.get(platform, "") + base


def _type_points(article: dict, ctype: str) -> list:
    """按类型从标题/描述/heading 提炼要点。"""
    points = []
    desc = article.get("description") or ""
    # knowledge / tip 用 heading 提炼价值点
    if ctype in ("knowledge", "tip"):
        for h in (article.get("headings") or [])[:3]:
            points.append(h.strip() if h and h.strip() else truncate(h, 70))
    # conversion 用标题/描述关键词
    if ctype == "conversion":
        points.append(truncate(article.get("title") or "", 100))
    # story / visual 用描述（P1-OPS-04: 去标题前缀 + 句子边界，防泄漏/重复/残句）
    # P1修复：first_meaningful_desc 已做句子边界截断，不再额外硬truncate避免残句
    if ctype in ("story", "visual") and desc:
        points.append(first_meaningful_desc(desc, article.get("title", ""), 90))
    return points


def _platform_style(platform: str) -> dict:
    """不同平台的文案长度与风格约束。"""
    return {
        "ig":        {"max_caption": 2000, "hashtags": ["#ChinaTravel", "#VisitChina", "#ChinaTrip"]},
        "pinterest": {"max_caption": 1200, "hashtags": ["chinatravel", "chinatrip", "chinatips"]},
        "x":         {"max_caption": 280,  "hashtags": ["#ChinaTravel"]},
        "fb":        {"max_caption": 1500, "hashtags": ["#ChinaTravel"]},
    }[platform]


def _keyword_dense(article: dict) -> str:
    """Pinterest 关键词密集描述（攻略实用型）。"""
    kw = []
    for tag in ["visa", "payment", "train", "packing", "food", "photo",
                "safety", "etiquette", "insurance", "internet"]:
        if tag in (article.get("title", "") + " " + (article.get("description") or "")).lower():
            kw.append(tag)
    # P1-OPS-04: 描述去标题前缀 + 句子边界，避免泄漏与重复
    dense = first_meaningful_desc(article.get("description") or "", article.get("title", ""), 200)
    if kw:
        dense += f" | Keywords: {', '.join(sorted(set(kw)))}"
    return dense


def _render_caption(article: dict, ctype: str, platform: str, utm_url: str) -> str:
    """按平台 + 类型渲染确定性文案。"""
    style = _platform_style(platform)
    hook = _type_hook(article, ctype, platform)
    points = _type_points(article, ctype)
    title = truncate(article.get("title") or "", 90)

    lines = []
    if platform == "pinterest":
        # 长文案 + 关键词密集，偏攻略实用型 — hook 基于文章标题/关键词（P1修复：去除无关通用句）
        pin_hook = _article_hook(article, ctype)
        lines.append(f"{title} | {pin_hook}")
        dense = _keyword_dense(article)
        if dense:
            lines.append("")
            lines.append(dense)
        lines.append("")
        lines.append("📌 Save this for your China trip planning.")
        lines.append("")
        lines.append(f"Full guide: {utm_url}")
    elif platform == "ig":
        # 短文案 + 情绪价值，偏视觉种草
        lines.append(hook)
        if points:
            lines.append("")
            for p in points:
                lines.append(f"· {p}")
        lines.append("")
        lines.append(f"Read the full guide: {utm_url}")
        lines.append("")
        lines.append(" ".join(style["hashtags"]))
    elif platform == "x":
        # 极短文案，观点型 / 避坑型
        core = hook
        if points:
            core += f" {points[0]}"
        url_part = f" → {utm_url}"
        hashtag = f" {style['hashtags'][0]}"
        reserve = len(url_part) + len(hashtag)
        core = truncate(core, max(1, style["max_caption"] - reserve))
        core = f"{core}{url_part}{hashtag}"
        lines.append(core)
    else:  # fb
        # 中等长度，互动引导型
        lines.append(hook)
        if points:
            lines.append("")
            for p in points:
                lines.append(f"• {p}")
        lines.append("")
        lines.append("What's your biggest China travel question? Drop it below. 👇")
        lines.append("")
        lines.append(f"Full guide: {utm_url}")
    caption = "\n".join(lines)
    # Apply learned strategy (Hook/CTA injection) — skip X due to strict char limits
    if platform != "x":
        caption = apply_strategy_to_caption(caption, platform, ctype)
    return caption


def _strip_flagged(text: str, flagged: list) -> str:
    for phrase in flagged or []:
        text = re.sub(re.escape(phrase), "", text, flags=re.IGNORECASE)
    return re.sub(r"\s{2,}", " ", text).strip()


def validate_copy(text: str):
    res = scan_text(text)
    ok = not res.get("forbidden") and not res.get("fictional")
    return ok, res


def generate_one(article: dict, ctype: str, platform: str, campaign: str) -> dict:
    """生成单条合规文案（品牌校验，最多 3 轮重写）。"""
    utm_url = build_utm(article["url"], platform, campaign)
    last_res = None
    final_text = None
    for attempt in range(1, REWRITE_ATTEMPTS + 1):
        if attempt == 1:
            text = _render_caption(article, ctype, platform, utm_url)
        else:
            flagged = ((last_res.get("forbidden") or []) +
                       (last_res.get("fictional") or []))
            safe = dict(article)
            safe["title"] = truncate(re.sub(r"[^A-Za-z0-9 ]", " ", article.get("title", "")), 60).strip() or "China Travel Guide"
            safe["description"] = truncate(article.get("description") or "", 100)
            safe["headings"] = []
            text = _strip_flagged(_render_caption(safe, ctype, platform, utm_url), flagged)
        ok, res = validate_copy(text)
        if ok:
            final_text = text
            break
        last_res = res
    if final_text is None:
        final_text = _render_caption(article, ctype, platform, utm_url)
        ok = False
    else:
        ok = True
    return {
        "text": final_text,
        "ok": ok,
        "issues": (last_res.get("forbidden") or []) + (last_res.get("fictional") or []) if not ok else [],
    }


# 主题关键词 → 场景描述（让每篇文章的配图提示词唯一、主题匹配）
_IMAGE_SCENE_KEYWORDS = [
    ("visa", "Chinese visa passport and travel documents"),
    ("144-hour", "modern Chinese airport and Beijing skyline, visa-free transit"),
    ("panda", "giant panda in Chengdu bamboo forest"),
    ("hotpot", "Sichuan hotpot bubbling with chili oil, fresh ingredients"),
    ("tea", "Chinese tea ceremony, porcelain teaware, green tea"),
    ("great wall", "Great Wall of China winding over green mountains"),
    ("terracotta", "Terracotta Warriors army in Xian museum"),
    ("west lake", "Hangzhou West Lake with pagoda at sunrise"),
    ("guilin", "Guilin karst mountains and Li River in mist"),
    ("zhangjiajie", "Zhangjiajie sandstone pillars in clouds"),
    ("high-speed", "Chinese high-speed train in a modern station"),
    ("subway", "modern Chinese metro station"),
    ("food", "Chinese street food: dumplings, noodles, night market"),
    ("packing", "packed travel suitcase with China travel essentials"),
    ("bargain", "colorful Chinese shopping street market"),
    ("remote", "laptop on a cafe table with a Chinese city view"),
    ("photography", "camera on a tripod overlooking a Chinese landscape"),
    ("alipay", "smartphone showing mobile payment at a shop"),
    ("wechat", "smartphone QR-code payment at a street vendor"),
    ("insurance", "travel insurance documents and luggage"),
    ("itinerary", "China travel map with landmarks and compass"),
    ("language", "Chinese calligraphy and a phrasebook"),
    ("transport", "Chinese train ticket and platform"),
    ("etiquette", "traditional Chinese architecture with red lanterns"),
    ("shanghai", "Shanghai Bund skyline at night"),
    ("beijing", "Forbidden City and Beijing landmarks"),
    ("xian", "Xian city wall and drum tower"),
    ("chengdu", "Chengdu teahouse street scene"),
    ("yunnan", "Yunnan rice terraces and ancient towns"),
    ("accommodation", "cozy Chinese boutique hotel room"),
]

def _image_scene(article: dict) -> str:
    """按文章标题/slug 命中主题关键词，返回差异化场景描述。"""
    hay = f"{(article.get('title') or '').lower()} {(article.get('slug') or '').lower()}"
    for kw, scene in _IMAGE_SCENE_KEYWORDS:
        if kw in hay:
            return scene
    return "iconic China travel scene, landmarks and culture"

def build_image_prompt(article: dict, ctype: str, platform: str) -> str:
    """配图生成提示词：文章主题 × 平台比例 × 内容类型三因素差异化（保证每条帖子提示词唯一）。"""
    title = article.get("title") or "China travel"
    desc = (article.get("description") or "").strip()
    scene = _image_scene(article)
    ratio_map = {
        "ig": "vertical 4:5",
        "pinterest": "vertical 2:3",
        "x": "wide landscape 16:9",
        "fb": "landscape 16:9",
    }
    ctype_angle = {
        "knowledge": "educational",
        "tip": "clean and practical",
        "story": "evocative storytelling",
        "visual": "striking instagram-worthy",
        "conversion": "inviting click-worthy",
    }
    desc_extra = f" Key elements: {desc[:140]}." if desc else ""
    return (f"Professional {ctype} social graphic for '{title}' (platform {platform}). "
            f"Scene: {scene}. Style: {ratio_map.get(platform, 'travel')}, "
            f"{ctype_angle.get(ctype, 'high quality')}, bright natural light, photorealistic, vibrant. "
            f"No people, no faces, no text, no words, no watermark, no logo.{desc_extra}")


# ============================================================
# LLM / 图片增强（预留接口）
# ============================================================


def llm_enhance(article: dict, ctype: str, platform: str, base_text: str) -> str:
    """可选 LLM 文案增强。仅当显式启用 SOCIAL_LLM_ENABLED 且配置了 key 才调用；
    未启用、未配置或失败时返回 base_text（确定性降级）。"""
    if not os.environ.get("SOCIAL_LLM_ENABLED", ""):
        return base_text
    key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("DOUBAO_ARK_API_KEY")
    if not key:
        return base_text
    endpoint = os.environ.get("DEEPSEEK_ENDPOINT",
                              "https://api.deepseek.com/chat/completions")
    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
    try:
        prompt = (
            f"Rewrite this social caption for platform '{platform}' (type '{ctype}') "
            "in the ChinaBound 2.0 editorial voice. IMPORTANT: never use first-person "
            "personal travel experience ('I stayed', 'I visited', 'my wife', etc.). "
            "Keep UTM link untouched. Return only the caption.\n\n"
            f"Article title: {article.get('title')}\n"
            f"Base caption:\n{base_text}"
        )
        resp = requests.post(
            endpoint,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": model, "messages": [{"role": "user", "content": prompt}],
                  "temperature": 0.7, "max_tokens": 400},
            timeout=60,
        )
        resp.raise_for_status()
        out = resp.json()["choices"][0]["message"]["content"].strip()
        return out or base_text
    except Exception as e:  # 错误降级
        logger.warning("LLM enhance failed, fallback to template: %s", e)
        return base_text


def _site_img_url(rel_path: str) -> str:
    """static 下相对路径 -> 站点绝对 URL（满足 worker 白名单 chinaboundtravel.com/img/china-dest/）。"""
    rel = str(rel_path).replace("\\", "/")
    marker = "/static/"
    if marker in rel:
        rel = rel.split(marker, 1)[1]
    elif rel.startswith("static/"):
        rel = rel[len("static/"):]
    return f"https://www.{SITE_DOMAIN}/{rel}"


def _gen_via_ark(prompt: str, out_path: Path) -> bool:
    """首选：豆包 Ark Seedream 文生图（需 ARK_IMAGE_MODEL 配置且账号已开通该模型）。"""
    key = os.environ.get("DOUBAO_ARK_API_KEY", "")
    model = os.environ.get("ARK_IMAGE_MODEL", "")
    if not key or not model:
        return False
    try:
        resp = requests.post(
            "https://ark.cn-beijing.volces.com/api/v3/images/generations",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": model, "prompt": prompt, "size": "1024x1024",
                  "response_format": "url"},
            timeout=90,
        )
        resp.raise_for_status()
        url = (resp.json().get("data") or [{}])[0].get("url", "")
        if not url:
            return False
        img = requests.get(url, timeout=90)
        img.raise_for_status()
        out_path.write_bytes(img.content)
        return out_path.stat().st_size > 1000
    except Exception as e:
        logger.warning("Ark 文生图失败（降级 pollinations）: %s", str(e)[:120])
        return False


def _gen_via_pollinations(prompt: str, out_path: Path, platform: str) -> bool:
    """兜底：pollinations flux 文生图（免费可用），下载后本地托管（消除外部 URL 依赖）。

    免费匿名额度约 1 张/分钟 → 内置 429 退避重试（45s/90s/120s），
    按额度自动节流，避免批量生成被限流打爆而丢图。
    """
    w, h = 1024, 1024
    if platform == "ig":
        w, h = 1024, 1280   # 4:5
    elif platform == "pinterest":
        w, h = 1024, 1536   # 2:3
    elif platform in ("x", "fb"):
        w, h = 1536, 864    # 16:9
    negative = ("blurry, distorted, deformed, ugly, disfigured, malformed, extra limbs, "
                "bad anatomy, low quality, watermark, text, words, letters, logo, person, "
                "people, face, portrait, human, figure, crowd, man, woman, child")
    url = (f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}"
           f"?width={w}&height={h}&nologo=true&model=flux&token=anonymous"
           f"&negative={requests.utils.quote(negative)}")
    for attempt in range(4):
        try:
            r = requests.get(url, timeout=120)
            if r.status_code == 429:
                wait = (45, 90, 120, 180)[attempt]
                logger.warning("pollinations 429 限流，等待 %ss 重试 (%d/3)...", wait, attempt + 1)
                time.sleep(wait)
                continue
            r.raise_for_status()
            if "image" not in r.headers.get("content-type", "").lower():
                return False
            out_path.write_bytes(r.content)
            return out_path.stat().st_size > 1000
        except Exception as e:
            logger.warning("pollinations 文生图失败: %s", str(e)[:120])
            return False
    logger.warning("pollinations 多次限流仍失败，跳过该图")
    return False


def generate_image(item: dict, path: Path) -> str:
    """真实文生图：为单条帖子生成独立配图并本地托管到 static/img/china-dest/social/。

    后端链：Ark Seedream（首选，需 ARK_IMAGE_MODEL）→ pollinations flux（兜底）→ 空串。
    返回站点绝对 URL；未生成返回 ""（调用方回退文章封面）。需 IMAGE_GEN_ENABLED=1。
    文件名含 slug/platform/type/prompt 摘要 → 同文同平台同类型也互不重复。
    """
    if not os.environ.get("IMAGE_GEN_ENABLED", ""):
        return ""
    prompt = (item.get("image_prompt") or "").strip()
    if not prompt:
        prompt = build_image_prompt(
            {"title": item.get("source_title", ""), "slug": item.get("source_article", ""),
             "description": item.get("source_description", "")},
            item.get("type", "knowledge"), item.get("platform", "ig"))
    slug = re.sub(r"[^a-z0-9]+", "-", str(item.get("source_article") or "post").lower()).strip("-")[:40]
    digest = hashlib.sha1(f"{slug}|{item.get('platform')}|{item.get('type')}|{prompt}".encode("utf-8")).hexdigest()[:8]
    out_dir = BLOG_ROOT / "static" / "img" / "china-dest" / "social"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{slug}-{item.get('platform')}-{item.get('type')}-{digest}.jpg"
    if out_path.exists() and out_path.stat().st_size > 1000:
        return _site_img_url(str(out_path))
    if not (_gen_via_ark(prompt, out_path)
            or _gen_via_pollinations(prompt, out_path, item.get("platform", "ig"))):
        try:
            out_path.unlink()
        except Exception:
            pass
        return ""
    return _site_img_url(str(out_path))


# ============================================================
# 选文（Top-N 高价值）
# ============================================================


def select_top_articles(n: int) -> list:
    """按 GA4 历史流量 + front matter 信号选 Top-N。复用 social_backfill 逻辑。"""
    articles = discover_articles()
    ga4_views = load_ga4_pageviews()
    processed = set()
    # 复用 social_backfill 的评分（但排除最近已分发）
    from social_backfill import recently_distributed
    candidates = [a for a in articles
                  if (a.get("cover") or a.get("image")) and not recently_distributed(a)]
    if not candidates:
        candidates = [a for a in articles if a.get("cover") or a.get("image")]
    ranked = sorted(
        candidates,
        key=lambda a: (min(ga4_views.get(a["slug"], 0), 50)
                       + (25 if a["slug"] in {
                            "144-hour-visa-free-transit-guide",
                            "china-bargaining-and-shopping-guide",
                            "chinese-tea-culture-where-to-experience-authentic-teahouses",
                            "chinas-food-through-the-ages-guide",
                            "china-packing-list-2026-what-to-bring-and-what-to-leave-at-home",
                            "china-photography-guide-capturing-the-wonders-of-the-middle-kingdom",
                       } else 0)),
        reverse=True,
    )
    return ranked[:n]

# ============================================================
# 批量生成 → 资产库
# ============================================================


def _generate_for_articles(data: dict, articles: list, sigs: set) -> list:
    """为给定文章列表生成素材并追加到 data（共用生成逻辑）。返回新增素材列表。"""
    campaign = f"cbt_social_{date.today().strftime('%Y%m%d')}"
    created = []
    platform_cycle = ["ig", "pinterest", "x", "fb"]
    for ai, article in enumerate(articles):
        for ti, ctype in enumerate(TYPES):
            platform = platform_cycle[(ai + ti) % len(platform_cycle)]
            gen = generate_one(article, ctype, platform, campaign)
            text = gen["text"]
            # LLM 增强（可选）
            text = llm_enhance(article, ctype, platform, text)
            ok, res = validate_copy(text)
            if not ok:
                text = gen["text"]
                ok = gen["ok"]
                res_issues = gen["issues"]
            else:
                res_issues = []
            item = {
                "id": next_item_id(data),
                "source_article": article["slug"],
                "source_title": article["title"],
                "platform": platform,
                "type": ctype,
                "caption": text,
                "image_prompt": build_image_prompt(article, ctype, platform),
                # 复用文章 front matter 的实景封面（绝对 URL），供 worker 发布时校验通过；
                # generate_image 为预留接口，未启用时也以此兜底。
                "image_url": article.get("cover") or article.get("image", "") or "",
                "utm_params": {
                    "utm_source": platform,
                    "utm_medium": "social",
                    "utm_campaign": campaign,
                },
                "status": "待审核",
                "publish_date": "",
                "metrics": {"impressions": 0, "clicks": 0, "engagements": 0,
                            "uv": 0, "platform": platform},
            }
            # 真实文生图：IMAGE_GEN_ENABLED=1 时为该帖子生成独立配图（否则回退文章封面）
            try:
                _gen_url = generate_image(item, None)
            except Exception as _e:
                logger.warning("generate_image 异常 %s: %s", item.get("id", "?"), _e)
                _gen_url = ""
            if _gen_url:
                item["image_url"] = _gen_url
                item["image_generated"] = True

            item["_sig"] = item_signature(item)
            # 跳过已存在签名（幂等）
            if item["_sig"] in sigs:
                continue
            data["items"].append(item)
            sigs.add(item["_sig"])
            created.append(item)
    return created


def build_inventory(top_n: int = DEFAULT_TOP_N, force: bool = False,
                    inventory_path: Path = INVENTORY_FILE) -> dict:
    """拆解 Top-N 文章，每篇生成 5 条（5 种 type）素材入库。

    平台分配：为保证 4 平台都覆盖且每篇 5 种 type 齐备，对每篇内部按
    type 顺序轮换平台，使整批整体均衡（约各占 25%）。

    增量模式（默认）：资产库已有内容时，自动补充「未入库的新文章」素材，
    已入库文章不重复生成；--force 则全量重建。
    """
    log_section(logger, "构建社媒内容资产库 build-inventory")
    data = load_inventory(inventory_path)
    sigs = existing_signatures(data)

    if force or not data.get("items"):
        # 全量重建：覆盖所有入选文章
        articles = select_top_articles(top_n)
        logger.info("全量重建，选文 Top-%d: %s", len(articles),
                    ", ".join(a["slug"] for a in articles))
        created = _generate_for_articles(data, articles, sigs)
        save_inventory(data, inventory_path)
        logger.info("新增 %d 条素材，资产库共 %d 条", len(created), len(data["items"]))
        return data

    # 增量模式：只补充未入库的新文章
    existing_articles = {i.get("source_article") for i in data.get("items", [])}
    articles = select_top_articles(max(top_n * 2, 30))
    new_articles = [a for a in articles if a["slug"] not in existing_articles]
    if not new_articles:
        logger.info("资产库已有 %d 条，无新文章需要入库（%d 篇已覆盖）",
                    len(sigs), len(existing_articles))
        return data

    logger.info("增量补充 %d 篇新文章素材: %s", len(new_articles),
                ", ".join(a["slug"] for a in new_articles))
    created = _generate_for_articles(data, new_articles, sigs)
    save_inventory(data, inventory_path)
    logger.info("增量新增 %d 条素材，资产库共 %d 条", len(created), len(data["items"]))
    return data

# ============================================================
# 查询 / 筛选
# ============================================================


def filter_items(data: dict, platform: str = None, ctype: str = None,
                  status: str = None, source_article: str = None) -> list:
    items = data.get("items", [])
    if platform:
        items = [i for i in items if i.get("platform") == platform]
    if ctype:
        items = [i for i in items if i.get("type") == ctype]
    if status:
        items = [i for i in items if i.get("status") == status]
    if source_article:
        items = [i for i in items if i.get("source_article") == source_article]
    return items

# ============================================================
# 排期策略
# ============================================================


def schedule_slots_for_day(d: date) -> list:
    """美东黄金时段 08:00 / 18:00 / 22:00 -> UTC 时间戳（EDT -4）。"""
    slots_et = [8, 18, 22]
    out = []
    for et_hour in slots_et:
        utc_hour = (et_hour + US_EAST_OFFSET) % 24
        utc_date = d + timedelta(days=1) if (et_hour + US_EAST_OFFSET) >= 24 else d
        out.append(f"{utc_date.isoformat()}T{utc_hour:02d}:00:00+00:00")
    return out


def get_platform_slot_utc(d: date, platform: str, slot_index: int) -> str:
    """获取指定平台、指定序号的发布时间（UTC 时间戳）。

    P2-SOCIAL-01: 按平台智能分布到3个活跃窗口，各平台时间错开。
    """
    slots = PLATFORM_DAILY_SLOTS.get(platform, PLATFORM_DAILY_SLOTS["ig"])
    et_hour, et_minute = slots[min(slot_index, len(slots) - 1)]
    utc_hour = (et_hour + US_EAST_OFFSET) % 24
    utc_date = d + timedelta(days=1) if (et_hour + US_EAST_OFFSET) >= 24 else d
    return f"{utc_date.isoformat()}T{utc_hour:02d}:{et_minute:02d}:00+00:00"


def build_schedule(data: dict, start_date: date = None) -> list:
    """从待审核素材生成每日 3 条排期（80% 价值 + 20% 转化，同篇 7 天不重复）。

    由于 7 天去重限制，同一篇文章在窗口内最多贡献 1 条。为满足
    80% 价值 / 20% 转化，先为每篇文章预选「指定类型」：约 20% 的文章
    贡献转化型（conversion），其余贡献价值型（knowledge/tip/story），
    再按文章铺排，每天 3 条（美东 08/18/22）。

    返回按日期分组排期项：{date, slots:[{item_id, platform, type, utc}]}
    """
    pending = filter_items(data, status="待审核")
    by_article: dict[str, list] = {}
    for it in pending:
        by_article.setdefault(it["source_article"], []).append(it)

    articles = sorted(by_article)
    total = len(articles)
    # 约 20% 文章贡献转化型：每 CONV_EVERY 篇选 1 篇转化。
    # 注意：conversion 素材只存在于部分文章；若按排序位置硬选（idx % CONV_EVERY），
    # 命中位置可能恰好无 conversion 素材，导致整体 0% 转化（2026-08-30 线上 80/20 断裂）。
    # 改为从「有 conversion 待审核素材的文章」池中每 CONV_EVERY 篇取 1 篇，保证比例稳定。
    CONV_EVERY = 5
    conv_articles = [a for a in articles
                     if any(i["type"] in CONVERSION_TYPES for i in by_article[a])]
    conv_pool = set(conv_articles[::CONV_EVERY])
    chosen: list[dict] = []
    for idx, art in enumerate(articles):
        items = by_article[art]
        want_conv = art in conv_pool
        conv_candidates = [i for i in items if i["type"] in CONVERSION_TYPES]
        value_candidates = [i for i in items if i["type"] in VALUE_TYPES]
        if want_conv and conv_candidates:
            chosen.append(conv_candidates[0])
        elif value_candidates:
            chosen.append(value_candidates[0])
        elif items:
            chosen.append(items[0])

    cursor = start_date or date.today()
    schedule = []
    day_items = {"date": cursor.isoformat(), "slots": []}
    per_day_by_platform: dict[str, int] = {}  # P2-SOCIAL-01: 按平台计数
    seen_article_last: dict[str, date] = {}
    for item in chosen:
        article = item["source_article"]
        platform = item["platform"]
        # 同篇 7 天不重复（每篇已预选 1 条，此项为防御性检查）
        if article in seen_article_last and \
           (cursor - seen_article_last[article]).days < COOLDOWN_DAYS:
            if day_items["slots"]:
                schedule.append(day_items)
            cursor = cursor + timedelta(days=1)
            per_day_by_platform: dict[str, int] = {}  # P2-SOCIAL-01: 按平台计数
            day_items = {"date": cursor.isoformat(), "slots": []}
        # P2-SOCIAL-01: 按平台智能分布到活跃窗口
        platform_count = per_day_by_platform.get(platform, 0)
        # 每日总量上限（与 manifest daily_social_publish_limit 统一），达到后顺延到次日
        if len(day_items["slots"]) >= DAILY_SOCIAL_LIMIT:
            schedule.append(day_items)
            cursor = cursor + timedelta(days=1)
            per_day_by_platform = {}
            day_items = {"date": cursor.isoformat(), "slots": []}
            platform_count = 0
        # 检查该平台当天是否已达上限
        elif platform_count >= MAX_PER_PLATFORM_PER_DAY:
            if day_items["slots"]:
                schedule.append(day_items)
            cursor = cursor + timedelta(days=1)
            per_day_by_platform: dict[str, int] = {}
            day_items = {"date": cursor.isoformat(), "slots": []}
            platform_count = 0
        utc_time = get_platform_slot_utc(cursor, platform, platform_count)
        slot_et = PLATFORM_DAILY_SLOTS.get(platform, PLATFORM_DAILY_SLOTS["ig"])[platform_count]
        day_items["slots"].append({
            "item_id": item["id"],
            "platform": platform,
            "type": item["type"],
            "utc": utc_time,
            "slot_et": f"{slot_et[0]:02d}:{slot_et[1]:02d}",
        })
        seen_article_last[article] = cursor
        per_day_by_platform[platform] = platform_count + 1
    if day_items["slots"]:
        schedule.append(day_items)
    return schedule


# ============================================================
# P1-GROWTH-29 社媒增长试点：Pinterest 2/天 + Instagram 1/天
# ============================================================

# 试点阶段仅启用 Pinterest + Instagram（禁止 FB / X 自动化）
PILOT_PLATFORMS = ("pinterest", "ig")
# 美东黄金时段 20:00-22:00；Pinterest 2 条，Instagram 1 条
PILOT_ET_SLOTS = {
    "pinterest": [(20, 0), (21, 0)],   # 2 条：20:00 / 21:00 ET
    "ig": [(20, 30)],                  # 1 条：20:30 ET
}


def _content_id_map() -> dict:
    """slug -> content_id（从文章 frontmatter 提取，确定性映射）。"""
    mapping = {}
    posts_dir = BLOG_ROOT / "content" / "posts"
    for p in sorted(posts_dir.glob("*.md")):
        text = p.read_text(encoding="utf-8", errors="replace")
        fm_match = re.search(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
        if not fm_match:
            continue
        fm = fm_match.group(1)
        cid = re.search(r'^content_id\s*[=:]\s*["\']?([^"\'\n]+)', fm, re.MULTILINE)
        slug = re.search(r'^slug\s*[=:]\s*["\']?([^"\'\n]+)', fm, re.MULTILINE)
        key = (slug.group(1).strip().strip('"').strip("'") if slug else p.stem)
        if cid:
            mapping[key] = cid.group(1).strip().strip('"').strip("'")
    return mapping


def build_pilot_schedule(data: dict, start_date: date = None,
                         days: int = 7) -> list[dict]:
    """Pinterest 2/天 + Instagram 1/天，7 天同篇不重复，返回按天排期。

    每条排期项包含 P1-GROWTH-29 统一字段：
      social_content_id / content_id / platform / content_type /
      source_article / scheduled_at_utc / scheduled_at_et / utm / status
    """
    start_date = start_date or date.today() + timedelta(days=1)
    content_ids = _content_id_map()
    pool = {
        "pinterest": sorted(
            (i for i in data["items"]
             if i.get("platform") == "pinterest" and i.get("status") != "已发布"),
            key=lambda i: i["id"]),
        "ig": sorted(
            (i for i in data["items"]
             if i.get("platform") == "ig" and i.get("status") != "已发布"),
            key=lambda i: i["id"]),
    }
    last_used: dict[str, dict[str, date]] = {}
    schedule = []
    for day_offset in range(days):
        d = start_date + timedelta(days=day_offset)
        day = {"date": d.isoformat(), "slots": []}
        used_articles_today: set[str] = set()
        for platform, et_times in PILOT_ET_SLOTS.items():
            for idx, (et_hour, et_min) in enumerate(et_times):
                candidate = None
                for item in pool[platform]:
                    art = item["source_article"]
                    if art in used_articles_today:
                        continue
                    last = last_used.get(art, {}).get(platform)
                    if last and (d - last).days < COOLDOWN_DAYS:
                        continue
                    candidate = item
                    break
                if candidate is None:
                    continue  # 库存不足时当天少发一条，宁缺毋滥
                art = candidate["source_article"]
                used_articles_today.add(art)
                last_used.setdefault(art, {})[platform] = d
                utc_total = et_hour * 60 + et_min + US_EAST_OFFSET * 60
                utc_date = d + timedelta(days=1) if utc_total >= 24 * 60 else d
                utc_hour, utc_min = divmod(utc_total % (24 * 60), 60)
                utc = f"{utc_date.isoformat()}T{utc_hour:02d}:{utc_min:02d}:00+00:00"
                utm = dict(candidate.get("utm_params", {}))
                utm["utm_content"] = f"pilot_{platform}_{idx + 1}"
                day["slots"].append({
                    "social_content_id": candidate["id"],
                    "content_id": content_ids.get(art, "NOT_FOUND"),
                    "platform": platform,
                    "content_type": candidate.get("type", ""),
                    "source_article": art,
                    "source_title": candidate.get("source_title", ""),
                    "url": candidate.get("url", ""),
                    "caption": candidate.get("caption", ""),
                    "scheduled_at_utc": utc,
                    "scheduled_at_et": f"{et_hour:02d}:{et_min:02d} America/New_York",
                    "utm": utm,
                    "status": "PENDING_APPROVAL",
                })
        if day["slots"]:
            schedule.append(day)
    return schedule


def _cmd_plan_pilot(args) -> int:
    data = load_inventory()
    start = _parse_date(args.start)
    sched = build_pilot_schedule(data, start_date=start, days=args.days)
    csv_path = SOCIAL_REPORTS_DIR / "P1_GROWTH_29_SOCIAL_PILOT_SCHEDULE.csv"
    json_path = SOCIAL_REPORTS_DIR / "P1_GROWTH_29_SOCIAL_PILOT_SCHEDULE.json"
    SOCIAL_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    import csv as _csv
    fields = ["social_content_id", "content_id", "platform", "content_type",
              "source_article", "source_title", "scheduled_at_utc",
              "scheduled_at_et", "utm", "status"]
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as fh:
        w = _csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for day in sched:
            for slot in day["slots"]:
                row = {k: slot.get(k, "") for k in fields}
                row["utm"] = urlencode(slot.get("utm", {}))
                w.writerow(row)
    json_path.write_text(json.dumps(
        {"schedule": sched, "generated_at": datetime.now().isoformat(timespec="seconds")},
        ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(len(d["slots"]) for d in sched)
    print(f"试点排期已生成: {csv_path}（{total} 条，{len(sched)} 天，"
          f"Pinterest 2/天 + Instagram 1/天，状态=PENDING_APPROVAL）")
    return 0

# ============================================================
# 分发（双 Buffer Worker）
# ============================================================


def publish_item(item: dict, endpoint: str, dry_run: bool = True) -> dict:
    """向 Buffer Worker 发布单条素材。"""
    caption = re.sub(r"\s*\|\s*Keywords:\s*[^\n]*", "", item.get("caption") or "")
    item = {**item, "caption": caption}
    post_url = _extract_post_url(item)
    # P1-OPS-04: 发布前 lint —— 有致命问题（shortcode/空链接/人设/标题重复等）一律拒绝发布
    problems = validate_social_copy(
        caption, title=item.get("source_title", ""), url=post_url,
    )
    if problems:
        return {"success": False, "dry_run": dry_run,
                "error": "LINT_FAILED: " + "; ".join(problems), "lint": problems}
    # Buffer API 不支持 .webp 格式，自动转换为 .jpg（网站同时保留两种格式）
    cover_url = item.get("image_url", "") or ""
    if cover_url and cover_url.lower().endswith(".webp"):
        cover_url = cover_url[:-5] + ".jpg"
    payload = {
        "title": item.get("source_title", ""),
        "desc": item["caption"],
        "cover": cover_url,
        "url": post_url,  # 必须传给 worker，否则链接会被剥离或回退首页
        "custom_text": item["caption"],
        "content_id": "",
        "content_variant": f"{item['platform']}_{item['type']}",
        "source_workflow": "social_content_agent",
        # 2026-08-28 修复：显式声明目标平台，防止 worker 广播到所有渠道
        "platforms": [item["platform"]],
    }
    if dry_run:
        return {"success": True, "dry_run": True, "endpoint": endpoint,
                "detail": "dry-run 未发送"}
    try:
        resp = requests.post(endpoint, json=payload, timeout=90)
        resp.raise_for_status()
        data = resp.json()
        platforms = (data.get("platforms") or {}).get("success", [])
        # worker 单日限流时返回 202 + queued:true（稿件已入重试队列，次日自动发布），
        # 视为成功交接而非失败，避免限流日被误报为发布失败。
        # worker 内容去重命中时返回 200 + success:false + error:'Duplicate content'，
        # 属预期跳过（内容已发布过），同样视为成功交接，避免重复内容把整个 run 标红。
        dup = ("Duplicate content" in str(data.get("error") or "")
               or "Duplicate content" in str(data.get("message") or ""))
        ok = bool(data.get("success")) or bool(data.get("queued")) or dup
        return {"success": ok, "queued": bool(data.get("queued")), "skipped": dup,
                "endpoint": endpoint, "platforms": platforms,
                "error": "" if ok else (data.get("message") or data.get("error", ""))}
    except requests.exceptions.Timeout:
        return {"success": False, "endpoint": endpoint, "error": "Timeout after 90s"}
    except requests.exceptions.HTTPError as e:
        # 保留响应体，便于定位 Buffer/Worker 的 400/500 具体原因
        _body = ""
        try:
            _body = (e.response.text or "")[:300]
        except Exception:
            pass
        return {"success": False, "endpoint": endpoint,
                "error": f"HTTP {e.response.status_code}: {_body}"}
    except Exception as e:
        return {"success": False, "endpoint": endpoint, "error": str(e)}


def _extract_post_url(item: dict) -> str:
    """从 caption 提取文章链接，交给 Buffer Worker 作为 postUrl。"""
    caption = item.get("caption") or ""
    m = re.search(r"https?://[^\s]+", caption)
    return m.group(0) if m else ""


def _ensure_cover_url(item: dict) -> str:
    """发布前自愈：为 image_url 为空的素材从文章 front matter 回填封面绝对 URL。

    worker 对 cover 有强校验（白名单域名 + /img/china-dest/ 路径），
    inventory 中历史条目 image_url 可能为空，直接复用 _extract_cover 提取。
    """
    slug = str(item.get("source_article") or "")
    if not slug:
        return ""
    posts_dir = BLOG_ROOT / "content" / "posts"
    if not posts_dir.is_dir():
        return ""
    for md in posts_dir.glob("*.md"):
        if md.stem == slug:
            try:
                return parse_article(md).get("cover") or ""
            except Exception:
                return ""
    return ""


def _image_live(url: str) -> bool:
    """HEAD 检查图片 URL 是否已上线（HTTP 200）。任何异常视为未上线（宁可推迟不可发失效图）。"""
    if not url:
        return True
    try:
        return requests.head(url, timeout=15, allow_redirects=True).status_code == 200
    except Exception:
        return False


def distribute_items(items: list, dry_run: bool = True,
                     inventory_path: Path = INVENTORY_FILE) -> list:
    """发布指定素材（自动/半自动共用），发布成功回写 status=已发布 + publish_date。"""
    data = load_inventory(inventory_path)
    by_id = {it["id"]: it for it in data["items"]}
    results = []
    for item in items:
        endpoint = account_url(item["platform"])
        # 发布前自愈：image_url 为空时从文章 front matter 回填封面（worker 封面必填校验）
        _cover = (item.get("image_url") or "").strip()
        if not _cover:
            _cover = _ensure_cover_url(item)
            if _cover:
                item["image_url"] = _cover
        # 发布前 URL 存活检查：文生图需先经静态资源 push 触发 Cloudflare Pages 部署上线；
        # 未上线则本轮跳过（保留待审核，下一轮自动补发），避免 worker 发布失效图。
        if _cover and not dry_run and not _image_live(_cover):
            logger.warning("配图未上线，本轮跳过发布 [%s]: %s", item.get("id", "?"), _cover)
            results.append({"item_id": item["id"], "platform": item["platform"],
                            "type": item["type"], "source_article": item["source_article"],
                            "success": True, "deferred": True, "error": "image_not_live_yet"})
            continue
        # P0: 发布前图片质量验证（宽高比/分辨率/AI图域）
        _img_issues = []
        if IMAGE_VALIDATOR_AVAILABLE and item.get("image_url"):
            _ivr = validate_image(item["image_url"], item["platform"])
            if not _ivr["passed"]:
                _img_issues = _ivr["issues"]
                logger.warning("图片验证未通过 %s [%s]: %s",
                    item.get("id","?"), item["platform"], "; ".join(_img_issues))
                # 非阻断：记录问题并继续发布（P1 后切换为严格阻断+自动优化）
                item["image_validation"] = {"passed": False, "issues": _img_issues}
            else:
                item["image_validation"] = {"passed": True, "issues": []}
        # P1: 图片自动优化 — 验证发现宽高比/分辨率问题时，自动裁剪为平台适配版本
        _optimized = False
        if IMAGE_OPTIMIZER_AVAILABLE and item.get("image_url") and _img_issues:
            _fixable = any(("wrong_aspect_ratio" in i or "low_resolution" in i) for i in _img_issues)
            if _fixable:
                try:
                    import os as _os
                    _os.makedirs(SOCIAL_IMG_OUTPUT_DIR, exist_ok=True)
                    _opt = optimize_image(item["image_url"], item["platform"], SOCIAL_IMG_OUTPUT_DIR)
                    if _opt.get("success") and _opt.get("output_path"):
                        _out_path = _opt["output_path"]
                        # 转换本地路径为网站URL: static/img/china-dest/social/xxx.jpg -> /img/china-dest/social/xxx.jpg
                        _rel = _out_path.replace(str(BLOG_ROOT / "static"), "").replace("\\", "/")
                        _opt_url = f"https://www.{SITE_DOMAIN}{_rel}"
                        logger.info("图片自动优化 %s [%s]: %dx%d -> %s",
                            item.get("id","?"), item["platform"], _opt["width"], _opt["height"], _opt_url)
                        item["image_url"] = _opt_url
                        item["image_optimized"] = True
                        _optimized = True
                        _img_issues = [i for i in _img_issues if "wrong_aspect_ratio" not in i and "low_resolution" not in i]
                except Exception as _e:
                    logger.warning("图片自动优化失败 %s: %s", item.get("id","?"), _e)

        res = publish_item(item, endpoint, dry_run=dry_run)
        if not dry_run and res.get("success"):
            rec = by_id.get(item["id"])
            if rec:
                rec["status"] = "已发布"
                rec["publish_date"] = date.today().isoformat()
        results.append({"item_id": item["id"], "platform": item["platform"],
                        "type": item["type"], "source_article": item["source_article"],
                        "image_issues": _img_issues,
                        **res})
        if not dry_run:
            time.sleep(2)
    if not dry_run:
        save_inventory(data, inventory_path)
    return results

# ============================================================
# 数据回流
# ============================================================


def backfill_metrics(metrics_file: Path,
                     inventory_path: Path = INVENTORY_FILE) -> int:
    """把外部指标 JSON 回填到资产库 metrics 字段。

    metrics_file 格式：{"items": [{"item_id": "...", "impressions": N,
      "clicks": N, "engagements": N, "uv": N}, ...]}
    返回更新条数。
    """
    if not metrics_file.exists():
        logger.warning("指标文件不存在: %s", metrics_file)
        return 0
    try:
        mdata = json.loads(metrics_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        logger.error("解析指标文件失败: %s", e)
        return 0
    data = load_inventory(inventory_path)
    by_id = {it["id"]: it for it in data["items"]}
    updated = 0
    for row in mdata.get("items", []):
        rec = by_id.get(row.get("item_id"))
        if not rec:
            continue
        metrics = rec.setdefault("metrics", {})
        for k in ("impressions", "clicks", "engagements", "uv"):
            if k in row:
                metrics[k] = int(row.get(k, 0) or 0)
        updated += 1
    if updated:
        save_inventory(data, inventory_path)
    logger.info("数据回流完成，更新 %d 条", updated)
    return updated

# ============================================================
# 日报 / 周报数据
# ============================================================


def summarize_daily(data: dict, d: date = None) -> dict:
    """日报社媒数据板块：昨日发布数、各平台曝光/点击、引流 UV。"""
    d = d or date.today() - timedelta(days=1)
    ds = d.isoformat()
    published = [i for i in data["items"]
                 if i.get("status") == "已发布" and i.get("publish_date") == ds]
    by_platform = {}
    for p in PLATFORMS:
        by_platform[p] = {"published": 0, "impressions": 0, "clicks": 0, "uv": 0}
    for i in published:
        p = i.get("platform")
        m = i.get("metrics", {})
        by_platform[p]["published"] += 1
        by_platform[p]["impressions"] += m.get("impressions", 0)
        by_platform[p]["clicks"] += m.get("clicks", 0)
        by_platform[p]["uv"] += m.get("uv", 0)
    return {
        "date": ds,
        "total_published": len(published),
        "total_impressions": sum(x["impressions"] for x in by_platform.values()),
        "total_clicks": sum(x["clicks"] for x in by_platform.values()),
        "total_uv": sum(x["uv"] for x in by_platform.values()),
        "by_platform": by_platform,
    }


def summarize_weekly(data: dict, end: date = None) -> dict:
    """周报社媒增长复盘：总量、分平台、Top5/Bottom5、类型对比、下周建议。"""
    end = end or date.today()
    start = end - timedelta(days=6)
    published = [i for i in data["items"]
                 if i.get("status") == "已发布"
                 and start.isoformat() <= i.get("publish_date", "") <= end.isoformat()]
    by_platform = {p: {"published": 0, "impressions": 0, "clicks": 0, "uv": 0}
                   for p in PLATFORMS}
    by_type = {}
    for i in published:
        p, t = i.get("platform"), i.get("type")
        m = i.get("metrics", {})
        by_platform[p]["published"] += 1
        by_platform[p]["impressions"] += m.get("impressions", 0)
        by_platform[p]["clicks"] += m.get("clicks", 0)
        by_platform[p]["uv"] += m.get("uv", 0)
        bt = by_type.setdefault(t, {"count": 0, "impressions": 0, "clicks": 0})
        bt["count"] += 1
        bt["impressions"] += m.get("impressions", 0)
        bt["clicks"] += m.get("clicks", 0)
    # 表现分 = impressions 主 + clicks 加权
    scored = []
    for i in published:
        m = i.get("metrics", {})
        score = m.get("impressions", 0) + m.get("clicks", 0) * 3
        scored.append({"id": i["id"], "source_article": i["source_article"],
                       "platform": i["platform"], "type": i["type"], "score": score,
                       **m})
    scored.sort(key=lambda x: x["score"], reverse=True)
    top5 = scored[:5]
    bottom5 = scored[-5:] if len(scored) > 5 else scored
    advice = []
    for t, bt in sorted(by_type.items(), key=lambda x: -x[1]["impressions"]):
        ctr = (bt["clicks"] / bt["impressions"] * 100) if bt["impressions"] else 0
        advice.append(f"{t}: {bt['count']}条, 曝光{bt['impressions']}, CTR {ctr:.1f}%")
    return {
        "week_start": start.isoformat(),
        "week_end": end.isoformat(),
        "total_published": len(published),
        "by_platform": by_platform,
        "by_type": by_type,
        "top5": top5,
        "bottom5": bottom5,
        "type_advice": advice,
        "next_week_suggestion": "基于曝光/CTR 表现，优先复用高表现 type+platform 组合，减少低表现题材频次。",
    }


def build_report(which: str, data: dict = None, out: Path = None) -> dict:
    data = data or load_inventory()
    SOCIAL_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    if which == "daily":
        payload = summarize_daily(data)
        name = f"social_daily_{payload['date']}.json"
    else:
        payload = summarize_weekly(data)
        name = f"social_weekly_{payload['week_end']}.json"
    out = out or SOCIAL_REPORTS_DIR / name
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("社媒%s报告已写入 %s", which, out)
    return payload

# ============================================================
# 飞书通知（复用错误降级）
# ============================================================


def send_feishu(title: str, content: str) -> bool:
    webhook = os.environ.get("FEISHU_WEBHOOK_URL", "")
    if not webhook:
        logger.info("未配置 FEISHU_WEBHOOK_URL，跳过飞书推送")
        return False
    try:
        resp = requests.post(webhook, json={
            "msg_type": "text",
            "content": {"text": f"{title}\n{content}"},
        }, timeout=15)
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.warning("飞书推送失败: %s", e)
        return False

# ============================================================
# CLI
# ============================================================


def _cmd_build(args) -> int:
    data = build_inventory(top_n=args.top_n, force=args.force)
    items = data["items"]
    print(f"\n资产库: {INVENTORY_FILE}")
    print(f"总素材: {len(items)} 条")
    by_status = {}
    by_platform = {}
    for i in items:
        by_status[i["status"]] = by_status.get(i["status"], 0) + 1
        by_platform[i["platform"]] = by_platform.get(i["platform"], 0) + 1
    print(f"状态: {by_status}")
    print(f"平台: {by_platform}")
    return 0


def _cmd_list(args) -> int:
    data = load_inventory()
    items = filter_items(data, platform=args.platform, ctype=args.type,
                         status=args.status, source_article=args.article)
    print(f"筛选到 {len(items)} 条:")
    for i in items[:args.limit]:
        print(f"  [{i['id']}] {i['platform']:9s} {i['type']:10s} {i['status']:4s} "
              f"{i['source_article'][:50]}")
    return 0


def _parse_date(arg: str):
    """解析 CLI 日期参数：支持 today / yesterday / 明天 / 具体 YYYY-MM-DD。"""
    if not arg:
        return None
    s = str(arg).strip().lower()
    today = date.today()
    if s in ("today", "今天", "今日"):
        return today
    if s in ("yesterday", "昨天"):
        return today - timedelta(days=1)
    if s in ("tomorrow", "明天"):
        return today + timedelta(days=1)
    return date.fromisoformat(arg)


def recycle_expired_items(data: dict, cooldown_days: int = REUSE_COOLDOWN_DAYS) -> int:
    """素材轮换复活：已发布超过冷却期的素材重新生成文案，回到待审核池。

    网站不会每天新增文章，但社媒每天需要发布内容。
    存量素材发布满一轮后，超过冷却期的自动复活（重新生成 caption 避免内容重复），
    保证"待审核"池始终有素材可排期，实现存量循环发布。
    """
    today = date.today()
    recycled = 0
    items = data.get("items", [])
    for it in items:
        if it.get("status") != "已发布":
            continue
        pub = it.get("publish_date") or ""
        try:
            pub_dt = date.fromisoformat(pub)
        except Exception:
            continue
        if (today - pub_dt).days < cooldown_days:
            continue
        # 重新生成文案（模板生成，不依赖 LLM）
        article = {
            "slug": it.get("source_article", ""),
            "title": it.get("source_title", ""),
            "url": f"https://www.{SITE_DOMAIN}/{it.get('source_article', '')}/",
            "description": "",
            "cover": it.get("image_url", ""),
        }
        campaign = f"cbt_social_{today.strftime('%Y%m%d')}"
        try:
            gen = generate_one(article, it.get("type", "knowledge"),
                               it.get("platform", "x"), campaign)
            text = gen["text"]
            text = llm_enhance(article, it.get("type", "knowledge"),
                               it.get("platform", "x"), text)
            ok, res = validate_copy(text)
            if not ok:
                text = gen["text"]
        except Exception as _e:
            logger.warning("素材复活重生成失败 %s: %s", it.get("id", "?"), _e)
            continue
        it["caption"] = text
        it["status"] = "待审核"
        it["publish_date"] = ""
        it["recycled_at"] = today.isoformat()
        it["recycle_count"] = it.get("recycle_count", 0) + 1
        recycled += 1
    if recycled:
        save_inventory(data)
    return recycled


def _cmd_plan(args) -> int:
    data = load_inventory()
    # 先复活过期素材，保证待审核池不空（存量循环）
    recycled = recycle_expired_items(data)
    if recycled:
        logger.info("素材轮换复活 %d 条（已发布超 %d 天，重新生成文案回到待审核池）",
                    recycled, REUSE_COOLDOWN_DAYS)
    start = _parse_date(args.date)
    sched = build_schedule(data, start_date=start)
    out = SOCIAL_REPORTS_DIR / f"social_schedule_{date.today().isoformat()}.json"
    SOCIAL_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"schedule": sched, "generated_at": datetime.now().isoformat()},
                              ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(len(d["slots"]) for d in sched)
    print(f"排期计划已生成: {out}（{total} 条，{len(sched)} 天）")
    for d in sched[:7]:
        print(f"  {d['date']}: " + ", ".join(s["item_id"] for s in d["slots"]))
    return 0


def _cmd_gen_images(args) -> int:
    """为资产库素材批量生成独立配图（真实文生图）。幂等：已生成且未 --force 的跳过。"""
    data = load_inventory()
    items = data["items"]
    targets = []
    for it in items:
        if it.get("image_generated") and not args.force:
            continue
        if it.get("image_url") and it.get("status") == "已发布" and not args.force:
            # 已发布素材默认不重写（避免改已上线配图），--force 可强制
            continue
        targets.append(it)
    if args.limit and args.limit > 0:
        targets = targets[: args.limit]
    ok = 0
    for it in targets:
        try:
            _gen_url = generate_image(it, None)
        except Exception as _e:
            logger.warning("generate_image 异常 %s: %s", it.get("id", "?"), _e)
            _gen_url = ""
        if _gen_url:
            it["image_url"] = _gen_url
            it["image_generated"] = True
            it.pop("image_optimized", None)
            ok += 1
            print(f"  OK [{it['id']}] {it['platform']} {it['type']} -> {_gen_url}")
        else:
            print(f"  SKIP [{it['id']}] {it['platform']} 生成失败，保留原封面")
        time.sleep(1)
    save_inventory(data)
    print(f"\n[SUMMARY] 生成独立配图 {ok}/{len(targets)} 条")
    return 0


def _cmd_publish(args) -> int:
    data = load_inventory()
    target_date = None
    if args.date:
        target_date = _parse_date(args.date)
        sched = build_schedule(data, start_date=target_date)
        target = [s for s in sched if s["date"] == target_date.isoformat()]
        ids = [sl["item_id"] for d in target for sl in d["slots"]]
        items = [i for i in data["items"] if i["id"] in ids]
    elif args.item_ids:
        ids = [x.strip() for x in args.item_ids.split(",")]
        items = [i for i in data["items"] if i["id"] in ids]
    else:
        items = filter_items(data, status="待审核")[:3]

    if not items:
        day = target_date.isoformat() if target_date else date.today().isoformat()
        print(f"[INFO] {day} 无待发布素材（今日无排期或素材未审核），跳过发布")
        return 0

    dry_run = not args.auto and not args.confirm
    if not dry_run and not args.auto:
        print("\n半自动模式：以下素材待发布，确认后逐个发送。")
        for i, it in enumerate(items, 1):
            print(f"  [{i}] {it['platform']:9s} {it['type']:10s} {it['source_article'][:45]}")
        ans = input("确认发布以上 %d 条? [y/N] " % len(items)).strip().lower()
        if ans not in ("y", "yes"):
            print("已取消")
            return 1

    results = distribute_items(items, dry_run=dry_run)
    for r in results:
        mark = "✅" if r.get("success") else "❌"
        detail = (r.get("platforms")
                  or ("skipped: duplicate" if r.get("skipped") else r.get("error") or "queued"))
        print(f"  {mark} {r['item_id']} {r['platform']} -> {detail}")
    ok = sum(1 for r in results if r.get("success"))
    print(f"[SUMMARY] {ok}/{len(results)} 成功")
    return 0 if ok == len(results) else 1


def _cmd_backfill(args) -> int:
    updated = backfill_metrics(Path(args.file))
    print(f"已更新 {updated} 条素材的 metrics")
    return 0


def _cmd_report(args) -> int:
    payload = build_report(args.which)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="ChinaBound 社媒增长引擎")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("build-inventory", help="批量生成素材入库")
    p.add_argument("--top-n", type=int, default=DEFAULT_TOP_N)
    p.add_argument("--force", action="store_true", help="重新生成（覆盖已有签名）")
    p.set_defaults(func=_cmd_build)

    p = sub.add_parser("list", help="列出素材")
    p.add_argument("--platform", choices=PLATFORMS)
    p.add_argument("--type", dest="type", choices=TYPES)
    p.add_argument("--status")
    p.add_argument("--article")
    p.add_argument("--limit", type=int, default=50)
    p.set_defaults(func=_cmd_list)

    p = sub.add_parser("plan", help="生成排期")
    p.add_argument("--date")
    p.set_defaults(func=_cmd_plan)

    p = sub.add_parser("gen-images", help="为资产库素材批量生成独立配图（真实文生图）")
    p.add_argument("--limit", type=int, default=0, help="最多生成 N 条（0=全部）")
    p.add_argument("--force", action="store_true", help="强制重生成（含已生成/已发布）")
    p.set_defaults(func=_cmd_gen_images)

    p = sub.add_parser("plan-pilot", help="P1-GROWTH-29 社媒试点排期（Pinterest 2/天 + IG 1/天）")
    p.add_argument("--start", default=None, help="开始日期 YYYY-MM-DD（默认明天）")
    p.add_argument("--days", type=int, default=7, help="试点天数 7-14（默认 7，库存限制）")
    p.set_defaults(func=_cmd_plan_pilot)

    p = sub.add_parser("publish", help="发布（自动/半自动）")
    p.add_argument("--auto", action="store_true", help="自动模式")
    p.add_argument("--confirm", action="store_true", help="半自动模式（免交互，直接发布待审核）")
    p.add_argument("--date")
    p.add_argument("--item-ids")
    p.set_defaults(func=_cmd_publish)

    p = sub.add_parser("backfill-metrics", help="数据回流")
    p.add_argument("--file", required=True)
    p.set_defaults(func=_cmd_backfill)

    p = sub.add_parser("report", help="社媒日报/周报")
    p.add_argument("which", choices=["daily", "weekly"])
    p.set_defaults(func=_cmd_report)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
