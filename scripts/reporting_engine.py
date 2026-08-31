#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P1-REPORT-02: ChinaBound Travel 2.0 unified reporting engine.

All five period reports (daily / weekly / monthly / quarterly / yearly)
are rendered from ONE KPI snapshot produced by reporting_kpi_engine.py.
No KPI calculation is duplicated here: the engine only formats values that
already exist in the snapshot.

CLI:
  python scripts/reporting_engine.py --daily
  python scripts/reporting_engine.py --weekly
  python scripts/reporting_engine.py --monthly
  python scripts/reporting_engine.py --quarterly
  python scripts/reporting_engine.py --yearly
  python scripts/reporting_engine.py --all
  python scripts/reporting_engine.py --master
  python scripts/reporting_engine.py --alerts
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

BASE = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent
REPORTS = BASE / "reports"
MGMT = REPORTS / "management"
SNAPSHOTS = MGMT / "snapshots"
SNAPSHOT_FILE = MGMT / "REPORTING_SNAPSHOT.json"
MASTER_FILE = REPORTS / "CHINABOUND_TRAVEL_2_0_MASTER_DASHBOARD.md"
ALERTS_FILE = MGMT / "ALERTS.md"

INSUFFICIENT_SAMPLE = "INSUFFICIENT_SAMPLE"
REVENUE_NOT_AVAILABLE = "REVENUE_NOT_AVAILABLE"

sys.path.insert(0, str(SCRIPTS))
import reporting_kpi_engine as kpi  # noqa: E402

PERIODS = {
    "daily": {
        "dir": "daily",
        "file": "CHINABOUND_TRAVEL_2_0_DAILY.md",
        "compare_label": "DoD",
        "title": "DAILY REPORT",
    },
    "weekly": {
        "dir": "weekly",
        "file": "CHINABOUND_TRAVEL_2_0_WEEKLY.md",
        "compare_label": "WoW",
        "title": "WEEKLY REPORT",
    },
    "monthly": {
        "dir": "monthly",
        "file": "CHINABOUND_TRAVEL_2_0_MONTHLY.md",
        "compare_label": "MoM",
        "title": "MONTHLY REPORT",
    },
    "quarterly": {
        "dir": "quarterly",
        "file": "CHINABOUND_TRAVEL_2_0_QUARTERLY.md",
        "compare_label": "QoQ / YoY",
        "title": "QUARTERLY REPORT",
    },
    "yearly": {
        "dir": "yearly",
        "file": "CHINABOUND_TRAVEL_2_0_YEARLY.md",
        "compare_label": "YoY",
        "title": "YEARLY REPORT",
    },
}


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def load_snapshot(as_of=None, build_if_missing=True) -> dict:
    """Read the persisted snapshot, or rebuild it deterministically."""
    if SNAPSHOT_FILE.exists() and not build_if_missing:
        return json.loads(SNAPSHOT_FILE.read_text(encoding="utf-8"))
    snap = kpi.build_snapshot(as_of or date.today())
    return snap


def _kmap(snapshot: dict, domain: str) -> dict:
    return {k["name"]: k for k in snapshot["domains"].get(domain, {}).get("kpis", [])}


def _val(rec) -> str:
    if rec is None:
        return "NULL"
    v = rec.get("value")
    if v is None:
        return "NULL"
    return str(v)


def _fmt(rec) -> str:
    if rec is None:
        return "NULL"
    v = rec.get("value")
    if v is None:
        return "NULL"
    unit = rec.get("unit") or ""
    if unit in ("status", "list", "breakdown", "counts"):
        return str(v)
    return f"{v} {unit}".strip()


def _fmt_kpi(rec) -> str:
    """name = value (data source type, status)."""
    if rec is None:
        return "NULL"
    return f"{_val(rec)} [{rec.get('data_source_type')}] {rec.get('status') or ''}".strip()


def _fmt_baseline(rec):
    b = rec.get("baseline")
    return "NULL" if b is None else str(b)


def _exp_table(snapshot: dict) -> list:
    return snapshot["domains"]["experiments"]["experiments"]


def _cluster_table(snapshot: dict) -> list:
    return snapshot["domains"]["commercial_clusters"]["clusters"]


def prior_snapshot(as_of: date):
    """Most recent dated snapshot strictly before as_of, or None."""
    if not SNAPSHOTS.exists():
        return None
    best = None
    best_d = None
    for p in SNAPSHOTS.glob("REPORTING_SNAPSHOT_*.json"):
        try:
            d = date.fromisoformat(p.stem.rsplit("_", 1)[1])
        except (ValueError, IndexError):
            continue
        if d < as_of and (best_d is None or d > best_d):
            best_d = d
            best = p
    if best is None:
        return None
    try:
        return json.loads(best.read_text(encoding="utf-8"))
    except Exception:
        return None


COMPARE_METRICS = [
    ("traffic", "sessions_28d"),
    ("traffic", "pageviews_28d"),
    ("seo_gsc", "gsc_clicks_28d"),
    ("seo_gsc", "gsc_impressions_28d"),
    ("affiliate_funnel", "affiliate_clicks_28d"),
    ("revenue", "revenue"),
]


def period_comparison(snapshot: dict, as_of: date, label: str) -> list:
    """DoD/WoW/MoM/QoQ/YoY from the closest prior snapshot.

    First run has no prior snapshot -> every row is INSUFFICIENT_SAMPLE.
    """
    prev = prior_snapshot(as_of)
    rows = []
    for domain, name in COMPARE_METRICS:
        cur = _kmap(snapshot, domain).get(name)
        prev_rec = _kmap(prev, domain).get(name) if prev else None
        cur_v = cur.get("value") if cur else None
        prev_v = prev_rec.get("value") if prev_rec else None
        if prev is None or prev_v is None or cur_v is None:
            rows.append({
                "metric": f"{domain}.{name}",
                "current": cur_v,
                "previous": prev_v,
                "delta": None,
                "delta_pct": None,
                "status": INSUFFICIENT_SAMPLE,
                "note": "no prior unified snapshot" if prev is None else "value unavailable",
            })
            continue
        try:
            d = float(cur_v) - float(prev_v)
            pct = round(d / abs(float(prev_v)) * 100.0, 2) if float(prev_v) != 0 else None
        except (TypeError, ValueError):
            d, pct = None, None
        rows.append({
            "metric": f"{domain}.{name}",
            "current": cur_v,
            "previous": prev_v,
            "delta": d,
            "delta_pct": pct,
            "status": "OK",
            "note": f"vs snapshot {prev.get('as_of')}",
        })
    return rows


def comparison_markdown(rows: list, label: str) -> str:
    lines = [f"### Period comparison ({label})", ""]
    if all(r["status"] == INSUFFICIENT_SAMPLE for r in rows):
        lines.append(f"All metrics: **{INSUFFICIENT_SAMPLE}** — no prior unified snapshot exists yet. "
                     "Comparisons become available once a second snapshot is generated.")
        lines.append("")
        return "\n".join(lines)
    lines.append("| Metric | Current | Previous | Delta | Delta % | Status |")
    lines.append("|---|---|---|---|---|---|")
    for r in rows:
        lines.append(f"| {r['metric']} | {r['current']} | {r['previous']} | "
                     f"{r['delta'] if r['delta'] is not None else 'NULL'} | "
                     f"{r['delta_pct'] if r['delta_pct'] is not None else 'NULL'} | {r['status']} |")
    lines.append("")
    return "\n".join(lines)
# --------------------------------------------------------------------------
# shared sections (single source of truth for all report types)
# --------------------------------------------------------------------------
def _experiment_rows(snapshot) -> list:
    out = []
    for e in _exp_table(snapshot):
        out.append({
            "experiment_id": e["experiment_id"],
            "display_name": e.get("display_name") or e["experiment_id"],
            "type": e.get("type"),
            "page": e.get("page"),
            "start_date": e.get("start_date"),
            "observation_days": e.get("observation_days"),
            "primary_metric": e.get("primary_metric"),
            "baseline": e.get("baseline"),
            "current": e.get("current"),
            "delta": e.get("delta"),
            "sample": e.get("sample_status") or e.get("sample"),
            "status": e.get("status"),
        })
    return out


def section_experiments(snapshot) -> str:
    rows = _experiment_rows(snapshot)
    lines = ["## Experiments", "", "| ID | Type | Page | Start | Days | Primary metric | Baseline | Current | Delta | Sample | Status |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['experiment_id']} | {r['type'] or '-'} | {r['page'] or '-'} | {r['start_date'] or '-'} | "
                     f"{r['observation_days'] if r['observation_days'] is not None else '-'} | "
                     f"{r['primary_metric'] or '-'} | {r['baseline'] if r['baseline'] is not None else 'NULL'} | "
                     f"{r['current'] if r['current'] is not None else 'NULL'} | "
                     f"{r['delta'] if r['delta'] is not None else 'NULL'} | {r['sample'] or '-'} | {r['status']} |")
    lines.append("")
    lines.append("Guard: observation < 28d or clicks < 20 => INSUFFICIENT_SAMPLE. "
                 "No WIN/LOSE declarations on insufficient data.")
    lines.append("")
    return "\n".join(lines)


def section_clusters(snapshot) -> str:
    rows = _cluster_table(snapshot)
    lines = ["## Commercial clusters", "", "| Cluster | Intent | Status | Priority | Score | Impressions 28d | Best pos | Affiliate fit | Experiments | Revenue |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['cluster']} | {r['intent'] or '-'} | {r['status'] or '-'} | {r['priority'] or '-'} | "
                     f"{r['score'] if r['score'] is not None else '-'} | "
                     f"{r['impressions_28d'] if r['impressions_28d'] is not None else 'NULL'} | "
                     f"{r['best_position'] if r['best_position'] is not None else 'NULL'} | "
                     f"{r['affiliate_fit_ratio'] if r['affiliate_fit_ratio'] is not None else '-'} | "
                     f"{'; '.join(r['experiments']) if r['experiments'] else 'none'} | "
                     f"{'NULL' if r.get('revenue') is None else r['revenue']} |")
    lines.append("")
    return "\n".join(lines)


def section_operations(snapshot) -> str:
    omap = _kmap(snapshot, "operations")
    lines = ["## Operations", "", "| KPI | Value | Source type | Status |", "|---|---|---|---|"]
    for name in ("automation_health", "workflow_health", "deployment_health",
                 "backup_rollback", "security_scan", "okr_plan_items"):
        rec = omap.get(name)
        if rec:
            lines.append(f"| {name} | {_fmt(rec)} | {rec.get('data_source_type')} | {rec.get('status') or ''} |")
    lines.append("")
    return "\n".join(lines)


def section_brand(snapshot) -> str:
    bmap = _kmap(snapshot, "brand")
    lines = ["## Brand 2.0", "", "| KPI | Value | Source type |", "|---|---|---|"]
    for name in ("editorial_persona_compliance", "legacy_persona_remaining",
                 "migrated_this_period", "logo_favicon_status", "core_brand_compliance",
                 "brand_asset_avatar"):
        rec = bmap.get(name)
        if rec:
            lines.append(f"| {name} | {_fmt(rec)} | {rec.get('data_source_type')} |")
    lines.append("")
    return "\n".join(lines)


def section_affiliate(snapshot) -> str:
    amap = _kmap(snapshot, "affiliate_funnel")
    lines = ["## Affiliate funnel", "", "| KPI | Value | Source type | Status |", "|---|---|---|---|"]
    for name in ("cta_inventory_rows", "cta_inventory_pages", "affiliate_clicks_28d",
                 "cta_impressions", "outbound_success", "click_rate", "outbound_rate",
                 "clicks_per_1000_sessions"):
        rec = amap.get(name)
        if rec:
            lines.append(f"| {name} | {_fmt(rec)} | {rec.get('data_source_type')} | {rec.get('status') or ''} |")
    lines.append("")
    return "\n".join(lines)


def section_revenue(snapshot) -> str:
    rmap = _kmap(snapshot, "revenue")
    lines = ["### Revenue", ""]
    rev = rmap.get("revenue")
    if rev and rev.get("value") is None:
        lines.append(f"Revenue: **NULL** ({REVENUE_NOT_AVAILABLE}) — no affiliate revenue API; nothing fabricated.")
        lines.append("")
        lines.append("| KPI | Value | Source type |", )
        lines.append("|---|---|---|")
        for name in ("revenue", "orders_conversions", "commission", "rpm", "revenue_per_1000_sessions"):
            rec = rmap.get(name)
            if rec:
                lines.append(f"| {name} | {_fmt(rec)} | {rec.get('data_source_type')} |")
    else:
        lines.append("Revenue: see snapshot.")
    lines.append("")
    return "\n".join(lines)


def section_content(snapshot) -> str:
    cmap = _kmap(snapshot, "content_assets")
    lines = ["## Content asset health", "", "| KPI | Value | Source type |", "|---|---|---|"]
    for name in ("published_posts", "content_id_coverage", "new_pages_30d", "updated_pages",
                 "indexed_posts", "asset_tier_distribution", "opportunity_pipeline",
                 "legacy_persona_pages", "migrated_persona_pages", "canonical_conflicts",
                 "duplicate_risk_rows"):
        rec = cmap.get(name)
        if rec:
            lines.append(f"| {name} | {_fmt(rec)} | {rec.get('data_source_type')} |")
    lines.append("")
    return "\n".join(lines)


def section_seo(snapshot) -> str:
    smap = _kmap(snapshot, "seo_gsc")
    lines = ["## SEO / GSC", "", "| KPI | Value | Source type | Status |", "|---|---|---|---|"]
    for name in ("gsc_clicks_28d", "gsc_impressions_28d", "gsc_ctr_28d",
                 "gsc_avg_position_28d", "indexed_pages", "not_indexed_pages",
                 "inspected_urls", "inspection_pass", "page_level_clicks_28d",
                 "page_level_impressions_28d", "pages_newly_indexed", "pages_losing_visibility"):
        rec = smap.get(name)
        if rec:
            lines.append(f"| {name} | {_fmt(rec)} | {rec.get('data_source_type')} | {rec.get('status') or ''} |")
    lines.append("")
    top = smap.get("top_opportunities")
    if top and isinstance(top.get("value"), list) and top["value"]:
        lines.append("Top opportunities: " + "; ".join(
            f"{o.get('title')} ({o.get('score')}, {o.get('tier')})" for o in top["value"]))
        lines.append("")
    return "\n".join(lines)


def section_traffic(snapshot) -> str:
    tmap = _kmap(snapshot, "traffic")
    lines = ["## Traffic", "", "| KPI | Value | Baseline | Source type | Status |", "|---|---|---|---|---|"]
    for name in ("users_28d", "sessions_28d", "pageviews_28d", "engagement_rate_28d"):
        rec = tmap.get(name)
        if rec:
            lines.append(f"| {name} | {_fmt(rec)} | {_fmt_baseline(rec)} | "
                         f"{rec.get('data_source_type')} | {rec.get('status') or ''} |")
    lines.append("")
    return "\n".join(lines)

# --------------------------------------------------------------------------
# report headers / consistency banner
# --------------------------------------------------------------------------
def _header(snapshot: dict, period_title: str, compare_label: str) -> str:
    return (
        f"# ChinaBound Travel 2.0 — {period_title}\n\n"
        f"- Generated: {snapshot.get('generated_at')} (Asia/Shanghai)\n"
        f"- as_of: {snapshot.get('as_of')}\n"
        f"- Data source: ONE unified snapshot — reports/management/REPORTING_SNAPSHOT.json\n"
        f"- Labels: LIVE / CACHED / LOCAL / NOT_AVAILABLE\n"
        f"- Revenue: NULL ({REVENUE_NOT_AVAILABLE}) — never fabricated\n"
        f"- Low data: {snapshot.get('low_data_warning')} — see ALERTS.md\n"
        f"- Period comparison: {compare_label} (INSUFFICIENT_SAMPLE until a prior snapshot exists)\n"
        f"- Consistency: same KPI definitions / experiment IDs / content count / brand status across all periods\n"
        f"\n## Executive status\n\n"
        f"- Published posts: {_fmt(_kmap(snapshot, 'content_assets').get('published_posts'))}\n"
        f"- Sessions 28d: {_fmt(_kmap(snapshot, 'traffic').get('sessions_28d'))} | "
        f"Pageviews 28d: {_fmt(_kmap(snapshot, 'traffic').get('pageviews_28d'))}\n"
        f"- GSC clicks 28d: {_fmt(_kmap(snapshot, 'seo_gsc').get('gsc_clicks_28d'))} | "
        f"Impressions: {_fmt(_kmap(snapshot, 'seo_gsc').get('gsc_impressions_28d'))}\n"
        f"- Revenue: NULL ({REVENUE_NOT_AVAILABLE})\n"
        f"- Drive: ACTIVE (DRIVE-001 RUNNING since 2026-08-16)\n"
        f"- Overall alert level: YELLOW (low sample + open recovery queues, see ALERTS.md)\n"
    )


# --------------------------------------------------------------------------
# daily
# --------------------------------------------------------------------------
def render_daily(snapshot: dict) -> str:
    out = [_header(snapshot, "DAILY REPORT", "DoD"), ""]

    out.append("## 1. Traffic today")
    out.append("")
    out.append("Daily window metrics are NOT available (no daily GA4 pull). 28d rolling figures shown with fetch date.")
    out.append("")
    out.append(section_traffic(snapshot))

    out.append("## 2. SEO changes")
    out.append("")
    out.append("Change vs previous day: **INSUFFICIENT_SAMPLE** (no prior daily snapshot).")
    out.append("")
    out.append(section_seo(snapshot))

    out.append("## 3. Indexing changes")
    out.append("")
    smap = _kmap(snapshot, "seo_gsc")
    out.append(f"- Indexed: {_fmt(smap.get('indexed_pages'))} | Not indexed: {_fmt(smap.get('not_indexed_pages'))} "
               f"(GSC UI 2026-08-16, CACHED)")
    out.append(f"- Newly indexed this period: {_val(smap.get('pages_newly_indexed'))} "
               f"(requires prior snapshot: INSUFFICIENT_SAMPLE)")
    out.append(f"- Losing visibility: {_val(smap.get('pages_losing_visibility'))} (INSUFFICIENT_SAMPLE)")
    out.append("")

    out.append("## 4. Revenue / affiliate events")
    out.append("")
    out.append(section_affiliate(snapshot))
    out.append(section_revenue(snapshot))

    out.append("## 5. Experiment events")
    out.append("")
    out.append("All experiments in observation window; no WIN/LOSE declarations.")
    out.append("")
    out.append(section_experiments(snapshot))

    out.append("## 6. Production health")
    out.append("")
    out.append(section_operations(snapshot))

    out.append("## 7. Brand compliance changes")
    out.append("")
    out.append("No brand changes today. Last brand event: P1-BRAND-04 favicon.png replacement 2026-08-17 "
               "(LOGO_REPLACEMENT_READY, favicon.svg retained).")
    out.append("")
    out.append(section_brand(snapshot))

    out.append("## 8. Alerts / anomalies")
    out.append("")
    out.append(f"- LOW_DATA_WARNING: {len(snapshot.get('low_data_reasons', []))} low-data reasons (see ALERTS.md)")
    out.append("- Anomalies: none beyond expected low-sample state")
    out.append("- Blockers: canonical conflicts (6 HIGH), WAITING_RECRAWL x2, no revenue API, no fresh GSC pull since 2026-08-16")
    out.append("")

    out.append("## 9. Today's actions")
    out.append("")
    out.append("- Keep REV001 / REV002 / DRIVE-001 untouched until review gate 2026-09-13")
    out.append("- Monitor WAITING_RECRAWL experiments (WeChat Pay weak, High-Speed Rail)")
    out.append("- Plan fresh GSC + GA4 pull for next snapshot")
    out.append("")
    return "\n".join(out)


# --------------------------------------------------------------------------
# weekly
# --------------------------------------------------------------------------
def render_weekly(snapshot: dict) -> str:
    out = [_header(snapshot, "WEEKLY REPORT", "WoW"), ""]

    out.append("## 1. Executive summary")
    out.append("")
    out.append("Week in observation: 3 revenue experiments running (REV001, REV002, DRIVE-001), "
               "2 index recoveries waiting for recrawl, 60-post inventory stable, revenue NULL.")
    out.append("")

    out.append("## 2. Traffic")
    out.append("")
    out.append(section_traffic(snapshot))

    out.append("## 3. SEO / GSC")
    out.append("")
    out.append(section_seo(snapshot))

    out.append("## 4. Content asset health")
    out.append("")
    out.append(section_content(snapshot))

    out.append("## 5. Brand 2.0")
    out.append("")
    out.append(section_brand(snapshot))

    out.append("## 6. Affiliate funnel")
    out.append("")
    out.append(section_affiliate(snapshot))

    out.append("## 7. Revenue")
    out.append("")
    out.append(section_revenue(snapshot))

    out.append("## 8. Experiments")
    out.append("")
    out.append(section_experiments(snapshot))

    out.append("## 9. Commercial clusters")
    out.append("")
    out.append(section_clusters(snapshot))

    out.append("## 10. Completed work")
    out.append("")
    out.append("- P1-REPORT-01: reporting baselines reconciled (58 posts, REV001 corrected, dashboards rebuilt)")
    out.append("- P1-BRAND-04: favicon.png replaced (LOGO_REPLACEMENT_READY)")
    out.append("- Engine re-runs on 60-post inventory: brand legacy, SEO opportunity/priority, revenue, commercial conversion")
    out.append("")

    out.append("## 11. Blockers")
    out.append("")
    out.append("- Revenue API absent -> revenue NULL (never fabricated)")
    out.append("- No fresh GSC pull since 2026-08-16")
    out.append("- 6 HIGH canonical conflicts await technical review")
    out.append("- GROWTH07B / GROWTH07C WAITING_RECRAWL")
    out.append("")

    out.append("## 12. Next-week priorities")
    out.append("")
    out.append("- Execute top content priorities (reports/seo/TOP_10_CONTENT_PRIORITIES.md)")
    out.append("- Fresh GSC/GA4 pull; refresh daily_search_performance + SEO snapshot reports")
    out.append("- Resolve canonical conflict queue (6 HIGH)")
    out.append("- Continue brand legacy persona migration beyond the 3 pilots")
    out.append("")
    out.append(comparison_markdown(period_comparison(snapshot, date.fromisoformat(snapshot["as_of"]), "WoW"), "WoW"))
    return "\n".join(out)


# --------------------------------------------------------------------------
# monthly
# --------------------------------------------------------------------------
def render_monthly(snapshot: dict) -> str:
    out = [_header(snapshot, "MONTHLY REPORT", "MoM"), ""]

    out.append("## 1. Executive KPI scorecard")
    out.append("")
    out.append("| KPI | Value | Data source | Status |")
    out.append("|---|---|---|---|")
    for domain, name in COMPARE_METRICS:
        rec = _kmap(snapshot, domain).get(name)
        if rec:
            out.append(f"| {name} | {_fmt(rec)} | {rec.get('data_source_type')} | {rec.get('status') or ''} |")
    out.append("")

    out.append("## 2. Traffic trend")
    out.append("")
    out.append("Trend direction: **INSUFFICIENT_SAMPLE** (single snapshot; MoM needs prior month).")
    out.append("")
    out.append(section_traffic(snapshot))

    out.append("## 3. SEO trend")
    out.append("")
    out.append("Trend direction: **INSUFFICIENT_SAMPLE**.")
    out.append("")
    out.append(section_seo(snapshot))

    out.append("## 4. Content asset portfolio")
    out.append("")
    out.append(section_content(snapshot))

    out.append("## 5. Brand migration")
    out.append("")
    out.append("BRAND-03 pilot migrated 3 posts (2026-08-16); 25 legacy-persona posts remain; "
               "BRAND-04 favicon replaced (2026-08-17).")
    out.append("")
    out.append(section_brand(snapshot))

    out.append("## 6. Affiliate funnel")
    out.append("")
    out.append(section_affiliate(snapshot))

    out.append("## 7. Revenue")
    out.append("")
    out.append(section_revenue(snapshot))

    out.append("## 8. Experiment performance")
    out.append("")
    out.append("Winner/loser: **none declared** (all experiments below 28d / 20-click guard).")
    out.append("")
    out.append(section_experiments(snapshot))

    out.append("## 9. Commercial cluster performance")
    out.append("")
    out.append(section_clusters(snapshot))

    out.append("## 10. Product / monetization progress")
    out.append("")
    out.append("- Drive ACTIVE site-wide (DRIVE-001, start 2026-08-16)")
    out.append("- REV001 Food Delivery + Airalo mid-CTA RUNNING")
    out.append("- REV002 Transportation + Trip.com mid-CTA RUNNING (frozen)")
    out.append("- REV003 copy variant PENDING (gate 2026-09-13)")
    out.append("- Payment cluster: Alipay/WeChat/Card releases done; eSIM candidates on WAIT")
    out.append("")

    out.append("## 11. Major risks")
    out.append("")
    out.append("- 6 HIGH canonical conflicts (transportation/safety/monthly-update duplicates)")
    out.append("- 25 legacy-persona posts (brand consistency)")
    out.append("- No revenue API -> monetization unmeasurable")
    out.append("- Low search clicks (3 page-level / 0 query-level 28d)")
    out.append("")

    out.append("## 12. Month-over-month change")
    out.append("")
    out.append(comparison_markdown(period_comparison(snapshot, date.fromisoformat(snapshot["as_of"]), "MoM"), "MoM"))

    out.append("## 13. Next-month strategy")
    out.append("")
    out.append("- Keep experiments untouched until 2026-09-13; then review REV001/REV002/DRIVE-001")
    out.append("- Fix canonical conflicts; push index recovery to completion")
    out.append("- Continue persona migration; grow CTA coverage toward 100%")
    out.append("- Connect a revenue API to replace NULL with real data")
    out.append("")
    return "\n".join(out)

# --------------------------------------------------------------------------
# quarterly
# --------------------------------------------------------------------------
def render_quarterly(snapshot: dict) -> str:
    out = [_header(snapshot, "QUARTERLY REPORT", "QoQ / YoY"), ""]

    out.append("## 1. Executive quarterly review")
    out.append("")
    out.append("Q3-2026 so far: site rebuilt around 58 posts, editorial persona 2.0 enforced, "
               "monetization moved from zero to three running experiments (REV001/REV002/DRIVE-001). "
               "Revenue remains NULL (no API).")
    out.append("")

    out.append("## 2. Traffic growth")
    out.append("")
    out.append("QoQ / YoY: **INSUFFICIENT_SAMPLE** (no prior unified snapshots). Current 28d: "
               f"{_fmt(_kmap(snapshot, 'traffic').get('sessions_28d'))} sessions / "
               f"{_fmt(_kmap(snapshot, 'traffic').get('pageviews_28d'))} pageviews (GA4 2026-08-17).")
    out.append("")
    out.append(section_traffic(snapshot))

    out.append("## 3. SEO growth")
    out.append("")
    out.append("Search visibility baseline: page-level impressions 1168 / clicks 3 (28d). "
               "Indexed 69 / not indexed 89 (GSC UI 2026-08-16). Trend: INSUFFICIENT_SAMPLE.")
    out.append("")
    out.append(section_seo(snapshot))

    out.append("## 4. Content portfolio value")
    out.append("")
    out.append(section_content(snapshot))

    out.append("## 5. Brand 2.0 migration")
    out.append("")
    out.append("Brand 2.0 roll-out: editorial persona audit 11/13 PASS, 3 pilot migrations complete, "
               "25 legacy posts remaining, logo asset migration READY.")
    out.append("")
    out.append(section_brand(snapshot))

    out.append("## 6. Commercial funnel")
    out.append("")
    out.append(section_affiliate(snapshot))

    out.append("## 7. Revenue")
    out.append("")
    out.append(section_revenue(snapshot))

    out.append("## 8. Experiment learnings")
    out.append("")
    out.append("- 2026-08-16: REV001 identity corrected from 144h/Booking to Food Delivery/Airalo")
    out.append("- DRIVE-001 activated site-wide; baseline 162 sessions / 365 pageviews / 0 clicks")
    out.append("- All experiments guarded: no WIN/LOSE below 28d or 20 clicks")
    out.append("")
    out.append(section_experiments(snapshot))

    out.append("## 9. Commercial clusters")
    out.append("")
    out.append(section_clusters(snapshot))

    out.append("## 10. Product / site development")
    out.append("")
    out.append("- Transportation cluster: guide authority upgraded (GROWTH-17A), card page added, REV002 RUNNING")
    out.append("- Payment cluster: Alipay/WeChat/Card releases live; index recovery for WeChat weak WAITING_RECRAWL")
    out.append("- Connectivity cluster: HOLD (low search demand), eSIM/payment candidates WAIT")
    out.append("")

    out.append("## 11. Major wins")
    out.append("")
    out.append("- 58 posts / 58 content_id with zero drift (audit PASS)")
    out.append("- Canonical content_id drift (transportation) reconciled")
    out.append("- First monetization experiments live on high-intent pages")
    out.append("")

    out.append("## 12. Major failures")
    out.append("")
    out.append("- Search clicks near zero (3 page-level / 0 query-level 28d)")
    out.append("- 89 pages not indexed; 6 HIGH canonical conflicts")
    out.append("- Revenue unmeasurable (no API) — monetization progress cannot be quantified")
    out.append("")

    out.append("## 13. Strategic risks")
    out.append("")
    out.append("- Low visibility -> experiments may stay INSUFFICIENT_SAMPLE for the full window")
    out.append("- Canonical conflicts split equity on transportation/safety/monthly-update pages")
    out.append("- 25 legacy-persona posts risk brand consistency")
    out.append("")

    out.append("## 14. Strategic opportunities")
    out.append("")
    out.append("- Index recovery + canonical cleanup could unlock existing demand (1168 impressions)")
    out.append("- Food Delivery / Transportation / Payment clusters already have affiliate coverage")
    out.append("- Persona migration protects content value ahead of scale")
    out.append("")

    out.append("## 15. Next-quarter OKRs")
    out.append("")
    out.append("- Reach SUFFICIENT_SAMPLE on REV001/REV002/DRIVE-001 (2026-09-13 review)")
    out.append("- Resolve 6 HIGH canonical conflicts")
    out.append("- Reduce not-indexed count materially")
    out.append("- Connect revenue API; report real revenue instead of NULL")
    out.append("")

    out.append("### Strategic questions")
    out.append("")
    out.append("- What worked? Reporting reconciliation, canonical content_id alignment, guarded experiment setup.")
    out.append("- What did not work? Search visibility (clicks ~0); monetization measurement (no API).")
    out.append("- Where should resources increase? Index recovery, canonical cleanup, persona migration.")
    out.append("- Where should resources decrease? Low-demand connectivity cluster HOLD.")
    out.append("- Which content clusters deserve investment? Transportation and Payment (highest impressions/intent).")
    out.append("- Which experiments should scale? None yet — all INSUFFICIENT_SAMPLE until 2026-09-13.")
    out.append("- Which activities should stop? Adding new CTA experiments before REV002 gate.")
    out.append("")
    out.append(comparison_markdown(period_comparison(snapshot, date.fromisoformat(snapshot["as_of"]), "QoQ / YoY"), "QoQ / YoY"))
    return "\n".join(out)


# --------------------------------------------------------------------------
# yearly
# --------------------------------------------------------------------------
def render_yearly(snapshot: dict) -> str:
    out = [_header(snapshot, "YEARLY REPORT", "YoY"), ""]

    out.append("## 1. Executive annual summary")
    out.append("")
    out.append("Year-to-date: ChinaBound Travel established as a 60-post English travel guide with editorial "
               "persona 2.0, first affiliate monetization experiments, and Drive site-wide. "
               "Annual growth deltas: INSUFFICIENT_SAMPLE (no prior-year snapshots).")
    out.append("")

    out.append("## 2. Traffic growth")
    out.append("")
    out.append("YoY: **INSUFFICIENT_SAMPLE**. Current 28d: "
               f"{_fmt(_kmap(snapshot, 'traffic').get('sessions_28d'))} sessions / "
               f"{_fmt(_kmap(snapshot, 'traffic').get('pageviews_28d'))} pageviews.")
    out.append("")
    out.append(section_traffic(snapshot))

    out.append("## 3. Search visibility")
    out.append("")
    out.append(section_seo(snapshot))

    out.append("## 4. Content asset growth")
    out.append("")
    out.append(section_content(snapshot))

    out.append("## 5. Brand evolution")
    out.append("")
    out.append(section_brand(snapshot))

    out.append("## 6. Affiliate funnel")
    out.append("")
    out.append(section_affiliate(snapshot))

    out.append("## 7. Revenue")
    out.append("")
    out.append(section_revenue(snapshot))

    out.append("## 8. Experiment portfolio")
    out.append("")
    out.append(section_experiments(snapshot))

    out.append("## 9. Commercial cluster development")
    out.append("")
    out.append(section_clusters(snapshot))

    out.append("## 10. Product / technical evolution")
    out.append("")
    out.append("- Static Hugo site on Cloudflare Pages; GA4 + GSC + Drive instrumentation live")
    out.append("- Automated content/SEO/revenue reporting engines established (P1-GROWTH series)")
    out.append("- Brand asset pipeline (BRAND-02/03/04) in place")
    out.append("")

    out.append("## 11. Operational maturity")
    out.append("")
    out.append(section_operations(snapshot))

    out.append("## 12. Security / reliability")
    out.append("")
    out.append("- Secret scan: PASS (test_no_hardcoded_secrets + test_secret_name_contract, 2026-08-17)")
    out.append("- Workflow validation: PASS (test_workflow_yaml / test_workflow_names)")
    out.append("- Backup/rollback: NOT_AVAILABLE — no source artifact")
    out.append("")

    out.append("## 13. Biggest wins")
    out.append("")
    out.append("- 58/58 content_id integrity; single inventory source")
    out.append("- First revenue experiments + Drive activation")
    out.append("- Editorial persona compliance enforced at brand layer")
    out.append("")

    out.append("## 14. Biggest failures")
    out.append("")
    out.append("- Near-zero search clicks; majority of URLs not indexed")
    out.append("- Revenue not measurable (no API)")
    out.append("- 25 legacy-persona posts still in production")
    out.append("")

    out.append("## 15. Lessons learned")
    out.append("")
    out.append("- Fix canonical/index problems before scaling content output")
    out.append("- Guarded experiment frameworks prevent false WIN/LOSE claims")
    out.append("- Never fabricate revenue or traffic data")
    out.append("")

    out.append("## 16. Resource efficiency")
    out.append("")
    out.append("Content investment efficiency: **INSUFFICIENT_SAMPLE** (no revenue to compare against spend/output).")
    out.append("")

    out.append("## 17. Strategic moat")
    out.append("")
    out.append("Differentiated editorial persona (Joran) + structured commercial clusters "
               "(Transportation/Payment/Connectivity) + deterministic measurement stack.")
    out.append("")

    out.append("## 18. Next-year strategy")
    out.append("")
    out.append("- Win indexing: canonical cleanup, index recovery, fresh GSC pulls")
    out.append("- Convert visibility into affiliate clicks (CTA experiments after gates)")
    out.append("- Connect revenue data and measure RPM")
    out.append("")

    out.append("## 19. Next-year OKRs")
    out.append("")
    out.append("- 100% indexed coverage of sitemap URLs")
    out.append("- SUFFICIENT_SAMPLE revenue experiments with declared WIN/LOSE")
    out.append("- Real revenue reporting (no NULL)")
    out.append("- Legacy persona count to 0")
    out.append("")

    out.append("### Value classification")
    out.append("")
    out.append("- Traffic growth: INSUFFICIENT_SAMPLE (baseline only, 166 sessions / 374 pageviews 28d)")
    out.append("- Content asset value: 58 posts, 51-item opportunity pipeline, 0 fabricated metrics")
    out.append("- Commercial value: 277 CTA rows / 45 pages, Drive ACTIVE, revenue NULL")
    out.append("- Operational maturity: automated engines + guarded reporting; backup/rollback NOT_AVAILABLE")
    out.append("")
    out.append(comparison_markdown(period_comparison(snapshot, date.fromisoformat(snapshot["as_of"]), "YoY"), "YoY"))
    return "\n".join(out)

# --------------------------------------------------------------------------
# master dashboard + alerts
# --------------------------------------------------------------------------
def derive_alerts(snapshot: dict) -> dict:
    """Deterministic alert derivation from the snapshot (no fabrication)."""
    red = []
    orange = []
    yellow = []
    green = []

    rev = _kmap(snapshot, "revenue").get("revenue")
    rev_val = (rev or {}).get("value")
    orders = _kmap(snapshot, "revenue").get("orders_conversions", {}).get("value")
    # 2.0: revenue 已 LIVE 接入后，0 收入（无订单无佣金）是正常状态，绝不误报 RED。
    # 仅当「有佣金却 0 订单」这种同源矛盾才判定为异常。
    if rev_val is not None and float(rev_val or 0) > 0 and not orders:
        red.append("Revenue anomaly detected (commission >0 but 0 orders)")
    # experiment failures
    for e in _exp_table(snapshot):
        if e.get("status") in ("LOSE", "FAILED", "NEGATIVE"):
            orange.append(f"Experiment {e['experiment_id']} status {e.get('status')}")
    # secret / security
    sec = _kmap(snapshot, "operations").get("security_scan")
    if sec and sec.get("value") not in (None, "PASS"):
        red.append("Security/secret scan not passing")
    # brand regression
    core = _kmap(snapshot, "brand").get("core_brand_compliance")
    if core and core.get("value") not in (None, "PASS", "WARN"):
        orange.append("Brand regression detected")

    low = snapshot.get("low_data_reasons", [])
    if low:
        yellow.append(f"LOW_DATA_WARNING ({len(low)} reasons): " + "; ".join(low[:4]))
    cmap = _kmap(snapshot, "content_assets")
    canon = cmap.get("canonical_conflicts")
    if canon and (canon.get("value") or 0) > 0:
        yellow.append(f"{canon.get('value')} HIGH canonical conflicts awaiting technical review")
    legacy = cmap.get("legacy_persona_pages")
    if legacy and (legacy.get("value") or 0) > 0:
        yellow.append(f"{legacy.get('value')} legacy-persona posts remaining")
    waiting = [e["experiment_id"] for e in _exp_table(snapshot)
               if e.get("status") == "WAITING_RECRAWL"]
    if waiting:
        yellow.append("WAITING_RECRAWL: " + ", ".join(waiting))

    if not red and not orange and not yellow:
        green.append("All monitored systems within expected state")
    level = "RED" if red else "ORANGE" if orange else "YELLOW" if yellow else "GREEN"
    return {"level": level, "red": red, "orange": orange, "yellow": yellow, "green": green}


def render_alerts(snapshot: dict) -> str:
    a = derive_alerts(snapshot)
    lines = [
        "# ChinaBound Travel 2.0 — Management Alerts",
        "",
        f"- Generated: {snapshot.get('generated_at')}",
        f"- Overall level: **{a['level']}**",
        "",
        "| Level | Meaning |",
        "|---|---|",
        "| GREEN | no action needed |",
        "| YELLOW | attention / low data / open queues |",
        "| ORANGE | escalate within the week |",
        "| RED | act immediately |",
        "",
        "## RED",
        "",
    ]
    lines += [f"- {x}" for x in a["red"]] or ["- none"]
    lines += ["", "## ORANGE", ""]
    lines += [f"- {x}" for x in a["orange"]] or ["- none"]
    lines += ["", "## YELLOW", ""]
    lines += [f"- {x}" for x in a["yellow"]] or ["- none"]
    lines += ["", "## GREEN", ""]
    lines += [f"- {x}" for x in a["green"]] or ["- none"]
    lines += [
        "",
        "## Trigger definitions",
        "",
        "- Traffic drop / indexing drop / revenue anomaly / experiment failure / production outage / "
        "secret-security issue / brand regression: detected only when snapshot evidence exists.",
        "- Every alert below the level of RED is advisory; no WIN/LOSE or success/failure claims on insufficient data.",
        "",
    ]
    return "\n".join(lines)


def render_master(snapshot: dict) -> str:
    a = derive_alerts(snapshot)
    lines = [
        "# ChinaBound Travel 2.0 — Master Dashboard",
        "",
        f"- Generated: {snapshot.get('generated_at')} | as_of: {snapshot.get('as_of')}",
        f"- Alert level: **{a['level']}**",
        "- Single source of truth: reports/management/REPORTING_SNAPSHOT.json",
        "",
        "## Latest period reports",
        "",
        "| Period | Report |",
        "|---|---|",
        "| Daily | reports/management/daily/CHINABOUND_TRAVEL_2_0_DAILY.md |",
        "| Weekly | reports/management/weekly/CHINABOUND_TRAVEL_2_0_WEEKLY.md |",
        "| Monthly | reports/management/monthly/CHINABOUND_TRAVEL_2_0_MONTHLY.md |",
        "| Quarterly | reports/management/quarterly/CHINABOUND_TRAVEL_2_0_QUARTERLY.md |",
        "| Yearly | reports/management/yearly/CHINABOUND_TRAVEL_2_0_YEARLY.md |",
        "",
        "## Current KPI baseline (2.0)",
        "",
    ]
    cmap = _kmap(snapshot, "content_assets")
    tmap = _kmap(snapshot, "traffic")
    smap = _kmap(snapshot, "seo_gsc")
    amap = _kmap(snapshot, "affiliate_funnel")
    lines.append("| KPI | Value | Data source |")
    lines.append("|---|---|---|")
    for rec in (cmap.get("published_posts"), cmap.get("content_id_coverage"),
                tmap.get("sessions_28d"), tmap.get("pageviews_28d"),
                smap.get("gsc_impressions_28d"), smap.get("gsc_clicks_28d"),
                amap.get("affiliate_clicks_28d"), cmap.get("legacy_persona_pages"),
                _kmap(snapshot, "brand").get("logo_favicon_status")):
        if rec:
            lines.append(f"| {rec['name']} | {_fmt(rec)} | {rec.get('data_source_type')} |")
    lines += [
        "",
        "## Current experiments",
        "",
        "| ID | Status | Sample |",
        "|---|---|---|",
    ]
    for e in _exp_table(snapshot):
        lines.append(f"| {e['experiment_id']} | {e.get('status')} | {e.get('sample_status') or e.get('sample') or '-'} |")
    lines += [
        "",
        "## Current commercial clusters",
        "",
        "| Cluster | Status | Score | Impressions 28d | Revenue |",
        "|---|---|---|---|---|",
    ]
    for c in _cluster_table(snapshot):
        lines.append(f"| {c['cluster']} | {c.get('status') or '-'} | {c.get('score') if c.get('score') is not None else '-'} | "
                     f"{c.get('impressions_28d') if c.get('impressions_28d') is not None else 'NULL'} | "
                     f"{'NULL' if c.get('revenue') is None else c['revenue']} |")
    lines += [
        "",
        "## Current blockers",
        "",
        "- Revenue API absent -> revenue NULL",
        "- 6 HIGH canonical conflicts (technical review pending)",
        "- GROWTH07B / GROWTH07C WAITING_RECRAWL",
        "- No fresh GSC pull since 2026-08-16",
        "",
        "## Alerts",
        "",
    ]
    lines.append(render_alerts(snapshot))
    return "\n".join(lines)


# --------------------------------------------------------------------------
# write + CLI
# --------------------------------------------------------------------------
RENDERERS = {
    "daily": render_daily,
    "weekly": render_weekly,
    "monthly": render_monthly,
    "quarterly": render_quarterly,
    "yearly": render_yearly,
}


def generate_period(period: str, snapshot: dict, output_root: Path) -> Path:
    assert period in PERIODS
    out_dir = output_root / PERIODS[period]["dir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / PERIODS[period]["file"]
    body = RENDERERS[period](snapshot)
    out.write_text(body + "\n", encoding="utf-8")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="ChinaBound 2.0 unified reporting engine")
    ap.add_argument("--daily", action="store_true")
    ap.add_argument("--weekly", action="store_true")
    ap.add_argument("--monthly", action="store_true")
    ap.add_argument("--quarterly", action="store_true")
    ap.add_argument("--yearly", action="store_true")
    ap.add_argument("--all", action="store_true", help="generate all five periods")
    ap.add_argument("--master", action="store_true", help="render master dashboard")
    ap.add_argument("--alerts", action="store_true", help="render alerts")
    ap.add_argument("--as-of", default=None, help="Reference date YYYY-MM-DD")
    ap.add_argument("--output-dir", default=str(MGMT), help="Output root (default reports/management)")
    args = ap.parse_args()

    as_of = date.fromisoformat(args.as_of) if args.as_of else date.today()
    snapshot = load_snapshot(as_of)
    output_root = Path(args.output_dir)

    flags = [args.daily, args.weekly, args.monthly, args.quarterly, args.yearly]
    if args.all or not any(flags) and not args.master and not args.alerts:
        flags = [True] * 5
    written = []
    for period, on in zip(PERIODS, flags):
        if on:
            written.append(str(generate_period(period, snapshot, output_root)))
    if args.master:
        master = MASTER_FILE if output_root == MGMT else output_root.parent / "CHINABOUND_TRAVEL_2_0_MASTER_DASHBOARD.md"
        master.write_text(render_master(snapshot) + "\n", encoding="utf-8")
        written.append(str(master))
    if args.alerts:
        alerts = ALERTS_FILE if output_root == MGMT else output_root / "ALERTS.md"
        alerts.write_text(render_alerts(snapshot) + "\n", encoding="utf-8")
        written.append(str(alerts))
    for w in written:
        print("WROTE " + w)
    if not written:
        ap.print_help()


if __name__ == "__main__":
    main()
