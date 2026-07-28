#!/usr/bin/env python3
"""
批量修复文章中的 canonicalURL，统一为 www 版本
"""

import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CONTENT_DIR = BASE_DIR / "content" / "posts"

OLD_PATTERN = 'canonicalURL: "https://chinaboundtravel.com/'
NEW_PATTERN = 'canonicalURL: "https://www.chinaboundtravel.com/'

def fix_canonical_urls():
    count = 0
    files_fixed = []
    
    for md_file in CONTENT_DIR.rglob("*.md"):
        if ".archived" in str(md_file):
            continue
        
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(md_file, 'r', encoding='latin-1') as f:
                content = f.read()
        
        if OLD_PATTERN in content:
            new_content = content.replace(OLD_PATTERN, NEW_PATTERN)
            
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            count += 1
            files_fixed.append(str(md_file.relative_to(BASE_DIR)))
            print(f"  Fixed: {md_file.relative_to(BASE_DIR)}")
    
    print(f"\n✅ 共修复 {count} 篇文章")
    return files_fixed

if __name__ == "__main__":
    print("🔍 扫描文章中的 canonicalURL...")
    fix_canonical_urls()
