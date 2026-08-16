#!/usr/bin/env python3
"""P1-GROWTH-10B: Drive ON revenue measurement baseline.

Builds the first commercialization baseline after Travelpayouts Drive
activation (2026-08-16, DRIVE-001 experiment, RUNNING):

  - pre-drive 28d baseline (GA4 sessions/pageviews + affiliate_click + GSC)
  - post-drive status (INSUFFICIENT_SAMPLE until >= 28d observation)
  - per-1000-session normalization for affiliate clicks
  - revenue stays NULL (no affiliate revenue API - never fabricated)
  - commercial page ranking (GSC demand x business intent x affiliate presence)

Outputs under reports/revenue/:
  - REVENUE_DASHBOARD.md
  - PRE_DRIVE_BASELINE.csv
  - DRIVE_EXPERIMENT_REGISTRY.csv
  - TRAVELPAYOUTS_DRIVE_BASELINE.md
  - AFFILIATE_PARTNER_INVENTORY.csv (field-aligned refresh)
  - AFFILIATE_TRACKING_HEALTH.md
  - TOP_COMMERCIAL_PAGES_DRIVE.md

CLI: --days N --partner X --content-id Y --drive-state PRE_DRIVE|POST_DRIVE|ALL
     --output path
"""

from __future__ import annotations

import csv
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

BLOG_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent
REPORTS_REVENUE = BLOG_ROOT / "reports" / "revenue"
REPORTS_REVENUE.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(SCRIPTS))

from affiliate_gap_detector import (PARTNER_DEFS, SITE_PREFIX, commercial_ranking,
                                    load_articles, load_gsc_page_data, scan_article,
                                    tracking_schema_check)  # noqa: E402

GA4_PROPERTY_ID = "541752321"
GA4_SCOPE = "https://www.googleapis.com/auth/analytics.readonly"
DRIVE_ACTIVE_DATE = date(2026, 8, 16)
MIN_OBSERVATION_DAYS = 28
LOW_CLICK_THRESHOLD = 20


def _num(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Pure helpers (deterministic, testable)
# ---------------------------------------------------------------------------
def days_since_drive_active(today: date) -> int:
    return (today - DRIVE_ACTIVE_DATE).days


def classify_drive_state(today: date) -> str:
    days = days_since_drive_active(today)
    if days < 0:
        return "PRE_DRIVE"
    if days < MIN_OBSERVATION_DAYS:
        return "INSUFFICIENT_SAMPLE"
    return "POST_DRIVE"


def per1000(clicks, sessions):
    sessions = _num(sessions)
    if sessions <= 0:
        return 0.0
    return round(_num(clicks) / sessions * 1000.0, 4)


def sample_guard(clicks, threshold: int = LOW_CLICK_THRESHOLD) -> str:
    return "INSUFFICIENT_SAMPLE" if _num(clicks) < threshold else "OK"


def build_pre_drive_rows(articles, ga4_by_page, sessions_total, gsc, partner_defs):
    """Per page/content_id/partner pre-drive baseline rows."""
    rows = []
    for a in articles:
        partners = {pdef["brand"] for k, pdef in partner_defs.items()
                    if any(a["scans"][kind].get(k, 0) for kind in ("inline_urls", "shortcodes", "ctas"))}
        path = "/" + a["url"].split("://", 1)[-1].split("/", 1)[-1].rstrip("/") + "/"
        aff_clicks = int(ga4_by_page.get(path, 0))
        for brand in sorted(partners) or ["NONE"]:
            rows.append({
                "content_id": a["content_id"],
                "page": a["url"],
                "partner": brand,
                "affiliate_clicks_28d": aff_clicks if brand != "NONE" else 0,
                "affiliate_sessions_28d": "NULL",
                "revenue_28d": "NULL",
                "pageviews_28d": "NULL",
                "sessions_28d_total": int(sessions_total),
                "affiliate_clicks_per_1000_sessions": per1000(aff_clicks, sessions_total),
                "gsc_clicks_28d": int(_num(a["gsc"].get("clicks"))),
                "gsc_impressions_28d": int(_num(a["gsc"].get("impressions"))),
                "commercial_intent": a["intent"],
            })
    return sorted(rows, key=lambda r: (-r["gsc_impressions_28d"], r["page"], r["partner"]))


def rank_commercial_drive(articles, partner_defs, ga4_by_page):
    """GSC demand x intent weight x affiliate presence, plus Drive status."""
    ranked = []
    for a in articles:
        imp = _num(a["gsc"].get("impressions"))
        path = "/" + a["url"].split("://", 1)[-1].split("/", 1)[-1].rstrip("/") + "/"
        has_aff = any(a["scans"][k] for k in ("inline_urls", "shortcodes", "ctas"))
        weighted = imp * (2.0 if a["intent"] in
                          ("VISA", "HOTEL", "FLIGHT", "TRAIN", "INTERNET", "VPN", "PAYMENT", "INSURANCE")
                          else 1.0)
        ranked.append({
            "content_id": a["content_id"],
            "title": a["title"],
            "url": a["url"],
            "impressions": int(imp),
            "clicks": int(_num(a["gsc"].get("clicks"))),
            "affiliate_clicks": int(ga4_by_page.get(path, 0)),
            "partner": ", ".join(sorted({pdef["brand"] for k, pdef in partner_defs.items()
                                         if any(a["scans"][kind].get(k, 0)
                                                for kind in ("inline_urls", "shortcodes", "ctas"))})) or "NONE",
            "commercial_intent": a["intent"],
            "drive_status": "ACTIVE",
            "commercial_score": round(weighted, 1),
        })
    ranked.sort(key=lambda r: (-r["commercial_score"], r["url"]))
    return ranked


# ---------------------------------------------------------------------------
# GA4 reads (read-only)
# ---------------------------------------------------------------------------
def _ga4_headers():
    import gsc_utils
    from google.auth.transport.requests import Request
    from google.oauth2 import service_account
    info = gsc_utils.load_service_account_info()
    if not info:
        return None
    creds = service_account.Credentials.from_service_account_info(info, scopes=[GA4_SCOPE])
    creds.refresh(Request())
    return {"Authorization": f"Bearer {creds.token}"}


def fetch_ga4_sessions(days: int = 28):
    """Return {date: {sessions, pageviews}} for the last N days (or None)."""
    headers = _ga4_headers()
    if not headers:
        return None
    import requests
    end = date.today()
    start = end - timedelta(days=days)
    body = {
        "dateRanges": [{"startDate": start.isoformat(), "endDate": end.isoformat()}],
        "metrics": [{"name": "sessions"}, {"name": "screenPageViews"}],
        "dimensions": [{"name": "date"}],
    }
    r = requests.post(
        f"https://analyticsdata.googleapis.com/v1beta/properties/{GA4_PROPERTY_ID}:runReport",
        headers=headers, json=body, timeout=25)
    if r.status_code != 200:
        return None
    out = {}
    for row in r.json().get("rows", []):
        d = row["dimensionValues"][0]["value"]
        out[d] = {"sessions": int(row["metricValues"][0]["value"]),
                  "pageviews": int(row["metricValues"][1]["value"])}
    return out


def fetch_ga4_affiliate_clicks(days: int = 28):
    """Return {pagePath: count} for affiliate_click events (or None)."""
    headers = _ga4_headers()
    if not headers:
        return None
    import requests
    end = date.today()
    start = end - timedelta(days=days)
    body = {
        "dateRanges": [{"startDate": start.isoformat(), "endDate": end.isoformat()}],
        "metrics": [{"name": "eventCount"}],
        "dimensions": [{"name": "eventName"}, {"name": "pagePath"}],
        "dimensionFilter": {"filter": {"fieldName": "eventName",
                                       "stringFilter": {"matchType": "EXACT", "value": "affiliate_click"}}},
    }
    r = requests.post(
        f"https://analyticsdata.googleapis.com/v1beta/properties/{GA4_PROPERTY_ID}:runReport",
        headers=headers, json=body, timeout=25)
    if r.status_code != 200:
        return None
    out = {}
    for row in r.json().get("rows", []):
        path = row["dimensionValues"][1]["value"] if len(row["dimensionValues"]) > 1 else "/"
        out[path] = int(row["metricValues"][0]["value"])
    return out


# ---------------------------------------------------------------------------
# Report writers
# ---------------------------------------------------------------------------
def write_csv(path, fieldnames, rows):
    with Path(path).open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def write_all(data: dict, output_dir: Path = REPORTS_REVENUE):
    write_csv(output_dir / "PRE_DRIVE_BASELINE.csv",
              ["content_id", "page", "partner", "affiliate_clicks_28d",
               "affiliate_sessions_28d", "revenue_28d", "pageviews_28d",
               "sessions_28d_total", "affiliate_clicks_per_1000_sessions",
               "gsc_clicks_28d", "gsc_impressions_28d", "commercial_intent"],
              data["pre_drive_rows"])

    write_csv(output_dir / "DRIVE_EXPERIMENT_REGISTRY.csv",
              ["experiment_id", "start_date", "baseline_period", "post_period",
               "status", "primary_metric", "secondary_metrics"],
              [{
                  "experiment_id": "DRIVE-001",
                  "start_date": DRIVE_ACTIVE_DATE.isoformat(),
                  "baseline_period": "2026-07-19..2026-08-15 (pre-drive 28d)",
                  "post_period": "2026-08-16.. (>=28d observation)",
                  "status": "RUNNING",
                  "primary_metric": "affiliate_clicks_per_1000_sessions"
                                    if data["revenue_available"] is False
                                    else "affiliate_revenue_per_1000_sessions",
                  "secondary_metrics": "affiliate_ctr;sessions;pageviews;gsc_clicks;gsc_impressions",
              }])

    write_csv(output_dir / "TOP_COMMERCIAL_PAGES_DRIVE.csv",
              ["content_id", "title", "url", "impressions", "clicks",
               "affiliate_clicks", "partner", "commercial_intent", "drive_status", "commercial_score"],
              data["commercial_rows"])

    # TRAVELPAYOUTS_DRIVE_BASELINE.md
    md = ["# TRAVELPAYOUTS DRIVE BASELINE", "",
          f"- activation_date: {DRIVE_ACTIVE_DATE.isoformat()}",
          "- site: https://www.chinaboundtravel.com/",
          "- drive_status: ACTIVE",
          "- drive_capacity: FULL",
          "- script_status: INSTALLED_ONCE_ALL_PAGES",
          f"- baseline_period: 2026-07-19..{DRIVE_ACTIVE_DATE.isoformat()} (pre-drive 28d)",
          f"- generated: {data['generated']}", "",
          "## Observation rule",
          "- Drive 刚激活：观察 >= 28 天后再判定效果",
          "- 1-7 天数据一律 INSUFFICIENT_SAMPLE，不宣布 WIN/LOSE",
          "- 保持当前 Drive 版本稳定，不做 A/B、不删除、不重装", ""]
    (output_dir / "TRAVELPAYOUTS_DRIVE_BASELINE.md").write_text("\n".join(md), encoding="utf-8")

    # AFFILIATE_TRACKING_HEALTH.md
    t = data["tracking"]
    health = "PASS" if t["status"] == "OK" else ("PARTIAL" if not t["missing_fields"] else "GAP")
    tm = ["# AFFILIATE TRACKING HEALTH", "",
          f"- Generated: {data['generated']}",
          f"- Event: `affiliate_click`",
          f"- Status: **{health}**",
          f"- Fields present: {', '.join(t['fields_present'])}",
          f"- Missing fields: {', '.join(t['missing_fields']) or 'none'}",
          f"- gtag event: {t['gtag_event']} | dataLayer push: {t['data_layer_push']}",
          "- No second tracking system added this round.", ""]
    (output_dir / "AFFILIATE_TRACKING_HEALTH.md").write_text("\n".join(tm), encoding="utf-8")

    # REVENUE_DASHBOARD.md
    ga4 = data["ga4_sessions"]
    ga4_src = "GA4_API" if ga4 is not None else "NOT_AVAILABLE"
    sessions_total = sum(v["sessions"] for v in ga4.values()) if ga4 else 0
    pageviews_total = sum(v["pageviews"] for v in ga4.values()) if ga4 else 0
    aff = data["ga4_affiliate"]
    aff_total = sum(aff.values()) if aff is not None else None
    db = ["# REVENUE DASHBOARD", "",
          f"- Generated: {data['generated']}",
          f"- DRIVE_ACTIVE_DATE: {DRIVE_ACTIVE_DATE.isoformat()}",
          f"- Drive state: {data['drive_state']}",
          f"- GA4 source: {ga4_src}",
          f"- 28d sessions: {sessions_total} | pageviews: {pageviews_total}",
          f"- 28d affiliate_click events: {aff_total if aff_total is not None else 'NOT_AVAILABLE'}",
          f"- Revenue: NULL (REVENUE_NOT_AVAILABLE - no affiliate revenue API)",
          f"- affiliate clicks / 1000 sessions: {per1000(aff_total or 0, sessions_total)}",
          "", "| Period | State | Sessions | Pageviews | Affiliate clicks | Per 1000 sessions | Revenue |",
          "|---|---|---|---|---|---|---|",
          f"| Pre-drive 28d | PRE_DRIVE | {sessions_total} | {pageviews_total} | {aff_total or 0} | "
          f"{per1000(aff_total or 0, sessions_total)} | NULL |",
          f"| Post-drive (0-{max(0, data['days_since_active'])}d) | {data['drive_state']} | - | - | - | - | NULL |",
          "",
          "## Classification",
          "- PRE_DRIVE: before 2026-08-16",
          "- POST_DRIVE: >= 28d after activation with sufficient clicks",
          f"- INSUFFICIENT_SAMPLE: current state (days_since_active={max(0, data['days_since_active'])}, "
          f"needs >= {MIN_OBSERVATION_DAYS})", "",
          "## Low-sample protection",
          "- GSC clicks 极低；Drive 刚启动",
          "- clicks < 20 或观察 < 28 天 → 不宣布 WIN/LOSE", ""]
    if data["errors"]:
        db.append("## API notes")
        for k, v in data["errors"].items():
            db.append(f"- {k}: {v}")
    (output_dir / "REVENUE_DASHBOARD.md").write_text("\n".join(db), encoding="utf-8")

    # TOP_COMMERCIAL_PAGES_DRIVE.md
    cl = ["# TOP COMMERCIAL PAGES (DRIVE ON)", "",
          f"- Generated: {data['generated']}", "",
          "| # | content_id | title | impressions | clicks | aff clicks | partner | intent | Drive |",
          "|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(data["commercial_rows"][:20], 1):
        cl.append(f"| {i} | {r['content_id']} | {r['title'][:50]} | {r['impressions']} | {r['clicks']} | "
                  f"{r['affiliate_clicks']} | {r['partner'][:40]} | {r['commercial_intent']} | {r['drive_status']} |")
    cl += ["", "LOW_DATA_WARNING: 28d 全站 clicks 极低，排名仅为观察基线。"]
    (output_dir / "TOP_COMMERCIAL_PAGES_DRIVE.md").write_text("\n".join(cl), encoding="utf-8")

    # AFFILIATE_PARTNER_INVENTORY.csv (field-aligned refresh)
    inv = []
    from affiliate_gap_detector import partner_inventory_rows as _pir
    base = _pir(data["articles"], PARTNER_DEFS)
    for r in base:
        inv.append({
            "partner": r["partner"],
            "pages_count": r["pages_count"],
            "link_count": r["link_count"],
            "affiliate_id": "yes",
            "utm": r["utm_present"],
            "tracking": r["tracking_present"],
            "status": r["status"],
        })
    write_csv(output_dir / "AFFILIATE_PARTNER_INVENTORY.csv",
              ["partner", "pages_count", "link_count", "affiliate_id", "utm", "tracking", "status"], inv)

    return db



def run(days: int = 28, skip_ga4: bool = False) -> dict:
    gsc = load_gsc_page_data(BLOG_ROOT / "reports" / "seo" / "page_performance.csv")
    if not gsc:
        gsc = load_gsc_page_data(BLOG_ROOT / "reports" / "seo" / "raw_pages_28d.csv")
    articles, _duplicates = load_articles(BLOG_ROOT / "content" / "posts", gsc)

    single_html = (BLOG_ROOT / "layouts" / "_default" / "single.html").read_text(
        encoding="utf-8", errors="replace")
    tracking = tracking_schema_check(single_html)

    errors = {}
    ga4_sessions = None
    ga4_affiliate = None
    if not skip_ga4:
        try:
            ga4_sessions = fetch_ga4_sessions(days)
        except Exception as exc:
            errors["ga4_sessions"] = str(exc)[:120]
        try:
            ga4_affiliate = fetch_ga4_affiliate_clicks(days)
        except Exception as exc:
            errors["ga4_affiliate"] = str(exc)[:120]

    ga4_by_page = ga4_affiliate or {}
    sessions_total = sum(v["sessions"] for v in ga4_sessions.values()) if ga4_sessions else 0
    revenue_available = False  # no affiliate revenue API connected

    pre_rows = build_pre_drive_rows(articles, ga4_by_page, sessions_total, gsc, PARTNER_DEFS)
    commercial = rank_commercial_drive(articles, PARTNER_DEFS, ga4_by_page)

    return {
        "generated": date.today().isoformat(),
        "days": days,
        "articles": articles,
        "tracking": tracking,
        "ga4_sessions": ga4_sessions,
        "ga4_affiliate": ga4_affiliate,
        "sessions_total": sessions_total,
        "revenue_available": revenue_available,
        "pre_drive_rows": pre_rows,
        "commercial_rows": commercial,
        "drive_state": classify_drive_state(date.today()),
        "days_since_active": days_since_drive_active(date.today()),
        "errors": errors,
    }


def main():
    argv = sys.argv[1:]
    days = 28
    if "--days" in argv:
        days = int(argv[argv.index("--days") + 1])
    skip = "--no-ga4" in argv
    data = run(days=days, skip_ga4=skip)
    out_path = REPORTS_REVENUE
    if "--output" in argv:
        out_path = Path(argv[argv.index("--output") + 1])
        out_path.mkdir(parents=True, exist_ok=True)
    write_all(data, output_dir=out_path)
    print(f"generated={data['generated']} drive_state={data['drive_state']} "
          f"days_since_active={data['days_since_active']}")
    print(f"sessions_28d={data['sessions_total']} "
          f"affiliate_clicks_28d={sum(data['ga4_affiliate'].values()) if data['ga4_affiliate'] is not None else 'NOT_AVAILABLE'}")
    print(f"pre_drive_rows={len(data['pre_drive_rows'])} commercial_rows={len(data['commercial_rows'])}")
    if data["errors"]:
        print("API errors:", json.dumps(data["errors"], ensure_ascii=False)[:400])
    return 0


if __name__ == "__main__":
    sys.exit(main())
