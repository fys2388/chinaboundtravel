"""P1-GROWTH-12B: FIRST AFFILIATE CTA EXPERIMENT (REV001) tests.

Verifies (pure, deterministic, no network):
1. CTA exists exactly once (source + rendered)
2. placement ID correct (food-delivery-mid-content)
3. partner valid (esim -> existing hugo.toml key)
4. destination unchanged (hugo.toml esim URL, byte-identical vs HEAD)
5. UTM unchanged (affiliate section byte-identical vs HEAD)
6. content_id unchanged
7. URL unchanged (rendered path exists)
8. canonical unchanged
9. title/description unchanged
10. Drive script unchanged (still exactly once)
11. no forbidden persona in CTA copy
12. no duplicate CTA block
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
from persona_guard import PersonaGuard  # noqa: E402

POST = REPO / "content" / "posts" / "2026-05-28-chinese-food-delivery-meituan-eleme-guide.md"
HEAD = REPO / "layouts" / "partials" / "head.html"
HUGO_TOML = REPO / "hugo.toml"
SINGLE = REPO / "layouts" / "_default" / "single.html"

CONTENT_ID = "cbt-e464169c4991"
CANONICAL = "https://www.chinaboundtravel.com/posts/chinese-food-delivery-meituan-eleme-guide/"
SLUG = "chinese-food-delivery-meituan-eleme-guide"
PLACEMENT = "food-delivery-mid-content"
PARTNER = "esim"
DRIVE_URL = "emrldtp.com/NTMxNDY5.js?t=531469"

POST_TEXT = POST.read_text(encoding="utf-8")
HEAD_TEXT = HEAD.read_text(encoding="utf-8", errors="replace")
TOML_NEW = HUGO_TOML.read_text(encoding="utf-8")
SINGLE_TEXT = SINGLE.read_text(encoding="gbk", errors="replace")


def _aff_section(t):
    start = t.find("[params.affiliate]")
    assert start >= 0, "affiliate section missing"
    end = t.find("\n[", start + 10)
    return t[start:end if end > 0 else len(t)]


def _fm(text, key):
    m = re.search(r"^\s*" + re.escape(key) + r"\s*[:=]\s*(.+)$", text.split("---", 2)[1], re.M)
    if not m:
        return None
    val = m.group(1).strip()
    if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
        val = val[1:-1]
    return val


@pytest.fixture(scope="module")
def built_site():
    out = Path(tempfile.mkdtemp(prefix="hugo_g12b_"))
    proc = subprocess.run(
        ["hugo", "--gc", "--minify", "--destination", str(out)],
        cwd=str(REPO), capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, proc.stderr[-1500:]
    return out


def rendered(built_site) -> str:
    return (built_site / "posts" / SLUG / "index.html").read_text(encoding="utf-8", errors="replace")
# ---------------------------------------------------------------------------
# 1-2, 12: CTA presence / uniqueness / placement
# ---------------------------------------------------------------------------
def test_cta_exists_exactly_once_in_source():
    assert POST_TEXT.count(PLACEMENT) == 1


def test_cta_block_exists_exactly_once_in_source():
    assert POST_TEXT.count("{{< affiliate-mid-cta") == 1
    assert POST_TEXT.count("{{< /affiliate-mid-cta >}}") == 1


def test_cta_rendered_once(built_site):
    html = rendered(built_site)
    assert html.count("affiliate-mid-cta affiliate-block") == 1
    assert html.count(PLACEMENT) == 1


def test_placement_id_correct():
    assert 'placement="' + PLACEMENT + '"' in POST_TEXT


# ---------------------------------------------------------------------------
# 3-5: partner / destination / UTM
# ---------------------------------------------------------------------------
def test_partner_valid():
    m = re.search(r'partner="([^"]+)"', POST_TEXT)
    assert m and m.group(1) == PARTNER
    assert PARTNER + " =" in _aff_section(TOML_NEW)


def test_destination_unchanged_vs_head():
    old = subprocess.run(["git", "show", "HEAD:hugo.toml"], cwd=str(REPO),
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert old.returncode == 0
    assert _aff_section(old.stdout) == _aff_section(TOML_NEW), "affiliate config changed"


def test_destination_rendered(built_site):
    html = rendered(built_site)
    m = re.search(
        r'<a href=([^ >]+) class=affiliate-link target=_blank rel="nofollow sponsored"'
        r" data-affiliate-partner=esim data-affiliate-placement=food-delivery-mid-content", html)
    assert m, "mid CTA link not rendered"
    expected = re.search(r'^\s*esim = "(.*)"$', _aff_section(TOML_NEW), re.M).group(1)
    assert m.group(1) == expected


def test_utm_unchanged_vs_head():
    old = subprocess.run(["git", "show", "HEAD:hugo.toml"], cwd=str(REPO),
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    pat = re.compile(r"utm_[a-z]+=[^&\s\"]+", re.I)
    assert sorted(pat.findall(old.stdout)) == sorted(pat.findall(TOML_NEW))
# ---------------------------------------------------------------------------
# 6-9: SEO invariants
# ---------------------------------------------------------------------------
def test_content_id_title_canonical_unchanged():
    old = subprocess.run(
        ["git", "show", "HEAD:content/posts/2026-05-28-chinese-food-delivery-meituan-eleme-guide.md"],
        cwd=str(REPO), capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert old.returncode == 0
    for key in ("content_id", "title", "canonicalURL", "slug", "description"):
        assert _fm(old.stdout, key) == _fm(POST_TEXT, key), key
    assert _fm(POST_TEXT, "content_id") == CONTENT_ID
    assert _fm(POST_TEXT, "canonicalURL") == CANONICAL


def test_url_unchanged_rendered(built_site):
    assert (built_site / "posts" / SLUG / "index.html").exists()


# ---------------------------------------------------------------------------
# 10: Drive isolation
# ---------------------------------------------------------------------------
def test_drive_script_unchanged_once():
    assert HEAD_TEXT.count(DRIVE_URL) == 1


def test_drive_script_rendered_once(built_site):
    assert rendered(built_site).count(DRIVE_URL) == 1


# ---------------------------------------------------------------------------
# 11: persona / compliance on CTA copy
# ---------------------------------------------------------------------------
def test_cta_persona_guard():
    guard = PersonaGuard()
    seg = POST_TEXT[POST_TEXT.find(PLACEMENT) - 300: POST_TEXT.find(PLACEMENT) + 400]
    assert guard.check(seg) == []


def test_cta_no_forbidden_claims():
    seg = POST_TEXT[POST_TEXT.find(PLACEMENT) - 300: POST_TEXT.find(PLACEMENT) + 400]
    for phrase in ("my wife", "I lived in China", "I remember", "American expat",
                   "personally tested", "personally use", "5 years", "10 years",
                   "American in Chengdu", "limited time", "only today", "50% off", "best deal"):
        assert phrase.lower() not in seg.lower(), phrase


# ---------------------------------------------------------------------------
# tracking reuses existing affiliate_click event
# ---------------------------------------------------------------------------
def test_tracking_uses_existing_event():
    assert "affiliate_click" in SINGLE_TEXT
    assert "data-affiliate-partner" in SINGLE_TEXT
    assert "data-affiliate-placement" in SINGLE_TEXT
    assert "function send(link)" in SINGLE_TEXT
    assert "document.addEventListener('click'" in SINGLE_TEXT
