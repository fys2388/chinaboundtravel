"""V6-2: VPN tag unification (china-vpn 404 fix).

Ensures:
  - /tags/vpn/ is generated from the Internet page tag taxonomy
  - /tags/china-vpn/ 301-redirects to /tags/vpn/
  - the homepage sidebar no longer links to /tags/china-vpn/
  - no content file can generate a duplicate china-vpn taxonomy page
"""
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

REDIRECTS = (REPO_ROOT / "static" / "_redirects").read_text(encoding="utf-8")
SIDEBAR = (REPO_ROOT / "layouts" / "partials" / "sidebar-author.html").read_text(encoding="utf-8")
INTERNET_INDEX = (REPO_ROOT / "content" / "internet" / "_index.md").read_text(encoding="utf-8")


def test_homepage_sidebar_uses_vpn_tag():
    assert 'href="/tags/china-vpn/"' not in SIDEBAR
    assert 'href="/tags/vpn/"' in SIDEBAR


def test_china_vpn_301_to_vpn():
    assert "/tags/china-vpn/ /tags/vpn/ 301" in REDIRECTS


def test_vpn_taxonomy_source_present():
    # internet page carries a "VPN" tag -> Hugo renders /tags/vpn/
    assert re.search(r"^\s*-\s*VPN\s*$", INTERNET_INDEX, re.M)


def test_no_china_vpn_taxonomy_source():
    # no content file may use china-vpn as a tag (duplicate taxonomy guard)
    for p in (REPO_ROOT / "content").rglob("*.md"):
        txt = p.read_text(encoding="utf-8", errors="replace")
        assert not re.search(r"^\s*-\s*[\x22']?china-vpn[\x22']?\s*$", txt, re.M | re.I), p
