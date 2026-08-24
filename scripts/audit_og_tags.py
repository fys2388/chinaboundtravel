#!/usr/bin/env python3
"""P1-GROWTH-28A: 全站 OG / Twitter Card 标签巡检（SEO 巡检的 OG 检测项）。

Checks every rendered Hugo page that carries the shared head partial:
  og:title / og:description / og:image / og:url / og:type
  twitter:card / twitter:title / twitter:description / twitter:image
plus og:image:width=1200 / og:image:height=630 (社交平台最优预览尺寸).

Tolerates Hugo --minify output (attribute quotes stripped where safe).
Pure/deterministic: no network, no LLM. Builds with `hugo --gc --minify`
into a temp directory unless --source points at an already-built site.

Output: reports/seo/OG_TAG_AUDIT.md
Exit:   0 = all pages PASS; 1 = missing/invalid tags found (workflow alert).
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parent.parent
REPORT = REPO / "reports" / "seo" / "OG_TAG_AUDIT.md"

REQUIRED_META = [
    ("property", "og:title"),
    ("property", "og:description"),
    ("property", "og:image"),
    ("property", "og:url"),
    ("property", "og:type"),
    ("name", "twitter:card"),
    ("name", "twitter:title"),
    ("name", "twitter:description"),
    ("name", "twitter:image"),
]
REQUIRED_DIMENSIONS = {
    "og:image:width": "1200",
    "og:image:height": "630",
}


def build_site() -> Path:
    out = Path(tempfile.mkdtemp(prefix="hugo_og_"))
    proc = subprocess.run(
        ["hugo", "--gc", "--minify", "--destination", str(out)],
        cwd=str(REPO), capture_output=True, text=True, encoding="utf-8",
        timeout=300,
    )
    if proc.returncode != 0:
        print(f"[OG-AUDIT] hugo build failed:\n{proc.stderr[-2000:]}")
        raise SystemExit(1)
    return out


def is_baseof_page(text: str) -> bool:
    """Only pages rendered through the shared head partial are audited.
    Hugo alias redirect stubs are minimal HTML (meta refresh) without the
    site manifest link emitted by head.html; minify may strip quotes (rel=manifest)."""
    return re.search(r'rel=["\']?manifest["\']?', text) is not None


def audit_page(text: str) -> list[str]:
    problems = []
    for attr, prop in REQUIRED_META:
        pat = rf'{attr}=["\']?{re.escape(prop)}["\']?\s+content='
        if not re.search(pat, text):
            problems.append(f"missing {prop}")
    for prop, expected in REQUIRED_DIMENSIONS.items():
        m = re.search(rf'property=["\']?{re.escape(prop)}["\']?\s+content=["\']?([0-9]+)["\']?', text)
        if not m:
            problems.append(f"missing {prop}")
        elif m.group(1) != expected:
            problems.append(f"{prop}={m.group(1)} (expected {expected})")
    return problems


def audit(site_dir: Path) -> tuple[int, list[dict]]:
    total, failed = 0, 0
    rows = []
    for html in sorted(site_dir.rglob("*.html")):
        text = html.read_text(encoding="utf-8", errors="replace")
        if not is_baseof_page(text):
            continue
        total += 1
        problems = audit_page(text)
        if problems:
            failed += 1
            rows.append({"file": html.relative_to(site_dir).as_posix(), "problems": problems})
    return total, rows


def write_report(generated: str, total: int, rows: list[dict]) -> Path:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# P1-GROWTH-28A — 全站 OG / Twitter Card 标签巡检", "",
             f"- Generated: {generated}", f"- Pages audited: {total}",
             f"- Pages with missing/invalid tags: {len(rows)}", ""]
    if rows:
        lines.append("| page | problems |")
        lines.append("|---|---|")
        for r in rows:
            lines.append(f"| {r['file']} | {'; '.join(r['problems'])} |")
        lines += ["", "**告警：存在缺失/不规范的 OG/Twitter 标签，请修复后重跑巡检。**"]
    else:
        lines.append("全部页面 PASS：og:title/description/image/url/type + twitter:card/title/description/image + 1200×630 尺寸声明完整。")
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    return REPORT


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Audit OG/Twitter Card tags on the rendered site")
    ap.add_argument("--source", type=Path, default=None,
                    help="already-built hugo output dir (skips hugo build)")
    args = ap.parse_args(argv)

    site_dir = args.source or build_site()
    if not site_dir.is_dir():
        print(f"[OG-AUDIT] source dir not found: {site_dir}")
        return 1

    total, rows = audit(site_dir)
    out = write_report(date.today().isoformat(), total, rows)
    for r in rows:
        print(f"  [FAIL] {r['file']}: {'; '.join(r['problems'])}")
    print(f"OG audit -> {out} (pages={total}, failed={len(rows)})")
    return 1 if rows else 0


if __name__ == "__main__":
    raise SystemExit(main())