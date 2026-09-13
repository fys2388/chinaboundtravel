#!/usr/bin/env python3
"""
ChinaBound Travel - SEO Growth Auto-Loop (Loop 2)

Scans Google Search Console keyword data every Tuesday, identifies
growth opportunities, and applies targeted SEO optimizations.

Trigger conditions:
  - New keywords entering Top 20 (growth potential, vs. previous baseline)
  - Keyword ranking dropped > 5 positions
  - Keyword CTR < 1% (impressions without clicks)
  - Pages with fewer than 3 internal links

Auto actions:
  - Internal link building (max 20 links/week)
  - Title optimization to include target keyword (max 10 pages/week)
  - FAQ section addition for long-tail keywords
  - Google Indexing API re-index request (urlNotifications:publish)
  - Sitemap update via Hugo rebuild

All modifications validated with `hugo --gc --minify`; failures roll back.

Usage:
  python scripts/seo_auto_optimizer.py --dry-run
  python scripts/seo_auto_optimizer.py --max-internal-links 20 --max-title-optimizations 10
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Path bootstrap
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from dotenv import load_dotenv  # noqa: E402

from gsc_utils import (  # noqa: E402
    SCOPE_INDEXING,
    SCOPE_WEBMASTERS_READONLY,
    build_credentials,
    describe_error,
    get_site_url,
    load_service_account_info,
)
from gsc_keyword_baseline import (  # noqa: E402
    compare_with_baseline,
    fetch_gsc_data,
    find_latest_baseline_csv,
    load_baseline_keywords,
    process_data,
)

BLOG_ROOT = SCRIPT_DIR.parent
CONTENT_DIR = BLOG_ROOT / "content" / "posts"
REPORTS_DIR = BLOG_ROOT / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(BLOG_ROOT / ".env")

SITE_URL = get_site_url()

# ---------------------------------------------------------------------------
# Safety thresholds
# ---------------------------------------------------------------------------
MAX_INTERNAL_LINKS_PER_WEEK = 20
MAX_TITLE_OPTIMIZATIONS_PER_WEEK = 10
CTR_LOW_THRESHOLD = 0.01  # 1%
RANK_DROP_THRESHOLD = 5.0
MIN_IMPRESSIONS_FOR_CTR = 5
HUGO_BIN = shutil.which("hugo") or r"C:\Users\神魂之人\bin\hugo.exe"  # portable: CI finds hugo in PATH

SEO_GROWTH_LOG = REPORTS_DIR / "seo-growth-log.json"
LEARNING_LIBRARY = REPORTS_DIR / "learning-library.json"

END_DATE = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
START_DATE = (datetime.now() - timedelta(days=92)).strftime("%Y-%m-%d")


# ===========================================================================
# Content parsing helpers (shared patterns with content_auto_optimizer)
# ===========================================================================

FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_post(file_path):
    """Parse a Hugo post, return dict with metadata and body analysis."""
    text = file_path.read_text(encoding="utf-8-sig")
    match = FRONT_MATTER_RE.match(text)
    if not match:
        return None

    fm_text = match.group(1)
    body = text[match.end():]

    fm = {}
    for line in fm_text.splitlines():
        m = re.match(r'^(\w+):\s*(.*)$', line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            if (val.startswith('"') and val.endswith('"')) or \
               (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            fm[key] = val

    internal_links = re.findall(r'\[([^\]]+)\]\((/[^)]+)\)', body)
    internal_links = [
        (a, h) for a, h in internal_links
        if h.startswith("/") and not h.startswith("//")
    ]

    has_faq = bool(re.search(r'^##\s+FAQ', body, re.MULTILINE | re.IGNORECASE))

    return {
        "file_path": file_path,
        "front_matter_text": fm_text,
        "body": body,
        "full_text": text,
        "title": fm.get("title", ""),
        "description": fm.get("description", fm.get("summary", "")),
        "slug": fm.get("slug", file_path.stem),
        "canonical_url": fm.get("canonicalURL", ""),
        "tags": fm.get("tags", ""),
        "categories": fm.get("categories", ""),
        "internal_link_count": len(internal_links),
        "internal_links": internal_links,
        "has_faq": has_faq,
        "word_count": len(re.findall(r'\b\w+\b', body)),
    }


def find_post_by_url(url):
    """Find content file matching a GSC page URL."""
    if not url:
        return None
    path = url.replace(SITE_URL.rstrip("/"), "").strip("/")
    slug = path.split("/")[-1] if path else ""
    if not slug:
        return None
    for candidate in CONTENT_DIR.glob("*.md"):
        if candidate.stem == slug or candidate.stem.endswith("-" + slug):
            return candidate
        try:
            text = candidate.read_text(encoding="utf-8")
            if f'canonicalURL: "{url}"' in text or \
               f"canonicalURL: '{url}'" in text:
                return candidate
        except Exception:
            pass
    return None


def list_all_posts():
    posts = []
    for fp in sorted(CONTENT_DIR.glob("*.md")):
        p = parse_post(fp)
        if p:
            posts.append(p)
    return posts


# ===========================================================================
# Front matter / body modifiers
# ===========================================================================

def modify_front_matter_field(file_path, field, new_value):
    """Replace a front matter field value, preserving formatting."""
    text = file_path.read_text(encoding="utf-8")
    pattern = re.compile(
        r'^(' + re.escape(field) + r':\s*)(["\']?)(.*?)(\2)(\s*)$',
        re.MULTILINE
    )
    match = pattern.search(text)
    if not match:
        title_match = re.search(r'^(title:.*)$', text, re.MULTILINE)
        if title_match:
            insert_pos = title_match.end()
            quote = '"' if '"' in title_match.group(1) else "'"
            new_line = f"\n{field}: {quote}{new_value}{quote}"
            text = text[:insert_pos] + new_line + text[insert_pos:]
            file_path.write_text(text, encoding="utf-8")
            return True
        return False
    if match.group(3) == new_value:
        return False
    quote = match.group(2) or '"'
    replacement = f"{match.group(1)}{quote}{new_value}{quote}{match.group(5)}"
    text = text[:match.start()] + replacement + text[match.end():]
    file_path.write_text(text, encoding="utf-8")
    return True


def append_to_body(file_path, content):
    text = file_path.read_text(encoding="utf-8")
    if not text.endswith("\n"):
        text += "\n"
    text += content
    file_path.write_text(text, encoding="utf-8")


def replace_body(file_path, new_body):
    text = file_path.read_text(encoding="utf-8")
    match = FRONT_MATTER_RE.match(text)
    if not match:
        return False
    fm_part = text[:match.end()]
    file_path.write_text(fm_part + new_body, encoding="utf-8")
    return True


# ===========================================================================
# SEO optimization actions
# ===========================================================================

def optimize_title_with_keyword(post, target_keyword):
    """Naturally integrate target keyword into title if not already present.

    Returns (new_title, changed_bool).
    """
    title = post["title"]
    kw_lower = target_keyword.lower()
    title_lower = title.lower()

    # Already contains keyword (as substring of meaningful words)
    kw_words = set(kw_lower.split())
    title_words = set(title_lower.split())
    if kw_words.issubset(title_words):
        return title, False

    # Strategy: if title has a colon, prepend keyword to first part
    if ":" in title and len(title) < 55:
        parts = title.split(":", 1)
        # Check if keyword fits naturally
        new_title = f"{target_keyword.title()}: {parts[1].strip()}"
        if len(new_title) <= 65:
            return new_title, True

    # Strategy: append keyword in parentheses
    if len(title) < 50:
        new_title = f"{title} ({target_keyword.title()})"
        if len(new_title) <= 65:
            return new_title, True

    return title, False


def find_related_posts_for_linking(target_post, all_posts, max_links=5):
    """Find posts that could link TO the target post (source candidates).

    Scores by title/tag keyword overlap with the target.
    """
    target_words = set(
        w.lower() for w in re.findall(r'\b\w{4,}\b',
                                      target_post["title"] + " " +
                                      target_post.get("tags", ""))
    )
    if not target_words:
        return []

    scored = []
    for p in all_posts:
        if p["file_path"] == target_post["file_path"]:
            continue
        # Don't add link if target already linked from this post
        target_slug = target_post["slug"]
        already_linked = any(
            target_slug in href for _, href in p["internal_links"]
        )
        if already_linked:
            continue
        p_words = set(
            w.lower() for w in re.findall(r'\b\w{4,}\b',
                                          p["title"] + " " + p.get("tags", ""))
        )
        overlap = target_words & p_words
        if overlap:
            scored.append((p, len(overlap)))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:max_links]


def add_link_to_post(source_post, target_post, anchor_text=None):
    """Add a link from source_post to target_post.

    Returns True if link was added.
    """
    target_href = f"/posts/{target_post['slug']}/"
    anchor = anchor_text or target_post["title"]

    # Check if link already exists
    if any(target_href in href for _, href in source_post["internal_links"]):
        return False

    body = source_post["body"]

    # Find a good insertion paragraph: one that mentions related topic
    # Simplest: add to a "Related Reading" section or create one
    if "## Related Reading" in body or "### Related Reading" in body:
        # Append to existing section
        pattern = re.compile(r'(##\s+Related Reading.*?)(?=\n##|\Z)', re.DOTALL)
        match = pattern.search(body)
        if match:
            section = match.group(1)
            new_link = f"- [{anchor}]({target_href})\n"
            if new_link.strip() not in section:
                body = body[:match.end()] + "\n" + new_link + body[match.end():]
                replace_body(source_post["file_path"], body)
                return True
    else:
        # Create Related Reading section at end
        related_section = f"\n## Related Reading\n\n- [{anchor}]({target_href})\n"
        append_to_body(source_post["file_path"], related_section)
        return True

    return False


def generate_faq_for_keyword(keyword, post):
    """Generate FAQ entries tailored to a long-tail keyword."""
    kw_lower = keyword.lower()

    # Generic FAQ based on keyword type
    if "visa" in kw_lower:
        faqs = [
            (f"Is {keyword} still valid in 2026?",
             "Yes, this policy is current for 2026. However, eligibility criteria and participating ports are updated periodically — always verify with official immigration sources before travel."),
            (f"What documents do I need for {keyword}?",
             "You'll need a valid passport (6+ months remaining), a confirmed onward ticket to a third country, and any supporting documents requested by immigration officers."),
        ]
    elif any(w in kw_lower for w in ["pay", "wechat", "alipay", "payment"]):
        faqs = [
            (f"Can foreigners use {keyword}?",
             "Yes, with some limitations. Foreign visitors can link an international Visa or Mastercard. For longer stays, a Chinese bank account provides the smoothest experience."),
            (f"Are there fees for {keyword}?",
             "Foreign-card transactions may incur a small currency conversion fee. Chinese bank card transactions are typically free."),
        ]
    elif any(w in kw_lower for w in ["train", "rail", "transport"]):
        faqs = [
            (f"How do I book {keyword}?",
             "Book online via the official app or at station ticket counters. Passport is required for pickup and boarding. Popular routes sell out during holidays."),
            (f"Is {keyword} reliable?",
             "Yes, China's transportation network has excellent on-time performance. Arrive 45-60 minutes early for security checks at major stations."),
        ]
    else:
        faqs = [
            (f"What should I know about {keyword}?",
             "This guide covers the essentials you need before your trip. Policies and practical details are updated for 2026, but always double-check official sources."),
            (f"Is {keyword} safe for tourists?",
             "Yes. China is generally very safe for tourists. Exercise normal precautions and keep your belongings secure, especially in crowded areas."),
        ]

    lines = ["\n## FAQ\n"]
    for q, a in faqs:
        lines.append(f"### {q}")
        lines.append("")
        lines.append(a)
        lines.append("")
    return "\n".join(lines)


# ===========================================================================
# Google Indexing API
# ===========================================================================

def request_reindex(url):
    """Request Google to re-index a URL via the Indexing API.

    Returns (success, message).
    """
    sa_info = load_service_account_info()
    if not sa_info:
        return False, "service account key not found"

    credentials = build_credentials(
        sa_info, scopes=[SCOPE_INDEXING]
    )
    if credentials is None:
        return False, "could not build indexing credentials"

    try:
        from googleapiclient.discovery import build
        service = build("indexing", "v3", credentials=credentials,
                        cache_discovery=False)
        response = service.urlNotifications().publish(
            body={
                "url": url,
                "type": "URL_UPDATED",
            }
        ).execute()
        return True, f"Indexing API notified: {response.get('urlNotificationMetadata', {}).get('latestUpdate', {}).get('notifyTime', 'ok')}"
    except Exception as exc:
        diagnosis = describe_error(exc)
        return False, f"{diagnosis['code']}: {diagnosis['message']}"


# ===========================================================================
# Hugo build
# ===========================================================================

def run_hugo_build():
    try:
        result = subprocess.run(
            [HUGO_BIN, "--gc", "--minify"],
            cwd=str(BLOG_ROOT),
            capture_output=True,
            text=True,
            timeout=120,
        )
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as exc:
        return False, str(exc)


# ===========================================================================
# Logging
# ===========================================================================

def load_json_file(path, default):
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default


def save_seo_log(entries):
    log = load_json_file(SEO_GROWTH_LOG, {"optimizations": []})
    log["optimizations"].extend(entries)
    SEO_GROWTH_LOG.write_text(
        json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8"
    )


# ===========================================================================
# Report
# ===========================================================================

def generate_report(keyword_analysis, actions_executed, dry_run,
                    error_code=None):
    today = datetime.now().strftime("%Y-%m-%d")
    report_path = REPORTS_DIR / f"seo-growth-report-{today}.md"

    lines = []
    lines.append("# ChinaBound Travel - SEO Growth Auto-Loop Report")
    lines.append("")
    lines.append(f"- **Run date**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"- **Mode**: {'DRY-RUN' if dry_run else 'LIVE'}")
    lines.append(f"- **GSC site**: {SITE_URL}")
    lines.append(f"- **Data window**: {START_DATE} ~ {END_DATE}")
    lines.append(f"- **Safety limits**: ≤{MAX_INTERNAL_LINKS_PER_WEEK} internal links, "
                 f"≤{MAX_TITLE_OPTIMIZATIONS_PER_WEEK} title optimizations")
    lines.append("")

    if error_code:
        lines.append("## Status: GSC API UNAVAILABLE")
        lines.append(f"Error: `{error_code}`")
        report_path.write_text("\n".join(lines), encoding="utf-8")
        return report_path

    # Keyword opportunities
    lines.append("## Keyword Opportunities")
    lines.append("")
    lines.append("| Category | Count |")
    lines.append("|----------|-------|")
    lines.append(f"| New Top 20 keywords | {len(keyword_analysis.get('new_top20', []))} |")
    lines.append(f"| Rank dropped >5 | {len(keyword_analysis.get('rank_dropped', []))} |")
    lines.append(f"| Low CTR (<1%) | {len(keyword_analysis.get('low_ctr', []))} |")
    lines.append(f"| Pages with <3 internal links | {len(keyword_analysis.get('low_internal_links', []))} |")
    lines.append("")

    # New Top 20 keywords
    new_top20 = keyword_analysis.get("new_top20", [])
    if new_top20:
        lines.append("### New Top 20 Keywords (Growth Potential)")
        lines.append("")
        lines.append("| Keyword | Position | Impr | Clicks | Page |")
        lines.append("|---------|----------|------|--------|------|")
        for kw in new_top20[:20]:
            lines.append(
                f"| {kw['query'][:50]} | {kw['position']} | "
                f"{kw['impressions']} | {kw['clicks']} | "
                f"{kw.get('page', '')[:40]} |"
            )
        lines.append("")

    # Low CTR keywords
    low_ctr = keyword_analysis.get("low_ctr", [])
    if low_ctr:
        lines.append("### Low CTR Keywords (<1%)")
        lines.append("")
        lines.append("| Keyword | Position | Impr | CTR | Page |")
        lines.append("|---------|----------|------|-----|------|")
        for kw in low_ctr[:15]:
            lines.append(
                f"| {kw['query'][:50]} | {kw['position']} | "
                f"{kw['impressions']} | {kw['ctr']*100:.2f}% | "
                f"{kw.get('page', '')[:40]} |"
            )
        lines.append("")

    # Actions executed
    lines.append("## Actions Executed")
    lines.append("")
    if actions_executed:
        lines.append("| # | Type | Target | Detail |")
        lines.append("|---|------|--------|--------|")
        for i, action in enumerate(actions_executed, 1):
            lines.append(
                f"| {i} | {action['type']} | {action['target'][:50]} | "
                f"{action.get('detail', '')[:60]} |"
            )
    else:
        lines.append("No actions executed (dry-run or no candidates).")
    lines.append("")

    # Indexing API results
    indexing_results = [a for a in actions_executed if a["type"] == "reindex"]
    if indexing_results:
        lines.append("### Indexing API Notifications")
        lines.append("")
        for r in indexing_results:
            lines.append(f"- {r['target']}: {r.get('detail', '')}")
        lines.append("")

    lines.append("## Next Steps")
    lines.append("")
    lines.append("1. Monitor keyword rankings weekly for improvement.")
    lines.append("2. Effective optimizations recorded in `learning-library.json`.")
    lines.append("3. Re-index requests submitted via Google Indexing API.")
    lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[INFO] Report saved: {report_path}")
    return report_path


# ===========================================================================
# Main
# ===========================================================================

def main():
    parser = argparse.ArgumentParser(
        description="ChinaBound Travel SEO growth auto-optimizer (Loop 2)"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Analyze only; do not modify files")
    parser.add_argument("--max-internal-links", type=int,
                        default=MAX_INTERNAL_LINKS_PER_WEEK)
    parser.add_argument("--max-title-optimizations", type=int,
                        default=MAX_TITLE_OPTIMIZATIONS_PER_WEEK)
    args = parser.parse_args()

    print("=" * 64)
    print("  ChinaBound Travel - SEO Growth Auto-Loop (Loop 2)")
    print(f"  Mode: {'DRY-RUN' if args.dry_run else 'LIVE'}")
    print(f"  Max internal links: {args.max_internal_links}")
    print(f"  Max title optimizations: {args.max_title_optimizations}")
    print("=" * 64)
    print()

    # 1. Fetch keyword data
    rows, error_code = fetch_gsc_data(dimensions=["query", "page"])
    if error_code:
        generate_report({}, [], args.dry_run, error_code=error_code)
        return 1

    if not rows:
        print("[WARN] No keyword data returned")
        generate_report({}, [], args.dry_run)
        return 0

    df_agg = process_data(rows)
    print(f"[INFO] Processed {len(df_agg)} unique keywords")

    # 2. Baseline comparison
    comparison = compare_with_baseline(df_agg)
    print(f"[INFO] Baseline: {comparison['baseline_file']}")
    print(f"  New keywords: {len(comparison['new_keywords'])}")
    print(f"  Rank improved: {len(comparison['rank_improved'])}")
    print(f"  Rank dropped: {len(comparison['rank_dropped'])}")

    # 3. Identify opportunities
    keyword_analysis = {
        "new_top20": [],
        "rank_dropped": [],
        "low_ctr": [],
        "low_internal_links": [],
    }

    # New keywords in Top 20 (by current position)
    top20_by_pos = df_agg[df_agg["position"] <= 20].sort_values("position")
    baseline_kw = load_baseline_keywords(find_latest_baseline_csv(exclude_current=True))
    for _, row in top20_by_pos.iterrows():
        if row["query"] not in baseline_kw:
            keyword_analysis["new_top20"].append({
                "query": row["query"],
                "page": row["page"],
                "position": round(row["position"], 1),
                "impressions": int(row["impressions"]),
                "clicks": int(row["clicks"]),
                "ctr": round(row["ctr"], 4),
            })

    # Rank dropped > 5
    for entry in comparison["rank_dropped"]:
        if abs(entry.get("delta", 0)) > RANK_DROP_THRESHOLD:
            keyword_analysis["rank_dropped"].append(entry)

    # Low CTR (< 1%) with meaningful impressions
    for _, row in df_agg.iterrows():
        if (row["impressions"] >= MIN_IMPRESSIONS_FOR_CTR and
                row["ctr"] < CTR_LOW_THRESHOLD):
            keyword_analysis["low_ctr"].append({
                "query": row["query"],
                "page": row["page"],
                "position": round(row["position"], 1),
                "impressions": int(row["impressions"]),
                "clicks": int(row["clicks"]),
                "ctr": round(row["ctr"], 4),
            })

    # Pages with < 3 internal links
    all_posts = list_all_posts()
    for post in all_posts:
        if post["internal_link_count"] < 3 and post["canonical_url"]:
            keyword_analysis["low_internal_links"].append({
                "url": post["canonical_url"],
                "slug": post["slug"],
                "title": post["title"],
                "internal_link_count": post["internal_link_count"],
            })

    print(f"\n[OPPORTUNITIES]")
    print(f"  New Top 20 keywords: {len(keyword_analysis['new_top20'])}")
    print(f"  Rank dropped >5: {len(keyword_analysis['rank_dropped'])}")
    print(f"  Low CTR (<1%): {len(keyword_analysis['low_ctr'])}")
    print(f"  Low internal links (<3): {len(keyword_analysis['low_internal_links'])}")

    # 4. Execute optimizations
    actions_executed = []
    internal_links_added = 0
    titles_optimized = 0
    urls_to_reindex = set()

    # --- 4a. Title optimization for low-CTR / new Top20 keywords ---
    print("\n[TITLE OPTIMIZATION]")
    title_candidates = (
        keyword_analysis["low_ctr"][:10] +
        keyword_analysis["new_top20"][:10]
    )
    seen_pages = set()
    for kw in title_candidates:
        if titles_optimized >= args.max_title_optimizations:
            break
        page_url = kw.get("page", "")
        if page_url in seen_pages:
            continue
        seen_pages.add(page_url)

        post_file = find_post_by_url(page_url)
        if not post_file:
            continue
        post = parse_post(post_file)
        if not post:
            continue

        new_title, changed = optimize_title_with_keyword(post, kw["query"])
        if changed:
            backup = post_file.read_text(encoding="utf-8")
            if not args.dry_run:
                modify_front_matter_field(post_file, "title", new_title)
                success, _ = run_hugo_build()
                if not success:
                    print(f"  [ROLLBACK] {post_file.name}")
                    post_file.write_text(backup, encoding="utf-8")
                    continue
                modify_front_matter_field(
                    post_file, "last_updated",
                    datetime.now().strftime("%Y-%m-%d")
                )
            titles_optimized += 1
            urls_to_reindex.add(page_url)
            actions_executed.append({
                "type": "title_optimization",
                "target": page_url,
                "detail": f"'{post['title']}' -> '{new_title}' (keyword: {kw['query']})",
                "timestamp": datetime.now().isoformat(),
            })
            print(f"  [TITLE] {post_file.name}: {new_title}")

    # --- 4b. Internal link building ---
    print("\n[INTERNAL LINK BUILDING]")
    # Priority: pages with low internal links, then new Top20 pages
    link_targets = []
    for entry in keyword_analysis["low_internal_links"]:
        link_targets.append(entry["slug"])
    for kw in keyword_analysis["new_top20"]:
        post_file = find_post_by_url(kw.get("page", ""))
        if post_file:
            p = parse_post(post_file)
            if p and p["slug"] not in link_targets:
                link_targets.append(p["slug"])

    for target_slug in link_targets:
        if internal_links_added >= args.max_internal_links:
            break
        target_post = None
        for p in all_posts:
            if p["slug"] == target_slug:
                target_post = p
                break
        if not target_post:
            continue

        sources = find_related_posts_for_linking(target_post, all_posts, max_links=3)
        for source_post, score in sources:
            if internal_links_added >= args.max_internal_links:
                break
            backup = source_post["file_path"].read_text(encoding="utf-8")
            if not args.dry_run:
                added = add_link_to_post(source_post, target_post)
                if added:
                    success, _ = run_hugo_build()
                    if not success:
                        print(f"  [ROLLBACK] {source_post['file_path'].name}")
                        source_post["file_path"].write_text(backup, encoding="utf-8")
                        continue
                    internal_links_added += 1
                    urls_to_reindex.add(source_post["canonical_url"] or
                                        f"{SITE_URL}posts/{source_post['slug']}/")
                    actions_executed.append({
                        "type": "internal_link",
                        "target": f"{source_post['slug']} -> {target_slug}",
                        "detail": f"score={score}",
                        "timestamp": datetime.now().isoformat(),
                    })
                    print(f"  [LINK] {source_post['file_path'].name} -> "
                          f"{target_post['file_path'].name} (score={score})")
            else:
                internal_links_added += 1
                actions_executed.append({
                    "type": "internal_link",
                    "target": f"{source_post['slug']} -> {target_slug}",
                    "detail": f"score={score} (dry-run)",
                    "timestamp": datetime.now().isoformat(),
                })
                print(f"  [LINK][DRY] {source_post['file_path'].name} -> "
                      f"{target_post['file_path'].name}")

    # --- 4c. FAQ addition for long-tail keywords (low CTR, long queries) ---
    print("\n[FAQ ADDITION]")
    faq_added = 0
    for kw in keyword_analysis["low_ctr"]:
        if faq_added >= 5:  # Sub-limit for FAQ
            break
        if len(kw["query"].split()) < 4:  # Long-tail only
            continue
        post_file = find_post_by_url(kw.get("page", ""))
        if not post_file:
            continue
        post = parse_post(post_file)
        if not post or post["has_faq"]:
            continue

        faq_content = generate_faq_for_keyword(kw["query"], post)
        backup = post_file.read_text(encoding="utf-8")
        if not args.dry_run:
            append_to_body(post_file, faq_content)
            success, _ = run_hugo_build()
            if not success:
                print(f"  [ROLLBACK] {post_file.name}")
                post_file.write_text(backup, encoding="utf-8")
                continue
            modify_front_matter_field(
                post_file, "last_updated",
                datetime.now().strftime("%Y-%m-%d")
            )
            faq_added += 1
            urls_to_reindex.add(kw["page"])
            actions_executed.append({
                "type": "faq_addition",
                "target": kw["page"],
                "detail": f"FAQ for '{kw['query']}'",
                "timestamp": datetime.now().isoformat(),
            })
            print(f"  [FAQ] {post_file.name}: added for '{kw['query']}'")
        else:
            faq_added += 1
            actions_executed.append({
                "type": "faq_addition",
                "target": kw["page"],
                "detail": f"FAQ for '{kw['query']}' (dry-run)",
                "timestamp": datetime.now().isoformat(),
            })
            print(f"  [FAQ][DRY] {post_file.name}")

    # --- 4d. Indexing API requests ---
    print("\n[INDEXING API]")
    if not args.dry_run and urls_to_reindex:
        for url in list(urls_to_reindex)[:10]:  # Google limits batch
            success, msg = request_reindex(url)
            status = "OK" if success else "FAIL"
            actions_executed.append({
                "type": "reindex",
                "target": url,
                "detail": f"{status}: {msg}",
                "timestamp": datetime.now().isoformat(),
            })
            print(f"  [{status}] {url}: {msg}")
    else:
        print(f"  [SKIP] {len(urls_to_reindex)} URLs pending re-index "
              f"({'dry-run' if args.dry_run else 'none'})")

    # 5. Save log
    if actions_executed and not args.dry_run:
        save_seo_log(actions_executed)

    # 6. Generate report
    report_path = generate_report(keyword_analysis, actions_executed,
                                  args.dry_run)

    # 7. Summary
    print("\n" + "=" * 64)
    print("  RUN SUMMARY")
    print("=" * 64)
    print(f"  Titles optimized   : {titles_optimized}")
    print(f"  Internal links     : {internal_links_added}")
    print(f"  FAQ sections       : {faq_added}")
    print(f"  Re-index requests  : {len(urls_to_reindex)}")
    print(f"  Report             : {report_path}")
    print(f"  Mode               : {'DRY-RUN' if args.dry_run else 'LIVE'}")
    print("=" * 64)

    return 0


if __name__ == "__main__":
    sys.exit(main())
