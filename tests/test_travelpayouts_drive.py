"""P1-GROWTH-10A: Travelpayouts Drive installation tests.

Verifies:
1. Drive script exists in the shared head partial
2. exact source URL exists (emrldtp.com/NTMxNDY5.js?t=531469)
3. source appears exactly once in rendered homepage
4. source appears exactly once in rendered articles
5. no duplicate Drive script anywhere in the build
6. affiliate URLs unchanged (hugo.toml markers + template-driven hrefs)
7. content_id unchanged (posts untouched)
"""
import re
import subprocess
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
HEAD_PARTIAL = REPO / "layouts" / "partials" / "head.html"
HUGO_TOML = (REPO / "hugo.toml").read_text(encoding="utf-8")
SINGLE_HTML = (REPO / "layouts" / "_default" / "single.html").read_text(encoding="utf-8", errors="replace")

DRIVE_URL = "emrldtp.com/NTMxNDY5.js?t=531469"
DRIVE_PAT = re.compile(re.escape(DRIVE_URL))


@pytest.fixture(scope="module")
def built_site():
    out = Path(tempfile.mkdtemp(prefix="hugo_drive_"))
    proc = subprocess.run(
        ["hugo", "--gc", "--minify", "--destination", str(out)],
        cwd=str(REPO), capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, proc.stderr[-1500:]
    return out


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Source template
# ---------------------------------------------------------------------------
def test_drive_script_exists_in_head_partial():
    text = _read(HEAD_PARTIAL)
    assert DRIVE_URL in text
    assert "nowprocket" in text
    assert "data-cfasync" in text
    assert "data-no-defer" in text


def test_drive_script_installed_exactly_once_in_partial():
    text = _read(HEAD_PARTIAL)
    assert len(DRIVE_PAT.findall(text)) == 1


def test_drive_script_keeps_async_and_attributes():
    text = _read(HEAD_PARTIAL)
    assert "script.async = 1" in text
    assert "setAttribute(\"data-cmp-ab\",\"2\")" in text
    # no defer / preload / rewrite directives added
    assert "defer" not in text.split("Travelpayouts Drive (P1-GROWTH-10A)")[1][:400].lower().replace("no-defer", "")


# ---------------------------------------------------------------------------
# Rendered output
# ---------------------------------------------------------------------------
def test_homepage_has_drive_once(built_site):
    html = _read(built_site / "index.html")
    assert DRIVE_URL in html
    assert len(DRIVE_PAT.findall(html)) == 1


def test_article_has_drive_once(built_site):
    html = _read(built_site / "posts" / "144-hour-visa-free-transit-guide" / "index.html")
    assert len(DRIVE_PAT.findall(html)) == 1


def test_other_pages_have_drive_once(built_site):
    for rel in ("about/index.html", "pricing/index.html", "cities/index.html"):
        html = _read(built_site / rel)
        assert len(DRIVE_PAT.findall(html)) == 1, rel


def test_no_duplicate_drive_in_build(built_site):
    """Every baseof-rendered page (has GA4 from the shared head partial)
    must have exactly one Drive occurrence.
    Hugo alias redirect stubs (meta refresh) use a minimal standalone
    HTML and are intentionally excluded - visitors are forwarded to the
    final page which carries the site-wide head."""
    bad, skipped = [], 0
    for html_file in built_site.rglob("*.html"):
        text = _read(html_file)
        if "G-GECBME3YVJ" not in text:
            # non-baseof pages (alias redirect stubs, static downloads)
            skipped += 1
            continue
        n = len(DRIVE_PAT.findall(text))
        if n != 1:
            bad.append((html_file.relative_to(built_site).as_posix(), n))
    assert not bad, "pages with != 1 Drive occurrence: %s" % bad[:10]
    assert skipped > 0, "expected to skip at least one non-baseof page"

# ---------------------------------------------------------------------------
# Regression: affiliate URLs / content untouched
# ---------------------------------------------------------------------------
def test_affiliate_urls_unchanged():
    for marker in ("aid=730795", "aff_id=150687", "klook.tpo.li",
                   "safetywing.com/nomad-insurance?referenceID=26548976",
                   "www.aviasales.com/?marker=730795"):
        assert marker in HUGO_TOML


def test_single_html_still_template_driven():
    for key in ("esim", "vpn", "hotel", "klook"):
        assert "{{{{ .Site.Params.affiliate.{key} }}}}".format(key=key) in SINGLE_HTML
    assert "affiliate_click" in SINGLE_HTML


def test_no_content_or_affiliate_files_touched():
    """This round may only touch layouts/partials/head.html + tests/reports."""
    proc = subprocess.run(["git", "status", "--short", "--", "content/"], cwd=str(REPO),
                          capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0
    assert proc.stdout.strip() == "", f"content/ has unexpected changes:\n{proc.stdout}"
    proc2 = subprocess.run(["git", "status", "--short", "--", "hugo.toml"], cwd=str(REPO),
                           capture_output=True, text=True, encoding="utf-8")
    assert proc2.stdout.strip() == "", "hugo.toml changed unexpectedly"
