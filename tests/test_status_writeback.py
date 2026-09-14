import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import status_writeback  # noqa: E402
from status_writeback import writeback_agent_task, writeback_issue  # noqa: E402


class StatusWritebackTests(unittest.TestCase):
    def _write_task(self, tasks_dir: Path, task_id: str) -> None:
        (tasks_dir / f"{task_id}.json").write_text(
            json.dumps({"task_id": task_id, "status": "pending", "issues": []}),
            encoding="utf-8",
        )

    def test_execution_summary_separates_fixes_manual_and_failures(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tasks_dir = Path(temp_dir) / "agent_tasks"
            tasks_dir.mkdir()
            log_path = Path(temp_dir) / "execution_log.json"

            for task_id in (
                "task_2026-09-13_content",
                "task_2026-09-13_ops",
                "task_2026-09-13_frontend",
            ):
                self._write_task(tasks_dir, task_id)

            writeback_agent_task(
                "task_2026-09-13_content",
                "completed",
                resolved_count=2,
                tasks_dir=tasks_dir,
                execution_log=log_path,
            )
            writeback_agent_task(
                "task_2026-09-13_ops",
                "partial",
                execution_note="manual permission fix required",
                tasks_dir=tasks_dir,
                execution_log=log_path,
            )
            writeback_agent_task(
                "task_2026-09-13_frontend",
                "failed",
                failed_count=1,
                tasks_dir=tasks_dir,
                execution_log=log_path,
            )
            log = json.loads(log_path.read_text(encoding="utf-8"))

        self.assertEqual("2026-09-13", log["target_date"])
        self.assertEqual(3, log["summary"]["total"])
        self.assertEqual(2, log["summary"]["fixed"])
        self.assertEqual(1, log["summary"]["manual_review"])
        self.assertEqual(1, log["summary"]["failed"])
        self.assertEqual(2, log["agents"]["content"]["fixed"])
        self.assertEqual(1, log["agents"]["ops"]["manual_review"])
        self.assertEqual(1, log["agents"]["frontend"]["failed"])

    def test_summary_is_rebuilt_from_terminal_entries_not_double_counted(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tasks_dir = Path(temp_dir) / "agent_tasks"
            tasks_dir.mkdir()
            log_path = Path(temp_dir) / "execution_log.json"
            task_id = "task_2026-09-13_ops"
            self._write_task(tasks_dir, task_id)

            writeback_agent_task(
                task_id,
                "in_progress",
                tasks_dir=tasks_dir,
                execution_log=log_path,
            )
            writeback_agent_task(
                task_id,
                "completed",
                resolved_count=1,
                tasks_dir=tasks_dir,
                execution_log=log_path,
            )
            log = json.loads(log_path.read_text(encoding="utf-8"))

        self.assertEqual(1, log["summary"]["total"])
        self.assertEqual(1, log["summary"]["fixed"])
        self.assertEqual(0, log["agents"]["ops"]["in_progress"])

    def test_issue_writeback_matches_source_page_not_every_same_type(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            issues_dir = Path(temp_dir) / "daily_issues"
            site_health_dir = Path(temp_dir) / "site_health"
            issues_dir.mkdir()
            site_health_dir.mkdir()
            report = {
                "issues": [
                    {
                        "type": "title_too_long",
                        "file": "content\\posts\\a.md",
                        "status": "assigned",
                    },
                    {
                        "type": "title_too_long",
                        "file": "content\\posts\\b.md",
                        "status": "assigned",
                    },
                ]
            }
            (issues_dir / "site_health_issues_audit.json").write_text(
                json.dumps(report), encoding="utf-8"
            )

            with mock.patch.object(status_writeback, "ISSUES_DIR", issues_dir):
                with mock.patch.object(status_writeback, "SITE_HEALTH_DIR", site_health_dir):
                    updated = writeback_issue(
                        source_file="site_health_issues_audit.json",
                        issue_type="title_too_long",
                        status="resolved",
                        page="content/posts/a.md",
                    )

            saved = json.loads(
                (issues_dir / "site_health_issues_audit.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertTrue(updated)
        self.assertEqual("resolved", saved["issues"][0]["status"])
        self.assertEqual("assigned", saved["issues"][1]["status"])


if __name__ == "__main__":
    unittest.main()
