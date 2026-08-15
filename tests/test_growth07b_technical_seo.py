"""P1-GROWTH-07B: technical SEO regression tests.

Verifies:
1. rail page renders at its canonical slug URL (real content, not a redirect stub)
2. rail page is indexable (no noindex)
3. rail canonical = self
4. transportation guide still renders (200-equivalent, real content)
5. transportation guide canonical unchanged (self)
6. FAQPage JSON-LD is emitted and valid when a real FAQ section exists
7. no FAQPage when FAQ absent
8. no duplicate FAQPage anywhere in the build
9. content_id unchanged for both pages
10. affiliate URLs / UTM unchanged
plus: dated rail URL still 301 -> final rail page (static/_redirects)
"""
import json
import re
import subprocess
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
POSTS = REPO / "content" / "posts"
SITE = "https://www.chinaboundtravel.com"
RAIL_SLUG = "/posts/china-high-speed-rail-how-to-book-tickets/"
GUIDE_SLUG = "/posts/china-transportation-complete-guide-trains-subways-taxis-and-more/"

RAIL = "content/posts/2026-05-25-china-high-speed-rail-how-to-book-tickets.md"
GUIDE = "content/posts/2026-07-16-china-transportation-complete-guide-trains-subways-taxis-and-more.md"

FAQ_PAGES = {
    "posts/china-high-speed-rail-how-to-book-tickets/index.html",
    "posts/how-to-use-wechat-pay-as-a-foreigner/index.html",
    "posts/wechat-pay-for-foreigners-step-by-step-setup-and-common-mistakes-to-avoid-guide/index.html",
    "posts/zhangjiajie-avatar-mountains-complete-guide-to-chinas-most-spectacular-park/index.html",
}
NO_FAQ_PAGE = "posts/best-travel-insurance-china/index.html"


def _fm(text, key):
    fm = text.split("---", 2)[1]
    m = re.search(r"^\s*" + re.escape(key) + r"\s*[:=]\s*(.+)$", fm, re.M)
    if not m:
        return None
    val = m.group(1).strip()
    if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
        val = val[1:-1]
    return val


def _read(name):
    return (REPO / name).read_text(encoding="utf-8", errors="ignore")


@pytest.fixture(scope="module")
def built_site():
    out = Path(tempfile.mkdtemp(prefix="hugo_g07b_"))
    proc = subprocess.run(
        ["hugo", "--gc", "--minify", "--destination", str(out)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    return out


def _page_html(built_site, rel):
    p = built_site / rel
    assert p.exists(), f"missing rendered page: {rel}"
    return p.read_text(encoding="utf-8", errors="replace")


def _ldjson_blocks(html):
    return re.findall(r'<script type=application/ld\+json>(.*?)</script>', html, re.S)


# ---------------------------------------------------------------------------
# rail page: 200-equivalent, indexable, self canonical, real content
# ---------------------------------------------------------------------------
def test_rail_page_renders_at_slug(built_site):
    html = _page_html(built_site, "posts/china-high-speed-rail-how-to-book-tickets/index.html")
    assert len(html) > 10000, "rail page looks like a redirect stub"
    assert "The Quick Answer" in html


def test_rail_page_indexable(built_site):
    html = _page_html(built_site, "posts/china-high-speed-rail-how-to-book-tickets/index.html")
    assert "noindex" not in html.lower()


def test_rail_canonical_is_self(built_site):
    html = _page_html(built_site, "posts/china-high-speed-rail-how-to-book-tickets/index.html")
    m = re.search(r'<link rel=canonical href=([^>]+)>', html)
    assert m, "no canonical link"
    assert SITE + RAIL_SLUG.rstrip("/") in m.group(1), m.group(1)


def test_rail_slug_declared_in_frontmatter():
    text = _read(RAIL)
    assert _fm(text, "slug") == RAIL_SLUG.strip("/").split("/")[-1]
    assert _fm(text, "canonicalURL") == SITE + RAIL_SLUG


# ---------------------------------------------------------------------------
# transportation guide regression
# ---------------------------------------------------------------------------
def test_guide_renders_and_indexable(built_site):
    html = _page_html(built_site, "posts/china-transportation-complete-guide-trains-subways-taxis-and-more/index.html")
    assert len(html) > 10000
    assert "noindex" not in html.lower()


def test_guide_canonical_unchanged(built_site):
    html = _page_html(built_site, "posts/china-transportation-complete-guide-trains-subways-taxis-and-more/index.html")
    m = re.search(r'<link rel=canonical href=([^>]+)>', html)
    assert m
    assert SITE + GUIDE_SLUG.rstrip("/") in m.group(1), m.group(1)


def test_guide_no_longer_claims_rail_alias():
    text = _read(GUIDE)
    assert RAIL_SLUG not in text, "guide still aliases the rail page URL"


# ---------------------------------------------------------------------------
# dated URL still 301s to the final rail page
# ---------------------------------------------------------------------------
def test_dated_rail_url_redirects_to_slug():
    redirects = (REPO / "static" / "_redirects").read_text(encoding="utf-8", errors="ignore")
    assert "/posts/2026-05-25-china-high-speed-rail-how-to-book-tickets/ " + RAIL_SLUG + " 301" in redirects


# ---------------------------------------------------------------------------
# FAQPage JSON-LD
# ---------------------------------------------------------------------------
def test_faqpage_emitted_when_faq_exists(built_site):
    for rel in sorted(FAQ_PAGES):
        html = _page_html(built_site, rel)
        blocks = _ldjson_blocks(html)
        faq = [b for b in blocks if '"@type":"FAQPage"' in b]
        assert len(faq) == 1, f"{rel}: expected exactly 1 FAQPage, got {len(faq)}"
        data = json.loads(faq[0])
        assert data["@type"] == "FAQPage"
        assert len(data["mainEntity"]) >= 1, f"{rel}: FAQPage with empty mainEntity"


def test_no_faqpage_when_no_faq(built_site):
    html = _page_html(built_site, NO_FAQ_PAGE)
    assert '"@type":"FAQPage"' not in html


def test_no_duplicate_faqpage_sitewide(built_site):
    dup = []
    for p in (built_site / "posts").rglob("index.html"):
        html = p.read_text(encoding="utf-8", errors="replace")
        n = html.count('"@type":"FAQPage"')
        if n > 1:
            dup.append(str(p))
    assert not dup, dup


# ---------------------------------------------------------------------------
# content_id / affiliate unchanged vs HEAD
# ---------------------------------------------------------------------------
def test_content_id_and_canonical_unchanged():
    for rel in (RAIL, GUIDE):
        old = subprocess.run(["git", "show", "HEAD:" + rel], cwd=str(REPO),
                             capture_output=True, text=True, encoding="utf-8")
        assert old.returncode == 0, old.stderr
        old_text, new_text = old.stdout, _read(rel)
        assert _fm(old_text, "content_id") == _fm(new_text, "content_id"), rel
        assert _fm(old_text, "canonicalURL") == _fm(new_text, "canonicalURL"), rel
        if _fm(old_text, "slug") is not None:
            assert _fm(old_text, "slug") == _fm(new_text, "slug"), rel


def test_affiliate_urls_utm_unchanged():
    pat = re.compile(r"\{\{<[^>]+>\}\}|https?://[^\s)\]]+|utm_[a-z]+=[^&\s)\]]+", re.I)
    for rel in (RAIL, GUIDE):
        old = subprocess.run(["git", "show", "HEAD:" + rel], cwd=str(REPO),
                             capture_output=True, text=True, encoding="utf-8")
        assert old.returncode == 0, old.stderr
        old_tokens = sorted(pat.findall(old.stdout))
        new_tokens = sorted(pat.findall(_read(rel)))
        assert old_tokens == new_tokens, rel
