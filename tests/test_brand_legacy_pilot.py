"""P1-BRAND-03: legacy persona migration pilot regression tests.

Verifies for the 3 pilot articles (migrated to the Joran editorial persona):
1. URL (slug) unchanged vs HEAD
2. canonical unchanged vs HEAD
3. content_id unchanged vs HEAD
4. affiliate URLs unchanged vs HEAD
5. UTM unchanged vs HEAD
6. PersonaGuard passes (no forbidden persona phrases)
7. no old fictional experience claims remain
8. article structure retained (title + main H2 sections preserved)
9. meta description valid (non-empty, <=160 chars, site-unique)
10. internal links valid (markdown audit clean for these files)
plus scope control: only the 3 pilot posts may change.
"""
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from persona_guard import PersonaGuard  # noqa: E402
from audit_internal_links import audit  # noqa: E402

SITE = "https://www.chinaboundtravel.com"

PILOT_POSTS = {
    "content/posts/western-sichuan-overland-camping-route.md": {
        "content_id": "cbt-80f6c218ad94",
        "canonical": SITE + "/posts/western-sichuan-overland-camping-route/",
        "title": "Western Sichuan Overland Camping Route: 7 Days",
        "h2": [
            "## Why Western Sichuan?",
            "## Day 1: Chengdu to Kangding (280km, ~5 hours)",
            "## Day 5: Daocheng Yading National Park",
            "## Essential Tips for Western Sichuan Camping",
            "## Final Thoughts: Why This Route Stands Out",
        ],
        "old_claims": [
            "My wife, Xiao Li",
            "Five years living in China",
            "my friend Lao Wang",
            "I made every mistake in the book",
            "I forgot lip balm once",
            "my Honda CR-V",
            "We left at 6 AM",
            "we set up camp",
            "our tent almost blew away",
            "Why This Trip Changed My Life",
            "When I first came to China",
            "based on my personal experience",
        ],
    },
    "content/posts/2026-07-03-guilin-and-yangshuo-the-ultimate-karst-landscape-guide-for-2026-guide.md": {
        "content_id": "cbt-bf4ec5e57a07",
        "canonical": SITE + "/posts/guilin-and-yangshuo-the-ultimate-karst-landscape-guide-for-2026/",
        "title": "Guilin & Yangshuo: Complete 2026 Travel Guide",
        "h2": [
            "## Li River Cruise: Your Core Decision",
            "## Best Time to Visit",
            "## 3-Day Itinerary",
            "## What to Eat (With Prices)",
            "## How to Get There",
            "## Where to Stay",
            "## Quick FAQ",
            "## Related Guides",
        ],
        "old_claims": [
            "5-year China expat",
            "I'd read about the karst landscape",
            "I looked down at those limestone peaks",
            "My honest take",
            "I've been to Guilin in three different seasons",
            "route I'd recommend to a friend",
            "as much as I do",
            "my top recommendation",
            "Based on what I'd actually spend",
            "I made this mistake once",
        ],
    },
    "content/posts/2026-06-23-sichuan-hotpot-guide-history-best-restaurants-and-cultural-significance.md": {
        "content_id": "cbt-550a6e3e929c",
        "canonical": SITE + "/posts/sichuan-hotpot-guide-history-best-restaurants-and-cultural-significance/",
        "title": "Sichuan Hotpot Guide: History & Best Restaurants",
        "h2": [
            "## History of Sichuan Hotpot",
            "## Cultural Significance of Sichuan Hotpot",
            "## Best Restaurants for Sichuan Hotpot",
            "## Tips for Enjoying Sichuan Hotpot",
            "## Conclusion",
        ],
        "old_claims": [
            "US expat in Chengdu",
            "American who has spent over 5 years living in Chengdu",
            "I remember one time when I was invited",
            "One of my personal favorites",
            "I would recommend checking out",
            "trust me, it's worth it for the taste",
            "tips that I would like to share",
            "I highly recommend giving Sichuan hotpot a try",
        ],
    },
}


def _read(rel):
    return (REPO / rel).read_text(encoding="utf-8")


def _git_show_head(rel):
    out = subprocess.run(["git", "show", "HEAD:" + rel], cwd=str(REPO),
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    return out.stdout if out.returncode == 0 else ""


def _fm(text, key):
    m = re.search(r"^\s*" + re.escape(key) + r"\s*[:=]\s*(.+)$", text.split("---", 2)[1], re.M)
    if not m:
        return None
    val = m.group(1).strip()
    if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
        val = val[1:-1]
    return val


def _all_posts_texts():
    for p in (REPO / "content" / "posts").glob("*.md"):
        yield p.name, p.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1-5: identity / affiliate / UTM locked vs HEAD
# ---------------------------------------------------------------------------
def test_url_content_id_canonical_unchanged():
    for rel in PILOT_POSTS:
        old, new = _git_show_head(rel), _read(rel)
        assert old, rel
        for key in ("content_id", "canonicalURL", "slug", "title"):
            assert _fm(old, key) == _fm(new, key), f"{rel}: {key} changed"
        assert _fm(new, "content_id") == PILOT_POSTS[rel]["content_id"], rel
        assert _fm(new, "canonicalURL") == PILOT_POSTS[rel]["canonical"], rel


def test_affiliate_urls_utm_unchanged():
    pat = re.compile(r"\{\{<[^>]+>\}\}|https?://[^\s)\]]+|utm_[a-z]+=[^&\s)\]]+", re.I)
    for rel in PILOT_POSTS:
        old_tokens = sorted(pat.findall(_git_show_head(rel)))
        new_tokens = sorted(pat.findall(_read(rel)))
        assert old_tokens == new_tokens, rel


# ---------------------------------------------------------------------------
# 6-7: persona guard + no old fictional claims
# ---------------------------------------------------------------------------
def test_persona_guard_passes():
    guard = PersonaGuard()
    for rel in PILOT_POSTS:
        assert guard.check(_read(rel)) == [], rel


def test_no_old_fictional_claims():
    for rel, meta in PILOT_POSTS.items():
        text = _read(rel)
        for claim in meta["old_claims"]:
            assert claim not in text, f"{rel}: stale claim present: {claim!r}"


# ---------------------------------------------------------------------------
# 8: structure retained
# ---------------------------------------------------------------------------
def test_title_and_h2_structure_retained():
    for rel, meta in PILOT_POSTS.items():
        text = _read(rel)
        assert _fm(text, "title") == meta["title"], rel
        for h2 in meta["h2"]:
            assert h2 in text, f"{rel}: missing section {h2!r}"


# ---------------------------------------------------------------------------
# 9: meta description valid + site-unique
# ---------------------------------------------------------------------------
def test_meta_description_valid_and_unique():
    # pilot descriptions must be present, <=160 chars, and unique site-wide
    seen = {}
    for name, text in _all_posts_texts():
        d = _fm(text, "description")
        if d:
            seen.setdefault(d.lower(), []).append(name)
    for rel in PILOT_POSTS:
        d = _fm(_read(rel), "description")
        assert d and len(d) <= 160, f"{rel}: description missing or >160"
        assert seen.get(d.lower()) == [Path(rel).name], f"{rel}: duplicate description"


# ---------------------------------------------------------------------------
# 10: internal links valid (markdown audit for these files)
# ---------------------------------------------------------------------------
def test_internal_links_audit_clean_for_pilots():
    result = audit(verbose=False)
    assert result["broken"] == 0, result["links"]
    assert result["malformed"] == 0, result["malformed_list"]
    for rel in PILOT_POSTS:
        rel_links = [ln for ln in result.get("links", []) if str(rel) in ln]
        assert not rel_links, rel_links


# ---------------------------------------------------------------------------
# scope control
# ---------------------------------------------------------------------------
def test_brand03_scope_only_three_pilot_posts():
    out = subprocess.run(["git", "diff", "HEAD", "--name-only"], cwd=str(REPO),
                         capture_output=True, text=True, encoding="utf-8")
    assert out.returncode == 0
    changed = [p for p in out.stdout.splitlines() if p]
    posts_changed = [p for p in changed if p.startswith("content/posts/")]
    # P1-GROWTH-12B authorizes the REV001 CTA post in addition to the 3 pilots
    allowed = set(PILOT_POSTS) | {"content/posts/2026-05-28-chinese-food-delivery-meituan-eleme-guide.md",
                                   # P1-GROWTH-15 REV002 CTA experiment post
                                   "content/posts/2026-07-16-china-transportation-complete-guide-trains-subways-taxis-and-more.md",
                                   # P1-GROWTH-18 internal-link additions
                                   "content/posts/2026-05-25-china-high-speed-rail-how-to-book-tickets.md",
                                   "content/posts/china-transportation-card-guide.md",
                                   # P1-GROWTH-22 authorized Alipay authority page + internal links
                                   "content/posts/alipay-for-foreigners-guide.md",
                                   "content/posts/2026-08-09-china-packing-list-2026-what-to-bring-and-what-to-leave-at-home.md",
                                   "content/posts/internet-connection-china-esim-vpn-guide.md",
                                   # P1-GROWTH-24 authorized TOP5 front-matter corruption fix
                                   "content/posts/china-extends-144-hour-visa-free-transit-policy-to-more-countries.md",
                                   # P1-GROWTH-25 authorized TOP-page title/meta update
                                   "content/posts/2026-08-01-chinabound-travel-guide-2026-08-monthly-update.md"}
    assert set(posts_changed) <= allowed, posts_changed
