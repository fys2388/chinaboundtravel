#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
social_backfill.py - ChinaBound 2.0 社媒补位脚本（P0-2）

背景：2.0 Editorial Voice 升级后社媒流量断崖（周同比 -91.7%），Buffer 双账户
排期可能为空。本脚本将站内高流量/高质量文章批量回填到 Buffer Worker，
并生成未来 7 天的排期计划。

流程：
  1. 从 content/posts/ 选取浏览量最高、内容质量最好的文章（默认 5 篇）
     - 优先 GA4 历史数据（reports/feishu_daily/*.json / *ga4*.json 缓存）
     - 无缓存时回退到本地 front matter 信号（weight / 更新日期 / 描述质量）
     - 排除近 14 天已分发的文章（manifest_rotator.json）
  2. 每篇生成 2 条社媒文案（IG 版 + Pinterest 版），2.0 Editorial Voice
  3. 自动调用 brand_identity_audit 规则（forbidden phrases + persona 模式）校验，
     不合格自动重写（最多 3 轮），仍不合格标记 needs_manual_review
  4. 输出待发布列表 reports/social_backfill_plan_YYYYMMDD.json
  5. 支持通过 Buffer Worker API 批量排期发布（未来 7 天，<=3 篇/天）

双账户路由（与 buffer-worker v3.0.1 保持一致）：
  - IG/X/FB   -> BUFFER_WORKER_URL     （Buffer-A token，worker 内部路由）
  - Pinterest -> NEW_BUFFER_WORKER_URL （Buffer-B token，worker 内部路由）
  两个 URL 均可通过环境变量覆盖；默认指向生产 Worker 同一端点
  （worker /publish 会把一条文案按账户分流到对应渠道）。

用法：
  python scripts/social_backfill.py                       # dry-run：生成文案+排期计划
  python scripts/social_backfill.py --publish             # 真实发布（全部计划项）
  python scripts/social_backfill.py --publish --date 2026-08-18   # 只发当天批次
  python scripts/social_backfill.py --count 3 --dry-run
"""
import argparse
import json
import os
import re
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
BLOG_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.stdout.reconfigure(encoding="utf-8")

# 品牌审计规则复用（forbidden phrases + persona 模式）
from brand_identity_audit import scan_text  # noqa: E402

# P1-OPS-04: 社媒文案清理公共工具（shortcode 剥离、描述去标题前缀、句子边界截断、配图过滤）
from social_text_utils import (  # noqa: E402
    clean_social_text,
    first_meaningful_desc,
    image_rejection_reason,
    strip_shortcodes,
    validate_social_copy,
)

# ============================================================
# 配置
# ============================================================

SITE_DOMAIN = "chinaboundtravel.com"
POSTS_DIR = BLOG_ROOT / "content" / "posts"
REPORTS_DIR = BLOG_ROOT / "reports"
MANIFEST_ROTATOR = BLOG_ROOT / "manifest_rotator.json"
MANIFEST_MAIN = BLOG_ROOT / "manifest.json"

# 双账户路由端点（可用环境变量覆盖；默认指向生产 Worker 同一端点）
ACCOUNT_A_URL = os.environ.get(
    "BUFFER_WORKER_URL", "https://buffer-worker.chinaboundtravel.com/publish"
)  # IG/X/FB
ACCOUNT_B_URL = os.environ.get(
    "NEW_BUFFER_WORKER_URL", ACCOUNT_A_URL
)  # Pinterest

COOLDOWN_DAYS = 14        # 同篇 14 天内不重复分发
PLAN_DAYS = 7             # 排期窗口
MAX_PER_DAY = 3           # 与 worker 全局单日上限一致
REWRITE_ATTEMPTS = 3      # 品牌校验失败自动重写次数
DEFAULT_COUNT = 5         # 默认补位文章数

# 2.0 品牌不追投的 legacy persona 题材 slug 标记
LEGACY_SLUG_MARKERS = (
    "californian", "my-mother", "dude-wheres", "gastronomic-adventure",
    "aussie-kiwi", "foodies-guide",
)

# 核心流量页加成：来源为 2026-08 GA4 日报 Top Pages 记录（本地无 GA4 缓存时的兜底信号）
KNOWN_TOP_PAGES = {
    "144-hour-visa-free-transit-guide",
    "china-bargaining-and-shopping-guide",
    "chinese-tea-culture-where-to-experience-authentic-teahouses",
    "chinas-food-through-the-ages-guide",
    "china-packing-list-2026-what-to-bring-and-what-to-leave-at-home",
    "china-photography-guide-capturing-the-wonders-of-the-middle-kingdom",
}

# ============================================================
# 文章解析
# ============================================================


def parse_frontmatter(content: str) -> dict:
    fm_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    frontmatter = {}
    if fm_match:
        for line in fm_match.group(1).split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and value:
                    frontmatter[key] = value
    return frontmatter


def _extract_cover(fm_text: str, content: str) -> str:
    """提取封面：front matter cover.image 优先，正文实景图兜底。

    兼容 cover 块内 alt 在 image 之前/之后的多行写法：
      cover:
        alt: "..."
        image: "https://..."
    """
    # 多行 cover 块：在 cover: 到下一个顶层键之间找 image:
    cover_match = re.search(
        r'^\s*cover\s*:\s*(?:\n(?!\S).*)*?\n\s*image\s*:\s*"?([^"\n]+)"?',
        fm_text, re.MULTILINE
    )
    if not cover_match:
        # 单行 cover: "url" 或 cover: image: "url"
        cover_match = re.search(r'^\s*cover\s*:\s*(?:image\s*:\s*)?\'?"?([^"\'\n]+)"?\'?',
                                fm_text, re.MULTILINE)
    if cover_match:
        url = cover_match.group(1).strip()
        if url and not url.startswith("http"):
            url = f"https://{SITE_DOMAIN}{url}"
        if url:
            return url
    for m in re.finditer(r"!\[([^\]]*)\]\(([^)]+)\)", content):
        img_alt = m.group(1)
        img = m.group(2)
        if img and ("pollinations" in img or "unsplash" in img or SITE_DOMAIN in img):
            if not img.startswith("http"):
                img = f"https://{SITE_DOMAIN}{img}"
            # 发布规则：禁止人物/头像、禁止抽象图
            if image_rejection_reason(alt=img_alt, url=img):
                continue
            return img
    return ""


def _extract_headings(body: str, title: str = "") -> list:
    """提取 H2/H3 标题作为价值点（最多 3 个，过滤第一人称/问候语/标题重复）。"""
    first_person = re.compile(
        r"^(let me|i'll|i will|i have|i had|my |how i|what i|why i|when i|i remember|i moved|i lived|hey|hello|hi |welcome)",
        re.IGNORECASE,
    )
    generic_headings = {
        "introduction", "overview", "background", "conclusion", "summary",
        "faq", "contents", "table of contents", "what you'll learn",
        "key takeaways", "getting started", "final thoughts",
    }
    norm = lambda s: re.sub(r"[^a-z0-9 ]", "", s.lower())
    title_norm = norm(title)
    h1_match = re.search(r"^\s{0,3}#\s+(.+)$", body, re.MULTILINE)
    h1_norm = norm(h1_match.group(1)) if h1_match else ""
    headings = []
    for line in body.split("\n"):
        m = re.match(r"^\s{0,3}#{2,3}\s+(.+)$", line)
        if m:
            h = re.sub(r"[*_`\[\]()]", "", m.group(1)).strip()
            hl = h.lower().rstrip(".:?!")
            if hl and hl not in generic_headings and hl not in ("contents", "faq", "conclusion"):
                if first_person.match(h) or "joran" in hl or "👋" in h:
                    continue
                h_norm = norm(h)
                if title_norm and (h_norm in title_norm or title_norm in h_norm):
                    continue
                if h1_norm and (h_norm in h1_norm or h1_norm in h_norm):
                    continue
                if len(h) < 12 or len(h) > 90:
                    continue
                headings.append(h)
        if len(headings) >= 3:
            break
    return headings


def parse_article(md_path: Path) -> dict:
    try:
        content = md_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = md_path.read_text(encoding="latin-1")

    fm = parse_frontmatter(content)
    fm_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    fm_text = fm_match.group(1) if fm_match else ""
    body = content[fm_match.end():] if fm_match else content

    slug = fm.get("slug", md_path.stem)
    canonical = fm.get("canonicalURL", "")
    if canonical:
        if not canonical.startswith("http"):
            canonical = f"https://{canonical}"
        url = canonical
    else:
        url = f"https://{SITE_DOMAIN}/posts/{slug}/"

    # P1-OPS-04: 剥离 shortcode/HTML/markdown 符号，描述去标题前缀、句子边界截断
    body_clean = clean_social_text(body)
    description = first_meaningful_desc(
        fm.get("description") or body_clean, fm.get("title", ""), 300,
    )

    pub_date = None
    for key in ("date", "updated", "lastmod"):
        val = fm.get(key, "")
        if val:
            try:
                pub_date = datetime.fromisoformat(val.replace("Z", "+00:00")).date()
                break
            except ValueError:
                continue

    return {
        "title": fm.get("title", md_path.stem.replace("-", " ").title()),
        "description": description.strip(),
        "slug": slug,
        "url": url,
        "content_id": fm.get("content_id", ""),
        "weight": int(fm["weight"]) if str(fm.get("weight", "")).isdigit() else None,
        "date": pub_date,
        "cover": _extract_cover(fm_text, content),
        "headings": _extract_headings(body, fm.get("title", "")),
        "source_file": str(md_path),
    }


def discover_articles() -> list:
    articles = []
    for md_file in sorted(POSTS_DIR.glob("*.md")):
        if md_file.name.startswith("."):
            continue
        try:
            articles.append(parse_article(md_file))
        except Exception as e:
            print(f"  [WARN] 解析失败 {md_file.name}: {e}")
    return articles

# ============================================================
# 数据信号（GA4 缓存 + 分发 manifest）
# ============================================================


def load_ga4_pageviews() -> dict:
    """汇总本地 GA4 缓存中的页面浏览量（slug -> views）。"""
    views = {}
    patterns = ("feishu_daily/*.json", "*ga4*.json", "*_GA4_*.json", "management/*.json")
    for pattern in patterns:
        for f in sorted(REPORTS_DIR.glob(pattern)):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            for row in data.get("top_pages") or []:
                path = row.get("pagePath") or row.get("path") or ""
                v = row.get("views") or row.get("pageviews") or row.get("screenPageViews") or 0
                try:
                    v = float(v)
                except (TypeError, ValueError):
                    continue
                slug = path.rstrip("/").split("/")[-1]
                if slug:
                    views[slug] = views.get(slug, 0) + v
    return views


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_processed_slugs() -> set:
    data = _load_json(MANIFEST_MAIN)
    return set(data.get("processed_social_posts") or [])


def recently_distributed(article: dict) -> bool:
    """manifest_rotator.json 中近 COOLDOWN_DAYS 天已分发过 -> True。"""
    data = _load_json(MANIFEST_ROTATOR)
    record = data.get("articles", {}).get(article["slug"])
    if not record:
        return False
    cutoff = (date.today() - timedelta(days=COOLDOWN_DAYS)).isoformat()
    for last in (record.get("platforms") or {}).values():
        if str(last) >= cutoff:
            return True
    return False

# ============================================================
# 选文评分
# ============================================================


def legacy_hits(article: dict) -> list:
    """标题/描述/摘要中的 legacy persona 短语命中（2.0 不追投的题材）。"""
    text = " ".join(filter(None, [
        article.get("title", ""), article.get("description", ""),
        article.get("summary", ""),
    ]))
    res = scan_text(text or "")
    return (res.get("forbidden") or []) + (res.get("fictional") or [])


def score_article(article: dict, ga4_views: dict, processed: set) -> float:
    score = 0.0
    # 2.0 品牌惩罚：描述/标题含 legacy persona 短语 -> 大幅降权（默认不追投）
    score -= min(len(legacy_hits(article)), 3) * 100
    if article["weight"]:
        score += max(0, 100 - article["weight"] * 10)
    if article["date"]:
        days_old = (date.today() - article["date"]).days
        if days_old <= 30:
            score += 15
        elif days_old <= 60:
            score += 5
    desc_len = len(article["description"] or "")
    if desc_len >= 80:
        score += 10
    elif desc_len >= 40:
        score += 5
    slug = article["slug"].lower()
    if any(m in slug for m in LEGACY_SLUG_MARKERS):
        score -= 50
    score += min(ga4_views.get(article["slug"], 0), 50)
    if article["slug"] in KNOWN_TOP_PAGES:
        score += 25
    if slug in processed:
        score -= 5
    return score


def select_articles(articles: list, count: int, ga4_views: dict, processed: set) -> list:
    candidates = [a for a in articles if a["cover"] and not recently_distributed(a)]
    if not candidates:
        candidates = [a for a in articles if a["cover"]]
    ranked = sorted(candidates, key=lambda a: score_article(a, ga4_views, processed), reverse=True)
    return ranked[:count]

# ============================================================
# 2.0 Editorial Voice 文案生成
# ============================================================


def _hook_for(title: str) -> str:
    t = title.lower()
    if any(k in t for k in ("visa", "transit", "entry")):
        return "China entry rules for 2026: what international travelers should know before booking."
    if "packing" in t:
        return "What belongs in a 2026 China packing list? A research-based checklist for international travelers."
    if any(k in t for k in ("alipay", "wechat", "payment")):
        return "Mobile payments in China, explained for international visitors — what to set up before you land."
    if any(k in t for k in ("train", "transport", "high-speed")):
        return "Getting around China by train: a practical guide to booking, classes, and station logistics."
    if any(k in t for k in ("food", "tea", "street")):
        return "China food and drink essentials, from street snacks to teahouse etiquette."
    return "Planning a trip to China? This research-based guide covers what international travelers actually need."


def build_utm(url: str, source: str, campaign: str) -> str:
    parts = urlparse(url)
    params = dict(parse_qsl(parts.query))
    params.update({
        "utm_source": source,
        "utm_medium": "social",
        "utm_campaign": campaign,
        "utm_content": f"{source}_v1",
    })
    return urlunparse(parts._replace(query=urlencode(params)))


def truncate(text: str, max_chars: int) -> str:
    """按句子边界截断，避免残句（如 "from a ."）。"""
    text = re.sub(r"\s+", " ", (text or "").strip())
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    # 优先在最近的句号后截断
    for ender in (". ", "! ", "? "):
        idx = cut.rfind(ender)
        if idx > max_chars * 0.5:
            return cut[: idx + 1].rstrip()
    idx = cut.rfind(" ")
    return cut[:idx] if idx > 0 else cut


def _safe_description(article: dict) -> str:
    """防御性清洗：移除 shortcode、HTML 残留与 forbidden phrases（复制前先净化）。"""
    desc = article.get("description") or ""
    desc = strip_shortcodes(desc)
    _, res = validate_copy(desc)
    for phrase in (res.get("forbidden") or []) + (res.get("fictional") or []):
        desc = re.sub(re.escape(phrase), "", desc, flags=re.IGNORECASE)
    return re.sub(r"\s{2,}", " ", desc).strip()


def generate_ig_copy(article: dict, utm_url: str) -> str:
    points = article.get("headings") or []
    lines = [_hook_for(article["title"]), ""]
    if points:
        for p in points[:3]:
            lines.append(f"· {truncate(p, 90)}")
        lines.append("")
    desc = truncate(_safe_description(article), 220)
    if desc:
        lines.append(desc)
        lines.append("")
    lines.append(f"Read the full guide: {utm_url}")
    lines.append("")
    lines.append("#ChinaTravel #VisitChina #ChinaTrip #China2026")
    return "\n".join(lines)


def generate_pinterest_copy(article: dict, utm_url: str) -> str:
    lines = [truncate(article["title"], 110), ""]
    desc = truncate(_safe_description(article), 260)
    if desc:
        lines.append(desc)
        lines.append("")
    lines.append("📌 Save this for your China trip planning.")
    lines.append("")
    lines.append(f"Full guide: {utm_url}")
    return "\n".join(lines)


def _strip_flagged(text: str, flagged: list) -> str:
    for phrase in flagged or []:
        text = re.sub(re.escape(phrase), "", text, flags=re.IGNORECASE)
    return re.sub(r"\s{2,}", " ", text).strip()


def safe_slug_title(article: dict) -> str:
    title = " ".join(article["slug"].replace("-", " ").split()).title()
    return truncate(title, 100)


def generate_compliant_copies(article: dict, campaign: str) -> list:
    """为每篇生成 IG + Pinterest 两条 2.0 文案，品牌校验不合格自动重写。"""
    outputs = []
    for variant, gen_fn in (("ig", generate_ig_copy), ("pinterest", generate_pinterest_copy)):
        utm_url = build_utm(article["url"], variant, campaign)
        last_res = None
        final_text = None
        for attempt in range(1, REWRITE_ATTEMPTS + 1):
            if attempt == 1:
                text = gen_fn(article, utm_url)
            elif attempt == 2:
                text = _strip_flagged(gen_fn(article, utm_url), last_res.get("forbidden") + last_res.get("fictional") if last_res else [])
            else:
                safe_article = dict(article)
                safe_article["title"] = safe_slug_title(article)
                safe_article["description"] = truncate(article["description"], 100)
                safe_article["headings"] = []
                text = gen_fn(safe_article, utm_url)
            ok, res = validate_copy(text)
            if ok:
                final_text = text
                break
            last_res = res
        if final_text is None:
            outputs.append({
                "variant": variant, "text": gen_fn(article, utm_url), "ok": False,
                "issues": (last_res or {}).get("forbidden", []) + (last_res or {}).get("fictional", []),
            })
        else:
            outputs.append({"variant": variant, "text": final_text, "ok": True, "issues": []})
    return outputs


def validate_copy(text: str):
    res = scan_text(text)
    ok = not res.get("forbidden") and not res.get("fictional")
    return ok, res

# ============================================================
# 排期计划 + 发布
# ============================================================


def build_plan(items: list, start_date: date = None) -> list:
    """把待发布项铺到未来 PLAN_DAYS 天，每天最多 MAX_PER_DAY 条。"""
    cursor = start_date or date.today()
    plan = []
    day_offset, per_day = 0, 0
    for item in items:
        if per_day >= MAX_PER_DAY:
            day_offset += 1
            per_day = 0
        plan.append({
            "date": (cursor + timedelta(days=day_offset)).isoformat(),
            "slot": per_day + 1,
            **item,
        })
        per_day += 1
    return plan


def worker_endpoint(variant: str) -> str:
    return ACCOUNT_A_URL if variant == "ig" else ACCOUNT_B_URL


def publish_item(item: dict, dry_run: bool = True) -> dict:
    # P1-OPS-04: 发布前 lint —— 有致命问题（shortcode/空链接/人设/标题重复等）一律拒绝发布
    problems = validate_social_copy(
        item.get("text", ""), title=item.get("title", ""), url=item.get("url", ""),
    )
    if problems:
        return {"success": False, "dry_run": dry_run, "error": "LINT_FAILED: " + "; ".join(problems),
                "lint": problems}
    payload = {
        "title": item["title"],
        "desc": item["text"],
        "cover": item["cover"],
        "url": item["url"],
        "custom_text": item["text"],
        "content_id": item.get("content_id", ""),
        "content_variant": item["variant"],
        "source_workflow": "social_backfill",
        # 2026-08-28 修复：显式声明目标平台（ig->instagram 由 worker 归一化），防止广播
        "platforms": [item["variant"]],
    }
    endpoint = worker_endpoint(item["variant"])
    if dry_run:
        return {"success": True, "dry_run": True, "endpoint": endpoint, "detail": "dry-run 未发送"}
    try:
        resp = requests.post(endpoint, json=payload, timeout=90)
        resp.raise_for_status()
        data = resp.json()
        platforms = (data.get("platforms") or {}).get("success", [])
        return {"success": bool(data.get("success")), "endpoint": endpoint,
                "platforms": platforms, "error": data.get("message") or data.get("error", "")}
    except requests.exceptions.Timeout:
        return {"success": False, "endpoint": endpoint, "error": "Timeout after 90s"}
    except requests.exceptions.HTTPError as e:
        return {"success": False, "endpoint": endpoint, "error": f"HTTP {e.response.status_code}"}
    except Exception as e:
        return {"success": False, "endpoint": endpoint, "error": str(e)}

# ============================================================
# 主流程
# ============================================================


def run(count: int, dry_run: bool, publish_date: str = None) -> int:
    print("=" * 66)
    print("🌐 ChinaBound 2.0 社媒补位 (social_backfill)")
    print(f"模式: {'DRY-RUN 预览' if dry_run else 'LIVE 发布'} | 文章数: {count}")
    print("=" * 66)

    articles = discover_articles()
    print(f"\n[SCAN] 解析文章 {len(articles)} 篇")

    ga4_views = load_ga4_pageviews()
    processed = load_processed_slugs()
    if ga4_views:
        print(f"[GA4] 命中缓存页面 {len(ga4_views)} 个 slug")
    else:
        print("[GA4] 无本地缓存，使用 front matter 信号排序")

    selected = select_articles(articles, count, ga4_views, processed)
    if not selected:
        print("[DONE] 没有可补位的文章（均缺少封面或近期已分发）")
        return 1

    campaign = f"social_backfill_{date.today().strftime('%Y%m%d')}"
    items = []
    for article in selected:
        copies = generate_compliant_copies(article, campaign)
        for c in copies:
            items.append({
                "title": article["title"],
                "slug": article["slug"],
                "url": article["url"],
                "cover": article["cover"],
                "content_id": article.get("content_id", ""),
                "variant": c["variant"],
                "text": c["text"],
                "ok": c["ok"],
                "issues": c["issues"],
            })

    plan = build_plan(items)
    plan_file = REPORTS_DIR / f"social_backfill_plan_{date.today().strftime('%Y%m%d')}.json"
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    plan_file.write_text(json.dumps({
        "generated_at": datetime.now().isoformat(),
        "campaign": campaign,
        "count": len(items),
        "routing": {
            "ig": ACCOUNT_A_URL,
            "pinterest": ACCOUNT_B_URL,
        },
        "plan": plan,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n[PLAN] 待发布 {len(items)} 条，计划文件: {plan_file}")
    print(f"       排期窗口: {plan[0]['date']} ~ {plan[-1]['date']}（每天 ≤{MAX_PER_DAY} 条）")
    print(f"       路由: IG/X/FB -> {ACCOUNT_A_URL}")
    print(f"              Pinterest -> {ACCOUNT_B_URL}")
    print("\n" + "-" * 66)
    for p in plan:
        mark = "✅" if p["ok"] else "❌ manual_review"
        print(f"  [{p['date']} #{p['slot']}] {mark} {p['variant']:9s} {p['title'][:52]}")
        if not p["ok"]:
            print(f"       需人工复核: {'; '.join(p['issues'][:3])}")
    print("-" * 66)

    if dry_run:
        print("\n[dry-run] 未调用 Buffer Worker。手动触发命令：")
        print(f"  python scripts/social_backfill.py --publish")
        print(f"  python scripts/social_backfill.py --publish --date {date.today().isoformat()}")
        return 0

    publishable = [p for p in plan if p["ok"] and (not publish_date or p["date"] == publish_date)]
    if not publishable:
        print("\n[DONE] 没有符合条件的可发布项")
        return 1

    print(f"\n[PUBLISH] 发送 {len(publishable)} 条到 Buffer Worker...")
    results = []
    for i, p in enumerate(publishable, 1):
        print(f"  [{i}/{len(publishable)}] {p['variant']} {p['title'][:50]}...")
        res = publish_item(p, dry_run=False)
        results.append({"slug": p["slug"], "variant": p["variant"], **res})
        status = "OK" if res["success"] else "FAIL"
        detail = res.get("platforms") or res.get("error") or "queued"
        print(f"      -> [{status}] {detail}")
        if i < len(publishable):
            time.sleep(2)

    ok = sum(1 for r in results if r["success"])
    print(f"\n[SUMMARY] {ok}/{len(results)} 发布成功")
    return 0 if ok == len(results) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="ChinaBound 2.0 社媒补位脚本")
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT,
                        help=f"补位文章数（默认 {DEFAULT_COUNT}）")
    parser.add_argument("--publish", action="store_true", help="真实发布（默认 dry-run）")
    parser.add_argument("--dry-run", action="store_true", help="强制预览，不发送")
    parser.add_argument("--date", type=str, default=None,
                        help="只发布指定日期 YYYY-MM-DD 的批次（配合 --publish）")
    args = parser.parse_args()

    dry_run = not args.publish or args.dry_run
    return run(args.count, dry_run=dry_run, publish_date=args.date)


if __name__ == "__main__":
    sys.exit(main())