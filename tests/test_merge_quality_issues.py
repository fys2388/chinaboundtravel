import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from merge_quality_issues import load_source_issues  # noqa: E402


class MergeQualityIssuesTests(unittest.TestCase):
    def test_content_audit_failure_reaches_dashboard_data(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            audit_dir = root / "reports" / "content_audit"
            audit_dir.mkdir(parents=True)
            (audit_dir / "latest_quality_result.json").write_text(
                json.dumps(
                    {
                        "status": "failed",
                        "generated_at": "2026-09-13T07:05:00Z",
                        "run_id": "34744341694",
                        "checks": [
                            {
                                "id": "quality_validator",
                                "name": "内容质量验证(P0乱码)",
                                "script": "content_quality_validator.py",
                                "exit_code": 1,
                                "blocking": True,
                                "agent": "content",
                            }
                        ],
                        "content": {
                            "total": 63,
                            "passed_count": 61,
                            "mojibake_files": ["broken.md"],
                            "encoding_error_files": [],
                        },
                    }
                ),
                encoding="utf-8",
            )
            (audit_dir / "validator_output.json").write_text(
                json.dumps(
                    {
                        "results": [
                            {
                                "file": "broken.md",
                                "frontmatter_ok": False,
                                "content_id_ok": False,
                                "brand_issues": ["I stayed in China"],
                                "fact_issues": ["visa"],
                                "media_issues": [],
                                "seo_issues": ["missing_description"],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            issues, summary = load_source_issues(
                root, "2026-09-13T07:10:00Z"
            )

        content_summary = summary["content"]
        self.assertTrue(content_summary["available"])
        self.assertGreaterEqual(content_summary["P0"], 3)
        self.assertEqual(2, content_summary["P1"])
        self.assertEqual(1, content_summary["P2"])
        self.assertTrue(
            any(
                issue["id"] == "content-check-quality_validator-failed"
                and issue["severity"] == "P0"
                and issue["owner"] == "content"
                for issue in issues
            )
        )
        self.assertTrue(
            any(
                issue["type"] == "invalid_frontmatter"
                and issue["page"] == "broken.md"
                for issue in issues
            )
        )

    def test_missing_content_audit_is_marked_unavailable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            issues, summary = load_source_issues(
                Path(temp_dir), "2026-09-13T07:10:00Z"
            )

        self.assertEqual([], issues)
        self.assertEqual(
            {"available": False, "issues": 0},
            summary["content"],
        )


if __name__ == "__main__":
    unittest.main()
