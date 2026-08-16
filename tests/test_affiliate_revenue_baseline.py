"""P1-GROWTH-09: affiliate revenue baseline tests.

Covers (pure/deterministic, no network):
- partner inventory fields + deterministic sorting
- content mapping + INLINE placement
- affiliate_click event schema (OK + TRACKING_GAP)
- NULL revenue (never fabricated)
- per-page GA4 attribution
- deterministic commercial ranking
- affiliate URL immutability (hugo.toml markers + template-driven hrefs)
- front matter parsing (YAML / TOML / BOM)
- duplicate URL dedup
- gap detection A-E
"""
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import affiliate_gap_detector as ag

HUGO_TOML = (REPO / "hugo.toml").read_text(encoding="utf-8")
SINGLE_HTML = (REPO / "layouts" / "_default" / "single.html").read_text(encoding="utf-8", errors="replace")


def sample_article(text, content_id="cbt-test1", title="Test Article", url=None):
    fm = ag.parse_front_matter(f"---\ncontent_id: \"{content_id}\"\ntitle: \"{title}\"\n---\n")
    return {
        "content_id": content_id,
        "title": title,
        "url": url or f"https://www.chinaboundtravel.com/posts/test-article/",
        "date": "2026-01-01",
        "scans": ag.scan_article(text),
        "intent": ag.infer_business_intent(url or "test", title),
        "gsc": {"clicks": 0, "impressions": 100, "ctr": 0, "position": 10},
    }


# ---------------------------------------------------------------------------
# Partner inventory
# ---------------------------------------------------------------------------
def test_partner_inventory_fields_and_sort():
    arts = [
        sample_article("{{< affiliate-hotel >}} {{< affiliate-hotel >}}"),
        sample_article("{{< affiliate-tour >}}"),
    ]
    rows = ag.partner_inventory_rows(arts, ag.PARTNER_DEFS)
    assert rows, "inventory must not be empty"
    keys = {"partner", "affiliate_key", "pages_count", "link_count",
            "affiliate_id_present", "utm_present", "tracking_present", "status"}
    assert keys <= set(rows[0])
    booking = next(r for r in rows if r["partner"] == "Booking")
    assert booking["link_count"] == 2
    # sorted by link_count desc
    counts = [r["link_count"] for r in rows]
    assert counts == sorted(counts, reverse=True)


def test_partner_inventory_deterministic():
    arts = [sample_article("{{< affiliate-esim >}}")]
    assert ag.partner_inventory_rows(arts, ag.PARTNER_DEFS) == ag.partner_inventory_rows(arts, ag.PARTNER_DEFS)


# ---------------------------------------------------------------------------
# Content mapping
# ---------------------------------------------------------------------------
def test_content_map_inline_placement():
    arts = [sample_article("{{< affiliate-hotel >}}")]
    rows = ag.content_map_rows(arts, ag.PARTNER_DEFS)
    assert any(r["content_id"] == "cbt-test1" and r["partner"] == "Booking" and r["placement"] == "INLINE"
               for r in rows)


def test_scan_article_detects_shortcodes_and_inline():
    text = ("{{< affiliate-hotel >}} {{< affiliate-tour >}} "
            "https://www.booking.com/index.html?aid=730795 https://klook.tpo.li/vrPkmS2v")
    scans = ag.scan_article(text)
    assert scans["shortcodes"]["hotel"] == 1
    assert scans["shortcodes"]["klook"] == 1
    assert scans["inline_urls"].get("hotel", 0) >= 1
    assert scans["inline_urls"].get("klook", 0) >= 1


# ---------------------------------------------------------------------------
# Tracking schema
# ---------------------------------------------------------------------------
def test_tracking_schema_ok():
    res = ag.tracking_schema_check(SINGLE_HTML)
    assert res["status"] == "OK"
    assert res["missing_fields"] == []
    assert res["event_name"] == "affiliate_click"


def test_tracking_schema_gap_when_missing_fields():
    html = "<script>gtag('event', 'affiliate_click', {})</script>"
    res = ag.tracking_schema_check(html)
    assert res["status"] == "TRACKING_GAP"
    assert set(res["missing_fields"]) >= {"content_id", "partner", "placement"}


# ---------------------------------------------------------------------------
# Revenue baseline: NULL revenue + per-page attribution
# ---------------------------------------------------------------------------
def test_baseline_null_revenue_never_fabricated():
    arts = [sample_article("{{< affiliate-hotel >}}")]
    rows = ag.baseline_rows(arts, ag.PARTNER_DEFS, {})
    assert rows[0]["revenue_28d"] == "NULL"
    assert rows[0]["affiliate_sessions_28d"] == "NULL"


def test_baseline_per_page_ga4_attribution():
    arts = [
        sample_article("{{< affiliate-hotel >}}", content_id="cbt-1",
                       url="https://www.chinaboundtravel.com/posts/visa-guide/"),
        sample_article("{{< affiliate-hotel >}}", content_id="cbt-2",
                       url="https://www.chinaboundtravel.com/posts/other/"),
    ]
    rows = ag.baseline_rows(arts, ag.PARTNER_DEFS, {"/posts/visa-guide/": 3})
    by_cid = {r["content_id"]: r for r in rows}
    assert by_cid["cbt-1"]["affiliate_clicks_28d"] == 3
    assert by_cid["cbt-2"]["affiliate_clicks_28d"] == 0


def test_baseline_status_not_available_when_no_ga4():
    arts = [sample_article("{{< affiliate-hotel >}}")]
    rows = ag.baseline_rows(arts, ag.PARTNER_DEFS, None)
    assert rows[0]["status"] == "NOT_AVAILABLE"


# ---------------------------------------------------------------------------
# Commercial ranking
# ---------------------------------------------------------------------------
def test_commercial_ranking_deterministic_and_weights_intent():
    arts = [
        sample_article("{{< affiliate-hotel >}}", content_id="cbt-v",
                       url="https://www.chinaboundtravel.com/posts/china-visa-guide/",
                       title="China Visa Guide"),
        sample_article("", content_id="cbt-g",
                       url="https://www.chinaboundtravel.com/posts/food-guide/",
                       title="Food Guide"),
    ]
    arts[0]["gsc"] = {"clicks": 0, "impressions": 100}
    arts[1]["gsc"] = {"clicks": 0, "impressions": 100}
    r1 = ag.commercial_ranking(arts)
    assert r1 == ag.commercial_ranking(arts)
    assert r1[0]["content_id"] == "cbt-v"  # VISA intent weighted above GENERAL


# ---------------------------------------------------------------------------
# No affiliate URL mutation
# ---------------------------------------------------------------------------
def test_affiliate_urls_unchanged_in_config():
    for marker in ("aid=730795", "aff_id=150687", "klook.tpo.li",
                   "safetywing.com/nomad-insurance?referenceID=26548976",
                   "www.aviasales.com/?marker=730795"):
        assert marker in HUGO_TOML


def test_single_html_uses_template_driven_urls():
    for key in ("esim", "vpn", "hotel", "klook"):
        assert "{{{{ .Site.Params.affiliate.{key} }}}}".format(key=key) in SINGLE_HTML


# ---------------------------------------------------------------------------
# Front matter parsing robustness
# ---------------------------------------------------------------------------
def test_front_matter_yaml():
    fm = ag.parse_front_matter('---\ncontent_id: "cbt-abc"\ntitle: "X"\ndraft: false\n---\nbody')
    assert fm["content_id"] == "cbt-abc"


def test_front_matter_toml():
    fm = ag.parse_front_matter('+++\ncontent_id = "cbt-def"\ntitle = "Y"\n+++\nbody')
    assert fm["content_id"] == "cbt-def"


def test_front_matter_bom():
    fm = ag.parse_front_matter('\ufeff---\ncontent_id: "cbt-bom"\ntitle: "Z"\n---\nbody')
    assert fm["content_id"] == "cbt-bom"


def test_url_from_slug_or_canonical():
    fm = {"canonicalURL": "https://www.chinaboundtravel.com/posts/x/"}
    assert ag.url_from_front_matter(fm, "2026-01-01-x.md") == "https://www.chinaboundtravel.com/posts/x/"
    fm2 = {"slug": "my-slug"}
    assert ag.url_from_front_matter(fm2, "2026-01-01-whatever.md") == \
        "https://www.chinaboundtravel.com/posts/my-slug/"
    fm3 = {}
    assert ag.url_from_front_matter(fm3, "2026-01-01-dated-file.md") == \
        "https://www.chinaboundtravel.com/posts/dated-file/"


# ---------------------------------------------------------------------------
# Duplicate dedup
# ---------------------------------------------------------------------------
def test_load_articles_dedup_by_url(tmp_path):
    (tmp_path / "a.md").write_text("---\ncontent_id: \"cbt-a\"\ncanonicalURL: \"https://www.chinaboundtravel.com/posts/same/\"\n---\nbody",
                                   encoding="utf-8")
    (tmp_path / "b.md").write_text("---\ncontent_id: \"cbt-b\"\ncanonicalURL: \"https://www.chinaboundtravel.com/posts/same/\"\n---\nbody",
                                   encoding="utf-8")
    articles, duplicates = ag.load_articles(tmp_path, {})
    assert len(articles) == 1
    assert len(duplicates) == 1


# ---------------------------------------------------------------------------
# Gap detection
# ---------------------------------------------------------------------------
def test_gap_detection_covers_types():
    a = sample_article("{{< affiliate-hotel >}}", content_id="cbt-imp",
                       url="https://www.chinaboundtravel.com/posts/china-visa-guide/", title="Visa")
    a["gsc"] = {"clicks": 0, "impressions": 200}
    b = sample_article("", content_id="cbt-noaff",
                       url="https://www.chinaboundtravel.com/posts/china-visa-free/", title="Visa Policy")
    b["gsc"] = {"clicks": 0, "impressions": 50}
    gaps = ag.gap_detection([a, b], ag.PARTNER_DEFS)
    types = {g["type"] for g in gaps}
    assert "C_HIGH_IMPRESSION_ZERO_CLICK" in types
    assert "A_HIGH_INTENT_NO_AFFILIATE" in types
