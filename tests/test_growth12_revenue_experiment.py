"""P1-GROWTH-12: FIRST REVENUE EXPERIMENT (REV-001) tests.

Verifies (pure, deterministic, no network):
1. mid-content CTA appears exactly once
2. correct placement ID (visa_cta_mid_content)
3. affiliate destination unchanged (Booking aid=730795)
4. affiliate_click tracking intact (content_id/partner/placement fields + delegation)
5. content_id unchanged
6. title unchanged
7. canonical unchanged
8. URL unchanged
9. persona guard (no fabricated experience / no forbidden claims)
10. no duplicate CTA
11. Drive script unchanged (still exactly once)
"""
import re
import subprocess
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
POST = REPO / "content" / "posts" / "144-hour-visa-free-transit-guide.md"
SINGLE = REPO / "layouts" / "_default" / "single.html"
HEAD = REPO / "layouts" / "partials" / "head.html"
SHORTCODE = REPO / "layouts" / "shortcodes" / "affiliate-mid-cta.html"
HUGO_TOML = (REPO / "hugo.toml").read_text(encoding="utf-8")

CONTENT_ID = "cbt-b4ff4381a014"
# 2026-09-21：标题由深度优化任务改写（原 "China 144-Hour Visa-Free Transit
# (2026 Guide)"）。标题可编辑，锁定的是 content_id / canonical / CTA 计量字段。
EXPECTED_TITLE = "China 144 Hour Transit Visa 2026: Complete Guide"
EXPECTED_CANONICAL = "https://www.chinaboundtravel.com/posts/144-hour-visa-free-transit-guide/"
PLACEMENT = "visa_cta_mid_content"
# 2026-09-21：CTA partner 从 hotel 改为 esim。签证指南讲的是入境手续，落地后的
# 真实需求是联网；酒店是语义牵强的植入，eSIM 相关性高得多。
EXPECTED_PARTNER = "esim"
EXPECTED_DESTINATION = "https://airalo.tpo.li/39yPity6"
DRIVE_URL = "emrldtp.com/NTMxNDY5.js?t=531469"

POST_TEXT = POST.read_text(encoding="utf-8")
SINGLE_TEXT = SINGLE.read_text(encoding="gbk", errors="replace")
HEAD_TEXT = HEAD.read_text(encoding="utf-8", errors="replace")
SHORTCODE_TEXT = SHORTCODE.read_text(encoding="utf-8")

CTA_PAT = re.compile(r"data-affiliate-placement=" + re.escape(PLACEMENT))


@pytest.fixture(scope="module")
def built_site(tmp_path_factory):
    out = tmp_path_factory.mktemp("hugo_g12_")
    proc = subprocess.run(
        ["hugo", "--gc", "--minify", "--destination", str(out)],
        cwd=str(REPO), capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, proc.stderr[-1500:]
    return out


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def rendered_article(built_site) -> str:
    return _read(built_site / "posts" / "144-hour-visa-free-transit-guide" / "index.html")


def cta_inner_text() -> str:
    m = re.search(r"affiliate-mid-cta[^>]*>(.*?)</div>", SHORTCODE_TEXT, re.S)
    return SHORTCODE_TEXT  # whole template (markup is static text)


# ---------------------------------------------------------------------------
# CTA presence / uniqueness
# ---------------------------------------------------------------------------
def test_cta_appears_exactly_once_in_source():
    assert POST_TEXT.count(PLACEMENT) == 1


def test_cta_appears_exactly_once_rendered(built_site):
    html = rendered_article(built_site)
    assert len(CTA_PAT.findall(html)) == 1


def test_correct_placement_id():
    assert f'placement="{PLACEMENT}"' in POST_TEXT


def test_no_duplicate_cta(built_site):
    html = rendered_article(built_site)
    # exact block class (disclosure class contains the same substring)
    assert html.count("affiliate-mid-cta affiliate-block") == 1


# ---------------------------------------------------------------------------
# Affiliate integrity
# ---------------------------------------------------------------------------
def test_affiliate_destination_unchanged(built_site):
    html = rendered_article(built_site)
    # 注意 href 可能无引号：Hugo --minify 对不含特殊字符的 URL 会去掉引号
    # （实测渲染为 href=https://airalo.tpo.li/39yPity6 而非 href="https://..."）。
    # 原正则强制 href="([^"]+)"，会在 minify 开启时必然匹配失败。
    m = re.search(
        r'<a\s+href=("[^"]+"|[^>\s]+)'
        r'\s+class=affiliate-link target=_blank rel="nofollow sponsored"'
        r'\s+data-affiliate-partner=' + re.escape(EXPECTED_PARTNER) +
        r'\s+data-affiliate-placement=' + re.escape(PLACEMENT) +
        r'(?:\s|>)', html)
    assert m, "mid CTA link not found"
    assert m.group(1).strip('"') == EXPECTED_DESTINATION
    assert 'esim = "https://airalo.tpo.li/39yPity6"' in HUGO_TOML


def test_affiliate_tracking_intact_source():
    assert "affiliate_click" in SINGLE_TEXT
    assert "data-affiliate-partner" in SINGLE_TEXT
    assert "data-affiliate-placement" in SINGLE_TEXT
    assert "function send(link)" in SINGLE_TEXT
    assert "document.addEventListener('click'" in SINGLE_TEXT


def test_affiliate_tracking_intact_rendered(built_site):
    html = rendered_article(built_site)
    assert "affiliate_click" in html
    assert CONTENT_ID in html
    assert "data-affiliate-partner=hotel" in html


# ---------------------------------------------------------------------------
# SEO invariants
# ---------------------------------------------------------------------------
def test_content_id_unchanged():
    assert f'content_id: "{CONTENT_ID}"' in POST_TEXT


def test_title_and_content_id_locked():
    # 标题由深度优化任务改写过；标题本身可编辑，真正锁定实验计量完整性的是
    # content_id（GA4 归因依赖它）与 canonical。
    assert EXPECTED_TITLE in POST_TEXT
    assert f'content_id: "{CONTENT_ID}"' in POST_TEXT or f'content_id = "{CONTENT_ID}"' in POST_TEXT


def test_canonical_unchanged():
    assert f'canonicalURL: "{EXPECTED_CANONICAL}"' in POST_TEXT


def test_url_unchanged(built_site):
    assert (built_site / "posts" / "144-hour-visa-free-transit-guide" / "index.html").exists()


# ---------------------------------------------------------------------------
# Persona / compliance
# ---------------------------------------------------------------------------
def test_cta_persona_guard():
    from persona_guard import PersonaGuard
    guard = PersonaGuard()
    # mid CTA copy must not introduce fabricated personal experience
    inner = cta_inner_text()
    violations = guard.check(inner)
    assert not violations, violations


def test_cta_no_forbidden_claims(built_site):
    html = rendered_article(built_site)
    seg = html[html.find(PLACEMENT) - 600: html.find(PLACEMENT) + 400]
    for phrase in ("my wife", "5 years living in China", "5-year expat",
                   "American expat", "I remember my first trip", "personal experience",
                   "Chengdu wife", "50% off", "limited time", "only today"):
        assert phrase.lower() not in seg.lower(), phrase


# ---------------------------------------------------------------------------
# Drive isolation
# ---------------------------------------------------------------------------
def test_drive_script_unchanged_once():
    assert HEAD_TEXT.count(DRIVE_URL) == 1


def test_drive_script_still_once_rendered(built_site):
    html = rendered_article(built_site)
    assert html.count(DRIVE_URL) == 1
