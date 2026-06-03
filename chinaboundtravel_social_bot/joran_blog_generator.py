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
SITE_DOMAIN = "https://chinaboundtravel.com"

GEO_REGIONS = ["EU", "US", "AU"]
GEO_WEIGHTS = [40, 35, 25]

TOPIC_CATEGORIES = [
    "visa requirements",
    "best time to visit",
    "packing list",
    "safety tips",
    "transportation guide",
    "accommodation tips",
    "food recommendations",
    "cultural etiquette",
    "budget planning",
    "travel itineraries"
]

PERSONA_REGEX = r"(?i)(10\s*years|decade).*(living|based|chengdu|china)|california|californian"

class DeepSeekClient:
    def __init__(self):
        self.main_key = os.getenv("DEEPSEEK_API_KEY")
        self.backup_key = os.getenv("DEEPSEEK_BACKUP_API_KEY")
        self.url = "https://api.deepseek.com/v1/chat/completions"
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=8))
    def chat(self, messages, model="deepseek-chat", max_tokens=3000, temperature=0.7):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.main_key}"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        try:
            response = requests.post(self.url, headers=headers, json=payload, timeout=120)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception:
            if self.backup_key:
                headers["Authorization"] = f"Bearer {self.backup_key}"
                response = requests.post(self.url, headers=headers, json=payload, timeout=120)
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
            raise

class ManifestManager:
    def __init__(self):
        self.path = MANIFEST_PATH
        self.data = self._load()
    
    def _load(self):
        if self.path.exists():
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"month_post_count": 0, "last_reset_date": datetime.now().strftime("%Y-%m-01"), "history_topics": []}
    
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

class AIEngine:
    def __init__(self):
        self.client = DeepSeekClient()
    
    def generate_post(self, topic, geo_region):
        region_info = {
            "EU": "European travelers from countries like Germany, France, UK, Italy, Spain",
            "US": "American travelers from the United States, primarily California and major cities",
            "AU": "Australian and New Zealand travelers"
        }
        
        prompt = f"""You are Joran, a native Californian American who has been living in Chengdu, China for over 10 years. Write a travel blog post in FIRST PERSON about: {topic}

Target audience: {region_info[geo_region]}

Requirements:
1. Write in natural, conversational English
2. Include personal anecdotes about living in China for 10 years
3. Mention your California roots naturally
4. Minimum 750 words
5. Include at least 3 internal links to other China travel topics
6. Structure: Introduction, 3 main sections, Conclusion
7. Use markdown format with proper headings

DO NOT include any canonicalURL in the output. Just write the article content.
"""
        
        messages = [{"role": "user", "content": prompt}]
        return self.client.chat(messages, max_tokens=4000)
    
    def assistant_editor_review(self, content):
        prompt = f"""You are an AI Assistant Editor reviewing this blog post:

{content}

Check these criteria and return ONLY 'PASS' or 'FAIL':
1. Word count >= 750 words
2. Contains personal anecdotes about living in China for 10+ years OR mentions California roots
3. Has proper structure: Introduction, at least 3 main sections, Conclusion
4. Contains at least 3 internal links (e.g., /posts/xxx/)
5. No political sensitive content
6. Topic stays relevant to China travel

If any criteria fail, return 'FAIL'. Otherwise return 'PASS'."""
        
        messages = [{"role": "user", "content": prompt}]
        result = self.client.chat(messages, max_tokens=100)
        return "PASS" in result.upper()
    
    def rewrite_post(self, content, feedback="Make it more engaging and include more personal stories about living in China"):
        prompt = f"""Rewrite this blog post to improve quality:

{content}

Instructions:
1. {feedback}
2. Maintain original topic and key information
3. Keep it natural and conversational
4. Ensure it's at least 750 words
5. Add personal anecdotes about living in China for 10 years
6. Include California references naturally
7. Keep markdown format"""
        
        messages = [{"role": "user", "content": prompt}]
        return self.client.chat(messages, max_tokens=4000)
    
    def chief_editor_review(self, content):
        prompt = f"""You are the Chief AI Editor. Review this blog post for final approval:

{content}

Check these final criteria and return ONLY 'PASS' or 'FAIL':
1. Content is factually accurate about China
2. No sensitive political content
3. External links (if any) point only to official government sites (consulates, railways, tourism boards)
4. Geographical information matches target region
5. Meta description is complete and compelling
6. Temporal logic is consistent

If any criteria fail, return 'FAIL'. Otherwise return 'PASS'."""
        
        messages = [{"role": "user", "content": prompt}]
        result = self.client.chat(messages, max_tokens=100)
        return "PASS" in result.upper()
    
    def persona_check(self, content):
        if re.search(PERSONA_REGEX, content):
            return True
        
        prompt = f"""Does this text sound like it was written by a native Californian who has lived in China for 10 years? Answer ONLY YES or NO.

{content[:2000]}"""
        
        messages = [{"role": "user", "content": prompt}]
        result = self.client.chat(messages, max_tokens=50)
        return "YES" in result.upper()

class FeishuNotifier:
    @staticmethod
    def send_notification(title, content, webhook_url=None):
        url = webhook_url or os.getenv("FEISHU_WEBHOOK_URL")
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

class BlogGenerator:
    def __init__(self):
        self.manifest = ManifestManager()
        self.ai_engine = AIEngine()
        self.notifier = FeishuNotifier()
    
    def select_topic(self):
        geo_region = random.choices(GEO_REGIONS, weights=GEO_WEIGHTS)[0]
        
        for _ in range(10):
            topic = random.choice(TOPIC_CATEGORIES)
            if not self.manifest.check_topic_repeat(topic, geo_region):
                return topic, geo_region
        
        return random.choice(TOPIC_CATEGORIES), geo_region
    
    def generate_slug(self, title):
        slug = re.sub(r'[^a-z0-9\s-]', '', title.lower())
        slug = re.sub(r'[\s-]+', '-', slug).strip('-')
        return slug
    
    def create_frontmatter(self, title, geo_region):
        slug = self.generate_slug(title)
        date = datetime.now().strftime("%Y-%m-%dT10:00:00+08:00")
        
        tags = ["ChinaTravel", "TravelGuide"]
        if geo_region == "EU":
            tags.append("EuropeToChina")
        elif geo_region == "US":
            tags.append("USToChina")
        elif geo_region == "AU":
            tags.append("AustraliaToChina")
        
        return {
            "title": title,
            "date": date,
            "author": "Joran",
            "slug": slug,
            "tags": tags,
            "categories": ["China"],
            "geo": geo_region,
            "draft": "true",
            "audit_status": "pending",
            "summary": f"Complete guide about {title.lower()} for travelers visiting China.",
            "description": f"Everything you need to know about {title.lower()} when traveling to China.",
            "canonicalURL": f"{SITE_DOMAIN}/posts/{slug}/"
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
    
    def move_to_posts(self, draft_path):
        filename = draft_path.name
        post_path = POSTS_DIR / filename
        
        with open(draft_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        content = content.replace('draft: "true"', 'draft: "false"')
        content = content.replace('audit_status: "pending"', 'audit_status: "pass2"')
        
        with open(post_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        draft_path.unlink()
    
    def run(self):
        max_posts = 22
        post_count = self.manifest.get_post_count()
        
        if post_count >= max_posts:
            self.notifier.send_notification(
                "⚠️ 月度发文额度已满",
                f"本月已发布 {post_count} 篇文章，达到上限 {max_posts} 篇。自动生成已暂停，次月1日自动恢复。"
            )
            print("Monthly post limit reached. Exiting.")
            return
        
        topic, geo_region = self.select_topic()
        print(f"Selected topic: {topic} for {geo_region}")
        
        try:
            content = self.ai_engine.generate_post(topic, geo_region)
        except Exception as e:
            self.notifier.send_notification(
                "❌ AI生成失败",
                f"文章生成时发生错误: {str(e)}"
            )
            raise
        
        title = re.search(r'^#\s+(.+)', content, re.MULTILINE)
        title = title.group(1) if title else f"{topic.title()} Guide"
        
        DRAFT_DIR.mkdir(parents=True, exist_ok=True)
        draft_path = DRAFT_DIR / f"{datetime.now().strftime('%Y-%m-%d')}-{self.generate_slug(title)}.md"
        
        frontmatter = self.create_frontmatter(title, geo_region)
        self.write_markdown(frontmatter, content, draft_path)
        
        persona_ok = self.ai_engine.persona_check(content)
        if not persona_ok:
            self.notifier.send_notification(
                "❌ 人设校验失败",
                f"文章《{title}》未通过Joran人设校验，已存入草稿。"
            )
            print("Persona check failed. Post saved to draft.")
            return
        
        review1_pass = self.ai_engine.assistant_editor_review(content)
        
        if not review1_pass:
            print("Assistant editor review failed, attempting rewrite...")
            content = self.ai_engine.rewrite_post(content)
            review1_pass = self.ai_engine.assistant_editor_review(content)
        
        if not review1_pass:
            self.notifier.send_notification(
                "❌ 初审未通过",
                f"文章《{title}》经过一次改写后仍未通过初审，已存入草稿。"
            )
            print("Assistant editor review failed after rewrite. Post saved to draft.")
            return
        
        review2_pass = self.ai_engine.chief_editor_review(content)
        
        if not review2_pass:
            self.notifier.send_notification(
                "❌ 终审未通过",
                f"文章《{title}》未通过终审，已存入草稿。"
            )
            print("Chief editor review failed. Post saved to draft.")
            return
        
        self.move_to_posts(draft_path)
        self.manifest.add_topic(topic, geo_region)
        self.manifest.increment_post_count()
        self.manifest.save()
        
        canonical_url = frontmatter["canonicalURL"]
        self.notifier.send_notification(
            "✅ 新文章上线",
            f"文章《{title}》已成功发布！\n\n落地链接: {canonical_url}\n目标受众: {geo_region}"
        )
        
        print(f"Post published successfully: {canonical_url}")

if __name__ == "__main__":
    generator = BlogGenerator()
    generator.run()