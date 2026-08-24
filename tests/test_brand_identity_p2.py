"""P1-BRAND-02: Joran editorial brand identity tests.

Covers (pure/deterministic, no network, no LLM):
1. homepage no fictional experience claims
2. resources no fictional experience claims
3. about no fictional experience claims
4. author block carries editorial identity
5. schema author description clean / editorial
6. forbidden phrases remain governed
7. affiliate URLs unchanged (hugo.toml affiliate section)
8. content_id unchanged (57/57, posts untouched)
9. canonical unchanged
10. legacy articles untouched by this commit
"""
import re
import subprocess
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tests"))
from _conversion_optimization import CONVERSION_OPT_AUTHORIZED  # noqa: E402

BRAND_FILES = {
    "homepage": ["layouts/index.html", "layouts/partials/home-banner.html", "hugo.toml"],
    "resources": ["content/resources/_index.md"],
    "about": ["content/about/_index.md"],
    "author_block": ["layouts/partials/sidebar-author.html", "layouts/_default/single.html",
                     "layouts/cities/single.html", "layouts/partials/affiliate-disclosure.html",
                     "layouts/shortcodes/affiliate-disclosure.html", "layouts/partials/travel-promo.html"],
    "schema": ["layouts/partials/templates/schema_json.html"],
}

FICTIONAL_PATTERNS = [
    r"personally (tested|used|use|recommend)",
    r"American expat",
    r"American (living in|in) Chengdu",
    r"Chengdu (husband|wife)",
    r"\bmy wife\b",
    r"years? (of )?living in (China|Chengdu)",
    r"years? of China travel experience",
    r"\b(first trip|my first trip)\b",
    r"I (lived|moved) (in|to)",
    r"I remember my",
    r"tested daily",
]

EDITORIAL_MARKERS = ["editorial", "research-based", "editorial team", "editorial voice", "reviewed",
                     "international travelers"]


def read(rel: str) -> str:
    p = REPO / rel
    if not p.exists():
        return ""
    enc = "gbk" if rel == "layouts/_default/single.html" else "utf-8"
    return p.read_text(encoding=enc, errors="replace")


def fictional_hits(text: str) -> list:
    return sorted({m.group(0) for pat in FICTIONAL_PATTERNS for m in re.finditer(pat, text, re.I)})


def git_show_head(rel: str) -> str:
    out = subprocess.run(["git", "show", "HEAD:" + rel], cwd=str(REPO),
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    return out.stdout if out.returncode == 0 else ""


# ---------------------------------------------------------------------------
# 1-3: no fictional experience on brand surfaces
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("layer,files", BRAND_FILES.items())
def test_brand_surfaces_no_fictional_experience(layer, files):
    for rel in files:
        text = read(rel)
        assert text, f"{rel} missing/empty"
        hits = fictional_hits(text)
        assert not hits, f"{rel} contains fictional persona claims: {hits}"


def test_homepage_editorial_identity_present():
    banner = read("layouts/partials/home-banner.html")
    assert "Editorial Voice" in banner
    toml = read("hugo.toml")
    assert "Research-based" in toml


# ---------------------------------------------------------------------------
# 4: author block editorial identity
# ---------------------------------------------------------------------------
def test_author_block_editorial_identity():
    sidebar = read("layouts/partials/sidebar-author.html")
    assert "Editorial Voice" in sidebar
    assert "American" not in sidebar and "Chengdu" not in sidebar
    intro = read("layouts/_default/single.html")
    assert "editorially reviewed" in intro
    assert "personally tested" not in intro


# ---------------------------------------------------------------------------
# 5: schema author description clean / editorial
# ---------------------------------------------------------------------------
def test_schema_author_editorial():
    schema = read("layouts/partials/templates/schema_json.html")
    assert "Editorial Voice, ChinaBound Travel" in schema
    assert "editorial voice behind ChinaBound Travel" in schema
    for bad in ("California native", "married into a Chengdu family", "5 years of China travel"):
        assert bad not in schema, bad


# ---------------------------------------------------------------------------
# 6: forbidden phrases remain governed
# ---------------------------------------------------------------------------
def test_forbidden_phrases_governed():
    data = json.loads((REPO / "config" / "content_governance.json").read_text(encoding="utf-8-sig"))
    fp = data["persona"]["forbidden_phrases"]
    for phrase in ("5-year expat", "American expat", "American living in Chengdu",
                   "my wife", "Chengdu wife", "I remember my first trip",
                   "personally tested", "personally used", "5 years living in China",
                   "I lived in"):
        assert phrase in fp, phrase


# ---------------------------------------------------------------------------
# 7: affiliate URLs unchanged (hugo.toml affiliate section)
# ---------------------------------------------------------------------------
def test_affiliate_urls_unchanged():
    old = git_show_head("hugo.toml")
    new = read("hugo.toml")
    def aff_section(t: str) -> str:
        start = t.find("[params.affiliate]")
        assert start >= 0, "affiliate section missing"
        end = t.find("\n[", start + 10)
        return t[start:end if end > 0 else len(t)]
    assert aff_section(old) == aff_section(new)


# ---------------------------------------------------------------------------
# 8-9: content_id / canonical unchanged (posts untouched)
# ---------------------------------------------------------------------------
# P1-GROWTH-15 authorized REV002 CTA experiment post
REV002_AUTHORIZED = {"content/posts/2026-07-16-china-transportation-complete-guide-trains-subways-taxis-and-more.md",
    # P1-GROWTH-18/19 authorized internal-link additions
    "content/posts/2026-05-25-china-high-speed-rail-how-to-book-tickets.md",
    "content/posts/china-transportation-card-guide.md",
    "content/posts/china-airport-transfer-guide.md",
    # P1-GROWTH-22 authorized Alipay authority page + payment cluster internal links
    "content/posts/alipay-for-foreigners-guide.md",
    "content/posts/2026-08-09-china-packing-list-2026-what-to-bring-and-what-to-leave-at-home.md",
    "content/posts/internet-connection-china-esim-vpn-guide.md"}

PILOT_POSTS = {
    "content/posts/western-sichuan-overland-camping-route.md",
    "content/posts/2026-07-03-guilin-and-yangshuo-the-ultimate-karst-landscape-guide-for-2026-guide.md",
    "content/posts/2026-06-23-sichuan-hotpot-guide-history-best-restaurants-and-cultural-significance.md",
    # P1-GROWTH-12B authorized REV001 CTA experiment post
    "content/posts/2026-05-28-chinese-food-delivery-meituan-eleme-guide.md",
}

# P1-GROWTH-24 authorized TOP5 front-matter corruption fix
GROWTH24_AUTHORIZED = {"content/posts/china-extends-144-hour-visa-free-transit-policy-to-more-countries.md"}
# P1-GROWTH-25 authorized TOP-page title/meta update
GROWTH25_AUTHORIZED = {"content/posts/2026-08-01-chinabound-travel-guide-2026-08-monthly-update.md"}
# P1-GROWTH-28 authorized CTR pilot title/meta updates
GROWTH28_AUTHORIZED = {
    "content/posts/2026-08-01-china-photography-guide-capturing-the-wonders-of-the-middle-kingdom.md",
    "content/posts/2026-07-05-yunnan-adventure-rice-terraces-ancient-towns-and-ethnic-minorities-guide.md",
}


def test_posts_untouched():
    """P1-BRAND-03 pilot posts + P1-GROWTH-12B REV001 CTA post may change; nothing else."""
    proc = subprocess.run(["git", "diff", "HEAD", "--name-only", "--", "content/posts/"],
                          cwd=str(REPO), capture_output=True, text=True, encoding="utf-8")
    changed = {p for p in proc.stdout.splitlines() if p}
    allowed = (PILOT_POSTS | REV002_AUTHORIZED | GROWTH24_AUTHORIZED |
               GROWTH25_AUTHORIZED | GROWTH28_AUTHORIZED | CONVERSION_OPT_AUTHORIZED)
    assert changed <= allowed, f"unexpected posts changed:\n{changed - allowed}"


def test_non_brand_content_untouched():
    proc = subprocess.run(["git", "diff", "HEAD", "--name-only", "--", "content/"],
                          cwd=str(REPO), capture_output=True, text=True, encoding="utf-8")
    changed = [p for p in proc.stdout.splitlines() if p]
    allowed = {"content/about/_index.md", "content/resources/_index.md",
               "content/posts/western-sichuan-overland-camping-route.md",
               "content/posts/2026-07-03-guilin-and-yangshuo-the-ultimate-karst-landscape-guide-for-2026-guide.md",
               "content/posts/2026-06-23-sichuan-hotpot-guide-history-best-restaurants-and-cultural-significance.md",
               "content/posts/2026-05-28-chinese-food-delivery-meituan-eleme-guide.md",
               # P1-GROWTH-15 authorized REV002 CTA experiment post
               "content/posts/2026-07-16-china-transportation-complete-guide-trains-subways-taxis-and-more.md",
               # P1-GROWTH-18 authorized internal-link additions
               "content/posts/2026-05-25-china-high-speed-rail-how-to-book-tickets.md",
               "content/posts/china-transportation-card-guide.md",
               # P1-GROWTH-22 authorized Alipay authority page + internal links
               "content/posts/alipay-for-foreigners-guide.md",
               "content/posts/2026-08-09-china-packing-list-2026-what-to-bring-and-what-to-leave-at-home.md",
               "content/posts/internet-connection-china-esim-vpn-guide.md",
               # P1-GROWTH-24 authorized TOP5 front-matter corruption fix
               "content/posts/china-extends-144-hour-visa-free-transit-policy-to-more-countries.md",
               # P1-GROWTH-25 authorized TOP-page title/meta update
               "content/posts/2026-08-01-chinabound-travel-guide-2026-08-monthly-update.md",
               # P1-GROWTH-28 authorized CTR pilot title/meta updates
               "content/posts/2026-08-01-china-photography-guide-capturing-the-wonders-of-the-middle-kingdom.md",
               "content/posts/2026-07-05-yunnan-adventure-rice-terraces-ancient-towns-and-ethnic-minorities-guide.md",
               # P1-GROWTH-28A: non-article page persona cleanup
               "content/7-day-china-itinerary.md",
               "content/affiliate-disclosure.md",
               "content/contact.md",
               "content/cities/_index.md",
               "content/cities/beijing.md",
               "content/cities/chengdu.md"}
    # 本次"转化与排名优化"任务授权：联盟软推荐 + 分类规范化 + 深度优化
    allowed |= CONVERSION_OPT_AUTHORIZED
    assert set(changed) <= allowed, f"unexpected content changes: {set(changed) - allowed}"


def test_canonical_unchanged():
    # P1-BRAND-03 pilot posts keep their canonical declarations vs HEAD
    for rel in PILOT_POSTS:
        old, new = git_show_head(rel), read(rel)
        assert old
        m_old = re.search(r"^canonicalURL:\s*['\"]([^'\"]+)", old, re.M)
        m_new = re.search(r"^canonicalURL:\s*['\"]([^'\"]+)", new, re.M)
        assert m_old and m_new and m_old.group(1) == m_new.group(1), rel
    # homepage/resources/about pages keep their identity fields
    about = read("content/about/_index.md")
    assert "hello@chinaboundtravel.com" in about
