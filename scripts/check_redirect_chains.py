#!/usr/bin/env python3
"""Audit Cloudflare Pages _redirects for redirect chains, loops and invalid finals.

Usage:
    python scripts/check_redirect_chains.py --audit
    python scripts/check_redirect_chains.py --audit --redirects static/_redirects --public public

Output per chain:
    source  ->  hop1  ->  hop2  ->  final

Checks:
  - 2-hop and 3-hop+ chains (redirect -> redirect -> 200)
  - loops (source eventually redirects back into the chain)
  - final targets that are themselves redirects
  - final targets that do not resolve to a built file (final not 200)

Domain-normalization rules (non-www -> www, HTTP -> HTTPS, wildcard splat
rules) are reported but never treated as fixable hops.
"""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REDIRECTS = REPO_ROOT / "static" / "_redirects"
REDIRECT_CODES = {"301", "302", "303", "307", "308"}


def load_rules(path=DEFAULT_REDIRECTS):
    """Parse _redirects into [(source, target, code)] (excludes comments/blanks).

    Lines with no explicit code default to Cloudflare's 302 behavior.
    """
    rules = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        if len(parts) < 2:
            continue
        code = parts[2].rstrip("!") if len(parts) > 2 else "302"
        rules.append((parts[0], parts[1], code))
    return rules


def find_chains(rules):
    """Return list of dicts for redirect chains (source -> hops -> final).

    Wildcard rules (e.g. domain normalization) cannot be resolved to a single
    target and are excluded from hop tracking; they may still appear as
    sources, but are reported separately by find_wildcard_sources().
    """
    src_map = {
        src: tgt
        for src, tgt, code in rules
        if "*" not in src and code in REDIRECT_CODES
    }
    chains = []
    for src, tgt, code in rules:
        if "*" in src or code not in REDIRECT_CODES:
            continue
        hops = []
        cur = tgt
        seen = {src}
        loop = False
        while cur in src_map and cur not in seen:
            hops.append(cur)
            seen.add(cur)
            cur = src_map[cur]
        if cur in seen and cur != tgt:
            loop = True
        if hops:
            chains.append({
                "source": src,
                "hops": hops,
                "final": cur,
                "loop": loop,
            })
    return chains


def find_wildcard_sources(rules):
    """Return sources that use a wildcard (non-fixable by normalization)."""
    return [src for src, _, code in rules if "*" in src and code in REDIRECT_CODES]


def resolve_final(url, public_dir):
    """Map a redirect target URL to a built file path (None if not found)."""
    if not public_dir or not public_dir.is_dir():
        return None  # no public build available -> cannot verify
    cleaned = url.split("#", 1)[0].split("?", 1)[0]
    if not cleaned.startswith("/"):
        return None  # external/absolute URL, not locally verifiable
    candidates = []
    if cleaned.endswith("/"):
        candidates.append(public_dir / cleaned.lstrip("/") / "index.html")
    else:
        candidates.append(public_dir / cleaned.lstrip("/"))
        candidates.append(public_dir / cleaned.lstrip("/") / "index.html")
    for c in candidates:
        try:
            if c.is_file():
                return c
        except OSError:
            continue
    return None


def audit(path=DEFAULT_REDIRECTS, public_dir=None, verbose=True):
    rules = load_rules(path)
    chains = find_chains(rules)
    wildcards = find_wildcard_sources(rules)

    problems = []
    for chain in chains:
        source = chain["source"]
        hops = chain["hops"]
        final = chain["final"]
        if chain["loop"]:
            problems.append(("loop", source, hops, final))
            continue
        if final in {r[0] for r in rules if "*" not in r[0]}:
            problems.append(("redirect-to-redirect", source, hops, final))
            continue
        resolved = resolve_final(final, public_dir)
        if public_dir and public_dir.is_dir() and resolved is None:
            problems.append(("final-not-200", source, hops, final))

    if verbose:
        for chain in chains:
            print("source:", chain["source"])
            for i, hop in enumerate(chain["hops"], 1):
                print("hop%d:  %s" % (i, hop))
            print("final:", chain["final"])
            if chain["loop"]:
                print("status: LOOP")
            print()
        if wildcards:
            print("wildcard rules (domain normalization, not fixable):")
            for w in wildcards:
                print("  ", w)
            print()
        print("chains: %d  loops: %d  final-not-200: %d"
              % (len(chains), sum(1 for p in problems if p[0] == "loop"),
                 sum(1 for p in problems if p[0] == "final-not-200")))

    return {"rules": len(rules), "chains": len(chains), "problems": problems,
            "wildcards": wildcards}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Audit _redirects for chains/loops/invalid finals")
    parser.add_argument("--audit", action="store_true", help="run audit (default)")
    parser.add_argument("--redirects", default=str(DEFAULT_REDIRECTS), help="path to _redirects")
    parser.add_argument("--public", default=None, help="path to hugo build output (public/)")
    args = parser.parse_args(argv)

    public_dir = Path(args.public) if args.public else None
    result = audit(path=Path(args.redirects), public_dir=public_dir)

    hard_fail = any(p[0] in ("loop", "redirect-to-redirect") for p in result["problems"])
    # final-not-200 is informational when public dir was provided
    return 1 if hard_fail else 0


if __name__ == "__main__":
    sys.exit(main())
