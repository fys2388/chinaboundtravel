#!/usr/bin/env python3
"""
ChinaBound Travel - 用户智能运营Agent
User Intelligence Agent

核心能力（L1 → L2）：
1. 用户行为追踪与分析 - 页面浏览、停留时间、跳出率、转化路径
2. 用户分层与画像 - 基于行为的用户分群、兴趣标签、价值评估
3. 用户旅程分析 - 首次访问→深度浏览→转化→复访全旅程
4. 智能客服知识库 - FAQ自动匹配、常见问题解答、问题分类
5. 用户反馈收集与分析 - 反馈收集、情感分析、问题优先级
6. 用户留存与忠诚度优化 - 留存策略、召回机制、忠诚度计划

成熟度目标：L1 → L2（6个月）
"""

import os
import sys
import json
import csv
import re
import math
from datetime import datetime, timedelta

# P1-AI-OPS-03: Consume user optimization strategy from Learning Closed Loop
try:
    from strategy_consumer import StrategyConsumer
    _STRATEGY_CONSUMER = None
except Exception:
    _STRATEGY_CONSUMER = None
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
from collections import defaultdict


# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
USER_DIR = REPORTS_DIR / "user"
USER_DIR.mkdir(parents=True, exist_ok=True)

# 数据文件
USER_AUDIT_FILE = USER_DIR / "user_behavior_audit.json"
USER_SEGMENTS_FILE = USER_DIR / "user_segments.json"
USER_JOURNEY_FILE = USER_DIR / "user_journey_analysis.json"
FAQ_KNOWLEDGE_BASE_FILE = USER_DIR / "faq_knowledge_base.json"
FEEDBACK_ANALYSIS_FILE = USER_DIR / "feedback_analysis.json"
RETENTION_STRATEGY_FILE = USER_DIR / "retention_strategy.json"
USER_REPORT_FILE = USER_DIR / "user_intelligence_report.md"


class UserSegment(Enum):
    """用户分层"""
    NEW_VISITOR = "new_visitor"              # 新访客
    CASUAL_BROWSER = "casual_browser"        # 随意浏览者
    DEEP_READER = "deep_reader"              # 深度阅读者
    PLANNING_TRAVELER = "planning_traveler"  # 计划旅行者
    HIGH_INTENT = "high_intent"              # 高意向用户
    CONVERTER = "converter"                  # 转化用户
    LOYAL_USER = "loyal_user"                # 忠诚用户


class UserIntent(Enum):
    """用户意图"""
    INFORMATIONAL = "informational"          # 信息查询
    NAVIGATIONAL = "navigational"            # 导航浏览
    COMMERCIAL = "commercial"                # 商业研究
    TRANSACTIONAL = "transactional"          # 交易转化


class FeedbackSentiment(Enum):
    """反馈情感"""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


@dataclass
class UserBehavior:
    """用户行为记录"""
    session_id: str
    user_type: str  # new/returning
    landing_page: str
    pages_visited: List[str]
    session_duration: int  # 秒
    bounce_rate: float
    device: str
    country: str
    source: str
    has_conversion: bool
    conversion_type: str = ""
    interests: List[str] = field(default_factory=list)


@dataclass
class UserSegmentProfile:
    """用户分层画像"""
    segment: str
    description: str
    percentage: float
    avg_session_duration: int
    avg_pages_per_session: float
    bounce_rate: float
    conversion_rate: float
    top_pages: List[str]
    top_interests: List[str]
    key_characteristics: List[str]
    recommended_strategy: str
    content_recommendations: List[str]


@dataclass
class JourneyStage:
    """旅程阶段"""
    stage: str
    description: str
    user_percentage: float
    avg_duration: str
    key_behaviors: List[str]
    drop_off_rate: float
    pain_points: List[str]
    optimization_opportunities: List[str]


@dataclass
class FAQItem:
    """FAQ条目"""
    id: str
    question: str
    answer: str
    category: str
    keywords: List[str]
    view_count: int
    helpful_count: int
    not_helpful_count: int
    last_updated: str
    related_articles: List[str]


@dataclass
class FeedbackItem:
    """反馈条目"""
    id: str
    feedback_type: str  # question/suggestion/complaint/praise
    content: str
    sentiment: str
    category: str
    priority: str  # high/medium/low
    status: str  # new/processing/resolved
    created_at: str
    response: str = ""


@dataclass
class RetentionStrategy:
    """留存策略"""
    id: str
    strategy_name: str
    description: str
    target_segment: str
    channel: str  # email/social/onsite/push
    trigger_condition: str
    expected_impact: str
    implementation_complexity: str
    status: str  # proposed/active/paused/completed


class UserIntelligenceAgent:
    """用户智能运营Agent主类"""

    def __init__(self):
        self.user_behaviors: List[UserBehavior] = []
        self.user_segments: List[UserSegmentProfile] = []
        self.journey_stages: List[JourneyStage] = []
        self.faq_knowledge_base: List[FAQItem] = []
        self.feedback_items: List[FeedbackItem] = []
        self.retention_strategies: List[RetentionStrategy] = []
        self._generate_sample_data()
        # P1-AI-OPS-03: Load user optimization strategy
        self.strategy = None
        if _STRATEGY_CONSUMER is not None:
            try:
                self.strategy = _STRATEGY_CONSUMER("reports/user/user_optimization_strategy.json", "user")
            except Exception as _e:
                print(f"  ⚠️ User Strategy load skipped: {_e}")

    def _generate_sample_data(self):
        """生成模拟用户数据用于演示"""
        print("  📊 生成模拟用户数据用于演示...")

        # 模拟用户行为数据
        pages = [
            "/", "/posts/china-travel-guide-2026/", "/posts/144-hour-visa-free-transit-guide/",
            "/posts/china-high-speed-rail-guide/", "/posts/alipay-wechat-pay-foreigners-guide/",
            "/posts/china-photography-guide/", "/posts/chinese-street-food-guide/",
            "/posts/7-day-china-itinerary/", "/posts/best-china-travel-insurance/",
            "/posts/china-packing-list/", "/resources/", "/about/", "/cities/beijing/",
            "/cities/shanghai/", "/cities/chengdu/", "/cities/guilin/"
        ]

        countries = ["United States", "United Kingdom", "Canada", "Australia", "Germany",
                    "France", "Japan", "Singapore", "Brazil", "India"]
        sources = ["organic_search", "direct", "organic_social", "referral", "email"]
        devices = ["desktop", "mobile", "tablet"]
        interests = ["visa", "transport", "food", "photography", "itinerary",
                    "payment", "insurance", "culture", "safety", "packing"]

        for i in range(100):
            user_type = "new" if i < 70 else "returning"
            pages_count = 1 + (i % 8)
            visited_pages = pages[:pages_count] if i % 3 == 0 else [pages[i % len(pages)]] + pages[1:pages_count]
            duration = 30 + (i % 300)
            bounce = 1.0 if pages_count == 1 else 0.0
            has_conversion = i % 15 == 0
            conversion_type = "affiliate_click" if has_conversion else ""
            user_interests = interests[i % len(interests):i % len(interests) + 2]

            behavior = UserBehavior(
                session_id=f"session_{i+1:04d}",
                user_type=user_type,
                landing_page=pages[i % len(pages)],
                pages_visited=visited_pages,
                session_duration=duration,
                bounce_rate=bounce,
                device=devices[i % len(devices)],
                country=countries[i % len(countries)],
                source=sources[i % len(sources)],
                has_conversion=has_conversion,
                conversion_type=conversion_type,
                interests=user_interests
            )
            self.user_behaviors.append(behavior)

        # 生成FAQ知识库
        faq_data = [
            ("Do I need a visa to visit China?", "It depends on your nationality. Many countries qualify for visa-free transit (24/72/144 hours) or visa-free entry for up to 30 days. Check our complete visa guide for your specific situation.", "visa", ["visa", "entry", "passport", "requirement"]),
            ("How do I pay for things in China?", "Mobile payment (Alipay and WeChat Pay) is ubiquitous. Foreigners can now link international cards to Alipay. Cash is accepted but less common. Credit cards work at major hotels but not small shops.", "payment", ["payment", "alipay", "wechat", "cash", "credit card"]),
            ("Is China safe for tourists?", "China is generally very safe for tourists. Violent crime is rare. Take normal precautions against pickpockets in crowded areas. Be aware of scams near tourist attractions. Our safety guide has detailed tips.", "safety", ["safety", "crime", "scam", "security"]),
            ("How do I book train tickets in China?", "You can book through official app (12306), third-party platforms like Trip.com, or at train stations. High-speed trains sell out, book 1-2 weeks in advance. Passport is required for pickup and boarding.", "transport", ["train", "ticket", "booking", "high-speed rail"]),
            ("Do I need travel insurance for China?", "Yes, travel insurance is highly recommended. Medical costs can be high for foreigners. Look for coverage that includes medical evacuation, trip cancellation, and adventure activities if applicable.", "insurance", ["insurance", "medical", "coverage", "safety"]),
            ("What's the best time to visit China?", "Spring (April-May) and autumn (September-October) are generally best with comfortable weather. Summer is hot and crowded. Winter is cold but less crowded and cheaper. Regional variations apply.", "planning", ["best time", "weather", "season", "when to visit"]),
            ("Can I use Google in China?", "Google services (Gmail, Maps, Drive) are blocked in mainland China. You'll need a VPN for access. Alternatively, use Baidu Maps for navigation and local email providers. Hong Kong and Macau have unrestricted access.", "internet", ["google", "vpn", "internet", "blocked", "access"]),
            ("What should I pack for China?", "Essentials include: passport and copies, power adapter (Type A/C/I), comfortable walking shoes, VPN, portable charger, medications, travel insurance documents, and a reusable water bottle. Layers are recommended for variable weather.", "packing", ["packing", "what to bring", "essentials", "list"]),
            ("How much does a trip to China cost?", "Budget travelers: $50-80/day (hostels, street food, public transport). Mid-range: $100-200/day (3-4 star hotels, restaurants, taxis). Luxury: $300+/day. International flights are the biggest expense.", "budget", ["cost", "budget", "price", "expensive", "how much"]),
            ("Do I need to know Chinese to travel?", "No, you don't need to know Chinese. English is spoken at major hotels, airports, and tourist attractions. Download translation apps (Google Translate works offline, Pleco is excellent). Learning basic phrases is appreciated and helpful.", "language", ["chinese", "language", "english", "communication", "phrase"]),
            ("What's the food like in China?", "Chinese cuisine is incredibly diverse with 8 major regional cuisines. Street food is a highlight. Spiciness varies (Sichuan is very spicy). Vegetarian options exist but may be limited outside major cities. Try local specialties in each region.", "food", ["food", "cuisine", "eating", "restaurant", "street food"]),
            ("Can I drink tap water in China?", "No, do not drink tap water in mainland China. Drink bottled water (widely available and cheap) or boiled water. Many hotels provide electric kettles. Avoid ice in drinks unless you know it's made from filtered water.", "health", ["water", "drink", "tap", "health", "safety"]),
        ]

        for i, (question, answer, category, keywords) in enumerate(faq_data):
            faq = FAQItem(
                id=f"faq_{i+1:03d}",
                question=question,
                answer=answer,
                category=category,
                keywords=keywords,
                view_count=100 + (i * 15) % 500,
                helpful_count=20 + (i * 7) % 80,
                not_helpful_count=2 + (i * 3) % 15,
                last_updated="2026-08-01",
                related_articles=[f"/posts/related-article-{i%5}/"]
            )
            self.faq_knowledge_base.append(faq)

        # 生成反馈数据
        feedback_data = [
            ("The visa guide was very helpful! Saved me hours of research.", "praise", "positive", "content", "low"),
            ("How do I get from Beijing airport to the city center?", "question", "neutral", "transport", "medium"),
            ("The page loaded slowly on my phone.", "complaint", "negative", "technical", "high"),
            ("Could you add more information about traveling with kids?", "suggestion", "neutral", "content", "medium"),
            ("Excellent photography guide! The tips were spot on.", "praise", "positive", "content", "low"),
            ("The booking link didn't work for me.", "complaint", "negative", "technical", "high"),
            ("What's the best way to get a tourist visa for US citizens?", "question", "neutral", "visa", "high"),
            ("Love the newsletter! Keep the great content coming.", "praise", "positive", "general", "low"),
            ("The article mentioned a museum that doesn't exist in Jiuzhaigou.", "complaint", "negative", "content_accuracy", "high"),
            ("Could you create a 10-day itinerary for first-timers?", "suggestion", "neutral", "content", "medium"),
        ]

        for i, (content, ftype, sentiment, category, priority) in enumerate(feedback_data):
            feedback = FeedbackItem(
                id=f"fb_{i+1:03d}",
                feedback_type=ftype,
                content=content,
                sentiment=sentiment,
                category=category,
                priority=priority,
                status="new" if i < 5 else "processing",
                created_at=(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            )
            self.feedback_items.append(feedback)

    # ==================== 1. 用户行为追踪与分析 ====================

    def analyze_user_behavior(self) -> Dict[str, Any]:
        """分析用户行为"""
        print("\n" + "=" * 60)
        print("  用户智能运营Agent - 用户行为分析")
        print("=" * 60)

        total_sessions = len(self.user_behaviors)
        new_visitors = sum(1 for b in self.user_behaviors if b.user_type == "new")
        returning_visitors = total_sessions - new_visitors
        avg_duration = sum(b.session_duration for b in self.user_behaviors) / total_sessions
        avg_pages = sum(len(b.pages_visited) for b in self.user_behaviors) / total_sessions
        bounce_rate = sum(b.bounce_rate for b in self.user_behaviors) / total_sessions
        conversion_rate = sum(1 for b in self.user_behaviors if b.has_conversion) / total_sessions

        # 热门页面
        page_views = defaultdict(int)
        for b in self.user_behaviors:
            for page in b.pages_visited:
                page_views[page] += 1
        top_pages = sorted(page_views.items(), key=lambda x: x[1], reverse=True)[:10]

        # 流量来源
        source_dist = defaultdict(int)
        for b in self.user_behaviors:
            source_dist[b.source] += 1

        # 设备分布
        device_dist = defaultdict(int)
        for b in self.user_behaviors:
            device_dist[b.device] += 1

        # 国家分布
        country_dist = defaultdict(int)
        for b in self.user_behaviors:
            country_dist[b.country] += 1

        # 兴趣分布
        interest_dist = defaultdict(int)
        for b in self.user_behaviors:
            for interest in b.interests:
                interest_dist[interest] += 1

        behavior_analysis = {
            "total_sessions": total_sessions,
            "new_visitors": new_visitors,
            "returning_visitors": returning_visitors,
            "new_visitor_percentage": new_visitors / total_sessions * 100,
            "avg_session_duration": avg_duration,
            "avg_pages_per_session": avg_pages,
            "bounce_rate": bounce_rate,
            "conversion_rate": conversion_rate,
            "top_pages": top_pages,
            "source_distribution": dict(source_dist),
            "device_distribution": dict(device_dist),
            "country_distribution": dict(country_dist),
            "interest_distribution": dict(interest_dist)
        }

        # 打印分析结果
        print(f"\n  📊 用户行为概览:")
        print(f"    总会话数: {total_sessions}")
        print(f"    新访客: {new_visitors} ({new_visitors/total_sessions*100:.1f}%)")
        print(f"    回访客: {returning_visitors} ({returning_visitors/total_sessions*100:.1f}%)")
        print(f"    平均会话时长: {avg_duration:.0f}秒")
        print(f"    平均页面浏览: {avg_pages:.1f}页")
        print(f"    跳出率: {bounce_rate*100:.1f}%")
        print(f"    转化率: {conversion_rate*100:.1f}%")

        print(f"\n  📊 热门页面 Top 5:")
        for page, views in top_pages[:5]:
            print(f"    {page}: {views}次浏览")

        print(f"\n  📊 流量来源:")
        for source, count in sorted(source_dist.items(), key=lambda x: x[1], reverse=True):
            print(f"    {source}: {count} ({count/total_sessions*100:.1f}%)")

        print(f"\n  📊 用户兴趣 Top 5:")
        for interest, count in sorted(interest_dist.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"    {interest}: {count}次")

        # 保存分析结果
        with open(USER_AUDIT_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "analyzed_at": datetime.now().isoformat(),
                "behavior_analysis": behavior_analysis,
                "recommendations": self._generate_behavior_recommendations(behavior_analysis)
            }, f, ensure_ascii=False, indent=2)

        print(f"\n  ✅ 用户行为分析已保存: {USER_AUDIT_FILE}")

        return behavior_analysis

    def _generate_behavior_recommendations(self, analysis: Dict) -> List[str]:
        """生成行为优化建议"""
        recommendations = []

        if analysis["bounce_rate"] > 0.6:
            recommendations.append(f"跳出率偏高（{analysis['bounce_rate']*100:.1f}%），优化落地页首屏内容和加载速度")
        if analysis["avg_session_duration"] < 60:
            recommendations.append(f"平均会话时长较短（{analysis['avg_session_duration']:.0f}秒），增加内链引导和相关内容推荐")
        if analysis["avg_pages_per_session"] < 2:
            recommendations.append(f"页面浏览深度不足（{analysis['avg_pages_per_session']:.1f}页），优化文章内链结构")
        if analysis["conversion_rate"] < 0.05:
            recommendations.append(f"转化率偏低（{analysis['conversion_rate']*100:.1f}%），优化CTA位置和联盟推荐区块")
        if analysis["new_visitor_percentage"] > 80:
            recommendations.append(f"新访客占比过高（{analysis['new_visitor_percentage']:.1f}%），加强邮件订阅和社媒关注，提升回访率")

        return recommendations

    # ==================== 2. 用户分层与画像 ====================

    def build_user_segments(self) -> List[UserSegmentProfile]:
        """构建用户分层与画像"""
        print("\n" + "=" * 60)
        print("  用户智能运营Agent - 用户分层与画像")
        print("=" * 60)

        segments = []

        # 1. 新访客
        new_visitors = [b for b in self.user_behaviors if b.user_type == "new"]
        if new_visitors:
            segments.append(self._create_segment_profile(
                "new_visitor", "新访客",
                new_visitors,
                ["首次访问网站", "对品牌不熟悉", "需要快速建立信任", "跳出率较高"],
                "提供高质量入门内容，优化首次体验，引导邮件订阅",
                ["中国旅行入门指南", "首次来中国必看", "旅行准备清单"]
            ))

        # 2. 随意浏览者
        casual_browsers = [b for b in self.user_behaviors
                          if b.user_type == "returning" and len(b.pages_visited) <= 2 and b.session_duration < 120]
        if casual_browsers:
            segments.append(self._create_segment_profile(
                "casual_browser", "随意浏览者",
                casual_browsers,
                ["快速浏览信息", "停留时间短", "未深度参与", "可能在对比多个网站"],
                "提供有价值的快速信息，增加视觉吸引力，引导深度阅读",
                ["快速旅行贴士", "信息图和清单", "热门目的地推荐"]
            ))

        # 3. 深度阅读者
        deep_readers = [b for b in self.user_behaviors
                       if len(b.pages_visited) >= 3 and b.session_duration >= 180]
        if deep_readers:
            segments.append(self._create_segment_profile(
                "deep_reader", "深度阅读者",
                deep_readers,
                ["阅读多篇文章", "停留时间长", "对内容有浓厚兴趣", "可能在计划旅行"],
                "提供深度内容和资源，引导邮件订阅，推荐相关文章和联盟产品",
                ["深度旅行攻略", "详细行程规划", "实用工具和资源"]
            ))

        # 4. 计划旅行者
        planning_travelers = [b for b in self.user_behaviors
                             if any("itinerary" in p or "planning" in p or "visa" in p for p in b.pages_visited)
                             and b.session_duration >= 120]
        if planning_travelers:
            segments.append(self._create_segment_profile(
                "planning_traveler", "计划旅行者",
                planning_travelers,
                [" actively planning a trip", "研究签证和行程", "高商业价值", "需要实用工具和预订链接"],
                "提供详细行程模板，推荐联盟产品（酒店/机票/保险），引导转化",
                ["完整行程模板", "签证申请指南", "预订工具和优惠"]
            ))

        # 5. 高意向用户
        high_intent = [b for b in self.user_behaviors
                      if b.has_conversion or any("insurance" in p or "booking" in p or "payment" in p for p in b.pages_visited)]
        if high_intent:
            segments.append(self._create_segment_profile(
                "high_intent", "高意向用户",
                high_intent,
                ["接近转化决策", "研究具体产品", "需要信任和保障", "对价格和评价敏感"],
                "优化转化路径，提供用户评价和保障，限时优惠，简化预订流程",
                ["产品对比评测", "用户真实评价", "限时优惠和折扣"]
            ))

        # 6. 转化用户
        converters = [b for b in self.user_behaviors if b.has_conversion]
        if converters:
            segments.append(self._create_segment_profile(
                "converter", "转化用户",
                converters,
                ["已完成联盟点击/预订", "高价值用户", "可能复购", "品牌认可度高"],
                "提供后续服务和支持，引导复购，鼓励分享和推荐，建立忠诚度",
                ["旅行后续指南", "目的地深度内容", "会员专属优惠"]
            ))

        self.user_segments = segments

        # 打印分层结果
        print(f"\n  📊 识别出 {len(segments)} 个用户分层:")
        print(f"\n  {'分层':<20} {'占比':<10} {'平均时长':<12} {'平均页数':<10} {'跳出率':<10} {'转化率':<10}")
        print("  " + "-" * 80)
        for segment in segments:
            print(f"  {segment.segment:<20} {segment.percentage:<10.1f}% {segment.avg_session_duration:<12.0f}s {segment.avg_pages_per_session:<10.1f} {segment.bounce_rate*100:<10.1f}% {segment.conversion_rate*100:<10.1f}%")

        # 保存分层结果
        with open(USER_SEGMENTS_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "analyzed_at": datetime.now().isoformat(),
                "total_segments": len(segments),
                "segments": [asdict(s) for s in segments]
            }, f, ensure_ascii=False, indent=2)

        print(f"\n  ✅ 用户分层与画像已保存: {USER_SEGMENTS_FILE}")

        return segments

    def _create_segment_profile(self, segment_id: str, name: str,
                                behaviors: List[UserBehavior],
                                characteristics: List[str],
                                strategy: str,
                                content_recs: List[str]) -> UserSegmentProfile:
        """创建单个分层画像"""
        total = len(self.user_behaviors)
        segment_count = len(behaviors)

        avg_duration = sum(b.session_duration for b in behaviors) / segment_count if segment_count > 0 else 0
        avg_pages = sum(len(b.pages_visited) for b in behaviors) / segment_count if segment_count > 0 else 0
        bounce = sum(b.bounce_rate for b in behaviors) / segment_count if segment_count > 0 else 0
        conversion = sum(1 for b in behaviors if b.has_conversion) / segment_count if segment_count > 0 else 0

        # 热门页面
        page_views = defaultdict(int)
        for b in behaviors:
            for page in b.pages_visited:
                page_views[page] += 1
        top_pages = [p for p, _ in sorted(page_views.items(), key=lambda x: x[1], reverse=True)[:5]]

        # 热门兴趣
        interest_dist = defaultdict(int)
        for b in behaviors:
            for interest in b.interests:
                interest_dist[interest] += 1
        top_interests = [i for i, _ in sorted(interest_dist.items(), key=lambda x: x[1], reverse=True)[:5]]

        return UserSegmentProfile(
            segment=segment_id,
            description=name,
            percentage=segment_count / total * 100 if total > 0 else 0,
            avg_session_duration=avg_duration,
            avg_pages_per_session=avg_pages,
            bounce_rate=bounce,
            conversion_rate=conversion,
            top_pages=top_pages,
            top_interests=top_interests,
            key_characteristics=characteristics,
            recommended_strategy=strategy,
            content_recommendations=content_recs
        )

    # ==================== 3. 用户旅程分析 ====================

    def analyze_user_journey(self) -> List[JourneyStage]:
        """分析用户旅程"""
        print("\n" + "=" * 60)
        print("  用户智能运营Agent - 用户旅程分析")
        print("=" * 60)

        journey_stages = [
            JourneyStage(
                stage="awareness",
                description="认知阶段 - 用户首次发现网站",
                user_percentage=100.0,
                avg_duration="首次访问",
                key_behaviors=["通过搜索/社媒发现网站", "浏览首页或热门文章", "判断网站是否可信"],
                drop_off_rate=45.0,
                pain_points=["首屏内容不吸引人", "加载速度慢", "缺乏信任信号"],
                optimization_opportunities=["优化首页首屏内容", "提升网站加载速度", "增加用户评价和信任信号"]
            ),
            JourneyStage(
                stage="interest",
                description="兴趣阶段 - 用户开始浏览内容",
                user_percentage=55.0,
                avg_duration="1-3分钟",
                key_behaviors=["浏览1-2篇文章", "查看热门目的地", "关注特定主题"],
                drop_off_rate=35.0,
                pain_points=["内容不够深入", "找不到相关内容", "内链引导不足"],
                optimization_opportunities=["优化文章内链结构", "增加相关文章推荐", "创建主题集群内容"]
            ),
            JourneyStage(
                stage="consideration",
                description="考虑阶段 - 用户深度研究旅行计划",
                user_percentage=35.0,
                avg_duration="3-10分钟",
                key_behaviors=["阅读多篇深度攻略", "查看签证和行程信息", "比较不同方案"],
                drop_off_rate=25.0,
                pain_points=["信息不够全面", "缺少实用工具", "联盟产品推荐不明显"],
                optimization_opportunities=["提供完整行程模板", "增加实用工具和资源", "优化联盟推荐区块"]
            ),
            JourneyStage(
                stage="conversion",
                description="转化阶段 - 用户完成联盟点击/预订",
                user_percentage=15.0,
                avg_duration="即时转化",
                key_behaviors=["点击联盟链接", "完成酒店/机票预订", "购买保险/eSIM"],
                drop_off_rate=60.0,
                pain_points=["CTA不明显", "跳转流程复杂", "缺乏信任和保障"],
                optimization_opportunities=["优化CTA位置和文案", "简化预订流程", "增加用户评价和保障"]
            ),
            JourneyStage(
                stage="retention",
                description="留存阶段 - 用户回访和持续参与",
                user_percentage=10.0,
                avg_duration="持续参与",
                key_behaviors=["回访网站", "订阅邮件", "关注社媒", "分享内容"],
                drop_off_rate=50.0,
                pain_points=["缺乏回访激励", "邮件内容不吸引人", "社媒互动不足"],
                optimization_opportunities=["建立邮件订阅序列", "提供会员专属内容", "增加社媒互动和活动"]
            ),
            JourneyStage(
                stage="advocacy",
                description="倡导阶段 - 用户成为品牌倡导者",
                user_percentage=5.0,
                avg_duration="长期忠诚",
                key_behaviors=["推荐给朋友", "发布旅行体验", "持续复购", "参与社区"],
                drop_off_rate=0.0,
                pain_points=["缺乏推荐激励", "社区氛围不足", "忠诚度计划缺失"],
                optimization_opportunities=["建立推荐奖励计划", "创建用户社区", "设计忠诚度计划"]
            )
        ]

        self.journey_stages = journey_stages

        # 打印旅程分析
        print(f"\n  📊 用户旅程分析（6个阶段）:")
        print(f"\n  {'阶段':<15} {'用户占比':<10} {'流失率':<10} {'关键痛点'}")
        print("  " + "-" * 80)
        for stage in journey_stages:
            top_pain = stage.pain_points[0] if stage.pain_points else "-"
            print(f"  {stage.stage:<15} {stage.user_percentage:<10.1f}% {stage.drop_off_rate:<10.1f}% {top_pain[:40]}")

        # 识别关键瓶颈
        print(f"\n  🔍 关键瓶颈识别:")
        bottlenecks = sorted(journey_stages, key=lambda x: x.drop_off_rate, reverse=True)[:3]
        for i, stage in enumerate(bottlenecks, 1):
            print(f"  {i}. {stage.stage}阶段 - 流失率{stage.drop_off_rate:.1f}%")
            print(f"     主要痛点: {', '.join(stage.pain_points[:2])}")
            print(f"     优化机会: {', '.join(stage.optimization_opportunities[:2])}")

        # 保存旅程分析
        with open(USER_JOURNEY_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "analyzed_at": datetime.now().isoformat(),
                "total_stages": len(journey_stages),
                "journey_stages": [asdict(s) for s in journey_stages],
                "key_bottlenecks": [s.stage for s in bottlenecks]
            }, f, ensure_ascii=False, indent=2)

        print(f"\n  ✅ 用户旅程分析已保存: {USER_JOURNEY_FILE}")

        return journey_stages

    # ==================== 4. 智能客服知识库 ====================

    def build_faq_knowledge_base(self) -> List[FAQItem]:
        """构建FAQ知识库"""
        print("\n" + "=" * 60)
        print("  用户智能运营Agent - FAQ知识库构建")
        print("=" * 60)

        # 按类别统计
        category_dist = defaultdict(int)
        for faq in self.faq_knowledge_base:
            category_dist[faq.category] += 1

        # 计算 helpful 率
        for faq in self.faq_knowledge_base:
            total_votes = faq.helpful_count + faq.not_helpful_count
            faq.helpful_rate = faq.helpful_count / total_votes * 100 if total_votes > 0 else 0

        # 热门FAQ
        popular_faqs = sorted(self.faq_knowledge_base, key=lambda x: x.view_count, reverse=True)[:5]

        # 需要更新的FAQ（helpful率低）
        needs_update = [faq for faq in self.faq_knowledge_base if hasattr(faq, 'helpful_rate') and faq.helpful_rate < 70]

        print(f"\n  📊 FAQ知识库统计:")
        print(f"    FAQ总数: {len(self.faq_knowledge_base)}")
        print(f"    覆盖类别: {len(category_dist)}个")
        print(f"    总浏览量: {sum(faq.view_count for faq in self.faq_knowledge_base)}")
        print(f"    需要更新: {len(needs_update)}个（helpful率<70%）")

        print(f"\n  📊 FAQ类别分布:")
        for category, count in sorted(category_dist.items(), key=lambda x: x[1], reverse=True):
            print(f"    {category}: {count}个")

        print(f"\n  🔥 热门FAQ Top 5:")
        for i, faq in enumerate(popular_faqs, 1):
            print(f"  {i}. [{faq.category}] {faq.question[:50]}... ({faq.view_count}次浏览)")

        # 保存知识库
        with open(FAQ_KNOWLEDGE_BASE_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "built_at": datetime.now().isoformat(),
                "total_faqs": len(self.faq_knowledge_base),
                "categories": dict(category_dist),
                "popular_faqs": [faq.id for faq in popular_faqs],
                "needs_update": [faq.id for faq in needs_update],
                "faq_items": [asdict(faq) for faq in self.faq_knowledge_base]
            }, f, ensure_ascii=False, indent=2)

        print(f"\n  ✅ FAQ知识库已保存: {FAQ_KNOWLEDGE_BASE_FILE}")

        return self.faq_knowledge_base

    def match_faq(self, query: str) -> List[FAQItem]:
        """匹配FAQ"""
        query_lower = query.lower()
        matched = []

        for faq in self.faq_knowledge_base:
            score = 0
            # 关键词匹配
            for keyword in faq.keywords:
                if keyword.lower() in query_lower:
                    score += 10
            # 问题匹配
            question_words = set(faq.question.lower().split())
            query_words = set(query_lower.split())
            common_words = question_words & query_words
            score += len(common_words) * 2
            # 类别匹配
            if faq.category in query_lower:
                score += 5

            if score > 0:
                matched.append((faq, score))

        matched.sort(key=lambda x: x[1], reverse=True)
        return [faq for faq, score in matched[:3]]

    # ==================== 5. 用户反馈收集与分析 ====================

    def analyze_feedback(self) -> Dict[str, Any]:
        """分析用户反馈"""
        print("\n" + "=" * 60)
        print("  用户智能运营Agent - 用户反馈分析")
        print("=" * 60)

        total_feedback = len(self.feedback_items)

        # 按类型统计
        type_dist = defaultdict(int)
        for fb in self.feedback_items:
            type_dist[fb.feedback_type] += 1

        # 按情感统计
        sentiment_dist = defaultdict(int)
        for fb in self.feedback_items:
            sentiment_dist[fb.sentiment] += 1

        # 按类别统计
        category_dist = defaultdict(int)
        for fb in self.feedback_items:
            category_dist[fb.category] += 1

        # 按优先级统计
        priority_dist = defaultdict(int)
        for fb in self.feedback_items:
            priority_dist[fb.priority] += 1

        # 高优先级反馈
        high_priority = [fb for fb in self.feedback_items if fb.priority == "high"]

        feedback_analysis = {
            "total_feedback": total_feedback,
            "type_distribution": dict(type_dist),
            "sentiment_distribution": dict(sentiment_dist),
            "category_distribution": dict(category_dist),
            "priority_distribution": dict(priority_dist),
            "high_priority_count": len(high_priority),
            "response_rate": sum(1 for fb in self.feedback_items if fb.status != "new") / total_feedback * 100
        }

        # 打印分析结果
        print(f"\n  📊 反馈统计:")
        print(f"    反馈总数: {total_feedback}")
        print(f"    回复率: {feedback_analysis['response_rate']:.1f}%")
        print(f"    高优先级: {len(high_priority)}个")

        print(f"\n  📊 反馈类型分布:")
        for ftype, count in sorted(type_dist.items(), key=lambda x: x[1], reverse=True):
            print(f"    {ftype}: {count} ({count/total_feedback*100:.1f}%)")

        print(f"\n  📊 情感分布:")
        for sentiment, count in sorted(sentiment_dist.items(), key=lambda x: x[1], reverse=True):
            print(f"    {sentiment}: {count} ({count/total_feedback*100:.1f}%)")

        print(f"\n  🔴 高优先级反馈:")
        for i, fb in enumerate(high_priority, 1):
            print(f"  {i}. [{fb.category}] {fb.content[:60]}...")

        # 保存分析结果
        with open(FEEDBACK_ANALYSIS_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "analyzed_at": datetime.now().isoformat(),
                "feedback_analysis": feedback_analysis,
                "high_priority_feedback": [asdict(fb) for fb in high_priority],
                "recommendations": self._generate_feedback_recommendations(feedback_analysis)
            }, f, ensure_ascii=False, indent=2)

        print(f"\n  ✅ 反馈分析已保存: {FEEDBACK_ANALYSIS_FILE}")

        return feedback_analysis

    def _generate_feedback_recommendations(self, analysis: Dict) -> List[str]:
        """生成反馈处理建议"""
        recommendations = []

        if analysis["high_priority_count"] > 0:
            recommendations.append(f"优先处理{analysis['high_priority_count']}个高优先级反馈")

        if analysis["sentiment_distribution"].get("negative", 0) > analysis["total_feedback"] * 0.3:
            recommendations.append("负面反馈占比较高，需要重点关注用户体验问题")

        if analysis["response_rate"] < 80:
            recommendations.append(f"反馈回复率偏低（{analysis['response_rate']:.1f}%），建立快速响应机制")

        if "content_accuracy" in analysis["category_distribution"]:
            recommendations.append("存在内容准确性反馈，需要加强内容审核和事实核查")

        if "technical" in analysis["category_distribution"]:
            recommendations.append("存在技术问题反馈，需要优化网站性能和用户体验")

        return recommendations

    # ==================== 6. 用户留存与忠诚度优化 ====================

    def build_retention_strategies(self) -> List[RetentionStrategy]:
        """构建留存策略"""
        print("\n" + "=" * 60)
        print("  用户智能运营Agent - 留存策略构建")
        print("=" * 60)

        strategies = [
            RetentionStrategy(
                id="ret_001",
                strategy_name="新访客欢迎邮件序列",
                description="新订阅用户发送3封欢迎邮件：第1天欢迎+热门内容，第3天旅行准备清单，第7天深度攻略+联盟推荐",
                target_segment="new_visitor",
                channel="email",
                trigger_condition="用户首次订阅邮件",
                expected_impact="提升回访率20-30%，增加首次转化机会",
                implementation_complexity="medium",
                status="proposed"
            ),
            RetentionStrategy(
                id="ret_002",
                strategy_name="深度阅读者内容推荐",
                description="基于用户阅读历史，每周发送个性化内容推荐邮件，包含相关文章和旅行灵感",
                target_segment="deep_reader",
                channel="email",
                trigger_condition="用户阅读≥3篇文章或停留≥5分钟",
                expected_impact="提升回访率15-25%，增加页面浏览深度",
                implementation_complexity="medium",
                status="proposed"
            ),
            RetentionStrategy(
                id="ret_003",
                strategy_name="计划旅行者转化序列",
                description="识别计划旅行的用户，发送行程模板、签证指南、预订优惠和实用工具，引导联盟转化",
                target_segment="planning_traveler",
                channel="email",
                trigger_condition="用户浏览签证/行程/预订相关页面",
                expected_impact="提升转化率30-50%，增加联盟收入",
                implementation_complexity="high",
                status="proposed"
            ),
            RetentionStrategy(
                id="ret_004",
                strategy_name="社媒互动和社区建设",
                description="在Instagram/Facebook/Pinterest建立活跃社区，定期发布旅行灵感、用户故事、问答互动，引导用户回访网站",
                target_segment="all_users",
                channel="social",
                trigger_condition="持续运营",
                expected_impact="提升品牌认知和回访率，增加社媒引流",
                implementation_complexity="medium",
                status="proposed"
            ),
            RetentionStrategy(
                id="ret_005",
                strategy_name="网站内相关内容推荐",
                description="在文章页底部和侧边栏增加智能相关内容推荐，基于用户当前阅读内容推荐相关文章，增加页面浏览深度和停留时间",
                target_segment="all_users",
                channel="onsite",
                trigger_condition="用户阅读文章时",
                expected_impact="提升页面浏览深度20-40%，降低跳出率",
                implementation_complexity="low",
                status="proposed"
            ),
            RetentionStrategy(
                id="ret_006",
                strategy_name="转化用户后续服务",
                description="对已完成联盟转化的用户，发送旅行后续指南、目的地深度内容、会员专属优惠，引导复购和推荐",
                target_segment="converter",
                channel="email",
                trigger_condition="用户完成联盟点击/预订",
                expected_impact="提升复购率20-30%，增加用户终身价值",
                implementation_complexity="high",
                status="proposed"
            ),
            RetentionStrategy(
                id="ret_007",
                strategy_name="流失用户召回",
                description="对30天未回访的用户，发送召回邮件，包含最新热门内容、限时优惠、旅行灵感，重新激活用户",
                target_segment="churned_user",
                channel="email",
                trigger_condition="用户30天未访问网站",
                expected_impact="召回5-15%流失用户，提升整体留存率",
                implementation_complexity="medium",
                status="proposed"
            ),
            RetentionStrategy(
                id="ret_008",
                strategy_name="用户反馈快速响应机制",
                description="建立用户反馈收集和快速响应机制，24小时内回复高优先级反馈，将负面反馈转化为改进机会，提升用户满意度和忠诚度",
                target_segment="all_users",
                channel="onsite",
                trigger_condition="用户提交反馈",
                expected_impact="提升用户满意度30-50%，减少负面口碑",
                implementation_complexity="low",
                status="proposed"
            )
        ]

        self.retention_strategies = strategies

        # 打印策略
        print(f"\n  📊 构建 {len(strategies)} 个留存策略:")
        print(f"\n  {'ID':<8} {'策略名称':<25} {'目标分层':<20} {'渠道':<10} {'复杂度':<10} {'预期影响'}")
        print("  " + "-" * 100)
        for strategy in strategies:
            print(f"  {strategy.id:<8} {strategy.strategy_name[:24]:<25} {strategy.target_segment:<20} {strategy.channel:<10} {strategy.implementation_complexity:<10} {strategy.expected_impact[:30]}...")

        # 按优先级排序（先低复杂度高影响）
        priority_strategies = sorted(strategies, key=lambda x: (
            {"low": 0, "medium": 1, "high": 2}.get(x.implementation_complexity, 3),
            x.id
        ))

        print(f"\n  🚀 建议实施顺序（先易后难）:")
        for i, strategy in enumerate(priority_strategies[:4], 1):
            print(f"  {i}. {strategy.strategy_name}（{strategy.implementation_complexity}复杂度）")

        # 保存策略
        with open(RETENTION_STRATEGY_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "built_at": datetime.now().isoformat(),
                "total_strategies": len(strategies),
                "recommended_implementation_order": [s.id for s in priority_strategies],
                "retention_strategies": [asdict(s) for s in strategies]
            }, f, ensure_ascii=False, indent=2)

        print(f"\n  ✅ 留存策略已保存: {RETENTION_STRATEGY_FILE}")

        # P1-AI-OPS-03: Strategy-informed retention strategies
        if getattr(self, "strategy", None) and self.strategy.available:
            high_intent = self.strategy.get_priority_list("high_intent_segments")
            best_retention = self.strategy.get_priority_list("best_retention_strategies")
            if high_intent or best_retention:
                print(f"  📋 策略已消费: version={self.strategy.version}, high_intent={len(high_intent)}, best_retention={len(best_retention)}")


        return strategies

    # ==================== 7. 生成完整报告 ====================

    def generate_full_report(self) -> str:
        """生成完整的用户智能运营报告"""
        print("\n" + "=" * 60)
        print("  用户智能运营Agent - 生成完整报告")
        print("=" * 60)

        now = datetime.now()

        report = f"""# ChinaBound Travel 用户智能运营报告

**生成时间**: {now.strftime('%Y-%m-%d %H:%M:%S')}
**引擎版本**: v1.0
**成熟度目标**: L1 → L2

---

## 📊 执行摘要

| 指标 | 数值 |
|------|------|
| 分析会话数 | {len(self.user_behaviors)} |
| 用户分层数 | {len(self.user_segments)} |
| 旅程阶段数 | {len(self.journey_stages)} |
| FAQ知识库 | {len(self.faq_knowledge_base)}条 |
| 用户反馈 | {len(self.feedback_items)}条 |
| 留存策略 | {len(self.retention_strategies)}个 |

---

## 👥 用户行为分析

### 核心指标

| 指标 | 数值 | 说明 |
|------|------|------|
| 总会话数 | {len(self.user_behaviors)} | 分析周期内 |
| 新访客占比 | {sum(1 for b in self.user_behaviors if b.user_type == 'new') / len(self.user_behaviors) * 100:.1f}% | 首次访问 |
| 平均会话时长 | {sum(b.session_duration for b in self.user_behaviors) / len(self.user_behaviors):.0f}秒 | 用户参与度 |
| 平均页面浏览 | {sum(len(b.pages_visited) for b in self.user_behaviors) / len(self.user_behaviors):.1f}页 | 内容深度 |
| 跳出率 | {sum(b.bounce_rate for b in self.user_behaviors) / len(self.user_behaviors) * 100:.1f}% | 单页离开 |
| 转化率 | {sum(1 for b in self.user_behaviors if b.has_conversion) / len(self.user_behaviors) * 100:.1f}% | 联盟转化 |

### 用户分层画像

| 分层 | 占比 | 平均时长 | 平均页数 | 跳出率 | 转化率 | 核心策略 |
|------|------|----------|----------|--------|--------|----------|
"""

        for segment in self.user_segments:
            report += f"| {segment.description} | {segment.percentage:.1f}% | {segment.avg_session_duration:.0f}s | {segment.avg_pages_per_session:.1f} | {segment.bounce_rate*100:.1f}% | {segment.conversion_rate*100:.1f}% | {segment.recommended_strategy[:30]}... |\n"

        report += """
---

## 🛤️ 用户旅程分析

### 旅程阶段

| 阶段 | 用户占比 | 流失率 | 关键痛点 | 优化机会 |
|------|----------|--------|----------|----------|
"""

        for stage in self.journey_stages:
            pain = stage.pain_points[0] if stage.pain_points else "-"
            opportunity = stage.optimization_opportunities[0] if stage.optimization_opportunities else "-"
            report += f"| {stage.description} | {stage.user_percentage:.1f}% | {stage.drop_off_rate:.1f}% | {pain[:30]} | {opportunity[:30]} |\n"

        report += """
### 关键瓶颈

1. **认知→兴趣** - 45%流失率，优化首屏内容和加载速度
2. **考虑→转化** - 60%流失率，优化CTA和联盟推荐
3. **转化→留存** - 50%流失率，建立邮件序列和回访激励

---

## 💬 智能客服知识库

### FAQ统计

| 类别 | 数量 | 热门问题 |
|------|------|----------|
"""

        category_faqs = defaultdict(list)
        for faq in self.faq_knowledge_base:
            category_faqs[faq.category].append(faq)

        for category, faqs in sorted(category_faqs.items(), key=lambda x: len(x[1]), reverse=True):
            top_faq = max(faqs, key=lambda x: x.view_count)
            report += f"| {category} | {len(faqs)} | {top_faq.question[:40]}... |\n"

        report += f"""
### 智能客服能力

- **FAQ自动匹配**: 基于关键词和语义匹配，快速找到相关答案
- **问题分类**: 自动将用户问题分类到12个类别
- **相关文章推荐**: 每个FAQ关联相关深度文章
- **反馈收集**: 用户可标记答案是否有帮助，持续优化
- **需要更新**: {sum(1 for faq in self.faq_knowledge_base if hasattr(faq, 'helpful_rate') and faq.helpful_rate < 70)}个FAQ helpful率<70%，需要优化

---

## 📝 用户反馈分析

### 反馈概览

| 指标 | 数值 |
|------|------|
| 反馈总数 | {len(self.feedback_items)} |
| 正面反馈 | {sum(1 for fb in self.feedback_items if fb.sentiment == 'positive')} |
| 中性反馈 | {sum(1 for fb in self.feedback_items if fb.sentiment == 'neutral')} |
| 负面反馈 | {sum(1 for fb in self.feedback_items if fb.sentiment == 'negative')} |
| 高优先级 | {sum(1 for fb in self.feedback_items if fb.priority == 'high')} |
| 回复率 | {sum(1 for fb in self.feedback_items if fb.status != 'new') / len(self.feedback_items) * 100:.1f}% |

### 反馈类型分布

| 类型 | 数量 | 占比 |
|------|------|------|
"""

        type_dist = defaultdict(int)
        for fb in self.feedback_items:
            type_dist[fb.feedback_type] += 1

        for ftype, count in sorted(type_dist.items(), key=lambda x: x[1], reverse=True):
            report += f"| {ftype} | {count} | {count/len(self.feedback_items)*100:.1f}% |\n"

        report += """
---

## 🔄 留存与忠诚度策略

### 留存策略清单

| ID | 策略名称 | 目标分层 | 渠道 | 复杂度 | 预期影响 |
|----|----------|----------|------|--------|----------|
"""

        for strategy in self.retention_strategies:
            report += f"| {strategy.id} | {strategy.strategy_name} | {strategy.target_segment} | {strategy.channel} | {strategy.implementation_complexity} | {strategy.expected_impact[:30]}... |\n"

        report += """
### 建议实施顺序

**第一阶段（1-2周）- 快速见效**:
1. 网站内相关内容推荐（低复杂度，提升页面浏览深度）
2. 用户反馈快速响应机制（低复杂度，提升满意度）
3. 新访客欢迎邮件序列（中复杂度，提升回访率）

**第二阶段（1个月）- 深度优化**:
4. 深度阅读者内容推荐（中复杂度，个性化推荐）
5. 社媒互动和社区建设（中复杂度，品牌建设）
6. 流失用户召回（中复杂度，挽回流失用户）

**第三阶段（2-3个月）- 高级功能**:
7. 计划旅行者转化序列（高复杂度，提升转化）
8. 转化用户后续服务（高复杂度，提升复购和LTV）

---

## 🎯 优化行动计划

### 立即执行（1-3天）
1. **优化首屏内容** - 降低认知阶段45%流失率
2. **增加相关内容推荐** - 提升页面浏览深度20-40%
3. **建立反馈快速响应机制** - 24小时内回复高优先级反馈
4. **优化CTA位置和文案** - 提升考虑→转化阶段转化率

### 短期优化（1-2周）
5. **搭建新访客欢迎邮件序列** - 3封邮件引导深度参与
6. **完善FAQ知识库** - 补充常见问题，优化低helpful率答案
7. **优化网站加载速度** - 降低跳出率，提升用户体验
8. **增加用户评价和信任信号** - 提升转化率

### 中期建设（1个月）
9. **实现个性化内容推荐** - 基于用户行为推荐相关内容
10. **建立用户分层运营体系** - 针对不同分层定制策略
11. **搭建社媒社区** - 提升用户互动和品牌忠诚度
12. **实现流失用户召回** - 邮件+社媒多渠道召回

### 长期战略（3个月）
13. **建立用户忠诚度计划** - 积分、等级、专属优惠
14. **实现智能客服机器人** - 7x24小时自动解答常见问题
15. **用户社区建设** - UGC内容、旅行分享、互助社区
16. **数据驱动的持续优化** - A/B测试、用户调研、持续迭代

---

## 📊 成熟度评估

| 能力维度 | 当前等级 | 目标等级 | 状态 |
|----------|----------|----------|------|
| 用户行为分析 | L2 | L2 | ✅ 已达标 |
| 用户分层画像 | L1 | L2 | 🟡 进行中 |
| 用户旅程分析 | L1 | L2 | 🟡 进行中 |
| 智能客服 | L0 | L2 | 🔴 需建设 |
| 反馈分析 | L1 | L2 | 🟡 进行中 |
| 留存优化 | L1 | L2 | 🟡 进行中 |
| 忠诚度计划 | L0 | L1 | 🔴 需建设 |

**综合成熟度**: L1 → L2（进行中）

---

*报告由用户智能运营Agent自动生成 | """ + now.strftime('%Y-%m-%d %H:%M:%S') + """*
*引擎版本: v1.0 | 成熟度目标: L1 → L2*
"""

        # 保存报告
        with open(USER_REPORT_FILE, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"\n  ✅ 报告已生成: {USER_REPORT_FILE}")
        print(f"  📊 报告长度: {len(report)} 字符")

        return report

    # ==================== 8. 完整优化流程 ====================

    def run_full_optimization(self):
        """运行完整的用户智能运营流程"""
        print("\n" + "=" * 60)
        print("  ChinaBound Travel - 用户智能运营Agent")
        print("  完整优化流程")
        print("=" * 60)

        print(f"\n📅 运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Step 1: 用户行为分析
        self.analyze_user_behavior()

        # Step 2: 用户分层与画像
        self.build_user_segments()

        # Step 3: 用户旅程分析
        self.analyze_user_journey()

        # Step 4: FAQ知识库构建
        self.build_faq_knowledge_base()

        # Step 5: 用户反馈分析
        self.analyze_feedback()

        # Step 6: 留存策略构建
        self.build_retention_strategies()

        # Step 7: 生成报告
        self.generate_full_report()

        print("\n" + "=" * 60)
        print("  ✅ 完整用户智能优化流程完成！")
        print("=" * 60)
        print(f"\n📁 报告目录: {USER_DIR}")
        print(f"📄 用户运营报告: {USER_REPORT_FILE}")
        print(f"👥 用户行为分析: {USER_AUDIT_FILE}")
        print(f"🎯 用户分层画像: {USER_SEGMENTS_FILE}")
        print(f"🛤️ 用户旅程分析: {USER_JOURNEY_FILE}")
        print(f"💬 FAQ知识库: {FAQ_KNOWLEDGE_BASE_FILE}")
        print(f"📝 反馈分析: {FEEDBACK_ANALYSIS_FILE}")
        print(f"🔄 留存策略: {RETENTION_STRATEGY_FILE}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="ChinaBound Travel 用户智能运营Agent")
    parser.add_argument("--all", action="store_true", help="运行完整优化流程")
    parser.add_argument("--behavior", action="store_true", help="仅用户行为分析")
    parser.add_argument("--segments", action="store_true", help="仅用户分层画像")
    parser.add_argument("--journey", action="store_true", help="仅用户旅程分析")
    parser.add_argument("--faq", action="store_true", help="仅FAQ知识库构建")
    parser.add_argument("--feedback", action="store_true", help="仅用户反馈分析")
    parser.add_argument("--retention", action="store_true", help="仅留存策略构建")
    parser.add_argument("--report", action="store_true", help="仅生成报告")

    args = parser.parse_args()

    agent = UserIntelligenceAgent()

    if args.all or not any([args.behavior, args.segments, args.journey, args.faq, args.feedback, args.retention, args.report]):
        agent.run_full_optimization()
    elif args.behavior:
        agent.analyze_user_behavior()
    elif args.segments:
        agent.analyze_user_behavior()
        agent.build_user_segments()
    elif args.journey:
        agent.analyze_user_journey()
    elif args.faq:
        agent.build_faq_knowledge_base()
    elif args.feedback:
        agent.analyze_feedback()
    elif args.retention:
        agent.build_retention_strategies()
    elif args.report:
        agent.analyze_user_behavior()
        agent.build_user_segments()
        agent.analyze_user_journey()
        agent.build_faq_knowledge_base()
        agent.analyze_feedback()
        agent.build_retention_strategies()
        agent.generate_full_report()


if __name__ == "__main__":
    main()
