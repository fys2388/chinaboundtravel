#!/usr/bin/env python3
"""P1-GROWTH-02: index coverage baseline + sitemap/index gap reports.

Consumes reports/seo/url_inspection_results.json (per-URL Search Console
URL Inspection API output) plus public/sitemap.xml and the 28-day page
performance CSV, and emits:

  reports/seo/INDEX_COVERAGE_BASELINE.md
  reports/seo/SITEMAP_INDEX_GAP.md
  reports/seo/INDEX_SEARCH_CONFLICTS.md

All data comes from the GSC API or the local build; nothing is guessed.
Exclusion reasons that the current API cannot provide are explicitly
marked NOT_AVAILABLE_FROM_CURRENT_API.
"""

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SEO_DIR = REPO / "reports" / "seo"
SITE = "https://www.chinaboundtravel.com"

INDEXED_STATES = {"submitted and indexed", "indexed"}
NOT_INDEXED_STATES = {
    "url is unknown to google",
    "crawled - currently not indexed",
    "discovered - currently not indexed",
    "duplicate without user-selected canonical",
    "duplicate, google chose different canonical than user",
    "alternate page with proper canonical tag",
    "page with redirect",
    "redirect error",
    "blocked by robots.txt",
    "soft 404",
}


def load_inspection(path=SEO_DIR / "url_inspection_results.json"):
    if not Path(path).is_file():
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_sitemap(path=REPO / "public" / "sitemap.xml"):
    if not Path(path).is_file():
        return []
    xml = Path(path).read_text(encoding="utf-8")
    return sorted(set(re.findall(r"<loc>(.*?)</loc>", xml)))


def load_pages(path=SEO_DIR / "raw_pages_28d.csv"):
    if not Path(path).is_file():
        return {}
    out = {}
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out[r["keys"].rstrip("/")] = {
                "clicks": int(float(r["clicks"])),
                "impressions": int(float(r["impressions"])),
                "ctr": float(r["ctr"]),
                "position": float(r["position"]),
            }
    return out


def status_of(rec):
    cov = (rec.get("coverage_state") or "").strip()
    low = cov.lower()
    if rec.get("error"):
        return "UNKNOWN"
    if not cov:
        return "UNKNOWN"
    if low in INDEXED_STATES or "indexed" in low:
        return "INDEXED"
    if low in NOT_INDEXED_STATES or "not indexed" in low or "excluded by" in low:
        return "NOT_INDEXED"
    return "UNKNOWN"


def main():
    inspection = load_inspection()
    sitemap = load_sitemap()
    pages = load_pages()
    recs = [(url, rec, status_of(rec)) for url, rec in inspection.items()]

    # ---------- INDEX_COVERAGE_BASELINE.md ----------
    by_status = Counter(s for _, _, s in recs)
    by_coverage = Counter((r.get("coverage_state") or r.get("error") or "EMPTY")
                          for _, r, _s in recs if r.get("coverage_state") or r.get("error"))
    lines = ["# Index Coverage Baseline", "",
             "Known totals (GSC UI, browser-verified 2026-08-16):",
             "",
             "- Indexed: **69**",
             "- Not indexed: **89**",
             "- Sitemap: /sitemap.xml submitted = SUCCESS (72 URLs per GSC; "
             "local build = %d)" % len(sitemap),
             "",
             "## Per-URL inspection (Search Console URL Inspection API)",
             "",
             f"URLs inspected: **{len(recs)}** (all sitemap URLs + posts + core pages)",
             "",
             "| status | count |",
             "|---|---|",
             f"| INDEXED | {by_status.get('INDEXED', 0)} |",
             f"| NOT_INDEXED | {by_status.get('NOT_INDEXED', 0)} |",
             f"| UNKNOWN | {by_status.get('UNKNOWN', 0)} |",
             "",
             "## Coverage states observed from the API", "",
             "| coverage state | count |",
             "|---|---|"]
    for state, n in by_coverage.most_common():
        lines.append(f"| {state} | {n} |")
    lines += ["",
              "## Exclusion reasons",
              "",
              "Per-URL exclusion reasons come from the URL Inspection API "
              "coverage states above. Full GSC UI reason breakdown (69/89) "
              "is NOT_AVAILABLE_FROM_CURRENT_API; the totals were verified "
              "in the GSC UI on 2026-08-16.",
              "",
              "## Canonical conflicts (inspection)", "",
              "| url | google canonical | user canonical |",
              "|---|---|---|"]
    conflicts = [(u, r) for u, r, _s in recs
                 if r.get("google_canonical") and r.get("user_canonical")
                 and r["google_canonical"].rstrip("/") != r["user_canonical"].rstrip("/")]
    for u, r in conflicts:
        lines.append(f"| {u} | {r['google_canonical']} | {r['user_canonical']} |")
    if not conflicts:
        lines.append("| (none detected) | | |")
    lines.append("")
    (SEO_DIR / "INDEX_COVERAGE_BASELINE.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote INDEX_COVERAGE_BASELINE.md (inspected={len(recs)})")

    # ---------- SITEMAP_INDEX_GAP.md ----------
    smap = set(sitemap)
    insp_urls = set(inspection)
    status = {u: s for u, _, s in recs}
    indexed_urls = {u for u, r in inspection.items() if status_of(r) == "INDEXED"}

    # A. sitemap but not indexed (per inspection, where known)
    a_rows = []
    for u in sorted(smap):
        if u in status and status[u] == "NOT_INDEXED":
            a_rows.append((u, inspection[u].get("coverage_state", "")))
    # B. indexed but not in sitemap
    b_rows = sorted(u for u in indexed_urls if u not in smap)
    # C. redirected URL in sitemap
    c_rows = []
    for u in sorted(smap):
        r = inspection.get(u, {})
        cov = (r.get("coverage_state") or "").lower()
        if "redirect" in cov:
            c_rows.append((u, r.get("coverage_state", "")))
    # D. canonical mismatch candidates
    d_rows = [(u, r["google_canonical"], r["user_canonical"])
              for u, r in conflicts]

    gap = ["# Sitemap / Index Gap", "",
           f"- Sitemap URLs (local build): {len(smap)}",
           f"- Sitemap URLs submitted per GSC: 72",
           f"- Inspected URLs: {len(insp_urls)}",
           f"- Inspected & indexed: {len(indexed_urls)}",
           "",
           "## A. In sitemap but not indexed (per URL Inspection API)", "",
           "| url | coverage state |", "|---|---|"]
    for u, cov in a_rows:
        gap.append(f"| {u} | {cov} |")
    if not a_rows:
        gap.append("| (none detected among inspected URLs) | |")
    gap += ["", "## B. Indexed but not in sitemap", ""]
    for u in b_rows:
        gap.append(f"- {u}")
    if not b_rows:
        gap.append("- (none detected)")
    gap += ["", "## C. Redirected URL in sitemap", ""]
    for u, cov in c_rows:
        gap.append(f"- {u} ({cov})")
    if not c_rows:
        gap.append("- (none detected)")
    gap += ["", "## D. Canonical mismatch candidates", "",
            "| url | google canonical | user canonical |", "|---|---|---|"]
    for u, g, uc in d_rows:
        gap.append(f"| {u} | {g} | {uc} |")
    if not d_rows:
        gap.append("| (none detected) | | |")
    gap.append("")
    (SEO_DIR / "SITEMAP_INDEX_GAP.md").write_text("\n".join(gap), encoding="utf-8")
    print(f"wrote SITEMAP_INDEX_GAP.md")

    # ---------- INDEX_SEARCH_CONFLICTS.md (Step 6, report-only) ----------
    page_urls = {u.rstrip("/") for u in pages}
    conf = ["# Index / Search Conflicts (report only, no changes)", "",
            "## Pages with GSC impressions but no post inventory row", ""]
    extra = sorted(u for u in page_urls if u not in {p.rstrip("/") for p in
                 (SEO_DIR / "CONTENT_SEO_INVENTORY.csv").read_text(encoding="utf-8").splitlines()} or True)
    # use inventory list properly
    inv = []
    with open(SEO_DIR / "CONTENT_SEO_INVENTORY.csv", encoding="utf-8") as f:
        inv = [r["url"].rstrip("/") for r in csv.DictReader(f)]
    extra = sorted(u for u in page_urls if u not in set(inv))
    for u in extra:
        conf.append(f"- {u} (impressions={pages[u]['impressions']})")
    if not extra:
        conf.append("- (none)")
    conf += ["", "## Sitemap pages without search impressions (28d)", ""]
    no_imp = sorted(u for u in smap if u.rstrip("/") not in page_urls)
    for u in no_imp[:40]:
        conf.append(f"- {u}")
    if not no_imp:
        conf.append("- (none)")
    conf += ["", "## Indexed pages without query data (inspected, indexed, no page row)", ""]
    no_query = sorted(u for u in indexed_urls if u.rstrip("/") not in page_urls)
    for u in no_query:
        conf.append(f"- {u}")
    if not no_query:
        conf.append("- (none)")
    conf += ["", "## Canonical inconsistencies (from inspection)", ""]
    for u, g, uc in d_rows:
        conf.append(f"- {u}: google={g} user={uc}")
    if not d_rows:
        conf.append("- (none detected)")
    conf.append("")
    (SEO_DIR / "INDEX_SEARCH_CONFLICTS.md").write_text("\n".join(conf), encoding="utf-8")
    print("wrote INDEX_SEARCH_CONFLICTS.md")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
