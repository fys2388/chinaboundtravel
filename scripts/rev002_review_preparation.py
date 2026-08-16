"""P1-GROWTH-19F: REV002 review preparation (no judgement, just preparation).

Deterministic, no network. Reads local registry/baseline/cached GSC data and
writes reports/revenue/REV002_REVIEW_READY.md with a sample-size guard.
"""
import csv
import json
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "reports/revenue/REV002_REVIEW_READY.md"

REV002_REGISTRY = REPO / "reports/revenue/REV002_EXPERIMENT_REGISTRY.csv"
REV002_BASELINE = REPO / "reports/revenue/REV002_BASELINE.csv"
GSC_INDEX = REPO / "reports/gsc_index_report.json"
GA4_SNAPSHOTS = list((REPO / "reports").glob("last_*_data.json"))

LOW_SAMPLE_CLICKS = 20


def read_registry():
    with REV002_REGISTRY.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    row = next((r for r in rows if r["experiment_id"] == "REV002"), None)
    if row is None:
        raise SystemExit("REV002 not found in registry")
    return row


def read_baseline():
    with REV002_BASELINE.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return rows[0] if rows else None


def read_gsc_cache():
    if not GSC_INDEX.exists():
        return None
    try:
        data = json.loads(GSC_INDEX.read_text(encoding="utf-8"))
        return data
    except (json.JSONDecodeError, OSError):
        return None


def read_ga4_cache():
    snapshots = {}
    for p in GA4_SNAPSHOTS:
        try:
            snapshots[p.name] = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
    return snapshots or None


def build_review_ready():
    registry = read_registry()
    baseline = read_baseline()
    gsc = read_gsc_cache()
    ga4 = read_ga4_cache()

    # data availability (no guessing)
    gsc_status = "AVAILABLE" if gsc else "NOT_AVAILABLE"
    ga4_status = "AVAILABLE" if ga4 else "NOT_AVAILABLE"

    # sample-size guard: clicks from GSC baseline (latest known)
    gsc_clicks = 0
    if baseline and baseline.get("gsc_clicks") not in (None, "", "NULL"):
        gsc_clicks = int(float(baseline["gsc_clicks"]))
    sample_status = "SUFFICIENT_SAMPLE" if gsc_clicks >= LOW_SAMPLE_CLICKS else "INSUFFICIENT_SAMPLE"

    lines = [
        "# REV002 Review Readiness (P1-GROWTH-19F)",
        "",
        f"Generated: {date.today().isoformat()}  |  Status: PREPARATION ONLY (no judgement)",
        "",
        "## Experiment",
        f"- experiment_id: {registry['experiment_id']}",
        f"- content_id: {registry['content_id']}",
        f"- url: {registry['url']}",
        f"- type: {registry['experiment_type']}",
        f"- start_date: {registry['start_date']}",
        f"- baseline_period: {registry['baseline_period']}",
        f"- review gate (min observation): {registry['minimum_observation_days']} days",
        f"- status: {registry['status']}",
        "",
        "## Metrics for review",
        "- Primary: affiliate_click_rate",
        "- Secondary: affiliate_outbound_rate; affiliate_clicks_per_1000_sessions; CTA impressions",
        "",
        "## Data availability",
        f"- GA4 events: {ga4_status}",
        f"- GSC snapshot: {gsc_status} (file: {GSC_INDEX.name if gsc else 'none'})",
        "",
        "## Baseline snapshot (frozen at experiment start)",
    ]
    if baseline:
        for key in ("content_id", "url", "baseline_start", "baseline_end",
                    "sessions", "pageviews", "affiliate_clicks",
                    "affiliate_clicks_per_1000", "gsc_impressions", "gsc_clicks",
                    "gsc_position", "revenue"):
            if key in baseline:
                lines.append(f"- {key}: {baseline[key]}")
    else:
        lines.append("- baseline: MISSING")

    lines += [
        "",
        "## Sample-size guard",
        f"- threshold: affiliate/gsc clicks < {LOW_SAMPLE_CLICKS} -> INSUFFICIENT_SAMPLE",
        f"- current known clicks (baseline gsc_clicks): {gsc_clicks}",
        f"- verdict at review time: {sample_status}",
        "",
        "## Rules",
        "- Do not declare WIN/LOSE at review time if clicks < 20.",
        "- Do not modify REV002 CTA before the gate (>= 2026-09-13).",
        "- No revenue data: keep NULL; never fabricate.",
    ]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "experiment_id": registry["experiment_id"],
        "sample_status": sample_status,
        "gsc_status": gsc_status,
        "ga4_status": ga4_status,
        "output": str(OUT),
    }


if __name__ == "__main__":
    if "--check" in sys.argv:
        result = build_review_ready()
        assert result["experiment_id"] == "REV002"
        assert result["sample_status"] == "INSUFFICIENT_SAMPLE"
        assert OUT.exists()
        print(f"OK sample_status={result['sample_status']} gsc={result['gsc_status']} ga4={result['ga4_status']}")
    else:
        result = build_review_ready()
        print(f"written {result['output']}")
