import os
from dotenv import load_dotenv

load_dotenv()

REDDIT_CONFIG = {
    "client_id": os.getenv("REDDIT_CLIENT_ID", "YOUR_REDDIT_CLIENT_ID"),
    "client_secret": os.getenv("REDDIT_CLIENT_SECRET", "YOUR_REDDIT_CLIENT_SECRET"),
    "user_agent": os.getenv("REDDIT_USER_AGENT", "ChinaBoundTravelBot/1.0 by fys2388"),
    "username": os.getenv("REDDIT_USERNAME", "YOUR_REDDIT_USERNAME"),
    "password": os.getenv("REDDIT_PASSWORD", "YOUR_REDDIT_PASSWORD"),
    "target_subreddits": ["ChinaTravel", "travel", "China", "AskChina", "TravelChina"],
    "min_post_interval_minutes": 60,
    "max_post_interval_minutes": 180,
    "max_posts_per_day": 5,
    "auto_publish": False,
    "require_approval": True
}

PINTEREST_CONFIG = {
    "api_key": os.getenv("PINTEREST_API_KEY", "YOUR_PINTEREST_API_KEY"),
    "access_token": os.getenv("PINTEREST_ACCESS_TOKEN", "YOUR_PINTEREST_ACCESS_TOKEN"),
    "board_ids": {
        "china-travel": "YOUR_BOARD_ID",
        "travel-tips": "YOUR_BOARD_ID",
        "china-cities": "YOUR_BOARD_ID",
        "travel-guides": "YOUR_BOARD_ID"
    },
    "default_tags": ["China", "ChinaTravel", "Travel", "TravelGuide", "ChinaTrip"],
    "image_width": 1080,
    "image_height": 1920
}

MEDIUM_CONFIG = {
    "integration_token": os.getenv("MEDIUM_INTEGRATION_TOKEN", "YOUR_MEDIUM_INTEGRATION_TOKEN"),
    "user_id": os.getenv("MEDIUM_USER_ID", "YOUR_MEDIUM_USER_ID"),
    "default_tags": ["China", "Travel", "ChinaTravel", "TravelGuide", "AsiaTravel"],
    "canonical_url_base": "https://chinaboundtravel.com",
    "auto_publish": False,
    "sync_interval_hours": 1
}

QUORA_CONFIG = {
    "email": os.getenv("QUORA_EMAIL", "YOUR_QUORA_EMAIL"),
    "password": os.getenv("QUORA_PASSWORD", "YOUR_QUORA_PASSWORD"),
    "monitor_keywords": ["China travel", "visit China", "China visa", "travel to China"],
    "notification_webhook": "",
    "max_questions_per_day": 10
}

BUFFER_CONFIG = {
    "access_token": os.getenv("BUFFER_ACCESS_TOKEN", ""),
    "base_url": "https://api.buffer.com/v1/graphql",
    "timezone": "America/New_York",
    "best_times": ["09:00", "12:00", "15:00", "18:00"]
}

CONTENT_TEMPLATES = {
    "reddit": {
        "title_template": "{title}",
        "body_template": """{summary}

{content}

---

Read the full guide here: {url}

#ChinaTravel #TravelChina {tags}
"""
    },
    "pinterest": {
        "title_template": "{title} | China Bound Travel",
        "description_template": "{summary}\n\n{url}\n\n#ChinaTravel #TravelGuide #China",
        "tag_template": "{tags}"
    },
    "medium": {
        "title_template": "{title}",
        "subtitle_template": "A comprehensive guide to {topic}",
        "content_template": """# {title}

{summary}

---

{content}

---

*Originally published at [{blog_url}]({blog_url})*
"""
    },
    "quora": {
        "answer_template": """Great question! Here's what I know about {question}:

{answer}

For more detailed information, check out my complete guide: {url}

#ChinaTravel #TravelTips
"""
    }
}

AUTHOR_BIO = """Joran is the editorial voice behind ChinaBound Travel — providing research-based, practical China travel information for international travelers."""

BLOG_URL = "https://chinaboundtravel.com"
AUTHOR_NAME = "Joran"

LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "log_file": "posting_log.txt",
    "max_file_size": 10485760,
    "backup_count": 5
}

SCHEDULE_CONFIG = {
    "reddit": {
        "enabled": True,
        "hours": [9, 12, 15, 18, 21]
    },
    "pinterest": {
        "enabled": True,
        "hours": [10, 14, 17, 20]
    },
    "medium": {
        "enabled": True,
        "hours": [11, 16]
    },
    "quora": {
        "enabled": True,
        "hours": [9, 15]
    }
}