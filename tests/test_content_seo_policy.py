import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from content_seo_policy import (  # noqa: E402
    TITLE_HARD_MAX,
    is_title_too_long,
    truncate_title,
)


class ContentSeoPolicyTests(unittest.TestCase):
    def test_title_limit_matches_rendered_template(self):
        self.assertEqual(60, TITLE_HARD_MAX)
        self.assertFalse(is_title_too_long("x" * 60))
        self.assertTrue(is_title_too_long("x" * 61))

    def test_truncate_title_avoids_partial_final_word(self):
        title = (
            "China Travel Guide: A Very Long Practical Planning Resource "
            "2026 Edition"
        )
        self.assertEqual(
            "China Travel Guide: A Very Long Practical Planning",
            truncate_title(title),
        )


if __name__ == "__main__":
    unittest.main()
