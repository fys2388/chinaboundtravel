import os
from dotenv import load_dotenv

load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

class Config:
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    
    DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
    DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
    DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
    
    DOUBAO_ARK_API_KEY = os.environ.get("DOUBAO_ARK_API_KEY", "")
    DOUBAO_MODEL = os.environ.get("DOUBAO_MODEL", "doubao-seed-character-251128")
    DOUBAO_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
    
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
    
    TIKTOK_CLIENT_KEY = os.environ.get("TIKTOK_CLIENT_KEY", "")
    TIKTOK_CLIENT_SECRET = os.environ.get("TIKTOK_CLIENT_SECRET", "")
    
    BUFFER_ACCESS_TOKEN = os.environ.get("BUFFER_ACCESS_TOKEN", "")
    
    OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
    TEMP_DIR = os.path.join(os.path.dirname(__file__), "temp")
    ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
    
    VIDEO_WIDTH = 1080
    VIDEO_HEIGHT = 1920
    VIDEO_FPS = 30
    
    VOICE_NAME = "en-US-GuyNeural"
    VOICE_RATE = "+0%"
    VOICE_VOLUME = "+0%"
    
    TOPIC_POOL_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "topic_pool.json")
    CONTENT_KNOWLEDGE_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "content_knowledge_base.json")
    
    MAX_SCRIPT_LENGTH = 30
    MAX_IMAGES_PER_VIDEO = 6
    
    @staticmethod
    def ensure_directories():
        for dir_path in [Config.OUTPUT_DIR, Config.TEMP_DIR, Config.ASSETS_DIR]:
            os.makedirs(dir_path, exist_ok=True)

Config.ensure_directories()