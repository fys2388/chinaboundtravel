import os
import json
import requests
from typing import Dict, Optional
from config import Config

class YouTubeUploader:
    def __init__(self):
        self.client_secret = Config.GOOGLE_CLIENT_SECRET
        self.api_key = Config.GOOGLE_API_KEY
    
    def upload(self, video_path: str, title: str, description: str, tags: list, privacy_status: str = "public") -> str:
        if not self.client_secret:
            print("YouTube: No client secret configured")
            return ""
        
        try:
            print(f"YouTube: Uploading {video_path}")
            
            with open(video_path, "rb") as f:
                video_data = f.read()
            
            print("YouTube: Video upload not fully implemented - requires OAuth2 flow")
            print(f"YouTube: Title: {title}")
            print(f"YouTube: Tags: {', '.join(tags)}")
            
            return f"https://www.youtube.com/watch?v=upload_pending"
        except Exception as e:
            print(f"YouTube upload error: {e}")
            return ""

class TikTokUploader:
    def __init__(self):
        self.client_key = Config.TIKTOK_CLIENT_KEY
        self.client_secret = Config.TIKTOK_CLIENT_SECRET
    
    def upload(self, video_path: str, title: str, description: str, tags: list) -> str:
        if not self.client_key or not self.client_secret:
            print("TikTok: No credentials configured")
            return ""
        
        try:
            print(f"TikTok: Uploading {video_path}")
            print(f"TikTok: Title: {title}")
            print(f"TikTok: Tags: {', '.join(tags)}")
            
            return f"https://www.tiktok.com/@chinaboundtravel/video/upload_pending"
        except Exception as e:
            print(f"TikTok upload error: {e}")
            return ""

class BufferUploader:
    def __init__(self):
        self.access_token = Config.BUFFER_ACCESS_TOKEN
        self.graphql_url = "https://api.buffer.com"
        self.rest_url = "https://api.bufferapp.com/1"
        self.channels = []
        self.organization_id = None
    
    def graphql_request(self, query: str, variables: dict = {}) -> dict:
        try:
            headers = {"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"}
            response = requests.post(self.graphql_url, json={"query": query, "variables": variables}, headers=headers, timeout=15)
            return response.json()
        except Exception as e:
            print(f"Buffer GraphQL request error: {e}")
            return {"errors": [{"message": str(e)}]}
    
    def get_organization_id(self) -> str:
        if self.organization_id:
            return self.organization_id
        
        query = """
        query GetAccount {
            account {
                organizations {
                    id
                    name
                }
            }
        }
        """
        result = self.graphql_request(query)
        
        if "errors" in result:
            print(f"Buffer get_organization_id error: {result['errors']}")
            return ""
        
        orgs = result.get("data", {}).get("account", {}).get("organizations", [])
        if orgs:
            self.organization_id = orgs[0]["id"]
            print(f"Buffer: Found organization - {orgs[0]['name']}: {self.organization_id}")
            return self.organization_id
        return ""
    
    def get_account_channels(self) -> list:
        if not self.access_token:
            return []
        
        org_id = self.get_organization_id()
        if not org_id:
            print("Buffer: Could not find organization ID")
            return []
        
        query = f"""
        query GetChannels {{
            channels(input: {{ organizationId: "{org_id}" }}) {{
                id
                name
                service
                avatar
            }}
        }}
        """
        
        result = self.graphql_request(query)
        
        if "errors" in result:
            print(f"Buffer channels error: {result['errors']}")
            return []
        
        self.channels = result.get("data", {}).get("channels", [])
        return self.channels
    
    def upload_file(self, file_path: str) -> str:
        if not self.access_token:
            return ""
        
        try:
            url = f"{self.rest_url}/upload.json"
            headers = {"Authorization": f"Bearer {self.access_token}"}
            
            with open(file_path, "rb") as f:
                files = {"file": (os.path.basename(file_path), f, "video/mp4")}
                response = requests.post(url, headers=headers, files=files, timeout=60)
            
            print(f"Buffer upload response status: {response.status_code}")
            result = response.json()
            print(f"Buffer upload response: {result}")
            
            if response.status_code == 200:
                return result.get("media", {}).get("id", "")
            return ""
        except Exception as e:
            print(f"Buffer file upload error: {e}")
            return ""
    
    def create_post(self, channel_id: str, text: str, media_id: str = "") -> str:
        if not self.access_token:
            return ""
        
        input_data = {
            "channelId": channel_id,
            "text": text,
            "schedulingType": "automatic",
            "mode": "shareNow"
        }
        
        if media_id:
            input_data["media"] = {"id": media_id}
        
        query = """
        mutation CreatePost($input: CreatePostInput!) {
            createPost(input: $input) {
                ... on PostActionSuccess {
                    post {
                        id
                        text
                    }
                }
                ... on MutationError {
                    message
                }
            }
        }
        """
        
        result = self.graphql_request(query, {"input": input_data})
        
        if "errors" in result:
            print(f"Buffer create post error: {result['errors']}")
            return ""
        
        post_data = result.get("data", {}).get("createPost", {})
        if post_data.get("message"):
            print(f"Buffer post error: {post_data['message']}")
            return ""
        
        post_id = post_data.get("post", {}).get("id", "")
        if post_id:
            return f"https://buffer.com/app/post/{post_id}"
        return ""
    
    def upload(self, video_path: str, title: str, description: str, tags: list, channel_id: str = "") -> str:
        if not self.access_token:
            print("Buffer: No access token configured")
            return ""
        
        try:
            channels = self.get_account_channels()
            
            if not channels:
                print("Buffer: No channels found via API")
                return ""
            
            print(f"Buffer: Found {len(channels)} channels")
            for ch in channels:
                print(f"  - {ch['name']} ({ch['service']}): {ch['id']}")
            
            if not channel_id:
                channel_id = channels[0]["id"]
            
            print(f"Buffer: Uploading to channel {channel_id}")
            
            media_id = self.upload_file(video_path)
            if media_id:
                print(f"Buffer: File uploaded successfully, media_id: {media_id}")
                text = f"{title}\n\n{description}\n\n{' '.join(tags)}"
                result = self.create_post(channel_id, text, media_id)
                
                if result:
                    print(f"Buffer: Post created successfully: {result}")
                    return result
                else:
                    print("Buffer: Post creation failed")
            else:
                print("="*60)
                print("Buffer API限制说明:")
                print("="*60)
                print("当前使用的是Public API Token，不支持REST API文件上传。")
                print("需要OAuth 2.0 Access Token才能通过API上传视频。")
                print("")
                print("解决方案:")
                print("1. 升级Buffer付费计划，创建OAuth应用获取Access Token")
                print("2. 手动登录Buffer网站上传视频")
                print("   URL: https://publish.buffer.com")
                print("")
                print(f"视频文件已生成: {video_path}")
                print(f"标题: {title}")
                print(f"描述: {description}")
                print(f"标签: {' '.join(tags)}")
                print("="*60)
            
            return f"https://publish.buffer.com (请手动上传视频)"
        except Exception as e:
            print(f"Buffer upload error: {e}")
            return ""

class InstagramUploader:
    def __init__(self):
        self.buffer_uploader = BufferUploader()
    
    def upload(self, video_path: str, title: str, description: str, tags: list) -> str:
        return self.buffer_uploader.upload(video_path, title, description, tags)

def upload_to_platforms(video_path: str, title: str, description: str, tags: list, platforms: list) -> Dict:
    results = {}
    
    uploaders = {
        "youtube": YouTubeUploader(),
        "tiktok": TikTokUploader(),
        "buffer": BufferUploader(),
        "instagram": InstagramUploader()
    }
    
    for platform in platforms:
        uploader = uploaders.get(platform.lower())
        if uploader:
            url = uploader.upload(video_path, title, description, tags)
            results[platform] = url
        else:
            results[platform] = f"Platform {platform} not supported"
    
    return results