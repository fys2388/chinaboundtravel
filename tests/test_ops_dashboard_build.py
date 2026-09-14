import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class OpsDashboardBuildTests(unittest.TestCase):
    def test_task_agents_and_execution_counts_are_rendered(self):
        temp_root = ROOT / ".pytest_tmp"
        temp_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temp_root) as temp_dir:
            build_dir = Path(temp_dir) / "ops-dashboard"
            build_dir.mkdir()
            shutil.copy(ROOT / "ops-dashboard" / "build.py", build_dir / "build.py")
            data = json.loads(
                (ROOT / "ops-dashboard" / "dashboard_data.json").read_text(
                    encoding="utf-8"
                )
            )
            data["agent_execution"] = {
                "date": "2026-09-13",
                "is_today": True,
                "total_fixed": 3,
                "total_issues": 5,
                "manual_review": 1,
                "failed": 1,
                "in_progress": 0,
                "agents": {
                    "frontend": {
                        "total": 2,
                        "fixed": 0,
                        "failed": 0,
                        "manual_review": 1,
                        "in_progress": 0,
                        "last_run": "2026-09-13T10:00:00+08:00",
                    },
                    "ops": {
                        "total": 1,
                        "fixed": 0,
                        "failed": 1,
                        "manual_review": 0,
                        "in_progress": 0,
                        "last_run": "2026-09-13T10:05:00+08:00",
                    },
                },
            }
            (build_dir / "dashboard_data.json").write_text(
                json.dumps(data, ensure_ascii=False),
                encoding="utf-8",
            )

            result = subprocess.run(
                [sys.executable, str(build_dir / "build.py")],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            html = (build_dir / "index.html").read_text(encoding="utf-8")

        self.assertIn("Frontend Agent", html)
        self.assertIn("Ops Agent", html)
        self.assertIn("今日任务 2", html)
        self.assertIn("待人工 1", html)


if __name__ == "__main__":
    unittest.main()
