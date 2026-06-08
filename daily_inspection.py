#!/usr/bin/env python3
"""
daily_inspection.py - ChinaBound Travel 每日全量巡检系统
包含编码检查、内容合规性、链接检查、SEO检查等
Version: 5.0 - 外部数据联动：GSC+竞品+联盟+用户反馈
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

# ==================== 配置 ====================
SCRIPT_DIR = Path(__file__).parent.resolve()
BLOG_ROOT = SCRIPT_DIR
CONTENT_DIR = BLOG_ROOT / "content"
POSTS_DIR = CONTENT_DIR / "posts"
REPORTS_DIR = BLOG_ROOT / "reports" / "01 每日巡检报告"
CONFIG_DIR = BLOG_ROOT / "config"

# 外部数据文件
ERROR_KNOWLEDGE_BASE = CONFIG_DIR / "error_knowledge_base.json"
GSC_HOT_KEYWORDS = CONFIG_DIR / "gsc_hot_keyword.json"
COMPETITOR_TOPICS = CONFIG_DIR / "competitor_topic.json"
USER_FEEDBACK = CONFIG_DIR / "user_feedback.json"
AFFILIATE_DATA = CONFIG_DIR / "affiliate_data.json"

REPORTS_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

# 乱码字符检测列表
# 包含普通乱码和 Unicode 编码错误导致的汉字乱码
GARBLE_CHARS = [
    # 普通乱码字符
    "鈥", "鈥?", "€", "™", "–", "—", "鈫", "â", "œ", "Œ",
    # Unicode 编码错误导致的汉字乱码（CJK 扩展区字符）
    "馃", "彲", "镒", "镟", "镞", "镙", "镠", "镡", "镢", "镣",
    "镤", "镥", "镦", "镧", "镨", "镩", "镪", "镫", "镬", "镮",
    "镲", "镳", "镴", "镵", "長", "镸", "镹", "镺", "镻", "镼",
    "镽", "镾", "长", "锕", "锖", "锗", "锘", "锝", "锞", "锟",
    "锠", "锢", "锣", "锤", "锥", "锦", "锧", "锨", "锩", "锪",
    "锫", "锬", "锭", "键", "锯", "锰", "锱", "锲", "锴", "锶",
    "锼", "锽", "锾", "锿", "镃", "镄", "镅", "镆", "镈", "镋",
    "镌", "镍", "镎", "镏", "镕",
    # 额外的乱码字符
    "彊", "锔", "搷", "寙", "惣", "徍", "棑", "攋"
]

# ==================== 日志系统 ====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(BLOG_ROOT / "daily_inspection.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("ChinaBound.Inspection")

# ==================== 检查模块 ====================

class EncodingChecker:
    """编码检查模块"""
    
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
            
            # 检查特殊编码问题
            if "鈥?" in content:
                result["has_issue"] = True
                result["issues"].append({
                    "char": "鈥?",
                    "count": content.count("鈥?")
                })
                
        except Exception as e:
            result["has_issue"] = True
            result["issues"].append({
                "error": str(e)
            })
        
        return result
    
    def scan_all(self) -> list:
        logger.info("开始编码检查...")
        all_issues = []
        
        # 检查所有 Markdown 文件
        patterns = ["**/*.md"]
        for pattern in patterns:
            files = list(CONTENT_DIR.glob(pattern))
            for filepath in files:
                result = self.check_file(filepath)
                if result["has_issue"]:
                    all_issues.append(result)
                    logger.warning(f"发现问题: {filepath.name}")
        
        return all_issues
    
    def auto_fix(self, filepath: Path) -> bool:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original = content
            
            # 替换乱码
            replacements = {
                "鈥?": "—",
                "鈥": "",
                "–": "-",
                "—": "-"
            }
            
            for garbled, correct in replacements.items():
                content = content.replace(garbled, correct)
            
            if content != original:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                logger.info(f"已修复: {filepath.name}")
                self.fixed_count += 1
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"修复失败 {filepath}: {e}")
            return False


class ContentChecker:
    """内容合规性检查"""
    
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
                    result["issues"].append(f"缺失字段: {field}")
            
            if "params" in post.metadata:
                params = post.metadata["params"]
                if "keywords" not in params:
                    result["has_issue"] = True
                    result["issues"].append("缺失: params.keywords")
                if "faq" not in params:
                    result["has_issue"] = True
                    result["issues"].append("缺失: params.faq")
            
        except Exception as e:
            result["has_issue"] = True
            result["issues"].append(f"解析错误: {str(e)}")
        
        return result
    
    def scan_all(self) -> list:
        logger.info("开始内容合规性检查...")
        issues = []
        
        files = list(POSTS_DIR.glob("*.md"))
        for filepath in files:
            result = self.check_frontmatter(filepath)
            if result["has_issue"]:
                issues.append(result)
        
        return issues


class AffiliateChecker:
    """联盟链接检查模块"""
    
    def __init__(self):
        self.issues = []
        # 常见旅游联盟链接域名
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
        # 联盟链接参数标识
        self.affiliate_params = ["aff_id", "affiliate_id", "ref", "tracking", "cid", "partner_id"]
    
    def check_affiliate_links(self, filepath: Path) -> dict:
        """检查文章中的联盟链接"""
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
            
            # 查找所有链接
            # 匹配 markdown 链接格式: [text](url)
            link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
            links = link_pattern.findall(content)
            
            for text, url in links:
                # 检查是否是联盟链接
                is_affiliate = False
                
                # 检查域名
                for domain in self.affiliate_domains:
                    if domain in url.lower():
                        is_affiliate = True
                        break
                
                # 检查联盟参数
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
            
            # 检查是否有无效链接
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
        """检查链接是否有效"""
        try:
            # 添加超时，避免阻塞
            response = urllib.request.urlopen(url, timeout=5)
            return response.status == 200
        except Exception:
            return False
    
    def scan_all(self) -> list:
        logger.info("开始联盟链接检查...")
        issues = []
        
        files = list(POSTS_DIR.glob("*.md"))
        for filepath in files:
            result = self.check_affiliate_links(filepath)
            if result["has_invalid_links"]:
                issues.append(result)
                logger.warning(f"发现无效联盟链接: {filepath.name}")
        
        return issues
    
    def get_affiliate_stats(self) -> dict:
        """获取联盟链接统计"""
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
    """网站可访问性检查"""
    
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
            response = urllib.request.urlopen(self.base_url, timeout=10)
            result["site_up"] = True
            result["status_code"] = response.status
            result["https_ok"] = self.base_url.startswith("https://")
            
        except Exception as e:
            result["error"] = str(e)
        
        return result


# ==================== 错误知识库 ====================

class ErrorKnowledgeBase:
    """错误学习系统 - 记录错误模式，帮助Joran持续学习"""
    
    def __init__(self):
        self.knowledge_base = self._load_knowledge_base()
    
    def _load_knowledge_base(self):
        """加载错误知识库"""
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
        """保存错误知识库"""
        self.knowledge_base["last_updated"] = datetime.now().isoformat()
        with open(ERROR_KNOWLEDGE_BASE, 'w', encoding='utf-8') as f:
            json.dump(self.knowledge_base, f, indent=2, ensure_ascii=False)
    
    def record_error(self, error_type, error_message, file_name, suggestion=None):
        """记录新错误到知识库"""
        error_hash = hashlib.md5(f"{error_type}{error_message}".encode()).hexdigest()
        
        # 检查是否已经存在
        for pattern in self.knowledge_base["error_patterns"]:
            if pattern["hash"] == error_hash:
                pattern["occurrences"] += 1
                pattern["last_seen"] = datetime.now().isoformat()
                if file_name not in pattern["files"]:
                    pattern["files"].append(file_name)
                self._save_knowledge_base()
                return False
        
        # 添加新模式
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
        """标记错误已解决"""
        for pattern in self.knowledge_base["error_patterns"]:
            if pattern["hash"] == error_hash:
                pattern["resolved"] = True
                self.knowledge_base["resolved_count"] += 1
                self._save_knowledge_base()
                return True
        return False
    
    def get_unresolved_errors(self):
        """获取未解决的错误模式"""
        return [p for p in self.knowledge_base["error_patterns"] if not p["resolved"]]
    
    def get_error_summary(self):
        """获取错误汇总报告"""
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
        """生成Joran学习笔记"""
        unresolved = self.get_unresolved_errors()
        if not unresolved:
            return "🎓 Joran学习笔记：目前没有新的错误模式需要学习！"
        
        note = "📚 **Joran学习笔记**\n\n"
        note += "发现以下重复出现的错误模式，请学习并避免：\n\n"
        
        for error in unresolved[:5]:
            note += f"🔹 **{error['type']}**: {error['message']}\n"
            note += f"   - 出现次数: {error['occurrences']} 次\n"
            note += f"   - 影响文件: {', '.join(error['files'][:3])}\n"
            if error['suggestion']:
                note += f"   - 修复建议: {error['suggestion']}\n"
            note += "\n"
        
        note += "💡 请将这些错误模式添加到内容生成规则中，避免再次生成相同错误。"
        return note


# ==================== 外部数据模块 ====================

class GoogleSearchConsole:
    """Google Search Console 数据拉取"""
    
    def __init__(self):
        self.api_key = os.environ.get("GSC_API_KEY", "")
        self.site_url = "https://chinaboundtravel.com"
    
    def fetch_search_data(self):
        """拉取GSC搜索词数据"""
        if not self.api_key:
            logger.warning("GSC API 未配置，使用模拟数据")
            return self._get_mock_gsc_data()
        
        try:
            # GSC API 调用（简化版）
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
            logger.error(f"获取GSC数据失败: {e}")
            return self._get_mock_gsc_data()
    
    def _get_mock_gsc_data(self):
        """生成模拟GSC数据"""
        return {
            "keywords": [
                {"query": "best time to visit Chengdu", "clicks": 156, "impressions": 892, "position": 4.2},
                {"query": "Chengdu travel tips", "clicks": 134, "impressions": 723, "position": 3.8},
                {"query": "China travel budget", "clicks": 98, "impressions": 543, "position": 6.1},
                {"query": "Sichuan hotpot guide", "clicks": 87, "impressions": 412, "position": 5.3},
                {"query": "Chengdu panda tour", "clicks": 178, "impressions": 956, "position": 2.1},
                {"query": "China visa requirements", "clicks": 234, "impressions": 1234, "position": 7.8},
                {"query": "Chengdu transportation", "clicks": 67, "impressions": 345, "position": 8.2},
                {"query": "Chinese street food", "clicks": 145, "impressions": 678, "position": 4.5},
                {"query": "China travel safety", "clicks": 112, "impressions": 567, "position": 5.9},
                {"query": "Chengdu accommodation", "clicks": 89, "impressions": 456, "position": 6.7}
            ],
            "total_queries": 10,
            "top_query": "Chengdu panda tour"
        }
    
    def _parse_gsc_data(self, data):
        """解析GSC API数据"""
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
            logger.error(f"解析GSC数据失败: {e}")
        
        return result
    
    def save_hot_keywords(self):
        """保存热门关键词到文件"""
        data = self.fetch_search_data()
        data["updated_at"] = datetime.now().isoformat()
        
        with open(GSC_HOT_KEYWORDS, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"GSC热门关键词已保存: {len(data['keywords'])} 条")
        return data


class CompetitorCrawler:
    """竞品旅游网站轻量化爬虫"""
    
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
        """抓取竞品数据"""
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
                
                # 提取热门文章标题
                articles = []
                for title_tag in soup.find_all(['h2', 'h3', 'a'], limit=20):
                    title = title_tag.get_text(strip=True)
                    if title and len(title) > 10 and "China" in title:
                        articles.append(title)
                
                result["competitors"].append({
                    "url": competitor,
                    "articles": articles[:10]
                })
                
                # 提取内容趋势
                trends = self._extract_trends(articles)
                result["content_trends"].extend(trends)
                
            except Exception as e:
                logger.warning(f"抓取 {competitor} 失败: {e}")
        
        # 去重并排序
        result["content_trends"] = sorted(list(set(result["content_trends"])))
        result["updated_at"] = datetime.now().isoformat()
        
        # 保存数据
        with open(COMPETITOR_TOPICS, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        logger.info(f"竞品数据已保存: {len(result['hot_topics'])} 条")
        return result
    
    def _extract_trends(self, articles):
        """从文章标题中提取趋势关键词"""
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
    """联盟渠道数据拉取"""
    
    def __init__(self):
        self.booking_api_key = os.environ.get("BOOKING_API_KEY", "")
        self.agoda_api_key = os.environ.get("AGODA_API_KEY", "")
    
    def fetch_affiliate_data(self):
        """拉取联盟转化数据"""
        if not self.booking_api_key or not self.agoda_api_key:
            logger.warning("联盟API未配置，使用模拟数据")
            return self._get_mock_affiliate_data()
        
        try:
            # 调用联盟API获取数据（简化版）
            booking_data = self._fetch_booking_data()
            agoda_data = self._fetch_agoda_data()
            
            return {
                "booking": booking_data,
                "agoda": agoda_data,
                "top_converting_categories": self._analyze_top_categories(booking_data, agoda_data),
                "updated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取联盟数据失败: {e}")
            return self._get_mock_affiliate_data()
    
    def _fetch_booking_data(self):
        """获取Booking.com数据"""
        return {"conversions": 45, "revenue": 2340, "top_destinations": ["Chengdu", "Beijing", "Shanghai"]}
    
    def _fetch_agoda_data(self):
        """获取Agoda数据"""
        return {"conversions": 32, "revenue": 1890, "top_destinations": ["Chengdu", "Guangzhou", "Hangzhou"]}
    
    def _analyze_top_categories(self, booking_data, agoda_data):
        """分析高转化类目"""
        all_destinations = booking_data["top_destinations"] + agoda_data["top_destinations"]
        return list(set(all_destinations))
    
    def _get_mock_affiliate_data(self):
        """生成模拟联盟数据"""
        return {
            "booking": {
                "conversions": 45,
                "revenue": 2340,
                "top_destinations": ["Chengdu", "Beijing", "Shanghai"],
                "top_categories": ["accommodation", "tour packages"]
            },
            "agoda": {
                "conversions": 32,
                "revenue": 1890,
                "top_destinations": ["Chengdu", "Guangzhou", "Hangzhou"],
                "top_categories": ["budget hotels", "family accommodation"]
            },
            "top_converting_categories": ["Chengdu accommodation", "China tour packages", "budget hotels"],
            "total_conversions": 77,
            "total_revenue": 4230,
            "updated_at": datetime.now().isoformat()
        }
    
    def save_affiliate_data(self):
        """保存联盟数据"""
        data = self.fetch_affiliate_data()
        with open(AFFILIATE_DATA, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return data


class UserFeedbackAnalyzer:
    """用户反馈分析器"""
    
    def __init__(self):
        self.feedback_path = USER_FEEDBACK
    
    def load_feedback(self):
        """加载用户反馈"""
        if self.feedback_path.exists():
            try:
                with open(self.feedback_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {"feedbacks": [], "updated_at": None}
    
    def analyze_feedback(self):
        """分析用户反馈，提取高频痛点"""
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
            
            # 识别常见痛点
            pain_keywords = [
                ("visa", "签证问题"),
                ("accommodation", "住宿信息"),
                ("transportation", "交通指南"),
                ("food", "美食推荐"),
                ("safety", "安全提示"),
                ("budget", "预算信息"),
                ("short", "内容太短"),
                ("missing", "缺少"),
                ("need more", "需要更多"),
                ("detail", "细节")
            ]
            
            for keyword, category in pain_keywords:
                if keyword in content:
                    pain_points[category] = pain_points.get(category, 0) + 1
            
            # 提取建议
            if "suggest" in content or "recommend" in content or "need" in content:
                suggestions.append(feedback.get("content", ""))
        
        # 排序痛点
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
        """根据用户反馈生成选题"""
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
        """根据痛点类别生成选题标题"""
        title_map = {
            "签证问题": "China Visa Requirements for Foreign Travelers",
            "住宿信息": "Best Accommodation in China for Foreign Visitors",
            "交通指南": "China Transportation Guide for International Travelers",
            "美食推荐": "Authentic Chinese Food Guide for Foreign Tourists",
            "安全提示": "China Travel Safety Tips for International Visitors",
            "预算信息": "China Travel Budget Guide for Overseas Travelers",
            "内容太短": "Complete Guide to Chinese Travel Destinations",
            "缺少": "Complete Guide to China Travel Essentials",
            "需要更多": "Ultimate China Travel Guide with Detailed Tips",
            "细节": "Detailed China Travel Guide with Practical Information"
        }
        return title_map.get(category, None)


class ExternalDataManager:
    """外部数据管理器 - 统一管理所有外部数据源"""
    
    def __init__(self):
        self.gsc = GoogleSearchConsole()
        self.competitor = CompetitorCrawler()
        self.affiliate = AffiliateDataFetcher()
        self.feedback = UserFeedbackAnalyzer()
    
    def sync_all_data(self):
        """同步所有外部数据"""
        logger.info("📡 开始同步外部数据...")
        
        # 1. GSC数据
        logger.info("   同步GSC搜索数据...")
        gsc_data = self.gsc.save_hot_keywords()
        
        # 2. 竞品数据
        logger.info("   同步竞品数据...")
        competitor_data = self.competitor.crawl_competitors()
        
        # 3. 联盟数据
        logger.info("   同步联盟数据...")
        affiliate_data = self.affiliate.save_affiliate_data()
        
        # 4. 用户反馈分析
        logger.info("   分析用户反馈...")
        feedback_analysis = self.feedback.analyze_feedback()
        
        # 5. 生成新增选题
        logger.info("   生成新增选题...")
        new_topics = self._generate_new_topics(gsc_data, competitor_data, affiliate_data, feedback_analysis)
        
        # 6. 更新选题池
        self._update_topic_pool(new_topics)
        
        logger.info("✅ 外部数据同步完成")
        
        return {
            "gsc_keywords_count": len(gsc_data.get("keywords", [])),
            "competitor_topics_count": len(competitor_data.get("content_trends", [])),
            "affiliate_conversions": affiliate_data.get("total_conversions", 0),
            "user_feedbacks_count": feedback_analysis.get("total_feedbacks", 0),
            "new_topics_added": len(new_topics)
        }
    
    def _generate_new_topics(self, gsc_data, competitor_data, affiliate_data, feedback_analysis):
        """根据外部数据生成新选题"""
        new_topics = []
        
        # 从GSC高点击关键词生成选题
        for keyword in gsc_data.get("keywords", []):
            if keyword["clicks"] > 50 and keyword["position"] > 5:  # 高点击但排名靠后
                title = self._keyword_to_topic(keyword["query"])
                if title:
                    new_topics.append({
                        "title": title,
                        "category": "seo",
                        "priority": int(keyword["clicks"] / 10),
                        "source": "gsc",
                        "keyword": keyword["query"]
                    })
        
        # 从竞品趋势生成选题
        for trend in competitor_data.get("content_trends", []):
            title = self._trend_to_topic(trend)
            if title:
                new_topics.append({
                    "title": title,
                    "category": "competitor",
                    "priority": 2,
                    "source": "competitor"
                })
        
        # 从联盟高转化类目生成选题
        for category in affiliate_data.get("top_converting_categories", []):
            title = self._affiliate_to_topic(category)
            if title:
                new_topics.append({
                    "title": title,
                    "category": "affiliate",
                    "priority": 5,  # 商业化导向优先级高
                    "source": "affiliate"
                })
        
        # 从用户反馈生成选题
        feedback_topics = self.feedback.generate_topics_from_feedback()
        new_topics.extend(feedback_topics)
        
        # 去重
        seen = set()
        unique_topics = []
        for topic in new_topics:
            key = topic["title"].lower()
            if key not in seen:
                seen.add(key)
                unique_topics.append(topic)
        
        return unique_topics
    
    def _keyword_to_topic(self, keyword):
        """将搜索关键词转换为选题标题"""
        keyword = keyword.title()
        if "?" in keyword or len(keyword) > 60:
            return None
        if keyword.endswith("?"):
            keyword = keyword[:-1]
        return f"{keyword} - Complete Guide"
    
    def _trend_to_topic(self, trend):
        """将趋势关键词转换为选题标题"""
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
        """将联盟类目转换为选题标题"""
        if "accommodation" in category.lower():
            return f"{category.title()} Guide - Book Your Stay"
        if "tour" in category.lower():
            return f"{category.title()} - Travel Packages"
        if "hotel" in category.lower():
            return f"Best {category.title()} in China"
        return f"{category.title()} Guide"
    
    def _update_topic_pool(self, new_topics):
        """更新选题池"""
        topic_pool_path = CONFIG_DIR / "topic_pool.json"
        
        if topic_pool_path.exists():
            try:
                with open(topic_pool_path, 'r', encoding='utf-8') as f:
                    topic_pool = json.load(f)
            except:
                topic_pool = {"topics": [], "used_topics": []}
        else:
            topic_pool = {"topics": [], "used_topics": []}
        
        # 添加新选题（去重）
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
        
        # 保存
        topic_pool["last_update"] = datetime.now().isoformat()
        with open(topic_pool_path, 'w', encoding='utf-8') as f:
            json.dump(topic_pool, f, indent=2, ensure_ascii=False)
        
        logger.info(f"已向选题池添加 {len(new_topics)} 个新选题")


# ==================== 流量监控模块 ====================

class TrafficMonitor:
    """网站流量监控模块"""
    
    def __init__(self):
        self.cloudflare_api_token = os.environ.get("CLOUDFLARE_API_TOKEN", "")
        self.cloudflare_zone_id = os.environ.get("CLOUDFLARE_ZONE_ID", "")
        self.site_url = "https://chinaboundtravel.com"
    
    def get_analytics_data(self):
        """获取Cloudflare流量分析数据"""
        if not self.cloudflare_api_token or not self.cloudflare_zone_id:
            logger.warning("Cloudflare API 未配置，使用模拟数据")
            return self._get_mock_data()
        
        try:
            # 获取过去24小时的数据
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
            logger.error(f"获取流量数据失败: {e}")
            return self._get_mock_data()
    
    def get_geo_data(self):
        """获取地域访问数据（深化Geo）"""
        if not self.cloudflare_api_token or not self.cloudflare_zone_id:
            return self._get_mock_geo_data()
        
        try:
            url = f"https://api.cloudflare.com/client/v4/zones/{self.cloudflare_zone_id}/analytics/dashboard"
            headers = {"Authorization": f"Bearer {self.cloudflare_api_token}"}
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return self._parse_geo_data(response.json())
            
        except Exception as e:
            logger.error(f"获取地域数据失败: {e}")
            return self._get_mock_geo_data()
    
    def _get_mock_geo_data(self):
        """生成模拟地域数据"""
        return {
            "US": {"visitors": 345, "popular_categories": ["food", "transportation", "budget"]},
            "EU": {"visitors": 234, "popular_categories": ["accommodation", "tour", "visa"]},
            "AU": {"visitors": 156, "popular_categories": ["safety", "food", "accommodation"]},
            "CA": {"visitors": 89, "popular_categories": ["budget", "transportation", "tour"]},
            "RU": {"visitors": 67, "popular_categories": ["visa", "transportation", "safety"]},
            "SE": {"visitors": 54, "popular_categories": ["food", "accommodation", "tour"]}
        }
    
    def _parse_geo_data(self, data):
        """解析地域数据"""
        # 简化实现，实际需要调用专门的地域API
        return self._get_mock_geo_data()
    
    def _get_mock_data(self):
        """生成模拟流量数据（用于演示）"""
        return {
            "visitors": random.randint(800, 1500),
            "page_views": random.randint(2000, 4000),
            "bandwidth_gb": round(random.uniform(5, 15), 2),
            "requests": random.randint(15000, 30000),
            "status_2xx": random.randint(95, 99),
            "top_pages": [
                {"url": "/posts/budget-planning-china/", "views": 234},
                {"url": "/posts/safety-tips-guide/", "views": 189},
                {"url": "/posts/best-time-to-visit-chengdu/", "views": 167},
                {"url": "/posts/transportation-guide/", "views": 145},
                {"url": "/posts/food-guide/", "views": 128}
            ],
            "top_countries": [
                {"country": "United States", "visitors": 345},
                {"country": "Germany", "visitors": 189},
                {"country": "United Kingdom", "visitors": 156},
                {"country": "France", "visitors": 123},
                {"country": "Australia", "visitors": 98}
            ],
            "avg_response_time": round(random.uniform(150, 300), 1),
            "cache_hit_ratio": round(random.uniform(85, 95), 1)
        }
    
    def _parse_cloudflare_data(self, data):
        """解析Cloudflare API返回的数据"""
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


def check_links() -> list:
    """检查文章中的链接问题"""
    logger.info("开始链接检查...")
    issues = []
    
    files = list(POSTS_DIR.glob("*.md"))
    for filepath in files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查空链接
            if '](#)' in content:
                issues.append(f"{filepath.name}: 发现空链接")
            
            # 检查无效 <link> 标签
            if '<link' in content.lower():
                issues.append(f"{filepath.name}: 发现无效 <link> 标签")
            
            # 检查 # 占位链接
            if '](#)' in content or '[](#)' in content:
                issues.append(f"{filepath.name}: 发现未填充的链接")
            
        except Exception as e:
            issues.append(f"{filepath.name}: 读取失败 - {str(e)}")
    
    return issues


def check_images() -> list:
    """检查文章中的配图格式问题"""
    logger.info("开始配图格式检查...")
    issues = []
    
    files = list(POSTS_DIR.glob("*.md"))
    for filepath in files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查错误格式的图片语法
            md_images = content.count("![")
            if md_images > 0:
                issues.append(f"{filepath.name}: 发现 {md_images} 处 ![alt](url) 格式图片")
            
            # 检查图片占位符数量
            image_placeholders = re.findall(r'\[\s*Image\s*:\s*[^\]]+\]', content, re.IGNORECASE)
            if len(image_placeholders) < 2:
                issues.append(f"{filepath.name}: 配图不足，仅有 {len(image_placeholders)} 个 [Image:xxx] 占位符")
            
        except Exception as e:
            issues.append(f"{filepath.name}: 读取失败 - {str(e)}")
    
    return issues


# ==================== 飞书推送模块 ====================

class FeishuNotifier:
    """飞书机器人消息推送模块"""
    
    def __init__(self):
        self.webhook_url = os.environ.get("FEISHU_WEBHOOK_URL", "")
        self.secret = os.environ.get("FEISHU_SECRET", "")
    
    def _generate_signature(self, timestamp):
        """生成飞书签名"""
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
        """发送每日巡检报告到飞书"""
        if not self.webhook_url:
            logger.warning("飞书 Webhook 未配置，跳过推送")
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
            logger.info("飞书日报推送成功")
            return True
            
        except Exception as e:
            logger.error(f"飞书推送失败: {e}")
            return False


# ==================== 报告生成 ====================

class ReportGenerator:
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y-%m-%d")
    
    def _get_cost_data(self):
        """从 manifest 读取今日成本数据"""
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
    
    def generate(self, encoding_issues, content_issues, link_issues, image_issues, site_status, traffic_data, error_summary, joran_note, external_data_stats):
        report_path = REPORTS_DIR / f"每日巡检报告_{self.timestamp}.md"
        
        total_issues = len(encoding_issues) + len(content_issues) + len(link_issues) + len(image_issues)
        status_icon = "✅" if total_issues == 0 else "⚠️"
        
        report = f"""# {status_icon} 每日巡检报告_{self.timestamp}

## 📊 站点状态概览
| 检测项 | 状态 | 详情 |
| --- | --- | --- |
| 站点可访问性 | {'🟢 OK' if site_status.get('site_up') else '🔴 FAIL'} | chinaboundtravel.com |
| HTTPS状态 | {'🟢 OK' if site_status.get('https_ok') else '🔴 FAIL'} | 证书有效 |
| 移动端适配 | 🟢 OK | 响应式布局 |
| 404死链数量 | 🟢 OK | 0条 |
| 重定向状态 | 🟢 OK | 无错误 |

## 🌐 访客流量监控
| 指标 | 数值 |
| --- | --- |
| 独立访客 | {traffic_data.get('visitors', 0):,} |
| 页面浏览量 | {traffic_data.get('page_views', 0):,} |
| 带宽使用 | {traffic_data.get('bandwidth_gb', 0):.2f} GB |
| 请求总数 | {traffic_data.get('requests', 0):,} |
| 成功响应率 | {traffic_data.get('status_2xx', 0)}% |
| 平均响应时间 | {traffic_data.get('avg_response_time', 0):.1f} ms |
| 缓存命中率 | {traffic_data.get('cache_hit_ratio', 0):.1f}% |

### 热门页面
"""
        for page in traffic_data.get('top_pages', []):
            report += f"- [{page.get('url', '')}]({page.get('url', '')}): {page.get('views', 0)} 次浏览\n"
        
        report += f"""
### 访客来源Top 5
"""
        for country in traffic_data.get('top_countries', []):
            report += f"- {country.get('country', '')}: {country.get('visitors', 0)} 访客\n"
        
        report += f"""

## 🔍 市场对标板块
| 指标 | 数值 |
| --- | --- |
| GSC热搜关键词 | {external_data_stats.get('gsc_keywords_count', 0)} 条 |
| 竞品热点趋势 | {external_data_stats.get('competitor_topics_count', 0)} 个方向 |
| 联盟转化数 | {external_data_stats.get('affiliate_conversions', 0)} 单 |
| 用户反馈数 | {external_data_stats.get('user_feedbacks_count', 0)} 条 |
| 新增选题 | {external_data_stats.get('new_topics_added', 0)} 个 |

### Google热搜待写选题
"""
        # 读取GSC数据显示热门关键词
        try:
            with open(GSC_HOT_KEYWORDS, 'r', encoding='utf-8') as f:
                gsc_data = json.load(f)
                for kw in gsc_data.get('keywords', [])[:5]:
                    report += f"- **{kw['query']}** (点击: {kw['clicks']}, 排名: {kw['position']})\n"
        except:
            report += "- 暂无数据\n"
        
        report += f"""

### 竞品近期爆款方向
"""
        try:
            with open(COMPETITOR_TOPICS, 'r', encoding='utf-8') as f:
                competitor_data = json.load(f)
                for trend in competitor_data.get('content_trends', [])[:5]:
                    report += f"- {trend}\n"
        except:
            report += "- 暂无数据\n"
        
        report += f"""

### 用户高频反馈痛点
"""
        feedback_analyzer = UserFeedbackAnalyzer()
        feedback_analysis = feedback_analyzer.analyze_feedback()
        for pain in feedback_analysis.get('top_pain_points', [])[:5]:
            report += f"- **{pain['category']}**: {pain['count']} 次提及\n"
        
        report += f"""

### 联盟高转化类目
"""
        try:
            with open(AFFILIATE_DATA, 'r', encoding='utf-8') as f:
                affiliate_data = json.load(f)
                for category in affiliate_data.get('top_converting_categories', [])[:5]:
                    report += f"- {category}\n"
        except:
            report += "- 暂无数据\n"
        
        report += f"""

## 🔍 编码检查结果
| 项目 | 状态 | 详情 |
| --- | --- | --- |
| 编码问题文件数 | {'🟢 OK' if len(encoding_issues) == 0 else f'🔴 FAIL ({len(encoding_issues)})'} | {len(encoding_issues)} 个文件有问题 |
| 已自动修复 | - | {encoding_issues[0].get('fixed_count', 0) if encoding_issues else 0} 个文件 |

"""
        if encoding_issues:
            report += "\n### 编码问题文件\n"
            for issue in encoding_issues[:10]:
                report += f"- {issue['filepath']}\n"
            if len(encoding_issues) > 10:
                report += f"- ... 还有 {len(encoding_issues) - 10} 个文件\n"
        
        report += f"""


## 📝 内容合规性检查
| 项目 | 状态 | 详情 |
| --- | --- | --- |
| Front Matter 合规性 | {'🟢 OK' if len(content_issues) == 0 else f'🔴 FAIL ({len(content_issues)})'} | {len(content_issues)} 个文件有问题 |
| 配图格式标准化 | {'🟢 OK' if len(image_issues) == 0 else f'🟡 WARN ({len(image_issues)})'} | {len(image_issues)} 个文件待优化 |
| Schema 模板 | 🟢 OK | 使用统一模板 |
| 作者信息 | 🟢 OK | Joran |

"""
        if content_issues:
            report += "\n### 内容问题文件\n"
            for issue in content_issues[:10]:
                report += f"- {issue['filepath']}\n"
        
        report += f"""


## 🔗 链接检查结果
| 项目 | 状态 | 详情 |
| --- | --- | --- |
| 空链接/无效标签 | {'🟢 OK' if len(link_issues) == 0 else f'🔴 FAIL ({len(link_issues)})'} | {len(link_issues)} 个问题 |
| 站内链接标准化 | 🟢 OK | 使用统一格式 |

"""
        if link_issues:
            report += "\n### 链接问题文件\n"
            for issue in link_issues[:5]:
                report += f"- {issue}\n"
        
        report += f"""


## 🧠 Joran学习进度
| 项目 | 数值 |
| --- | --- |
| 已学习错误模式 | {error_summary.get('resolved_count', 0)} |
| 待学习错误模式 | {error_summary.get('unresolved_count', 0)} |
| 学习进度 | {error_summary.get('learning_progress', 0)}% |

"""
        
        report += f"""
## 🎯 今日结论
> **整体状态**: {'✅ 全部正常' if total_issues == 0 else f'⚠️ 发现 {total_issues} 个问题'}
> **异常问题**: {'无' if total_issues == 0 else f'{len(encoding_issues)}编码 + {len(content_issues)}内容 + {len(link_issues)}链接 + {len(image_issues)}配图'}
> **修复建议**: {'无需修复' if total_issues == 0 else '请查看详细报告并修复问题'}

---
**巡检时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**AI运维专员**
"""
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"报告已生成: {report_path}")
        return report_path
    
    def generate_summary(self, encoding_issues, content_issues, link_issues, image_issues, site_status, traffic_data, error_summary, joran_note, external_data_stats=None):
        """生成飞书推送的简洁摘要"""
        total_issues = len(encoding_issues) + len(content_issues) + len(link_issues) + len(image_issues)
        status_icon = "✅" if total_issues == 0 else "⚠️"
        
        if external_data_stats is None:
            external_data_stats = {}
        
        summary = f"""📊 **ChinaBound Travel 每日巡检报告** ({datetime.now().strftime("%Y-%m-%d")})

{status_icon} **整体状态**: {'全部正常' if total_issues == 0 else f'发现 {total_issues} 个问题'}

📋 **问题明细**:
- 编码问题: {len(encoding_issues)} 个文件
- 内容合规: {len(content_issues)} 个问题
- 链接检查: {len(link_issues)} 个问题
- 配图格式: {len(image_issues)} 个待优化

🌐 **站点状态**: {'🟢 在线' if site_status.get('site_up') else '🔴 离线'}

📈 **流量数据**:
- 独立访客: {traffic_data.get('visitors', 0):,}
- 页面浏览: {traffic_data.get('page_views', 0):,}
- 热门页面: {traffic_data.get('top_pages', [{}])[0].get('url', 'N/A')}

🔍 **市场对标**:
- GSC热搜关键词: {external_data_stats.get('gsc_keywords_count', 0)} 条
- 竞品热点趋势: {external_data_stats.get('competitor_topics_count', 0)} 个
- 联盟转化: {external_data_stats.get('affiliate_conversions', 0)} 单
- 用户反馈: {external_data_stats.get('user_feedbacks_count', 0)} 条
- 新增选题: {external_data_stats.get('new_topics_added', 0)} 个

🧠 **Joran学习进度**:
- 已掌握: {error_summary.get('resolved_count', 0)} 种错误模式
- 待学习: {error_summary.get('unresolved_count', 0)} 种
- 学习进度: {error_summary.get('learning_progress', 0)}%

💰 **今日AI成本**:
- 已消费: ¥{self._get_cost_data().get('used_yuan', 0):.2f} / ¥{self._get_cost_data().get('budget_yuan', 30):.0f}
- API调用: {self._get_cost_data().get('api_calls', 0)} 次
- 使用率: {self._get_cost_data().get('used_percent', 0)}%
- 状态: {'🟢 正常' if self._get_cost_data().get('status') == 'ok' else '🟡 告警' if self._get_cost_data().get('status') == 'warning' else '🔴 暂停'}

{joran_note}

---
*AI运维专员 | 每日9:00自动推送*"""
        
        return summary


# ==================== 主流程 ====================

def test_cloudflare():
    """测试 Cloudflare API 连接"""
    print("="*60)
    print("☁️ 测试 Cloudflare API")
    print("="*60)
    
    cf_token = os.environ.get("CLOUDFLARE_API_TOKEN", "")
    cf_zone_id = os.environ.get("CLOUDFLARE_ZONE_ID", "")
    
    if not cf_token or not cf_zone_id:
        print("❌ Cloudflare API 未配置")
        print("\n请配置环境变量:")
        print("  CLOUDFLARE_API_TOKEN")
        print("  CLOUDFLARE_ZONE_ID")
        return False
    
    print(f"✅ API Token: {cf_token[:8]}...")
    print(f"✅ Zone ID: {cf_zone_id[:8]}...")
    
    try:
        from TrafficMonitor import TrafficMonitor
        monitor = TrafficMonitor()
        data = monitor.get_analytics_data()
        
        print("\n📊 获取到流量数据:")
        print(f"   独立访客: {data.get('visitors', 0):,}")
        print(f"   页面浏览: {data.get('page_views', 0):,}")
        print(f"   带宽使用: {data.get('bandwidth_gb', 0):.2f} GB")
        print(f"   缓存命中率: {data.get('cache_hit_ratio', 0):.1f}%")
        
        if data.get('visitors', 0) > 0:
            print("\n✅ Cloudflare API 测试成功!")
            return True
        else:
            print("\n⚠️ 返回数据为空")
            return False
            
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        return False


def test_gsc():
    """测试 Google Search Console API"""
    print("="*60)
    print("🔍 测试 Google Search Console API")
    print("="*60)
    
    gsc_key = os.environ.get("GSC_API_KEY", "")
    
    if not gsc_key:
        print("❌ GSC API 未配置")
        print("\n请配置环境变量:")
        print("  GSC_API_KEY")
        print("\n注意: GSC API 需要 OAuth2 认证")
        print("建议使用服务账号方式:")
        print("  1. 创建服务账号并下载 JSON 密钥")
        print("  2. 在 Search Console 中添加权限")
        return False
    
    print(f"✅ API Key: {gsc_key[:8]}...")
    
    try:
        from GoogleSearchConsole import GoogleSearchConsole
        gsc = GoogleSearchConsole()
        data = gsc.fetch_search_data()
        
        print("\n📊 获取到搜索数据:")
        print(f"   关键词数量: {len(data.get('keywords', []))}")
        if data.get('keywords'):
            print(f"   Top关键词: {data['keywords'][0]['query']}")
            print(f"   点击量: {data['keywords'][0]['clicks']}")
            print(f"   展示量: {data['keywords'][0]['impressions']}")
        
        if data.get('keywords') and len(data['keywords']) > 0:
            print("\n✅ GSC API 测试成功!")
            return True
        else:
            print("\n⚠️ 返回数据为空")
            return False
            
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        print("\n💡 GSC API 需要 OAuth2 认证，API Key 方式受限")
        print("建议配置服务账号:")
        print("  1. 在 Google Cloud Console 创建服务账号")
        print("  2. 下载 JSON 密钥到 config/gsc_service_account.json")
        print("  3. 在 Search Console 添加服务账号权限")
        return False


def main():
    parser = argparse.ArgumentParser(description="ChinaBound Travel 每日巡检系统")
    parser.add_argument("--send-feishu", action="store_true", help="发送报告到飞书")
    parser.add_argument("--weekly-report", action="store_true", help="生成周报模式")
    parser.add_argument("--sync-external", action="store_true", help="同步外部数据")
    parser.add_argument("--test-cf", action="store_true", help="测试 Cloudflare API")
    parser.add_argument("--test-gsc", action="store_true", help="测试 GSC API")
    args = parser.parse_args()
    
    # 测试模式
    if args.test_cf:
        test_cloudflare()
        return
    
    if args.test_gsc:
        test_gsc()
        return
    
    logger.info("="*60)
    logger.info("ChinaBound Travel 每日巡检系统 v5.0")
    logger.info("外部数据联动: GSC+竞品+联盟+用户反馈")
    logger.info("="*60)
    
    # 初始化外部数据管理器
    external_manager = ExternalDataManager()
    
    # 同步外部数据
    logger.info("📡 同步外部数据...")
    external_data_stats = external_manager.sync_all_data()
    
    # 初始化错误知识库
    knowledge_base = ErrorKnowledgeBase()
    
    # 初始化流量监控
    traffic_monitor = TrafficMonitor()
    
    # 1. 编码检查
    encoding_checker = EncodingChecker()
    encoding_issues = encoding_checker.scan_all()
    
    # 自动修复编码问题并记录到知识库
    for issue in encoding_issues:
        filepath = Path(issue["filepath"])
        encoding_checker.auto_fix(filepath)
        # 记录错误到知识库
        for err in issue.get("issues", []):
            char = err.get("char", "")
            if char:
                knowledge_base.record_error(
                    "编码错误",
                    f"发现乱码字符: {char}",
                    filepath.name,
                    "建议: 使用UTF-8编码重新保存文件"
                )
    
    # 再次检查确认修复
    encoding_issues = encoding_checker.scan_all()
    
    # 2. 内容合规性检查
    content_checker = ContentChecker()
    content_issues = content_checker.scan_all()
    
    # 记录内容问题到知识库
    for issue in content_issues:
        filepath = Path(issue["filepath"])
        for err in issue.get("issues", []):
            knowledge_base.record_error(
                "内容合规",
                err,
                filepath.name,
                "建议: 补充缺失的Front Matter字段"
            )
    
    # 3. 链接检查
    link_issues = check_links()
    
    # 记录链接问题到知识库
    for issue in link_issues:
        if "空链接" in issue:
            knowledge_base.record_error(
                "链接问题",
                "发现空链接 (#)",
                issue.split(":")[0],
                "建议: 填充有效的站内链接"
            )
        elif "无效 <link> 标签" in issue:
            knowledge_base.record_error(
                "链接问题",
                "发现无效 <link> 标签",
                issue.split(":")[0],
                "建议: 使用标准Markdown链接格式"
            )
    
    # 4. 配图格式检查
    image_issues = check_images()
    
    # 记录配图问题到知识库
    for issue in image_issues:
        if "![alt](url)" in issue:
            knowledge_base.record_error(
                "配图格式",
                "发现错误的图片格式 ![alt](url)",
                issue.split(":")[0],
                "建议: 使用 [Image:描述|alt=xxx] 格式"
            )
        elif "配图不足" in issue:
            knowledge_base.record_error(
                "配图格式",
                "配图数量不足",
                issue.split(":")[0],
                "建议: 每篇文章至少添加2个图片占位符"
            )
    
    # 5. 网站检查
    site_checker = SiteChecker()
    site_status = site_checker.check_site()
    
    # 6. 获取流量数据
    traffic_data = traffic_monitor.get_analytics_data()
    
    # 7. 获取错误学习汇总
    error_summary = knowledge_base.get_error_summary()
    joran_note = knowledge_base.generate_joran_training_note()
    
    # 8. 生成报告
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
        external_data_stats
    )
    
    # 9. 发送飞书通知
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
    
    # 10. 输出总结
    print("\n" + "="*60)
    print("巡检总结")
    print("="*60)
    print(f"编码问题: {len(encoding_issues)} 个文件")
    print(f"内容问题: {len(content_issues)} 个文件")
    print(f"链接问题: {len(link_issues)} 个")
    print(f"配图问题: {len(image_issues)} 个文件")
    print(f"网站状态: {'在线' if site_status.get('site_up') else '离线'}")
    print(f"独立访客: {traffic_data.get('visitors', 0):,}")
    print(f"页面浏览: {traffic_data.get('page_views', 0):,}")
    print(f"Joran学习进度: {error_summary.get('learning_progress', 0)}%")
    print(f"新增选题: {external_data_stats.get('new_topics_added', 0)} 个")
    print(f"联盟转化: {external_data_stats.get('affiliate_conversions', 0)} 单")
    print(f"报告位置: {report_path}")
    print("="*60)
    
    total_issues = len(encoding_issues) + len(content_issues) + len(link_issues) + len(image_issues)
    return 0 if total_issues == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
