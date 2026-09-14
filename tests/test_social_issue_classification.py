import json
import tempfile
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from daily_issue_router import classify_social_metrics  # noqa: E402
import social_reports  # noqa: E402


class SocialIssueClassificationTests(unittest.TestCase):
    def test_legacy_report_without_provenance_is_ops_issue(self):
        self.assertEqual(
            "social_analytics_unavailable",
            classify_social_metrics(
                {
                    "total_published": 4,
                    "total_impressions": 0,
                    "total_clicks": 0,
                }
            ),
        )

    def test_verified_zero_impressions_is_engagement_issue(self):
        self.assertEqual(
            "social_zero_engagement",
            classify_social_metrics(
                {
                    "total_published": 4,
                    "total_impressions": 0,
                    "total_clicks": 0,
                    "analytics_status": "ok",
                }
            ),
        )

    def test_verified_impressions_without_clicks_is_cta_issue(self):
        self.assertEqual(
            "social_no_traffic",
            classify_social_metrics(
                {
                    "total_published": 4,
                    "total_impressions": 200,
                    "total_clicks": 0,
                    "analytics_status": "ok",
                }
            ),
        )

    def test_healthy_metrics_have_no_issue(self):
        self.assertIsNone(
            classify_social_metrics(
                {
                    "total_published": 4,
                    "total_impressions": 200,
                    "total_clicks": 12,
                    "analytics_status": "ok",
                }
            )
        )

    def test_legacy_zero_impressions_without_metric_marker_is_not_trusted(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            analytics_dir = root / "data"
            analytics_dir.mkdir()
            payload = {
                "status": "ok",
                "metrics_available_count": 1,
                "posts": [
                    {
                        "platform": "x",
                        "published_at": "2026-09-12T08:00:00Z",
                        "metrics_available": True,
                        "impressions": 0,
                        "clicks": 0,
                    }
                ],
            }
            (analytics_dir / "analytics_2026-09-13.json").write_text(
                json.dumps(payload), encoding="utf-8"
            )
            with mock.patch.object(
                social_reports, "ANALYTICS_DIR", analytics_dir
            ), mock.patch.object(
                social_reports, "REAL_SOCIAL_DATA", root / "missing.json"
            ):
                self.assertIsNone(social_reports._load_analytics_snapshot())


if __name__ == "__main__":
    unittest.main()
