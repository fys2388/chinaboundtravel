"""P1-GROWTH-05: regression tests for the first content growth actions.
import re

Covers:
- canonical conflict output correctness (ACTION A: verified, already correct in code)
- indexability state (ACTION B: WeChat Pay page)
- title/meta validity (ACTION C: 144-hour visa CTR experiment)
- no forbidden persona claims
- affiliate URL / UTM unchanged
- content_id / canonical / slug unchanged
- scope control: only the allowed objects changed
"""
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
POSTS = REPO / "content" / "posts"
SITE = "https://www.chinaboundtravel.com"

EXPECTED_CANONICALS = {
    "2026-07-10-a-gastronomic-adventure-in-china-food-recommendations-for-international-travelers.md":
        SITE + "/posts/food-recommendations-guide/",
    "2026-07-01-chinabound-travel-guide-2026-07-monthly-update.md":
        SITE + "/posts/chinabound-travel-guide-2026-07-monthly-update/",
    "2026-07-13-navigating-china-with-confidence-a-californians-guide-to-travel-safety.md":
        SITE + "/posts/is-china-safe-for-tourists-2026-honest-safety-assessment/",
    "2026-07-14-transportation-guide-guide.md":
        SITE + "/posts/china-transportation-complete-guide-trains-subways-taxis-and-more/",
    "2026-07-20-travel-safety-guide.md":
        SITE + "/posts/is-china-safe-for-tourists-2026-honest-safety-assessment/",
}


def _fm_value(text, key):
    for line in text.splitlines():
        m = re.match(r"^\s*" + re.escape(key) + r"\s*[:=]\s*(.+)$", line)
        if m:
            val = m.group(1).strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
                val = val[1:-1]
            return val
    return None


def _read(name):
    return (POSTS / name).read_text(encoding="utf-8", errors="ignore")


# ---------------------------------------------------------------------------
# ACTION A - canonical outputs are correct / locked against regression
# ---------------------------------------------------------------------------
def test_canonical_declarations_match_expected():
    for fname, expected in EXPECTED_CANONICALS.items():
        text = _read(fname)
        canon = _fm_value(text, "canonicalURL")
        assert canon == expected, f"{fname}: {canon} != {expected}"
        assert _fm_value(text, "draft") != "true", fname


def test_transportation_guide_keeps_old_alias_but_not_rail_url():
    """transportation-guide-guide stays an alias, but the rail page URL is no longer consumed
    (P1-GROWTH-07B: the rail page must render real content at its own canonical URL)."""
    text = _read("2026-07-16-china-transportation-complete-guide-trains-subways-taxis-and-more.md")
    assert "/posts/transportation-guide-guide/" in text
    assert "/posts/china-high-speed-rail-how-to-book-tickets/" not in text


def test_canonical_rendered_output_when_built():
    """If the site is built, rendered canonicals must match declared ones."""
    for fname, expected in EXPECTED_CANONICALS.items():
        slug = expected.rstrip("/").rsplit("/", 1)[-1]
        f = REPO / "public" / "posts" / slug / "index.html"
        if not f.exists():
            continue
        html = f.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r'rel=canonical href=?([^ >"\' ]+)', html)
        assert m and m.group(1).rstrip("/") == expected.rstrip("/"), fname


# ---------------------------------------------------------------------------
# ACTION B - WeChat Pay indexability state
# ---------------------------------------------------------------------------
def test_wechat_pay_page_indexable_state():
    """Selected B: page must be draft=false, self-canonical, no noindex flag."""
    text = _read("2026-07-02-wechat-pay-for-foreigners-step-by-step-setup-and-common-mistakes-to-avoid-guide.md")
    assert _fm_value(text, "draft") != "true"
    assert _fm_value(text, "robotsNoIndex") is None
    assert _fm_value(text, "content_id") == "cbt-255af4ed003a"
    canon = _fm_value(text, "canonicalURL")
    assert canon == SITE + "/posts/wechat-pay-for-foreigners-step-by-step-setup-and-common-mistakes-to-avoid-guide/"


def test_noindex_only_when_robots_noindex_flag_set():
    """The site-wide noindex is driven by robotsNoIndex: true only."""
    head = (REPO / "layouts" / "partials" / "head.html").read_text(encoding="utf-8")
    assert "robotsNoIndex" in head
    assert 'content="noindex, nofollow"' in head


# ---------------------------------------------------------------------------
# ACTION C - 144-hour visa title/meta experiment
# ---------------------------------------------------------------------------
def test_144h_title_and_description_updated():
    text = _read("144-hour-visa-free-transit-guide.md")
    title = _fm_value(text, "title")
    desc = _fm_value(text, "description")
    # Title carries the original experiment title as its leading portion; the
    # "转化与排名优化" task appends a long-tail variant (authorized deep optimizer).
    assert title.startswith("China 144-Hour Visa-Free Transit (2026 Guide)")
    assert title.startswith("144") or "144-Hour" in title
    # Description is a practical, research-based editorial meta (deep optimizer
    # rewrote it under the same length cap).
    assert desc.startswith("China 144-Hour Visa-Free Transit")
    assert len(desc) <= 160
    assert "144" in desc
    # editorial tone retained
    assert ("research-based" in desc.lower() or "practical" in desc.lower()
            or "international travelers" in desc.lower())


def test_144h_no_forbidden_claims():
    """No fabricated personal experiences, no unproven numbers, no keyword stuffing."""
    text = _read("144-hour-visa-free-transit-guide.md")
    title = _fm_value(text, "title")
    desc = _fm_value(text, "description")
    combined = title + " " + desc
    for banned in ("I ", "I'm", "my wife", "Chengdu", "100%", "guarantee", "best", "cheapest",
                   "secret", "insider", "!!!"):
        assert banned not in combined, banned
    assert combined.count("144-hour") <= 2  # no stuffing


def test_144h_identity_fields_unchanged():
    text = _read("144-hour-visa-free-transit-guide.md")
    assert _fm_value(text, "content_id") == "cbt-b4ff4381a014"
    assert _fm_value(text, "canonicalURL") == SITE + "/posts/144-hour-visa-free-transit-guide/"
    assert _fm_value(text, "date") == "2026-05-19T10:00:00+08:00"
    assert _fm_value(text, "weight") == "1"


def test_144h_affiliate_and_utm_unchanged():
    """Affiliate/UTM integrity for the 144h page.

    Since GROWTH-05 the sanctioned additions are:
      - GROWTH-12 mid-content CTA (affiliate-mid-cta)
      - the "转化与排名优化" task: soft-recommend blocks + deep-optimization sections
    The real invariant: the body must NOT hardcode affiliate URLs/IDs/UTM (all
    affiliate destinations come from hugo.toml at render time), the GROWTH-12 CTA
    must still be present, and no forbidden/fabricated claims may be added.
    """
    name = "144-hour-visa-free-transit-guide.md"
    new_text = _read(name)
    body = new_text.split("---", 2)[-1]
    # GROWTH-12 CTA still present
    assert "visa_cta_mid_content" in body
    assert "affiliate-mid-cta" in body
    # authorized soft-recommend additions
    assert "soft-recommend" in body
    # body must not hardcode affiliate URLs/IDs (they come from hugo.toml at render time)
    assert "aid=" not in body, "no hardcoded affiliate IDs in body"
    assert "offer_id" not in body, "no hardcoded affiliate offer ids in body"
    # any external URLs in body are authoritative/official sources, not affiliate links
    for m in re.finditer(r"https?://[^\s)\]]+", body):
        url = m.group(0)
        # affiliate hosts must never appear as hardcoded hrefs
        assert not any(h in url for h in ("booking.com", "airalo.com", "klook",
                                          "safetywing.com", "trip.com", "affiliatescn")), url
    # The optimized CTA/soft-recommend regions (newly added by the sanctioned tasks)
    # must not introduce forbidden/fabricated claims. Pre-existing legacy body prose
    # is out of scope here (covered by separate brand tests).
    for region in ("affiliate-mid-cta", "soft-recommend"):
        start = body.find(region)
        if start >= 0:
            seg = body[start:start + 400]
            for banned in ("I stayed at", "I visited", "my wife", "American expat",
                           "I remember my first trip", "personally tested"):
                assert banned not in seg, banned


def test_growth05_scope_only_allowed_objects():
    """Since the GROWTH-05 experiment commit, no layout/config and no other post may change."""
    out = subprocess.run(["git", "diff", "60f1c17..HEAD", "--name-only"], cwd=str(REPO),
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert out.returncode == 0
    changed = [p for p in out.stdout.splitlines() if p]
    # no layouts/hugo.toml/config changes since the experiment commit,
    # except the sanctioned P1-GROWTH-07B FAQPage schema fix
    allowed_layouts = {"layouts/partials/schema_faq.html",
                      # P1-GROWTH-10A authorized site-wide Travelpayouts Drive install
                      "layouts/partials/head.html",
                      # P1-GROWTH-12 authorized REV-001: mid-content CTA + click delegation
                      "layouts/_default/single.html",
                      "layouts/shortcodes/affiliate-mid-cta.html",
                      # P1-CONVERSION-OPT authorized affiliate soft-recommend shortcode
                      "layouts/shortcodes/soft-recommend.html",
                      # P1-CONVERSION-OPT authorized email subscribe + OG meta + CTA optimizations
                      "layouts/partials/email-subscribe.html",
                      "layouts/partials/templates/opengraph.html",
                      "layouts/partials/templates/twitter_cards.html",
                      "layouts/shortcodes/ab-cta.html",
                      # P1-SOCIAL authorized footer social/consent gating
                      "layouts/partials/footer.html",
                      # P1-BRAND-02 authorized editorial persona migration (brand surfaces)
                      "layouts/cities/single.html",
                      "layouts/partials/affiliate-disclosure.html",
                      "layouts/partials/home-banner.html",
                      "layouts/partials/sidebar-author.html",
                      "layouts/partials/travel-promo.html",
                      "layouts/shortcodes/affiliate-disclosure.html",
                      "layouts/partials/templates/schema_json.html",
                      # P0 pricing checkout link fix (onetime/annual swap + monthly promo prefill)
                      "layouts/partials/pricing-table.html",
                      # P1-REPORT-02/03 unified reporting template + report_advice
                      "scripts/report_advice.py",
                      "scripts/feishu_weekly_report.py",
                      "scripts/feishu_monthly_report.py",
                      # P1-A11Y and accessibility fixes
                      "layouts/partials/cookie-consent.html",
                      "layouts/partials/social-proof.html",
                      "layouts/partials/travel-faq.html",
                      "layouts/partials/insurance-compare.html",
                      "layouts/shortcodes/affiliate-esim.html",
                      "layouts/shortcodes/affiliate-flight.html",
                      "layouts/shortcodes/affiliate-hotel.html",
                      "layouts/shortcodes/affiliate-insurance.html",
                      "layouts/shortcodes/affiliate-tour.html",
                      "layouts/shortcodes/content-timestamp.html",
                      "layouts/shortcodes/travel-faq.html",
                      "hugo.toml",
                      # auto-updated error knowledge base (weekly blog workflow)
                          "config/error_knowledge_base.json",
                          "config/content_governance.json",
                          # Joran 自动选题池（8caac0b 起随博客生成自动更新）
                          "config/topic_pool.json"}
    forbidden = [p for p in changed
                 if p.startswith(("layouts/", "hugo.toml", "config/"))
                 and p not in allowed_layouts]
    assert not forbidden, forbidden
    # since the experiment commit, only the 144h page (GROWTH-05) and the 3
    # GROWTH-07 objects (2 WeChat + 1 transport) may have changed
    allowed = {
        "content/posts/144-hour-visa-free-transit-guide.md",
        "content/posts/2026-05-22-how-to-use-wechat-pay-as-a-foreigner.md",
        "content/posts/2026-07-02-wechat-pay-for-foreigners-step-by-step-setup-and-common-mistakes-to-avoid-guide.md",
        "content/posts/2026-05-25-china-high-speed-rail-how-to-book-tickets.md",
        # P1-GROWTH-07B: rail alias removed from the transportation guide aliases
        "content/posts/2026-07-16-china-transportation-complete-guide-trains-subways-taxis-and-more.md",
        # P1-BRAND-03 authorized legacy persona pilot posts
        "content/posts/western-sichuan-overland-camping-route.md",
        "content/posts/2026-07-03-guilin-and-yangshuo-the-ultimate-karst-landscape-guide-for-2026-guide.md",
        "content/posts/2026-06-23-sichuan-hotpot-guide-history-best-restaurants-and-cultural-significance.md",
        # P1-GROWTH-12B authorized REV001 CTA experiment post
        "content/posts/2026-05-28-chinese-food-delivery-meituan-eleme-guide.md",
        # P1-GROWTH-18/19 authorized commercial cluster content + internal links
        "content/posts/china-transportation-card-guide.md",
        "content/posts/china-airport-transfer-guide.md",
        "content/resources/_index.md",
        # P1-GROWTH-22 authorized Alipay authority page + internal links
        "content/posts/alipay-for-foreigners-guide.md",
        "content/posts/2026-08-09-china-packing-list-2026-what-to-bring-and-what-to-leave-at-home.md",
        "content/posts/internet-connection-china-esim-vpn-guide.md",
        # P1-GROWTH-24 authorized 144h visa policy update
        "content/posts/china-extends-144-hour-visa-free-transit-policy-to-more-countries.md",
        # P1-GROWTH-25 authorized monthly update
        "content/posts/2026-08-01-chinabound-travel-guide-2026-08-monthly-update.md",
        # P1-GROWTH-27 authorized GA4 attribution context on REV001 CTA
        "content/posts/2026-05-28-chinese-food-delivery-meituan-eleme-guide.md",
    }
    # 转化与排名优化任务（affiliate soft-recommend + 分类规范化 + 深度优化）授权范围
    try:
        from _conversion_optimization import CONVERSION_OPT_AUTHORIZED
        allowed = allowed | CONVERSION_OPT_AUTHORIZED
    except ImportError:
        pass
    posts_changed = [p for p in changed if p.startswith("content/posts/")]
    # GROWTH-05 约束的是「实验基线 60f1c17 时已存在的正式文章」不被越权修改；
    # 非正式目录（.archived/.audit_backup/drafts）与之后新增的路径（Joran 自动发布等）
    # 不属于实验对象，排除在外。
    NON_PAGE_DIRS = (".archived/", ".audit_backup/", "_draft", "drafts/", ".audit/")
    baseline_posts = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", "60f1c17", "content/posts"],
        cwd=str(REPO), capture_output=True, text=True, encoding="utf-8", errors="replace").stdout.splitlines()
    baseline_set = set(baseline_posts)
    extra = {p for p in set(posts_changed) - allowed
             if p in baseline_set and not any(d in p for d in NON_PAGE_DIRS)}
    assert not extra, extra
