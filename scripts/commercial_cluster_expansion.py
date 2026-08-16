#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P1-GROWTH-16A: Commercial Cluster Expansion Engine.

Deterministic ranking of commercial topic clusters (no LLM / no external API).

Scoring (100):
  Search Demand        30   (cluster impressions_28d)
  Commercial Intent    30   (cluster intent type)
  Existing Authority   20   (best position in cluster)
  Affiliate Fit        15   (partner intersection ratio)
  Content Gap           5   (keyword coverage shortfall)

Outputs (reports/revenue/):
  - COMMERCIAL_CLUSTER_PRIORITY.csv
  - COMMERCIAL_EXPANSION_ROADMAP.md
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
sys.path.insert(0, str(BLOG_ROOT / "scripts"))

from commercial_content_engine import CLUSTERS, INTENT_SCORE, _tokens  # noqa: E402

CLUSTER_INTENT = {"China Transportation": "TRAIN",
                  "China Payment": "PAYMENT",
                  "China Connectivity": "INTERNET"}


def demand30(impressions: int) -> int:
    if impressions >= 800:
        return 30
    if impressions >= 400:
        return 25
    if impressions >= 200:
        return 20
    if impressions >= 100:
        return 15
    if impressions >= 50:
        return 10
    if impressions > 0:
        return 5
    return 0


def authority20(position: float) -> int:
    if not position or position <= 0:
        return 0
    if position <= 5:
        return 20
    if position <= 10:
        return 17
    if position <= 20:
        return 13
    if position <= 30:
        return 9
    if position <= 50:
        return 5
    return 2


def affiliate15(hit: int, total: int) -> int:
    if total <= 0:
        return 0
    ratio = hit / total
    if ratio >= 0.6:
        return 15
    if ratio >= 0.3:
        return 10
    if ratio > 0:
        return 5
    return 0


def gap5(covered: int, total: int) -> int:
    if total <= 0:
        return 0
    missing = total - covered
    if missing <= 0:
        return 0
    if missing == total:
        return 5
    return 3


def _num(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _load_csv(path: Path) -> list:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_cluster_rows(priority_rows=None, seo_rows=None, funnel_rows=None) -> list:
    priority_rows = priority_rows if priority_rows is not None else _load_csv(REV / "COMMERCIAL_CONTENT_PRIORITY.csv")
    seo_rows = seo_rows if seo_rows is not None else _load_csv(SEO / "CONTENT_SEO_INVENTORY.csv")
    funnel_rows = funnel_rows if funnel_rows is not None else _load_csv(REV / "AFFILIATE_FUNNEL_INVENTORY.csv")

    partner_by_url = {}
    for r in funnel_rows:
        partner_by_url.setdefault(r["url"], set()).add(r["partner"])

    rows = []
    for cluster, spec in CLUSTERS.items():
        kw_rows = [r for r in priority_rows if r["keyword_cluster"] == cluster]
        if not kw_rows:
            continue
        impressions = sum(int(_num(r.get("impressions_28d"))) for r in kw_rows)
        positions = [_num(r.get("best_position")) for r in kw_rows if _num(r.get("best_position")) > 0]
        best_pos = min(positions) if positions else 0.0
        covered = sum(1 for r in kw_rows if int(_num(r.get("existing_pages"))) > 0)
        total_kw = len(kw_rows)

        # affiliate fit: pages across cluster keywords
        cluster_urls = {r.get("target_url", "") for r in kw_rows}
        partners = set()
        for u in cluster_urls:
            partners |= partner_by_url.get(u, set())
        rec = set(spec["affiliate_match"])
        hit = len(partners & rec)

        intent = CLUSTER_INTENT.get(cluster, spec["intent"])
        score = (demand30(impressions)
                 + INTENT_SCORE.get(intent, 20)
                 + authority20(best_pos)
                 + affiliate15(hit, len(rec))
                 + gap5(covered, total_kw))
        rows.append({
            "cluster": cluster,
            "intent": intent,
            "keywords_total": total_kw,
            "keywords_covered": covered,
            "impressions_28d": impressions,
            "best_position": best_pos,
            "affiliate_partners": ",".join(sorted(partners)) or "none",
            "recommended_partners": ",".join(rec),
            "affiliate_fit_ratio": round(hit / len(rec), 2) if rec else 0.0,
            "demand_score": demand30(impressions),
            "intent_score": INTENT_SCORE.get(intent, 20),
            "authority_score": authority20(best_pos),
            "affiliate_score": affiliate15(hit, len(rec)),
            "gap_score": gap5(covered, total_kw),
            "score": score,
            "priority": "A" if score >= 75 else "B" if score >= 60 else "C",
            "status": "READY" if score >= 70 else "HOLD",
        })
    rows.sort(key=lambda r: (-r["score"], r["cluster"]))
    return rows


CLUSTER_FIELDS = ["cluster", "intent", "keywords_total", "keywords_covered",
                  "impressions_28d", "best_position", "affiliate_partners",
                  "recommended_partners", "affiliate_fit_ratio", "demand_score",
                  "intent_score", "authority_score", "affiliate_score",
                  "gap_score", "score", "priority", "status"]


def write_cluster_priority(rows: list, out: Path = None) -> Path:
    out = out or (REV / "COMMERCIAL_CLUSTER_PRIORITY.csv")
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CLUSTER_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return out


def write_roadmap(rows: list, out: Path = None) -> Path:
    out = out or (REV / "COMMERCIAL_EXPANSION_ROADMAP.md")
    lines = [
        "# Commercial Expansion Roadmap (P1-GROWTH-16A)",
        "",
        "Date: 2026-08-16  |  Status: RANKING ONLY (no content execution)",
        "",
        "Scoring: Search Demand 30 + Commercial Intent 30 + Existing Authority 20 + "
        "Affiliate Fit 15 + Content Gap 5 = 100",
        "",
        "| rank | cluster | score | priority | status | impressions | position | partners | gap |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(rows, 1):
        lines += [f"| {i} | {r['cluster']} | {r['score']} | {r['priority']} | {r['status']} | "
                  f"{r['impressions_28d']} | {r['best_position']} | {r['affiliate_partners']} | "
                  f"{r['keywords_covered']}/{r['keywords_total']} |"]
    lines += ["", "## Phased plan", "",
              "- Phase 1: Cluster A China Transportation (highest score) - supporting content decision "
              "in CONTENT_EXPANSION_DECISION.md; execution deferred to P1-GROWTH-17.",
              "- Phase 2: Cluster B China Payment - HOLD until WeChat Pay index recovery stabilizes.",
              "- Phase 3: Cluster C China Connectivity - HOLD until REV001 data matures.",
              "", "## Rules", "",
              "- Deterministic model only; no LLM, no external API, no fake data.",
              "- No content/CTA/affiliate changes in this round."]
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


# Candidate topics for supporting content (P1-GROWTH-16B)
EXPANSION_CANDIDATES = [
    {"topic": "China Railway 12306 App Guide", "intents": ["china railway app", "12306 foreigner"],
     "probe": ["12306"], "partners": ["Trip.com"]},
    {"topic": "China Transportation Card", "intents": ["china transport card", "metro card china tourist"],
     "probe": ["transportation card", "transport card", "metro card"], "partners": ["Klook"]},
    {"topic": "China Airport Transfer", "intents": ["airport transfer china", "shanghai airport transfer"],
     "probe": ["airport transfer"], "partners": ["Booking", "Klook"]},
]


def _probe_hits(candidate: dict, posts_dir: Path = None, seo_rows: list = None) -> list:
    """Pages whose body/title/url contains a probe term (discriminator)."""
    posts_dir = posts_dir or (BLOG_ROOT / "content" / "posts")
    seo_rows = seo_rows if seo_rows is not None else _load_csv(SEO / "CONTENT_SEO_INVENTORY.csv")
    seo_by_url = {}
    for r in seo_rows:
        cur = seo_by_url.get(r["url"])
        if cur is None or int(_num(r.get("impressions_28d"))) > int(_num(cur.get("impressions_28d"))):
            seo_by_url[r["url"]] = r
    sys.path.insert(0, str(BLOG_ROOT / "scripts"))
    from affiliate_gap_detector import parse_front_matter, url_from_front_matter
    hits = []
    probes = [pr.lower() for pr in candidate["probe"]]
    for f in sorted(posts_dir.glob("*.md")):
        raw = f.read_text(encoding="utf-8", errors="replace")
        if not any(pr in raw.lower() for pr in probes):
            continue
        fm = parse_front_matter(raw)
        if str(fm.get("draft", "")).strip().lower() in ("true", "yes"):
            continue
        url = url_from_front_matter(fm, f.name)
        seo = seo_by_url.get(url, {})
        hits.append({"url": url, "impressions": int(_num(seo.get("impressions_28d"))),
                     "position": _num(seo.get("position_28d"))})
    return hits


def build_expansion_decision(seo_rows=None) -> list:
    seo_rows = seo_rows if seo_rows is not None else _load_csv(SEO / "CONTENT_SEO_INVENTORY.csv")
    rows = []
    for c in EXPANSION_CANDIDATES:
        hits = _probe_hits(c, seo_rows=seo_rows)
        imp = sum(h["impressions"] for h in hits)
        positions = [h["position"] for h in hits if h["position"] > 0]
        best = min(positions) if positions else 0.0
        if not hits:
            action = "CREATE"
            reason = "no page covers this intent; execution deferred to P1-GROWTH-17"
        elif imp >= 100 and 0 < best <= 30:
            action = "KEEP"
            reason = "existing page(s) already carry the intent with real demand"
        elif imp >= 20:
            action = "UPDATE"
            reason = "partial coverage on existing page(s); enrich, do not create a new page yet"
        else:
            action = "CREATE"
            reason = "weak existing coverage; candidate for P1-GROWTH-17 single release"
        rows.append({
            "topic": c["topic"],
            "search_intent": ";".join(c["intents"]),
            "existing_url": hits[0]["url"] if hits else "",
            "existing_pages": len(hits),
            "impressions_28d": imp,
            "best_position": best,
            "affiliate_match": ",".join(c["partners"]),
            "action": action,
            "reason": reason,
        })
    rows.sort(key=lambda r: (-r["impressions_28d"], r["topic"]))
    return rows


def write_expansion_decision(rows=None, out: Path = None) -> Path:
    out = out or (REV / "CONTENT_EXPANSION_DECISION.md")
    rows = rows if rows is not None else build_expansion_decision()
    lines = [
        "# Content Expansion Decision (P1-GROWTH-16B)",
        "",
        "Date: 2026-08-16  |  Status: DECISION ONLY - no content published",
        "",
        "| topic | intent | existing url | pages | impressions | position | partners | action |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines += [f"| {r['topic']} | {r['search_intent']} | {r['existing_url'] or 'none'} | "
                  f"{r['existing_pages']} | {r['impressions_28d']} | {r['best_position']} | "
                  f"{r['affiliate_match']} | {r['action']} |"]
    lines += ["", "## Rules", "",
              "- No article is created this round; CREATE/UPDATE execute in P1-GROWTH-17.",
              "- REV002 CTA stays untouched (frozen until 2026-09-13)."]
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def build_legacy_risk(seo_rows=None) -> list:
    """P1-GROWTH-16D: commercial value x persona violations (analysis only)."""
    sys.path.insert(0, str(BLOG_ROOT / "scripts"))
    from affiliate_gap_detector import parse_front_matter, url_from_front_matter
    from persona_guard import PersonaGuard
    guard = PersonaGuard()
    posts_dir = BLOG_ROOT / "content" / "posts"
    seo_rows = seo_rows if seo_rows is not None else _load_csv(SEO / "CONTENT_SEO_INVENTORY.csv")
    # url -> seo row (dedupe, keep highest impressions)
    best = {}
    for r in seo_rows:
        cur = best.get(r["url"])
        if cur is None or int(_num(r.get("impressions_28d"))) > int(_num(cur.get("impressions_28d"))):
            best[r["url"]] = r
    rows = []
    for f in sorted(posts_dir.glob("*.md")):
        text = f.read_text(encoding="utf-8", errors="replace")
        fm = parse_front_matter(text)
        if str(fm.get("draft", "")).strip().lower() in ("true", "yes"):
            continue
        fm_text = text
        m = re.match(r"^(?:---|\+\+\+)\r?\n(.*?)\r?\n(?:---|\+\+\+)", text, re.S)
        body = text[m.end():] if m else text
        violations = guard.check(body)
        cid = (fm.get("content_id") or "").strip()
        url = url_from_front_matter(fm, f.name)
        seo = best.get(url, {})
        imp = int(_num(seo.get("impressions_28d")))
        if not violations and imp < 30:
            continue
        rows.append({
            "content_id": cid,
            "url": url,
            "impressions_28d": imp,
            "violations": len(violations),
            "risk": "HIGH" if violations and imp >= 50 else
                   "MED" if violations else "LOW",
        })
    rows.sort(key=lambda r: (-r["violations"], -r["impressions_28d"], r["url"]))
    return rows


def write_legacy_risk(rows=None, out: Path = None) -> Path:
    out = out or (REV / "LEGACY_COMMERCIAL_RISK_REPORT.md")
    rows = rows if rows is not None else build_legacy_risk()
    lines = [
        "# Legacy Persona Commercial Risk Report (P1-GROWTH-16D)",
        "",
        "Date: 2026-08-16  |  Status: ANALYSIS ONLY - no content changes",
        "",
        "Pages combining commercial value (impressions) with legacy persona risk (violations).",
        "",
        "| content_id | url | impressions | persona violations | risk |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        lines += [f"| {r['content_id']} | {r['url']} | {r['impressions_28d']} | "
                  f"{r['violations']} | {r['risk']} |"]
    lines += ["", "## Rules", "",
              "- Read-only analysis; persona migration remains deferred.",
              "- Priority for future cleanup: HIGH-risk pages with real impressions."]
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def main():
    rows = build_cluster_rows()
    write_cluster_priority(rows)
    write_roadmap(rows)
    write_expansion_decision()
    write_legacy_risk()
    print(f"clusters: {len(rows)}")
    for r in rows:
        print(f"  {r['score']:3d} {r['priority']} {r['status']:<8} {r['cluster']}")


if __name__ == "__main__":
    main()
