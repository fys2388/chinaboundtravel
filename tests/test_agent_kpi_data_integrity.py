"""Agent KPI 考核的数据完整性回归测试。

守护 2026-09-18 修复的四个问题：
1. 硬编码字面量（avg_word_count=1808 / publish_rate=4.0）曾被标成 measured
   参与评分 —— 现在必须不存在。
2. load_real_revenue_data() 曾完全失效（import 不存在的类 + 判断不存在的
   status 键）且从未被调用 —— 现在必须是可调用函数并返回同构结构。
3. kpi_coverage 曾从未计算 —— 现在必须等于独立算出的实测占比。
4. 小样本比率（tp_clicks < 20）不得产出「精确」转化率。
"""
import json
import shutil
from pathlib import Path

import pytest

import agent_kpi_auditor as A


REAL_PROJECT_ROOT = A.PROJECT_ROOT
DAILY_DIR = REAL_PROJECT_ROOT / "reports" / "feishu_daily"


def _daily_files():
    return sorted(DAILY_DIR.glob("daily_*.json"))


def test_no_hardcoded_literal_metrics():
    """硬编码常量不得伪装成实测值进入评分。"""
    metrics = A.collect_metrics()
    content = metrics.get("content", {})
    assert "avg_word_count" not in content, (
        "avg_word_count 不得是硬编码常量：它曾是固定值 1808，"
        "却被标为 status=measured 参与评分"
    )
    assert "publish_rate" not in content, (
        "publish_rate 不得是硬编码常量：它曾是固定值 4.0"
    )
    # 反证：这两个 id 确实存在于 KPI 定义里，所以「不存在」是主动留空，
    # 不是 id 拼错导致静默漏掉。
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
