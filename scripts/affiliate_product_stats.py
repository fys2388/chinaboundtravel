#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
affiliate_product_stats.py - 分产品联盟转化统计
================================================

统计全站各联盟产品（flight/insurance/esim/hotel/tour）的 CTA 曝光面与
（如有）点击/转化数据，供周报对比各品类点击率。

数据来源：
  1. 站点 CTA 分布：扫描所有文章，统计每篇文章出现的 affiliate shortcode /
     soft-recommend 次数（按产品逻辑名分组）。
  2. 转化数据：读取 reports/ 下的 GA4 affiliate_click 缓存（若存在）。当前
     没有真实点击数据时，点击/转化/CTR 保持 0 并明确标注未接入，绝不编造。

输出：
  reports/revenue/AFFILIATE_PRODUCT_STATS.json
  reports/revenue/AFFILIATE_PRODUCT_STATS.csv

提供周报可调用的汇总函数 product_summary()。

用法：
  python scripts/affiliate_product_stats.py [--apply]   # apply 才会读真实转化缓存
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

SCRIPT_DIR = Path(__file__).resolve().parent
BLOG_ROOT = SCRIPT_DIR.parent
POSTS_DIR = BLOG_ROOT / "content" / "posts"
REPORTS_REVENUE = BLOG_ROOT / "reports" / "revenue"
REPORTS_REVENUE.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(SCRIPT_DIR))

from affiliate_link_builder import PRODUCT_KEY_MAP, parse_affiliate_urls  # noqa: E402

PRODUCTS = ["flight", "insurance", "esim", "hotel", "tour"]

# 识别文章中的联盟引用（按产品逻辑名）
# 形如: {{< affiliate-hotel >}} {{< soft-recommend partner="klook" ...>}} etc.
SHORTCODE_PATTERNS = {
    "flight": r"affiliate-flight",
    "insurance": r"affiliate-insurance|soft-recommend partner=\"safetywing\"",
    "esim": r"affiliate-esim|soft-recommend partner=\"esim\"",
    "hotel": r"affiliate-hotel|soft-recommend partner=\"hotel\"",
    "tour": r"affiliate-tour|soft-recommend partner=\"klook\"",
}


def scan_article_ctas(text: str) -> dict:
    """统计一篇文章中各产品的 CTA 出现次数。"""
    counts = {p: 0 for p in PRODUCTS}
    for prod in PRODUCTS:
        pat = re.compile(SHORTCODE_PATTERNS[prod], re.IGNORECASE)
        counts[prod] = len(pat.findall(text))
    return counts


def product_distribution() -> dict:
    """返回 {product: {"posts": n, "cta_count": m}}。"""
    dist = {p: {"posts": 0, "cta_count": 0} for p in PRODUCTS}
    for post in POSTS_DIR.glob("*.md"):
        try:
            text = post.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        counts = scan_article_ctas(text)
        for prod, n in counts.items():
            if n > 0:
                dist[prod]["posts"] += 1
            dist[prod]["cta_count"] += n
    return dist


def load_conversion_cache() -> dict:
    """读取 GA4 affiliate_click 缓存（若存在）。返回空 dict 表示未接入。"""
    for pat in ("*affiliate*click*.json", "*affiliate*conversion*.json", "*GA4*affiliate*.json"):
        for f in sorted((BLOG_ROOT / "reports").glob(pat)):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                return {"source_file": str(f), "data": data}
            except Exception:
                continue
    return {}


def build_report(include_conversion: bool = False) -> dict:
    dist = product_distribution()
    conversion = load_conversion_cache() if include_conversion else {}
    urls = parse_affiliate_urls()
    rows = []
    for prod in PRODUCTS:
        rows.append({
            "product": prod,
            "posts": dist[prod]["posts"],
            "cta_count": dist[prod]["cta_count"],
            "clicks": 0,
            "conversions": 0,
            "ctr_pct": 0.0,
            "conversion_cache": bool(conversion),
            "url": urls.get(PRODUCT_KEY_MAP[prod], ""),
        })
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "include_conversion": include_conversion,
        "conversion_source": conversion.get("source_file", "") if conversion else "",
        "products": rows,
    }


def product_summary() -> list:
    """供周报调用的汇总（product, posts, cta_count, ctr_pct）。"""
    return build_report(include_conversion=False)["products"]


def _write_csv(report: dict, path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["product", "posts", "cta_count",
                                           "clicks", "conversions", "ctr_pct",
                                           "conversion_cache", "url"])
        w.writeheader()
        for row in report["products"]:
            w.writerow(row)


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="分产品联盟转化统计")
    ap.add_argument("--apply", action="store_true",
                    help="读取真实转化缓存（默认仅统计 CTA 曝光面）")
    args = ap.parse_args(argv)

    report = build_report(include_conversion=args.apply)
    json_path = REPORTS_REVENUE / "AFFILIATE_PRODUCT_STATS.json"
    csv_path = REPORTS_REVENUE / "AFFILIATE_PRODUCT_STATS.csv"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_csv(report, csv_path)

    print(f"分产品联盟统计已写入:\n  {json_path}\n  {csv_path}")
    print(f"{'product':<10}{'posts':>6}{'cta':>6}{'clicks':>8}{'ctr%':>8}")
    for r in report["products"]:
        print(f"{r['product']:<10}{r['posts']:>6}{r['cta_count']:>6}"
              f"{r['clicks']:>8}{r['ctr_pct']:>8.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
