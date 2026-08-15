#!/usr/bin/env python3
"""P1-GROWTH-03: Content Opportunity Engine (ChinaBound Travel).

Combines GSC search analytics, content inventory, index status, query
intent, business intent and content-gap signals into one transparent,
deterministic, rule-based opportunity score per article (0-100, no LLM).

Scoring model (sum of five components):
  INDEXING  /20   20=indexed 10=unknown 0=not indexed
  DEMAND    /25   impressions tiers: 0 / 1-49 / 50-99 / 100-499 / 500+
  PERFORM   /20   position band + CTR + clicks (rewards position 4-20)
  BUSINESS  /20   intent value HIGH/MEDIUM/LOW
  GAP       /15   multi-query -> same page; high impression weak page
Tier: A 80-100 | B 60-79 | C 40-59 | D <40

Outputs (reports/seo/):
  content_opportunity_scores.csv
  TIER_A_CONTENT_OPPORTUNITIES.md        (top 20)
  TIER_B_CONTENT_OPPORTUNITIES.md        (top 30)
  INDEX_RECOVERY_QUEUE.md                (10 not-indexed posts)
  CANONICAL_CONFLICT_QUEUE.md            (6 known candidates)
  TOPIC_CLUSTER_GAPS.md
  NEW_CONTENT_IDEAS.md                   (top 20, evidence-backed)
  COMMERCIAL_CONTENT_OPPORTUNITIES.md
  CONTENT_UPDATE_ROADMAP.md              (NOW / NEXT / LATER)
  CONTENT_OPPORTUNITY_FEED.json          (stable machine-readable feed)

Read-only: never modifies articles, front matter, URLs, sitemap or robots.
"""

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SEO_DIR = REPO / "reports" / "seo"
SITE = "https://www.chinaboundtravel.com"

# --------------------------------------------------------------------------
# Intent / business classification (transparent rules, no LLM)
# --------------------------------------------------------------------------

INTENT_KEYWORDS = {
    "VISA": ["visa", "transit", "144", "240", "entry", "immigration", "border", "evisa"],
    "PAYMENT": ["wechat pay", "alipay", "payment", "pay", "card", "cash", "money", "unionpay"],
    "INTERNET": ["wifi", "sim", "internet", "vpn", "esim", "data", "hotspot", "phone plan"],
    "TRANSPORT": ["train", "rail", "subway", "metro", "flight", "airport", "taxi", "bus", "ticket", "12306", "transport"],
    "CITY": ["beijing", "shanghai", "shenzhen", "chengdu", "guangzhou", "hangzhou", "xian", "chongqing", "hong kong", "macau", "suzhou", "tianjin", "sichuan", "guilin", "yangshuo", "kunming", "zhangjiajie"],
    "TRAVEL_GUIDE": ["itinerary", "travel guide", "travel", "guide", "tour", "trip", "attraction", "tips", "packing", "food", "restaurant", "hotel", "accommodation", "language", "etiquette", "culture", "weather", "insurance", "safe"],
}

BUSINESS_VALUE = {
    "VISA": "HIGH",
    "PAYMENT": "HIGH",
    "INTERNET": "HIGH",
    "TRANSPORT": "HIGH",
    "CITY": "MEDIUM",
    "TRAVEL_GUIDE": "MEDIUM",
    "OTHER": "LOW",
}

BUSINESS_SCORE = {"HIGH": 20, "MEDIUM": 12, "LOW": 6}


def classify_text(text):
    t = (text or "").lower()
    for intent, words in INTENT_KEYWORDS.items():
        for w in words:
            if w in t:
                return intent
    return "OTHER"


def business_value(text):
    return BUSINESS_VALUE.get(classify_text(text), "LOW")


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------

def load_csv(path):
    rows = []
    if not Path(path).is_file():
        return rows
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows


def load_json(path):
    if not Path(path).is_file():
        return {}
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}


def _num(v, default=0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


# --------------------------------------------------------------------------
# Scoring (pure, deterministic)
# --------------------------------------------------------------------------

def indexing_score(status):
    s = (status or "").strip().lower()
    if s == "indexed":
        return 20
    if s in ("unknown", ""):
        return 10
    return 0


def demand_score(impressions):
    imp = int(impressions or 0)
    if imp >= 500:
        return 25
    if imp >= 100:
        return 20
    if imp >= 50:
        return 15
    if imp >= 1:
        return 10
    return 0


def performance_score(position, ctr, clicks):
    pos = _num(position, 0)
    ctr = _num(ctr, 0)
    clicks = int(clicks or 0)
    if pos <= 0:
        return 0
    if pos <= 3:
        pos_pts = 12
    elif pos <= 10:
        pos_pts = 10
    elif pos <= 20:
        pos_pts = 8
    elif pos <= 50:
        pos_pts = 4
    else:
        pos_pts = 2
    ctr_pts = min(5, int(ctr * 250))
    click_pts = min(3, clicks)
    return min(20, pos_pts + ctr_pts + click_pts)


def business_intent_score(text):
    return BUSINESS_SCORE.get(business_value(text), 6)


def gap_score(impressions, position, clicks, query_count):
    imp = int(impressions or 0)
    pos = _num(position, 0)
    clicks = int(clicks or 0)
    pts = 0
    if query_count >= 6:
        pts += 6
    elif query_count >= 3:
        pts += 4
    elif query_count >= 2:
        pts += 2
    if imp >= 100 and pos > 20:
        pts += 4
    if imp >= 100 and clicks == 0:
        pts += 3
    if imp >= 50 and pos >= 20:
        pts += 2
    return min(15, pts)


def tier_of(score):
    if score >= 80:
        return "A"
    if score >= 60:
        return "B"
    if score >= 40:
        return "C"
    return "D"


def primary_action(row):
    """Deterministic single primary action per article (priority order)."""
    status = (row.get("indexed_status") or "").strip().lower()
    imp = int(row.get("impressions_28d") or 0)
    clicks = int(row.get("clicks_28d") or 0)
    pos = _num(row.get("position_28d"), 0)
    ctr = _num(row.get("ctr_28d"), 0)
    qcount = int(row.get("query_count") or 0)
    business = row.get("business_value") or "LOW"

    if status != "indexed":
        return "INDEX_FIX"
    if imp >= 100 and clicks == 0:
        return "TITLE_TEST"
    if 4 <= pos <= 20 and imp >= 50:
        return "CONTENT_UPDATE"
    if imp >= 100 and ctr < 0.03:
        return "META_TEST"
    if business == "HIGH" and imp >= 20:
        return "COMMERCIAL_OPTIMIZATION"
    if qcount >= 5:
        return "INTERNAL_LINK"
    if qcount >= 2 and imp >= 10:
        return "FAQ_EXPANSION"
    if imp >= 1:
        return "CONTENT_EXPANSION"
    return "MONITOR"


# --------------------------------------------------------------------------
# Report writers
# --------------------------------------------------------------------------

def md_table(path, title, columns, rows, intro=None):
    lines = [f"# {title}", ""]
    if intro:
        lines.append(intro)
        lines.append("")
    lines.append("| " + " | ".join(columns) + " |")
    lines.append("|" + "---|" * len(columns))
    for r in rows:
        vals = []
        for c in columns:
            v = r.get(c, "")
            if c == "ctr" and isinstance(v, (int, float)):
                v = f"{v * 100:.2f}%"
            vals.append(str(v))
        lines.append("| " + " | ".join(vals) + " |")
    lines.append("")
    Path(path).write_text("\n".join(lines), encoding="utf-8")


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inventory", default=str(SEO_DIR / "CONTENT_SEO_INVENTORY.csv"))
    ap.add_argument("--queries", default=str(SEO_DIR / "query_performance.csv"))
    ap.add_argument("--pages", default=str(SEO_DIR / "page_performance.csv"))
    ap.add_argument("--query-pages", default=str(SEO_DIR / "raw_queries_pages_28d.csv"))
    ap.add_argument("--opportunities", default=str(SEO_DIR / "seo_opportunities.csv"))
    ap.add_argument("--inspection", default=str(SEO_DIR / "url_inspection_results.json"))
    ap.add_argument("--sitemap", default=str(REPO / "public" / "sitemap.xml"))
    ap.add_argument("--out-dir", default=str(SEO_DIR))
    args = ap.parse_args(argv)

    inventory = load_csv(args.inventory)
    queries = load_csv(args.queries)
    pages = load_csv(args.pages)
    qp = load_csv(args.query_pages)
    opps = load_csv(args.opportunities)
    inspection = load_json(args.inspection)
    out_dir = Path(args.out_dir)

    # Duplicate handling: several legacy Persona posts share one canonical
    # URL.  Score every inventory row, but mark one primary row per URL
    # (latest published_date, then content_id) so tier lists are clean.
    dup_count = Counter((inv.get("url") or "").rstrip("/") for inv in inventory)
    primary_by_url = {}
    for inv in sorted(inventory,
                      key=lambda r: ((r.get("published_date") or ""), r.get("content_id") or ""),
                      reverse=True):
        u = (inv.get("url") or "").rstrip("/")
        if u and u not in primary_by_url:
            primary_by_url[u] = (inv.get("content_id") or "")

    # query count per URL from the query+page cross dimension
    qcount_by_url = Counter()
    for r in qp:
        parts = (r.get("keys") or "").split(";")
        if len(parts) == 2:
            qcount_by_url[parts[1].rstrip("/")] += 1

    # opportunity types per URL
    opp_types_by_url = defaultdict(list)
    for r in opps:
        u = (r.get("page") or "").rstrip("/")
        if u:
            opp_types_by_url[u].append(r.get("opportunity_type", ""))

    # sitemap URL set
    sitemap = set()
    if Path(args.sitemap).is_file():
        xml = Path(args.sitemap).read_text(encoding="utf-8")
        sitemap = {u.rstrip("/") for u in re.findall(r"<loc>(.*?)</loc>", xml)}

    # canonical conflicts from inspection
    conflicts = []
    for u, rec in inspection.items():
        gc = rec.get("google_canonical") or ""
        uc = rec.get("user_canonical") or ""
        if gc and uc and gc.rstrip("/") != uc.rstrip("/"):
            conflicts.append({
                "url": u,
                "canonical": gc,
                "user_canonical": uc,
                "sitemap_status": "IN_SITEMAP" if u.rstrip("/") in sitemap else "NOT_IN_SITEMAP",
                "indexed_status": "INDEXED" if "indexed" in (rec.get("coverage_state") or "").lower() else "NOT_INDEXED",
            })

    # ---- score every article ----
    inspection_norm = {u.rstrip("/"): rec for u, rec in inspection.items()}
    rows = []
    for inv in inventory:
        url = (inv.get("url") or "").strip()
        key = url.rstrip("/")
        imp = int(_num(inv.get("impressions_28d"), 0))
        clicks = int(_num(inv.get("clicks_28d"), 0))
        ctr = _num(inv.get("ctr_28d"), 0)
        pos = _num(inv.get("position_28d"), 0)
        qcount = qcount_by_url.get(key, 0)
        status = (inv.get("indexed_status") or "UNKNOWN").strip()
        intent = classify_text(url + " " + (inv.get("title") or ""))
        bval = BUSINESS_VALUE.get(intent, "LOW")
        s_index = indexing_score(status)
        s_demand = demand_score(imp)
        s_perf = performance_score(pos, ctr, clicks)
        s_biz = BUSINESS_SCORE.get(bval, 6)
        s_gap = gap_score(imp, pos, clicks, qcount)
        total = min(100, s_index + s_demand + s_perf + s_biz + s_gap)
        row = {
            "content_id": inv.get("content_id", ""),
            "title": inv.get("title", ""),
            "url": url,
            "section": inv.get("section", "posts"),
            "published_date": inv.get("published_date", ""),
            "duplicate_count": dup_count.get(key, 1),
            "is_primary": primary_by_url.get(key) == (inv.get("content_id") or ""),
            "indexed_status": status,
            "clicks_28d": clicks,
            "impressions_28d": imp,
            "ctr_28d": round(ctr, 6),
            "avg_position": round(pos, 2),
            "query_count": qcount,
            "business_intent": intent,
            "business_value": bval,
            "indexing_score": s_index,
            "demand_score": s_demand,
            "performance_score": s_perf,
            "business_score": s_biz,
            "gap_score": s_gap,
            "opportunity_score": total,
            "opportunity_tier": tier_of(total),
            "primary_action": "",
            "opportunity_types": ";".join(sorted(set(opp_types_by_url.get(key, [])))),
            "reason": "",
        }
        row["primary_action"] = primary_action(row)
        rows.append(row)

    rows.sort(key=lambda r: (-r["opportunity_score"], -r["impressions_28d"],
                             r["avg_position"] if r["avg_position"] else 1e9, r["url"]))

    # reasons (human-readable one-liner for tier reports)
    for i, r in enumerate(rows, 1):
        parts = []
        if r["indexed_status"] != "INDEXED":
            parts.append("not indexed")
        if r["impressions_28d"] >= 100 and r["clicks_28d"] == 0:
            parts.append(f"high impressions ({r['impressions_28d']}) with zero clicks")
        if 4 <= r["avg_position"] <= 20 and r["impressions_28d"] >= 50:
            parts.append(f"near page 1 (pos {r['avg_position']})")
        if r["query_count"] >= 3:
            parts.append(f"{r['query_count']} queries point to this page")
        if r["business_value"] == "HIGH":
            parts.append("high commercial intent")
        if not parts:
            parts.append("monitor")
        r["reason"] = "; ".join(parts)

    # ---- content_opportunity_scores.csv ----
    csv_fields = ["content_id", "title", "url", "section", "published_date",
                  "duplicate_count", "is_primary", "indexed_status",
                  "clicks_28d", "impressions_28d", "ctr_28d",
                  "avg_position", "query_count", "business_intent", "business_value",
                  "indexing_score", "demand_score", "performance_score",
                  "business_score", "gap_score", "opportunity_score",
                  "opportunity_tier", "primary_action", "reason"]
    with open(out_dir / "content_opportunity_scores.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=csv_fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in csv_fields})

    primary_rows = [r for r in rows if r["is_primary"]]
    tier_a = [r for r in primary_rows if r["opportunity_tier"] == "A"][:20]
    tier_b = [r for r in primary_rows if r["opportunity_tier"] == "B"][:30]

    # ---- Tier A report ----
    a_cols = ["rank", "content_id", "title", "url", "opportunity_score",
              "opportunity_tier", "impressions_28d", "clicks_28d", "ctr_28d",
              "avg_position", "indexed_status", "business_intent",
              "primary_action", "reason"]
    a_intro = ("Score 80-100. Top 20 ranked by opportunity_score. "
               "LOW_DATA_WARNING: 28d clicks = 3; small sample. "
               "Primary row per canonical URL (duplicates grouped).")
    if not tier_a:
        a_intro += (" No article reached the Tier A threshold (80+); the "
                    "table below lists the top 20 highest-scoring articles "
                    "as the current pipeline.")
        tier_a = primary_rows[:20]
    a_rows = []
    for rank, r in enumerate(tier_a, 1):
        rr = dict(r)
        rr["rank"] = rank
        rr["ctr_28d"] = r["ctr_28d"]
        a_rows.append(rr)
    md_table(out_dir / "TIER_A_CONTENT_OPPORTUNITIES.md",
             "Tier A Content Opportunities (Top 20)", a_cols, a_rows, a_intro)

    # ---- Tier B report ----
    b_rows = []
    for rank, r in enumerate(tier_b, 1):
        rr = dict(r)
        rr["rank"] = rank
        b_rows.append(rr)
    md_table(out_dir / "TIER_B_CONTENT_OPPORTUNITIES.md",
             "Tier B Content Opportunities (Top 30)", a_cols, b_rows,
             "Score 60-79. Top 30 ranked by opportunity_score. "
             "LOW_DATA_WARNING: small 28d sample.")

    # ---- Index recovery queue (10 not-indexed posts) ----
    not_indexed = [r for r in rows if r["indexed_status"] != "INDEXED"]
    recovery = []
    for r in not_indexed[:10]:
        rec = inspection_norm.get(r["url"].rstrip("/"), {})
        cov = rec.get("coverage_state") or ""
        status_label = cov or "NOT_INSPECTED"
        if cov:
            likely = cov
        else:
            likely = "INFERENCE"
        recovery.append({
            "rank": len(recovery) + 1,
            "content_id": r["content_id"],
            "title": r["title"],
            "url": r["url"],
            "inspection_status": status_label,
            "likely_reason": likely,
            "priority": "HIGH" if r["impressions_28d"] >= 20 else "MEDIUM",
            "recommended_action": "INDEX_FIX",
        })
    r_cols = ["rank", "content_id", "title", "url", "inspection_status",
              "likely_reason", "priority", "recommended_action"]
    md_table(out_dir / "INDEX_RECOVERY_QUEUE.md",
             "Index Recovery Queue (10 not-indexed articles)", r_cols, recovery,
             "likely_reason comes from the GSC URL Inspection API coverage "
             "state; non-API inferences are marked INFERENCE.")

    # ---- Canonical conflict queue ----
    c_cols = ["url", "canonical", "user_canonical", "sitemap_status",
              "indexed_status", "severity", "recommended_action"]
    c_rows = []
    for i, c in enumerate(conflicts, 1):
        severity = "HIGH" if c["sitemap_status"] == "IN_SITEMAP" else "MEDIUM"
        if c["canonical"] != SITE and not c["canonical"].startswith(SITE):
            severity = "HIGH"
        c_rows.append({
            "url": c["url"],
            "canonical": c["canonical"],
            "user_canonical": c["user_canonical"],
            "sitemap_status": c["sitemap_status"],
            "indexed_status": c["indexed_status"],
            "severity": severity,
            "recommended_action": "TECHNICAL_REVIEW",
        })
    md_table(out_dir / "CANONICAL_CONFLICT_QUEUE.md",
             "Canonical Conflict Queue", c_cols, c_rows,
             "Candidates detected via URL Inspection API "
             "(google_canonical != user_canonical). No changes made.")

    # ---- Topic cluster gaps ----
    cluster_lines = build_topic_clusters(queries, rows, qcount_by_url)
    (out_dir / "TOPIC_CLUSTER_GAPS.md").write_text("\n".join(cluster_lines), encoding="utf-8")

    # ---- New content ideas (top 20, evidence-backed) ----
    ideas = build_new_content_ideas(queries, qp, rows)
    n_cols = ["rank", "topic", "target_query", "evidence", "recommended_format",
              "priority", "business_intent"]
    md_table(out_dir / "NEW_CONTENT_IDEAS.md", "New Content Ideas (Top 20)",
             n_cols, ideas,
             "Evidence-backed only (GSC query impressions / multi-query "
             "evidence / topic gap). No articles created.")

    # ---- Commercial content opportunities ----
    comm = build_commercial(queries, qp, rows)
    g_cols = ["rank", "query", "page", "impressions", "position",
              "business_intent", "business_value", "recommended_action"]
    md_table(out_dir / "COMMERCIAL_CONTENT_OPPORTUNITIES.md",
             "Commercial Content Opportunities", g_cols, comm,
             "High search + high business intent. No affiliate insertion.")

    # ---- Content update roadmap (NOW / NEXT / LATER) ----
    roadmap = []
    for rank, r in enumerate(primary_rows, 1):
        bucket = "NOW" if rank <= 10 else ("NEXT" if rank <= 25 else "LATER")
        roadmap.append({
            "rank": rank,
            "bucket": bucket,
            "content_id": r["content_id"],
            "title": r["title"],
            "url": r["url"],
            "opportunity_score": r["opportunity_score"],
            "primary_action": r["primary_action"],
            "why": r["reason"],
            "what": action_what(r["primary_action"]),
            "expected_goal": action_goal(r["primary_action"]),
            "risk": "Low" if r["primary_action"] in ("INDEX_FIX", "TITLE_TEST", "META_TEST") else "Medium",
        })
    m_cols = ["rank", "bucket", "content_id", "title", "url", "opportunity_score",
              "primary_action", "why", "what", "expected_goal", "risk"]
    md_table(out_dir / "CONTENT_UPDATE_ROADMAP.md",
             "Content Update Roadmap (NOW / NEXT / LATER)", m_cols, roadmap,
             "NOW = top 10 by score, NEXT = 11-25, LATER = rest. "
             "LOW_DATA_WARNING: 28d clicks = 3.")

    # ---- Feed JSON (stable schema for future AI content system) ----
    queries_by_url = defaultdict(list)
    for r in qp:
        parts = (r.get("keys") or "").split(";")
        if len(parts) == 2:
            queries_by_url[parts[1].rstrip("/")].append(parts[0])
    feed = []
    for r in primary_rows:
        feed.append({
            "content_id": r["content_id"],
            "url": r["url"],
            "opportunity_score": r["opportunity_score"],
            "tier": r["opportunity_tier"],
            "action": r["primary_action"],
            "evidence": {
                "impressions_28d": r["impressions_28d"],
                "clicks_28d": r["clicks_28d"],
                "ctr_28d": r["ctr_28d"],
                "avg_position": r["avg_position"],
                "query_count": r["query_count"],
                "indexed_status": r["indexed_status"],
            },
            "queries": sorted(set(queries_by_url.get(r["url"].rstrip("/"), [])))[:20],
            "business_intent": r["business_intent"],
            "index_status": r["indexed_status"],
        })
    (out_dir / "CONTENT_OPPORTUNITY_FEED.json").write_text(
        json.dumps(feed, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"wrote content_opportunity_scores.csv ({len(rows)} rows)")
    print(f"tier distribution: {dict(Counter(r['opportunity_tier'] for r in rows))}")
    print(f"tier A report: {len(tier_a)} rows | tier B report: {len(tier_b)} rows")
    print(f"index recovery: {len(recovery)} | canonical conflicts: {len(conflicts)}")
    print(f"new content ideas: {len(ideas)} | commercial: {len(comm)}")
    return 0


def action_what(action):
    return {
        "INDEX_FIX": "Investigate coverage state; fix noindex/redirect/canonical causes; request indexing",
        "TITLE_TEST": "Draft 2-3 title variants matching query intent; A/B test snippets",
        "META_TEST": "Rewrite meta description to improve CTR from SERP",
        "CONTENT_UPDATE": "Strengthen on-page relevance for the target query cluster",
        "CONTENT_EXPANSION": "Expand the page with a dedicated section for the missed intent",
        "INTERNAL_LINK": "Add internal links from related hub/related posts",
        "FAQ_EXPANSION": "Add FAQ schema + 3-5 questions matching query intent",
        "COMMERCIAL_OPTIMIZATION": "Add commercial framing and product comparison content",
        "MONITOR": "No strong signal yet; monitor for 2-4 weeks",
    }.get(action, "Review")


def action_goal(action):
    return {
        "INDEX_FIX": "Move page from not-indexed to indexed",
        "TITLE_TEST": "Increase CTR toward category benchmark",
        "META_TEST": "Increase CTR toward category benchmark",
        "CONTENT_UPDATE": "Improve position from page 2+ toward page 1",
        "CONTENT_EXPANSION": "Capture additional query variants",
        "INTERNAL_LINK": "Improve crawl and position distribution",
        "FAQ_EXPANSION": "Win featured snippets / additional impressions",
        "COMMERCIAL_OPTIMIZATION": "Increase monetizable traffic",
        "MONITOR": "Establish a stable baseline",
    }.get(action, "Improve performance")


def build_topic_clusters(queries, rows, qcount_by_url):
    """Aggregate query + article signals per topic cluster."""
    q_imp = defaultdict(int)
    q_cnt = defaultdict(int)
    for q in queries:
        intent = classify_text(q.get("query", ""))
        q_imp[intent] += int(_num(q.get("impressions"), 0))
        q_cnt[intent] += 1
    art = defaultdict(lambda: {"count": 0, "impressions": 0, "indexed": 0})
    for r in rows:
        intent = r["business_intent"]
        art[intent]["count"] += 1
        art[intent]["impressions"] += r["impressions_28d"]
        if r["indexed_status"] == "INDEXED":
            art[intent]["indexed"] += 1
    lines = ["# Topic Cluster Gaps", "",
             "Aggregated from QUERY_INTENT_DISTRIBUTION + article inventory. "
             "LOW_DATA_WARNING: 28d sample is small.", "",
             "| cluster | queries | query impressions | articles | article impressions | indexed articles |",
             "|---|---|---|---|---|---|"]
    order = ["VISA", "PAYMENT", "INTERNET", "TRANSPORT", "CITY", "TRAVEL_GUIDE", "OTHER"]
    for c in order:
        a = art.get(c, {"count": 0, "impressions": 0, "indexed": 0})
        lines.append(f"| {c} | {q_cnt.get(c, 0)} | {q_imp.get(c, 0)} | {a['count']} | "
                     f"{a['impressions']} | {a['indexed']} |")
    lines += ["", "## Strong topics",
              "- Topics with both demand and article coverage (see table above: "
              "query impressions and indexed article count).",
              "",
              "## Weak topics with demand",
              "- VISA: 22 queries / high demand but avg position far from page 1 "
              "(144-hour content ranks ~45-74).",
              "- TRANSPORT: 26 queries; high-speed-rail page ranks ~26-35.",
              "",
              "## Multi-query pages (same page, many queries)",
              ""]
    for u, n in sorted(qcount_by_url.items(), key=lambda x: -x[1]):
        if n >= 3:
            lines.append(f"- {u} ({n} queries)")
    lines += ["", "## Topic gaps (query demand with weak coverage)",
              "- VISA cluster: consider a comparison/FAQ hub for 144-hour vs "
              "30-day visa (multiple queries point to one transit page).",
              "- TRANSPORT: dedicated pages per train class / route booking steps.",
              "- INTERNET: eSIM vs physical SIM vs VPN comparison page.",
              "- PAYMENT: WeChat Pay vs Alipay comparison and setup checklist.",
              "",
              "## Expandable clusters",
              "- VISA and TRANSPORT have the strongest demand-to-coverage signal; "
              "build hub pages + internal linking.",
              "",
              "See NEW_CONTENT_IDEAS.md for evidence-backed new content "
              "candidates.", ""]
    return lines


def build_new_content_ideas(queries, qp, rows):
    """Top 20 new content ideas with GSC query evidence."""
    q_imp = {q.get("query", ""): int(_num(q.get("impressions"), 0)) for q in queries}
    # map query -> pages it currently appears on
    q_pages = defaultdict(list)
    for r in qp:
        parts = (r.get("keys") or "").split(";")
        if len(parts) == 2:
            q_pages[parts[0]].append(parts[1])
    indexed_urls = {r["url"].rstrip("/") for r in rows if r["indexed_status"] == "INDEXED"}
    candidates = []
    for q in queries:
        qname = q.get("query", "")
        imp = int(_num(q.get("impressions"), 0))
        if imp < 3:
            continue
        pages = q_pages.get(qname, [])
        intent = classify_text(qname)
        has_indexed = any(p.rstrip("/") in indexed_urls for p in pages)
        if has_indexed:
            continue  # already covered by an indexed page
        if not pages:
            evidence = f"{imp} impressions, no dedicated page in query+page data"
        else:
            evidence = (f"{imp} impressions, lands on {len(pages)} page(s) that "
                        f"are NOT indexed - consider INDEX_FIX before new content")
        fmt = {
            "VISA": "GUIDE", "PAYMENT": "HOW_TO", "INTERNET": "GUIDE",
            "TRANSPORT": "HOW_TO", "CITY": "CITY", "TRAVEL_GUIDE": "GUIDE",
        }.get(intent, "GUIDE")
        priority = "HIGH" if imp >= 10 else ("MEDIUM" if imp >= 5 else "LOW")
        candidates.append({
            "topic": qname,
            "target_query": qname,
            "evidence": evidence,
            "recommended_format": fmt,
            "priority": priority,
            "business_intent": intent,
        })
    candidates.sort(key=lambda c: (-q_imp[c["target_query"]], c["topic"]))
    for i, c in enumerate(candidates[:20], 1):
        c["rank"] = i
    return candidates[:20]


def build_commercial(queries, qp, rows):
    """High search + high business intent opportunities."""
    comm_intents = {"VISA", "PAYMENT", "INTERNET", "TRANSPORT"}
    q_pages = defaultdict(list)
    for r in qp:
        parts = (r.get("keys") or "").split(";")
        if len(parts) == 2:
            q_pages[parts[0]].append(parts[1])
    indexed_urls = {r["url"].rstrip("/") for r in rows if r["indexed_status"] == "INDEXED"}
    out = []
    for q in queries:
        qname = q.get("query", "")
        intent = classify_text(qname)
        if intent not in comm_intents:
            continue
        imp = int(_num(q.get("impressions"), 0))
        if imp < 3:
            continue
        pos = _num(q.get("position"), 0)
        pages = q_pages.get(qname, [])
        page = pages[0] if pages else "NONE"
        bval = BUSINESS_VALUE.get(intent, "LOW")
        out.append({
            "query": qname,
            "page": page,
            "impressions": imp,
            "position": round(pos, 1),
            "business_intent": intent,
            "business_value": bval,
            "recommended_action": "COMMERCIAL_OPTIMIZATION" if page != "NONE" else "NEW_CONTENT",
        })
    out.sort(key=lambda r: ({"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(r["business_value"], 3),
                            -r["impressions"], r["position"]))
    for i, r in enumerate(out[:30], 1):
        r["rank"] = i
    return out[:30]


if __name__ == "__main__":
    import sys
    sys.exit(main())
