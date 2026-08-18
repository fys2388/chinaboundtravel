#!/usr/bin/env python3
"""P1-BRAND-02: ChinaBound Travel brand identity audit.

Checks the 5 brand-layer surfaces:
  1. Homepage        (layouts/index.html, layouts/partials/home-banner.html, hugo.toml profileMode)
  2. Resources page  (content/resources/_index.md)
  3. Author blocks   (sidebar-author.html, affiliate-intro in single/cities, affiliate-disclosure, travel-promo)
  4. About page      (content/about/_index.md)
  5. Schema author   (layouts/partials/templates/schema_json.html, hugo.toml author)

Detects:
  - forbidden_persona_phrases  (from config/content_governance.json)
  - fictional_experience_claims (rule-based persona patterns)
  - editorial_positioning       (presence of editorial/research language)

Output: reports/P1_BRAND_02_BRAND_IDENTITY_AUDIT.md
Legacy mode (--legacy): stats over content/posts -> reports/P1_BRAND_02_LEGACY_PERSONA_REVIEW.md
Pure, deterministic, no network, no LLM.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

BLOG_ROOT = Path(__file__).resolve().parent.parent
GOVERNANCE = BLOG_ROOT / "config" / "content_governance.json"
REPORTS = BLOG_ROOT / "reports"

BRAND_FILES = [
    # (path, layer, kind)
    ("layouts/index.html", "homepage", "template"),
    ("layouts/partials/home-banner.html", "homepage", "template"),
    ("hugo.toml", "homepage", "config"),
    ("content/resources/_index.md", "resources", "content"),
    ("layouts/partials/sidebar-author.html", "author_block", "template"),
    ("layouts/partials/author.html", "author_block", "template"),
    ("layouts/_default/single.html", "author_block", "template"),
    ("layouts/cities/single.html", "author_block", "template"),
    ("layouts/partials/affiliate-disclosure.html", "author_block", "template"),
    ("layouts/shortcodes/affiliate-disclosure.html", "author_block", "template"),
    ("layouts/partials/travel-promo.html", "author_block", "template"),
    ("content/about/_index.md", "about", "content"),
    ("layouts/partials/templates/schema_json.html", "schema", "template"),
    ("content/pricing.md", "pricing", "content"),
    ("layouts/partials/pricing-table.html", "pricing", "template"),
]

# Rule-based fictional-experience claim patterns (brand layer, not full content governance)
FICTIONAL_PATTERNS = [
    r"personally (tested|used|use|recommend)",
    r"American expat",
    r"American (living in|in) Chengdu",
    r"Chengdu (husband|wife)",
    r"my wife",
    r"years? (of )?living in (China|Chengdu)",
    r"years? of China travel experience",
    r"\d+[- ]year expat",
    r"(first trip|my first trip)",
    r"I (lived|moved) (in|to)",
    r"I remember my",
    r"tested daily",
]

EDITORIAL_PATTERNS = [
    r"editorial",
    r"research-based",
    r"editorial team",
    r"editorial voice",
    r"reviewed",
    r"international travelers?",
]


def load_forbidden() -> list[str]:
    if not GOVERNANCE.exists():
        return []
    data = json.loads(GOVERNANCE.read_text(encoding="utf-8-sig"))
    return data.get("persona", {}).get("forbidden_phrases", [])


def scan_text(text: str) -> dict:
    forbidden = load_forbidden()
    fpat = re.compile("|".join(re.escape(p) for p in forbidden), re.IGNORECASE)
    fiction = re.compile("|".join(FICTIONAL_PATTERNS), re.IGNORECASE)
    edit = re.compile("|".join(EDITORIAL_PATTERNS), re.IGNORECASE)
    return {
        "forbidden": sorted(set(fpat.findall(text))),
        "fictional": sorted({m.group(0) for m in fiction.finditer(text)}),
        "editorial": bool(edit.search(text)),
    }


def scan_brand() -> list[dict]:
    rows = []
    for rel, layer, kind in BRAND_FILES:
        p = BLOG_ROOT / rel
        if not p.exists():
            rows.append({"path": rel, "layer": layer, "status": "MISSING",
                         "forbidden": [], "fictional": [], "editorial": False})
            continue
        enc = "gbk" if rel == "layouts/_default/single.html" else "utf-8"
        try:
            text = p.read_text(encoding=enc, errors="replace")
        except Exception:
            text = p.read_text(encoding="utf-8", errors="replace")
        res = scan_text(text)
        if res["forbidden"] or res["fictional"]:
            status = "FAIL"
        elif res["editorial"]:
            status = "PASS"
        else:
            status = "WARN"
        rows.append({"path": rel, "layer": layer, "status": status,
                     "forbidden": res["forbidden"], "fictional": res["fictional"],
                     "editorial": res["editorial"]})
    return rows


def write_brand_report(rows: list[dict], generated: str) -> Path:
    out = REPORTS / "P1_BRAND_02_BRAND_IDENTITY_AUDIT.md"
    lines = ["# P1-BRAND-02 — Brand Identity Audit", "",
             f"- Generated: {generated}", "",
             "品牌层检查：Homepage / Resources / Author Block / About / Schema。", "",
             "| layer | file | status | forbidden | fictional | editorial |",
             "|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['layer']} | {r['path']} | {r['status']} | "
                     f"{'; '.join(r['forbidden']) or '-'} | {'; '.join(r['fictional']) or '-'} | {r['editorial']} |")
    n_pass = sum(1 for r in rows if r["status"] == "PASS")
    lines += ["", f"Summary: {n_pass}/{len(rows)} PASS (WARN = editorial language not yet present, no violations).",
              "", "LOW_DATA_WARNING: brand audit is rule-based; manual copy review recommended before publishing changes."]
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def scan_legacy() -> list[dict]:
    forbidden = load_forbidden()
    fpat = re.compile("|".join(re.escape(p) for p in forbidden), re.IGNORECASE)
    rows = []
    for f in sorted((BLOG_ROOT / "content" / "posts").glob("*.md")):
        text = f.read_text(encoding="utf-8", errors="replace")
        hits = sorted(set(fpat.findall(text)))
        rows.append({"file": f.name, "hits": hits, "count": len(hits)})
    return rows


def write_legacy_report(rows: list[dict], generated: str) -> Path:
    out = REPORTS / "P1_BRAND_02_LEGACY_PERSONA_REVIEW.md"
    total = len(rows)
    hit = [r for r in rows if r["count"] > 0]
    lines = ["# P1-BRAND-02 — Legacy Persona Content Review", "",
             f"- Generated: {generated}", "",
             f"统计：content/posts 共 {total} 篇，命中 legacy persona 短语 {len(hit)} 篇。", "",
             "本轮**不修改** legacy 文章；统一标记 LEGACY_PERSONA_CONTENT，后续单独处理。", "",
             "| file | hits | matched phrases |",
             "|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['file']} | {r['count']} | {'; '.join(r['hits']) or '-'} |")
    lines += ["", "## 后续建议", "",
              "1. 不批量改写 legacy 正文（避免排名/流量波动）。",
              "2. 优先修订有自然搜索流量的 legacy 页（按 opportunity engine 排序）。",
              "3. 修订时保留 URL / canonical / content_id / affiliate / UTM。",
              "4. 每批最多 2-3 篇，改后 28 天观察。"]
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--legacy", action="store_true", help="scan content/posts for legacy persona phrases")
    args = ap.parse_args()
    generated = date.today().isoformat()
    if args.legacy:
        rows = scan_legacy()
        out = write_legacy_report(rows, generated)
        print(f"legacy scanned={len(rows)} hits={sum(1 for r in rows if r['count'] > 0)} -> {out}")
        return 0
    rows = scan_brand()
    out = write_brand_report(rows, generated)
    for r in rows:
        flag = r["status"]
        print(f"  [{flag:6s}] {r['path']}")
    print(f"brand audit -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
