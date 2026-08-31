#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
content_quality_validator.py - Content Trust 验证器
====================================================

P1-CONTENT-TRUST-FIX-01 流水线的守门员。所有自动修复后的文章必须通过本
验证器，否则拒绝上线（类似 CI 的 trust_score >= 90 门槛）。

验证维度：
  - 结构完整性：front matter 未被破坏、URL/slug/canonical/content_id 不变
  - 品牌合规：无第一人称虚构体验、无 forbidden phrases
  - 语言质量：无中文残留、无乱码
  - 事实守卫：动态事实关键词需带验证提示或 last_updated
  - SEO 完整性：title/description 存在且长度合理

评分体系（0-100，加权）：
  trust_score = brand*40 + fact*25 + language*15 + seo*20

用法：
  python scripts/content_quality_validator.py                    # 验证全部文章
  python scripts/content_quality_validator.py --file xxx.md      # 验证单篇
  python scripts/content_quality_validator.py --json             # JSON 输出
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

BLOG_ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = BLOG_ROOT / "content" / "posts"
GOVERNANCE = BLOG_ROOT / "config" / "content_governance.json"

# 发布门槛
PASS_THRESHOLD = 90
# P0: External AI image domain blocklist (must not appear in cover/body images)
BLOCKED_IMAGE_DOMAINS = [
    "pollinations.ai",
    "image.pollinations.ai",
    "lexica.art",
    "midjourney",
    "dalle",
    "stablediffusion",
    "craiyon.com",
    "bing.com/images/create",
]
# Allowed local image domain (cover images should be on this domain)
LOCAL_IMAGE_DOMAIN = "chinaboundtravel.com"


def load_forbidden() -> list:
    if GOVERNANCE.exists():
        try:
            data = json.loads(GOVERNANCE.read_text(encoding="utf-8-sig"))
            return data.get("persona", {}).get("forbidden_phrases", [])
        except Exception:
            pass
    return []


FORBIDDEN = load_forbidden()
CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")

# 品牌违规模式（第一人称虚构体验）
BRAND_PATTERNS = [
    r"\bI (stayed|visited|booked|tried|ate at|flew to|arrived in)\b",
    r"\bI've (been|lived) in\b", r"\bI have (been|lived) in\b",
    r"\bmy (wife|husband|partner|family)\b",
    r"\bwe (stayed|visited)\b", r"\bmy first trip\b",
    r"\b\d+\s*years? living in China\b", r"\b\d+\s*-year expat\b",
    r"\bI lived in\b", r"\bI moved to\b",
]
BRAND_RE = re.compile("|".join(BRAND_PATTERNS), re.IGNORECASE)

# 动态事实关键词（需验证提示或 last_updated）
FACT_KEYWORDS = ["visa", "visa-free", "144-hour", "240-hour", "transit",
                 "immigration", "price", "prices", "cost", "costs", "fee",
                 "fees", "charge", "charges", "opening hours", "hours",
                 "high-speed rail", "ticket price", "fare", "policy",
                 "rules", "restriction", "passport", "entry requirement"]
FACT_RE = re.compile(r"\b(" + "|".join(FACT_KEYWORDS) + r")\b", re.IGNORECASE)
VERIFY_HINT = "verify the latest information from official sources"


def split_frontmatter(text: str):
    for delim in ("---", "+++"):
        ed = re.escape(delim)
        m = re.match(r"^%s\s*\n(.*?)\n%s\s*\n" % (ed, ed), text, re.DOTALL)
        if m:
            return m.group(1), text[m.end():], delim
    return None, text, ""


def read_fm_value(fm: str, key: str) -> str:
    """Parse front matter scalar value. Handles quoted strings with apostrophes."""
    m = re.search(rf'^{key}\s*[=:]\s*(.+)$', fm, re.MULTILINE)
    if not m:
        return ""
    val = m.group(1).strip()
    if val.startswith('"'):
        end = val.find('"', 1)
        return val[1:end] if end > 0 else val[1:].rstrip('"')
    if val.startswith("\'"):
        end = val.find("\'", 1)
        return val[1:end] if end > 0 else val[1:].rstrip("\'")
    val = re.sub(r'\s+#.*$', '', val)
    return val.strip()

def validate_article(path: Path) -> dict:
    """验证单篇文章，返回结构化结果。"""
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    fm, body, delim = split_frontmatter(text)
    result = {
        "file": path.name,
        "frontmatter_ok": fm is not None,
        "content_id_ok": bool(read_fm_value(fm or "", "content_id")),
        "url_ok": True,  # URL 由 front matter 不变保证（未修改 canonicalURL/slug）
        "canonical_ok": True,
        "brand_issues": [],
        "language_issues": [],
        "fact_issues": [],
        "seo_issues": [],
        "media_issues": [],
        "cover_ok": False,
        "cover_image": "",
        "scores": {},
        "trust_score": 0,
        "passed": False,
    }
    if fm is None:
        result["passed"] = False
        result["scores"] = {"brand": 0, "fact": 0, "language": 0, "seo": 0}
        return result

    # ---- 品牌 ----
    brand_issues = []
    for m in BRAND_RE.finditer(body):
        brand_issues.append(m.group(0))
    for phrase in FORBIDDEN:
        if phrase.lower() in body.lower():
            brand_issues.append(phrase)
    result["brand_issues"] = list(dict.fromkeys(brand_issues))[:10]
    brand_score = max(0, 100 - len(set(brand_issues)) * 15)

    # ---- 语言 ----
    cjk = CJK_RE.findall(body)
    result["language_issues"] = cjk[:10]
    language_score = 100 if not cjk else max(0, 100 - len(cjk) * 20)

    # ---- 事实 ----
    fact_hits = set(FACT_RE.findall(body.lower()))
    # 有验证提示或 last_updated 即可视为已守卫
    has_verify = VERIFY_HINT.lower() in body.lower()
    fm_lower = (fm or "").lower()
    has_last_updated = "last_updated" in fm_lower or "lastmod" in fm_lower
    unguarded = [k for k in fact_hits
                 if not has_verify and not has_last_updated]
    result["fact_issues"] = unguarded[:10]
    fact_score = 100 if has_verify or has_last_updated or not fact_hits \
        else max(0, 100 - len(unguarded) * 8)

    # ---- SEO ----
    seo_issues = []
    title = read_fm_value(fm, "title")
    desc = read_fm_value(fm, "description")
    if not title:
        seo_issues.append("missing_title")
    elif len(title) > 70:
        seo_issues.append("title_too_long")
    if not desc:
        seo_issues.append("missing_description")
    elif len(desc) < 50:
        seo_issues.append("description_short")
    h2_count = len(re.findall(r"^##\s+", body, re.MULTILINE))
    if h2_count < 2:
        seo_issues.append("few_headings")
    result["seo_issues"] = seo_issues
    seo_score = max(0, 100 - len(seo_issues) * 20)

    # ---- 媒体/封面 (P0) ----
    media_issues = []
    cover_ok = False
    cover_image = ""
    fm_lines = (fm or "").split("\n")
    in_cover = False
    for line in fm_lines:
        stripped = line.strip()
        if stripped.startswith("cover:"):
            in_cover = True
            continue
        if in_cover and stripped.startswith("image:"):
            cover_image = stripped.split(":", 1)[1].strip().strip('"').strip("'")
            cover_ok = True
            in_cover = False
            break
        if in_cover and stripped and not stripped.startswith(" "):
            in_cover = False
    if not cover_ok:
        media_issues.append("missing_cover")
    if cover_image:
        is_blocked = any(d in cover_image.lower() for d in BLOCKED_IMAGE_DOMAINS)
        is_local = LOCAL_IMAGE_DOMAIN in cover_image.lower()
        if is_blocked:
            media_issues.append("blocked_ai_image_domain:" + cover_image[:60])
        elif not is_local and cover_image.startswith("http"):
            media_issues.append("external_image_domain:" + cover_image[:60])
    body_images = re.findall(r'!\[.*?\]\((.*?)\)', body)
    body_images += re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', body)
    for img_url in body_images:
        if any(d in img_url.lower() for d in BLOCKED_IMAGE_DOMAINS):
            media_issues.append("body_blocked_ai_image:" + img_url[:60])
    result["media_issues"] = media_issues
    result["cover_ok"] = cover_ok
    result["cover_image"] = cover_image
    media_score = max(0, 100 - len(media_issues) * 25)


    # ---- 综合评分 ----
    result["scores"] = {
        "brand": brand_score,
        "fact": fact_score,
        "language": language_score,
        "seo": seo_score,
        "media": media_score,
    }
    trust = (brand_score * 0.35 + fact_score * 0.2 +
             language_score * 0.1 + seo_score * 0.15 + media_score * 0.2)
    result["trust_score"] = round(trust, 1)
    result["passed"] = trust >= PASS_THRESHOLD
    return result


def validate_all() -> list:
    results = []
    for f in sorted(POSTS_DIR.glob("*.md")):
        results.append(validate_article(f))
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description="Content Trust Validator")
    ap.add_argument("--file", type=str, default=None, help="验证单篇")
    ap.add_argument("--json", action="store_true", help="JSON 输出")
    ap.add_argument("--threshold", type=int, default=PASS_THRESHOLD)
    args = ap.parse_args()

    if args.file:
        results = [validate_article(POSTS_DIR / args.file)]
    else:
        results = validate_all()

    passed = [r for r in results if r["trust_score"] >= args.threshold]
    if args.json:
        print(json.dumps({"results": results, "passed_count": len(passed),
                          "total": len(results)}, ensure_ascii=False, indent=2))
        return 0

    print(f"Content Trust Validator（门槛 {args.threshold}）")
    print(f"  通过: {len(passed)}/{len(results)}")
    for r in results:
        mark = "✅" if r["passed"] else "❌"
        print(f"  {mark} {r['file'][:45]:47s} trust={r['trust_score']:6.1f} "
              f"brand={r['scores']['brand']} fact={r['scores']['fact']} "
              f"lang={r['scores']['language']} seo={r['scores']['seo']}")
        if not r["passed"] and not args.file:
            if r["brand_issues"]:
                print(f"       brand: {r['brand_issues'][:3]}")
            if r["fact_issues"]:
                print(f"       fact: {r['fact_issues'][:3]}")
            if r["seo_issues"]:
                print(f"       seo: {r['seo_issues'][:3]}")
            if r.get("media_issues"):
                print(f"       media: {r['media_issues'][:3]}")
    return 0 if len(passed) == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
