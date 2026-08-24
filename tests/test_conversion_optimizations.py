# -*- coding: utf-8 -*-
"""Tests for the conversion & ranking optimizations (Task 1-3).

Covers:
  - affiliate_link_builder: theme->product matching, placements, coverage
  - affiliate_product_stats: per-product CTA stats
  - content_category_normalizer: category mapping, tag normalization
  - content_deep_optimizer: content padding, internal links, title/meta
  - generate_lead_magnet_pdf: lead magnet PDF generation
  - gsc_index_submit: optimized-page URL extraction (no network)

No real network calls: requests are mocked where needed.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import affiliate_link_builder as alb  # noqa: E402
import affiliate_product_stats as aps  # noqa: E402
import content_category_normalizer as ccn  # noqa: E402
import content_deep_optimizer as cdo  # noqa: E402
import generate_lead_magnet_pdf as glm  # noqa: E402


# ============================================================
# Task 1: affiliate_link_builder
# ============================================================

ARTICLE_VISA = {
    "title": "China 144-Hour Visa-Free Transit Guide",
    "description": "Who qualifies, eligible cities, documents.",
    "body": "visa-free transit 144-hour entry requirements immigration passport border " * 5,
}
ARTICLE_CITY = {
    "title": "Beijing Travel Guide",
    "description": "Hotels, day trips, attractions.",
    "body": "beijing city destination hotel attraction sightseeing itinerary" * 5,
}
ARTICLE_TRANSPORT = {
    "title": "China High-Speed Rail Guide",
    "description": "Booking tickets and stations.",
    "body": "train high-speed rail subway station transport booking" * 5,
}


def test_detect_themes_visa():
    themes = alb.detect_themes(ARTICLE_VISA["title"], ARTICLE_VISA["body"])
    assert "visa" in themes


def test_products_for_visa():
    products = alb.products_for(ARTICLE_VISA)
    assert "flight" in products and "insurance" in products and "esim" in products


def test_products_for_city():
    products = alb.products_for(ARTICLE_CITY)
    assert "hotel" in products and "tour" in products


def test_products_for_transport():
    products = alb.products_for(ARTICLE_TRANSPORT)
    assert "flight" in products


def test_soft_recommend_shortcode_valid():
    s = alb.soft_recommend_shortcode("klook", "city", "article_mid_1", "ctx")
    open_line = [ln for ln in s.splitlines() if "soft-recommend partner" in ln][0]
    assert open_line.rstrip().endswith(">}}")
    assert "partner=\"klook\"" in open_line


def test_resolve_key_maps_tour_to_klook():
    assert alb.resolve_key("tour") == "klook"
    assert alb.resolve_key("insurance") == "safetywing"
    assert alb.resolve_key("hotel") == "hotel"


def test_build_placements_skips_existing():
    products = ["flight", "insurance", "esim"]
    placements = alb.build_placements(ARTICLE_VISA, products, existing={"flight", "insurance"})
    # esim missing -> 1 placement
    assert len(placements) == 1
    assert placements[0][0] == "esim"


def test_insert_soft_recommends_preserves_frontmatter():
    md = "---\ntitle: X\n---\n\n## Intro\n\nbody text here\n\n## More\n\nmore body\n"
    pl = [("esim", "article_mid_1"), ("klook", "article_mid_2")]
    out = alb.insert_soft_recommends(md, pl, "visa")
    assert out.startswith("---")
    # count open tags (each block has one "soft-recommend partner=")
    assert out.count("soft-recommend partner=") == 2


def test_affiliate_urls_parsed_from_hugo():
    urls = alb.parse_affiliate_urls()
    assert isinstance(urls, dict)
    assert "esim" in urls or "hotel" in urls


def test_known_tour_url_present():
    # consistency with existing test_postrelease_link_cleanup.py
    assert alb.KNOWN_TOUR_URL == "https://klook.tpo.li/vrPkmS2v"
    src = (REPO_ROOT / "scripts" / "affiliate_link_builder.py").read_text(encoding="utf-8")
    assert "klook.tpo.li/vrPkmS2v" in src


# ============================================================
# Task 1b: affiliate_product_stats
# ============================================================


def test_product_distribution_shape():
    dist = aps.product_distribution()
    assert set(dist) == {"flight", "insurance", "esim", "hotel", "tour"}
    for p in dist:
        assert "posts" in dist[p] and "cta_count" in dist[p]


def test_scan_article_ctas():
    text = "{{< affiliate-hotel >}} {{< affiliate-tour >}} {{< soft-recommend partner=\"klook\" >}}"
    counts = aps.scan_article_ctas(text)
    assert counts["hotel"] == 1
    assert counts["tour"] >= 1


# ============================================================
# Task 3a: content_category_normalizer
# ============================================================


def test_normalize_tag_consistency():
    assert ccn.normalize_tag("ChinaTravel") == "ChinaTravel"
    assert ccn.normalize_tag("china travel tips") == "China Travel Tips"
    assert ccn.normalize_tag("shanghai") == "Shanghai"


def test_category_map_merges():
    assert ccn.CATEGORY_MAP["china travel guide"] == "travel-tips"
    assert ccn.CATEGORY_MAP["china itinerary"] == "itinerary"


def test_split_frontmatter_yaml_and_toml():
    yfm, ybody, ydelim = ccn.split_frontmatter("---\ntitle: X\n---\nbody")
    assert ydelim == "---" and ybody == "body"
    tfm, tbody, tdelim = ccn.split_frontmatter("+++\ntitle = \"X\"\n+++\nbody")
    assert tdelim == "+++" and tbody == "body"


def test_read_frontmatter_array_yaml():
    fm = "categories:\n  - Visa\n  - Travel\n"
    assert ccn.read_frontmatter_array(fm, "categories") == ["Visa", "Travel"]


def test_read_frontmatter_array_toml():
    fm = 'categories = ["Visa", "Travel"]'
    assert ccn.read_frontmatter_array(fm, "categories") == ["Visa", "Travel"]


def test_set_frontmatter_array_toml_above_table():
    fm = 'title = "X"\n[cover]\n  image = "/img.jpg"'
    new = ccn.set_frontmatter_array(fm, "categories", ["visa"], "+++")
    # categories must be above [cover]
    assert new.index("categories") < new.index("[cover]")


def test_detect_category_prefers_strong_topic():
    cats = ccn.detect_category_from_text("visa-free transit 144-hour entry " * 4)
    assert "visa" in cats


# ============================================================
# Task 3b: content_deep_optimizer
# ============================================================


def test_word_count():
    assert cdo.word_count("hello world foo") == 3


def test_append_content_adds_sections():
    body = "short body text"
    new, added = cdo.append_content(body, "visa")
    assert added >= 1
    assert cdo.word_count(new) > cdo.word_count(body)


def test_count_internal_links():
    body = "[a](/posts/x/) [b](/posts/y/) plain text"
    assert cdo.count_internal_links(body) == 2


def test_post_url_strips_date_prefix():
    assert cdo.post_url("2026-05-22-slug-name") == "/posts/slug-name/"
    assert cdo.post_url("plain-slug") == "/posts/plain-slug/"


def test_generic_sections_present_for_all_keys():
    for key in ("visa", "payment", "transport", "safety", "packing"):
        assert key in cdo.GENERIC_SECTIONS
        assert len(cdo.GENERIC_SECTIONS[key]) >= 3


# ============================================================
# Task 2a: generate_lead_magnet_pdf
# ============================================================


def test_lead_magnet_pdf_generated(tmp_path):
    out = glm.build_pdf()
    assert out.exists()
    assert out.stat().st_size > 1000
    # PDF magic header
    assert out.read_bytes()[:5] == b"%PDF-"


# ============================================================
# Task 3c: gsc_index_submit optimized URLs
# ============================================================


def test_optimized_page_urls_from_report():
    import gsc_index_submit as gis
    s = gis.GSCIndexSubmitter(site_url="https://example.com")
    urls = s._optimized_page_urls()
    assert isinstance(urls, list)
    for u in urls:
        assert u.startswith("https://example.com/posts/")
