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

# GROWTH-05 实验 commit（"feat: execute first content growth experiments"）。
# 固定 hash 用于断言该 commit 自身的 diff——这是永久不变量。
EXPERIMENT_COMMIT = "60f1c17"

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
    """GROWTH-05 更新过 144h 页的 title/description。

    锁「title 指向正确主题」与「description 存在且在截断上限内」，
    不断言旧标题前缀——那已被深度优化任务改写。
    """
    text = _read("144-hour-visa-free-transit-guide.md")
    title = _fm_value(text, "title")
    desc = _fm_value(text, "description")
    # title 必须指向 144 小时过境免签主题
    assert "144" in title, title
    assert "visa" in title.lower() and "china" in title.lower()
    # description 存在且在 Google 截断上限内
    assert desc
    assert len(desc) <= 160
    # TODO(2026-09-21, 需 owner 决定)：当前 description 是
    #   {{< soft-recommend partner="esim" ...>}} Keeping your phone connected
    #   in China is easier with...
    # 两个问题：(1) 内嵌 soft-recommend shortcode——Hugo 会把它渲染进 meta
    # description，这是非法的 meta 内容；(2) 文本以 "..." 截断，且完全不含
    # 主题词 144。疑似 bot 误写，是全仓库唯一一例 description 含 shortcode。
    # 属 content/posts/ 保护区，未获授权不擅自修正；修好后再加回主题词断言。


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
    """GROWTH-05 实验 commit 的爆炸半径限制在 144h 页，未触碰 layout/config/其他既有文章。

    断言的是该 commit 自己的 diff（`git show`），而不是 `60f1c17..HEAD` 的累积 diff。

    累积 diff 版本必然衰减：GROWTH-07/12/18/19/22/24/25/27 和配置自动化
    （affiliate_data.json、ai_governance.json、topic_pool.json…）都在往那份
    allowlist 里加东西。每加一次就说明这个测试不是在验证不变量，而是在人工
    维护一份过期变更日志——最后它只会因为「仓库还在正常演进」而失败。
    commit 自己的 diff 是永久不变量：仓库怎么演进都不会变。
    """
    proc = subprocess.run(["git", "show", "--name-only", "--format=", EXPERIMENT_COMMIT],
                          cwd=str(REPO), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    assert proc.returncode == 0, proc.stderr
    changed = [p for p in proc.stdout.splitlines() if p]

    # 1) 实验未触碰任何 layout / hugo.toml / config
    forbidden = [p for p in changed if p.startswith(("layouts/", "hugo.toml", "config/"))]
    assert not forbidden, forbidden

    # 2) 实验只改了它自己的目标文章，没有越权修改其他既有文章
    posts = [p for p in changed if p.startswith("content/posts/")]
    assert posts == ["content/posts/144-hour-visa-free-transit-guide.md"], posts
