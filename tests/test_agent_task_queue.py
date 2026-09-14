import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from agent_task_queue import enqueue_issues  # noqa: E402
import agent_task_executor  # noqa: E402
from agent_task_executor import execute_frontend, execute_ops  # noqa: E402
from auto_error_router import enqueue_workflow_failure  # noqa: E402


class AgentTaskQueueTests(unittest.TestCase):
    def test_quality_issue_is_dispatched_to_frontend(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tasks_dir = Path(temp_dir)
            results = enqueue_issues(
                [
                    {
                        "id": "visual-1",
                        "type": "visual_quality_failed",
                        "severity": "P0",
                        "owner": "engineering",
                        "page": "/posts/example/",
                        "evidence": "mobile overflow",
                        "recommended_action": "Fix responsive layout.",
                    }
                ],
                task_source="quality_gate",
                target_date="2026-09-13",
                tasks_dir=tasks_dir,
            )
            task_path = tasks_dir / "task_2026-09-13_frontend.json"
            task = json.loads(task_path.read_text(encoding="utf-8"))

        self.assertEqual(1, len(results))
        self.assertTrue(results[0]["changed"])
        self.assertEqual("frontend", task["agent"])
        self.assertEqual("pending", task["status"])
        self.assertEqual("critical", task["issues"][0]["severity"])

    def test_duplicate_dispatch_is_idempotent(self):
        issue = {
            "id": "content-1",
            "type": "mojibake",
            "severity": "P0",
            "owner": "content",
            "page": "content/posts/broken.md",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            tasks_dir = Path(temp_dir)
            first = enqueue_issues(
                [issue],
                task_source="quality_gate",
                target_date="2026-09-13",
                tasks_dir=tasks_dir,
            )
            second = enqueue_issues(
                [issue],
                task_source="quality_gate",
                target_date="2026-09-13",
                tasks_dir=tasks_dir,
            )

        self.assertTrue(first[0]["changed"])
        self.assertFalse(second[0]["changed"])

    def test_source_file_and_windows_path_are_preserved(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tasks_dir = Path(temp_dir)
            enqueue_issues(
                [
                    {
                        "id": "legacy-audit",
                        "type": "title_too_long",
                        "severity": "P1",
                        "agent": "seo",
                        "file": "content\\posts\\example.md",
                        "source_file": "site_health_issues_audit_2026-09-04.json",
                    }
                ],
                task_source="daily_issue_router",
                target_date="2026-09-13",
                tasks_dir=tasks_dir,
            )
            task = json.loads(
                (tasks_dir / "task_2026-09-13_seo.json").read_text(
                    encoding="utf-8"
                )
            )

        issue = task["issues"][0]
        self.assertEqual(
            "site_health_issues_audit_2026-09-04.json",
            issue["source_file"],
        )
        self.assertEqual("content/posts/example.md", issue["file"])

    def test_workflow_failure_creates_ops_task(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            results = enqueue_workflow_failure(
                "Post-deploy Tasks",
                "34745370937",
                "git_push_failed",
                {"agent": "ops"},
                "failed to push",
                ["post-deploy / push"],
                tasks_dir=Path(temp_dir),
                target_date="2026-09-13",
            )
            task_path = Path(temp_dir) / "task_2026-09-13_ops.json"
            task = json.loads(task_path.read_text(encoding="utf-8"))

        self.assertEqual("ops", results[0]["agent"])
        self.assertEqual("git_push_failed", task["issues"][0]["type"])

    def test_incremental_source_does_not_erase_other_agent_tasks(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tasks_dir = Path(temp_dir)
            enqueue_issues(
                [
                    {
                        "id": "workflow-ops",
                        "type": "git_push_failed",
                        "severity": "P1",
                        "owner": "ops",
                    }
                ],
                task_source="workflow_failure",
                target_date="2026-09-13",
                tasks_dir=tasks_dir,
                prune_missing=False,
            )
            enqueue_issues(
                [
                    {
                        "id": "workflow-content",
                        "type": "content_quality_p0",
                        "severity": "P0",
                        "owner": "content",
                    }
                ],
                task_source="workflow_failure",
                target_date="2026-09-13",
                tasks_dir=tasks_dir,
                prune_missing=False,
            )
            ops_task = json.loads(
                (tasks_dir / "task_2026-09-13_ops.json").read_text(
                    encoding="utf-8"
                )
            )
            content_task = json.loads(
                (tasks_dir / "task_2026-09-13_content.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(["workflow-ops"], [i["id"] for i in ops_task["issues"]])
        self.assertEqual(
            ["workflow-content"], [i["id"] for i in content_task["issues"]]
        )

    def test_quality_dispatch_preserves_existing_site_health_task(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tasks_dir = Path(temp_dir)
            task_path = tasks_dir / "task_2026-09-13_content.json"
            task_path.write_text(
                json.dumps(
                    {
                        "task_id": "task_2026-09-13_content",
                        "agent": "content",
                        "status": "pending",
                        "issues": [
                            {
                                "id": "site-1",
                                "type": "persona_violation",
                                "severity": "high",
                                "agent": "content",
                                "status": "new",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            enqueue_issues(
                [
                    {
                        "id": "quality-1",
                        "type": "mojibake",
                        "severity": "P0",
                        "owner": "content",
                        "page": "broken.md",
                    }
                ],
                task_source="quality_gate",
                target_date="2026-09-13",
                tasks_dir=tasks_dir,
            )
            task = json.loads(task_path.read_text(encoding="utf-8"))

        self.assertEqual(2, task["issue_count"])
        self.assertEqual(
            {"site-1", "quality-1"},
            {issue["id"] for issue in task["issues"]},
        )

    def test_frontend_and_ops_handlers_mark_manual_work(self):
        task = {
            "issues": [
                {
                    "type": "visual_quality_failed",
                    "page": "/example/",
                    "recommended_action": "Fix layout.",
                }
            ]
        }
        self.assertEqual(1, execute_frontend(task)["need_manual"])
        self.assertEqual(1, execute_ops(task)["need_manual"])

    def test_ops_resolves_workflow_guard_when_guard_already_exists(self):
        task = {
            "target_date": "2026-09-13",
            "issues": [
                {
                    "id": "guard-1",
                    "type": "workflow_missing_guard",
                    "page": ".github/workflows/monthly-ebook-update.yml",
                    "file": ".github/workflows/monthly-ebook-update.yml",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            workflow = (
                Path(temp_dir)
                / ".github"
                / "workflows"
                / "monthly-ebook-update.yml"
            )
            workflow.parent.mkdir(parents=True)
            workflow.write_text(
                'name: "Guard: truncate long titles"\n',
                encoding="utf-8",
            )
            with mock.patch.object(agent_task_executor, "BASE_DIR", Path(temp_dir)):
                results = execute_ops(task, dry_run=True)

        self.assertEqual(1, results["resolved"])
        self.assertEqual(0, results["need_manual"])

    def test_legacy_daily_issues_are_migrated_without_duplicates(self):
        legacy_issue = {
            "id": "issue_legacy",
            "type": "title_too_long",
            "severity": "medium",
            "agent": "seo",
            "description": "Legacy issue",
            "action": "optimize_title",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            tasks_dir = Path(temp_dir)
            task_path = tasks_dir / "task_2026-09-13_seo.json"
            task_path.write_text(
                json.dumps(
                    {
                        "task_id": "task_2026-09-13_seo",
                        "agent": "seo",
                        "status": "completed",
                        "issues": [legacy_issue],
                    }
                ),
                encoding="utf-8",
            )
            enqueue_issues(
                [
                    {
                        **legacy_issue,
                        "severity": "medium",
                    }
                ],
                task_source="daily_issue_router",
                target_date="2026-09-13",
                tasks_dir=tasks_dir,
            )
            task = json.loads(task_path.read_text(encoding="utf-8"))

        ids = [issue["id"] for issue in task["issues"]]
        self.assertEqual(["issue_legacy"], ids)
        self.assertEqual("daily_issue_router", task["issues"][0]["task_source"])
        self.assertEqual("pending", task["status"])

    def test_resolved_legacy_daily_issue_is_cleared(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tasks_dir = Path(temp_dir)
            task_path = tasks_dir / "task_2026-09-13_content.json"
            task_path.write_text(
                json.dumps(
                    {
                        "task_id": "task_2026-09-13_content",
                        "agent": "content",
                        "status": "pending",
                        "issues": [
                            {
                                "id": "issue_resolved",
                                "type": "content_placeholder",
                                "severity": "high",
                                "agent": "content",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            enqueue_issues(
                [],
                task_source="daily_issue_router",
                target_date="2026-09-13",
                tasks_dir=tasks_dir,
            )
            task = json.loads(task_path.read_text(encoding="utf-8"))

        self.assertEqual(0, task["issue_count"])
        self.assertEqual([], task["issues"])
        self.assertEqual("completed", task["status"])


if __name__ == "__main__":
    unittest.main()
