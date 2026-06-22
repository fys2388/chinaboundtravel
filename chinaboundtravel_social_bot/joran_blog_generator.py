import os
import re
import json
import random
import requests
import hashlib
import sys
import base64
from datetime import datetime, timedelta
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_exponential
from budget_controller import BudgetController
from doubao_ark_client import DoubaoArkClient
from google import genai
from google.genai import types

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
MANIFEST_PATH = BASE_DIR / "manifest.json"
DRAFT_DIR = BASE_DIR / "content" / "_draft"
POSTS_DIR = BASE_DIR / "content" / "posts"
DRAFTS_DIR = BASE_DIR / "content" / "content" / "drafts"
SITE_DOMAIN = "https://chinaboundtravel.com"

# ========== 封面图生成相关常量
COVER_BASE = BASE_DIR / "static" / "img" / "china-dest"
SITE_NAME = "chinaboundtravel.com"

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


def wrap_text(text, max_chars):
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


# ========== 多 API 图片生成系统（智能降级）
# 优先级: Google Gemini 官方 API > Google AI Studio > Pollinations.ai > Picsum.photos

PROXIES = {}

IMAGE_SAVE_DIR = BASE_DIR / "static" / "generated_images"
IMAGE_SAVE_DIR.mkdir(parents=True, exist_ok=True)

IMAGE_API_CONFIG = {
    "google_gemini": {
        "name": "Google Gemini (主力生产)",
        "priority": 0,
        "api_key": os.getenv("GEMINI_API_KEY", ""),
        "model": "gemini-2.5-flash-image",
        "proxy": os.getenv("GEMINI_PROXY", ""),
    },
    "google_aistudio": {
        "name": "Google AI Studio (备用)",
        "api_key": os.getenv("GOOGLE_AISTUDIO_API_KEY", ""),
        "url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key={api_key}",
        "priority": 1,
    },
    "pollinations": {
        "name": "Pollinations.ai (免费兜底)",
        "api_key": "",
        "url": "https://image.pollinations.ai/prompt/{prompt}?width={w}&height={h}&nologo=true&seed={seed}",
        "priority": 98,
    },
    "picsum": {
        "name": "Picsum.photos (最终占位兜底)",
        "api_key": "",
        "url": "https://picsum.photos/seed/{seed}/{w}/{h}",
        "priority": 99,
    },
}

LOCATION_KEYWORDS = [
    ("chengdu", "modern Chengdu city with pandas, Sichuan spicy hotpot"),
    ("beijing", "Beijing Forbidden City, Great Wall of China, imperial palace"),
    ("shanghai", "Shanghai Bund skyline, Oriental Pearl Tower at night"),
    ("xian", "Xian Terracotta Army, ancient Chinese city walls"),
    ("guilin", "Guilin karst mountains, Li River cruise landscape"),
    ("zhangjiajie", "Zhangjiajie Avatar mountains, quartz sandstone pillars"),
    ("hangzhou", "West Lake Hangzhou, traditional Chinese pagoda garden"),
    ("hong kong", "Hong Kong Victoria Harbour night skyline"),
    ("sichuan", "Sichuan mountains, giant panda in bamboo forest"),
    ("yunnan", "Yunnan rice terraces, Lijiang ancient town, Shangri-La"),
    ("great wall", "Great Wall of China winding through mountains"),
    ("visa", "travel visa document with Chinese flag background"),
    ("packing", "travel suitcase with China travel essentials checklist"),
    ("safety", "safe travel in China with Chinese cityscape background"),
    ("transportation", "China high-speed train, modern subway system"),
    ("accommodation", "Chinese boutique hotel room interior design"),
    ("food", "Chinese street food market, dumplings, noodles feast"),
    ("cultural", "traditional Chinese cultural scene, red lanterns"),
    ("budget", "budget travel planning with Chinese yuan banknotes"),
    ("itinerary", "China travel map with compass and passport"),
    ("best time", "spring cherry blossoms in Beijing or autumn West Lake"),
]

def build_prompt(title, slug):
    """根据标题构建图片生成 prompt"""
    title_lower = title.lower()
    scene_desc = "Beautiful China travel landscape photography, cinematic composition"
    for kw, desc in LOCATION_KEYWORDS:
        if kw in title_lower:
            scene_desc = desc
            break
    return f"Professional travel blog cover image, {scene_desc}, high-resolution travel photography, cinematic lighting, vibrant colors, 4k quality, photorealistic, beautiful scenery"

def try_google_aistudio(prompt, size="1024x1024"):
    """API #1: Google AI Studio (主力生产) - Gemini 2.5 Flash Image"""
    cfg = IMAGE_API_CONFIG["google_aistudio"]
    api_key = cfg["api_key"]
    if not api_key:
        print(f"  [{cfg['name']}] 未配置 API Key，跳过")
        return None
    try:
        url = cfg["url"].format(api_key=api_key)
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }]
        }
        r = requests.post(url, headers=headers, json=payload, timeout=60)
        result = r.json()
        if "error" in result:
            err = result["error"].get("message", str(result["error"]))
            print(f"  [{cfg['name']}] {err[:120]}")
            return None
        candidates = result.get("candidates", [])
        if candidates:
            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            if parts:
                part = parts[0]
                if "inlineData" in part:
                    base64_str = part["inlineData"].get("data", "")
                    if base64_str:
                        import base64
                        img_data = base64.b64decode(base64_str)
                        import io
                        from PIL import Image
                        img = Image.open(io.BytesIO(img_data))
                        img_format = img.format or "PNG"
                        import hashlib
                        img_hash = hashlib.md5(img_data).hexdigest()[:16]
                        img_dir = BASE_DIR / "static" / "generated"
                        img_dir.mkdir(parents=True, exist_ok=True)
                        img_path = img_dir / f"gai-{img_hash}.{img_format.lower()}"
                        img.save(img_path, format=img_format)
                        return f"/static/generated/{img_path.name}"
                elif "text" in part:
                    text_content = part["text"]
                    if text_content.startswith("data:image/"):
                        import base64
                        base64_str = text_content.split(",", 1)[1]
                        img_data = base64.b64decode(base64_str)
                        import io
                        from PIL import Image
                        img = Image.open(io.BytesIO(img_data))
                        img_format = img.format or "PNG"
                        import hashlib
                        img_hash = hashlib.md5(img_data).hexdigest()[:16]
                        img_dir = BASE_DIR / "static" / "generated"
                        img_dir.mkdir(parents=True, exist_ok=True)
                        img_path = img_dir / f"gai-{img_hash}.{img_format.lower()}"
                        img.save(img_path, format=img_format)
                        return f"/static/generated/{img_path.name}"
        return None
    except Exception as e:
        print(f"  [{cfg['name']}] {type(e).__name__}: {str(e)[:80]}")
        return None

def try_pollinations(prompt, width=1200, height=630):
    """API #2: Pollinations.ai（免费兜底）"""
    try:
        seed = abs(hash(prompt)) % 100000
        encoded = requests.utils.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded}?width={width}&height={height}&nologo=true&seed={seed}"
        r = requests.get(url, timeout=60, proxies=PROXIES, verify=False, stream=True)
        ct = r.headers.get("content-type", "")
        if r.status_code == 200 and "image" in ct.lower():
            return url
        print(f"  [{IMAGE_API_CONFIG['pollinations']['name']}] HTTP {r.status_code}, content-type: {ct}")
        return None
    except Exception as e:
        print(f"  [{IMAGE_API_CONFIG['pollinations']['name']}] {type(e).__name__}: {str(e)[:80]}")
        return None

def generate_image_url(prompt, size_str="16:9"):
    """主入口：按优先级尝试所有可用 API，返回第一个成功的图片 URL"""
    print(f"\n[ImageGen] 开始生成 (prompt: {prompt[:60]}...)")
    
    # 尺寸映射
    size_map = {
        "16:9": {"aspect_ratio": "16:9", "w": 1792, "h": 1024},
        "4:3": {"aspect_ratio": "4:3", "w": 1024, "h": 768},
        "1:1": {"aspect_ratio": "1:1", "w": 1024, "h": 1024},
    }
    size_cfg = size_map.get(size_str, size_map["16:9"])
    
    # 优先级排序
    apis = sorted(IMAGE_API_CONFIG.items(), key=lambda x: x[1]["priority"])
    
    for api_id, cfg in apis:
        print(f"  尝试 [{cfg['name']}] (priority={cfg['priority']})...")
        
        result = None
        try:
            if api_id == "google_gemini":
                if not cfg["api_key"]:
                    print(f"  [{cfg['name']}] 未配置 API Key，跳过")
                    continue
                
                client_kwargs = {"api_key": cfg["api_key"]}
                if cfg.get("proxy"):
                    client_kwargs["http_options"] = {"proxy": cfg["proxy"]}
                client = genai.Client(**client_kwargs)
                
                response = client.models.generate_content(
                    model=cfg["model"],
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE"],
                        image_config=types.ImageConfig(
                            aspect_ratio=size_cfg["aspect_ratio"],
                        ),
                    ),
                )
                
                for part in response.candidates[0].content.parts:
                    if part.inline_data:
                        img_seed = abs(hash(prompt + size_str)) % 1000000
                        img_filename = f"gemini_{img_seed}.png"
                        img_path = IMAGE_SAVE_DIR / img_filename
                        
                        if img_path.exists():
                            print(f"  [{cfg['name']}] 图片已存在，复用: {img_filename}")
                            result = f"/static/generated_images/{img_filename}"
                            break
                        
                        img_bytes = base64.b64decode(part.inline_data.data)
                        with open(img_path, "wb") as f:
                            f.write(img_bytes)
                        
                        result = f"/static/generated_images/{img_filename}"
                        break
                    
            elif api_id == "google_aistudio":
                result = try_google_aistudio(prompt, f"{size_cfg['w']}x{size_cfg['h']}")
            elif api_id == "pollinations":
                result = try_pollinations(prompt, size_cfg["w"], size_cfg["h"])
            elif api_id == "picsum":
                seed = abs(hash(prompt)) % 1000000
                picsum_url = f"https://picsum.photos/seed/{seed}/{size_cfg['w']}/{size_cfg['h']}"
                r = requests.get(picsum_url, timeout=30, proxies=PROXIES, verify=False, stream=True)
                if r.status_code == 200 and "image" in r.headers.get("content-type", ""):
                    result = picsum_url
        except Exception as e:
            print(f"  [{cfg['name']}] 调用失败: {type(e).__name__}: {str(e)[:80]}")
        
        if result:
            print(f"  ✅ [{cfg['name']}] 成功: {result[:80]}")
            return result
        else:
            print(f"  ❌ [{cfg['name']}] 失败，尝试下一个...")
    
    print(f"\n  ⚠️ 所有 API 均失败，返回最终兜底图")
    final_seed = abs(hash(prompt)) % 1000000
    return f"https://picsum.photos/seed/{final_seed}/{size_cfg['w']}/{size_cfg['h']}"

def generate_cover_for_post(title, slug):
    """生成博文封面图"""
    prompt = build_prompt(title, slug)
    return generate_image_url(prompt, "16:9")


GEO_REGIONS = ["EU", "US", "AU"]
GEO_WEIGHTS = [40, 35, 25]

# ========== SEO Meta Description 生成系统
# 依据 chinaboundtravel.com Meta Description 批量生成模板与优化规范
# 字符长度：120-155字符，必含三要素：核心价值+信任背书+弱行动号召

# 人设差异化结尾（轮换使用，避免重复）
JORAN_ENDINGS = [
    "from a US expat based in Chengdu",
    "from on-the-ground experience in China",
    "curated by a US-based China travel expert",
    "real tips from someone living in China since 2016",
    "by an American expat with 10 years in China"
]

# 品类模板定义
SEO_TEMPLATES = {
    "visa": {
        "template": "[Updated 2026] {topic} guide. {key_points} {ending}.",
        "key_points_examples": [
            "rules, eligible cities & common mistakes for travelers",
            "step-by-step process, required documents & latest policy updates",
            "requirements, application tips & insider advice"
        ]
    },
    "city_guide": {
        "template": "Complete {city} travel guide 2026. {highlights} {ending}.",
        "highlights_examples": [
            "best local food, 3-5 day itineraries & hidden gems",
            "top attractions, transportation tips & where to stay",
            "itineraries, local food & cultural experiences"
        ]
    },
    "internet_vpn": {
        "template": "Best {topic} for China in 2026 tested monthly. {benefits} {ending}.",
        "benefits_examples": [
            "reliable options for Google, WhatsApp & streaming",
            "tested & updated for reliable connectivity",
            "top picks for staying online without restrictions"
        ]
    },
    "payment": {
        "template": "{topic} guide for travelers in China 2026. {benefits} {ending}.",
        "benefits_examples": [
            "setup steps, limits & tips for foreigners",
            "step-by-step process, common pitfalls to avoid",
            "how to use without a Chinese bank account"
        ]
    },
    "accommodation": {
        "template": "Where to stay in {city} China 2026. {highlights} {ending}.",
        "highlights_examples": [
            "best neighborhoods, hotel recommendations & budget options",
            "area guide, top hotel picks & local boutiques",
            "accommodation options for all types of travelers"
        ]
    },
    "food": {
        "template": "{city} food guide: {highlights}. {ending}.",
        "highlights_examples": [
            "must-try local dishes & best restaurants",
            "top local snacks, where to find them & what to avoid",
            "authentic picks & hidden culinary gems"
        ]
    },
    "transportation": {
        "template": "China {topic}: complete guide 2026. {benefits} {ending}.",
        "benefits_examples": [
            "booking tips, seat classes & rookie mistakes to avoid",
            "how to navigate like a local, tested strategies",
            "practical guide based on 200+ rides experience"
        ]
    },
    "safety": {
        "template": "Is China safe for travelers in 2026? {highlights} {ending}.",
        "highlights_examples": [
            "honest assessment, crime rates & common scams to avoid",
            "practical safety tips from someone who lives here",
            "what to know before you go, real talk on safety"
        ]
    },
    "default": {
        "template": "{topic} for travelers visiting China. {highlights} {ending}.",
        "highlights_examples": [
            "practical tips & common mistakes to avoid",
            "essential guide based on 10 years of experience",
            "what you need to know before your trip"
        ]
    }
}

def classify_topic(topic, title):
    """根据选题和标题分类，返回类别标识"""
    topic_lower = (topic + " " + title).lower()
    
    if any(k in topic_lower for k in ["visa", "144-hour", "transit", "entry"]):
        return "visa"
    elif any(k in topic_lower for k in ["vpn", "internet", "esim", "sim", "wifi", "connect"]):
        return "internet_vpn"
    elif any(k in topic_lower for k in ["alipay", "wechat", "payment", "pay", "cash", "card"]):
        return "payment"
    elif any(k in topic_lower for k in ["hotel", "stay", "accommodation", "hostel", "airbnb"]):
        return "accommodation"
    elif any(k in topic_lower for k in ["food", "eat", "restaurant", "dish", "cuisine", "dumpling", "noodle"]):
        return "food"
    elif any(k in topic_lower for k in ["train", "metro", "taxi", "transport", "bus", "flight", "subway", "ride"]):
        return "transportation"
    elif any(k in topic_lower for k in ["safety", "safe", "crime", "scam", "danger", "risk"]):
        return "safety"
    elif any(k in topic_lower for k in ["chengdu", "beijing", "shanghai", "xian", "hangzhou", "guilin", "yunnan", "sichuan"]):
        return "city_guide"
    else:
        return "default"

def extract_city_name(topic, title):
    """从选题和标题中提取城市名"""
    cities = [
        "Beijing", "Shanghai", "Chengdu", "Xi'an", "Hangzhou", "Guilin",
        "Xian", "Guangzhou", "Shenzhen", "Hong Kong", "Macau",
        "Lijiang", "Dali", "Kunming", "Lhasa", "Jiuzhaigou"
    ]
    text = topic + " " + title
    for city in cities:
        if city.lower() in text.lower():
            return city
    return "China"

def generate_seo_description(topic, title):
    """生成 SEO 优化的 meta description"""
    category = classify_topic(topic, title)
    template_config = SEO_TEMPLATES.get(category, SEO_TEMPLATES["default"])
    template = template_config["template"]
    
    # 提取城市名
    city = extract_city_name(topic, title)
    
    # 替换模板变量
    description = template
    description = description.replace("{topic}", topic.replace(" guide", "").replace(" Guide", ""))
    description = description.replace("{city}", city)
    
    # 添加随机亮点
    if "key_points_examples" in template_config:
        key_point = random.choice(template_config["key_points_examples"])
        description = description.replace("{key_points}", key_point)
    elif "highlights_examples" in template_config:
        highlight = random.choice(template_config["highlights_examples"])
        description = description.replace("{highlights}", highlight)
    elif "benefits_examples" in template_config:
        benefit = random.choice(template_config["benefits_examples"])
        description = description.replace("{benefits}", benefit)
    else:
        description = description.replace("{highlights}", "practical tips & essential guide")
    
    # 添加随机结尾
    ending = random.choice(JORAN_ENDINGS)
    description = description.replace("{ending}", ending)
    
    # 清理多余空格
    description = re.sub(r'\s+', ' ', description).strip()
    
    # 确保字符长度在 120-155 之间
    while len(description) > 155 and len(description) > 0:
        # 找到最后一个逗号或介词，尝试截断
        if ", " in description:
            description = description.rsplit(", ", 1)[0]
        elif " & " in description:
            description = description.rsplit(" & ", 1)[0]
        else:
            break
    
    while len(description) < 120:
        # 添加额外信息
        extra = "practical guide for foreign travelers"
        if description.endswith("."):
            description = description[:-1] + ", " + extra + "."
        else:
            description = description + ". " + extra
    
    return description

# 选题库 - 主选题、备选选题、万能选题
TOPIC_LIBRARY = {
    "main": [
        "transportation guide",
        "cultural etiquette",
        "travel safety",
        "accommodation tips",
        "food recommendations"
    ],
    "alternate": [
        "off-the-beaten-path routes",
        "visa and entry requirements",
        "family travel tips"
    ],
    "universal": [
        "Essential Safety Tips for First-Time Travellers in China",
        "Must-Try Traditional Chinese Food for Overseas Visitors",
        "Basic Cultural Etiquette While Traveling Around China"
    ]
}

AUTHOR_CFG = {
    "name": "Joran",
    "identity": "American from California, long-term resident living in Chengdu over 10 years, movie buff",
    "view": "first-person personal travel experience with humorous movie references",
    "tone": "witty, humorous, conversational blogger writing style with movie analogies",
    "forbid": ["randomly add Los Angeles/San Francisco without contextual demand", "shift to third-person narration", "fabricate travel cost data", "write extensively about overseas travel or movie plots"]
}

MAX_DAILY_RETRY = 3
FEISHU_WEBHOOK = os.getenv("FEISHU_WEBHOOK_URL")

class BlogAIClient:
    """统一的博客AI客户端 - 使用豆包API"""
    def __init__(self):
        self.client = DoubaoArkClient()
        self._call_count = 0

    def chat(self, messages, model=None, max_tokens=2000, temperature=0.7):
        """调用豆包API生成内容"""
        result = self.client.chat(messages, model=model, max_tokens=max_tokens, temperature=temperature)
        self._call_count += 1
        print(f"[AI] 调用 #{self._call_count}, 输出 {result.get('output_tokens', 0)} tokens")
        return result["content"]

    def get_cost_summary(self):
        return {
            "calls_this_session": self._call_count,
            "daily_used_yuan": 0,
            "daily_budget_yuan": 0,
            "monthly_used_yuan": 0,
            "monthly_budget_yuan": 0,
        }

class ManifestManager:
    def __init__(self):
        self.path = MANIFEST_PATH
        self.data = self._load()
    
    def _load(self):
        if self.path.exists():
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"month_post_count": 0, "last_reset_date": datetime.now().strftime("%Y-%m-01"), "history_topics": [], "keyword_convert_rate": {}, "geo_convert_rate": {}}
    
    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)
    
    def check_topic_repeat(self, topic, geo_region, days=30):
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        for record in self.data["history_topics"]:
            if record["topic"] == topic and record["geo_region"] == geo_region:
                if record["create_date"] >= cutoff_date:
                    return True
        return False
    
    def add_topic(self, topic, geo_region):
        self.data["history_topics"].append({
            "topic": topic,
            "geo_region": geo_region,
            "create_date": datetime.now().strftime("%Y-%m-%d")
        })
    
    def increment_post_count(self):
        today = datetime.now()
        current_month = f"{today.year}-{today.month:02d}-01"
        
        if self.data["last_reset_date"] != current_month:
            self.data["month_post_count"] = 0
            self.data["last_reset_date"] = current_month
        
        self.data["month_post_count"] += 1
    
    def get_post_count(self):
        today = datetime.now()
        current_month = f"{today.year}-{today.month:02d}-01"
        
        if self.data["last_reset_date"] != current_month:
            self.data["month_post_count"] = 0
            self.data["last_reset_date"] = current_month
            self.save()
        
        return self.data["month_post_count"]

    def check_daily_social_limit(self, daily_limit=5):
        """检查今日社媒发布是否已达上限，返回 (是否受限, 今日已发布数, 限额)"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 初始化默认值（防止旧版本 manifest 缺失字段）
        if "daily_social_publish_date" not in self.data:
            self.data["daily_social_publish_date"] = today
            self.data["daily_social_publish_count"] = 0
            self.data["daily_social_publish_limit"] = daily_limit
            self.save()
            return False, 0, daily_limit
        
        # 新的一天，重置计数
        if self.data["daily_social_publish_date"] != today:
            self.data["daily_social_publish_date"] = today
            self.data["daily_social_publish_count"] = 0
            self.save()
            return False, 0, daily_limit
        
        # 确保 limit 字段存在
        if "daily_social_publish_limit" not in self.data:
            self.data["daily_social_publish_limit"] = daily_limit
            self.save()
        
        current_count = self.data.get("daily_social_publish_count", 0)
        limit = self.data.get("daily_social_publish_limit", daily_limit)
        is_limited = current_count >= limit
        
        return is_limited, current_count, limit

    def increment_daily_social_count(self):
        """社媒发布成功后，递增今日计数"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 新的一天或字段缺失，重置并初始化
        if self.data.get("daily_social_publish_date") != today:
            self.data["daily_social_publish_date"] = today
            self.data["daily_social_publish_count"] = 0
            if "daily_social_publish_limit" not in self.data:
                self.data["daily_social_publish_limit"] = 5
        
        self.data["daily_social_publish_count"] = self.data.get("daily_social_publish_count", 0) + 1
        self.save()
        return self.data["daily_social_publish_count"]

class FeishuNotifier:
    @staticmethod
    def send_notification(title, content, webhook_url=None):
        url = webhook_url or FEISHU_WEBHOOK
        if not url:
            return
        
        payload = {
            "msg_type": "post",
            "content": {
                "post": {
                    "zh_cn": {
                        "title": title,
                        "content": [[{"tag": "text", "text": content}]]
                    }
                }
            }
        }
        
        try:
            requests.post(url, json=payload, timeout=30)
        except Exception:
            pass

class AIEngine:
    def __init__(self):
        self.client = BlogAIClient()
        self.external_data = self._load_external_data()
    
    def _load_external_data(self):
        """加载外部数据文件（生成前置加载）"""
        config_dir = BASE_DIR / "config"
        
        data = {
            "error_knowledge": [],
            "gsc_keywords": [],
            "competitor_topics": [],
            "user_feedback": [],
            "content_knowledge": []
        }
        
        # 1. 加载错误知识库
        try:
            with open(config_dir / "error_knowledge_base.json", 'r', encoding='utf-8') as f:
                kb_data = json.load(f)
                data["error_knowledge"] = kb_data.get("error_patterns", [])
        except:
            pass
        
        # 2. 加载GSC热搜词
        try:
            with open(config_dir / "gsc_hot_keyword.json", 'r', encoding='utf-8') as f:
                gsc_data = json.load(f)
                data["gsc_keywords"] = gsc_data.get("keywords", [])
        except:
            pass
        
        # 3. 加载竞品数据
        try:
            with open(config_dir / "competitor_topic.json", 'r', encoding='utf-8') as f:
                competitor_data = json.load(f)
                data["competitor_topics"] = competitor_data.get("content_trends", [])
        except:
            pass
        
        # 4. 加载用户反馈
        try:
            with open(config_dir / "user_feedback.json", 'r', encoding='utf-8') as f:
                feedback_data = json.load(f)
                data["user_feedback"] = feedback_data.get("feedbacks", [])
        except:
            pass
        
        # 5. 加载旅行知识库（从外部学习的内容）
        try:
            with open(config_dir / "content_knowledge_base.json", 'r', encoding='utf-8') as f:
                kb_data = json.load(f)
                all_knowledge = []
                for category, entries in kb_data.get("knowledge_categories", {}).items():
                    all_knowledge.extend(entries)
                data["content_knowledge"] = all_knowledge
        except:
            pass
        
        return data
    
    def _build_prevention_rules(self):
        """从错误知识库构建预防规则，注入到生成Prompt中"""
        rules = []
        
        rules.append("ENCODING RULES (CRITICAL):")
        rules.append("  - NEVER use Chinese characters (use Pinyin or English instead)")
        rules.append("  - NEVER use emojis or special symbols (→, ✅, ❌, 🇨🇳, etc.)")
        rules.append("  - NEVER use Chinese quotation marks 「」『』")
        rules.append("  - Use ONLY standard ASCII quotes (\")")
        rules.append("  - Use ONLY English punctuation (. , ! ? ;)")
        rules.append("  - Use \"->\" or \"leads to\" instead of arrow symbols")
        rules.append("  - Chinese place names: use Pinyin (Chengdu, Beijing, Shanghai)")
        rules.append("  - Chinese food names: use English translation (hotpot, dumplings, noodles)")
        
        unresolved_errors = [e for e in self.external_data["error_knowledge"] if not e.get("resolved")]
        if unresolved_errors:
            rules.append("")
            rules.append("==== LEARNING BASE (ACTIVE ISSUES) ====")
            rules.append("THESE ARE CRITICAL ISSUES THAT CAUSED REJECTIONS - MUST FOLLOW:")
            for error in unresolved_errors:
                if error.get("prevention_rules"):
                    rules.append("")
                    rules.append(f"[ACTIVE] {error.get('message', '')[:60]} (occurred {error.get('occurrences', 0)} times)")
                    for rule in error["prevention_rules"]:
                        rules.append(f"  - MUST: {rule}")
        
        resolved_errors = [e for e in self.external_data["error_knowledge"] if e.get("resolved")]
        if resolved_errors:
            rules.append("")
            rules.append("==== HISTORICAL LEARNING (RESOLVED) ====")
            for error in resolved_errors:
                if error.get("prevention_rules"):
                    rules.append("")
                    rules.append(f"[RESOLVED] {error.get('message', '')[:40]}...")
                    for rule in error["prevention_rules"]:
                        rules.append(f"  - {rule}")
        
        rules.append("")
        rules.append("PLACEHOLDER RULES:")
        rules.append("  - Use [Image:description] format for image placeholders")
        rules.append("  - NEVER use ![alt](url) format")
        rules.append("  - Use {{< vpn-link \"text\" />}} for VPN affiliate links")
        rules.append("  - Use {{< klook-link \"text\" />}} for booking/hotel affiliate links")
        rules.append("  - NEVER leave placeholder text like \"#TP_VPN_PLACEHOLDER#\"")
        
        rules.append("")
        rules.append("FRONT MATTER RULES:")
        rules.append("  - title: must be properly quoted")
        rules.append("  - description: must be 120-155 characters")
        rules.append("  - date: must follow ISO format YYYY-MM-DDTHH:MM:SS+08:00")
        rules.append("  - NO duplicate documents in YAML stream")
        
        rules.append("")
        rules.append("CONTENT QUALITY RULES:")
        rules.append("  - NO factual errors (verify time, prices, durations)")
        rules.append("  - description/summary must be unique per article")
        rules.append("  - NO test pages in production")
        rules.append("  - Include Schema markup for SEO")
        rules.append("  - Add Alt text for all images")
        rules.append("  - MINIMUM 1500 words required - provide EXTREMELY detailed content")
        
        rules.append("")
        rules.append("SENSITIVE CONTENT RULES (MANDATORY):")
        rules.append("  - NEVER mention politics, government, communist, or any political topics")
        rules.append("  - NEVER mention Tiananmen, Taiwan independence, or Falun Gong")
        rules.append("  - NEVER discuss controversial topics or sensitive historical events")
        rules.append("  - Focus ONLY on travel, culture, food, transportation, and practical tips")
        rules.append("  - If discussing history, focus on ancient history (dynasty era) only")
        rules.append("  - Avoid any modern political or social commentary")
        
        return "\n".join(rules)
    
    def _get_related_knowledge(self, topic):
        topic_lower = topic.lower()
        related = []
        
        for item in self.external_data.get("content_knowledge", []):
            item_keyword = item.get("keyword", "").lower()
            item_content = item.get("content", "").lower()
            
            if topic_lower in item_keyword or item_keyword in topic_lower:
                related.append(item)
            elif any(kw in topic_lower for kw in item_content.split()[:15]):
                related.append(item)
        
        related.sort(key=lambda x: x.get("relevance", 0), reverse=True)
        return related[:5]
    
    def generate_post(self, topic, geo_region):
        region_info = {
            "EU": "European travelers (UK, Germany, France, Italy, Spain)",
            "US": "American travelers (California, major cities)",
            "AU": "Australian and New Zealand travelers"
        }
        
        # 构建SEO关键词提示（从外部数据）
        seo_keywords = []
        for kw in self.external_data["gsc_keywords"][:5]:
            seo_keywords.append(kw.get("query", ""))
        
        # 构建用户需求提示
        user_needs = []
        for feedback in self.external_data["user_feedback"][:5]:
            content = feedback.get("content", "")
            if content and len(content) > 10:
                user_needs.append(content)
        
        prevention_rules = self._build_prevention_rules()
        
        related_knowledge = self._get_related_knowledge(topic)
        knowledge_section = ""
        if related_knowledge:
            knowledge_section = "\n===== RELATED TRAVEL KNOWLEDGE (LEARNED FROM OTHER BLOGGERS) =====\n"
            for idx, item in enumerate(related_knowledge[:5], 1):
                key_points = "\n".join([f"  - {kp}" for kp in item.get("key_points", [])])
                knowledge_section += f"[{idx}] {item.get('keyword', '')}\n{key_points}\n\n"
            knowledge_section += "===== END RELATED KNOWLEDGE =====\n\n"
        
        prompt = f"""Joran: California American who has lived in Chengdu for over 10 years. I'm a movie buff and travel blogger with a witty, conversational writing style.

Write an IN-DEPTH, DETAILED, HUMOROUS FIRST-PERSON travel blog post about: {topic}
Target audience: {region_info[geo_region]}

SEO Keywords to include naturally: {', '.join(seo_keywords) if seo_keywords else 'China travel, Chengdu, travel tips'}

User feedback to address: {'; '.join(user_needs) if user_needs else 'None'}

{knowledge_section}

===== CRITICAL PREVENTION RULES (MUST FOLLOW) =====
{prevention_rules}
===== END PREVENTION RULES =====

===== ORIGINALITY GUARANTEE (MANDATORY) =====
1. ORIGINAL CONTENT: Write ENTIRELY original content - NEVER copy, paraphrase, or closely mimic other blogs
2. UNIQUE ANGLE: Find a unique perspective or angle that other travel blogs haven't covered
3. NEW INFORMATION: Include facts, tips, or stories that are NOT commonly found in other China travel guides
4. PERSONAL VOICE: Use your own unique voice and experiences - don't regurgitate generic travel advice
5. NO PLAGIARISM: Do NOT use sentences or paragraphs from other sources - write everything in your own words
6. VALUE ADD: Provide MORE value than what's available on popular travel sites - go deeper, be more specific
===== END ORIGINALITY RULES =====

Requirements for HIGH-QUALITY CONTENT:
1. TONE: Conversational, witty, authoritative - like chatting with a trusted friend who's been there and done it
2. DEPTH: Provide EXTREMELY detailed, actionable insights - NO surface-level tips. Go DEEP into topics.
3. PERSONAL ANECDOTES: Include MULTIPLE SPECIFIC stories from my 10+ years in China:
   - Funny mishaps (getting lost, language barriers, cultural misunderstandings)
   - Street food adventures (specific stalls, weird foods tried)
   - Transportation stories (crazy taxi rides, subway experiences)
   - Personal connections (local friends, unexpected friendships)
4. COMPARISONS: Mention California roots NATURALLY for humorous comparison (e.g., "In LA we have In-N-Out, but in Chengdu...")
5. MOVIE REFERENCES: Include 2-3 funny movie analogies (e.g., comparing subway crowds to 'The Hunger Games', bargaining like 'Ocean's Eleven', Chinese bureaucracy like 'The Matrix')
6. LENGTH: MINIMUM 2000 words - provide COMPREHENSIVE coverage with plenty of details
7. STRUCTURE: 
   - Engaging introduction with a strong hook (story, surprising fact, or question)
   - 5-7 DETAILED H2 sections (##) with SUBPOINTS and EXAMPLES
   - Each section must have PRACTICAL takeaways/summary
   - Memorable conclusion with call to action and personal reflection
8. INTERNAL LINKS: Include at least 4 internal links like [topic](https://chinaboundtravel.com/posts/topic-slug/)
9. IMAGE PLACEHOLDERS: MUST include EXACTLY 2 image placeholders:
   - One RIGHT AFTER the introduction
   - One IN the MIDDLE of the article (around 40-60% mark)
   - FORMAT: [Image:detailed description of the scene, including subject, setting, mood]
10. PRACTICAL VALUE: Provide SPECIFIC tips, hidden gems, local secrets, and actionable advice:
    - Exact addresses or areas to visit
    - How much things cost (specific prices)
    - Best times to go
    - What to avoid
    - Step-by-step guides
11. CULTURAL INSIGHTS: Explain the 'WHY' behind Chinese customs and behaviors - give historical/cultural context
12. MAIN FOCUS: China travel - comparisons/California/movies are just flavor, NOT the main dish
13. NO sensitive topics: government, politics, religion, or controversial issues
14. ADDRESS CONCERNS: Visa info, transportation, budget, safety - address these naturally throughout
15. AUTHORITY: Reference my 10+ years experience frequently but naturally

Output ONLY the article content with proper Markdown formatting."""
        
        messages = [{"role": "user", "content": prompt}]
        # 【深度内容】max_tokens=3500，确保足够深度（生成2000+词文章）
        return self.client.chat(messages, max_tokens=3500)
    
    def rewrite_post(self, content, topic, geo_region):
        region_info = {
            "EU": "European travelers",
            "US": "American travelers",
            "AU": "Australian and New Zealand travelers"
        }
        
        # 【深度版】增强重写Prompt
        prompt = f"""Rewrite and ENHANCE this blog post to be more in-depth and engaging.

{content}

Requirements:
1. Add proper H2 headings (##) for main sections if missing
2. Expand content to minimum 1000 words with detailed insights
3. Add at least 3 internal links to other China travel topics
4. Add EXACTLY 2 image placeholders:
   - One AFTER the introduction
   - One IN the MIDDLE of the article
   - Format: [Image:detailed description of the scene, including subject, setting, mood]
5. Keep Joran persona: California native, 10+ years in Chengdu, witty, movie references
6. Add more personal anecdotes and actionable tips
7. Original topic: {topic}
8. Target audience: {region_info[geo_region]}
9. MAIN FOCUS must be China travel

Output ONLY the rewritten article with proper Markdown formatting."""
        
        messages = [{"role": "user", "content": prompt}]
        # 【深度重写】max_tokens=2500，确保足够深度
        return self.client.chat(messages, max_tokens=2500)
    
    def add_image_placeholders(self, article_md):
        """【降本核心】局部补图 - 仅添加图片占位符，不修改任何文字，Token仅为全文5%"""
        prompt = f"""TASK: Add or fix EXACTLY 2 image placeholders in this article. DO NOT MODIFY ANY EXISTING TEXT.

RULES:
1. If there are any existing ![alt text](url) format images, CONVERT THEM to [Image:description] format
2. Add/ensure EXACTLY 2 image placeholders total:
   - One RIGHT AFTER the introduction (first paragraph)
   - One IN the MIDDLE of the article (around the halfway point)
3. FORMAT: [Image:detailed description of the scene, including subject, setting, mood]
4. DO NOT USE ![alt text](url) format - ONLY use [Image:xxx] format
5. Do not change, delete, or rephrase ANY existing words.

Article:
{article_md}

Output ONLY the modified article with correct [Image:xxx] placeholders."""
        
        messages = [{"role": "user", "content": prompt}]
        # 【降本】max_tokens=500，补图只需要少量token
        return self.client.chat(messages, max_tokens=500)

class SubEditor:
    def __init__(self):
        self.client = BlogAIClient()
    
    def full_check(self, article_md, frontmatter):
        """副主编初审：校验图片占位符格式 + 链接格式 + 内容质量 + 编码验证"""
        errors = []
        
        # 【编码校验】检查乱码字符
        garbled_count = article_md.count("\ufffd") + article_md.count("�")
        if garbled_count > 0:
            errors.append(f"【编码错误】发现{garbled_count}处乱码字符（�），必须修复后才能发布")
        
        # 【编码校验】检查中文字符
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', article_md)
        if chinese_chars:
            errors.append(f"【编码错误】发现中文字符，应使用拼音或英文替代")
        
        # 【编码校验】检查 emoji
        emoji_pattern = re.compile(r'[\u2700-\u27bf]|[\uE000-\uF8FF]|\uD83C[\uDC00-\uDFFF]|\uD83D[\uDC00-\uDFFF]|\uD83E[\uDD00-\uDEFF]')
        emojis = emoji_pattern.findall(article_md)
        if emojis:
            errors.append(f"【编码错误】发现{len(emojis)}个emoji，应使用文字描述替代")
        
        # 【编码校验】检查特殊箭头符号
        special_arrows = article_md.count("→") + article_md.count("←") + article_md.count("↑") + article_md.count("↓")
        if special_arrows > 0:
            errors.append(f"【编码错误】发现特殊箭头符号，应使用 -> 或文字描述替代")
        
        # 【编码校验】检查中文引号
        chinese_quotes = article_md.count("「") + article_md.count("」") + article_md.count("『") + article_md.count("』")
        if chinese_quotes > 0:
            errors.append(f"【编码错误】发现中文引号，应使用标准英文引号")
        
        # 【图片占位符校验】检查 [Image:xxx] 格式的占位符数量
        image_placeholders = re.findall(r'\[\s*Image\s*:\s*[^\]]+\]', article_md, re.IGNORECASE)
        img_num = len(image_placeholders)
        
        # 检查是否有错误格式的图片（![xxx] 格式）
        md_images = article_md.count("![")
        if md_images > 0:
            errors.append(f"【图片格式错误】发现{md_images}处 ![alt](url) 格式图片，请使用标准 [Image:描述] 格式")
        
        # 检查图片数量是否达标
        if img_num < 2:
            errors.append(f"【配图不足】仅有{img_num}个 [Image:xxx] 占位符，需2个（导语后1个 + 正文中1个）")
        
        # 【链接格式校验】检查是否有无效链接格式（如 <link> 标签）
        if '<link' in article_md.lower():
            errors.append("【链接格式】发现无效 <link> 标签，请使用标准 Markdown 链接格式 [文字](链接)")
        
        # 【占位符校验】检查未替换的占位符
        if "#TP_VPN_PLACEHOLDER#" in article_md or "#TP_BOOKING_PLACEHOLDER#" in article_md:
            errors.append("【占位符残留】发现未替换的联盟链接占位符")
        
        # 【内容长度检查】确保内容足够深入
        word_count = len(article_md.split())
        if word_count < 600:
            errors.append(f"【内容过短】当前仅{word_count}词，建议至少800词以保证内容深度")
        
        return len(errors) == 0, errors

class ChiefEditor:
    def __init__(self):
        self.client = BlogAIClient()
    
    def full_check(self, content):
        """主编终审：检查主旨、深度和原创性"""
        errors = []
        error_types = []
        
        # 【主旨检查】正文核心必须是中国内容
        content_lower = content.lower()
        china_markers = ["china", "chengdu", "beijing", "shanghai", "chinese", "xian", "guilin", "suzhou", "hangzhou"]
        china_count = sum(content_lower.count(m) for m in china_markers)
        
        if china_count < 3:
            errors.append("【主旨驳回】文章未以中国为主体，缺少核心中国内容")
            error_types.append("topic")
        
        # 【深度检查】确保有足够的细节和分析
        word_count = len(content.split())
        if word_count < 700:
            errors.append(f"【内容深度不足】文章内容过短({word_count}词)，缺少深度分析和实用信息")
            error_types.append("depth")
        
        # 【敏感词检查】纯文本匹配
        sensitive_words = ["politics", "government", "communist", "tiananmen", "taiwan independence", "falun gong"]
        for w in sensitive_words:
            if w in content_lower:
                errors.append(f"【风控】正文含违规词汇:{w}")
                error_types.append("sensitive")
        
        return len(errors) == 0, errors, error_types, word_count

class BlogGenerator:
    def __init__(self):
        self.manifest = ManifestManager()
        self.ai_engine = AIEngine()
        self.sub_editor = SubEditor()
        self.chief_editor = ChiefEditor()
        self.notifier = FeishuNotifier()
        self.max_retries = MAX_DAILY_RETRY
        self.used_topics = set()  # 记录本轮已尝试的选题
        
        from scripts.error_handler import ErrorHandler
        self.error_handler = ErrorHandler(str(BASE_DIR))
    
    def topic_precheck(self, topic):
        """选题预检 - 零Token消耗，检查选题是否以中国为落脚点"""
        china_keywords = ["china", "chinese", "chengdu", "beijing", "shanghai", "xian", "guilin", "panda"]
        topic_lower = topic.lower()
        
        # 检查选题是否与中国相关
        for kw in china_keywords:
            if kw in topic_lower:
                return True
        
        # 如果是通用选题，也认为是有效的（如 "travel safety"）
        return True
    
    def check_cooldown(self, topic, days=7):
        """检查选题是否在冷却期内（7天）"""
        return self.manifest.check_topic_repeat(topic, "global", days)

    def load_topic_pool(self):
        """加载外部选题库 (config/topic_pool.json)"""
        topic_pool_path = BASE_DIR / "config" / "topic_pool.json"
        try:
            if topic_pool_path.exists():
                with open(topic_pool_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get("topics", [])
        except Exception as e:
            print(f"[WARN] 加载选题库失败: {e}")
        return []

    def select_topic(self, attempt=1):
        """选择选题 - 优先从外部选题库选择，只有选题库为空时才回退到内置选题库"""
        geo_convert_rates = self.manifest.data.get("geo_convert_rate", {})
        if geo_convert_rates:
            regions = list(geo_convert_rates.keys())
            geo_weights = [geo_convert_rates.get(r, 0.1) * GEO_WEIGHTS[GEO_REGIONS.index(r)] for r in regions]
            geo_region = random.choices(regions, weights=geo_weights)[0]
        else:
            geo_region = random.choices(GEO_REGIONS, weights=GEO_WEIGHTS)[0]
        
        # 优先从外部选题库选择（100%概率，不再回退到旧选题库）
        topic_pool = self.load_topic_pool()
        if topic_pool:
            available_topics = [t for t in topic_pool 
                              if t.get("status") == "pending"
                              and t.get("geo") == geo_region
                              and t.get("title") not in self.used_topics]
            
            if available_topics:
                topic_data = random.choice(available_topics)
                topic = topic_data["title"]
                self.used_topics.add(topic)
                return topic, geo_region
            
            # 如果当前地域没有可用选题，尝试其他地域
            available_topics = [t for t in topic_pool 
                              if t.get("status") == "pending"
                              and t.get("title") not in self.used_topics]
            
            if available_topics:
                topic_data = random.choice(available_topics)
                topic = topic_data["title"]
                geo_region = topic_data.get("geo", geo_region)
                self.used_topics.add(topic)
                return topic, geo_region
        
        # 只有当外部选题库为空或所有选题都已使用时，才回退到内置选题库
        if attempt == 1:
            topics = TOPIC_LIBRARY["main"]
        elif attempt == 2:
            topics = TOPIC_LIBRARY["alternate"]
        else:
            topics = TOPIC_LIBRARY["universal"]
        
        available_topics = [t for t in topics if t not in self.used_topics and not self.check_cooldown(t)]
        
        if available_topics:
            topic = random.choice(available_topics)
        else:
            topic = random.choice(topics)
        
        self.used_topics.add(topic)
        return topic, geo_region
    
    def generate_slug(self, title):
        slug = re.sub(r'[^a-z0-9\s-]', '', title.lower())
        slug = re.sub(r'[\s-]+', '-', slug).strip('-')
        return slug
    
    def _record_audit_failure(self, error_hash, error_message, title):
        kb = self.error_handler.kb
        existing_pattern = None
        
        for pattern in kb.get("error_patterns", []):
            if pattern.get("hash") == error_hash:
                existing_pattern = pattern
                break
        
        if existing_pattern:
            existing_pattern["occurrences"] = existing_pattern.get("occurrences", 0) + 1
            existing_pattern["last_seen"] = datetime.now().isoformat()
            if title not in existing_pattern.get("files", []):
                existing_pattern["files"].append(title)
        else:
            new_pattern = {
                "hash": error_hash,
                "type": "内容质量" if error_hash == "content_depth_insufficient" else "风控" if error_hash == "sensitive_content_politics" else "选题",
                "message": error_message,
                "occurrences": 1,
                "first_seen": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat(),
                "files": [title],
                "suggestion": "确保文章至少700词" if error_hash == "content_depth_insufficient" else "避免政治敏感内容",
                "resolved": False,
                "priority": "P0",
                "source": "主编终审"
            }
            kb["error_patterns"].append(new_pattern)
        
        kb["total_errors"] = kb.get("total_errors", 0) + 1
        kb["last_updated"] = datetime.now().isoformat()
        self.error_handler.save_knowledge_base()
        print(f"[Learning] Recorded audit failure: {error_hash} - {title}")
    
    def create_frontmatter(self, title, geo_region, topic):
        slug = self.generate_slug(title)
        date = datetime.now().strftime("%Y-%m-%dT10:00:00+08:00")
        
        tags = ["ChinaTravel", "TravelGuide", "China"]
        if geo_region == "EU":
            tags.append("EuropeToChina")
        elif geo_region == "US":
            tags.append("USToChina")
        elif geo_region == "AU":
            tags.append("AustraliaToChina")
        
        # 生成 SEO 优化的 meta description
        seo_description = generate_seo_description(topic, title)
        seo_summary = seo_description  # summary 也使用同一描述
        
        return {
            "title": title,
            "date": date,
            "lastmod": date,
            "author": "Joran",
            "slug": slug,
            "tags": tags,
            "categories": ["China"],
            "geo": geo_region,
            "draft": "true",
            "audit_status": "pending",
            "summary": seo_summary,
            "description": seo_description,
            "canonicalURL": f"{SITE_DOMAIN}/posts/{slug}/",
            "ShowToc": "true",
            "TocOpen": "false",
            "weight": 1
        }
    
    def write_markdown(self, frontmatter, content, filepath):
        frontmatter_lines = ["---"]
        for key, value in frontmatter.items():
            if isinstance(value, list):
                frontmatter_lines.append(f"{key}:")
                for item in value:
                    frontmatter_lines.append(f"  - {item}")
            else:
                frontmatter_lines.append(f'{key}: "{value}"')
        frontmatter_lines.append("---")
        
        full_content = "\n".join(frontmatter_lines) + "\n\n" + content
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(full_content)
        
        self._validate_file(filepath)
    
    def _validate_file(self, filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            
            corruption_patterns = ["-t-i-t-l-e-", "-d-e-s-c-r-i-p-t-i-o-n-", "-d-a-t-e-", "-a-u-t-h-o-r-"]
            for pattern in corruption_patterns:
                if pattern in content:
                    print(f"⚠️ 检测到文件损坏模式: {pattern}")
                    os.remove(filepath)
                    raise ValueError(f"File corrupted with pattern: {pattern}")
            
            if content.count("---") < 2:
                print("⚠️ 检测到 YAML 边界缺失")
                os.remove(filepath)
                raise ValueError("YAML frontmatter boundary missing")
            
            if len(content) < 10:
                print("⚠️ 检测到文件内容过短")
                os.remove(filepath)
                raise ValueError("File content too short")
            
            print(f"✅ 文件验证通过: {filepath}")
        except Exception as e:
            print(f"❌ 文件验证失败: {e}")
            raise
    
    def move_to_posts(self, draft_path, title, slug):
        filename = draft_path.name.replace("-attempt1", "").replace("-attempt2", "").replace("-attempt3", "")
        post_path = POSTS_DIR / filename
        
        with open(draft_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        content = content.replace('draft: "true"', 'draft: "false"')
        content = content.replace('audit_status: "pending"', 'audit_status: "pass2"')
        
        # 生成封面图，添加 cover 字段到 frontmatter
        cover_url = generate_cover_for_post(title, slug)
        if cover_url:
            # 在第二个 "---" 前插入 cover 字段
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = parts[1]
                if 'cover:' not in frontmatter:
                    # 插入 cover 到 frontmatter 开头（title 之后）
                    lines = frontmatter.split("\n")
                    new_lines = []
                    cover_inserted = False
                    for line in lines:
                        new_lines.append(line)
                        if line.startswith('title:') and not cover_inserted:
                            new_lines.append('cover:')
                            new_lines.append(f'  image: "{cover_url}"')
                            cover_inserted = True
                    new_frontmatter = "\n".join(new_lines)
                    content = f"---{new_frontmatter}---{parts[2]}"
        
        # 替换文章正文中的 [Image:xxx] 占位符为真实图片
        import re
        image_pattern = r'\[\s*Image\s*:\s*([^\]]+)\]'
        image_matches = re.findall(image_pattern, content, re.IGNORECASE)
        for idx, placeholder in enumerate(image_matches):
            print(f"  [ImageGen] Replacing placeholder {idx+1}: {placeholder[:50]}...")
            img_url = generate_image_url(placeholder, "4:3")
            if img_url:
                old_text = re.search(r'\[\s*Image\s*:\s*' + re.escape(placeholder) + r'\]', content, re.IGNORECASE)
                if old_text:
                    new_text = f"![{placeholder}]({img_url})"
                    content = content[:old_text.start()] + new_text + content[old_text.end():]
                    print(f"  [ImageGen] OK: {img_url[:80]}")
        
        with open(post_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        draft_path.unlink()
        return cover_url

    
    def run_single_post(self, attempt=1):
        topic, geo_region = self.select_topic(attempt)
        print(f"[Attempt {attempt}] Selected topic: {topic} for {geo_region}")
        self.notifier.send_notification(f"🔄 开始第{attempt}/{MAX_DAILY_RETRY}轮AI撰稿生成", f"选题: {topic} | 目标地域: {geo_region}")
        
        # 选题预检
        if not self.topic_precheck(topic):
            self.notifier.send_notification("❌ 选题预检失败", f"选题《{topic}》未以中国为落脚点，已拦截")
            print(f"[Attempt {attempt}] Topic precheck failed: {topic}")
            return {"success": False, "reason": "topic_precheck_failed", "title": topic, "same_topic": False}
        
        try:
            content = self.ai_engine.generate_post(topic, geo_region)
        except Exception as e:
            self.notifier.send_notification("❌ AI生成失败", f"第{attempt}次尝试: 文章生成时发生错误: {str(e)}")
            raise
        
        title = re.search(r'^#\s+(.+)', content, re.MULTILINE)
        title = title.group(1) if title else f"{topic.title()} Guide"
        
        DRAFT_DIR.mkdir(parents=True, exist_ok=True)
        draft_path = DRAFT_DIR / f"{datetime.now().strftime('%Y-%m-%d')}-{self.generate_slug(title)}-attempt{attempt}.md"
        
        frontmatter = self.create_frontmatter(title, geo_region, topic)
        self.write_markdown(frontmatter, content, draft_path)
        
        # 【降本版】SubEditor 只检查图片，缺图直接局部补图，永远不重写全文
        sub_ok, sub_errors = self.sub_editor.full_check(content, frontmatter)
        if not sub_ok:
            # 只有图片问题，直接用局部补图
            print(f"[Attempt {attempt}] Image placeholders missing, using PARTIAL image addition (95% Token saved)...")
            self.notifier.send_notification("🖼️ 图片占位符不足", f"文章《{title}》图片不足，启动局部补图（节省95% Token，不重写全文）")
            
            try:
                content = self.ai_engine.add_image_placeholders(content)
                # 更新草稿文件
                self.write_markdown(frontmatter, content, draft_path)
                self.notifier.send_notification("✅ 局部补图成功", f"文章《{title}》图片已补全，继续发布流程")
            except Exception as e:
                self.notifier.send_notification("❌ 局部补图失败", f"第{attempt}次尝试: 补图时发生错误: {str(e)}")
                # 即使补图失败，也直接发布（封面图会用 Pollinations.ai 自动生成）
                print(f"[Attempt {attempt}] Image addition failed, proceeding to publish anyway")
        
        self.notifier.send_notification("✅ 副主编初审通过", f"文章《{title}》进入主编终审")
        
        # 【降本版】ChiefEditor 只查主旨 + 敏感词，零 Token 消耗
        chief_ok, chief_errors, error_types, word_count = self.chief_editor.full_check(content)
        if not chief_ok:
            error_msg = "\n".join(chief_errors)
            print(f"[Attempt {attempt}] Chief editor review failed: {chief_errors}, types: {error_types}")
            
            can_fix = False
            fix_attempts = 0
            max_fix_attempts = 2
            
            while not chief_ok and fix_attempts < max_fix_attempts:
                fix_attempts += 1
                
                if "depth" in error_types and "sensitive" not in error_types and "topic" not in error_types:
                    can_fix = True
                    print(f"[Attempt {attempt}] 内容深度不足({word_count}词)，尝试自动扩写修复...")
                    self.notifier.send_notification("📝 内容深度不足，启动自动扩写", f"文章《{title}》当前{word_count}词，需至少700词，启动AI扩写修复")
                    
                    try:
                        content = self.ai_engine.rewrite_post(content, topic, geo_region)
                        self.write_markdown(frontmatter, content, draft_path)
                        chief_ok, chief_errors, error_types, word_count = self.chief_editor.full_check(content)
                        
                        if chief_ok:
                            print(f"[Attempt {attempt}] 自动扩写成功!")
                            self.notifier.send_notification("✅ 自动扩写成功", f"文章《{title}》已扩展到{word_count}词，继续发布流程")
                        else:
                            print(f"[Attempt {attempt}] 自动扩写后仍未通过: {chief_errors}")
                    except Exception as e:
                        print(f"[Attempt {attempt}] 自动扩写失败: {e}")
                        break
                else:
                    break
            
            if not chief_ok:
                self.notifier.send_notification("❌ 主编终审驳回", f"第{attempt}次尝试: 文章《{title}》\n\n{error_msg}\n\n废弃旧选题，换新选题重试")
                
                for et in error_types:
                    error_hash = {
                        "depth": "content_depth_insufficient",
                        "sensitive": "sensitive_content_politics",
                        "topic": "topic_inappropriate"
                    }.get(et, "unknown_audit_error")
                    error_message = {
                        "depth": f"内容深度不足（{word_count}词，需至少700词）",
                        "sensitive": "正文含违规词汇",
                        "topic": "选题方向不符合要求"
                    }.get(et, error_msg)
                    self._record_audit_failure(error_hash, error_message, title)
                
                return {"success": False, "reason": "chief_editor_failed", "title": title, "draft_path": draft_path, "same_topic": False}
        
        post_slug = self.generate_slug(title)
        cover_url = self.move_to_posts(draft_path, title, post_slug)
        self.manifest.add_topic(topic, geo_region)
        self.manifest.increment_post_count()
        self.manifest.save()
        
        canonical_url = frontmatter["canonicalURL"]
        cover_msg = f"\n封面图: {cover_url}" if cover_url else ""
        self.notifier.send_notification("✅ 双审全通过，正式发布", f"文章《{title}》已成功发布！\n\n落地链接: {canonical_url}\n目标受众: {geo_region}\n尝试次数: {attempt}{cover_msg}")
        
        print(f"[Attempt {attempt}] Post published successfully: {canonical_url}")
        print(f"  Cover: {cover_url}")
        return {"success": True, "title": title, "canonical_url": canonical_url, "geo_region": geo_region, "cover_url": cover_url}
    
    def run(self):
        # 【社媒每日限额】如果今日社媒发布已达上限，就不再生成新文章
        is_limited, current_count, daily_limit = self.manifest.check_daily_social_limit()
        if is_limited:
            self.notifier.send_notification("⏸️ 社媒发布已达日限", f"今日社媒已发布 {current_count} 篇文章，达到每日上限 {daily_limit} 篇。为保证社媒曝光效果，今日不再生成新文章，明日自动恢复。")
            print(f"Social media limit reached: {current_count}/{daily_limit}. Exiting.")
            return
        
        max_posts = 22
        post_count = self.manifest.get_post_count()
        
        if post_count >= max_posts:
            self.notifier.send_notification("⚠️ 月度发文额度已满", f"本月已发布 {post_count} 篇文章，达到上限 {max_posts} 篇。自动生成已暂停，次月1日自动恢复。")
            print("Monthly post limit reached. Exiting.")
            return
        
        last_topic = None
        
        for attempt in range(1, self.max_retries + 1):
            result = self.run_single_post(attempt)
            
            if result["success"]:
                return
            
            if not result.get("same_topic", False):
                last_topic = None
            
            if attempt < self.max_retries:
                print(f"[Attempt {attempt}] 审核失败，准备第 {attempt + 1} 次重试...")
            else:
                DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
                draft_path = result.get("draft_path")
                if draft_path and draft_path.exists():
                    import shutil
                    final_draft = DRAFTS_DIR / draft_path.name
                    shutil.move(str(draft_path), str(final_draft))
                
                self.notifier.send_notification("❌ 当日3轮撰稿全部审核失败", f"经过 {self.max_retries} 次尝试后仍未能发布文章。稿件已存入 content/drafts/ 目录，当日停止生成。")
                print(f"All {self.max_retries} attempts failed. Post saved to drafts.")

if __name__ == "__main__":
    generator = BlogGenerator()
    generator.run()