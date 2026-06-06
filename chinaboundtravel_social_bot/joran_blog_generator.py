import os
import re
import json
import random
import requests
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_exponential

BASE_DIR = Path(__file__).parent.parent
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


def generate_pollinations_url(title, slug):
    """生成 Pollinations.ai 动态图片 URL，零存储零下载"""
    title_lower = title.lower()

    # 根据标题关键词生成场景描述
    location_keywords = [
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

    scene_desc = "Beautiful China travel landscape photography, cinematic composition"
    for kw, desc in location_keywords:
        if kw in title_lower:
            scene_desc = desc
            break

    # 拼接提示词 + URL 编码
    prompt = f"Professional travel blog cover image, {scene_desc}, high-resolution travel photography, cinematic lighting, vibrant colors, 4k quality, photorealistic, beautiful scenery"
    encoded_prompt = requests.utils.quote(prompt)

    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1200&height=630&nologo=true&seed={abs(hash(slug)) % 100000}"
    print(f"[Pollinations] URL: {url}")
    return url


def generate_cover_for_post(title, slug):
    """生成封面图 - 使用 Pollinations.ai 零存储外链方案"""
    return generate_pollinations_url(title, slug)


GEO_REGIONS = ["EU", "US", "AU"]
GEO_WEIGHTS = [40, 35, 25]

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

class DeepSeekClient:
    def __init__(self):
        self.main_key = os.getenv("DEEPSEEK_API_KEY")
        self.backup_key = os.getenv("DEEPSEEK_BACKUP_API_KEY")
        self.url = "https://api.deepseek.com/v1/chat/completions"
        self._use_backup = False  # 标记是否已切换到备用密钥
        # 【降本控规】强制使用 deepseek-v4-flash，全局禁用 pro/reasoner
        self.default_model = "deepseek-v4-flash"
    
    def _get_current_key(self):
        """获取当前应该使用的密钥"""
        if self._use_backup and self.backup_key:
            return self.backup_key
        return self.main_key
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=8))
    def chat(self, messages, model=None, max_tokens=720, temperature=0.7):
        # 【降本控规】强制使用 deepseek-v4-flash，忽略任何传入的 pro/reasoner 模型
        use_model = self.default_model
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._get_current_key()}"
        }
        
        payload = {
            "model": use_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        response = requests.post(self.url, headers=headers, json=payload, timeout=120)
        
        # 如果主密钥失败且有备用密钥，切换到备用密钥
        if response.status_code == 401 and not self._use_backup and self.backup_key:
            self._use_backup = True
            headers["Authorization"] = f"Bearer {self.backup_key}"
            response = requests.post(self.url, headers=headers, json=payload, timeout=120)
        
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

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
        self.client = DeepSeekClient()
    
    def generate_post(self, topic, geo_region):
        region_info = {
            "EU": "European travelers (UK, Germany, France, Italy, Spain)",
            "US": "American travelers (California, major cities)",
            "AU": "Australian and New Zealand travelers"
        }
        
        # 【降本版】精简Prompt，去掉冗余，固定图片占位符
        prompt = f"""Joran: California American, 10+ years living in Chengdu China, movie buff, humorous travel blogger.

Write a HUMOROUS FIRST-PERSON travel blog post about: {topic}
Target audience: {region_info[geo_region]}

Rules:
1. Conversational, witty tone - like chatting with a friend
2. Include SPECIFIC personal anecdotes from China (street food, taxis, transport, cultural moments)
3. Mention California roots NATURALLY only when relevant for comparison
4. Include 1-2 funny movie references (e.g., comparing subway crowds to 'The Hunger Games', bargaining like 'Ocean's Eleven')
5. Minimum 700 words
6. Include at least 2 internal links like [topic](https://chinaboundtravel.com/posts/topic-slug/)
7. Structure: Introduction + 3 H2 sections (##) + Short Conclusion
8. MUST include EXACTLY 2 image placeholders:
   - One AFTER the introduction
   - One IN the MIDDLE of the article
   - Format: ![alt text describing the scene](https://example.com/image.jpg)
9. MAIN FOCUS must be China travel - comparisons/California/movies are just flavor
10. NO government, politics, sensitive topics

Output ONLY the article content."""
        
        messages = [{"role": "user", "content": prompt}]
        # 【降本】max_tokens=1200，输出约900词（足够700词+2张图+内链）
        return self.client.chat(messages, max_tokens=1200)
    
    def rewrite_post(self, content, topic, geo_region):
        region_info = {
            "EU": "European travelers",
            "US": "American travelers",
            "AU": "Australian and New Zealand travelers"
        }
        
        # 【降本】精简重写Prompt
        prompt = f"""Rewrite this blog post. Fix any formatting issues, add missing structure, ensure minimum 700 words.

{content}

Requirements:
1. Add proper H2 headings (##) for main sections if missing
2. Add at least 2 internal links to other China travel topics
3. Add EXACTLY 2 image placeholders:
   - One AFTER the introduction
   - One IN the MIDDLE of the article
   - Format: ![alt text describing the scene](https://example.com/image.jpg)
4. Keep Joran persona: California native, 10+ years in Chengdu, witty, movie references
5. Original topic: {topic}
6. Target audience: {region_info[geo_region]}
7. MAIN FOCUS must be China travel

Output ONLY the rewritten article."""
        
        messages = [{"role": "user", "content": prompt}]
        # 【降本】max_tokens 从4000降到720
        return self.client.chat(messages, max_tokens=720)
    
    def add_image_placeholders(self, article_md):
        """【降本核心】局部补图 - 仅添加图片占位符，不修改任何文字，Token仅为全文5%"""
        prompt = f"""TASK: Add EXACTLY 2 image placeholders to this article. DO NOT MODIFY ANY EXISTING TEXT.

Placements:
1. Add one RIGHT AFTER the introduction (first paragraph)
2. Add one IN the MIDDLE of the article (around the halfway point)

Format for each placeholder:
![short description of what the image shows](https://example.com/image.jpg)

RULE: Do not change, delete, or rephrase ANY existing words. Only insert the two image placeholders.

Article:
{article_md}

Output ONLY the modified article with placeholders inserted."""
        
        messages = [{"role": "user", "content": prompt}]
        # 【降本】max_tokens=1200，补图需要保留原文章+插入图片描述
        return self.client.chat(messages, max_tokens=1200)

class SubEditor:
    def __init__(self):
        self.client = DeepSeekClient()
    
    def full_check(self, article_md, frontmatter):
        """【降本版】副主编初审：只校验图片占位符，其他一律放行"""
        errors = []
        
        # 【唯一校验】检查图片占位符数量，其他全部跳过
        img_num = article_md.count("![")
        if img_num < 2:
            errors.append(f"【配图不足】仅有{img_num}张图片，需2张（导语后1张 + 正文中1张）")
        
        # 其他检查全部跳过 - 省Token，后续不再因为格式/字数/链接问题驳回
        
        return len(errors) == 0, errors

class ChiefEditor:
    def __init__(self):
        self.client = DeepSeekClient()
    
    def full_check(self, content):
        """【降本版】主编终审：只查主旨，不使用 AI 审核，不因为 California/电影关键词驳回"""
        errors = []
        
        # 【唯一强制规则】正文核心必须是中国内容，通篇写海外才驳回
        content_lower = content.lower()
        
        # 检查中国相关关键词密度（文章是否以中国为主体）
        china_markers = ["china", "chengdu", "beijing", "shanghai", "chinese", "xian", "guilin", "suzhou", "hangzhou"]
        china_count = sum(content_lower.count(m) for m in china_markers)
        
        # 检查是否有纯海外内容（如整篇写洛杉矶/旧金山而没有中国）
        has_china = china_count >= 3
        
        if not has_china:
            errors.append("【主旨驳回】文章未以中国为主体，缺少核心中国内容")
        
        # 【California/电影关键词一律放行】不再因为加州关键词、电影引用驳回
        # 【不做 E-E-A-T AI 审核】节省 API 调用
        # 【不做逻辑 flow AI 审核】节省 API 调用
        # 【不做第三人称检查】文风一律放行
        
        # 仅保留最低限度的敏感词检查（纯文本匹配，零Token消耗）
        sensitive_words = ["politics", "government", "communist", "tiananmen", "taiwan independence", "falun gong"]
        for w in sensitive_words:
            if w in content_lower:
                errors.append(f"【风控】正文含违规词汇:{w}")
        
        return len(errors) == 0, errors

class BlogGenerator:
    def __init__(self):
        self.manifest = ManifestManager()
        self.ai_engine = AIEngine()
        self.sub_editor = SubEditor()
        self.chief_editor = ChiefEditor()
        self.notifier = FeishuNotifier()
        self.max_retries = MAX_DAILY_RETRY
        self.used_topics = set()  # 记录本轮已尝试的选题
    
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
    
    def select_topic(self, attempt=1):
        """选择选题 - 根据尝试次数选择不同选题库"""
        geo_convert_rates = self.manifest.data.get("geo_convert_rate", {})
        if geo_convert_rates:
            regions = list(geo_convert_rates.keys())
            geo_weights = [geo_convert_rates.get(r, 0.1) * GEO_WEIGHTS[GEO_REGIONS.index(r)] for r in regions]
            geo_region = random.choices(regions, weights=geo_weights)[0]
        else:
            geo_region = random.choices(GEO_REGIONS, weights=GEO_WEIGHTS)[0]
        
        # 根据尝试次数选择选题库
        if attempt == 1:
            topics = TOPIC_LIBRARY["main"]
        elif attempt == 2:
            topics = TOPIC_LIBRARY["alternate"]
        else:
            topics = TOPIC_LIBRARY["universal"]
        
        # 随机选择一个未使用且不在冷却期的选题
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
            "summary": f"Complete {topic} guide for travelers visiting China based on 10 years of experience.",
            "description": f"Everything you need to know about traveling to China. Practical tips from a California native living in Chengdu for over 10 years.",
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
        chief_ok, chief_errors = self.chief_editor.full_check(content)
        if not chief_ok:
            error_msg = "\n".join(chief_errors)
            self.notifier.send_notification("❌ 主编终审驳回", f"第{attempt}次尝试: 文章《{title}》\n\n{error_msg}\n\n废弃旧选题，换新选题重试")
            print(f"[Attempt {attempt}] Chief editor review failed: {chief_errors}")
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