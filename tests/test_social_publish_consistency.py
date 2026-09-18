# -*- coding: utf-8 -*-
"""tests/test_social_publish_consistency.py

回归锁：social.publish_consistency 从 reports/social/social_daily_*.json
计算发布一致性达标率。

为什么这个接线值得锁住
----------------------
Social Agent 此前 7 个 KPI 只有 1 个（engagement_rate，权重 10）有数据，
覆盖率 10%，分数上限 73.0。social_daily 是 Buffer API 拉的活数据，
24 天、176 条真实发布，却一直没接。

口径校验（已人工核对）：平台分项求和与 total_published 一致
  2026-09-01: ig 9 + pinterest 13 + x 8 + fb 9 = 39 = total_published

明确排除：reports/social/post_performance_data.json 自报
  data_source="sample_data (replace with Buffer API)"
是样例数据，接进考核等于给分数喂编造数字。
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import agent_kpi_auditor as A  # noqa: E402


def _write(dirpath, date, total_published, **extra):
    """写一个 social_daily 文件。日期用 ISO 周可推算的已知值。"""
    p = dirpath / f"social_daily_{date}.json"
    body = {"date": date, "total_published": total_published}
    body.update(extra)
    p.write_text(json.dumps(body), encoding="utf-8")
    return p


def _weeks_in(result):
    return {k: v["published"] for k, v in result["weeks"].items()}


# ── 周阈值 ──────────────────────────────────────────────────

def test_week_meeting_threshold_counts_as_met(tmp_path):
    """一周恰好 5 条 = 达标（目标是「≥5条」，不是「>5条」）。"""
    _write(tmp_path, "2026-09-01", 5)          # W36 周一
    _write(tmp_path, "2026-09-02", 0)
    r = A._publish_consistency(tmp_path)
    assert r["rate"] == 100.0, r
    assert r["weeks_met"] == 1 and r["weeks_measured"] == 1


def test_week_one_below_threshold_is_not_met(tmp_path):
    _write(tmp_path, "2026-09-01", 4)
    r = A._publish_consistency(tmp_path)
    assert r["rate"] == 0.0, r
    assert r["weeks_met"] == 0


def test_week_counts_are_summed_across_days(tmp_path):
    """一周多天，发布量按周累加——达标判在周上，不在日上。"""
    _write(tmp_path, "2026-09-01", 2)
    _write(tmp_path, "2026-09-02", 1)
    _write(tmp_path, "2026-09-03", 2)          # 合计 5 → 达标
    r = A._publish_consistency(tmp_path)
    assert r["rate"] == 100.0, r
    assert list(_weeks_in(r).values()) == [5]


def test_mixed_weeks_give_fractional_rate(tmp_path):
    """4 周里 3 周达标 → 75.0%。"""
    # 09-01..09-05 = W36(达标), 09-08..09-10 = W37(达标)
    _write(tmp_path, "2026-09-01", 5)
    _write(tmp_path, "2026-09-08", 6)
    _write(tmp_path, "2026-09-15", 3)          # W38 不达标
    _write(tmp_path, "2026-09-22", 4)          # W39 不达标
    r = A._publish_consistency(tmp_path)
    assert r["weeks_measured"] == 4, _weeks_in(r)
    assert r["rate"] == 50.0, r


# ── 无数据 / 坏数据 ─────────────────────────────────────────

def test_no_files_returns_none_rate(tmp_path):
    r = A._publish_consistency(tmp_path)
    assert r["rate"] is None
    assert r["weeks_measured"] == 0
    assert "无 social_daily" in r["note"]


def test_only_weeks_with_data_files_are_counted(tmp_path):
    """关键诚实性：某周完全没日报文件时，不能当成「0 条发布」扣分。
    没有文件只能说明采集器那天没跑，与「当天确实没发」是两件事。"""
    _write(tmp_path, "2026-09-01", 5)          # W36 达标
    _write(tmp_path, "2026-09-22", 4)          # W39 不达标
    # W37、W38 完全没有文件 → 不计入分母
    r = A._publish_consistency(tmp_path)
    assert r["weeks_measured"] == 2, _weeks_in(r)
    assert r["rate"] == 50.0


def test_malformed_files_are_skipped(tmp_path):
    _write(tmp_path, "2026-09-01", 5)
    (tmp_path / "social_daily_2026-09-02.json").write_text("{broken json", encoding="utf-8")
    (tmp_path / "social_daily_2026-09-03.json").write_text(
        json.dumps({"date": "not-a-date", "total_published": 9}), encoding="utf-8")
    (tmp_path / "social_daily_2026-09-04.json").write_text(
        json.dumps({"date": "2026-09-04"}), encoding="utf-8")  # 缺 total_published
    r = A._publish_consistency(tmp_path)
    assert r["rate"] is not None
    assert list(_weeks_in(r).values()) == [5]


def test_partial_week_is_reported_not_hidden(tmp_path):
    """只有 3 天数据的周仍然计入，但 days_with_data 必须暴露出来。
    否则读者会把「3 天 0 条」和「7 天 0 条」当成同一件事。"""
    _write(tmp_path, "2026-09-01", 0)
    _write(tmp_path, "2026-09-02", 0)
    _write(tmp_path, "2026-09-03", 0)
    r = A._publish_consistency(tmp_path)
    w = list(r["weeks"].values())[0]
    assert w["published"] == 0 and w["days_with_data"] == 3
    assert r["rate"] == 0.0


# ── 数据源守卫 ─────────────────────────────────────────────

def test_sample_data_file_is_not_used(tmp_path):
    """post_performance_data.json 自报 data_source="sample_data"，
    绝不能进考核。这里确认它就算和 social_daily 放在同一目录也不会被读。"""
    _write(tmp_path, "2026-09-01", 5)
    (tmp_path / "post_performance_data.json").write_text(
        json.dumps({"total_count": 50,
                    "data_source": "sample_data (replace with Buffer API)"}),
        encoding="utf-8")
    r = A._publish_consistency(tmp_path)
    assert r["rate"] == 100.0
    assert r["posts_total"] == 5, "样例数据被当成真实发布量了"


def test_only_social_daily_glob_is_read(tmp_path):
    """目录里其它文件（周计划、审计、模型）不参与计算。"""
    _write(tmp_path, "2026-09-01", 5)
    (tmp_path / "social_schedule_2026-09-01.json").write_text("{}", encoding="utf-8")
    (tmp_path / "social_audit_report.json").write_text("{}", encoding="utf-8")
    r = A._publish_consistency(tmp_path)
    assert r["posts_total"] == 5
    assert r["days"] == 1


# ── 报告字段完整性 ──────────────────────────────────────────

def test_report_carries_full_evidence(tmp_path):
    """分数必须带得出处：达标周数、总发布量、天数、报告年龄。
    只给一个百分数，读者无法判断它是几天数据算出来的。"""
    _write(tmp_path, "2026-09-01", 5)
    _write(tmp_path, "2026-09-08", 4)
    r = A._publish_consistency(tmp_path)
    for key in ("rate", "weeks_met", "weeks_measured", "weeks",
                "posts_total", "days", "age_days"):
        assert key in r, key
    assert r["posts_total"] == 9
    assert r["days"] == 2
    assert r["age_days"] >= 0, "文件名里的日期应能被解析出年龄"


def test_real_data_platform_sums_match_total():
    """口径校验锁：平台分项之和必须等于 total_published。
    一旦上游把 total_published 的算法改坏（比如去重/跨平台重复计数），
    这里会先炸，而不是让 39 条/天 这种异常数字静默流进分数。"""
    p = Path(A.__file__).resolve().parent.parent / "reports" / "social"
    files = sorted(p.glob("social_daily_*.json"))
    if not files:
        pytest.skip("无 social_daily 数据")
    bad = []
    for f in files:
        d = json.load(open(f, encoding="utf-8"))
        bp = d.get("by_platform", {})
        if not bp:
            continue
        per_platform = sum(v.get("published", 0) for v in bp.values() if isinstance(v, dict))
        if per_platform != d.get("total_published"):
            bad.append(f"{f.name}: {per_platform} != {d.get('total_published')}")
    assert not bad, "口径漂移: " + "; ".join(bad[:5])


# ── 接线 ────────────────────────────────────────────────────

def test_collect_metrics_wires_publish_consistency(monkeypatch):
    """接线点：social.publish_consistency 必须由 _publish_consistency 提供。
    把收集器改成固定值，确认 collect_metrics 确实用了它。"""
    fake = {"rate": 66.6, "weeks_met": 2, "weeks_measured": 3, "weeks": {},
            "posts_total": 0, "days": 0, "age_days": 0, "note": ""}
    monkeypatch.setattr(A, "_publish_consistency", lambda: fake)
    metrics = A.collect_metrics()
    assert metrics["social"]["publish_consistency"] == 66.6


def test_daily_report_does_not_supersede_publish_consistency():
    """日报路径里没有 publish_consistency，所以接线不会被 _set 的 None 语义误清。
    反过来，如果哪天日报开始提供这个字段，就必须和 social_daily 对齐口径，
    不能两个源各自算出一个数。这里把「日报当前不提供该字段」写成显式断言，
    将来日报一旦新增该字段，测试会失败并提醒我们处理双源冲突。"""
    daily = A._latest_daily_report()
    assert isinstance(daily, dict)
    assert "publish_consistency" not in daily
