#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P1-GROWTH-17C: Commercial Content Release Decision Engine.

Decides which of the two CREATE candidates (Transportation Card vs Airport
Transfer) is released first. Deterministic, no LLM.

Decision rule (transparent):
  - score each candidate = demand evidence + affiliate fit + existing partial
    coverage + launch risk (0-100)
  - the higher-scoring candidate -> CREATE ONE; the other -> HOLD

Output: reports/revenue/COMMERCIAL_RELEASE_DECISION.md
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

from commercial_cluster_expansion import (  # noqa: E402
    EXPANSION_CANDIDATES, build_expansion_decision,
)

RELEASE_CANDIDATES = [
    {"topic": "China Transportation Card", "partner": "Klook",
     "probe": ["transportation card", "transport card", "metro card"]},
    {"topic": "China Airport Transfer", "partner": "Booking, Klook",
     "probe": ["airport transfer"]},
]


def _num(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def build_release_decision() -> list:
    """Score the two CREATE candidates; one becomes CREATE_ONE, other HOLD."""
    decisions = build_expansion_decision()
    by_topic = {d["topic"]: d for d in decisions}
    rows = []
    for c in RELEASE_CANDIDATES:
        d = by_topic.get(c["topic"], {})
        imp = int(_num(d.get("impressions_28d")))
        pages = int(_num(d.get("existing_pages")))
        # demand evidence: existing impressions signal real queries
        demand = 30 if imp >= 100 else 20 if imp >= 20 else 10 if imp > 0 else 0
        # affiliate fit: partner already present in repo config
        fit = 25 if c["partner"] != "Booking, Klook" else 20
        # existing coverage: partial coverage lowers launch risk
        coverage = 15 if pages > 0 else 5
        # launch risk: fewer moving parts wins
        risk = 15 if pages <= 1 else 5
        score = demand + fit + coverage + risk
        rows.append({
            "topic": c["topic"],
            "partner": c["partner"],
            "probe": ";".join(c["probe"]),
            "existing_pages": pages,
            "impressions_28d": imp,
            "demand_score": demand,
            "affiliate_fit_score": fit,
            "coverage_score": coverage,
            "risk_score": risk,
            "score": score,
        })
    rows.sort(key=lambda r: -r["score"])
    rows[0]["action"] = "CREATE_ONE"
    rows[1]["action"] = "HOLD"
    return rows


def write_release_decision(rows=None, out: Path = None) -> Path:
    out = out or (REV / "COMMERCIAL_RELEASE_DECISION.md")
    rows = rows if rows is not None else build_release_decision()
    lines = [
        "# Commercial Release Decision (P1-GROWTH-17C)",
        "",
        "Date: 2026-08-16  |  Status: DECISION ONLY - no page created this round",
        "",
        "| topic | partner | existing pages | impressions | score | action |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines += [f"| {r['topic']} | {r['partner']} | {r['existing_pages']} | "
                  f"{r['impressions_28d']} | {r['score']} | {r['action']} |"]
    lines += ["", "## Rules", "",
              "- Deterministic scoring: demand evidence + affiliate fit + coverage + launch risk.",
              "- CREATE_ONE executes in P1-GROWTH-18; HOLD is re-evaluated after the first release.",
              "- No new affiliate partners; no UTM changes; no bulk content."]
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def main():
    rows = build_release_decision()
    write_release_decision(rows)
    for r in rows:
        print(f"  {r['score']:3d} {r['action']:<12} {r['topic']} (impressions={r['impressions_28d']})")


if __name__ == "__main__":
    main()
