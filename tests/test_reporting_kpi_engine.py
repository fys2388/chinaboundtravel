"""P1-REPORT-02: unified KPI engine tests.

Covers (deterministic, no network):
- snapshot builds from real repo artifacts
- 58-post / 58-content_id baseline
- NULL revenue (never fabricated)
- low-data guard (INSUFFICIENT_SAMPLE)
- experiment states (REV001/REV002/REV003/DRIVE-001/GROWTH-05/recoveries)
- valid data source labels
- deterministic output
- UTF-8 JSON
- no duplicate KPI definitions
"""
import json
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import reporting_kpi_engine as rke

AS_OF = date(2026, 8, 17)
VALID_LABELS = ("LIVE", "CACHED", "LOCAL", "NOT_AVAILABLE")


def test_snapshot_schema():
    snap = rke.build_snapshot(AS_OF)
    assert snap["schema"] == "chinabound-2.0-kpi-snapshot"
    assert snap["as_of"] == "2026-08-17"
    assert set(snap["domains"]) == {
        "traffic", "seo_gsc", "content_assets", "brand", "affiliate_funnel",
        "revenue", "experiments", "commercial_clusters", "operations",
        "social_growth", "content_trust", "growth_funnel"}


def test_current_content_baseline():
    snap = rke.build_snapshot(AS_OF)
    cmap = {k["name"]: k for k in snap["domains"]["content_assets"]["kpis"]}
    assert cmap["published_posts"]["value"] == 58
    assert cmap["content_id_coverage"]["value"] == 58


def test_revenue_null():
    snap = rke.build_snapshot(AS_OF)
    rmap = {k["name"]: k for k in snap["domains"]["revenue"]["kpis"]}
    assert rmap["revenue"]["value"] is None
    assert rmap["revenue"]["data_source_type"] == "NOT_AVAILABLE"
    for k in rmap.values():
        assert k["value"] is None, k["name"]


def test_low_data_guard_present():
    snap = rke.build_snapshot(AS_OF)
    assert snap["low_data_warning"] is True
    assert len(snap["low_data_reasons"]) > 0
    amap = {k["name"]: k for k in snap["domains"]["affiliate_funnel"]["kpis"]}
    assert amap["affiliate_clicks_28d"]["status"] == "INSUFFICIENT_SAMPLE"


def test_experiment_states():
    snap = rke.build_snapshot(AS_OF)
    exps = {e["experiment_id"]: e for e in snap["domains"]["experiments"]["experiments"]}
    assert exps["REV001"]["status"] == "RUNNING"
    assert exps["REV002"]["status"] == "RUNNING"
    assert exps["REV003"]["status"] == "PENDING"
    assert exps["DRIVE-001"]["status"] == "RUNNING"
    assert exps["GROWTH05-CTR-001"]["status"] == "RUNNING"
    assert exps["GROWTH07B-TECH-001"]["status"] == "WAITING_RECRAWL"
    assert exps["GROWTH07C-INDEX-001"]["status"] == "WAITING_RECRAWL"


def test_data_source_labels_valid():
    snap = rke.build_snapshot(AS_OF)
    for domain, dom in snap["domains"].items():
        if "kpis" in dom:
            for k in dom["kpis"]:
                assert k["data_source_type"] in VALID_LABELS, k["name"]


def test_no_duplicate_kpi_definitions():
    snap = rke.build_snapshot(AS_OF)
    seen = {}
    for domain, dom in snap["domains"].items():
        for k in dom.get("kpis", []):
            key = f"{domain}.{k['name']}"
            assert key not in seen, key
            seen[key] = True


def test_snapshot_json_utf8(tmp_path):
    snap = rke.build_snapshot(AS_OF)
    out = tmp_path / "snap.json"
    rke.write_snapshot(snap, out)
    text = out.read_text(encoding="utf-8")
    assert "REVENUE_NOT_AVAILABLE" in text
    json.loads(text)  # valid JSON


def test_snapshot_deterministic():
    a = rke.build_snapshot(AS_OF)
    b = rke.build_snapshot(AS_OF)
    assert json.dumps(a, ensure_ascii=False, sort_keys=True) == json.dumps(b, ensure_ascii=False, sort_keys=True)


def test_clusters_and_operations_present():
    snap = rke.build_snapshot(AS_OF)
    clusters = snap["domains"]["commercial_clusters"]["clusters"]
    names = {c["cluster"] for c in clusters}
    assert {"China Transportation", "China Payment", "China Connectivity"} <= names
    omap = {k["name"]: k for k in snap["domains"]["operations"]["kpis"]}
    assert omap["security_scan"]["value"] == "PASS"
