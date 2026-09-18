"""GSC 查询窗口口径的回归测试。

守护 2026-09-18 的修复：_fetch_gsc 原先用 (yesterday, yesterday) 单日查询，
而 GSC dataState=final 的数据有 2-3 天定稿延迟，单日窗口几乎恒返回空行。
结果日报每天报「0 曝光 0 点击」，把真实的 1883 曝光/28天 抹成了零——
自动化系统因此误判「站点在自然搜索里完全没有存在感」。
"""
from datetime import datetime, timedelta

import pytest

sys_path_hack = True  # noqa: F841  (保留标记：下方手动插 sys.path)
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import feishu_daily_report as F  # noqa: E402


NOW = datetime(2026, 9, 18, 8, 30, 0)


def test_window_is_not_single_day():
    """回归核心：主窗口跨度必须大于 1 天。单日窗口在 GSC 上恒空。"""
    w = F.gsc_windows(NOW)
    start = datetime.strptime(w["window_start"], "%Y-%m-%d")
    end = datetime.strptime(w["window_end"], "%Y-%m-%d")
    span = (end - start).days
    assert span > 1, f"主窗口跨度只有 {span} 天——这是 GSC 恒空 bug 的直接成因"


def test_window_ends_after_finalization_delay():
    """主窗口必须止于 D-3 或更早，否则读到未定稿数据（恒空）。"""
    w = F.gsc_windows(NOW)
    end = datetime.strptime(w["window_end"], "%Y-%m-%d")
    earliest_ok = (NOW - timedelta(days=3)).date()
    assert end.date() <= earliest_ok, (
        f"窗口止于 {end.date()}，晚于 D-3（{earliest_ok}）——GSC final 数据尚未定稿"
    )


def test_windows_are_contiguous_and_non_overlapping():
    """三个窗口必须同维度、互不重叠、时间上有先后。"""
    w = F.gsc_windows(NOW)
    spans = {}
    pairs = {
        "window": (w["window_start"], w["window_end"]),
        "prev7": (w["prev7_start"], w["prev7_end"]),
        "prev4w": (w["prev4w_start"], w["prev4w_end"]),
    }
    for name, (s, e) in pairs.items():
        sd, ed = datetime.strptime(s, "%Y-%m-%d"), datetime.strptime(e, "%Y-%m-%d")
        assert sd < ed, f"{name} 窗口起止倒置"
        spans[name] = (ed - sd).days
    # 同维度：三个窗口都必须是 7 天，否则环比在拿不同长度比较
    assert spans["window"] == spans["prev7"] == spans["prev4w"] == 6, (
        f"窗口跨度不一致 {spans}——环比失去可比性（应为 6 天差 = 7 天含端点）"
    )
    # 严格先后，无重叠
    assert datetime.strptime(pairs["prev7"][1], "%Y-%m-%d") < datetime.strptime(pairs["window"][0], "%Y-%m-%d"), \
        "prev7 与当前窗口重叠"
    assert datetime.strptime(pairs["prev4w"][1], "%Y-%m-%d") < datetime.strptime(pairs["prev7"][0], "%Y-%m-%d"), \
        "prev4w 与 prev7 重叠"


def test_prev7_end_butts_against_window_start():
    """prev7 的结束日与当前窗口开始日之间不允许有缺口——
    否则「周环比」比较的是不相邻的两段，数字无意义。"""
    w = F.gsc_windows(NOW)
    gap = (datetime.strptime(w["window_start"], "%Y-%m-%d")
           - datetime.strptime(w["prev7_end"], "%Y-%m-%d")).days
    assert gap == 1, f"prev7 与当前窗口之间有 {gap - 1} 天缺口"


def test_current_and_prev7_cover_14_consecutive_days():
    """当前 7 天 + 前 7 天应该拼成一段 14 天的连续区间。"""
    w = F.gsc_windows(NOW)
    start = datetime.strptime(w["prev7_start"], "%Y-%m-%d")
    end = datetime.strptime(w["window_end"], "%Y-%m-%d")
    total = (end - start).days
    assert total == 13, (
        f"prev7+window 跨度 {total} 天，应为 13 天（14 天区间）。"
        "如果这里断了，周环比就是在拿不相邻的两段比较"
    )


def test_windows_are_deterministic_for_given_now():
    """同一 now 必须给出同一组窗口（幂等，可被快照测试依赖）。"""
    assert F.gsc_windows(NOW) == F.gsc_windows(NOW)


def test_window_fields_are_iso_dates():
    """所有字段必须是 YYYY-MM-DD，GSC API 要求该格式。"""
    w = F.gsc_windows(NOW)
    for key, value in w.items():
        parsed = datetime.strptime(value, "%Y-%m-%d")
        assert parsed.strftime("%Y-%m-%d") == value, f"{key} 不是规范 ISO 日期: {value}"


def test_all_windows_within_recent_history():
    """所有窗口必须落在最近 40 天内，避免读到远古数据。"""
    w = F.gsc_windows(NOW)
    for value in w.values():
        d = datetime.strptime(value, "%Y-%m-%d")
        assert NOW - timedelta(days=40) <= d <= NOW, (
            f"{value} 超出合理范围（{NOW - timedelta(days=40).date()} ~ {NOW.date()}）"
        )


@pytest.mark.parametrize("days_back,field", [
    (3, "window_end"),
    (9, "window_start"),
    (10, "prev7_end"),
    (16, "prev7_start"),
    (28, "prev4w_end"),
    (34, "prev4w_start"),
])
def test_window_boundaries_match_documented_offsets(days_back, field):
    """每个窗口端点必须精确等于文档声明的 D-N 偏移。"""
    w = F.gsc_windows(NOW)
    expected = (NOW - timedelta(days=days_back)).strftime("%Y-%m-%d")
    assert w[field] == expected, (
        f"{field} = {w[field]}，应为 D-{days_back} = {expected}。"
        "窗口偏移被改动了但没有同步更新测试"
    )
