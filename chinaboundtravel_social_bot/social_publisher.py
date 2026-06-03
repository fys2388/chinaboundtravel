import os
import json
import requests
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

class SocialPublisher:
    def __init__(self):
        self.pinterest_api_key = os.getenv("PINTEREST_API_KEY")
        self.pinterest_token = os.getenv("PINTEREST_ACCESS_TOKEN")
        self.facebook_token = os.getenv("FACEBOOK_ACCESS_TOKEN")
        self.feishu_webhook = os.getenv("FEISHU_WEBHOOK_URL")
        self.logs_dir = BASE_DIR / "social_media_logs"
        self.logs_dir.mkdir(exist_ok=True)
    
    def get_new_posts(self):
        posts_dir = BASE_DIR / "content" / "posts"
        posts = []
        
        manifest_path = BASE_DIR / "manifest.json"
        if manifest_path.exists():
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            last_publish_time = manifest.get("last_social_publish", "2020-01-01")
        else:
            last_publish_time = "2020-01-01"
        
        for filepath in posts_dir.glob("*.md"):
            mtime = filepath.stat().st_mtime
            mtime_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            if mtime_str > last_publish_time:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                
                title = ""
                geo_region = "US"
                slug = filepath.stem
                
                for line in content.split('\n'):
                    if line.startswith('title:'):
                        title = line.split(':', 1)[1].strip().strip('"')
                    elif line.startswith('geo:'):
                        geo_region = line.split(':', 1)[1].strip().strip('"')
                
                posts.append({
                    "title": title,
                    "slug": slug,
                    "geo_region": geo_region,
                    "url": f"https://chinaboundtravel.com/posts/{slug}/",
                    "filepath": str(filepath)
                })
        
        return posts
    
    def publish_to_pinterest(self, post):
        if not self.pinterest_api_key or not self.pinterest_token:
            return {"status": "skipped", "reason": "Pinterest credentials not configured"}
        
        try:
            url = "https://api.pinterest.com/v5/pins"
            headers = {
                "Authorization": f"Bearer {self.pinterest_token}",
                "Content-Type": "application/json"
            }
            
            body = {
                "title": post["title"],
                "description": f"Read the full guide: {post['title']}",
                "link": post["url"],
                "board_id": self._get_board_id(post["geo_region"]),
                "media_source": {
                    "source_type": "image_url",
                    "url": f"https://chinaboundtravel.com/images/{post['slug']}.jpg"
                }
            }
            
            response = requests.post(url, headers=headers, json=body, timeout=30)
            if response.status_code == 201:
                return {"status": "success", "response": response.json()}
            else:
                return {"status": "failed", "error": response.text}
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    def _get_board_id(self, geo_region):
        boards = {
            "EU": "1234567890",
            "US": "0987654321",
            "AU": "1122334455"
        }
        return boards.get(geo_region, boards["US"])
    
    def publish_to_facebook(self, post):
        if not self.facebook_token:
            return {"status": "skipped", "reason": "Facebook credentials not configured"}
        
        try:
            url = "https://graph.facebook.com/v19.0/me/feed"
            params = {
                "access_token": self.facebook_token,
                "message": f"New post: {post['title']}\n{post['url']}",
                "link": post["url"]
            }
            
            response = requests.post(url, params=params, timeout=30)
            if response.status_code == 200:
                return {"status": "success", "response": response.json()}
            else:
                return {"status": "failed", "error": response.text}
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    def send_feishu_notification(self, results):
        if not self.feishu_webhook:
            return
        
        success_count = sum(1 for r in results if r["status"] == "success")
        failed_count = sum(1 for r in results if r["status"] == "failed")
        
        content = f"## 📢 社媒发布结果\n\n"
        content += f"**成功**: {success_count} | **失败**: {failed_count}\n\n"
        
        for result in results:
            status_icon = "✅" if result["status"] == "success" else "❌" if result["status"] == "failed" else "⏭️"
            content += f"- {status_icon} {result['platform']}: {result['title']} ({result.get('reason', result.get('error', ''))})\n"
        
        try:
            payload = {
                "msg_type": "post",
                "content": {
                    "post": {
                        "zh_cn": {
                            "title": "社媒发布通知",
                            "content": [[{"tag": "text", "text": content}]]
                        }
                    }
                }
            }
            requests.post(self.feishu_webhook, json=payload, timeout=30)
        except Exception:
            pass
    
    def save_log(self, results):
        log_file = self.logs_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_social_publish.log"
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
    
    def update_manifest(self):
        manifest_path = BASE_DIR / "manifest.json"
        if manifest_path.exists():
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        else:
            manifest = {"month_post_count": 0, "last_reset_date": datetime.now().strftime("%Y-%m-01"), "history_topics": []}
        
        manifest["last_social_publish"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
    
    def run(self):
        posts = self.get_new_posts()
        if not posts:
            print("No new posts to publish")
            return
        
        results = []
        
        for post in posts:
            print(f"Publishing: {post['title']}")
            
            pinterest_result = self.publish_to_pinterest(post)
            results.append({
                "platform": "Pinterest",
                "title": post["title"],
                **pinterest_result
            })
            
            facebook_result = self.publish_to_facebook(post)
            results.append({
                "platform": "Facebook",
                "title": post["title"],
                **facebook_result
            })
        
        self.save_log(results)
        self.send_feishu_notification(results)
        self.update_manifest()
        
        print("Social publishing completed")

if __name__ == "__main__":
    publisher = SocialPublisher()
    publisher.run()