#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P1-GROWTH-13: unified revenue + SEO experiment review.

Deterministic, no-network. Reads persisted registry/baseline/comparison
artifacts and produces a single EXPERIMENT_COMPARISON.csv plus status logic.

Used by:
  - scripts/revenue_experiment_review.py (CLI)
  - tests/test_revenue_experiment_review.py
"""
import argparse
import csv
import json
from datetime import date
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
REV = BASE / "reports" / "revenue"
SEO = BASE / "reports" / "seo"

MIN_OBSERVATION_DAYS = 28
MIN_CLICKS = 20


def calc_per1000(clicks, pageviews):
    """affiliate_clicks_per_1000_pageviews; None-safe."""
    if clicks is None or pageviews is None or pageviews == 0:
        return 0.0
    return round(float(clicks) * 1000.0 / float(pageviews), 4)


def calc_delta(baseline, current):
    if baseline is None or current is None:
        return None, None
    d = current - baseline
    if baseline == 0:
        pct = None
    else:
        pct = round((current - baseline) / abs(baseline) * 100.0, 2)
    return round(d, 4), pct


def sample_status(observation_days, clicks):
    """SAMPLE SUFFICIENT only when observation >= 28d AND clicks >= 20."""
    if observation_days is None or observation_days < MIN_OBSERVATION_DAYS:
        return "INSUFFICIENT_SAMPLE"
    if clicks is None or clicks < MIN_CLICKS:
        return "INSUFFICIENT_SAMPLE"
    return "SUFFICIENT"


def classify_experiment(status, delta_pct):
    """Transparent experiment status rules (never announces WIN/LOSE on small samples)."""
    if status != "SUFFICIENT":
        return "INSUFFICIENT_SAMPLE"
    if delta_pct is None:
        return "NEUTRAL"
    if delta_pct >= 20:
        return "POSITIVE"
    if delta_pct <= -20:
        return "NEGATIVE"
    return "NEUTRAL"


def load_rev001_baseline():
    p = REV / "REV001_BASELINE.csv"
    with p.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return rows[0] if rows else {}


def load_drive_registry():
    p = REV / "DRIVE_EXPERIMENT_REGISTRY.csv"
    with p.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return rows[0] if rows else {}


def load_growth_comparison():
    p = SEO / "GROWTH_VALIDATION_COMPARISON.csv"
    with p.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_seo_registry():
    p = SEO / "EXPERIMENT_REGISTRY.csv"
    with p.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_snapshot(experiment_id, suffix):
    p = SEO / "experiment_snapshots" / f"{experiment_id}_{suffix}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))
def _as_float(v):
    if v is None or str(v).strip() == "" or str(v).strip().lower() == "null":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def build_comparison():
    """Build the unified comparison rows (deterministic order)."""
    today = date(2026, 8, 16)  # experiment cycle reference date
    rows = []

    # --- REV001 (CTA_PLACEMENT) ---
    rev = load_rev001_baseline()
    obs_days = max(0, (today - date.fromisoformat("2026-08-16")).days)  # REV001 start_date
    rev_aff_clicks = _as_float(rev.get("affiliate_clicks")) or 0.0
    rev_pv = _as_float(rev.get("pageviews")) or 0.0
    base_per1000 = calc_per1000(rev_aff_clicks, rev_pv)
    # post-CTA: no data yet (0 days); keep baseline placeholder, no fabrication
    cur_per1000 = base_per1000
    delta, pct = calc_delta(base_per1000, cur_per1000)
    rows.append({
        "experiment_id": "REV001",
        "experiment_type": "CTA_PLACEMENT",
        "page": "Chinese Food Delivery: Meituan & Ele.me Guide",
        "content_id": "cbt-e464169c4991",
        "start_date": "2026-08-16",
        "observation_days": obs_days,
        "baseline_metric": base_per1000,
        "current_metric": cur_per1000,
        "delta": delta,
        "delta_percent": pct,
        "sample_size": int(rev_aff_clicks),
        "data_source": "CACHED",
        "status": sample_status(obs_days, int(rev_aff_clicks)),
    })

    # --- DRIVE-001 ---
    drive = load_drive_registry()
    drive_obs = max(0, (today - date.fromisoformat("2026-08-16")).days)
    # pre-drive baseline: sitewide 28d (162 sessions / 365 pageviews / 0 clicks)
    drive_per1000 = calc_per1000(0, 365)
    rows.append({
        "experiment_id": "DRIVE-001",
        "experiment_type": "SITE_WIDE_DRIVE",
        "page": "Site-wide Travelpayouts Drive",
        "content_id": "",
        "start_date": "2026-08-16",
        "observation_days": drive_obs,
        "baseline_metric": drive_per1000,
        "current_metric": drive_per1000,
        "delta": 0.0,
        "delta_percent": None,
        "sample_size": 0,
        "data_source": "CACHED",
        "status": sample_status(drive_obs, 0),
    })

    # --- SEO experiments from GROWTH_VALIDATION_COMPARISON ---
    for row in load_growth_comparison():
        exp_id = row.get("experiment", "")
        clicks = _as_float(row.get("current_clicks")) or 0.0
        ctr_b = _as_float(row.get("baseline_ctr"))
        ctr_c = _as_float(row.get("current_ctr"))
        delta, pct = calc_delta(ctr_b or 0.0, ctr_c or 0.0)
        rows.append({
            "experiment_id": exp_id,
            "experiment_type": row.get("type", ""),
            "page": row.get("name", ""),
            "content_id": row.get("content_id", ""),
            "start_date": "2026-08-16",
            "observation_days": 0,
            "baseline_metric": ctr_b if ctr_b is not None else 0.0,
            "current_metric": ctr_c if ctr_c is not None else 0.0,
            "delta": delta,
            "delta_percent": pct,
            "sample_size": int(clicks),
            "data_source": row.get("data_source", "CACHED"),
            "status": sample_status(0, int(clicks)),
        })

    rows.sort(key=lambda r: (r["experiment_id"], r["page"]))
    return rows


def write_comparison(rows, out=None):
    out = out or (REV / "EXPERIMENT_COMPARISON.csv")
    fieldnames = ["experiment_id", "experiment_type", "page", "content_id", "start_date",
                  "observation_days", "baseline_metric", "current_metric", "delta",
                  "delta_percent", "sample_size", "data_source", "status"]
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return out


def main():
    ap = argparse.ArgumentParser(description="Unified revenue+SEO experiment review")
    ap.add_argument("--output", default=None, help="CSV output path")
    args = ap.parse_args()
    rows = build_comparison()
    out = write_comparison(rows, Path(args.output) if args.output else None)
    print(f"WROTE {out} ({len(rows)} experiments)")
    for r in rows:
        print(f"  {r['experiment_id']}: {r['status']} (days={r['observation_days']}, clicks={r['sample_size']})")


if __name__ == "__main__":
    main()
