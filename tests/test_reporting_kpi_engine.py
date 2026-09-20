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


# --------------------------------------------------------------------------
# 数据源陈旧度：有数值 ≠ 测量在
# --------------------------------------------------------------------------
class TestSourceStaleness:
    """每日快照会把同一份静态基线连盖几十天日期（实测 2026-08-17..09-20 共 24
    个快照 indexed_pages 恒为 69，全部指向 2026-08-16 那次抓取）。这类 CACHED KPI
    必须显式标陈旧，否则日报拿过期数字当今日结论。

    注意：陈旧是「观测点相对 as_of」的概念，不是文件的绝对属性。
    as_of=2026-08-17 时那些 08-15/16 的观测是新鲜的；只有把它放到
    2026-09-20 再看才会暴露。所以下面显式传入要测的日期。
    """
    LATE = date(2026, 9, 20)

    def test_parse_observed_date_from_source_string(self):
        obs, age = rke._source_observed_date(
            "reports/seo/SEO_BASELINE_2026-08.md (GSC API 2026-08-15)", self.LATE)
        assert obs == "2026-08-15"
        assert age == 36

    def test_takes_latest_date_when_several_present(self):
        obs, age = rke._source_observed_date(
            "reports/x.md (2026-08-01) .. (2026-09-10)", self.LATE)
        assert obs == "2026-09-10"
        assert age == 10

    def test_recent_source_is_not_stale(self):
        rke._set_as_of(self.LATE)
        k = rke._kpi("fresh", "m", 42, "n", "CACHED",
                     "reports/seo/x.md (2026-09-18)", "c", "daily")
        assert k["stale_source"] is False
        assert k["status"] == "OK"

    def test_old_cached_source_is_flagged_stale(self):
        rke._set_as_of(self.LATE)
        k = rke._kpi("old", "m", 69, "n", "CACHED",
                     "reports/seo/INDEX_COVERAGE_BASELINE.md (GSC UI 2026-08-16)",
                     "c", "daily")
        assert k["stale_source"] is True
        assert k["status"] == "STALE_SOURCE"
        assert k["source_age_days"] == 35
        # 数值必须保留（可作趋势基线），不能被当成 NOT_AVAILABLE 丢掉
        assert k["value"] == 69

    def test_stale_does_not_clobber_insufficient_sample(self):
        """陈旧标记绝不能覆盖更强的信号 —— 覆盖会让 low_data_reasons 静默归零。"""
        rke._set_as_of(self.LATE)
        k = rke._kpi("x", "m", 0, "n", "CACHED",
                     "reports/y.md (2026-07-01)", "c", "daily",
                     status="INSUFFICIENT_SAMPLE")
        assert k["status"] == "INSUFFICIENT_SAMPLE"
        assert k["stale_source"] is True  # 标记仍在，供 stale_sources 汇总

    def test_not_available_ignores_staleness(self):
        rke._set_as_of(self.LATE)
        k = rke._kpi("none", "m", None, "n", "CACHED",
                     "reports/y.md (2026-01-01)", "c")
        assert k["stale_source"] is False
        assert k["status"] == "NOT_AVAILABLE"

    def test_fresh_at_original_asof_not_stale(self):
        """同一份数据在它的观测日附近是新鲜的 —— 陈旧必须相对 as_of 判定。"""
        rke._set_as_of(date(2026, 8, 17))
        k = rke._kpi("a", "m", 69, "n", "CACHED",
                     "reports/seo/INDEX_COVERAGE_BASELINE.md (GSC UI 2026-08-16)",
                     "c", "daily")
        assert k["stale_source"] is False
        assert k["status"] == "OK"

    def test_snapshot_reports_stale_sources(self):
        """放到 09-20 再看，2026-08-16 的基线就暴露为 35 天陈旧。"""
        snap = rke.build_snapshot(self.LATE)
        st = snap["stale_sources"]
        assert st["stale_after_days"] == rke.STALE_AFTER_DAYS
        assert st["count"] > 0, "09-20 视角下必然有 CACHED 且已陈旧的指标"
        assert st["oldest_age_days"] >= st["stale_after_days"]
        for row in st["rows"]:
            assert row["source_age_days"] > rke.STALE_AFTER_DAYS
            assert row["domain"] and row["name"]
        assert any(r["name"] == "indexed_pages" for r in st["rows"])

    def test_low_data_reasons_survive_stale_marking(self):
        """回归保护：stale 标记引入前是 8 条，引入时曾被覆盖成 0。"""
        snap = rke.build_snapshot(self.LATE)
        assert len(snap["low_data_reasons"]) > 0
        assert any("INSUFFICIENT_SAMPLE" in r or "sample below guard" in r
                   for r in snap["low_data_reasons"])


# --------------------------------------------------------------------------
# 真实数据接入：原来标 NOT_AVAILABLE 但数据其实已经拉下来
# --------------------------------------------------------------------------
class TestRealDataWiring:
    def test_ga4_real_file_readable(self):
        g = rke._read_ga4_real()
        if not g:
            import pytest
            pytest.skip("ga4_real_data.json 不在仓库里（本地拉取产物）")
        assert g["activeUsers"] == 246
        assert g["period"] == "2026-08-24..2026-09-19"
        assert g["traffic_sources"] == []  # 采集脚本未取 channel 维度

    def test_users_28d_and_engagement_now_live(self):
        snap = rke.build_snapshot(AS_OF)
        tmap = {k["name"]: k for k in snap["domains"]["traffic"]["kpis"]}
        assert tmap["users_28d"]["value"] is not None
        assert tmap["users_28d"]["data_source_type"] == "LIVE"
        assert tmap["engagement_rate_28d"]["value"] is not None
        assert 0 < tmap["engagement_rate_28d"]["value"] < 1
        # traffic_sources 为空 -> 该项必须如实保持 NOT_AVAILABLE，不得臆造 breakdown
        assert tmap["source_channel_mix"]["value"] is None
        assert tmap["source_channel_mix"]["data_source_type"] == "NOT_AVAILABLE"

    def test_updated_pages_from_git_history(self):
        """原实现因「inventory 无 updated_at」直接 NOT_AVAILABLE；
        git 提交历史本身就是权威更新记录。cutoff 必须与 build_content 一致
        （as_of - 30d），否则两边算的不是同一个窗口。"""
        from datetime import timedelta
        cutoff = AS_OF - timedelta(days=30)
        n, src = rke._count_updated_posts(cutoff.isoformat())
        assert isinstance(n, int) and n >= 0
        assert "git log" in src
        snap = rke.build_snapshot(AS_OF)
        c = {k["name"]: k for k in snap["domains"]["content_assets"]["kpis"]}
        assert c["updated_pages"]["data_source_type"] == "LOCAL"
        assert c["updated_pages"]["value"] == n
        # 更新的页数不可能少于同期新发的文章数
        assert c["updated_pages"]["value"] >= (c["new_pages_30d"]["value"] or 0)

    def test_brand_compliance_parses_real_table(self):
        """原实现 grep 一个不存在的 'N/13 PASS' 汇总行，且分母 13 也是错的
        ——审计实际覆盖 113 个模板/配置层。"""
        counts = rke._count_md_table_status(
            rke.REPORTS / "P1_BRAND_02_BRAND_IDENTITY_AUDIT.md")
        assert counts["total"] > 20, f"表行数异常: {counts['total']}"
        snap = rke.build_snapshot(AS_OF)
        b = {k["name"]: k for k in snap["domains"]["brand"]["kpis"]}
        v = b["editorial_persona_compliance"]
        assert v["value"] == f"{counts['PASS']}/{counts['total']}"
        assert v["value"] != "31/13"  # 旧的分母
        assert b["editorial_persona_compliance"]["value"].count("/") == 1
