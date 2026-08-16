"""P1-GROWTH-20B: Transportation Card CTA experiment readiness.

Deterministic, no network. Scores the card page (cbt-55aef784e6aa) for a
future CTA experiment and outputs a three-way verdict.
"""
import csv
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "reports/revenue/TRANSPORTATION_CARD_CTA_READINESS.md"

CARD_PAGE = REPO / "content/posts/china-transportation-card-guide.md"
REV002_REGISTRY = REPO / "reports/revenue/REV002_EXPERIMENT_REGISTRY.csv"
GSC_CACHE = REPO / "reports/gsc_index_report.json"

# dimensions (100)
WEIGHTS = {"gsc_demand": 25, "commercial_intent": 30, "affiliate_fit": 25,
           "index_status": 10, "risk": 10}


def rev002_running():
    if not REV002_REGISTRY.exists():
        return False
    with REV002_REGISTRY.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    row = next((r for r in rows if r["experiment_id"] == "REV002"), None)
    return bool(row and row["status"] == "RUNNING")


def gsc_data_available():
    return GSC_CACHE.exists() and "success" in GSC_CACHE.read_text(encoding="utf-8", errors="replace")


def score():
    page_exists = CARD_PAGE.exists()
    # GSC Demand: page launched today; no GSC history yet
    gsc = 2 if page_exists else 0
    # Commercial Intent: transit card = local payment/shopping intent (high)
    commercial = 24
    # Affiliate Fit: Klook/Booking/Trip.com on-page (existing, medium-high)
    affiliate = 18
    # Index Status: not yet confirmed in GSC (just launched)
    index = 2 if gsc_data_available() else 1
    # Risk: REV002 active in same cluster -> signal overlap risk
    risk = 6 if rev002_running() else 8
    total = gsc + commercial + affiliate + index + risk

    if total >= 75 and gsc_data_available():
        verdict = "READY_FOR_EXPERIMENT"
    elif total >= 55:
        verdict = "WAIT_FOR_DATA"
    else:
        verdict = "REJECT"

    lines = [
        "# Transportation Card CTA Readiness (P1-GROWTH-20B)",
        "",
        f"Generated: {date.today().isoformat()}  |  Candidate: cbt-55aef784e6aa",
        "",
        "## Score (100)",
        "| Dimension | Weight | Score |",
        "|---|---|---|",
        f"| GSC Demand | {WEIGHTS['gsc_demand']} | {gsc} |",
        f"| Commercial Intent | {WEIGHTS['commercial_intent']} | {commercial} |",
        f"| Affiliate Fit | {WEIGHTS['affiliate_fit']} | {affiliate} |",
        f"| Index Status | {WEIGHTS['index_status']} | {index} |",
        f"| Risk | {WEIGHTS['risk']} | {risk} |",
        f"| **Total** | 100 | **{total}** |",
        "",
        f"## Verdict: {verdict}",
        "",
        "## Constraints if READY",
        "- 1 page / 1 CTA / 1 partner / 1 placement only",
        "- Preferred partner: Trip.com (city movement + train booking intent)",
        "- Do not touch Transportation Guide / REV002 / Airport Transfer simultaneously",
        "- Sample guard: affiliate_clicks < 20 -> INSUFFICIENT_SAMPLE",
        "",
        "## Rules",
        "- REV002 must remain the only active transportation CTA experiment until its gate (2026-09-13).",
        "- No new affiliate partner / tracking / UTM.",
    ]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"verdict": verdict, "total": total}


if __name__ == "__main__":
    if "--check" in sys.argv:
        result = score()
        assert result["verdict"] in ("READY_FOR_EXPERIMENT", "WAIT_FOR_DATA", "REJECT")
        assert OUT.exists()
        print(f"OK verdict={result['verdict']} total={result['total']}")
    else:
        result = score()
        print(f"written {OUT} verdict={result['verdict']}")
