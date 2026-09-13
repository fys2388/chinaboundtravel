#!/usr/bin/env python3
"""
ChinaBound Travel - P0 GSC 63-Page Scoring + Top 20 Growth Pages
Reads GSC keyword baseline + all 63 posts, outputs scoring CSV/MD and Top20 CSV/MD.
"""
import csv
import re
import os
import json
from collections import defaultdict
from pathlib import Path

# === PATHS ===
BASE = Path(r"E:\AI\dulizhan\travel-blog")
POSTS_DIR = BASE / "content" / "posts"
GSC_CSV = BASE / "reports" / "keyword-baseline-2026-09.csv"
REPORTS_DIR = BASE / "reports"
BASE_URL = "https://www.chinaboundtravel.com"

# === HIGH-VALUE KEYWORD CLUSTERS (for Search Potential scoring) ===
HIGH_VALUE_TERMS = {
    "visa": ["visa", "144-hour", "144 hour", "transit", "entry", "passport"],
    "payment": ["wechat pay", "alipay", "payment", "qr code", "paypal"],
    "transport": ["high-speed rail", "high speed train", "train", "transportation", "subway", "airport", "transfer"],
    "hotel": ["hotel", "accommodation", "booking", "stay"],
    "insurance": ["insurance", "safety", "safe"],
    "esim": ["esim", "vpn", "internet", "sim"],
    "itinerary": ["itinerary", "7-day", "7 day", "guide", "how to"],
}

COMMERCIAL_CATEGORIES = {
    "visa": 10, "payment": 10, "transport": 9, "transportation": 9,
    "hotel": 9, "accommodation": 9, "insurance": 10, "safety": 7,
    "internet": 8, "esim": 9, "food": 5, "culture": 3, "history": 3,
    "travel-tips": 6, "cities": 6, "travel": 5, "photography": 4,
    "camping": 6,
}


def parse_front_matter(text):
    """Parse YAML front matter between --- markers. Handles inline and multi-line lists."""
    fm = {}
    body = text
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            fm_text = text[3:end].strip()
            body = text[end + 3:].strip()
            lines = fm_text.split("\n")
            i = 0
            current_list_key = None
            while i < len(lines):
                line = lines[i]
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    i += 1
                    continue
                # Check if this is a list item continuation (starts with -)
                if stripped.startswith("- ") and current_list_key:
                    item = stripped[2:].strip().strip('"').strip("'")
                    fm[current_list_key].append(item)
                    i += 1
                    continue
                if ":" in stripped:
                    key, _, val = stripped.partition(":")
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    current_list_key = None
                    if key in ("tags", "categories"):
                        if val.startswith("["):
                            val = [x.strip().strip('"').strip("'") for x in val.strip("[]").split(",") if x.strip()]
                            current_list_key = None
                        elif val == "":
                            val = []
                            current_list_key = key
                        else:
                            val = [val]
                    fm[key] = val
                i += 1
    return fm, body


def extract_first_paragraph(body):
    """Extract first meaningful text paragraph, skipping headings, shortcodes, blank lines."""
    lines = body.split("\n")
    para_lines = []
    in_shortcode = False
    for line in lines:
        stripped = line.strip()
        # skip headings
        if stripped.startswith("#"):
            if para_lines:
                break
            continue
        # skip shortcode open/close - check closing tags FIRST
        if stripped.startswith("{{< /"):
            in_shortcode = False
            continue
        if stripped.startswith("{{<") and not stripped.endswith("/>}}"):
            in_shortcode = True
            continue
        if stripped.endswith("/>}}"):
            in_shortcode = False
            continue
        if in_shortcode:
            continue
        # skip images, html comments
        if stripped.startswith("![") or stripped.startswith("<!--"):
            continue
        if stripped:
            para_lines.append(stripped)
        elif para_lines:
            break
    return " ".join(para_lines)


def count_internal_links(body):
    """Count internal markdown links pointing to /posts/ or / (root-relative)."""
    # Match [text](/path) or [text](/posts/slug)
    links = re.findall(r'\]\((/[^)]*)\)', body)
    # exclude anchor-only and external
    internal = [l for l in links if l.startswith("/") and not l.startswith("//")]
    return len(internal)


def count_affiliate_cta(body):
    """Count affiliate/commercial shortcodes."""
    patterns = [
        r'\{\{<\s*affiliate',
        r'\{\{<\s*klook',
        r'\{\{<\s*soft-recommend',
        r'\{\{<\s*booking',
        r'\{\{<\s*agoda',
        r'\{\{<\s*trip',
        r'\{\{<\s*getyourguide',
        r'\{\{<\s*travelpayouts',
    ]
    count = 0
    for p in patterns:
        count += len(re.findall(p, body, re.IGNORECASE))
    return count


def determine_search_intent(title, description, categories, keywords_for_url):
    """Classify search intent: informational, transactional, navigational, commercial."""
    title_lower = title.lower()
    desc_lower = (description or "").lower()
    cats_lower = [c.lower() for c in (categories if isinstance(categories, list) else [])]

    transactional_signals = ["buy", "book", "price", "cost", "best", "review", "vs", "compare",
                             "insurance", "ticket", "booking", "reservation"]
    commercial_signals = ["guide", "how to", "tips", "best", "ultimate", "complete", "review"]
    navigational_signals = ["login", "official", "app"]

    text = title_lower + " " + desc_lower
    for s in transactional_signals:
        if s in text:
            return "transactional"
    if any(c in cats_lower for c in ["visa", "payment", "insurance", "hotel", "accommodation"]):
        return "commercial"
    for s in commercial_signals:
        if s in text:
            return "commercial_investigational"
    if any(c in cats_lower for c in ["history", "culture"]):
        return "informational"
    return "informational"


def score_title(title, core_keywords):
    """Score title 1-10: length, keyword inclusion, clarity."""
    if not title:
        return 2
    score = 5
    t_len = len(title)
    # ideal 50-60 chars
    if 50 <= t_len <= 60:
        score += 3
    elif 40 <= t_len < 50 or 60 < t_len <= 70:
        score += 2
    elif 30 <= t_len < 40 or 70 < t_len <= 80:
        score += 1
    else:
        score -= 1
    # keyword presence
    title_lower = title.lower()
    kw_hits = sum(1 for kw in core_keywords if kw.lower() in title_lower)
    if kw_hits >= 2:
        score += 2
    elif kw_hits == 1:
        score += 1
    return min(10, max(1, score))


def score_first_para(para, core_keywords):
    """Score first paragraph 1-10: keyword presence, length, direct answer."""
    if not para:
        return 2
    score = 4
    p_len = len(para)
    if 80 <= p_len <= 200:
        score += 3
    elif 50 <= p_len < 80 or 200 < p_len <= 300:
        score += 2
    elif p_len > 300:
        score += 1
    para_lower = para.lower()
    kw_hits = sum(1 for kw in core_keywords if kw.lower() in para_lower)
    if kw_hits >= 2:
        score += 3
    elif kw_hits == 1:
        score += 2
    # direct answer signals
    if any(w in para_lower for w in ["is", "are", "you can", "need to", "should"]):
        score += 1
    return min(10, max(1, score))


def get_commercial_value(title, categories, affiliate_count):
    """Score commercial value 1-10 based on categories, title keywords, affiliate presence."""
    cats = [c.lower() for c in (categories if isinstance(categories, list) else [])]
    title_lower = title.lower()
    score = 3  # baseline

    # Check categories first
    for cat in cats:
        if cat in COMMERCIAL_CATEGORIES:
            score = max(score, COMMERCIAL_CATEGORIES[cat])

    # Check title keywords for commercial intent (boost if categories missed it)
    title_commercial_signals = {
        "visa": 10, "144-hour": 10, "144 hour": 10, "transit": 8,
        "wechat pay": 10, "alipay": 10, "payment": 9, "qr code": 8,
        "high-speed": 9, "high speed": 9, "train": 7, "transport": 8, "transportation": 8,
        "airport": 7, "transfer": 7, "subway": 7,
        "hotel": 9, "accommodation": 9, "booking": 8, "stay": 6,
        "insurance": 10, "safe": 7, "safety": 7,
        "esim": 9, "vpn": 8, "internet": 7, "sim": 7,
        "business": 8, "insurance": 10, "ticket": 8,
        "itinerary": 7, "7-day": 7, "packing": 5,
        "bargaining": 6, "shopping": 6,
    }
    for keyword, val in title_commercial_signals.items():
        if keyword in title_lower:
            score = max(score, val)

    # boost if affiliate CTAs present
    if affiliate_count >= 5:
        score = min(10, score + 1)
    elif affiliate_count == 0:
        score = max(1, score - 2)
    return min(10, max(1, score))


def get_search_potential(title, categories, keywords_for_url, total_impressions):
    """Score search potential 1-10 based on topic value and GSC signals."""
    title_lower = title.lower()
    cats = [c.lower() for c in (categories if isinstance(categories, list) else [])]
    score = 3

    # Check high-value clusters
    cluster_scores = []
    for cluster, terms in HIGH_VALUE_TERMS.items():
        for term in terms:
            if term in title_lower or any(term in c for c in cats):
                if cluster in ("visa", "payment"):
                    cluster_scores.append(10)
                elif cluster in ("transport", "insurance", "esim"):
                    cluster_scores.append(9)
                elif cluster in ("hotel",):
                    cluster_scores.append(8)
                elif cluster == "itinerary":
                    cluster_scores.append(7)
                break
    if cluster_scores:
        score = max(cluster_scores)

    # Boost from actual GSC impressions
    if total_impressions >= 15:
        score = min(10, score + 1)
    elif total_impressions >= 5:
        score = min(10, score + 0.5)

    # Keywords with good positions boost
    best_pos = min((k["position"] for k in keywords_for_url), default=100)
    if best_pos <= 30:
        score = min(10, score + 1)
    elif best_pos <= 50:
        score = min(10, score + 0.5)

    return round(min(10, max(1, score)), 1)


def get_content_quality(body, word_count, internal_links, affiliate_count, first_para_score):
    """Score content quality 1-10."""
    score = 4
    # word count
    if word_count >= 2000:
        score += 3
    elif word_count >= 1500:
        score += 2
    elif word_count >= 1000:
        score += 1
    elif word_count < 500:
        score -= 1
    # internal links
    if internal_links >= 5:
        score += 2
    elif internal_links >= 3:
        score += 1
    # affiliate / commercial structure
    if affiliate_count >= 3:
        score += 1
    # FAQ presence
    if re.search(r'(faq|frequently asked|q&a)', body, re.IGNORECASE):
        score += 1
    # first para quality
    score += first_para_score / 5  # normalize
    # headings structure
    h2_count = len(re.findall(r'^##\s', body, re.MULTILINE))
    if h2_count >= 5:
        score += 1
    elif h2_count >= 3:
        score += 0.5
    return round(min(10, max(1, score)), 1)


def load_gsc_data():
    """Load and aggregate GSC CSV by URL."""
    url_data = defaultdict(lambda: {
        "impressions": 0, "clicks": 0, "keywords": [],
        "positions": [], "best_position": 999, "avg_position": 0
    })
    with open(GSC_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row.get("URL", "").strip()
            if not url:
                continue
            try:
                pos = float(row.get("Position", 999))
            except (ValueError, TypeError):
                pos = 999
            try:
                imp = int(row.get("Impressions", 0))
            except (ValueError, TypeError):
                imp = 0
            try:
                clk = int(row.get("Clicks", 0))
            except (ValueError, TypeError):
                clk = 0
            kw = row.get("Keyword", "").strip()
            url_data[url]["impressions"] += imp
            url_data[url]["clicks"] += clk
            url_data[url]["keywords"].append({"keyword": kw, "position": pos, "impressions": imp})
            url_data[url]["positions"].append(pos)
            if pos < url_data[url]["best_position"]:
                url_data[url]["best_position"] = pos
    # compute avg position
    for url, d in url_data.items():
        if d["positions"]:
            d["avg_position"] = round(sum(d["positions"]) / len(d["positions"]), 1)
        else:
            d["avg_position"] = 0
    return dict(url_data)


def normalize_url(url):
    """Normalize URL for matching: strip trailing slash, lowercase."""
    if not url:
        return ""
    url = url.strip().rstrip("/")
    return url.lower()


def main():
    print("=== Loading GSC data ===")
    gsc_data = load_gsc_data()
    print(f"Loaded GSC data for {len(gsc_data)} URLs")

    # Build normalized lookup
    gsc_norm = {normalize_url(k): v for k, v in gsc_data.items()}

    # Get all post files
    post_files = sorted(POSTS_DIR.glob("*.md"))
    print(f"Found {len(post_files)} post files")

    results = []

    for pf in post_files:
        filename = pf.name
        try:
            text = pf.read_text(encoding="utf-8-sig")
        except Exception as e:
            print(f"  ERROR reading {filename}: {e}")
            continue

        fm, body = parse_front_matter(text)

        title = fm.get("title", "")
        description = fm.get("description", "")
        categories = fm.get("categories", [])
        tags = fm.get("tags", [])
        canonical = fm.get("canonicalURL", "")

        # Derive slug: prefer front matter slug, then strip date prefix from filename
        raw_slug = filename.replace(".md", "")
        fm_slug = fm.get("slug", "")
        if fm_slug:
            slug = fm_slug
        else:
            slug = re.sub(r'^\d{4}-\d{2}-\d{2}-', '', raw_slug)
        # Construct URL - canonical takes priority
        if canonical:
            url = canonical
        else:
            url = f"{BASE_URL}/posts/{slug}/"

        # Try multiple URL formats for GSC matching (date-prefixed and non-prefixed)
        candidate_urls = [
            normalize_url(url),
            normalize_url(f"{BASE_URL}/posts/{slug}/"),
            normalize_url(f"{BASE_URL}/posts/{raw_slug}/"),
        ]
        if canonical:
            candidate_urls.append(normalize_url(canonical))

        # Match GSC data - try each candidate
        gsc = None
        matched_url = None
        for cand in candidate_urls:
            if cand in gsc_norm:
                gsc = gsc_norm[cand]
                matched_url = cand
                break
        if gsc:
            indexed = True
            total_impressions = gsc["impressions"]
            total_clicks = gsc["clicks"]
            keyword_count = len(gsc["keywords"])
            best_position = gsc["best_position"]
            avg_position = gsc["avg_position"]
            keywords_for_url = gsc["keywords"]
        else:
            indexed = False
            total_impressions = 0
            total_clicks = 0
            keyword_count = 0
            best_position = None
            avg_position = None
            keywords_for_url = []

        # Core keywords from GSC + title
        core_keywords = [k["keyword"] for k in keywords_for_url[:3]]
        if not core_keywords:
            # derive from title
            core_keywords = [w for w in re.findall(r'[a-zA-Z]{4,}', title.lower())
                             if w not in ("guide", "2026", "complete", "ultimate", "china", "your")]

        # Metrics
        internal_links = count_internal_links(body)
        affiliate_cta = count_affiliate_cta(body)
        first_para = extract_first_paragraph(body)
        word_count = len(re.findall(r'\b\w+\b', body))

        # Scores
        title_score = score_title(title, core_keywords)
        h1_score = title_score  # H1 is typically the title or first heading
        first_para_score = score_first_para(first_para, core_keywords)
        search_intent = determine_search_intent(title, description, categories, keywords_for_url)
        commercial_value = get_commercial_value(title, categories, affiliate_cta)
        search_potential = get_search_potential(title, categories, keywords_for_url, total_impressions)
        content_quality = get_content_quality(body, word_count, internal_links, affiliate_cta, first_para_score)

        # CTR opportunity score
        if best_position and best_position <= 20:
            ctr_opportunity = 10
        elif best_position and best_position <= 40:
            ctr_opportunity = 8
        elif best_position and best_position <= 60:
            ctr_opportunity = 6
        elif best_position:
            ctr_opportunity = 4
        else:
            ctr_opportunity = 2

        # Current impressions score
        if total_impressions >= 15:
            imp_score = 10
        elif total_impressions >= 10:
            imp_score = 8
        elif total_impressions >= 5:
            imp_score = 6
        elif total_impressions >= 1:
            imp_score = 4
        else:
            imp_score = 2

        # Growth Score = Search Potential × Current Impressions × CTR Opportunity × Commercial Value × Content Quality
        # Normalize: product of 5 factors (each 1-10), then scale to 0-10000
        growth_score = round(
            search_potential * imp_score * ctr_opportunity * commercial_value * content_quality, 1
        )

        # Grade assignment
        # A: Impressions >= 10 OR best_pos <= 30 + commercial value >= 7
        # B: Impressions 3-9 OR best_pos 30-50 + content quality >= 6
        # C: Impressions 1-2 OR best_pos 50-70
        # D: no GSC data
        # E: duplicate/low value (detected by title similarity, very low content quality)
        grade = "D"
        notes = ""

        if not indexed:
            grade = "D"
            notes = "no GSC data"
        else:
            has_top30 = best_position and best_position <= 30
            has_30_50 = best_position and 30 < best_position <= 50
            has_50_70 = best_position and 50 < best_position <= 70

            if (total_impressions >= 10 or has_top30) and commercial_value >= 6:
                grade = "A"
                notes = f"High potential: {total_impressions} imp, best pos {best_position}"
            elif (3 <= total_impressions <= 9) or has_30_50:
                if content_quality >= 5:
                    grade = "B"
                    notes = f"CTR optimization: {total_impressions} imp, best pos {best_position}"
                else:
                    grade = "C"
                    notes = f"Needs content enhancement: {total_impressions} imp, best pos {best_position}"
            elif (1 <= total_impressions <= 2) or has_50_70:
                grade = "C"
                notes = f"Low signal: {total_impressions} imp, best pos {best_position}"
            elif total_impressions == 0 and keyword_count > 0:
                grade = "C"
                notes = f"Ranked but 0 imp: {keyword_count} keywords, best pos {best_position}"
            else:
                grade = "D"
                notes = "Minimal GSC signal"

        # E grade: detect duplicates / low value
        # Monthly updates are low SEO value
        if "monthly-update" in slug or "monthly update" in title.lower():
            grade = "E"
            notes = "Monthly update - low evergreen SEO value, consider merging"
        # Very short content
        elif word_count < 400 and grade in ("C", "D"):
            grade = "E"
            notes = f"Thin content ({word_count} words) - merge or expand"

        results.append({
            "filename": filename,
            "slug": slug,
            "url": url,
            "title": title,
            "indexed": indexed,
            "total_impressions": total_impressions,
            "total_clicks": total_clicks,
            "keyword_count": keyword_count,
            "best_position": best_position if best_position else "N/A",
            "avg_position": avg_position if avg_position else "N/A",
            "search_intent": search_intent,
            "title_score": title_score,
            "h1_score": h1_score,
            "first_para_score": first_para_score,
            "internal_link_count": internal_links,
            "affiliate_cta_count": affiliate_cta,
            "commercial_value": commercial_value,
            "content_quality": content_quality,
            "search_potential": search_potential,
            "ctr_opportunity": ctr_opportunity,
            "imp_score": imp_score,
            "growth_score": growth_score,
            "grade": grade,
            "notes": notes,
            "word_count": word_count,
            "first_para_preview": first_para[:120] if first_para else "",
        })

    # === OUTPUT 1: Scoring CSV ===
    csv_path = REPORTS_DIR / "P0_GSC_PAGE_SCORING.csv"
    fieldnames = ["filename", "slug", "url", "title", "indexed", "total_impressions",
                  "total_clicks", "keyword_count", "best_position", "avg_position",
                  "search_intent", "title_score", "h1_score", "first_para_score",
                  "internal_link_count", "affiliate_cta_count", "commercial_value",
                  "grade", "notes"]
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in sorted(results, key=lambda x: x["growth_score"], reverse=True):
            writer.writerow({k: r[k] for k in fieldnames})
    print(f"\nWritten: {csv_path}")

    # === OUTPUT 2: Scoring MD Report ===
    grade_counts = defaultdict(int)
    for r in results:
        grade_counts[r["grade"]] += 1

    md_lines = []
    md_lines.append("# ChinaBound Travel - P0 GSC 63-Page Scoring Report\n")
    md_lines.append(f"- **Generated**: 2026-09-08")
    md_lines.append(f"- **Total pages analyzed**: {len(results)}")
    md_lines.append(f"- **GSC data source**: keyword-baseline-2026-09.csv (Top 20 keywords by impressions)")
    md_lines.append(f"- **Base URL**: {BASE_URL}\n")

    md_lines.append("## 1. Grade Distribution Summary\n")
    md_lines.append("| Grade | Count | Description |")
    md_lines.append("|-------|-------|-------------|")
    grade_desc = {
        "A": "High potential - optimize for CTR & conversions",
        "B": "Has impressions - redo Title/Description",
        "C": "Low signal - enhance content & internal links",
        "D": "No GSC data - hold for now",
        "E": "Low value/duplicate - merge or restructure",
    }
    for g in ["A", "B", "C", "D", "E"]:
        md_lines.append(f"| {g} | {grade_counts.get(g, 0)} | {grade_desc[g]} |")
    md_lines.append("")

    # Indexed stats
    indexed_count = sum(1 for r in results if r["indexed"])
    total_imp = sum(r["total_impressions"] for r in results)
    md_lines.append(f"**Indexed with GSC data**: {indexed_count}/{len(results)} pages")
    md_lines.append(f"**Total impressions tracked**: {total_imp}")
    md_lines.append(f"**Total clicks**: 0 (site-wide)\n")

    # A Grade detailed
    md_lines.append("## 2. Grade A - High Priority Pages (Detailed Analysis)\n")
    a_pages = [r for r in results if r["grade"] == "A"]
    a_pages.sort(key=lambda x: x["growth_score"], reverse=True)
    if a_pages:
        md_lines.append("| # | Title | URL | Impressions | Best Pos | Keywords | Commercial | Growth Score | Key Issue |")
        md_lines.append("|---|-------|-----|-------------|----------|----------|------------|--------------|-----------|")
        for i, r in enumerate(a_pages, 1):
            md_lines.append(
                f"| {i} | {r['title'][:50]} | /posts/{r['slug']}/ | {r['total_impressions']} | "
                f"{r['best_position']} | {r['keyword_count']} | {r['commercial_value']}/10 | "
                f"{r['growth_score']} | {r['notes'][:40]} |"
            )
    else:
        md_lines.append("No Grade A pages found.")
    md_lines.append("")

    # A page recommendations
    if a_pages:
        md_lines.append("### A-Grade Optimization Priorities\n")
        for r in a_pages:
            md_lines.append(f"**{r['title']}**")
            md_lines.append(f"- URL: {r['url']}")
            md_lines.append(f"- GSC: {r['total_impressions']} imp, best rank #{r['best_position']}, {r['keyword_count']} keywords")
            md_lines.append(f"- Title score: {r['title_score']}/10 | First para: {r['first_para_score']}/10 | Internal links: {r['internal_link_count']}")
            if r['title_score'] < 7:
                md_lines.append(f"- **Action**: Rewrite meta title to include core keyword, target 50-60 chars")
            if r['first_para_score'] < 6:
                md_lines.append(f"- **Action**: Strengthen first paragraph with direct answer + keyword")
            if r['internal_link_count'] < 3:
                md_lines.append(f"- **Action**: Add 2-3 internal links to related pillar pages")
            md_lines.append("")

    # B Grade
    md_lines.append("## 3. Grade B - Title/Description Optimization Candidates\n")
    b_pages = [r for r in results if r["grade"] == "B"]
    b_pages.sort(key=lambda x: x["total_impressions"], reverse=True)
    if b_pages:
        md_lines.append("| # | Title | Impressions | Best Pos | Title Score | Recommended Title Direction |")
        md_lines.append("|---|-------|-------------|----------|-------------|----------------------------|")
        for i, r in enumerate(b_pages, 1):
            # Suggest title direction
            suggestion = f"Include top keyword + year + benefit; current: {r['title_score']}/10"
            md_lines.append(f"| {i} | {r['title'][:50]} | {r['total_impressions']} | {r['best_position']} | {r['title_score']}/10 | {suggestion} |")
    else:
        md_lines.append("No Grade B pages found.")
    md_lines.append("")

    # E Grade
    md_lines.append("## 4. Grade E - Low Value / Duplicate Pages (Merge or Restructure)\n")
    e_pages = [r for r in results if r["grade"] == "E"]
    if e_pages:
        md_lines.append("| # | Title | Word Count | Reason |")
        md_lines.append("|---|-------|------------|--------|")
        for i, r in enumerate(e_pages, 1):
            md_lines.append(f"| {i} | {r['title'][:55]} | {r['word_count']} | {r['notes']} |")
        md_lines.append("")
        md_lines.append("### Recommendations for E-Grade:\n")
        md_lines.append("- **Monthly updates**: Consolidate key policy changes into evergreen pillar pages, then 301-redirect")
        md_lines.append("- **Thin content**: Merge into related comprehensive guides or expand to 1000+ words")
        md_lines.append("- **Duplicate topics**: Identify canonical version, consolidate and redirect others")
    else:
        md_lines.append("No Grade E pages found.")
    md_lines.append("")

    # Full scoring table
    md_lines.append("## 5. Complete 63-Page Scoring Table\n")
    md_lines.append("| # | File | Grade | Imp | Best Pos | KW | Title | H1 | 1stPara | IL | Aff | CV | CQ | Growth |")
    md_lines.append("|---|------|-------|-----|----------|-----|-------|-----|---------|-----|-----|-----|-----|--------|")
    for i, r in enumerate(sorted(results, key=lambda x: x["growth_score"], reverse=True), 1):
        md_lines.append(
            f"| {i} | {r['filename'][:40]} | {r['grade']} | {r['total_impressions']} | "
            f"{r['best_position']} | {r['keyword_count']} | {r['title_score']} | {r['h1_score']} | "
            f"{r['first_para_score']} | {r['internal_link_count']} | {r['affiliate_cta_count']} | "
            f"{r['commercial_value']} | {r['content_quality']} | {r['growth_score']} |"
        )
    md_lines.append("")
    md_lines.append("*IL = Internal Links, Aff = Affiliate CTAs, CV = Commercial Value, CQ = Content Quality*\n")

    md_path = REPORTS_DIR / "P0_GSC_PAGE_SCORING.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"Written: {md_path}")

    # === OUTPUT 3: Top 20 Growth Pages ===
    top20 = sorted([r for r in results if r["grade"] != "E"], key=lambda x: x["growth_score"], reverse=True)[:20]

    # Recommendations for each top 20
    def get_recommendation(r):
        actions = []
        if r["title_score"] < 7:
            actions.append("rewrite title")
        if r["first_para_score"] < 6:
            actions.append("strengthen intro")
        if r["internal_link_count"] < 3:
            actions.append("add internal links")
        if r["grade"] == "A":
            actions.append("optimize CTR & add affiliate CTA")
        elif r["grade"] == "B":
            actions.append("optimize meta description")
        elif r["grade"] == "C":
            actions.append("expand content depth")
        if not actions:
            actions.append("maintain & monitor ranking")
        return "; ".join(actions)

    # Top20 MD
    t20_lines = []
    t20_lines.append("# ChinaBound Travel - Top 20 Growth Pages Ranking\n")
    t20_lines.append(f"- **Generated**: 2026-09-08")
    t20_lines.append(f"- **Formula**: Growth Score = Search Potential × Impression Score × CTR Opportunity × Commercial Value × Content Quality")
    t20_lines.append(f"- **Total pages evaluated**: {len(results)}\n")

    t20_lines.append("## Growth Score Formula\n")
    t20_lines.append("| Factor | Scale | Description |")
    t20_lines.append("|--------|-------|-------------|")
    t20_lines.append("| Search Potential | 1-10 | Topic search volume & competition (visa/payment/transport highest) |")
    t20_lines.append("| Current Impressions | 1-10 | GSC actual impressions (≥15→10, 10-14→8, 5-9→6, 1-4→4, 0→2) |")
    t20_lines.append("| CTR Opportunity | 1-10 | Ranking position (≤20→10, 20-40→8, 40-60→6, 60+→4, none→2) |")
    t20_lines.append("| Commercial Value | 1-10 | Affiliate monetization potential (visa/payment/insurance highest) |")
    t20_lines.append("| Content Quality | 1-10 | Word count, structure, internal links, FAQ, first para |")
    t20_lines.append("")

    t20_lines.append("## Top 20 Ranking Table\n")
    t20_lines.append("| Rank | Title | Grade | SP | Imp | CTR | CV | CQ | **Growth Score** | Recommended Action |")
    t20_lines.append("|------|-------|-------|-----|-----|-----|-----|-----|------------------|-------------------|")
    for i, r in enumerate(top20, 1):
        t20_lines.append(
            f"| {i} | {r['title'][:45]} | {r['grade']} | {r['search_potential']} | "
            f"{r['imp_score']} | {r['ctr_opportunity']} | {r['commercial_value']} | "
            f"{r['content_quality']} | **{r['growth_score']}** | {get_recommendation(r)} |"
        )
    t20_lines.append("")

    # Detailed per-page
    t20_lines.append("## Detailed Optimization Recommendations\n")
    for i, r in enumerate(top20, 1):
        t20_lines.append(f"### #{i} {r['title']}\n")
        t20_lines.append(f"- **URL**: {r['url']}")
        t20_lines.append(f"- **Grade**: {r['grade']} | **Growth Score**: {r['growth_score']}")
        t20_lines.append(f"- **GSC**: {r['total_impressions']} impressions, best position #{r['best_position']}, {r['keyword_count']} keywords")
        t20_lines.append(f"- **Scores**: SP={r['search_potential']} | Imp={r['imp_score']} | CTR={r['ctr_opportunity']} | CV={r['commercial_value']} | CQ={r['content_quality']}")
        t20_lines.append(f"- **Content**: {r['word_count']} words, {r['internal_link_count']} internal links, {r['affiliate_cta_count']} affiliate CTAs")
        t20_lines.append(f"- **Search Intent**: {r['search_intent']}")
        # Specific 1-2 sentence recommendation
        rec = get_recommendation(r)
        t20_lines.append(f"- **Action**: {rec}")
        if r['title_score'] < 7:
            t20_lines.append(f"  - Current title ({r['title_score']}/10): \"{r['title'][:60]}\" → target 50-60 chars with primary keyword")
        if r['first_para_score'] < 6:
            t20_lines.append(f"  - First paragraph ({r['first_para_score']}/10) needs direct answer + keyword in first 150 chars")
        t20_lines.append("")

    t20_md_path = REPORTS_DIR / "P0_TOP20_GROWTH_PAGES.md"
    t20_md_path.write_text("\n".join(t20_lines), encoding="utf-8")
    print(f"Written: {t20_md_path}")

    # Top20 CSV
    t20_csv_path = REPORTS_DIR / "P0_TOP20_GROWTH_PAGES.csv"
    t20_fields = ["rank", "filename", "title", "url", "search_potential", "current_impressions",
                  "ctr_opportunity", "commercial_value", "content_quality", "growth_score",
                  "grade", "recommended_action"]
    with open(t20_csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=t20_fields)
        writer.writeheader()
        for i, r in enumerate(top20, 1):
            writer.writerow({
                "rank": i,
                "filename": r["filename"],
                "title": r["title"],
                "url": r["url"],
                "search_potential": r["search_potential"],
                "current_impressions": r["total_impressions"],
                "ctr_opportunity": r["ctr_opportunity"],
                "commercial_value": r["commercial_value"],
                "content_quality": r["content_quality"],
                "growth_score": r["growth_score"],
                "grade": r["grade"],
                "recommended_action": get_recommendation(r),
            })
    print(f"Written: {t20_csv_path}")

    # === SUMMARY PRINT ===
    print("\n" + "=" * 60)
    print("SCORING SUMMARY")
    print("=" * 60)
    for g in ["A", "B", "C", "D", "E"]:
        print(f"  Grade {g}: {grade_counts.get(g, 0)} pages")
    print(f"\n  Top 5 Growth Pages:")
    for i, r in enumerate(top20[:5], 1):
        print(f"    {i}. [{r['grade']}] {r['title'][:50]} (score={r['growth_score']}, imp={r['total_impressions']})")
    print("\nDone!")


if __name__ == "__main__":
    main()
