"""Agent KPI 考核的数据完整性回归测试。

守护 2026-09-18 修复的四个问题：
1. 硬编码字面量（avg_word_count=1808 / publish_rate=4.0）曾被标成 measured
   参与评分 —— 后来接入真实测量，因此「键不存在」不再成立，改为断言值
   等于独立重算结果（见 test_no_hardcoded_literal_metrics）。
2. load_real_revenue_data() 曾完全失效（import 不存在的类 + 判断不存在的
   status 键）且从未被调用 —— 现在必须是可调用函数并返回同构结构。
3. kpi_coverage 曾从未计算 —— 现在必须等于独立算出的实测占比。
4. 小样本比率（tp_clicks < 20）不得产出「精确」转化率。
"""
import json
import re
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import pytest

import agent_kpi_auditor as A


REAL_PROJECT_ROOT = A.PROJECT_ROOT
DAILY_DIR = REAL_PROJECT_ROOT / "reports" / "feishu_daily"


def _daily_files():
    return sorted(DAILY_DIR.glob("daily_*.json"))


def _recompute_content_stats():
    """独立重算平均词数与近 7 天发布量，不依赖 A 的内部实现。

    用于证明这两个值是实测出来的：若有人把它改回硬编码常量，
    独立重算结果会不一致，测试立刻失败。
    """
    posts = sorted((A.PROJECT_ROOT / "content" / "posts").glob("*.md"))
    counts, last7 = [], 0
    now = datetime.now()
    for p in posts:
        text = p.read_text(encoding="utf-8", errors="ignore")
        body = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.S)
        body = re.sub(r"<[^>]+>", " ", body)
        counts.append(len(body.split()))
        m = re.match(r"^---\n(.*?)\n---", text, re.S)
        if m:
            dm = re.search(r"^date:\s*[\"']?(\d{4}-\d{2}-\d{2})", m.group(1), re.M)
            if dm:
                try:
                    if now - datetime.strptime(dm.group(1), "%Y-%m-%d") < timedelta(days=7):
                        last7 += 1
                except ValueError:
                    pass
    assert counts, "content/posts 下应有文章"
    return round(sum(counts) / len(counts), 1), last7


def test_no_hardcoded_literal_metrics():
    """avg_word_count / publish_rate 必须是实测值，不是常量。

    历史上这两个是硬编码 1808 / 4.0，却被标成 status=measured 参与评分。
    2026-09-18 接入真实测量后，原先「键必须不存在」的断言已失效——
    改为断言值等于独立重算结果。
    """
    metrics = A.collect_metrics()
    content = metrics.get("content", {})

    avg, last7 = _recompute_content_stats()
    assert content.get("avg_word_count") == avg, (
        f"avg_word_count={content.get('avg_word_count')} 但独立重算 {avg}——"
        "疑似硬编码常量（历史上曾被固定为 1808）"
    )
    assert content.get("publish_rate") == last7, (
        f"publish_rate={content.get('publish_rate')} 但独立重算近7天 {last7} 篇——"
        "疑似硬编码常量（历史上曾被固定为 4.0）"
    )
    # 反证：这两个 id 确实存在于 KPI 定义里，取值不会因 id 拼错而静默漏掉。
    defined = {k["id"] for k in A.AGENTS["content"]["kpis"]}
    assert "avg_word_count" in defined and "publish_rate" in defined


def test_kpi_coverage_is_actually_computed():
    """kpi_coverage 必须等于独立遍历算出的实测占比，而不是常量。"""
    metrics = A.collect_metrics()
    data = metrics.get("data", {})
    reported = data.get("kpi_coverage")
    assert reported is not None, "kpi_coverage 必须被计算并写入 metrics"

    total = measured = 0
    for aid in A.AGENTS:
        for kpi in A.AGENTS[aid]["kpis"]:
            total += 1
            if metrics.get(aid, {}).get(kpi["id"]) is not None:
                measured += 1
    expected = round(measured / total * 100, 1) if total else 0.0
    assert reported == expected, f"kpi_coverage {reported} != 独立计算 {expected}"
    assert data.get("_total_count") == total
    assert data.get("_measured_count") == measured


def test_daily_report_values_are_real_measurements():
    """日报里的真实实测值必须流入对应 KPI。"""
    files = _daily_files()
    if not files:
        pytest.skip("没有日报 JSON，跳过")
    daily = json.loads(files[-1].read_text(encoding="utf-8-sig"))
    metrics = A.collect_metrics()

    if daily.get("affiliate_revenue") is not None:
        assert metrics["revenue"]["affiliate_revenue"] == daily["affiliate_revenue"]
    if daily.get("engagement_rate") is not None:
        assert metrics["social"]["engagement_rate"] == daily["engagement_rate"]
    if daily.get("ml_new_subscribers") is not None:
        assert metrics["user"]["email_list_growth"] == daily["ml_new_subscribers"]

    # 站点可用性不得从 site_up 接入：CI runner 网络瞬时失败会把 uptime 打成 0 分，
    # 那是给考核注入新的假扣分。
    assert "uptime" not in metrics.get("ops", {}), (
        "ops.uptime 不得取自 daily.site_up —— 2026-09-18 该字段为 False 实为 "
        "CI 网络抖动，当日线上站点实测 HTTP 200"
    )


def test_small_sample_does_not_produce_precise_rate(tmp_path, monkeypatch):
    """样本量不足时不得产出「精确」转化率。"""
    fake_daily = tmp_path / "reports" / "feishu_daily"
    fake_daily.mkdir(parents=True)
    (fake_daily / "daily_2026-01-01.json").write_text(
        json.dumps({"tp_clicks": 3, "tp_bookings": 0, "affiliate_revenue": 1.25}),
        encoding="utf-8",
    )
    monkeypatch.setattr(A, "PROJECT_ROOT", tmp_path)

    metrics = A.collect_metrics()
    assert metrics["revenue"]["affiliate_revenue"] == 1.25
    assert "conversion_rate" not in metrics["revenue"], (
        "3 次点击样本量不足以支撑转化率结论，应留空标记 no_data"
    )

    # 样本量充足时才产出
    (fake_daily / "daily_2026-01-02.json").write_text(
        json.dumps({"tp_clicks": 40, "tp_bookings": 2}), encoding="utf-8"
    )
    metrics = A.collect_metrics()
    assert metrics["revenue"]["conversion_rate"] == 5.0


def test_revenue_loader_returns_structured_metrics_without_side_effects(tmp_path, monkeypatch):
    """load_real_revenue_data 必须读已落盘结果，不发起网络调用、不写文件。"""
    rd = tmp_path / "reports" / "revenue_data"
    rd.mkdir(parents=True)
    (rd / "revenue_data_20260101.json").write_text(json.dumps({
        "collected_at": "2026-01-01T00:00:00",
        "period_days": 30,
        "total_revenue": 42.5,
        "sources": {
            "travelpayouts": {"approved_commission": 12.5},
            "stripe": {"net_revenue": 30.0},
        },
    }), encoding="utf-8")
    monkeypatch.setattr(A, "PROJECT_ROOT", tmp_path)

    out = A.load_real_revenue_data()
    assert out == {
        "revenue": {"affiliate_revenue": 12.5, "ebook_revenue": 30.0}
    }


def test_revenue_loader_empty_when_no_data(tmp_path, monkeypatch):
    """没有落盘数据时返回 {}，而不是伪造 0。"""
    monkeypatch.setattr(A, "PROJECT_ROOT", tmp_path)
    assert A.load_real_revenue_data() == {}


def test_revenue_loader_is_no_longer_orphan():
    """load_real_revenue_data 必须真的被调用（历史上它是零调用方的孤立函数）。"""
    called = []
    original = A.load_real_revenue_data

    def spy():
        called.append(1)
        return original()

    A.load_real_revenue_data = spy
    try:
        A.collect_metrics()
    finally:
        A.load_real_revenue_data = original
    assert called, "load_real_revenue_data() 从未被调用 —— 孤立函数回归"


def test_revenue_collector_import_does_not_fail():
    """import 必须走真实存在的模块，而不是不存在的类。"""
    assert A.REVENUE_COLLECTOR_AVAILABLE is True
    # 该模块只有函数，没有 RevenueDataCollector 类 —— 旧 import 形式必须失败
    with pytest.raises(ImportError):
        from revenue_data_collector import RevenueDataCollector  # noqa: F401


# ── 数据覆盖率与分数上限 ─────────────────────────────────────

def _score_agent(agent_id, kpi_values):
    """按 KPI id 喂真实值，其余留 no_data，返回该 Agent 的考核结果。"""
    metrics = {k: v for k, v in kpi_values.items()}
    return A.calculate_agent_score(agent_id, metrics)


def test_no_data_placeholder_is_a_named_constant():
    """占位分必须只有一处定义，不能散落五六个 70.0 各自漂移。"""
    assert A.NO_DATA_BASE_SCORE == 70.0
    r = _score_agent("content", {})
    assert r["kpi_results"][0]["score"] == A.NO_DATA_BASE_SCORE
    assert r["kpi_results"][0]["status"] == "no_data"


def test_score_ceiling_matches_the_placeholder_math():
    """上限 = 70 + 30 * 已接数据权重占比。
    没接数据前分数有硬顶，这个关系必须严格成立。"""
    for agent_id in A.AGENTS:
        r = _score_agent(agent_id, {})
        assert r["score_ceiling"] == A.NO_DATA_BASE_SCORE, agent_id
        assert r["measured_kpis"] == 0
        assert r["data_coverage_weight"] == 0.0
    r = _score_agent("revenue", {"affiliate_revenue": 100.0})
    kpi = next(k for k in A.AGENTS["revenue"]["kpis"] if k["id"] == "affiliate_revenue")
    expected = round(
        100 * (kpi["weight"] / 100) + A.NO_DATA_BASE_SCORE * (1 - kpi["weight"] / 100), 1)
    assert r["data_coverage_weight"] == round(kpi["weight"] / 100, 3)
    assert r["score_ceiling"] == expected


def test_full_coverage_lifts_ceiling_to_100():
    """所有 KPI 都接上真实数据时，上限回到 100。"""
    agent_id = "revenue"
    all_ids = {k["id"]: 100.0 for k in A.AGENTS[agent_id]["kpis"]}
    r = _score_agent(agent_id, all_ids)
    assert r["measured_kpis"] == r["total_kpis"]
    assert r["data_coverage_weight"] == 1.0
    assert r["score_ceiling"] == 100.0


def test_ceiling_is_never_below_current_score():
    """当前分数不可能超过上限（否则上限算法就错了）。"""
    agent_id = "seo"
    all_ids = {k["id"]: 100.0 for k in A.AGENTS[agent_id]["kpis"]}
    r = _score_agent(agent_id, all_ids)
    assert r["score"] <= r["score_ceiling"], (r["score"], r["score_ceiling"])


def test_ceiling_caps_below_A_grade():
    """现实约束：按权重算，覆盖率不高的 Agent 上限根本到不了 A(≥90)。
    把这个事实写成测试，防止将来有人偷偷把占位分改高、让分数看起来更好。"""
    # 只接权重 25% 的单个 KPI
    r = _score_agent("social", {"social_referral_traffic": 100.0})
    assert r["score_ceiling"] < 90.0, r["score_ceiling"]
