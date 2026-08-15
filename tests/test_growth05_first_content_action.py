"""P1-GROWTH-05: regression tests for the first content growth actions.

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


def test_transportation_main_page_keeps_alias_for_old_slug():
    """transportation-guide-guide is an alias of the canonical transportation guide."""
    text = _read("2026-07-16-china-transportation-complete-guide-trains-subways-taxis-and-more.md")
    assert "/posts/transportation-guide-guide/" in text
    assert "/posts/china-high-speed-rail-how-to-book-tickets/" in text


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
    assert title == "China 144-Hour Visa-Free Transit (2026 Guide)"
    assert title.startswith("144") or "144-Hour" in title
    assert desc.startswith("China's 144-hour visa-free transit")
    assert len(desc) <= 160
    assert "144" in desc and "documents" in desc and "border" in desc


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
    """Body + affiliate/UTM must stay byte-identical to the GROWTH-05 experiment commit (60f1c17)."""
    name = "144-hour-visa-free-transit-guide.md"
    rel = str(POSTS.relative_to(REPO) / name).replace("\\", "/")
    old = subprocess.run(["git", "show", "60f1c17:" + rel],
                         cwd=str(REPO), capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert old.returncode == 0, old.stderr
    old_text = old.stdout
    new_text = _read(name)
    # front-matter title/description are the experiment's only allowed diffs vs pre-experiment HEAD
    base = subprocess.run(["git", "show", "HEAD:" + rel],
                          cwd=str(REPO), capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert base.returncode == 0, base.stderr
    assert old_text == new_text, "post must not be modified since the GROWTH-05 experiment commit"
    assert base.stdout == new_text, "post must stay at the committed GROWTH-05 state"
    # affiliate/UTM-bearing body identical
    old_body = old_text.split("---", 2)[-1]
    new_body = new_text.split("---", 2)[-1]
    assert old_body == new_body, "body/affiliate/UTM content changed"


def test_growth05_scope_only_allowed_objects():
    """Since the GROWTH-05 experiment commit, no layout/config and no other post may change."""
    out = subprocess.run(["git", "diff", "60f1c17..HEAD", "--name-only"], cwd=str(REPO),
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert out.returncode == 0
    changed = [p for p in out.stdout.splitlines() if p]
    # no layouts/hugo.toml/config changes since the experiment commit
    forbidden = [p for p in changed if p.startswith(("layouts/", "hugo.toml", "config/"))]
    assert not forbidden, forbidden
    # since the experiment commit, only the 144h page (GROWTH-05) and the 3
    # GROWTH-07 objects (2 WeChat + 1 transport) may have changed
    allowed = {
        "content/posts/144-hour-visa-free-transit-guide.md",
        "content/posts/2026-05-22-how-to-use-wechat-pay-as-a-foreigner.md",
        "content/posts/2026-07-02-wechat-pay-for-foreigners-step-by-step-setup-and-common-mistakes-to-avoid-guide.md",
        "content/posts/2026-05-25-china-high-speed-rail-how-to-book-tickets.md",
    }
    posts_changed = [p for p in changed if p.startswith("content/posts/")]
    extra = set(posts_changed) - allowed
    assert not extra, extra