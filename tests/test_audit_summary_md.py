# -*- coding: utf-8 -*-
"""tests/test_audit_summary_md.py

回归锁：scripts/audit_summary_md.py（CI 报告摘要）
+ .github/workflows/endpoint-health-audit.yml（定时审计）

为什么值得锁
------------
api_health 报告曾停在 11 天前没人刷新，agent_kpi_auditor 于是拿过期快照
给 ops.api_health_rate 打分（75.0%，线上实际 100.0%）。
根因是没有定时任务跑这两个审计脚本。
这条 workflow 把测量放进日程；测试锁住两件事：
  1. 摘要能正确呈现通过/失败（否则 CI 看板一直是绿的）
  2. workflow YAML 语法有效、触发器与提交范围正确
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import audit_summary_md as M  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def _api_report(tmp_path, passed=True, rate=100.0):
    p = tmp_path / "reports" / "api_health"
    p.mkdir(parents=True, exist_ok=True)
    body = {
        "summary": {"total": 2, "passed": 2 if passed else 1,
                    "failed": 0 if passed else 1, "pass_rate": rate},
        "api_tests": [
            {"name": "checkout_valid_plan", "passed": True},
            {"name": "subscribe_cors_preflight", "passed": passed},
        ],
    }
    f = p / "api_health_20260918_151345.json"
    f.write_text(json.dumps(body), encoding="utf-8")
    return f


def _sub_report(tmp_path, passed=True):
    p = tmp_path / "reports" / "subscription_health"
    p.mkdir(parents=True, exist_ok=True)
    body = {
        "summary": {"total": 1, "passed": 1 if passed else 0,
                    "failed": 0 if passed else 1, "all_passed": passed},
        "api_tests": [{"name": "subscribe_valid_email", "passed": passed}],
        "mailerlite": {"configured": False, "endpoint_reported": {
            "mailerlite": "configured_and_accepting",
            "resend": "configured_but_rejected_by_provider"}},
    }
    f = p / "subscription_health_20260918_145141.json"
    f.write_text(json.dumps(body), encoding="utf-8")
    return f


# ── 通过场景 ────────────────────────────────────────────────

def test_all_pass_shows_green(tmp_path):
    _api_report(tmp_path, passed=True)
    _sub_report(tmp_path, passed=True)
    text, failed = M.build_summary(tmp_path)
    assert failed is False
    assert "✅ 2/2" in text
    assert "100.0%" in text
    assert "失败用例 |" in text
    assert "无" in text


def test_subscription_line_shows_provider_status(tmp_path):
    """服务商状态必须显示出来——这是 2026-09-18 修的「本机 env 假信号」，
    如果摘要不回显，CI 看板就看不出版本是否带了这个修复。"""
    _api_report(tmp_path)
    _sub_report(tmp_path)
    text, _ = M.build_summary(tmp_path)
    assert "MailerLite=configured_and_accepting" in text
    assert "Resend=configured_but_rejected_by_provider" in text


# ── 失败场景 ────────────────────────────────────────────────

def test_failed_case_is_marked_and_named(tmp_path):
    _api_report(tmp_path, passed=False, rate=50.0)
    text, failed = M.build_summary(tmp_path)
    assert failed is True
    assert "❌" in text
    assert "1/2" in text
    assert "subscribe_cors_preflight" in text  # 失败用例必须点名，不能只显示数字


def test_fail_flag_returns_nonzero(tmp_path):
    """--fail 必须在有失败时非零，否则 workflow 的条件判定会永远为假。"""
    _api_report(tmp_path, passed=False)
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "audit_summary_md.py"),
         "--fail", "--root", str(tmp_path)],
        capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert r.returncode == 1, r.stdout


def test_fail_flag_zero_when_all_pass(tmp_path):
    _api_report(tmp_path)
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "audit_summary_md.py"),
         "--fail", "--root", str(tmp_path)],
        capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert r.returncode == 0, r.stdout


def test_no_reports_does_not_crash(tmp_path):
    """报告缺失时给提示而不是抛异常——CI 步骤不能因为摘要脚本崩掉。"""
    text, failed = M.build_summary(tmp_path)
    assert failed is False
    assert "未找到任何审计报告" in text


def test_malformed_report_does_not_crash(tmp_path):
    p = tmp_path / "reports" / "api_health"
    p.mkdir(parents=True, exist_ok=True)
    (p / "api_health_20260918_000000.json").write_text("{broken", encoding="utf-8")
    text, failed = M.build_summary(tmp_path)
    assert failed is True          # 读不出来按失败处理，不静默
    assert "读取失败" in text


# ── 最新文件选择 ────────────────────────────────────────────

def test_latest_picks_newest_file(tmp_path):
    """mtime 是选择依据（文件名只是兜底），所以必须用 os.utime 显式设时间：
    按写入先后判定会得出相反结论。"""
    _api_report(tmp_path)
    p = tmp_path / "reports" / "api_health"
    newest = p / "api_health_20260918_151345.json"
    older = p / "api_health_20260901_000000.json"
    older.write_text(json.dumps({"summary": {"passed": 0, "total": 2,
                                             "pass_rate": 0.0},
                                 "api_tests": [{"name": "a", "passed": False}]}),
                     encoding="utf-8")
    import os
    import time
    now = time.time()
    os.utime(newest, (now + 3600, now + 3600))
    os.utime(older, (now - 3600, now - 3600))
    text, _ = M.build_summary(tmp_path)
    assert "api_health_20260918_151345.json" in text
    assert "api_health_20260901_000000.json" not in text


# ── workflow YAML ───────────────────────────────────────────

WORKFLOW = ROOT / ".github" / "workflows" / "endpoint-health-audit.yml"


def _workflow_code():
    """只返回 YAML 里的可执行行，剥掉注释。
    注释里会出现 git add -A / python -c 这类字样（用来解释为什么不用它们），
    直接全文匹配会误判。"""
    out = []
    for line in WORKFLOW.read_text(encoding="utf-8").splitlines():
        stripped = line.split("#", 1)[0].rstrip()
        if stripped:
            out.append(stripped)
    return "\n".join(out)


def test_workflow_file_exists():
    assert WORKFLOW.is_file(), "定时审计 workflow 缺失——报告又会回到靠人工刷新"


def test_workflow_yaml_parses():
    """语法无效 = 这条流水线永远不会跑，等于没写。"""
    try:
        import yaml
    except ImportError:
        pytest.skip("PyYAML 不可用")
    with open(WORKFLOW, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert data, "YAML 解析为空"


def test_workflow_runs_both_audit_scripts():
    src = WORKFLOW.read_text(encoding="utf-8")
    assert "scripts/api_health_audit.py" in src
    assert "scripts/subscription_health_audit.py" in src


def test_workflow_has_schedule_trigger():
    src = WORKFLOW.read_text(encoding="utf-8")
    assert "schedule:" in src and "cron:" in src, "必须定时触发"
    assert "workflow_dispatch" in src, "必须保留手动触发入口"


def test_workflow_does_not_use_git_add_all():
    """site-health-daily.yml 用 git add -A 会把工作区残留文件打进提交。
    这里只允许提交两个审计目录。"""
    code = _workflow_code()
    assert "git add -A" not in code
    assert "git add reports/api_health reports/subscription_health" in code


def test_workflow_commits_even_on_audit_failure():
    """端点真的挂了时，报告提交不能一起被取消——那正是最该留档的时刻。"""
    src = WORKFLOW.read_text(encoding="utf-8")
    assert src.count("if: always()") >= 2, "Summarize/Commit 必须带 if: always()"


def test_workflow_passes_mailerlite_secret():
    """CI 里要能跑本机 MailerLite 检查（端点自报是另一路，两者并列）。"""
    src = WORKFLOW.read_text(encoding="utf-8")
    assert "secrets.MAILERLITE_API_TOKEN" in src


def test_summary_logic_lives_in_a_script_not_inline_python():
    """内联 python -c 嵌多层 f-string 引号，只能等 CI 才暴露错误。"""
    code = _workflow_code()
    assert "audit_summary_md.py" in code
    assert "python -c" not in code
