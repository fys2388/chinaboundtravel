#!/usr/bin/env python3
"""Unified Agent task queue.

All issue sources write the same task format so the executor can process
quality-gate failures, workflow failures and Site Health issues without one
source overwriting another.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import date, datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_TASKS_DIR = BASE_DIR / "reports" / "daily_issues" / "agent_tasks"

AGENT_NAMES = {
    "content": "Content Intelligence Agent (内容智能优化)",
    "seo": "SEO Intelligent Agent (SEO智能优化)",
    "social": "Social Intelligence Agent (社媒智能优化)",
    "user": "User Intelligence Agent (用户智能运营)",
    "revenue": "Revenue Analytics Engine (收入分析引擎)",
    "conversion": "Conversion Optimization Agent (转化优化Agent)",
    "frontend": "Frontend Agent (页面/视觉/响应式)",
    "ops": "Ops Agent (部署/配置/权限)",
}

OWNER_AGENT_MAP = {
    "content": "content",
    "seo": "seo",
    "social": "social",
    "user": "user",
    "revenue": "revenue",
    "conversion": "conversion",
    "frontend": "frontend",
    "engineering": "frontend",
    "ops": "ops",
    "operations": "ops",
    "orchestrator": "ops",
}

SEVERITY_MAP = {
    "P0": "critical",
    "P1": "high",
    "P2": "medium",
    "critical": "critical",
    "high": "high",
    "medium": "medium",
    "low": "low",
}
SEVERITY_WEIGHT = {"critical": 4, "high": 3, "medium": 2, "low": 1}


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def normalize_agent(value: str | None) -> str:
    return OWNER_AGENT_MAP.get(str(value or "").strip().lower(), "ops")


def normalize_severity(value: str | None) -> str:
    return SEVERITY_MAP.get(str(value or "").strip(), "medium")


def _task_id(target_date: str, agent: str) -> str:
    return f"task_{target_date}_{agent}"


def _stable_issue_id(issue: dict, task_source: str, agent: str) -> str:
    explicit = issue.get("id")
    if explicit:
        return str(explicit)
    seed = "|".join(
        str(issue.get(key, ""))
        for key in ("type", "page", "file", "title", "evidence")
    )
    digest = hashlib.sha1(f"{task_source}|{agent}|{seed}".encode("utf-8")).hexdigest()
    return f"{task_source}-{digest[:12]}"


def _normalize_path(value: object) -> str:
    return str(value or "").replace("\\", "/")


def normalize_issue(issue: dict, task_source: str) -> dict:
    owner = issue.get("owner") or issue.get("assigned_to") or issue.get("agent")
    agent = normalize_agent(owner)
    title = issue.get("title") or issue.get("description") or issue.get("type", "Issue")
    evidence = issue.get("evidence") or issue.get("message") or issue.get("description") or ""
    page = _normalize_path(issue.get("page") or issue.get("file") or "")
    return {
        "id": _stable_issue_id(issue, task_source, agent),
        "type": issue.get("type", "unknown"),
        "title": title,
        "description": issue.get("description") or title,
        "page": page,
        "file": _normalize_path(issue.get("file") or page),
        "evidence": evidence,
        "recommended_action": issue.get("recommended_action")
        or issue.get("resolution_note")
        or "Review the issue and apply the documented remediation.",
        "severity": normalize_severity(issue.get("severity")),
        "agent": agent,
        "action": issue.get("action") or "manual_review",
        "source": issue.get("source") or task_source,
        "source_file": issue.get("source_file") or "",
        "task_source": task_source,
        "status": "new",
        "assigned": True,
        "assigned_to": agent,
        "detected_at": issue.get("detected_at") or _now_iso(),
    }


def _task_path(tasks_dir: Path, target_date: str, agent: str) -> Path:
    return tasks_dir / f"{_task_id(target_date, agent)}.json"


def _load_task(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _same_payload(existing: dict, candidate: dict) -> bool:
    keys = (
        "agent",
        "agent_name",
        "task_id",
        "target_date",
        "issue_count",
        "severity_summary",
        "issues",
        "priority_issue",
        "expected_actions",
        "status",
    )
    return all(existing.get(key) == candidate.get(key) for key in keys)


def enqueue_issues(
    issues: list[dict],
    task_source: str,
    target_date: str | None = None,
    tasks_dir: Path | None = None,
    prune_missing: bool = True,
) -> list[dict]:
    """Merge issues into per-agent task files and return changed task metadata.

    ``prune_missing`` should be True only when the caller provides a complete
    snapshot for the source. Event-driven callers must set it to False so a new
    event cannot erase unrelated pending work from the same source.
    """
    target_date = target_date or date.today().isoformat()
    tasks_dir = tasks_dir or DEFAULT_TASKS_DIR
    tasks_dir.mkdir(parents=True, exist_ok=True)

    grouped: dict[str, list[dict]] = {}
    for issue in issues:
        normalized = normalize_issue(issue, task_source)
        grouped.setdefault(normalized["agent"], []).append(normalized)

    # If a source no longer reports an issue, clear that source's issues from
    # every existing task so resolved findings do not reappear as work.
    if prune_missing:
        for task_file in tasks_dir.glob(f"task_{target_date}_*.json"):
            existing = _load_task(task_file)
            has_current_source = any(
                issue.get("task_source") == task_source
                for issue in existing.get("issues", [])
            )
            has_legacy_daily_source = (
                task_source == "daily_issue_router"
                and any(
                    issue.get("task_source") is None
                    for issue in existing.get("issues", [])
                )
            )
            if has_current_source or has_legacy_daily_source:
                agent = existing.get("agent")
                if agent and agent not in grouped:
                    grouped[agent] = []

    results = []
    for agent, current_issues in grouped.items():
        path = _task_path(tasks_dir, target_date, agent)
        existing = _load_task(path)
        # Tasks created before task_source existed came from the daily issue
        # router. Treat those entries as the same source on migration; the
        # stable IDs keep unchanged issues from accumulating across runs.
        existing_issues = existing.get("issues", [])
        legacy_daily_issues = [
            issue
            for issue in existing_issues
            if task_source == "daily_issue_router"
            and issue.get("task_source") is None
        ]
        had_legacy_daily_source = bool(legacy_daily_issues)
        legacy_daily_ids = {issue.get("id") for issue in legacy_daily_issues}
        current_ids = {issue.get("id") for issue in current_issues}
        kept = []
        for issue in existing_issues:
            if issue.get("id") in legacy_daily_ids:
                continue
            if issue.get("task_source") != task_source:
                kept.append(issue)
                continue
            if not prune_missing and issue.get("id") not in current_ids:
                kept.append(issue)
        previous_source_ids = {
            issue.get("id")
            for issue in existing_issues
            if issue.get("task_source") == task_source
            or issue.get("id") in legacy_daily_ids
        }
        previous_source = {
            issue.get("id"): issue
            for issue in existing_issues
            if issue.get("task_source") == task_source
            or issue.get("id") in legacy_daily_ids
        }
        for issue in current_issues:
            previous = previous_source.get(issue.get("id"))
            if previous and previous.get("detected_at"):
                issue["detected_at"] = previous["detected_at"]
        has_new_issues = bool(current_ids - previous_source_ids)
        merged = kept + current_issues
        merged.sort(
            key=lambda issue: (
                -SEVERITY_WEIGHT.get(issue.get("severity"), 0),
                issue.get("page", ""),
                issue.get("type", ""),
            )
        )

        previous_status = existing.get("status", "")
        if merged:
            if had_legacy_daily_source and previous_status == "completed":
                status = "pending"
            elif has_new_issues and previous_status not in ("pending", "in_progress"):
                status = "pending"
            else:
                status = previous_status or "pending"
        else:
            status = "completed"

        severity_summary = Counter(
            issue.get("severity", "medium") for issue in merged
        )
        candidate = {
            "agent": agent,
            "agent_name": AGENT_NAMES.get(agent, agent),
            "task_id": _task_id(target_date, agent),
            "created_at": existing.get("created_at") or _now_iso(),
            "updated_at": _now_iso(),
            "target_date": target_date,
            "issue_count": len(merged),
            "severity_summary": {
                level: severity_summary.get(level, 0)
                for level in ("critical", "high", "medium", "low")
            },
            "issues": merged,
            "priority_issue": merged[0] if merged else None,
            "expected_actions": sorted(
                {issue.get("action", "manual_review") for issue in merged}
            ),
            "status": status,
        }
        if status in ("pending", "in_progress") and "execution" in existing:
            candidate["execution"] = {
                "resolved_count": 0,
                "failed_count": 0,
                "completed_at": None,
                "note": "awaiting execution",
            }
        elif "execution" in existing:
            candidate["execution"] = existing["execution"]

        changed = not _same_payload(existing, candidate)
        if changed:
            path.write_text(
                json.dumps(candidate, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        results.append(
            {
                "agent": agent,
                "task_id": candidate["task_id"],
                "path": str(path),
                "issue_count": candidate["issue_count"],
                "changed": changed,
            }
        )

    return results
