# -*- coding: utf-8 -*-
"""日报语义修复回归测试。

覆盖四类「报表达人但不表达真相」的缺陷：
1. OKR 连续零值：0 篇不再是 🟢，而是按 content/posts 真实日期升级
2. OKR 假绿：目标 = 当前基线 / 当前远超目标时标注，100% 不伪装成达成
3. 建议分流：平均排名在 20 名外时不再建议「改标题」
4. 实验幻影：快照 RUNNING 但登记表 PLANNED / 无 start_date -> NOT_STARTED

背景见 2026-09-19 日报诊断：18 天 0 篇显示 🟢、排名 33.6 被诊断为标题问题、
4 个从未启动的实验显示「在跑」。
"""
import json
from datetime import datetime
from pathlib import Path

import pytest

import okr_utils
import report_advice
import feishu_daily_report as fdr

REPO = Path(__file__).resolve().parent.parent
SNAPSHOT = REPO / "reports" / "feishu_daily" / "daily_2026-09-18.json"


# ---------------------------------------------------------------------------
# 1. OKR 连续零值
# ---------------------------------------------------------------------------

class TestDaysSinceLastPost:
    def test_counts_quoted_dates(self):
        """48/60 篇文章的 date 带引号；早先的正则漏掉它们，把断更算成 18 天。"""
        n = okr_utils._days_since_last_post(datetime(2026, 9, 19))
        assert n is not None
        assert 0 <= n <= 40, f"断更天数异常: {n}"

    def test_reference_date_matters(self):
        # 报告日之前 -> 负数；之后 -> 正数
        early = okr_utils._days_since_last_post(datetime(2026, 9, 1))
        late = okr_utils._days_since_last_post(datetime(2026, 10, 20))
        assert late > early
        assert early < 0

    def test_missing_posts_dir_returns_none(self, monkeypatch, tmp_path):
        monkeypatch.setattr(okr_utils, "BLOG_ROOT", tmp_path)
        assert okr_utils._days_since_last_post() is None


class TestZeroRunEscalation:
    def _row(self, source, name):
        return okr_utils._zero_run_icon(source, name, 0.0, 0, datetime(2026, 9, 19))

    def test_content_new_escalates_when_overdue(self):
        icon, note = self._row("content_new", "日新增文章")
        assert icon in ("🟠", "🔴")
        assert "天未发布" in note

    def test_content_new_within_cadence_stays_green(self, monkeypatch):
        # 强制把「距上次发布」压到节奏内
        monkeypatch.setattr(okr_utils, "_days_since_last_post", lambda *a, **k: 2)
        icon, note = self._row("content_new", "日新增文章")
        assert icon == "🟢"
        assert "节奏内" in note

    def test_content_new_double_overdue_is_red(self, monkeypatch):
        monkeypatch.setattr(okr_utils, "_days_since_last_post", lambda *a, **k: 20)
        icon, note = self._row("content_new", "日新增文章")
        assert icon == "🔴"
        assert "生产中断" in note

    def test_no_false_alarm_for_other_sources(self, monkeypatch):
        # 没有可靠历史源的 KR 不应被臆造升级
        monkeypatch.setattr(okr_utils, "_days_since_last_post", lambda *a, **k: 99)
        icon, note = self._row("ml_new", "邮件订阅")
        assert icon == "🟡"
        assert note is None

    def test_unresolvable_date_keeps_original_icon(self, monkeypatch):
        monkeypatch.setattr(okr_utils, "_days_since_last_post", lambda *a, **k: None)
        icon, note = self._row("content_new", "日新增文章")
        assert icon == "🟢"
        assert note is None


# ---------------------------------------------------------------------------
# 2. OKR 假绿
# ---------------------------------------------------------------------------

def _load_snapshot():
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))


class TestOkrFakeGreen:
    def test_target_equal_to_current_is_flagged(self):
        rows = okr_utils.build_okr_progress(_load_snapshot(), "daily", datetime(2026, 9, 19))
        visit = [r for r in rows if "访问" in r["name"]]
        assert visit, "找不到访问用户 KR"
        r = visit[0]
        if r.get("available") and r["current"] == r["target"]:
            assert r["icon"] == "✅"
            assert "自动成立" in r.get("note", "")

    def test_far_above_target_is_flagged(self):
        rows = okr_utils.build_okr_progress(_load_snapshot(), "daily", datetime(2026, 9, 19))
        gsc = [r for r in rows if "曝光" in r["name"]]
        assert gsc
        r = gsc[0]
        if r.get("available") and r["current"] > r["target"]:
            assert "封顶" in r.get("note", "")

    def test_zero_new_content_is_not_green(self):
        rows = okr_utils.build_okr_progress(_load_snapshot(), "daily", datetime(2026, 9, 19))
        new = [r for r in rows if "新增文章" in r["name"]]
        assert new
        assert new[0]["icon"] != "🟢", "连续多天 0 篇仍标绿，报警信号被隐藏"

    def test_note_is_rendered_into_the_table(self):
        md = okr_utils.build_okr_section(_load_snapshot(), "daily", datetime(2026, 9, 19))
        assert "天未发布" in md or "自动成立" in md


# ---------------------------------------------------------------------------
# 3. 建议排名感知
# ---------------------------------------------------------------------------

def _advice_with(avg_pos):
    d = _load_snapshot()
    # 构造 organic 占比落在 10-30% 区间，命中新分支
    d["top_channels"] = [
        {"channel": "Organic Search", "users": 1, "sessions": 1},
        {"channel": "Organic Social", "users": 3, "sessions": 3},
        {"channel": "Cross-network", "users": 2, "sessions": 2},
        {"channel": "Unassigned", "users": 2, "sessions": 5},
    ]
    d["visitors"] = 7
    d["users"] = 7
    d["gsc_avg_position"] = avg_pos
    return [a for a in report_advice.generate_advice(d, "daily") if "自然搜索" in a["title"]]


class TestRankAwareAdvice:
    def test_high_position_suppresses_title_advice(self):
        (a,) = _advice_with(33.6)
        # 断言旧文案消失，而不是「标题」二字消失（新文案也要提到标题）
        assert "标题第一行加入明确关键词" not in a["detail"]
        assert "排名" in a["detail"]
        assert "33.6" in a["title"]

    def test_good_position_keeps_title_advice(self):
        (a,) = _advice_with(8.0)
        assert "标题第一行" in a["detail"]

    def test_missing_position_falls_back_to_original(self):
        (a,) = _advice_with(None)
        assert "标题第一行" in a["detail"]

    def test_garbage_position_is_ignored(self):
        # 脏值不应误报成排名问题
        d = _load_snapshot()
        d["top_channels"] = [
            {"channel": "Organic Search", "users": 1, "sessions": 1},
            {"channel": "Organic Social", "users": 3, "sessions": 3},
            {"channel": "Unassigned", "users": 3, "sessions": 8},
        ]
        d["visitors"] = 7
        d["users"] = 7
        d["gsc_avg_position"] = "NOT_AVAILABLE"
        hits = [a for a in report_advice.generate_advice(d, "daily") if "自然搜索" in a["title"]]
        for a in hits:
            assert "瓶颈是排名" not in a["detail"]


# ---------------------------------------------------------------------------
# 4. 实验幻影
# ---------------------------------------------------------------------------

class TestExperimentPhantom:
    def test_config_loads_all_experiments(self):
        cfg = fdr.load_experiment_config()
        assert len(cfg) >= 7

    def test_running_in_snapshot_but_planned_in_config_is_not_started(self):
        cfg = fdr.load_experiment_config()
        e = {"experiment_id": "REV001", "status": "RUNNING"}
        assert fdr._effective_running(e, cfg) == "NOT_STARTED"

    def test_waiting_recrawl_is_not_treated_as_phantom(self):
        cfg = fdr.load_experiment_config()
        e = {"experiment_id": "GROWTH07B-TECH-001", "status": "WAITING_RECRAWL"}
        assert fdr._effective_running(e, cfg) == "WAITING_RECRAWL"

    def test_missing_config_falls_back_to_snapshot(self):
        e = {"experiment_id": "REV001", "status": "RUNNING"}
        assert fdr._effective_running(e, {}) == "RUNNING"

    def test_config_says_running_with_start_date_is_real(self):
        cfg = {"REV001": {"status": "RUNNING", "start_date": "2026-08-16"}}
        e = {"experiment_id": "REV001", "status": "RUNNING"}
        assert fdr._effective_running(e, cfg) == "RUNNING"

    def test_missing_config_file_returns_empty(self, monkeypatch, tmp_path):
        monkeypatch.setattr(fdr, "EXPERIMENT_CONFIG_FILE", tmp_path / "nope.json")
        assert fdr.load_experiment_config() == {}


# ---------------------------------------------------------------------------
# 5. CI 完成窗口：周更工作流不该用日更阈值
# ---------------------------------------------------------------------------

class TestCiWindow:
    """weekly-blog-update.yml 的 cron 是 '0 0 * * 1'（周一 00:00 UTC）。

    原实现用 created_at.startswith(report_day) 只认昨日当天，除周一外每天都
    查不到完成记录，日报于是每周 6 天把健康的周更渲染成「状态未知（近 2 天无
    完成记录）」。且文案说「近 2 天」而真实过滤是 1 天——文案与实现都不对。
    """

    def test_zero_records_reports_real_window(self):
        s = fdr._ci_state_str(None, False, True, "x", 0, 8)
        assert "8 天内" in s
        assert "2 天" not in s

    def test_records_exist_but_none_in_window_is_not_a_failure(self):
        # paths_total > 0：workflow 存在、历史有记录，只是窗口内没跑
        s = fdr._ci_state_str(None, False, True, "x", 12, 8)
        assert "周期未到期" in s
        assert "失败" not in s

    def test_default_window_is_2_days(self):
        # 缺省按日更处理，不改变原有日报/社媒工作流的语义
        s = fdr._ci_state_str(None, False, True, "x", 0)
        assert "2 天内" in s

    def test_success_and_failure_are_unaffected_by_window(self):
        assert fdr._ci_state_str(True, False, True, "x", 0, 8) == "成功"
        assert fdr._ci_state_str(False, False, True, "x", 0, 8) == "失败"

    def test_api_failure_still_distinguishable(self):
        s = fdr._ci_state_str(None, False, False, "rate limited", 0, 8)
        assert "rate limited" in s

    def test_token_missing_still_distinguishable(self):
        s = fdr._ci_state_str(None, True, True, "x", 0, 8)
        assert "本地预览" in s
