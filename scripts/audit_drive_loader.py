#!/usr/bin/env python3
"""P1-GROWTH-28A: Travelpayouts Drive loader audit (content patrol integration).

Verifies:
  1. Drive bootstrap exists in layouts/partials/head.html (installed once).
  2. Drive loading is gated behind marketing-cookie consent (GDPR).
  3. Site-wide cookie consent partial is referenced from footer.html.
  4. Cookie consent emits the `cbt-gdpr-consent-change` event (Drive late-load path).
  5. After a Hugo build, every article page + the homepage render the Drive
     bootstrap exactly once (no missing / no duplicate injection).

Pure, deterministic, no network. Output: reports/operations/DRIVE_LOADER_AUDIT.md
Exit code 0 = PASS, 1 = FAIL (anomalies are surfaced for the daily alert board).
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

BLOG_ROOT = Path(__file__).resolve().parent.parent
HEAD_PARTIAL = BLOG_ROOT / "layouts" / "partials" / "head.html"
FOOTER_PARTIAL = BLOG_ROOT / "layouts" / "partials" / "footer.html"
COOKIE_PARTIAL = BLOG_ROOT / "layouts" / "partials" / "cookie-consent.html"
REPORTS = BLOG_ROOT / "reports" / "operations"
REPORTS.mkdir(parents=True, exist_ok=True)

DRIVE_URL = "emrldtp.com/NTMxNDY5.js?t=531469"
CONSENT_KEY = "cbt_gdpr_consent"
EVENT_NAME = "cbt-gdpr-consent-change"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def check_head() -> list[str]:
    """Template-level checks on the Drive bootstrap in head.html."""
    problems = []
    text = read(HEAD_PARTIAL)
    if DRIVE_URL not in text:
        problems.append("head.html: Drive URL missing")
    if text.count(DRIVE_URL) != 1:
        problems.append(f"head.html: Drive URL count={text.count(DRIVE_URL)} (expected 1)")
    if "marketingAllowed" not in text:
        problems.append("head.html: marketing-consent gate (marketingAllowed) missing")
    if CONSENT_KEY not in text:
        problems.append(f"head.html: consent key {CONSENT_KEY} missing")
    if "loadDrive" not in text:
        problems.append("head.html: loadDrive() missing")
    if EVENT_NAME not in text:
        problems.append(f"head.html: consent-change listener ({EVENT_NAME}) missing")
    return problems


def check_footer() -> list[str]:
    problems = []
    text = read(FOOTER_PARTIAL)
    if "cookie-consent.html" not in text:
        problems.append("footer.html: site-wide cookie-consent partial not referenced")
    return problems


def check_cookie_partial() -> list[str]:
    problems = []
    text = read(COOKIE_PARTIAL)
    if CONSENT_KEY not in text:
        problems.append(f"cookie-consent.html: consent key {CONSENT_KEY} missing")
    if "marketing" not in text:
        problems.append("cookie-consent.html: marketing consent option missing")
    if EVENT_NAME not in text:
        problems.append(f"cookie-consent.html: {EVENT_NAME} event not dispatched")
    return problems


def check_rendered() -> list[str]:
    """Build the site once and verify Drive bootstrap appears exactly once per page."""
    problems = []
    with tempfile.TemporaryDirectory(prefix="hugo_drive_audit_") as tmp:
        out = Path(tmp)
        proc = subprocess.run(
            ["hugo", "--gc", "--minify", "--destination", str(out)],
            cwd=str(BLOG_ROOT), capture_output=True, text=True, encoding="utf-8")
        if proc.returncode != 0:
            return [f"hugo build failed: {proc.stderr[-800:]}"]

        targets = [out / "index.html"] + sorted((out / "posts").glob("*/index.html"))
        if not targets:
            return ["hugo build produced no article pages"]
        for page in targets:
            html = page.read_text(encoding="utf-8", errors="replace")
            # Skip Hugo alias redirect stubs (meta refresh) - they are not baseof pages.
            if re.search(r'rel=["\']?manifest["\']?', html) is None:
                continue
            count = html.count(DRIVE_URL)
            if count != 1:
                rel = page.relative_to(out).as_posix()
                problems.append(f"rendered {rel}: Drive bootstrap count={count} (expected 1)")
    return problems


def write_report(problems: list[str], generated: str) -> Path:
    out = REPORTS / "DRIVE_LOADER_AUDIT.md"
    status = "PASS" if not problems else "FAIL"
    lines = [
        "# P1-GROWTH-28A — Travelpayouts Drive Loader Audit",
        "",
        f"- Generated: {generated}",
        f"- Status: **{status}**",
        "",
        "检查范围：head.html 模板、footer.html cookie 引用、cookie-consent.html 事件、" +
        "Hugo 渲染后首页与全部文章页的 Drive bootstrap 唯一性。",
        "",
        f"- Drive URL: `{DRIVE_URL}`",
        f"- Consent key: `{CONSENT_KEY}`",
        f"- Consent-change event: `{EVENT_NAME}`",
        "",
    ]
    if problems:
        lines.append(f"发现的异常（{len(problems)} 项，需进入日报待办）：")
        lines.append("")
        for p in problems:
            lines.append(f"- {p}")
        lines.append("")
        lines.append("> 日报联盟板块的「Drive状态」字段将标红，直到此处恢复 PASS。")
    else:
        lines.append("所有检查通过：Drive 脚本存在、营销 Cookie 门控生效、全站唯一注入。")
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Travelpayouts Drive loader audit")
    ap.add_argument("--skip-build", action="store_true",
                    help="skip the Hugo build step (template checks only)")
    args = ap.parse_args()

    problems = []
    problems += check_head()
    problems += check_footer()
    problems += check_cookie_partial()
    if not args.skip_build:
        problems += check_rendered()

    generated = date.today().isoformat()
    out = write_report(problems, generated)
    for p in problems:
        print(f"  [FAIL] {p}")
    print(f"drive loader audit -> {out} ({'PASS' if not problems else f'FAIL x{len(problems)}'})")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
