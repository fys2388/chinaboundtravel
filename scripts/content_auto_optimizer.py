#!/usr/bin/env python3
"""
ChinaBound Travel - Content Production Auto-Optimization Loop (Loop 1)

Scans Google Search Console page-level data every Monday, identifies
underperforming pages, and applies low-risk SEO optimizations automatically.

Trigger conditions:
  - impressions > 10 AND clicks = 0  (CTR problem)
  - average position dropped > 5 vs. previous baseline
  - (GA4 avg engagement < 10s — skipped when GA4 data unavailable)

Low-risk actions auto-executed:
  - Title / meta description optimization (front matter)
  - FAQ section addition
  - Internal link supplementation
  - First-paragraph intent alignment

High-risk actions (>30% content rewrite) are NOT auto-executed; they are
flagged in the report for manual review.

Safety: MAX_AUTO_OPTIMIZE_PER_WEEK = 2 pages per run.
Every modified file is validated with `hugo --gc --minify`; build failures
trigger an automatic rollback of that file.

Usage:
  python scripts/content_auto_optimizer.py --dry-run
  python scripts/content_auto_optimizer.py --max-pages 2
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Path bootstrap — allow importing sibling modules regardless of CWD
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from dotenv import load_dotenv  # noqa: E402

from gsc_utils import (  # noqa: E402
    build_credentials,
    describe_error,
    get_site_url,
    load_service_account_info,
)

BLOG_ROOT = SCRIPT_DIR.parent
CONTENT_DIR = BLOG_ROOT / "content" / "posts"
REPORTS_DIR = BLOG_ROOT / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Load .env so GSC_SITE_URL / GSC_SERVICE_ACCOUNT_JSON are available
load_dotenv(BLOG_ROOT / ".env")

SITE_URL = get_site_url()

# ---------------------------------------------------------------------------
# Safety thresholds
# ---------------------------------------------------------------------------
MAX_AUTO_OPTIMIZE_PER_WEEK = 2  # user-adjusted: max 1-2 pages/week
MIN_IMPRESSIONS_FOR_CTR_CHECK = 10
RANK_DROP_THRESHOLD = 5.0
HUGO_BIN = r"C:\Users\神魂之人\bin\hugo.exe"

# Files that track state across runs
OPTIMIZATION_LOG = REPORTS_DIR / "content-optimization-log.json"
LEARNING_LIBRARY = REPORTS_DIR / "learning-library.json"
P0_BASELINE_CSV = REPORTS_DIR / "P0_GSC_PAGE_SCORING.csv"

# Date window for GSC (GSC has 2-3 day latency)
END_DATE = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
START_DATE = (datetime.now() - timedelta(days=92)).strftime("%Y-%m-%d")


# ===========================================================================
# GSC data fetching (page-level)
# ===========================================================================

def fetch_page_level_gsc():
    """Fetch page-level searchanalytics (dimensions=["page"]).

    Returns (list_of_rows, error_code_or_None).
    """
    print(f"[INFO] Fetching page-level GSC data for {SITE_URL}")
    print(f"[INFO] Date range: {START_DATE} ~ {END_DATE}")

    sa_info = load_service_account_info()
    if not sa_info:
        print("[ERROR] Cannot load service-account key")
        return None, "KEY_NOT_FOUND"

    sa_email = sa_info.get("client_email", "unknown")
    print(f"[INFO] Service account: {sa_email}")

    credentials = build_credentials(sa_info)
    if credentials is None:
        print("[ERROR] Cannot build credentials")
        return None, "CREDENTIAL_BUILD_FAILED"

    try:
        from googleapiclient.discovery import build
        service = build("searchconsole", "v1", credentials=credentials,
                        cache_discovery=False)
    except Exception as exc:
        print(f"[ERROR] Failed to build GSC service: {exc}")
        return None, "SERVICE_BUILD_FAILED"

    request_body = {
        "startDate": START_DATE,
        "endDate": END_DATE,
        "dimensions": ["page"],
        "rowLimit": 5000,
    }

    try:
        response = service.searchanalytics().query(
            siteUrl=SITE_URL, body=request_body
        ).execute()
        rows = response.get("rows", [])
        print(f"[INFO] Fetched {len(rows)} page records")
        return rows, None
    except Exception as exc:
        diagnosis = describe_error(exc)
        print("[ERROR] GSC API call failed")
        print(f"  code: {diagnosis['code']}")
        print(f"  message: {diagnosis['message']}")
        print(f"  hint: {diagnosis['hint']}")
        return None, diagnosis["code"]


# ===========================================================================
# Baseline comparison (ranking drop detection)
# ===========================================================================

def load_previous_baseline_positions():
    """Read P0_GSC_PAGE_SCORING.csv and return {url: avg_position}."""
    positions = {}
    if not P0_BASELINE_CSV.is_file():
        print("[WARN] P0 baseline CSV not found, skipping rank-drop detection")
        return positions
    try:
        import csv
        with open(P0_BASELINE_CSV, "r", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                url = (row.get("url") or "").strip()
                pos_raw = (row.get("avg_position") or "").strip()
                if url and pos_raw and pos_raw != "N/A":
                    try:
                        positions[url] = float(pos_raw)
                    except ValueError:
                        pass
    except Exception as exc:
        print(f"[WARN] Could not parse baseline CSV: {exc}")
    return positions


# ===========================================================================
# Content file helpers
# ===========================================================================

FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_post(file_path):
    """Parse a Hugo markdown post.

    Returns dict with keys: front_matter_text, body, title, description,
    slug, canonical_url, tags, categories, word_count, internal_links,
    has_faq, first_paragraph.
    """
    text = file_path.read_text(encoding="utf-8-sig")
    match = FRONT_MATTER_RE.match(text)
    if not match:
        return None

    fm_text = match.group(1)
    body = text[match.end():]

    # Parse front matter fields via simple line regex (preserves order)
    fm = {}
    for line in fm_text.splitlines():
        m = re.match(r'^(\w+):\s*(.*)$', line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            # Strip surrounding quotes
            if (val.startswith('"') and val.endswith('"')) or \
               (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            fm[key] = val

    # Count internal links (markdown links pointing to /posts/ or /)
    internal_links = re.findall(
        r'\[([^\]]+)\]\((/[^)]+)\)', body
    )
    # Filter to actual site-internal links (not external)
    internal_links = [
        (anchor, href) for anchor, href in internal_links
        if href.startswith("/") and not href.startswith("//")
    ]

    has_faq = bool(re.search(r'^##\s+FAQ', body, re.MULTILINE | re.IGNORECASE))

    # First non-empty, non-heading paragraph
    first_paragraph = ""
    for para in re.split(r'\n\s*\n', body):
        para = para.strip()
        if para and not para.startswith("#") and not para.startswith("{{"):
            first_paragraph = para[:500]
            break

    word_count = len(re.findall(r'\b\w+\b', body))

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
        "word_count": word_count,
        "internal_links": internal_links,
        "internal_link_count": len(internal_links),
        "has_faq": has_faq,
        "first_paragraph": first_paragraph,
    }


def find_post_by_url(url):
    """Find the content markdown file matching a GSC page URL.

    Matches by canonicalURL in front matter, or by slug in filename.
    """
    if not url:
        return None
    # Normalize: extract path after base URL
    path = url.replace(SITE_URL.rstrip("/"), "").strip("/")
    # path like "posts/some-slug" or "posts/some-slug/"
    slug = path.split("/")[-1] if path else ""

    if not slug:
        return None

    # Try exact filename match first
    for candidate in CONTENT_DIR.glob("*.md"):
        if candidate.stem == slug or candidate.stem.endswith("-" + slug):
            return candidate
        # Also check canonicalURL inside front matter
        try:
            text = candidate.read_text(encoding="utf-8")
            if f'canonicalURL: "{url}"' in text or \
               f"canonicalURL: '{url}'" in text:
                return candidate
        except Exception:
            pass
    return None


def list_all_posts():
    """Return list of parsed post dicts for all content files."""
    posts = []
    for fp in sorted(CONTENT_DIR.glob("*.md")):
        parsed = parse_post(fp)
        if parsed:
            posts.append(parsed)
    return posts


# ===========================================================================
# Issue analysis
# ===========================================================================

def analyze_page_issues(page_data, post, baseline_positions):
    """Analyze a problem page and return list of issue categories + actions.

    page_data: dict with keys page, clicks, impressions, ctr, position
    post: parsed post dict (may be None if file not found)
    baseline_positions: dict {url: previous_avg_position}
    """
    issues = []
    actions = []

    url = page_data["page"]
    impressions = page_data.get("impressions", 0)
    clicks = page_data.get("clicks", 0)
    position = page_data.get("position", 999)

    # 1. CTR problem: impressions > 10 but clicks = 0
    if impressions > MIN_IMPRESSIONS_FOR_CTR_CHECK and clicks == 0:
        issues.append("CTR_ZERO_CLICKS")
        if post:
            # Title likely not compelling or keyword mismatch
            actions.append("optimize_title")
            actions.append("optimize_description")

    # 2. Ranking drop > 5
    prev_pos = baseline_positions.get(url)
    if prev_pos is not None and position > prev_pos + RANK_DROP_THRESHOLD:
        issues.append(f"RANK_DROP_{prev_pos:.1f}_to_{position:.1f}")
        actions.append("optimize_title")
        actions.append("add_internal_links")

    # 3. Content-level checks (only if post found)
    if post:
        # FAQ missing
        if not post["has_faq"]:
            issues.append("FAQ_MISSING")
            actions.append("add_faq")

        # Internal link deficiency
        if post["internal_link_count"] < 3:
            issues.append(f"LOW_INTERNAL_LINKS_{post['internal_link_count']}")
            actions.append("add_internal_links")

        # Content depth (very short articles)
        if post["word_count"] < 500:
            issues.append(f"LOW_CONTENT_DEPTH_{post['word_count']}words")
            # This is high-risk (would need >30% rewrite), flag only
            actions.append("flag_for_manual_review")

        # First paragraph intent check: does it contain key terms from title?
        if post["first_paragraph"] and post["title"]:
            title_words = set(
                w.lower() for w in re.findall(r'\b\w{4,}\b', post["title"])
            )
            para_words = set(
                w.lower() for w in re.findall(r'\b\w{4,}\b',
                                              post["first_paragraph"])
            )
            overlap = title_words & para_words
            if len(title_words) > 3 and len(overlap) < 2:
                issues.append("FIRST_PARA_INTENT_MISMATCH")
                actions.append("rewrite_first_paragraph")

    # Deduplicate actions while preserving order
    seen = set()
    unique_actions = []
    for a in actions:
        if a not in seen:
            seen.add(a)
            unique_actions.append(a)

    return {
        "url": url,
        "impressions": impressions,
        "clicks": clicks,
        "position": round(position, 1),
        "previous_position": prev_pos,
        "issues": issues,
        "recommended_actions": unique_actions,
        "post_found": post is not None,
        "post_slug": post["slug"] if post else None,
    }


# ===========================================================================
# Optimization actions (low-risk)
# ===========================================================================

def optimize_title(post, target_keywords=None):
    """Generate an optimized title. Returns new title string.

    Strategy: keep existing title structure, ensure primary keyword is
    near the front, add year/CTR hook if missing.
    """
    old_title = post["title"]
    if not old_title:
        return old_title

    # If title already has good structure (contains colon or question),
    # and is under 60 chars, keep it but ensure 2026 relevance
    if len(old_title) <= 60 and ("2026" in old_title or "2025" in old_title):
        return old_title

    # Simple optimization: ensure year is present for time-sensitive content
    if "2026" not in old_title and "2025" not in old_title:
        if ":" in old_title:
            parts = old_title.split(":", 1)
            new_title = f"{parts[0].strip()} 2026: {parts[1].strip()}"
        else:
            new_title = f"{old_title} (2026 Guide)"
        # Keep under 65 chars
        if len(new_title) > 65:
            new_title = old_title
        return new_title

    return old_title


def optimize_description(post, target_keywords=None):
    """Generate an optimized meta description. Returns new description."""
    old_desc = post["description"]
    if old_desc and len(old_desc) >= 100 and len(old_desc) <= 160:
        return old_desc  # Already good length

    title = post["title"]
    slug = post["slug"]

    # Build a compelling description from title + first paragraph
    first_para = post["first_paragraph"]
    if first_para:
        # Take first sentence(s), trim to ~150 chars
        sentences = re.split(r'(?<=[.!?])\s+', first_para)
        desc = " ".join(sentences[:2])
        desc = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', desc)  # strip markdown links
        desc = re.sub(r'\*\*([^*]+)\*\*', r'\1', desc)  # strip bold
        if len(desc) > 155:
            desc = desc[:152].rsplit(" ", 1)[0] + "..."
        if len(desc) >= 80:
            return desc

    # Fallback: derive from title
    desc = f"{title.rstrip('.')} — practical tips, step-by-step guidance, and insider advice for travelers."
    if len(desc) > 160:
        desc = desc[:157] + "..."
    return desc


def generate_faq_section(post, page_data):
    """Generate a FAQ section based on page keywords and content.

    Returns markdown string for the FAQ section, or None if not appropriate.
    """
    title = post["title"]
    slug = post["slug"]

    # Topic-based FAQ templates
    faq_templates = {
        "visa": [
            ("Do I need a visa for China?",
             "It depends on your nationality. Citizens of many countries can enter China visa-free for up to 15 or 30 days under the current unilateral visa-free policy. For longer stays, a tourist visa (L-type) is required."),
            ("How long does it take to get a Chinese visa?",
             "Standard processing takes 4-7 business days. Same-day and 2-3 day express services are available at most consulates for an additional fee."),
            ("Can I extend my visa while in China?",
             "Yes, you can apply for an extension at the local Exit-Entry Administration Bureau. It's recommended to apply at least 7 days before your current visa expires."),
        ],
        "payment": [
            ("Can I use my foreign credit card in China?",
             "Major hotels and international chains accept Visa and Mastercard, but most local shops and restaurants only accept mobile payments (WeChat Pay or Alipay). Cash is increasingly rare."),
            ("Is WeChat Pay safe for foreigners?",
             "Yes. WeChat Pay uses encryption and real-name verification. Foreign users can link an international Visa or Mastercard via the Tour Card feature for short visits."),
            ("What should I do if my payment fails?",
             "Check that your card supports international transactions, ensure you have sufficient funds, and try a different payment method. Most tourists carry a backup card and some cash for emergencies."),
        ],
        "transport": [
            ("How early should I arrive at a Chinese train station?",
             "Arrive at least 45-60 minutes before departure for major stations. Security checks and ticket verification can take time, especially during holidays."),
            ("Can I buy train tickets at the station?",
             "Yes, ticket counters and self-service machines are available at all stations. However, popular routes sell out quickly, so booking in advance online is recommended."),
            ("Are Chinese high-speed trains reliable?",
             "Yes, China's high-speed rail network has an excellent on-time record. Delays are rare and usually weather-related."),
        ],
        "default": [
            ("Is this guide up to date for 2026?",
             "Yes, this guide was reviewed and updated for 2026. Policies and prices can change, so always double-check with official sources before your trip."),
            ("Do I need travel insurance for China?",
             "Travel insurance is highly recommended. Medical costs can be high for foreigners, and trip cancellation coverage provides peace of mind."),
            ("What's the best time of year to visit?",
             "Spring (April-May) and autumn (September-October) offer the most comfortable weather across most of China. Summer is hot and rainy in many regions; winter is cold but less crowded."),
        ],
    }

    # Determine topic from slug/categories/tags
    topic = "default"
    slug_lower = slug.lower()
    cats = (post.get("categories", "") or "").lower()
    tags = (post.get("tags", "") or "").lower()
    combined = slug_lower + " " + cats + " " + tags

    if "visa" in combined:
        topic = "visa"
    elif any(w in combined for w in ["wechat", "alipay", "pay", "payment"]):
        topic = "payment"
    elif any(w in combined for w in ["train", "rail", "transport", "subway", "taxi"]):
        topic = "transport"

    faqs = faq_templates.get(topic, faq_templates["default"])

    lines = ["\n## FAQ\n"]
    for question, answer in faqs:
        lines.append(f"### {question}")
        lines.append("")
        lines.append(answer)
        lines.append("")
    return "\n".join(lines)


def find_related_posts(target_post, all_posts, max_links=3):
    """Find posts related to the target by keyword overlap in titles/tags.

    Returns list of (post_dict, relevance_score).
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
        p_words = set(
            w.lower() for w in re.findall(r'\b\w{4,}\b',
                                          p["title"] + " " + p.get("tags", ""))
        )
        overlap = target_words & p_words
        if overlap:
            scored.append((p, len(overlap)))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:max_links]


def add_internal_links(post, all_posts, max_new_links=2):
    """Add internal links to related posts in the body.

    Returns modified body text and count of links added.
    """
    related = find_related_posts(post, all_posts, max_links=max_new_links)
    if not related:
        return post["body"], 0

    body = post["body"]
    added = 0

    # Find a good insertion point: end of a paragraph that mentions
    # a related topic. Simplest: append a "Related Reading" section
    # if one doesn't exist.
    if "## Related" in body or "### Related" in body:
        return body, 0

    related_lines = ["\n## Related Reading\n"]
    for rel_post, score in related:
        slug = rel_post["slug"]
        title = rel_post["title"]
        # Build relative URL from slug
        href = f"/posts/{slug}/"
        related_lines.append(f"- [{title}]({href})")
    related_lines.append("")

    body = body.rstrip() + "\n" + "\n".join(related_lines) + "\n"
    added = len(related)
    return body, added


# ===========================================================================
# File modification with rollback
# ===========================================================================

def modify_front_matter_field(file_path, field, new_value):
    """Replace a front matter field value, preserving formatting.

    Returns True if modified.
    """
    text = file_path.read_text(encoding="utf-8")
    # Match field: value (quoted or unquoted)
    pattern = re.compile(
        r'^(' + re.escape(field) + r':\s*)(["\']?)(.*?)(\2)(\s*)$',
        re.MULTILINE
    )
    match = pattern.search(text)
    if not match:
        # Field doesn't exist — add it after title line
        title_match = re.search(r'^(title:.*)$', text, re.MULTILINE)
        if title_match:
            insert_pos = title_match.end()
            # Determine quote style
            quote = '"' if '"' in title_match.group(1) else "'"
            new_line = f"\n{field}: {quote}{new_value}{quote}"
            text = text[:insert_pos] + new_line + text[insert_pos:]
            file_path.write_text(text, encoding="utf-8")
            return True
        return False

    old_val = match.group(3)
    if old_val == new_value:
        return False  # No change needed

    quote = match.group(2) or '"'
    replacement = f"{match.group(1)}{quote}{new_value}{quote}{match.group(5)}"
    text = text[:match.start()] + replacement + text[match.end():]
    file_path.write_text(text, encoding="utf-8")
    return True


def append_to_body(file_path, content):
    """Append content to the end of the post body."""
    text = file_path.read_text(encoding="utf-8")
    if not text.endswith("\n"):
        text += "\n"
    text += content
    file_path.write_text(text, encoding="utf-8")


def replace_body(file_path, new_body):
    """Replace the entire body (after front matter)."""
    text = file_path.read_text(encoding="utf-8")
    match = FRONT_MATTER_RE.match(text)
    if not match:
        return False
    fm_part = text[:match.end()]
    file_path.write_text(fm_part + new_body, encoding="utf-8")
    return True


def run_hugo_build():
    """Run Hugo build. Returns (success, output)."""
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
# Logging & learning library
# ===========================================================================

def load_json_file(path, default):
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default


def save_optimization_log(entries):
    log = load_json_file(OPTIMIZATION_LOG, {"optimizations": []})
    log["optimizations"].extend(entries)
    OPTIMIZATION_LOG.write_text(
        json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def save_learning_library(entries):
    lib = load_json_file(LEARNING_LIBRARY, {"optimizations": []})
    lib["optimizations"].extend(entries)
    LEARNING_LIBRARY.write_text(
        json.dumps(lib, indent=2, ensure_ascii=False), encoding="utf-8"
    )


# ===========================================================================
# Report generation
# ===========================================================================

def generate_report(analyses, executed, skipped, dry_run, error_code=None):
    """Generate Markdown optimization report."""
    today = datetime.now().strftime("%Y-%m-%d")
    report_path = REPORTS_DIR / f"content-optimization-results-{today}.md"

    lines = []
    lines.append("# ChinaBound Travel - Content Auto-Optimization Report")
    lines.append("")
    lines.append(f"- **Run date**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"- **Mode**: {'DRY-RUN (analysis only)' if dry_run else 'LIVE (changes applied)'}")
    lines.append(f"- **GSC site**: {SITE_URL}")
    lines.append(f"- **Data window**: {START_DATE} ~ {END_DATE}")
    lines.append(f"- **Safety limit**: max {MAX_AUTO_OPTIMIZE_PER_WEEK} pages/run")
    lines.append("")

    if error_code:
        lines.append("## Status: GSC API UNAVAILABLE")
        lines.append("")
        lines.append(f"Error code: `{error_code}`")
        lines.append("")
        lines.append("Please verify service-account permissions in Search Console.")
        report_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"[INFO] Report saved: {report_path}")
        return report_path

    # Summary
    lines.append("## Summary")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Pages analyzed | {len(analyses)} |")
    lines.append(f"| Pages with issues | {len([a for a in analyses if a['issues']])} |")
    lines.append(f"| Pages optimized | {len(executed)} |")
    lines.append(f"| Pages skipped (over limit) | {len(skipped)} |")
    lines.append("")

    # Problem pages table
    lines.append("## Problem Pages Identified")
    lines.append("")
    if analyses:
        lines.append("| # | Page | Impr | Clicks | Pos | Issues | Actions |")
        lines.append("|---|------|------|--------|-----|--------|---------|")
        for i, a in enumerate(analyses, 1):
            issues_str = ", ".join(a["issues"][:3]) if a["issues"] else "none"
            actions_str = ", ".join(a["recommended_actions"][:3])
            url_short = a["url"].replace(SITE_URL, "")[:50]
            lines.append(
                f"| {i} | {url_short} | {a['impressions']} | "
                f"{a['clicks']} | {a['position']} | {issues_str} | {actions_str} |"
            )
    else:
        lines.append("No problem pages found in this run.")
    lines.append("")

    # Executed optimizations
    if executed:
        lines.append("## Optimizations Applied")
        lines.append("")
        for entry in executed:
            lines.append(f"### {entry['page']}")
            lines.append("")
            lines.append(f"- **Actions**: {', '.join(entry['actions'])}")
            lines.append(f"- **Timestamp**: {entry['timestamp']}")
            lines.append(f"- **Metrics before**: impr={entry['metrics_before'].get('impressions')}, "
                         f"clicks={entry['metrics_before'].get('clicks')}, "
                         f"pos={entry['metrics_before'].get('position')}")
            lines.append("")
    elif not dry_run:
        lines.append("## Optimizations Applied")
        lines.append("")
        lines.append("None — all candidate pages exceeded safety limits or required manual review.")
        lines.append("")

    # Skipped
    if skipped:
        lines.append("## Pages Skipped (safety limit / manual review)")
        lines.append("")
        for s in skipped:
            lines.append(f"- **{s['url']}**: {s.get('reason', 'over limit')}")
        lines.append("")

    # Next steps
    lines.append("## Next Steps")
    lines.append("")
    lines.append("1. Deploy will trigger Cloudflare Pages build automatically.")
    lines.append("2. Track optimized pages for 2 weeks; compare impressions/clicks/CTR.")
    lines.append("3. Effective optimizations are recorded in `learning-library.json`.")
    lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[INFO] Report saved: {report_path}")
    return report_path


# ===========================================================================
# Main orchestration
# ===========================================================================

def main():
    parser = argparse.ArgumentParser(
        description="ChinaBound Travel content auto-optimizer (Loop 1)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Analyze only; do not modify any files"
    )
    parser.add_argument(
        "--max-pages", type=int, default=MAX_AUTO_OPTIMIZE_PER_WEEK,
        help=f"Max pages to optimize (default: {MAX_AUTO_OPTIMIZE_PER_WEEK})"
    )
    args = parser.parse_args()

    print("=" * 64)
    print("  ChinaBound Travel - Content Auto-Optimizer (Loop 1)")
    print(f"  Mode: {'DRY-RUN' if args.dry_run else 'LIVE'}  "
          f"Max pages: {args.max_pages}")
    print("=" * 64)
    print()

    # 1. Fetch GSC page data
    rows, error_code = fetch_page_level_gsc()
    if error_code:
        generate_report([], [], [], args.dry_run, error_code=error_code)
        return 1

    if not rows:
        print("[WARN] No GSC page data returned")
        generate_report([], [], [], args.dry_run)
        return 0

    # 2. Load baseline for rank-drop comparison
    baseline_positions = load_previous_baseline_positions()

    # 3. Convert rows to page dicts
    page_data_list = []
    for row in rows:
        page_url = row["keys"][0]
        page_data_list.append({
            "page": page_url,
            "clicks": row.get("clicks", 0),
            "impressions": row.get("impressions", 0),
            "ctr": row.get("ctr", 0),
            "position": row.get("position", 999),
        })

    # 4. Filter problem pages
    problem_pages = []
    for pd in page_data_list:
        is_problem = False
        # CTR problem
        if (pd["impressions"] > MIN_IMPRESSIONS_FOR_CTR_CHECK and
                pd["clicks"] == 0):
            is_problem = True
        # Rank drop
        prev = baseline_positions.get(pd["page"])
        if prev is not None and pd["position"] > prev + RANK_DROP_THRESHOLD:
            is_problem = True
        if is_problem:
            problem_pages.append(pd)

    # Sort by impressions descending (highest potential first)
    problem_pages.sort(key=lambda x: x["impressions"], reverse=True)
    print(f"[INFO] Found {len(problem_pages)} problem pages "
          f"(out of {len(page_data_list)} total)")

    # 5. Load all posts for analysis and internal linking
    all_posts = list_all_posts()
    print(f"[INFO] Loaded {len(all_posts)} content posts")

    # 6. Analyze each problem page
    analyses = []
    for pd in problem_pages:
        post_file = find_post_by_url(pd["page"])
        post = parse_post(post_file) if post_file else None
        analysis = analyze_page_issues(pd, post, baseline_positions)
        analyses.append(analysis)
        status = "FOUND" if post else "NOT_FOUND"
        print(f"  [{status}] {pd['page'][:60]} "
              f"impr={pd['impressions']} clicks={pd['clicks']} "
              f"pos={pd['position']:.1f} issues={analysis['issues']}")

    # 7. Execute optimizations (up to max_pages)
    executed = []
    skipped = []
    optimized_count = 0

    for analysis in analyses:
        if optimized_count >= args.max_pages:
            skipped.append({
                "url": analysis["url"],
                "reason": f"safety limit ({args.max_pages} pages/run reached)",
            })
            continue

        if not analysis["post_found"]:
            skipped.append({
                "url": analysis["url"],
                "reason": "content file not found",
            })
            continue

        if "flag_for_manual_review" in analysis["recommended_actions"]:
            # High-risk: only do low-risk sub-actions, flag the rest
            pass

        post_file = find_post_by_url(analysis["url"])
        post = parse_post(post_file)

        actions_applied = []
        backup_text = post_file.read_text(encoding="utf-8")

        try:
            # --- Title optimization ---
            if "optimize_title" in analysis["recommended_actions"]:
                new_title = optimize_title(post)
                if new_title != post["title"]:
                    if not args.dry_run:
                        modify_front_matter_field(post_file, "title", new_title)
                    actions_applied.append(f"title: '{post['title']}' -> '{new_title}'")
                    print(f"  [TITLE] {post_file.name}: {new_title}")

            # --- Description optimization ---
            if "optimize_description" in analysis["recommended_actions"]:
                new_desc = optimize_description(post)
                if new_desc != post["description"]:
                    if not args.dry_run:
                        modify_front_matter_field(post_file, "description", new_desc)
                    actions_applied.append("description optimized")
                    print(f"  [DESC] {post_file.name}: {new_desc[:80]}...")

            # --- FAQ addition ---
            if "add_faq" in analysis["recommended_actions"] and not post["has_faq"]:
                faq_content = generate_faq_section(post, analysis)
                if faq_content:
                    if not args.dry_run:
                        append_to_body(post_file, faq_content)
                    actions_applied.append("faq section added")
                    print(f"  [FAQ] {post_file.name}: FAQ section appended")

            # --- Internal links ---
            if "add_internal_links" in analysis["recommended_actions"]:
                # Re-parse post in case body changed
                post = parse_post(post_file)
                new_body, links_added = add_internal_links(post, all_posts)
                if links_added > 0:
                    if not args.dry_run:
                        replace_body(post_file, new_body)
                    actions_applied.append(f"{links_added} internal links added")
                    print(f"  [LINKS] {post_file.name}: +{links_added} links")

            # --- First paragraph rewrite (low-risk: only if mismatch) ---
            if "rewrite_first_paragraph" in analysis["recommended_actions"]:
                # This is moderate risk; in dry-run we just report
                actions_applied.append("first_paragraph_intent_flagged")
                print(f"  [PARA] {post_file.name}: first-paragraph intent "
                      f"mismatch flagged (manual review recommended)")

            if actions_applied and not args.dry_run:
                # Hugo build validation
                print(f"  [BUILD] Validating Hugo build for {post_file.name}...")
                success, build_output = run_hugo_build()
                if not success:
                    print(f"  [ROLLBACK] Hugo build FAILED, reverting "
                          f"{post_file.name}")
                    post_file.write_text(backup_text, encoding="utf-8")
                    skipped.append({
                        "url": analysis["url"],
                        "reason": "hugo build failed, rolled back",
                    })
                    continue

                # Update last_updated
                modify_front_matter_field(
                    post_file, "last_updated",
                    datetime.now().strftime("%Y-%m-%d")
                )

                optimized_count += 1
                timestamp = datetime.now().isoformat()
                log_entry = {
                    "page": analysis["url"],
                    "file": str(post_file.relative_to(BLOG_ROOT)),
                    "actions": actions_applied,
                    "timestamp": timestamp,
                    "metrics_before": {
                        "impressions": analysis["impressions"],
                        "clicks": analysis["clicks"],
                        "position": analysis["position"],
                    },
                    "result": "pending",
                }
                executed.append(log_entry)
                save_optimization_log([log_entry])

                # Learning library entry (pending evaluation)
                save_learning_library([{
                    "page": analysis["url"],
                    "action": ", ".join(actions_applied),
                    "date": timestamp,
                    "result": "pending",
                    "metrics_before": log_entry["metrics_before"],
                    "metrics_after": {},
                }])

            elif actions_applied and args.dry_run:
                optimized_count += 1
                executed.append({
                    "page": analysis["url"],
                    "file": str(post_file.relative_to(BLOG_ROOT)),
                    "actions": actions_applied,
                    "timestamp": datetime.now().isoformat(),
                    "metrics_before": {
                        "impressions": analysis["impressions"],
                        "clicks": analysis["clicks"],
                        "position": analysis["position"],
                    },
                    "result": "dry_run",
                })

        except Exception as exc:
            print(f"  [ERROR] Failed to optimize {post_file.name}: {exc}")
            # Rollback
            post_file.write_text(backup_text, encoding="utf-8")
            skipped.append({
                "url": analysis["url"],
                "reason": f"exception: {exc}",
            })

    # 8. Generate report
    report_path = generate_report(analyses, executed, skipped, args.dry_run)

    # 9. Console summary
    print("\n" + "=" * 64)
    print("  RUN SUMMARY")
    print("=" * 64)
    print(f"  Problem pages found : {len(problem_pages)}")
    print(f"  Pages optimized     : {len(executed)}")
    print(f"  Pages skipped       : {len(skipped)}")
    print(f"  Report              : {report_path}")
    print(f"  Mode                : {'DRY-RUN' if args.dry_run else 'LIVE'}")
    print("=" * 64)

    return 0


if __name__ == "__main__":
    sys.exit(main())
