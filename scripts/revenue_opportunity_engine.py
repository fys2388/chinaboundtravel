#!/usr/bin/env python3
"""P1-GROWTH-11: Revenue Opportunity Engine.

Unifies GSC + GA4 + Affiliate + Drive + Content Inventory + Commercial Intent
into a single Revenue Opportunity Score (0-100) per content/page.

Model (transparent, deterministic):
  Traffic Potential        /20
  Commercial Intent        /20
  Affiliate Presence       /15
  Conversion Gap           /15
  SEO Opportunity          /10
  Drive Opportunity        /10
  Execution Ease            /5
  Data Confidence           /5
  TOTAL                    /100

Data Confidence actively down-weights small-sample pages (current site:
sessions=162/28d, affiliate_clicks=0, GSC clicks=3/28d). Revenue stays NULL
(REVENUE_NOT_AVAILABLE) - never fabricated.

Inputs (reports/):
  revenue/AFFILIATE_PARTNER_INVENTORY.csv
  revenue/AFFILIATE_CONTENT_MAP.csv
  revenue/PRE_DRIVE_BASELINE.csv
  seo/CONTENT_SEO_INVENTORY.csv
  seo/CONTENT_OPPORTUNITY_FEED.json
  seo/GROWTH_VALIDATION_COMPARISON.csv

Outputs (reports/revenue/):
  REVENUE_OPPORTUNITY_SCORES.csv
  TOP_20_REVENUE_OPPORTUNITIES.md
  TOP_5_REVENUE_ACTIONS.md
  DRIVE_OPPORTUNITIES.md
  PARTNER_OPPORTUNITY_MATRIX.csv
  REVENUE_FUNNEL_BASELINE.md
  REVENUE_EXPERIMENT_CANDIDATES.md
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

BLOG_ROOT = Path(__file__).resolve().parent.parent
REPORTS_SEO = BLOG_ROOT / "reports" / "seo"
REPORTS_REVENUE = BLOG_ROOT / "reports" / "revenue"
REPORTS_REVENUE.mkdir(parents=True, exist_ok=True)

DRIVE_ACTIVE = True
SESSIONS_28D_TOTAL = 162
PAGEVIEWS_28D_TOTAL = 365
GSC_CLICKS_28D_TOTAL = 3
LOW_DATA_WARNING = ("LOW_DATA_WARNING: 28d 全站 sessions=162 / pageviews=365 / affiliate_clicks=0 / "
                    "GSC clicks=3。样本极小，任何结论只能标记 INSUFFICIENT_SAMPLE，不能宣布成败。")

HIGH_INTENT = {"VISA", "HOTEL", "FLIGHT", "TRAIN", "INTERNET", "ESIM", "VPN", "PAYMENT", "TOUR", "INSURANCE"}
MEDIUM_INTENT = {"CITY", "TRANSPORT", "TRAVEL GUIDE", "FOOD"}


def _num(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Pure scoring functions
# ---------------------------------------------------------------------------
def intent_tier(intent: str) -> str:
    i = (intent or "GENERAL").upper()
    if i in HIGH_INTENT:
        return "HIGH"
    if i in MEDIUM_INTENT:
        return "MEDIUM"
    return "LOW"


def commercial_intent_score(intent: str) -> float:
    t = intent_tier(intent)
    return 20.0 if t == "HIGH" else 12.0 if t == "MEDIUM" else 5.0


def traffic_potential_score(impressions: float, position: float) -> float:
    imp = _num(impressions)
    pos = _num(position)
    if imp <= 0:
        base = 0.0
    elif imp < 10:
        base = 4.0
    elif imp < 50:
        base = 8.0
    elif imp < 100:
        base = 12.0
    elif imp < 300:
        base = 16.0
    else:
        base = 20.0
    bonus = 4.0 if 0 < pos <= 10 else 2.0 if 0 < pos <= 20 else 0.0
    return round(min(20.0, base + bonus), 1)


def affiliate_presence_score(partner_count: int, has_affiliate: bool) -> float:
    if not has_affiliate:
        return 0.0
    base = 8.0
    extra = min(7.0, _num(partner_count) * 1.75)
    return round(min(15.0, base + extra), 1)


def conversion_gap_score(impressions: float, gsc_clicks: float, affiliate_clicks: float,
                         has_affiliate: bool, intent: str) -> float:
    score = 0.0
    imp, clk = _num(impressions), _num(gsc_clicks)
    if imp >= 100 and _num(affiliate_clicks) == 0:
        score += 5.0  # A
    if imp >= 50 and has_affiliate and clk == 0:
        score += 5.0  # B
    if intent_tier(intent) == "HIGH" and not has_affiliate:
        score += 5.0  # C
    if has_affiliate and imp >= 50 and _num(gsc_clicks) / imp < 0.01 and clk > 0:
        score += 3.0  # D (low CTR on commercial page)
    return round(min(15.0, score), 1)


def seo_opportunity_score(feed_score: float) -> float:
    fs = _num(feed_score)
    if fs >= 60:
        return 10.0
    if fs >= 40:
        return 7.0
    if fs >= 20:
        return 4.0
    if fs > 0:
        return 2.0
    return 0.0


def drive_opportunity_score(intent: str, impressions: float) -> float:
    t = intent_tier(intent)
    imp = _num(impressions)
    if t == "HIGH" and imp >= 30:
        return 10.0 if imp >= 100 else 8.0
    if t == "MEDIUM" and imp >= 50:
        return 5.0
    if t == "HIGH":
        return 4.0
    return 1.0


def execution_ease_score(indexed: str, has_affiliate: bool) -> float:
    s = 3.0 if str(indexed).upper() in ("INDEXED", "PASS") else 1.0
    s += 2.0 if has_affiliate else 0.0
    return round(min(5.0, s), 1)


def confidence_factor(impressions: float, gsc_clicks: float, affiliate_clicks: float) -> float:
    imp, clk, aff = _num(impressions), _num(gsc_clicks), _num(affiliate_clicks)
    if clk >= 20 or aff >= 20:
        f = 1.0
    elif imp >= 500:
        f = 0.95
    elif imp >= 100:
        f = 0.85
    elif imp >= 20:
        f = 0.70
    elif imp > 0:
        f = 0.60
    else:
        f = 0.50
    # site-wide small-sample dampener
    if SESSIONS_28D_TOTAL < 500:
        f = round(f * 0.95, 3)
    return f


def compute_score(row: dict) -> dict:
    imp = _num(row.get("impressions_28d"))
    clk = _num(row.get("gsc_clicks_28d"))
    aff = _num(row.get("affiliate_clicks_28d"))
    has_aff = bool(row.get("has_affiliate"))
    intent = row.get("commercial_intent") or row.get("business_intent") or "GENERAL"

    raw = (
        traffic_potential_score(imp, _num(row.get("position_28d"))) +
        commercial_intent_score(intent) +
        affiliate_presence_score(_num(row.get("partner_count")), has_aff) +
        conversion_gap_score(imp, clk, aff, has_aff, intent) +
        seo_opportunity_score(_num(row.get("seo_opportunity_score"))) +
        drive_opportunity_score(intent, imp) +
        execution_ease_score(row.get("indexed_status", ""), has_aff)
    )
    factor = confidence_factor(imp, clk, aff)
    confidence = round(5.0 * factor, 1)
    final = round(raw * (0.55 + 0.45 * factor) + confidence, 1)
    final = min(100.0, final)
    tier = "A" if final >= 80 else "B" if final >= 60 else "C" if final >= 40 else "D"
    return {"raw": round(raw, 1), "confidence": round(factor * 100, 1),
            "confidence_score": confidence, "score": final, "tier": tier}


def primary_action(row: dict, comp: dict) -> str:
    factor = comp["confidence"] / 100.0
    imp = _num(row.get("impressions_28d"))
    has_aff = bool(row.get("has_affiliate"))
    intent = row.get("commercial_intent") or row.get("business_intent") or "GENERAL"
    indexed = str(row.get("indexed_status", "")).upper()
    if factor < 0.5:
        return "MONITOR" if imp == 0 else "MEASURE_MORE"
    # small-sample guard: near-zero impressions cannot support any action
    if imp == 0:
        return "MONITOR"
    if imp < 20 and _num(row.get("gsc_clicks_28d")) == 0:
        return "MEASURE_MORE"
    if intent_tier(intent) == "HIGH" and not has_aff:
        return "AFFILIATE_PLACEMENT"
    if intent_tier(intent) == "HIGH" and has_aff and imp >= 50 and _num(row.get("gsc_clicks_28d")) == 0:
        return "CTA_OPTIMIZATION"
    if imp >= 100 and has_aff:
        return "CONTENT_COMMERCIALIZATION"
    if indexed not in ("INDEXED", "PASS") and imp > 0:
        return "INTERNAL_LINK"
    return "MONITOR"


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
def read_csv(path) -> list:
    if not Path(path).exists():
        return []
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_inputs():
    seo_inv = read_csv(REPORTS_SEO / "CONTENT_SEO_INVENTORY.csv")
    feed = []
    fp = REPORTS_SEO / "CONTENT_OPPORTUNITY_FEED.json"
    if fp.exists():
        feed = json.loads(fp.read_text(encoding="utf-8"))
    aff_map = read_csv(REPORTS_REVENUE / "AFFILIATE_CONTENT_MAP.csv")
    pre = read_csv(REPORTS_REVENUE / "PRE_DRIVE_BASELINE.csv")
    return seo_inv, feed, aff_map, pre


def build_rows(seo_inv, feed, aff_map, pre) -> list:
    feed_by = {f["content_id"]: f for f in feed if f.get("content_id")}
    partners_by = {}
    for r in aff_map:
        cid = r.get("content_id")
        if not cid:
            continue
        partners_by.setdefault(cid, set()).add(r.get("partner", ""))
    pre_by = {}
    for r in pre:
        cid = r.get("content_id")
        if not cid:
            continue
        d = pre_by.setdefault(cid, {"affiliate_clicks_28d": 0.0})
        d["affiliate_clicks_28d"] = max(d["affiliate_clicks_28d"], _num(r.get("affiliate_clicks_28d")))
        d["commercial_intent"] = r.get("commercial_intent") or d.get("commercial_intent", "GENERAL")
        d["gsc_clicks_28d"] = max(d.get("gsc_clicks_28d", 0.0), _num(r.get("gsc_clicks_28d")))
        d["gsc_impressions_28d"] = max(d.get("gsc_impressions_28d", 0.0), _num(r.get("gsc_impressions_28d")))

    rows = []
    for r in seo_inv:
        cid = r.get("content_id")
        if not cid:
            continue
        f = feed_by.get(cid, {})
        p = pre_by.get(cid, {})
        partners = partners_by.get(cid, set())
        row = {
            "content_id": cid,
            "url": r.get("url", ""),
            "title": r.get("title", ""),
            "section": r.get("section", "posts"),
            "sessions": SESSIONS_28D_TOTAL,
            "pageviews": PAGEVIEWS_28D_TOTAL,
            "gsc_impressions": _num(r.get("impressions_28d") or p.get("gsc_impressions_28d")),
            "gsc_clicks": _num(r.get("clicks_28d") or p.get("gsc_clicks_28d")),
            "avg_position": _num(r.get("position_28d")),
            "affiliate_clicks": _num(p.get("affiliate_clicks_28d")),
            "affiliate_clicks_per_1000_sessions": round(
                _num(p.get("affiliate_clicks_28d")) / SESSIONS_28D_TOTAL * 1000.0, 4) if SESSIONS_28D_TOTAL else 0.0,
            "revenue": "NULL",
            "revenue_status": "REVENUE_NOT_AVAILABLE",
            "partner_count": len(partners),
            "has_affiliate": len(partners) > 0,
            "drive_active": DRIVE_ACTIVE,
            "commercial_intent": (p.get("commercial_intent") or f.get("business_intent") or "GENERAL"),
            "indexed_status": r.get("indexed_status") or f.get("index_status", "UNKNOWN"),
            "seo_opportunity_score": _num(f.get("opportunity_score")),
            "query_count": _num(f.get("evidence", {}).get("query_count")) if isinstance(f.get("evidence"), dict) else 0,
            # alias columns used by scoring
            "impressions_28d": _num(r.get("impressions_28d") or p.get("gsc_impressions_28d")),
            "clicks_28d": _num(r.get("clicks_28d") or p.get("gsc_clicks_28d")),
            "gsc_clicks_28d": _num(p.get("gsc_clicks_28d") or r.get("clicks_28d")),
            "position_28d": _num(r.get("position_28d")),
            "affiliate_clicks_28d": _num(p.get("affiliate_clicks_28d")),
            "business_intent": f.get("business_intent", ""),
        }
        rows.append(row)
    return rows

# ---------------------------------------------------------------------------
# Report writers
# ---------------------------------------------------------------------------
def write_csv(path, fieldnames, rows):
    with Path(path).open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def build_scored(rows) -> list:
    scored = []
    for r in rows:
        comp = compute_score(r)
        r2 = dict(r)
        r2.update({
            "revenue_opportunity_score": comp["score"],
            "raw_score": comp["raw"],
            "data_confidence_pct": comp["confidence"],
            "tier": comp["tier"],
            "primary_action": primary_action(r, comp),
        })
        scored.append(r2)
    scored.sort(key=lambda x: (-x["revenue_opportunity_score"], -x["data_confidence_pct"], x["url"]))
    return scored


SCORE_FIELDS = ["content_id", "url", "title", "section", "sessions", "pageviews",
                "gsc_impressions", "gsc_clicks", "avg_position", "affiliate_clicks",
                "affiliate_clicks_per_1000_sessions", "revenue", "revenue_status",
                "partner_count", "has_affiliate", "drive_active", "commercial_intent",
                "indexed_status", "seo_opportunity_score", "query_count",
                "revenue_opportunity_score", "raw_score", "data_confidence_pct", "tier", "primary_action"]


def write_reports(scored: list, generated: str):
    write_csv(REPORTS_REVENUE / "REVENUE_OPPORTUNITY_SCORES.csv", SCORE_FIELDS, scored)

    top20 = scored[:20]
    lines = ["# TOP 20 REVENUE OPPORTUNITIES", "", f"- Generated: {generated}", "",
             "| # | content_id | title | url | score | tier | sessions | impressions | aff clicks | revenue | intent | action | reason |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(top20, 1):
        lines.append(f"| {i} | {r['content_id']} | {r['title'][:45]} | {r['url']} | {r['revenue_opportunity_score']} | "
                     f"{r['tier']} | {r['sessions']} | {int(r['gsc_impressions'])} | {int(r['affiliate_clicks'])} | "
                     f"{r['revenue']} | {r['commercial_intent']} | {r['primary_action']} | "
                     f"conf={r['data_confidence_pct']}% |")
    lines += ["", LOW_DATA_WARNING]
    (REPORTS_REVENUE / "TOP_20_REVENUE_OPPORTUNITIES.md").write_text("\n".join(lines), encoding="utf-8")

    t5 = []
    for r in top20:
        action = r["primary_action"]
        if r["data_confidence_pct"] < 50:
            action = "MEASURE_MORE" if r["gsc_impressions"] > 0 else "MONITOR"
        t5.append({**r, "primary_action": action})
    t5 = t5[:5]
    tl = ["# TOP 5 REVENUE ACTIONS", "", f"- Generated: {generated}", "",
          "- Rule: data confidence < 50% forces MEASURE_MORE / MONITOR (no premature decisions).", "",
          "| # | content_id | title | score | confidence | primary_action | reason |", "|---|---|---|---|---|---|---|"]
    for i, r in enumerate(t5, 1):
        tl.append(f"| {i} | {r['content_id']} | {r['title'][:50]} | {r['revenue_opportunity_score']} | "
                  f"{r['data_confidence_pct']}% | {r['primary_action']} | "
                  f"intent={r['commercial_intent']}, imp={int(r['gsc_impressions'])}, aff={int(r['affiliate_clicks'])} |")
    tl += ["", LOW_DATA_WARNING]
    (REPORTS_REVENUE / "TOP_5_REVENUE_ACTIONS.md").write_text("\n".join(tl), encoding="utf-8")

    dl = ["# DRIVE OPPORTUNITIES (DRIVE-001 RUNNING)", "", f"- Generated: {generated}",
          "- Criteria: high commercial intent + sufficient traffic + currently monetizable.", "",
          "| page | content_id | sessions | intent | affiliate | drive | action |", "|---|---|---|---|---|---|---|"]
    for r in scored:
        if intent_tier(r["commercial_intent"]) != "HIGH" or r["gsc_impressions"] < 20:
            continue
        dl.append(f"| {r['url']} | {r['content_id']} | {r['sessions']} | {r['commercial_intent']} | "
                  f"{'yes' if r['has_affiliate'] else 'no'} | ACTIVE | {r['primary_action']} |")
    dl += ["", LOW_DATA_WARNING]
    (REPORTS_REVENUE / "DRIVE_OPPORTUNITIES.md").write_text("\n".join(dl), encoding="utf-8")

    pm = partner_matrix(scored)
    write_csv(REPORTS_REVENUE / "PARTNER_OPPORTUNITY_MATRIX.csv",
              ["partner", "pages", "sessions", "affiliate_clicks", "impressions",
               "commercial_pages", "clicks_per_1000_sessions", "data_confidence", "opportunity"],
              pm)

    fl = ["# REVENUE FUNNEL BASELINE", "", f"- Generated: {generated}", "",
          "| Stage | Value | Source |", "|---|---|---|",
          f"| sessions (28d) | {SESSIONS_28D_TOTAL} | GA4 |",
          f"| pageviews (28d) | {PAGEVIEWS_28D_TOTAL} | GA4 |",
          "| affiliate_clicks (28d) | 0 | GA4 affiliate_click |",
          "| affiliate_sessions | NOT_AVAILABLE | no affiliate API |",
          "| revenue | NOT_AVAILABLE | no affiliate revenue API |", "",
          "Funnel: sessions -> pageviews -> affiliate_clicks -> affiliate_sessions -> revenue",
          "affiliate_sessions / revenue 当前不可得，明确 NOT_AVAILABLE，不猜测。", "", LOW_DATA_WARNING]
    (REPORTS_REVENUE / "REVENUE_FUNNEL_BASELINE.md").write_text("\n".join(fl), encoding="utf-8")

    el = ["# REVENUE EXPERIMENT CANDIDATES", "", f"- Generated: {generated}", "",
          "| # | Experiment | Status | Notes |", "|---|---|---|---|",
          "| A | CTA placement test | PLANNED | 等 DRIVE-001 满 28d 后再做 |",
          "| B | affiliate placement test | PLANNED | 不批量增加联盟链接 |",
          "| C | commercial content update | PLANNED | 仅基于 TOP_5 单项执行 |",
          "| D | Drive effect | RUNNING | DRIVE-001, 观察至 2026-09-13 |",
          "| E | partner comparison | PLANNED | 需要 affiliate clicks 样本 |", "",
          LOW_DATA_WARNING]
    (REPORTS_REVENUE / "REVENUE_EXPERIMENT_CANDIDATES.md").write_text("\n".join(el), encoding="utf-8")


def partner_matrix(scored: list) -> list:
    """Partner aggregation. Affiliate clicks per page currently 0 site-wide;
    partner-level clicks cannot be split further - keep truthful zeros/NULL."""
    from collections import defaultdict
    by_partner = defaultdict(lambda: {"pages": set(), "impressions": 0.0, "aff_clicks": 0.0,
                                      "commercial": 0, "has": False})
    aff_map = read_csv(REPORTS_REVENUE / "AFFILIATE_CONTENT_MAP.csv")
    scored_by_cid = {r["content_id"]: r for r in scored}
    for a in aff_map:
        cid = a.get("content_id")
        if not cid or cid not in scored_by_cid:
            continue
        d = by_partner[a["partner"]]
        d["pages"].add(cid)
        d["impressions"] += _num(scored_by_cid[cid]["gsc_impressions"])
        d["aff_clicks"] += _num(scored_by_cid[cid]["affiliate_clicks"])
        if intent_tier(scored_by_cid[cid]["commercial_intent"]) == "HIGH":
            d["commercial"] += 1
    rows = []
    for partner, d in sorted(by_partner.items(), key=lambda kv: (-len(kv[1]["pages"]), kv[0])):
        rows.append({
            "partner": partner,
            "pages": len(d["pages"]),
            "sessions": SESSIONS_28D_TOTAL,
            "affiliate_clicks": int(d["aff_clicks"]),
            "impressions": int(d["impressions"]),
            "commercial_pages": d["commercial"],
            "clicks_per_1000_sessions": round(d["aff_clicks"] / SESSIONS_28D_TOTAL * 1000.0, 4),
            "data_confidence": "LOW",
            "opportunity": "MEASURE_MORE",
        })
    return rows


def main():
    seo_inv, feed, aff_map, pre = load_inputs()
    rows = build_rows(seo_inv, feed, aff_map, pre)
    scored = build_scored(rows)
    write_reports(scored, date.today().isoformat())
    print(f"scored={len(scored)} tiers=" +
          ",".join(f"{t}={sum(1 for r in scored if r['tier'] == t)}" for t in "ABCD"))
    for r in scored[:5]:
        print(f"  {r['content_id']} {r['revenue_opportunity_score']:5.1f} {r['tier']} "
              f"conf={r['data_confidence_pct']}% {r['primary_action']} {r['commercial_intent']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
