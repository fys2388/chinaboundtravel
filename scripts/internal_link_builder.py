#!/usr/bin/env python3
"""
Internal Link Builder for chinaboundtravel blog posts.
Analyzes tag/category/keyword overlap between posts, finds Top 5 related posts,
and appends a "Related Reading" section to each post.

Usage:
  python internal_link_builder.py --dry-run    # preview only
  python internal_link_builder.py --apply      # write changes
"""
import os
import re
import json
import argparse
from pathlib import Path
from collections import Counter
from datetime import datetime

CONTENT_DIR = Path(r"E:\AI\dulizhan\travel-blog\content\posts")
BACKUP_DIR = Path(r"E:\AI\dulizhan\travel-blog\auto-script\backup\content\posts")
SITE_BASE = "https://www.chinaboundtravel.com"

# Common English stop words for keyword extraction
STOP_WORDS = set("""
a an the and or but if then else when at by for with about against between into through during before after above below to from up down in out on off over under again further then once here there when where why how all any both each few more most other some such no nor not only own same so than too very can will just should now
is are was were be been being have has had having do does did doing i me my myself we our ours ourselves you your yours yourself yourselves he him his himself she her hers herself it its itself they them their theirs themselves what which who whom this that these those am
""".split())

def parse_front_matter(content, filename=""):
    """Parse Hugo front matter (--- delimited YAML-like)."""
    if not content.startswith('---'):
        # No front matter — derive title from body or filename
        fm = {}
        body = content.strip()
        h_match = re.search(r'^#{1,2}\s+(.+)$', body, re.MULTILINE)
        if h_match:
            fm['title'] = h_match.group(1).strip()
        else:
            stem = filename.replace('.md', '').replace('-', ' ').replace('_', ' ')
            stem = re.sub(r'^\d{4}-\d{2}-\d{2}-', '', stem)
            fm['title'] = stem.title()
        fm['tags'] = []
        fm['categories'] = []
        return fm, body
    end = content.find('---', 3)
    if end == -1:
        return {}, content
    fm_text = content[3:end].strip()
    body = content[end+3:].strip()
    fm = {}
    # Simple parser for the fields we need
    for line in fm_text.split('\n'):
        line = line.strip()
        if line.startswith('title:'):
            val = line.split(':', 1)[1].strip().strip('"').strip("'")
            if val:
                fm['title'] = val
        elif line.startswith('draft:'):
            fm['draft'] = 'true' in line.lower()
        elif line.startswith('canonicalURL:'):
            fm['canonicalURL'] = line.split(':', 1)[1].strip().strip('"').strip("'")
        elif line.startswith('categories:'):
            cats = re.findall(r'"([^"]*)"', line)
            if not cats:
                cats = re.findall(r"'([^']*)'", line)
            fm['categories'] = [c.lower() for c in cats]
        elif line.startswith('tags:'):
            fm['tags'] = []  # multi-line, parse below
    # Parse multi-line tags
    if 'tags' in fm:
        in_tags = False
        tags = []
        for line in fm_text.split('\n'):
            stripped = line.strip()
            if stripped.startswith('tags:'):
                in_tags = True
                inline = re.findall(r'"([^"]*)"', stripped)
                if inline:
                    tags = inline
                    in_tags = False
                continue
            if in_tags:
                if stripped.startswith('- '):
                    tags.append(stripped[2:].strip().strip('"').strip("'"))
                elif stripped and not stripped.startswith('#'):
                    in_tags = False
        fm['tags'] = [t.lower() for t in tags]
    # Fallback title: from first H1/H2 in body, or from filename
    if 'title' not in fm or not fm['title']:
        h_match = re.search(r'^#{1,2}\s+(.+)$', body, re.MULTILINE)
        if h_match:
            fm['title'] = h_match.group(1).strip()
        else:
            stem = filename.replace('.md', '').replace('-', ' ').replace('_', ' ')
            stem = re.sub(r'^\d{4}-\d{2}-\d{2}-', '', stem)
            fm['title'] = stem.title()
    return fm, body

def extract_keywords(text, top_n=15):
    """Extract top keywords from body text."""
    # Remove markdown syntax
    text = re.sub(r'[#*`\[\]()!|>_-]', ' ', text)
    text = re.sub(r'<[^>]+>', ' ', text)
    words = re.findall(r'[a-zA-Z]{3,}', text.lower())
    words = [w for w in words if w not in STOP_WORDS and len(w) > 2]
    counter = Counter(words)
    return set(w for w, _ in counter.most_common(top_n))

def compute_similarity(post_a, post_b):
    """Compute relevance score between two posts."""
    score = 0.0
    # Tag overlap (high weight)
    tags_a = set(post_a.get('tags', []))
    tags_b = set(post_b.get('tags', []))
    tag_overlap = tags_a & tags_b
    if tags_a and tags_b:
        score += len(tag_overlap) / max(len(tags_a), len(tags_b)) * 40
    # Category overlap (medium weight)
    cats_a = set(post_a.get('categories', []))
    cats_b = set(post_b.get('categories', []))
    cat_overlap = cats_a & cats_b
    if cats_a and cats_b:
        score += len(cat_overlap) / max(len(cats_a), len(cats_b)) * 25
    # Keyword overlap (medium weight)
    kw_a = post_a.get('keywords', set())
    kw_b = post_b.get('keywords', set())
    kw_overlap = kw_a & kw_b
    if kw_a and kw_b:
        score += len(kw_overlap) / max(len(kw_a), len(kw_b)) * 20
    # Title keyword match (low weight)
    title_words_a = set(re.findall(r'[a-zA-Z]{4,}', post_a.get('title', '').lower())) - STOP_WORDS
    title_words_b = set(re.findall(r'[a-zA-Z]{4,}', post_b.get('title', '').lower())) - STOP_WORDS
    title_overlap = title_words_a & title_words_b
    if title_words_a and title_words_b:
        score += len(title_overlap) / max(len(title_words_a), len(title_words_b)) * 15
    return score

def get_post_url(post, filename):
    """Derive post URL from canonicalURL or slug."""
    if post.get('canonicalURL'):
        return post['canonicalURL']
    slug = filename.replace('.md', '')
    return f"{SITE_BASE}/posts/{slug}/"

def has_related_section(body):
    """Check if post already has a generated Related Reading section with links."""
    # Match our exact format: ## Related Reading followed by markdown links
    pattern = r'##\s*Related Reading\s*\n(?:\s*-\s*\[.*?\]\(https?://.*?\)\s*\n?)+'
    return bool(re.search(pattern, body, re.IGNORECASE))

def build_related_section(related_posts):
    """Build markdown for Related Reading section."""
    lines = [
        "",
        "---",
        "",
        "## Related Reading",
        "",
    ]
    for rp in related_posts:
        lines.append(f"- [{rp['title']}]({rp['url']})")
    lines.append("")
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='Preview only, no writes')
    parser.add_argument('--apply', action='store_true', help='Write changes to files')
    parser.add_argument('--force', action='store_true', help='Force process even if related section exists')
    parser.add_argument('--top-n', type=int, default=5, help='Number of related posts per article')
    args = parser.parse_args()

    # Scan all posts
    posts = []
    for md_file in sorted(CONTENT_DIR.glob('*.md')):
        content = md_file.read_text(encoding='utf-8')
        fm, body = parse_front_matter(content, md_file.name)
        if fm.get('draft', False):
            continue
        if not args.force and has_related_section(body):
            print(f"[SKIP] Already has related section: {md_file.name}")
            continue
        fm['keywords'] = extract_keywords(body)
        fm['_filename'] = md_file.name
        fm['_path'] = md_file
        fm['_body'] = body
        fm['_raw'] = content
        posts.append(fm)

    print(f"\nTotal posts to process: {len(posts)}")

    # Compute pairwise similarity and find top related
    results = []
    for i, post in enumerate(posts):
        scored = []
        for j, other in enumerate(posts):
            if i == j:
                continue
            sim = compute_similarity(post, other)
            if sim > 0:
                scored.append((sim, other))
        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:args.top_n]
        related = []
        for sim, rp in top:
            related.append({
                'title': rp['title'],
                'url': get_post_url(rp, rp['_filename']),
                'score': round(sim, 1),
            })
        results.append({
            'post': post,
            'related': related,
        })

    # Dry run report
    print("\n" + "="*60)
    print("DRY RUN PREVIEW")
    print("="*60)
    for r in results:
        print(f"\n📄 {r['post']['title'][:60]}")
        for rel in r['related']:
            print(f"   [{rel['score']:4.1f}] {rel['title'][:55]}")
            print(f"          -> {rel['url']}")
        if not r['related']:
            print("   ⚠️  No related posts found (low similarity)")

    if args.apply:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        applied = 0
        for r in results:
            if not r['related']:
                continue
            post = r['post']
            # Backup
            backup_path = BACKUP_DIR / f"{post['_filename'].replace('.md','')}_{timestamp}.bak"
            backup_path.write_text(post['_raw'], encoding='utf-8')
            # Append related section
            new_content = post['_raw'].rstrip() + "\n" + build_related_section(r['related'])
            post['_path'].write_text(new_content, encoding='utf-8')
            applied += 1
            print(f"[APPLIED] {post['_filename']} ({len(r['related'])} links)")
        print(f"\n✅ Applied internal links to {applied} posts. Backups in {BACKUP_DIR}")
    else:
        print(f"\n💡 Dry run complete. {len(results)} posts would be updated.")
        print("   Run with --apply to write changes.")

if __name__ == '__main__':
    main()
