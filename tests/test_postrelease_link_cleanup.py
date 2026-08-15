"""P1-POSTRELEASE-01: low-risk link cleanup regression tests.

Covers:
  - travel-faq templates must not reference the old broken internal URL
  - cities index must link to the real Western Sichuan city page
  - Klook affiliate URL must be consistent across hugo.toml, scripts and content
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

TRAVEL_FAQ_FILES = [
    REPO_ROOT / "layouts" / "partials" / "travel-faq.html",
    REPO_ROOT / "layouts" / "shortcodes" / "travel-faq.html",
]
CITIES_LIST = REPO_ROOT / "layouts" / "cities" / "list.html"
HUGO_TOML = REPO_ROOT / "hugo.toml"
RESOURCES_INDEX = REPO_ROOT / "content" / "resources" / "_index.md"
CANONICAL_SAFETY_URL = "/posts/is-china-safe-for-tourists-2026-honest-safety-assessment/"


def test_travel_faq_no_broken_safety_link():
    """The FAQ hardcoded link must point at the canonical safety article."""
    for fp in TRAVEL_FAQ_FILES:
        text = fp.read_text(encoding="utf-8", errors="replace")
        assert "/posts/is-china-safe-for-tourists/" not in text, fp
        assert CANONICAL_SAFETY_URL in text, fp


def test_cities_index_links_western_sichuan():
    """The Western Sichuan group link must target the real city page slug."""
    text = CITIES_LIST.read_text(encoding="utf-8", errors="replace")
    assert '"link" "western-sichuan"' in text
    # link must use the link override, not the bare tag slug
    assert 'href="/cities/{{ $city.link | default $slug }}/"' in text


def test_klook_url_consistent_across_repo():
    """hugo.toml, scripts and rendered content must all use one Klook URL."""
    expected = "https://klook.tpo.li/vrPkmS2v"
    assert expected in HUGO_TOML.read_text(encoding="utf-8", errors="replace")
    # resources page must not carry the stale legacy short code
    res = RESOURCES_INDEX.read_text(encoding="utf-8", errors="replace")
    assert "klook.tpo.li/ppB4vZQ6" not in res
    assert expected in res
    # scripts/affiliate_link_builder.py must agree
    builder = (REPO_ROOT / "scripts" / "affiliate_link_builder.py").read_text(encoding="utf-8", errors="replace")
    assert "klook.tpo.li/vrPkmS2v" in builder
    assert "klook.tpo.li/ppB4vZQ6" not in builder
