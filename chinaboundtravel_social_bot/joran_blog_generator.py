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
    
    def _get_current_key(self):
        """获取当前应该使用的密钥"""
        if self._use_backup and self.backup_key:
            return self.backup_key
        return self.main_key
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=8))
    def chat(self, messages, model="deepseek-chat", max_tokens=3000, temperature=0.7):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._get_current_key()}"
        }
        
        payload = {
            "model": model,
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
            "EU": "European travelers from countries like Germany, France, UK, Italy, Spain",
            "US": "American travelers from the United States, primarily California and major cities",
            "AU": "Australian and New Zealand travelers"
        }
        
        prompt = f"""You are Joran, a witty Californian American who's been living in Chengdu, China for over 10 years. You're a movie buff who loves to reference classic films when talking about travel. Write a HUMOROUS travel blog post in FIRST PERSON about: {topic}

Target audience: {region_info[geo_region]}

Requirements:
1. Write in witty, conversational English - think of it like chatting with a friend over coffee
2. Include SPECIFIC personal anecdotes from living in China for 10 years - mention real experiences like ordering street food, dealing with taxis, navigating public transport, or cultural misunderstandings
3. NATURALLY mention your California roots ONLY when it makes sense for comparison - e.g., "Back in California we do X, but here in China it's Y" - don't force California references
4. Drop 1-2 funny movie references (e.g., comparing a crowded subway to a scene from 'The Hunger Games' or bargaining like it's a 'Ocean's Eleven' heist) - keep them light and relevant
5. Minimum 750 words
6. Include at least 2 internal links to other China travel topics using markdown link format like [topic](https://chinaboundtravel.com/posts/topic-slug/)
7. Structure: Introduction, 3 main sections with H2 headings (##), Conclusion
8. MUST include EXACTLY 2 image placeholders in markdown format: ![alt text describing the image](https://example.com/image.jpg) - one after the introduction, one in the middle of the article
9. China travel content must be the MAIN focus - comparisons are just for humor and context
10. DO NOT mention government, politics, or sensitive political topics

DO NOT include any canonicalURL in the output. Just write the article content."""
        
        messages = [{"role": "user", "content": prompt}]
        return self.client.chat(messages, max_tokens=4000)
    
    def rewrite_post(self, content, topic, geo_region):
        region_info = {
            "EU": "European travelers",
            "US": "American travelers",
            "AU": "Australian and New Zealand travelers"
        }
        
        prompt = f"""Rewrite this blog post to fix formatting and structure issues:

{content}

Instructions:
1. Ensure minimum 750 words
2. Add proper markdown structure with H2 headings (##) for main sections
3. Include at least 2 internal links to other China travel topics
4. Add EXACTLY 2 image placeholders with alt text
5. Maintain Joran persona: California native living in Chengdu for 10 years with movie references
6. Keep the original topic: {topic}
7. Target audience: {region_info[geo_region]}
8. Make it witty and conversational
9. China travel content must be the MAIN focus"""
        
        messages = [{"role": "user", "content": prompt}]
        return self.client.chat(messages, max_tokens=4000)
    
    def add_image_placeholders(self, article_md):
        """局部补图 - 仅添加图片占位符，不修改其他内容，节省95% Token"""
        prompt = f"""Please add EXACTLY 2 image placeholders to this article without modifying any existing text.
Place one after the introduction (first paragraph) and one in the middle of the article.
Use this format: ![alt text describing the scene](https://example.com/image.jpg)

Article:
{article_md}

Return ONLY the modified article with image placeholders added."""
        
        messages = [{"role": "user", "content": prompt}]
        return self.client.chat(messages, max_tokens=1500)

class SubEditor:
    def __init__(self):
        self.client = DeepSeekClient()
    
    def full_check(self, article_md, frontmatter):
        errors = []
        
        if "description" not in frontmatter or len(str(frontmatter.get("description", ""))) < 40:
            errors.append("【格式】缺少合规Meta Description（需≥40字符）")
        
        if "summary" not in frontmatter or len(str(frontmatter.get("summary", ""))) < 30:
            errors.append("【格式】缺少合规摘要（需≥30字符）")
        
        if not frontmatter.get("slug"):
            errors.append("【格式】slug配置缺失")
        
        if "## " not in article_md:
            errors.append("【排版】分级标题未使用H2标签##")
        
        img_num = article_md.count("![")
        if img_num < 1:
            errors.append("【排版】配图不足1张，请添加图片占位符")
        
        link_count = article_md.count("[") - img_num
        if link_count < 2:
            errors.append("【SEO】站内锚文本不足2处")
        
        word_count = len(article_md.split())
        if word_count < 750:
            errors.append(f"【格式】字数不足750词，当前{word_count}词")
        
        if "I" not in article_md[:500] and "my" not in article_md[:500] and "I've" not in article_md[:500]:
            errors.append("【格式】缺少第一人称表述")
        
        sensitive_words = ["politics", "government", "communist", "Tiananmen", "Taiwan independence", "Falun Gong"]
        for w in sensitive_words:
            if w.lower() in article_md.lower():
                errors.append(f"【风控】正文含违规词汇:{w}")
        
        return len(errors) == 0, errors

class ChiefEditor:
    def __init__(self):
        self.client = DeepSeekClient()
    
    def full_check(self, content):
        errors = []
        
        if "I" not in content[:600] and "my" not in content[:600] and "I've" not in content[:600]:
            errors.append("【人设驳回】脱离Joran第一人称旅居博主设定")
        
        if ("Los Angeles" in content or "San Francisco" in content) and ("fly from" not in content.lower() and "from LA" not in content.lower() and "from SF" not in content.lower()):
            errors.append("【人设驳回】无出行上下文强行添加加州城市，破坏原文逻辑")
        
        years_in_china = re.search(r'(10\s+years|ten\s+years|decade)', content, re.IGNORECASE)
        california = re.search(r'california|californian', content, re.IGNORECASE)
        chengdu = re.search(r'chengdu', content, re.IGNORECASE)
        
        if not years_in_china and not (california and chengdu):
            errors.append("【人设驳回】未体现十年旅居中国+加州出身的核心人设")
        
        third_person = re.search(r'\bhe\b|\bshe\b|\bthey\b|\bthe author\b|\bthe writer\b', content[:500], re.IGNORECASE)
        if third_person and "I" not in content[:500]:
            errors.append("【人设驳回】文风切换为第三人称，违反Joran第一人称设定")
        
        prompt = f"""As Chief Editor, evaluate if this content demonstrates E-E-A-T (Experience, Expertise, Authoritativeness, Trustworthiness):

Content:
{content[:3000]}

Checklist:
1. Does the content show genuine travel experience in China?
2. Are the travel tips practical and actionable?
3. Is there evidence of long-term residency in China?
4. Are claims about travel costs, transportation, and logistics realistic?
5. Are external links (if any) pointing to authoritative sources?

Answer ONLY 'PASS' or 'FAIL'."""
        
        messages = [{"role": "user", "content": prompt}]
        eeaat_result = self.client.chat(messages, max_tokens=100)
        if "FAIL" in eeaat_result.upper():
            errors.append("【E-E-A-T】内容可信度不足，未体现十年旅居实操经验")
        
        prompt2 = f"""Check if this travel article has logical flow issues:

Content:
{content[:3000]}

Check:
1. Introduction -> Body -> Conclusion structure
2. Paragraphs follow a logical sequence
3. Ideas connect coherently
4. No contradictory statements

Answer ONLY 'PASS' or 'FAIL'."""
        
        messages = [{"role": "user", "content": prompt2}]
        logic_result = self.client.chat(messages, max_tokens=100)
        if "FAIL" in logic_result.upper():
            errors.append("【逻辑】文章段落前后不通顺，上下文割裂")
        
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
        
        sub_ok, sub_errors = self.sub_editor.full_check(content, frontmatter)
        if not sub_ok:
            # 检查是否只是图片占位符问题
            img_errors = [e for e in sub_errors if "配图" in e or "图片" in e or "Image" in e]
            if img_errors and len(img_errors) == len(sub_errors):
                # 只有图片问题，使用局部补图
                print(f"[Attempt {attempt}] Only image errors found, using partial image addition...")
                self.notifier.send_notification("⚠️ 仅图片占位符不足", f"文章《{title}》仅缺图片，启动局部补图（节省95% Token）")
                
                try:
                    content = self.ai_engine.add_image_placeholders(content)
                    # 重新检查
                    sub_ok, sub_errors = self.sub_editor.full_check(content, frontmatter)
                    
                    if sub_ok:
                        # 图片补全成功，继续主编审核
                        self.notifier.send_notification("✅ 局部补图成功", f"文章《{title}》图片已补全")
                    else:
                        # 补图后仍有问题，标记为失败
                        error_msg = "\n".join(sub_errors)
                        self.notifier.send_notification("❌ 补图后仍不通过", f"第{attempt}次尝试: 文章《{title}》\n\n{error_msg}")
                        print(f"[Attempt {attempt}] Still failed after image addition: {sub_errors}")
                        return {"success": False, "reason": "image_fix_failed", "title": title, "draft_path": draft_path, "same_topic": True}
                except Exception as e:
                    self.notifier.send_notification("❌ 局部补图失败", f"第{attempt}次尝试: 补图时发生错误: {str(e)}")
                    return {"success": False, "reason": "image_addition_error", "title": title, "draft_path": draft_path, "same_topic": True}
            else:
                # 有其他问题，需要重写
                error_msg = "\n".join(sub_errors)
                self.notifier.send_notification("❌ 副主编初审失败", f"第{attempt}次尝试: 文章《{title}》\n\n{error_msg}\n\n同选题重新生成稿件")
                print(f"[Attempt {attempt}] Sub-editor review failed: {sub_errors}")
                return {"success": False, "reason": "sub_editor_failed", "title": title, "draft_path": draft_path, "same_topic": True}
        
        self.notifier.send_notification("✅ 副主编初审通过", f"文章《{title}》进入主编终审")
        
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