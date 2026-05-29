# ============================================
# Medium Poster Module
# ============================================

import logging
from config import MEDIUM_CONFIG, CONTENT_TEMPLATES

logger = logging.getLogger(__name__)

class MediumPoster:
    """Medium posting functionality"""

    def __init__(self):
        self.config = MEDIUM_CONFIG
        self.template = CONTENT_TEMPLATES['medium']
        self.token = self.config['integration_token']
        self.user_id = self.config['user_id']
        self._headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def is_configured(self):
        """Check if Medium is properly configured"""
        return (
            self.token != "YOUR_MEDIUM_INTEGRATION_TOKEN" and
            self.user_id != "YOUR_MEDIUM_USER_ID"
        )

    def is_connected(self):
        """Check if connected to Medium API"""
        if not self.is_configured():
            return False

        try:
            import requests

            response = requests.get(
                "https://api.medium.com/v1/me",
                headers=self._headers,
                timeout=10
            )
            return response.status_code == 200

        except Exception as e:
            logger.error(f"Medium connection failed: {e}")
            return False

    def post(self, content):
        """
        Post article to Medium

        Note: Medium API only allows posting to your own account,
        not to publications (requires additional OAuth)
        """
        if not self.is_connected():
            return {"success": False, "error": "Not connected or not configured"}

        try:
            import requests

            article_data = {
                "title": self._format_title(content),
                "contentFormat": "markdown",
                "content": self._format_content(content),
                "tags": self._get_tags(content),
                "publishStatus": "draft"  # Start as draft for review
            }

            response = requests.post(
                f"https://api.medium.com/v1/users/{self.user_id}/posts",
                headers=self._headers,
                json=article_data,
                timeout=30
            )

            if response.status_code in [200, 201]:
                data = response.json()
                post_url = data.get('data', {}).get('url', '')
                logger.info(f"Posted to Medium: {post_url}")
                return {
                    "success": True,
                    "url": post_url,
                    "id": data.get('data', {}).get('id', '')
                }
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}

        except Exception as e:
            logger.error(f"Medium post failed: {e}")
            return {"success": False, "error": str(e)}

    def post_to_publication(self, content, publication_id):
        """Post article to a Medium publication"""
        if not self.is_connected():
            return {"success": False, "error": "Not connected"}

        try:
            import requests

            article_data = {
                "title": self._format_title(content),
                "contentFormat": "markdown",
                "content": self._format_content(content),
                "tags": self._get_tags(content),
                "publishStatus": "draft"
            }

            response = requests.post(
                f"https://api.medium.com/v1/publications/{publication_id}/posts",
                headers=self._headers,
                json=article_data,
                timeout=30
            )

            if response.status_code in [200, 201]:
                data = response.json()
                return {
                    "success": True,
                    "url": data.get('data', {}).get('url', '')
                }
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}

        except Exception as e:
            logger.error(f"Medium publication post failed: {e}")
            return {"success": False, "error": str(e)}

    def _format_title(self, content):
        """Format article title"""
        template = self.template['title_template']
        return template.format(title=content.get('title', ''))

    def _format_content(self, content):
        """Format article content as Markdown"""
        markdown_content = f"# {content.get('title', '')}\n\n"
        markdown_content += f"*{self.template['subtitle_template']}*\n\n"
        markdown_content += f"## Introduction\n\n"
        markdown_content += f"{content.get('summary', '')}\n\n"
        markdown_content += f"---\n\n"
        markdown_content += f"{self._get_author_bio()}\n"
        return markdown_content

    def _get_tags(self, content):
        """Get article tags"""
        default_tags = self.config['default_tags']
        topic = content.get('topic', '')

        if topic:
            default_tags.append(topic.lower().replace(' ', '-'))

        return default_tags[:5]

    def _get_author_bio(self):
        """Get author bio for article footer"""
        from config import AUTHOR_BIO, BLOG_URL, AUTHOR_NAME
        return f"""
---

**About the Author**

{AUTHOR_BIO}

For more travel guides, visit [{BLOG_URL}]({BLOG_URL})

Written by {AUTHOR_NAME}
"""