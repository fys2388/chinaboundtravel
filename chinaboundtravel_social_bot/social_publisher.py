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
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 提取 frontmatter
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

    # 描述/摘要取正文前几句
    body_text = content[fm_match.end():] if fm_match else content
    body_text = re.sub(r'[#>*_`\[\]\(\)]', '', body_text)
    body_text = re.sub(r'\s+', ' ', body_text).strip()
    description = body_text[:300] if len(body_text) > 300 else body_text

    return {
        "title": frontmatter.get("title", md_path.stem.replace('-', ' ').title()),
        "description": description,
        "slug": md_path.stem,
        "url": f"https://{SITE_DOMAIN}/posts/{md_path.stem}/",
    }


def update_article_cover(md_path: Path, cover_url: str):
    """更新文章 frontmatter 的 cover 字段"""
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    fm_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if fm_match:
        existing_fm = fm_match.group(1)
        # 检查是否已有 cover
        if re.search(r'^\s*cover\s*:', existing_fm, re.MULTILINE):
            new_fm = re.sub(r'^\s*cover\s*:.*$',
                          f'cover: "{cover_url}"',
                          existing_fm, flags=re.MULTILINE)
        else:
            new_fm = existing_fm + f'\ncover: "{cover_url}"'

        content = content.replace(fm_match.group(0), f"---\n{new_fm}\n---", 1)
    else:
        # 没有 frontmatter，新建
        content = f'---\ntitle: "{md_path.stem.replace("-", " ").title()}"\ncover: "{cover_url}"\n---\n\n' + content

    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(content)


def publish_to_worker(article: dict, cover_url: str) -> dict:
    """调用 Cloudflare Worker 发布到多平台"""
    payload = {
        "title": article["title"],
        "desc": article["description"],
        "cover": cover_url,
        "url": article["url"]
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


def send_feishu_notification(results: list):
    """发送飞书通知"""
    webhook = os.getenv("FEISHU_WEBHOOK_URL")
    if not webhook:
        return

    summary_lines = []
    for r in results:
        status_icon = "✅" if r.get("worker_success") else "❌"
        summary_lines.append(f"{status_icon} {r['title']}")
        if "success_platforms" in r:
            summary_lines.append(f"   成功: {r['success_platforms']}")
        if "failed_platforms" in r and r["failed_platforms"]:
            summary_lines.append(f"   失败: {r['failed_platforms']}")

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
    """主流程"""
    print(f"[{datetime.now()}] 开始扫描新文章...")
    manifest = get_manifest()
    last_publish = manifest.get("last_social_publish", "2020-01-01")
    print(f"上次发布时间: {last_publish}")

    new_posts = []
    for md_file in sorted(POSTS_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime):
        mtime = datetime.fromtimestamp(md_file.stat().st_mtime)
        mtime_str = mtime.strftime("%Y-%m-%d %H:%M:%S")
        if mtime_str > last_publish:
            article = get_article_info(md_file)
            article["mtime"] = mtime_str
            article["md_path"] = str(md_file)
            new_posts.append(article)

    print(f"发现 {len(new_posts)} 篇待发布文章")

    results = []
    for article in new_posts:
        print(f"\n--- 处理: {article['title']} ---")

        # 1. 判断分类
        category = classify_category(article["title"])
        print(f"  分类: {category}")

        # 2. 生成封面图
        cover_url = generate_cover_image(article["title"], article["slug"], category)
        print(f"  封面: {cover_url}")

        # 3. 更新文章 frontmatter
        update_article_cover(Path(article["md_path"]), cover_url)
        print(f"  已更新 cover 字段")

        # 4. 调用 Worker 发布
        worker_resp = publish_to_worker(article, cover_url)
        success_platforms = []
        failed_platforms = []
        if worker_resp.get("success"):
            platforms = worker_resp.get("platforms", {})
            success_platforms = platforms.get("success", [])
            failed_platforms = platforms.get("failed", [])

        result = {
            "title": article["title"],
            "cover": cover_url,
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

    print(f"\n[{datetime.now()}] 完成，共处理 {len(results)} 篇文章")


if __name__ == "__main__":
    run()
