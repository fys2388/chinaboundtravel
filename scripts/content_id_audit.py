#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Content ID audit & backfill.

Content IDs are stable, unique identifiers for content (the foundation for
affiliate attribution, analytics joins and future data tooling).

Design:
  - ID format: cbt-<12 hex chars>.
  - ID anchor priority: canonical URL -> canonical -> slug -> file stem.
    If the preferred anchor collides with an already-assigned ID (historical
    variant articles can share a canonical URL), the next anchor is used so IDs
    stay unique. IDs are derived once and frozen: the audit NEVER regenerates
    existing content_id values; backfill only fills missing ones.
  - Supports YAML (---) and TOML-style (+++) front matter, CRLF or LF.

Commands:
  python scripts/content_id_audit.py audit            # validate + report
  python scripts/content_id_audit.py backfill         # add missing content_id
  python scripts/content_id_audit.py audit --strict   # exit 1 on any issue
"""

import argparse
import hashlib
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
POSTS_DIR = BASE_DIR / "content" / "posts"
ID_RE = re.compile(r"^cbt-[0-9a-f]{12}$")


def _split_front_matter(text):
    """Return (delimiter, inner_text) for --- (YAML) or +++ (TOML) front matter."""
    if text.startswith("\ufeff"):  # tolerate UTF-8 BOM
        text = text[1:]
    m = re.match(r"^(---|\+\+\+)\r?\n(.*?)\r?\n\1", text, re.DOTALL)
    if m:
        return m.group(1), m.group(2)
    return None, None


def _front_matter_dict(text):
    delim, inner = _split_front_matter(text)
    if inner is None:
        return {}, None
    data = {}
    lines = inner.splitlines()
    for line in lines:
        kv = re.match(r"^([A-Za-z0-9_]+)\s*(?::|=)\s*(.*)$", line)
        if kv:
            key = kv.group(1)
            value = kv.group(2).strip().strip('"').strip("'")
            if value:
                data[key] = value
    return data, delim


def collect_posts():
    if not POSTS_DIR.exists():
        return []
    return sorted(POSTS_DIR.glob("*.md"))


def _candidate(anchor):
    digest = hashlib.sha256(anchor.encode("utf-8")).hexdigest()
    return "cbt-" + digest[:12]


def derive_id(post_path, fm, used_ids):
    """Pick the first anchor that yields an unused ID (deterministic)."""
    anchors = [fm.get("canonicalURL"), fm.get("canonical"), fm.get("slug"), post_path.stem]
    for anchor in anchors:
        if not anchor:
            continue
        cid = _candidate(anchor)
        if cid not in used_ids:
            return cid
    return _candidate(str(post_path.resolve()))


def add_content_id(post_path, fm, delim, used_ids, dry_run=False):
    """Add a content_id line into front matter if missing. Returns new_id or None."""
    current = fm.get("content_id")
    if current:
        return None
    new_id = derive_id(post_path, fm, used_ids)
    text = post_path.read_text(encoding="utf-8")
    delim, inner = _split_front_matter(text)
    if inner is None:
        return None
    # Mixed line endings exist in this repo: try CRLF then LF for the front matter.
    updated = text
    kv = 'content_id = "' + new_id + '"' if delim == "+++" else 'content_id: "' + new_id + '"'
    for eol in ("\r\n", "\n"):
        target = delim + eol + inner
        if target in text:
            new_inner = kv + eol + inner
            updated = text.replace(target, delim + eol + new_inner, 1)
            break
    if updated == text:
        return None
    if not dry_run:
        post_path.write_text(updated, encoding="utf-8", newline="")
    return new_id


def audit(strict=False, dry_run=False, backfill=False):
    posts = collect_posts()
    issues = []
    ids = {}
    missing = []
    malformed = []
    backfilled = 0

    for post in posts:
        text = post.read_text(encoding="utf-8")
        fm, delim = _front_matter_dict(text)
        cid = (fm.get("content_id") or "").strip()
        if not cid:
            missing.append(post)
            if backfill:
                new_id = add_content_id(post, fm, delim, ids, dry_run=dry_run)
                if new_id:
                    cid = new_id
                    backfilled += 1
                    print(f"[backfill] {post.name}: content_id={cid}")
                else:
                    issues.append(f"[missing] could not backfill: {post.name}")
                    continue
            else:
                issues.append(f"[missing] {post.name}")
                continue
        if not ID_RE.match(cid):
            malformed.append((post, cid))
            issues.append(f"[malformed] {post.name}: {cid!r}")
            continue
        if cid in ids:
            issues.append(f"[duplicate] content_id={cid} on {ids[cid]} and {post.name}")
        else:
            ids[cid] = post.name

    print(f"\n===== CONTENT ID AUDIT =====")
    print(f"Posts scanned : {len(posts)}")
    print(f"With content_id: {len(ids)}")
    print(f"Missing       : {len(missing)}")
    print(f"Malformed     : {len(malformed)}")
    print(f"Backfilled    : {backfilled}")
    dup_count = sum(1 for i in issues if i.startswith("[duplicate]"))
    print(f"Duplicates    : {dup_count}")

    if issues:
        for issue in issues:
            print(f"  - {issue}")
        if strict:
            print("RESULT: FAIL")
            return 1
        print("RESULT: WARN (issues found; run with --strict to fail)")
        return 0

    print("RESULT: PASS")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Content ID audit/backfill")
    parser.add_argument("command", choices=["audit", "backfill"], default="audit", nargs="?")
    parser.add_argument("--strict", action="store_true", help="exit 1 on any issue")
    parser.add_argument("--dry-run", action="store_true", help="do not write files")
    args = parser.parse_args()

    backfill = args.command == "backfill"
    return audit(strict=args.strict, dry_run=args.dry_run, backfill=backfill)


if __name__ == "__main__":
    raise SystemExit(main())