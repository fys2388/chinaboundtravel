#!/usr/bin/env python3
"""
fix_existing_posts.py - 修复现有文章中的图片占位符

将所有文章中的 [Image:xxx] 占位符转换为实际的图片URL
"""

import os
import sys
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from image_processor import process_markdown_images


def fix_all_posts(posts_dir: str = "content/posts") -> int:
    """
    修复所有文章中的图片占位符
    
    Args:
        posts_dir: 文章目录路径
    
    Returns:
        修复的文章数量
    """
    posts_path = Path(posts_dir)
    if not posts_path.exists():
        print(f"❌ 目录不存在: {posts_dir}")
        return 0
    
    # 查找所有md文件
    md_files = list(posts_path.glob("*.md"))
    if not md_files:
        print(f"❌ 未找到任何文章文件")
        return 0
    
    fixed_count = 0
    
    print(f"Found {len(md_files)} posts")
    print("=" * 60)
    
    for filepath in md_files:
        try:
            # 读取文件
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查是否有图片占位符
            if "[Image:" in content:
                # 处理图片占位符
                new_content = process_markdown_images(content)
                
                # 保存处理后的内容
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                print(f"OK: {filepath.name} - image placeholders replaced")
                fixed_count += 1
            else:
                print(f"SKIP: {filepath.name} - no image placeholders")
        
        except Exception as e:
            print(f"ERROR: {filepath.name} - failed: {str(e)}")
    
    print("=" * 60)
    print(f"Done! Fixed {fixed_count} posts")
    
    return fixed_count


def main():
    """主函数"""
    fix_all_posts()


if __name__ == "__main__":
    main()
