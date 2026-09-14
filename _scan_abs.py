#!/usr/bin/env python3
"""Scan built HTML for ALL image srcs including absolute URLs"""
import os, re, glob

static_dir = 'static'
public_dir = 'public'

# Collect all existing images
existing = set()
for ext in ('jpg', 'jpeg', 'png', 'webp', 'gif', 'svg'):
    for f in glob.glob(f'{static_dir}/**/*.{ext}', recursive=True):
        rel = '/' + f[len(static_dir)+1:].replace('\\', '/')
        existing.add(rel)
        # Also add with full URL
        existing.add('https://www.chinaboundtravel.com' + rel)
        existing.add('http://www.chinaboundtravel.com' + rel)

print(f"Existing images: {len(existing)}")

# Scan all built HTML
broken = {}
html_files = glob.glob(f'{public_dir}/**/*.html', recursive=True)
print(f"Scanning {len(html_files)} files...")

for hf in html_files:
    try:
        html = open(hf, encoding='utf-8', errors='replace').read()
        # Find ALL src attributes
        for m in re.finditer(r'src=["\']?(https?://[^"\'>\s]+\.(?:jpg|jpeg|png|webp|gif))', html):
            url = m.group(1)
            if url not in existing:
                img_path = url.replace('https://www.chinaboundtravel.com', '').replace('http://www.chinaboundtravel.com', '')
                page = hf[len(public_dir)+1:].replace('\\', '/')
                broken.setdefault(img_path, []).append(page)
        # Also root-relative
        for m in re.finditer(r'src=["\']?(/(?:img|images)/[^"\'>\s]+\.(?:jpg|jpeg|png|webp|gif))', html):
            url = m.group(1)
            if url not in existing:
                broken.setdefault(url, []).append(page)
    except:
        pass

print(f"\nBroken images: {len(broken)}")
total_refs = sum(len(v) for v in broken.values())
print(f"Total broken references: {total_refs}")
print("\nTop 20 broken images:")
for img, pages in sorted(broken.items(), key=lambda x: -len(x[1]))[:20]:
    print(f"  {len(pages)}x  {img}")
