"""P1-GROWTH-07: WeChat Pay differentiation + first SEO expansion regression tests.

Verifies:
1. two WeChat titles differ
2. two WeChat meta descriptions differ
3. H1 intent differs
4. minimum 3 unique H2 per article
5. reciprocal internal links exist
6. URL unchanged
7. content_id unchanged
8. affiliate URLs unchanged
9. PersonaGuard passes
10. no duplicate meta description
plus scope control (only the 3 allowed objects changed).
"""
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "tests"))
from persona_guard import PersonaGuard  # noqa: E402
from _conversion_optimization import CONVERSION_OPT_AUTHORIZED  # noqa: E402

SITE = "https://www.chinaboundtravel.com"

STRONG = "content/posts/2026-05-22-how-to-use-wechat-pay-as-a-foreigner.md"
WEAK = "content/posts/2026-07-02-wechat-pay-for-foreigners-step-by-step-setup-and-common-mistakes-to-avoid-guide.md"
TRANSPORT = "content/posts/2026-05-25-china-high-speed-rail-how-to-book-tickets.md"


def _read(name):
    return (REPO / name).read_text(encoding="utf-8")


def _fm(text, key):
    fm = text.split("---", 2)[1]
    m = re.search(r"^\s*" + re.escape(key) + r"\s*[:=]\s*(.+)$", fm, re.M)
    if not m:
        return None
    val = m.group(1).strip()
    if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
        val = val[1:-1]
    return val


def _h1(body):
    m = re.search(r"^#\s+(.+)$", body, re.M)
    return m.group(1).strip() if m else None


def _h2s(body):
    return [m.group(1).strip() for m in re.finditer(r"^##\s+(.+)$", body, re.M)]


def _normalize_heading(h):
    return re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", h).strip()


# ---------------------------------------------------------------------------
# 1-4: titles / descriptions / H1 / H2 uniqueness
# ---------------------------------------------------------------------------

def test_wechat_titles_differ():
    a = _fm(_read(STRONG), "title")
    b = _fm(_read(WEAK), "title")
    assert a and b and a != b
    assert "Step by Step" not in a
    assert "Can Foreigners" in a
    assert "Step by Step" in b


def test_wechat_meta_descriptions_differ():
    a = _fm(_read(STRONG), "description")
    b = _fm(_read(WEAK), "description")
    assert a and b and a != b
    assert len(a) <= 155 and len(b) <= 155


def test_h1_intent_differs():
    # STRONG renders its title as H1; WEAK has an explicit body H1 too
    a_h1 = _fm(_read(STRONG), "title")
    b_h1 = _h1(_read(WEAK).split("---", 2)[2]) or _fm(_read(WEAK), "title")
    assert a_h1 and b_h1 and a_h1 != b_h1
    assert "Can Foreigners" in a_h1
    assert "Step by Step" in b_h1


def test_minimum_3_unique_h2_per_article():
    strong_h2 = {_normalize_heading(h) for h in _h2s(_read(STRONG).split("---", 2)[2])}
    weak_h2 = {_normalize_heading(h) for h in _h2s(_read(WEAK).split("---", 2)[2])}
    assert len(strong_h2) >= 3
    assert len(weak_h2) >= 3
    overlap = strong_h2 & weak_h2
    assert len(overlap) <= 1, overlap  # at most one shared H2 (FAQ) - differentiation
    # intent-specific sections exist
    assert any("Eligibility" in h or "Can Foreigners" in h or "Cards" in h for h in strong_h2)
    assert any("Pay" in h and ("QR" in h or "Merchant" in h) for h in weak_h2)
    assert any("Troubleshooting" in h for h in weak_h2)


# ---------------------------------------------------------------------------
# 5: reciprocal internal links
# ---------------------------------------------------------------------------

def test_reciprocal_internal_links_exist():
    strong_body = _read(STRONG).split("---", 2)[2]
    weak_body = _read(WEAK).split("---", 2)[2]
    assert "/posts/wechat-pay-for-foreigners-step-by-step-setup-and-common-mistakes-to-avoid-guide/" in strong_body
    assert "/posts/how-to-use-wechat-pay-as-a-foreigner/" in weak_body


# ---------------------------------------------------------------------------
# 6-8: URL / content_id / affiliate unchanged vs HEAD
# ---------------------------------------------------------------------------

def test_url_content_id_canonical_unchanged():
    for name in (STRONG, WEAK, TRANSPORT):
        rel = name.replace("\\", "/")
        old = subprocess.run(["git", "show", "HEAD:" + rel], cwd=str(REPO),
                             capture_output=True, text=True, encoding="utf-8")
        assert old.returncode == 0, old.stderr
        old_text, new_text = old.stdout, _read(name)
        assert _fm(old_text, "content_id") == _fm(new_text, "content_id"), rel
        assert _fm(old_text, "canonicalURL") == _fm(new_text, "canonicalURL"), rel
        if _fm(old_text, "slug") is not None:
            assert _fm(old_text, "slug") == _fm(new_text, "slug"), rel


def test_affiliate_urls_utm_unchanged():
    """Existing affiliate URLs/UTM must be preserved; the "转化与排名优化" task
    may only ADD config-driven soft-recommend shortcodes (no hardcoded URLs)."""
    pat = re.compile(r"\{\{<[^>]+>\}\}|https?://[^\s)\]]+|utm_[a-z]+=[^&\s)\]]+", re.I)
    soft_pat = re.compile(r"\{\{< ?/?soft-recommend[^>]*>?\}\}", re.I)
    for name in (STRONG, WEAK, TRANSPORT):
        rel = name.replace("\\", "/")
        old = subprocess.run(["git", "show", "HEAD:" + rel], cwd=str(REPO),
                             capture_output=True, text=True, encoding="utf-8")
        old_tokens = sorted(pat.findall(old.stdout))
        new_tokens = sorted(pat.findall(_read(name)))
        # the only allowed NEW tokens are soft-recommend shortcodes
        removed = [t for t in old_tokens if t not in new_tokens]
        added = [t for t in new_tokens if t not in old_tokens]
        assert not removed, f"{name}: existing affiliate/URL/UTM removed: {removed}"
        assert all(soft_pat.match(t) for t in added), \
            f"{name}: unexpected new tokens: {added}"


# ---------------------------------------------------------------------------
# 9: PersonaGuard
# ---------------------------------------------------------------------------

def test_persona_guard_passes():
    guard = PersonaGuard()
    for name in (STRONG, WEAK, TRANSPORT):
        assert guard.check(_read(name)) == [], name


# ---------------------------------------------------------------------------
# 10: no duplicate meta descriptions site-wide
# ---------------------------------------------------------------------------

def test_no_duplicate_meta_description():
    seen = {}
    for p in (REPO / "content" / "posts").glob("*.md"):
        d = _fm(p.read_text(encoding="utf-8"), "description")
        if d:
            seen.setdefault(d.lower(), []).append(p.name)
    dupes = {k: v for k, v in seen.items() if len(v) > 1}
    assert not dupes, dupes


# ---------------------------------------------------------------------------
# scope control
# ---------------------------------------------------------------------------

def test_growth07_scope_only_allowed_objects():
    out = subprocess.run(["git", "diff", "HEAD", "--name-only"], cwd=str(REPO),
                         capture_output=True, text=True, encoding="utf-8")
    changed = [p for p in out.stdout.splitlines() if p]
    posts_changed = [p for p in changed if p.startswith("content/posts/")]
    allowed = {"content/posts/2026-05-22-how-to-use-wechat-pay-as-a-foreigner.md",
               "content/posts/2026-07-02-wechat-pay-for-foreigners-step-by-step-setup-and-common-mistakes-to-avoid-guide.md",
               "content/posts/2026-05-25-china-high-speed-rail-how-to-book-tickets.md",
               "content/posts/2026-07-16-china-transportation-complete-guide-trains-subways-taxis-and-more.md",
               # P1-GROWTH-12 authorized REV-001: 144h mid-content CTA
               "content/posts/144-hour-visa-free-transit-guide.md",
               # P1-BRAND-03 authorized legacy persona pilot posts
               "content/posts/western-sichuan-overland-camping-route.md",
               "content/posts/2026-07-03-guilin-and-yangshuo-the-ultimate-karst-landscape-guide-for-2026-guide.md",
               "content/posts/2026-06-23-sichuan-hotpot-guide-history-best-restaurants-and-cultural-significance.md",
               # P1-GROWTH-12B authorized REV001 CTA experiment post
               "content/posts/2026-05-28-chinese-food-delivery-meituan-eleme-guide.md",
               # P1-GROWTH-18/19 authorized commercial cluster content + internal links
               "content/posts/china-transportation-card-guide.md",
               "content/posts/china-airport-transfer-guide.md",
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
               # P1-GROWTH-31 authorized content trust auto-fix pilot
               "content/posts/china-extends-144-hour-visa-free-transit-policy-to-more-countries.md",
               "content/posts/2026-05-22-how-to-use-wechat-pay-as-a-foreigner.md",
               "content/posts/western-sichuan-overland-camping-route.md",
               "content/posts/2026-07-03-guilin-and-yangshuo-the-ultimate-karst-landscape-guide-for-2026-guide.md",
               "content/posts/2026-06-30-zhangjiajie-avatar-mountains-complete-guide-to-chinas-most-spectacular-park.md",
               "content/posts/2026-07-27-accommodation-tips-guide.md",
               "content/posts/2026-06-23-sichuan-hotpot-guide-history-best-restaurants-and-cultural-significance.md",
               "content/posts/2026-05-25-shanghai-bund-french-concession-2-day-guide.md",
               "content/posts/2026-08-03-chinese-language-survival-phrases-guide.md",
               "content/posts/2026-07-01-chinese-street-food-a-first-timers-guide-to-night-markets-and-street-stalls.md"}
    # 本次"转化与排名优化"任务授权：联盟软推荐 + 分类规范化 + 深度优化
    allowed = allowed | CONVERSION_OPT_AUTHORIZED
    extra = set(posts_changed) - allowed
    assert not extra, extra
    assert set(posts_changed) <= allowed
    allowed_layouts = {"layouts/partials/schema_faq.html",
                      # P1-GROWTH-10A authorized site-wide Travelpayouts Drive install
                      "layouts/partials/head.html",
                      # P1-GROWTH-12 authorized REV-001: mid-content CTA + click delegation
                      "layouts/_default/single.html",
                      "layouts/shortcodes/affiliate-mid-cta.html",
                      # P1-GROWTH-27 authorized GA4 funnel attribution on A/B CTA
                      "layouts/shortcodes/ab-cta.html",
                      # P1-BRAND-02 authorized editorial persona migration (brand surfaces)
                      "layouts/cities/single.html",
                      "layouts/partials/affiliate-disclosure.html",
                      "layouts/partials/home-banner.html",
                      "layouts/partials/sidebar-author.html",
                      "layouts/partials/travel-promo.html",
                      "layouts/shortcodes/affiliate-disclosure.html",
                      "layouts/partials/templates/schema_json.html",
                      # P0-2026-08-16 authorized pricing checkout link fix (onetime/annual swapped)
                      "layouts/partials/pricing-table.html",
                      "hugo.toml",
                      "layouts/partials/cookie-consent.html",
                      # P1-GROWTH-28A authorized site-wide OG/Twitter templates + cookie/footer/email cleanup
                      "layouts/partials/email-subscribe.html",
                      "layouts/partials/footer.html",
                      "layouts/partials/templates/opengraph.html",
                      "layouts/partials/templates/twitter_cards.html",
                      "config/content_governance.json",
                      # P1-GROWTH-30R authorized redirect-chain closure (direct-to-final 301)
                      "static/_redirects"}
    forbidden = [p for p in changed
                 if (p.startswith(("layouts/", "hugo.toml", "config/", "static/_redirects"))
                     and p not in allowed_layouts)]
    assert not forbidden, forbidden
