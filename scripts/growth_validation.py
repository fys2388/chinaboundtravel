#!/usr/bin/env python3
"""P1-GROWTH-08: Growth validation dashboard generator.

Tracks CTR experiments, index recovery, and technical SEO fixes using GSC
Search Analytics (live API preferred, cached raw CSVs as fallback) plus
read-only URL Inspection.

Outputs (under reports/seo/):
  - GROWTH_VALIDATION_COMPARISON.csv
  - GROWTH_VALIDATION_DASHBOARD.md
  - GROWTH_QUERY_MOVEMENT.md
  - REVENUE_MEASUREMENT_READINESS.md

Design: pure, deterministic scoring/classification functions separated from
I/O so tests can feed fixtures without hitting the network.
"""

from __future__ import annotations

import csv
import json
import sys
import time
from dataclasses import dataclass, asdict
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import quote

sys.stdout.reconfigure(encoding="utf-8")

BLOG_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent
REPORTS_SEO = BLOG_ROOT / "reports" / "seo"
REPORTS_SEO.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(SCRIPTS))

SITE = "https://www.chinaboundtravel.com/"

# ---------------------------------------------------------------------------
# Targets (content_id / canonical URL)
# ---------------------------------------------------------------------------
TARGETS = {
    "A": {
        "experiment": "GROWTH05-CTR-001",
        "content_id": "cbt-b4ff4381a014",
        "url": "https://www.chinaboundtravel.com/posts/144-hour-visa-free-transit-guide/",
        "name": "144-Hour Visa",
        "type": "CTR_TITLE_META",
        "cache_aliases": ["https://www.chinaboundtravel.com/posts/144-hour-visa-free-transit-guide/"],
    },
    "B": {
        "experiment": "GROWTH07C-INDEX-001",
        "content_id": "cbt-255af4ed003a",
        "url": "https://www.chinaboundtravel.com/posts/wechat-pay-for-foreigners-step-by-step-setup-and-common-mistakes-to-avoid-guide/",
        "name": "WeChat Pay Weak",
        "type": "INDEX_RECOVERY",
        "cache_aliases": ["https://www.chinaboundtravel.com/posts/wechat-pay-for-foreigners-step-by-step-setup-and-common-mistakes-to-avoid-guide/"],
    },
    "C": {
        "experiment": "GROWTH07B-TECH-001",
        "content_id": "cbt-cc4549872c92",
        "url": "https://www.chinaboundtravel.com/posts/china-high-speed-rail-how-to-book-tickets/",
        "name": "High-Speed Rail Booking",
        "type": "TECHNICAL_INDEX_FIX",
        "cache_aliases": [
            "https://www.chinaboundtravel.com/posts/2026-05-25-china-high-speed-rail-how-to-book-tickets/",
            "https://www.chinaboundtravel.com/posts/china-high-speed-rail-how-to-book-tickets/",
        ],
        "legacy_url": "https://www.chinaboundtravel.com/posts/2026-05-25-china-high-speed-rail-how-to-book-tickets/",
    },
}

WINDOWS = ["7d", "14d", "28d", "90d"]
WINDOW_DAYS = {"7d": 7, "14d": 14, "28d": 28, "90d": 90}
LOW_CLICK_THRESHOLD = 20

_SITE_PREFIX = "https://www.chinaboundtravel.com"

# Known inspection results from earlier rounds (07B/07C live API reads) used as
# fallback when no live inspection is available (e.g. --cached mode).
KNOWN_INSPECTION_FALLBACK = {
    "B": {
        "coverageState": "Alternate page with proper canonical tag",
        "verdict": "NEUTRAL",
        "indexingState": "NOT_INDEXED",
        "lastCrawlTime": "2026-07-28",
    },
    "C": {
        "coverageState": "NOT_INDEXED (pre-recrawl snapshot)",
        "verdict": "NEUTRAL",
        "indexingState": "NOT_INDEXED",
        "lastCrawlTime": "NOT_AVAILABLE",
    },
}


_URL_INSPECT_ENDPOINT = "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"
_SA_ENDPOINT_TMPL = "https://searchconsole.googleapis.com/webmasters/v3/sites/{encoded}/searchAnalytics/query"


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------
def _num(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def low_sample_guard(clicks: float, threshold: int = LOW_CLICK_THRESHOLD) -> str:
    """Return 'INSUFFICIENT_SAMPLE' when clicks below threshold, else 'OK'."""
    return "INSUFFICIENT_SAMPLE" if clicks < threshold else "OK"


def compute_deltas(baseline: dict, current: dict) -> dict:
    b_imp, c_imp = _num(baseline.get("impressions")), _num(current.get("impressions"))
    b_clk, c_clk = _num(baseline.get("clicks")), _num(current.get("clicks"))
    b_ctr, c_ctr = _num(baseline.get("ctr")), _num(current.get("ctr"))
    b_pos, c_pos = _num(baseline.get("position")), _num(current.get("position"))
    def pct(old, new):
        if old == 0:
            return None if new == 0 else 100.0
        return round((new - old) / old * 100.0, 2)
    return {
        "baseline_impressions": b_imp,
        "current_impressions": c_imp,
        "impressions_delta": round(c_imp - b_imp, 2),
        "impressions_delta_pct": pct(b_imp, c_imp),
        "baseline_clicks": b_clk,
        "current_clicks": c_clk,
        "clicks_delta": round(c_clk - b_clk, 2),
        "clicks_delta_pct": pct(b_clk, c_clk),
        "baseline_ctr": round(b_ctr, 6),
        "current_ctr": round(c_ctr, 6),
        "ctr_delta": round(c_ctr - b_ctr, 6),
        "ctr_delta_pct": pct(b_ctr, c_ctr),
        "baseline_position": round(b_pos, 2),
        "current_position": round(c_pos, 2),
        "position_delta": round(c_pos - b_pos, 2),
    }


def classify_status(coverage_state: str, verdict: str, has_technical_block: bool = False) -> str:
    """Index-status classification from a GSC URL Inspection result."""
    cs = (coverage_state or "").lower()
    if has_technical_block:
        return "TECHNICAL_BLOCK"
    if ("not" in cs and "index" in cs) or "noindex" in cs or "meta tag" in cs:
        return "NOT_INDEXED"
    if "indexed" in cs or verdict == "PASS":
        return "INDEXED"
    if "alternate" in cs or "duplicate" in cs:
        return "WAITING_RECRAWL"
    return "UNKNOWN"


def impact_score(index_status: str, metrics: dict, query_delta: dict) -> dict:
    """Internal experiment score /100. Explicitly NOT a Google score."""
    score = 0.0
    reasons = []
    if index_status == "INDEXED":
        score += 30
        reasons.append("INDEX_GAIN")
    elif index_status == "WAITING_RECRAWL":
        score += 15
        reasons.append("INDEX_PENDING")
    elif index_status == "TECHNICAL_BLOCK":
        score += 0
        reasons.append("INDEX_BLOCKED")
    imp = _num(metrics.get("current_impressions"))
    b_imp = _num(metrics.get("baseline_impressions"))
    if b_imp > 0 and imp > b_imp:
        growth = (imp - b_imp) / b_imp
        score += min(20, 20 * growth)
        reasons.append("IMPRESSION_GAIN")
    pos_delta = _num(metrics.get("position_delta"))
    if pos_delta < 0:
        score += min(25, abs(pos_delta) * 2.5)
        reasons.append("POSITION_GAIN")
    clicks = _num(metrics.get("current_clicks"))
    if clicks >= LOW_CLICK_THRESHOLD:
        ctr_delta = _num(metrics.get("ctr_delta"))
        if ctr_delta > 0:
            score += 15
            reasons.append("CTR_GAIN")
    elif clicks > 0:
        score += 5
        reasons.append("EARLY_CLICKS")
    nq = query_delta.get("new_queries", 0)
    if isinstance(nq, (list, tuple, set, frozenset)):
        nq = len(nq)
    if nq > 0:
        score += 10
        reasons.append("QUERY_EXPANSION")
    score = round(min(100.0, score), 1)
    return {"score": score, "reasons": reasons, "label": "INTERNAL EXPERIMENT SCORE"}


def compare_queries(baseline_queries: dict, current_queries: dict) -> dict:
    """Classify NEW / EMERGING / LOST queries between two query->impressions maps."""
    bq, cq = set(baseline_queries), set(current_queries)
    new_q = cq - bq
    lost_q = bq - cq
    emerging = [q for q in cq if q not in new_q and _num(current_queries.get(q, {}).get("impressions")) > 0
                and _num(baseline_queries.get(q, {}).get("impressions", 0)) > 0
                and _num(current_queries.get(q, {}).get("impressions")) > _num(baseline_queries.get(q, {}).get("impressions"))]
    return {
        "new_queries": sorted(new_q),
        "lost_queries": sorted(lost_q),
        "emerging_queries": sorted(emerging),
    }


# ---------------------------------------------------------------------------
# I/O: GSC API with cached fallback
# ---------------------------------------------------------------------------
def _credentials():
    try:
        from gsc_utils import (SCOPE_WEBMASTERS_READONLY, build_credentials,
                               get_site_url, load_service_account_info)
        info = load_service_account_info()
        if not info:
            return None, None
        creds = build_credentials(info, scopes=[SCOPE_WEBMASTERS_READONLY])
        from google.auth.transport.requests import Request
        creds.refresh(Request())
        return get_site_url(), {"Authorization": f"Bearer {creds.token}"}
    except Exception:
        return None, None


def _post_json(url, headers, payload, timeout=20):
    import requests
    return requests.post(url, headers=headers, json=payload, timeout=timeout)


def fetch_page_metrics_live(site, headers, url, window_days):
    """Return aggregated metrics dict for one page over window_days."""
    import requests
    encoded = quote(site, safe="")
    endpoint = _SA_ENDPOINT_TMPL.format(encoded=encoded)
    end = date.today()
    start = end - timedelta(days=window_days)
    body = {
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "dimensions": ["date"],
        "dimensionFilterGroups": [{"filters": [{"dimension": "page", "operator": "EQUALS", "expression": url}]}],
    }
    r = _post_json(endpoint, headers, body, timeout=25)
    if r.status_code != 200:
        raise RuntimeError(f"SA HTTP {r.status_code}: {r.text[:120]}")
    rows = r.json().get("rows", [])
    agg = {"clicks": 0.0, "impressions": 0.0, "ctr": 0.0, "position": 0.0}
    n = len(rows)
    for row in rows:
        agg["clicks"] += row["clicks"]
        agg["impressions"] += row["impressions"]
        agg["ctr"] += row.get("ctr", 0)
        agg["position"] += row.get("position", 0)
    if n:
        agg["ctr"] = agg["ctr"] / n
        agg["position"] = agg["position"] / n
    return {k: round(v, 6) for k, v in agg.items()}


def fetch_queries_live(site, headers, url, window_days):
    """Return {query: {clicks, impressions, position}} for one page."""
    import requests
    encoded = quote(site, safe="")
    endpoint = _SA_ENDPOINT_TMPL.format(encoded=encoded)
    end = date.today()
    start = end - timedelta(days=window_days)
    body = {
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "dimensions": ["query"],
        "rowLimit": 500,
        "dimensionFilterGroups": [{"filters": [{"dimension": "page", "operator": "EQUALS", "expression": url}]}],
    }
    r = _post_json(endpoint, headers, body, timeout=25)
    if r.status_code != 200:
        raise RuntimeError(f"SA HTTP {r.status_code}: {r.text[:120]}")
    out = {}
    for row in r.json().get("rows", []):
        q = row.get("keys", ["(not provided)"])[0]
        out[q] = {"clicks": row["clicks"], "impressions": row["impressions"],
                  "ctr": row.get("ctr", 0), "position": row.get("position", 0)}
    return out


def fetch_inspection_live(site, headers, url):
    """Return URL Inspection indexStatusResult dict."""
    payload = {"inspectionUrl": url, "siteUrl": site}
    r = _post_json(_URL_INSPECT_ENDPOINT, headers, payload, timeout=25)
    if r.status_code != 200:
        raise RuntimeError(f"Inspect HTTP {r.status_code}: {r.text[:120]}")
    return r.json().get("inspectionResult", {}).get("indexStatusResult", {})


def load_cached_pages(window):
    """Return {page_url: metrics} from cached raw CSV (best effort)."""
    fname = f"raw_pages_{window}.csv"
    path = REPORTS_SEO / fname
    if not path.exists():
        return {}
    out = {}
    with path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            out[row["keys"]] = {"clicks": _num(row["clicks"]), "impressions": _num(row["impressions"]),
                                "ctr": _num(row["ctr"]), "position": _num(row["position"])}
    return out


def load_cached_queries(window):
    fname = f"raw_queries_pages_{window}.csv"
    path = REPORTS_SEO / fname
    if not path.exists():
        return {}
    out = {}
    with path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            parts = row["keys"].split(";", 1)
            if len(parts) != 2:
                continue
            q, page = parts
            out.setdefault(page, {})[q] = {"clicks": _num(row["clicks"]), "impressions": _num(row["impressions"]),
                                           "ctr": _num(row["ctr"]), "position": _num(row["position"])}
    return out


def _abs_url(path: str) -> str:
    """Normalize a cache alias to a full URL (cached CSVs key on full URLs)."""
    return path if path.startswith("http") else _SITE_PREFIX + path


def _match_cached(cached: dict, target: dict, window):
    """Return first cache entry matching any alias (full-URL aware)."""
    for alias in target["cache_aliases"]:
        key = _abs_url(alias)
        if key in cached:
            return cached[key]
        if alias in cached:
            return cached[alias]
    return None


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def run(force_cached: bool = False):
    site, headers = (None, None) if force_cached else _credentials()
    live = bool(site and headers)
    data_source = "LIVE" if live else "CACHED"

    metrics = {}     # key -> {window: {clicks, impressions, ctr, position}}
    queries = {}     # key -> {window: {query: metrics}}
    inspections = {} # key -> inspection dict (may be {})
    used_legacy = set()  # "KEY:window" / "KEY:queries" where data came from legacy URL
    errors = {}

    cached_28 = load_cached_pages("28d") if not live else {}
    cached_90 = load_cached_pages("90d") if not live else {}

    for key, tgt in TARGETS.items():
        metrics[key] = {}
        queries[key] = {}
        for w in WINDOWS:
            days = WINDOW_DAYS[w]
            try:
                if live:
                    m = fetch_page_metrics_live(site, headers, tgt["url"], days)
                    if _num(m.get("impressions")) == 0 and tgt.get("legacy_url"):
                        lm = fetch_page_metrics_live(site, headers, tgt["legacy_url"], days)
                        if _num(lm.get("impressions")) > 0:
                            m = lm
                            used_legacy.add(f"{key}:{w}")
                    metrics[key][w] = m
                else:
                    raise RuntimeError("cached mode")
            except Exception as exc:
                errors[f"{key}:{w}:metrics"] = str(exc)[:120]
                cached = cached_28 if w == "28d" else cached_90 if w == "90d" else cached_28
                got = _match_cached(cached, tgt, w)
                metrics[key][w] = got if got else {"clicks": 0.0, "impressions": 0.0, "ctr": 0.0, "position": 0.0}
        try:
            if live:
                q = fetch_queries_live(site, headers, tgt["url"], 28)
                if not q and tgt.get("legacy_url"):
                    lq = fetch_queries_live(site, headers, tgt["legacy_url"], 28)
                    if lq:
                        q = lq
                        used_legacy.add(f"{key}:queries")
                queries[key]["28d"] = q
            else:
                raise RuntimeError("cached mode")
        except Exception as exc:
            errors[f"{key}:queries"] = str(exc)[:120]
            qmap = load_cached_queries("28d")
            got = qmap.get(tgt["url"]) or next(
                (v for alias in tgt["cache_aliases"] if _abs_url(alias) in qmap for v in [qmap[_abs_url(alias)]]), {})
            queries[key]["28d"] = got
        if key in ("B", "C"):
            try:
                inspections[key] = fetch_inspection_live(site, headers, tgt["url"]) if live else {}
            except Exception as exc:
                errors[f"{key}:inspect"] = str(exc)[:120]
                inspections[key] = {}
            if not inspections[key]:
                inspections[key] = dict(KNOWN_INSPECTION_FALLBACK.get(key, {}))

    return {
        "data_source": data_source,
        "metrics": metrics,
        "queries": queries,
        "inspections": inspections,
        "used_legacy": sorted(used_legacy),
        "errors": errors,
    }


def build_rows(data: dict) -> list:
    rows = []
    for key, tgt in TARGETS.items():
        m = data["metrics"][key]
        # baseline = cached 28d snapshot (pre-experiment/pre-fix where available)
        cached_28 = _match_cached(load_cached_pages("28d"), tgt, "28d") or {}
        cur = m.get("28d", {})
        deltas = compute_deltas(cached_28, cur)
        insp = data["inspections"].get(key, {})
        coverage = insp.get("coverageState", "")
        verdict = insp.get("verdict", "")
        index_status = classify_status(coverage, verdict, has_technical_block=False)
        if not insp:
            index_status = "UNKNOWN"
        clicks = _num(cur.get("clicks"))
        legacy_used = f"{key}:28d" in data.get("used_legacy", []) or "28d" in data.get("used_legacy", [])
        rows.append({
            "experiment": tgt["experiment"],
            "content_id": tgt["content_id"],
            "name": tgt["name"],
            "url": tgt["url"],
            "type": tgt["type"],
            **deltas,
            "index_status": index_status,
            "coverage_state": coverage or "NOT_AVAILABLE",
            "last_crawl": insp.get("lastCrawlTime", "NOT_AVAILABLE"),
            "verdict": verdict or "NOT_AVAILABLE",
            "sample_status": low_sample_guard(clicks),
            "data_source": data["data_source"],
            "legacy_url_used": legacy_used,
        })
    return rows


def write_outputs(data: dict):
    rows = build_rows(data)
    by_key = {r["content_id"]: r for r in rows}

    # comparison CSV
    csv_path = REPORTS_SEO / "GROWTH_VALIDATION_COMPARISON.csv"
    fieldnames = ["experiment", "content_id", "name", "url", "type",
                  "baseline_impressions", "current_impressions", "impressions_delta", "impressions_delta_pct",
                  "baseline_clicks", "current_clicks", "clicks_delta", "clicks_delta_pct",
                  "baseline_ctr", "current_ctr", "ctr_delta", "ctr_delta_pct",
                  "baseline_position", "current_position", "position_delta",
                  "index_status", "coverage_state", "last_crawl", "verdict",
                  "sample_status", "data_source", "legacy_url_used"]
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    # dashboard
    dash = ["# GROWTH VALIDATION DASHBOARD",
            "",
            f"- Generated: {date.today().isoformat()}",
            f"- DATA_SOURCE: {data['data_source']}",
            "- Note: scores below are INTERNAL EXPERIMENT SCORES, not Google scores.",
            "",
            "| Page | Experiment | Type | Days | Index status | Impressions (28d) | Clicks (28d) | CTR (28d) | Position (28d) | Signal |",
            "|---|---|---|---|---|---|---|---|---|---|"]
    statuses = {"A": "INSUFFICIENT_SAMPLE", "B": "WAITING_RECRAWL", "C": "NOT_INDEXED"}
    for key, tgt in TARGETS.items():
        r = by_key.get(tgt["content_id"], {})
        cur = data["metrics"].get(key, {}).get("28d", {})
        status = r.get("index_status", "UNKNOWN")
        if status == "WAITING_RECRAWL":
            signal = "WAITING_RECRAWL"
        elif status == "INDEXED":
            signal = "RUNNING/EARLY_SIGNAL"
        elif status in ("NOT_INDEXED", "UNKNOWN"):
            signal = status
        dash.append(f"| {tgt['name']} | {tgt['experiment']} | {tgt['type']} | 28 | {status} | "
                    f"{_num(cur.get('impressions')):.0f} | {_num(cur.get('clicks')):.0f} | "
                    f"{_num(cur.get('ctr'))*100:.2f}% | {_num(cur.get('position')):.1f} | {signal} |")
    dash.append("")
    dash.append("## Status legend")
    dash.append("- RUNNING: experiment in observation window")
    dash.append("- EARLY_SIGNAL: meaningful movement but below sample threshold")
    dash.append("- VALIDATED: meets thresholds and sample size")
    dash.append("- INSUFFICIENT_SAMPLE: clicks < 20 — do not declare win/loss")
    dash.append("- WAITING_RECRAWL: alternate/duplicate coverage awaiting Google recrawl")
    dash.append("- BLOCKED: technical issue blocking indexing")
    dash.append("- NOT_INDEXED: not indexed (GSC snapshot may predate the fix — check last crawl)")
    dash.append("")
    if data["errors"]:
        dash.append("## API errors (fallback used)")
        for k, v in data["errors"].items():
            dash.append(f"- `{k}`: {v}")
    if data.get("used_legacy"):
        legacy_keys = sorted({k.split(":")[0] for k in data["used_legacy"]})
        dash.insert(4, f"- Note: targets {legacy_keys} metrics come from the legacy dated URL "
                     "(GSC still attributes data to the old URL; new slug URL awaiting data migration).")
    (REPORTS_SEO / "GROWTH_VALIDATION_DASHBOARD.md").write_text("\n".join(dash), encoding="utf-8")

    # query movement
    qm = ["# GROWTH QUERY MOVEMENT", "", f"- Generated: {date.today().isoformat()}",
          f"- DATA_SOURCE: {data['data_source']}", "",
          "Only records movement; no article changes made.", ""]
    for key, tgt in TARGETS.items():
        qmap = data["queries"].get(key, {}).get("28d", {})
        qm.append(f"## {tgt['name']} (`{tgt['content_id']}`)")
        if not qmap:
            qm.append("- No query data (DATA_SOURCE=CACHED single snapshot; movement N/A).")
        else:
            cached_q = load_cached_queries("28d")
            base_q = next((v for alias in tgt["cache_aliases"] if _abs_url(alias) in cached_q
                           for v in [cached_q[_abs_url(alias)]]), {})
            mov = compare_queries(base_q, qmap)
            qm.append(f"- Query count current: {len(qmap)} | baseline: {len(base_q)}")
            qm.append(f"- NEW queries ({len(mov['new_queries'])}): {', '.join(mov['new_queries'][:15]) or 'none'}")
            qm.append(f"- EMERGING queries ({len(mov['emerging_queries'])}): {', '.join(mov['emerging_queries'][:15]) or 'none'}")
            qm.append(f"- LOST queries ({len(mov['lost_queries'])}): {', '.join(mov['lost_queries'][:15]) or 'none'}")
        qm.append("")
    (REPORTS_SEO / "GROWTH_QUERY_MOVEMENT.md").write_text("\n".join(qm), encoding="utf-8")

    # revenue readiness (schema only; values NULL)
    rr = ["# REVENUE MEASUREMENT READINESS", "", f"- Generated: {date.today().isoformat()}",
          "- Status: READY_FOR_FUTURE_EXPERIMENTS (no revenue experiment started)",
          "- Current values: NULL (no revenue data tracked yet; nothing fabricated).", "",
          "| content_id | page | affiliate_click | affiliate_sessions | affiliate_revenue |", "|---|---|---|---|---|"]
    for key, tgt in TARGETS.items():
        rr.append(f"| {tgt['content_id']} | {tgt['url']} | NULL | NULL | NULL |")
    rr.append("")
    rr.append("Future linkage plan: affiliate_click / affiliate_sessions / affiliate_revenue "
              "will be joined to content_id once affiliate tracking is enabled. Until then all values remain NULL.")
    (REPORTS_SEO / "REVENUE_MEASUREMENT_READINESS.md").write_text("\n".join(rr), encoding="utf-8")

    return rows


def main():
    force = "--cached" in sys.argv
    data = run(force_cached=force)
    rows = write_outputs(data)
    print(f"DATA_SOURCE={data['data_source']}")
    for r in rows:
        print(f"{r['name']}: index={r['index_status']} coverage={r['coverage_state'][:40]} "
              f"imp={r['current_impressions']} clicks={r['current_clicks']} "
              f"sample={r['sample_status']}")
    if data.get("used_legacy"):
        print("LEGACY_URL_USED:", data["used_legacy"])
    if data["errors"]:
        print("API errors:", json.dumps(data["errors"], ensure_ascii=False)[:400])
    return 0


if __name__ == "__main__":
    sys.exit(main())
