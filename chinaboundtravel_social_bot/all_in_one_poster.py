import os
import json
import requests
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

class ZohoPoster:
    def __init__(self):
        self.client_id = os.getenv("ZOHO_CLIENT_ID")
        self.client_secret = os.getenv("ZOHO_CLIENT_SECRET")
        self.refresh_token = os.getenv("ZOHO_REFRESH_TOKEN")
        self.brand_id = os.getenv("ZOHO_BRAND_ID")
        self.queue_id = os.getenv("ZOHO_QUEUE_ID")
        self.access_token = self._get_access_token()
    
    def _get_access_token(self):
        if not self.client_id or not self.client_secret or not self.refresh_token:
            return None
        
        url = "https://accounts.zoho.com/oauth/v2/token"
        params = {
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token"
        }
        
        try:
            response = requests.post(url, params=params, timeout=30)
            if response.status_code == 200:
                return response.json()["access_token"]
        except Exception:
            pass
        return None
    
    def post_to_zoho(self, title, summary, url, image_url):
        if not self.access_token:
            return {"status": "skipped", "reason": "Zoho credentials not configured"}
        
        try:
            url = f"https://social.zoho.com/api/v1/posts"
            headers = {"Authorization": f"Bearer {self.access_token}"}
            
            payload = {
                "title": title,
                "content": f"{summary}\n\n{url}",
                "brand_id": self.brand_id,
                "queue_id": self.queue_id,
                "media_url": image_url,
                "platforms": ["facebook", "instagram", "twitter", "linkedin"]
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            if response.status_code == 200:
                return {"status": "success", "response": response.json()}
            else:
                return {"status": "failed", "error": response.text}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

class PinterestPoster:
    def __init__(self):
        self.token = os.getenv("PINTEREST_TOKEN")
        self.board_id = os.getenv("PINTEREST_BOARD_ID")
    
    def post_to_pinterest(self, title, summary, url, image_url):
        if not self.token or not self.board_id:
            return {"status": "skipped", "reason": "Pinterest credentials not configured"}
        
        try:
            url = "https://api.pinterest.com/v5/pins"
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "title": title,
                "description": f"{summary}\n\n{url}",
                "link": url,
                "board_id": self.board_id,
                "media_source": {
                    "source_type": "image_url",
                    "url": image_url
                }
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code == 201:
                return {"status": "success", "response": response.json()}
            else:
                return {"status": "failed", "error": response.text}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

class DelayForRedditPoster:
    def __init__(self):
        self.api_key = os.getenv("DFR_API_KEY")
        self.queue_id = os.getenv("DFR_QUEUE_ID")
    
    def post_to_reddit(self, title, summary, url):
        if not self.api_key or not self.queue_id:
            return {"status": "skipped", "reason": "DelayForReddit credentials not configured"}
        
        try:
            url = "https://api.delayforreddit.com/v1/posts"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            
            payload = {
                "title": title,
                "content": f"{summary}\n\n{url}",
                "queue_id": self.queue_id,
                "subreddit": "ChinaTravel",
                "post_type": "link"
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                return {"status": "success", "response": response.json()}
            else:
                return {"status": "failed", "error": response.text}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

class FeishuNotifier:
    @staticmethod
    def send_notification(title, content):
        url = os.getenv("FEISHU_WEBHOOK_URL")
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

class AllInOnePoster:
    def __init__(self):
        self.zoho = ZohoPoster()
        self.pinterest = PinterestPoster()
        self.reddit = DelayForRedditPoster()
        self.notifier = FeishuNotifier()
        self.logs_dir = BASE_DIR / "social_media_logs"
        self.logs_dir.mkdir(exist_ok=True)
    
    def get_latest_post(self):
        posts_dir = BASE_DIR / "content" / "posts"
        latest_post = None
        latest_date = None
        
        for filepath in posts_dir.glob("*.md"):
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            
            post_date = None
            for line in content.split('\n'):
                if line.startswith('date:'):
                    date_str = line.split(':', 1)[1].strip().strip('"').strip("'")
                    try:
                        post_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    except:
                        pass
                    break
            
            if post_date and (latest_date is None or post_date > latest_date):
                latest_date = post_date
                latest_post = filepath
        
        if latest_post:
            with open(latest_post, "r", encoding="utf-8") as f:
                content = f.read()
            
            title = ""
            summary = ""
            slug = latest_post.stem
            
            for line in content.split('\n'):
                if line.startswith('title:'):
                    title = line.split(':', 1)[1].strip().strip('"').strip("'")
                elif line.startswith('summary:'):
                    summary = line.split(':', 1)[1].strip().strip('"').strip("'")
            
            return {
                "title": title,
                "summary": summary,
                "slug": slug,
                "url": f"https://chinaboundtravel.com/posts/{slug}/",
                "image_url": f"https://chinaboundtravel.com/images/{slug}.webp"
            }
        return None
    
    def run(self):
        post = self.get_latest_post()
        if not post:
            print("No new post found")
            return
        
        print(f"Posting to social media: {post['title']}")
        
        results = []
        
        zoho_result = self.zoho.post_to_zoho(
            post["title"], post["summary"], post["url"], post["image_url"]
        )
        results.append({"platform": "Zoho (FB/IG/X/LN)", **zoho_result})
        
        pinterest_result = self.pinterest.post_to_pinterest(
            post["title"], post["summary"], post["url"], post["image_url"]
        )
        results.append({"platform": "Pinterest", **pinterest_result})
        
        reddit_result = self.reddit.post_to_reddit(
            post["title"], post["summary"], post["url"]
        )
        results.append({"platform": "DelayForReddit", **reddit_result})
        
        log_file = self.logs_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_social_publish.log"
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        
        success_count = sum(1 for r in results if r["status"] == "success")
        failed_count = sum(1 for r in results if r["status"] == "failed")
        skipped_count = sum(1 for r in results if r["status"] == "skipped")
        
        content = f"## 📢 全平台社媒发布结果\n\n"
        content += f"**文章**: {post['title']}\n"
        content += f"**链接**: {post['url']}\n\n"
        content += f"**成功**: {success_count} | **失败**: {failed_count} | **跳过**: {skipped_count}\n\n"
        
        for result in results:
            status_icon = "✅" if result["status"] == "success" else "❌" if result["status"] == "failed" else "⏭️"
            content += f"- {status_icon} {result['platform']}: {result.get('reason', result.get('error', ''))}\n"
        
        self.notifier.send_notification("社媒发布结果", content)
        
        print("Social publishing completed")

if __name__ == "__main__":
    poster = AllInOnePoster()
    poster.run()