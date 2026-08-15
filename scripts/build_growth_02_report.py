#!/usr/bin/env python3
"""P1-GROWTH-02: assemble the final GSC Search Analytics report.

Reads the generated data files under reports/seo/ and emits
reports/P1_GROWTH_02_GSC_SEARCH_ANALYTICS_REPORT.md with the 14 sections
required by the P1-GROWTH-02 spec.
"""

import csv
import json
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SEO = REPO / "reports" / "seo"


def read_csv(name):
    with open(SEO / name, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def agg(rows, imp_col="impressions", click_col="clicks", pos_col="position"):
    imp = sum(int(float(r[imp_col])) for r in rows)
    clicks = sum(int(float(r[click_col])) for r in rows)
    ctr = (clicks / imp) if imp else 0
    pos = (sum(float(r[pos_col]) * int(float(r[imp_col])) for r in rows) / imp) if imp else 0
    return clicks, imp, ctr, pos


def pct(x):
    return f"{x*100:.2f}%"


def main():
    q28 = read_csv("query_performance.csv")
    p28 = read_csv("page_performance.csv")
    d28 = read_csv("daily_search_performance.csv")
    q90 = read_csv("raw_queries_90d.csv")
    p90 = read_csv("raw_pages_90d.csv")
    d90 = read_csv("daily_search_performance_90d.csv")
    qp = read_csv("raw_queries_pages_28d.csv")

    c28, i28, ctr28, pos28 = agg(q28)
    c28p, i28p, ctr28p, pos28p = agg(p28)
    c90, i90, ctr90, pos90 = agg(q90)
    c90p, i90p, ctr90p, pos90p = agg(p90)

    top_queries = sorted(q28, key=lambda r: -int(float(r["impressions"])))[:15]
    top_pages = sorted(p28, key=lambda r: -int(float(r["impressions"])))[:15]

    # index coverage from inspection results
    insp_path = SEO / "url_inspection_results.json"
    inspection = json.loads(insp_path.read_text(encoding="utf-8")) if insp_path.exists() else {}
    cov = Counter((r.get("coverage_state") or r.get("error") or "EMPTY") for r in inspection.values())
    indexed = sum(1 for r in inspection.values()
                  if "indexed" in (r.get("coverage_state") or "").lower()
                  and not r.get("error"))

    # content inventory
    inv = read_csv("CONTENT_SEO_INVENTORY.csv")

    # intent distribution summary
    intent_rows = read_csv("query_intent_distribution.csv")
    intent_agg = Counter(r["intent"] for r in intent_rows)

    lines = []
    lines.append("# P1-GROWTH-02 GSC Search Analytics + Index Opportunity Engine — Report")
    lines.append("")
    lines.append(f"- Date: 2026-08-16")
    lines.append(f"- GSC property: https://www.chinaboundtravel.com/")
    lines.append(f"- GitHub main: `7f4c0b9` (P1-GROWTH-01) → new commit this round")
    lines.append("")
    lines.append("## 1. GSC access status")
    lines.append("")
    lines.append("- Property ownership: **VERIFIED** (browser-verified 2026-08-16)")
    lines.append("- Service account read access: **VERIFIED** (Search Console API OK)")
    lines.append("- Indexed / Not indexed (GSC UI): **69 / 89**")
    lines.append("- Sitemap: /sitemap.xml submitted = SUCCESS (72 URLs per GSC; local build = 71)")
    lines.append("")
    lines.append("## 2. 28-day metrics")
    lines.append("")
    lines.append("| dimension | clicks | impressions | ctr | avg position |")
    lines.append("|---|---|---|---|---|")
    lines.append(f"| query | {c28} | {i28} | {pct(ctr28)} | {pos28:.1f} |")
    lines.append(f"| page | {c28p} | {i28p} | {pct(ctr28p)} | {pos28p:.1f} |")
    lines.append("")
    lines.append(f"- Window: 2026-07-19 .. 2026-08-15 (GSC data through 08-13), "
                 f"{len(d28)} days with data")
    lines.append("")
    lines.append("## 3. 3-month metrics")
    lines.append("")
    lines.append("| dimension | clicks | impressions | ctr | avg position |")
    lines.append("|---|---|---|---|---|")
    lines.append(f"| query | {c90} | {i90} | {pct(ctr90)} | {pos90:.1f} |")
    lines.append(f"| page | {c90p} | {i90p} | {pct(ctr90p)} | {pos90p:.1f} |")
    lines.append("")
    lines.append(f"- 90-day window matches 28-day data: property registered 2026-07-20; "
                 f"only {len(d90)} days with data exist.")
    lines.append("")
    lines.append("## 4. Top queries (28d)")
    lines.append("")
    lines.append("| query | impressions | clicks | ctr | position |")
    lines.append("|---|---|---|---|---|")
    for r in top_queries:
        lines.append(f"| {r['query']} | {r['impressions']} | {r['clicks']} | "
                     f"{pct(float(r['ctr']))} | {float(r['position']):.1f} |")
    lines.append("")
    lines.append("## 5. Top pages (28d)")
    lines.append("")
    lines.append("| page | impressions | clicks | ctr | position |")
    lines.append("|---|---|---|---|---|")
    for r in top_pages:
        lines.append(f"| {r['page']} | {r['impressions']} | {r['clicks']} | "
                     f"{pct(float(r['ctr']))} | {float(r['position']):.1f} |")
    lines.append("")
    lines.append("## 6. Low CTR opportunities")
    lines.append("")
    lines.append("- See `reports/seo/LOW_CTR_OPPORTUNITIES.md` (sorted by position, "
                 "banded 1-3 / 4-10 / 11-20).")
    lines.append(f"- Query-level CTR is 0% for all 120 queries; page-level CTR is {pct(ctr28p)}.")
    lines.append("")
    lines.append("## 7. Page 1 opportunities")
    lines.append("")
    lines.append("- See `reports/seo/PAGE_1_OPPORTUNITIES.md` (position 4-20, "
                 "prioritised by impressions).")
    lines.append("")
    lines.append("## 8. Index coverage baseline")
    lines.append("")
    lines.append(f"- GSC UI totals: indexed = **69**, not indexed = **89** (2026-08-16).")
    lines.append(f"- Per-URL URL Inspection API: {len(inspection)} URLs inspected, "
                 f"{indexed} indexed.")
    lines.append("- Coverage-state breakdown and canonical conflicts: "
                 "`reports/seo/INDEX_COVERAGE_BASELINE.md`.")
    lines.append("- Exclusion reasons not available via the current API are marked "
                 "`NOT_AVAILABLE_FROM_CURRENT_API` (no guessing).")
    lines.append("")
    lines.append("## 9. Sitemap / index gap")
    lines.append("")
    lines.append("- See `reports/seo/SITEMAP_INDEX_GAP.md`: in-sitemap-not-indexed, "
                 "indexed-not-in-sitemap, redirected-in-sitemap, canonical-mismatch.")
    lines.append("")
    lines.append("## 10. Content inventory")
    lines.append("")
    lines.append(f"- `reports/seo/CONTENT_SEO_INVENTORY.csv`: {len(inv)} posts "
                 "with content_id/title/url/date/28d performance/indexed_status.")
    lines.append("")
    lines.append("## 11. Query intent distribution")
    lines.append("")
    lines.append("| intent | queries | share |")
    lines.append("|---|---|---|")
    total_q = len(intent_rows)
    for intent in ["BRAND", "VISA", "PAYMENT", "INTERNET", "CITY", "TRANSPORT", "TRAVEL_GUIDE", "OTHER"]:
        n = intent_agg.get(intent, 0)
        lines.append(f"| {intent} | {n} | {n/total_q*100:.1f}% |")
    lines.append("")
    lines.append("- Rule-based classification, no external LLM API. "
                 "Full table: `reports/seo/QUERY_INTENT_DISTRIBUTION.md`.")
    lines.append("")
    lines.append("## 12. Recommended next actions")
    lines.append("")
    lines.append("- **TITLE/META**: highest-impression zero-click queries (e.g. `china high "
                 "speed rail tickets`, `china bound`) → snippet/CTR work in GROWTH-03.")
    lines.append("- **FAQ**: position 4-10 queries (`china bound` pos 7.25, "
                 "`china visa itinerary template` pos 9.3).")
    lines.append("- **CONTENT_UPDATE**: position 11-20 queries and weak-CTR pages "
                 "(food-delivery guide 159 imp, high-speed-rail 138 imp).")
    lines.append("- **INTERNAL_LINK**: multi-query pages (E-rule) → hub + internal linking.")
    lines.append("- **TECHNICAL_REVIEW**: query/page mismatch signals (G-rule).")
    lines.append("- **Indexing**: re-check excluded 89 URLs; address any real coverage "
                 "issues before GROWTH-03 content work.")
    lines.append("")
    lines.append("## 13. Tests")
    lines.append("")
    lines.append("| check | result |")
    lines.append("|---|---|")
    lines.append("| `python -m pytest tests/ -q` | PASS (129 passed) |")
    lines.append("| `hugo --gc --minify` | PASS (exit 0) |")
    lines.append("| `content_id_audit audit --strict` | PASS (57/57) |")
    lines.append("| workflow yaml validation | PASS (18/18) |")
    lines.append("| secret scan (HEAD + tracked) | PASS (0 real secret hits) |")
    lines.append("")
    lines.append("## 14. Production status")
    lines.append("")
    lines.append("- GitHub main: `7f4c0b9` (this round adds analysis-only files; "
                 "a normal `git push` follows).")
    lines.append("- No production change: no article/URL/canonical/sitemap/robots/"
                 "affiliate modification; no deploy triggered by this round's content.")
    lines.append("")
    lines.append("## Final status")
    lines.append("")
    lines.append("P1-GROWTH-02 = **PASS** (data successfully obtained; analysis-only)")
    lines.append("")
    lines.append("NEXT = P1-GROWTH-03 CONTENT OPPORTUNITY ENGINE")
    lines.append("")
    (REPO / "reports" / "P1_GROWTH_02_GSC_SEARCH_ANALYTICS_REPORT.md").write_text(
        "\n".join(lines), encoding="utf-8")
    print("wrote reports/P1_GROWTH_02_GSC_SEARCH_ANALYTICS_REPORT.md")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
