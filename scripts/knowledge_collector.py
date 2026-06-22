import os
import json
import re
import hashlib
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional
from urllib.parse import quote

class KnowledgeCollector:
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.kb_path = os.path.join(repo_path, "config", "content_knowledge_base.json")
        self.kb = self._load_kb()
        
        self.search_keywords = [
            "China travel guide", "Chengdu travel", "Yunnan travel", "Beijing travel", "Xi'an travel",
            "Guilin Yangshuo", "Zhangjiajie", "Shanghai travel", "Chongqing travel", "Tibet travel",
            "China food guide", "China high speed rail", "China visa", "China transportation",
            "China travel tips", "China road trip", "China backpacking", "Chinese culture"
        ]
        
        self.category_keywords = {
            "destinations": ["attraction", "guide", "must see", "recommend", "ancient", "nature", "scenic"],
            "transportation": ["high speed rail", "metro", "transport", "taxi", "rent", "drive", "flight", "train"],
            "accommodation": ["hotel", "hostel", "stay", "lodging", "inn"],
            "food": ["food", "cuisine", "hotpot", "restaurant", "local", "street food"],
            "culture": ["culture", "traditional", "festival", "custom", "experience"],
            "tips": ["guide", "tip", "advice", "warning", "avoid", "best"],
            "seasons": ["season", "best time", "weather", "climate"],
            "budget": ["budget", "cost", "save", "affordable", "cheap"],
            "safety": ["safety", "caution", "danger", "precaution"],
            "visa": ["visa", "entry", "customs", "immigration"]
        }
    
    def _load_kb(self):
        if os.path.exists(self.kb_path):
            with open(self.kb_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "total_entries": 0,
            "sources": [],
            "knowledge_categories": {
                "destinations": [],
                "transportation": [],
                "accommodation": [],
                "food": [],
                "culture": [],
                "tips": [],
                "seasons": [],
                "budget": [],
                "safety": [],
                "visa": []
            },
            "learning_metrics": {
                "total_learned": 0,
                "total_deduplicated": 0,
                "total_filtered": 0,
                "last_learning_date": ""
            }
        }
    
    def _save_kb(self):
        self.kb["last_updated"] = datetime.now().isoformat()
        self.kb["learning_metrics"]["last_learning_date"] = datetime.now().strftime("%Y-%m-%d")
        with open(self.kb_path, 'w', encoding='utf-8') as f:
            json.dump(self.kb, f, indent=2, ensure_ascii=False)
    
    def _generate_hash(self, content: str) -> str:
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def _classify(self, text: str) -> str:
        text_lower = text.lower()
        for category, keywords in self.category_keywords.items():
            for kw in keywords:
                if kw in text_lower:
                    return category
        return "tips"
    
    def _clean_content(self, content: str) -> str:
        content = re.sub(r'\s+', ' ', content).strip()
        content = re.sub(r'[^\w\s\-\.\,\!\?\;\:\"\'\(\)]', '', content)
        return content[:1500]
    
    def _extract_key_points(self, content: str) -> List[str]:
        sentences = re.split(r'[\.\!\?\n]', content)
        key_points = []
        for s in sentences:
            s = s.strip()
            if len(s) > 15 and len(s) < 120:
                if any(kw in s.lower() for kw in ["recommend", "suggest", "avoid", "best", "must", "tip", "guide"]):
                    key_points.append(s)
        return key_points[:10]
    
    def _is_duplicate(self, content_hash: str) -> bool:
        for category, entries in self.kb["knowledge_categories"].items():
            for entry in entries:
                if entry.get("hash") == content_hash:
                    return True
        return False
    
    def search_web(self, keyword: str, max_results: int = 5) -> List[Dict[str, Any]]:
        results = []
        try:
            encoded_keyword = quote(keyword)
            url = f"https://www.bing.com/search?q={encoded_keyword}+travel+blog"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                links = re.findall(r'<a href="([^"]+)" h=".*?">', response.text)
                for i, link in enumerate(links[:max_results * 2]):
                    try:
                        if link.startswith("http") and "bing.com" not in link and "microsoft.com" not in link:
                            results.append({"url": link, "keyword": keyword})
                    except:
                        continue
        except Exception as e:
            print(f"[Search] Error searching for {keyword}: {e}")
        
        return results
    
    def fetch_article(self, url: str) -> Optional[str]:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.encoding = response.apparent_encoding
            
            text = response.text
            text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()
            
            return text[:5000]
        except Exception as e:
            print(f"[Fetch] Error fetching {url}: {e}")
            return None
    
    def learn_from_search(self, keywords: Optional[List[str]] = None):
        keywords = keywords or self.search_keywords
        learned_count = 0
        
        print(f"[Learning] Starting knowledge collection from {len(keywords)} keywords...")
        
        for keyword in keywords:
            print(f"[Learning] Searching: {keyword}")
            search_results = self.search_web(keyword)
            
            for result in search_results:
                content = self.fetch_article(result["url"])
                if not content or len(content) < 200:
                    continue
                
                cleaned_content = self._clean_content(content)
                content_hash = self._generate_hash(cleaned_content)
                
                if self._is_duplicate(content_hash):
                    self.kb["learning_metrics"]["total_deduplicated"] += 1
                    continue
                
                category = self._classify(cleaned_content)
                key_points = self._extract_key_points(cleaned_content)
                
                if not key_points:
                    self.kb["learning_metrics"]["total_filtered"] += 1
                    continue
                
                entry = {
                    "hash": content_hash,
                    "source": "web_search",
                    "url": result["url"],
                    "keyword": keyword,
                    "category": category,
                    "content": cleaned_content[:500],
                    "key_points": key_points,
                    "language": "en",
                    "learned_at": datetime.now().isoformat(),
                    "relevance": len(key_points)
                }
                
                self.kb["knowledge_categories"][category].append(entry)
                self.kb["total_entries"] += 1
                learned_count += 1
                
                if learned_count % 10 == 0:
                    print(f"[Learning] Learned {learned_count} entries so far...")
        
        self.kb["learning_metrics"]["total_learned"] += learned_count
        self._save_kb()
        
        print(f"[Learning] Completed! Learned {learned_count} new entries.")
        return learned_count
    
    def learn_from_ai_summary(self, topic: str, summary: str):
        content_hash = self._generate_hash(summary)
        
        if self._is_duplicate(content_hash):
            return False
        
        category = self._classify(summary)
        key_points = self._extract_key_points(summary)
        
        entry = {
            "hash": content_hash,
            "source": "ai_summary",
            "url": "",
            "keyword": topic,
            "category": category,
            "content": summary[:500],
            "key_points": key_points,
            "language": "en",
            "learned_at": datetime.now().isoformat(),
            "relevance": len(key_points)
        }
        
        self.kb["knowledge_categories"][category].append(entry)
        self.kb["total_entries"] += 1
        self.kb["learning_metrics"]["total_learned"] += 1
        self._save_kb()
        
        print(f"[Learning] Learned from AI summary: {topic}")
        return True
    
    def get_knowledge_for_topic(self, topic: str, limit: int = 5) -> List[Dict[str, Any]]:
        topic_lower = topic.lower()
        matched = []
        
        for category, entries in self.kb["knowledge_categories"].items():
            for entry in entries:
                entry_keyword = entry.get("keyword", "").lower()
                entry_content = entry.get("content", "").lower()
                if topic_lower in entry_keyword or entry_keyword in topic_lower:
                    matched.append(entry)
                elif any(kw in topic_lower for kw in entry_content.split()[:10]):
                    matched.append(entry)
        
        matched.sort(key=lambda x: x.get("relevance", 0), reverse=True)
        return matched[:limit]
    
    def get_summary(self) -> Dict[str, Any]:
        summary = {
            "total_entries": self.kb["total_entries"],
            "categories": {},
            "metrics": self.kb["learning_metrics"],
            "last_updated": self.kb["last_updated"]
        }
        
        for category, entries in self.kb["knowledge_categories"].items():
            summary["categories"][category] = len(entries)
        
        return summary

if __name__ == "__main__":
    import sys
    repo_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    collector = KnowledgeCollector(repo_path)
    
    if len(sys.argv) > 1 and sys.argv[1] == "learn":
        keywords = sys.argv[2:] if len(sys.argv) > 2 else None
        collector.learn_from_search(keywords)
    elif len(sys.argv) > 1 and sys.argv[1] == "summary":
        summary = collector.get_summary()
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print("Usage: python knowledge_collector.py [learn|summary] [keywords...]")
        print("Example: python knowledge_collector.py learn Yunnan travel Chengdu food")
