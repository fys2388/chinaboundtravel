import os
import json
import requests
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# P1-OPS-04: 社媒文案清理/校验公共工具（shortcode 剥离、描述去标题前缀、URL 保证、配图过滤）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from social_text_utils import (  # noqa: E402
    clean_social_text,
    ensure_article_url,
    first_meaningful_desc,
    image_rejection_reason,
    is_acceptable_social_image,
    validate_social_copy,
)

# ========== 配置 ==========
BASE_DIR = Path(__file__).parent.parent
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

# P1-GROWTH-28A: Worker 地址从 .env 读取，禁止硬编码旧地址。
LEGACY_WORKER_URL = "https://buffer-worker.chinaboundtravel.com"
BUFFER_WORKER_URL = (os.getenv("BUFFER_WORKER_URL") or LEGACY_WORKER_URL).strip().rstrip("/")  # 主账户 IG/X/FB
NEW_BUFFER_WORKER_URL = (os.getenv("NEW_BUFFER_WORKER_URL") or "").strip().rstrip("/")  # 长尾账户 Pinterest

# 双账户路由（P1-GROWTH-28A）：
#   ig_main / ig_story / x_promo -> BUFFER_WORKER_URL（主账户）
#   pin_secondary -> NEW_BUFFER_WORKER_URL（Pinterest 长尾流量账户）
MAIN_PLATFORMS = ["x", "facebook", "instagram"]
PINTEREST_PLATFORMS = ["pinterest"]
VARIANT_PLATFORMS = {
    "ig_main": ["instagram"],
    "ig_story": ["instagram"],
    "x_promo": ["x"],
    "pin_secondary": ["pinterest"],
}

try:
    from zoneinfo import ZoneInfo
    EST_TZ = ZoneInfo("America/New_York")
except Exception:
    EST_TZ = timezone(timedelta(hours=-5))

# 黄金时段：20:00-22:00 EST（排期时间统一美东时间）
GOLDEN_HOUR_START_EST, GOLDEN_HOUR_END_EST = 20, 22

def now_est():
    """当前时间统一转换为美东时间（发布/排期口径）。"""
    return datetime.now(EST_TZ)

def is_golden_hour_est(dt=None):
    dt = dt or now_est()
    return GOLDEN_HOUR_START_EST <= dt.hour < GOLDEN_HOUR_END_EST

def worker_url_for_variant(variant):
    """双账户路由：pin_secondary -> NEW_BUFFER_WORKER_URL；其余 -> BUFFER_WORKER_URL。"""
    platforms = VARIANT_PLATFORMS.get(variant, MAIN_PLATFORMS)
    if "pinterest" in platforms:
        if not NEW_BUFFER_WORKER_URL:
            print("[WARN] NEW_BUFFER_WORKER_URL 未配置，Pinterest 请求回退到 BUFFER_WORKER_URL（需配置 .env）")
            return BUFFER_WORKER_URL + "/publish", platforms, True
        return NEW_BUFFER_WORKER_URL + "/publish", platforms, False
    return BUFFER_WORKER_URL + "/publish", platforms, False
SITE_DOMAIN = "chinaboundtravel.com"
DAILY_SOCIAL_LIMIT = 5  # 每日社媒发布上限（与生成器 manifest 统一为 5，消除 2/5 不一致）
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
    ("food", ["food", "gastronomic", "cuisine", "eat", "dish", "restaurant", "street food", "dining", "cook"]),
    ("accommodation", ["accommodation", "hotel", "hostel", "stay", "sleep", "lodging", "airbnb"]),
    ("safety", ["safety", "safe", "scam", "crime", "security", "danger"]),
    ("transport", ["transport", "train", "flight", "bus", "metro", "subway", "high-speed", "airport"]),
    ("visa", ["visa", "passport", "entry", "transit"]),
    ("payment", ["alipay", "wechat pay", "payment", "money", "currency", "exchange"]),
    ("culture", ["culture", "etiquette", "custom", "tradition", "festival", "temple"]),
    ("budget", ["budget", "cost", "price", "cheap", "expensive", "money saving"]),
]

# 分类 -> 社媒 hashtag 组（根据文章分类动态选择）
CATEGORY_HASHTAGS = {
    "chengdu": "#Chengdu #SichuanFood #PandaLovers #ChinaTravel",
    "beijing": "#Beijing #GreatWall #ForbiddenCity #ChinaTravel",
    "greatwall": "#GreatWallOfChina #ChinaHistory #TravelChina #VisitChina",
    "zhangjiajie": "#Zhangjiajie #AvatarMountains #HunanTravel #ChinaTravel",
    "xian": "#Xian #TerracottaWarriors #AncientChina #ChinaTravel",
    "shanghai": "#Shanghai #TheBund #ModernChina #ChinaTravel",
    "hangzhou": "#Hangzhou #WestLake #ChineseGarden #ChinaTravel",
    "guilin": "#Guilin #LiRiver #KarstLandscape #ChinaTravel",
    "yunnan": "#Yunnan #Lijiang #RiceTerraces #ChinaTravel",
    "sichuan": "#Sichuan #Hotpot #MountainTravel #ChinaTravel",
    "food": "#ChineseFood #FoodieTravel #StreetFoodChina #ChinaTravel",
    "accommodation": "#ChinaHotels #TravelTips #ChinaTravel #BudgetTravel",
    "safety": "#TravelSafety #ChinaTravel #SafeTravel #TravelTips",
    "transport": "#ChinaTrains #TravelChina #HighSpeedRail #ChinaTravel",
    "visa": "#ChinaVisa #VisaFree #TravelTips #ChinaTravel",
    "payment": "#Alipay #WeChatPay #ChinaTech #ChinaTravel",
    "culture": "#ChineseCulture #CulturalTravel #ChinaTravel #DiscoverChina",
    "budget": "#BudgetTravel #ChinaOnABudget #TravelTips #ChinaTravel",
}

DEFAULT_HASHTAGS = "#ChinaTravel #TravelChina #VisitChina #ChinaLife"

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
    生成真实风景照片封面图（不再使用纯文字海报）。
    优先使用 Pollinations.ai 生成 AI 风景照片，兜底使用 Unsplash 高质量图片。
    下载后保存到 static/img/china-dest/<category>/ 并返回完整 URL。
    """
    # 创建目录
    cover_dir = BASE_DIR / "static" / "img" / "china-dest" / category
    cover_dir.mkdir(parents=True, exist_ok=True)

    # 构建场景描述
    title_lower = title.lower()
    scene_keywords = {
        "chengdu": "Chengdu China skyline pandas bamboo architecture",
        "beijing": "Beijing China Forbidden City Great Wall architecture",
        "greatwall": "Great Wall of China mountains scenic landscape",
        "zhangjiajie": "Zhangjiajie Avatar mountains sandstone pillars landscape",
        "xian": "Xian China Terracotta Army ancient city walls",
        "shanghai": "Shanghai Bund skyline Oriental Pearl night architecture",
        "hangzhou": "Hangzhou West Lake pagoda garden traditional",
        "guilin": "Guilin karst mountains Li River landscape",
        "yunnan": "Yunnan rice terraces Lijiang ancient town scenery",
        "sichuan": "Sichuan mountains panda bamboo forest nature",
        "food": "Chinese food street market dim sum hotpot colorful dishes",
        "accommodation": "China hotel room interior traditional courtyard boutique",
        "safety": "China city street safe architecture night landscape",
        "transport": "China high-speed train station modern bullet train",
        "visa": "China passport visa stamp travel document airport",
        "payment": "China mobile payment phone scanning QR code alipay wechat",
        "culture": "Chinese temple traditional architecture red lanterns festival",
        "budget": "China budget travel street market affordable goods",
    }
    scene_desc = scene_keywords.get(category, "China travel landscape scenic beautiful")

    # 尝试 Pollinations.ai（免费 AI 图片生成）
    # 发布规则（2026-08-28）：配图必须是真实写实的实景照片 —— 禁止人物/头像、禁止抽象图
    prompt = f"Ultra-detailed professional travel photography of {scene_desc}, cinematic wide-angle composition, golden hour or blue hour lighting, dramatic shadows, vibrant natural colors, photorealistic, 8k resolution, sharp focus, depth of field, award-winning travel magazine quality, no text, no watermark, realistic photography only, no abstract, no illustration, no cartoon, no vector, no 3d render, no digital art, no minimalism, ZERO people, ZERO persons, ZERO faces, ZERO portraits, ZERO human figures, ZERO humans, ZERO crowd, ZERO tourists, ZERO man woman child, empty scene, pure architecture landscape food objects only, absolutely no human beings whatsoever"
    seed = abs(hash(f"{slug}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}")) % 1000000
    image_url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}?width=1792&height=1024&nologo=true&seed={seed}&model=flux&negative=person,people,face,portrait,human,figure,crowd,man,woman,child,close-up%20face,selfie,group%20photo,tourists,traveler,backpacker,human%20being"

    try:
        print(f"  [CoverGen] Downloading cover image via Pollinations.ai...")
        r = requests.get(image_url, timeout=90, stream=True)
        if r.status_code == 200 and "image" in r.headers.get("content-type", "").lower():
            filename = f"{slug}.jpg"
            image_path = cover_dir / filename
            with open(image_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            file_size_kb = image_path.stat().st_size / 1024
            print(f"  [CoverGen] Saved: {filename} ({file_size_kb:.0f} KB)")
            return f"https://www.{SITE_DOMAIN}/img/china-dest/{category}/{filename}"
        else:
            print(f"  [CoverGen] Pollinations failed: HTTP {r.status_code}")
    except Exception as e:
        print(f"  [CoverGen] Pollinations error: {e}")

    # 兜底：使用 Unsplash Source（高质量真实照片）
    print(f"  [CoverGen] Falling back to Unsplash...")
    unsplash_url = f"https://source.unsplash.com/1792x1024/?{requests.utils.quote(scene_desc.replace(',', ''))}"
    try:
        r = requests.get(unsplash_url, timeout=60, stream=True, allow_redirects=True)
        if r.status_code == 200 and "image" in r.headers.get("content-type", "").lower():
            filename = f"{slug}.jpg"
            image_path = cover_dir / filename
            with open(image_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            file_size_kb = image_path.stat().st_size / 1024
            print(f"  [CoverGen] Saved (Unsplash): {filename} ({file_size_kb:.0f} KB)")
            return f"https://www.{SITE_DOMAIN}/img/china-dest/{category}/{filename}"
        else:
            print(f"  [CoverGen] Unsplash failed: HTTP {r.status_code}")
    except Exception as e:
        print(f"  [CoverGen] Unsplash error: {e}")

    # 最后兜底：Picsum（随机高质量照片）
    picsum_url = f"https://picsum.photos/seed/{seed}/1792/1024"
    try:
        r = requests.get(picsum_url, timeout=30, stream=True)
        if r.status_code == 200:
            filename = f"{slug}.jpg"
            image_path = cover_dir / filename
            with open(image_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            file_size_kb = image_path.stat().st_size / 1024
            print(f"  [CoverGen] Saved (Picsum): {filename} ({file_size_kb:.0f} KB)")
            return f"https://www.{SITE_DOMAIN}/img/china-dest/{category}/{filename}"
    except Exception as e:
        print(f"  [CoverGen] Picsum error: {e}")

    # 所有方法失败，返回空
    print(f"  [CoverGen] FAILED: all image sources failed")
    return ""


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
    body_text = clean_social_text(body_text)

    slug = frontmatter.get("slug", md_path.stem)
    canonical_url = frontmatter.get("canonicalURL", "")
    
    if canonical_url:
        if not canonical_url.startswith("http"):
            canonical_url = f"https://{canonical_url}"
        url = canonical_url
    else:
        url = f"https://www.{SITE_DOMAIN}/posts/{slug}/"
    url = ensure_article_url(url, slug, SITE_DOMAIN)
    
    # 优先使用 frontmatter 的 description/summary，其次截取正文
    # P1-OPS-04: 一律剥离 shortcode/HTML 并去掉标题前缀，避免泄漏与视觉重复
    fm_desc = frontmatter.get("description", "") or frontmatter.get("summary", "")
    title = frontmatter.get("title", md_path.stem.replace('-', ' ').title())
    if fm_desc and len(fm_desc) > 30:
        description = first_meaningful_desc(fm_desc, title, 300)
    else:
        description = first_meaningful_desc(body_text, title, 300)

    return {
        "title": frontmatter.get("title", md_path.stem.replace('-', ' ').title()),
        "description": description,
        "summary": frontmatter.get("summary", ""),
        "slug": slug,
        "url": url,
        "content_id": frontmatter.get("content_id", ""),
        "content": content,
        "date": frontmatter.get("date", ""),
        "geo": frontmatter.get("geo", ""),
        "tags": frontmatter.get("tags", []),
        "categories": frontmatter.get("categories", []),
    }


def extract_images_from_article(md_path: Path) -> list:
    """提取文章中的所有图片，正文实景图优先排前面（社媒发帖用实景图效果更好）"""
    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        with open(md_path, 'r', encoding='latin-1') as f:
            content = f.read()
        content = content.encode('utf-8', errors='replace').decode('utf-8', errors='replace')

    body_images = []   # 正文实景图（优先用于社媒）
    cover_images = []  # 封面图（备用）

    fm_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if fm_match:
        fm_text = fm_match.group(1)
        # 支持两种 cover 格式:
        # 1. cover: "url" (单行)
        # 2. cover:\n  image: "url" (多行 map)
        cover_img_match = re.search(r'^\s*cover\s*:\s*\n\s*image\s*:\s*"?([^"\n]+)"?', fm_text, re.MULTILINE)
        if not cover_img_match:
            cover_img_match = re.search(r'^\s*cover\s*:\s*"?([^"\n]+)"?', fm_text, re.MULTILINE)
        if cover_img_match:
            cover_url = cover_img_match.group(1).strip()
            if cover_url:
                if not cover_url.startswith('http'):
                    cover_url = f"https://{SITE_DOMAIN}{cover_url}"
                cover_images.append({"url": cover_url, "type": "cover"})

    body_content = content[fm_match.end():] if fm_match else content
    img_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
    for match in re.finditer(img_pattern, body_content):
        alt_text = match.group(1)
        img_url = match.group(2)
        if img_url and ('pollinations' in img_url or 'picsum' in img_url or SITE_DOMAIN in img_url):
            if not img_url.startswith('http'):
                img_url = f"https://{SITE_DOMAIN}{img_url}"
            # 发布规则：禁止人物/头像、禁止抽象图 —— 不合规的正文图直接丢弃
            reason = image_rejection_reason(alt=alt_text, url=img_url)
            if reason:
                print(f"  [IMG-SKIP] 正文图 {img_url[-50:]} 因含{reason}特征被过滤（{alt_text[:40]}）")
                continue
            body_images.append({"url": img_url, "type": "body", "alt": alt_text})

    # 正文实景图排前面，封面海报排后面（社媒优先用实景图）
    return body_images + cover_images


def build_story_text(category, title, url, hashtags):
    """按文章分类生成 IG 故事文案，不再硬编码单一话题（原 144-hour visa-free 与多数文章无关）"""
    story_hooks = {
        "food": ("What's the first meal you should try in China?", "Ask a local where they eat — that's where the real food is."),
        "visa": ("Confused about China's visa rules?", "Here's what first-time applicants should know before applying."),
        "transport": ("Getting around China can feel confusing. Where do you start?", "Trains beat flights on most routes. Here's the honest breakdown."),
        "accommodation": ("Picking where to stay in China?", "Location beats luxury every time. Here's why."),
        "safety": ("Worried about staying safe in China?", "Most 'scary' travel stories are avoidable with a few simple habits."),
        "budget": ("Think a China trip is expensive?", "You'd be surprised — here's what it actually costs."),
        "culture": ("China has some unwritten rules. Ready?", "A few etiquette basics will change your whole trip."),
        "payment": ("Cashless payments everywhere in China — help?", "Getting Alipay or WeChat Pay set up is easier than you think."),
        "travel": ("Planning your first China trip?", "Here's what our editorial team says actually matters."),
        "city": ("Beijing, Shanghai or Chengdu — which first?", "Each city has its own vibe. Here's how to pick."),
        "nature": ("Want to see China's wild side?", "These landscapes will change how you see the country."),
        "general": ("Your first China trip — what's the biggest thing to know?", "Here are the essentials every first-time traveler should plan for."),
    }
    question, answer = story_hooks.get(category, story_hooks["general"])
    return f"""Q: {question}

A: {answer}

Save this guide → {url}

{hashtags}"""

def generate_social_posts(article: dict, images: list, category: str = "general") -> list:
    """根据文章内容和配图生成多条不同的社媒帖子，适配 IG/Pinterest/X 不同风格"""
    title = article["title"]
    desc = article["description"]
    url = ensure_article_url(article.get("url", ""), article.get("slug", ""), SITE_DOMAIN)

    # 根据分类选择 hashtag
    hashtags = CATEGORY_HASHTAGS.get(category, DEFAULT_HASHTAGS)

    posts = []
    used_images = set()

    # 优先使用正文中的实景图片（type=body），cover 海报仅作 fallback
    body_images = [img for img in images if img.get("type") == "body"]
    cover_images = [img for img in images if img.get("type") == "cover"]

    # 如果没有正文图片，使用 cover 图
    available_images = body_images if body_images else cover_images
    if not available_images:
        return posts

    # P1-OPS-04: 描述去标题前缀、剥离 shortcode、句子边界截断（避免视觉重复与半句残文）
    clean_desc = first_meaningful_desc(desc, title, 180)
    desc_snippet = clean_desc

    # 帖子 1: IG 风格主帖 - 高情绪价值，故事性强，引导保存和点击
    first_img = available_images[0]
    used_images.add(first_img["url"])
    
    hook_emojis = {
        "food": "🍜", "travel": "✈️", "culture": "🏮", "nature": "🏔️", 
        "city": "🌆", "budget": "💰", "safety": "🛡️", "visa": "🗺️",
        "transport": "🚄", "accommodation": "🏨", "general": "✨"
    }
    
    emoji = hook_emojis.get(category, "✨")
    
    ig_text = f"""{emoji} {title}

{desc_snippet}

👇 Why you NEED to read this:
✅ Research-based China travel tips from our editorial team
✅ Hidden gems most tourists miss
✅ Step-by-step guides that actually work

👉 Full article: {url}

{hashtags}"""
    
    posts.append({
        "text": ig_text,
        "image": first_img["url"],
        "variant": "ig_main"
    })

    # 帖子 2: Pinterest 风格 - 信息密度高，实用价值强，适合搜索
    for img in available_images[1:]:
        if img["url"] not in used_images:
            used_images.add(img["url"])
            alt_text = img.get("alt", "")
            # P1-OPS-04: alt 若为图片生成提示词则弃用（曾泄漏为帖子正文），否则截取前 80 字符
            if alt_text and len(alt_text) > 10 and not re.search(
                    r"Ultra-detailed|no watermark|8k resolution|ZERO people|photorealistic|travel photography of|negative=",
                    alt_text, re.IGNORECASE):
                caption = alt_text[:80]
            else:
                caption = f"Ultimate Guide to {title[:60]}"
            
            pin_text = f"""{caption} | China Travel Guide

📌 What you'll learn:
• How to avoid tourist traps
• Practical tips for international travelers
• Budget-friendly tips for travelers

🔗 Full guide: {url}

#ChinaTravel #TravelTips #TravelGuide #Wanderlust #China"""
            
            posts.append({
                "text": pin_text,
                "image": img["url"],
                "variant": "pin_secondary"
            })
            break

    # 帖子 3: X 风格 - 短平快，话题性强，引发互动
    x_image = available_images[0] if len(available_images) == 1 else available_images[-1]
    # P1-OPS-04: desc 用句子边界截断 + 去标题前缀
    x_desc = first_meaningful_desc(desc, title, 140)
    x_text = f"""{emoji} Just dropped: {title}

Planning your first trip to China? Here are the practical things international travelers should know before they arrive.

{x_desc}

Full breakdown: {url}

#ChinaTravel #Travel"""
    
    posts.append({
        "text": x_text,
        "image": x_image["url"],
        "variant": "x_promo"
    })

    # 帖子 4: IG 故事风格 - 提问式，促进互动
    stories_image = available_images[0]
    stories_text = build_story_text(category, title, url, hashtags)
    
    posts.append({
        "text": stories_text,
        "image": stories_image["url"],
        "variant": "ig_story"
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


def publish_to_worker(article: dict, cover_url: str, custom_text: str = None, variant: str = "main") -> dict:
    """调用 Cloudflare Worker 发布到多平台"""
    # P1-GROWTH-28A: 双账户路由 - Pinterest 长尾账户走 NEW_BUFFER_WORKER_URL，其余走主账户
    worker_url, platforms, fell_back = worker_url_for_variant(variant)
    if fell_back:
        print("[ROUTE] Pinterest 目标回退到主 Worker（NEW_BUFFER_WORKER_URL 未配置）")
    else:
        print(f"[ROUTE] variant={variant} -> {worker_url}")
    payload = {
        "title": article["title"],
        "desc": custom_text or article["description"],
        "cover": cover_url,
        "url": article.get("url", ""),
        "custom_text": custom_text,
        "content_id": article.get("content_id", ""),
        "content_variant": variant,
        "source_workflow": "social_publisher"
    }
    payload["platforms"] = platforms

    try:
        resp = requests.post(worker_url, json=payload, timeout=90)
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


def check_worker_health(timeout: int = 10) -> list:
    """P1-GROWTH-28A: 探测两个 Worker 的 /health 接口，异常返回列表（供自动告警）。"""
    issues = []
    for label, base in (("BUFFER_WORKER_URL", BUFFER_WORKER_URL),
                        ("NEW_BUFFER_WORKER_URL", NEW_BUFFER_WORKER_URL)):
        if not base:
            issues.append(f"{label}: 未配置（.env 缺少该键）")
            continue
        try:
            r = requests.get(base + "/health", timeout=timeout)
            if r.status_code != 200:
                issues.append(f"{label}: HTTP {r.status_code} ({base}/health)")
            else:
                print(f"[HEALTH] {label} OK ({base}/health)")
        except Exception as e:
            issues.append(f"{label}: {e} ({base}/health)")
    return issues


def update_manifest():
    """更新发布时间"""
    manifest_path = BASE_DIR / "manifest.json"
    manifest = get_manifest()
    manifest["last_social_publish"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)


def check_daily_social_limit(daily_limit=DAILY_SOCIAL_LIMIT):
    """检查今日社媒发布是否已达上限，返回 (是否受限, 今日已发布数, 限额)"""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
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
        manifest["daily_social_publish_limit"] = daily_limit
        manifest_path = BASE_DIR / "manifest.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2)
        return False, 0, daily_limit
    
    # 以代码常量 daily_limit 为准，覆盖 manifest 历史残留值，避免限额漂移（曾出现"传 2 存 5"不一致）
    if manifest.get("daily_social_publish_limit", daily_limit) != daily_limit:
        manifest["daily_social_publish_limit"] = daily_limit
        manifest_path = BASE_DIR / "manifest.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2)
    current_count = manifest.get("daily_social_publish_count", 0)
    is_limited = current_count >= daily_limit
    
    return is_limited, current_count, daily_limit


def increment_daily_social_count():
    """社媒发布成功后，递增今日计数"""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    manifest_path = BASE_DIR / "manifest.json"
    manifest = get_manifest()
    
    # 新的一天或字段缺失，重置并初始化
    if manifest.get("daily_social_publish_date") != today:
        manifest["daily_social_publish_date"] = today
        manifest["daily_social_publish_count"] = 0
        if "daily_social_publish_limit" not in manifest:
            manifest["daily_social_publish_limit"] = DAILY_SOCIAL_LIMIT
    
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
# 已入队：达到每日发布上限，明日自动发布
        if r.get("queued"):
            summary_lines.append(f"⏳ {r['title']} ({r.get('variant', 'main')})")
            summary_lines.append("   已入队：达到每日上限，稿件已存入队列，明日自动发布")
            continue

        if r.get("skipped"):
            summary_lines.append(f"⏭️ {r['title']} ({r.get('variant', 'main')})")
            summary_lines.append("   跳过：重复内容（30 天内已发布，去重窗口生效）")
            continue

        status_icon = "✅" if r.get("worker_success") else "❌"
        variant = r.get("variant", "main")
        summary_lines.append(f"{status_icon} {r['title']} ({variant})")
        
        success_platforms = r.get("success_platforms", "")
        failed_platforms = r.get("failed_platforms", "")
        
        if success_platforms:
            summary_lines.append(f"   成功: {success_platforms}")
        elif not r.get("worker_success"):
            err = ""
            raw = r.get("raw_response") or {}
            if isinstance(raw, dict):
                err = raw.get("error", "") or raw.get("message", "") or ""
            detail = f"Worker调用失败: {err}" if err else "Worker调用失败"
            summary_lines.append(f"   失败: {failed_platforms if failed_platforms else detail}")

    content = "\n".join(summary_lines)
    payload = {
        "msg_type": "text",
        "content": {"text": f"## 📢 社媒发布结果\n\n{content}"}
    }

    try:
        # 使用显式 UTF-8 编码发送（requests 默认会用 \uXXXX 转义导致乱码）
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        requests.post(webhook, data=data, headers={"Content-Type": "application/json"}, timeout=15)
    except:
        pass


def run():
    """主流程：每次只处理一篇最新文章，生成多条不同内容的社媒帖子"""
    # P1-GROWTH-28A: 健康检查（探测两个 Worker 的 /health，异常自动告警）
    health_issues = check_worker_health()
    for issue in health_issues:
        print(f"[HEALTH][WARN] {issue}")
    print(f"[{datetime.now(timezone.utc)}] 开始扫描新文章... (EST {now_est().isoformat(timespec='seconds')}, 黄金时段 {GOLDEN_HOUR_START_EST}:00-{GOLDEN_HOUR_END_EST}:00 EST)")
    manifest = get_manifest()
    last_publish = manifest.get("last_social_publish", "2020-01-01")
    print(f"上次发布时间: {last_publish}")

    # CI 中所有文件 mtime 均为 checkout 时间，改用 frontmatter date 选最新文章，避免误选旧文
    md_files = sorted(POSTS_DIR.glob("*.md"), key=lambda p: get_article_info(p).get("date", ""), reverse=True)

    processed = set(get_manifest().get("processed_social_posts", []))
    latest_article = None
    for md_file in md_files:
        article = get_article_info(md_file)
        if article["slug"] in processed:
            continue
        if not article.get("date"):
            continue
        latest_article = article
        latest_article["md_path"] = str(md_file)
        break

    if not latest_article:
        print("No new articles found to publish")
        return

    print(f"\nFound latest article: {latest_article['title']}")

    # 【每日发布限额】检查今日是否已达社媒发布上限（每天最多5条）
    is_limited, current_count, daily_limit = check_daily_social_limit()
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
    social_posts = generate_social_posts(latest_article, images, category=category)
    print(f"  生成 {len(social_posts)} 条社媒帖子")

    results = []
    for post_idx, post in enumerate(social_posts):
        print(f"\n--- 发布帖子 [{post_idx+1}/{len(social_posts)}] ({post['variant']}) ---")
        
        is_limited_now, current_count_now, _ = check_daily_social_limit()
        if is_limited_now:
            print(f"Daily social limit reached ({current_count_now}/{daily_limit})")
            break

        # P1-OPS-04: 发布前 lint —— 有致命问题（shortcode/空链接/人设/标题重复等）一律拒绝发布
        problems = validate_social_copy(
            post["text"], title=latest_article.get("title", ""),
            url=ensure_article_url(latest_article.get("url", ""), latest_article.get("slug", ""), SITE_DOMAIN),
        )
        if problems:
            print(f"  [LINT][{post['variant']}] 文案未通过校验，跳过发布:")
            for p in problems:
                print(f"    - {p}")
            results.append({
                "title": latest_article["title"],
                "variant": post["variant"],
                "image": post["image"],
                "worker_success": False,
                "queued": False,
                "success_platforms": "",
                "failed_platforms": "lint_failed",
                "raw_response": {"error": "LINT_FAILED: " + "; ".join(problems)},
            })
            continue

        print(f"  配图: {post['image'][-40:]}")
        print(f"  内容: {post['text'][:100]}...")

        worker_resp = publish_to_worker(latest_article, post["image"], post["text"], post.get("variant", "main"))
        success_platforms = []
        failed_platforms = []
        queued = bool(worker_resp.get("queued"))
        # 内容去重命中 = 预期跳过（30 天内已发布过），不是失败（与 social_content_agent 口径一致）
        dup = ("Duplicate content" in str(worker_resp.get("error") or "")
               or "Duplicate content" in str(worker_resp.get("message") or ""))
        if worker_resp.get("success"):
            platforms = worker_resp.get("platforms", {})
            success_platforms = platforms.get("success", [])
            failed_platforms = platforms.get("failed", [])
            increment_daily_social_count()

        result = {
            "title": latest_article["title"],
            "variant": post["variant"],
            "image": post["image"],
            "worker_success": worker_resp.get("success", False) or queued or dup,
            "queued": queued,
            "skipped": dup,
            "success_platforms": ", ".join(success_platforms),
            "failed_platforms": ", ".join(failed_platforms) if failed_platforms else "",
            "raw_response": worker_resp
        }
        results.append(result)
        print(f"  发布: {'成功' if result['worker_success'] else '失败'}")
        print(f"  平台: success={result['success_platforms']} failed={result['failed_platforms']}")

    if results:
        manifest = get_manifest()
        processed_posts = manifest.setdefault("processed_social_posts", [])
        if latest_article["slug"] not in processed_posts:
            processed_posts.append(latest_article["slug"])
        # 保留完整已处理历史（不再滑动裁剪 30 条），
        # 防止旧文章掉出窗口后被反复选中，造成重复分发/去重误报。
        # 站点文章约 60-100 篇，完整列表开销可忽略。
        manifest["processed_social_posts"] = processed_posts
        manifest["last_social_publish"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        with open(BASE_DIR / "manifest.json", 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2)
        send_feishu_notification(results)

    print(f"\n[{datetime.now(timezone.utc)}] 完成，共发布 {len(results)} 条社媒帖子")


if __name__ == "__main__":
    run()
