#!/usr/bin/env python3
"""Scan built HTML for broken image references"""
import os, re, glob

static_dir = 'static'
public_dir = 'public'

# Collect all image files that exist
existing_imgs = set()
for ext in ('jpg', 'jpeg', 'png', 'webp', 'gif', 'svg'):
    for f in glob.glob(f'{static_dir}/**/*.{ext}', recursive=True):
        existing_imgs.add('/' + f[len(static_dir)+1:].replace('\\', '/'))

print(f"Existing images in static/: {len(existing_imgs)}")

# Scan all built HTML
broken = []
html_files = glob.glob(f'{public_dir}/**/*.html', recursive=True)
print(f"Scanning {len(html_files)} HTML files...")

for hf in html_files:
    try:
        html = open(hf, encoding='utf-8', errors='replace').read()
        # Find all src attributes pointing to local images
        for m in re.finditer(r'src=(?:["\']?)(/img/[^"\'>\s]+\.(?:jpg|jpeg|png|webp|gif))', html):
            img_path = m.group(1)
            if img_path not in existing_imgs:
                rel_page = hf[len(public_dir)+1:].replace('\\', '/')
                broken.append((rel_page, img_path))
        # Also check srcset
        for m in re.finditer(r'srcset=["\']([^"\']+)["\']', html):
            for part in m.group(1).split(','):
                url = part.strip().split(' ')[0]
                if url.startswith('/img/') and url.endswith(('.jpg','.jpeg','.png','.webp')):
                    if url not in existing_imgs:
                        rel_page = hf[len(public_dir)+1:].replace('\\', '/')
                        broken.append((rel_page, url))
    except:
        pass

# Deduplicate
broken = list(set(broken))
print(f"\nBroken images found: {len(broken)}")
from collections import Counter
img_counts = Counter(b[1] for b in broken)
print(f"Unique missing images: {len(img_counts)}")
print("\nTop 15 missing images:")
for img, count in img_counts.most_common(15):
    print(f"  {count}x  {img}")
