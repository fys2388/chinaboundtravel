"""
Multi-platform social media distributors for ChinaBound Travel.
Each distributor wraps a platform's API and provides a uniform publish() interface.
"""

import os
import json
import requests
from pathlib import Path
from datetime import datetime


class FacebookDistributor:
    """Facebook Graph API distributor - supports text posts, image posts, and video uploads"""

    PAGE_ID = os.getenv("FACEBOOK_PAGE_ID", "")
    PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", "")
    API_VERSION = "v21.0"
    BASE_URL = f"https://graph.facebook.com/{API_VERSION}"

    def is_configured(self) -> bool:
        return bool(self.PAGE_ID and self.PAGE_ACCESS_TOKEN)

    def publish(self, content: dict, content_type: str = "post") -> dict:
        if not self.is_configured():
            return {"success": False, "error": "Facebook not configured: set FACEBOOK_PAGE_ID and FACEBOOK_PAGE_ACCESS_TOKEN"}

        try:
            if content_type == "video" and content.get("video_path"):
                return self._upload_video(content)
            elif content.get("cover_url"):
                return self._post_with_image(content)
            else:
                return self._post_text(content)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _post_text(self, content: dict) -> dict:
        resp = requests.post(
            f"{self.BASE_URL}/{self.PAGE_ID}/feed",
            params={"access_token": self.PAGE_ACCESS_TOKEN},
            data={"message": content["text"]},
            timeout=30
        )
        if resp.status_code == 200:
            return {"success": True, "post_id": resp.json().get("id"), "platform": "facebook"}
        return {"success": False, "error": f"Facebook API error {resp.status_code}: {resp.text[:200]}"}

    def _post_with_image(self, content: dict) -> dict:
        # Step 1: Upload photo unpublished
        photo_resp = requests.post(
            f"{self.BASE_URL}/{self.PAGE_ID}/photos",
            params={"access_token": self.PAGE_ACCESS_TOKEN, "published": "false", "url": content["cover_url"]},
            timeout=30
        )
        if photo_resp.status_code != 200:
            return {"success": False, "error": f"Photo upload failed: {photo_resp.status_code}"}

        photo_id = photo_resp.json().get("id")

        # Step 2: Create post with photo
        post_resp = requests.post(
            f"{self.BASE_URL}/{self.PAGE_ID}/feed",
            params={"access_token": self.PAGE_ACCESS_TOKEN},
            data={"message": content["text"], "attached_media[0]": json.dumps({"media_fbid": photo_id})},
            timeout=30
        )
        if post_resp.status_code == 200:
            return {"success": True, "post_id": post_resp.json().get("id"), "platform": "facebook"}
        return {"success": False, "error": f"Post creation failed: {post_resp.status_code}"}

    def _upload_video(self, content: dict) -> dict:
        video_path = content.get("video_path")
        if not video_path or not Path(video_path).exists():
            return {"success": False, "error": f"Video file not found: {video_path}"}

        # Initiate upload
        init_resp = requests.post(
            f"{self.BASE_URL}/{self.PAGE_ID}/videos",
            params={"access_token": self.PAGE_ACCESS_TOKEN, "upload_phase": "start"},
            json={"file_size": Path(video_path).stat().st_size},
            timeout=30
        )
        if init_resp.status_code != 200:
            return {"success": False, "error": f"Video upload init failed: {init_resp.status_code}"}

        upload_session_id = init_resp.json().get("upload_session_id")
        video_id = init_resp.json().get("video_id")

        # Upload video bytes
        with open(video_path, "rb") as f:
            upload_resp = requests.post(
                f"{self.BASE_URL}/{video_id}",
                params={
                    "access_token": self.PAGE_ACCESS_TOKEN,
                    "upload_phase": "transfer",
                    "upload_session_id": upload_session_id,
                    "start_offset": "0",
                },
                headers={"offset": "0", "file_offset": "0"},
                data=f,
                timeout=300
            )

        if upload_resp.status_code != 200:
            return {"success": False, "error": f"Video transfer failed: {upload_resp.status_code}"}

        # Finish upload
        finish_resp = requests.post(
            f"{self.BASE_URL}/{self.PAGE_ID}/videos",
            params={"access_token": self.PAGE_ACCESS_TOKEN, "upload_phase": "finish", "upload_session_id": upload_session_id},
            data={"description": content["text"]},
            timeout=30
        )

        if finish_resp.status_code in (200, 206):
            return {"success": True, "video_id": video_id, "platform": "facebook"}
        return {"success": False, "error": f"Video finish failed: {finish_resp.status_code}"}


class TwitterDistributor:
    """X/Twitter API v2 distributor"""

    BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN", "")
    API_KEY = os.getenv("TWITTER_API_KEY", "")
    API_SECRET = os.getenv("TWITTER_API_SECRET", "")
    ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN", "")
    ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET", "")
    BASE_URL = "https://api.twitter.com/2"
    OAUTH_BASE = "https://api.twitter.com/1.1"

    def is_configured(self) -> bool:
        return bool(self.BEARER_TOKEN or (self.API_KEY and self.ACCESS_TOKEN))

    def publish(self, content: dict, content_type: str = "post") -> dict:
        if not self.is_configured():
            return {"success": False, "error": "Twitter not configured: set TWITTER_BEARER_TOKEN"}

        try:
            if self.BEARER_TOKEN:
                return self._post_oauth2(content)
            else:
                return self._post_oauth1(content)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _post_oauth2(self, content: dict) -> dict:
        headers = {"Authorization": f"Bearer {self.BEARER_TOKEN}"}
        payload = {"text": content["text"]}

        resp = requests.post(
            f"{self.BASE_URL}/tweets",
            headers=headers,
            json=payload,
            timeout=30
        )

        if resp.status_code == 201:
            tweet_data = resp.json().get("data", {})
            return {"success": True, "tweet_id": tweet_data.get("id"), "platform": "twitter"}
        return {"success": False, "error": f"Twitter API {resp.status_code}: {resp.text[:200]}"}

    def _post_oauth1(self, content: dict) -> dict:
        # OAuth 1.0a implementation for media upload
        from requests_oauthlib import OAuth1Session

        oauth = OAuth1Session(
            self.API_KEY, client_secret=self.API_SECRET,
            resource_owner_key=self.ACCESS_TOKEN,
            resource_owner_secret=self.ACCESS_TOKEN_SECRET
        )

        payload = {"text": content["text"]}
        resp = oauth.post(f"{self.BASE_URL}/tweets", json=payload, timeout=30)

        if resp.status_code == 201:
            return {"success": True, "tweet_id": resp.json()["data"]["id"], "platform": "twitter"}
        return {"success": False, "error": f"Twitter API {resp.status_code}: {resp.text[:200]}"}


class LinkedInDistributor:
    """LinkedIn API distributor - posts to LinkedIn Company Page"""

    ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
    COMPANY_URN = os.getenv("LINKEDIN_COMPANY_URN", "")  # e.g. "123456789"
    BASE_URL = "https://api.linkedin.com/v2"

    def is_configured(self) -> bool:
        return bool(self.ACCESS_TOKEN and self.COMPANY_URN)

    def publish(self, content: dict, content_type: str = "post") -> dict:
        if not self.is_configured():
            return {"success": False, "error": "LinkedIn not configured: set LINKEDIN_ACCESS_TOKEN and LINKEDIN_COMPANY_URN"}

        try:
            headers = {"Authorization": f"Bearer {self.ACCESS_TOKEN}", "Content-Type": "application/json"}
            payload = {
                "author": f"urn:li:organization:{self.COMPANY_URN}",
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "attributes": [],
                            "text": content["text"]
                        },
                        "shareMediaCategory": "ARTICLE" if content.get("url") else "NONE"
                    }
                },
                "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
            }

            if content.get("url"):
                payload["specificContent"]["com.linkedin.ugc.ShareContent"]["shareUrl"] = content["url"]

            resp = requests.post(
                f"{self.BASE_URL}/ugcPosts",
                headers=headers,
                json=payload,
                timeout=30
            )

            if resp.status_code == 201:
                return {"success": True, "post_urn": resp.json().get("id"), "platform": "linkedin"}
            return {"success": False, "error": f"LinkedIn API {resp.status_code}: {resp.text[:200]}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


class TikTokDistributor:
    """TikTok Content Posting API distributor"""

    ACCESS_TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN", "")
    BUSINESS_ID = os.getenv("TIKTOK_BUSINESS_ID", "")
    BASE_URL = "https://open.tiktokapis.com/v2"

    def is_configured(self) -> bool:
        return bool(self.ACCESS_TOKEN)

    def publish(self, content: dict, content_type: str = "post") -> dict:
        if not self.is_configured():
            return {"success": False, "error": "TikTok not configured: set TIKTOK_ACCESS_TOKEN"}

        try:
            headers = {"Authorization": f"Bearer {self.ACCESS_TOKEN}", "Content-Type": "application/json"}

            if content_type in ("video", "reel") and content.get("video_path"):
                return self._upload_video(content, headers)
            else:
                # TikTok doesn't support text-only posts, post to inbox for review
                return self._post_to_content_draft(content, headers)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _post_to_content_draft(self, content: dict, headers: dict) -> dict:
        payload = {
            "post_info": {
                "title": content["title"][:150],
                "description": content["text"],
                "privacy_level": "PUBLIC_TO_EVERYONE",
            }
        }

        if content.get("cover_url"):
            payload["post_info"]["cover_image_url"] = content["cover_url"]

        resp = requests.post(
            f"{self.BASE_URL}/content/publish/",
            headers=headers,
            json=payload,
            timeout=30
        )

        if resp.status_code == 200:
            return {"success": True, "publish_id": resp.json().get("data", {}).get("publish_id"), "platform": "tiktok"}
        return {"success": False, "error": f"TikTok API {resp.status_code}: {resp.text[:200]}"}

    def _upload_video(self, content: dict, headers: dict) -> dict:
        video_path = content.get("video_path")
        if not video_path:
            return {"success": False, "error": "No video path provided"}

        # Step 1: Initialize upload
        init_payload = {"post_info": {"title": content["title"][:150], "privacy_level": "PUBLIC_TO_EVERYONE", "disable_duet": False, "disable_comment": False, "disable_stitch": False}}
        init_resp = requests.post(f"{self.BASE_URL}/post/publish/video/init/", headers=headers, json=init_payload, timeout=30)

        if init_resp.status_code != 200:
            return {"success": False, "error": f"TikTok video init failed: {init_resp.status_code}"}

        upload_url = init_resp.json().get("data", {}).get("upload_url")

        # Step 2: Upload video
        with open(video_path, "rb") as f:
            upload_resp = requests.put(upload_url, data=f, headers={"Content-Type": "application/octet-stream"}, timeout=300)

        if upload_resp.status_code not in (200, 201):
            return {"success": False, "error": f"TikTok video upload failed: {upload_resp.status_code}"}

        # Step 3: Check status and publish
        publish_id = init_resp.json().get("data", {}).get("publish_id")
        check_resp = requests.post(f"{self.BASE_URL}/post/publish/video/status/fetch/", headers=headers, json={"publish_id": publish_id}, timeout=30)

        return {"success": True, "publish_id": publish_id, "status": check_resp.json().get("data", {}).get("status"), "platform": "tiktok"}


class YouTubeDistributor:
    """YouTube Data API v3 distributor"""

    CLIENT_SECRETS_FILE = os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", "")
    OAUTH_REFRESH_TOKEN = os.getenv("YOUTUBE_OAUTH_REFRESH_TOKEN", "")
    CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID", "")

    def is_configured(self) -> bool:
        return bool(self.CLIENT_SECRETS_FILE or self.OAUTH_REFRESH_TOKEN)

    def publish(self, content: dict, content_type: str = "post") -> dict:
        if not self.is_configured():
            return {"success": False, "error": "YouTube not configured: set YOUTUBE_OAUTH_REFRESH_TOKEN and YOUTUBE_CLIENT_SECRETS_FILE"}

        if content_type not in ("video", "reel") or not content.get("video_path"):
            return {"success": False, "error": "YouTube only supports video uploads. Provide --type video --video-path path/to/video.mp4"}

        try:
            return self._upload_video(content)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_access_token(self) -> str:
        """Refresh OAuth token"""
        if not self.CLIENT_SECRETS_FILE or not Path(self.CLIENT_SECRETS_FILE).exists():
            raise Exception("YouTube client secrets file not found")

        with open(self.CLIENT_SECRETS_FILE) as f:
            secrets = json.load(f)

        client_id = secrets.get("installed", {}).get("client_id") or secrets.get("web", {}).get("client_id", "")
        client_secret = secrets.get("installed", {}).get("client_secret") or secrets.get("web", {}).get("client_secret", "")

        resp = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": self.OAUTH_REFRESH_TOKEN,
                "grant_type": "refresh_token",
            },
            timeout=30
        )

        if resp.status_code == 200:
            return resp.json()["access_token"]
        raise Exception(f"Token refresh failed: {resp.status_code}")

    def _upload_video(self, content: dict) -> dict:
        access_token = self._get_access_token()

        video_path = content.get("video_path")
        if not video_path or not Path(video_path).exists():
            return {"success": False, "error": f"Video file not found: {video_path}"}

        headers = {"Authorization": f"Bearer {access_token}"}

        body = {
            "snippet": {
                "title": content["title"][:100],
                "description": content["text"][:5000],
                "tags": [t.strip("#") for t in content.get("hashtags", "").split() if t],
                "categoryId": "22",  # Travel
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False,
                "embeddable": True,
            }
        }

        resp = requests.post(
            "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
            headers={**headers, "Content-Type": "application/json"},
            json=body,
            timeout=30
        )

        if resp.status_code == 200:
            return {"success": True, "video_id": resp.json().get("id"), "platform": "youtube"}
        return {"success": False, "error": f"YouTube API {resp.status_code}: {resp.text[:200]}"}
