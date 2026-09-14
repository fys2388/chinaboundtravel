import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from auto_error_router import (  # noqa: E402
    ERROR_ROUTES,
    classify_error_extended,
    extract_error_evidence,
    run_gh,
)
import content_quality_validator  # noqa: E402
from content_quality_validator import validate_article  # noqa: E402
from error_handler import ErrorHandler  # noqa: E402


CONTENT_AUDIT_LOG = """
content-quality-audit\tUNKNOWN STEP\t2026-09-13T07:05:20.3240207Z Traceback (most recent call last):
content-quality-audit\tUNKNOWN STEP\t2026-09-13T07:05:20.3544930Z KeyError: 'mojibake'
content-quality-audit\tUNKNOWN STEP\t2026-09-13T07:05:20.3591228Z ##[error]Process completed with exit code 1.
content-quality-audit\tComplete job\t2026-09-13T07:05:24.2935804Z Cleaning up orphan processes
content-quality-audit\tComplete job\t2026-09-13T07:05:24.3264809Z ##[warning]Node.js 20 is deprecated.
"""

VISUAL_AUDIT_LOG = """
post-deploy\t2.0 Pre-deploy Quality Gate (P0/P1 blocker)\tvisual quality: pages=12 P0=6 P1=43 P2=12
post-deploy\t2.0 Pre-deploy Quality Gate (P0/P1 blocker)\twrote reports/quality/visual_audit.json
post-deploy\t2.0 Pre-deploy Quality Gate (P0/P1 blocker)\t##[error]Process completed with exit code 1.
post-deploy\tComplete job\tCleaning up orphan processes
"""


class AutoErrorRouterTests(unittest.TestCase):
    @mock.patch("auto_error_router.subprocess.run")
    def test_gh_output_is_decoded_as_utf8_with_replacement(self, run_mock):
        run_mock.return_value = subprocess.CompletedProcess(
            ["gh"], 0, stdout="ok", stderr=""
        )
        run_gh(["run", "view", "1"])
        kwargs = run_mock.call_args.kwargs
        self.assertEqual("utf-8", kwargs["encoding"])
        self.assertEqual("replace", kwargs["errors"])

    def test_content_report_crash_is_not_permission_error(self):
        category = classify_error_extended(CONTENT_AUDIT_LOG)
        self.assertEqual("content_audit_script_error", category)
        self.assertEqual("content", ERROR_ROUTES[category]["agent"])

    def test_content_quality_gate_is_assigned_to_content(self):
        log = "::error::内容质量门禁失败，失败项: 内容质量验证(P0乱码)"
        category = classify_error_extended(log)
        self.assertEqual("content_quality_p0", category)
        self.assertEqual("content", ERROR_ROUTES[category]["agent"])

    def test_fact_failure_is_not_masked_by_aggregate_gate(self):
        log = (
            "::error::内容事实检查发现问题，exit code=1\n"
            "::error::内容质量门禁失败，失败项: 内容事实检查"
        )
        self.assertEqual("fact_guard_failed", classify_error_extended(log))

    def test_echoed_workflow_source_does_not_create_false_failure(self):
        log = """
        echo "::error::内容事实检查发现问题，exit code=$FACT_EXIT"
        echo "::error::品牌审计发现旧人设表述，exit code=$BRAND_EXIT"
        ::error::内容ID审计失败，存在缺失或重复的content_id
        """
        self.assertEqual("content_id_error", classify_error_extended(log))

    def test_visual_quality_failure_is_assigned_to_frontend(self):
        category = classify_error_extended(VISUAL_AUDIT_LOG)
        self.assertEqual("visual_quality_failed", category)
        self.assertEqual("frontend", ERROR_ROUTES[category]["agent"])

    def test_evidence_excludes_ci_cleanup_noise(self):
        evidence = "\n".join(extract_error_evidence(CONTENT_AUDIT_LOG))
        self.assertIn("KeyError: 'mojibake'", evidence)
        self.assertNotIn("Cleaning up orphan processes", evidence)
        self.assertNotIn("Node.js 20 is deprecated", evidence)

    def test_bare_403_is_not_permission_error(self):
        log = "Fetching https://example.com/403 then process completed with exit code 1"
        self.assertEqual("unknown", classify_error_extended(log))

    def test_explicit_forbidden_is_permission_error(self):
        log = "fatal: unable to access repository: HTTP 403 Forbidden"
        self.assertEqual("permission_denied", classify_error_extended(log))

    def test_remote_rejection_is_git_push_failure(self):
        log = "! [remote rejected] main -> main (fetch first)"
        self.assertEqual("git_push_failed", classify_error_extended(log))

    def test_predeploy_quality_failure_has_frontend_owner(self):
        log = "predeploy quality: pages=68 P0=0 P1=1 P2=0"
        category = classify_error_extended(log)
        self.assertEqual("predeploy_quality_failed", category)
        self.assertEqual("frontend", ERROR_ROUTES[category]["agent"])

    def test_error_handler_ignores_cleanup_context(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            handler = ErrorHandler(temp_dir)
            log = (
                "git config --local --name-only --get-regexp remote.origin.url\n"
                "Node.js 20 is deprecated\n"
                "Cleaning up orphan processes"
            )
            self.assertEqual("unknown", handler.classify_error(log))

    def test_invalid_frontmatter_result_has_complete_score_schema(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "broken.md"
            path.write_bytes(b"\xc3\xa2\xc2\x80\xc2\x94")
            result = validate_article(path)
        self.assertIn("mojibake", result["scores"])
        self.assertIn("media", result["scores"])
        self.assertFalse(result["passed"])
        self.assertTrue(result["mojibake_issues"])

    def test_json_mode_returns_failure_when_any_article_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "broken.md"
            path.write_bytes(b"\xc3\xa2\xc2\x80\xc2\x94")
            stdout = io.StringIO()
            with mock.patch.object(content_quality_validator, "POSTS_DIR", Path(temp_dir)):
                with mock.patch.object(sys, "argv", ["validator", "--json"]):
                    with contextlib.redirect_stdout(stdout):
                        exit_code = content_quality_validator.main()
        self.assertEqual(1, exit_code)
        self.assertIn('"passed_count": 0', stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
