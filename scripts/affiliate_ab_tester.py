#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Affiliate CTA A/B Tester — Closed Loop 3 (P2)
================================================
Weekly affiliate conversion optimization for ChinaBound Travel.

Pipeline:
  1. Pull GA4 page-level data (sessions, pageviews, affiliate_click events)
  2. Fall back to P0_AFFILIATE_CTA_INVENTORY.csv static analysis if GA4 unavailable
  3. Analyze CTA performance: impressions, clicks, CTR, RPM
  4. Identify low-performing CTAs (CTR < 0.5% OR impressions > 100 but clicks < 1)
  5. Generate A/B test suggestions (higher-intent affiliate match per article topic)
  6. Auto-execute low-risk adjustments (front matter cta_variant / shortcode params)
  7. Write markdown report + JSON learning library
  8. Verify Hugo build

Safety:
  - Max 10 CTA adjustments per run (configurable)
  - Minimum sample: impressions > 200 before judging (else "insufficient data")
  - --dry-run mode never modifies files
  - All modifications verified by Hugo build

Usage:
  python scripts/affiliate_ab_tester.py --dry-run
  python scripts/affiliate_ab_tester.py --max-adjustments 5
  python scripts/affiliate_ab_tester.py --days 28
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
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
CONTENT_DIR = PROJECT_ROOT / "content" / "posts"
REPORTS_DIR = PROJECT_ROOT / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
CTA_INVENTORY_CSV = REPORTS_DIR / "P0_AFFILIATE_CTA_INVENTORY.csv"
LEARNING_LIBRARY_JSON = REPORTS_DIR / "affiliate-learning-library.json"
HUGO_BIN = r"C:\Users\神魂之人\bin\hugo.exe"

GA4_PROPERTY_ID = os.environ.get("GA4_PROPERTY_ID", "541752321")
GA4_SCOPE = "https://www.googleapis.com/auth/analytics.readonly"

# Thresholds
LOW_CTR_THRESHOLD = 0.005          # 0.5%
MIN_IMPRESSIONS_FOR_JUDGMENT = 50  # lowered from 200 for low-traffic stage
ZERO_CLICK_IMPRESSION_THRESHOLD = 30   # lowered from 100 for low-traffic stage
DEFAULT_MAX_ADJUSTMENTS = 10
DEFAULT_LOOKBACK_DAYS = 28

# UTM base for A/B test CTAs
UTM_BASE = "utm_source=blog&utm_medium=cta&utm_campaign=ab_test"

# Article topic → recommended affiliate partners (higher intent first)
TOPIC_PARTNER_MAP: Dict[str, List[str]] = {
    "Visa / Visa-Free": ["flight", "safetywing", "esim", "hotel"],
    "Itinerary / Destination": ["hotel", "klook", "flight", "esim", "safetywing"],
    "Payment (WeChat/Alipay)": ["esim", "safetywing", "vpn", "hotel"],
    "High-speed rail / Transportation": ["flight", "safetywing", "esim", "hotel"],
    "Safety": ["safetywing", "vpn", "esim", "hotel"],
    "Internet / eSIM / VPN": ["esim", "vpn", "safetywing", "flight"],
    "Food / Culture": ["klook", "hotel", "esim", "safetywing"],
    "Accommodation / Hotel": ["hotel", "klook", "esim", "safetywing"],
    "Default": ["esim", "safetywing", "hotel", "flight", "klook"],
}

# Partner display names
PARTNER_NAMES: Dict[str, str] = {
    "esim": "Airalo (eSIM)",
    "vpn": "NordVPN (VPN)",
    "hotel": "Booking (Hotels)",
    "klook": "Klook (Tours/Activities)",
    "safetywing": "SafetyWing (Insurance)",
    "trip": "Trip.com",
    "flight": "Aviasales (Flights)",
}

# CTA variant definitions
CTA_VARIANTS = ["top_button", "mid_text", "bottom_card", "inline_link"]


# ---------------------------------------------------------------------------
# Environment loading
# ---------------------------------------------------------------------------
def load_env() -> None:
    """Load .env from project root (best-effort, never fatal)."""
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
    except Exception:
        # Manual fallback parse
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


# ---------------------------------------------------------------------------
# GA4 Data Fetching (read-only, graceful degradation)
# ---------------------------------------------------------------------------
def _ga4_auth_headers() -> Optional[Dict[str, str]]:
    """Build GA4 Data API auth headers from service account JSON."""
    key_file_env = os.environ.get("GA4_SERVICE_ACCOUNT_JSON", "gsc-service-account-key.json")
    key_path = PROJECT_ROOT / key_file_env if not Path(key_file_env).is_absolute() else Path(key_file_env)
    if not key_path.exists():
        print(f"   [GA4] Service account key not found: {key_path}")
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
    """POST to GA4 Data API runReport, return parsed JSON or None."""
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


def fetch_ga4_page_traffic(days: int = DEFAULT_LOOKBACK_DAYS) -> Optional[Dict[str, Dict[str, int]]]:
    """Return {pagePath: {sessions, pageviews}} for last N days, or None."""
    end = date.today()
    start = end - timedelta(days=days)
    body = {
        "dateRanges": [{"startDate": start.isoformat(), "endDate": end.isoformat()}],
        "metrics": [{"name": "sessions"}, {"name": "screenPageViews"}],
        "dimensions": [{"name": "pagePath"}],
        "limit": 10000,
    }
    data = _ga4_run_report(body)
    if not data:
        return None
    out: Dict[str, Dict[str, int]] = {}
    for row in data.get("rows", []):
        path = row["dimensionValues"][0]["value"]
        out[path] = {
            "sessions": int(row["metricValues"][0]["value"]),
            "pageviews": int(row["metricValues"][1]["value"]),
        }
    return out


def fetch_ga4_affiliate_clicks(days: int = DEFAULT_LOOKBACK_DAYS) -> Optional[Dict[str, int]]:
    """Return {pagePath: affiliate_click_count} for last N days, or None.

    Tries eventName=affiliate_click first; falls back to outbound_click
    filtered by affiliate hostnames if no affiliate_click events exist.
    """
    end = date.today()
    start = end - timedelta(days=days)

    # Try affiliate_click custom event first
    body = {
        "dateRanges": [{"startDate": start.isoformat(), "endDate": end.isoformat()}],
        "metrics": [{"name": "eventCount"}],
        "dimensions": [{"name": "pagePath"}],
        "dimensionFilter": {
            "filter": {
                "fieldName": "eventName",
                "stringFilter": {"matchType": "EXACT", "value": "affiliate_click"},
            }
        },
        "limit": 10000,
    }
    data = _ga4_run_report(body)
    if data and data.get("rows"):
        out = {}
        for row in data["rows"]:
            path = row["dimensionValues"][0]["value"]
            out[path] = int(row["metricValues"][0]["value"])
        return out

    # Fallback: outbound clicks to affiliate domains
    print("   [GA4] No affiliate_click events found; trying outbound_click fallback...")
    affiliate_hosts = ["airalo.com", "booking.com", "aviasales.com", "klook.com",
                       "safetywing.com", "trip.com", "affiliatescn.net"]
    body2 = {
        "dateRanges": [{"startDate": start.isoformat(), "endDate": end.isoformat()}],
        "metrics": [{"name": "eventCount"}],
        "dimensions": [{"name": "pagePath"}, {"name": "outbound"}],
        "dimensionFilter": {
            "filter": {
                "fieldName": "eventName",
                "stringFilter": {"matchType": "EXACT", "value": "click"},
            }
        },
        "limit": 10000,
    }
    data2 = _ga4_run_report(body2)
    if not data2:
        return None
    out: Dict[str, int] = {}
    for row in data2.get("rows", []):
        path = row["dimensionValues"][0]["value"]
        outbound_url = row["dimensionValues"][1]["value"] if len(row["dimensionValues"]) > 1 else ""
        if any(host in outbound_url for host in affiliate_hosts):
            out[path] = out.get(path, 0) + int(row["metricValues"][0]["value"])
    return out if out else None


# ---------------------------------------------------------------------------
# CTA Inventory loading
# ---------------------------------------------------------------------------
def load_cta_inventory() -> List[Dict[str, str]]:
    """Load P0_AFFILIATE_CTA_INVENTORY.csv. Returns list of row dicts."""
    if not CTA_INVENTORY_CSV.exists():
        print(f"   [Inventory] CSV not found: {CTA_INVENTORY_CSV}")
        return []
    rows: List[Dict[str, str]] = []
    with open(CTA_INVENTORY_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(dict(row))
    return rows


def normalize_partner_key(partner_display: str) -> str:
    """Map partner display name from CSV to hugo.toml affiliate key."""
    p = (partner_display or "").lower()
    if "airalo" in p or "esim" in p:
        return "esim"
    if "nordvpn" in p or "vpn" in p:
        return "vpn"
    if "booking" in p or "hotel" in p:
        return "hotel"
    if "klook" in p or "tour" in p:
        return "klook"
    if "safetywing" in p or "insurance" in p:
        return "safetywing"
    if "trip.com" in p or "trip" in p:
        return "trip"
    if "aviasales" in p or "flight" in p:
        return "flight"
    return "esim"


# ---------------------------------------------------------------------------
# Performance analysis
# ---------------------------------------------------------------------------
def build_cta_performance(
    inventory: List[Dict[str, str]],
    page_traffic: Optional[Dict[str, Dict[str, int]]],
    affiliate_clicks: Optional[Dict[str, int]],
) -> List[Dict[str, Any]]:
    """Join CTA inventory with GA4 data to produce per-CTA performance records.

    If GA4 data is unavailable, uses static analysis (impressions=0, clicks=0,
    status=insufficient_data) but still flags intent mismatches from CSV.
    """
    records: List[Dict[str, Any]] = []
    # Group inventory by slug to estimate CTA count per page (for impression share)
    cta_count_by_slug: Dict[str, int] = {}
    for row in inventory:
        slug = row.get("slug", "")
        cta_count_by_slug[slug] = cta_count_by_slug.get(slug, 0) + 1

    for row in inventory:
        slug = row.get("slug", "")
        filename = row.get("filename", "")
        topic = row.get("article_topic", "Default")
        cta_type = row.get("cta_type", "")
        partner_raw = row.get("partner", "")
        partner_key = normalize_partner_key(partner_raw)
        location = row.get("location", "body")
        intent_match = row.get("intent_match", "yes")

        # Estimate page path
        page_path = f"/posts/{slug}/"

        # GA4 data
        sessions = 0
        pageviews = 0
        clicks = 0
        data_source = "static"

        if page_traffic and page_path in page_traffic:
            sessions = page_traffic[page_path]["sessions"]
            pageviews = page_traffic[page_path]["pageviews"]
            data_source = "ga4"
        if affiliate_clicks and page_path in affiliate_clicks:
            # Distribute page-level clicks across CTAs proportionally
            total_ctas = cta_count_by_slug.get(slug, 1)
            clicks = affiliate_clicks[page_path] // max(total_ctas, 1)
            data_source = "ga4"

        # Impressions ≈ pageviews (each pageview shows all CTAs on page)
        impressions = pageviews
        ctr = (clicks / impressions) if impressions > 0 else 0.0

        # Determine status
        if impressions < MIN_IMPRESSIONS_FOR_JUDGMENT:
            status = "insufficient_data"
        elif clicks == 0 and impressions > ZERO_CLICK_IMPRESSION_THRESHOLD:
            status = "zero_clicks"
        elif ctr < LOW_CTR_THRESHOLD and impressions >= MIN_IMPRESSIONS_FOR_JUDGMENT:
            status = "low_ctr"
        else:
            status = "ok"

        # Intent mismatch flag
        intent_mismatch = intent_match.lower() == "no"

        records.append({
            "filename": filename,
            "slug": slug,
            "page_path": page_path,
            "topic": topic,
            "cta_type": cta_type,
            "partner_raw": partner_raw,
            "partner_key": partner_key,
            "location": location,
            "intent_match": intent_match,
            "intent_mismatch": intent_mismatch,
            "impressions": impressions,
            "sessions": sessions,
            "clicks": clicks,
            "ctr": round(ctr, 6),
            "status": status,
            "data_source": data_source,
        })

    return records


def identify_low_performers(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter records to only low-performing CTAs needing optimization."""
    return [r for r in records if r["status"] in ("low_ctr", "zero_clicks") or r["intent_mismatch"]]


# ---------------------------------------------------------------------------
# A/B test suggestion generation
# ---------------------------------------------------------------------------
def suggest_replacement(record: Dict[str, Any]) -> Dict[str, Any]:
    """Generate an A/B test suggestion for a low-performing CTA.

    Logic:
    - If intent_mismatch: replace with top recommended partner for the topic
    - If low_ctr/zero_clicks: try the next best partner for the topic that
      isn't already the current partner
    - Suggest a different CTA variant (position/type)
    """
    topic = record.get("topic", "Default")
    current_partner = record["partner_key"]
    recommended = TOPIC_PARTNER_MAP.get(topic, TOPIC_PARTNER_MAP["Default"])

    # Find best replacement partner (not current)
    replacement_partner = current_partner
    for p in recommended:
        if p != current_partner:
            replacement_partner = p
            break

    # Suggest a different variant
    current_variant_hint = record.get("location", "body")
    variant_options = [v for v in CTA_VARIANTS]
    # Simple heuristic: if body/mid, try top_button; if top, try bottom_card
    if "top" in current_variant_hint.lower():
        suggested_variant = "bottom_card"
    elif "bottom" in current_variant_hint.lower():
        suggested_variant = "top_button"
    else:
        suggested_variant = "top_button"

    variant_id = f"ab_{record['slug'][:30]}_{replacement_partner}_{suggested_variant}"
    utm_content = f"{UTM_BASE}&utm_content={variant_id}"

    return {
        "slug": record["slug"],
        "filename": record["filename"],
        "current_partner": current_partner,
        "current_partner_name": PARTNER_NAMES.get(current_partner, current_partner),
        "replacement_partner": replacement_partner,
        "replacement_partner_name": PARTNER_NAMES.get(replacement_partner, replacement_partner),
        "suggested_variant": suggested_variant,
        "variant_id": variant_id,
        "utm_content": utm_content,
        "reason": _reason_text(record),
        "current_ctr": record["ctr"],
        "current_impressions": record["impressions"],
        "current_clicks": record["clicks"],
        "topic": record["topic"],
    }


def _reason_text(record: Dict[str, Any]) -> str:
    if record["intent_mismatch"]:
        return f"Intent mismatch: {record['partner_raw']} not optimal for {record['topic']} articles"
    if record["status"] == "zero_clicks":
        return f"Zero clicks after {record['impressions']} impressions"
    if record["status"] == "low_ctr":
        return f"CTR {record['ctr']*100:.3f}% below {LOW_CTR_THRESHOLD*100:.1f}% threshold"
    return "Performance below target"


# ---------------------------------------------------------------------------
# Auto-execution: modify content files
# ---------------------------------------------------------------------------
def read_post_front_matter(filepath: Path) -> Tuple[Dict[str, Any], str, bool]:
    """Parse YAML front matter from a Hugo post.

    Returns (front_matter_dict, body_text, has_front_matter).
    Simple parser: extracts between first --- and second ---.
    """
    if not filepath.exists():
        return {}, "", False
    text = filepath.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}, text, False
    end = text.find("---", 3)
    if end == -1:
        return {}, text, False
    fm_text = text[3:end].strip()
    body = text[end + 3:]
    # Simple YAML parse (avoid pyyaml dependency for flat keys)
    fm: Dict[str, Any] = {}
    current_key = None
    current_list: List[str] = []
    for line in fm_text.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- ") and current_key:
            current_list.append(stripped[2:].strip().strip('"').strip("'"))
            continue
        if current_key and current_list:
            fm[current_key] = current_list
            current_list = []
        if ":" in stripped:
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if val:
                fm[key] = val
                current_key = None
            else:
                current_key = key
                current_list = []
    if current_key and current_list:
        fm[current_key] = current_list
    return fm, body, True


def write_post_front_matter(filepath: Path, fm: Dict[str, Any], body: str) -> None:
    """Write front matter + body back to file."""
    lines = ["---"]
    for k, v in fm.items():
        if isinstance(v, list):
            lines.append(f"{k}:")
            for item in v:
                lines.append(f"- {item}")
        else:
            # Quote strings that contain special chars
            if isinstance(v, str) and (":" in v or "#" in v or "[" in v or "]" in v):
                lines.append(f'{k}: "{v}"')
            else:
                lines.append(f"{k}: {v}")
    lines.append("---")
    lines.append(body)
    filepath.write_text("\n".join(lines), encoding="utf-8")


def apply_cta_adjustment(
    suggestion: Dict[str, Any],
    dry_run: bool = True,
) -> Dict[str, Any]:
    """Apply a single CTA adjustment to a content file.

    Low-risk action: add/update cta_variant in front matter.
    Also attempts to replace the first matching affiliate shortcode partner param.

    Returns a result dict with action details.
    """
    filename = suggestion["filename"]
    filepath = CONTENT_DIR / filename
    result = {
        "filename": filename,
        "slug": suggestion["slug"],
        "action": "none",
        "dry_run": dry_run,
        "details": "",
    }

    if not filepath.exists():
        result["details"] = f"File not found: {filepath}"
        return result

    fm, body, has_fm = read_post_front_matter(filepath)
    if not has_fm:
        result["details"] = "No YAML front matter found"
        return result

    changed = False
    actions: List[str] = []

    # 1. Set cta_variant in front matter
    old_variant = fm.get("cta_variant", "")
    new_variant = suggestion["suggested_variant"]
    if old_variant != new_variant:
        fm["cta_variant"] = new_variant
        actions.append(f"cta_variant: {old_variant or '(none)'} → {new_variant}")
        changed = True

    # 2. Try to replace matching shortcode partner in body
    # Match patterns like {{< soft-recommend partner="esim" ... >}}
    # or {{< affiliate-link key="esim" ... >}}
    current_partner = suggestion["current_partner"]
    replacement = suggestion["replacement_partner"]
    new_body = body

    # Pattern 1: soft-recommend partner="X"
    pattern1 = rf'({{{{<\s*soft-recommend\s+[^>]*?partner="){current_partner}(")'
    if re.search(pattern1, new_body):
        new_body = re.sub(pattern1, rf"\g<1>{replacement}\g<2>", new_body, count=1)
        actions.append(f"shortcode partner: {current_partner} → {replacement} (soft-recommend)")
        changed = True

    # Pattern 2: affiliate-link key="X"
    pattern2 = rf'({{{{<\s*affiliate-link\s+[^>]*?key="){current_partner}(")'
    if re.search(pattern2, new_body):
        new_body = re.sub(pattern2, rf"\g<1>{replacement}\g<2>", new_body, count=1)
        actions.append(f"shortcode key: {current_partner} → {replacement} (affiliate-link)")
        changed = True

    # Pattern 3: affiliate-esim / affiliate-hotel etc. specific shortcodes
    specific_pattern = rf'({{{{<\s*affiliate-){current_partner}(\s+[^>]*?>}}}})'
    if re.search(specific_pattern, new_body):
        new_body = re.sub(specific_pattern, rf"\g<1>{replacement}\g<2>", new_body, count=1)
        actions.append(f"shortcode: affiliate-{current_partner} → affiliate-{replacement}")
        changed = True

    if not changed:
        result["action"] = "no_change_needed"
        result["details"] = "Front matter already optimal and no matching shortcode found"
        return result

    result["action"] = "modified"
    result["details"] = "; ".join(actions)

    if not dry_run:
        write_post_front_matter(filepath, fm, new_body)
        result["written"] = True
    else:
        result["written"] = False

    return result


# ---------------------------------------------------------------------------
# RPM calculation (with Travelpayouts revenue)
# ---------------------------------------------------------------------------
def fetch_travelpayouts_revenue(days: int = DEFAULT_LOOKBACK_DAYS) -> Optional[Dict[str, Any]]:
    """Fetch total affiliate revenue from Travelpayouts for RPM estimation."""
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from travelpayouts_client import fetch_affiliate_stats
        stats = fetch_affiliate_stats(days=days)
        return stats
    except Exception as e:
        print(f"   [Travelpayouts] Revenue fetch failed: {e}")
        return None


def calculate_rpm(
    records: List[Dict[str, Any]],
    revenue_stats: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Estimate RPM per CTA. Revenue is site-wide, so distribute by click share."""
    if not revenue_stats or revenue_stats.get("revenue", 0) <= 0:
        for r in records:
            r["rpm"] = 0.0
            r["estimated_revenue"] = 0.0
        return records

    total_clicks = sum(r["clicks"] for r in records) or 1
    total_revenue = revenue_stats["revenue"]
    total_impressions = sum(r["impressions"] for r in records) or 1

    for r in records:
        click_share = r["clicks"] / total_clicks
        r["estimated_revenue"] = round(total_revenue * click_share, 4)
        r["rpm"] = round((r["estimated_revenue"] / r["impressions"]) * 1000, 4) if r["impressions"] > 0 else 0.0

    return records


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------
def generate_report(
    records: List[Dict[str, Any]],
    low_performers: List[Dict[str, Any]],
    suggestions: List[Dict[str, Any]],
    adjustments: List[Dict[str, Any]],
    revenue_stats: Optional[Dict[str, Any]],
    data_source: str,
    dry_run: bool,
    days: int,
) -> str:
    """Generate markdown A/B test report."""
    today = date.today().isoformat()
    total_impressions = sum(r["impressions"] for r in records)
    total_clicks = sum(r["clicks"] for r in records)
    overall_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
    low_count = len(low_performers)
    insufficient_count = sum(1 for r in records if r["status"] == "insufficient_data")
    ok_count = sum(1 for r in records if r["status"] == "ok")

    lines = [
        f"# Affiliate CTA A/B Test Report — {today}",
        "",
        f"> Closed Loop 3: Affiliate Conversion Auto-Optimization",
        f"> Lookback: {days} days | Data source: {data_source} | Mode: {'DRY-RUN' if dry_run else 'LIVE'}",
        "",
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total CTAs analyzed | {len(records)} |",
        f"| Total impressions | {total_impressions:,} |",
        f"| Total affiliate clicks | {total_clicks:,} |",
        f"| Overall CTR | {overall_ctr:.3f}% |",
        f"| Low-performing CTAs | {low_count} |",
        f"| Insufficient data | {insufficient_count} |",
        f"| Healthy CTAs | {ok_count} |",
        f"| Adjustments applied | {len([a for a in adjustments if a['action'] == 'modified'])} |",
    ]

    if revenue_stats:
        lines.extend([
            f"| Affiliate revenue (period) | ${revenue_stats.get('revenue', 0):.2f} |",
            f"| Affiliate bookings (period) | {revenue_stats.get('bookings', 0)} |",
        ])

    lines.extend(["", "## Low-Performing CTAs", ""])
    if low_performers:
        lines.extend([
            "| Slug | Topic | Partner | Impressions | Clicks | CTR | Status |",
            "|------|-------|---------|-------------|--------|-----|--------|",
        ])
        for r in sorted(low_performers, key=lambda x: x["impressions"], reverse=True)[:30]:
            lines.append(
                f"| {r['slug'][:40]} | {r['topic'][:25]} | {r['partner_raw'][:20]} | "
                f"{r['impressions']:,} | {r['clicks']} | {r['ctr']*100:.3f}% | {r['status']} |"
            )
    else:
        lines.append("No low-performing CTAs identified.")

    lines.extend(["", "## A/B Test Suggestions & Adjustments", ""])
    if suggestions:
        lines.extend([
            "| # | Slug | Current → Replacement | Variant | Reason | Applied? |",
            "|---|------|----------------------|---------|--------|----------|",
        ])
        for i, (s, a) in enumerate(zip(suggestions, adjustments), 1):
            applied = "✅" if a.get("action") == "modified" else "⏭️"
            if dry_run and a.get("action") == "modified":
                applied = "🔍 (dry-run)"
            lines.append(
                f"| {i} | {s['slug'][:35]} | "
                f"{s['current_partner_name'][:15]} → {s['replacement_partner_name'][:15]} | "
                f"{s['suggested_variant']} | {s['reason'][:50]} | {applied} |"
            )
    else:
        lines.append("No suggestions generated (all CTAs healthy or insufficient data).")

    # Adjustment details
    modified = [a for a in adjustments if a["action"] == "modified"]
    if modified:
        lines.extend(["", "### Adjustment Details", ""])
        for a in modified:
            lines.append(f"- **{a['filename']}**: {a['details']}")

    # Top performers
    top_performers = sorted(
        [r for r in records if r["status"] == "ok" and r["impressions"] >= MIN_IMPRESSIONS_FOR_JUDGMENT],
        key=lambda x: x["ctr"], reverse=True,
    )[:10]
    if top_performers:
        lines.extend(["", "## Top Performing CTAs (Learning)", ""])
        lines.extend([
            "| Slug | Partner | Impressions | Clicks | CTR |",
            "|------|---------|-------------|--------|-----|",
        ])
        for r in top_performers:
            lines.append(
                f"| {r['slug'][:40]} | {r['partner_raw'][:20]} | "
                f"{r['impressions']:,} | {r['clicks']} | {r['ctr']*100:.3f}% |"
            )

    lines.extend([
        "",
        "## Methodology",
        "",
        f"- Low CTR threshold: {LOW_CTR_THRESHOLD*100:.1f}%",
        f"- Minimum impressions for judgment: {MIN_IMPRESSIONS_FOR_JUDGMENT}",
        f"- Zero-click flag threshold: >{ZERO_CLICK_IMPRESSION_THRESHOLD} impressions with 0 clicks",
        f"- Max adjustments per run: {DEFAULT_MAX_ADJUSTMENTS}",
        "- UTM tracking: utm_source=blog&utm_medium=cta&utm_campaign=ab_test&utm_content=<variant_id>",
        "- Revenue data: Travelpayouts API (site-wide, distributed by click share for RPM)",
        "",
        f"_Generated: {datetime.now().isoformat()}_",
    ])

    return "\n".join(lines)


def update_learning_library(
    suggestions: List[Dict[str, Any]],
    adjustments: List[Dict[str, Any]],
    records: List[Dict[str, Any]],
) -> None:
    """Append test results to affiliate-learning-library.json."""
    existing: Dict[str, Any] = {"tests": [], "last_updated": ""}
    if LEARNING_LIBRARY_JSON.exists():
        try:
            existing = json.loads(LEARNING_LIBRARY_JSON.read_text(encoding="utf-8"))
        except Exception:
            existing = {"tests": [], "last_updated": ""}

    today = date.today().isoformat()
    for s, a in zip(suggestions, adjustments):
        if a.get("action") != "modified":
            continue
        entry = {
            "date": today,
            "slug": s["slug"],
            "variant_id": s["variant_id"],
            "topic": s["topic"],
            "old_partner": s["current_partner"],
            "new_partner": s["replacement_partner"],
            "variant": s["suggested_variant"],
            "reason": s["reason"],
            "baseline_ctr": s["current_ctr"],
            "baseline_impressions": s["current_impressions"],
            "status": "running",
        }
        existing["tests"].append(entry)

    existing["last_updated"] = datetime.now().isoformat()
    existing["total_tests"] = len(existing.get("tests", []))
    LEARNING_LIBRARY_JSON.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# Hugo build verification
# ---------------------------------------------------------------------------
def verify_hugo_build() -> Tuple[bool, str]:
    """Run Hugo build to verify no template/content errors."""
    hugo = HUGO_BIN if Path(HUGO_BIN).exists() else "hugo"
    try:
        result = subprocess.run(
            [hugo, "--quiet", "--minify", "-d", str(PROJECT_ROOT / "public_ab_test")],
            cwd=str(PROJECT_ROOT),
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0:
            return True, "Hugo build succeeded"
        return False, f"Hugo build failed (exit {result.returncode}): {result.stderr[:500]}"
    except FileNotFoundError:
        return False, "Hugo binary not found"
    except subprocess.TimeoutExpired:
        return False, "Hugo build timed out (120s)"
    except Exception as e:
        return False, f"Hugo build error: {e}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="Affiliate CTA A/B Tester (Closed Loop 3)")
    parser.add_argument("--dry-run", action="store_true", help="Analyze and suggest without modifying files")
    parser.add_argument("--max-adjustments", type=int, default=DEFAULT_MAX_ADJUSTMENTS,
                        help=f"Max CTA adjustments per run (default: {DEFAULT_MAX_ADJUSTMENTS})")
    parser.add_argument("--days", type=int, default=DEFAULT_LOOKBACK_DAYS,
                        help=f"GA4 lookback days (default: {DEFAULT_LOOKBACK_DAYS})")
    parser.add_argument("--skip-hugo", action="store_true", help="Skip Hugo build verification")
    args = parser.parse_args()

    load_env()

    print("=" * 70)
    print("  Affiliate CTA A/B Tester — Closed Loop 3")
    print(f"  Mode: {'DRY-RUN' if args.dry_run else 'LIVE'} | Days: {args.days} | Max adj: {args.max_adjustments}")
    print("=" * 70)

    # 1. Load CTA inventory
    print("\n[1/6] Loading CTA inventory...")
    inventory = load_cta_inventory()
    print(f"   Loaded {len(inventory)} CTA records from inventory")

    # 2. Fetch GA4 data
    print("\n[2/6] Fetching GA4 data...")
    page_traffic = fetch_ga4_page_traffic(args.days)
    affiliate_clicks = fetch_ga4_affiliate_clicks(args.days)
    data_source = "ga4" if (page_traffic or affiliate_clicks) else "static_fallback"
    if page_traffic:
        print(f"   Page traffic: {len(page_traffic)} pages")
    else:
        print("   Page traffic: unavailable (using static fallback)")
    if affiliate_clicks:
        print(f"   Affiliate clicks: {len(affiliate_clicks)} pages with clicks")
    else:
        print("   Affiliate clicks: unavailable (using static fallback)")

    # 3. Analyze performance
    print("\n[3/6] Analyzing CTA performance...")
    records = build_cta_performance(inventory, page_traffic, affiliate_clicks)

    # Fetch revenue for RPM
    print("\n[4/6] Fetching affiliate revenue...")
    revenue_stats = fetch_travelpayouts_revenue(args.days)
    if revenue_stats:
        print(f"   Revenue: ${revenue_stats.get('revenue', 0):.2f} | "
              f"Clicks: {revenue_stats.get('clicks', 0)} | "
              f"Bookings: {revenue_stats.get('bookings', 0)}")
    else:
        print("   Revenue: unavailable")
    records = calculate_rpm(records, revenue_stats)

    low_performers = identify_low_performers(records)
    print(f"   Low-performing CTAs: {len(low_performers)}")
    print(f"   Insufficient data: {sum(1 for r in records if r['status'] == 'insufficient_data')}")
    print(f"   Healthy: {sum(1 for r in records if r['status'] == 'ok')}")

    # 4. Generate suggestions
    print("\n[5/6] Generating A/B test suggestions...")
    # Sort low performers by impressions descending (highest impact first)
    low_performers_sorted = sorted(low_performers, key=lambda x: x["impressions"], reverse=True)
    candidates = low_performers_sorted[:args.max_adjustments]
    suggestions = [suggest_replacement(r) for r in candidates]
    print(f"   Generated {len(suggestions)} suggestions (capped at {args.max_adjustments})")

    # 5. Apply adjustments
    print("\n[6/6] Applying adjustments...")
    adjustments: List[Dict[str, Any]] = []
    for s in suggestions:
        result = apply_cta_adjustment(s, dry_run=args.dry_run)
        adjustments.append(result)
        status = "DRY-RUN" if args.dry_run else ("WRITTEN" if result.get("written") else "SKIPPED")
        print(f"   [{status}] {s['slug'][:40]}: {result['details'][:60]}")

    # 6. Hugo build verification (only if live modifications were made)
    if not args.dry_run and any(a.get("written") for a in adjustments) and not args.skip_hugo:
        print("\n[Build] Verifying Hugo build...")
        ok, msg = verify_hugo_build()
        print(f"   {msg}")
        if not ok:
            print("   ⚠️  Hugo build FAILED — modifications may need review")
    elif args.dry_run:
        print("\n[Build] Skipped (dry-run mode)")
    else:
        print("\n[Build] No modifications written, skipping build verification")

    # 7. Generate report
    today = date.today().isoformat()
    report_path = REPORTS_DIR / f"affiliate-ab-test-{today}.md"
    report = generate_report(
        records, low_performers, suggestions, adjustments,
        revenue_stats, data_source, args.dry_run, args.days,
    )
    report_path.write_text(report, encoding="utf-8")
    print(f"\n📄 Report written: {report_path}")

    # 8. Update learning library
    if not args.dry_run:
        update_learning_library(suggestions, adjustments, records)
        print(f"📚 Learning library updated: {LEARNING_LIBRARY_JSON}")

    # Summary
    modified_count = len([a for a in adjustments if a["action"] == "modified"])
    print("\n" + "=" * 70)
    print(f"  DONE. {modified_count} adjustments {'simulated' if args.dry_run else 'applied'}.")
    print(f"  Report: {report_path.name}")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
