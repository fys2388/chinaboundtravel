#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P1-GROWTH-14A: Affiliate Funnel CTA Inventory Engine.

Scans all published posts and produces a deterministic CTA inventory used
by the affiliate funnel measurement layer:

  reports/revenue/AFFILIATE_FUNNEL_INVENTORY.csv

Fields:
  content_id, url, partner, cta_type, placement, tracking_event,
  utm_source, utm_campaign

Event model (GA4, P1-GROWTH-14A):
  affiliate_impression - CTA visible in viewport (once per placement)
  affiliate_click      - CTA clicked (compatible with previous model)
  affiliate_outbound   - confirms whether the click actually left the site

Rules:
  - read-only: never modifies content, URLs, UTM or affiliate IDs
  - deterministic ordering (content_id, url, partner, placement)
  - revenue stays NULL; never fabricated
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

BLOG_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent
POSTS = BLOG_ROOT / "content" / "posts"
OUT = BLOG_ROOT / "reports" / "revenue"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(SCRIPTS))

from affiliate_gap_detector import PARTNER_DEFS, SITE_PREFIX, parse_front_matter  # noqa: E402

# CTA types recognized by the funnel audit.
CTA_MID = "MID_CTA"          # {{< affiliate-mid-cta ... >}} (REV001 style)
CTA_SHORTCODE = "SHORTCODE"  # {{< affiliate-esim/affiliate-link/... >}}
CTA_AB = "AB_CTA"            # {{< ab-cta affiliate_key=... >}}
CTA_INLINE = "INLINE"        # raw affiliate URL inside markdown body
CTA_TEMPLATE = "TEMPLATE"    # site-wide article affiliate section (single.html)

EVENT_FULL = "affiliate_impression|affiliate_click|affiliate_outbound"
EVENT_CLICK = "affiliate_click"

# Shortcode name -> brand (shortcodes render template-driven affiliate URLs).
SHORTCODE_BRAND = {
    "esim": "Airalo",
    "flight": "Aviasales",
    "hotel": "Booking",
    "tour": "Klook",
    "insurance": "SafetyWing",
}

SHORTCODE_PARTNER_RE = re.compile(r"\{\{<\s*affiliate-([a-z]+)\b")
MID_CTA_RE = re.compile(r"\{\{<\s*affiliate-mid-cta\b([^>]*)>")
AB_CTA_RE = re.compile(r"\{\{<\s*ab-cta\b([^>]*)>")
AFF_LINK_RE = re.compile(r"\{\{<\s*affiliate-link\b([^>]*)>")
ATTR_RE = re.compile(r'(\w+)\s*=\s*"([^"]*)"')


def _attr(attrs_text: str, key: str) -> str:
    m = ATTR_RE.search(attrs_text, re.I)
    while m:
        if m.group(1).lower() == key:
            return m.group(2)
        m = ATTR_RE.search(attrs_text, m.end())
    return ""


def _url_from_fm(fm: dict, filename: str) -> str:
    url = (fm.get("url") or "").strip()
    if url:
        return url if url.startswith("http") else f"{SITE_PREFIX}{url}"
    slug = (fm.get("slug") or "").strip() or Path(filename).stem
    return f"{SITE_PREFIX}/posts/{slug}/"


def _utm_from_url(raw_url: str) -> tuple:
    """Extract (utm_source, utm_campaign) from a URL query string."""
    if "?" not in raw_url:
        return "", ""
    q = raw_url.split("?", 1)[1]
    source = ""
    campaign = ""
    for pair in q.split("&"):
        if "=" not in pair:
            continue
        k, v = pair.split("=", 1)
        if k.lower() == "utm_source":
            source = v
        elif k.lower() == "utm_campaign":
            campaign = v
    return source, campaign


def _brand(key: str) -> str:
    pdef = PARTNER_DEFS.get(key)
    return pdef["brand"] if pdef else key.title()


def scan_post(text: str) -> list:
    """Return per-CTA rows for one post body (deterministic order)."""
    rows = []
    # mid-content CTA (REV001): partner + placement from shortcode args
    for m in MID_CTA_RE.finditer(text):
        partner = _attr(m.group(1), "partner") or "hotel"
        placement = _attr(m.group(1), "placement") or "article_mid_cta"
        key = _attr(m.group(1), "key") or partner
        rows.append({
            "partner": _brand(key),
            "cta_type": CTA_MID,
            "placement": placement,
            "tracking_event": EVENT_FULL,
            "raw_url": "",
        })
    # ab-cta (variant CTA component): partner from affiliate_key
    for m in AB_CTA_RE.finditer(text):
        key = _attr(m.group(1), "affiliate_key")
        placement = f"ab_cta_{_attr(m.group(1), 'test_id') or 'default'}"
        rows.append({
            "partner": _brand(key) if key else "Unknown",
            "cta_type": CTA_AB,
            "placement": placement,
            "tracking_event": EVENT_CLICK,
            "raw_url": "",
        })
    # generic affiliate-* shortcodes (affiliate-esim, affiliate-hotel, ...)
    for m in SHORTCODE_PARTNER_RE.finditer(text):
        key = m.group(1)
        if key in ("link", "mid", "section", "disclosure"):
            continue
        rows.append({
            "partner": SHORTCODE_BRAND.get(key, _brand(key)),
            "cta_type": CTA_SHORTCODE,
            "placement": "article_resource_block",
            "tracking_event": EVENT_FULL,
            "raw_url": "",
        })
    # inline affiliate URLs in the body
    for raw in re.findall(r"https?://[^\s\"'<>)\]]+", text):
        u = raw.rstrip(".,;")
        low = u.lower()
        matched = None
        for key, pdef in PARTNER_DEFS.items():
            if key in ("vpn", "vpnNord"):
                continue
            if pdef["tracking_marker"] in low:
                matched = key
                break
        if matched is None and "affiliatescn" in low:
            matched = "vpn"
        if matched is None:
            continue
        src, camp = _utm_from_url(u)
        rows.append({
            "partner": _brand(matched),
            "cta_type": CTA_INLINE,
            "placement": "inline",
            "tracking_event": EVENT_CLICK,
            "raw_url": u,
        })
    return rows


def build_inventory(posts_dir: Path = POSTS) -> list:
    """Scan all published posts; return sorted funnel inventory rows."""
    rows = []
    for f in sorted(posts_dir.glob("*.md")):
        text = f.read_text(encoding="utf-8", errors="replace")
        fm = parse_front_matter(text)
        if str(fm.get("draft", "")).strip().lower() in ("true", "yes"):
            continue
        cid = (fm.get("content_id") or "").strip()
        url = _url_from_fm(fm, f.name)
        for cta in scan_post(text):
            src, camp = _utm_from_url(cta["raw_url"]) if cta["raw_url"] else ("", "")
            rows.append({
                "content_id": cid,
                "url": url,
                "partner": cta["partner"],
                "cta_type": cta["cta_type"],
                "placement": cta["placement"],
                "tracking_event": cta["tracking_event"],
                "utm_source": src,
                "utm_campaign": camp,
            })
    rows.sort(key=lambda r: (r["content_id"], r["url"], r["partner"], r["cta_type"], r["placement"]))
    return rows


def write_inventory(rows: list, out: Path = None) -> Path:
    out = out or (OUT / "AFFILIATE_FUNNEL_INVENTORY.csv")
    fieldnames = ["content_id", "url", "partner", "cta_type", "placement",
                  "tracking_event", "utm_source", "utm_campaign"]
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return out


def main():
    rows = build_inventory()
    out = write_inventory(rows)
    print(f"CTA rows: {len(rows)} -> {out.name}")
    from collections import Counter
    by_type = Counter(r["cta_type"] for r in rows)
    by_partner = Counter(r["partner"] for r in rows)
    print("by cta_type:", dict(by_type))
    print("by partner:", dict(by_partner))


if __name__ == "__main__":
    main()
