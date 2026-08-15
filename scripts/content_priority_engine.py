"""P1-GROWTH-04: content prioritization engine.

Reads P1-GROWTH-03 artifacts (NO new GSC API calls, NO repo-wide SEO scan):

  reports/seo/CONTENT_OPPORTUNITY_FEED.json   (48 opportunity items)
  reports/seo/CANONICAL_CONFLICT_QUEUE.md     (6 canonical conflicts, HIGH)
  reports/seo/INDEX_RECOVERY_QUEUE.md         (10 not-indexed articles)
  reports/seo/NEW_CONTENT_IDEAS.md            (14 evidence-backed candidates)
  reports/seo/COMMERCIAL_CONTENT_OPPORTUNITIES.md (16 commercial entries)
  content/posts/*.md                          (read-only title/canonical index)

Produces Priority Score (0-100) that is DIFFERENT from the Opportunity Score:

  SEO Opportunity         /25
  Search Demand           /20
  Business Intent         /15
  Index/Technical Urgency /15
  Execution Ease          /10
  Expected Impact         /10
  Risk                     /5
  --------------------------
  Total                   /100

Outputs (reports/seo/):
  TOP_10_CONTENT_PRIORITIES.md
  CONTENT_EXECUTION_BATCHES.md
  CONTENT_DO_NOT_DO_YET.md
  FIRST_CONTENT_REVIEW_QUEUE.csv
  TOP_5_COMMERCIAL_PAGES.md
  TOP_5_NEW_CONTENT_IDEAS.md

Read-only: never modifies articles, front matter, URLs, sitemap or robots.
Deterministic: same input -> same output (tested).
"""
import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SEO = REPO / "reports" / "seo"
POSTS_DIR = REPO / "content" / "posts"
SITE = "https://www.chinaboundtravel.com"

BUSINESS_VALUE_WEIGHT = {"HIGH": 15, "MEDIUM": 10, "LOW": 5}
INTENT_COMMERCIAL_BIAS = {
    "VISA": 1.0, "PAYMENT": 1.0, "TRANSPORT": 0.9, "INTERNET": 0.8,
    "TRAVEL_GUIDE": 0.5, "CITY": 0.6, "OTHER": 0.3,
}

# ---------------------------------------------------------------------------
# Markdown table parsing (simple, deterministic)
# ---------------------------------------------------------------------------
def parse_md_table(path):
    """Parse a markdown pipe table into a list of dicts. Skips header/separator."""
    rows = []
    header = None
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells or all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
            continue
        if header is None:
            header = cells
            continue
        if len(cells) != len(header):
            continue
        rows.append(dict(zip(header, cells)))
    return rows


def norm_url(u):
    if not u:
        return u
    u = u.strip()
    if u.startswith(SITE):
        u = u[len(SITE):]
    return u.rstrip("/")


# ---------------------------------------------------------------------------
# Input loaders
# ---------------------------------------------------------------------------
def load_feed():
    data = json.loads((SEO / "CONTENT_OPPORTUNITY_FEED.json").read_text(encoding="utf-8"))
    out = []
    for item in data:
        ev = item.get("evidence", {}) or {}
        row = {
            "content_id": item["content_id"],
            "url": item["url"],
            "opportunity_score": float(item.get("opportunity_score", 0)),
            "tier": item.get("tier", "D"),
            "action": item.get("action", "MONITOR"),
            "business_intent": item.get("business_intent", "OTHER"),
            "index_status": item.get("index_status", "UNKNOWN"),
            "queries": item.get("queries", []),
            "query_count": len(item.get("queries", [])),
            "impressions_28d": int(ev.get("impressions_28d", 0)),
            "clicks_28d": int(ev.get("clicks_28d", 0)),
            "ctr_28d": float(ev.get("ctr_28d", 0.0)),
            "avg_position": float(ev.get("avg_position", 0.0)),
            "indexed_status": ev.get("indexed_status", item.get("index_status", "UNKNOWN")),
        }
        out.append(row)
    return out


def _fm_value(text, key):
    """Read one key from YAML (---) or TOML (+++) front matter, quoted values ok."""
    for line in text.splitlines():
        if not line or line.startswith(("---", "+++")):
            continue
        m = re.match(r"^\s*" + re.escape(key) + r"\s*[:=]\s*(.+)$", line)
        if m:
            val = m.group(1).strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
                val = val[1:-1]
            return val
    return None


def load_posts_index():
    """content_id -> title/canonical from front matter (read-only)."""
    idx = {}
    for md in POSTS_DIR.glob("*.md"):
        text = md.read_text(encoding="utf-8", errors="ignore")
        cid = _fm_value(text, "content_id")
        if not cid:
            continue
        title = _fm_value(text, "title") or md.stem
        canonical = _fm_value(text, "canonicalURL")
        idx[cid] = {
            "content_id": cid,
            "title": title,
            "canonical": norm_url(canonical) if canonical else None,
        }
    return idx


def load_canonical_conflicts():
    """Map normalized page URLs to conflict severity."""
    conflicts = {}
    for r in parse_md_table(SEO / "CANONICAL_CONFLICT_QUEUE.md"):
        severity = r.get("severity", "").upper()
        for u in (r.get("url"), r.get("user_canonical")):
            nu = norm_url(u)
            if nu:
                conflicts.setdefault(nu, severity)
    return conflicts


def load_index_recovery():
    """content_id -> likely_reason (real GSC coverage state)."""
    rec = {}
    for r in parse_md_table(SEO / "INDEX_RECOVERY_QUEUE.md"):
        cid = r.get("content_id")
        if cid:
            rec[cid] = r.get("likely_reason", "INFERENCE")
    return rec


def load_new_content_ideas():
    rows = []
    for r in parse_md_table(SEO / "NEW_CONTENT_IDEAS.md"):
        rows.append({
            "rank": int(r.get("rank", 0)),
            "topic": r.get("topic", ""),
            "target_query": r.get("target_query", ""),
            "evidence": r.get("evidence", ""),
            "recommended_format": r.get("recommended_format", ""),
            "priority": r.get("priority", "LOW"),
            "business_intent": r.get("business_intent", "OTHER"),
        })
    return rows


def load_commercial():
    rows = []
    for r in parse_md_table(SEO / "COMMERCIAL_CONTENT_OPPORTUNITIES.md"):
        try:
            imp = int(r.get("impressions", 0))
            pos = float(r.get("position", 99.0))
        except ValueError:
            continue
        rows.append({
            "query": r.get("query", ""),
            "page": norm_url(r.get("page", "")),
            "impressions": imp,
            "position": pos,
            "business_intent": r.get("business_intent", "OTHER"),
            "business_value": r.get("business_value", "LOW"),
            "recommended_action": r.get("recommended_action", ""),
        })
    return rows


# ---------------------------------------------------------------------------
# Scoring components
# ---------------------------------------------------------------------------
def seo_opportunity_score(opportunity_score):
    """/25 - scaled from GROWTH-03 opportunity score (0-100)."""
    return round(opportunity_score * 0.25, 2)


def search_demand_score(impressions, query_count):
    """/20 - impressions tiers plus multi-query evidence (capped)."""
    if impressions >= 500:
        base = 20
    elif impressions >= 100:
        base = 16
    elif impressions >= 50:
        base = 12
    elif impressions >= 1:
        base = 8
    else:
        base = 2
    multi = min(3, query_count // 5)
    return min(20, base + multi)


def business_intent_score(business_intent, business_value):
    """/15 - business value tier weighted by intent commercial bias."""
    tier = BUSINESS_VALUE_WEIGHT.get(business_value, 5)
    bias = INTENT_COMMERCIAL_BIAS.get(business_intent, 0.5)
    return round(tier * bias, 2)


def technical_urgency_score(index_status, canonical_sev, recovery_reason):
    """/15 - not indexed / canonical HIGH get the highest urgency."""
    not_indexed = index_status != "INDEXED"
    if canonical_sev == "HIGH":
        return 15.0
    if not_indexed:
        if recovery_reason and recovery_reason != "INFERENCE":
            return 15.0
        return 12.0
    return 3.0


def execution_ease_score(action):
    """/10 - low effort first (technical/title fixes > rewrites > new content)."""
    easy = {"TECHNICAL_FIX": 9, "INDEX_RECOVERY": 8, "TITLE_META_UPDATE": 9,
            "INTERNAL_LINK": 8, "FAQ_EXPANSION": 7, "MONITOR": 8}
    medium = {"CONTENT_REFRESH": 6, "COMMERCIAL_OPTIMIZATION": 6, "CONTENT_EXPANSION": 5}
    hard = {"NEW_CONTENT": 2}
    if action in easy:
        return easy[action]
    if action in medium:
        return medium[action]
    return hard.get(action, 5)


def expected_impact_score(position, impressions, clicks):
    """/10 - position 4-20 with demand is the sweet spot; weak data caps impact."""
    if impressions == 0:
        return 1.0
    if position <= 0:
        return 3.0
    if 4 <= position <= 20:
        base = 9.0
    elif 21 <= position <= 50:
        base = 6.5
    else:
        base = 3.5
    if clicks > 0:
        base += 1.0
    if impressions < 10:
        base = min(base, 4.0)  # Rule F: low data must not over-inflate
    return round(min(10.0, base), 2)


def risk_score(action, impressions):
    """/5 - higher is safer. Large rewrites / new content are riskier."""
    low_risk = {"TITLE_META_UPDATE": 4, "INTERNAL_LINK": 5, "FAQ_EXPANSION": 4,
                "INDEX_RECOVERY": 3, "MONITOR": 5, "TECHNICAL_FIX": 3}
    med_risk = {"CONTENT_REFRESH": 3, "COMMERCIAL_OPTIMIZATION": 3, "CONTENT_EXPANSION": 3}
    high_risk = {"NEW_CONTENT": 2}
    score = low_risk.get(action, med_risk.get(action, high_risk.get(action, 3)))
    if impressions < 10:
        score = min(score, 3)  # low data guard
    return score


# ---------------------------------------------------------------------------
# Primary action selection
# ---------------------------------------------------------------------------
def primary_action(row, canonical_sev, recovery_reason):
    """One PRIMARY_ACTION per item. Rules are ordered and transparent."""
    if canonical_sev == "HIGH":
        return "TECHNICAL_FIX"
    if row["index_status"] != "INDEXED":
        return "INDEX_RECOVERY"
    imp = row["impressions_28d"]
    ctr = row["ctr_28d"]
    pos = row["avg_position"]
    clicks = row["clicks_28d"]
    qc = row["query_count"]
    if imp >= 50 and ctr < 0.03:
        return "TITLE_META_UPDATE"
    if 4 <= pos <= 20 and imp >= 100:
        return "CONTENT_REFRESH"
    if imp >= 100 and clicks == 0:
        return "TITLE_META_UPDATE"
    if qc >= 8:
        return "CONTENT_EXPANSION"
    if row["business_intent"] in ("VISA", "PAYMENT", "TRANSPORT") and imp > 0:
        return "COMMERCIAL_OPTIMIZATION"
    if qc >= 3:
        return "FAQ_EXPANSION"
    if imp > 0:
        return "INTERNAL_LINK"
    return "MONITOR"


def secondary_actions(row, primary, canonical_sev, recovery_reason):
    """1-3 focused secondary actions."""
    sec = []
    if canonical_sev == "HIGH":
        sec.append("CANONICAL_FIX")
    if row["index_status"] != "INDEXED":
        sec.append("INDEXING_REQUEST")
    if primary != "TITLE_META_UPDATE" and row["ctr_28d"] < 0.03 and row["impressions_28d"] >= 30:
        sec.append("TITLE_META_UPDATE")
    if row["query_count"] >= 5 and primary != "CONTENT_EXPANSION":
        sec.append("FAQ_EXPANSION")
    if row["business_intent"] in ("VISA", "PAYMENT", "TRANSPORT") and primary != "COMMERCIAL_OPTIMIZATION":
        sec.append("COMMERCIAL_REVIEW")
    if row["impressions_28d"] >= 50 and primary not in ("INTERNAL_LINK",):
        sec.append("INTERNAL_LINK")
    return sec[:3] or ["MONITOR"]


# ---------------------------------------------------------------------------
# Full priority scoring with forced rules
# ---------------------------------------------------------------------------
def score_item(row, canonical_conflicts, recovery):
    cu = norm_url(row["url"])
    canonical_sev = canonical_conflicts.get(cu, "")
    reason = recovery.get(row["content_id"], "")
    action = primary_action(row, canonical_sev, reason)
    components = {
        "seo_opportunity": seo_opportunity_score(row["opportunity_score"]),
        "search_demand": search_demand_score(row["impressions_28d"], row["query_count"]),
        "business_intent": business_intent_score(row["business_intent"], "HIGH"
                                                   if row["business_intent"] in ("VISA", "PAYMENT") else "MEDIUM"),
        "technical_urgency": technical_urgency_score(row["index_status"], canonical_sev, reason),
        "execution_ease": execution_ease_score(action),
        "expected_impact": expected_impact_score(row["avg_position"], row["impressions_28d"], row["clicks_28d"]),
        "risk": risk_score(action, row["impressions_28d"]),
    }
    total = round(sum(components.values()), 2)

    # ---- forced rules ----
    rule_flags = []
    if canonical_sev == "HIGH":                      # Rule A
        total = max(total, 85.0)
        rule_flags.append("RULE_A_CANONICAL_HIGH")
    if row["index_status"] != "INDEXED" and row["business_intent"] in ("VISA", "PAYMENT", "TRANSPORT"):  # Rule B
        total = max(total, 80.0)
        rule_flags.append("RULE_B_NOT_INDEXED_COMMERCIAL")
    if 4 <= row["avg_position"] <= 20 and row["impressions_28d"] >= 100:  # Rule C
        total = min(100.0, total + 6.0)
        rule_flags.append("RULE_C_NEAR_PAGE1")
    elif 21 <= row["avg_position"] <= 50 and row["impressions_28d"] >= 100:  # Rule D
        total = min(100.0, total + 3.0)
        rule_flags.append("RULE_D_MID_POSITION")
    if row["clicks_28d"] > 0 and row["business_intent"] in ("VISA", "PAYMENT", "TRANSPORT"):  # Rule E
        total = min(100.0, total + 3.0)
        rule_flags.append("RULE_E_CLICKS_COMMERCIAL")
    if row["impressions_28d"] < 10 and not (canonical_sev or row["index_status"] != "INDEXED"):
        # Rule F: low data must never inflate priority by itself
        total = min(total, 60.0)
        rule_flags.append("RULE_F_LOW_DATA_CAP")

    total = round(min(100.0, max(0.0, total)), 2)
    row.update({
        "canonical_conflict": canonical_sev or "NONE",
        "recovery_reason": reason,
        "primary_action": action,
        "secondary_actions": secondary_actions(row, action, canonical_sev, reason),
        "priority_components": components,
        "priority_score": total,
        "rule_flags": rule_flags,
        "priority_p0": action in ("TECHNICAL_FIX", "INDEX_RECOVERY"),
    })
    return row


def effort_of(action):
    return {"TECHNICAL_FIX": "S", "INDEX_RECOVERY": "S", "TITLE_META_UPDATE": "S",
            "INTERNAL_LINK": "S", "FAQ_EXPANSION": "S", "MONITOR": "S",
            "CONTENT_REFRESH": "M", "COMMERCIAL_OPTIMIZATION": "M",
            "CONTENT_EXPANSION": "M", "NEW_CONTENT": "L"}.get(action, "M")


def tier_of_score(score):
    if score >= 85:
        return "P0"
    if score >= 75:
        return "P1"
    if score >= 65:
        return "P2"
    if score >= 50:
        return "P3"
    return "P4"


# ---------------------------------------------------------------------------
# Markdown / CSV writers
# ---------------------------------------------------------------------------
def md_table(path, title, cols, rows, intro=None):
    lines = [f"# {title}", ""]
    if intro:
        lines += [intro, ""]
    lines.append("| " + " | ".join(cols) + " |")
    lines.append("|" + "|".join(["---"] * len(cols)) + "|")
    for r in rows:
        lines.append("| " + " | ".join(str(r.get(c, "")).replace("|", "/") for c in cols) + " |")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def find_title(posts, row):
    p = posts.get(row["content_id"])
    if p and p["title"]:
        return p["title"]
    return row.get("content_id", "")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def build_report_rows(feed_rows, posts, canonical_conflicts, recovery):
    scored = [score_item(dict(r), canonical_conflicts, recovery) for r in feed_rows]
    # deterministic sort: priority desc, impressions desc, opportunity desc, content_id asc
    scored.sort(key=lambda r: (-r["priority_score"], -r["impressions_28d"],
                               -r["opportunity_score"], r["content_id"]))
    for r in scored:
        r["_title"] = find_title(posts, r)
        r["_effort"] = effort_of(r["primary_action"])
        r["_tier_p"] = tier_of_score(r["priority_score"])
    return scored


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=str(SEO))
    ap.add_argument("--top-n", type=int, default=10)
    args = ap.parse_args()
    out = Path(args.out_dir)

    feed = load_feed()
    posts = load_posts_index()
    conflicts = load_canonical_conflicts()
    recovery = load_index_recovery()
    new_ideas = load_new_content_ideas()
    commercial = load_commercial()

    scored = build_report_rows(feed, posts, conflicts, recovery)
    top10 = scored[:args.top_n]

    # ---- TOP 10 report ----
    cols = ["rank", "priority_score", "priority_tier", "content_id", "title", "url",
            "indexed_status", "impressions_28d", "clicks_28d", "ctr_28d", "avg_position",
            "business_intent", "primary_action", "secondary_actions", "reason",
            "expected_impact", "risk", "effort"]
    rows = []
    for i, r in enumerate(top10, 1):
        reasons = list(r["rule_flags"])
        if r["recovery_reason"] and r["recovery_reason"] != "INFERENCE":
            reasons.append(f"GSC: {r['recovery_reason']}")
        rows.append({
            "rank": i, "priority_score": r["priority_score"], "priority_tier": r["_tier_p"],
            "content_id": r["content_id"], "title": r["_title"], "url": r["url"],
            "indexed_status": r["index_status"],
            "impressions_28d": r["impressions_28d"], "clicks_28d": r["clicks_28d"],
            "ctr_28d": f"{r['ctr_28d']*100:.2f}%", "avg_position": r["avg_position"],
            "business_intent": r["business_intent"], "primary_action": r["primary_action"],
            "secondary_actions": "; ".join(r["secondary_actions"]),
            "reason": "; ".join(reasons) or "monitor",
            "expected_impact": {
                "TECHNICAL_FIX": "Unblock indexing / consolidate signals",
                "INDEX_RECOVERY": "Move page to indexed; enable query capture",
                "TITLE_META_UPDATE": "Higher SERP CTR on existing impressions",
                "CONTENT_REFRESH": "Position gain toward page 1",
                "CONTENT_EXPANSION": "Capture additional query variants",
                "INTERNAL_LINK": "Strengthen page authority flow",
                "FAQ_EXPANSION": "Featured snippet / more impressions",
                "COMMERCIAL_OPTIMIZATION": "More monetizable traffic",
                "NEW_CONTENT": "New demand capture",
                "MONITOR": "Data collection",
            }.get(r["primary_action"], "Review"),
            "risk": {
                "TECHNICAL_FIX": "Low", "INDEX_RECOVERY": "Low", "TITLE_META_UPDATE": "Low",
                "INTERNAL_LINK": "Low", "FAQ_EXPANSION": "Medium", "MONITOR": "Low",
                "CONTENT_REFRESH": "Medium", "COMMERCIAL_OPTIMIZATION": "Medium",
                "CONTENT_EXPANSION": "Medium", "NEW_CONTENT": "High",
            }.get(r["primary_action"], "Medium"),
            "effort": r["_effort"],
        })
    md_table(out / "TOP_10_CONTENT_PRIORITIES.md",
             "Top 10 Content Priorities",
             cols, rows,
             "Priority Score 0-100. LOW_DATA_WARNING: 28d clicks = 3. "
             "Priority != ranking guarantee. Estimated effort: S/M/L only.")

    # ---- Execution batches ----
    batch_map = [
        ("BATCH A - TECHNICAL", ("TECHNICAL_FIX", "INDEX_RECOVERY")),
        ("BATCH B - SEO CONTENT", ("TITLE_META_UPDATE", "CONTENT_REFRESH",
                                   "CONTENT_EXPANSION", "INTERNAL_LINK", "FAQ_EXPANSION")),
        ("BATCH C - COMMERCIAL", ("COMMERCIAL_OPTIMIZATION",)),
        ("BATCH D - NEW CONTENT", ("NEW_CONTENT",)),
        ("MONITOR", ("MONITOR",)),
    ]
    b_lines = ["# Content Execution Batches", "",
               "Order is mandatory: A (technical) -> B (SEO content) -> C (commercial) -> D (new content). "
               "MONITOR items stay queued until more data.", ""]
    for name, actions in batch_map:
        members = [r for r in scored if r["primary_action"] in actions]
        b_lines.append(f"## {name} ({len(members)})")
        b_lines.append("")
        b_lines.append("| rank | content_id | title | url | priority | action | effort |")
        b_lines.append("|---|---|---|---|---|---|---|")
        for i, r in enumerate(members, 1):
            b_lines.append(f"| {i} | {r['content_id']} | {r['_title']} | {r['url']} | "
                           f"{r['priority_score']} | {r['primary_action']} | {r['_effort']} |")
        b_lines.append("")
    (out / "CONTENT_EXECUTION_BATCHES.md").write_text("\n".join(b_lines), encoding="utf-8")

    # ---- Do-not-do-yet ----
    dnd = [
        "Do not bulk-edit the top 10 articles at once - one page per review cycle.",
        "Do not modify all 6 canonical conflicts in one deploy - fix one, re-verify in GSC, then next.",
        "Do not rewrite all titles in one pass - title tests are per-page, A/B in Google Search Console.",
        "Do not make extreme decisions on 3 clicks - wait for 2 consecutive data windows before re-scoring.",
        "Do not mass-produce new articles - only the 5 evidence-backed ideas in TOP_5_NEW_CONTENT_IDEAS.md qualify.",
        "Do not run multiple affiliate experiments simultaneously - one monetization test at a time.",
        "Do not bulk-edit the 41 legacy persona posts - they are out of scope for P1-GROWTH.",
        "Do not change sitemap.xml or robots.txt automatically.",
        "Do not submit GSC indexing requests in bulk - one URL per week for recovery items.",
        "Do not touch affiliate URLs / UTM parameters during content edits.",
    ]
    lines = ["# Content Do-Not-Do-Yet", "",
             "Guardrails for the first execution cycle (LOW_DATA_WARNING applies).", ""]
    lines += [f"- {d}" for d in dnd]
    lines.append("")
    lines.append(f"Data context: 28d impressions={sum(r['impressions_28d'] for r in scored)}, "
                 f"clicks=3, CTR=0.26%.")
    (out / "CONTENT_DO_NOT_DO_YET.md").write_text("\n".join(lines), encoding="utf-8")

    # ---- First review queue CSV ----
    csv_cols = ["content_id", "title", "url", "current_issue", "recommended_change",
                "evidence", "priority", "risk", "business_value", "review_status"]
    with open(out / "FIRST_CONTENT_REVIEW_QUEUE.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=csv_cols)
        w.writeheader()
        for r in top10:
            w.writerow({
                "content_id": r["content_id"],
                "title": r["_title"],
                "url": r["url"],
                "current_issue": r["recovery_reason"] or r["rule_flags"][0]
                                  if r["rule_flags"] else r["primary_action"],
                "recommended_change": r["primary_action"].replace("_", " ").title(),
                "evidence": f"{r['impressions_28d']} imp / {r['clicks_28d']} clicks / "
                            f"pos {r['avg_position']} / {r['query_count']} queries",
                "priority": r["_tier_p"],
                "risk": "Low" if r["_effort"] == "S" else "Medium" if r["_effort"] == "M" else "High",
                "business_value": "HIGH" if r["business_intent"] in ("VISA", "PAYMENT", "TRANSPORT") else "MEDIUM",
                "review_status": "PENDING",
            })

    # ---- Top 5 commercial pages (aggregated by page) ----
    by_page = defaultdict(lambda: {"queries": 0, "impressions": 0, "positions": [], "intent": "OTHER", "value": "LOW"})
    for c in commercial:
        d = by_page[c["page"]]
        d["queries"] += 1
        d["impressions"] += c["impressions"]
        d["positions"].append(c["position"])
        if c["business_value"] == "HIGH":
            d["value"] = "HIGH"
        if c["business_intent"] in ("VISA", "PAYMENT", "TRANSPORT"):
            d["intent"] = c["business_intent"]
    comm_rows = []
    for page, d in by_page.items():
        avg_pos = sum(d["positions"]) / len(d["positions"])
        comm_rows.append({"page": page, "queries": d["queries"], "impressions": d["impressions"],
                          "avg_position": round(avg_pos, 2), "business_intent": d["intent"],
                          "business_value": d["value"]})
    comm_rows.sort(key=lambda r: (-(1 if r["business_value"] == "HIGH" else 0),
                                  -r["impressions"], -r["queries"], r["avg_position"]))
    top5_comm = comm_rows[:5]
    # affiliate presence per page (read-only scan of rendered markdown)
    def affiliate_presence(page):
        slug = page.rsplit("/", 1)[-1]
        # strict slug match only: exact file or date-prefixed variant, no partial glob
        cands = [c for c in POSTS_DIR.glob("*.md")
                 if c.stem == slug or c.stem.endswith("-" + slug)]
        text = ""
        for c in cands:
            text += c.read_text(encoding="utf-8", errors="ignore")
        found = []
        for brand in ("booking.com", "klook", "aviasales", "nordvpn", "safetywing"):
            if re.search(brand, text, re.I):
                found.append(brand.split(".")[0].capitalize())
        return found or ["NONE"]
    c_lines = ["# Top 5 Commercial Pages", "",
               "From COMMERCIAL_CONTENT_OPPORTUNITIES.md (16 entries aggregated by page). "
               "No affiliate added.", ""]
    c_lines.append("| rank | page | traffic_evidence | search_evidence | affiliate_potential | "
                   "current_affiliate_presence | missing_monetization | recommended_action |")
    c_lines.append("|---|---|---|---|---|---|---|---|")
    for i, r in enumerate(top5_comm, 1):
        c_lines.append(f"| {i} | {r['page']} | {r['impressions']} imp / avg pos {r['avg_position']} | "
                       f"{r['queries']} queries | {'HIGH' if r['business_value'] == 'HIGH' else 'MEDIUM'} | "
                       f"{'; '.join(affiliate_presence(r['page']))} | "
                       f"Commercial framing / product comparison around intent | COMMERCIAL_OPTIMIZATION |")
    c_lines.append("")
    c_lines.append("Affiliate check: Booking / Klook / Aviasales / NordVPN / SafetyWing - read-only scan; no new partner added.")
    (out / "TOP_5_COMMERCIAL_PAGES.md").write_text("\n".join(c_lines), encoding="utf-8")

    # ---- Top 5 new content ideas ----
    def idea_rank(idea):
        score = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(idea["priority"], 1)
        if "NOT indexed" in idea["evidence"]:
            score -= 1
        if idea["business_intent"] in ("VISA", "PAYMENT", "TRANSPORT", "INTERNET"):
            score += 1
        return score
    ranked_ideas = sorted(new_ideas, key=lambda x: (-idea_rank(x), x["rank"]))
    top5_ideas = ranked_ideas[:5]
    n_lines = ["# Top 5 New Content Ideas", "",
               "From NEW_CONTENT_IDEAS.md (14 evidence-backed candidates). "
               "Many candidates have evidence pointing to INDEX_FIX first - new content is the last batch. "
               "No article created.", ""]
    n_lines.append("| rank | topic | target_query | evidence | recommended_format | priority | business_intent |")
    n_lines.append("|---|---|---|---|---|---|---|")
    for i, idea in enumerate(top5_ideas, 1):
        n_lines.append(f"| {i} | {idea['topic']} | {idea['target_query']} | {idea['evidence']} | "
                       f"{idea['recommended_format']} | {idea['priority']} | {idea['business_intent']} |")
    n_lines.append("")
    n_lines.append("Selection rule: query evidence + topic gap + no duplication + business/strategic intent; "
                   "ideas whose evidence is purely 'lands on not-indexed page' lose priority (INDEX_FIX first).")
    (out / "TOP_5_NEW_CONTENT_IDEAS.md").write_text("\n".join(n_lines), encoding="utf-8")

    # ---- console summary ----
    print(f"scored items: {len(scored)}")
    print(f"priority tiers: {dict(Counter(r['_tier_p'] for r in scored))}")
    print(f"top1: {top10[0]['content_id']} score={top10[0]['priority_score']} action={top10[0]['primary_action']}")
    print(f"batches: A={sum(1 for r in scored if r['primary_action'] in ('TECHNICAL_FIX','INDEX_RECOVERY'))} "
          f"B={sum(1 for r in scored if r['primary_action'] in ('TITLE_META_UPDATE','CONTENT_REFRESH','CONTENT_EXPANSION','INTERNAL_LINK','FAQ_EXPANSION'))} "
          f"C={sum(1 for r in scored if r['primary_action'] == 'COMMERCIAL_OPTIMIZATION')} "
          f"D={sum(1 for r in scored if r['primary_action'] == 'NEW_CONTENT')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
