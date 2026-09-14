import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from site_visual_audit import sitemap_pages  # noqa: E402


SITEMAP = b"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://www.chinaboundtravel.com/</loc></url>
  <url><loc>https://www.chinaboundtravel.com/posts/example/</loc></url>
</urlset>
"""


class SiteVisualAuditTests(unittest.TestCase):
    def test_local_audit_rewrites_canonical_sitemap_urls_to_local_server(self):
        response = mock.Mock()
        response.content = SITEMAP
        with mock.patch("site_visual_audit.requests.get", return_value=response):
            pages = sitemap_pages("http://127.0.0.1:8765", 5, 10)
        self.assertIn("http://127.0.0.1:8765/posts/example/", pages)
        self.assertFalse(any(page.startswith("https://www.chinaboundtravel.com") for page in pages))

    def test_production_audit_keeps_sitemap_urls(self):
        response = mock.Mock()
        response.content = SITEMAP
        with mock.patch("site_visual_audit.requests.get", return_value=response):
            pages = sitemap_pages("https://www.chinaboundtravel.com", 5, 10)
        self.assertIn("https://www.chinaboundtravel.com/posts/example/", pages)


if __name__ == "__main__":
    unittest.main()
