"""P1-GROWTH-28A: 全站 OG / Twitter Card 标签测试。

Covers:
1. head partial includes opengraph + twitter_cards templates
2. OG template declares the required properties at 1200x630
3. Twitter template declares required names + summary_large_image
4. Rendered homepage carries full OG/Twitter sets with the default image
5. Rendered article page uses its cover as og:image (not the fallback)
6. scripts/audit_og_tags.py exits 0 on the built site (no missing tags)

Pure/deterministic; the only subprocess is the local Hugo build.
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
HEAD_PARTIAL = REPO / "layouts" / "partials" / "head.html"
OG_PARTIAL = REPO / "layouts" / "partials" / "templates" / "opengraph.html"
TW_PARTIAL = REPO / "layouts" / "partials" / "templates" / "twitter_cards.html"
AUDIT_SCRIPT = REPO / "scripts" / "audit_og_tags.py"

OG_PROPS = ("og:title", "og:description", "og:image", "og:url", "og:type",
            "og:image:width", "og:image:height", "og:site_name")
TW_NAMES = ("twitter:card", "twitter:title", "twitter:description", "twitter:image")


@pytest.fixture(scope="module")
def built_site():
    out = Path(tempfile.mkdtemp(prefix="hugo_og_test_"))
    proc = subprocess.run(
        ["hugo", "--gc", "--minify", "--destination", str(out)],
        cwd=str(REPO), capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, proc.stderr[-1500:]
    return out


def test_head_includes_og_and_twitter_partials():
    text = HEAD_PARTIAL.read_text(encoding="utf-8", errors="replace")
    assert "templates/opengraph.html" in text
    assert "templates/twitter_cards.html" in text


def test_og_template_required_tags_and_dimensions():
    text = OG_PARTIAL.read_text(encoding="utf-8", errors="replace")
    for prop in OG_PROPS:
        assert prop in text, prop
    assert 'content="1200"' in text
    assert 'content="630"' in text


def test_twitter_template_required_tags():
    text = TW_PARTIAL.read_text(encoding="utf-8", errors="replace")
    for name in TW_NAMES:
        assert name in text, name
    assert 'content="summary_large_image"' in text


def test_homepage_has_full_og_and_twitter(built_site):
    html = (built_site / "index.html").read_text(encoding="utf-8", errors="replace")
    for prop in OG_PROPS:
        assert prop in html, prop
    for name in TW_NAMES:
        assert name in html, name
    assert "og-default.jpg" in html
    assert 'og:image:width' in html and 'content="1200"' in html
    assert 'og:image:height' in html and 'content="630"' in html


def test_article_uses_cover_as_og_image(built_site):
    html = (built_site / "posts" / "144-hour-visa-free-transit-guide" / "index.html").read_text(
        encoding="utf-8", errors="replace")
    m = re.search(r'property=["\']?og:image["\']?\s+content="([^"]+)"', html)
    assert m, "og:image missing on article page"
    assert "og-default.jpg" not in m.group(1), "article should use its cover, not the default fallback"
    assert "twitter:image" in html and "twitter:card" in html


def test_og_audit_script_passes(built_site):
    proc = subprocess.run(
        [sys.executable, str(AUDIT_SCRIPT), "--source", str(built_site)],
        cwd=str(REPO), capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, f"OG audit failed:\n{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}"
    assert "failed=0" in proc.stdout
