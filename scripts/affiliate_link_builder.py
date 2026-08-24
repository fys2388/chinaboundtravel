#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
affiliate_link_builder.py - 全站联盟链接精细化布局引擎
==========================================================

v2.0：按文章主题自动匹配对应联盟产品组合，插入 2-3 处 Editorial Voice
软推荐（avoid 硬广），并输出分产品转化统计。

主题 → 产品组合映射：
  - 签证 / 出行准备类  -> 机票(flight) + 旅行保险(insurance) + eSIM(esim)
  - 城市攻略类         -> 酒店(hotel) + 当地一日游/门票(tour) [+ eSIM 兜底]
  - 交通攻略类         -> 机票(flight) + 高铁接送/门票(tour 兜底)
  - 通用兜底           -> eSIM(esim) + 保险(insurance)

规则：
  - 已在文内出现的联盟 shortcode（affiliate-* / soft-recommend / ab-cta /
    affiliate-mid-cta / affiliate-link）视为"已覆盖"，跳过对应产品，避免重复。
  - 每篇最多插入 SOFT_MAX 处（默认 3），不足则由未覆盖产品补齐。
  - 软推荐文案为 2.0 Editorial Voice（无第一人称虚构体验、无夸大促销）。
  - 真实 URL 由 hugo.toml [params.affiliate.<partner>] 解析；缺配置则不写。
  - --dry-run 默认：只预览不写文件；加 --apply 才实际落盘。
  - --coverage 输出全站覆盖率 + 分产品统计（JSON + 表格）。

用法：
  python scripts/affiliate_link_builder.py                     # dry-run 预览
  python scripts/affiliate_link_builder.py --apply             # 实际插入
  python scripts/affiliate_link_builder.py --coverage          # 统计/分产品
  python scripts/affiliate_link_builder.py --coverage --apply  # 先插后统计
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

SCRIPT_DIR = Path(__file__).resolve().parent
BLOG_ROOT = SCRIPT_DIR.parent
CONTENT_DIR = BLOG_ROOT / "content"
POSTS_DIR = CONTENT_DIR / "posts"
REPORTS_DIR = BLOG_ROOT / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
HUGO_TOML = BLOG_ROOT / "hugo.toml"

# ------------------------------------------------------------
# 主题 → 产品组合
# ------------------------------------------------------------
# 每个主题: 关键词(命中即判该主题) + 产品顺序(按优先级)
THEME_CONFIG = {
    "visa": {
        "label": "签证/出行准备",
        "keywords": ["visa", "visa-free", "transit", "144-hour", "240-hour",
                     "immigration", "entry requirement", "passport", "border",
                     "entry", "travel document", "packing", "what to bring",
                     "before you go", "preparation", "planning"],
        "products": ["flight", "insurance", "esim"],
    },
    "city": {
        "label": "城市攻略",
        "keywords": ["city", "beijing", "shanghai", "chengdu", "xian", "hangzhou",
                     "guilin", "destination", "itinerary", "attraction", "sightseeing",
                     "neighborhood", "day trip", "museum", "temple", "park",
                     "bund", "great wall", "west lake"],
        "products": ["hotel", "tour", "esim"],
    },
    "transport": {
        "label": "交通攻略",
        "keywords": ["train", "high-speed rail", "high speed rail", "subway", "metro",
                     "taxi", "flight", "airport", "transfer", "station", "transport",
                     "high-speed", "booking ticket", "12306", "bus", "flight to"],
        "products": ["flight", "tour"],
    },
    "food": {
        "label": "美食/文化",
        "keywords": ["food", "cuisine", "hotpot", "noodles", "tea", "street food",
                     "restaurant", "dining", "culture", "etiquette"],
        "products": ["tour", "esim"],
    },
    "payments": {
        "label": "支付/通讯",
        "keywords": ["payment", "alipay", "wechat pay", "wechat", "esim", "sim card",
                     "internet", "vpn", "data", "mobile payment", "app"],
        "products": ["esim", "insurance"],
    },
}
# 通用兜底（未命中任何主题时）
FALLBACK_PRODUCTS = ["esim", "insurance"]

# 产品逻辑名 -> hugo.toml [params.affiliate] 键名映射
# （tour 使用 Klook 的键）
PRODUCT_KEY_MAP = {
    "flight": "flight",
    "insurance": "safetywing",
    "esim": "esim",
    "hotel": "hotel",
    "tour": "klook",
}
# Klook 追踪 URL 常量（供一致性测试引用；与 hugo.toml params.affiliate.klook 一致）
KNOWN_TOUR_URL = "https://klook.tpo.li/vrPkmS2v"

# 已被视为"已覆盖联盟"的 shortcode 标记（任一出现即该文章已含联盟）
AFFILIATE_MARKERS = [
    "affiliate-hotel", "affiliate-flight", "affiliate-insurance",
    "affiliate-esim", "affiliate-tour", "affiliate-mid-cta",
    "affiliate-link", "affiliate-section", "ab-cta", "soft-recommend",
]

# 每篇软推荐最大插入数
SOFT_MAX = 3

# ------------------------------------------------------------
# hugo.toml 解析（[params.affiliate.<key>] -> url）
# ------------------------------------------------------------


def parse_affiliate_urls(hugo_toml: Path = HUGO_TOML) -> dict:
    """解析 hugo.toml [params.affiliate] 键值对。"""
    if not hugo_toml.exists():
        return {}
    text = hugo_toml.read_text(encoding="utf-8")
    urls = {}
    in_section = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("[params.affiliate]"):
            in_section = True
            continue
        if in_section:
            if line.startswith("[") and not line.startswith("[["):
                break
            if "=" in line:
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k and v and not v.startswith("#"):
                    urls[k] = v
    return urls


# ------------------------------------------------------------
# 主题检测
# ------------------------------------------------------------


def detect_themes(title: str, body: str, meta: str = "") -> list:
    """返回按关键词命中数排序的主题 key 列表。"""
    text = " ".join(filter(None, [title, body[:3000], meta])).lower()
    scored = []
    for key, cfg in THEME_CONFIG.items():
        hits = sum(1 for kw in cfg["keywords"] if kw in text)
        if hits > 0:
            scored.append((key, hits))
    scored.sort(key=lambda x: -x[1])
    return [k for k, _ in scored]


def products_for(article: dict, config: dict = THEME_CONFIG) -> list:
    """返回去重后的产品逻辑名列表（优先主题组合，兜底 fallback）。"""
    themes = detect_themes(article.get("title", ""),
                           article.get("body", ""),
                           article.get("description", ""))
    products = []
    for theme in themes:
        for p in config[theme]["products"]:
            if p not in products:
                products.append(p)
    if not products:
        products = list(FALLBACK_PRODUCTS)
    return products


def resolve_key(product: str) -> str:
    """产品逻辑名 -> hugo.toml 键名。"""
    return PRODUCT_KEY_MAP.get(product, product)


# ------------------------------------------------------------
# 软推荐文案（Editorial Voice）
# ------------------------------------------------------------


def _existing_partners(content: str) -> set:
    """从已存在的 shortcode 提取已覆盖的**产品逻辑名**集合。

    - `affiliate-tour` / `soft-recommend partner="klook"` -> 归一到产品逻辑名 tour
    - `affiliate-mid-cta partner="hotel"` -> hotel
    """
    products = set()
    # affiliate-<prod> shortcode（逻辑名）
    for m in re.finditer(r"affiliate-([a-z]+)", content):
        token = m.group(1)
        if token == "cta":
            continue
        products.add(token)
    # soft-recommend / affiliate-mid-cta / ab-cta partner 参数（可能是键名）
    for m in re.finditer(r'(?:soft-recommend|affiliate-mid-cta|ab-cta)[^>]*?partner="([a-z]+)"',
                         content):
        key = m.group(1)
        # 键名 -> 产品逻辑名
        logic = next((prod for prod, k in PRODUCT_KEY_MAP.items() if k == key), key)
        products.add(logic)
    return products


SOFT_COPY = {
    "flight": (
        "For international travelers comparing options, flight search platforms "
        "help you weigh routes and dates before you commit. It's a low-pressure "
        "way to see what's available.",
        "Compare flights to China",
    ),
    "insurance": (
        "Travel insurance is one of the practical pieces of preparation that "
        "gives peace of mind before a China trip — worth reviewing alongside "
        "your visa and itinerary.",
        "Review travel insurance options",
    ),
    "esim": (
        "Keeping your phone connected in China is easier with an eSIM, which "
        "avoids a physical SIM swap at the airport. Many travelers set it up "
        "before departure.",
        "See eSIM options",
    ),
    "hotel": (
        "Where you stay shapes a city trip. Comparing hotel options across "
        "platforms helps you find the location and budget that fit your route.",
        "Search accommodation",
    ),
    "tour": (
        "For first-time visitors, a structured day tour or skip-the-line ticket "
        "can simplify logistics at major attractions.",
        "Browse tours and tickets",
    ),
}


def soft_recommend_shortcode(partner: str, topic: str, placement: str,
                             context: str = "") -> str:
    """生成 soft-recommend shortcode。partner 为 hugo.toml 键名（如 klook/safetywing）。

    context 若为空则用模板默认文案（键名回退到产品逻辑名匹配文案）。
    """
    # 键名 -> 产品逻辑名
    logic = next((prod for prod, k in PRODUCT_KEY_MAP.items() if k == partner), partner)
    copy, cta = SOFT_COPY.get(logic, (
        "Practical travel products can simplify your China trip planning.",
        "See current options",
    ))
    inner = context or copy
    inner = inner.rstrip().rstrip(".")
    return (f'\n\n{{{{< soft-recommend partner="{partner}" topic="{topic}" '
            f'placement="{placement}" text="{cta}" >}}}}\n'
            f"{inner}.\n{{{{< /soft-recommend >}}}}")


# ------------------------------------------------------------
# 每篇处理
# ------------------------------------------------------------


def split_frontmatter(md_text: str):
    """识别 YAML(---) 或 TOML(+++) front matter。返回 (frontmatter_text, body, fm_delim)。

    兼容 BOM 前缀和 '---' / '+++' 分隔符。
    """
    text = md_text
    bom = ""
    if text.startswith("\ufeff"):
        bom = "\ufeff"
        text = text[1:]
    m = re.match(r"^(---|\+\+\+)\s*\n(.*?)\n\1\s*\n", text, re.DOTALL)
    if not m:
        return None, text, ""
    delim = m.group(1)
    return m.group(2), text[m.end():], delim


def parse_frontmatter_fields(fm_text: str, delim: str) -> dict:
    """解析 front matter 键值对（兼容 TOML 与 YAML 常见写法）。"""
    fm = {}
    for line in fm_text.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k and v:
                fm[k] = v
    return fm


def parse_article_text(md_text: str, default_slug: str = "") -> dict:
    """提取 title / description / slug / body / frontmatter。兼容 YAML 与 TOML。"""
    fm_text, body, delim = split_frontmatter(md_text)
    fm = parse_frontmatter_fields(fm_text or "", delim) if fm_text is not None else {}
    slug = fm.get("slug") or default_slug
    return {"title": fm.get("title", ""), "description": fm.get("description", ""),
            "slug": slug, "body": body or md_text, "frontmatter": fm_text or "",
            "fm_delim": delim}


def build_placements(article: dict, products: list,
                     existing: set, max_count: int = SOFT_MAX) -> list:
    """决定要插入的 (product_key, placement) 列表。

    - 跳过已覆盖产品（existing 为产品逻辑名集合）
    - 尽量在正文中分 2 处（中前部/中后部），余下补充
    """
    missing = [p for p in products if p not in existing]
    if not missing:
        return []
    placeholders = ["article_mid_1", "article_mid_2"]
    out = []
    for i, partner in enumerate(missing[:max_count]):
        if i < len(placeholders):
            placement = placeholders[i]
        else:
            placement = f"article_soft_{i + 1}"
        out.append((resolve_key(partner), placement))
    return out


def insert_soft_recommends(md_text: str, placements: list, topic: str) -> str:
    """在正文中均匀插入 soft-recommend shortcode。兼容 YAML/TOML front matter 与 BOM。"""
    if not placements:
        return md_text
    bom = ""
    text = md_text
    if text.startswith("\ufeff"):
        bom = "\ufeff"
        text = text[1:]

    # 定位 front matter 结束位置
    fm_m = re.match(r"^(---|\+\+\+)\s*\n(.*?)\n\1\s*\n", text, re.DOTALL)
    body_start = fm_m.end() if fm_m else 0
    body = text[body_start:]
    lines = body.split("\n")
    # 过滤 front matter 后的空行/短代码块，寻找正文 H2
    h2_idx = [i for i, ln in enumerate(lines) if re.match(r"^#{2,3}\s", ln)]
    anchors = []
    if h2_idx:
        mid = len(h2_idx) // 2
        anchors = [h2_idx[0], h2_idx[mid] if mid != 0 else h2_idx[0]]
    else:
        # 无 H2 时找一个非空内容行作为锚点
        content_idx = [i for i, ln in enumerate(lines) if ln.strip()]
        anchors = [content_idx[len(content_idx) // 2]] if content_idx else [len(lines) - 1]

    n = len(placements)
    if len(anchors) < n:
        while len(anchors) < n:
            anchors.append(len(lines) - 1)

    blocks = []
    for (partner, placement) in placements:
        blocks.append(soft_recommend_shortcode(partner, topic, placement))

    insert_at = sorted(set(anchors[:n]))
    while len(insert_at) < n:
        insert_at.append(len(lines) - 1)
    insert_at = sorted(insert_at)

    # 从后往前插入，避免索引错乱
    for idx, block in zip(reversed(insert_at[:n]), reversed(blocks)):
        lines.insert(idx + 1, block)

    return bom + md_text[:body_start] + "\n".join(lines)


# ------------------------------------------------------------
# 批处理
# ------------------------------------------------------------


class AffiliateLinkBuilder:
    def __init__(self):
        self.urls = parse_affiliate_urls()
        self.stats = {
            "total_files": 0,
            "modified_files": 0,
            "already_covered": 0,
            "error_files": [],
            "theme_stats": {},
            "product_stats": {},
        }

    def _bump(self, key, by=1):
        self.stats.setdefault(key, 0)
        self.stats[key] += by

    def process_file(self, md_path: Path, apply: bool = False) -> dict:
        try:
            text = md_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = md_path.read_text(encoding="latin-1")
        article = parse_article_text(text, default_slug=md_path.stem)

        # 主题与产品
        products = products_for(article)
        themes = detect_themes(article["title"], article["body"], article["description"])
        topic = themes[0] if themes else "general"
        for th in themes:
            self.stats["theme_stats"].setdefault(th, 0)
            self.stats["theme_stats"][th] += 1
        for p in products:
            self.stats["product_stats"].setdefault(p, 0)
            self.stats["product_stats"][p] += 1

        # 已覆盖
        existing = _existing_partners(text)
        placements = build_placements(article, products, existing)
        if not placements:
            self._bump("already_covered")
            return {"status": "covered", "slug": article["slug"],
                    "products": products, "placements": []}

        new_text = insert_soft_recommends(text, placements, topic)
        if apply and new_text != text:
            md_path.write_text(new_text, encoding="utf-8")
            self._bump("modified_files")
            return {"status": "updated", "slug": article["slug"],
                    "products": products, "placements": placements}
        if not apply:
            # dry-run 也计数为待更新
            self._bump("modified_files")
        return {"status": "would_update" if not apply else "no_change",
                "slug": article["slug"], "products": products,
                "placements": placements}

    def process_all(self, apply: bool = False) -> list:
        md_files = sorted(POSTS_DIR.glob("*.md"))
        self.stats["total_files"] = len(md_files)
        results = []
        for md_file in md_files:
            try:
                results.append(self.process_file(md_file, apply=apply))
            except Exception as e:
                self._bump("error_files", 1)
                results.append({"status": "error", "slug": md_file.stem, "error": str(e)})
        return results

    def coverage(self) -> dict:
        total = self.stats["total_files"]
        if total == 0:
            return {"coverage_rate": 0.0}
        covered = self.stats["modified_files"] + self.stats["already_covered"]
        return {"coverage_rate": round(covered / total * 100, 1),
                "covered_files": covered, "total_files": total}

    def report(self) -> dict:
        return {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "stats": self.stats,
            "coverage": self.coverage(),
            "affiliate_urls": self.urls,
            "themes": {k: v["label"] for k, v in THEME_CONFIG.items()},
        }


def save_report(data: dict, name: str = "affiliate_coverage_report.json") -> Path:
    out = REPORTS_DIR / name
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def _print_report(report: dict, results: list = None):
    s = report["stats"]
    cov = report["coverage"]
    print("\n" + "=" * 66)
    print("  联盟链接精细化布局统计")
    print("=" * 66)
    print(f"  总文章数: {s['total_files']}")
    print(f"  新增/待更新软推荐: {s['modified_files']}")
    print(f"  已覆盖: {s['already_covered']}")
    print(f"  覆盖率: {cov['coverage_rate']}%")
    print("\n  主题分布:")
    for k, n in sorted(s["theme_stats"].items(), key=lambda x: -x[1]):
        print(f"    - {k} ({THEME_CONFIG[k]['label']}): {n}")
    print("\n  产品组合分布:")
    for k, n in sorted(s["product_stats"].items(), key=lambda x: -x[1]):
        print(f"    - {k}: {n}")
    if s["error_files"]:
        print(f"\n  处理失败: {s['error_files']} 个")
    if results:
        pending = [r for r in results if r.get("placements")]
        print(f"\n  待插入软推荐的文章（{len(pending)} 篇）:")
        for r in pending[:20]:
            pl = ", ".join(f"{p}@{pl}" for p, pl in r["placements"])
            print(f"    - {r['slug'][:50]} -> {pl}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="全站联盟链接精细化布局")
    ap.add_argument("--apply", action="store_true", help="实际写文件（默认 dry-run）")
    ap.add_argument("--coverage", action="store_true", help="输出覆盖率/分产品统计")
    args = ap.parse_args(argv)

    builder = AffiliateLinkBuilder()
    results = builder.process_all(apply=args.apply)
    report = builder.report()
    save_report(report)
    _print_report(report, results)

    # 分产品转化统计（基于资产库 metrics，若存在）
    if args.coverage:
        from social_content_agent import load_inventory  # 可选依赖
        inv = load_inventory()
        _print_product_conversion(inv)
    return 0


def _print_product_conversion(inventory):
    """分产品转化数据：基于 content/social/inventory.json 的 metrics。
    无真实点击数据时给出基于 CTA 存在的"曝光面"统计。"""
    if not inventory.get("items"):
        print("\n  分产品转化: 资产库为空，跳过")
        return
    by_product = {}
    for it in inventory["items"]:
        p = it.get("platform", "?")
        by_product.setdefault(p, {"items": 0, "impressions": 0, "clicks": 0})
        by_product[p]["items"] += 1
        m = it.get("metrics", {})
        by_product[p]["impressions"] += m.get("impressions", 0)
        by_product[p]["clicks"] += m.get("clicks", 0)
    print("\n  分产品转化统计（来自社媒资产库 metrics）:")
    for p, d in sorted(by_product.items(), key=lambda x: -x[1]["clicks"]):
        ctr = (d["clicks"] / d["impressions"] * 100) if d["impressions"] else 0
        print(f"    - {p}: {d['items']}条, 曝光{d['impressions']}, 点击{d['clicks']}, CTR {ctr:.2f}%")


if __name__ == "__main__":
    sys.exit(main())
