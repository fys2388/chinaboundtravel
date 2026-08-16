#!/usr/bin/env python3
"""P1-GROWTH-09: Affiliate revenue baseline + attribution gap detector.

Scans the ChinaBound Travel Hugo site to build the first affiliate revenue
baseline:

  - partner inventory (from hugo.toml [params.affiliate] + shortcode usage)
  - per-article content map (content_id -> partner -> placement -> link count)
  - 28d revenue baseline (GA4 affiliate_click counts via Data API; revenue is
    NULL unless a real affiliate revenue API exists - never fabricated)
  - affiliate gap detection (A-E) and commercial page ranking
  - tracking quality check for the affiliate_click event schema

Outputs under reports/revenue/.  Does NOT modify any affiliate URL, UTM,
content, or tracking code.

Design: pure/deterministic analysis functions separated from I/O so tests can
feed fixtures without touching the network.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from dataclasses import dataclass, asdict
from datetime import date, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

BLOG_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent
REPORTS_REVENUE = BLOG_ROOT / "reports" / "revenue"
REPORTS_REVENUE.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(SCRIPTS))

GA4_PROPERTY_ID = "541752321"
GA4_SCOPE = "https://www.googleapis.com/auth/analytics.readonly"
GA4_EVENT = "affiliate_click"

# hugo.toml affiliate key -> brand / partner id markers
PARTNER_DEFS = {
    "esim":      {"brand": "Airalo",        "tracking_marker": "airalo"},
    "vpn":       {"brand": "NordVPN",       "tracking_marker": "affiliatescn"},
    "vpnNord":   {"brand": "NordVPN",       "tracking_marker": "affiliatescn"},
    "nordpass":  {"brand": "NordPass",      "tracking_marker": "nordpass"},
    "hotel":     {"brand": "Booking",       "tracking_marker": "booking"},
    "klook":     {"brand": "Klook",         "tracking_marker": "klook"},
    "safetywing": {"brand": "SafetyWing",   "tracking_marker": "safetywing"},
    "trip":      {"brand": "Trip.com",      "tracking_marker": "trip.com"},
    "flight":    {"brand": "Aviasales",     "tracking_marker": "aviasales"},
    "worldnomads": {"brand": "World Nomads", "tracking_marker": "worldnomads"},
    "allianz":   {"brand": "Allianz",       "tracking_marker": "allianz"},
}

# shortcode -> partner key
SHORTCODE_PARTNER = {
    "affiliate-tour": "klook",
    "affiliate-flight": "flight",
    "affiliate-hotel": "hotel",
    "affiliate-esim": "esim",
    "affiliate-insurance": "safetywing",
}

SITE_PREFIX = "https://www.chinaboundtravel.com"

# ---------------------------------------------------------------------------
# Front matter parsing (no third-party deps)
# ---------------------------------------------------------------------------
def parse_front_matter(text: str) -> dict:
    """Parse YAML (`---`) or TOML (`+++`) front matter into a flat dict."""
    fm = {}
    if text.startswith("\ufeff"):
        text = text[1:]
    if text.startswith("---"):
        sep = "---"
    elif text.startswith("+++"):
        sep = "+++"
    else:
        return fm
    end = text.find("\n" + sep, 3)
    if end == -1:
        return fm
    block = text[3:end]
    for line in block.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)\s*[:=]\s*(.*)$', line)
        if m:
            key, val = m.group(1), m.group(2).strip().strip('"').strip("'")
            fm[key] = val
    return fm


def url_from_front_matter(fm: dict, fname: str) -> str:
    if fm.get("canonicalURL"):
        return fm["canonicalURL"]
    slug = fm.get("slug") or re.sub(r"^\d{4}-\d{2}-\d{2}-", "", Path(fname).stem)
    return f"{SITE_PREFIX}/posts/{slug}/"


# ---------------------------------------------------------------------------
# Content scanning
# ---------------------------------------------------------------------------
def scan_article(text: str) -> dict:
    """Return {inline_urls: {partner: count}, shortcodes: {partner: count},
    ctas: {partner: count}, raw_urls: [url]} found in one article body."""
    out = {"inline_urls": {}, "shortcodes": {}, "ctas": {}, "raw_urls": []}
    for sc, partner in SHORTCODE_PARTNER.items():
        n = len(re.findall(r"\{\{<\s*" + re.escape(sc) + r"\b", text))
        if n:
            out["shortcodes"][partner] = out["shortcodes"].get(partner, 0) + n
    for m in re.finditer(r"\{\{<\s*ab-cta\b([^>]*)>", text):
        attrs = m.group(1)
        km = re.search(r'affiliate_key\s*=\s*"([^"]+)"', attrs)
        key = km.group(1) if km else None
        if key in PARTNER_DEFS:
            out["ctas"][key] = out["ctas"].get(key, 0) + 1
        else:
            out["ctas"]["unknown"] = out["ctas"].get("unknown", 0) + 1
    for m in re.finditer(r"\{\{<\s*affiliate-link\b([^>]*)>", text):
        attrs = m.group(1)
        km = re.search(r'key\s*=\s*"([^"]+)"', attrs)
        key = km.group(1) if km else None
        if key in PARTNER_DEFS:
            out["shortcodes"][key] = out["shortcodes"].get(key, 0) + 1
        else:
            out["shortcodes"]["unknown"] = out["shortcodes"].get("unknown", 0) + 1
    for url in re.findall(r"https?://[^\s\"'<>)\]]+", text):
        u = url.rstrip(".,;")
        out["raw_urls"].append(u)
        for key, pdef in PARTNER_DEFS.items():
            if key in ("vpn", "vpnNord"):
                continue  # aliases handled below
            if pdef["tracking_marker"] in u.lower():
                out["inline_urls"][key] = out["inline_urls"].get(key, 0) + 1
                break
        low = u.lower()
        if "affiliatescn" in low:
            out["inline_urls"]["vpn"] = out["inline_urls"].get("vpn", 0) + 1
    return out


def infer_business_intent(url: str, title: str) -> str:
    hay = f"{url} {title}".lower()
    intent = "GENERAL"
    rules = [
        ("VISA", ["visa", "transit"]),
        ("HOTEL", ["hotel", "accommodation", "stay in", "airbnb"]),
        ("FLIGHT", ["flight", "fly ", "airfare"]),
        ("TRAIN", ["train", "rail", "high-speed", "hsr"]),
        ("INTERNET", ["esim", "sim card", "internet", "wifi", "data plan"]),
        ("VPN", ["vpn"]),
        ("PAYMENT", ["wechat pay", "alipay", "payment", "pay in china", "mobile pay"]),
        ("INSURANCE", ["insurance"]),
        ("TOUR", ["itinerary", "attraction", "tour", "disney", "panda", "great wall"]),
        ("TRANSPORT", ["metro", "subway", "taxi", "transport", "did", "didi"]),
        ("FOOD", ["food", "restaurant", "street food", "market"]),
        ("CITY", ["beijing", "shanghai", "xian", "chengdu", "guangzhou", "shenzhen",
                  "yunnan", "sichuan", "zhangjiajie", "guilin", "hangzhou", "city"]),
    ]
    for name, keys in rules:
        if any(k in hay for k in keys):
            intent = name
            break
    return intent


def classify_placement(kind: str) -> str:
    mapping = {"inline_urls": "INLINE", "shortcodes": "INLINE", "ctas": "CTA",
               "article_cta": "ARTICLE_CTA", "section": "SECTION"}
    return mapping.get(kind, "OTHER")


# ---------------------------------------------------------------------------
# Tracking schema check (single.html / GA4)
# ---------------------------------------------------------------------------
REQUIRED_TRACKING_FIELDS = [
    "content_id", "partner", "placement", "channel", "timestamp", "destination",
]

def tracking_schema_check(single_html: str) -> dict:
    """Verify the affiliate_click event model in layouts/_default/single.html."""
    missing = [f for f in REQUIRED_TRACKING_FIELDS if f not in single_html]
    has_gtag_event = "affiliate_click" in single_html
    has_data_layer = "dataLayer.push" in single_html
    has_article_cta = "data-affiliate-partner" in single_html
    return {
        "event_name": "affiliate_click",
        "fields_present": REQUIRED_TRACKING_FIELDS if not missing else
                          [f for f in REQUIRED_TRACKING_FIELDS if f in single_html],
        "missing_fields": missing,
        "gtag_event": has_gtag_event,
        "data_layer_push": has_data_layer,
        "article_cta_attrs": has_article_cta,
        "status": "OK" if not missing and has_gtag_event and has_data_layer else "TRACKING_GAP",
    }


# ---------------------------------------------------------------------------
# GA4 read (optional, read-only)
# ---------------------------------------------------------------------------
def fetch_affiliate_clicks_ga4(days: int = 28, timeout: int = 25):
    """Return {page_path: count} for GA4 affiliate_click events, or None on failure."""
    try:
        import gsc_utils
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request
        import requests
        info = gsc_utils.load_service_account_info()
        if not info:
            return None
        creds = service_account.Credentials.from_service_account_info(
            info, scopes=[GA4_SCOPE])
        creds.refresh(Request())
        headers = {"Authorization": f"Bearer {creds.token}"}
        end = date.today()
        start = end - timedelta(days=days)
        body = {
            "dateRanges": [{"startDate": start.isoformat(), "endDate": end.isoformat()}],
            "metrics": [{"name": "eventCount"}],
            "dimensions": [{"name": "eventName"}, {"name": "pagePath"}],
            "dimensionFilter": {"filter": {"fieldName": "eventName",
                                           "stringFilter": {"matchType": "EXACT", "value": GA4_EVENT}}},
        }
        r = requests.post(
            f"https://analyticsdata.googleapis.com/v1beta/properties/{GA4_PROPERTY_ID}:runReport",
            headers=headers, json=body, timeout=timeout)
        if r.status_code != 200:
            return None
        out = {}
        for row in r.json().get("rows", []):
            path = row["dimensionValues"][1]["value"] if len(row["dimensionValues"]) > 1 else "/"
            out[path] = int(row["metricValues"][0]["value"])
        return out if out else {}
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Gap / opportunity logic (pure)
# ---------------------------------------------------------------------------
def partner_inventory_rows(articles: list, partner_defs: dict) -> list:
    """Aggregate per-partner counts across articles."""
    rows = []
    for key, pdef in partner_defs.items():
        if key in ("vpn", "vpnNord"):
            continue
        pages = set()
        links = 0
        for a in articles:
            total = sum(a["scans"][k].get(key, 0) for k in ("inline_urls", "shortcodes", "ctas"))
            if total:
                pages.add(a["content_id"])
                links += total
        rows.append({
            "partner": pdef["brand"],
            "affiliate_key": key,
            "pages_count": len(pages),
            "link_count": links,
            "affiliate_id_present": "yes",
            "utm_present": "yes" if key == "safetywing" else "n/a",
            "tracking_present": "yes",
            "status": "ACTIVE",
        })
    return sorted(rows, key=lambda r: (-r["link_count"], r["partner"]))


def content_map_rows(articles: list, partner_defs: dict) -> list:
    rows = []
    for a in articles:
        partners = {}
        for kind in ("inline_urls", "shortcodes", "ctas"):
            for key, n in a["scans"][kind].items():
                brand = partner_defs.get(key, {}).get("brand", key.upper())
                partners[brand] = partners.get(brand, 0) + n
        for brand, n in sorted(partners.items()):
            rows.append({
                "content_id": a["content_id"],
                "title": a["title"],
                "url": a["url"],
                "partner": brand,
                "placement": "INLINE",
                "link_count": n,
            })
    return sorted(rows, key=lambda r: (r["content_id"], r["partner"]))


def _path_of(url: str) -> str:
    """Extract the path part of an absolute URL."""
    return "/" + url.split("://", 1)[-1].split("/", 1)[-1].rstrip("/") + "/"


def baseline_rows(articles: list, partner_defs: dict, ga4_clicks: dict) -> list:
    """Revenue baseline: per-page affiliate clicks from GA4 (path dimension),
    sessions/revenue NULL until a real affiliate/revenue API exists."""
    rows = []
    ga4_map = ga4_clicks or {}
    ga4_available = ga4_clicks is not None
    for a in articles:
        has_affiliate = any(a["scans"][k] for k in ("inline_urls", "shortcodes", "ctas"))
        path = _path_of(a["url"])
        page_clicks = int(ga4_map.get(path, 0))
        rows.append({
            "content_id": a["content_id"],
            "url": a["url"],
            "partner": "ALL" if has_affiliate else "NONE",
            "affiliate_clicks_28d": page_clicks if has_affiliate else 0,
            "affiliate_sessions_28d": "NULL",
            "revenue_28d": "NULL",
            "currency": "USD",
            "status": "NOT_AVAILABLE" if not ga4_available else
                      ("ZERO" if page_clicks == 0 else "MEASURED"),
        })
    return rows


def gap_detection(articles: list, partner_defs: dict) -> list:
    """A: commercial intent + no affiliate; B: affiliate + low visibility;
    C: affiliate + high impressions + low clicks; D: many partners one page;
    E: potential over-monetization (>=5 distinct partners on one page)."""
    gaps = []
    for a in articles:
        distinct = {pdef["brand"] for k, pdef in partner_defs.items()
                    if any(a["scans"][kind].get(k, 0) for kind in ("inline_urls", "shortcodes", "ctas"))}
        high_intent = a["intent"] in ("VISA", "HOTEL", "FLIGHT", "TRAIN", "INTERNET", "VPN", "PAYMENT", "INSURANCE")
        imp = a["gsc"].get("impressions", 0)
        clicks = a["gsc"].get("clicks", 0)
        if high_intent and not distinct:
            gaps.append({"content_id": a["content_id"], "url": a["url"], "type": "A_HIGH_INTENT_NO_AFFILIATE",
                         "detail": f"intent={a['intent']}, impressions={imp}"})
        if distinct and imp == 0:
            gaps.append({"content_id": a["content_id"], "url": a["url"], "type": "B_AFFILIATE_LOW_VISIBILITY",
                         "detail": f"impressions=0, partners={len(distinct)}"})
        if distinct and imp >= 100 and clicks == 0:
            gaps.append({"content_id": a["content_id"], "url": a["url"], "type": "C_HIGH_IMPRESSION_ZERO_CLICK",
                         "detail": f"impressions={imp}, clicks=0, partners={len(distinct)}"})
        if len(distinct) >= 5:
            gaps.append({"content_id": a["content_id"], "url": a["url"], "type": "D_MULTI_PARTNER_PAGE",
                         "detail": f"distinct partners={len(distinct)}"})
        if len(distinct) >= 6:
            gaps.append({"content_id": a["content_id"], "url": a["url"], "type": "E_OVER_MONETIZATION",
                         "detail": f"distinct partners={len(distinct)}"})
    return gaps


def commercial_ranking(articles: list) -> list:
    """Rank commercial pages by search demand + business intent + affiliate presence."""
    ranked = []
    for a in articles:
        imp = a["gsc"].get("impressions", 0)
        has_affiliate = any(a["scans"][k] for k in ("inline_urls", "shortcodes", "ctas"))
        ranked.append({
            "content_id": a["content_id"],
            "url": a["url"],
            "title": a["title"],
            "intent": a["intent"],
            "impressions_28d": imp,
            "clicks_28d": a["gsc"].get("clicks", 0),
            "affiliate_present": "yes" if has_affiliate else "no",
            "commercial_score": round(imp * (2.0 if a["intent"] in
                ("VISA", "HOTEL", "FLIGHT", "TRAIN", "INTERNET", "VPN", "PAYMENT", "INSURANCE") else 1.0), 1),
        })
    ranked.sort(key=lambda r: (-r["commercial_score"], r["url"]))
    return ranked

# ---------------------------------------------------------------------------
# I/O orchestration
# ---------------------------------------------------------------------------
def load_hugo_affiliate(hugo_toml_text: str) -> dict:
    """Parse [params.affiliate] key = "url" pairs from hugo.toml."""
    out = {}
    m = re.search(r"\[params\.affiliate\]\s*\n(.*?)(\n\[|\Z)", hugo_toml_text, re.S)
    if not m:
        return out
    for line in m.group(1).splitlines():
        kv = re.match(r'\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*"([^"]+)"', line)
        if kv:
            out[kv.group(1)] = kv.group(2)
    return out


def load_gsc_page_data(path) -> dict:
    """Return {page_url: {clicks, impressions, ctr, position}} from page_performance.csv."""
    out = {}
    if not Path(path).exists():
        return out
    with open(path, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            out[row["page"]] = {
                "clicks": _num(row.get("clicks")),
                "impressions": _num(row.get("impressions")),
                "ctr": _num(row.get("ctr")),
                "position": _num(row.get("position")),
            }
    return out


def _num(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def load_articles(posts_dir, gsc_data) -> tuple:
    """Return (articles, duplicates). Articles are deduped by canonical URL;
    duplicates are existing repo data-quality issues, recorded for review
    (never modified here)."""
    articles = []
    seen = {}
    duplicates = []
    for f in sorted(Path(posts_dir).glob("*.md")):
        text = f.read_text(encoding="utf-8", errors="replace")
        fm = parse_front_matter(text)
        if fm.get("draft", "").lower() in ("true", "yes"):
            continue
        url = url_from_front_matter(fm, f.name)
        if url in seen:
            duplicates.append({"url": url, "kept": seen[url], "extra": f.name})
            continue
        seen[url] = f.name
        gsc = gsc_data.get(url) or next(
            (v for u, v in gsc_data.items() if u.rstrip("/").endswith("/" + Path(url).name.rstrip("/"))),
            {})
        articles.append({
            "content_id": fm.get("content_id", ""),
            "title": fm.get("title", Path(f.name).stem),
            "url": url,
            "date": fm.get("date", ""),
            "scans": scan_article(text),
            "intent": infer_business_intent(url, fm.get("title", "")),
            "gsc": gsc,
        })
    articles.sort(key=lambda a: (a["content_id"], a["url"]))
    return articles, duplicates


def run(skip_ga4: bool = False) -> dict:
    hugo_toml = (BLOG_ROOT / "hugo.toml").read_text(encoding="utf-8")
    affiliate_cfg = load_hugo_affiliate(hugo_toml)
    gsc = load_gsc_page_data(BLOG_ROOT / "reports" / "seo" / "page_performance.csv")
    if not gsc:
        gsc = load_gsc_page_data(BLOG_ROOT / "reports" / "seo" / "raw_pages_28d.csv")
    articles, duplicates = load_articles(BLOG_ROOT / "content" / "posts", gsc)

    single_html = (BLOG_ROOT / "layouts" / "_default" / "single.html").read_text(
        encoding="utf-8", errors="replace")
    tracking = tracking_schema_check(single_html)

    ga4_clicks = None if skip_ga4 else fetch_affiliate_clicks_ga4(28)
    if ga4_clicks is None and not skip_ga4:
        ga4_clicks = {}  # API unavailable -> treat as unknown-zero, mark NOT_AVAILABLE

    rows = {
        "inventory": partner_inventory_rows(articles, PARTNER_DEFS),
        "content_map": content_map_rows(articles, PARTNER_DEFS),
        "baseline": baseline_rows(articles, PARTNER_DEFS, ga4_clicks),
        "gaps": gap_detection(articles, PARTNER_DEFS),
        "commercial": commercial_ranking(articles),
    }
    return {
        "affiliate_cfg": affiliate_cfg,
        "articles": articles,
        "duplicates": duplicates,
        "tracking": tracking,
        "ga4_clicks": ga4_clicks,
        "rows": rows,
        "generated": date.today().isoformat(),
    }


def write_csv(path, fieldnames, rows):
    with Path(path).open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def write_outputs(data: dict):
    rows = data["rows"]
    write_csv(REPORTS_REVENUE / "AFFILIATE_PARTNER_INVENTORY.csv",
              ["partner", "affiliate_key", "pages_count", "link_count",
               "affiliate_id_present", "utm_present", "tracking_present", "status"],
              rows["inventory"])
    write_csv(REPORTS_REVENUE / "AFFILIATE_CONTENT_MAP.csv",
              ["content_id", "title", "url", "partner", "placement", "link_count"],
              rows["content_map"])
    write_csv(REPORTS_REVENUE / "AFFILIATE_REVENUE_BASELINE.csv",
              ["content_id", "url", "partner", "affiliate_clicks_28d",
               "affiliate_sessions_28d", "revenue_28d", "currency", "status"],
              rows["baseline"])
    write_csv(REPORTS_REVENUE / "AFFILIATE_GAPS_DETAIL.csv",
              ["content_id", "url", "type", "detail"],
              rows["gaps"])
    write_csv(REPORTS_REVENUE / "TOP_COMMERCIAL_PAGES.csv",
              ["content_id", "url", "title", "intent", "impressions_28d",
               "clicks_28d", "affiliate_present", "commercial_score"],
              rows["commercial"])
    return rows


def write_markdown_reports(data: dict):
    rows = data["rows"]
    low = "LOW_DATA_WARNING: GSC 28d clicks 极低（全站 3），GA4 affiliate_click 数据接近 0。不要基于当前数据宣布盈利结论。"
    ga4_total = sum((data["ga4_clicks"] or {}).values()) if data["ga4_clicks"] is not None else 0
    ga4_src = "GA4_API(28d, per-page)" if data["ga4_clicks"] is not None else "NOT_AVAILABLE"

    lines = ["# TOP AFFILIATE OPPORTUNITIES", "",
             f"- Generated: {data['generated']}", f"- GA4 data source: {ga4_src}", "",
             "- Rule: high SEO impressions + high affiliate intent + existing placement + low current clicks.", "",
             "| # | page | content_id | partner | impressions | affiliate clicks | revenue | opportunity | recommended action |",
             "|---|---|---|---|---|---|---|---|---|"]
    opps = []
    for a in data["articles"]:
        imp = a["gsc"].get("impressions", 0)
        partners = {pdef["brand"] for k, pdef in PARTNER_DEFS.items()
                    if any(a["scans"][k2].get(k, 0) for k2 in ("inline_urls", "shortcodes", "ctas"))}
        if not partners or imp < 10:
            continue
        opps.append((a, imp, sorted(partners)))
    opps.sort(key=lambda t: -t[1])
    for i, (a, imp, partners) in enumerate(opps[:20], 1):
        action = "MONITOR" if imp < 100 else "CTA_TEST"
        lines.append(f"| {i} | {a['url']} | {a['content_id']} | {', '.join(partners)} | {imp} | {ga4_total} | NULL | "
                     f"impressions={imp}, intent={a['intent']} | {action} |")
    lines += ["", low]
    (REPORTS_REVENUE / "TOP_AFFILIATE_OPPORTUNITIES.md").write_text("\n".join(lines), encoding="utf-8")

    gl = ["# AFFILIATE GAPS", "", f"- Generated: {data['generated']}", "",
          "Detection rules:", "- A: high commercial intent + no affiliate",
          "- B: affiliate exists + zero visibility (0 impressions)",
          "- C: affiliate exists + high impressions (>=100) + zero clicks",
          "- D: >=5 distinct partners on one page",
          "- E: >=6 distinct partners on one page (over-monetization risk)", "",
          "| content_id | url | type | detail |", "|---|---|---|---|"]
    for g in sorted(rows["gaps"], key=lambda x: (x["type"], x["url"])):
        gl.append(f"| {g['content_id']} | {g['url']} | {g['type']} | {g['detail']} |")
    if not rows["gaps"]:
        gl.append("| - | - | NONE | no gaps detected |")
    gl += ["", low]
    (REPORTS_REVENUE / "AFFILIATE_GAPS.md").write_text("\n".join(gl), encoding="utf-8")

    cl = ["# TOP COMMERCIAL PAGES", "", f"- Generated: {data['generated']}", "",
          "Ranking: search demand (impressions) x business intent weight x affiliate presence.", "",
          "| # | url | intent | impressions | clicks | affiliate | score |", "|---|---|---|---|---|---|---|"]
    for i, r in enumerate(rows["commercial"][:25], 1):
        cl.append(f"| {i} | {r['url']} | {r['intent']} | {r['impressions_28d']} | {r['clicks_28d']} | "
                  f"{r['affiliate_present']} | {r['commercial_score']} |")
    cl += ["", low]
    (REPORTS_REVENUE / "TOP_COMMERCIAL_PAGES.md").write_text("\n".join(cl), encoding="utf-8")

    t = data["tracking"]
    rl = ["# REVENUE EXPERIMENT READINESS", "", f"- Generated: {data['generated']}", "",
          "## Affiliate click tracking", f"- Event: `{t['event_name']}`", f"- Status: `{t['status']}`",
          f"- Fields present: {', '.join(t['fields_present'])}",
          f"- Missing fields: {', '.join(t['missing_fields']) or 'none'}",
          f"- gtag event: {t['gtag_event']} | dataLayer push: {t['data_layer_push']}", "",
          "## Experiment types", "| Experiment | Ready | Notes |", "|---|---|---|",
          "| A. CTA placement test | READY | article_cta exists; can A/B placement via shortcode |",
          "| B. Affiliate partner comparison | READY | partner field tracked per click |",
          "| C. Content-to-affiliate conversion | PARTIAL | needs affiliate sessions/revenue API |",
          "| D. Travelpayouts Drive experiment | NOT_READY | Drive NOT enabled this round |", "",
          "## Data quality note", f"- Duplicate articles by URL: {len(data['duplicates'])} "
          "(existing repo issue, not modified this round; kept for manual review)", "",
          "## Revenue availability", "- affiliate_click 28d = {} (source: {})".format(
              ga4_total, ga4_src),
          "- affiliate_sessions / revenue: **NULL** until an affiliate revenue API is connected.", "",
          "DRIVE_STATUS = NOT_ENABLED（本轮不启用 Travelpayouts Drive）", "", low]
    (REPORTS_REVENUE / "REVENUE_EXPERIMENT_READINESS.md").write_text("\n".join(rl), encoding="utf-8")


def main():
    skip = "--no-ga4" in sys.argv
    data = run(skip_ga4=skip)
    rows = write_outputs(data)
    write_markdown_reports(data)
    print(f"generated={data['generated']}")
    print(f"articles={len(data['articles'])} duplicates={len(data['duplicates'])} "
          f"partners={len(rows['inventory'])} content_map_rows={len(rows['content_map'])} "
          f"gaps={len(rows['gaps'])}")
    t = data["tracking"]
    print(f"tracking_status={t['status']} missing={t['missing_fields'] or 'none'}")
    ga4 = data["ga4_clicks"]
    ga4_total = sum((ga4 or {}).values()) if ga4 is not None else None
    print(f"ga4_affiliate_clicks_28d={ga4_total if ga4_total is not None else 'NOT_AVAILABLE'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
