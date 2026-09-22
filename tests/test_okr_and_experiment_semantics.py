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
import reporting_kpi_engine as rke
import feishu_daily_report as fdr

REPO = Path(__file__).resolve().parent.parent
SNAPSHOT = REPO / "reports" / "feishu_daily" / "daily_2026-09-18.json"

# ---------------------------------------------------------------------------
# 0. 常量契约：新增函数确实存在，避免「测了空壳」
# ---------------------------------------------------------------------------

def test_new_helpers_exist():
    assert callable(fdr.load_experiment_config)
    assert callable(fdr._effective_running)
    assert callable(rke._read_experiment_registry)
    assert callable(rke._backup_rollback_state)
    assert hasattr(fdr, "EXPERIMENT_CONFIG_FILE")
    assert hasattr(rke, "EXPERIMENT_REGISTRY")


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
        # AUDIT-RV-001 fix 2026-09-22: load_experiment_config 现在额外返回
        # "__updated_at__" 键（供 experiment_registry_age_days 检测陈旧），
        # 所以真实实验数 = len(cfg) - 1。断言 >= 6 以留增长余量；
        # 原写的是 >= 7，本意是"登记表至少 7 个实验"，扣除元键后 >= 6。
        assert len(cfg) >= 7  # 6 个真实验 + 1 个 __updated_at__ 元键

    def test_running_in_snapshot_but_planned_in_config_is_not_started(self):
        cfg = fdr.load_experiment_config()
        # AUDIT-RV-001 fix 2026-09-22: 原用 REV001 作 fixture 是因为它当时在
        # config 里是 PLANNED；2026-09-22 三方登记表对齐后 REV001 已修正为
        # RUNNING（start_date 2026-08-16），不再适合验证「快照 RUNNING 但
        # config PLANNED」的漂移场景。改用 GROWTH05-CTR-001 —— 它是真 PLANNED
        # 且 start_date:null 的实验，正是漂移检测要抓的目标。
        e = {"experiment_id": "GROWTH05-CTR-001", "status": "RUNNING"}
        assert fdr._effective_running(e, cfg) == "NOT_STARTED"

    def test_retired_config_is_terminal_regardless_of_snapshot(self):
        # AUDIT-RV-001 fix 2026-09-22: REV002 于 2026-09-21 RETIRED
        # (decision=RETIRED_INVALID_INSTRUMENT)。原逻辑不识别 RETIRED，
        # 会把快照里的 PENDING/INSUFFICIENT_SAMPLE 当真实状态；现在必须
        # 强制归入 RETIRED 终态，避免它继续出现在日报的「待启动 N」里。
        cfg = fdr.load_experiment_config()
        # 无论快照怎么写，只要 config 标 RETIRED 就该被 _effective_running 归入终态
        e = {"experiment_id": "REV002", "status": "PENDING"}
        assert fdr._effective_running(e, cfg) == "RETIRED"
        e2 = {"experiment_id": "REV002", "status": "INSUFFICIENT_SAMPLE"}
        assert fdr._effective_running(e2, cfg) == "RETIRED"

    def test_registry_age_days_detects_stale(self):
        # AUDIT-RV-001 fix 2026-09-22: experiments.json updated_at 2026-09-06 ->
        # 2026-09-22（15 天陈旧）导致 DRIVE-001 幻影。>7 天触发陈旧告警。
        cfg = fdr.load_experiment_config()
        # 当前 updated_at=2026-09-22，age_days 应 ≤ 3（当天/次日运行都成立）
        age = fdr.experiment_registry_age_days(cfg)
        assert age is not None and age <= 3
        # 模拟陈旧：把 updated_at 改成 2026-09-01 -> age ≥ 20
        cfg_stale = dict(cfg, __updated_at__="2026-09-01")
        assert fdr.experiment_registry_age_days(cfg_stale) >= 20
        # 无 updated_at 字段 -> 不告警
        cfg_noattr = {e: v for e, v in cfg.items() if e != "__updated_at__"}
        assert fdr.experiment_registry_age_days(cfg_noattr) is None

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


# ---------------------------------------------------------------------------
# 6. 实验登记表收敛：快照不再硬编码 RUNNING
# ---------------------------------------------------------------------------

class TestExperimentRegistryConvergence:
    """reporting_kpi_engine.build_experiments 原先有硬编码 status_override，
    把 REV001 / DRIVE-001 / GROWTH05-CTR-001 无条件标成 RUNNING；REV002 的
    RUNNING 来自 CSV 里的 start_date 2026-08-16（那是「原计划启动日」）。
    而 static/experiments.json（owner 指定为权威）里它们全是 PLANNED /
    start_date:null —— 从未部署 CTA，样本不可能累积。
    """

    def test_registry_reads_all_config_entries(self):
        status, start = rke._read_experiment_registry()
        assert len(status) >= 7
        assert "REV001" in status

    def test_snapshot_experiments_follow_registry(self):
        status, start = rke._read_experiment_registry()
        built = rke.build_experiments()
        by_id = {e["experiment_id"]: e for e in built["experiments"]}
        for eid, cfg_status in status.items():
            if eid in by_id:
                assert by_id[eid]["status"] == cfg_status, (
                    f"{eid}: 快照 {by_id[eid]['status']} != 登记表 {cfg_status}"
                )

    def test_not_started_experiments_have_no_start_date(self):
        status, start = rke._read_experiment_registry()
        built = rke.build_experiments()
        by_id = {e["experiment_id"]: e for e in built["experiments"]}
        for eid, st in status.items():
            if st in ("PLANNED", "PENDING") and eid in by_id:
                assert by_id[eid]["start_date"] is None, (
                    f"{eid}: 未启动实验不应有 start_date"
                )

    def test_registry_missing_falls_back_to_csv(self, monkeypatch, tmp_path):
        monkeypatch.setattr(rke, "EXPERIMENT_REGISTRY", tmp_path / "missing.json")
        assert rke._read_experiment_registry() == ({}, {})


# ---------------------------------------------------------------------------
# 7. 备份/回滚能力实测（不再硬编码 NOT_AVAILABLE）
# ---------------------------------------------------------------------------

class TestBackupRollbackState:
    """原实现把 backup_rollback 硬编码为 NOT_AVAILABLE，机制建成后仍会
    长期显示「备份回滚: 未配置」，让日报的阻塞区挂着一个不存在的问题。
    """

    def test_real_repo_state_is_deterministic(self):
        status, iso, note = rke._backup_rollback_state()
        assert status in ("CONFIGURED", "SCRIPT_ONLY", "PARTIAL", "NOT_AVAILABLE")
        assert isinstance(note, str) and note

    def test_no_workflow_no_script_is_not_available(self, monkeypatch, tmp_path):
        monkeypatch.setattr(rke, "BASE", tmp_path)
        status, iso, note = rke._backup_rollback_state()
        assert status == "NOT_AVAILABLE"
        assert iso is None

    def test_workflow_and_script_but_no_tag_is_script_only(self, monkeypatch, tmp_path):
        (tmp_path / "scripts").mkdir()
        (tmp_path / "scripts" / "restore_site.sh").write_text("#!/bin/bash\n", encoding="utf-8")
        (tmp_path / ".github" / "workflows").mkdir(parents=True)
        (tmp_path / ".github" / "workflows" / "site-backup-daily.yml").write_text("name: x\n", encoding="utf-8")
        monkeypatch.setattr(rke, "BASE", tmp_path)
        status, iso, note = rke._backup_rollback_state()
        # git 不可用时退化为文件判定，不能报错也不能谎称已配置
        assert status in ("SCRIPT_ONLY", "NOT_AVAILABLE")

    def test_partial_is_reported(self, monkeypatch, tmp_path):
        (tmp_path / "scripts").mkdir()
        (tmp_path / "scripts" / "restore_site.sh").write_text("#!/bin/bash\n", encoding="utf-8")
        monkeypatch.setattr(rke, "BASE", tmp_path)
        status, _iso, note = rke._backup_rollback_state()
        assert status == "PARTIAL"
        assert "机制不完整" in note


# ---------------------------------------------------------------------------
# 8. Canonical 队列交叉核验：陈旧观测不是真冲突
# ---------------------------------------------------------------------------

class TestCanonicalVerification:
    """CANONICAL_CONFLICT_QUEUE.md 由 GSC URL Inspection API 生成，是一次性
    点观测，不会自己失效。源码修好后队列仍会持续列出它，日报于是每天报
    「canonical 冲突 6 处 HIGH」——实测 6/6 都已在源码解决。
    """

    def test_queue_is_parsed(self):
        v = rke._canonical_conflicts_verified()
        assert v["total"] >= 1, f"未解析出任何队列行: {v}"

    def test_verdicts_are_exhaustive(self):
        v = rke._canonical_conflicts_verified()
        assert v["real"] + v["stale"] + v["unknown"] == v["total"]

    def test_current_queue_has_no_real_conflicts(self):
        """2026-09-20 实测：5 条有精确 301，1 条 front-matter 已声明 www。

        若源码出现真实冲突，这条测试会失败并提示去看具体行。
        """
        v = rke._canonical_conflicts_verified()
        real = [r for r in v["rows"] if r["verdict"] == "REAL"]
        assert not real, f"源码里仍有真实 canonical 冲突: {real}"

    def test_every_row_has_a_reason(self):
        v = rke._canonical_conflicts_verified()
        for r in v["rows"]:
            assert r["reason"], f"{r['url']} 没有判定依据"
            assert r["verdict"] in ("REAL", "STALE", "UNKNOWN")

    def test_missing_queue_does_not_crash(self, monkeypatch, tmp_path):
        monkeypatch.setattr(rke, "SEO", tmp_path)
        v = rke._canonical_conflicts_verified()
        assert v["total"] == 0
        assert v["real"] == 0

    def test_real_conflict_is_detected(self, monkeypatch, tmp_path):
        """构造一条真冲突：无 301，front-matter 指向的页与队列两个值都不符。"""
        seo = tmp_path / "seo"
        seo.mkdir()
        (tmp_path / "static").mkdir()
        (tmp_path / "static" / "_redirects").write_text("", encoding="utf-8")
        posts = tmp_path / "content" / "posts"
        posts.mkdir(parents=True)
        (posts / "2026-01-01-my-post.md").write_text(
            "---\ncanonicalURL: \"https://www.example.com/posts/wrong-page/\"\n---\nbody\n",
            encoding="utf-8")
        (seo / "CANONICAL_CONFLICT_QUEUE.md").write_text(
            "| url | canonical | user_canonical | sitemap_status | indexed_status | severity | recommended_action |\n"
            "|---|---|---|---|---|---|---|\n"
            "| https://www.example.com/posts/my-post/ "
            "| https://www.example.com/posts/my-post/ "
            "| https://www.example.com/posts/the-correct-page/ "
            "| NOT_IN_SITEMAP | INDEXED | HIGH | TECHNICAL_REVIEW |\n",
            encoding="utf-8")
        monkeypatch.setattr(rke, "BASE", tmp_path)
        monkeypatch.setattr(rke, "SEO", seo)
        v = rke._canonical_conflicts_verified()
        assert v["total"] == 1
        assert v["real"] == 1
        assert v["rows"][0]["verdict"] == "REAL"

    def test_front_matter_matching_google_canonical_is_stale(self, monkeypatch, tmp_path):
        """front-matter 与 google_canonical 一致 = 源已声明正确值，属陈旧观测。"""
        seo = tmp_path / "seo"
        seo.mkdir()
        (tmp_path / "static").mkdir()
        (tmp_path / "static" / "_redirects").write_text("", encoding="utf-8")
        posts = tmp_path / "content" / "posts"
        posts.mkdir(parents=True)
        (posts / "2026-01-01-my-post.md").write_text(
            "---\ncanonicalURL: \"https://www.example.com/posts/other-post/\"\n---\nbody\n",
            encoding="utf-8")
        (seo / "CANONICAL_CONFLICT_QUEUE.md").write_text(
            "| url | canonical | user_canonical | sitemap_status | indexed_status | severity | recommended_action |\n"
            "|---|---|---|---|---|---|---|\n"
            "| https://www.example.com/posts/my-post/ "
            "| https://www.example.com/posts/other-post/ "
            "| https://www.example.com/posts/my-post/ "
            "| NOT_IN_SITEMAP | INDEXED | HIGH | TECHNICAL_REVIEW |\n",
            encoding="utf-8")
        monkeypatch.setattr(rke, "BASE", tmp_path)
        monkeypatch.setattr(rke, "SEO", seo)
        v = rke._canonical_conflicts_verified()
        assert v["stale"] == 1
        assert "front-matter" in v["rows"][0]["reason"]

    def test_exact_redirect_is_stale(self, monkeypatch, tmp_path):
        """_redirects 里已有精确 301 = 源已修。"""
        seo = tmp_path / "seo"
        seo.mkdir()
        (tmp_path / "static").mkdir()
        (tmp_path / "static" / "_redirects").write_text(
            "/posts/old-slug/ /posts/new-slug/ 301\n", encoding="utf-8")
        posts = tmp_path / "content" / "posts"
        posts.mkdir(parents=True)
        (seo / "CANONICAL_CONFLICT_QUEUE.md").write_text(
            "| url | canonical | user_canonical | sitemap_status | indexed_status | severity | recommended_action |\n"
            "|---|---|---|---|---|---|---|\n"
            "| https://www.example.com/posts/old-slug/ "
            "| https://www.example.com/posts/old-slug/ "
            "| https://www.example.com/posts/new-slug/ "
            "| NOT_IN_SITEMAP | INDEXED | HIGH | TECHNICAL_REVIEW |\n",
            encoding="utf-8")
        monkeypatch.setattr(rke, "BASE", tmp_path)
        monkeypatch.setattr(rke, "SEO", seo)
        v = rke._canonical_conflicts_verified()
        assert v["stale"] == 1
        assert "301 已存在" in v["rows"][0]["reason"]



