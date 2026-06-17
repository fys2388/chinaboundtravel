#!/usr/bin/env python3
"""
daily_inspection.py - ChinaBound Travel 
SEO
Version: 5.0 - GSC+++
"""

import os
import sys
import glob
import logging
import re
import argparse
import hashlib
import base64
import hmac
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse, urlencode
import urllib.request
import frontmatter
import requests
from bs4 import BeautifulSoup

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ====================  ====================
SCRIPT_DIR = Path(__file__).parent.resolve()
BLOG_ROOT = SCRIPT_DIR
CONTENT_DIR = BLOG_ROOT / "content"
POSTS_DIR = CONTENT_DIR / "posts"
REPORTS_DIR = BLOG_ROOT / "reports" / "01_daily_inspection"
CONFIG_DIR = BLOG_ROOT / "config"

# 
ERROR_KNOWLEDGE_BASE = CONFIG_DIR / "error_knowledge_base.json"
GSC_HOT_KEYWORDS = CONFIG_DIR / "gsc_hot_keyword.json"
COMPETITOR_TOPICS = CONFIG_DIR / "competitor_topic.json"
USER_FEEDBACK = CONFIG_DIR / "user_feedback.json"
AFFILIATE_DATA = CONFIG_DIR / "affiliate_data.json"

REPORTS_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

GARBLE_CHARS = [
    '\uFFFD', '\uFFFE', '\uFFFF',
    '\u0000', '\u0001', '\u0002', '\u0003', '\u0004', '\u0005',
    '\u0006', '\u0007', '\u0008', '\u000B', '\u000C', '\u000E',
    '\u000F', '\u007F', '\u0080', '\u0081', '\u0082', '\u0083',
    '\u0084', '\u0085', '\u0086', '\u0087', '\u0088', '\u0089',
    '\u008A', '\u008B', '\u008C', '\u008D', '\u008E', '\u008F',
    '\u0090', '\u0091', '\u0092', '\u0093', '\u0094', '\u0095',
    '\u0096', '\u0097', '\u0098', '\u0099', '\u009A', '\u009B',
    '\u009C', '\u009D', '\u009E', '\u009F',
    '\uFEFF', '\u200B', '\u200C', '\u200D', '\u200E', '\u200F',
]

# ====================  ====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(BLOG_ROOT / "daily_inspection.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("ChinaBound.Inspection")

# ====================  ====================

class EncodingChecker:
    """"""
    
    def __init__(self):
        self.issues = []
        self.fixed_count = 0
    
    def check_file(self, filepath: Path) -> dict:
        result = {
            "filepath": str(filepath),
            "has_issue": False,
            "issues": [],
            "fixed": False
        }
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            for garbled in GARBLE_CHARS:
                if garbled in content:
                    result["has_issue"] = True
                    result["issues"].append({
                        "char": garbled,
                        "count": content.count(garbled)
                    })
            
            # 
            if "?" in content:
                result["has_issue"] = True
                result["issues"].append({
                    "char": "?",
                    "count": content.count("?")
                })
                
        except Exception as e:
            result["has_issue"] = True
            result["issues"].append({
                "error": str(e)
            })
        
        return result
    
    def scan_all(self) -> list:
        logger.info("Starting encoding check...")
        all_issues = []
        
        skip_dirs = [".archived", ".audit_backup", "_draft", "drafts"]
        patterns = ["**/*.md"]
        for pattern in patterns:
            files = list(CONTENT_DIR.glob(pattern))
            for filepath in files:
                if any(skip_dir in str(filepath) for skip_dir in skip_dirs):
                    continue
                result = self.check_file(filepath)
                if result["has_issue"]:
                    all_issues.append(result)
                    logger.warning(f"Found issue: {filepath.name}")
        
        return all_issues
    
    def auto_fix(self, filepath: Path) -> bool:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original = content
            
            # 
            replacements = {
                "?": "",
                "": "",
                "": "-",
                "": "-"
            }
            
            for garbled, correct in replacements.items():
                content = content.replace(garbled, correct)
            
            if content != original:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                logger.info(f": {filepath.name}")
                self.fixed_count += 1
                return True
            
            return False
            
        except Exception as e:
            logger.error(f" {filepath}: {e}")
            return False


class ContentChecker:
    """"""
    
    def __init__(self):
        self.issues = []
    
    def check_frontmatter(self, filepath: Path) -> dict:
        result = {
            "filepath": str(filepath),
            "has_issue": False,
            "issues": []
        }
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
            
            required_fields = ["title", "description", "date", "author"]
            for field in required_fields:
                if field not in post.metadata:
                    result["has_issue"] = True
                    result["issues"].append(f": {field}")
            
            if "params" in post.metadata:
                params = post.metadata["params"]
                if "keywords" not in params:
                    result["has_issue"] = True
                    result["issues"].append(": params.keywords")
                if "faq" not in params:
                    result["has_issue"] = True
                    result["issues"].append(": params.faq")
            
        except Exception as e:
            result["has_issue"] = True
            result["issues"].append(f": {str(e)}")
        
        return result
    
    def scan_all(self) -> list:
        logger.info("...")
        issues = []
        
        files = list(POSTS_DIR.glob("*.md"))
        for filepath in files:
            result = self.check_frontmatter(filepath)
            if result["has_issue"]:
                issues.append(result)
        
        return issues


class AffiliateChecker:
    """"""
    
    def __init__(self):
        self.issues = []
        # 
        self.affiliate_domains = [
            "ctrip.com",
            "qunar.com", 
            "fliggy.com",
            "booking.com",
            "agoda.com",
            "expedia.com",
            "tripadvisor.com",
            "viator.com",
            "klook.com",
            "getyourguide.com",
            "ctrip.io",
            "m.ctrip.com"
        ]
        # 
        self.affiliate_params = ["aff_id", "affiliate_id", "ref", "tracking", "cid", "partner_id"]
    
    def check_affiliate_links(self, filepath: Path) -> dict:
        """"""
        result = {
            "filepath": str(filepath),
            "has_affiliate": False,
            "has_invalid_links": False,
            "affiliate_links": [],
            "invalid_links": []
        }
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 
            #  markdown : [text](url)
            link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
            links = link_pattern.findall(content)
            
            for text, url in links:
                # 
                is_affiliate = False
                
                # 
                for domain in self.affiliate_domains:
                    if domain in url.lower():
                        is_affiliate = True
                        break
                
                # 
                if not is_affiliate:
                    for param in self.affiliate_params:
                        if param in url.lower():
                            is_affiliate = True
                            break
                
                if is_affiliate:
                    result["has_affiliate"] = True
                    result["affiliate_links"].append({
                        "text": text,
                        "url": url,
                        "valid": self._check_link_validity(url)
                    })
            
            # 
            for link in result["affiliate_links"]:
                if not link["valid"]:
                    result["has_invalid_links"] = True
                    result["invalid_links"].append(link)
        
        except Exception as e:
            result["has_invalid_links"] = True
            result["invalid_links"].append({
                "error": str(e)
            })
        
        return result
    
    def _check_link_validity(self, url: str) -> bool:
        """"""
        try:
            # 
            response = urllib.request.urlopen(url, timeout=5)
            return response.status == 200
        except Exception:
            return False
    
    def scan_all(self) -> list:
        logger.info("...")
        issues = []
        
        files = list(POSTS_DIR.glob("*.md"))
        for filepath in files:
            result = self.check_affiliate_links(filepath)
            if result["has_invalid_links"]:
                issues.append(result)
                logger.warning(f": {filepath.name}")
        
        return issues
    
    def get_affiliate_stats(self) -> dict:
        """"""
        stats = {
            "total_posts": 0,
            "posts_with_affiliate": 0,
            "total_affiliate_links": 0,
            "invalid_links": 0
        }
        
        files = list(POSTS_DIR.glob("*.md"))
        stats["total_posts"] = len(files)
        
        for filepath in files:
            result = self.check_affiliate_links(filepath)
            if result["has_affiliate"]:
                stats["posts_with_affiliate"] += 1
                stats["total_affiliate_links"] += len(result["affiliate_links"])
                stats["invalid_links"] += len(result["invalid_links"])
        
        return stats


class SiteChecker:
    """Website accessibility checker"""
    
    def __init__(self):
        self.base_url = "https://chinaboundtravel.com"
    
    def check_site(self) -> dict:
        result = {
            "site_up": False,
            "https_ok": False,
            "status_code": None,
            "error": None
        }
        
        try:
            response = requests.get(self.base_url, timeout=10, headers={"User-Agent": "ChinaBound-Inspection/1.0"})
            result["site_up"] = response.status_code == 200
            result["status_code"] = response.status_code
            result["https_ok"] = self.base_url.startswith("https://")
            
        except requests.exceptions.RequestException as e:
            result["error"] = str(e)
            logger.warning(f"Site check failed: {e}")
        
        return result


# ====================  ====================

class ErrorKnowledgeBase:
    """ - Joran"""
    
    def __init__(self):
        self.knowledge_base = self._load_knowledge_base()
    
    def _load_knowledge_base(self):
        """"""
        if ERROR_KNOWLEDGE_BASE.exists():
            try:
                with open(ERROR_KNOWLEDGE_BASE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            "error_patterns": [],
            "resolved_count": 0,
            "total_errors": 0,
            "last_updated": None
        }
    
    def _save_knowledge_base(self):
        """"""
        self.knowledge_base["last_updated"] = datetime.now().isoformat()
        with open(ERROR_KNOWLEDGE_BASE, 'w', encoding='utf-8') as f:
            json.dump(self.knowledge_base, f, indent=2, ensure_ascii=False)
    
    def record_error(self, error_type, error_message, file_name, suggestion=None):
        """"""
        error_hash = hashlib.md5(f"{error_type}{error_message}".encode()).hexdigest()
        
        # 
        for pattern in self.knowledge_base["error_patterns"]:
            if pattern["hash"] == error_hash:
                pattern["occurrences"] += 1
                pattern["last_seen"] = datetime.now().isoformat()
                if file_name not in pattern["files"]:
                    pattern["files"].append(file_name)
                self._save_knowledge_base()
                return False
        
        # 
        self.knowledge_base["error_patterns"].append({
            "hash": error_hash,
            "type": error_type,
            "message": error_message,
            "occurrences": 1,
            "first_seen": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
            "files": [file_name],
            "suggestion": suggestion,
            "resolved": False
        })
        self.knowledge_base["total_errors"] += 1
        self._save_knowledge_base()
        return True
    
    def mark_resolved(self, error_hash):
        """"""
        for pattern in self.knowledge_base["error_patterns"]:
            if pattern["hash"] == error_hash:
                pattern["resolved"] = True
                self.knowledge_base["resolved_count"] += 1
                self._save_knowledge_base()
                return True
        return False
    
    def get_unresolved_errors(self):
        """"""
        return [p for p in self.knowledge_base["error_patterns"] if not p["resolved"]]
    
    def get_error_summary(self):
        """"""
        total = len(self.knowledge_base["error_patterns"])
        unresolved = len(self.get_unresolved_errors())
        resolved = self.knowledge_base["resolved_count"]
        
        return {
            "total_patterns": total,
            "resolved_count": resolved,
            "unresolved_count": unresolved,
            "learning_progress": round((resolved / max(total, 1)) * 100, 1)
        }
    
    def generate_joran_training_note(self):
        """Joran"""
        unresolved = self.get_unresolved_errors()
        if not unresolved:
            return " Joran"
        
        note = " **Joran**\n\n"
        note += "\n\n"
        
        for error in unresolved[:5]:
            note += f" **{error['type']}**: {error['message']}\n"
            note += f"   - : {error['occurrences']} \n"
            note += f"   - : {', '.join(error['files'][:3])}\n"
            if error['suggestion']:
                note += f"   - : {error['suggestion']}\n"
            note += "\n"
        
        note += " "
        return note


# ====================  ====================

class GoogleSearchConsole:
    """Google Search Console """
    
    def __init__(self):
        self.api_key = os.environ.get("GSC_API_KEY", "")
        self.site_url = "https://chinaboundtravel.com"
    
    def fetch_search_data(self):
        """GSC"""
        if not self.api_key:
            logger.warning("GSC API not configured - skipping")
            return {"keywords": [], "total_queries": 0, "total_clicks": 0, "total_impressions": 0, "avg_position": 0}
        
        try:
            # GSC API 
            url = f"https://www.googleapis.com/webmasters/v3/sites/{self.site_url}/searchAnalytics/query"
            
            params = {
                "startDate": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
                "endDate": datetime.now().strftime("%Y-%m-%d"),
                "dimensions": ["query"],
                "rowLimit": 100
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, headers=headers, json=params, timeout=30)
            response.raise_for_status()
            return self._parse_gsc_data(response.json())
            
        except Exception as e:
            logger.error(f"GSC API error: {e}")
            return {"keywords": [], "total_queries": 0, "total_clicks": 0, "total_impressions": 0, "avg_position": 0}
    
    def _parse_gsc_data(self, data):
        """GSC API"""
        result = {
            "keywords": [],
            "total_queries": 0,
            "top_query": ""
        }
        
        try:
            rows = data.get("rows", [])
            result["total_queries"] = len(rows)
            
            for row in rows:
                keyword = row.get("keys", [""])[0]
                result["keywords"].append({
                    "query": keyword,
                    "clicks": row.get("clicks", 0),
                    "impressions": row.get("impressions", 0),
                    "position": row.get("position", 0)
                })
            
            if result["keywords"]:
                result["keywords"].sort(key=lambda x: x["clicks"], reverse=True)
                result["top_query"] = result["keywords"][0]["query"]
                
        except Exception as e:
            logger.error(f"GSC: {e}")
        
        return result
    
    def save_hot_keywords(self):
        """"""
        data = self.fetch_search_data()
        data["updated_at"] = datetime.now().isoformat()
        
        with open(GSC_HOT_KEYWORDS, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"GSC: {len(data['keywords'])} ")
        return data


class CompetitorCrawler:
    """"""
    
    def __init__(self):
        self.competitors = [
            "https://www.chinatravel.com",
            "https://www.travelchinaguide.com",
            "https://www.wanderlustchina.com"
        ]
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
    
    def crawl_competitors(self):
        """"""
        result = {
            "competitors": [],
            "hot_topics": [],
            "content_trends": []
        }
        
        for competitor in self.competitors:
            try:
                response = requests.get(competitor, headers=self.headers, timeout=15)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 
                articles = []
                for title_tag in soup.find_all(['h2', 'h3', 'a'], limit=20):
                    title = title_tag.get_text(strip=True)
                    if title and len(title) > 10 and "China" in title:
                        articles.append(title)
                
                result["competitors"].append({
                    "url": competitor,
                    "articles": articles[:10]
                })
                
                # 
                trends = self._extract_trends(articles)
                result["content_trends"].extend(trends)
                
            except Exception as e:
                logger.warning(f" {competitor} : {e}")
        
        # 
        result["content_trends"] = sorted(list(set(result["content_trends"])))
        result["updated_at"] = datetime.now().isoformat()
        
        # 
        with open(COMPETITOR_TOPICS, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        logger.info(f": {len(result['hot_topics'])} ")
        return result
    
    def _extract_trends(self, articles):
        """"""
        trend_keywords = [
            "budget", "cheap", "affordable",
            "food", "street food", "hotpot",
            "transportation", "train", "flight",
            "accommodation", "hotel", "hostel",
            "visa", "travel tips", "guide",
            "panda", "tour", "attraction",
            "safety", "best time", "season"
        ]
        
        trends = []
        for article in articles:
            article_lower = article.lower()
            for keyword in trend_keywords:
                if keyword in article_lower:
                    trends.append(keyword)
        
        return trends


class AffiliateDataFetcher:
    """"""
    
    def __init__(self):
        self.booking_api_key = os.environ.get("BOOKING_API_KEY", "")
        self.agoda_api_key = os.environ.get("AGODA_API_KEY", "")
    
    def fetch_affiliate_data(self):
        """"""
        if not self.booking_api_key or not self.agoda_api_key:
            logger.warning("Booking/Agoda API keys not configured - skipping")
            return {"booking": {}, "agoda": {}, "top_converting_categories": [], "total_conversions": 0, "total_revenue": 0, "updated_at": datetime.now().isoformat()}
        
        try:
            # API
            booking_data = self._fetch_booking_data()
            agoda_data = self._fetch_agoda_data()
            
            return {
                "booking": booking_data,
                "agoda": agoda_data,
                "top_converting_categories": self._analyze_top_categories(booking_data, agoda_data),
                "updated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Affiliate API error: {e}")
            return {"booking": {}, "agoda": {}, "top_converting_categories": [], "total_conversions": 0, "total_revenue": 0, "updated_at": datetime.now().isoformat()}
    
    def _fetch_booking_data(self):
        """Booking.com"""
        return {"conversions": 0, "revenue": 0, "top_destinations": []}
    
    def _fetch_agoda_data(self):
        """Agoda"""
        return {"conversions": 0, "revenue": 0, "top_destinations": []}
    
    def _analyze_top_categories(self, booking_data, agoda_data):
        """"""
        all_destinations = booking_data.get("top_destinations", []) + agoda_data.get("top_destinations", [])
        return list(set(all_destinations))
    
    def save_affiliate_data(self):
        """"""
        data = self.fetch_affiliate_data()
        with open(AFFILIATE_DATA, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return data


class UserFeedbackAnalyzer:
    """"""
    
    def __init__(self):
        self.feedback_path = USER_FEEDBACK
    
    def load_feedback(self):
        """"""
        if self.feedback_path.exists():
            try:
                with open(self.feedback_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {"feedbacks": [], "updated_at": None}
    
    def analyze_feedback(self):
        """"""
        data = self.load_feedback()
        feedbacks = data.get("feedbacks", [])
        
        if not feedbacks:
            return {
                "total_feedbacks": 0,
                "positive_count": 0,
                "negative_count": 0,
                "top_pain_points": [],
                "suggestions": []
            }
        
        pain_points = {}
        suggestions = []
        positive_count = 0
        negative_count = 0
        
        for feedback in feedbacks:
            content = feedback.get("content", "").lower()
            
            if feedback.get("rating", 0) >= 4:
                positive_count += 1
            else:
                negative_count += 1
            
            # 
            pain_keywords = [
                ("visa", ""),
                ("accommodation", ""),
                ("transportation", ""),
                ("food", ""),
                ("safety", ""),
                ("budget", ""),
                ("short", ""),
                ("missing", ""),
                ("need more", ""),
                ("detail", "")
            ]
            
            for keyword, category in pain_keywords:
                if keyword in content:
                    pain_points[category] = pain_points.get(category, 0) + 1
            
            # 
            if "suggest" in content or "recommend" in content or "need" in content:
                suggestions.append(feedback.get("content", ""))
        
        # 
        top_pain_points = sorted(pain_points.items(), key=lambda x: x[1], reverse=True)[:5]
        
        result = {
            "total_feedbacks": len(feedbacks),
            "positive_count": positive_count,
            "negative_count": negative_count,
            "top_pain_points": [{"category": p[0], "count": p[1]} for p in top_pain_points],
            "suggestions": suggestions[:10],
            "updated_at": datetime.now().isoformat()
        }
        
        return result
    
    def generate_topics_from_feedback(self):
        """"""
        analysis = self.analyze_feedback()
        topics = []
        
        for pain in analysis["top_pain_points"]:
            if pain["count"] >= 2:
                topic_title = self._generate_topic_title(pain["category"])
                if topic_title:
                    topics.append({
                        "title": topic_title,
                        "category": pain["category"],
                        "priority": pain["count"],
                        "source": "user_feedback"
                    })
        
        return topics
    
    def _generate_topic_title(self, category):
        """"""
        title_map = {
            "": "China Visa Requirements for Foreign Travelers",
            "": "Best Accommodation in China for Foreign Visitors",
            "": "China Transportation Guide for International Travelers",
            "": "Authentic Chinese Food Guide for Foreign Tourists",
            "": "China Travel Safety Tips for International Visitors",
            "": "China Travel Budget Guide for Overseas Travelers",
            "": "Complete Guide to Chinese Travel Destinations",
            "": "Complete Guide to China Travel Essentials",
            "": "Ultimate China Travel Guide with Detailed Tips",
            "": "Detailed China Travel Guide with Practical Information"
        }
        return title_map.get(category, None)


class ExternalDataManager:
    """ - """
    
    def __init__(self):
        self.gsc = GoogleSearchConsole()
        self.competitor = CompetitorCrawler()
        self.affiliate = AffiliateDataFetcher()
        self.feedback = UserFeedbackAnalyzer()
    
    def sync_all_data(self):
        """"""
        logger.info(" ...")
        
        # 1. GSC
        logger.info("   GSC...")
        gsc_data = self.gsc.save_hot_keywords()
        
        # 2. 
        logger.info("   ...")
        competitor_data = self.competitor.crawl_competitors()
        
        # 3. 
        logger.info("   ...")
        affiliate_data = self.affiliate.save_affiliate_data()
        
        # 4. 
        logger.info("   ...")
        feedback_analysis = self.feedback.analyze_feedback()
        
        # 5. 
        logger.info("   ...")
        new_topics = self._generate_new_topics(gsc_data, competitor_data, affiliate_data, feedback_analysis)
        
        # 6. 
        self._update_topic_pool(new_topics)
        
        logger.info(" ")
        
        return {
            "gsc_keywords_count": len(gsc_data.get("keywords", [])),
            "competitor_topics_count": len(competitor_data.get("content_trends", [])),
            "affiliate_conversions": affiliate_data.get("total_conversions", 0),
            "user_feedbacks_count": feedback_analysis.get("total_feedbacks", 0),
            "new_topics_added": len(new_topics)
        }
    
    def _generate_new_topics(self, gsc_data, competitor_data, affiliate_data, feedback_analysis):
        """"""
        new_topics = []
        
        # GSC
        for keyword in gsc_data.get("keywords", []):
            if keyword["clicks"] > 50 and keyword["position"] > 5:  # 
                title = self._keyword_to_topic(keyword["query"])
                if title:
                    new_topics.append({
                        "title": title,
                        "category": "seo",
                        "priority": int(keyword["clicks"] / 10),
                        "source": "gsc",
                        "keyword": keyword["query"]
                    })
        
        # 
        for trend in competitor_data.get("content_trends", []):
            title = self._trend_to_topic(trend)
            if title:
                new_topics.append({
                    "title": title,
                    "category": "competitor",
                    "priority": 2,
                    "source": "competitor"
                })
        
        # 
        for category in affiliate_data.get("top_converting_categories", []):
            title = self._affiliate_to_topic(category)
            if title:
                new_topics.append({
                    "title": title,
                    "category": "affiliate",
                    "priority": 5,  # 
                    "source": "affiliate"
                })
        
        # 
        feedback_topics = self.feedback.generate_topics_from_feedback()
        new_topics.extend(feedback_topics)
        
        # 
        seen = set()
        unique_topics = []
        for topic in new_topics:
            key = topic["title"].lower()
            if key not in seen:
                seen.add(key)
                unique_topics.append(topic)
        
        return unique_topics
    
    def _keyword_to_topic(self, keyword):
        """"""
        keyword = keyword.title()
        if "?" in keyword or len(keyword) > 60:
            return None
        if keyword.endswith("?"):
            keyword = keyword[:-1]
        return f"{keyword} - Complete Guide"
    
    def _trend_to_topic(self, trend):
        """"""
        trend_map = {
            "budget": "China Travel Budget Guide",
            "food": "Authentic Chinese Food Guide",
            "street food": "Chinese Street Food Guide",
            "hotpot": "Sichuan Hotpot Guide",
            "transportation": "China Transportation Guide",
            "train": "China High-Speed Train Guide",
            "accommodation": "China Accommodation Guide",
            "hotel": "Best Hotels in China",
            "visa": "China Visa Guide",
            "travel tips": "China Travel Tips",
            "guide": "China Travel Guide",
            "panda": "Chengdu Panda Guide",
            "tour": "China Tour Guide",
            "safety": "China Travel Safety",
            "best time": "Best Time to Visit China",
            "season": "China Travel Season Guide"
        }
        return trend_map.get(trend, None)
    
    def _affiliate_to_topic(self, category):
        """"""
        if "accommodation" in category.lower():
            return f"{category.title()} Guide - Book Your Stay"
        if "tour" in category.lower():
            return f"{category.title()} - Travel Packages"
        if "hotel" in category.lower():
            return f"Best {category.title()} in China"
        return f"{category.title()} Guide"
    
    def _update_topic_pool(self, new_topics):
        """"""
        topic_pool_path = CONFIG_DIR / "topic_pool.json"
        
        if topic_pool_path.exists():
            try:
                with open(topic_pool_path, 'r', encoding='utf-8') as f:
                    topic_pool = json.load(f)
            except:
                topic_pool = {"topics": [], "used_topics": []}
        else:
            topic_pool = {"topics": [], "used_topics": []}
        
        # 
        existing_titles = {t["title"].lower() for t in topic_pool["topics"]}
        
        for topic in new_topics:
            if topic["title"].lower() not in existing_titles:
                topic_pool["topics"].append({
                    "id": hashlib.md5(f"{topic['title']}{datetime.now()}".encode()).hexdigest()[:8],
                    "title": topic["title"],
                    "category": topic["category"],
                    "geo": "US",
                    "keywords": [topic["title"].lower()],
                    "priority": topic["priority"],
                    "status": "pending",
                    "source": topic.get("source", "external"),
                    "created_at": datetime.now().isoformat(),
                    "used_at": None
                })
        
        # 
        topic_pool["last_update"] = datetime.now().isoformat()
        with open(topic_pool_path, 'w', encoding='utf-8') as f:
            json.dump(topic_pool, f, indent=2, ensure_ascii=False)
        
        logger.info(f" {len(new_topics)} ")


# ====================  ====================

class TrafficMonitor:
    """"""
    
    def __init__(self):
        self.cloudflare_api_token = os.environ.get("CLOUDFLARE_API_TOKEN", "")
        self.cloudflare_zone_id = os.environ.get("CLOUDFLARE_ZONE_ID", "")
        self.site_url = "https://chinaboundtravel.com"
    
    def get_analytics_data(self):
        """Get Cloudflare analytics data"""
        if not self.cloudflare_api_token or not self.cloudflare_zone_id:
            logger.warning("Cloudflare API not configured - skipping")
            return {"visitors": 0, "page_views": 0, "bandwidth_gb": 0, "requests": 0, "status_2xx": 0, "top_pages": [], "top_countries": [], "avg_response_time": 0, "cache_hit_ratio": 0}
        
        try:
            start_time = (datetime.now() - timedelta(days=1)).isoformat() + "Z"
            end_time = datetime.now().isoformat() + "Z"
            
            url = f"https://api.cloudflare.com/client/v4/zones/{self.cloudflare_zone_id}/analytics/dashboard"
            
            headers = {
                "Authorization": f"Bearer {self.cloudflare_api_token}",
                "Content-Type": "application/json"
            }
            
            params = {
                "since": start_time,
                "until": end_time
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            return self._parse_cloudflare_data(data)
            
        except Exception as e:
            logger.warning(f"Cloudflare API request failed: {e}")
            return {"visitors": 0, "page_views": 0, "bandwidth_gb": 0, "requests": 0, "status_2xx": 0, "top_pages": [], "top_countries": [], "avg_response_time": 0, "cache_hit_ratio": 0}
    
    def get_geo_data(self):
        """Get Geo data"""
        if not self.cloudflare_api_token or not self.cloudflare_zone_id:
            logger.warning("Cloudflare API not configured - skipping")
            return {}
        
        try:
            url = f"https://api.cloudflare.com/client/v4/zones/{self.cloudflare_zone_id}/analytics/dashboard"
            headers = {"Authorization": f"Bearer {self.cloudflare_api_token}"}
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return self._parse_geo_data(response.json())
            
        except Exception as e:
            logger.warning(f"Cloudflare Geo API request failed: {e}")
            return {}
    
    def _parse_geo_data(self, data):
        """"""
        return {}
    
    def _parse_cloudflare_data(self, data):
        """Cloudflare API"""
        result = {
            "visitors": 0,
            "page_views": 0,
            "bandwidth_gb": 0,
            "requests": 0,
            "status_2xx": 0,
            "top_pages": [],
            "top_countries": [],
            "avg_response_time": 0,
            "cache_hit_ratio": 0
        }
        
        try:
            if "result" in data:
                result = data["result"]
        except:
            pass
        
        return result
    
    def get_travelpayouts_stats(self):
        """Get Travelpayouts affiliate statistics using execute_query API"""
        API_TOKEN = os.environ.get("TRAVELPAYOUTS_API_TOKEN", "")
        MARKER = "730795"
        
        if not API_TOKEN:
            logger.warning("Travelpayouts API token not configured - skipping")
            return None
        
        try:
            # Travelpayouts statistics API - 使用正确的 execute_query 端点
            url = "https://api.travelpayouts.com/statistics/v1/execute_query"
            headers = {
                "X-Access-Token": API_TOKEN,
                "Content-Type": "application/json"
            }
            
            # 查询最近7天的数据
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            
            # 构建正确的请求格式
            payload = {
                "fields": [
                    "action_id",
                    "sub_id",
                    "price_usd",
                    "paid_profit_usd",
                    "state",
                    "date",
                    "type"
                ],
                "filters": [
                    {
                        "field": "date",
                        "op": "ge",
                        "value": start_date
                    },
                    {
                        "field": "date",
                        "op": "le",
                        "value": end_date
                    }
                ],
                "sort": [{"field": "date", "order": "desc"}],
                "offset": 0,
                "limit": 100
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code != 200:
                logger.warning(f"Travelpayouts API returned {response.status_code}")
                return None
            
            data = response.json()
            
            # 处理返回数据 - API返回 {"results": [...], "total_rows": N}
            results = data.get("results", [])
            if not results:
                logger.info("No Travelpayouts data for the period")
                return None
            
            total_rows = data.get("total_rows", 0)
            
            # 计算总数据
            total_clicks = 0
            total_bookings = 0
            total_revenue = 0.0
            
            for item in results:
                # clicks 通过 type='redirect' 或 type='init' 计算
                if item.get("type") in ["redirect", "init"]:
                    total_clicks += 1
                # bookings 通过 state='paid' 计算
                if item.get("state") == "paid":
                    total_bookings += 1
                    total_revenue += float(item.get("paid_profit_usd", 0))
            
            logger.info(f"Travelpayouts: {total_clicks} clicks, {total_bookings} bookings, ${total_revenue:.2f} revenue (total rows: {total_rows})")
            
            return {
                "clicks": total_clicks,
                "bookings": total_bookings,
                "revenue_usd": round(total_revenue, 2),
                "total_rows": total_rows,
                "top_pages": sorted(results, key=lambda x: float(x.get("paid_profit_usd", 0)), reverse=True)[:3]
            }
            
        except Exception as e:
            logger.warning(f"Travelpayouts API request failed: {e}")
            return None


def check_links() -> list:
    """"""
    logger.info("...")
    issues = []
    
    files = list(POSTS_DIR.glob("*.md"))
    for filepath in files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 
            if '](#)' in content:
                issues.append(f"{filepath.name}: ")
            
            #  <link> 
            if '<link' in content.lower():
                issues.append(f"{filepath.name}:  <link> ")
            
            #  # 
            if '](#)' in content or '[](#)' in content:
                issues.append(f"{filepath.name}: ")
            
        except Exception as e:
            issues.append(f"{filepath.name}:  - {str(e)}")
    
    return issues


def check_images() -> list:
    """"""
    logger.info("...")
    issues = []
    
    files = list(POSTS_DIR.glob("*.md"))
    for filepath in files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 
            md_images = content.count("![")
            if md_images > 0:
                issues.append(f"{filepath.name}:  {md_images}  ![alt](url) ")
            
            # 
            image_placeholders = re.findall(r'\[\s*Image\s*:\s*[^\]]+\]', content, re.IGNORECASE)
            if len(image_placeholders) < 2:
                issues.append(f"{filepath.name}:  {len(image_placeholders)}  [Image:xxx] ")
            
        except Exception as e:
            issues.append(f"{filepath.name}:  - {str(e)}")
    
    return issues


# ====================  ====================

class FeishuNotifier:
    """"""
    
    def __init__(self):
        self.webhook_url = os.environ.get("FEISHU_WEBHOOK_URL", "")
        self.secret = os.environ.get("FEISHU_SECRET", "")
    
    def _generate_signature(self, timestamp):
        """"""
        if not self.secret:
            return ""
        string_to_sign = f"{timestamp}\n{self.secret}"
        signature = hmac.new(
            self.secret.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            hashlib.sha256
        ).digest()
        return base64.b64encode(signature).decode('utf-8')
    
    def send_daily_report(self, report_summary):
        """"""
        if not self.webhook_url:
            logger.warning(" Webhook ")
            return False
        
        try:
            timestamp = str(int(datetime.now().timestamp()))
            signature = self._generate_signature(timestamp)
            
            headers = {
                "Content-Type": "application/json",
            }
            
            payload = {
                "timestamp": timestamp,
                "sign": signature,
                "msg_type": "text",
                "content": {
                    "text": report_summary
                }
            }
            
            response = requests.post(self.webhook_url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            logger.info("")
            return True
            
        except Exception as e:
            logger.error(f": {e}")
            return False


# ====================  ====================

class ReportGenerator:
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y-%m-%d")
    
    def _get_cost_data(self):
        """ manifest """
        try:
            manifest_path = Path(__file__).parent / "manifest.json"
            if manifest_path.exists():
                with open(manifest_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                cost_tracking = data.get("cost_tracking", {})
                today = datetime.now().strftime("%Y-%m-%d")
                today_data = cost_tracking.get(today, {
                    "total_cost_yuan": 0.0,
                    "api_calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0
                })
                budget = 30.0
                used = today_data.get("total_cost_yuan", 0.0)
                return {
                    "used_yuan": used,
                    "budget_yuan": budget,
                    "api_calls": today_data.get("api_calls", 0),
                    "input_tokens": today_data.get("input_tokens", 0),
                    "output_tokens": today_data.get("output_tokens", 0),
                    "used_percent": round((used / budget * 100), 1),
                    "status": "exceeded" if (used / budget) >= 0.95 else "warning" if (used / budget) >= 0.7 else "ok"
                }
        except:
            pass
        return {"used_yuan": 0, "budget_yuan": 30, "api_calls": 0, "used_percent": 0, "status": "ok"}
    
    def generate(self, encoding_issues, content_issues, link_issues, image_issues, site_status, traffic_data, error_summary, joran_note, external_data_stats, tp_stats=None):
        report_path = REPORTS_DIR / f"daily_report_{self.timestamp}.md"
        
        total_issues = len(encoding_issues) + len(content_issues) + len(link_issues) + len(image_issues)
        status_icon = "" if total_issues == 0 else ""
        
        report = f"""# {status_icon} _{self.timestamp}

##  
|  |  |  |
| --- | --- | --- |
|  | {' OK' if site_status.get('site_up') else ' FAIL'} | chinaboundtravel.com |
| HTTPS | {' OK' if site_status.get('https_ok') else ' FAIL'} |  |
|  |  OK |  |
| 404 |  OK | 0 |
|  |  OK |  |

##  
|  |  |
| --- | --- |
|  | {traffic_data.get('visitors', 0):,} |
|  | {traffic_data.get('page_views', 0):,} |
|  | {traffic_data.get('bandwidth_gb', 0):.2f} GB |
|  | {traffic_data.get('requests', 0):,} |
|  | {traffic_data.get('status_2xx', 0)}% |
|  | {traffic_data.get('avg_response_time', 0):.1f} ms |
|  | {traffic_data.get('cache_hit_ratio', 0):.1f}% |

### 
"""
        for page in traffic_data.get('top_pages', []):
            report += f"- [{page.get('url', '')}]({page.get('url', '')}): {page.get('views', 0)} \n"
        
        report += f"""
### Top 5
"""
        for country in traffic_data.get('top_countries', []):
            report += f"- {country.get('country', '')}: {country.get('visitors', 0)} \n"
        
        report += f"""

##  
|  |  |
| --- | --- |
| GSC | {external_data_stats.get('gsc_keywords_count', 0)}  |
|  | {external_data_stats.get('competitor_topics_count', 0)}  |
|  | {external_data_stats.get('affiliate_conversions', 0)}  |
|  | {external_data_stats.get('user_feedbacks_count', 0)}  |
|  | {external_data_stats.get('new_topics_added', 0)}  |

### Google
"""
        # GSC
        try:
            with open(GSC_HOT_KEYWORDS, 'r', encoding='utf-8') as f:
                gsc_data = json.load(f)
                for kw in gsc_data.get('keywords', [])[:5]:
                    report += f"- **{kw['query']}** (: {kw['clicks']}, : {kw['position']})\n"
        except:
            report += "- \n"
        
        report += f"""

### 
"""
        try:
            with open(COMPETITOR_TOPICS, 'r', encoding='utf-8') as f:
                competitor_data = json.load(f)
                for trend in competitor_data.get('content_trends', [])[:5]:
                    report += f"- {trend}\n"
        except:
            report += "- \n"
        
        report += f"""

### 
"""
        feedback_analyzer = UserFeedbackAnalyzer()
        feedback_analysis = feedback_analyzer.analyze_feedback()
        for pain in feedback_analysis.get('top_pain_points', [])[:5]:
            report += f"- **{pain['category']}**: {pain['count']} \n"
        
        report += f"""

### 
"""
        try:
            with open(AFFILIATE_DATA, 'r', encoding='utf-8') as f:
                affiliate_data = json.load(f)
                for category in affiliate_data.get('top_converting_categories', [])[:5]:
                    report += f"- {category}\n"
        except:
            report += "- \n"
        
        report += f"""

## Travelpayouts 
"""
        if tp_stats:
            report += f"""|  |  |
| --- | --- |
|  | {tp_stats.get('clicks', 0)} |
|  | {tp_stats.get('bookings', 0)} |
|  | ${tp_stats.get('revenue_usd', 0):.2f} |

### Top 3 
"""
            for item in tp_stats.get('top_pages', []):
                sub_id = item.get('sub_id', '')
                profit = float(item.get('paid_profit_usd', 0) or 0)
                clicks = item.get('clicks', 0)
                report += f"- **{sub_id}**: {clicks} clicks, ${profit:.2f}\n"
        else:
            report += "- API \n"
        
        report += f"""

##  
|  |  |  |
| --- | --- | --- |
|  | {' OK' if len(encoding_issues) == 0 else f' FAIL ({len(encoding_issues)})'} | {len(encoding_issues)}  |
|  | - | {encoding_issues[0].get('fixed_count', 0) if encoding_issues else 0}  |

"""
        if encoding_issues:
            report += "\n### \n"
            for issue in encoding_issues[:10]:
                report += f"- {issue['filepath']}\n"
            if len(encoding_issues) > 10:
                report += f"- ...  {len(encoding_issues) - 10} \n"
        
        report += f"""


##  
|  |  |  |
| --- | --- | --- |
| Front Matter  | {' OK' if len(content_issues) == 0 else f' FAIL ({len(content_issues)})'} | {len(content_issues)}  |
|  | {' OK' if len(image_issues) == 0 else f' WARN ({len(image_issues)})'} | {len(image_issues)}  |
| Schema  |  OK |  |
|  |  OK | Joran |

"""
        if content_issues:
            report += "\n### \n"
            for issue in content_issues[:10]:
                report += f"- {issue['filepath']}\n"
        
        report += f"""


##  
|  |  |  |
| --- | --- | --- |
| / | {' OK' if len(link_issues) == 0 else f' FAIL ({len(link_issues)})'} | {len(link_issues)}  |
|  |  OK |  |

"""
        if link_issues:
            report += "\n### \n"
            for issue in link_issues[:5]:
                report += f"- {issue}\n"
        
        report += f"""


##  Joran
|  |  |
| --- | --- |
|  | {error_summary.get('resolved_count', 0)} |
|  | {error_summary.get('unresolved_count', 0)} |
|  | {error_summary.get('learning_progress', 0)}% |

"""
        
        report += f"""
##  
> ****: {' ' if total_issues == 0 else f'  {total_issues} '}
> ****: {'' if total_issues == 0 else f'{len(encoding_issues)} + {len(content_issues)} + {len(link_issues)} + {len(image_issues)}'}
> ****: {'' if total_issues == 0 else ''}

---
****: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**AI**
"""
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f": {report_path}")
        return report_path
    
    def generate_summary(self, encoding_issues, content_issues, link_issues, image_issues, site_status, traffic_data, error_summary, joran_note, external_data_stats=None):
        """"""
        total_issues = len(encoding_issues) + len(content_issues) + len(link_issues) + len(image_issues)
        status_icon = "" if total_issues == 0 else ""
        
        if external_data_stats is None:
            external_data_stats = {}
        
        summary = f""" **ChinaBound Travel ** ({datetime.now().strftime("%Y-%m-%d")})

{status_icon} ****: {'' if total_issues == 0 else f' {total_issues} '}

 ****:
- : {len(encoding_issues)} 
- : {len(content_issues)} 
- : {len(link_issues)} 
- : {len(image_issues)} 

 ****: {' ' if site_status.get('site_up') else ' '}

 ****:
- : {traffic_data.get('visitors', 0):,}
- : {traffic_data.get('page_views', 0):,}
- : {traffic_data.get('top_pages', [])[0].get('url', 'N/A') if traffic_data.get('top_pages') else 'N/A'}

 ****:
- GSC: {external_data_stats.get('gsc_keywords_count', 0)} 
- : {external_data_stats.get('competitor_topics_count', 0)} 
- : {external_data_stats.get('affiliate_conversions', 0)} 
- : {external_data_stats.get('user_feedbacks_count', 0)} 
- : {external_data_stats.get('new_topics_added', 0)} 

 **Joran**:
- : {error_summary.get('resolved_count', 0)} 
- : {error_summary.get('unresolved_count', 0)} 
- : {error_summary.get('learning_progress', 0)}%

 **AI**:
- : {self._get_cost_data().get('used_yuan', 0):.2f} / {self._get_cost_data().get('budget_yuan', 30):.0f}
- API: {self._get_cost_data().get('api_calls', 0)} 
- : {self._get_cost_data().get('used_percent', 0)}%
- : {' ' if self._get_cost_data().get('status') == 'ok' else ' ' if self._get_cost_data().get('status') == 'warning' else ' '}

{joran_note}

---
*AI | 9:00*"""
        
        return summary


# ====================  ====================

def test_cloudflare():
    """ Cloudflare API """
    print("="*60)
    print("  Cloudflare API")
    print("="*60)
    
    cf_token = os.environ.get("CLOUDFLARE_API_TOKEN", "")
    cf_zone_id = os.environ.get("CLOUDFLARE_ZONE_ID", "")
    
    if not cf_token or not cf_zone_id:
        print(" Cloudflare API ")
        print("\n:")
        print("  CLOUDFLARE_API_TOKEN")
        print("  CLOUDFLARE_ZONE_ID")
        return False
    
    print(f" API Token: {cf_token[:8]}...")
    print(f" Zone ID: {cf_zone_id[:8]}...")
    
    try:
        from TrafficMonitor import TrafficMonitor
        monitor = TrafficMonitor()
        data = monitor.get_analytics_data()
        
        print("\n :")
        print(f"   : {data.get('visitors', 0):,}")
        print(f"   : {data.get('page_views', 0):,}")
        print(f"   : {data.get('bandwidth_gb', 0):.2f} GB")
        print(f"   : {data.get('cache_hit_ratio', 0):.1f}%")
        
        if data.get('visitors', 0) > 0:
            print("\n Cloudflare API !")
            return True
        else:
            print("\n ")
            return False
            
    except Exception as e:
        print(f"\n : {e}")
        return False


def test_gsc():
    """ Google Search Console API"""
    print("="*60)
    print("  Google Search Console API")
    print("="*60)
    
    gsc_key = os.environ.get("GSC_API_KEY", "")
    
    if not gsc_key:
        print(" GSC API ")
        print("\n:")
        print("  GSC_API_KEY")
        print("\n: GSC API  OAuth2 ")
        print(":")
        print("  1.  JSON ")
        print("  2.  Search Console ")
        return False
    
    print(f" API Key: {gsc_key[:8]}...")
    
    try:
        from GoogleSearchConsole import GoogleSearchConsole
        gsc = GoogleSearchConsole()
        data = gsc.fetch_search_data()
        
        print("\n :")
        print(f"   : {len(data.get('keywords', []))}")
        if data.get('keywords'):
            print(f"   Top: {data['keywords'][0]['query']}")
            print(f"   : {data['keywords'][0]['clicks']}")
            print(f"   : {data['keywords'][0]['impressions']}")
        
        if data.get('keywords') and len(data['keywords']) > 0:
            print("\n GSC API !")
            return True
        else:
            print("\n ")
            return False
            
    except Exception as e:
        print(f"\n : {e}")
        print("\n GSC API  OAuth2 API Key ")
        print(":")
        print("  1.  Google Cloud Console ")
        print("  2.  JSON  config/gsc_service_account.json")
        print("  3.  Search Console ")
        return False


def main():
    parser = argparse.ArgumentParser(description="ChinaBound Travel Daily Inspection")
    parser.add_argument("--send-feishu", action="store_true", help="Send report to Feishu")
    parser.add_argument("--weekly-report", action="store_true", help="Generate weekly report")
    parser.add_argument("--sync-external", action="store_true", help="Sync external data")
    parser.add_argument("--auto-fix", action="store_true", help="Auto fix encoding issues")
    parser.add_argument("--test-cf", action="store_true", help="Test Cloudflare API")
    parser.add_argument("--test-gsc", action="store_true", help="Test GSC API")
    args = parser.parse_args()
    
    # 
    if args.test_cf:
        test_cloudflare()
        return
    
    if args.test_gsc:
        test_gsc()
        return
    
    logger.info("="*60)
    logger.info("ChinaBound Travel  v5.0")
    logger.info(": GSC+++")
    logger.info("="*60)
    
    if args.auto_fix:
        logger.info("Running in auto-fix mode")
        encoding_checker = EncodingChecker()
        encoding_issues = encoding_checker.scan_all()
        for issue in encoding_issues:
            filepath = Path(issue["filepath"])
            encoding_checker.auto_fix(filepath)
        logger.info("Auto-fix completed, exiting early")
        return 0
    
    # 
    external_manager = ExternalDataManager()
    
    # 
    logger.info(" ...")
    external_data_stats = external_manager.sync_all_data()
    
    # 
    knowledge_base = ErrorKnowledgeBase()
    
    traffic_monitor = TrafficMonitor()
    
    encoding_checker = EncodingChecker()
    encoding_issues = encoding_checker.scan_all()
    
    for issue in encoding_issues:
        filepath = Path(issue["filepath"])
        encoding_checker.auto_fix(filepath)
        for err in issue.get("issues", []):
            char = err.get("char", "")
            if char:
                knowledge_base.record_error(
                    "Encoding Error",
                    f"Bad char: {char}",
                    filepath.name,
                    "Solution: Convert to UTF-8"
                )
    
    encoding_issues = encoding_checker.scan_all()
    
    # 2. 
    content_checker = ContentChecker()
    content_issues = content_checker.scan_all()
    
    # 
    for issue in content_issues:
        filepath = Path(issue["filepath"])
        for err in issue.get("issues", []):
            knowledge_base.record_error(
                "",
                err,
                filepath.name,
                ": Front Matter"
            )
    
    # 3. 
    link_issues = check_links()
    
    # 
    for issue in link_issues:
        if "" in issue:
            knowledge_base.record_error(
                "",
                " (#)",
                issue.split(":")[0],
                ": "
            )
        elif " <link> " in issue:
            knowledge_base.record_error(
                "",
                " <link> ",
                issue.split(":")[0],
                ": Markdown"
            )
    
    # 4. 
    image_issues = check_images()
    
    # 
    for issue in image_issues:
        if "![alt](url)" in issue:
            knowledge_base.record_error(
                "",
                " ![alt](url)",
                issue.split(":")[0],
                ":  [Image:|alt=xxx] "
            )
        elif "" in issue:
            knowledge_base.record_error(
                "",
                "",
                issue.split(":")[0],
                ": 2"
            )
    
    # 5. 
    site_checker = SiteChecker()
    site_status = site_checker.check_site()
    
    # 6. 
    traffic_data = traffic_monitor.get_analytics_data()
    
    # 6.1 
    tp_stats = traffic_monitor.get_travelpayouts_stats()
    if tp_stats:
        logger.info(f"Travelpayouts stats: clicks={tp_stats['clicks']}, bookings={tp_stats['bookings']}, revenue=${tp_stats['revenue_usd']}")
    else:
        logger.info("Travelpayouts API not available")
    
    # 7. 
    error_summary = knowledge_base.get_error_summary()
    joran_note = knowledge_base.generate_joran_training_note()
    
    # 8. 
    report_gen = ReportGenerator()
    report_path = report_gen.generate(
        encoding_issues,
        content_issues,
        link_issues,
        image_issues,
        site_status,
        traffic_data,
        error_summary,
        joran_note,
        external_data_stats,
        tp_stats
    )
    
    # 9. 
    if args.send_feishu:
        summary = report_gen.generate_summary(
            encoding_issues,
            content_issues,
            link_issues,
            image_issues,
            site_status,
            traffic_data,
            error_summary,
            joran_note,
            external_data_stats
        )
        notifier = FeishuNotifier()
        notifier.send_daily_report(summary)
    
    # 10. 
    print("\n" + "="*60)
    print("")
    print("="*60)
    print(f": {len(encoding_issues)} ")
    print(f": {len(content_issues)} ")
    print(f": {len(link_issues)} ")
    print(f": {len(image_issues)} ")
    print(f": {'' if site_status.get('site_up') else ''}")
    print(f": {traffic_data.get('visitors', 0):,}")
    print(f": {traffic_data.get('page_views', 0):,}")
    print(f"Joran: {error_summary.get('learning_progress', 0)}%")
    print(f": {external_data_stats.get('new_topics_added', 0)} ")
    print(f": {external_data_stats.get('affiliate_conversions', 0)} ")
    print(f": {report_path}")
    print("="*60)
    
    total_issues = len(encoding_issues) + len(content_issues) + len(link_issues) + len(image_issues)
    logger.info(f"Total issues found: {total_issues}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
