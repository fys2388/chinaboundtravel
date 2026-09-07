#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Content Coverage Audit - 内容覆盖率检查
=========================================

P1/P2-FIX (2026-09-07): 新增内容字段覆盖率检查。

检查项：
  1. last_updated 覆盖率（阈值 90%）
  2. description 覆盖率（阈值 95%）
  3. 图片 WebP 转化率（阈值 80%）
  4. canonicalURL 覆盖率（阈值 100%）
  5. content_id 覆盖率（阈值 100%）

退出码：
  0 = 全部达标
  1 = 存在不达标项（CI阻断）

用法：
  python scripts/content_coverage_audit.py
  python scripts/content_coverage_audit.py --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = PROJECT_ROOT / "content" / "posts"
IMG_DIR = PROJECT_ROOT / "static" / "img"
REPORTS_DIR = PROJECT_ROOT / "reports" / "content_coverage"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# 阈值配置
THRESHOLDS = {
    "last_updated": 90.0,
    "description": 95.0,
    "webp_conversion": 80.0,
    "canonical_url": 100.0,
    "content_id": 100.0,
}


def read_frontmatter(path: Path) -> Dict[str, str]:
    """读取文章 front matter，返回字段字典"""
    try:
        raw = path.read_bytes()
        text = raw.decode("utf-8", errors="replace")
    except Exception:
        return {}

    # 提取 front matter
    fm = {}
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.DOTALL)
    if not match:
        return fm

    fm_text = match.group(1)
    for line in fm_text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # 简单 key: value 解析
        m = re.match(r'^(\w+)\s*[:=]\s*(.+)$', line)
        if m:
            key = m.group(1).lower()
            value = m.group(2).strip().strip('"').strip("'")
            fm[key] = value
    return fm


def audit_post_fields() -> Dict:
    """审计文章字段覆盖率"""
    posts = sorted(POSTS_DIR.glob("*.md"))
    total = len(posts)

    fields = ["last_updated", "description", "canonicalurl", "content_id"]
    counts = {f: 0 for f in fields}
    missing = {f: [] for f in fields}

    for post in posts:
        fm = read_frontmatter(post)
        for field in fields:
            if field in fm and fm[field]:
                counts[field] += 1
            else:
                missing[field].append(post.name)

    result = {
        "total_posts": total,
        "last_updated": {
            "count": counts["last_updated"],
            "coverage": round(counts["last_updated"] / total * 100, 1) if total else 0,
            "threshold": THRESHOLDS["last_updated"],
            "missing": missing["last_updated"][:20],
            "passed": counts["last_updated"] / total * 100 >= THRESHOLDS["last_updated"] if total else False,
        },
        "description": {
            "count": counts["description"],
            "coverage": round(counts["description"] / total * 100, 1) if total else 0,
            "threshold": THRESHOLDS["description"],
            "missing": missing["description"],
            "passed": counts["description"] / total * 100 >= THRESHOLDS["description"] if total else False,
        },
        "canonical_url": {
            "count": counts["canonicalurl"],
            "coverage": round(counts["canonicalurl"] / total * 100, 1) if total else 0,
            "threshold": THRESHOLDS["canonical_url"],
            "missing": missing["canonicalurl"],
            "passed": counts["canonicalurl"] / total * 100 >= THRESHOLDS["canonical_url"] if total else False,
        },
        "content_id": {
            "count": counts["content_id"],
            "coverage": round(counts["content_id"] / total * 100, 1) if total else 0,
            "threshold": THRESHOLDS["content_id"],
            "missing": missing["content_id"],
            "passed": counts["content_id"] / total * 100 >= THRESHOLDS["content_id"] if total else False,
        },
    }
    return result


def audit_image_formats() -> Dict:
    """审计图片格式覆盖率"""
    if not IMG_DIR.exists():
        return {"total": 0, "webp": 0, "jpg": 0, "png": 0, "webp_rate": 0, "passed": False, "threshold": THRESHOLDS["webp_conversion"]}

    webp = list(IMG_DIR.rglob("*.webp"))
    jpg = list(IMG_DIR.rglob("*.jpg")) + list(IMG_DIR.rglob("*.jpeg"))
    png = list(IMG_DIR.rglob("*.png"))
    total = len(webp) + len(jpg) + len(png)
    webp_rate = round(len(webp) / total * 100, 1) if total else 0

    # 列出最大的 JPG 文件（优化候选）
    jpg_with_size = [(f.name, f.stat().st_size) for f in jpg]
    jpg_with_size.sort(key=lambda x: x[1], reverse=True)

    return {
        "total": total,
        "webp": len(webp),
        "jpg": len(jpg),
        "png": len(png),
        "webp_rate": webp_rate,
        "threshold": THRESHOLDS["webp_conversion"],
        "passed": webp_rate >= THRESHOLDS["webp_conversion"],
        "top_jpg_candidates": [{"name": n, "size_kb": round(s / 1024, 1)} for n, s in jpg_with_size[:10]],
    }


def run_audit() -> Dict:
    """运行全部覆盖率审计"""
    print(f"\n{'='*60}")
    print(f"  Content Coverage Audit")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    post_audit = audit_post_fields()
    image_audit = audit_image_formats()

    # 打印结果
    print(f"  📝 文章字段覆盖率 (共 {post_audit['total_posts']} 篇):")
    for field in ["last_updated", "description", "canonical_url", "content_id"]:
        data = post_audit[field]
        status = "✅" if data["passed"] else "❌"
        print(f"    {status} {field:20s}: {data['coverage']:5.1f}% ({data['count']}/{post_audit['total_posts']}) threshold={data['threshold']}%")
        if not data["passed"] and data["missing"]:
            print(f"         缺失示例: {data['missing'][:3]}")

    print(f"\n  🖼️  图片格式覆盖率 (共 {image_audit['total']} 张):")
    status = "✅" if image_audit["passed"] else "❌"
    print(f"    {status} WebP 转化率: {image_audit['webp_rate']:5.1f}% (WebP:{image_audit['webp']} JPG:{image_audit['jpg']} PNG:{image_audit['png']}) threshold={image_audit['threshold']}%")
    if not image_audit["passed"] and image_audit["top_jpg_candidates"]:
        print(f"         Top JPG 优化候选:")
        for c in image_audit["top_jpg_candidates"][:5]:
            print(f"           - {c['name']}: {c['size_kb']} KB")

    # 汇总
    all_checks = [
        post_audit["last_updated"]["passed"],
        post_audit["description"]["passed"],
        post_audit["canonical_url"]["passed"],
        post_audit["content_id"]["passed"],
        image_audit["passed"],
    ]
    all_passed = all(all_checks)

    print(f"\n{'='*60}")
    print(f"  Overall: {'✅ ALL PASSED' if all_passed else '❌ SOME FAILED'} ({sum(all_checks)}/{len(all_checks)} checks passed)")
    print(f"{'='*60}\n")

    report = {
        "audit_version": "1.0",
        "audit_time": datetime.now().isoformat(),
        "post_fields": post_audit,
        "image_formats": image_audit,
        "summary": {
            "all_passed": all_passed,
            "checks_passed": sum(all_checks),
            "checks_total": len(all_checks),
        },
    }

    # 保存报告
    report_path = REPORTS_DIR / f"coverage_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"  Report saved: {report_path}")

    return report


def main():
    parser = argparse.ArgumentParser(description="Content Coverage Audit")
    parser.add_argument("--json", action="store_true", help="JSON output only")
    args = parser.parse_args()

    report = run_audit()

    if args.json:
        print(json.dumps(report["summary"], ensure_ascii=False, indent=2))

    return 0 if report["summary"]["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
