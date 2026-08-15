#!/usr/bin/env python3
"""P1-GROWTH-02: SEO opportunity detector (GSC Search Analytics baseline).

Reads Search Console CSVs (query dimension, page dimension, and the
query+page cross dimension) and produces:

  * reports/seo/seo_opportunities.csv      - machine-readable opportunities
  * reports/seo/SEO_OPPORTUNITIES.md       - top 20 query + top 20 page
  * reports/seo/LOW_CTR_OPPORTUNITIES.md   - high impression + low CTR
  * reports/seo/PAGE_1_OPPORTUNITIES.md    - position 4-20 candidates

Rules (at least A-G from P1-GROWTH-02):
  A. High Impression + Low CTR (query level and page level)
  B. Position 4-10
  C. Position 11-20
  D. High Impression + Zero Click (query level and page level)
  E. Multiple related queries -> same page
  F. High click page with weak CTR
  G. Query/page mismatch signal

Read-only analysis: never modifies articles, URLs, canonicals, sitemap,
robots, or affiliate links.

Recommended-action vocabulary (single value per row):
TITLE / META / CONTENT_UPDATE / INTERNAL_LINK / FAQ /
TOPICAL_EXPANSION / TECHNICAL_REVIEW / MONITOR

Threshold defaults follow the P1-GROWTH-02 spec (high impression >= 100,
low CTR < 3%, high opportunity >= 500).  Every threshold is adjustable via
CLI so small baselines can be analysed without over-filtering.
"""

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SEO_DIR = REPO / "reports" / "seo"

ACTIONS = {
    "TITLE", "META", "CONTENT_UPDATE", "INTERNAL_LINK", "FAQ",
    "TOPICAL_EXPANSION", "TECHNICAL_REVIEW", "MONITOR",
}

# Keyword groups used for the query/page mismatch heuristic (rule G).
INTENT_KEYWORDS = {
    "visa": ["visa", "visa free", "visa-free", "transit", "144", "240", "30 day", "entry"],
    "payment": ["wechat pay", "alipay", "payment", "pay", "mobile pay", "card", "cash"],
    "internet": ["wifi", "sim", "internet", "vpn", "esim", "data", "hotspot", "phone"],
    "city": ["beijing", "shanghai", "shenzhen", "chengdu", "guangzhou", "hangzhou", "xi'an", "xian", "chongqing", "hong kong", "macau", "suzhou", "tianjin", "sichuan"],
    "transport": ["train", "high speed rail", "hsr", "subway", "metro", "flight", "airport", "taxi", "bus", "ticket"],
    "food": ["food", "restaurant", "delivery", "meituan", "eleme", "dining"],
    "hotel": ["hotel", "accommodation", "stay", "hostel"],
    "etiquette": ["etiquette", "culture", "customs", "manners", "tradition"],
}

# URL fragment -> intent keyword map for the page side of rule G.
PAGE_INTENT_HINTS = {
    "visa": ["visa", "transit", "entry", "border"],
    "payment": ["pay", "wechat", "alipay", "money", "card"],
    "internet": ["wifi", "sim", "internet", "vpn", "esim", "phone", "data"],
    "city": ["beijing", "shanghai", "shenzhen", "chengdu", "guangzhou", "hangzhou", "xian", "chongqing", "hong-kong", "macau", "suzhou", "tianjin", "sichuan", "city"],
    "transport": ["train", "rail", "subway", "metro", "flight", "airport", "taxi", "bus", "ticket", "transport"],
    "food": ["food", "delivery", "meituan", "eleme", "restaurant", "dining"],
    "hotel": ["hotel", "accommodation", "stay"],
    "etiquette": ["etiquette", "culture", "customs"],
}


def load_rows(path):
    """Load a GSC CSV into normalized dicts."""
    if not Path(path).is_file():
        return []
    rows = []
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                rows.append({
                    "keys": (r.get("keys") or "").strip(),
                    "clicks": int(float(r.get("clicks") or 0)),
                    "impressions": int(float(r.get("impressions") or 0)),
                    "ctr": float(r.get("ctr") or 0),
                    "position": float(r.get("position") or 0),
                })
            except (TypeError, ValueError):
                continue
    return rows


def _query_intent(query):
    q = (query or "").lower()
    for intent, words in INTENT_KEYWORDS.items():
        for w in words:
            if w in q:
                return intent
    return None


def _page_intent(url):
    u = (url or "").lower()
    for intent, hints in PAGE_INTENT_HINTS.items():
        for h in hints:
            if h in u:
                return intent
    return None


def opportunity(page, query, impressions, clicks, ctr, position, opp_type, action):
    return {
        "page": page or "",
        "query": query or "",
        "impressions": impressions,
        "clicks": clicks,
        "ctr": round(ctr, 6),
        "position": round(position, 2),
        "opportunity_type": opp_type,
        "recommended_action": action,
    }


def detect_opportunities(queries, pages, query_pages,
                         min_impressions=100, max_position=20,
                         low_ctr=0.03, high_opportunity=500):
    """Return a list of opportunity dicts (rules A-G)."""
    opps = []
    seen = set()

    def add(op):
        key = (op["opportunity_type"], op["query"], op["page"])
        if key not in seen:
            seen.add(key)
            opps.append(op)

    # A. High impression + low CTR (query level and page level)
    for r in queries:
        if r["impressions"] >= min_impressions and r["ctr"] < low_ctr:
            add(opportunity("", r["keys"], r["impressions"], r["clicks"],
                            r["ctr"], r["position"], "A_HIGH_IMP_LOW_CTR", "META"))
    for r in pages:
        if r["impressions"] >= min_impressions and r["ctr"] < low_ctr:
            add(opportunity(r["keys"], "", r["impressions"], r["clicks"],
                            r["ctr"], r["position"], "A_HIGH_IMP_LOW_CTR", "META"))
    # B. Position 4-10
    for r in queries:
        if 4 <= r["position"] <= 10 and r["impressions"] >= 1:
            add(opportunity("", r["keys"], r["impressions"], r["clicks"],
                            r["ctr"], r["position"], "B_POSITION_4_10", "FAQ"))
    # C. Position 11-20
    for r in queries:
        if 11 <= r["position"] <= max_position and r["impressions"] >= 1:
            add(opportunity("", r["keys"], r["impressions"], r["clicks"],
                            r["ctr"], r["position"], "C_POSITION_11_20", "CONTENT_UPDATE"))
    # D. High impression + zero click (query level and page level)
    for r in queries:
        if r["impressions"] >= min_impressions and r["clicks"] == 0:
            add(opportunity("", r["keys"], r["impressions"], r["clicks"],
                            r["ctr"], r["position"], "D_HIGH_IMP_ZERO_CLICK", "TITLE"))
    for r in pages:
        if r["impressions"] >= min_impressions and r["clicks"] == 0:
            add(opportunity(r["keys"], "", r["impressions"], r["clicks"],
                            r["ctr"], r["position"], "D_HIGH_IMP_ZERO_CLICK", "TITLE"))
    # E. Multiple related queries -> same page
    by_page = defaultdict(list)
    for r in query_pages:
        parts = r["keys"].split(";")
        if len(parts) == 2:
            by_page[parts[1]].append({"query": parts[0], "impressions": r["impressions"],
                                      "clicks": r["clicks"], "ctr": r["ctr"],
                                      "position": r["position"]})
    for page, items in by_page.items():
        total_imp = sum(i["impressions"] for i in items)
        if len(items) >= 3 and total_imp >= 1:
            avg_pos = sum(i["position"] for i in items) / len(items)
            add(opportunity(page, "", total_imp, sum(i["clicks"] for i in items),
                            0.0, avg_pos, "E_MULTI_QUERY_PAGE", "INTERNAL_LINK"))
    # F. High click page with weak CTR
    for r in pages:
        if r["clicks"] >= 1 and r["ctr"] < low_ctr and r["impressions"] >= min_impressions:
            add(opportunity(r["keys"], "", r["impressions"], r["clicks"],
                            r["ctr"], r["position"], "F_HIGH_CLICK_WEAK_CTR", "CONTENT_UPDATE"))
    # G. Query/page mismatch signal (query intent not reflected on page)
    for r in query_pages:
        parts = r["keys"].split(";")
        if len(parts) != 2:
            continue
        qi = _query_intent(parts[0])
        pi = _page_intent(parts[1])
        if qi and pi and qi != pi and r["impressions"] >= max(1, min_impressions // 4):
            add(opportunity(parts[1], parts[0], r["impressions"], r["clicks"],
                            r["ctr"], r["position"], "G_QUERY_PAGE_MISMATCH", "TECHNICAL_REVIEW"))

    # Sort: high-opportunity first (impressions desc), then position asc.
    opps.sort(key=lambda o: (-o["impressions"], o["position"]))
    for o in opps:
        o["high_opportunity"] = o["impressions"] >= high_opportunity
    return opps


def best_page_for_queries(query_pages):
    """query -> dominant page (by impressions) using the query+page CSV."""
    agg = defaultdict(lambda: {"page": "", "impressions": 0})
    for r in query_pages:
        parts = r["keys"].split(";")
        if len(parts) != 2:
            continue
        q, p = parts[0], parts[1]
        if r["impressions"] > agg[q]["impressions"]:
            agg[q] = {"page": p, "impressions": r["impressions"]}
    return {q: v["page"] for q, v in agg.items()}


def write_csv(path, opps):
    fields = ["page", "query", "impressions", "clicks", "ctr", "position",
              "opportunity_type", "recommended_action"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for o in opps:
            w.writerow({k: o.get(k, "") for k in fields})
    return path


def _pct(ctr):
    return f"{ctr * 100:.1f}%"


def _md_row(r, cols, enrich_page=None):
    vals = []
    for c in cols:
        v = r.get(c, "")
        if c == "ctr" and isinstance(v, (int, float)):
            v = _pct(v)
        elif c == "page" and not v and enrich_page and r.get("query"):
            v = enrich_page.get(r["query"], "")
        vals.append(str(v))
    return "| " + " | ".join(vals) + " |"


def build_reports(opps, query_pages, out_dir=SEO_DIR):
    """Generate the three markdown reports required by P1-GROWTH-02."""
    enrich = best_page_for_queries(query_pages)

    # Top 20 query opportunities (rows where query is set)
    q_opps = [o for o in opps if o["query"]][:20]
    q_cols = ["query", "page", "impressions", "clicks", "ctr", "position",
              "opportunity_type", "recommended_action"]
    intro = ("Top 20 query opportunities (28-day window). ctr is a ratio "
             "(0.05 = 5%); page column is the dominant page for the query "
             "from query+page data.")
    lines = ["# SEO Opportunities", "",
             intro, "",
             "## Top 20 Query Opportunities", "",
             "| " + " | ".join(q_cols) + " |",
             "|" + "---|" * len(q_cols)]
    for r in q_opps:
        lines.append(_md_row(r, q_cols, enrich))
    lines.append("")

    # Top 20 page opportunities (rows where page is set)
    p_opps = [o for o in opps if o["page"]][:20]
    p_cols = ["page", "query", "impressions", "clicks", "ctr", "position",
              "opportunity_type", "recommended_action"]
    lines.append("## Top 20 Page Opportunities")
    lines.append("")
    lines.append("| " + " | ".join(p_cols) + " |")
    lines.append("|" + "---|" * len(p_cols))
    for r in p_opps:
        lines.append(_md_row(r, p_cols))
    lines.append("")
    (out_dir / "SEO_OPPORTUNITIES.md").write_text("\n".join(lines), encoding="utf-8")

    # Low CTR opportunities, sorted by position
    low = sorted([o for o in opps if o["opportunity_type"] in
                  ("A_HIGH_IMP_LOW_CTR", "F_HIGH_CLICK_WEAK_CTR",
                   "D_HIGH_IMP_ZERO_CLICK")],
                 key=lambda o: (o["position"], -o["impressions"]))
    low_cols = ["query", "page", "impressions", "clicks", "ctr", "position",
                "opportunity_type", "recommended_action"]
    low_lines = ["# Low CTR Opportunities", "",
                 "Sorted by position. Position bands: 1-3 (top), 4-10, 11-20.",
                 "",
                 "| " + " | ".join(low_cols) + " |",
                 "|" + "---|" * len(low_cols)]
    for r in low:
        low_lines.append(_md_row(r, low_cols, enrich))
    low_lines.append("")
    (out_dir / "LOW_CTR_OPPORTUNITIES.md").write_text("\n".join(low_lines), encoding="utf-8")

    # Page-1 opportunities (position 4-20), prioritise impressions >= 100
    p1 = [o for o in opps if 4 <= o["position"] <= 20]
    p1.sort(key=lambda o: (-o["impressions"], o["position"]))
    p1_cols = ["query", "page", "position", "impressions", "clicks", "ctr",
               "opportunity_type", "recommended_action"]
    p1_lines = ["# Page 1 Opportunities (Position 4-20)", "",
                "Prioritised by impressions (>= 100 first), then position.",
                "",
                "| " + " | ".join(p1_cols) + " |",
                "|" + "---|" * len(p1_cols)]
    for r in p1:
        p1_lines.append(_md_row(r, p1_cols, enrich))
    p1_lines.append("")
    (out_dir / "PAGE_1_OPPORTUNITIES.md").write_text("\n".join(p1_lines), encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", default=str(SEO_DIR / "raw_queries_28d.csv"),
                    help="query-dimension CSV (also accepts --queries)")
    ap.add_argument("--queries", default=None, help="query-dimension CSV")
    ap.add_argument("--pages", default=str(SEO_DIR / "raw_pages_28d.csv"),
                    help="page-dimension CSV")
    ap.add_argument("--query-pages", default=str(SEO_DIR / "raw_queries_pages_28d.csv"),
                    help="query+page cross-dimension CSV")
    ap.add_argument("--output", default=str(SEO_DIR / "seo_opportunities.csv"),
                    help="output CSV path")
    ap.add_argument("--min-impressions", type=int, default=100,
                    help="high-impression threshold (default 100)")
    ap.add_argument("--max-position", type=int, default=20,
                    help="max position for rule C (default 20)")
    ap.add_argument("--low-ctr", type=float, default=0.03,
                    help="low-CTR threshold as ratio (default 0.03)")
    ap.add_argument("--high-opportunity", type=int, default=500,
                    help="impressions threshold marking high opportunity (default 500)")
    ap.add_argument("--no-reports", action="store_true",
                    help="write only the CSV, skip markdown reports")
    args = ap.parse_args(argv)

    queries_path = args.queries or args.input
    queries = load_rows(queries_path)
    pages = load_rows(args.pages)
    query_pages = load_rows(args.query_pages)
    opps = detect_opportunities(
        queries, pages, query_pages,
        min_impressions=args.min_impressions, max_position=args.max_position,
        low_ctr=args.low_ctr, high_opportunity=args.high_opportunity)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_csv(out, opps)
    print(f"wrote {out} ({len(opps)} opportunities)")

    if not args.no_reports:
        build_reports(opps, query_pages)
        print(f"wrote {SEO_DIR / 'SEO_OPPORTUNITIES.md'}")
        print(f"wrote {SEO_DIR / 'LOW_CTR_OPPORTUNITIES.md'}")
        print(f"wrote {SEO_DIR / 'PAGE_1_OPPORTUNITIES.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
