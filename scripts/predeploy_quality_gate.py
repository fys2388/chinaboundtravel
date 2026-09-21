#!/usr/bin/env python3
"""Block known user-visible defects before a Hugo build is deployed."""

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
from urllib.parse import unquote, urljoin, urlparse

from bs4 import BeautifulSoup


SEVERITY_RANK = {"P0": 0, "P1": 1, "P2": 2}

# ---------------------------------------------------------------------------
# False-positive ignore list (2026-09-21: audit governance)
# ---------------------------------------------------------------------------

# URL path prefixes that are Cloudflare runtime endpoints. A headless audit
# that does not execute JavaScript will always receive HTTP 404 from these.
# They appear in ~60 broken_internal_link findings per audit run — the single
# largest noise source in the 489-issue report.
#
# This list is shared with site_quality_audit.py to ensure the two gates
# have consistent ignore logic.
IGNORE_URL_PREFIXES = (
    "/cdn-cgi/l/email-protection",  # Cloudflare Email Address Obfuscation
    "/cdn-cgi/trace",               # Cloudflare trace endpoint
    "/cdn-cgi/",                    # Any other Cloudflare runtime endpoint
)

# Dot-directories under site_dir that must be skipped. Hugo does not publish
# these, but if --site-dir is pointed at content/ instead of public/, they
# would leak into the scan and produce false U+FFFD findings.
SKIP_DIRS = frozenset({
    ".archived",
    ".audit_backup",
    "drafts",
    "_draft",
    "_drafts",
    ".git",
})


def make_issue(
    severity: str,
    issue_type: str,
    page: str,
    evidence: str,
    action: str,
    source: str = "predeploy",
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


def to_page(site_dir: Path, html_file: Path) -> str:
    rel = html_file.relative_to(site_dir).as_posix()
    if rel == "index.html":
        return "/"
    if rel.endswith("/index.html"):
        return f"/{rel[:-10]}"
    return f"/{rel}"


def sitemap_targets(site_dir: Path) -> set[str] | None:
    sitemap = site_dir / "sitemap.xml"
    if not sitemap.exists():
        return None
    try:
        root = ET.fromstring(sitemap.read_bytes())
    except (ET.ParseError, OSError):
        return None
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    targets = {
        urlparse(node.text.strip()).path or "/"
        for node in root.findall(".//sm:loc", namespace)
        if node.text and node.text.strip()
    }
    targets.add("/")
    return targets


def visible_text_without_code(soup: BeautifulSoup) -> str:
    parts: list[str] = []
    for node in soup.find_all(string=True):
        parent = node.parent
        if parent and parent.name in {"code", "kbd", "pre", "samp", "script", "style"}:
            continue
        parts.append(str(node))
    return " ".join(parts)


def resolve_local_path(
    site_dir: Path,
    raw_url: str,
    site_hosts: set[str] | None = None,
    page_url: str = "",
) -> Path | None:
    value = unquote(raw_url.strip())
    # Skip Cloudflare runtime endpoints (headless audit always gets 404).
    # These are false positives, not real broken links.
    if any(value.startswith(p) for p in IGNORE_URL_PREFIXES):
        return None
    if not value or value.startswith(("#", "data:", "mailto:", "tel:", "javascript:")):
        return None
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"} or parsed.netloc:
        host = parsed.netloc.lower()
        if site_hosts is None or host not in site_hosts:
            return None
        path = parsed.path or "/"
    else:
        path = parsed.path
        if not path:
            return None
        if not path.startswith("/"):
            path = urljoin(page_url or "/", path)
    relative = path.lstrip("/")
    candidate = site_dir / relative
    if path.endswith("/") or candidate.is_dir():
        candidate = candidate / "index.html"
    elif candidate.suffix == "":
        candidate = candidate / "index.html"
    return candidate


def load_issue_count(issues: list[dict]) -> dict:
    counts = Counter(issue["severity"] for issue in issues)
    return {level: counts.get(level, 0) for level in ("P0", "P1", "P2")}


def audit_static_site(site_dir: Path, site_hosts: set[str]) -> dict:
    issues: list[dict] = []
    # Skip dot-directories (e.g. .audit_backup, .archived, drafts). Hugo does
    # not publish these, but if --site-dir is pointed at content/ instead of
    # public/, they would leak into the scan and produce false U+FFFD findings.
    all_pages = []
    for html_file in site_dir.rglob("*.html"):
        parts = html_file.relative_to(site_dir).parts
        if any(p in SKIP_DIRS for p in parts):
            continue
        all_pages.append(html_file)
    all_pages = sorted(all_pages)
    targets = sitemap_targets(site_dir)
    if targets is None:
        pages = all_pages
    else:
        pages = [html_file for html_file in all_pages if to_page(site_dir, html_file) in targets]
    image_count = 0
    canonical_count = 0
    title_map: dict[str, list[str]] = {}

    for html_file in pages:
        page = to_page(site_dir, html_file)
        raw = html_file.read_text(encoding="utf-8", errors="replace")
        soup = BeautifulSoup(raw, "html.parser")

        if "\ufffd" in raw:
            issues.append(
                make_issue(
                    "P0",
                    "replacement_character",
                    page,
                    "Rendered HTML contains U+FFFD replacement characters.",
                    "Fix the source encoding and rebuild the page.",
                )
            )

        if "</span>" in visible_text_without_code(soup):
            issues.append(
                make_issue(
                    "P0",
                    "literal_html_tag",
                    page,
                    "Visible text contains a literal closing span tag.",
                    "Fix the malformed template string and rebuild.",
                )
            )

        h1_count = len(soup.find_all("h1"))
        if h1_count != 1:
            issues.append(
                make_issue(
                    "P1",
                    "h1_structure",
                    page,
                    f"Page contains {h1_count} H1 elements.",
                    "Keep exactly one page-level H1 and demote content headings.",
                )
            )

        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        if title:
            title_map.setdefault(title, []).append(page)

        for image in soup.find_all("img"):
            src = (image.get("src") or "").strip()
            if not src:
                issues.append(
                    make_issue(
                        "P1",
                        "image_src_missing",
                        page,
                        str(image)[:240],
                        "Add a valid image source.",
                    )
                )
                continue
            target = resolve_local_path(site_dir, src, site_hosts, page)
            if target is None:
                continue
            image_count += 1
            if not target.exists():
                issues.append(
                    make_issue(
                        "P0",
                        "broken_local_image",
                        page,
                        src,
                        "Update the content reference or add the missing asset.",
                    )
                )
            if not (image.get("alt") or "").strip():
                issues.append(
                    make_issue(
                        "P2",
                        "image_alt_missing",
                        page,
                        src,
                        "Add concise alt text when the image conveys information.",
                    )
                )

        canonicals = soup.find_all(
            "link", rel=lambda value: value and "canonical" in value
        )
        if len(canonicals) != 1:
            issues.append(
                make_issue(
                    "P1",
                    "canonical_count",
                    page,
                    f"Page contains {len(canonicals)} canonical links.",
                    "Emit exactly one canonical URL per indexable page.",
                )
            )
        canonical = canonicals[0] if canonicals else None
        if canonical and canonical.get("href"):
            href = canonical["href"].strip()
            parsed = urlparse(href)
            host = parsed.netloc.lower()
            if not host or host in site_hosts:
                canonical_count += 1
                canonical_path = parsed.path or "/"
                if canonical_path != page:
                    issues.append(
                        make_issue(
                            "P1",
                            "canonical_path_mismatch",
                            page,
                            href,
                            "Canonicalize an indexable page to its own final URL.",
                        )
                    )
                target = resolve_local_path(site_dir, href, site_hosts, page)
                if target is None or not target.exists():
                    issues.append(
                        make_issue(
                            "P0",
                            "canonical_target_missing",
                            page,
                            href,
                            "Point canonicalURL at a deployed 200 page.",
                        )
                    )

        # 所有 GA4 measurement ID，不限 gtag.js 加载脚本。
        #
        # 旧实现只匹配 gtag/js?id= —— 双计场景下第二个 ID 出现在 collect 路径
        # tid=G-P6BH500VBK 里，闸门完全看不见。实测线上（2026-09-20）：首页每次
        # page_view 同时 POST
        #   /vo5w/ga/g/c?tid=G-P6BH500VBK   和   /vo5w/ga/g/c?tid=G-GECBME3YVJ
        # 两条共用同一个 gtm= 配置哈希与 cid，即同一个配置里的两个 measurement ID。
        # 仓库里只有 G-GECBME3YVJ（hugo.toml），另一个来自部署层。
        #
        # 后果：所有流量 KPI 双计 —— users_28d / sessions_28d /
        # engagement_rate_28d 全部失真。一个"看起来干净"的错误数字比显示 0 更
        # 危险，所以这是 P0，不是 P1（--fail-on P1 下 P1 同样拦，但语义要说清）。
        #
        # 只在 <script> 文本与 HTML 属性里扫，不扫正文散文，避免文章里出现
        # "G-XXXXXXXX" 字样就误拦部署。
        script_text = "\n".join(
            s.get_text() for s in soup.find_all("script")
        )
        attr_text = " ".join(
            f'{name}="{value}"'
            for tag in soup.find_all(True)
            for name, value in tag.attrs.items()
        )
        tag_ids = set(
            re.findall(r"\bG-[A-Z0-9]{8,12}\b", script_text + "\n" + attr_text)
        )
        if len(tag_ids) > 1:
            issues.append(
                make_issue(
                    "P0",
                    "multiple_analytics_tags",
                    page,
                    ", ".join(sorted(tag_ids)),
                    "Load exactly one GA4 measurement ID. Multiple IDs double-count "
                    "every page_view and corrupt all traffic and revenue KPIs.",
                )
            )

    for title, title_pages in title_map.items():
        unique_pages = sorted(set(title_pages))
        if len(unique_pages) > 1:
            issues.append(
                make_issue(
                    "P2",
                    "duplicate_title",
                    unique_pages[0],
                    f"{len(unique_pages)} pages share the title: {title}",
                    "Differentiate titles for distinct search intent.",
                    source="predeploy",
                )
            )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "site_dir": str(site_dir),
        "summary": {
            "pages": len(pages),
            "html_files": len(all_pages),
            "images_checked": image_count,
            "canonicals_checked": canonical_count,
            "issues": len(issues),
            **load_issue_count(issues),
        },
        "issues": issues,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site-dir", default="public")
    parser.add_argument("--output", default="reports/quality/predeploy_quality.json")
    parser.add_argument("--site-host", action="append", default=[])
    parser.add_argument(
        "--fail-on",
        choices=("none", "P0", "P1", "P2"),
        default="P1",
        help="Fail when an issue at this severity or higher is found.",
    )
    parser.add_argument("--strict", action="store_true", help="Alias for --fail-on P1.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    site_dir = Path(args.site_dir).resolve()
    if not site_dir.exists():
        print(f"site directory does not exist: {site_dir}", file=sys.stderr)
        return 2

    hosts = {host.lower() for host in args.site_host if host}
    hosts.update({"www.chinaboundtravel.com", "chinaboundtravel.com"})
    report = audit_static_site(site_dir, hosts)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = report["summary"]
    print(
        "predeploy quality: "
        f"pages={summary['pages']} P0={summary['P0']} "
        f"P1={summary['P1']} P2={summary['P2']}"
    )
    print(f"wrote {output.as_posix()}")

    fail_on = "P1" if args.strict else args.fail_on
    if fail_on == "none":
        return 0
    threshold = SEVERITY_RANK[fail_on]
    return int(
        any(SEVERITY_RANK[issue["severity"]] <= threshold for issue in report["issues"])
    )


if __name__ == "__main__":
    raise SystemExit(main())
