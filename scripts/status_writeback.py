#!/usr/bin/env python3
"""
Status Writeback Middleware — 统一状态回写中间件

所有 Agent / Router / 修复器 完成操作后，必须通过本中间件回写状态到原始数据源，
确保看板/报表反映真实状态，避免"修复了但看板还显示失败"的闭环断裂。

支持的回写目标：
1. site_health_issues_*.json  — 问题巡检结果
2. reports/site_health/site_health_*.json — site_health summary
3. agent_tasks/task_*.json — Agent 任务状态
4. GitHub Actions workflow 状态（通过 gh CLI）
5. execution_log.json — 执行日志

Usage:
    from status_writeback import writeback_issue, writeback_workflow, writeback_agent_task
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).parent.parent
ISSUES_DIR = BASE_DIR / "reports" / "daily_issues"
SITE_HEALTH_DIR = BASE_DIR / "reports" / "site_health"
AGENT_TASKS_DIR = ISSUES_DIR / "agent_tasks"
EXECUTION_LOG = ISSUES_DIR / "execution_log.json"


def _load_json(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def writeback_issue(
    source_file: str,
    issue_type: str,
    status: str,
    resolved_by: Optional[str] = None,
    resolution_note: Optional[str] = None,
    target_date: Optional[str] = None,
    issue_id: Optional[str] = None,
    page: Optional[str] = None,
) -> bool:
    """
    回写单个问题的状态到 site_health_issues 文件。

    Args:
        source_file: 来源文件名，如 "site_health_issues_2026-09-04.json"
        issue_type: 问题类型，如 "title_too_short"
        status: 新状态 — assigned / resolved / false_positive / in_progress / failed
        resolved_by: 解决者（agent 名称）
        resolution_note: 解决说明
        target_date: 目标日期，如 "2026-09-04"，不填则用今天

    Returns:
        True if updated, False if not found
    """
    if not target_date:
        target_date = datetime.now().strftime("%Y-%m-%d")

    def matches(issue: dict) -> bool:
        if issue_id and str(issue.get("id", "")) == str(issue_id):
            return True
        if issue.get("type") != issue_type:
            return False
        if page:
            normalized_page = str(page).replace("\\", "/")
            candidates = {
                str(issue.get("file", "")).replace("\\", "/"),
                str(issue.get("page", "")).replace("\\", "/"),
            }
            return normalized_page in candidates
        return True

    # 1. 回写到 daily_issues/site_health_issues_*.json
    issues_file = ISSUES_DIR / source_file
    updated = False
    if issues_file.exists():
        data = _load_json(issues_file)
        for issue in data.get("issues", []):
            if matches(issue):
                issue["status"] = status
                issue["assigned"] = status in ("assigned", "in_progress", "resolved", "false_positive")
                if resolved_by:
                    issue["resolved_by"] = resolved_by
                if resolution_note:
                    issue["resolution_note"] = resolution_note
                issue["updated_at"] = datetime.now().isoformat()
                if status in ("resolved", "false_positive"):
                    issue["resolved_at"] = datetime.now().isoformat()
                updated = True
        if updated:
            _save_json(issues_file, data)

    # 2. 同步回写到 reports/site_health/site_health_*.json summary
    sh_file = SITE_HEALTH_DIR / f"site_health_{target_date}.json"
    if sh_file.exists():
        sh = _load_json(sh_file)
        for issue in sh.get("issues", []):
            if matches(issue):
                issue["status"] = status
                issue["assigned"] = True
                if resolved_by:
                    issue["resolved_by"] = resolved_by
                if resolution_note:
                    issue["resolution_note"] = resolution_note
                updated = True

        # 重新计算 summary
        issues = sh.get("issues", [])
        summary = sh.get("summary", {})
        summary["need_manual"] = sum(
            1 for i in issues if i.get("status") in ("new", "", None) or not i.get("assigned")
        )
        summary["resolved"] = sum(
            1 for i in issues if i.get("status") in ("resolved", "fixed", "false_positive")
        )
        summary["in_progress"] = sum(
            1 for i in issues if i.get("status") in ("assigned", "in_progress")
        )
        summary["last_updated"] = datetime.now().isoformat()
        sh["summary"] = summary
        _save_json(sh_file, sh)

    return updated


def writeback_agent_task(
    task_id: str,
    status: str,
    resolved_count: int = 0,
    failed_count: int = 0,
    execution_note: Optional[str] = None,
    execution_log: Optional[Path] = None,
    tasks_dir: Optional[Path] = None,
) -> bool:
    """
    回写 Agent 任务的执行状态。

    Args:
        task_id: 任务 ID，如 "task_2026-09-04_content"
        status: pending / in_progress / completed / failed / partial
        resolved_count: 已解决问题数
        failed_count: 失败问题数
        execution_note: 执行说明

    Returns:
        True if updated
    """
    task_file = (tasks_dir or AGENT_TASKS_DIR) / f"{task_id}.json"
    if not task_file.exists():
        return False

    task = _load_json(task_file)
    task["status"] = status
    task["updated_at"] = datetime.now().isoformat()
    task["execution"] = {
        "resolved_count": resolved_count,
        "failed_count": failed_count,
        "completed_at": datetime.now().isoformat() if status == "completed" else None,
        "note": execution_note,
    }
    _save_json(task_file, task)

    # 记录执行日志
    _log_execution(
        task_id,
        status,
        resolved_count,
        failed_count,
        execution_note,
        execution_log=execution_log,
        tasks_dir=tasks_dir,
    )
    return True


def writeback_workflow(
    workflow_name: str,
    status: str,
    fixed_by: Optional[str] = None,
    fix_note: Optional[str] = None,
) -> bool:
    """
    记录 Workflow 修复状态（写入本地修复日志，看板可读取）。

    Args:
        workflow_name: Workflow 名称
        status: fixed / retried / needs_manual
        fixed_by: 修复者
        fix_note: 修复说明
    """
    log_file = ISSUES_DIR / "workflow_fix_log.json"
    log = _load_json(log_file)
    if "fixes" not in log:
        log["fixes"] = []

    log["fixes"].append({
        "workflow": workflow_name,
        "status": status,
        "fixed_by": fixed_by,
        "fix_note": fix_note,
        "fixed_at": datetime.now().isoformat(),
    })
    _save_json(log_file, log)
    return True


def _log_execution(
    task_id: str,
    status: str,
    resolved: int,
    failed: int,
    note: Optional[str],
    execution_log: Optional[Path] = None,
    tasks_dir: Optional[Path] = None,
):
    """记录执行日志"""
    log_path = execution_log or EXECUTION_LOG
    log = _load_json(log_path)
    if "executions" not in log:
        log["executions"] = []
    entry = {
        "task_id": task_id,
        "status": status,
        "resolved": resolved,
        "failed": failed,
        "note": note,
        "executed_at": datetime.now().isoformat(),
    }
    log["executions"].append(entry)
    log["last_run"] = datetime.now().isoformat()
    log["total_executions"] = log.get("total_executions", 0) + 1

    # Keep the legacy summary fields for existing consumers, but rebuild them
    # from real task executions. A "partial" task is work handed to a human,
    # not a completed fix.
    task_date = task_id.split("_", 2)[1] if task_id.startswith("task_") else ""
    dated_agents: dict = {}
    latest_by_task: dict[str, dict] = {}
    for item in log["executions"]:
        item_date = (
            str(item.get("task_id", "")).split("_", 2)[1]
            if str(item.get("task_id", "")).startswith("task_")
            else ""
        )
        if item_date != task_date:
            continue
        latest_by_task[str(item.get("task_id", ""))] = item

    for item in latest_by_task.values():
        item_agent = str(item.get("task_id", "")).rsplit("_", 1)[-1]
        agent_stats = dated_agents.setdefault(
            item_agent,
            {
                "total": 0,
                "fixed": 0,
                "failed": 0,
                "manual_review": 0,
                "in_progress": 0,
                "last_run": "",
            },
        )
        executed_at = str(item.get("executed_at", "") or "")
        if executed_at > str(agent_stats.get("last_run", "")):
            agent_stats["last_run"] = executed_at
        # Only terminal entries are counted so each task is not double-counted
        # when it briefly passes through in_progress.
        if item.get("status") == "in_progress":
            agent_stats["in_progress"] = agent_stats.get("in_progress", 0) + 1
        else:
            agent_stats["total"] = agent_stats.get("total", 0) + 1
            if item.get("status") == "completed":
                agent_stats["fixed"] = agent_stats.get("fixed", 0) + int(
                    item.get("resolved", 0) or 0
                )
            elif item.get("status") == "failed":
                agent_stats["failed"] = agent_stats.get("failed", 0) + 1
            elif item.get("status") == "partial":
                agent_stats["manual_review"] = agent_stats.get("manual_review", 0) + 1

    reconcile_agents_with_tasks(
        dated_agents,
        task_date,
        tasks_dir or AGENT_TASKS_DIR,
    )
    log["target_date"] = task_date or log.get("target_date", "")
    log["agents"] = dated_agents
    log["summary"] = {
        "total": sum(v.get("total", 0) for v in dated_agents.values()),
        "fixed": sum(v.get("fixed", 0) for v in dated_agents.values()),
        "failed": sum(v.get("failed", 0) for v in dated_agents.values()),
        "manual_review": sum(
            v.get("manual_review", 0) for v in dated_agents.values()
        ),
        "in_progress": sum(
            v.get("in_progress", 0) for v in dated_agents.values()
        ),
    }
    _save_json(log_path, log)


def reconcile_agents_with_tasks(
    dated_agents: dict,
    target_date: str,
    tasks_dir: Path,
):
    """Prefer current task files over stale terminal log entries.

    A task can be reopened under another agent or cleared by the router after
    the original execution. The dashboard must reflect the current task file,
    not the last historical execution for that agent.
    """
    if not target_date:
        return
    for task_file in tasks_dir.glob(f"task_{target_date}_*.json"):
        task = _load_json(task_file)
        agent = str(task.get("agent", "") or "")
        if not agent:
            continue
        status = str(task.get("status", "") or "")
        execution = task.get("execution") or {}
        resolved = int(execution.get("resolved_count", 0) or 0)
        failed_count = int(execution.get("failed_count", 0) or 0)
        issue_count = int(task.get("issue_count", 0) or 0)

        if status == "completed" and issue_count == 0 and resolved == 0:
            dated_agents.pop(agent, None)
            continue

        stats = dated_agents.setdefault(
            agent,
            {
                "total": 0,
                "fixed": 0,
                "failed": 0,
                "manual_review": 0,
                "in_progress": 0,
                "last_run": "",
            },
        )
        stats["total"] = max(int(stats.get("total", 0) or 0), 1)
        stats["last_run"] = max(
            str(stats.get("last_run", "") or ""),
            str(task.get("updated_at", "") or ""),
        )
        if status in ("pending", "in_progress"):
            stats["in_progress"] = max(
                int(stats.get("in_progress", 0) or 0), 1
            )
        elif status == "partial":
            stats["manual_review"] = max(
                int(stats.get("manual_review", 0) or 0), 1
            )
            stats["in_progress"] = 0
        elif status == "failed":
            stats["failed"] = max(
                int(stats.get("failed", 0) or 0), max(failed_count, 1)
            )
            stats["in_progress"] = 0
        elif status == "completed":
            stats["fixed"] = max(int(stats.get("fixed", 0) or 0), resolved)
            stats["manual_review"] = 0
            stats["failed"] = 0
            stats["in_progress"] = 0


def get_pending_issues(target_date: Optional[str] = None) -> list:
    """获取所有待处理问题（跨来源）"""
    if not target_date:
        target_date = datetime.now().strftime("%Y-%m-%d")

    pending = []
    # site_health_issues
    issues_file = ISSUES_DIR / f"site_health_issues_{target_date}.json"
    if issues_file.exists():
        data = _load_json(issues_file)
        for issue in data.get("issues", []):
            if issue.get("status") in ("new", "", None) or not issue.get("assigned"):
                pending.append({**issue, "source": "site_health"})

    return pending


def get_pending_agent_tasks() -> list:
    """获取所有 pending 的 Agent 任务"""
    pending = []
    for task_file in AGENT_TASKS_DIR.glob("task_*.json"):
        task = _load_json(task_file)
        if task.get("status") == "pending":
            pending.append(task)
    return pending


if __name__ == "__main__":
    # 自检
    print("=== Status Writeback Middleware ===")
    print(f"Base dir: {BASE_DIR}")
    print(f"Issues dir: {ISSUES_DIR}")
    print(f"Agent tasks dir: {AGENT_TASKS_DIR}")
    pending = get_pending_agent_tasks()
    print(f"Pending agent tasks: {len(pending)}")
    for t in pending:
        print(f"  - {t.get('task_id')}: {t.get('issue_count')} issues, agent={t.get('agent')}")
