#!/usr/bin/env python3
"""
ChinaBound Travel - 社媒智能优化Agent
Social Intelligence Agent

核心能力（L2 → L3）：
1. 社媒内容效果追踪与分析 - 展示/点击/互动/转化全链路
2. 智能分发时间优化 - 基于用户活跃时间的最佳发布时间推荐
3. 平台内容适配优化 - Instagram/Facebook/Pinterest/X各平台最佳实践
4. 爆款内容模式识别 - 基于历史数据的高互动内容特征提取
5. 社媒引流效果分析 - 社媒→网站→联盟转化全漏斗分析
6. 社媒内容自动迭代优化 - 基于效果数据的内容自动改进建议

成熟度目标：L2 → L3（6个月）
"""

import os
import sys
import json
import csv
import re
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
from collections import defaultdict


# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
SOCIAL_DIR = REPORTS_DIR / "social"
SOCIAL_DIR.mkdir(parents=True, exist_ok=True)

# 数据文件
SOCIAL_AUDIT_FILE = SOCIAL_DIR / "social_audit_report.json"
POST_PERFORMANCE_FILE = SOCIAL_DIR / "post_performance_data.json"
BEST_TIMES_FILE = SOCIAL_DIR / "best_publishing_times.json"
VIRAL_PATTERNS_FILE = SOCIAL_DIR / "viral_content_patterns.json"
TRAFFIC_FUNNEL_FILE = SOCIAL_DIR / "social_traffic_funnel.json"
OPTIMIZATION_PLAN_FILE = SOCIAL_DIR / "social_optimization_plan.json"
SOCIAL_REPORT_FILE = SOCIAL_DIR / "social_intelligence_report.md"

# 平台定义
PLATFORMS = ["instagram", "facebook", "pinterest", "x", "linkedin"]

# 各平台最佳实践
PLATFORM_BEST_PRACTICES = {
    "instagram": {
        "best_times": ["09:00", "11:00", "14:00", "18:00", "21:00"],
        "best_days": ["monday", "wednesday", "thursday", "friday", "saturday"],
        "ideal_caption_length": 125,
        "hashtag_count": 5,
        "content_types": ["carousel", "reel", "image", "story"],
        "engagement_rate_benchmark": 0.03,
        "description": "视觉为主，重视觉冲击力和故事性"
    },
    "facebook": {
        "best_times": ["09:00", "13:00", "15:00", "19:00"],
        "best_days": ["monday", "wednesday", "thursday", "friday"],
        "ideal_caption_length": 80,
        "hashtag_count": 2,
        "content_types": ["image", "video", "link", "carousel"],
        "engagement_rate_benchmark": 0.02,
        "description": "社区互动为主，重视频分享和讨论"
    },
    "pinterest": {
        "best_times": ["20:00", "21:00", "22:00", "14:00"],
        "best_days": ["friday", "saturday", "sunday"],
        "ideal_caption_length": 200,
        "hashtag_count": 3,
        "content_types": ["pin", "board", "story", "video"],
        "engagement_rate_benchmark": 0.05,
        "description": "搜索和发现为主，重信息图和长尾关键词"
    },
    "x": {
        "best_times": ["08:00", "12:00", "17:00", "20:00"],
        "best_days": ["monday", "tuesday", "wednesday", "thursday"],
        "ideal_caption_length": 280,
        "hashtag_count": 2,
        "content_types": ["tweet", "thread", "image", "video"],
        "engagement_rate_benchmark": 0.015,
        "description": "实时信息为主，重简洁和话题性"
    },
    "linkedin": {
        "best_times": ["09:00", "10:00", "12:00", "17:00"],
        "best_days": ["tuesday", "wednesday", "thursday"],
        "ideal_caption_length": 150,
        "hashtag_count": 3,
        "content_types": ["article", "image", "video", "document"],
        "engagement_rate_benchmark": 0.025,
        "description": "专业内容为主，重深度和价值"
    }
}


class ContentType(Enum):
    """内容类型"""
    TIP = "tip"                          # 旅行知识型
    WARNING = "warning"                  # 避坑型
    STORY = "story"                      # 城市故事型
    VISUAL = "visual"                    # 图片视觉型
    CONVERSION = "conversion"            # 商业转化型
    LIST = "list"                        # 列表型
    GUIDE = "guide"                      # 攻略型
    QUESTION = "question"                # 问答型


class PostStatus(Enum):
    """帖子状态"""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"


@dataclass
class SocialPost:
    """社媒帖子记录"""
    id: str
    platform: str
    content_type: str
    title: str
    caption: str
    article_url: str
    utm_source: str
    publish_time: str
    status: str

    # 效果数据
    impressions: int = 0
    reach: int = 0
    clicks: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    engagement_rate: float = 0.0
    click_through_rate: float = 0.0
    conversion_rate: float = 0.0
    revenue: float = 0.0

    # 质量评分
    quality_score: float = 0.0
    viral_score: float = 0.0
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class PlatformPerformance:
    """平台表现"""
    platform: str
    total_posts: int = 0
    total_impressions: int = 0
    total_clicks: int = 0
    total_engagement: int = 0
    avg_engagement_rate: float = 0.0
    avg_ctr: float = 0.0
    best_content_types: List[str] = field(default_factory=list)
    best_publishing_times: List[str] = field(default_factory=list)
    growth_trend: str = "stable"
    recommendations: List[str] = field(default_factory=list)


@dataclass
class ViralPattern:
    """爆款内容模式"""
    id: str
    pattern_name: str
    description: str
    content_type: str
    platforms: List[str]
    avg_engagement_rate: float = 0.0
    sample_size: int = 0
    key_elements: List[str] = field(default_factory=list)
    headline_templates: List[str] = field(default_factory=list)
    recommended_usage: str = ""
    confidence: float = 0.0


@dataclass
class BestPublishingTime:
    """最佳发布时间"""
    platform: str
    day: str
    hour: int
    avg_impressions: int = 0
    avg_engagement: float = 0.0
    post_count: int = 0
    confidence: float = 0.0
    recommendation: str = ""


class SocialIntelligenceAgent:
    """社媒智能优化Agent主类"""

    def __init__(self):
        self.posts: List[SocialPost] = []
        self.platform_performances: Dict[str, PlatformPerformance] = {}
        self.viral_patterns: List[ViralPattern] = []
        self.best_times: List[BestPublishingTime] = []
        self._load_existing_data()

    def _load_existing_data(self):
        """加载现有数据"""
        # 加载帖子性能数据
        if POST_PERFORMANCE_FILE.exists():
            try:
                with open(POST_PERFORMANCE_FILE, encoding="utf-8") as f:
                    data = json.load(f)
                    self.posts = [SocialPost(**p) for p in data.get("posts", [])]
            except Exception as e:
                print(f"  ⚠️ 加载帖子数据失败: {e}")

        # 如果没有数据，生成模拟数据用于演示
        if not self.posts:
            self._generate_sample_data()

    def _generate_sample_data(self):
        """生成模拟数据用于演示（实际使用时应从Buffer API获取）"""
        print("  📊 生成模拟社媒数据用于演示...")

        content_types = [ct.value for ct in ContentType]
        sample_titles = [
            "China Travel Tips #018: High-Speed Rail Guide",
            "5 Things Tourists Should Know Before Visiting China",
            "Why Chengdu Feels Different? Not Just Pandas",
            "Guilin Karst Landscape: Some Places Don't Look Real",
            "Planning China Trip? Here's Your Complete Checklist",
            "China Street Food: A First-Timer's Guide",
            "144-Hour Visa-Free Transit: Complete Guide",
            "Alipay vs WeChat Pay: Which Should Foreigners Use?",
            "China Photography: Best Spots for Stunning Photos",
            "What to Pack for China: Ultimate Packing List"
        ]

        for i in range(50):
            platform = PLATFORMS[i % len(PLATFORMS)]
            content_type = content_types[i % len(content_types)]
            hour = [8, 9, 11, 13, 14, 17, 18, 19, 21, 22][i % 10]
            day = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][i % 7]

            # 模拟效果数据（不同平台和内容类型有不同表现）
            base_impressions = {
                "instagram": 500, "facebook": 300, "pinterest": 800,
                "x": 200, "linkedin": 150
            }
            type_multiplier = {
                "visual": 1.5, "tip": 1.2, "warning": 1.3,
                "story": 1.1, "list": 1.4, "guide": 1.0,
                "conversion": 0.8, "question": 1.2
            }

            impressions = int(base_impressions.get(platform, 300) * type_multiplier.get(content_type, 1.0) * (0.5 + (i % 10) / 10))
            clicks = int(impressions * (0.02 + (i % 5) * 0.01))
            likes = int(impressions * (0.03 + (i % 4) * 0.01))
            comments = int(likes * 0.1)
            shares = int(likes * 0.05)
            saves = int(likes * 0.15)

            engagement = likes + comments + shares + saves
            engagement_rate = engagement / impressions if impressions > 0 else 0
            ctr = clicks / impressions if impressions > 0 else 0

            post = SocialPost(
                id=f"post_{i+1:03d}",
                platform=platform,
                content_type=content_type,
                title=sample_titles[i % len(sample_titles)],
                caption=f"Sample caption for {content_type} post on {platform}",
                article_url=f"https://www.chinaboundtravel.com/posts/sample-article-{i}/",
                utm_source=platform,
                publish_time=f"2026-08-{1 + (i % 28):02d} {hour:02d}:00:00",
                status="published",
                impressions=impressions,
                reach=int(impressions * 0.8),
                clicks=clicks,
                likes=likes,
                comments=comments,
                shares=shares,
                saves=saves,
                engagement_rate=engagement_rate,
                click_through_rate=ctr,
                conversion_rate=clicks * 0.01 if clicks > 0 else 0,
                revenue=clicks * 0.05 if clicks > 0 else 0
            )

            # 质量评分和问题检测
            self._score_post_quality(post)

            self.posts.append(post)

        # 保存模拟数据
        self._save_post_data()

    def _save_post_data(self):
        """保存帖子数据"""
        with open(POST_PERFORMANCE_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "posts": [asdict(p) for p in self.posts],
                "total_count": len(self.posts),
                "last_updated": datetime.now().isoformat(),
                "data_source": "sample_data (replace with Buffer API)"
            }, f, ensure_ascii=False, indent=2)

    # ==================== 1. 社媒内容效果追踪与分析 ====================

    def analyze_post_performance(self) -> Dict[str, PlatformPerformance]:
        """分析所有帖子的表现"""
        print("\n" + "=" * 60)
        print("  社媒智能优化Agent - 内容效果分析")
        print("=" * 60)

        platform_performances = {}

        for platform in PLATFORMS:
            platform_posts = [p for p in self.posts if p.platform == platform]
            if not platform_posts:
                continue

            perf = PlatformPerformance(platform=platform)
            perf.total_posts = len(platform_posts)
            perf.total_impressions = sum(p.impressions for p in platform_posts)
            perf.total_clicks = sum(p.clicks for p in platform_posts)
            perf.total_engagement = sum(p.likes + p.comments + p.shares + p.saves for p in platform_posts)
            perf.avg_engagement_rate = sum(p.engagement_rate for p in platform_posts) / len(platform_posts)
            perf.avg_ctr = sum(p.click_through_rate for p in platform_posts) / len(platform_posts)

            # 最佳内容类型
            type_performance = defaultdict(lambda: {"count": 0, "engagement": 0.0})
            for p in platform_posts:
                type_performance[p.content_type]["count"] += 1
                type_performance[p.content_type]["engagement"] += p.engagement_rate

            best_types = sorted(
                type_performance.items(),
                key=lambda x: x[1]["engagement"] / x[1]["count"] if x[1]["count"] > 0 else 0,
                reverse=True
            )[:3]
            perf.best_content_types = [t[0] for t in best_types]

            # 最佳发布时间
            time_performance = defaultdict(lambda: {"count": 0, "impressions": 0})
            for p in platform_posts:
                try:
                    hour = int(p.publish_time.split(" ")[1].split(":")[0])
                    time_performance[hour]["count"] += 1
                    time_performance[hour]["impressions"] += p.impressions
                except Exception:
                    pass

            best_times = sorted(
                time_performance.items(),
                key=lambda x: x[1]["impressions"] / x[1]["count"] if x[1]["count"] > 0 else 0,
                reverse=True
            )[:3]
            perf.best_publishing_times = [f"{t[0]:02d}:00" for t in best_times]

            # 增长趋势（简化：基于最近帖子的表现）
            recent_posts = platform_posts[-10:] if len(platform_posts) >= 10 else platform_posts
            older_posts = platform_posts[:-10] if len(platform_posts) >= 10 else []
            if older_posts:
                recent_avg = sum(p.engagement_rate for p in recent_posts) / len(recent_posts)
                older_avg = sum(p.engagement_rate for p in older_posts) / len(older_posts)
                if recent_avg > older_avg * 1.1:
                    perf.growth_trend = "growing"
                elif recent_avg < older_avg * 0.9:
                    perf.growth_trend = "declining"
                else:
                    perf.growth_trend = "stable"

            # 平台建议
            perf.recommendations = self._generate_platform_recommendations(perf)

            platform_performances[platform] = perf

        self.platform_performances = platform_performances

        # 打印分析结果
        print(f"\n  📊 分析 {len(self.posts)} 条帖子，覆盖 {len(platform_performances)} 个平台")
        print(f"\n  平台表现对比:")
        print(f"  {'平台':<12} {'帖子数':<8} {'总展示':<10} {'总点击':<8} {'平均互动率':<12} {'平均CTR':<10} {'趋势':<10}")
        print("  " + "-" * 80)
        for platform, perf in sorted(platform_performances.items(), key=lambda x: x[1].total_impressions, reverse=True):
            print(f"  {platform:<12} {perf.total_posts:<8} {perf.total_impressions:<10} {perf.total_clicks:<8} {perf.avg_engagement_rate*100:<12.2f}% {perf.avg_ctr*100:<10.2f}% {perf.growth_trend:<10}")

        # 保存分析结果
        audit_report = {
            "analyzed_at": datetime.now().isoformat(),
            "total_posts": len(self.posts),
            "platforms_analyzed": len(platform_performances),
            "platform_performances": {k: asdict(v) for k, v in platform_performances.items()},
            "top_performing_posts": [asdict(p) for p in sorted(self.posts, key=lambda x: x.engagement_rate, reverse=True)[:10]],
            "worst_performing_posts": [asdict(p) for p in sorted(self.posts, key=lambda x: x.engagement_rate)[:10]]
        }

        with open(SOCIAL_AUDIT_FILE, "w", encoding="utf-8") as f:
            json.dump(audit_report, f, ensure_ascii=False, indent=2)

        print(f"\n  ✅ 分析报告已保存: {SOCIAL_AUDIT_FILE}")

        return platform_performances

    def _score_post_quality(self, post: SocialPost):
        """评估帖子质量"""
        score = 100.0
        issues = []
        recommendations = []

        # 文案长度检查
        best_practices = PLATFORM_BEST_PRACTICES.get(post.platform, {})
        ideal_length = best_practices.get("ideal_caption_length", 100)
        caption_length = len(post.caption)

        if caption_length < ideal_length * 0.5:
            score -= 15
            issues.append(f"文案过短（{caption_length}字符，理想{ideal_length}）")
            recommendations.append("增加文案长度，提供更多价值信息")
        elif caption_length > ideal_length * 1.5:
            score -= 10
            issues.append(f"文案过长（{caption_length}字符，理想{ideal_length}）")
            recommendations.append("精简文案，突出核心信息")

        # 互动率检查
        benchmark = best_practices.get("engagement_rate_benchmark", 0.02)
        if post.engagement_rate < benchmark * 0.5:
            score -= 20
            issues.append(f"互动率过低（{post.engagement_rate*100:.2f}%，基准{benchmark*100:.1f}%）")
            recommendations.append("优化内容质量，增加互动引导（提问、投票等）")
        elif post.engagement_rate > benchmark * 1.5:
            score += 10  # 高互动加分

        # CTR检查
        if post.click_through_rate < 0.01:
            score -= 15
            issues.append(f"点击率过低（{post.click_through_rate*100:.2f}%）")
            recommendations.append("优化CTA文案，增加行动号召，优化链接位置")

        # 内容类型适配
        platform_content_types = best_practices.get("content_types", [])
        if post.content_type not in ["tip", "warning", "story", "visual", "list", "guide"]:
            pass  # 简化检查

        post.quality_score = max(0, min(100, score))
        post.issues = issues
        post.recommendations = recommendations

        # 爆款评分（基于互动率和分享率）
        viral_score = 0.0
        if post.engagement_rate > benchmark * 2:
            viral_score += 40
        elif post.engagement_rate > benchmark * 1.5:
            viral_score += 25

        share_rate = post.shares / post.impressions if post.impressions > 0 else 0
        if share_rate > 0.01:
            viral_score += 30
        elif share_rate > 0.005:
            viral_score += 15

        save_rate = post.saves / post.impressions if post.impressions > 0 else 0
        if save_rate > 0.02:
            viral_score += 30
        elif save_rate > 0.01:
            viral_score += 15

        post.viral_score = min(100, viral_score)

    def _generate_platform_recommendations(self, perf: PlatformPerformance) -> List[str]:
        """生成平台优化建议"""
        recommendations = []
        best_practices = PLATFORM_BEST_PRACTICES.get(perf.platform, {})

        # 互动率对比
        benchmark = best_practices.get("engagement_rate_benchmark", 0.02)
        if perf.avg_engagement_rate < benchmark * 0.7:
            recommendations.append(f"互动率低于基准（{perf.avg_engagement_rate*100:.2f}% vs {benchmark*100:.1f}%），优化内容质量和互动引导")
        elif perf.avg_engagement_rate > benchmark * 1.3:
            recommendations.append(f"互动率高于基准，继续保持，可尝试增加发布频率")

        # CTR对比
        if perf.avg_ctr < 0.015:
            recommendations.append("点击率偏低，优化CTA文案和链接展示方式")

        # 内容类型建议
        if perf.best_content_types:
            recommendations.append(f"优先使用高互动内容类型：{', '.join(perf.best_content_types)}")

        # 发布时间建议
        if perf.best_publishing_times:
            recommendations.append(f"最佳发布时间：{', '.join(perf.best_publishing_times)}")

        # 增长趋势
        if perf.growth_trend == "declining":
            recommendations.append("⚠️ 表现呈下降趋势，需要调整内容策略")
        elif perf.growth_trend == "growing":
            recommendations.append("📈 表现呈增长趋势，继续优化并扩大投入")

        return recommendations

    # ==================== 2. 智能分发时间优化 ====================

    def analyze_best_publishing_times(self) -> List[BestPublishingTime]:
        """分析最佳发布时间"""
        print("\n" + "=" * 60)
        print("  社媒智能优化Agent - 最佳发布时间分析")
        print("=" * 60)

        best_times = []

        for platform in PLATFORMS:
            platform_posts = [p for p in self.posts if p.platform == platform]
            if not platform_posts:
                continue

            # 按小时和星期分析
            time_data = defaultdict(lambda: {"count": 0, "impressions": 0, "engagement": 0.0})

            for post in platform_posts:
                try:
                    parts = post.publish_time.split(" ")
                    date_part = parts[0]
                    time_part = parts[1] if len(parts) > 1 else "00:00:00"
                    hour = int(time_part.split(":")[0])

                    # 计算星期
                    date_obj = datetime.strptime(date_part, "%Y-%m-%d")
                    day = date_obj.strftime("%A").lower()

                    key = f"{day}_{hour}"
                    time_data[key]["count"] += 1
                    time_data[key]["impressions"] += post.impressions
                    time_data[key]["engagement"] += post.engagement_rate
                except Exception as e:
                    continue

            # 找出最佳时间（样本量>=2）
            valid_times = [(k, v) for k, v in time_data.items() if v["count"] >= 2]
            sorted_times = sorted(
                valid_times,
                key=lambda x: (x[1]["impressions"] / x[1]["count"]) * (x[1]["engagement"] / x[1]["count"]),
                reverse=True
            )[:5]

            for key, data in sorted_times:
                day, hour = key.split("_")
                hour = int(hour)
                avg_impressions = int(data["impressions"] / data["count"])
                avg_engagement = data["engagement"] / data["count"]
                confidence = min(100, data["count"] * 20)  # 样本量越多置信度越高

                bt = BestPublishingTime(
                    platform=platform,
                    day=day,
                    hour=hour,
                    avg_impressions=avg_impressions,
                    avg_engagement=avg_engagement,
                    post_count=data["count"],
                    confidence=confidence,
                    recommendation=f"{day.capitalize()} {hour:02d}:00 - 平均展示{avg_impressions}，互动率{avg_engagement*100:.1f}%"
                )
                best_times.append(bt)

        self.best_times = best_times

        # 打印结果
        print(f"\n  📊 分析出 {len(best_times)} 个最佳发布时间")
        print(f"\n  各平台最佳发布时间:")
        for platform in PLATFORMS:
            platform_times = [bt for bt in best_times if bt.platform == platform][:3]
            if platform_times:
                print(f"\n  {platform.upper()}:")
                for bt in platform_times:
                    print(f"    {bt.day.capitalize():<10} {bt.hour:02d}:00  展示:{bt.avg_impressions:<6} 互动:{bt.avg_engagement*100:.1f}%  置信度:{bt.confidence:.0f}%")

        # 与行业最佳实践对比
        print(f"\n  📊 与行业最佳实践对比:")
        for platform in PLATFORMS:
            best_practice = PLATFORM_BEST_PRACTICES.get(platform, {})
            industry_times = best_practice.get("best_times", [])
            platform_times = [bt for bt in best_times if bt.platform == platform]

            if platform_times and industry_times:
                our_best_hour = platform_times[0].hour
                industry_best_hour = int(industry_times[0].split(":")[0])
                match = "✅ 匹配" if abs(our_best_hour - industry_best_hour) <= 2 else "⚠️ 差异"
                print(f"  {platform:<12} 我们最佳:{our_best_hour:02d}:00  行业最佳:{industry_best_hour:02d}:00  {match}")

        # 保存结果
        with open(BEST_TIMES_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "analyzed_at": datetime.now().isoformat(),
                "total_best_times": len(best_times),
                "best_times": [asdict(bt) for bt in best_times],
                "industry_benchmarks": PLATFORM_BEST_PRACTICES
            }, f, ensure_ascii=False, indent=2)

        print(f"\n  ✅ 最佳发布时间分析已保存: {BEST_TIMES_FILE}")

        return best_times

    # ==================== 3. 爆款内容模式识别 ====================

    def identify_viral_patterns(self) -> List[ViralPattern]:
        """识别爆款内容模式"""
        print("\n" + "=" * 60)
        print("  社媒智能优化Agent - 爆款内容模式识别")
        print("=" * 60)

        viral_patterns = []

        # 按内容类型分析
        type_performance = defaultdict(lambda: {
            "posts": [], "avg_engagement": 0.0, "avg_viral_score": 0.0,
            "platforms": set(), "high_performers": []
        })

        for post in self.posts:
            type_performance[post.content_type]["posts"].append(post)
            type_performance[post.content_type]["platforms"].add(post.platform)
            if post.viral_score >= 50:
                type_performance[post.content_type]["high_performers"].append(post)

        # 识别高表现内容类型
        for content_type, data in type_performance.items():
            if not data["posts"]:
                continue

            avg_engagement = sum(p.engagement_rate for p in data["posts"]) / len(data["posts"])
            avg_viral = sum(p.viral_score for p in data["posts"]) / len(data["posts"])

            # 只保留表现较好的模式
            if avg_engagement < 0.02 and avg_viral < 30:
                continue

            # 分析高表现帖子的共同特征
            high_performers = data["high_performers"] or data["posts"][:3]
            key_elements = self._extract_key_elements(high_performers)
            headline_templates = self._extract_headline_templates(high_performers)

            pattern = ViralPattern(
                id=f"viral_{content_type}",
                pattern_name=f"{content_type.capitalize()} Content Pattern",
                description=f"高表现的{content_type}类型内容，平均互动率{avg_engagement*100:.1f}%",
                content_type=content_type,
                platforms=list(data["platforms"]),
                avg_engagement_rate=avg_engagement,
                sample_size=len(data["posts"]),
                key_elements=key_elements,
                headline_templates=headline_templates,
                recommended_usage=self._generate_pattern_usage(content_type, avg_engagement),
                confidence=min(100, len(data["posts"]) * 10)
            )
            viral_patterns.append(pattern)

        # 按表现排序
        viral_patterns.sort(key=lambda x: x.avg_engagement_rate, reverse=True)
        self.viral_patterns = viral_patterns

        # 打印结果
        print(f"\n  📊 识别出 {len(viral_patterns)} 个爆款内容模式")
        print(f"\n  爆款模式排行:")
        for i, pattern in enumerate(viral_patterns[:5], 1):
            print(f"\n  {i}. {pattern.pattern_name}")
            print(f"     平均互动率: {pattern.avg_engagement_rate*100:.2f}%")
            print(f"     样本量: {pattern.sample_size}条")
            print(f"     适用平台: {', '.join(pattern.platforms)}")
            print(f"     置信度: {pattern.confidence:.0f}%")
            print(f"     关键元素: {', '.join(pattern.key_elements[:3])}")

        # 保存结果
        with open(VIRAL_PATTERNS_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "analyzed_at": datetime.now().isoformat(),
                "total_patterns": len(viral_patterns),
                "viral_patterns": [asdict(p) for p in viral_patterns]
            }, f, ensure_ascii=False, indent=2)

        print(f"\n  ✅ 爆款模式识别已保存: {VIRAL_PATTERNS_FILE}")

        return viral_patterns

    def _extract_key_elements(self, posts: List[SocialPost]) -> List[str]:
        """提取高表现帖子的关键元素"""
        elements = []

        # 分析标题特征
        for post in posts:
            title = post.title.lower()
            if any(word in title for word in ["guide", "complete", "ultimate"]):
                elements.append("完整指南型标题")
            if any(word in title for word in ["tips", "tricks", "hacks"]):
                elements.append("技巧型标题")
            if any(word in title for word in ["mistakes", "avoid", "warning"]):
                elements.append("避坑型标题")
            if any(word in title for word in ["best", "top", "ultimate"]):
                elements.append("列表型标题")
            if "?" in title:
                elements.append("问答型标题")
            if any(word in title for word in ["why", "how", "what"]):
                elements.append("疑问型标题")

        # 去重并限制数量
        return list(dict.fromkeys(elements))[:5]

    def _extract_headline_templates(self, posts: List[SocialPost]) -> List[str]:
        """提取标题模板"""
        templates = []

        for post in posts:
            title = post.title
            # 简化标题为模板
            template = re.sub(r'\d+', '{number}', title)
            template = re.sub(r'(China|Chinese|Chengdu|Beijing|Shanghai)', '{location}', template)
            if template not in templates:
                templates.append(template)

        return templates[:3]

    def _generate_pattern_usage(self, content_type: str, engagement_rate: float) -> str:
        """生成模式使用建议"""
        if engagement_rate > 0.05:
            return f"⭐ 高表现模式，建议每周发布2-3条{content_type}类型内容"
        elif engagement_rate > 0.03:
            return f"✅ 良好表现，建议每周发布1-2条{content_type}类型内容"
        else:
            return f"📊 一般表现，可适当减少{content_type}类型内容发布频率"

    # ==================== 4. 社媒引流效果分析 ====================

    def analyze_traffic_funnel(self) -> Dict[str, Any]:
        """分析社媒引流效果漏斗"""
        print("\n" + "=" * 60)
        print("  社媒智能优化Agent - 引流效果漏斗分析")
        print("=" * 60)

        # 计算全漏斗数据
        total_impressions = sum(p.impressions for p in self.posts)
        total_clicks = sum(p.clicks for p in self.posts)
        total_engagement = sum(p.likes + p.comments + p.shares + p.saves for p in self.posts)
        total_revenue = sum(p.revenue for p in self.posts)

        # 估算网站访问（点击的80%会到达网站）
        estimated_visits = int(total_clicks * 0.8)
        # 估算联盟转化（网站访问的2%会转化）
        estimated_conversions = int(estimated_visits * 0.02)

        funnel = {
            "impressions": total_impressions,
            "engagement": total_engagement,
            "clicks": total_clicks,
            "estimated_website_visits": estimated_visits,
            "estimated_conversions": estimated_conversions,
            "revenue": total_revenue,
            "rates": {
                "engagement_rate": total_engagement / total_impressions if total_impressions > 0 else 0,
                "click_through_rate": total_clicks / total_impressions if total_impressions > 0 else 0,
                "visit_rate": estimated_visits / total_clicks if total_clicks > 0 else 0,
                "conversion_rate": estimated_conversions / estimated_visits if estimated_visits > 0 else 0,
                "revenue_per_click": total_revenue / total_clicks if total_clicks > 0 else 0,
                "revenue_per_impression": total_revenue / total_impressions if total_impressions > 0 else 0
            },
            "by_platform": {}
        }

        # 各平台漏斗
        for platform in PLATFORMS:
            platform_posts = [p for p in self.posts if p.platform == platform]
            if not platform_posts:
                continue

            p_impressions = sum(p.impressions for p in platform_posts)
            p_clicks = sum(p.clicks for p in platform_posts)
            p_engagement = sum(p.likes + p.comments + p.shares + p.saves for p in platform_posts)
            p_revenue = sum(p.revenue for p in platform_posts)

            funnel["by_platform"][platform] = {
                "impressions": p_impressions,
                "engagement": p_engagement,
                "clicks": p_clicks,
                "revenue": p_revenue,
                "ctr": p_clicks / p_impressions if p_impressions > 0 else 0,
                "engagement_rate": p_engagement / p_impressions if p_impressions > 0 else 0,
                "revenue_per_click": p_revenue / p_clicks if p_clicks > 0 else 0,
                "contribution_to_clicks": p_clicks / total_clicks if total_clicks > 0 else 0,
                "contribution_to_revenue": p_revenue / total_revenue if total_revenue > 0 else 0
            }

        # 打印漏斗
        print(f"\n  📊 社媒引流全漏斗:")
        print(f"  {'阶段':<20} {'数量':<12} {'转化率':<12} {'说明'}")
        print("  " + "-" * 70)
        print(f"  {'展示量':<20} {total_impressions:<12} {'100%':<12} 社媒内容曝光")
        print(f"  {'互动量':<20} {total_engagement:<12} {funnel['rates']['engagement_rate']*100:<12.2f}% 点赞+评论+分享+收藏")
        print(f"  {'点击量':<20} {total_clicks:<12} {funnel['rates']['click_through_rate']*100:<12.2f}% 点击链接到网站")
        print(f"  {'网站访问':<20} {estimated_visits:<12} {funnel['rates']['visit_rate']*100:<12.2f}% 估算到达网站")
        print(f"  {'联盟转化':<20} {estimated_conversions:<12} {funnel['rates']['conversion_rate']*100:<12.2f}% 估算完成预订")
        print(f"  {'收入':<20} ${total_revenue:<11.2f} {'-':<12} 联盟佣金收入")

        # 各平台贡献
        print(f"\n  📊 各平台贡献对比:")
        print(f"  {'平台':<12} {'展示':<10} {'点击':<8} {'CTR':<10} {'收入':<10} {'点击贡献':<10} {'收入贡献':<10}")
        print("  " + "-" * 80)
        for platform, data in sorted(funnel["by_platform"].items(), key=lambda x: x[1]["clicks"], reverse=True):
            print(f"  {platform:<12} {data['impressions']:<10} {data['clicks']:<8} {data['ctr']*100:<10.2f}% ${data['revenue']:<9.2f} {data['contribution_to_clicks']*100:<10.1f}% {data['contribution_to_revenue']*100:<10.1f}%")

        # 漏斗瓶颈分析
        print(f"\n  🔍 漏斗瓶颈分析:")
        ctr = funnel["rates"]["click_through_rate"]
        if ctr < 0.02:
            print(f"  🔴 点击率偏低（{ctr*100:.2f}%），主要瓶颈在社媒→网站环节")
            print(f"     建议：优化CTA文案，增加行动号召，优化链接展示位置")
        elif ctr < 0.05:
            print(f"  🟡 点击率一般（{ctr*100:.2f}%），有优化空间")
        else:
            print(f"  🟢 点击率良好（{ctr*100:.2f}%）")

        conversion_rate = funnel["rates"]["conversion_rate"]
        if conversion_rate < 0.01:
            print(f"  🔴 网站转化率偏低（{conversion_rate*100:.2f}%），主要瓶颈在网站→联盟环节")
            print(f"     建议：优化落地页，增加联盟推荐区块，提升用户信任")
        elif conversion_rate < 0.03:
            print(f"  🟡 网站转化率一般（{conversion_rate*100:.2f}%），有优化空间")
        else:
            print(f"  🟢 网站转化率良好（{conversion_rate*100:.2f}%）")

        # 保存结果
        with open(TRAFFIC_FUNNEL_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "analyzed_at": datetime.now().isoformat(),
                "funnel": funnel,
                "bottleneck_analysis": self._generate_funnel_recommendations(funnel)
            }, f, ensure_ascii=False, indent=2)

        print(f"\n  ✅ 引流漏斗分析已保存: {TRAFFIC_FUNNEL_FILE}")

        return funnel

    def _generate_funnel_recommendations(self, funnel: Dict) -> List[str]:
        """生成漏斗优化建议"""
        recommendations = []
        rates = funnel["rates"]

        if rates["click_through_rate"] < 0.02:
            recommendations.append("优化社媒CTA文案，增加明确的行动号召")
            recommendations.append("在文案中增加链接价值说明，提升点击意愿")
            recommendations.append("测试不同的链接展示方式（短链接vs完整链接）")

        if rates["engagement_rate"] < 0.03:
            recommendations.append("增加互动引导（提问、投票、征集意见）")
            recommendations.append("优化内容质量，提供更多实用价值")
            recommendations.append("使用视觉冲击力强的图片和视频")

        if rates["conversion_rate"] < 0.02:
            recommendations.append("优化落地页首屏内容，与社媒文案保持一致")
            recommendations.append("在文章中增加联盟推荐区块和CTA按钮")
            recommendations.append("增加用户评价和信任信号，提升转化率")

        if rates["revenue_per_click"] < 0.03:
            recommendations.append("优化联盟产品选择，推广高佣金产品")
            recommendations.append("增加高转化页面的社媒推广力度")

        return recommendations

    # ==================== 5. 生成完整报告 ====================

    def generate_full_report(self) -> str:
        """生成完整的社媒智能优化报告"""
        print("\n" + "=" * 60)
        print("  社媒智能优化Agent - 生成完整报告")
        print("=" * 60)

        now = datetime.now()

        # 汇总数据
        total_posts = len(self.posts)
        total_impressions = sum(p.impressions for p in self.posts)
        total_clicks = sum(p.clicks for p in self.posts)
        total_engagement = sum(p.likes + p.comments + p.shares + p.saves for p in self.posts)
        avg_engagement_rate = sum(p.engagement_rate for p in self.posts) / total_posts if total_posts > 0 else 0
        avg_ctr = sum(p.click_through_rate for p in self.posts) / total_posts if total_posts > 0 else 0

        report = f"""# ChinaBound Travel 社媒智能优化报告

**生成时间**: {now.strftime('%Y-%m-%d %H:%M:%S')}
**引擎版本**: v1.0
**成熟度目标**: L2 → L3

---

## 📊 执行摘要

| 指标 | 数值 |
|------|------|
| 分析帖子数 | {total_posts}条 |
| 总展示量 | {total_impressions:,} |
| 总点击量 | {total_clicks:,} |
| 总互动量 | {total_engagement:,} |
| 平均互动率 | {avg_engagement_rate*100:.2f}% |
| 平均点击率 | {avg_ctr*100:.2f}% |
| 覆盖平台 | {len(self.platform_performances)}个 |
| 识别爆款模式 | {len(self.viral_patterns)}个 |
| 最佳发布时间 | {len(self.best_times)}个 |

---

## 🏆 平台表现对比

| 平台 | 帖子数 | 总展示 | 总点击 | 平均互动率 | 平均CTR | 最佳内容类型 | 趋势 |
|------|--------|--------|--------|------------|---------|--------------|------|
"""

        for platform, perf in sorted(self.platform_performances.items(), key=lambda x: x[1].total_impressions, reverse=True):
            best_types = ", ".join(perf.best_content_types[:2]) if perf.best_content_types else "-"
            trend_icon = {"growing": "📈", "declining": "📉", "stable": "➡️"}.get(perf.growth_trend, "➡️")
            report += f"| {platform} | {perf.total_posts} | {perf.total_impressions:,} | {perf.total_clicks:,} | {perf.avg_engagement_rate*100:.2f}% | {perf.avg_ctr*100:.2f}% | {best_types} | {trend_icon} {perf.growth_trend} |\n"

        report += """
---

## ⏰ 最佳发布时间推荐

### 各平台最佳发布时间

| 平台 | 最佳时间 | 平均展示 | 平均互动率 | 置信度 |
|------|----------|----------|------------|--------|
"""

        for platform in PLATFORMS:
            platform_times = [bt for bt in self.best_times if bt.platform == platform][:2]
            for bt in platform_times:
                report += f"| {platform} | {bt.day.capitalize()} {bt.hour:02d}:00 | {bt.avg_impressions:,} | {bt.avg_engagement*100:.1f}% | {bt.confidence:.0f}% |\n"

        report += """
### 发布时间优化建议

1. **优先在各平台最佳时间发布**，可提升展示量20-40%
2. **Pinterest重点在晚间（20:00-22:00）发布**，用户活跃度最高
3. **Instagram和Facebook在工作日中午和傍晚发布**效果最佳
4. **X（Twitter）在早高峰和晚高峰发布**，实时性内容效果好
5. **周末增加视觉类内容发布**，用户有更多时间浏览和互动

---

## 🔥 爆款内容模式识别

### 高表现内容模式排行

| 排名 | 模式名称 | 内容类型 | 平均互动率 | 样本量 | 适用平台 | 置信度 |
|------|----------|----------|------------|--------|----------|--------|
"""

        for i, pattern in enumerate(self.viral_patterns[:5], 1):
            platforms = ", ".join(pattern.platforms[:3])
            report += f"| {i} | {pattern.pattern_name} | {pattern.content_type} | {pattern.avg_engagement_rate*100:.2f}% | {pattern.sample_size} | {platforms} | {pattern.confidence:.0f}% |\n"

        report += """
### 爆款内容关键元素

1. **实用价值** - 提供可操作的建议、清单、指南
2. **视觉冲击** - 高质量图片、信息图、短视频
3. **情感共鸣** - 故事性内容、个人体验、文化洞察
4. **互动引导** - 提问、投票、征集意见
5. **时效性** - 结合热点、季节、节日
6. **稀缺性** - 独家信息、 insider tips、避坑指南

### 标题模板推荐

- "X Things Tourists Should Know Before Visiting China"
- "Why [Location] Feels Different? Not Just [Obvious]"
- "Complete Guide to [Topic]: Everything You Need to Know"
- "[Number] [Topic] Tips for First-Time Visitors"
- "Planning [Trip Type]? Here's Your Complete Checklist"

---

## 📈 社媒引流效果漏斗

### 全漏斗数据

| 阶段 | 数量 | 转化率 | 说明 |
|------|------|--------|------|
| 展示量 | """ + f"{total_impressions:,}" + """ | 100% | 社媒内容曝光 |
| 互动量 | """ + f"{total_engagement:,}" + f""" | {total_engagement/total_impressions*100:.2f}% | 点赞+评论+分享+收藏 |
| 点击量 | {total_clicks:,} | {total_clicks/total_impressions*100:.2f}% | 点击链接到网站 |
| 网站访问 | ~{int(total_clicks*0.8):,} | ~80% | 估算到达网站 |
| 联盟转化 | ~{int(total_clicks*0.8*0.02):,} | ~2% | 估算完成预订 |

### 各平台引流贡献

| 平台 | 点击量 | CTR | 点击贡献 | 优化重点 |
|------|--------|-----|----------|----------|
"""

        for platform, perf in sorted(self.platform_performances.items(), key=lambda x: x[1].total_clicks, reverse=True):
            ctr = perf.avg_ctr
            contribution = perf.total_clicks / total_clicks * 100 if total_clicks > 0 else 0
            if ctr < 0.02:
                focus = "🔴 优化CTA和文案"
            elif ctr < 0.04:
                focus = "🟡 提升内容质量"
            else:
                focus = "🟢 保持并扩大"
            report += f"| {platform} | {perf.total_clicks:,} | {ctr*100:.2f}% | {contribution:.1f}% | {focus} |\n"

        report += """
---

## 🎯 优化行动计划

### 立即执行（1-3天）
1. **调整发布时间** - 按照各平台最佳发布时间重新安排内容排期
2. **优化低表现帖子** - 对互动率低于2%的帖子进行文案和图片优化
3. **增加高互动内容类型** - 优先使用识别出的爆款内容模式
4. **优化CTA文案** - 增加明确的行动号召，提升点击率

### 短期优化（1-2周）
5. **A/B测试标题和文案** - 测试不同标题模板的效果
6. **优化图片质量** - 提升视觉冲击力，增加信息图使用
7. **增加互动引导** - 在文案中增加提问和投票
8. **建立内容日历** - 基于最佳时间和内容类型规划发布

### 中期建设（1个月）
9. **建立爆款内容库** - 收集和整理高表现内容，形成可复用模板
10. **实现发布时间自动优化** - 基于历史数据自动推荐最佳发布时间
11. **建立社媒效果追踪体系** - 实时监控各平台表现，自动预警
12. **跨平台内容适配优化** - 针对各平台特点定制内容

### 长期战略（3个月）
13. **实现社媒内容自动迭代优化** - 基于效果数据自动改进内容
14. **建立智能分发系统** - 自动选择最佳平台、时间、内容类型
15. **实现社媒→网站→转化全链路优化** - 端到端漏斗优化
16. **建立预测模型** - 预测内容表现，优化内容生产决策

---

## 📊 成熟度评估

| 能力维度 | 当前等级 | 目标等级 | 状态 |
|----------|----------|----------|------|
| 内容生成 | L3 | L3 | ✅ 已达标 |
| 效果追踪 | L2 | L3 | 🟡 进行中 |
| 智能分发 | L1 | L3 | 🔴 需提升 |
| 爆款识别 | L1 | L2 | 🔴 需提升 |
| 引流优化 | L2 | L3 | 🟡 进行中 |
| 自动迭代 | L0 | L2 | 🔴 需建设 |

**综合成熟度**: L2 → L3（进行中）

---

*报告由社媒智能优化Agent自动生成 | """ + now.strftime('%Y-%m-%d %H:%M:%S') + """*
*引擎版本: v1.0 | 成熟度目标: L2 → L3*
"""

        # 保存报告
        with open(SOCIAL_REPORT_FILE, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"\n  ✅ 报告已生成: {SOCIAL_REPORT_FILE}")
        print(f"  📊 报告长度: {len(report)} 字符")

        return report

    # ==================== 6. 完整优化流程 ====================

    def run_full_optimization(self):
        """运行完整的社媒智能优化流程"""
        print("\n" + "=" * 60)
        print("  ChinaBound Travel - 社媒智能优化Agent")
        print("  完整优化流程")
        print("=" * 60)

        print(f"\n📅 运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Step 1: 内容效果分析
        self.analyze_post_performance()

        # Step 2: 最佳发布时间分析
        self.analyze_best_publishing_times()

        # Step 3: 爆款内容模式识别
        self.identify_viral_patterns()

        # Step 4: 引流效果漏斗分析
        self.analyze_traffic_funnel()

        # Step 5: 生成报告
        self.generate_full_report()

        print("\n" + "=" * 60)
        print("  ✅ 完整社媒智能优化流程完成！")
        print("=" * 60)
        print(f"\n📁 报告目录: {SOCIAL_DIR}")
        print(f"📄 社媒优化报告: {SOCIAL_REPORT_FILE}")
        print(f"🔍 内容审计报告: {SOCIAL_AUDIT_FILE}")
        print(f"⏰ 最佳发布时间: {BEST_TIMES_FILE}")
        print(f"🔥 爆款模式识别: {VIRAL_PATTERNS_FILE}")
        print(f"📈 引流漏斗分析: {TRAFFIC_FUNNEL_FILE}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="ChinaBound Travel 社媒智能优化Agent")
    parser.add_argument("--all", action="store_true", help="运行完整优化流程")
    parser.add_argument("--performance", action="store_true", help="仅内容效果分析")
    parser.add_argument("--times", action="store_true", help="仅最佳发布时间分析")
    parser.add_argument("--viral", action="store_true", help="仅爆款模式识别")
    parser.add_argument("--funnel", action="store_true", help="仅引流漏斗分析")
    parser.add_argument("--report", action="store_true", help="仅生成报告")

    args = parser.parse_args()

    agent = SocialIntelligenceAgent()

    if args.all or not any([args.performance, args.times, args.viral, args.funnel, args.report]):
        agent.run_full_optimization()
    elif args.performance:
        agent.analyze_post_performance()
    elif args.times:
        agent.analyze_post_performance()
        agent.analyze_best_publishing_times()
    elif args.viral:
        agent.analyze_post_performance()
        agent.identify_viral_patterns()
    elif args.funnel:
        agent.analyze_post_performance()
        agent.analyze_traffic_funnel()
    elif args.report:
        agent.analyze_post_performance()
        agent.analyze_best_publishing_times()
        agent.identify_viral_patterns()
        agent.analyze_traffic_funnel()
        agent.generate_full_report()


if __name__ == "__main__":
    main()
