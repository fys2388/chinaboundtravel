#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
news_monitor.py — 实时新闻 / 行业动态 / 政策监控

为博文生成器和社媒帖子提供「最新实时信息源」。
每日定时运行，抓取多源数据，输出到 config/news_digest.json，
供 joran_blog_generator.py 和 content_rotator.py 读取。

数据源：
  1. Google News RSS（行业 / 旅游 / 签证政策）
  2. DuckDuckGo Instant Answer API（免 key 实时搜索）
  3. 中国领事服务网签证政策页
  4. 各旅行媒体 RSS feed

输出结构：config/news_digest.json
  {
    "version": "1.0",
    "last_updated": "...",
    "digest": {
      "visa_policy": [...],
      "travel_industry": [...],
      "destination_news": [...],
      "safety_alerts": [...],
      "general": [...]
    },
    "sources": { ... }
  }

用法：
  python scripts/news_monitor.py                 # 正常采集
  python scripts/news_monitor.py --dry-run       # 仅打印，不写文件
  python scripts/news_monitor.py --count 10      # 每类最多 10 条
  python scripts/news_monitor.py --sources visa  # 仅签证政策
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote, urlparse

try:
    import requests
except ImportError:
    print("[FATAL] requests library not installed. Run: pip install requests", file=sys.stderr)
    sys.exit(1)

try:
    import feedparser
    HAS_FEEDPARSER = True
except ImportError:
    HAS_FEEDPARSER = False

# ── paths ────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
BLOG_ROOT = SCRIPT_DIR.parent
CONFIG_DIR = BLOG_ROOT / "config"
OUTPUT_PATH = CONFIG_DIR / "news_digest.json"
# 官方政策事实快照：用于"官方公告变化检测"（policy change detection）
OFFICIAL_STATE_PATH = CONFIG_DIR / "official_policy_state.json"

SITE_DOMAIN = "chinaboundtravel.com"

# ── 中文→英文映射（输出给英文 LLM 时需要） ────────────────────────────
# DuckDuckGo 返回可能含中文摘要，我们清洗为英文
CN_STOPWORDS = set("""
的 了 是 在 和 与 也 就 都 而 及 等 着 这 那 之 于 有 无 不 很 太 很 将 被 把 给 为 以 对 从 到
中国 旅游 旅行 签证 政策 新闻 消息 报道 发布 更新 调整 变化 规定 要求 措施 服务 支持 游客
外国人 旅客 旅客 交通 火车 高铁 地铁 机场 酒店 住宿 食物 美食 景点 文化 历史 自然 风景
""".split())


# ══════════════════════════════════════════════════════════════════════
# 数据源定义
# ══════════════════════════════════════════════════════════════════════

# Google News RSS feeds (free, no API key required)
GOOGLE_NEWS_FEEDS = {
    "visa_policy": [
        "China+visa+policy+2026",
        "China+visa+free+transit+240+hour",
        "China+entry+policy+foreign+travelers",
        "China+passport+policy+update",
    ],
    "travel_industry": [
        "China+travel+industry+2026",
        "China+tourism+news",
        "China+travel+restrictions+update",
        "China+inbound+tourism",
    ],
    "destination_news": [
        "China+travel+destination+news",
        "Chengdu+Shanghai+Beijing+Xian+travel",
        "China+new+attractions+open",
        "China+cultural+heritage+news",
    ],
    "safety_alerts": [
        "China+travel+safety+alert",
        "China+weather+warning+travel",
        "China+transportation+update",
    ],
}

# Direct RSS feeds for specific travel media
DIRECT_RSS_FEEDS = [
    "https://www.chinadaily.com.cn/rss/china.xml",
    "https://www.chinadaily.com.cn/rss/travel.xml",
    "https://www.scmp.com/rss/30165921/latest-travel-feed",
    "https://www.theguardian.com/travel/rss",
]

# Visa / policy sources to check
# Official government policy pages — authoritative sources only.
# NOTE: URLs verified reachable (2026-11). The old NIA index URL (n741490/n741898) is 404,
# so it is replaced by the live NIA transit-policy page + the State Council (gov.cn) pages.
POLICY_SOURCES = [
    {
        "name": "State Council (EN) 240-hour policy",
        "url": "https://english.www.gov.cn/policies/featured/202412/20/content_WS676548cbc6d0868f4e8ee28f.html",
        "type": "page",
        "category": "visa_policy",
        "description": "China's 240-hour visa-free transit policy (State Council, updated 2026-08)",
    },
    {
        "name": "NIA visa-free transit policy",
        "url": "https://www.nia.gov.cn/n741440/n741577/c1731205/content.html",
        "type": "page",
        "category": "visa_policy",
        "description": "240-hour visa-free transit policy (China National Immigration Administration)",
    },
    {
        "name": "State Council 57-country notice",
        "url": "https://www.gov.cn/lianbo/202608/content_7078699.htm",
        "type": "page",
        "category": "visa_policy",
        "description": "China extends 240-hour visa-free transit to 57 countries (State Council, 2026-08-20)",
    },
]

# DuckDuckGo Instant Answer search topics
DDG_SEARCH_TOPICS = [
    ("visa_policy", "China visa policy 2026 changes"),
    ("visa_policy", "240 hour visa free transit China 2026"),
    ("travel_industry", "China inbound tourism 2026 news"),
    ("travel_industry", "China travel restrictions 2026 update"),
    ("destination_news", "China new tourist attractions 2026"),
    ("destination_news", "China travel events festivals 2026"),
    ("safety_alerts", "China travel safety advisory 2026"),
]

# ── 请求头（模拟正常浏览器，避免被反爬） ──────────────────────────────
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
}

# ── 分类关键词 ────────────────────────────────────────────────────────
CATEGORY_KEYWORDS = {
    "visa_policy": [
        "visa", "签证", "entry", "transit", "144", "240", "immigration",
        "policy", "policy", "rules", "regulations", "exemption", "free entry",
        "passport", "consular", "consulate", "immigration policy",
        "visa-free", "免签", "入境", "出境", "居留", "证件",
    ],
    "safety_alerts": [
        "safety", "safety", "warning", "alert", "earthquake", "typhoon",
        "flood", "disaster", "emergency", "advisory", "danger",
        "risk", "hazard", "事故", "地震", "台风", "洪水", "灾害",
        "警报", "警告", "危险", "安全",
    ],
    "travel_industry": [
        "tourism", "tourism", "industry", "market", "hotel", "airline",
        "flight", "transportation", "train", "rail", "booking", "travel agency",
        "OTA", "OTA", "OTA", "OTA",
        "旅游", "酒店", "航空", "航班", "交通", "铁路", "预订",
        "OTA", "OTA",
    ],
    "destination_news": [
        "attraction", "site", "open", "new", "landmark", "monument",
        "festival", "event", "cultural", "heritage", "scenic", "nature",
        "museum", "park", "exhibition", "opening", "destination",
        "景点", "博物馆", "公园", "展览", "开馆", "开放", "文化节",
        "遗产", "地标", "景区", "自然",
    ],
    "general": [],  # fallback
}


# ══════════════════════════════════════════════════════════════════════
# 工具函数
# ══════════════════════════════════════════════════════════════════════


def make_hash(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:12]


def normalize_text(text: str, max_len: int = 300) -> str:
    """清理文本：去多余空白、截断、清洗中文标记词。"""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)          # 去 HTML
    text = re.sub(r"&#?\w+;", " ", text)            # 去 HTML 实体
    text = re.sub(r"\s+", " ", text).strip()
    # 移除 stopword 密集片段（简化：直接去停用词）
    tokens = text.split()
    cleaned = [t for t in tokens if t.lower() not in CN_STOPWORDS]
    text = " ".join(cleaned)
    if len(text) > max_len:
        text = text[:max_len].rsplit(" ", 1)[0] + "..."
    return text


def classify_item(title: str, summary: str = "") -> str:
    """根据标题+摘要中的关键词自动分类。"""
    combined = (title + " " + summary).lower()
    best_cat = "general"
    best_count = 0
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if not keywords:
            continue
        count = sum(1 for kw in keywords if kw.lower() in combined)
        if count > best_count:
            best_count = count
            best_cat = cat
    return best_cat


def deduplicate(items: List[dict]) -> List[dict]:
    """按 hash 去重，保留最新。"""
    seen = set()
    result = []
    for item in items:
        key = item.get("_hash") or make_hash(item.get("title", ""))
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def parse_date(date_str: str) -> str:
    """尝试解析多种日期格式，返回 ISO 格式字符串。"""
    if not date_str:
        return ""
    # 尝试常见格式
    for fmt in [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S GMT",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%B %d, %Y",
        "%b %d, %Y",
        "%Y-%m-%d %H:%M:%S",
    ]:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return date_str


# ══════════════════════════════════════════════════════════════════════
# 官方政策事实提取 + 快照变化检测（以官方公告为准）
# ══════════════════════════════════════════════════════════════════════

# 政策事实提取模式（中英双语）。每个字段从官方页面文本中提取关键数字。
POLICY_FACT_PATTERNS = {
    # 过境免签时长（小时）：只匹配 72 / 144 / 240 政策锚点，兼容 "240小时" / "240-hour"
    "hours": r"(?:过境免签|transit)[^\n]{0,40}?(72|144|240)\s*[- ]?\s*(?:小时|hours?|hour)\b|(72|144|240)\s*[- ]?\s*(?:小时|hours?|hour)\b",
    # 适用国家数（兼容 "57个国家" / "57国"）
    "countries": r"(\d{2,3})\s*(?:个)?\s*国(?:家)?(?:的|公民|护照)?",
    # 开放口岸数
    "ports": r"(\d{2,3})\s*(?:个)?(?:口岸|ports?|entry\s+point)",
    # 覆盖省份数
    "provinces": r"(\d{2,3})\s*(?:个)?(?:省|provinces?|regions?)",
}


def extract_policy_facts(text: str) -> dict:
    """从官方公告页面文本中提取政策事实签名。

    只提取政策锚点数字（如 240 小时、57 国、65 口岸、24 省、10 天），
    返回 {field: value}。提取不到的不含在结果里。
    """
    facts: Dict[str, int] = {}
    if not text:
        return facts
    # 去除 HTML 标签与实体，让"240小时 / 57个国家 / 65个口岸"等连续文本可匹配
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&#?\w+;", " ", text)
    text = re.sub(r"\s+", " ", text)
    # 页面里常含多个数字，政策相关字段取"最常见/最大"的值作为锚点，
    # 但 hours 用政策锚点（72/144/240）优先。
    for field, pattern in POLICY_FACT_PATTERNS.items():
        try:
            if field == "hours":
                m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                if m:
                    val = m.group(1) or m.group(2)
                    if val:
                        facts["hours"] = int(val)
            else:
                # 收集所有匹配，取众数（出现最多的值），无则取最大值
                vals = [int(x) for x in re.findall(pattern, text, re.IGNORECASE | re.DOTALL)]
                if not vals:
                    continue
                # 排除明显过大的（如年份 2026）——政策数字应 < 500
                vals = [v for v in vals if 0 < v < 500]
                if not vals:
                    continue
                counts = {}
                for v in vals:
                    counts[v] = counts.get(v, 0) + 1
                best = max(counts.items(), key=lambda kv: (kv[1], kv[0]))[0]
                facts[field] = best
        except Exception:
            continue
    return facts


def load_official_state() -> dict:
    """读取上次官方政策事实快照；不存在则返回空。"""
    if OFFICIAL_STATE_PATH.exists():
        try:
            with open(OFFICIAL_STATE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_official_state(state: dict):
    """保存官方政策事实快照。"""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(OFFICIAL_STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"  [WARN] save official state failed: {e}")


def detect_policy_change(new_facts: dict, old_facts: dict) -> dict | None:
    """对比新旧政策事实，返回变化描述（changed fields）；无变化返回 None。

    只有官方事实出现实质变化（时长/国家数/口岸数/省份数/天数不同）才算变化。
    """
    if not new_facts:
        return None
    if not old_facts:
        # 首次建立基线：不视为"变化"，但记录（避免首跑就误报）
        return None
    changed = {}
    for field, val in new_facts.items():
        if field in old_facts and old_facts[field] != val:
            changed[field] = {"old": old_facts[field], "new": val}
        elif field not in old_facts:
            changed[field] = {"old": None, "new": val}
    if not changed:
        return None
    return {"changed_fields": changed, "detected_at": datetime.now(timezone.utc).isoformat()}


# ══════════════════════════════════════════════════════════════════════
# 采集器
# ══════════════════════════════════════════════════════════════════════


class NewsCollector:
    """采集单条新闻。"""

    def __init__(self, session: requests.Session):
        self.session = session
        self.collected: Dict[str, List[dict]] = {}
        # 官方政策事实（跨来源合并），供变化检测
        self.policy_facts: Dict[str, int] = {}

    def _add(self, category: str, item: dict):
        cat = item.get("category") or classify_item(item.get("title", ""), item.get("summary", ""))
        self.collected.setdefault(cat, []).append(item)

    # ── 1. Google News RSS ────────────────────────────────────────────
    def fetch_google_news(self, max_per_query: int = 5) -> int:
        """从 Google News RSS 抓取多主题新闻。"""
        if not HAS_FEEDPARSER:
            print("  [SKIP] feedparser not installed for Google News RSS")
            return 0

        count = 0
        total_queries = 0
        for category, queries in GOOGLE_NEWS_FEEDS.items():
            for qi, query in enumerate(queries):
                total_queries += 1
                rss_url = f"https://news.google.com/rss/search?q={quote(query)}&hl=en-US&gl=US&ceid=US:en"
                try:
                    resp = self.session.get(rss_url, headers=HEADERS, timeout=15)
                    if resp.status_code != 200:
                        print(f"  [WARN] Google News RSS {query[:30]}... -> HTTP {resp.status_code}")
                        continue
                    feed = feedparser.parse(resp.content)
                    entries = feed.entries[:max_per_query]
                    for entry in entries:
                        title = entry.get("title", "").strip()
                        if not title:
                            continue
                        summary = normalize_text(entry.get("summary", ""))
                        link = entry.get("link", "")
                        pub_date = entry.get("published", "") or entry.get("updated", "")
                        item = {
                            "title": title,
                            "summary": summary,
                            "url": link,
                            "date": parse_date(pub_date),
                            "source": "Google News RSS",
                            "source_query": query,
                            "category": category,
                            "type": "news",
                            "_hash": make_hash(title),
                        }
                        self._add(category, item)
                        count += 1
                except Exception as e:
                    print(f"  [WARN] Google News RSS error ({query[:30]}...): {e}")
                # 查询间小延迟，避免被限流
                if qi < len(queries) - 1:
                    time.sleep(0.5)

        print(f"  [OK] Google News RSS: {count} items from {total_queries} queries")
        return count

    # ── 2. Direct RSS feeds ──────────────────────────────────────────
    def fetch_direct_rss(self, max_per_feed: int = 5) -> int:
        """从指定 RSS feed 抓取新闻。"""
        if not HAS_FEEDPARSER:
            print("  [SKIP] feedparser not installed for direct RSS feeds")
            return 0

        count = 0
        for url in DIRECT_RSS_FEEDS:
            try:
                resp = self.session.get(url, headers=HEADERS, timeout=15)
                if resp.status_code != 200:
                    print(f"  [WARN] RSS {url} -> HTTP {resp.status_code}")
                    continue
                feed = feedparser.parse(resp.content)
                feed_name = feed.feed.get("title", url.split("//")[-1].split("/")[0]) if feed.feed else url
                entries = feed.entries[:max_per_feed]
                for entry in entries:
                    title = entry.get("title", "").strip()
                    if not title:
                        continue
                    # 简单过滤：只保留与 travel / China / tourism 相关的
                    title_lower = title.lower()
                    related = any(kw in title_lower for kw in [
                        "china", "chinese", "travel", "tourism", "visit", "visa",
                        "airport", "flight", "hotel", "transport", "train",
                        "beijing", "shanghai", "chengdu", "xian", "xi'an",
                        "guilin", "yangshuo", "zhangjiajie", "sichuan", "yunnan",
                    ])
                    if not related:
                        continue
                    summary = normalize_text(entry.get("summary", ""))
                    link = entry.get("link", "")
                    pub_date = entry.get("published", "") or entry.get("updated", "")
                    category = classify_item(title, summary)
                    item = {
                        "title": title,
                        "summary": summary,
                        "url": link,
                        "date": parse_date(pub_date),
                        "source": feed_name,
                        "category": category,
                        "type": "news",
                        "_hash": make_hash(title),
                    }
                    self._add(category, item)
                    count += 1
            except Exception as e:
                print(f"  [WARN] RSS error ({url[:50]}...): {e}")

        print(f"  [OK] Direct RSS: {count} items")
        return count

    # ── 3. DuckDuckGo Instant Answer ──────────────────────────────────
    def fetch_duckduckgo(self, max_per_topic: int = 3) -> int:
        """通过 DuckDuckGo Instant Answer API 搜索最新新闻。

        带指数退避重试（最多 3 次）+ 请求间 1s 延迟，
        连续 3 次失败后自动降级跳过（不再重试后续主题）。
        """
        count = 0
        api_url = "https://api.duckduckgo.com/"
        max_retries = 3
        base_delay = 1.0  # 秒
        consecutive_failures = 0

        for topic_idx, (category, query) in enumerate(DDG_SEARCH_TOPICS):
            # 连续失败过多，提前退出
            if consecutive_failures >= 3:
                print(f"  [SKIP] DDG: {consecutive_failures} consecutive failures, skipping remaining topics")
                break

            success = False
            for attempt in range(max_retries):
                try:
                    if attempt > 0:
                        delay = base_delay * (2 ** (attempt - 1))  # 1s, 2s, 4s
                        print(f"  [RETRY] DDG {query[:30]}... attempt {attempt+1}/{max_retries} (delay {delay:.0f}s)")
                        time.sleep(delay)

                    params = {
                        "q": query,
                        "format": "json",
                        "no_redirect": 1,
                        "no_html": 1,
                        "skip_disambig": 1,
                    }
                    resp = self.session.get(api_url, params=params, headers=HEADERS, timeout=15)
                    if resp.status_code != 200:
                        raise RuntimeError(f"HTTP {resp.status_code}")

                    data = resp.json()

                    # DDG 返回多种结果：Abstract, RelatedTopics, Results
                    results = []

                    # 1) Abstract
                    abstract = data.get("Abstract", "")
                    abstract_url = data.get("AbstractURL", "")
                    if abstract and len(abstract) > 50:
                        topic_title = data.get("Heading", query)
                        results.append({
                            "title": topic_title,
                            "summary": normalize_text(abstract),
                            "url": abstract_url,
                            "source": "DuckDuckGo Instant Answer",
                            "category": category,
                            "type": "article",
                        })

                    # 2) RelatedTopics
                    for topic in data.get("RelatedTopics", [])[:max_per_topic]:
                        if isinstance(topic, dict):
                            t = topic.get("Text", "")
                            u = topic.get("FirstURL", "")
                            if t and u:
                                results.append({
                                    "title": normalize_text(t, 200),
                                    "summary": normalize_text(topic.get("Text", "")),
                                    "url": u,
                                    "source": "DuckDuckGo Related Topics",
                                    "category": category,
                                    "type": "article",
                                })

                    # 3) Results (if any)
                    for r in data.get("Results", [])[:max_per_topic]:
                        if isinstance(r, dict):
                            text = r.get("Text", "")
                            first_url = r.get("FirstURL", "")
                            if text and first_url:
                                results.append({
                                    "title": normalize_text(text, 200),
                                    "summary": normalize_text(text),
                                    "url": first_url,
                                    "source": "DuckDuckGo Results",
                                    "category": category,
                                    "type": "article",
                                })

                    for item in results:
                        item["_hash"] = make_hash(item["title"])
                        self._add(category, item)
                        count += 1

                    # 即使返回 0 条也算成功（API 正常响应），重置失败计数
                    consecutive_failures = 0
                    success = True
                    break  # 成功，不再重试

                except requests.exceptions.Timeout:
                    print(f"  [WARN] DDG timeout ({query[:30]}...) attempt {attempt+1}/{max_retries}")
                except requests.exceptions.ConnectionError:
                    print(f"  [WARN] DDG connection error ({query[:30]}...) attempt {attempt+1}/{max_retries}")
                except Exception as e:
                    print(f"  [WARN] DDG error ({query[:30]}...) attempt {attempt+1}/{max_retries}: {e}")

            if not success:
                consecutive_failures += 1

            # 请求间小延迟，避免被限流
            if topic_idx < len(DDG_SEARCH_TOPICS) - 1:
                time.sleep(1.0)

        print(f"  [OK] DuckDuckGo: {count} items from {len(DDG_SEARCH_TOPICS)} topics")
        return count

    # ── 4. 签证政策页面抓取 ──────────────────────────────────────────
    def fetch_policy_pages(self) -> int:
        """抓取官方签证政策页面，提取最新动态 + 政策事实签名。

        除提取标题当新闻条目外，还从页面文本提取政策事实（240 小时 / 57 国 /
        65 口岸 / 24 省 / 10 天），供 detect_policy_change 做"官方公告变化检测"。
        """
        count = 0
        for source in POLICY_SOURCES:
            try:
                resp = self.session.get(source["url"], headers=HEADERS, timeout=20)
                if resp.status_code != 200:
                    print(f"  [WARN] Policy page {source['name']} -> HTTP {resp.status_code}")
                    continue

                # 官方页（gov.cn / nia.gov.cn）常被 requests 误判为 ISO-8859-1，
                # 实际为 UTF-8 —— 强制按 UTF-8 解码，避免中文乱码导致事实提取失败。
                try:
                    html = resp.content.decode("utf-8", errors="ignore")
                except Exception:
                    html = resp.text
                title = source["name"]

                # 提取政策事实（以官方公告为准）
                page_facts = extract_policy_facts(html)
                for k, v in page_facts.items():
                    # 合并：同一字段取更"保守"（更严格）的值？
                    # 官方多个页面应一致；不一致时以最大值（最新放宽）为准。
                    if k not in self.policy_facts or v > self.policy_facts[k]:
                        self.policy_facts[k] = v

                # 简单提取标题和内容块（保留原有逻辑，作为"新闻条目"）
                title_pattern = re.compile(
                    r"<(?:h[1-3]|strong|a)[^>]*>([^<]{10,200})</(?:h[1-3]|strong|a)>",
                    re.IGNORECASE | re.DOTALL
                )
                titles = title_pattern.findall(html)

                # 去重并过滤
                seen = set()
                for t in titles:
                    t_clean = normalize_text(t, 200)
                    if not t_clean or t_clean in seen or len(t_clean) < 10:
                        continue
                    seen.add(t_clean)

                    # 简单检查是否与签证/旅游相关
                    t_lower = t_clean.lower()
                    is_relevant = any(kw in t_lower for kw in [
                        "visa", "visa", "签证", "transit", "入境", "出境",
                        "immigration", "policy", "policy", "rules", "regulations",
                        "entry", "travel", "foreign", "passport", "免签", "240",
                    ])
                    if not is_relevant:
                        continue

                    item = {
                        "title": t_clean,
                        "summary": f"From {source['name']}: {source['description']}",
                        "url": source["url"],
                        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                        "source": source["name"],
                        "category": source["category"],
                        "type": "policy_page",
                        "_hash": make_hash(t_clean),
                    }
                    self._add(source["category"], item)
                    count += 1

                    if count >= 10:  # 每来源最多 10 条
                        break

            except Exception as e:
                print(f"  [WARN] Policy page error ({source['name']}): {e}")

        print(f"  [OK] Policy pages: {count} items, facts={self.policy_facts}")
        return count

    # ── 汇总 ──────────────────────────────────────────────────────────
    def collect_all(self, max_per_category: int = 10) -> dict:
        """运行所有采集器，返回去重排序后的结果。"""
        all_count = 0
        all_count += self.fetch_google_news()
        all_count += self.fetch_direct_rss()
        all_count += self.fetch_duckduckgo()
        all_count += self.fetch_policy_pages()

        print(f"\n  [TOTAL] Collected {all_count} raw items")

        # 去重 + 排序
        digest = {}
        for cat, items in self.collected.items():
            items = deduplicate(items)
            # 按日期排序（最新的在前）
            items.sort(key=lambda x: x.get("date", ""), reverse=True)
            digest[cat] = items[:max_per_category]

        # 添加 general 分类（剩余未归类的）
        digest.setdefault("general", [])

        return digest


# ══════════════════════════════════════════════════════════════════════
# 输出
# ══════════════════════════════════════════════════════════════════════


def build_output(digest: dict, max_per_category: int = 10) -> dict:
    """构建最终输出 JSON。"""
    now = datetime.now(timezone.utc)

    # 统计
    source_stats = {}
    total_items = 0
    for cat, items in digest.items():
        cat_items = items[:max_per_category]
        digest[cat] = cat_items
        total_items += len(cat_items)
        for item in cat_items:
            src = item.get("source", "unknown")
            source_stats[src] = source_stats.get(src, 0) + 1

    # 生成 LLM-friendly 摘要（最多前 3 条/类）
    llm_summary = {}
    for cat, items in digest.items():
        if not items:
            continue
        lines = []
        for item in items[:3]:
            lines.append(f"- [{item.get('date', 'N/A')}] {item['title']}")
            if item.get("summary"):
                lines.append(f"  {item['summary'][:150]}")
        llm_summary[cat] = "\n".join(lines)

    output = {
        "version": "1.0",
        "last_updated": now.isoformat(),
        "last_updated_date": now.strftime("%Y-%m-%d"),
        "total_items": total_items,
        "digest": digest,
        "llm_summary": llm_summary,
        "sources": source_stats,
        "source_config": {
            "google_news_queries": sum(len(v) for v in GOOGLE_NEWS_FEEDS.values()),
            "direct_rss_feeds": len(DIRECT_RSS_FEEDS),
            "duckduckgo_topics": len(DDG_SEARCH_TOPICS),
            "policy_pages": len(POLICY_SOURCES),
        },
    }
    return output


# ══════════════════════════════════════════════════════════════════════
# 飞书通知
# ══════════════════════════════════════════════════════════════════════


def send_feishu_notification(digest: dict, dry_run: bool = False):
    """发送飞书通知（如果配置了）。"""
    webhook = os.getenv("FEISHU_WEBHOOK_URL")
    if not webhook:
        return

    total = sum(len(items) for items in digest.values())
    lines = [f"📰 News Monitor: {total} items collected", ""]
    for cat, items in digest.items():
        if not items:
            continue
        lines.append(f"{cat}: {len(items)} items")
        for item in items[:2]:
            lines.append(f"  • {item['title'][:60]}")
    content = "\n".join(lines)

    payload = {
        "msg_type": "text",
        "content": {"text": f"📰 News Monitor Daily\n\n{content}"},
    }

    try:
        resp = requests.post(webhook, json=payload, timeout=15)
        print(f"  [Feishu] Notification sent: HTTP {resp.status_code}")
    except Exception as e:
        print(f"  [Feishu] Notification failed: {e}")


# ══════════════════════════════════════════════════════════════════════
# 主流程
# ══════════════════════════════════════════════════════════════════════


def run(dry_run: bool = False, count: int = 10, sources: str = "all"):
    """执行新闻监控。"""
    print("=" * 60)
    print("ChinaBound Travel - News Monitor")
    print(f"Started: {datetime.now(timezone.utc).isoformat()}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'} | Per-category max: {count}")
    print("=" * 60)

    # 确定要运行哪些采集器
    source_flags = set(s.strip().lower() for s in sources.split(","))

    session = requests.Session()
    collector = NewsCollector(session)

    # 按源运行
    if "google" in source_flags or "all" in source_flags:
        collector.fetch_google_news(max_per_query=min(3, count))
    if "rss" in source_flags or "all" in source_flags:
        collector.fetch_direct_rss(max_per_feed=min(3, count))
    if "ddg" in source_flags or "all" in source_flags:
        collector.fetch_duckduckgo(max_per_topic=min(3, count))
    if "policy" in source_flags or "all" in source_flags:
        collector.fetch_policy_pages()

    # 汇总
    digest = {}
    all_count = 0
    for cat, items in collector.collected.items():
        items = deduplicate(items)
        items.sort(key=lambda x: x.get("date", ""), reverse=True)
        digest[cat] = items[:count]
        all_count += len(digest[cat])

    print(f"\n{'=' * 60}")
    print(f"Collected {all_count} items across {len(digest)} categories")
    for cat, items in sorted(digest.items()):
        print(f"  {cat}: {len(items)} items")
    print(f"{'=' * 60}")

    # 构建输出
    output = build_output(digest, max_per_category=count)

    # ── 官方公告变化检测（以官方公告为准） ──────────────────────────
    old_state = load_official_state()
    old_facts = old_state.get("facts", {})
    policy_change = detect_policy_change(collector.policy_facts, old_facts)
    new_state = {
        "facts": collector.policy_facts,
        "sources": [s["url"] for s in POLICY_SOURCES],
        "last_checked": datetime.now(timezone.utc).isoformat(),
        "last_change": old_state.get("last_change"),
    }
    if policy_change:
        new_state["last_change"] = policy_change["detected_at"]
    output["official_facts"] = collector.policy_facts
    output["policy_change"] = policy_change
    output["official_state_checked_at"] = new_state["last_checked"]
    if policy_change:
        print(f"  [POLICY CHANGE] {policy_change['changed_fields']}")
    else:
        print(f"  [NO POLICY CHANGE] official facts={collector.policy_facts or 'unavailable'}")

    # 显示摘要
    if not dry_run:
        print("\n── Preview (LLM-friendly) ──")
        for cat, summary in output.get("llm_summary", {}).items():
            if summary:
                print(f"\n  [{cat.upper()}]")
                for line in summary.split("\n"):
                    print(f"  {line}")

    if dry_run:
        print("\n[DRY RUN] Not writing to file.")
        return output

    # 写文件
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n[OK] Written to {OUTPUT_PATH}")

    # 保存官方政策事实快照（供下次变化检测 + policy_content_sync 读取）
    save_official_state(new_state)
    print(f"[OK] Official policy state saved to {OFFICIAL_STATE_PATH}")

    # 飞书通知
    send_feishu_notification(output)

    return output


def main():
    parser = argparse.ArgumentParser(description="ChinaBound Travel News Monitor")
    parser.add_argument("--dry-run", action="store_true", help="Print results only, do not write file")
    parser.add_argument("--count", type=int, default=10, help="Max items per category (default: 10)")
    parser.add_argument(
        "--sources",
        default="all",
        help="Comma-separated source list: google,rss,ddg,policy (default: all)",
    )
    args = parser.parse_args()

    # 确保 stdout 是 UTF-8
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    run(dry_run=args.dry_run, count=args.count, sources=args.sources)


if __name__ == "__main__":
    main()
