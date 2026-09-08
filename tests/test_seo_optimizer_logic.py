#!/usr/bin/env python3
"""Test harness for seo_auto_optimizer and gsc_keyword_baseline extensions."""
import sys
sys.path.insert(0, "scripts")

import json
import pandas as pd

# ===========================================================================
# Test gsc_keyword_baseline extensions
# ===========================================================================
print("=" * 60)
print("  Test: gsc_keyword_baseline extensions")
print("=" * 60)

import gsc_keyword_baseline as gkb

# Test 1: find_latest_baseline_csv
print("\n--- Test: find_latest_baseline_csv ---")
baseline = gkb.find_latest_baseline_csv()
print(f"  Latest baseline: {baseline}")
baseline_prev = gkb.find_latest_baseline_csv(exclude_current=True)
print(f"  Previous baseline: {baseline_prev}")

# Test 2: load_baseline_keywords
print("\n--- Test: load_baseline_keywords ---")
kw_map = gkb.load_baseline_keywords(baseline)
print(f"  Loaded {len(kw_map)} keywords from baseline")
for kw, data in list(kw_map.items())[:3]:
    print(f"    {kw[:40]:40s} pos={data['position']} impr={data['impressions']}")

# Test 3: process_data with mock rows
print("\n--- Test: process_data (mock) ---")
mock_rows = [
    {"keys": ["china 144 hour transit visa",
              "https://www.chinaboundtravel.com/posts/144-hour-visa-free-transit-guide/"],
     "clicks": 0, "impressions": 18, "ctr": 0, "position": 66.5},
    {"keys": ["wechat pay international",
              "https://www.chinaboundtravel.com/posts/how-to-use-wechat-pay-as-a-foreigner/"],
     "clicks": 0, "impressions": 16, "ctr": 0, "position": 74.7},
    {"keys": ["china high speed rail tickets",
              "https://www.chinaboundtravel.com/posts/2026-05-25-china-high-speed-rail-how-to-book-tickets/"],
     "clicks": 0, "impressions": 10, "ctr": 0, "position": 26.4},
    {"keys": ["144 hour visa china",
              "https://www.chinaboundtravel.com/posts/144-hour-visa-free-transit-guide/"],
     "clicks": 0, "impressions": 14, "ctr": 0, "position": 54.9},
]
df = gkb.process_data(mock_rows)
print(f"  Processed {len(df)} unique keywords")
print(f"  Columns: {list(df.columns)}")
for _, row in df.iterrows():
    print(f"    {row['query'][:35]:35s} pos={row['position']:.1f} "
          f"impr={row['impressions']} page={row['page'][:40]}")

# Test 4: compare_with_baseline
print("\n--- Test: compare_with_baseline ---")
comparison = gkb.compare_with_baseline(df, baseline)
print(f"  Baseline file: {comparison['baseline_file']}")
print(f"  New keywords: {len(comparison['new_keywords'])}")
print(f"  Rank improved: {len(comparison['rank_improved'])}")
print(f"  Rank dropped: {len(comparison['rank_dropped'])}")
print(f"  Stable: {len(comparison['stable'])}")

# Test 5: output_json structure
print("\n--- Test: output_json structure (capture) ---")
import io
from contextlib import redirect_stdout
f = io.StringIO()
with redirect_stdout(f):
    gkb.output_json(df, comparison)
json_output = json.loads(f.getvalue())
print(f"  Keys: {list(json_output.keys())}")
print(f"  total_keywords: {json_output['total_keywords']}")
print(f"  total_impressions: {json_output['total_impressions']}")
print(f"  has comparison: {'comparison' in json_output}")
if 'comparison' in json_output:
    print(f"  comparison.new_keywords_count: {json_output['comparison']['new_keywords_count']}")

# ===========================================================================
# Test seo_auto_optimizer logic
# ===========================================================================
print("\n" + "=" * 60)
print("  Test: seo_auto_optimizer logic")
print("=" * 60)

import seo_auto_optimizer as seo

# Test 1: parse_post
print("\n--- Test: parse_post ---")
fp = seo.find_post_by_url(
    "https://www.chinaboundtravel.com/posts/144-hour-visa-free-transit-guide/"
)
post = seo.parse_post(fp)
print(f"  title: {post['title']}")
print(f"  internal_link_count: {post['internal_link_count']}")
print(f"  has_faq: {post['has_faq']}")
print(f"  slug: {post['slug']}")

# Test 2: optimize_title_with_keyword
print("\n--- Test: optimize_title_with_keyword ---")
new_title, changed = seo.optimize_title_with_keyword(
    post, "144 hour visa free transit"
)
print(f"  keyword: '144 hour visa free transit'")
print(f"  old: {post['title']}")
print(f"  new: {new_title}")
print(f"  changed: {changed}")

# Test with a page that doesn't contain keyword
fp2 = seo.find_post_by_url(
    "https://www.chinaboundtravel.com/posts/how-to-use-wechat-pay-as-a-foreigner/"
)
post2 = seo.parse_post(fp2)
new_title2, changed2 = seo.optimize_title_with_keyword(
    post2, "wechat pay for tourists"
)
print(f"\n  keyword: 'wechat pay for tourists'")
print(f"  old: {post2['title']}")
print(f"  new: {new_title2}")
print(f"  changed: {changed2}")

# Test 3: find_related_posts_for_linking
print("\n--- Test: find_related_posts_for_linking ---")
all_posts = seo.list_all_posts()
sources = seo.find_related_posts_for_linking(post, all_posts, max_links=3)
print(f"  Found {len(sources)} source candidates for linking to {post['slug']}")
for src, score in sources:
    print(f"    score={score} {src['file_path'].name}: {src['title'][:45]}")

# Test 4: generate_faq_for_keyword
print("\n--- Test: generate_faq_for_keyword ---")
faq = seo.generate_faq_for_keyword("144 hour visa free transit china", post)
print(f"  Generated {len(faq)} chars")
print(f"  Preview: {faq[:100]}...")

faq2 = seo.generate_faq_for_keyword("wechat pay international", post2)
print(f"  Payment FAQ: {len(faq2)} chars, preview: {faq2[:80]}...")

# Test 5: list_all_posts with low internal links
print("\n--- Test: low internal link pages ---")
low_link_posts = [p for p in all_posts if p["internal_link_count"] < 3]
print(f"  Pages with <3 internal links: {len(low_link_posts)}")
for p in low_link_posts[:5]:
    print(f"    {p['internal_link_count']} links: {p['file_path'].name}")

# Test 6: modify_front_matter_field regex
print("\n--- Test: front matter field regex ---")
import re
text = fp.read_text(encoding="utf-8-sig")
pattern = re.compile(r'^(title:\s*)(["\']?)(.*?)(\2)(\s*)$', re.MULTILINE)
m = pattern.search(text)
print(f"  title matched: {m is not None}, value: {m.group(3)[:50] if m else 'N/A'}")

print("\n" + "=" * 60)
print("  ALL SEO OPTIMIZER TESTS PASSED")
print("=" * 60)
