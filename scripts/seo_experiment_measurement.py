#!/usr/bin/env python3
"""P1-GROWTH-06: SEO experiment measurement loop.

Reads ``EXPERIMENT_REGISTRY.csv`` and computes baseline/current metrics plus
deltas for each RUNNING experiment.

Data sources (deterministic, no LLM):
1. Live GSC Search Analytics (``--fetch-live``) via ``gsc_utils``; on any
   failure it falls back to the offline raw CSVs and records ``source=RAW``.
2. Existing raw CSVs in ``reports/seo/`` (default; raw_pages_28d.csv,
   raw_pages_90d.csv, raw_dates_28d.csv, raw_dates_90d.csv).

Classification rules (transparent):
- INSUFFICIENT_SAMPLE: observed days < minimum_observation_days OR
  current clicks < min_clicks (default 20). Never declare success/failure
  on tiny samples.
- POSITIVE: CTR change >= +20% AND impressions change >= -10%
  (CTR improved without a meaningful impression drop).
- NEUTRAL: CTR change within +/-20%.
- NEGATIVE: CTR change <= -20%.

Outputs:
- reports/seo/EXPERIMENT_RESULTS.md (all experiments)
- reports/seo/experiment_snapshots/<experiment_id>_<date>.csv (per-run snapshot)
- reports/seo/experiment_snapshots/<experiment_id>_baseline.json (first run)
"""

import argparse
import csv
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SEO_DIR = REPO / "reports" / "seo"
DEFAULT_REGISTRY = SEO_DIR / "EXPERIMENT_REGISTRY.csv"
DEFAULT_SNAPSHOT_DIR = SEO_DIR / "experiment_snapshots"
DEFAULT_RESULTS = SEO_DIR / "EXPERIMENT_RESULTS.md"
DEFAULT_MIN_OBSERVATION_DAYS = 28
DEFAULT_MIN_CLICKS = 20
CTR_POSITIVE_PCT = 20.0
CTR_NEGATIVE_PCT = -20.0
IMPRESSION_FLOOR_PCT = -10.0  # impressions may not drop more than 10% for POSITIVE


# --------------------------------------------------------------------------
# registry
# --------------------------------------------------------------------------

def load_registry(path=DEFAULT_REGISTRY):
    if not Path(path).is_file():
        return []
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def find_experiment(registry, experiment_id):
    for row in registry:
        if row.get("experiment_id", "").strip() == experiment_id:
            return row
    return None


# --------------------------------------------------------------------------
# metrics loading (offline raw CSVs / live GSC)
# --------------------------------------------------------------------------

def _read_csv_rows(path):
    if not Path(path).is_file():
        return []
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def load_page_metrics_from_csv(raw_pages_csv, url):
    """Return dict(impressions, clicks, ctr, position) for one page URL."""
    url = (url or "").rstrip("/")
    for row in _read_csv_rows(raw_pages_csv):
        key = (row.get("keys") or "").strip().rstrip("/")
        if key == url:
            return {
                "impressions": int(float(row.get("impressions") or 0)),
                "clicks": int(float(row.get("clicks") or 0)),
                "ctr": float(row.get("ctr") or 0.0),
                "position": float(row.get("position") or 0.0),
            }
    return {"impressions": 0, "clicks": 0, "ctr": 0.0, "position": 0.0}


def load_live_page_metrics(site_url, url, start_date, end_date):
    """Fetch single-page metrics from GSC Search Analytics (live)."""
    sys.path.insert(0, str(REPO / "scripts"))
    import gsc_utils  # local import keeps offline runs dependency-free

    creds = gsc_utils.build_credentials()
    if creds is None:
        raise RuntimeError("NO_CREDENTIALS")
    from googleapiclient.discovery import build

    svc = build("searchconsole", "v1", credentials=creds, cache_discovery=False)
    body = {
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "dimensions": ["page"],
        "rowLimit": 25,
    }
    resp = svc.searchanalytics().query(siteUrl=site_url, body=body).execute()
    target = (url or "").rstrip("/")
    for row in resp.get("rows", []):
        key = (row.get("keys") or [""])[0].rstrip("/")
        if key == target:
            return {
                "impressions": int(row.get("impressions") or 0),
                "clicks": int(row.get("clicks") or 0),
                "ctr": float(row.get("ctr") or 0.0),
                "position": float(row.get("position") or 0.0),
            }
    return {"impressions": 0, "clicks": 0, "ctr": 0.0, "position": 0.0}


def resolve_current_metrics(experiment, days, fetch_live):
    """Return (metrics, source) preferring live GSC when requested."""
    url = experiment.get("url", "").strip()
    today = date.today()
    start = today - __import__("datetime").timedelta(days=days - 1)
    if fetch_live:
        try:
            site = os.environ.get("GSC_SITE_URL", "https://www.chinaboundtravel.com/")
            m = load_live_page_metrics(site, url, start, today)
            if m["impressions"] or m["clicks"]:
                return m, "LIVE"
            raise RuntimeError("EMPTY_LIVE_RESPONSE")
        except Exception as exc:
            print(f"[warn] live GSC unavailable ({type(exc).__name__}); using raw CSVs", file=sys.stderr)
    raw = SEO_DIR / f"raw_pages_{days}d.csv"
    return load_page_metrics_from_csv(raw, url), "RAW"


# --------------------------------------------------------------------------
# delta + classification
# --------------------------------------------------------------------------

def pct_change(before, after):
    if before in (None, "") or float(before) == 0:
        return None
    return (float(after) - float(before)) / float(before) * 100.0


def compute_deltas(baseline, current):
    deltas = {}
    for key in ("impressions", "clicks", "ctr", "position"):
        b, c = float(baseline.get(key) or 0.0), float(current.get(key) or 0.0)
        deltas[key + "_delta"] = c - b
        deltas[key + "_pct"] = pct_change(b, c)
    return deltas


def classify(current, observed_days, min_observation_days, min_clicks,
             ctr_pct, impressions_pct):
    """Return classification status string per transparent rules."""
    if observed_days < min_observation_days or int(current.get("clicks") or 0) < min_clicks:
        return "INSUFFICIENT_SAMPLE"
    if ctr_pct is None:
        return "INSUFFICIENT_SAMPLE"
    if ctr_pct >= CTR_POSITIVE_PCT and (impressions_pct is None or impressions_pct >= IMPRESSION_FLOOR_PCT):
        return "POSITIVE"
    if ctr_pct <= CTR_NEGATIVE_PCT:
        return "NEGATIVE"
    return "NEUTRAL"


# --------------------------------------------------------------------------
# baseline persistence
# --------------------------------------------------------------------------

def baseline_path(experiment_id, snapshot_dir=DEFAULT_SNAPSHOT_DIR):
    return Path(snapshot_dir) / f"{experiment_id}_baseline.json"


def load_baseline(experiment_id, snapshot_dir=DEFAULT_SNAPSHOT_DIR):
    p = baseline_path(experiment_id, snapshot_dir)
    if p.is_file():
        return json.loads(p.read_text(encoding="utf-8"))
    return None


def save_baseline(experiment_id, metrics, observed_date, snapshot_dir=DEFAULT_SNAPSHOT_DIR):
    Path(snapshot_dir).mkdir(parents=True, exist_ok=True)
    payload = {"experiment_id": experiment_id, "baseline_date": observed_date,
               "metrics": metrics}
    baseline_path(experiment_id, snapshot_dir).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


# --------------------------------------------------------------------------
# snapshot + results
# --------------------------------------------------------------------------

def write_snapshot(experiment_id, payload, snapshot_dir=DEFAULT_SNAPSHOT_DIR):
    Path(snapshot_dir).mkdir(parents=True, exist_ok=True)
    stamp = date.today().isoformat()
    out = Path(snapshot_dir) / f"{experiment_id}_{stamp}.json"
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def measure_one(experiment, days, fetch_live, snapshot_dir):
    exp_id = experiment.get("experiment_id", "").strip()
    start_date = experiment.get("start_date", "").strip()
    min_days = int(float(experiment.get("minimum_observation_days") or DEFAULT_MIN_OBSERVATION_DAYS))
    observed_days = 0
    try:
        start = date.fromisoformat(start_date) if start_date else date.today()
        observed_days = max(0, (date.today() - start).days)
    except ValueError:
        observed_days = 0

    current, source = resolve_current_metrics(experiment, days, fetch_live)
    baseline = load_baseline(exp_id, snapshot_dir)
    if baseline is None:
        baseline = save_baseline(exp_id, current, date.today().isoformat(), snapshot_dir)
        baseline_metrics = current
    else:
        baseline_metrics = baseline.get("metrics", {})

    deltas = compute_deltas(baseline_metrics, current)
    status = classify(current, observed_days, min_days, DEFAULT_MIN_CLICKS,
                      deltas.get("ctr_pct"), deltas.get("impressions_pct"))

    payload = {
        "experiment_id": exp_id,
        "content_id": experiment.get("content_id", "").strip(),
        "url": experiment.get("url", "").strip(),
        "start_date": start_date,
        "baseline_date": baseline.get("baseline_date", start_date),
        "observed_days": observed_days,
        "minimum_observation_days": min_days,
        "data_source": source,
        "baseline": baseline_metrics,
        "current": current,
        "deltas": deltas,
        "classification": status,
        "low_sample_warning": int(current.get("clicks") or 0) < DEFAULT_MIN_CLICKS,
        "measured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    write_snapshot(exp_id, payload, snapshot_dir)
    return payload


def render_results(rows):
    lines = ["# SEO Experiment Results", "",
             "- Generated: " + date.today().isoformat(),
             "- Data source: per-experiment (LIVE when GSC reachable, else raw CSVs)",
             "- LOW_SAMPLE_WARNING: clicks < %d or observation < %d days => INSUFFICIENT_SAMPLE"
             % (DEFAULT_MIN_CLICKS, DEFAULT_MIN_OBSERVATION_DAYS), "",
             "| experiment | content | baseline period | current period | impressions (b→c) | clicks (b→c) | ctr (b→c) | position (b→c) | delta ctr% | status | recommendation |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        b, c = r["baseline"], r["current"]
        lines.append(
            "| {exp} | {cid} | {bd} | {md} | {bi}→{ci} | {bc}→{cc} | {bctr}→{cctr} | {bp}→{cp} | {dpct} | {st} | {rec} |".format(
                exp=r["experiment_id"], cid=r["content_id"],
                bd=r.get("baseline_date", ""), md=r.get("measured_at", "")[:10],
                bi=b["impressions"], ci=c["impressions"],
                bc=b["clicks"], cc=c["clicks"],
                bctr=round(float(b["ctr"]) * 100, 2), cctr=round(float(c["ctr"]) * 100, 2),
                bp=round(float(b["position"]), 2), cp=round(float(c["position"]), 2),
                dpct=("n/a" if r["deltas"].get("ctr_pct") is None
                      else round(r["deltas"]["ctr_pct"], 1)),
                st=r["classification"],
                rec={"POSITIVE": "Keep / double down", "NEUTRAL": "Monitor",
                     "NEGATIVE": "Revert or adjust", "INSUFFICIENT_SAMPLE": "Wait for data"}
                .get(r["classification"], "Monitor")))
    lines += ["", "## Notes", "",
              "- POSITIVE: CTR delta >= +20% with impressions delta >= -10%.",
              "- NEUTRAL: CTR delta within +/-20%.",
              "- NEGATIVE: CTR delta <= -20%.",
              "- INSUFFICIENT_SAMPLE: clicks < %d or observation < %d days; no success/failure claim." % (
                  DEFAULT_MIN_CLICKS, DEFAULT_MIN_OBSERVATION_DAYS),
              "- Revenue fields (affiliate_clicks/affiliate_sessions/revenue) are reserved and may be null."]
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="SEO experiment measurement loop")
    ap.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    ap.add_argument("--experiment-id", default=None, help="measure one experiment")
    ap.add_argument("--all", action="store_true", help="measure every RUNNING experiment")
    ap.add_argument("--days", type=int, default=28, help="lookback days for current metrics")
    ap.add_argument("--output", default=str(DEFAULT_RESULTS))
    ap.add_argument("--snapshot-dir", default=str(DEFAULT_SNAPSHOT_DIR))
    ap.add_argument("--fetch-live", action="store_true", help="try live GSC first")
    args = ap.parse_args(argv)

    registry = load_registry(args.registry)
    if not registry:
        print("registry empty or missing:", args.registry)
        return 2
    selected = ([r for r in registry if r.get("experiment_id", "").strip() == args.experiment_id]
                if args.experiment_id
                else ([r for r in registry if (r.get("status") or "").strip().upper() == "RUNNING"]
                      if args.all else registry))
    if not selected:
        print("no experiments selected")
        return 2

    rows = [measure_one(r, args.days, args.fetch_live, args.snapshot_dir) for r in selected]
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_results(rows), encoding="utf-8")
    print(f"wrote {out}")
    for r in rows:
        print(f"{r['experiment_id']}: {r['classification']} (clicks={r['current']['clicks']}, "
              f"days={r['observed_days']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
