import os
import json
import requests
import re
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ========== 配置 ==========
BASE_DIR = Path(__file__).parent.parent
WORKER_URL = "https://buffer-auto-poster.fys2388.workers.dev/publish"
SITE_DOMAIN = "chinaboundtravel.com"
COVER_BASE = "static/img/china-dest"
POSTS_DIR = BASE_DIR / "content/posts"

# 标题关键词 -> 分类目录
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

# 配色方案：中国风
COLOR_SCHEMES = [
    ((196, 30, 58), (255, 245, 230), "北京宫墙红"),
    ((34, 87, 122), (255, 255, 255), "桂林漓江青"),
    ((88, 53, 39), (255, 235, 205), "西安古槐褐"),
    ((34, 139, 34), (255, 255, 220), "黄山青松绿"),
    ((255, 140, 0), (255, 255, 245), "九寨枫叶橙"),
]


def classify_category(title: str) -> str:
    """根据文章标题关键词判断分类目录"""
    title_lower = title.lower()
    for cat, keywords in CATEGORY_MAP:
        for kw in keywords:
            if kw in title_lower:
                return cat
    return "general"


def generate_cover_image(title: str, slug: str, category: str) -> str:
    """
    生成 1080x1350 竖版海报封面图，保存在 static/img/china-dest/<category>/
    返回图片的完整 URL
    """
    # 创建目录
    cover_dir = BASE_DIR / COVER_BASE / category
    cover_dir.mkdir(parents=True, exist_ok=True)

    # 选择配色
    color_idx = hash(title) % len(COLOR_SCHEMES)
    bg_color, text_color, _ = COLOR_SCHEMES[color_idx]

    # 创建画布
    img = Image.new('RGB', (1080, 1350), color=bg_color)
    draw = ImageDraw.Draw(img)

    # 尝试加载字体，失败则用默认
    try:
        title_font = ImageFont.truetype('arial.ttf', 72)
        sub_font = ImageFont.truetype('arial.ttf', 40)
    except (OSError, IOError):
        try:
            title_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 72)
            sub_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 40)
        except (OSError, IOError):
            title_font = ImageFont.load_default()
            sub_font = ImageFont.load_default()

    # 标题自动换行
    title_lines = wrap_text(title, 18)

    # 垂直居中绘制标题
    line_height = 90
    total_height = len(title_lines) * line_height
    start_y = (1350 - total_height) // 2 - 50

    for i, line in enumerate(title_lines):
        bbox = draw.textbbox((0, 0), line, font=title_font)
        text_width = bbox[2] - bbox[0]
        x = (1080 - text_width) // 2
        y = start_y + i * line_height
        draw.text((x, y), line, fill=text_color, font=title_font)

    # 绘制副标题 / 网站信息
    sub_text = "chinaboundtravel.com"
    bbox = draw.textbbox((0, 0), sub_text, font=sub_font)
    sw = bbox[2] - bbox[0]
    sx = (1080 - sw) // 2
    sy = start_y + total_height + 60
    draw.text((sx, sy), sub_text, fill=text_color, font=sub_font, alpha=200)

    # 上下装饰线
    line_y_top = start_y - 40
    line_y_bottom = sy + 80
    draw.rectangle([150, line_y_top, 930, line_y_top + 4], fill=text_color)
    draw.rectangle([150, line_y_bottom, 930, line_y_bottom + 4], fill=text_color)

    # 保存为 jpg
    filename = f"{slug}.jpg"
    image_path = cover_dir / filename
    img.save(image_path, 'JPEG', quality=90, optimize=True)

    return f"https://{SITE_DOMAIN}/img/china-dest/{category}/{filename}"


def wrap_text(text, max_chars):
    """按字符数自动换行"""
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


def get_article_info(md_path: Path) -> dict:
    """解析 markdown 文章的 frontmatter"""
    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        with open(md_path, 'r', encoding='latin-1') as f:
            content = f.read()
        content = content.encode('utf-8', errors='replace').decode('utf-8', errors='replace')

    fm_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    frontmatter = {}
    if fm_match:
        fm_text = fm_match.group(1)
        for line in fm_text.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and value:
                    frontmatter[key] = value

    body_text = content[fm_match.end():] if fm_match else content
    body_text = re.sub(r'[#>*_`\[\]\(\)]', '', body_text)
    body_text = re.sub(r'\s+', ' ', body_text).strip()
    description = body_text[:300] if len(body_text) > 300 else body_text

    return {
        "title": frontmatter.get("title", md_path.stem.replace('-', ' ').title()),
        "description": description,
        "slug": md_path.stem,
        "url": f"https://{SITE_DOMAIN}/posts/{md_path.stem}/",
        "content": content,
    }


def extract_images_from_article(md_path: Path) -> list:
    """提取文章中的所有图片（封面图 + 正文插图）"""
    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        with open(md_path, 'r', encoding='latin-1') as f:
            content = f.read()
        content = content.encode('utf-8', errors='replace').decode('utf-8', errors='replace')

    images = []

    fm_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if fm_match:
        fm_text = fm_match.group(1)
        cover_match = re.search(r'^\s*cover\s*:', fm_text, re.MULTILINE)
        if cover_match:
            cover_value = re.search(r'cover:\s*"?([^"\n]+)"?', fm_text)
            if cover_value:
                cover_url = cover_value.group(1).strip()
                if cover_url:
                    if not cover_url.startswith('http'):
                        cover_url = f"https://{SITE_DOMAIN}{cover_url}"
                    images.append({"url": cover_url, "type": "cover"})

    body_content = content[fm_match.end():] if fm_match else content
    img_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
    for match in re.finditer(img_pattern, body_content):
        alt_text = match.group(1)
        img_url = match.group(2)
        if img_url and ('pollinations' in img_url or 'picsum' in img_url or SITE_DOMAIN in img_url):
            if not img_url.startswith('http'):
                img_url = f"https://{SITE_DOMAIN}{img_url}"
            images.append({"url": img_url, "type": "body", "alt": alt_text})

    return images


def generate_social_posts(article: dict, images: list) -> list:
    """根据文章内容和配图生成多条不同的社媒帖子"""
    title = article["title"]
    desc = article["description"]
    url = article["url"]

    posts = []
    used_images = set()

    if images:
        cover_img = images[0]
        used_images.add(cover_img["url"])
        
        posts.append({
            "text": f"New post: {title}\n\n{desc[:150]}...\n\nRead more: {url}\n\n#ChinaTravel #TravelGuide",
            "image": cover_img["url"],
            "variant": "main"
        })

    for i, img in enumerate(images[1:], 1):
        if len(posts) >= 2:
            break
        if img["url"] in used_images:
            continue
        
        used_images.add(img["url"])
        alt_text = img.get("alt", "Beautiful scenery")
        
        if i == 1:
            posts.append({
                "text": f"Highlight: {alt_text[:50]}...\n\nDiscover more about {title[:40]}...\n\nRead: {url}\n\n#ChinaTravel #TravelTips",
                "image": img["url"],
                "variant": "highlight"
            })
        else:
            posts.append({
                "text": f"Preview: {title[:60]}\n\nHere's a sneak peek - {alt_text[:30]}...\n\nRead the full guide: {url}\n\n#ChinaTravel #Wanderlust",
                "image": img["url"],
                "variant": "teaser"
            })

    if len(posts) < 2 and images:
        second_img = images[0] if len(images) == 1 else images[1]
        posts.append({
            "text": f"Travel inspiration: {desc[:120]}...\n\nFull article: {url}\n\n#ChinaTravel #TravelInspiration",
            "image": second_img["url"],
            "variant": "quote"
        })

    return posts[:2]


def update_article_cover(md_path: Path, cover_url: str):
    """更新文章 frontmatter 的 cover 字段"""
    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        # 尝试使用 latin-1 编码读取
        with open(md_path, 'r', encoding='latin-1') as f:
            content = f.read()
        content = content.encode('utf-8', errors='replace').decode('utf-8', errors='replace')

    fm_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    cover_block = f'cover:\n  image: "{cover_url}"'
    if fm_match:
        existing_fm = fm_match.group(1)
        # 检查是否已有 cover
        if re.search(r'^\s*cover\s*:', existing_fm, re.MULTILINE):
            # 替换已有的 cover（包括可能的多行 map 格式）
            new_fm = re.sub(r'^\s*cover\s*:(?:\n\s+\w+\s*:.*$)*',
                          cover_block,
                          existing_fm, flags=re.MULTILINE)
        else:
            new_fm = existing_fm + f'\n{cover_block}'

        content = content.replace(fm_match.group(0), f"---\n{new_fm}\n---", 1)
    else:
        # 没有 frontmatter，新建
        content = f'---\ntitle: "{md_path.stem.replace("-", " ").title()}"\n{cover_block}\n---\n\n' + content

    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(content)


def publish_to_worker(article: dict, cover_url: str, custom_text: str = None) -> dict:
    """调用 Cloudflare Worker 发布到多平台"""
    payload = {
        "title": article["title"],
        "desc": custom_text or article["description"],
        "cover": cover_url,
        "url": article["url"],
        "custom_text": custom_text
    }

    try:
        resp = requests.post(WORKER_URL, json=payload, timeout=90)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_manifest():
    """读取发布清单"""
    manifest_path = BASE_DIR / "manifest.json"
    if manifest_path.exists():
        with open(manifest_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"last_social_publish": "2020-01-01"}


def update_manifest():
    """更新发布时间"""
    manifest_path = BASE_DIR / "manifest.json"
    manifest = get_manifest()
    manifest["last_social_publish"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)


def check_daily_social_limit(daily_limit=5):
    """检查今日社媒发布是否已达上限，返回 (是否受限, 今日已发布数, 限额)"""
    today = datetime.now().strftime("%Y-%m-%d")
    manifest = get_manifest()
    
    # 初始化默认值（防止旧版本 manifest 缺失字段）
    if "daily_social_publish_date" not in manifest:
        manifest["daily_social_publish_date"] = today
        manifest["daily_social_publish_count"] = 0
        manifest["daily_social_publish_limit"] = daily_limit
        manifest_path = BASE_DIR / "manifest.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2)
        return False, 0, daily_limit
    
    # 新的一天，重置计数
    if manifest["daily_social_publish_date"] != today:
        manifest["daily_social_publish_date"] = today
        manifest["daily_social_publish_count"] = 0
        manifest_path = BASE_DIR / "manifest.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2)
        return False, 0, daily_limit
    
    # 确保 limit 字段存在
    if "daily_social_publish_limit" not in manifest:
        manifest["daily_social_publish_limit"] = daily_limit
    
    current_count = manifest.get("daily_social_publish_count", 0)
    limit = manifest.get("daily_social_publish_limit", daily_limit)
    is_limited = current_count >= limit
    
    return is_limited, current_count, limit


def increment_daily_social_count():
    """社媒发布成功后，递增今日计数"""
    today = datetime.now().strftime("%Y-%m-%d")
    manifest_path = BASE_DIR / "manifest.json"
    manifest = get_manifest()
    
    # 新的一天或字段缺失，重置并初始化
    if manifest.get("daily_social_publish_date") != today:
        manifest["daily_social_publish_date"] = today
        manifest["daily_social_publish_count"] = 0
        if "daily_social_publish_limit" not in manifest:
            manifest["daily_social_publish_limit"] = 5
    
    manifest["daily_social_publish_count"] = manifest.get("daily_social_publish_count", 0) + 1
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)
    return manifest["daily_social_publish_count"]


def send_feishu_notification(results: list):
    """发送飞书通知"""
    webhook = os.getenv("FEISHU_WEBHOOK_URL")
    if not webhook:
        return

    summary_lines = []
    for r in results:
        status_icon = "✅" if r.get("worker_success") else "❌"
        variant = r.get("variant", "main")
        summary_lines.append(f"{status_icon} {r['title']} ({variant})")
        
        success_platforms = r.get("success_platforms", "")
        failed_platforms = r.get("failed_platforms", "")
        
        if success_platforms:
            summary_lines.append(f"   成功: {success_platforms}")
        elif not r.get("worker_success"):
            summary_lines.append(f"   失败: {failed_platforms if failed_platforms else 'Worker调用失败'}")

    content = "\n".join(summary_lines)
    payload = {
        "msg_type": "text",
        "content": {"text": f"## 📢 社媒发布结果\n\n{content}"}
    }

    try:
        requests.post(webhook, json=payload, timeout=15)
    except:
        pass


def run():
    """主流程：每次只处理一篇最新文章，生成多条不同内容的社媒帖子"""
    print(f"[{datetime.now()}] 开始扫描新文章...")
    manifest = get_manifest()
    last_publish = manifest.get("last_social_publish", "2020-01-01")
    print(f"上次发布时间: {last_publish}")

    md_files = sorted(POSTS_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    
    latest_article = None
    for md_file in md_files:
        mtime = datetime.fromtimestamp(md_file.stat().st_mtime)
        mtime_str = mtime.strftime("%Y-%m-%d %H:%M:%S")
        if mtime_str > last_publish:
            article = get_article_info(md_file)
            article["mtime"] = mtime_str
            article["md_path"] = str(md_file)
            latest_article = article
            break

    if not latest_article:
        print("No new articles found to publish")
        return

    print(f"\nFound latest article: {latest_article['title']}")

    # 【每日发布限额】检查今日是否已达社媒发布上限（每天最多2条）
    is_limited, current_count, daily_limit = check_daily_social_limit(daily_limit=2)
    if is_limited:
        print(f"Daily social limit reached: {current_count}/{daily_limit}")
        print("Stopping for today to maintain social media exposure effectiveness.")
        return

    # 1. 判断分类
    category = classify_category(latest_article["title"])
    print(f"  分类: {category}")

    # 2. 生成封面图（如果还没有）
    cover_url = generate_cover_image(latest_article["title"], latest_article["slug"], category)
    print(f"  封面: {cover_url}")

    # 3. 更新文章 frontmatter
    update_article_cover(Path(latest_article["md_path"]), cover_url)
    print(f"  已更新 cover 字段")

    # 4. 提取文章中的所有图片（封面图 + 正文插图）
    images = extract_images_from_article(Path(latest_article["md_path"]))
    print(f"  提取到 {len(images)} 张图片: {', '.join([img['url'][-30:] for img in images])}")

    # 5. 生成多条不同内容的社媒帖子（当天最多2条，内容和配图不重复）
    social_posts = generate_social_posts(latest_article, images)
    print(f"  生成 {len(social_posts)} 条社媒帖子")

    results = []
    for post_idx, post in enumerate(social_posts):
        print(f"\n--- 发布帖子 [{post_idx+1}/{len(social_posts)}] ({post['variant']}) ---")
        
        is_limited_now, current_count_now, _ = check_daily_social_limit(daily_limit=2)
        if is_limited_now:
            print(f"Daily social limit reached ({current_count_now}/{daily_limit})")
            break

        print(f"  配图: {post['image'][-40:]}")
        print(f"  内容: {post['text'][:100]}...")

        worker_resp = publish_to_worker(latest_article, post["image"], post["text"])
        success_platforms = []
        failed_platforms = []
        if worker_resp.get("success"):
            platforms = worker_resp.get("platforms", {})
            success_platforms = platforms.get("success", [])
            failed_platforms = platforms.get("failed", [])
            increment_daily_social_count()

        result = {
            "title": latest_article["title"],
            "variant": post["variant"],
            "image": post["image"],
            "worker_success": worker_resp.get("success", False),
            "success_platforms": ", ".join(success_platforms),
            "failed_platforms": ", ".join(failed_platforms) if failed_platforms else "",
            "raw_response": worker_resp
        }
        results.append(result)
        print(f"  发布: {'成功' if result['worker_success'] else '失败'}")
        print(f"  平台: success={result['success_platforms']} failed={result['failed_platforms']}")

    if results:
        update_manifest()
        send_feishu_notification(results)

    print(f"\n[{datetime.now()}] 完成，共发布 {len(results)} 条社媒帖子")


if __name__ == "__main__":
    run()
