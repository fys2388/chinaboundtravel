#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Risk Gate - blocks automatic publishing of HIGH-risk content.

Used by .github/workflows/weekly-blog-update.yml before the commit step.

Behavior:
  - Scans changed Markdown files under content/posts/ (from `git diff --name-only`,
    or an explicit --files list).
  - If a changed post has `risk_level: high` and is NOT a draft:
      * rewrites it to draft: true + audit_status: "pending_review"
      * prints the file list
      * exits 1 (workflow stops before commit/push/deploy, error alert fires)
  - LOW / MEDIUM / missing risk_level: no action, exit 0 (existing automation works).

Design notes:
  - Only CHANGED files are evaluated, so existing live posts (e.g. old visa guides)
    do not block future automation runs.
  - Front matter is parsed with a minimal dependency-free parser (supports
    `key: value`, quoted values, and `key:` list items).

No network access, no third-party dependencies.
"""

import re
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def get_changed_posts():
    """Return changed content/posts/*.md paths relative to BASE_DIR."""
    try:
        out = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=ACMR", "--", "content/posts/"],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=30,
        )
    except Exception as exc:  # pragma: no cover - git unavailable fallback
        print(f"[risk-gate] git unavailable ({exc}); scanning all posts", file=sys.stderr)
        return [p for p in (BASE_DIR / "content" / "posts").glob("*.md") if ".archived" not in p.parts]

    paths = []
    for line in out.stdout.splitlines():
        line = line.strip()
        if line and line.endswith(".md"):
            paths.append(BASE_DIR / line)
    return paths


def parse_front_matter(text):
    """Minimal front matter parser. Returns dict of str->str (lists are joined)."""
    fm = {}
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return fm
    lines = m.group(1).splitlines()
    current_key = None
    for line in lines:
        kv = re.match(r"^([A-Za-z0-9_]+)\s*:\s*(.*)$", line)
        if kv:
            current_key = kv.group(1)
            value = kv.group(2).strip().strip('"').strip("'")
            fm[current_key] = value
        elif current_key and re.match(r"^\s*-\s+", line):
            # list item: keep first item only (enough for gate decisions)
            fm.setdefault(current_key, "")
    return fm


def classify_risk(keywords, title="", body=""):
    """Classify risk using config keywords when front matter has no risk_level."""
    import json

    try:
        with open(BASE_DIR / "config" / "content_governance.json", "r", encoding="utf-8-sig") as f:
            cfg = json.load(f)
    except (OSError, json.JSONDecodeError):
        cfg = {}
    levels = cfg.get("risk_levels", {})
    text = (title + " " + body).lower()
    for level in ("high", "medium", "low"):
        kws = [k.lower() for k in levels.get(level, {}).get("keywords", [])]
        if any(k in text for k in kws):
            return level
    return cfg.get("publish_flow", {}).get("missing_default", "medium")


def gate_file(path, rewrite=True):
    """Check one post. Returns (blocked: bool, risk: str)."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"[risk-gate] cannot read {path}: {exc}", file=sys.stderr)
        return False, "unknown"

    fm = parse_front_matter(text)
    risk = (fm.get("risk_level") or "").strip().lower()
    draft = (fm.get("draft") or "false").strip().lower()

    if not risk:
        risk = classify_risk([], title=fm.get("title", ""), body=text[:2000])

    if risk != "high":
        return False, risk

    if draft in ("true", "yes", "1"):
        return False, risk  # already a draft -> not auto-published

    if rewrite:
        updated = text.replace('draft: false', 'draft: true', 1)
        if 'draft: false' not in text:
            # fallback: insert after front matter `---` line
            parts = text.split("---", 2)
            if len(parts) >= 3:
                updated = parts[0] + "---" + parts[1] + "draft: true" + parts[2]
        if 'audit_status' in updated:
            updated = re.sub(r'audit_status:\s*["\']?[^"\'\n]*["\']?', 'audit_status: "pending_review"', updated, count=1)
        else:
            updated = updated.replace('draft: true', 'draft: true\naudit_status: "pending_review"', 1)
        path.write_text(updated, encoding="utf-8")
        print(f"[risk-gate] BLOCKED (rewritten to draft): {path} (risk_level={risk})")

    return True, risk


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    rewrite = "--no-rewrite" not in argv
    if "--files" in argv:
        idx = argv.index("--files")
        paths = [Path(p) for p in argv[idx + 1:] if p.endswith(".md")]
    else:
        paths = get_changed_posts()

    if not paths:
        print("[risk-gate] PASS (no changed posts)")
        return 0

    blocked = []
    for path in paths:
        is_blocked, risk = gate_file(path, rewrite=rewrite)
        if is_blocked:
            blocked.append((path, risk))

    if blocked:
        print("[risk-gate] FAIL: high-risk content must NOT auto-publish")
        for path, risk in blocked:
            print(f"  - {path} (risk_level={risk}) -> pending_review")
        return 1
    print("[risk-gate] PASS (no high-risk non-draft posts among changed files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
