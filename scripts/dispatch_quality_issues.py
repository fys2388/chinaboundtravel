#!/usr/bin/env python3
"""Dispatch open unified quality issues to Agent task files."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from agent_task_queue import enqueue_issues


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "reports" / "quality" / "quality_issues.json"


def load_open_issues(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    resolved = {"resolved", "fixed", "false_positive", "closed"}
    return [
        issue
        for issue in report.get("issues", [])
        if str(issue.get("status", "open")).lower() not in resolved
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--date", default=None)
    args = parser.parse_args()

    issues = load_open_issues(Path(args.input))
    tasks = enqueue_issues(
        issues,
        task_source="quality_gate",
        target_date=args.date,
    )

    changed = [task for task in tasks if task["changed"]]
    print(
        f"quality task dispatch: issues={len(issues)} "
        f"agents={len(tasks)} changed={len(changed)}"
    )
    for task in tasks:
        print(
            f"  {task['agent']}: issues={task['issue_count']} "
            f"changed={task['changed']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
