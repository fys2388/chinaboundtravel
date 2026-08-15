#!/usr/bin/env python3
"""P1-GROWTH-02: build the content SEO inventory CSV.

Joins post front matter (content_id/title/url/date) with 28-day GSC page
performance and per-URL index inspection status.

Front matter parsing:
  - supports both YAML (---) and TOML (+++) blocks and UTF-8 BOM
  - URL resolution order: canonicalURL -> url field -> slug -> filename
    (hugo /posts/ section permalink convention)

Output: reports/seo/CONTENT_SEO_INVENTORY.csv
Read-only: never modifies front matter.
"""

import argparse
import csv
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SEO_DIR = REPO / "reports" / "seo"
SITE = "https://www.chinaboundtravel.com"

YAML_RE = re.compile(r"^---\s*\n(.*?)\n---", re.S | re.M)
TOML_RE = re.compile(r"^\+\+\+\s*\n(.*?)\n\+\+\+", re.S | re.M)


def _clean(value):
    return (value or "").strip().strip('"').strip("'")


def front_matter(path):
    text = path.read_text(encoding="utf-8-sig")
    fm = {}
    if text.startswith("---"):
        block = text.split("---", 2)[1]
        toml = False
    elif text.startswith("+++"):
        block = text.split("+++", 2)[1]
        toml = True
    else:
        return fm
    for line in block.splitlines():
        if ":" in line and not toml:
            k, _, v = line.partition(":")
            if not k.strip() or not k.strip()[0].isalnum():
                continue
            fm[k.strip()] = _clean(v)
        elif "=" in line and toml:
            k, _, v = line.partition("=")
            if not k.strip():
                continue
            fm[k.strip()] = _clean(v)
    return fm


def load_perf(path):
    perf = {}
    if path.is_file():
        with open(path, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                perf[r["keys"].rstrip("/")] = {
                    "clicks": int(float(r["clicks"])),
                    "impressions": int(float(r["impressions"])),
                    "ctr": float(r["ctr"]),
                    "position": float(r["position"]),
                }
    return perf


def load_inspection(path):
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}


def resolve_url(fm, filename):
    url = _clean(fm.get("canonicalURL"))
    if url:
        return url
    rel = _clean(fm.get("url"))
    if rel:
        return rel if rel.startswith("http") else SITE + ("" if rel.startswith("/") else "/") + rel
    slug = _clean(fm.get("slug"))
    if slug:
        return SITE + "/posts/" + slug.strip("/") + "/"
    name = filename.replace(".md", "")
    return SITE + "/posts/" + name + "/"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--posts-dir", default=str(REPO / "content" / "posts"))
    ap.add_argument("--perf", default=str(SEO_DIR / "raw_pages_28d.csv"))
    ap.add_argument("--inspection", default=str(SEO_DIR / "url_inspection_results.json"))
    ap.add_argument("--output", default=str(SEO_DIR / "CONTENT_SEO_INVENTORY.csv"))
    args = ap.parse_args(argv)

    perf = load_perf(Path(args.perf))
    inspection = load_inspection(Path(args.inspection))
    posts = sorted(Path(args.posts_dir).glob("*.md"))
    rows = []
    for p in posts:
        fm = front_matter(p)
        url = resolve_url(fm, p.name)
        key = url.rstrip("/")
        d = perf.get(key, {"clicks": 0, "impressions": 0, "ctr": 0.0, "position": 0.0})
        insp = inspection.get(url, {})
        coverage = insp.get("coverage_state", "") or ""
        if insp.get("error"):
            indexed = "UNKNOWN"
        elif not coverage:
            indexed = "UNKNOWN"
        elif "indexed" in coverage.lower() or coverage == "Submitted and indexed":
            indexed = "INDEXED"
        elif "not indexed" in coverage.lower() or "excluded by" in coverage.lower() or "unknown to google" in coverage.lower():
            indexed = "NOT_INDEXED"
        else:
            indexed = coverage or "UNKNOWN"
        date = _clean(fm.get("date", "")).split("T")[0]
        rows.append({
            "content_id": _clean(fm.get("content_id")),
            "title": _clean(fm.get("title")),
            "url": url,
            "section": "posts",
            "published_date": date,
            "clicks_28d": d["clicks"],
            "impressions_28d": d["impressions"],
            "ctr_28d": round(d["ctr"], 6),
            "position_28d": round(d["position"], 2),
            "indexed_status": indexed,
        })

    out = Path(args.output)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    from collections import Counter
    c = Counter(r["indexed_status"] for r in rows)
    print(f"wrote {out} ({len(rows)} posts) indexed_status: {dict(c)}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
