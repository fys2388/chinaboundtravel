"""P1-GROWTH-06: unit tests for the SEO experiment measurement loop.
import re

Covers: CTR/impression/click/position deltas, POSITIVE/NEUTRAL/NEGATIVE
thresholds, INSUFFICIENT_SAMPLE guard, deterministic output, and the
144-hour experiment protection invariants (URL/canonical/affiliate/UTM/
content_id unchanged).
"""
import csv
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import seo_experiment_measurement as sem  # noqa: E402
import pytest

SITE = "https://www.chinaboundtravel.com"


def _make_registry(path, rows):
    fields = ["experiment_id", "content_id", "url", "experiment_type", "start_date",
              "baseline_date", "old_title", "new_title", "old_description",
              "new_description", "primary_metric", "secondary_metrics",
              "minimum_observation_days", "status", "decision",
              "affiliate_clicks", "affiliate_sessions", "revenue"]
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for row in rows:
            base = {f: "" for f in fields}
            base.update(row)
            w.writerow(base)


def _exp(**kw):
    d = dict(
        experiment_id="TST-001", content_id="cbt-x", url="https://example.com/p/",
        experiment_type="TITLE_META", start_date="2026-08-16", baseline_date="",
        old_title="", new_title="", old_description="", new_description="",
        primary_metric="CTR", secondary_metrics="Impressions;Clicks",
        minimum_observation_days="28", status="RUNNING", decision="PENDING",
        affiliate_clicks="", affiliate_sessions="", revenue="",
    )
    d.update(kw)
    return d


# ---------------------------------------------------------------------------
# delta calculations
# ---------------------------------------------------------------------------

def test_pct_change_basic():
    assert sem.pct_change(100, 120) == 20.0
    assert sem.pct_change(0, 5) is None
    assert sem.pct_change(None, 5) is None


def test_compute_deltas_impressions_clicks_ctr_position():
    base = {"impressions": 100, "clicks": 10, "ctr": 0.10, "position": 8.0}
    cur = {"impressions": 120, "clicks": 18, "ctr": 0.15, "position": 6.5}
    d = sem.compute_deltas(base, cur)
    assert d["impressions_delta"] == 20
    assert d["clicks_delta"] == 8
    assert d["position_delta"] == -1.5
    assert d["ctr_pct"] == pytest.approx(50.0)
    assert d["impressions_pct"] == 20.0
    assert abs(d["position_pct"] - (-18.75)) < 1e-9


def test_compute_deltas_zero_baseline_pct_none():
    base = {"impressions": 0, "clicks": 0, "ctr": 0.0, "position": 0.0}
    cur = {"impressions": 10, "clicks": 1, "ctr": 0.10, "position": 5.0}
    d = sem.compute_deltas(base, cur)
    assert d["ctr_pct"] is None
    assert d["impressions_pct"] is None
    assert d["clicks_delta"] == 1


# ---------------------------------------------------------------------------
# classification thresholds
# ---------------------------------------------------------------------------

def test_classify_positive():
    assert sem.classify({"clicks": 40}, 40, 28, 20, ctr_pct=25.0, impressions_pct=0.0) == "POSITIVE"


def test_classify_positive_requires_impressions_not_cratering():
    # CTR +25% but impressions -30%: NOT positive (impression floor violated)
    assert sem.classify({"clicks": 40}, 40, 28, 20, ctr_pct=25.0, impressions_pct=-30.0) == "POSITIVE" or True
    # floor is -10%, so -30% must not be POSITIVE
    r = sem.classify({"clicks": 40}, 40, 28, 20, ctr_pct=25.0, impressions_pct=-30.0)
    assert r != "POSITIVE"


def test_classify_neutral():
    assert sem.classify({"clicks": 40}, 40, 28, 20, ctr_pct=10.0, impressions_pct=5.0) == "NEUTRAL"
    assert sem.classify({"clicks": 40}, 40, 28, 20, ctr_pct=-10.0, impressions_pct=5.0) == "NEUTRAL"


def test_classify_negative():
    assert sem.classify({"clicks": 40}, 40, 28, 20, ctr_pct=-30.0, impressions_pct=5.0) == "NEGATIVE"


def test_classify_insufficient_sample_low_clicks():
    assert sem.classify({"clicks": 5}, 40, 28, 20, ctr_pct=50.0, impressions_pct=0.0) == "INSUFFICIENT_SAMPLE"


def test_classify_insufficient_sample_short_observation():
    assert sem.classify({"clicks": 40}, 10, 28, 20, ctr_pct=50.0, impressions_pct=0.0) == "INSUFFICIENT_SAMPLE"


# ---------------------------------------------------------------------------
# registry + deterministic end-to-end (no network)
# ---------------------------------------------------------------------------

def test_measure_one_deterministic_with_temp_snapshot_dir():
    with tempfile.TemporaryDirectory() as tmp:
        registry = Path(tmp) / "registry.csv"
        _make_registry(registry, [_exp()])
        reg = sem.load_registry(registry)
        assert len(reg) == 1
        r1 = sem.measure_one(reg[0], days=28, fetch_live=False, snapshot_dir=tmp)
        r2 = sem.measure_one(reg[0], days=28, fetch_live=False, snapshot_dir=tmp)
        assert r1["classification"] == r2["classification"] == "INSUFFICIENT_SAMPLE"
        assert r1["current"] == r2["current"]
        assert r1["baseline"] == r2["baseline"]
        # baseline persists and equals current at T0
        assert r2["baseline"]["impressions"] == 0
        # snapshots written
        snaps = list(Path(tmp).glob("TST-001_2*.json")) + list(Path(tmp).glob("TST-001_baseline.json"))
        assert len(snaps) == 2


# ---------------------------------------------------------------------------
# 144-hour experiment protection (GROWTH-05 invariants)
# ---------------------------------------------------------------------------

def _fm_value(text, key):
    for line in text.splitlines():
        m = re.match(r"^\s*" + re.escape(key) + r"\s*[:=]\s*(.+)$", line)
        if m:
            val = m.group(1).strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
                val = val[1:-1]
            return val
    return None


def test_144h_experiment_protection_invariants():
    registry = sem.load_registry()
    row = sem.find_experiment(registry, "GROWTH05-CTR-001")
    assert row is not None, "GROWTH05-CTR-001 must exist in EXPERIMENT_REGISTRY.csv"
    post = REPO / "content" / "posts" / "144-hour-visa-free-transit-guide.md"
    text = post.read_text(encoding="utf-8")
    # content_id / URL / canonical unchanged
    assert _fm_value(text, "content_id") == row["content_id"]
    expected_url = SITE + "/posts/144-hour-visa-free-transit-guide/"
    assert row["url"].rstrip("/") == expected_url.rstrip("/")
    assert _fm_value(text, "canonicalURL") == expected_url
    body = text.split("---", 2)[-1]
    # The GROWTH-12 CTA must still be present; the "转化与排名优化" task additionally
    # adds config-driven soft-recommend blocks and deep-optimization sections.
    assert "visa_cta_mid_content" in body, "GROWTH-12 CTA must remain"
    assert "affiliate-mid-cta" in body
    assert "soft-recommend" in body
    # body must not hardcode affiliate URLs/IDs (config-driven at render time)
    assert "aid=" not in body, "no hardcoded affiliate IDs in body"
    assert "offer_id" not in body, "no hardcoded affiliate offer ids in body"
    # external links must be authoritative/official sources, not affiliate hosts
    for m in re.finditer(r"https?://[^\s)\]]+", body):
        url = m.group(0)
        assert not any(h in url for h in ("booking.com", "airalo.com", "klook",
                                          "safetywing.com", "trip.com", "affiliatescn")), url


def test_registry_schema_includes_revenue_fields():
    registry = sem.load_registry()
    assert registry, "registry must not be empty"
    for row in registry:
        assert "affiliate_clicks" in row
        assert "affiliate_sessions" in row
        assert "revenue" in row
        assert row.get("status", "").strip() == "RUNNING"
        assert row.get("decision", "").strip() == "PENDING"
