#!/usr/bin/env python3
"""Audit the deployed sitemap for broken pages, assets, canonicals and semantics."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import threading
import xml.etree.ElementTree as ET
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag

import requests
from bs4 import BeautifulSoup


SEVERITY_RANK = {"P0": 0, "P1": 1, "P2": 2}
USER_AGENT = "ChinaBound-Quality-Audit/1.0 (+https://www.chinaboundtravel.com/)"
THREAD_LOCAL = threading.local()
STATUS_LOCK = threading.Lock()
STATUS_CACHE: dict[str, tuple[int, str, int, str]] = {}


def make_issue(
    severity: str,
    issue_type: str,
    page: str,
    evidence: str,
    action: str,
    source: str = "site",
) -> dict:
    ident = hashlib.sha1(
        f"{source}|{issue_type}|{page}|{evidence}".encode("utf-8")
    ).hexdigest()[:16]
    return {
        "id": ident,
        "severity": severity,
        "source": source,
        "type": issue_type,
        "page": page,
        "evidence": evidence,
        "recommended_action": action,
    }


def session() -> requests.Session:
    value = getattr(THREAD_LOCAL, "session", None)
    if value is None:
        value = requests.Session()
        value.headers.update({"User-Agent": USER_AGENT})
        THREAD_LOCAL.session = value
    return value


def same_origin(left: str, right: str) -> bool:
    a, b = urlparse(left), urlparse(right)
    return (a.scheme, a.netloc.lower()) == (b.scheme, b.netloc.lower())


def visible_text_without_code(soup: BeautifulSoup) -> str:
    parts: list[str] = []
    for node in soup.find_all(string=True):
        parent = node.parent
        if parent and parent.name in {"code", "kbd", "pre", "samp", "script", "style"}:
            continue
        parts.append(str(node))
    return " ".join(parts)


def check_url(url: str, timeout: int) -> tuple[int, str, int, str]:
    clean = urldefrag(url)[0]
    with STATUS_LOCK:
        cached = STATUS_CACHE.get(clean)
    if cached is not None:
        return cached

    try:
        response = session().head(clean, timeout=timeout, allow_redirects=True)
        if response.status_code in (403, 405, 501):
            response = session().get(
                clean, timeout=timeout, allow_redirects=True, stream=True
            )
            response.close()
        result = (
            response.status_code,
            response.url,
            len(response.history),
            "",
        )
    except requests.RequestException as exc:
        result = (0, clean, 0, str(exc)[:240])

    with STATUS_LOCK:
        STATUS_CACHE[clean] = result
    return result


def sitemap_urls(sitemap_url: str, timeout: int) -> list[str]:
    response = session().get(sitemap_url, timeout=timeout)
    response.raise_for_status()
    root = ET.fromstring(response.content)
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locations = [node.text.strip() for node in root.findall(".//sm:loc", namespace)]
    if root.tag.endswith("sitemapindex"):
        urls: list[str] = []
        for child in locations:
            child_response = session().get(child, timeout=timeout)
            child_response.raise_for_status()
            child_root = ET.fromstring(child_response.content)
            urls.extend(
                node.text.strip()
                for node in child_root.findall(".//sm:loc", namespace)
            )
        return sorted(set(urls))
    return sorted(set(locations))


def audit_page(page_url: str, timeout: int) -> tuple[list[dict], dict]:
    issues: list[dict] = []
    stats: Counter = Counter()
    try:
        response = session().get(page_url, timeout=timeout, allow_redirects=True)
    except requests.RequestException as exc:
        issues.append(
            make_issue(
                "P0",
                "sitemap_page_unreachable",
                page_url,
                str(exc)[:240],
                "Restore the page or remove it from the sitemap.",
            )
        )
        return issues, {"status": 0, "error": str(exc)[:240]}

    path = urlparse(page_url).path or "/"
    if response.status_code >= 400:
        issues.append(
            make_issue(
                "P0",
                "sitemap_page_status",
                path,
                f"HTTP {response.status_code}",
                "Restore the page or remove it from the sitemap.",
            )
        )
        return issues, {"status": response.status_code}

    if len(response.history) > 0:
        issues.append(
            make_issue(
                "P1",
                "sitemap_url_redirect",
                path,
                f"{page_url} -> {response.url}",
                "Publish the canonical URL directly and keep redirects only for legacy URLs.",
            )
        )

    raw = response.text
    soup = BeautifulSoup(raw, "html.parser")
    stats["pages"] += 1

    if "\ufffd" in raw:
        issues.append(
            make_issue(
                "P0",
                "replacement_character",
                path,
                "Rendered HTML contains U+FFFD replacement characters.",
                "Fix the source encoding and redeploy.",
            )
        )
    if "</span>" in visible_text_without_code(soup):
        issues.append(
            make_issue(
                "P0",
                "literal_html_tag",
                path,
                "Visible text contains a literal closing span tag.",
                "Fix the template output and redeploy.",
            )
        )

    h1_count = len(soup.find_all("h1"))
    if h1_count != 1:
        issues.append(
            make_issue(
                "P1",
                "h1_structure",
                path,
                f"Page contains {h1_count} H1 elements.",
                "Keep one page-level H1 and demote content headings.",
            )
        )

    tag_ids = sorted(
        set(re.findall(r"googletagmanager\.com/gtag/js\?id=([A-Za-z0-9_-]+)", raw))
    )
    if len(tag_ids) > 1:
        issues.append(
            make_issue(
                "P1",
                "multiple_analytics_tags",
                path,
                ", ".join(tag_ids),
                "Load one analytics tag per page.",
            )
        )

    canonical = soup.find("link", rel=lambda value: value and "canonical" in value)
    canonical_href = canonical.get("href", "").strip() if canonical else ""
    if canonical_href:
        canonical_url = urljoin(page_url, canonical_href)
        canonical_status, canonical_final, redirects, error = check_url(
            canonical_url, timeout
        )
        if canonical_status == 0:
            issues.append(
                make_issue(
                    "P0",
                    "canonical_unreachable",
                    path,
                    f"{canonical_url}: {error}",
                    "Point canonicalURL at a reachable page.",
                )
            )
        elif canonical_status >= 400:
            issues.append(
                make_issue(
                    "P0",
                    "canonical_target_missing",
                    path,
                    f"{canonical_url} -> HTTP {canonical_status}",
                    "Point canonicalURL at a deployed 200 page.",
                )
            )
        elif redirects:
            issues.append(
                make_issue(
                    "P1",
                    "canonical_redirect",
                    path,
                    f"{canonical_url} -> {canonical_final}",
                    "Use the final canonical URL directly.",
                )
            )

    images: set[str] = set()
    for image in soup.find_all("img"):
        src = (image.get("src") or "").strip()
        if src:
            images.add(urljoin(page_url, src))

    internal_links: set[str] = set()
    for anchor in soup.find_all("a"):
        href = (anchor.get("href") or "").strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        target = urljoin(page_url, href)
        if same_origin(page_url, target):
            internal_links.add(urldefrag(target)[0])

    for image_url in sorted(images):
        if not same_origin(page_url, image_url):
            continue
        status, _final, _redirects, error = check_url(image_url, timeout)
        stats["images"] += 1
        if status == 0 or status >= 400:
            issues.append(
                make_issue(
                    "P0",
                    "broken_image",
                    path,
                    f"{image_url}: HTTP {status or 'ERR'} {error}",
                    "Restore the image URL or update the page reference.",
                )
            )

    for link in sorted(internal_links):
        if link == page_url:
            continue
        status, final, redirects, error = check_url(link, timeout)
        stats["links"] += 1
        if status == 0 or status >= 400:
            issues.append(
                make_issue(
                    "P1",
                    "broken_internal_link",
                    path,
                    f"{link}: HTTP {status or 'ERR'} {error}",
                    "Update the link to a live route or add a redirect.",
                )
            )
        elif redirects:
            issues.append(
                make_issue(
                    "P2",
                    "internal_link_redirect",
                    path,
                    f"{link} -> {final}",
                    "Link directly to the final URL.",
                )
            )

    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    return issues, {
        "status": response.status_code,
        "title": title,
        "images": stats["images"],
        "links": stats["links"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="https://www.chinaboundtravel.com")
    parser.add_argument("--sitemap", default="")
    parser.add_argument("--output", default="reports/quality/site_audit.json")
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--max-pages", type=int, default=0)
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base_url = args.base_url.rstrip("/") + "/"
    sitemap_url = args.sitemap or urljoin(base_url, "sitemap.xml")
    try:
        urls = sitemap_urls(sitemap_url, args.timeout)
    except Exception as exc:
        print(f"failed to read sitemap {sitemap_url}: {exc}", file=sys.stderr)
        return 2

    if args.max_pages > 0:
        urls = urls[: args.max_pages]

    issues: list[dict] = []
    page_stats: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(audit_page, url, args.timeout): url for url in urls}
        for future in as_completed(futures):
            url = futures[future]
            try:
                page_issues, stats = future.result()
            except Exception as exc:
                page_issues = [
                    make_issue(
                        "P0",
                        "page_audit_failed",
                        urlparse(url).path or "/",
                        str(exc)[:240],
                        "Investigate the audit error and rerun.",
                    )
                ]
                stats = {"status": 0}
            issues.extend(page_issues)
            page_stats[url] = stats

    unresolved_titles: dict[str, list[str]] = {}
    for url, stats in page_stats.items():
        title = stats.get("title", "")
        if title:
            unresolved_titles.setdefault(title, []).append(url)
    for title, pages in unresolved_titles.items():
        unique_pages = sorted(set(pages))
        if len(unique_pages) > 1:
            issues.append(
                make_issue(
                    "P2",
                    "duplicate_title",
                    urlparse(unique_pages[0]).path or "/",
                    f"{len(unique_pages)} pages share the title: {title}",
                    "Differentiate titles for distinct search intent.",
                )
            )

    issues.sort(
        key=lambda item: (
            SEVERITY_RANK.get(item["severity"], 9),
            item.get("type", ""),
            item.get("page", ""),
        )
    )
    counts = Counter(issue["severity"] for issue in issues)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "sitemap": sitemap_url,
        "summary": {
            "pages": len(urls),
            "images_checked": sum(v.get("images", 0) for v in page_stats.values()),
            "links_checked": sum(v.get("links", 0) for v in page_stats.values()),
            "issues": len(issues),
            "P0": counts.get("P0", 0),
            "P1": counts.get("P1", 0),
            "P2": counts.get("P2", 0),
        },
        "issues": issues,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        "site quality: "
        f"pages={len(urls)} P0={counts.get('P0', 0)} "
        f"P1={counts.get('P1', 0)} P2={counts.get('P2', 0)}"
    )
    print(f"wrote {output.as_posix()}")
    if args.strict:
        return int(any(issue["severity"] in ("P0", "P1") for issue in issues))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
