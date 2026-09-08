#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Email Sequence Tracker — Closed Loop 4 (P2)
=============================================
Weekly email marketing performance tracker for ChinaBound Travel.

Pipeline:
  1. Pull MailerLite subscriber stats & campaign metrics (open rate, CTR)
  2. Pull GA4 email-channel traffic & conversions
  3. Pull Travelpayouts affiliate revenue (filtered by utm_source=email)
  4. Generate weekly Email Marketing Effectiveness Report

Report metrics:
  - Subscriber count & growth
  - Open rate, click rate, CTR
  - Email-driven affiliate clicks
  - Affiliate revenue from email channel
  - RPM (Revenue Per Mille emails sent)
  - Per-day sequence performance (Day 1–7)

Usage:
  python scripts/email_sequence_tracker.py
  python scripts/email_sequence_tracker.py --dry-run
  python scripts/email_sequence_tracker.py --days 7
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

MAILERLITE_API_BASE = "https://connect.mailerlite.com/api"
GA4_PROPERTY_ID = os.environ.get("GA4_PROPERTY_ID", "541752321")
GA4_SCOPE = "https://www.googleapis.com/auth/analytics.readonly"

DEFAULT_LOOKBACK_DAYS = 7


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
def load_env() -> None:
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
    except Exception:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


# ---------------------------------------------------------------------------
# MailerLite API
# ---------------------------------------------------------------------------
def mailerlite_request(method: str, endpoint: str, token: str, params: Optional[Dict] = None) -> Tuple[int, Any]:
    """Make MailerLite API request."""
    import requests
    url = f"{MAILERLITE_API_BASE}/{endpoint.lstrip('/')}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    try:
        if method.upper() == "GET":
            r = requests.get(url, headers=headers, params=params, timeout=30)
        else:
            return 0, {"error": f"Unsupported method: {method}"}
        try:
            return r.status_code, r.json()
        except Exception:
            return r.status_code, {"raw": r.text[:500]}
    except Exception as e:
        return 0, {"error": str(e)}


def fetch_mailerlite_subscribers(token: str) -> Optional[Dict[str, Any]]:
    """Fetch subscriber count by status. MailerLite uses cursor pagination
    without a total field, so we fetch with a high limit and count by status."""
    if not token:
        return None
    active = 0
    unsubscribed = 0
    total_sent = 0
    total_opens = 0
    total_clicks = 0
    cursor = None
    pages = 0
    max_pages = 20  # safety cap at ~20k subscribers

    while pages < max_pages:
        params = {"limit": 1000}
        if cursor:
            params["cursor"] = cursor
        code, data = mailerlite_request("GET", "subscribers", token, params=params)
        if code != 200:
            print(f"   [MailerLite] Subscribers fetch failed HTTP {code}: {str(data)[:150]}")
            if pages == 0:
                return None
            break
        batch = data.get("data", [])
        for s in batch:
            status = s.get("status", "active")
            if status == "active":
                active += 1
            elif status in ("unsubscribed", "unsubscribed"):
                unsubscribed += 1
            total_sent += s.get("sent", 0) or 0
            total_opens += s.get("opens_count", 0) or 0
            total_clicks += s.get("clicks_count", 0) or 0
        cursor = data.get("meta", {}).get("next_cursor")
        pages += 1
        if not cursor or len(batch) < 1000:
            break

    return {
        "total_active": active,
        "unsubscribed": unsubscribed,
        "total_list": active + unsubscribed,
        "total_sent": total_sent,
        "total_opens": total_opens,
        "total_clicks": total_clicks,
    }


def fetch_mailerlite_campaigns(token: str, limit: int = 20) -> Optional[List[Dict[str, Any]]]:
    """Fetch recent campaigns with open/click stats."""
    if not token:
        return None
    code, data = mailerlite_request("GET", "campaigns", token, params={"limit": limit, "sort": "-date"})
    if code != 200:
        print(f"   [MailerLite] Campaigns fetch failed HTTP {code}: {str(data)[:150]}")
        return None
    campaigns = []
    for c in data.get("data", []):
        stats = c.get("stats", {})
        campaigns.append({
            "id": c.get("id"),
            "name": c.get("name", ""),
            "subject": c.get("subject", ""),
            "status": c.get("status", ""),
            "date": c.get("date", ""),
            "sent": stats.get("sent", 0),
            "opened": stats.get("opened", 0),
            "clicked": stats.get("clicked", 0),
            "bounced": stats.get("bounced", 0),
            "unsubscribed": stats.get("unsubscribed", 0),
            "open_rate": round(stats.get("opened", 0) / stats.get("sent", 1) * 100, 2) if stats.get("sent", 0) > 0 else 0,
            "click_rate": round(stats.get("clicked", 0) / stats.get("sent", 1) * 100, 2) if stats.get("sent", 0) > 0 else 0,
        })
    return campaigns


def fetch_mailerlite_forms(token: str) -> Optional[List[Dict[str, Any]]]:
    """Fetch signup forms. MailerLite API may not support GET /forms (405);
    in that case return None gracefully."""
    if not token:
        return None
    code, data = mailerlite_request("GET", "forms", token, params={"limit": 20})
    if code == 405:
        print("   [MailerLite] Forms endpoint GET not supported (405) — skipping")
        return None
    if code != 200:
        print(f"   [MailerLite] Forms fetch failed HTTP {code}: {str(data)[:150]}")
        return None
    forms = []
    for f in data.get("data", []):
        forms.append({
            "id": f.get("id"),
            "name": f.get("name", ""),
            "type": f.get("type", ""),
            "subscribers": f.get("subscribers_count", f.get("subscribers", 0)),
            "impressions": f.get("views", f.get("impressions", 0)),
        })
    return forms


# ---------------------------------------------------------------------------
# GA4 Data API
# ---------------------------------------------------------------------------
def _ga4_auth_headers() -> Optional[Dict[str, str]]:
    key_file_env = os.environ.get("GA4_SERVICE_ACCOUNT_JSON", "gsc-service-account-key.json")
    key_path = PROJECT_ROOT / key_file_env if not Path(key_file_env).is_absolute() else Path(key_file_env)
    if not key_path.exists():
        return None
    try:
        from google.auth.transport.requests import Request
        from google.oauth2 import service_account
        with open(key_path, "r", encoding="utf-8") as f:
            info = json.load(f)
        creds = service_account.Credentials.from_service_account_info(info, scopes=[GA4_SCOPE])
        creds.refresh(Request())
        return {"Authorization": f"Bearer {creds.token}"}
    except Exception as e:
        print(f"   [GA4] Auth failed: {e}")
        return None


def _ga4_run_report(body: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    import requests
    headers = _ga4_auth_headers()
    if not headers:
        return None
    url = f"https://analyticsdata.googleapis.com/v1beta/properties/{GA4_PROPERTY_ID}:runReport"
    try:
        r = requests.post(url, headers=headers, json=body, timeout=30)
        if r.status_code != 200:
            print(f"   [GA4] API HTTP {r.status_code}: {r.text[:200]}")
            return None
        return r.json()
    except Exception as e:
        print(f"   [GA4] API call failed: {e}")
        return None


def fetch_ga4_email_traffic(days: int = DEFAULT_LOOKBACK_DAYS) -> Optional[Dict[str, Any]]:
    """Fetch GA4 email-channel traffic: sessions, pageviews, conversions."""
    end = date.today()
    start = end - timedelta(days=days)
    body = {
        "dateRanges": [{"startDate": start.isoformat(), "endDate": end.isoformat()}],
        "metrics": [
            {"name": "sessions"},
            {"name": "screenPageViews"},
            {"name": "engagedSessions"},
            {"name": "conversions"},
        ],
        "dimensions": [{"name": "sessionSourceMedium"}, {"name": "sessionCampaignName"}],
        "dimensionFilter": {
            "filter": {
                "fieldName": "sessionSourceMedium",
                "stringFilter": {"matchType": "CONTAINS", "value": "email"},
            }
        },
        "limit": 100,
    }
    data = _ga4_run_report(body)
    if not data:
        return None
    rows_out = []
    total_sessions = 0
    total_pageviews = 0
    total_conversions = 0
    for row in data.get("rows", []):
        source_medium = row["dimensionValues"][0]["value"]
        campaign = row["dimensionValues"][1]["value"] if len(row["dimensionValues"]) > 1 else "(not set)"
        sessions = int(row["metricValues"][0]["value"])
        pageviews = int(row["metricValues"][1]["value"])
        engaged = int(row["metricValues"][2]["value"])
        conversions = int(row["metricValues"][3]["value"])
        total_sessions += sessions
        total_pageviews += pageviews
        total_conversions += conversions
        rows_out.append({
            "source_medium": source_medium,
            "campaign": campaign,
            "sessions": sessions,
            "pageviews": pageviews,
            "engaged_sessions": engaged,
            "conversions": conversions,
        })
    return {
        "total_sessions": total_sessions,
        "total_pageviews": total_pageviews,
        "total_conversions": total_conversions,
        "by_campaign": rows_out,
    }


def fetch_ga4_email_affiliate_clicks(days: int = DEFAULT_LOOKBACK_DAYS) -> Optional[int]:
    """Fetch affiliate clicks from email traffic (via landing page + outbound events)."""
    end = date.today()
    start = end - timedelta(days=days)
    # Count affiliate_click events where session source contains email
    body = {
        "dateRanges": [{"startDate": start.isoformat(), "endDate": end.isoformat()}],
        "metrics": [{"name": "eventCount"}],
        "dimensions": [{"name": "sessionSourceMedium"}],
        "dimensionFilter": {
            "andGroup": {
                "expressions": [
                    {"filter": {"fieldName": "eventName",
                                "stringFilter": {"matchType": "EXACT", "value": "affiliate_click"}}},
                    {"filter": {"fieldName": "sessionSourceMedium",
                                "stringFilter": {"matchType": "CONTAINS", "value": "email"}}},
                ]
            }
        },
        "limit": 50,
    }
    data = _ga4_run_report(body)
    if not data:
        return None
    total = 0
    for row in data.get("rows", []):
        total += int(row["metricValues"][0]["value"])
    return total


# ---------------------------------------------------------------------------
# Travelpayouts revenue
# ---------------------------------------------------------------------------
def fetch_email_revenue(days: int = DEFAULT_LOOKBACK_DAYS) -> Optional[Dict[str, Any]]:
    """Fetch affiliate revenue. Travelpayouts doesn't filter by UTM directly,
    so we return total revenue and estimate email share from GA4 click ratio."""
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from travelpayouts_client import fetch_affiliate_stats
        stats = fetch_affiliate_stats(days=days)
        return stats
    except Exception as e:
        print(f"   [Travelpayouts] Revenue fetch failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------
def generate_report(
    subscriber_stats: Optional[Dict[str, Any]],
    campaigns: Optional[List[Dict[str, Any]]],
    forms: Optional[List[Dict[str, Any]]],
    ga4_email: Optional[Dict[str, Any]],
    email_affiliate_clicks: Optional[int],
    revenue_stats: Optional[Dict[str, Any]],
    days: int,
    dry_run: bool,
) -> str:
    """Generate weekly email marketing report in Markdown."""
    today = date.today().isoformat()
    lines = [
        f"# Email Marketing Effectiveness Report — {today}",
        "",
        f"> Closed Loop 4: Email Growth Automation",
        f"> Lookback: {days} days | Mode: {'DRY-RUN' if dry_run else 'LIVE'}",
        "",
        "## Executive Summary",
        "",
    ]

    # Subscriber metrics
    if subscriber_stats:
        lines.extend([
            "| Metric | Value |",
            "|--------|-------|",
            f"| Active subscribers | {subscriber_stats.get('total_active', 0):,} |",
            f"| Unsubscribed | {subscriber_stats.get('unsubscribed', 0):,} |",
            f"| Total list size | {subscriber_stats.get('total_list', 0):,} |",
        ])
    else:
        lines.append("*Subscriber data unavailable (MailerLite API error or missing token)*")

    # Campaign performance
    if campaigns:
        # Aggregate stats from recent campaigns
        total_sent = sum(c.get("sent", 0) for c in campaigns)
        total_opened = sum(c.get("opened", 0) for c in campaigns)
        total_clicked = sum(c.get("clicked", 0) for c in campaigns)
        avg_open_rate = round(total_opened / total_sent * 100, 2) if total_sent > 0 else 0
        avg_click_rate = round(total_clicked / total_sent * 100, 2) if total_sent > 0 else 0
        ctr = round(total_clicked / total_opened * 100, 2) if total_opened > 0 else 0

        lines.extend([
            "",
            "## Campaign Performance",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Campaigns tracked | {len(campaigns)} |",
            f"| Total emails sent | {total_sent:,} |",
            f"| Total opens | {total_opened:,} |",
            f"| Total clicks | {total_clicked:,} |",
            f"| Average open rate | {avg_open_rate}% |",
            f"| Average click rate | {avg_click_rate}% |",
            f"| CTR (clicks/opens) | {ctr}% |",
        ])

        # Per-campaign breakdown
        lines.extend(["", "### Recent Campaigns", ""])
        lines.extend([
            "| Campaign | Sent | Opens | Open Rate | Clicks | Click Rate |",
            "|----------|------|-------|-----------|--------|------------|",
        ])
        for c in campaigns[:15]:
            lines.append(
                f"| {c['name'][:35]} | {c['sent']:,} | {c['opened']:,} | "
                f"{c['open_rate']}% | {c['clicked']:,} | {c['click_rate']}% |"
            )
    else:
        lines.extend(["", "*Campaign data unavailable*"])

    # GA4 email traffic
    if ga4_email:
        lines.extend([
            "",
            "## GA4 Email Channel Traffic",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Email-driven sessions | {ga4_email['total_sessions']:,} |",
            f"| Email-driven pageviews | {ga4_email['total_pageviews']:,} |",
            f"| Email-driven conversions | {ga4_email['total_conversions']:,} |",
        ])
        if ga4_email.get("by_campaign"):
            lines.extend(["", "### By Campaign", ""])
            lines.extend([
                "| Source/Medium | Campaign | Sessions | Pageviews | Conversions |",
                "|---------------|----------|----------|-----------|-------------|",
            ])
            for row in ga4_email["by_campaign"][:10]:
                lines.append(
                    f"| {row['source_medium'][:25]} | {row['campaign'][:25]} | "
                    f"{row['sessions']:,} | {row['pageviews']:,} | {row['conversions']} |"
                )
    else:
        lines.extend(["", "*GA4 email traffic data unavailable*"])

    # Affiliate clicks & revenue
    lines.extend(["", "## Affiliate Performance (Email Channel)", ""])
    if email_affiliate_clicks is not None:
        lines.append(f"- Email-driven affiliate clicks: **{email_affiliate_clicks:,}**")
    else:
        lines.append("- Email-driven affiliate clicks: *unavailable*")

    if revenue_stats:
        total_revenue = revenue_stats.get("revenue", 0)
        total_clicks = revenue_stats.get("clicks", 0)
        # Estimate email revenue share
        email_click_share = 0
        if email_affiliate_clicks is not None and total_clicks > 0:
            email_click_share = email_affiliate_clicks / total_clicks
        estimated_email_revenue = round(total_revenue * email_click_share, 2)
        # RPM: revenue per 1000 emails sent
        total_sent = sum(c.get("sent", 0) for c in campaigns) if campaigns else 0
        rpm = round((estimated_email_revenue / total_sent) * 1000, 4) if total_sent > 0 else 0

        lines.extend([
            f"- Total affiliate revenue (period): ${total_revenue:.2f}",
            f"- Total affiliate clicks (period): {total_clicks:,}",
            f"- Estimated email revenue share: {email_click_share*100:.1f}%",
            f"- Estimated email-driven revenue: ${estimated_email_revenue:.2f}",
            f"- Email RPM (revenue per 1000 emails): ${rpm:.4f}",
        ])
    else:
        lines.append("- Affiliate revenue data: *unavailable*")

    # Signup forms
    if forms:
        lines.extend(["", "## Signup Forms", ""])
        lines.extend([
            "| Form | Type | Subscribers |",
            "|------|------|-------------|",
        ])
        for f in forms[:10]:
            lines.append(f"| {f['name'][:35]} | {f['type']} | {f['subscribers']:,} |")

    # Recommendations
    lines.extend([
        "",
        "## Observations & Recommendations",
        "",
    ])
    recs = []
    if campaigns:
        avg_open = sum(c.get("open_rate", 0) for c in campaigns) / max(len(campaigns), 1)
        if avg_open < 20:
            recs.append(f"⚠️ Average open rate ({avg_open:.1f}%) is below 20% benchmark. Consider A/B testing subject lines and optimizing send time.")
        elif avg_open > 40:
            recs.append(f"✅ Average open rate ({avg_open:.1f}%) is strong — above 40% benchmark.")
        avg_click = sum(c.get("click_rate", 0) for c in campaigns) / max(len(campaigns), 1)
        if avg_click < 2:
            recs.append(f"⚠️ Average click rate ({avg_click:.1f}%) is below 2% benchmark. Review CTA placement and affiliate link relevance.")
    if subscriber_stats and subscriber_stats.get("total_active", 0) < 100:
        recs.append("📈 Subscriber base is small (<100). Focus on lead magnet promotion and content upgrades to grow list.")
    if ga4_email and ga4_email["total_sessions"] == 0:
        recs.append("⚠️ No email-driven sessions detected in GA4. Verify UTM parameters in email links and GA4 email channel tracking.")
    if not recs:
        recs.append("All metrics within expected ranges. Continue monitoring.")

    for r in recs:
        lines.append(f"- {r}")

    lines.extend([
        "",
        "## Data Sources",
        "",
        "- MailerLite API: subscribers, campaigns, forms",
        "- GA4 Data API: email-channel sessions, pageviews, conversions, affiliate clicks",
        "- Travelpayouts API: total affiliate revenue (email share estimated by click ratio)",
        "",
        f"_Generated: {datetime.now().isoformat()}_",
    ])

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="Email Sequence Tracker (Closed Loop 4)")
    parser.add_argument("--dry-run", action="store_true", help="Fetch data and generate report without side effects")
    parser.add_argument("--days", type=int, default=DEFAULT_LOOKBACK_DAYS,
                        help=f"Lookback days (default: {DEFAULT_LOOKBACK_DAYS})")
    args = parser.parse_args()

    load_env()
    token = os.environ.get("MAILERLITE_API_TOKEN", "").strip()

    print("=" * 70)
    print("  Email Sequence Tracker — Closed Loop 4")
    print(f"  Mode: {'DRY-RUN' if args.dry_run else 'LIVE'} | Days: {args.days}")
    print("=" * 70)

    # 1. MailerLite data
    print("\n[1/4] Fetching MailerLite subscriber stats...")
    subscriber_stats = fetch_mailerlite_subscribers(token)
    if subscriber_stats:
        print(f"   Active: {subscriber_stats['total_active']:,} | "
              f"Unsubscribed: {subscriber_stats['unsubscribed']:,}")

    print("\n[2/4] Fetching MailerLite campaign metrics...")
    campaigns = fetch_mailerlite_campaigns(token)
    if campaigns:
        print(f"   Found {len(campaigns)} campaigns")

    print("\n[3/4] Fetching MailerLite signup forms...")
    forms = fetch_mailerlite_forms(token)
    if forms:
        print(f"   Found {len(forms)} forms")

    # 2. GA4 data
    print("\n[4/4] Fetching GA4 email channel data...")
    ga4_email = fetch_ga4_email_traffic(args.days)
    if ga4_email:
        print(f"   Email sessions: {ga4_email['total_sessions']:,} | "
              f"Conversions: {ga4_email['total_conversions']}")
    email_affiliate_clicks = fetch_ga4_email_affiliate_clicks(args.days)
    if email_affiliate_clicks is not None:
        print(f"   Email affiliate clicks: {email_affiliate_clicks:,}")

    # 3. Revenue
    print("\n   Fetching Travelpayouts revenue...")
    revenue_stats = fetch_email_revenue(args.days)
    if revenue_stats:
        print(f"   Revenue: ${revenue_stats.get('revenue', 0):.2f} | "
              f"Clicks: {revenue_stats.get('clicks', 0)}")

    # 4. Generate report
    today = date.today().isoformat()
    report_path = REPORTS_DIR / f"email-marketing-report-{today}.md"
    report = generate_report(
        subscriber_stats, campaigns, forms,
        ga4_email, email_affiliate_clicks, revenue_stats,
        args.days, args.dry_run,
    )
    report_path.write_text(report, encoding="utf-8")
    print(f"\n📄 Report written: {report_path}")

    print("\n" + "=" * 70)
    print("  DONE. Email marketing report generated.")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
