# -*- coding: utf-8 -*-
"""tests/test_email_list_growth_audit.py

锁 user.email_list_growth 的口径：必须用总量快照算增长率，
不能拿每日新增绝对数冒充增长率。

为什么值得锁
------------
email_list_growth 目标「环比增长≥10%」是**增长率**，但 2026-09-18 之前
接线是：

    _set("user", "email_list_growth", daily.get("ml_new_subscribers"))

`ml_new_subscribers` 是**每日新增绝对数**。把绝对数喂进增长率目标：

    当日 0 个新增   -> _ratio_ladder(0, 10)  = 30 分（看起来很差，
                              但我们测的根本不是增长）
    当日 20 个新增  -> _ratio_ladder(20, 10) = 2.0 -> 95 分
                              （「一天新增 20 人」被当成「达到目标的 2 倍」）

原注释写「0 个新增订阅 → 0 分，这是真实测量而非缺数据」，
但代码给 30 分，且没有任何路径通向 0 分——注释描述了一个
代码没实现的意图。

仓库自己的原则是「绝对计数不接增长型目标」，
content.top10_keywords 就是因为这条被故意留成 no_data 的。
email_list_growth 是这条原则的漏网之鱼。

修法：新增 _email_list_growth()，用 ml_total_subscribers 快照序列
算 (最新 - 最早) / 最早 × 100。当前 3 份快照 total 恒为 3 -> 0% -> 30 分，
**分数与修复前一致**，但口径从「绝对数冒充增长率」变成真增长率。
"""
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import agent_kpi_auditor as K   # noqa: E402


def _seed(tmp_path, snapshots, extra_fields=None):
    """snapshots: [(date_str, total_subscribers), ...]"""
    daily_dir = tmp_path / "reports" / "feishu_daily"
    daily_dir.mkdir(parents=True, exist_ok=True)
    for d, total in snapshots:
        body = {"ml_total_subscribers": total, "ml_new_subscribers": 0,
                "ml_available": True}
        if extra_fields:
            body.update(extra_fields)
        (daily_dir / f"daily_{d}.json").write_text(
            json.dumps(body, ensure_ascii=False), encoding="utf-8")
    return daily_dir


# ── 增长率计算 ──────────────────────────────────────────────

def test_growth_from_total_snapshots(tmp_path):
    d = _seed(tmp_path, [("2026-08-01", 10), ("2026-08-15", 10),
                         ("2026-09-01", 12)])
    r = K._email_list_growth(d)
    assert r["growth"] == 20.0, "10 → 12 应为 +20%"
    assert r["first_total"] == 10
    assert r["last_total"] == 12
    assert r["snapshots"] == 3
    assert r["window_days"] == 31


def test_flat_list_is_zero_growth(tmp_path):
    """当前线上真实情况：3 份快照 total 恒为 3。
    增长率 0% 与「环比增长≥10%」对比走 ladder 得 30 分——
    与修复前的分数完全一致，但口径从绝对数变成真增长率。"""
    d = _seed(tmp_path, [("2026-09-16", 3), ("2026-09-17", 3),
                         ("2026-09-18", 3)])
    r = K._email_list_growth(d)
    assert r["growth"] == 0.0
    assert r["window_days"] == 2
    assert r["snapshots"] == 3


def test_shrinking_list_is_negative_growth(tmp_path):
    d = _seed(tmp_path, [("2026-08-01", 20), ("2026-09-01", 10)])
    r = K._email_list_growth(d)
    assert r["growth"] == -50.0


def test_uses_first_and_last_not_adjacent(tmp_path):
    """必须是首尾两点，不是最后两份相邻快照。
    否则中间那段增长会被整段历史掩盖。"""
    d = _seed(tmp_path, [("2026-07-01", 10), ("2026-08-01", 30),
                         ("2026-09-01", 20)])
    r = K._email_list_growth(d)
    assert r["growth"] == 100.0, "10 -> 20 应为 +100%，不是 30 -> 20 的 -33%"
    assert r["window_days"] == 62


# ── 边界：不给出假分数 ──────────────────────────────────────

def test_zero_base_is_not_measured(tmp_path):
    """起始总量 0 时百分比无定义。
    强行给 0 会冒充「零增长」，给 100 会冒充「满分」——都不对。"""
    d = _seed(tmp_path, [("2026-08-01", 0), ("2026-09-01", 15)])
    r = K._email_list_growth(d)
    assert r["growth"] is None
    assert "起始总量为 0" in r["note"]
    assert r["last_total"] == 15, "总量本身仍是已知事实，不能一起丢掉"


def test_single_snapshot_is_not_measured(tmp_path):
    d = _seed(tmp_path, [("2026-09-18", 3)])
    r = K._email_list_growth(d)
    assert r["growth"] is None
    assert "只有 1 份" in r["note"]
    assert r["last_total"] == 3


def test_no_files_is_not_measured(tmp_path):
    r = K._email_list_growth(tmp_path / "reports" / "feishu_daily")
    assert r["growth"] is None
    assert "无日报数据" in r["note"]


def test_missing_field_skipped_not_fatal(tmp_path):
    """缺 ml_total_subscribers 的快照要跳过，不能崩，也不能当 0 算进去。"""
    d = _seed(tmp_path, [("2026-09-18", 3)])
    # 再加一份缺字段的
    body = {"ml_new_subscribers": 0}
    (d / "daily_2026-09-17.json").write_text(
        json.dumps(body), encoding="utf-8")
    r = K._email_list_growth(d)
    assert r["growth"] is None, "跳过缺字段后只剩 1 份快照，算不出增长"
    assert r["snapshots"] == 1


def test_malformed_filename_skipped(tmp_path):
    d = _seed(tmp_path, [("2026-09-18", 3)])
    (d / "daily_nodate.json").write_text(
        json.dumps({"ml_total_subscribers": 99}), encoding="utf-8")
    r = K._email_list_growth(d)
    assert r["snapshots"] == 1, "无日期文件名必须跳过，否则会算错 window_days"


def test_unreadable_file_skipped(tmp_path):
    d = _seed(tmp_path, [("2026-09-18", 3)])
    (d / "daily_2026-09-17.json").write_text("{broken json", encoding="utf-8")
    r = K._email_list_growth(d)
    assert r["snapshots"] == 1


def test_non_numeric_total_skipped(tmp_path):
    d = _seed(tmp_path, [("2026-09-18", 3)])
    (d / "daily_2026-09-17.json").write_text(
        json.dumps({"ml_total_subscribers": "unknown"}), encoding="utf-8")
    r = K._email_list_growth(d)
    assert r["snapshots"] == 1


# ── 分数口径 ────────────────────────────────────────────────

def test_absolute_count_no_longer_drives_the_score():
    """本轮修的根因：ml_new_subscribers 不能再驱动这个 KPI 的分数。

    断言的是可执行代码，不是全文——注释里故意引了旧字段名
    来说明修的是什么，全文匹配会命中它自己（Round 14/17/18 修过的
    同类假阳性）。
    """
    import inspect
    code = inspect.getsource(K.collect_metrics)
    body = code.split('"""', 2)[2] if code.count('"""') >= 2 else code
    stripped = "\n".join(l.split("#", 1)[0] for l in body.splitlines())
    assert "ml_new_subscribers" not in stripped, (
        "collect_metrics 里仍有可执行代码引用每日新增绝对数")
    assert "_email_list_growth()" in stripped


def test_same_daily_count_different_bases_score_differently(tmp_path):
    """旧口径的致命问题：分数是每日新增数的**常数函数**，基数完全不可见。

    两个场景的当日新增都是 20 人：
      A: 3   → 23   （+666.67%，基数极小，20 人就是天翻地覆）
      B: 500 → 520  （+4.00%，基数很大，20 人远达不到 10% 目标）

    旧口径：两者都是 _ratio_ladder(20, 10) = 2.0 -> 95 分，一模一样。
    新口径：A 拿 95（真实大幅超目标），B 拿 30（真实未达标）。
    """
    small = _seed(tmp_path / "small",
                  [("2026-09-17", 3), ("2026-09-18", 23)],
                  extra_fields={"ml_new_subscribers": 20})
    large = _seed(tmp_path / "large",
                  [("2026-09-17", 500), ("2026-09-18", 520)],
                  extra_fields={"ml_new_subscribers": 20})

    kpi = {"id": "email_list_growth", "target": "环比增长≥10%",
           "type": "process", "unit": "pct"}

    a = K._email_list_growth(small)
    b = K._email_list_growth(large)
    assert a["growth"] == pytest.approx(666.67)
    assert b["growth"] == pytest.approx(4.0)

    score_a = K.normalize_metric_to_score(kpi, a["growth"])
    score_b = K.normalize_metric_to_score(kpi, b["growth"])
    assert score_a == 95.0
    assert score_b == 30.0, "500 -> 520 只有 4% 增长，达不到 10% 目标"

    # 记录旧口径的行为，证明两者确实被压成同一个分数
    old_a = K.normalize_metric_to_score(kpi, 20)   # ml_new_subscribers=20
    old_b = K.normalize_metric_to_score(kpi, 20)
    assert old_a == old_b == 95.0, "旧口径下基数无关，两场景同分"


def test_email_list_growth_declares_pct_unit():
    src = (Path(__file__).resolve().parent.parent / "scripts"
           / "agent_kpi_auditor.py").read_text(encoding="utf-8")
    m = re.search(r'\{"id": "email_list_growth"[^}]*\}', src)
    assert m, "找不到 email_list_growth 定义"
    assert '"unit": "pct"' in m.group(0), "增长率必须声明 unit=pct"


def test_negative_growth_scores_zero(tmp_path):
    """列表缩水是明确退步。环比型目标下负值应为 0 分——
    这条规则在 normalize_metric_to_score 里，不能因为改成 pct 单位而失效。"""
    d = _seed(tmp_path, [("2026-08-01", 20), ("2026-09-01", 10)])
    r = K._email_list_growth(d)
    assert r["growth"] == -50.0
    score = K.normalize_metric_to_score(
        {"id": "email_list_growth", "target": "环比增长≥10%",
         "type": "process", "unit": "pct"}, r["growth"])
    assert score == 0.0


def test_flat_list_still_scores_30(tmp_path):
    """当前线上真实情形：3 -> 3，0% 增长，30 分。
    锁住这条是为了证明本次修复**没有改分数**，只改了口径。"""
    d = _seed(tmp_path, [("2026-09-16", 3), ("2026-09-17", 3),
                         ("2026-09-18", 3)])
    r = K._email_list_growth(d)
    score = K.normalize_metric_to_score(
        {"id": "email_list_growth", "target": "环比增长≥10%",
         "type": "process", "unit": "pct"}, r["growth"])
    assert score == 30.0


# ── 其余环比 KPI 补 unit=pct 不产生回归 ─────────────────────

GROWTH_KPIS = ["top10_keywords", "avg_position", "follower_growth",
               "lead_magnet_download", "email_list_growth"]


def test_all_growth_rate_kpis_declare_pct_unit():
    src = (Path(__file__).resolve().parent.parent / "scripts"
           / "agent_kpi_auditor.py").read_text(encoding="utf-8")
    missing = []
    for kid in GROWTH_KPIS:
        m = re.search(r'\{"id": "%s"[^}]*\}' % kid, src)
        if not m or '"unit": "pct"' not in m.group(0):
            missing.append(kid)
    assert not missing, f"这些环比增长型 KPI 仍未声明 unit=pct：{missing}"


@pytest.mark.parametrize("value", [39.24, 0.0, -12.0, 5.0, 100.0])
def test_avg_position_score_unchanged_by_unit_declaration(value):
    """avg_position 已接线（当前 39.24%）。补 unit=pct 后
    分数必须逐分一致——目标 5% <= 83.33%，两侧都走 ladder。"""
    base = {"id": "avg_position", "target": "环比提升≥5%", "type": "process"}
    with_unit = dict(base, unit="pct")
    assert K.normalize_metric_to_score(base, value) == \
        K.normalize_metric_to_score(with_unit, value), f"value={value} 分数漂移"


def test_short_window_warning_is_printed(tmp_path):
    """目标写的是「环比（月）」，窗口只有 2 天时分数必须带上这个限定。"""
    src = (Path(__file__).resolve().parent.parent / "scripts"
           / "agent_kpi_auditor.py").read_text(encoding="utf-8")
    assert "比月环比短" in src
    assert "25" in src, "窗口阈值应在代码里显式写出"
