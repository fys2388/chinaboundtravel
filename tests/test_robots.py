"""V6-4: robots.txt regression tests.

Requires a Hugo build (no network, no deploy):
  - robots.txt exists at the site root (serves 200)
  - content is valid and references the correct sitemap
  - important pages are not blocked by obviously wrong Disallow rules
"""

import subprocess
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

SITEMAP_EXPECTED = "https://www.chinaboundtravel.com/sitemap.xml"


@pytest.fixture(scope="module")
def built_robots():
    out = Path(tempfile.mkdtemp(prefix="hugo_robots_"))
    try:
        proc = subprocess.run(
            ["hugo", "--gc", "--minify", "--destination", str(out)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("hugo unavailable")
    assert proc.returncode == 0, proc.stderr[-2000:]
    return out


def test_robots_txt_exists(built_robots):
    assert (built_robots / "robots.txt").exists(), "public/robots.txt not generated"


def test_robots_txt_valid(built_robots):
    text = (built_robots / "robots.txt").read_text(encoding="utf-8")
    assert "User-agent: *" in text
    assert "Allow: /" in text
    # sitemap reference must point to the canonical domain
    assert "Sitemap:" in text
    assert SITEMAP_EXPECTED in text, text


def test_robots_txt_sitemap_reference_correct(built_robots):
    text = (built_robots / "robots.txt").read_text(encoding="utf-8")
    sitemap_lines = [ln for ln in text.splitlines() if ln.lower().startswith("sitemap")]
    assert sitemap_lines, "missing Sitemap directive"
    assert any(SITEMAP_EXPECTED in ln for ln in sitemap_lines)


def test_robots_txt_does_not_block_important_pages(built_robots):
    text = (built_robots / "robots.txt").read_text(encoding="utf-8")
    # root must not be blocked and no obviously wrong disallow for core sections
    disallow_lines = {ln.strip() for ln in text.splitlines() if ln.strip().lower().startswith("disallow")}
    assert "Disallow: /" not in disallow_lines, "root blocked"
    for section in ("/posts", "/cities", "/visa", "/pricing", "/about"):
        assert not any(ln.lower().startswith(f"disallow: {section}") for ln in disallow_lines), \
            f"{section} wrongly blocked"
