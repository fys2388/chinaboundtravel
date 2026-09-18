"""按 unit 分派的归一化器回归测试。

守护 2026-09-18 三轮修复：
1. 零基准（target=0 非百分比）：value=0 是满分。
   「0 个坏链接」原先被 0<=value<=100 吃掉拿 0 分，语义完全反了。
2. 量纲漂移：affiliate_revenue 是美元金额，旧逻辑 $0→0、$5→5、
   $500→95、$0.50→50（被当成 0.5 的比率 ×100）——$0.50 比 0 营收还高分。
3. 达标度被忽略：engagement_rate=0.05 对「≥3%」是达标（5%>3%），
   旧逻辑直接 return value*100 不看目标，只得 5 分。
4. 方向反转：lcp_performance 目标「≤2.5s」越小越好，旧逻辑按 value/target
   算达标度，实际 3.0s（更差）反而拿 95 分。
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import agent_kpi_auditor as A  # noqa: E402

CUR = {"id": "affiliate_revenue", "target": "环比增长≥10%", "type": "revenue", "unit": "currency"}
LCP = {"id": "lcp_performance", "target": "≤2.5s", "type": "process", "unit": "seconds"}
ENG = {"id": "engagement_rate", "target": "≥3%", "type": "process", "unit": "ratio"}
OPEN = {"id": "email_open_rate", "target": "≥25%", "type": "process", "unit": "pct"}
COMP = {"id": "affiliate_compliance", "target": "100%合规", "type": "quality", "unit": "pct"}
COV = {"id": "kpi_coverage", "target": "100%", "type": "quality", "unit": "pct"}
PUB = {"id": "publish_rate", "target": "≥4篇/周", "type": "process", "unit": "count"}
WORDS = {"id": "avg_word_count", "target": "≥1500字", "type": "process", "unit": "words"}
BROKEN = {"id": "broken_affiliate_links", "target": "0个", "type": "quality"}
LEGACY = {"id": "some_old_kpi", "target": "≥100", "type": "revenue"}  # 无 unit


# ── 量纲漂移（本轮核心）────────────────────────────────────

@pytest.mark.parametrize("amount,score", [(0.0, 0.0), (0.50, 70.0), (5.0, 70.0), (500.0, 70.0)])
def test_currency_does_not_drift_with_magnitude(amount, score):
    """回归：$0.50 曾被当成 50% 得 50 分，比 0 营收还高分。"""
    assert A.normalize_metric_to_score(CUR, amount) == score


def test_subdollar_currency_scores_no_higher_than_zero():
    """$0.50 必须比 0 营收分更高，绝不能低于。"""
    assert A.normalize_metric_to_score(CUR, 0.50) > A.normalize_metric_to_score(CUR, 0.0)


def test_currency_zero_is_hard_zero_not_default():
    """0 营收拿 0 分，不是 70 分的无数据默认值——这是必须暴露的信号。"""
    assert A.normalize_metric_to_score(CUR, 0.0) == 0.0


@pytest.mark.parametrize("kpi", [
    {"id": "ebook_revenue", "target": "环比增长≥15%", "type": "revenue", "unit": "currency"},
    {"id": "content_driven_revenue", "target": "环比增长≥10%", "type": "revenue", "unit": "currency"},
])
def test_all_currency_kpis_share_semantics(kpi):
    assert A.normalize_metric_to_score(kpi, 0.0) == 0.0
    assert A.normalize_metric_to_score(kpi, 12.34) == 70.0


# ── 方向反转 ────────────────────────────────────────────────

@pytest.mark.parametrize("seconds,score", [(1.0, 95.0), (2.0, 95.0), (2.5, 85.0),
                                           (3.0, 70.0), (5.0, 50.0), (10.0, 30.0)])
def test_lower_is_better_seconds_ladder(seconds, score):
    assert A.normalize_metric_to_score(LCP, seconds) == score


def test_lcp_worse_than_target_must_score_lower():
    """回归：3.0s 比 2.5s 目标差，绝不能拿 95 分。"""
    worse = A.normalize_metric_to_score(LCP, 3.0)
    better = A.normalize_metric_to_score(LCP, 2.0)
    assert worse < better
    assert worse < 85.0


# ── 达标度必须被比较 ────────────────────────────────────────

@pytest.mark.parametrize("rate,score", [(0.05, 95.0), (0.03, 85.0), (0.025, 70.0),
                                        (0.015, 50.0), (0.005, 30.0), (0.0, 30.0)])
def test_ratio_compared_against_target(rate, score):
    """回归：0.05 对「≥3%」是达标，旧逻辑不看目标只得 5 分。"""
    assert A.normalize_metric_to_score(ENG, rate) == score


@pytest.mark.parametrize("value,score", [(30.0, 95.0), (25.0, 85.0), (20.0, 70.0), (15.0, 50.0)])
def test_pct_below_ceiling_target_uses_ladder(value, score):
    """目标低于 100% 时（email_open_rate ≥25%）必须按达标程度给分。"""
    assert A.normalize_metric_to_score(OPEN, value) == score


@pytest.mark.parametrize("value,score", [(100.0, 100.0), (90.0, 90.0), (60.9, 60.9), (0.0, 0.0)])
def test_pct_ceiling_target_returns_value(value, score):
    """目标 100% 是天花板指标：100% 必须拿 100 分，不能卡在阶梯的 85。"""
    assert A.normalize_metric_to_score(COMP, value) == score
    assert A.normalize_metric_to_score(COV, value) == score


# ── 计数与字数 ──────────────────────────────────────────────

@pytest.mark.parametrize("value,score", [(8, 95.0), (4, 85.0), (3, 50.0), (2, 50.0), (0, 30.0)])
def test_count_ladder(value, score):
    assert A.normalize_metric_to_score(PUB, value) == score


@pytest.mark.parametrize("value,score", [(1904, 95.0), (1500, 85.0), (1300, 70.0), (900, 50.0)])
def test_words_ladder(value, score):
    assert A.normalize_metric_to_score(WORDS, value) == score


# ── 零基准仍然最先判定 ──────────────────────────────────────

@pytest.mark.parametrize("value,score", [(0, 100.0), (3, 30.0), (1, 30.0)])
def test_zero_baseline_still_first(value, score):
    """零基准分支必须在 unit 分派之前：0 个坏链接是满分。"""
    assert A.normalize_metric_to_score(BROKEN, value) == score


# ── 无 unit 的 KPI 保持旧评分 ───────────────────────────────

def test_untagged_kpi_uses_legacy_behavior():
    """没声明 unit 的 KPI 评分与改造前逐分一致，避免大面积跳变。"""
    # type=revenue 且 0<=v<=100 → 原值
    assert A.normalize_metric_to_score(LEGACY, 60.0) == 60.0
    # 0<v<=1 → ×100（旧逻辑不看目标，这是它的历史行为）
    assert A.normalize_metric_to_score({"id": "x", "target": "≥3%", "type": "process"}, 0.05) == 5.0
    # 无可解析目标值 + 大数值 → 75
    assert A.normalize_metric_to_score(
        {"id": "x", "target": "持续提升", "type": "process"}, 2500) == 75.0


def test_none_and_nonnumeric_still_default():
    for kpi in (CUR, LCP, ENG, OPEN):
        assert A.normalize_metric_to_score(kpi, None) == 70.0
        assert A.normalize_metric_to_score(kpi, "n/a") == 70.0
        assert A.normalize_metric_to_score(kpi, []) == 70.0


# ── 所有 KPI 定义自洽 ──────────────────────────────────────

VALID_UNITS = {"currency", "ratio", "seconds", "pct", "count", "words"}


def test_every_declared_unit_is_known():
    """防止拼写错误悄悄退回 legacy 分支。"""
    seen = {}
    for agent in A.AGENTS.values():
        for kpi in agent["kpis"]:
            if "unit" in kpi:
                assert kpi["unit"] in VALID_UNITS, kpi
                assert kpi["id"] not in seen, kpi["id"]
                seen[kpi["id"]] = kpi


CURRENCY_IDS = {
    "affiliate_revenue", "ebook_revenue", "content_driven_revenue",
    "seo_driven_revenue", "social_driven_revenue", "email_driven_revenue",
}


def _kpi_by_id():
    out = {}
    for agent in A.AGENTS.values():
        for kpi in agent["kpis"]:
            out[kpi["id"]] = kpi
    return out


def test_all_monetary_revenue_kpis_declare_currency():
    """金额类营收 KPI 必须显式声明 currency，否则又会按数值范围猜。"""
    by_id = _kpi_by_id()
    assert set(by_id) >= CURRENCY_IDS
    for kid in CURRENCY_IDS:
        assert by_id[kid]["unit"] == "currency", kid
    # 反向：声明 currency 的必须确实是金额类，防止误标
    for kpi in by_id.values():
        if kpi.get("unit") == "currency":
            assert kpi["id"] in CURRENCY_IDS, kpi["id"]


def test_lower_is_better_targets_declare_seconds():
    """目标写成「≤Ns」的 KPI 必须声明 seconds，否则越大越好的默认逻辑会反着打。"""
    import re as _re
    for kpi in _kpi_by_id().values():
        if _re.match(r"^≤\d+(?:\.\d+)?s", kpi["target"]):
            assert kpi.get("unit") == "seconds", kpi
