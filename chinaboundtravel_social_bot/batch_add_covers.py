#!/usr/bin/env python3
"""为现有文章批量生成封面图并更新 cover 字段"""

import os
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
POSTS_DIR = BASE_DIR / "content" / "posts"
SITE_NAME = "chinaboundtravel.com"

# ========== 分类映射 ==========
CATEGORY_MAP = [
    ("chengdu", ["chengdu", "panda", "sichuan", "hotpot"]),
    ("beijing", ["beijing", "great wall", "forbidden city", "tiananmen"]),
    ("greatwall", ["great wall", "mutianyu", "badaling"]),
    ("zhangjiajie", ["zhangjiajie", "avatar mountain", "hunan"]),
    ("xian", ["xi'an", "xian", "terracotta", "warrior", "shaanxi"]),
    ("shanghai", ["shanghai", "bund", "pudong"]),
    ("hangzhou", ["hangzhou", "west lake", "xihu"]),
    ("guilin", ["guilin", "li river", "yangshuo"]),
    ("yunnan", ["yunnan", "lijiang", "shangri-la", "dali", "kunming"]),
    ("sichuan", ["sichuan", "leshan", "mount emei", "jiuzhaigou"]),
]

COLOR_SCHEMES = [
    ((196, 30, 58), (255, 245, 230)),
    ((34, 87, 122), (255, 255, 255)),
    ((88, 53, 39), (255, 235, 205)),
    ((34, 139, 34), (255, 255, 220)),
    ((255, 140, 0), (255, 255, 245)),
]


def classify_category(title: str) -> str:
    """根据标题判断分类"""
    title_lower = title.lower()
    for cat, keywords in CATEGORY_MAP:
        for kw in keywords:
            if kw in title_lower:
                return cat
    return "general"


def wrap_text(text, max_chars):
    """自动换行"""
    words = text.split()
    lines = []
    current = ""
    for w in words:
        if len(current) + len(w) + 1 <= max_chars:
            current = current + " " + w if current else w
        else:
            lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines


def generate_cover(title: str, slug: str) -> str:
    """生成封面图并返回 URL"""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print(f"  ⚠️ PIL 未安装，跳过封面生成")
        return None

    category = classify_category(title)
    cover_dir = BASE_DIR / "static" / "img" / "china-dest" / category
    cover_dir.mkdir(parents=True, exist_ok=True)

    color_idx = hash(title) % len(COLOR_SCHEMES)
    bg_color, text_color = COLOR_SCHEMES[color_idx]

    img = Image.new('RGB', (1080, 1350), color=bg_color)
    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype('DejaVuSans-Bold.ttf', 72)
        font_sub = ImageFont.truetype('DejaVuSans.ttf', 36)
    except:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    title_lines = wrap_text(title, 18)
    line_height = 90
    total_height = len(title_lines) * line_height
    start_y = (1350 - total_height) // 2 - 50

    for i, line in enumerate(title_lines):
        bbox = draw.textbbox((0, 0), line, font=font_title)
        text_width = bbox[2] - bbox[0]
        x = (1080 - text_width) // 2
        y = start_y + i * line_height
        draw.text((x, y), line, fill=text_color, font=font_title)

    sub = "chinaboundtravel.com"
    bbox = draw.textbbox((0, 0), sub, font=font_sub)
    sx = (1080 - (bbox[2] - bbox[0])) // 2
    sy = start_y + total_height + 60
    draw.text((sx, sy), sub, fill=text_color, font=font_sub)

    draw.rectangle([150, start_y - 40, 930, start_y - 36], fill=text_color)
    draw.rectangle([150, sy + 80, 930, sy + 84], fill=text_color)

    filename = f"{slug}.jpg"
    img.save(cover_dir / filename, 'JPEG', quality=90)

    return f"https://{SITE_NAME}/img/china-dest/{category}/{filename}"


def get_article_info(md_path: Path) -> dict:
    """解析文章信息"""
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 提取 frontmatter
    fm_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    frontmatter = {}
    if fm_match:
        for line in fm_match.group(1).split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and value:
                    frontmatter[key] = value

    title = frontmatter.get("title", md_path.stem.replace('-', ' ').title())
    slug = frontmatter.get("slug", md_path.stem)
    has_cover = 'cover' in frontmatter and frontmatter['cover']

    return {
        "title": title,
        "slug": slug,
        "has_cover": has_cover,
        "current_cover": frontmatter.get("cover", ""),
        "content": content,
        "fm_match": fm_match
    }


def update_cover_in_md(md_path: Path, cover_url: str):
    """更新文章的 cover 字段"""
    info = get_article_info(md_path)
    content = info["content"]
    fm_match = info["fm_match"]

    if fm_match:
        existing_fm = fm_match.group(1)
        if 'cover:' in existing_fm:
            new_fm = re.sub(r'^\s*cover\s*:.*$', f'cover: "{cover_url}"', existing_fm, flags=re.MULTILINE)
        else:
            lines = existing_fm.split("\n")
            new_lines = []
            for line in lines:
                new_lines.append(line)
                if line.startswith('title:'):
                    new_lines.append(f'cover: "{cover_url}"')
            new_fm = "\n".join(new_lines)
        new_content = content.replace(fm_match.group(0), f"---\n{new_fm}\n---", 1)
    else:
        new_content = f'---\ntitle: "{info["title"]}"\ncover: "{cover_url}"\n---\n\n' + content

    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(new_content)


def main():
    print("=== 批量为现有文章生成封面图 ===")
    print(f"扫描目录: {POSTS_DIR}")

    md_files = sorted(POSTS_DIR.glob("*.md"))
    print(f"发现 {len(md_files)} 篇文章\n")

    results = {
        "generated": 0,
        "updated": 0,
        "skipped": 0,
        "failed": 0,
        "details": []
    }

    for md_file in md_files:
        print(f"\n--- {md_file.name} ---")
        info = get_article_info(md_file)
        print(f"标题: {info['title']}")
        print(f"Slug: {info['slug']}")

        if info['has_cover']:
            print(f"现有封面: {info['current_cover']}")
            if 'chinaboundtravel.com/img/china-dest/' in info['current_cover']:
                print("  [OK] 已使用本站封面图，跳过")
                results["skipped"] += 1
                continue
            else:
                print("  [WARN] 外链封面，需要替换")

        # 生成封面
        cover_url = generate_cover(info['title'], info['slug'])
        if cover_url:
            print(f"生成封面: {cover_url}")
            update_cover_in_md(md_file, cover_url)
            print("  [OK] 更新成功")
            results["generated"] += 1
            results["updated"] += 1
            results["details"].append({
                "file": md_file.name,
                "title": info['title'],
                "cover": cover_url
            })
        else:
            print("  [FAIL] 封面生成失败")
            results["failed"] += 1

    print("\n=== 批量处理完成 ===")
    print(f"生成封面: {results['generated']}")
    print(f"更新文章: {results['updated']}")
    print(f"跳过(已有封面): {results['skipped']}")
    print(f"失败: {results['failed']}")

    if results['details']:
        print("\n--- 更新详情 ---")
        for detail in results['details']:
            print(f"- {detail['file']}: {detail['cover']}")


if __name__ == "__main__":
    main()
