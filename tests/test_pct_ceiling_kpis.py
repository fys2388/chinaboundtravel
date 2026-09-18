# -*- coding: utf-8 -*-
"""tests/test_pct_ceiling_kpis.py

锁「百分比 KPI 被达标阶梯卡在 85 分」的修复。

为什么值得锁
------------
_ratio_ladder 的 95 分档要求 实际值/目标值 >= 1.2。
对天然上限 100% 的百分比指标，这只有在 1.2 × 目标 <= 100
（即目标 <= 83.33%）时才可能达到。

于是目标 >=95%/>=98%/>=99%/100% 的指标，做到满分也只能拿 85 分。
2026-09-18 实测有 3 个已接线 KPI 全部恰好卡在 85.0：

    内链健康度(无死链)   100% vs 100%  -> 阶梯 ratio 1.0 -> 85
    API健康率(3端点)     100% vs >=99% -> 阶梯 ratio 1.01 -> 85
    报告准时率           100% vs 100%  -> 阶梯 ratio 1.0 -> 85

三个不同数据源、同一个分数——不是巧合，是天花板。
和 A++ 上限不可达是同一类「数学上够不着」的缺陷，
但发生在单个 KPI 内部而不是整个 Agent 上。

修法
----
1. `unit == "pct"` 分支的天花板判定从 `target_val >= 100`
   放宽到 `target_val > 100.0 / 1.2`（≈83.33%）——
   阈值从 _ratio_ladder 的定义推出来，不是拍的。
2. 给 8 个 process 类型的百分比 KPI 补上 `unit: "pct"`。
   它们原先没声明 unit，落进 _legacy_normalize，
   那里对 process 类型没有「百分比直接取原值」的分支。

注意：quality / revenue 类型的百分比 KPI 早就被
_legacy_normalize 的 `type in ("revenue","quality")` 早退正确处理，
所以这次只影响 process 类型。
"""
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import agent_kpi_auditor as A   # noqa: E402


def _kpi(kpi_id, target, ktype="process", unit="pct"):
    return {"id": kpi_id, "name": kpi_id, "weight": 10,
            "target": target, "type": ktype, "unit": unit}


# ── 核心：高目标百分比 KPI 不再被卡在 85 ─────────────────────

@pytest.mark.parametrize("target,value,score", [
    ("100%", 100.0, 100.0),
    ("100%", 90.0, 90.0),
    ("100%", 0.0, 0.0),
    ("≥99%", 100.0, 100.0),   # 原先 85.0
    ("≥99%", 99.0, 99.0),
    ("≥99%", 60.0, 60.0),
    ("≥98%", 98.0, 98.0),
    ("≥98%", 100.0, 100.0),
    ("≥95%", 100.0, 100.0),
    ("≥95%", 95.0, 95.0),
    ("≥90%达标率", 80.0, 80.0),  # 原先阶梯给 70.0
    ("≥90%达标率", 100.0, 100.0),
])
def test_high_target_pct_returns_value_not_ladder(target, value, score):
    """目标 > 83.33% 时 95 分档数学上不可达，必须直接取原值。"""
    assert A.normalize_metric_to_score(_kpi("x", target), value) == score


def test_99_percent_target_must_not_cap_at_85():
    """这是本次修复的主回归：API健康率目标 ≥99%，做到 100% 必须拿 100 分。"""
    kpi = _kpi("api_health_rate", "≥99%")
    assert A.normalize_metric_to_score(kpi, 100.0) == 100.0
    assert A.normalize_metric_to_score(kpi, 100.0) != 85.0


def test_three_capped_kpis_all_recover():
    """三个实测卡在 85 的 KPI，各自用真实目标与真实取值。"""
    cases = [
        (_kpi("internal_link_health", "100%"), 100.0),
        (_kpi("api_health_rate", "≥99%"), 100.0),
        (_kpi("report_timeliness", "100%"), 100.0),
    ]
    for kpi, value in cases:
        got = A.normalize_metric_to_score(kpi, value)
        assert got > 85.0, (
            f"{kpi['id']} 仍被卡在 {got}——目标 {kpi['target']} "
            f"下 95 分档需要 {1.2 * float(re.search(r'([\\d.]+)', kpi['target']).group(1))}%，"
            f"百分比不可能超过 100%")


# ── 边界：83.33% 这条线 ──────────────────────────────────────

def test_threshold_derived_from_ladder_not_hardcoded():
    """阈值必须是 100/1.2，改了阶梯就要跟着改。

    算术：95 分档要求 value/target >= 1.2。
    96/80 = 1.20 → 95；80/80 = 1.00 → 85。
    """
    assert A._ratio_ladder(96.0, 80.0) == 95.0, "1.2x 应为 95 分"
    assert A._ratio_ladder(80.0, 80.0) == 85.0, "1.0x 应为 85 分"
    # 1.2 × 83 = 99.6% < 100%：95 分档仍可达，走阶梯
    #   value 83 / target 83 = 1.00 → 85
    assert A.normalize_metric_to_score(_kpi("x", "≥83%"), 83.0) == 85.0
    # 1.2 × 84 = 100.8% > 100%：95 分档不可达，直接取原值
    assert A.normalize_metric_to_score(_kpi("x", "≥84%"), 100.0) == 100.0


@pytest.mark.parametrize("target,value,score,why", [
    ("≥83%", 83.0, 85.0, "ratio 1.0 → 阶梯的 85 档"),
    ("≥83%", 99.6, 95.0, "1.2×83=99.6 ≤ 100，95 档仍可达"),
    ("≥84%", 100.0, 100.0, "1.2×84=100.8 > 100，改走直取"),
    ("≥84%", 60.0, 60.0, "直取后低值也照实反映"),
])
def test_boundary_around_83_33(target, value, score, why):
    """83.33% 这条线两侧行为必须不同——这正是阈值的意义。"""
    got = A.normalize_metric_to_score(_kpi("x", target), value)
    assert got == score, f"{why}（{target} @ {value}）"


# ── 留有余量的目标仍走阶梯（不能被这次修改误伤）────────────────

@pytest.mark.parametrize("target,value,score", [
    ("≥25%", 30.0, 95.0),   # 1.2x = 30% 恰好达标
    ("≥25%", 25.0, 85.0),
    ("≥25%", 20.0, 70.0),
    ("≥25%", 15.0, 50.0),
    ("≥3%", 3.6, 95.0),
    ("≥3%", 3.0, 85.0),
    ("≥1.5%", 2.0, 95.0),
    ("≥60%", 72.0, 95.0),   # 60 × 1.2 = 72 仍可达
    ("≥60%", 60.0, 85.0),
])
def test_low_target_pct_still_uses_ladder(target, value, score):
    """目标 <= 83.33% 时 1.2x 可达，仍必须按达标程度给分。
    这次修改只应影响高目标 KPI，不能把有增长空间的指标变成直取值。"""
    assert A.normalize_metric_to_score(_kpi("x", target), value) == score


def test_low_target_pct_value_is_not_just_returned():
    """≥25% 目标下 30% 应该拿 95（阶梯），不是拿 30（直取）。"""
    assert A.normalize_metric_to_score(_kpi("x", "≥25%"), 30.0) == 95.0


# ── 其他 type 的百分比 KPI 不受影响 ──────────────────────────

def test_quality_pct_early_returns_still_work():
    """quality 类型在 _legacy_normalize 里早退，本来就正确，不能被改动。"""
    assert A.normalize_metric_to_score(
        {"id": "a", "target": "100%", "type": "quality"}, 60.9) == 60.9
    assert A.normalize_metric_to_score(
        {"id": "a", "target": "100%", "type": "quality"}, 100.0) == 100.0


def test_revenue_pct_early_returns_still_work():
    assert A.normalize_metric_to_score(
        {"id": "a", "target": "≥99.9%", "type": "revenue"}, 99.9) == 99.9


def test_undeclared_unit_high_pct_target_uses_legacy_path():
    """没声明 unit 的高目标 KPI 仍走 _legacy_normalize（旧行为保留）。
    这条不是本次要修的对象——本次是给它们补 unit。"""
    kpi = {"id": "x", "target": "100%", "type": "process"}  # 无 unit
    assert A.normalize_metric_to_score(kpi, 100.0) == 85.0


# ── 源级：8 个 process 百分比 KPI 必须声明 unit=pct ──────────

REQUIRED_UNIT_PCT = [
    "index_coverage", "internal_link_health", "publish_consistency",
    "deploy_success_rate", "api_health_rate", "report_timeliness",
    "data_accuracy", "dashboard_uptime",
]


def _load_kpis():
    src = (Path(__file__).resolve().parent.parent
           / "scripts" / "agent_kpi_auditor.py").read_text(encoding="utf-8")
    pat = re.compile(
        r'\{"id": "(\w+)", "name": "([^"]+)", "weight": (\d+), '
        r'"target": "([^"]+)"(?:, "type": "(\w+)")?'
        r'(?:, "unit": "(\w+)")?(?:, "source": "[^"]*")?\}'
    )
    return {m.group(1): dict(id=m.group(1), target=m.group(4),
                             type=m.group(5) or "?",
                             unit=m.group(6) or None)
            for m in pat.finditer(src)}


def test_the_eight_capped_kpis_declare_unit_pct():
    kpis = _load_kpis()
    missing = [k for k in REQUIRED_UNIT_PCT if kpis.get(k, {}).get("unit") != "pct"]
    assert not missing, f"这些 KPI 仍未声明 unit=pct：{missing}"


def test_every_process_high_pct_target_declares_unit():
    """系统性回归锁：不允许再出现「process + 目标 > 83.33% + 无 unit」。
    否则那个 KPI 会再次被卡在 85 分而没有任何测试能发现。"""
    kpis = _load_kpis()
    bad = []
    for k, v in kpis.items():
        if v["type"] != "process":
            continue
        m = re.search(r"(\d+(?:\.\d+)?)%", v["target"])
        if not m:
            continue
        target = float(m.group(1))
        if target > 100.0 / 1.2 and v["unit"] != "pct":
            bad.append(f"{k}(target={v['target']},unit={v['unit']})")
    assert not bad, "仍有 process 类型高目标百分比 KPI 未声明 unit=pct：\n  " + "\n  ".join(bad)


def test_declared_units_are_all_known():
    """补 unit 时不能写出归一化器不认识的量纲。"""
    valid = {"currency", "ratio", "seconds", "pct", "count", "words"}
    kpis = _load_kpis()
    unknown = {k: v["unit"] for k, v in kpis.items()
               if v["unit"] and v["unit"] not in valid}
    assert not unknown, f"未知 unit：{unknown}"


def test_normalizer_dispatches_pct_unit():
    """unit=pct 必须真的进入归一化器，而不是声明了没人读。"""
    import inspect
    code = inspect.getsource(A.normalize_metric_to_score)
    assert 'unit == "pct"' in code
    assert "100.0 / 1.2" in code, "阈值必须从阶梯定义推出"
