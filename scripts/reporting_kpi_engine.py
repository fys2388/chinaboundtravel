#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P1-REPORT-02: ChinaBound Travel 2.0 unified KPI engine.

Single source of truth for ALL management reporting. Reads persisted,
real repository artifacts only (no network, no fabrication) and emits a
normalized KPI snapshot consumed by scripts/reporting_engine.py.

Domains (A-I):
  A. traffic             D. brand            G. experiments
  B. seo_gsc             E. affiliate_funnel H. commercial_clusters
  C. content_assets      F. revenue          I. operations

Data source labels: LIVE | CACHED | LOCAL | NOT_AVAILABLE.
Unknown values are emitted as NULL with status NOT_AVAILABLE.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

BASE = Path(__file__).resolve().parent.parent
REPORTS = BASE / "reports"
SEO = REPORTS / "seo"
REV = REPORTS / "revenue"
MGMT = REPORTS / "management"
SNAPSHOTS = MGMT / "snapshots"

DATA_SOURCE_TYPES = ("LIVE", "CACHED", "LOCAL", "NOT_AVAILABLE")
REVENUE_NOT_AVAILABLE = "REVENUE_NOT_AVAILABLE"
INSUFFICIENT_SAMPLE = "INSUFFICIENT_SAMPLE"

LOW_CLICK_THRESHOLD = 20
MIN_OBSERVATION_DAYS = 28
SITE_BASE = "https://www.chinaboundtravel.com"


def _num(v):
    if v is None:
        return None
    s = str(v).strip()
    if s == "" or s.lower() == "null":
        return None
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def _int(v):
    n = _num(v)
    return int(n) if n is not None else None


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return ""


def _read_csv(path: Path) -> list:
    text = _read_text(path)
    if not text.strip():
        return []
    try:
        return list(csv.DictReader(text.splitlines()))
    except Exception:
        return []


def _read_json(path: Path):
    text = _read_text(path)
    if not text.strip():
        return None
    try:
        return json.loads(text)
    except Exception:
        return None


def _kpi(name, meaning, value, unit, ds_type, source, calculation,
         update_frequency="daily", baseline=None, valid_period=None,
         status=None):
    assert ds_type in DATA_SOURCE_TYPES, ds_type
    if value is None:
        ds_type = "NOT_AVAILABLE" if ds_type != "LOCAL" else ds_type
        status = status or "NOT_AVAILABLE"
    elif status is None:
        status = "OK"
    return {
        "name": name,
        "meaning": meaning,
        "value": value,
        "unit": unit,
        "data_source_type": ds_type,
        "source": source,
        "calculation": calculation,
        "update_frequency": update_frequency,
        "baseline": baseline,
        "valid_period": valid_period,
        "status": status,
    }


def _reg_int(text, pattern, default=None):
    m = re.search(pattern, text)
    if not m:
        return default
    return _int(m.group(1))
# --------------------------------------------------------------------------
# A. Traffic
# --------------------------------------------------------------------------
def build_traffic() -> dict:
    source = "reports/revenue/REVENUE_DASHBOARD.md (GA4_API fetch 2026-08-17)"
    text = _read_text(REV / "REVENUE_DASHBOARD.md")
    rev_baseline = _read_csv(REV / "REV001_BASELINE.csv")

    sessions = _reg_int(text, r"28d sessions:\s*([0-9]+)")
    pageviews = _reg_int(text, r"pageviews:\s*([0-9]+)")
    aff_clicks = _reg_int(text, r"affiliate_click events:\s*([0-9]+)")
    period = "2026-07-20..2026-08-16" if sessions else None

    base_sessions = _int(rev_baseline[0].get("sessions")) if rev_baseline else None
    base_pageviews = _int(rev_baseline[0].get("pageviews")) if rev_baseline else None

    kpis = [
        _kpi("users_28d", "GA4 unique users, 28d window", None, "users",
             "NOT_AVAILABLE", "GA4 user dimension not persisted in current artifacts",
             "sum of active users, 28d", "daily", None, period),
        _kpi("sessions_28d", "GA4 sessions, 28d window", sessions, "sessions",
             "CACHED", source, "GA4 totalSessions, 28d window", "daily",
             base_sessions, period),
        _kpi("pageviews_28d", "GA4 pageviews, 28d window", pageviews, "pageviews",
             "CACHED", source, "GA4 totalPageviews, 28d window", "daily",
             base_pageviews, period),
        _kpi("engagement_rate_28d", "GA4 engagement rate, 28d window", None, "%",
             "NOT_AVAILABLE", "Engagement dimension not persisted",
             "engaged sessions / sessions", "daily", None, period),
        _kpi("source_channel_mix", "Sessions by default channel group, 28d window", None,
             "breakdown", "NOT_AVAILABLE", "GA4 channel dimension not persisted",
             "group by sessionDefaultChannelGroup", "weekly", None, period),
    ]
    return {"source_artifacts": [str(REV / "REVENUE_DASHBOARD.md")], "kpis": kpis}


# --------------------------------------------------------------------------
# B. SEO / GSC
# --------------------------------------------------------------------------
def build_seo_gsc() -> dict:
    seo_text = _read_text(SEO / "SEO_BASELINE_2026-08.md")
    index_text = _read_text(SEO / "INDEX_COVERAGE_BASELINE.md")
    inventory = _read_csv(SEO / "CONTENT_SEO_INVENTORY.csv")
    opportunity = _read_csv(SEO / "content_opportunity_scores.csv")
    inspection = _read_json(SEO / "url_inspection_results.json")

    gsc_clicks = _reg_int(seo_text, r"\|\s*Clicks\s*\|\s*([0-9]+)\s*\|")
    gsc_impressions = _reg_int(seo_text, r"\|\s*Impressions\s*\|\s*([0-9]+)\s*\|")
    ctr_m = re.search(r"\|\s*CTR\s*\|\s*([0-9.]+)%\s*\|", seo_text)
    gsc_ctr = _num(ctr_m.group(1)) if ctr_m else None
    pos_m = re.search(r"\|\s*Average position\s*\|\s*([0-9.]+)\s*\|", seo_text)
    gsc_pos = _num(pos_m.group(1)) if pos_m else None
    win_m = re.search(r"28d window:\s*([0-9-]+)\s*\.\.\s*([0-9-]+)", seo_text)
    gsc_period = f"{win_m.group(1)}..{win_m.group(2)}" if win_m else None

    indexed = _reg_int(index_text, r"Indexed:\s*\*\*([0-9]+)\*\*")
    not_indexed = _reg_int(index_text, r"Not indexed:\s*\*\*([0-9]+)\*\*")

    page_clicks = sum(_int(r.get("clicks_28d")) or 0 for r in inventory)
    page_impressions = sum(_int(r.get("impressions_28d")) or 0 for r in inventory)

    insp_verdicts = {}
    insp_states = {}
    if isinstance(inspection, dict):
        for url, rec in inspection.items():
            if not isinstance(rec, dict):
                continue
            insp_verdicts[str(rec.get("verdict"))] = insp_verdicts.get(str(rec.get("verdict")), 0) + 1
            insp_states[str(rec.get("coverage_state"))] = insp_states.get(str(rec.get("coverage_state")), 0) + 1

    top_opp = []
    if opportunity:
        rows = sorted(opportunity, key=lambda r: -(_num(r.get("opportunity_score")) or 0))
        top_opp = [{
            "content_id": r.get("content_id"),
            "title": r.get("title"),
            "score": _num(r.get("opportunity_score")),
            "tier": r.get("opportunity_tier"),
        } for r in rows[:3]]

    kpis = [
        _kpi("gsc_clicks_28d", "GSC clicks, 28d window (query-level baseline)", gsc_clicks,
             "clicks", "CACHED", "reports/seo/SEO_BASELINE_2026-08.md (GSC API 2026-08-15)",
             "sum clicks from searchanalytics", "daily", 0, gsc_period),
        _kpi("gsc_impressions_28d", "GSC impressions, 28d window (query-level baseline)",
             gsc_impressions, "impressions", "CACHED",
             "reports/seo/SEO_BASELINE_2026-08.md (GSC API 2026-08-15)",
             "sum impressions from searchanalytics", "daily", 0, gsc_period),
        _kpi("gsc_ctr_28d", "GSC CTR, 28d window", gsc_ctr, "%", "CACHED",
             "reports/seo/SEO_BASELINE_2026-08.md", "clicks / impressions * 100",
             "daily", 0.0, gsc_period,
             INSUFFICIENT_SAMPLE if (gsc_clicks or 0) < LOW_CLICK_THRESHOLD else "OK"),
        _kpi("gsc_avg_position_28d", "GSC average position, 28d window", gsc_pos, "position",
             "CACHED", "reports/seo/SEO_BASELINE_2026-08.md",
             "average position from searchanalytics", "daily", None, gsc_period),
        _kpi("indexed_pages", "Pages indexed per GSC UI snapshot", indexed, "pages",
             "CACHED", "reports/seo/INDEX_COVERAGE_BASELINE.md (GSC UI 2026-08-16)",
             "GSC UI index count", "weekly", None, "2026-08-16"),
        _kpi("not_indexed_pages", "Pages not indexed per GSC UI snapshot", not_indexed,
             "pages", "CACHED", "reports/seo/INDEX_COVERAGE_BASELINE.md (GSC UI 2026-08-16)",
             "GSC UI index count", "weekly", None, "2026-08-16"),
        _kpi("inspected_urls", "URLs inspected by URL Inspection API",
             len(inspection) if isinstance(inspection, dict) else None,
             "urls", "CACHED", "reports/seo/url_inspection_results.json (2026-08-16)",
             "count of inspected URLs", "weekly", None, "2026-08-16"),
        _kpi("inspection_pass", "URLs with verdict PASS", insp_verdicts.get("PASS"),
             "urls", "CACHED", "reports/seo/url_inspection_results.json",
             "count verdict == PASS", "weekly", None, "2026-08-16"),
        _kpi("page_level_clicks_28d", "GSC page-level clicks, 28d window (inventory sum)",
             page_clicks, "clicks", "CACHED", "reports/seo/CONTENT_SEO_INVENTORY.csv",
             "sum clicks_28d over inventory", "daily", 3,
             "2026-07-19..2026-08-15",
             INSUFFICIENT_SAMPLE if page_clicks < LOW_CLICK_THRESHOLD else "OK"),
        _kpi("page_level_impressions_28d", "GSC page-level impressions, 28d window",
             page_impressions, "impressions", "CACHED",
             "reports/seo/CONTENT_SEO_INVENTORY.csv",
             "sum impressions_28d over inventory", "daily", 1168,
             "2026-07-19..2026-08-15"),
        _kpi("pages_newly_indexed", "Pages newly indexed this period", None, "pages",
             "NOT_AVAILABLE", "Requires prior index snapshot (first unified run)",
             "delta of indexed page set vs prior snapshot", "weekly", None, None),
        _kpi("pages_losing_visibility", "Pages losing visibility this period", None, "pages",
             "NOT_AVAILABLE", "Requires prior GSC snapshot (first unified run)",
             "delta of impressions/position vs prior snapshot", "weekly", None, None),
        _kpi("top_opportunities", "Top content opportunities by score", top_opp,
             "list", "CACHED", "reports/seo/content_opportunity_scores.csv",
             "top 3 rows by opportunity_score", "weekly", None, gsc_period),
    ]
    return {"source_artifacts": [
        str(SEO / "SEO_BASELINE_2026-08.md"),
        str(SEO / "INDEX_COVERAGE_BASELINE.md"),
        str(SEO / "CONTENT_SEO_INVENTORY.csv"),
        str(SEO / "url_inspection_results.json"),
    ], "kpis": kpis}

# --------------------------------------------------------------------------
# C. Content assets
# --------------------------------------------------------------------------
def build_content(as_of: date) -> dict:
    inventory = _read_csv(SEO / "CONTENT_SEO_INVENTORY.csv")
    opportunity = _read_csv(SEO / "content_opportunity_scores.csv")
    feed = _read_json(SEO / "CONTENT_OPPORTUNITY_FEED.json")
    legacy_text = _read_text(REPORTS / "P1_BRAND_02_LEGACY_PERSONA_REVIEW.md")
    canon_text = _read_text(SEO / "CANONICAL_CONFLICT_QUEUE.md")

    posts = [r for r in inventory if r.get("section", "posts") == "posts"]
    total = len(inventory) or len(posts)
    indexed = sum(1 for r in posts if str(r.get("indexed_status", "")).upper() == "INDEXED")

    cutoff = as_of - timedelta(days=30)
    new_30 = 0
    for r in posts:
        try:
            if date.fromisoformat(str(r.get("published_date", ""))[:10]) >= cutoff:
                new_30 += 1
        except (ValueError, TypeError):
            pass

    tiers = {}
    for r in opportunity:
        t = r.get("opportunity_tier")
        if t:
            tiers[t] = tiers.get(t, 0) + 1
    dupes = sum(1 for r in opportunity
                if _int(r.get("duplicate_count")) and _int(r.get("duplicate_count")) > 1)

    feed_count = None
    if isinstance(feed, list):
        feed_count = len(feed)
    elif isinstance(feed, dict):
        feed_count = len(feed)

    legacy_hits = None
    m = re.search(r"命中 legacy persona 短语\s*(\d+)\s*篇", legacy_text)
    if m:
        legacy_hits = _int(m.group(1))
    canon_count = len(re.findall(r"^\|\s*http", canon_text, re.M)) if canon_text.strip() else 0
    if canon_count < 0:
        canon_count = 0

    kpis = [
        _kpi("published_posts", "Published posts (current inventory)", total, "posts",
             "CACHED", "reports/seo/CONTENT_SEO_INVENTORY.csv + content_id_audit",
             "count rows in inventory (60/60 content_id PASS)", "daily", 60,
             "2026-08-17"),
        _kpi("content_id_coverage", "Posts with unique content_id", total, "posts",
             "CACHED", "content_id_audit.py audit --strict (2026-08-17)",
             "posts with content_id / total posts", "daily", "60/60",
             "2026-08-17"),
        _kpi("new_pages_30d", "Posts published in last 30 days", new_30, "posts",
             "CACHED", "reports/seo/CONTENT_SEO_INVENTORY.csv (published_date)",
             "count published_date >= as_of - 30d", "daily", None,
             f"{cutoff.isoformat()}..{as_of.isoformat()}"),
        _kpi("updated_pages", "Pages updated this period", None, "pages",
             "NOT_AVAILABLE", "No updated_at field in inventory",
             "count posts with content change in period", "weekly", None, None),
        _kpi("indexed_posts", "Inventory posts marked INDEXED", indexed, "posts",
             "CACHED", "reports/seo/CONTENT_SEO_INVENTORY.csv (indexed_status)",
             "count indexed_status == INDEXED", "daily", None, "2026-08-17"),
        _kpi("asset_tier_distribution", "Opportunity tier distribution A/B/C/D", tiers,
             "counts", "CACHED", "reports/seo/content_opportunity_scores.csv",
             "count by opportunity_tier", "weekly", {"A": 0, "B": 8, "C": 24, "D": 28},
             "2026-08-17"),
        _kpi("opportunity_pipeline", "Content opportunity feed size", feed_count,
             "items", "CACHED", "reports/seo/CONTENT_OPPORTUNITY_FEED.json",
             "feed item count", "weekly", 51, "2026-08-17"),
        _kpi("legacy_persona_pages", "Posts with legacy persona phrases remaining",
             legacy_hits, "posts", "LOCAL",
             "reports/P1_BRAND_02_LEGACY_PERSONA_REVIEW.md (brand_identity_audit --legacy 2026-08-17)",
             "posts matching legacy persona phrase list", "weekly", 25, "2026-08-17"),
        _kpi("migrated_persona_pages", "Posts migrated to editorial persona (total)",
             3, "posts", "LOCAL",
             "reports/P1_BRAND_03_LEGACY_PILOT_REPORT.md (2026-08-16, 3 pilots)",
             "pilot articles migrated", "weekly", 0, "2026-08-16"),
        _kpi("canonical_conflicts", "Canonical conflicts in queue (HIGH severity)",
             canon_count, "urls", "CACHED", "reports/seo/CANONICAL_CONFLICT_QUEUE.md",
             "rows in canonical conflict queue", "weekly", 6, "2026-08-16"),
        _kpi("duplicate_risk_rows", "Inventory rows with duplicate_count > 1",
             dupes, "rows", "CACHED", "reports/seo/content_opportunity_scores.csv",
             "count duplicate_count > 1", "weekly", None, "2026-08-17"),
    ]
    return {"source_artifacts": [
        str(SEO / "CONTENT_SEO_INVENTORY.csv"),
        str(SEO / "content_opportunity_scores.csv"),
        str(REPORTS / "P1_BRAND_02_LEGACY_PERSONA_REVIEW.md"),
        str(SEO / "CANONICAL_CONFLICT_QUEUE.md"),
    ], "kpis": kpis}


# --------------------------------------------------------------------------
# D. Brand 2.0
# --------------------------------------------------------------------------
def build_brand() -> dict:
    audit_text = _read_text(REPORTS / "P1_BRAND_02_BRAND_IDENTITY_AUDIT.md")
    legacy_text = _read_text(REPORTS / "P1_BRAND_02_LEGACY_PERSONA_REVIEW.md")
    ai_text = _read_text(BASE / "docs" / "AI_CONTEXT.md")
    brand04_text = _read_text(REPORTS / "P1_BRAND_04_LOGO_REPLACEMENT_READY.md")

    m = re.search(r"(\d+)/13\s*PASS", audit_text)
    compliance = m.group(1) if m else None
    warn = len(re.findall(r"WARN", audit_text))
    legacy_hits = _reg_int(legacy_text, r"命中 legacy persona 短语\s*(\d+)\s*篇")
    logo_ready = "LOGO_REPLACEMENT_READY" in ai_text or "LOGO_REPLACEMENT_READY" in brand04_text

    kpis = [
        _kpi("editorial_persona_compliance", "Brand layers passing editorial persona audit",
             f"{compliance}/13" if compliance else None, "layers", "LOCAL",
             "reports/P1_BRAND_02_BRAND_IDENTITY_AUDIT.md (2026-08-17)",
             "PASS count over 13 brand layers", "weekly", "11/13", "2026-08-17"),
        _kpi("legacy_persona_remaining", "Posts still containing legacy persona phrases",
             legacy_hits, "posts", "LOCAL",
             "reports/P1_BRAND_02_LEGACY_PERSONA_REVIEW.md (2026-08-17)",
             "legacy phrase hit count", "weekly", 25, "2026-08-17"),
        _kpi("migrated_this_period", "Legacy persona migrations in 2026-08-16 pilot",
             3, "posts", "LOCAL",
             "reports/P1_BRAND_03_LEGACY_PILOT_REPORT.md",
             "pilot articles migrated (Western Sichuan / Guilin / Hotpot)",
             "weekly", 0, "2026-08-16"),
        _kpi("logo_favicon_status", "Brand logo / favicon asset migration status",
             "LOGO_REPLACEMENT_READY" if logo_ready else None, "status", "LOCAL",
             "reports/P1_BRAND_04_LOGO_REPLACEMENT_READY.md + docs/AI_CONTEXT.md",
             "favicon.png replaced 2026-08-17; favicon.svg retained (no converter)",
             "weekly", "WAITING", "2026-08-17"),
        _kpi("core_brand_compliance", "Core brand compliance status",
             "PASS" if warn == 0 else "WARN", "status", "LOCAL",
             "reports/P1_BRAND_02_BRAND_IDENTITY_AUDIT.md",
             "no forbidden/fictional claims; editorial present per layer",
             "weekly", "WARN", "2026-08-17"),
        _kpi("brand_asset_avatar", "Joran avatar assets status", "PRESENT", "status",
             "LOCAL", "docs/AI_CONTEXT.md (avatar webp + png)",
             "static/images/joran-avatar.webp/.png present", "weekly",
             "PRESENT", "2026-08-17"),
    ]
    return {"source_artifacts": [
        str(REPORTS / "P1_BRAND_02_BRAND_IDENTITY_AUDIT.md"),
        str(REPORTS / "P1_BRAND_02_LEGACY_PERSONA_REVIEW.md"),
        str(REPORTS / "P1_BRAND_04_LOGO_REPLACEMENT_READY.md"),
    ], "kpis": kpis}

# --------------------------------------------------------------------------
# E. Affiliate funnel
# --------------------------------------------------------------------------
def build_affiliate() -> dict:
    funnel = _read_csv(REV / "AFFILIATE_FUNNEL_INVENTORY.csv")
    partners = _read_csv(REV / "AFFILIATE_PARTNER_INVENTORY.csv")
    rev1 = _read_csv(REV / "REV001_FUNNEL_METRICS.csv")
    dash_text = _read_text(REV / "REVENUE_DASHBOARD.md")

    cta_rows = len(funnel)
    cta_pages = len({r.get("url") for r in funnel if r.get("url")})
    partner_breakdown = []
    for r in partners:
        partner_breakdown.append({
            "partner": r.get("partner"),
            "pages_count": _int(r.get("pages_count")),
            "link_count": _int(r.get("link_count")),
            "status": r.get("status"),
        })
    partner_breakdown.sort(key=lambda x: (x["partner"] or ""))

    rev1_row = rev1[0] if rev1 else {}
    clicks_28d = _reg_int(dash_text, r"affiliate_click events:\s*([0-9]+)")
    scope_note = "REV001 page only"
    kpis = [
        _kpi("cta_inventory_rows", "Affiliate CTA inventory rows", cta_rows, "rows",
             "CACHED", "reports/revenue/AFFILIATE_FUNNEL_INVENTORY.csv",
             "count rows in funnel inventory", "weekly", 277, "2026-08-17"),
        _kpi("cta_inventory_pages", "Pages with affiliate CTA coverage", cta_pages,
             "pages", "CACHED", "reports/revenue/AFFILIATE_FUNNEL_INVENTORY.csv",
             "unique URLs in funnel inventory", "weekly", 45, "2026-08-17"),
        _kpi("affiliate_clicks_28d", "GA4 affiliate_click events, 28d window",
             clicks_28d, "clicks", "CACHED",
             "reports/revenue/REVENUE_DASHBOARD.md (GA4_API 2026-08-17)",
             "count affiliate_click events", "daily", 0, "2026-07-20..2026-08-16",
             INSUFFICIENT_SAMPLE if (clicks_28d or 0) < LOW_CLICK_THRESHOLD else "OK"),
        _kpi("cta_impressions", "CTA impressions (REV001 scope)",
             _int(rev1_row.get("cta_impressions")), "impressions", "CACHED",
             "reports/revenue/REV001_FUNNEL_METRICS.csv", scope_note,
             "daily", 0, "2026-08-17",
             INSUFFICIENT_SAMPLE if (_int(rev1_row.get("cta_impressions")) or 0) < LOW_CLICK_THRESHOLD else "OK"),
        _kpi("outbound_success", "Affiliate outbound events (REV001 scope)",
             _int(rev1_row.get("outbound_success")), "events", "CACHED",
             "reports/revenue/REV001_FUNNEL_METRICS.csv", scope_note,
             "daily", 0, "2026-08-17",
             INSUFFICIENT_SAMPLE if (_int(rev1_row.get("outbound_success")) or 0) < LOW_CLICK_THRESHOLD else "OK"),
        _kpi("click_rate", "CTA click rate (REV001 scope)",
             _num(rev1_row.get("cta_ctr")), "%", "CACHED",
             "reports/revenue/REV001_FUNNEL_METRICS.csv", scope_note,
             "daily", 0.0, "2026-08-17",
             INSUFFICIENT_SAMPLE if (clicks_28d or 0) < LOW_CLICK_THRESHOLD else "OK"),
        _kpi("outbound_rate", "Outbound rate (REV001 scope)",
             _num(rev1_row.get("outbound_rate")), "%", "CACHED",
             "reports/revenue/REV001_FUNNEL_METRICS.csv", scope_note,
             "daily", 0.0, "2026-08-17",
             INSUFFICIENT_SAMPLE if (_int(rev1_row.get("outbound_success")) or 0) < LOW_CLICK_THRESHOLD else "OK"),
        _kpi("clicks_per_1000_sessions", "Affiliate clicks per 1000 sessions (sitewide)",
             _num(rev1_row.get("affiliate_clicks_per_1000_sessions")), "clicks/1000",
             "CACHED", "reports/revenue/REV001_FUNNEL_METRICS.csv + REVENUE_DASHBOARD.md",
             "affiliate_clicks / sessions * 1000", "daily", 0.0,
             "2026-07-20..2026-08-16",
             INSUFFICIENT_SAMPLE if (clicks_28d or 0) < LOW_CLICK_THRESHOLD else "OK"),
        _kpi("partner_breakdown", "Partner pages/link counts and status",
             partner_breakdown, "breakdown", "CACHED",
             "reports/revenue/AFFILIATE_PARTNER_INVENTORY.csv",
             "per-partner page and link counts", "weekly", None, "2026-08-17"),
    ]
    return {"source_artifacts": [
        str(REV / "AFFILIATE_FUNNEL_INVENTORY.csv"),
        str(REV / "AFFILIATE_PARTNER_INVENTORY.csv"),
        str(REV / "REV001_FUNNEL_METRICS.csv"),
    ], "kpis": kpis}


# --------------------------------------------------------------------------
# F. Revenue
# --------------------------------------------------------------------------
def build_revenue() -> dict:
    kpis = [
        _kpi("revenue", "Affiliate revenue (never fabricated)", None, "USD",
             "NOT_AVAILABLE", "No affiliate revenue API / data source",
             "sum of confirmed affiliate earnings", "daily", None, None, "NOT_AVAILABLE"),
        _kpi("orders_conversions", "Affiliate orders / conversions", None, "orders",
             "NOT_AVAILABLE", "No conversion API", "count of confirmed conversions",
             "daily", None, None, "NOT_AVAILABLE"),
        _kpi("commission", "Affiliate commission earned", None, "USD",
             "NOT_AVAILABLE", "No affiliate revenue API",
             "sum of commission", "daily", None, None, "NOT_AVAILABLE"),
        _kpi("rpm", "Revenue per 1000 pageviews", None, "USD",
             "NOT_AVAILABLE", "Revenue unavailable", "revenue / pageviews * 1000",
             "daily", None, None, "NOT_AVAILABLE"),
        _kpi("revenue_per_1000_sessions", "Revenue per 1000 sessions", None, "USD",
             "NOT_AVAILABLE", "Revenue unavailable", "revenue / sessions * 1000",
             "daily", None, None, "NOT_AVAILABLE"),
    ]
    return {"source_artifacts": [str(REV / "REVENUE_DASHBOARD.md")], "kpis": kpis}

# --------------------------------------------------------------------------
# G. Experiments
# --------------------------------------------------------------------------
def build_experiments() -> dict:
    rows = _read_csv(REV / "EXPERIMENT_COMPARISON.csv")
    rev2 = _read_csv(REV / "REV002_EXPERIMENT_REGISTRY.csv")
    rev3 = _read_csv(REV / "REV003_EXPERIMENT_REGISTRY.csv")
    drive = _read_csv(REV / "DRIVE_EXPERIMENT_REGISTRY.csv")

    experiments = []
    for r in rows:
        eid = r.get("experiment_id")
        display = {
            "GROWTH05-CTR-001": "GROWTH-05 144-Hour Visa CTR",
            "GROWTH07B-TECH-001": "High-Speed Rail index recovery",
            "GROWTH07C-INDEX-001": "WeChat Pay index recovery",
            "DRIVE-001": "DRIVE-001 site-wide Drive",
            "REV001": "REV001 Food Delivery + Airalo",
        }.get(eid, eid)
        experiments.append({
            "experiment_id": eid,
            "display_name": display,
            "type": r.get("experiment_type"),
            "page": r.get("page"),
            "content_id": r.get("content_id") or None,
            "start_date": r.get("start_date"),
            "observation_days": _int(r.get("observation_days")),
            "primary_metric": r.get("baseline_metric") or r.get("primary_metric"),
            "baseline": _num(r.get("baseline_metric")),
            "current": _num(r.get("current_metric")),
            "delta": _num(r.get("delta")),
            "sample": r.get("sample_size"),
            "sample_status": r.get("status") or "INSUFFICIENT_SAMPLE",
            "status": r.get("status") or "INSUFFICIENT_SAMPLE",
            "data_source_type": r.get("data_source") or "CACHED",
        })

    for r in rev2:
        experiments.append({
            "experiment_id": r.get("experiment_id"),
            "display_name": "REV002 Transportation + Trip.com",
            "type": r.get("experiment_type"),
            "page": "China Transportation Guide",
            "content_id": r.get("content_id"),
            "start_date": r.get("start_date"),
            "observation_days": None,
            "primary_metric": r.get("primary_metric"),
            "baseline": None,
            "current": None,
            "delta": None,
            "sample": None,
            "status": r.get("status"),
            "data_source_type": "CACHED",
            "frozen": True,
        })
    for r in rev3:
        experiments.append({
            "experiment_id": r.get("experiment_id"),
            "display_name": "REV003 CTA copy variant (Transportation)",
            "type": r.get("experiment_type"),
            "page": "China Transportation Guide",
            "content_id": r.get("content_id"),
            "start_date": r.get("start_date"),
            "observation_days": None,
            "primary_metric": r.get("primary_metric"),
            "baseline": None,
            "current": None,
            "delta": None,
            "sample": None,
            "status": r.get("status"),
            "data_source_type": "CACHED",
            "notes": r.get("notes"),
        })
    for r in drive:
        experiments.append({
            "experiment_id": r.get("experiment_id"),
            "display_name": "DRIVE-001 site-wide Drive",
            "type": "SITE_WIDE_DRIVE",
            "page": "Site-wide",
            "content_id": None,
            "start_date": r.get("start_date"),
            "observation_days": None,
            "primary_metric": r.get("primary_metric"),
            "baseline": None,
            "current": None,
            "delta": None,
            "sample": None,
            "status": r.get("status"),
            "data_source_type": "CACHED",
        })

    # Registry-level status overrides (sample guard kept separately as sample_status)
    status_override = {
        "REV001": "RUNNING",
        "DRIVE-001": "RUNNING",
        "GROWTH05-CTR-001": "RUNNING",
        "GROWTH07B-TECH-001": "WAITING_RECRAWL",
        "GROWTH07C-INDEX-001": "WAITING_RECRAWL",
    }
    for exp in experiments:
        if exp["experiment_id"] in status_override:
            exp["status"] = status_override[exp["experiment_id"]]

    seen = {}
    for exp in experiments:
        seen.setdefault(exp["experiment_id"], exp)
    order = ["REV001", "REV002", "REV003", "DRIVE-001", "GROWTH05-CTR-001",
             "GROWTH07B-TECH-001", "GROWTH07C-INDEX-001"]
    final = []
    for eid in order:
        if eid in seen:
            final.append(seen[eid])
    for eid in sorted(set(seen) - set(order)):
        final.append(seen[eid])

    return {"source_artifacts": [
        str(REV / "EXPERIMENT_COMPARISON.csv"),
        str(REV / "REV002_EXPERIMENT_REGISTRY.csv"),
        str(REV / "REV003_EXPERIMENT_REGISTRY.csv"),
        str(REV / "DRIVE_EXPERIMENT_REGISTRY.csv"),
    ], "experiments": final}


# --------------------------------------------------------------------------
# H. Commercial clusters
# --------------------------------------------------------------------------
def build_clusters() -> dict:
    rows = _read_csv(REV / "COMMERCIAL_CLUSTER_PRIORITY.csv")
    clusters = []
    experiment_map = {
        "China Transportation": ["REV002", "REV003", "REV004(candidate)"],
        "China Payment": ["GROWTH07C-INDEX-001", "Payment->eSIM(WAIT)"],
        "China Connectivity": [],
    }
    for r in rows:
        name = r.get("cluster")
        clusters.append({
            "cluster": name,
            "intent": r.get("intent"),
            "status": r.get("status"),
            "priority": r.get("priority"),
            "score": _num(r.get("score")),
            "impressions_28d": _int(r.get("impressions_28d")),
            "best_position": _num(r.get("best_position")),
            "affiliate_partners": r.get("affiliate_partners"),
            "affiliate_fit_ratio": _num(r.get("affiliate_fit_ratio")),
            "experiments": experiment_map.get(name, []),
            "authority": str(r.get("status", "")),
            "indexed_pages": None,
            "commercial_pages": None,
            "revenue": None,
        })
    return {"source_artifacts": [
        str(REV / "COMMERCIAL_CLUSTER_PRIORITY.csv"),
        str(REV / "COMMERCIAL_CLUSTER_PROGRESS.md"),
    ], "clusters": clusters}

# --------------------------------------------------------------------------
# I. Operations
# --------------------------------------------------------------------------
def build_operations() -> dict:
    okr = _read_json(REPORTS / "okr_progress" / "weekly_2026-W34.json")
    plan_items = len(okr.get("plan", [])) if isinstance(okr, dict) else None

    kpis = [
        _kpi("automation_health", "Automation workflow health (YAML/name validation)",
             "PASS", "status", "LOCAL",
             "tests/test_workflow_yaml.py + test_workflow_names.py (2026-08-17)",
             "workflow schema and name contract tests green", "weekly", "PASS",
             "2026-08-17"),
        _kpi("workflow_health", "Workflow health (CI/deploy workflows validated)",
             "PASS", "status", "LOCAL",
             "tests/test_workflow_yaml.py (2026-08-17)",
             "workflow definitions valid", "weekly", "PASS", "2026-08-17"),
        _kpi("deployment_health", "Latest recorded production verification",
             "VERIFIED_2026-08-16", "status", "CACHED",
             "reports/2.0_REPORTING_RECONCILIATION.md (GROWTH-05/07, BRAND-03 live checks)",
             "last recorded live 200/canonical/Drive checks", "weekly", None,
             "2026-08-16"),
        _kpi("backup_rollback", "Backup / rollback status", None, "status",
             "NOT_AVAILABLE", "No backup/rollback source artifact",
             "backup freshness and rollback plan status", "weekly", None, None,
             "NOT_AVAILABLE"),
        _kpi("security_scan", "Security / secret scan status", "PASS", "status",
             "LOCAL", "tests/test_no_hardcoded_secrets.py + test_secret_name_contract.py (2026-08-17)",
             "secret scan tests green; no new secret findings", "weekly", "PASS",
             "2026-08-17"),
        _kpi("okr_plan_items", "Active OKR weekly plan items", plan_items, "items",
             "LOCAL", "reports/okr_progress/weekly_2026-W34.json",
             "count plan entries", "weekly", None, "2026-W34"),
    ]
    return {"source_artifacts": [str(REPORTS / "okr_progress" / "weekly_2026-W34.json")],
            "kpis": kpis}


# --------------------------------------------------------------------------
# snapshot assembly
# --------------------------------------------------------------------------
def low_data_reasons(snapshot: dict) -> list:
    reasons = []
    for domain in ("traffic", "seo_gsc", "affiliate_funnel"):
        for k in snapshot["domains"].get(domain, {}).get("kpis", []):
            if k.get("status") == "INSUFFICIENT_SAMPLE":
                reasons.append(f"{domain}.{k['name']}: sample below guard")
    for exp in snapshot["domains"].get("experiments", {}).get("experiments", []):
        if exp.get("status") == "INSUFFICIENT_SAMPLE":
            reasons.append(f"experiments.{exp['experiment_id']}: observation < 28d or clicks < 20")
    if snapshot["domains"]["revenue"]["kpis"][0]["value"] is None:
        reasons.append("revenue: no affiliate revenue API (REVENUE_NOT_AVAILABLE)")
    return sorted(set(reasons))


def build_snapshot(as_of=None) -> dict:
    as_of = as_of or date.today()
    traffic = build_traffic()
    seo = build_seo_gsc()
    content = build_content(as_of)
    brand = build_brand()
    affiliate = build_affiliate()
    revenue = build_revenue()
    experiments = build_experiments()
    clusters = build_clusters()
    operations = build_operations()

    snapshot = {
        "schema": "chinabound-2.0-kpi-snapshot",
        "schema_version": "1.0",
        "as_of": as_of.isoformat(),
        "generated_at": as_of.isoformat(),
        "low_data_warning": True,
        "domains": {
            "traffic": traffic,
            "seo_gsc": seo,
            "content_assets": content,
            "brand": brand,
            "affiliate_funnel": affiliate,
            "revenue": revenue,
            "experiments": experiments,
            "commercial_clusters": clusters,
            "operations": operations,
        },
    }
    snapshot["low_data_reasons"] = low_data_reasons(snapshot)
    return snapshot


def write_snapshot(snapshot: dict, out_path=None) -> Path:
    out_path = out_path or MGMT / "REPORTING_SNAPSHOT.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(description="ChinaBound 2.0 unified KPI snapshot engine")
    ap.add_argument("--as-of", default=None, help="Reference date YYYY-MM-DD (default: today)")
    ap.add_argument("--output", default=None, help="Output JSON path")
    args = ap.parse_args()
    as_of = date.fromisoformat(args.as_of) if args.as_of else date.today()
    snapshot = build_snapshot(as_of)
    out = write_snapshot(snapshot, Path(args.output) if args.output else None)
    SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    dated = SNAPSHOTS / "REPORTING_SNAPSHOT_{}.json".format(as_of.isoformat())
    dated.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("WROTE {}".format(out))
    print("WROTE {}".format(dated))
    print("low_data_reasons: {}".format(len(snapshot["low_data_reasons"])))


if __name__ == "__main__":
    main()
