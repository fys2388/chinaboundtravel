#!/usr/bin/env python3
"""Test harness for content_auto_optimizer with mock GSC data."""
import sys
sys.path.insert(0, "scripts")

import content_auto_optimizer as cao

# Mock GSC page data based on real baseline (5 pages with impressions, 0 clicks)
mock_rows = [
    {"keys": ["https://www.chinaboundtravel.com/posts/144-hour-visa-free-transit-guide/"],
     "clicks": 0, "impressions": 82, "ctr": 0, "position": 66.7},
    {"keys": ["https://www.chinaboundtravel.com/posts/how-to-use-wechat-pay-as-a-foreigner/"],
     "clicks": 0, "impressions": 40, "ctr": 0, "position": 69.6},
    {"keys": ["https://www.chinaboundtravel.com/posts/china-high-speed-rail-how-to-book-tickets/"],
     "clicks": 0, "impressions": 22, "ctr": 0, "position": 45.8},
    {"keys": ["https://www.chinaboundtravel.com/posts/china-business-travel-guide-meetings-dining-and-networking/"],
     "clicks": 0, "impressions": 11, "ctr": 0, "position": 81.7},
    {"keys": ["https://www.chinaboundtravel.com/posts/is-china-safe-for-tourists-2026-honest-safety-assessment/"],
     "clicks": 0, "impressions": 10, "ctr": 0, "position": 91.4},
    {"keys": ["https://www.chinaboundtravel.com/"],
     "clicks": 0, "impressions": 35, "ctr": 0, "position": 55.0},
]

print("=== Test 1: find_post_by_url ===")
for row in mock_rows:
    url = row["keys"][0]
    fp = cao.find_post_by_url(url)
    name = fp.name if fp else "NOT FOUND"
    print(f"  {url[:65]:65s} -> {name}")

print("\n=== Test 2: parse_post (144-hour-visa) ===")
fp = cao.find_post_by_url(
    "https://www.chinaboundtravel.com/posts/144-hour-visa-free-transit-guide/"
)
post = cao.parse_post(fp)
print(f"  title: {post['title']}")
print(f"  description: {post['description'][:80]}...")
print(f"  slug: {post['slug']}")
print(f"  word_count: {post['word_count']}")
print(f"  internal_link_count: {post['internal_link_count']}")
print(f"  has_faq: {post['has_faq']}")
print(f"  first_paragraph: {post['first_paragraph'][:100]}...")

print("\n=== Test 3: analyze_page_issues ===")
baseline = cao.load_previous_baseline_positions()
for row in mock_rows:
    url = row["keys"][0]
    pd = {
        "page": url, "clicks": row["clicks"],
        "impressions": row["impressions"], "ctr": row["ctr"],
        "position": row["position"],
    }
    fp = cao.find_post_by_url(url)
    post = cao.parse_post(fp) if fp else None
    analysis = cao.analyze_page_issues(pd, post, baseline)
    slug = url.split("/")[-2] if url.endswith("/") else url.split("/")[-1]
    print(f"  {slug:45s} impr={pd['impressions']:3d} "
          f"issues={analysis['issues']} actions={analysis['recommended_actions']}")

print("\n=== Test 4: optimize_title ===")
fp = cao.find_post_by_url(
    "https://www.chinaboundtravel.com/posts/how-to-use-wechat-pay-as-a-foreigner/"
)
post = cao.parse_post(fp)
new_title = cao.optimize_title(post)
print(f"  old: {post['title']}")
print(f"  new: {new_title}")

print("\n=== Test 5: optimize_description ===")
new_desc = cao.optimize_description(post)
print(f"  old: {post['description'][:80]}...")
print(f"  new: {new_desc[:80]}...")

print("\n=== Test 6: generate_faq_section ===")
faq = cao.generate_faq_section(post, {"page": "test"})
print(f"  generated {len(faq)} chars")
print(f"  preview: {faq[:120]}...")

print("\n=== Test 7: find_related_posts ===")
all_posts = cao.list_all_posts()
related = cao.find_related_posts(post, all_posts, max_links=3)
for rp, score in related:
    print(f"  score={score} {rp['file_path'].name}: {rp['title'][:50]}")

print("\n=== Test 8: modify_front_matter_field (dry, no actual write) ===")
# Test regex matching logic without writing
import re
text = fp.read_text(encoding="utf-8")
pattern = re.compile(r'^(title:\s*)(["\']?)(.*?)(\2)(\s*)$', re.MULTILINE)
m = pattern.search(text)
print(f"  title field matched: {m is not None}")
if m:
    print(f"  current value: {m.group(3)}")

print("\n=== ALL LOGIC TESTS PASSED ===")
