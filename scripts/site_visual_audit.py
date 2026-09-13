#!/usr/bin/env python3
"""Run browser checks at desktop and mobile sizes and keep review screenshots."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

try:
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright
except ImportError:
    PlaywrightError = RuntimeError
    sync_playwright = None


SEVERITY_RANK = {"P0": 0, "P1": 1, "P2": 2}
GA_MEASUREMENT_ID_RE = re.compile(r"\bG-[A-Z0-9]{4,}\b", re.IGNORECASE)


def make_issue(
    severity: str,
    issue_type: str,
    page: str,
    viewport: str,
    evidence: str,
    action: str,
) -> dict:
    ident = hashlib.sha1(
        f"visual|{issue_type}|{page}|{viewport}|{evidence}".encode("utf-8")
    ).hexdigest()[:16]
    return {
        "id": ident,
        "severity": severity,
        "source": "visual",
        "type": issue_type,
        "page": page,
        "viewport": viewport,
        "evidence": evidence,
        "recommended_action": action,
    }


def parse_color(value: str) -> tuple[int, int, int, float] | None:
    match = re.match(
        r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*([\d.]+))?\s*\)",
        value or "",
    )
    if not match:
        return None
    alpha = float(match.group(4)) if match.group(4) is not None else 1.0
    return int(match.group(1)), int(match.group(2)), int(match.group(3)), alpha


def luminance(rgb: tuple[int, int, int, float]) -> float:
    channels = []
    for value in rgb[:3]:
        channel = value / 255
        channels.append(
            channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
        )
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast_ratio(foreground: str, background: str) -> float | None:
    fg = parse_color(foreground)
    bg = parse_color(background)
    if not fg or not bg or bg[3] < 0.95:
        return None
    first, second = luminance(fg), luminance(bg)
    lighter, darker = max(first, second), min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


def sitemap_pages(base_url: str, max_pages: int, timeout: int) -> list[str]:
    base_url = base_url.rstrip("/") + "/"
    local_request = urlparse(base_url).hostname in {"127.0.0.1", "localhost", "::1"}
    preferred = [
        base_url,
        urljoin(base_url, "pricing/"),
        urljoin(base_url, "posts/alipay-for-foreigners-guide/"),
        urljoin(base_url, "posts/chinabound-travel-guide-2026-09-monthly-update/"),
    ]
    try:
        response = requests.get(
            urljoin(base_url, "sitemap.xml"),
            timeout=timeout,
            headers={"User-Agent": "ChinaBound-Visual-Audit/1.0"},
            proxies={"http": None, "https": None} if local_request else None,
        )
        response.raise_for_status()
        root = ET.fromstring(response.content)
        namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        urls = sorted(
            {
                node.text.strip()
                for node in root.findall(".//sm:loc", namespace)
                if node.text and node.text.strip()
            }
        )
    except Exception:
        urls = []

    selected: list[str] = []
    for url in preferred:
        if url not in selected:
            selected.append(url)
    for url in urls:
        if "/posts/" not in url:
            continue
        if url not in selected:
            selected.append(url)
        if len(selected) >= max_pages:
            break
    for url in urls:
        if url not in selected:
            selected.append(url)
        if len(selected) >= max_pages:
            break
    return selected[:max_pages]


def slug_for_url(url: str) -> str:
    path = urlparse(url).path.strip("/")
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", path).strip("-") or "home"


def pixel_diff_ratio(current: Path, baseline: Path) -> float | None:
    try:
        from PIL import Image, ImageChops
    except ImportError:
        return None
    if not baseline.exists():
        return None
    with Image.open(current).convert("RGB") as current_image, Image.open(
        baseline
    ).convert("RGB") as baseline_image:
        if current_image.size != baseline_image.size:
            return 1.0
        diff = ImageChops.difference(current_image, baseline_image)
        changed = sum(1 for pixel in diff.getdata() if pixel != (0, 0, 0))
        total = current_image.width * current_image.height
        return changed / total if total else 0.0


def audit_page(page, url: str, viewport: dict, timeout: int) -> tuple[list[dict], dict]:
    issues: list[dict] = []
    console_errors: list[str] = []
    page_errors: list[str] = []
    failed_requests: list[str] = []
    analytics_ids: set[str] = set()
    analytics_requests: list[str] = []
    origin = f"{urlparse(url).scheme}://{urlparse(url).netloc}"

    def on_console(message) -> None:
        if message.type == "error":
            console_errors.append(message.text[:240])

    def on_page_error(error) -> None:
        page_errors.append(str(error)[:240])

    def on_request_failed(request) -> None:
        if request.url.startswith(origin):
            failed_requests.append(f"{request.url}: {request.failure or 'failed'}")

    def on_request(request) -> None:
        ids = {match.upper() for match in GA_MEASUREMENT_ID_RE.findall(request.url)}
        if not ids:
            return
        analytics_ids.update(ids)
        if len(analytics_requests) < 5:
            analytics_requests.append(request.url[:300])

    page.on("console", on_console)
    page.on("pageerror", on_page_error)
    page.on("requestfailed", on_request_failed)
    page.on("request", on_request)
    response = page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
    page.wait_for_timeout(1000)
    viewport_name = viewport["name"]

    status = response.status if response else 0
    if status == 0 or status >= 400:
        issues.append(
            make_issue(
                "P0",
                "page_status",
                urlparse(url).path or "/",
                viewport_name,
                f"HTTP {status or 'ERR'}",
                "Restore the page before deployment.",
            )
        )

    metrics = page.evaluate(
        """
        () => {
          const visible = (el) => {
            if (!el) return false;
            const style = getComputedStyle(el);
            const rect = el.getBoundingClientRect();
            return style.display !== 'none' && style.visibility !== 'hidden' &&
                   Number(style.opacity) > 0 && rect.width > 0 && rect.height > 0;
          };
          const effectiveBackground = (el) => {
            let current = el;
            while (current) {
              const value = getComputedStyle(current).backgroundColor;
              if (value && value !== 'rgba(0, 0, 0, 0)' && value !== 'transparent') {
                return value;
              }
              current = current.parentElement;
            }
            return 'rgb(255, 255, 255)';
          };
          const hamburgers = ['#nav-toggle', '.hamburger-btn']
            .map(selector => document.querySelector(selector))
            .filter(visible)
            .map(el => el.id ? `#${el.id}` : el.className);
          const brokenImages = [...document.images]
            .filter(img => img.complete && img.naturalWidth === 0)
            .map(img => img.currentSrc || img.src);
          const shareContrast = [...document.querySelectorAll('.share-btn')]
            .filter(visible)
            .map(el => ({
              label: (el.textContent || '').trim(),
              color: getComputedStyle(el).color,
              background: effectiveBackground(el)
            }));
          return {
            width: window.innerWidth,
            scrollWidth: document.documentElement.scrollWidth,
            hamburgers,
            brokenImages,
            shareContrast
          };
        }
        """
    )

    if metrics["scrollWidth"] > metrics["width"] + 1:
        issues.append(
            make_issue(
                "P0",
                "horizontal_overflow",
                urlparse(url).path or "/",
                viewport_name,
                f"scrollWidth={metrics['scrollWidth']} viewport={metrics['width']}",
                "Fix the element that exceeds the viewport width.",
            )
        )

    if metrics["brokenImages"]:
        issues.append(
            make_issue(
                "P0",
                "broken_image",
                urlparse(url).path or "/",
                viewport_name,
                ", ".join(metrics["brokenImages"][:5]),
                "Restore the image or update its URL.",
            )
        )

    if viewport_name == "desktop" and metrics["hamburgers"]:
        issues.append(
            make_issue(
                "P1",
                "desktop_hamburger_visible",
                urlparse(url).path or "/",
                viewport_name,
                ", ".join(metrics["hamburgers"]),
                "Hide the mobile navigation toggle at desktop breakpoints.",
            )
        )

    if viewport_name == "desktop" and len(analytics_ids) > 1:
        issues.append(
            make_issue(
                "P2",
                "multiple_ga_measurement_ids",
                urlparse(url).path or "/",
                viewport_name,
                (
                    f"network GA IDs: {', '.join(sorted(analytics_ids))}; "
                    f"requests: {' | '.join(analytics_requests)}"
                ),
                (
                    "Keep one GA4 measurement ID per page and remove the "
                    "duplicate edge, WordPress, or third-party tag injection."
                ),
            )
        )

    for item in metrics["shareContrast"]:
        ratio = contrast_ratio(item["color"], item["background"])
        if ratio is not None and ratio < 4.5:
            issues.append(
                make_issue(
                    "P1",
                    "share_button_contrast",
                    urlparse(url).path or "/",
                    viewport_name,
                    f"{item['label'] or 'share button'} ratio={ratio:.2f}",
                    "Use a darker background or adjust label color to reach WCAG AA.",
                )
            )

    if page_errors:
        issues.append(
            make_issue(
                "P1",
                "page_javascript_error",
                urlparse(url).path or "/",
                viewport_name,
                " | ".join(page_errors[:3]),
                "Fix the uncaught browser error.",
            )
        )
    if failed_requests:
        issues.append(
            make_issue(
                "P1",
                "same_origin_request_failed",
                urlparse(url).path or "/",
                viewport_name,
                " | ".join(failed_requests[:5]),
                "Restore the missing same-origin resource.",
            )
        )
    if console_errors:
        issues.append(
            make_issue(
                "P2",
                "console_error",
                urlparse(url).path or "/",
                viewport_name,
                " | ".join(console_errors[:3]),
                "Remove avoidable browser console errors.",
            )
        )

    return issues, {
        "status": status,
        "console_errors": len(console_errors),
        "failed_requests": len(failed_requests),
        "analytics_ids": sorted(analytics_ids),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="https://www.chinaboundtravel.com")
    parser.add_argument("--output", default="reports/quality/visual_audit.json")
    parser.add_argument("--screenshot-dir", default="reports/quality/screenshots")
    parser.add_argument("--baseline-dir", default="")
    parser.add_argument("--max-pages", type=int, default=6)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--enforce-baseline", action="store_true")
    return parser.parse_args()


def main() -> int:
    if sync_playwright is None:
        print(
            "playwright is not installed; run: pip install playwright && "
            "python -m playwright install chromium",
            file=sys.stderr,
        )
        return 2

    args = parse_args()
    base_url = args.base_url.rstrip("/") + "/"
    pages = sitemap_pages(base_url, max(1, args.max_pages), args.timeout)
    screenshot_dir = Path(args.screenshot_dir)
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    issues: list[dict] = []
    page_results: dict[str, dict] = {}
    baseline_dir = Path(args.baseline_dir) if args.baseline_dir else None

    viewports = [
        {"name": "desktop", "width": 1440, "height": 900},
        {"name": "mobile", "width": 390, "height": 844},
    ]

    try:
        with sync_playwright() as playwright:
            try:
                browser = playwright.chromium.launch(headless=True)
            except PlaywrightError:
                browser = playwright.chromium.launch(headless=True, channel="chrome")

            for viewport in viewports:
                context = browser.new_context(
                    viewport={
                        "width": viewport["width"],
                        "height": viewport["height"],
                    },
                    ignore_https_errors=True,
                )
                for url in pages:
                    page = context.new_page()
                    try:
                        page_issues, stats = audit_page(
                            page, url, viewport, args.timeout
                        )
                    except Exception as exc:
                        page_issues = [
                            make_issue(
                                "P1",
                                "visual_audit_failed",
                                urlparse(url).path or "/",
                                viewport["name"],
                                str(exc)[:240],
                                "Investigate the browser failure and rerun.",
                            )
                        ]
                        stats = {"status": 0, "error": str(exc)[:240]}
                    issues.extend(page_issues)
                    screenshot = screenshot_dir / (
                        f"{slug_for_url(url)}-{viewport['name']}.png"
                    )
                    try:
                        page.screenshot(path=str(screenshot), full_page=True)
                    except PlaywrightError:
                        screenshot = None
                    if screenshot and baseline_dir:
                        ratio = pixel_diff_ratio(
                            screenshot, baseline_dir / screenshot.name
                        )
                        stats["pixel_diff_ratio"] = ratio
                        if (
                            args.enforce_baseline
                            and ratio is not None
                            and ratio > 0.01
                        ):
                            issues.append(
                                make_issue(
                                    "P2",
                                    "visual_regression",
                                    urlparse(url).path or "/",
                                    viewport["name"],
                                    f"pixel diff {ratio:.2%}",
                                    "Review the screenshot change against the approved baseline.",
                                )
                            )
                    page_results[f"{url}#{viewport['name']}"] = stats
                    page.close()
                context.close()
            browser.close()
    except Exception as exc:
        print(f"visual audit failed: {exc}", file=sys.stderr)
        return 2

    issues.sort(
        key=lambda item: (
            SEVERITY_RANK.get(item["severity"], 9),
            item.get("type", ""),
            item.get("page", ""),
            item.get("viewport", ""),
        )
    )
    counts = Counter(issue["severity"] for issue in issues)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "summary": {
            "pages": len(pages),
            "viewports": len(viewports),
            "issues": len(issues),
            "P0": counts.get("P0", 0),
            "P1": counts.get("P1", 0),
            "P2": counts.get("P2", 0),
        },
        "pages": page_results,
        "issues": issues,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        "visual quality: "
        f"pages={len(pages)} P0={counts.get('P0', 0)} "
        f"P1={counts.get('P1', 0)} P2={counts.get('P2', 0)}"
    )
    print(f"wrote {output.as_posix()}")
    if args.strict:
        return int(any(issue["severity"] in ("P0", "P1") for issue in issues))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
