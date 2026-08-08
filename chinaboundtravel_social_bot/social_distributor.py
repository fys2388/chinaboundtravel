#!/usr/bin/env python3
"""ChinaBound Travel - Multi-Platform Social Media Distributor"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

# Import platform modules
from modules.distributors import FacebookDistributor, TwitterDistributor, LinkedInDistributor, TikTokDistributor, YouTubeDistributor

BASE_DIR = Path(__file__).parent
POSTS_DIR = Path(__file__).parent.parent / "content" / "posts"
MANIFEST_PATH = BASE_DIR / "distribution_manifest.json"
SITE_URL = "https://www.chinaboundtravel.com"  # canonical 域名带 www，与站点主域名保持一致

def smart_truncate(text, max_len=140):
    """智能截断：文本超长才截断加省略号，避免短文本被误加 ..."""
    text = re.sub(r'\s+', ' ', str(text or "")).strip()
    if len(text) <= max_len:
        return text
    return text[:max_len - 3].rstrip(' ,;:.') + "..."

PLATFORM_HASHTAGS = {
    "facebook": "#ChinaTravel #China #VisitChina #TravelTips #ChinaBoundTravel",
    "twitter": "#ChinaTravel #China #Travel #VisitChina",
    "linkedin": "#ChinaTravel #TravelIndustry #ChinaTourism #DigitalNomad",
    "tiktok": "#ChinaTravel #VisitChina #ChinaTrip #TravelChina",
    "youtube": "",
}

def get_latest_unpublished_posts(platform: str, limit: int = 1) -> list:
    """获取未发布到指定平台的博文列表"""
    if not MANIFEST_PATH.exists():
        manifest = {"published": {}}
    else:
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    
    platform_published = set(manifest.get("published", {}).get(platform, []))
    
    posts = []
    for md_file in sorted(POSTS_DIR.glob("*.md"), reverse=True):
        # 使用 frontmatter 的 slug 作为发布记录标识（文件名带日期前缀/旧命名不稳定）
        frontmatter = parse_frontmatter(md_file)
        if not frontmatter.get("title") or frontmatter.get("draft") == True:
            continue
        slug = frontmatter.get("slug") or md_file.stem
        if slug in platform_published:
            continue
        
        # Skip monthly update posts (not suitable for social media)
        if "monthly-update" in slug or "monthly_update" in slug:
            continue
        
        posts.append({
            "slug": slug,
            "file": md_file,
            "title": frontmatter.get("title", ""),
            "description": frontmatter.get("description", ""),
            "summary": frontmatter.get("summary", ""),
            "cover": frontmatter.get("cover", {}).get("image", "") if isinstance(frontmatter.get("cover"), dict) else frontmatter.get("cover", ""),
            "categories": frontmatter.get("categories", []),
            "tags": frontmatter.get("tags", []),
            "date": str(frontmatter.get("date", "")),
            "url": f"{SITE_URL}/posts/{slug}/"
        })
        
        if len(posts) >= limit:
            break
    
    return posts

def parse_frontmatter(md_path: Path) -> dict:
    """解析 markdown frontmatter"""
    try:
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()
    except:
        return {}
    
    if not content.startswith("---"):
        return {}
    
    fm_end = content.find("---", 3)
    if fm_end == -1:
        return {}
    
    fm_text = content[3:fm_end].strip()
    frontmatter = {}
    current_key = None
    current_list = None
    
    for line in fm_text.split("\n"):
        if line.startswith("  - "):
            if current_list is not None:
                current_list.append(line[4:].strip())
            continue
        
        if ": " in line:
            key, value = line.split(": ", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            
            if value.startswith("[") and value.endswith("]"):
                value = [v.strip().strip('"').strip("'") for v in value[1:-1].split(",")]
                frontmatter[key] = value
                current_list = value
            else:
                frontmatter[key] = value
                current_list = None
            current_key = key
        elif line.strip().startswith("- "):
            if current_key and current_list is None:
                current_list = []
                frontmatter[current_key] = current_list
            if current_list is not None:
                current_list.append(line.strip()[2:].strip('"').strip("'"))
    
    return frontmatter

def generate_social_text(post: dict, platform: str, content_type: str = "post") -> dict:
    """为不同平台生成文案"""
    title = post["title"]
    url = post["url"]
    description = post.get("description", "")
    summary = post.get("summary", description)
    hashtags = PLATFORM_HASHTAGS.get(platform, "")
    
    # Truncate description for platform limits
    max_len = {"facebook": 500, "twitter": 280, "linkedin": 700, "tiktok": 2200, "youtube": 5000}
    
    if platform == "twitter":
        # Twitter: compact with URL
        text = f"{title}\n\n{smart_truncate(summary, 100)}\n\n{url}\n{hashtags}"
        if len(text) > max_len["twitter"]:
            text = f"{smart_truncate(title, 60)}\n{url}\n{hashtags}"
    elif platform == "facebook":
        # Facebook: engaging with emoji
        text = f"✈️ {title}\n\n{summary}\n\nRead the full guide: {url}\n\n{hashtags}"
    elif platform == "linkedin":
        # LinkedIn: professional tone
        text = f"New on ChinaBound Travel! 🇨🇳\n\n{title}\n\n{summary}\n\nRead the full guide: {url}\n\n{hashtags}"
    elif platform == "tiktok":
        # TikTok: short and punchy
        text = f"{title}\n\n{smart_truncate(summary, 150)} Link in bio: {url}\n\n{hashtags}"
    else:
        text = f"{title}\n\n{summary}\n\n{url}"
    
    return {
        "text": text[:max_len.get(platform, 5000)],
        "title": title,
        "url": url,
        "link": url,
        "hashtags": hashtags,
        "cover_url": post.get("cover", ""),
    }

def mark_as_published(platform: str, slug: str):
    """标记文章已发布到指定平台（published[platform] = {slug: 时间戳} 字典，不再混入时间戳到数组）"""
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    else:
        manifest = {"published": {}}
    
    published_map = manifest.setdefault("published", {})
    published = published_map.get(platform)
    
    # 兼容旧格式：旧版是 [slug, 时间, slug, 时间...] 列表，迁移为 {slug: 时间戳} 字典
    if isinstance(published, list):
        old_list = published
        published = {}
        for i in range(0, len(old_list), 2):
            key = old_list[i]
            ts = old_list[i + 1] if i + 1 < len(old_list) else ""
            published[key] = ts if isinstance(ts, str) and len(ts) >= 10 else datetime.now().isoformat()
        published_map[platform] = published
    elif not isinstance(published, dict):
        published = {}
        published_map[platform] = published
    
    published[slug] = datetime.now().isoformat()
    
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


def distribute(args):
    """主分发函数"""
    platforms = args.platform.split(",") if args.platform else ["facebook", "twitter", "linkedin"]
    content_types = args.type.split(",") if args.type else ["post"]
    dry_run = args.dry_run
    limit = args.limit
    
    print(f"🚀 ChinaBound Social Distributor")
    print(f"   Platforms: {', '.join(platforms)}")
    print(f"   Content types: {', '.join(content_types)}")
    print(f"   Dry run: {dry_run}")
    print()
    
    results = {}
    
    for platform in platforms:
        print(f"\n📱 Processing {platform}...")
        posts = get_latest_unpublished_posts(platform, limit=limit)
        
        if not posts:
            print(f"   ✅ No unpublished posts for {platform}")
            results[platform] = {"status": "no_posts"}
            continue
        
        for post in posts:
            for content_type in content_types:
                social_content = generate_social_text(post, platform, content_type)
                
                print(f"   📝 Post: {post['title'][:60]}...")
                print(f"   📝 Type: {content_type}")
                print(f"   📝 Text: {social_content['text'][:80]}...")
                
                if dry_run:
                    print(f"   🔇 DRY RUN - skipping actual publish")
                    results[platform] = {"status": "dry_run", "post": post["slug"]}
                    continue
                
                try:
                    distributor = get_distributor(platform)
                    if not distributor:
                        print(f"   ⚠️ Distributor for {platform} not configured")
                        results[platform] = {"status": "not_configured"}
                        continue
                    
                    result = distributor.publish(social_content, content_type)
                    results[platform] = result
                    
                    if result.get("success"):
                        mark_as_published(platform, post["slug"])
                        print(f"   ✅ Published successfully!")
                    else:
                        print(f"   ❌ Failed: {result.get('error', 'Unknown error')}")
                        
                except Exception as e:
                    print(f"   ❌ Error: {e}")
                    results[platform] = {"status": "error", "error": str(e)}
    
    return results

def get_distributor(platform: str):
    """获取平台分发器实例"""
    distributors = {
        "facebook": FacebookDistributor,
        "twitter": TwitterDistributor,
        "linkedin": LinkedInDistributor,
        "tiktok": TikTokDistributor,
        "youtube": YouTubeDistributor,
    }
    cls = distributors.get(platform)
    if cls:
        return cls()
    return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ChinaBound Social Media Distributor")
    parser.add_argument("--platform", "-p", default="facebook,twitter,linkedin", help="Comma-separated platforms")
    parser.add_argument("--type", "-t", default="post", help="Content type: post, reel, video")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Dry run without publishing")
    parser.add_argument("--limit", "-l", type=int, default=1, help="Number of posts to distribute")
    parser.add_argument("--list", action="store_true", help="List unpublished posts")
    
    args = parser.parse_args()
    
    if args.list:
        for p in ["facebook", "twitter", "linkedin", "tiktok", "youtube"]:
            posts = get_latest_unpublished_posts(p, limit=5)
            if posts:
                print(f"\n📱 {p} ({len(posts)} unpublished):")
                for post in posts:
                    print(f"   - {post['title'][:60]}")
            else:
                print(f"\n📱 {p}: All up to date")
        sys.exit(0)
    
    distribute(args)
