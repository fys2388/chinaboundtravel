"""P1-REPORT-02: unified KPI engine tests.

Covers (deterministic, no network):
- snapshot builds from real repo artifacts
- 58-post / 58-content_id baseline
- revenue LIVE (Travelpayouts) 或 NOT_AVAILABLE（有凭据/无凭据两态，绝不虚构）
- low-data guard (INSUFFICIENT_SAMPLE)
- experiment states (REV001/REV002/REV003/DRIVE-001/GROWTH-05/recoveries)
- valid data source labels
- deterministic output
- UTF-8 JSON
- no duplicate KPI definitions
"""
import json
import os
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
    n_posts = len(list((REPO / "content" / "posts").glob("*.md")))
    assert cmap["published_posts"]["value"] == n_posts
    assert cmap["content_id_coverage"]["value"] == n_posts


def test_revenue_never_fabricated():
    # 无 TRAVELPAYOUTS_API_TOKEN → 全部 NOT_AVAILABLE/None（绝不虚构）
    # 有凭据 → 全部 LIVE 真实数值（0 也是真实测量），rpm 派生一致
    snap = rke.build_snapshot(AS_OF)
    rmap = {k["name"]: k for k in snap["domains"]["revenue"]["kpis"]}
    live = rmap["revenue"]["data_source_type"] == "LIVE"
    if not live:
        assert rmap["revenue"]["value"] is None
        assert rmap["revenue"]["data_source_type"] == "NOT_AVAILABLE"
        for k in rmap.values():
            assert k["value"] is None, k["name"]
    else:
        assert rmap["revenue"]["value"] is not None
        assert all(k["data_source_type"] == "LIVE" for k in rmap.values())
        assert rmap["orders_conversions"]["value"] is not None


def test_low_data_guard_present():
    snap = rke.build_snapshot(AS_OF)
    assert snap["low_data_warning"] is True
    assert len(snap["low_data_reasons"]) > 0
    amap = {k["name"]: k for k in snap["domains"]["affiliate_funnel"]["kpis"]}
    assert amap["affiliate_clicks_28d"]["status"] == "INSUFFICIENT_SAMPLE"


def test_experiment_states():
    """快照的实验状态必须等于权威登记表 static/experiments.json 的状态。

    原先这里硬编码了 RUNNING，而那是 reporting_kpi_engine 里一个硬编码
    status_override 的产物（把 3 个从未部署 CTA 的实验标成在跑）。owner 于
    2026-09-20 裁定以 static/experiments.json 为准，因此断言改为与登记表逐条
    对齐——登记表一变，这个测试就该跟着报，而不是继续锁死幻影状态。
    """
    snap = rke.build_snapshot(AS_OF)
    exps = {e["experiment_id"]: e for e in snap["domains"]["experiments"]["experiments"]}

    reg_status, reg_start = rke._read_experiment_registry()
    assert reg_status, "登记表为空，无法判定"

    # 结构契约：7 个已知实验必须都在
    for eid in ("REV001", "REV002", "REV003", "DRIVE-001",
                "GROWTH05-CTR-001", "GROWTH07B-TECH-001", "GROWTH07C-INDEX-001"):
        assert eid in exps, f"缺少实验 {eid}"

    # 状态契约：快照 = 登记表
    for eid, st in reg_status.items():
        if eid in exps:
            assert exps[eid]["status"] == st, (
                f"{eid}: 快照 {exps[eid]['status']} != 登记表 {st}"
            )
            # 未启动的实验不该有 start_date（那是幻影的第二个症状）
            if st in ("PLANNED", "PENDING"):
                assert exps[eid]["start_date"] is None, (
                    f"{eid}: 状态 {st} 但 start_date={exps[eid]['start_date']}"
                )

    # 两个索引恢复实验在两份登记里都是 WAITING_RECRAWL，属稳定契约
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
    assert '"revenue"' in text  # 快照含 revenue 域（LIVE 或 NOT_AVAILABLE 均可）
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
