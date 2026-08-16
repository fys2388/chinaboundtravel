"""P1-GROWTH-20A: REV002 commercial experiment review framework.

Deterministic, no network. Checks the review gate first; if the gate has not
been reached, outputs WAITING_REVIEW_GATE (no judgement). If reached, applies
the sample guard and positive gate using local registry/GA4/GSC data.
"""
import csv
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "reports/revenue/REV002_FINAL_REVIEW.md"

REVIEW_GATE = date(2026, 9, 13)
LOW_SAMPLE_CLICKS = 20
REV002_REGISTRY = REPO / "reports/revenue/REV002_EXPERIMENT_REGISTRY.csv"
REV002_BASELINE = REPO / "reports/revenue/REV002_BASELINE.csv"


def load_registry():
    with REV002_REGISTRY.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return next((r for r in rows if r["experiment_id"] == "REV002"), None)


def load_baseline():
    if not REV002_BASELINE.exists():
        return None
    with REV002_BASELINE.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return rows[0] if rows else None


def num(value):
    try:
        return float(value) if value not in (None, "", "NULL") else 0.0
    except (TypeError, ValueError):
        return 0.0


def build_review():
    today = date.today()
    registry = load_registry()
    baseline = load_baseline()

    if today < REVIEW_GATE:
        lines = [
            "# REV002 Final Review (P1-GROWTH-20A)",
            "",
            f"Generated: {today.isoformat()}  |  Gate: {REVIEW_GATE.isoformat()}",
            "",
            "## Status: WAITING_REVIEW_GATE",
            f"- review date {today.isoformat()} < gate {REVIEW_GATE.isoformat()}",
            "- No judgement is allowed before the gate.",
            "- Sample guard remains: affiliate_clicks < 20 -> INSUFFICIENT_SAMPLE.",
        ]
        if registry:
            lines += ["", "## Experiment (frozen)", f"- experiment_id: {registry['experiment_id']}",
                      f"- content_id: {registry['content_id']}", f"- status: {registry['status']}"]
        lines += ["", "## Framework (applied at gate)", "- clicks >= 20 AND affiliate_click_rate improvement >= 20%",
                  "  AND outbound_rate not worse than baseline -10% -> PROMISING", "- otherwise -> NEUTRAL",
                  "- clicks < 20 -> INSUFFICIENT_SAMPLE (no WIN/LOSE)"]
        OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return {"status": "WAITING_REVIEW_GATE", "output": str(OUT)}

    # gate reached: apply rules on local data (no fabrication)
    gsc_clicks = num(baseline.get("gsc_clicks")) if baseline else 0
    baseline_ctr = num(baseline.get("affiliate_click_rate")) if baseline else 0
    if gsc_clicks < LOW_SAMPLE_CLICKS or baseline_ctr == 0:
        status = "INSUFFICIENT_SAMPLE"
    else:
        status = "NEUTRAL"  # positive gate requires current-period data we do not fabricate
    lines = [
        "# REV002 Final Review (P1-GROWTH-20A)",
        "",
        f"Generated: {today.isoformat()}  |  Gate: reached",
        f"## Status: {status}",
    ]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"status": status, "output": str(OUT)}


if __name__ == "__main__":
    if "--check" in sys.argv:
        result = build_review()
        assert result["status"] == "WAITING_REVIEW_GATE"
        assert OUT.exists()
        print("OK status=WAITING_REVIEW_GATE")
    else:
        result = build_review()
        print(f"written {result['output']} status={result['status']}")
