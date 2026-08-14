"""V6-2: redirect chain audit.

Ensures the Cloudflare _redirects file has:
  - zero redirect chains (301 -> 301 -> 200)
  - zero loops
  - finals that are not themselves redirect sources
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from check_redirect_chains import audit, find_chains, load_rules


def test_no_redirect_chains():
    rules = load_rules(REPO_ROOT / "static" / "_redirects")
    assert find_chains(rules) == []


def test_no_loops():
    result = audit(path=REPO_ROOT / "static" / "_redirects", verbose=False)
    assert not [p for p in result["problems"] if p[0] == "loop"]


def test_finals_are_not_redirect_sources():
    rules = load_rules(REPO_ROOT / "static" / "_redirects")
    codes = {"301", "302", "303", "307", "308"}
    src_map = {src for src, _, code in rules if "*" not in src and code.rstrip("!") in codes}
    chains = find_chains(rules)
    assert chains == []
    for src, tgt, code in rules:
        if "*" in src or code.rstrip("!") not in codes:
            continue
        assert tgt not in src_map, "redirect target is itself a redirect source: %s -> %s" % (src, tgt)
