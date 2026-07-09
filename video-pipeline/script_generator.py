import json
import re
from typing import Dict, List, Optional
from openai import OpenAI
import httpx
from config import Config

http_client = httpx.Client(
    limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
)

if Config.DOUBAO_ARK_API_KEY and Config.DOUBAO_MODEL:
    client = OpenAI(api_key=Config.DOUBAO_ARK_API_KEY, base_url=Config.DOUBAO_BASE_URL, http_client=http_client)
    MODEL_TO_USE = Config.DOUBAO_MODEL
elif Config.DEEPSEEK_API_KEY:
    client = OpenAI(api_key=Config.DEEPSEEK_API_KEY, base_url=Config.DEEPSEEK_BASE_URL, http_client=http_client)
    MODEL_TO_USE = Config.DEEPSEEK_MODEL
else:
    client = OpenAI(api_key=Config.OPENAI_API_KEY, http_client=http_client)
    MODEL_TO_USE = Config.OPENAI_MODEL

def load_topic_pool() -> List[Dict]:
    with open(Config.TOPIC_POOL_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("topics", [])

def load_knowledge_base() -> Dict:
    with open(Config.CONTENT_KNOWLEDGE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def find_relevant_knowledge(topic_title: str) -> str:
    kb = load_knowledge_base()
    categories = kb.get("knowledge_categories", {})
    
    keywords = re.findall(r"[\w]+", topic_title.lower())
    
    best_match = ""
    best_score = 0
    
    for category, items in categories.items():
        for item in items:
            item_title = item.get("keyword", "").lower()
            item_content = item.get("content", "")
            
            score = sum(1 for kw in keywords if kw in item_title)
            if score > best_score:
                best_score = score
                best_match = item_content
    
    return best_match

def generate_script(topic: Dict) -> Dict:
    title = topic.get("title", "")
    keywords = topic.get("keywords", [])
    category = topic.get("category", "")
    geo = topic.get("geo", "")
    
    knowledge = find_relevant_knowledge(title)
    
    prompt = f"""
You are a professional travel content creator. Create a short video script (15-30 seconds) for a travel channel targeting foreigners visiting China.

Topic: {title}
Category: {category}
Target Audience: Foreign travelers from {geo}
Keywords: {', '.join(keywords)}

Existing knowledge (use if relevant):
{knowledge[:500] if knowledge else 'None'}

Requirements:
1. Script should be engaging and informative
2. Keep sentences short for better pacing
3. Include strong hook in the first 3 seconds
4. End with a call to action or intriguing question
5. Duration: 15-30 seconds
6. Language: English

Output format (JSON only, no markdown):
{{
  "hook": "First 3 seconds hook text",
  "narration": "Full narration text",
  "scenes": [
    {{"time": "0-5s", "description": "Visual description for this time segment", "image_prompt": "AI image generation prompt"}},
    {{"time": "5-10s", "description": "...", "image_prompt": "..."}}
  ],
  "subtitles": [
    {{"time": "0-3s", "text": "First subtitle"}},
    {{"time": "3-6s", "text": "Second subtitle"}}
  ],
  "tags": ["#tag1", "#tag2", "#tag3"]
}}
"""
    
    try:
        response = client.chat.completions.create(
            model=MODEL_TO_USE,
            messages=[
                {"role": "system", "content": "You are an expert travel video scriptwriter."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        content = response.choices[0].message.content.strip()
        
        content = re.sub(r"^```json\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
        
        return json.loads(content)
    except Exception as e:
        print(f"Error generating script: {e}")
        return {
            "hook": f"Did you know about {title}?",
            "narration": f"Discover everything you need to know about {title}. This comprehensive guide will help you plan your trip to China.",
            "scenes": [
                {"time": "0-5s", "description": f"Beautiful scenery of {title}", "image_prompt": f"Beautiful {title} scenery, travel photography, cinematic lighting"},
                {"time": "5-10s", "description": f"Tourists enjoying {title}", "image_prompt": f"Tourists enjoying {title}, happy travelers, vibrant atmosphere"}
            ],
            "subtitles": [
                {"time": "0-5s", "text": f"Discover {title}"},
                {"time": "5-10s", "text": "Plan your China trip"}
            ],
            "tags": [f"#{category}", "#ChinaTravel", "#TravelTips"]
        }

def get_pending_topics(count: int = 5) -> List[Dict]:
    topics = load_topic_pool()
    pending = [t for t in topics if t.get("status") == "pending"]
    return pending[:count]