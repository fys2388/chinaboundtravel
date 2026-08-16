#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P1-GROWTH-14B: Commercial Content Opportunity Engine.

Deterministic scoring model (no LLM, no subjective judgement, no fake data).
Ranks keyword clusters by commercial opportunity using persisted data:

  - reports/seo/CONTENT_SEO_INVENTORY.csv      (impressions / position / indexed)
  - reports/revenue/AFFILIATE_FUNNEL_INVENTORY.csv (partner coverage per page)

Scoring model (100 points):
  Commercial Intent   30
  Search Demand       25
  Affiliate Fit       20
  Existing Authority  15
  Content Gap         10

Outputs (reports/revenue/):
  - COMMERCIAL_CONTENT_PRIORITY.csv
  - COMMERCIAL_TOPIC_CLUSTERS.md
  - CONTENT_REVENUE_GAPS.md

This round performs analysis ONLY. No content/CTA/URL changes.
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

BLOG_ROOT = Path(__file__).resolve().parent.parent
SEO = BLOG_ROOT / "reports" / "seo"
REV = BLOG_ROOT / "reports" / "revenue"
REV.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Topic clusters (from P1-GROWTH-14B instruction)
# ---------------------------------------------------------------------------
CLUSTERS = {
    "China Transportation": {
        "keywords": [
            "china train tickets",
            "china railway app",
            "china high speed rail booking",
            "china airport transfer",
            "china transportation card",
        ],
        "intent": "TRAIN",
        "affiliate_match": ["Trip.com", "Booking", "Klook"],
        "commercial_value": 5,
    },
    "China Payment": {
        "keywords": [
            "alipay for foreigners",
            "wechat pay foreign card",
            "china mobile payment",
            "china payment problems",
        ],
        "intent": "PAYMENT",
        "affiliate_match": ["Airalo", "NordVPN"],
        "commercial_value": 5,
    },
    "China Connectivity": {
        "keywords": [
            "china esim",
            "china vpn",
            "china mobile data",
            "google services china",
        ],
        "intent": "INTERNET",
        "affiliate_match": ["Airalo", "NordVPN"],
        "commercial_value": 4,
    },
}

INTENT_SCORE = {
    "TRAIN": 30, "PAYMENT": 28, "INTERNET": 26, "FLIGHT": 26,
    "HOTEL": 26, "VISA": 30, "INSURANCE": 24, "VPN": 24, "E_SIM": 26,
}


def demand_score(impressions: int) -> int:
    """Search demand proxy from total cluster impressions (max 25)."""
    if impressions is None or impressions <= 0:
        return 0
    if impressions >= 500:
        return 25
    if impressions >= 200:
        return 20
    if impressions >= 100:
        return 16
    if impressions >= 50:
        return 12
    if impressions >= 20:
        return 8
    return 5


def authority_score(position: float, indexed: str) -> int:
    """Existing authority from best position (max 15)."""
    if str(indexed).strip().upper() == "NOT_INDEXED" or not position or position <= 0:
        return 0
    if position <= 5:
        return 15
    if position <= 10:
        return 13
    if position <= 20:
        return 10
    if position <= 50:
        return 6
    return 2


def gap_score(has_page: bool, best_position: float, indexed: str) -> int:
    """Content gap: absent page -> 10; weak page -> 6; strong page -> 2 (max 10)."""
    if not has_page:
        return 10
    if str(indexed).strip().upper() == "NOT_INDEXED" or not best_position or best_position <= 0:
        return 8
    if best_position <= 10:
        return 2
    if best_position <= 30:
        return 5
    return 7


def _num(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _load_seo() -> list:
    p = SEO / "CONTENT_SEO_INVENTORY.csv"
    if not p.exists():
        return []
    with p.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _load_funnel() -> list:
    p = REV / "AFFILIATE_FUNNEL_INVENTORY.csv"
    if not p.exists():
        return []
    with p.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _tokens(text: str) -> set:
    return {w for w in re.split(r"[^a-z0-9]+", text.lower()) if len(w) >= 3}


def _page_matches(row: dict, keyword: str, min_overlap: int = 2) -> bool:
    """Token-overlap match: keyword tokens vs page title+url tokens."""
    hay = f"{row.get('title', '')} {row.get('url', '')}"
    kt = _tokens(keyword)
    pt = _tokens(hay)
    return len(kt & pt) >= min_overlap


def build_priority_rows(seo_rows=None, funnel_rows=None) -> list:
    """Deterministic per-keyword scoring across clusters."""
    seo_rows = seo_rows if seo_rows is not None else _load_seo()
    funnel_rows = funnel_rows if funnel_rows is not None else _load_funnel()

    # partner coverage per url (page) for affiliate fit
    partner_by_url = {}
    for r in funnel_rows:
        partner_by_url.setdefault(r["url"], set()).add(r["partner"])

    rows = []
    for cluster, spec in CLUSTERS.items():
        for keyword in spec["keywords"]:
            matches = [r for r in seo_rows if _page_matches(r, keyword)]
            if matches:
                impressions = sum(int(_num(r.get("impressions_28d"))) for r in matches)
                positions = [_num(r.get("position_28d")) for r in matches if _num(r.get("position_28d")) > 0]
                best_pos = min(positions) if positions else 0.0
                indexed = matches[0].get("indexed_status", "INDEXED")
                target_url = matches[0]["url"]
            else:
                impressions = 0
                best_pos = 0.0
                indexed = "NOT_INDEXED"
                slug = re.sub(r"[^a-z0-9]+", "-", keyword).strip("-")
                target_url = f"https://www.chinaboundtravel.com/posts/{slug}/"

            # affiliate fit: matched pages' partners intersect cluster matches
            matched_partners = set()
            for r in matches:
                matched_partners |= partner_by_url.get(r["url"], set())
            intersect = matched_partners & set(spec["affiliate_match"])
            if intersect:
                aff_score = 20
            elif matched_partners:
                aff_score = 12
            else:
                aff_score = 4

            score = (
                INTENT_SCORE.get(spec["intent"], 20)
                + demand_score(impressions)
                + aff_score
                + authority_score(best_pos, indexed)
                + gap_score(bool(matches), best_pos, indexed)
            )
            priority = "A" if score >= 80 else "B" if score >= 60 else "C"
            action = "OPTIMIZE" if matches else "CREATE"
            if matches and intersect and best_pos > 10:
                action = "CTA_ALIGN"
            elif matches and best_pos <= 10:
                action = "MONITOR"
            rows.append({
                "keyword_cluster": cluster,
                "keyword": keyword,
                "target_url": target_url,
                "intent": spec["intent"],
                "affiliate_match": ",".join(spec["affiliate_match"]),
                "existing_pages": len(matches),
                "impressions_28d": impressions,
                "best_position": best_pos,
                "score": score,
                "priority": priority,
                "action": action,
            })
    rows.sort(key=lambda r: (-r["score"], r["keyword_cluster"], r["keyword"]))
    return rows


PRIORITY_FIELDS = ["keyword_cluster", "keyword", "target_url", "intent",
                   "affiliate_match", "existing_pages", "impressions_28d",
                   "best_position", "score", "priority", "action"]


def write_priority(rows: list, out: Path = None) -> Path:
    out = out or (REV / "COMMERCIAL_CONTENT_PRIORITY.csv")
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=PRIORITY_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return out


def write_topic_clusters(out: Path = None) -> Path:
    out = out or (REV / "COMMERCIAL_TOPIC_CLUSTERS.md")
    lines = [
        "# Commercial Topic Clusters (P1-GROWTH-14B)",
        "",
        "Date: 2026-08-16  |  Status: RANKING ONLY (no publication)",
        "",
        "Scoring: Commercial Intent 30 + Search Demand 25 + Affiliate Fit 20 + "
        "Existing Authority 15 + Content Gap 10 = 100",
        "",
    ]
    rows = build_priority_rows()
    for cluster, spec in CLUSTERS.items():
        stars = "★" * spec["commercial_value"]
        lines += [f"## Cluster: {cluster} ({stars})", ""]
        lines += [f"- Intent: {spec['intent']}"]
        lines += [f"- Affiliate match: {', '.join(spec['affiliate_match'])}"]
        lines += ["- Keywords:"]
        for kw in spec["keywords"]:
            lines += [f"  - {kw}"]
        lines += [""]
    lines += ["## Priority queue (top 10)", ""]
    lines += ["| rank | cluster | keyword | score | priority | action | target |"]
    lines += ["|---|---|---|---|---|---|---|"]
    for i, r in enumerate(rows[:10], 1):
        lines += [f"| {i} | {r['keyword_cluster']} | {r['keyword']} | {r['score']} | "
                  f"{r['priority']} | {r['action']} | {r['target_url']} |"]
    lines += ["", "## Rules", "",
              "- Analysis only: no article creation, no CTA changes, no affiliate changes.",
              "- No LLM judgement: scoring is deterministic from persisted data.",
              "- Revenue remains NULL until a real revenue API exists."]
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def write_content_revenue_gaps(seo_rows=None, funnel_rows=None, out: Path = None) -> Path:
    out = out or (REV / "CONTENT_REVENUE_GAPS.md")
    seo_rows = seo_rows if seo_rows is not None else _load_seo()
    funnel_rows = funnel_rows if funnel_rows is not None else _load_funnel()
    partner_by_url = {}
    for r in funnel_rows:
        partner_by_url.setdefault(r["url"], set()).add(r["partner"])
    lines = [
        "# Content Revenue Gap Analysis (P1-GROWTH-14B)",
        "",
        "Date: 2026-08-16  |  Status: ANALYSIS ONLY (no CTA changes)",
        "",
        f"Baseline: 57 posts / {len(funnel_rows)} CTA rows / revenue NULL",
        "",
        "## Pages with traffic + commercial intent but weak CTA alignment",
        "",
        "| page | impressions | position | current partners | gap |",
        "|---|---|---|---|---|",
    ]
    gaps = []
    for r in sorted(seo_rows, key=lambda x: -int(_num(x.get("impressions_28d")))):
        imp = int(_num(r.get("impressions_28d")))
        if imp < 20:
            continue
        partners = partner_by_url.get(r["url"], set())
        missing = [p for p in ("Booking", "Klook", "Airalo", "NordVPN") if p not in partners]
        if not partners:
            note = "NO_AFFILIATE"
        elif missing:
            note = "PARTIAL:" + ",".join(sorted(missing))
        else:
            note = "OK"
        gaps.append((r, imp, note))
    for r, imp, note in gaps[:15]:
        pos = r.get("position_28d", "0")
        lines += [f"| {r['url']} | {imp} | {pos} | "
                  f"{','.join(sorted(partner_by_url.get(r['url'], set()))) or 'none'} | {note} |"]
    lines += ["", "## Example: Food Delivery page", "",
              "Current CTA partner: Airalo (mid-content CTA).",
              "Possible future alignment: Trip.com / Klook / eSIM / Payment.",
              "Note: NOT changed this round; REV001 stays frozen until 2026-09-13."]
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def main():
    rows = build_priority_rows()
    write_priority(rows)
    write_topic_clusters()
    write_content_revenue_gaps()
    print(f"priority rows: {len(rows)}")
    for r in rows[:6]:
        print(f"  {r['score']:3d} {r['priority']} {r['action']:<12} {r['keyword_cluster']} | {r['keyword']}")


if __name__ == "__main__":
    main()
