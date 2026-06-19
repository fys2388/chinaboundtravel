#!/usr/bin/env python3
"""
fix_all_images.py - 全面修复所有文章中的图片问题

修复的图片问题:
1. placeholder.jpg, example.com 等无效图片链接
2. 仅有alt文本没有实际URL的图片
3. Alt text: xxx 格式的旧格式图片
4. [Image:xxx] 占位符
"""

import os
import re
import sys
from pathlib import Path
from urllib.parse import quote

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from image_processor import process_markdown_images


# 无效图片域名/路径列表
INVALID_PATTERNS = [
    r'https?://example\.com[^\s\)]*',
    r'placeholder\.jpg',
    r'placeholder\.png',
    r'image\.jpg',
    r'image\.png',
    r'photo\.jpg',
    r'photo\.png',
    r'\.jpg\)',
    r'\.png\)',
    r'\.webp\)',
    r'local-file-[a-z0-9]+\.jpg',
]


def extract_alt_text(line: str) -> str:
    """从行中提取alt文本描述"""
    # 匹配 Alt text: xxx 格式
    match = re.search(r'Alt text:\s*(.+?)(?:\]|$)', line, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    # 匹配 ![描述](链接) 格式，提取描述
    match = re.search(r'!\[[^\]]*\]\([^\)]*\)', line)
    if match:
        img_match = re.search(r'!\[[^\]]*\]', match.group())
        if img_match:
            alt = img_match.group().replace('![', '').replace(']', '')
            return alt.strip()
    
    return ""


def is_valid_image_url(url: str) -> bool:
    """检查是否是有效的图片URL"""
    if not url or url.strip() == "":
        return False
    
    for pattern in INVALID_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            return False
    
    # 检查是否是pollinations.ai URL
    if 'pollinations.ai' in url:
        return True
    
    # 检查是否以常见图片扩展名结尾
    valid_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.svg']
    for ext in valid_extensions:
        if url.lower().endswith(ext):
            return True
    
    # 如果是完整的http/https URL，认为是有效的
    if url.startswith('http://') or url.startswith('https://'):
        return True
    
    return False


def generate_image_from_description(desc: str, seed: int = None) -> str:
    """从描述生成Pollinations.ai图片URL"""
    if not desc:
        desc = "Beautiful travel photography, China landscape"
    
    # 清理描述
    clean_desc = desc.strip()
    
    # 如果描述过长，截断
    if len(clean_desc) > 500:
        clean_desc = clean_desc[:500]
    
    # 生成seed
    if seed is None:
        seed = abs(hash(clean_desc)) % 100000
    
    # URL编码
    encoded = quote(clean_desc)
    
    return f"https://image.pollinations.ai/prompt/{encoded}?width=800&height=600&nologo=true&seed={seed}"


def fix_markdown_images(content: str, filename: str = "") -> tuple:
    """
    修复Markdown内容中的图片问题
    
    Returns:
        (修复后的内容, 修复的图片数量)
    """
    fixed_count = 0
    lines = content.split('\n')
    new_lines = []
    
    for line in lines:
        original_line = line
        
        # 跳过frontmatter (---之间的内容)
        if line.strip() == '---' or line.strip().startswith('title:') or line.strip().startswith('date:') or line.strip().startswith('cover:') or line.strip().startswith('slug:') or line.strip().startswith('description:') or line.strip().startswith('tags:') or line.strip().startswith('author:') or line.strip().startswith('lastmod:') or line.strip().startswith('ShowToc:') or line.strip().startswith('TocOpen:') or line.strip().startswith('weight:'):
            new_lines.append(line)
            continue
        
        # 跳过HTML标签行
        if line.strip().startswith('<') and '</' in line:
            new_lines.append(line)
            continue
        
        # 跳过已经是有效pollinations图片的行
        if 'pollinations.ai' in line and line.strip().startswith('!['):
            new_lines.append(line)
            continue
        
        # 处理 ![描述](链接) 格式
        img_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        match = re.search(img_pattern, line)
        
        if match:
            alt_text = match.group(1)
            url = match.group(2)
            
            # 检查URL是否有效
            if not is_valid_image_url(url):
                # 提取描述生成新图片
                if alt_text and alt_text.strip():
                    new_url = generate_image_from_description(alt_text, seed=abs(hash(filename + alt_text)) % 100000)
                    line = line.replace(url, new_url)
                    fixed_count += 1
                elif 'Alt text:' in line:
                    # 尝试提取Alt text描述
                    alt_match = re.search(r'Alt text:\s*(.+?)(?:\]|$|\n)', line, re.IGNORECASE)
                    if alt_match:
                        desc = alt_match.group(1).strip()
                        new_url = generate_image_from_description(desc, seed=abs(hash(filename + desc)) % 100000)
                        line = re.sub(img_pattern, f'![{desc}]({new_url})', line)
                        fixed_count += 1
        
        # 处理仅有Alt text没有URL的情况
        if 'Alt text:' in line and '![' not in line:
            alt_match = re.search(r'Alt text:\s*(.+?)(?:\)|$)', line, re.IGNORECASE)
            if alt_match:
                desc = alt_match.group(1).strip()
                if desc and not desc.startswith('http'):
                    new_url = generate_image_from_description(desc, seed=abs(hash(filename + desc)) % 100000)
                    line = f'![{desc}]({new_url})'
                    fixed_count += 1
        
        # 处理 *描述*(placeholder.jpg) 格式
        placeholder_pattern = r'\*\*(.+?)\*\*\s*\(([^)]+\.(?:jpg|png|webp))\)'
        match = re.search(placeholder_pattern, line)
        if match:
            desc = match.group(1).strip()
            url = match.group(2).strip()
            if not is_valid_image_url(url):
                new_url = generate_image_from_description(desc, seed=abs(hash(filename + desc)) % 100000)
                line = f'![{desc}]({new_url})'
                fixed_count += 1
        
        new_lines.append(line)
    
    return '\n'.join(new_lines), fixed_count


def fix_all_posts(posts_dir: str = "content/posts") -> dict:
    """
    修复所有文章中的图片问题
    
    Returns:
        修复统计信息
    """
    posts_path = Path(posts_dir)
    if not posts_path.exists():
        print(f"ERROR: Directory not found: {posts_dir}")
        return {"total": 0, "fixed": 0, "errors": 0}
    
    # 查找所有md文件
    md_files = list(posts_path.glob("*.md"))
    if not md_files:
        print("ERROR: No markdown files found")
        return {"total": 0, "fixed": 0, "errors": 0}
    
    total_files = 0
    total_fixed = 0
    errors = 0
    details = []
    
    print(f"Found {len(md_files)} posts to check")
    print("=" * 70)
    
    for filepath in sorted(md_files):
        try:
            # 读取文件
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            total_files += 1
            
            # 1. 先处理 [Image:xxx] 占位符
            if "[Image:" in content:
                content = process_markdown_images(content)
            
            # 2. 修复无效图片
            new_content, fixed = fix_markdown_images(content, filepath.name)
            
            # 检查是否有更改
            if new_content != original_content or fixed > 0:
                # 保存处理后的内容
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                total_fixed += fixed
                details.append(f"OK: {filepath.name} - fixed {fixed} images")
                print(f"OK: {filepath.name} - fixed {fixed} images")
            else:
                details.append(f"SKIP: {filepath.name} - no issues found")
                print(f"SKIP: {filepath.name} - no issues found")
        
        except Exception as e:
            errors += 1
            details.append(f"ERROR: {filepath.name} - {str(e)}")
            print(f"ERROR: {filepath.name} - {str(e)}")
    
    print("=" * 70)
    print(f"Done! Checked {total_files} posts, fixed {total_fixed} images, {errors} errors")
    
    return {
        "total": total_files,
        "fixed": total_fixed,
        "errors": errors,
        "details": details
    }


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fix all image issues in blog posts")
    parser.add_argument("--dir", default="content/posts", help="Posts directory path")
    args = parser.parse_args()
    
    result = fix_all_posts(args.dir)
    
    # 返回非零退出码表示有错误
    sys.exit(1 if result["errors"] > 0 else 0)


if __name__ == "__main__":
    main()
