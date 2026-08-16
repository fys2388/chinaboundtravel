#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P1-GROWTH-15A: Commercial Conversion Target Engine.

Deterministic scoring (no LLM / no subjective judgement) that converts
existing high-intent pages into Decision Support Page candidates.

Commercial Conversion Score (100):
  Traffic Potential   25   (GSC impressions_28d)
  Commercial Intent   30   (intent type)
  CTA Match           25   (existing partners vs recommended partners)
  Current CTA Gap     15   (CTA coverage shortfall)
  Risk Adjustment      5   (experiment-conflict free = 5, else 0)

Outputs (reports/revenue/):
  - COMMERCIAL_CONVERSION_TARGETS.csv
  - TOP_COMMERCIAL_PAGES.md (top 3 + CTA gap table, analysis only)
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

BLOG_ROOT = Path(__file__).resolve().parent.parent
SEO = BLOG_ROOT / "reports" / "seo"
REV = BLOG_ROOT / "reports" / "revenue"
sys.path.insert(0, str(BLOG_ROOT / "scripts"))

from affiliate_gap_detector import (SITE_PREFIX, infer_business_intent,  # noqa: E402
                                        parse_front_matter)


def load_true_content_ids(posts_dir: Path = None) -> dict:
    """Ground-truth url -> content_id map from post front matter."""
    posts_dir = posts_dir or (BLOG_ROOT / "content" / "posts")
    mapping = {}
    for f in sorted(posts_dir.glob("*.md")):
        fm = parse_front_matter(f.read_text(encoding="utf-8", errors="replace"))
        if str(fm.get("draft", "")).strip().lower() in ("true", "yes"):
            continue
        cid = (fm.get("content_id") or "").strip()
        if not cid:
            continue
        slug = (fm.get("slug") or "").strip() or f.stem
        mapping[f"{SITE_PREFIX}/posts/{slug}/"] = cid
    return mapping

# Recommended partner by intent (affiliate brand names).
INTENT_PARTNERS = {
    "TRAIN": ["Trip.com", "Booking", "Klook"],
    "PAYMENT": ["Airalo", "NordVPN", "Trip.com"],
    "INTERNET": ["Airalo", "NordVPN"],
    "VPN": ["Airalo", "NordVPN"],
    "HOTEL": ["Booking", "Klook"],
    "FLIGHT": ["Aviasales", "Booking"],
    "VISA": ["Booking", "Klook", "Airalo"],
    "FOOD": ["Airalo", "Klook", "Trip.com"],
    "TOUR": ["Klook", "Booking"],
    "TRANSPORT": ["Trip.com", "Klook", "Booking"],
    "INSURANCE": ["SafetyWing"],
    "GENERAL": ["Airalo", "Booking"],
    "CITY": ["Booking", "Klook"],
}

INTENT_WEIGHT = {
    "VISA": 30, "TRAIN": 28, "PAYMENT": 28, "INTERNET": 26, "VPN": 26,
    "HOTEL": 26, "FLIGHT": 26, "INSURANCE": 24, "TOUR": 20,
    "TRANSPORT": 24, "FOOD": 18, "CITY": 14, "GENERAL": 10,
}

# Pages with active experiments (frozen; analysis only, no CTA change).
EXPERIMENT_PAGES = {
    "cbt-e464169c4991",  # REV001 food delivery CTA
    "cbt-b4ff4381a014",  # 144-hour visa CTR experiment
    "cbt-255af4ed003a",  # WeChat weak index recovery
    "cbt-cc4549872c92",  # High-speed rail technical observation
}

COMMERCIAL_QUERY_TOKENS = ("book", "buy", "ticket", "card", "sim", "vpn",
                           "insurance", "hotel", "transfer", "app", "pay",
                           "train", "visa", "esim")


def traffic_score(impressions: int) -> int:
    if impressions >= 500:
        return 25
    if impressions >= 200:
        return 20
    if impressions >= 100:
        return 15
    if impressions >= 50:
        return 10
    if impressions >= 20:
        return 6
    if impressions > 0:
        return 3
    return 0


def cta_match_score(partners: set, intent: str) -> int:
    rec = set(INTENT_PARTNERS.get(intent, []))
    if not rec:
        return 0
    hit = partners & rec
    if len(hit) >= 2:
        return 25
    if len(hit) == 1:
        return 18
    return 8


def cta_gap_score(partners: set, intent: str) -> int:
    rec = set(INTENT_PARTNERS.get(intent, []))
    missing = rec - partners
    if not partners:
        return 15
    if missing:
        return 8
    return 2


def risk_score(content_id: str) -> int:
    return 0 if content_id in EXPERIMENT_PAGES else 5


def load_seo() -> list:
    with (SEO / "CONTENT_SEO_INVENTORY.csv").open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_funnel() -> list:
    with (REV / "AFFILIATE_FUNNEL_INVENTORY.csv").open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _num(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def build_targets(seo_rows=None, funnel_rows=None) -> list:
    seo_rows = seo_rows if seo_rows is not None else load_seo()
    funnel_rows = funnel_rows if funnel_rows is not None else load_funnel()
    partner_by_url = {}
    for r in funnel_rows:
        partner_by_url.setdefault(r["url"], set()).add(r["partner"])

    true_ids = load_true_content_ids()
    targets = []
    for r in seo_rows:
        url = r.get("url", "")
        impressions = int(_num(r.get("impressions_28d")))
        position = _num(r.get("position_28d"))
        indexed = str(r.get("indexed_status", "")).upper()
        cid = true_ids.get(url, r.get("content_id", ""))
        title = r.get("title", "")
        intent = infer_business_intent(url, title)
        partners = partner_by_url.get(url, set())
        has_commercial_query = any(tok in f"{url} {title}".lower() for tok in COMMERCIAL_QUERY_TOKENS)
        score = (traffic_score(impressions)
                 + INTENT_WEIGHT.get(intent, 10)
                 + cta_match_score(partners, intent)
                 + cta_gap_score(partners, intent)
                 + risk_score(cid))
        targets.append({
            "content_id": cid,
            "url": url,
            "title": title,
            "intent": intent,
            "impressions_28d": impressions,
            "position_28d": position,
            "indexed_status": indexed,
            "existing_partners": ",".join(sorted(partners)),
            "traffic_score": traffic_score(impressions),
            "intent_score": INTENT_WEIGHT.get(intent, 10),
            "cta_match_score": cta_match_score(partners, intent),
            "cta_gap_score": cta_gap_score(partners, intent),
            "risk_score": risk_score(cid),
            "conversion_score": score,
            "commercial_query": has_commercial_query,
        })
    # dedupe by URL (CONTENT_SEO_INVENTORY has legacy duplicate rows) keeping
    # the highest conversion score, then sort deterministically
    best = {}
    for tr in targets:
        cur = best.get(tr["url"])
        if cur is None or tr["conversion_score"] > cur["conversion_score"]:
            best[tr["url"]] = tr
    targets = sorted(best.values(),
                     key=lambda t: (-t["conversion_score"], -t["impressions_28d"], t["url"]))
    return targets


TARGET_FIELDS = ["content_id", "url", "title", "intent", "impressions_28d",
                 "position_28d", "indexed_status", "existing_partners",
                 "traffic_score", "intent_score", "cta_match_score",
                 "cta_gap_score", "risk_score", "conversion_score",
                 "commercial_query"]


def write_targets(rows: list, out: Path = None) -> Path:
    out = out or (REV / "COMMERCIAL_CONVERSION_TARGETS.csv")
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=TARGET_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return out


def eligible_top3(rows: list) -> list:
    # Frozen experiment pages cannot host a new CTA experiment; exclude them
    # from the executable top-3 (they stay MONITOR in the full table).
    return [r for r in rows
            if r["impressions_28d"] > 50
            and r["indexed_status"] == "INDEXED"
            and r["commercial_query"]
            and r["content_id"] not in EXPERIMENT_PAGES][:3]


def write_top_pages(rows: list, out: Path = None) -> Path:
    out = out or (REV / "TOP_COMMERCIAL_PAGES.md")
    top3 = eligible_top3(rows)
    lines = [
        "# Top Commercial Pages (P1-GROWTH-15A, analysis only)",
        "",
        "Date: 2026-08-16  |  Status: RANKING ONLY - no CTA changes this section",
        "",
        "## Top 3 conversion targets",
        "",
        "| rank | page | intent | impressions | position | partners | score |",
        "|---|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(top3, 1):
        lines += [f"| {i} | {r['url']} | {r['intent']} | {r['impressions_28d']} | "
                  f"{r['position_28d']} | {r['existing_partners'] or 'none'} | {r['conversion_score']} |"]
    lines += ["", "## CTA Gap Analysis (CTA_EXISTING / INTENT_MATCH / GAP / ACTION)", ""]
    for i, r in enumerate(top3, 1):
        rec = INTENT_PARTNERS.get(r["intent"], [])
        partners = set(r["existing_partners"].split(",")) if r["existing_partners"] else set()
        missing = [p for p in rec if p not in partners]
        lines += [f"### {i}. {r['url']}", ""]
        lines += [f"- CTA_EXISTING: {r['existing_partners'] or 'none'}"]
        lines += [f"- CTA_INTENT_MATCH: {', '.join(rec) or 'n/a'}"]
        lines += [f"- CTA_GAP: {', '.join(missing) if missing else 'none' }"]
        if r["content_id"] in EXPERIMENT_PAGES:
            lines += ["- RECOMMENDED_ACTION: MONITOR (active experiment - frozen)"]
        elif missing:
            lines += ["- RECOMMENDED_ACTION: CTA_ALIGN (next experiment candidate)"]
        else:
            lines += ["- RECOMMENDED_ACTION: MONITOR"]
        lines += [""]
    lines += ["## Rules", "",
              "- Analysis only: no content/CTA changes in this artifact.",
              "- REV001 / 144h / WeChat / Rail pages are frozen experiments (risk=0, monitor)."]
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def main():
    rows = build_targets()
    write_targets(rows)
    write_top_pages(rows)
    top3 = eligible_top3(rows)
    print(f"targets: {len(rows)} | eligible top3: {len(top3)}")
    for r in top3:
        print(f"  {r['conversion_score']:3d} {r['content_id']} {r['intent']:<10} {r['impressions_28d']:4d} {r['url']}")


if __name__ == "__main__":
    main()
