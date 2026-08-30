#!/usr/bin/env python3
"""
ChinaBound Travel - 内容智能优化Agent
Content Intelligence Agent

核心能力（L3 → L4）：
1. 内容质量智能审计 - 多维度质量评分、问题检测
2. 旧内容自动更新建议 - 基于数据的内容刷新优先级
3. 多模态内容生成规划 - 图片、信息图、视频脚本推荐
4. 内容效果追踪与迭代 - 展示/点击/转化全链路分析
5. 智能内容规划与选题 - 基于搜索需求和内容缺口的选题推荐
6. 内链与内容结构优化 - 主题集群、支柱页面、内链建议

成熟度目标：L3 → L4（6个月）
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


def split_frontmatter(text: str):
    """分割Front Matter，支持YAML(---)和TOML(+++)"""
    for delim in ("---", "+++"):
        ed = re.escape(delim)
        m = re.match(r"^%s\s*\n(.*?)\n%s\s*\n" % (ed, ed), text, re.DOTALL)
        if m:
            return m.group(1), text[m.end():], delim
    return None, text, ""


def read_fm_value(fm: str, key: str) -> str:
    """从Front Matter中读取值"""
    if not fm:
        return ""
    m = re.search(rf'^{key}\s*[=:]\s*["\']?([^"\'\n#]+)', fm, re.MULTILINE)
    return m.group(1).strip().strip('"').strip("'") if m else ""


# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
CONTENT_DIR = REPORTS_DIR / "content"
CONTENT_DIR.mkdir(parents=True, exist_ok=True)

# 数据文件
CONTENT_AUDIT_FILE = CONTENT_DIR / "content_audit_report.json"
CONTENT_OPTIMIZATION_FILE = CONTENT_DIR / "content_optimization_plan.json"
MULTIMODAL_PLAN_FILE = CONTENT_DIR / "multimodal_content_plan.json"
TOPIC_RECOMMENDATIONS_FILE = CONTENT_DIR / "topic_recommendations.json"
CONTENT_REPORT_FILE = CONTENT_DIR / "content_intelligence_report.md"

# 内容目录
POSTS_DIR = PROJECT_ROOT / "content" / "posts"


class ContentQualityDimension(Enum):
    """内容质量维度"""
    DEPTH = "depth"                    # 内容深度
    STRUCTURE = "structure"            # 结构完整性
    SEO = "seo"                        # SEO优化
    READABILITY = "readability"        # 可读性
    MULTIMEDIA = "multimedia"          # 多媒体丰富度
    ENGAGEMENT = "engagement"          # 互动性
    ACCURACY = "accuracy"              # 事实准确性
    FRESHNESS = "freshness"            # 内容新鲜度


class ContentStatus(Enum):
    """内容状态"""
    EXCELLENT = "excellent"            # 优秀，无需优化
    GOOD = "good"                      # 良好，小幅优化
    AVERAGE = "average"                # 一般，需要优化
    POOR = "poor"                      # 较差，需要深度优化
    OUTDATED = "outdated"              # 过时，需要更新


@dataclass
class ContentRecord:
    """内容记录"""
    id: str
    title: str
    slug: str
    url: str
    file_path: str
    publish_date: str
    last_updated: str
    word_count: int
    reading_time: int

    # 质量评分（各维度0-100）
    quality_scores: Dict[str, float] = field(default_factory=dict)
    overall_score: float = 0.0
    quality_status: str = "average"

    # SEO指标
    impressions_28d: int = 0
    clicks_28d: int = 0
    ctr_28d: float = 0.0
    position_28d: float = 0.0
    indexed_status: str = "unknown"

    # 内容结构
    has_faq: bool = False
    has_toc: bool = False
    has_internal_links: bool = False
    internal_link_count: int = 0
    has_affiliate_links: bool = False
    affiliate_link_count: int = 0
    has_images: bool = False
    image_count: int = 0
    has_video: bool = False

    # 问题与建议
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    optimization_priority: str = "low"  # high/medium/low
    estimated_impact: str = ""

    # 多模态建议
    multimodal_recommendations: List[str] = field(default_factory=list)


@dataclass
class TopicRecommendation:
    """选题推荐"""
    id: str
    topic: str
    keyword: str
    search_intent: str  # informational/commercial/transactional
    search_volume: str  # high/medium/low/unknown
    competition: str    # high/medium/low/unknown
    content_gap: bool
    related_existing_content: List[str]
    priority: str
    estimated_traffic_potential: str
    content_type: str  # guide/how-to/list/comparison/case_study
    rationale: str


@dataclass
class MultimodalRecommendation:
    """多模态内容推荐"""
    id: str
    content_id: str
    content_title: str
    media_type: str  # image/infographic/video_slides/video_script/audio
    description: str
    purpose: str  # engagement/seo/understanding/conversion
    priority: str
    estimated_impact: str
    creation_complexity: str  # low/medium/high


class ContentIntelligenceAgent:
    """内容智能优化Agent主类"""

    def __init__(self):
        self.content_inventory: List[ContentRecord] = []
        self.topic_recommendations: List[TopicRecommendation] = []
        self.multimodal_recommendations: List[MultimodalRecommendation] = []
        self._load_gsc_data()

    def _load_gsc_data(self) -> Dict[str, Any]:
        """加载GSC数据"""
        gsc_data = {}
        gsc_file = PROJECT_ROOT / "reports" / "seo" / "CONTENT_SEO_INVENTORY.csv"

        if gsc_file.exists():
            try:
                with open(gsc_file, encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        url = row.get("url", "")
                        if url:
                            gsc_data[url] = {
                                "impressions_28d": int(row.get("impressions_28d", 0) or 0),
                                "clicks_28d": int(row.get("clicks_28d", 0) or 0),
                                "ctr_28d": float(row.get("ctr_28d", 0) or 0),
                                "position_28d": float(row.get("position_28d", 0) or 0),
                                "indexed_status": row.get("indexed_status", "unknown"),
                                "title": row.get("title", ""),
                                "content_id": row.get("content_id", "")
                            }
            except Exception as e:
                print(f"  ⚠️ 加载GSC数据失败: {e}")

        return gsc_data

    # ==================== 1. 内容质量智能审计 ====================

    def audit_content_quality(self) -> List[ContentRecord]:
        """审计所有内容的质量"""
        print("\n" + "=" * 60)
        print("  内容智能优化Agent - 内容质量审计")
        print("=" * 60)

        gsc_data = self._load_gsc_data()
        content_records = []

        if not POSTS_DIR.exists():
            print("  ❌ content/posts 目录不存在")
            return []

        md_files = list(POSTS_DIR.glob("*.md"))
        print(f"\n  📝 扫描文章: {len(md_files)}篇")

        for md_file in md_files:
            try:
                record = self._audit_single_content(md_file, gsc_data)
                content_records.append(record)
            except Exception as e:
                print(f"  ⚠️ 审计 {md_file.name} 失败: {e}")

        self.content_inventory = content_records

        # 统计
        total = len(content_records)
        avg_score = sum(r.overall_score for r in content_records) / total if total > 0 else 0
        status_dist = defaultdict(int)
        for r in content_records:
            status_dist[r.quality_status] += 1

        print(f"\n  📊 内容质量统计:")
        print(f"    文章总数: {total}")
        print(f"    平均质量分: {avg_score:.1f}/100")
        print(f"    平均字数: {sum(r.word_count for r in content_records) // total if total > 0 else 0}")

        print(f"\n  📊 质量分布:")
        for status, count in sorted(status_dist.items(), key=lambda x: x[1], reverse=True):
            print(f"    {status}: {count}篇 ({count/total*100:.1f}%)")

        # 各维度平均分
        print(f"\n  📊 各维度平均分:")
        all_scores = defaultdict(list)
        for r in content_records:
            for dim, score in r.quality_scores.items():
                all_scores[dim].append(score)
        for dim, scores in sorted(all_scores.items()):
            avg = sum(scores) / len(scores) if scores else 0
            print(f"    {dim}: {avg:.1f}/100")

        # 高优先级优化
        high_priority = [r for r in content_records if r.optimization_priority == "high"]
        print(f"\n  🔴 高优先级优化: {len(high_priority)}篇")

        # 保存审计报告
        audit_report = {
            "audited_at": datetime.now().isoformat(),
            "total_content": total,
            "average_score": avg_score,
            "average_word_count": sum(r.word_count for r in content_records) // total if total > 0 else 0,
            "status_distribution": dict(status_dist),
            "dimension_averages": {dim: sum(scores)/len(scores) for dim, scores in all_scores.items()},
            "high_priority_count": len(high_priority),
            "content_records": [asdict(r) for r in content_records]
        }

        with open(CONTENT_AUDIT_FILE, "w", encoding="utf-8") as f:
            json.dump(audit_report, f, ensure_ascii=False, indent=2)

        print(f"\n  ✅ 审计报告已保存: {CONTENT_AUDIT_FILE}")

        return content_records

    def _audit_single_content(self, md_file: Path, gsc_data: Dict) -> ContentRecord:
        """审计单篇内容"""
        # 读取文件并解析Front Matter
        raw = md_file.read_bytes()
        text = raw.decode("utf-8", errors="replace")
        fm, body, delim = split_frontmatter(text)

        # 从Front Matter读取字段
        title = read_fm_value(fm, "title") or md_file.stem
        slug = read_fm_value(fm, "slug") or md_file.stem
        publish_date = read_fm_value(fm, "date")[:10]
        last_updated = read_fm_value(fm, "last_updated")[:10] or publish_date

        # 使用body计算字数（不含Front Matter）
        word_count = len(body.split())
        reading_time = max(1, word_count // 200)  # 假设200词/分钟

        # URL
        url = f"https://www.chinaboundtravel.com/posts/{slug}/"

        # 创建记录
        record = ContentRecord(
            id=f"content_{slug[:20]}",
            title=title,
            slug=slug,
            url=url,
            file_path=str(md_file),
            publish_date=publish_date,
            last_updated=last_updated,
            word_count=word_count,
            reading_time=reading_time
        )

        # 加载GSC数据
        if url in gsc_data:
            gsc = gsc_data[url]
            record.impressions_28d = gsc["impressions_28d"]
            record.clicks_28d = gsc["clicks_28d"]
            record.ctr_28d = gsc["ctr_28d"]
            record.position_28d = gsc["position_28d"]
            record.indexed_status = gsc["indexed_status"]

        # 内容结构分析
        record.has_faq = "faq" in body.lower() or "q&a" in body.lower() or "frequently asked" in body.lower()
        record.has_toc = "table of contents" in body.lower() or "{{< toc" in body or "ShowToc" in body
        record.internal_link_count = len(re.findall(r'\]\(/posts/', body))
        record.has_internal_links = record.internal_link_count > 0
        record.affiliate_link_count = len(re.findall(r'(booking\.com|agoda\.com|klook\.com|trip\.com|travelpayouts)', body, re.IGNORECASE))
        record.has_affiliate_links = record.affiliate_link_count > 0
        record.image_count = len(re.findall(r'!\[.*?\]\(.*?\)', body)) + len(re.findall(r'<img', body, re.IGNORECASE))
        record.has_images = record.image_count > 0
        record.has_video = "youtube" in body.lower() or "vimeo" in body.lower() or "{{< video" in body

        # 多维度质量评分
        scores = {}

        # 1. 内容深度（基于字数）
        if word_count >= 2500:
            scores["depth"] = 90
        elif word_count >= 2000:
            scores["depth"] = 80
        elif word_count >= 1500:
            scores["depth"] = 70
        elif word_count >= 1000:
            scores["depth"] = 60
        else:
            scores["depth"] = 40

        # 2. 结构完整性
        structure_score = 50
        if record.has_faq:
            structure_score += 15
        if record.has_toc:
            structure_score += 10
        if record.has_internal_links:
            structure_score += 15
        if record.has_affiliate_links:
            structure_score += 10
        scores["structure"] = min(100, structure_score)

        # 3. SEO优化（基于GSC数据）
        if record.indexed_status == "INDEXED":
            seo_score = 60
            if record.position_28d > 0 and record.position_28d <= 10:
                seo_score += 25
            elif record.position_28d > 0 and record.position_28d <= 20:
                seo_score += 15
            elif record.position_28d > 0:
                seo_score += 5
            if record.ctr_28d > 2:
                seo_score += 15
            elif record.ctr_28d > 1:
                seo_score += 10
        else:
            seo_score = 30
        scores["seo"] = min(100, seo_score)

        # 4. 可读性（基于段落长度、标题结构）
        heading_count = len(re.findall(r'^#{1,3}\s', body, re.MULTILINE))
        if heading_count >= 8:
            readability_score = 85
        elif heading_count >= 5:
            readability_score = 75
        elif heading_count >= 3:
            readability_score = 65
        else:
            readability_score = 50
        scores["readability"] = readability_score

        # 5. 多媒体丰富度
        if record.has_video and record.image_count >= 3:
            multimedia_score = 90
        elif record.image_count >= 3:
            multimedia_score = 75
        elif record.image_count >= 1:
            multimedia_score = 60
        else:
            multimedia_score = 30
        scores["multimedia"] = multimedia_score

        # 6. 互动性（FAQ、CTA、相关文章推荐）
        engagement_score = 40
        if record.has_faq:
            engagement_score += 20
        if record.has_affiliate_links:
            engagement_score += 20
        if "related" in body.lower() or "you might also" in body.lower():
            engagement_score += 20
        scores["engagement"] = min(100, engagement_score)

        # 7. 内容新鲜度
        if last_updated:
            try:
                update_date = datetime.strptime(last_updated, "%Y-%m-%d")
                days_since_update = (datetime.now() - update_date).days
                if days_since_update <= 30:
                    freshness_score = 90
                elif days_since_update <= 90:
                    freshness_score = 75
                elif days_since_update <= 180:
                    freshness_score = 60
                else:
                    freshness_score = 40
            except Exception:
                freshness_score = 60
        else:
            freshness_score = 50
        scores["freshness"] = freshness_score

        record.quality_scores = scores
        record.overall_score = sum(scores.values()) / len(scores) if scores else 0

        # 质量状态
        if record.overall_score >= 80:
            record.quality_status = ContentStatus.EXCELLENT.value
        elif record.overall_score >= 65:
            record.quality_status = ContentStatus.GOOD.value
        elif record.overall_score >= 50:
            record.quality_status = ContentStatus.AVERAGE.value
        else:
            record.quality_status = ContentStatus.POOR.value

        # 问题检测与建议
        self._detect_issues_and_recommendations(record)

        # 优化优先级
        self._calculate_optimization_priority(record)

        # 多模态建议
        self._generate_multimodal_recommendations(record)

        return record

    def _detect_issues_and_recommendations(self, record: ContentRecord):
        """检测问题并生成建议"""
        issues = []
        recommendations = []

        # 内容深度问题
        if record.word_count < 1000:
            issues.append("内容过短（<1000词），深度不足")
            recommendations.append("扩充内容至1500+词，增加详细步骤、案例和FAQ")
        elif record.word_count < 1500:
            issues.append("内容深度一般（<1500词）")
            recommendations.append("扩充内容至2000+词，增加更多实用细节")

        # 结构问题
        if not record.has_faq:
            issues.append("缺少FAQ区块")
            recommendations.append("添加3-5个常见问题及答案，提升SEO和用户体验")
        if not record.has_toc and record.word_count > 1500:
            issues.append("长文章缺少目录导航")
            recommendations.append("添加目录（TOC），方便用户快速导航")
        if record.internal_link_count < 3:
            issues.append(f"内链不足（仅{record.internal_link_count}条）")
            recommendations.append("增加3-5条相关文章内链，提升用户停留和SEO")

        # SEO问题
        if record.indexed_status != "INDEXED":
            issues.append("页面未被Google索引")
            recommendations.append("提交GSC索引请求，检查是否有索引错误")
        if record.position_28d > 0 and record.position_28d > 20:
            issues.append(f"搜索排名靠后（第{record.position_28d:.0f}位）")
            recommendations.append("优化Title和Meta描述，增加内容深度和内链")
        if record.impressions_28d > 50 and record.ctr_28d < 1:
            issues.append(f"高展示低CTR（{record.impressions_28d}次展示，CTR {record.ctr_28d:.1f}%）")
            recommendations.append("优化Title和Meta描述，提升点击率")

        # 多媒体问题
        if record.image_count == 0:
            issues.append("文章无图片")
            recommendations.append("添加2-3张高质量相关图片，提升视觉体验和SEO")
        elif record.image_count < 2:
            issues.append("图片数量不足")
            recommendations.append("增加1-2张信息图或步骤示意图")

        # 转化问题
        if not record.has_affiliate_links:
            issues.append("缺少联盟链接和CTA")
            recommendations.append("添加相关的联盟推荐区块和CTA按钮")

        # 新鲜度问题
        if record.quality_scores.get("freshness", 0) < 60:
            issues.append("内容可能过时")
            recommendations.append("更新内容，确保信息准确，添加最新数据和案例")

        record.issues = issues
        record.recommendations = recommendations

    def _calculate_optimization_priority(self, record: ContentRecord):
        """计算优化优先级"""
        priority_score = 0

        # 高展示低CTR（高优先级）
        if record.impressions_28d > 50 and record.ctr_28d < 1:
            priority_score += 40

        # 排名4-20（高优先级，有机会进入首页）
        if 4 <= record.position_28d <= 20:
            priority_score += 30

        # 未索引（高优先级）
        if record.indexed_status != "INDEXED":
            priority_score += 20

        # 内容质量差（中优先级）
        if record.overall_score < 50:
            priority_score += 25
        elif record.overall_score < 65:
            priority_score += 15

        # 缺少联盟链接（中优先级，影响收入）
        if not record.has_affiliate_links:
            priority_score += 15

        # 内容过时（中优先级）
        if record.quality_scores.get("freshness", 100) < 50:
            priority_score += 10

        # 确定优先级
        if priority_score >= 50:
            record.optimization_priority = "high"
            record.estimated_impact = "高 - 预计可显著提升流量和转化"
        elif priority_score >= 25:
            record.optimization_priority = "medium"
            record.estimated_impact = "中 - 预计可提升流量和用户体验"
        else:
            record.optimization_priority = "low"
            record.estimated_impact = "低 - 小幅优化，影响有限"

    def _generate_multimodal_recommendations(self, record: ContentRecord):
        """生成多模态内容建议"""
        recommendations = []

        # 无图片的文章优先推荐图片
        if record.image_count == 0:
            recommendations.append("添加2-3张高质量相关图片（封面图、步骤示意图、信息图）")

        # 攻略类文章推荐信息图
        if "guide" in record.slug.lower() or "how-to" in record.slug.lower() or "tips" in record.slug.lower():
            if record.word_count > 1500:
                recommendations.append("创建信息图（Infographic）总结核心要点，便于分享和Pinterest引流")

        # 行程类文章推荐视频脚本
        if "itinerary" in record.slug.lower() or "route" in record.slug.lower() or "days" in record.slug.lower():
            recommendations.append("创建短视频脚本（60秒），展示行程亮点，用于YouTube Shorts/TikTok")

        # 列表类文章推荐轮播图
        if "best" in record.slug.lower() or "top" in record.slug.lower() or "things" in record.slug.lower():
            recommendations.append("创建Instagram轮播图（Carousel），每项一张图，提升互动")

        # 交通/支付类文章推荐步骤图
        if "transport" in record.slug.lower() or "payment" in record.slug.lower() or "visa" in record.slug.lower():
            recommendations.append("创建步骤示意图（Step-by-step diagram），降低理解门槛")

        record.multimodal_recommendations = recommendations

    # ==================== 2. 智能内容规划与选题推荐 ====================

    def generate_topic_recommendations(self) -> List[TopicRecommendation]:
        """基于搜索需求和内容缺口生成选题推荐"""
        print("\n" + "=" * 60)
        print("  内容智能优化Agent - 选题推荐")
        print("=" * 60)

        recommendations = []

        # 分析现有内容主题
        existing_topics = defaultdict(int)
        for record in self.content_inventory:
            # 简单的主题分类
            title_lower = record.title.lower()
            slug_lower = record.slug.lower()
            for keyword in ["visa", "transport", "food", "hotel", "safety", "photography",
                           "culture", "payment", "internet", "city", "itinerary", "guide",
                           "tea", "history", "etiquette", "packing", "language"]:
                if keyword in title_lower or keyword in slug_lower:
                    existing_topics[keyword] += 1

        print(f"\n  📊 现有内容主题分布:")
        for topic, count in sorted(existing_topics.items(), key=lambda x: x[1], reverse=True):
            print(f"    {topic}: {count}篇")

        # 基于内容缺口和搜索需求生成推荐
        topic_ideas = [
            {
                "topic": "China eSIM and VPN Guide 2026",
                "keyword": "china esim for tourists",
                "search_intent": "commercial",
                "search_volume": "high",
                "competition": "medium",
                "content_gap": existing_topics.get("internet", 0) < 3,
                "content_type": "how-to guide",
                "rationale": "eSIM和VPN是游客刚需，商业意图强，现有内容不足"
            },
            {
                "topic": "Best China Travel Insurance for Foreigners",
                "keyword": "china travel insurance",
                "search_intent": "commercial",
                "search_volume": "high",
                "competition": "medium",
                "content_gap": True,
                "content_type": "comparison guide",
                "rationale": "旅行保险是高转化产品，现有内容缺失"
            },
            {
                "topic": "China High-Speed Rail Complete Guide 2026",
                "keyword": "china high speed rail guide",
                "search_intent": "informational",
                "search_volume": "high",
                "competition": "high",
                "content_gap": existing_topics.get("transport", 0) < 5,
                "content_type": "comprehensive guide",
                "rationale": "高铁是中国旅行核心话题，搜索量大，需要更全面的内容"
            },
            {
                "topic": "China Street Food Guide: What to Eat and Avoid",
                "keyword": "china street food guide",
                "search_intent": "informational",
                "search_volume": "high",
                "competition": "medium",
                "content_gap": existing_topics.get("food", 0) < 5,
                "content_type": "list guide",
                "rationale": "街头美食是热门话题，视觉性强，适合多模态内容"
            },
            {
                "topic": "China Cashless Payment: Alipay vs WeChat Pay",
                "keyword": "alipay vs wechat pay for foreigners",
                "search_intent": "commercial",
                "search_volume": "medium",
                "competition": "medium",
                "content_gap": existing_topics.get("payment", 0) < 3,
                "content_type": "comparison guide",
                "rationale": "支付是游客痛点，对比类内容转化率高"
            },
            {
                "topic": "China Photography Locations: Ultimate Guide",
                "keyword": "best photography spots china",
                "search_intent": "informational",
                "search_volume": "medium",
                "competition": "low",
                "content_gap": existing_topics.get("photography", 0) < 2,
                "content_type": "list guide",
                "rationale": "摄影主题竞争低，适合Pinterest和Instagram引流"
            },
            {
                "topic": "China Tea Culture: Complete Guide for Tea Lovers",
                "keyword": "china tea culture guide",
                "search_intent": "informational",
                "search_volume": "medium",
                "competition": "low",
                "content_gap": existing_topics.get("tea", 0) < 2,
                "content_type": "comprehensive guide",
                "rationale": "茶文化是中国特色，竞争低，适合建立主题权威"
            },
            {
                "topic": "China Packing List: What to Bring in 2026",
                "keyword": "china packing list",
                "search_intent": "commercial",
                "search_volume": "high",
                "competition": "medium",
                "content_gap": existing_topics.get("packing", 0) < 2,
                "content_type": "checklist guide",
                "rationale": "打包清单是高搜索量、高转化内容，适合联盟推广"
            },
            {
                "topic": "China Business Travel Guide: Meetings and Etiquette",
                "keyword": "china business travel guide",
                "search_intent": "commercial",
                "search_volume": "medium",
                "competition": "low",
                "content_gap": True,
                "content_type": "how-to guide",
                "rationale": "商务旅行是细分市场，竞争低，商业价值高"
            },
            {
                "topic": "China Language Survival Phrases for Travelers",
                "keyword": "basic chinese phrases for travel",
                "search_intent": "informational",
                "search_volume": "high",
                "competition": "medium",
                "content_gap": existing_topics.get("language", 0) < 2,
                "content_type": "reference guide",
                "rationale": "常用语是高搜索量内容，适合创建可下载的PDF诱饵"
            }
        ]

        for i, idea in enumerate(topic_ideas):
            # 优先级计算
            priority_score = 0
            if idea["search_volume"] == "high":
                priority_score += 30
            elif idea["search_volume"] == "medium":
                priority_score += 20

            if idea["competition"] == "low":
                priority_score += 30
            elif idea["competition"] == "medium":
                priority_score += 15

            if idea["content_gap"]:
                priority_score += 25

            if idea["search_intent"] == "commercial":
                priority_score += 15

            if priority_score >= 60:
                priority = "high"
            elif priority_score >= 40:
                priority = "medium"
            else:
                priority = "low"

            # 流量潜力
            if idea["search_volume"] == "high" and idea["competition"] == "low":
                traffic_potential = "高 - 预计每月可带来500+访问"
            elif idea["search_volume"] == "high" or idea["competition"] == "low":
                traffic_potential = "中 - 预计每月可带来100-500访问"
            else:
                traffic_potential = "低 - 预计每月可带来<100访问"

            rec = TopicRecommendation(
                id=f"topic_{i+1:03d}",
                topic=idea["topic"],
                keyword=idea["keyword"],
                search_intent=idea["search_intent"],
                search_volume=idea["search_volume"],
                competition=idea["competition"],
                content_gap=idea["content_gap"],
                related_existing_content=[],
                priority=priority,
                estimated_traffic_potential=traffic_potential,
                content_type=idea["content_type"],
                rationale=idea["rationale"]
            )
            recommendations.append(rec)

        self.topic_recommendations = recommendations

        # 按优先级排序
        recommendations.sort(key=lambda x: {"high": 0, "medium": 1, "low": 2}[x.priority])

        print(f"\n  📊 生成 {len(recommendations)} 条选题推荐:")
        for i, rec in enumerate(recommendations[:5], 1):
            priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(rec.priority, "⚪")
            print(f"\n  {i}. {priority_icon} [{rec.priority.upper()}] {rec.topic}")
            print(f"     关键词: {rec.keyword}")
            print(f"     搜索意图: {rec.search_intent} | 搜索量: {rec.search_volume} | 竞争: {rec.competition}")
            print(f"     内容类型: {rec.content_type}")
            print(f"     流量潜力: {rec.estimated_traffic_potential}")
            print(f"     理由: {rec.rationale}")

        # 保存推荐
        with open(TOPIC_RECOMMENDATIONS_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "generated_at": datetime.now().isoformat(),
                "total_recommendations": len(recommendations),
                "recommendations": [asdict(r) for r in recommendations]
            }, f, ensure_ascii=False, indent=2)

        print(f"\n  ✅ 选题推荐已保存: {TOPIC_RECOMMENDATIONS_FILE}")

        return recommendations

    # ==================== 3. 多模态内容生成规划 ====================

    def generate_multimodal_plan(self) -> List[MultimodalRecommendation]:
        """生成多模态内容生成计划"""
        print("\n" + "=" * 60)
        print("  内容智能优化Agent - 多模态内容规划")
        print("=" * 60)

        multimodal_recs = []

        # 优先为高流量、高质量文章生成多模态建议
        priority_content = sorted(
            self.content_inventory,
            key=lambda x: (x.impressions_28d, x.overall_score),
            reverse=True
        )[:20]  # Top 20文章

        for record in priority_content:
            for i, rec_text in enumerate(record.multimodal_recommendations):
                # 判断媒体类型
                if "信息图" in rec_text or "infographic" in rec_text.lower():
                    media_type = "infographic"
                    purpose = "seo + engagement"
                    complexity = "medium"
                elif "视频" in rec_text or "video" in rec_text.lower():
                    media_type = "video_script"
                    purpose = "engagement + traffic"
                    complexity = "high"
                elif "轮播" in rec_text or "carousel" in rec_text.lower():
                    media_type = "image_carousel"
                    purpose = "social engagement"
                    complexity = "medium"
                elif "步骤示意图" in rec_text or "step" in rec_text.lower():
                    media_type = "step_diagram"
                    purpose = "understanding"
                    complexity = "low"
                else:
                    media_type = "image"
                    purpose = "visual appeal"
                    complexity = "low"

                # 优先级
                if record.impressions_28d > 50:
                    priority = "high"
                    impact = "高 - 高流量页面，多模态内容可显著提升停留和转化"
                elif record.overall_score >= 70:
                    priority = "medium"
                    impact = "中 - 高质量内容，多模态可提升用户体验"
                else:
                    priority = "low"
                    impact = "低 - 一般内容，多模态提升有限"

                multimodal_rec = MultimodalRecommendation(
                    id=f"mm_{record.id}_{i}",
                    content_id=record.id,
                    content_title=record.title[:50],
                    media_type=media_type,
                    description=rec_text,
                    purpose=purpose,
                    priority=priority,
                    estimated_impact=impact,
                    creation_complexity=complexity
                )
                multimodal_recs.append(multimodal_rec)

        self.multimodal_recommendations = multimodal_recs

        # 统计
        type_dist = defaultdict(int)
        priority_dist = defaultdict(int)
        for rec in multimodal_recs:
            type_dist[rec.media_type] += 1
            priority_dist[rec.priority] += 1

        print(f"\n  📊 生成 {len(multimodal_recs)} 条多模态内容建议:")
        print(f"\n  媒体类型分布:")
        for media_type, count in sorted(type_dist.items(), key=lambda x: x[1], reverse=True):
            print(f"    {media_type}: {count}个")

        print(f"\n  优先级分布:")
        for priority, count in sorted(priority_dist.items(), key=lambda x: x[1], reverse=True):
            print(f"    {priority}: {count}个")

        print(f"\n  🔴 高优先级建议 (前5):")
        high_priority = [r for r in multimodal_recs if r.priority == "high"][:5]
        for i, rec in enumerate(high_priority, 1):
            print(f"\n  {i}. [{rec.media_type}] {rec.content_title}")
            print(f"     建议: {rec.description[:80]}...")
            print(f"     目的: {rec.purpose} | 复杂度: {rec.creation_complexity}")

        # 保存计划
        with open(MULTIMODAL_PLAN_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "generated_at": datetime.now().isoformat(),
                "total_recommendations": len(multimodal_recs),
                "type_distribution": dict(type_dist),
                "priority_distribution": dict(priority_dist),
                "recommendations": [asdict(r) for r in multimodal_recs]
            }, f, ensure_ascii=False, indent=2)

        print(f"\n  ✅ 多模态内容计划已保存: {MULTIMODAL_PLAN_FILE}")

        return multimodal_recs

    # ==================== 4. 生成完整报告 ====================

    def generate_full_report(self) -> str:
        """生成完整的内容智能优化报告"""
        print("\n" + "=" * 60)
        print("  内容智能优化Agent - 生成完整报告")
        print("=" * 60)

        now = datetime.now()

        # 统计数据
        total = len(self.content_inventory)
        avg_score = sum(r.overall_score for r in self.content_inventory) / total if total > 0 else 0
        high_priority = [r for r in self.content_inventory if r.optimization_priority == "high"]
        medium_priority = [r for r in self.content_inventory if r.optimization_priority == "medium"]

        report = f"""# ChinaBound Travel 内容智能优化报告

**生成时间**: {now.strftime('%Y-%m-%d %H:%M:%S')}
**引擎版本**: v1.0
**成熟度目标**: L3 → L4

---

## 📊 执行摘要

| 指标 | 数值 |
|------|------|
| 文章总数 | {total} |
| 平均质量分 | {avg_score:.1f}/100 |
| 平均字数 | {sum(r.word_count for r in self.content_inventory) // total if total > 0 else 0} |
| 高优先级优化 | {len(high_priority)}篇 |
| 中优先级优化 | {len(medium_priority)}篇 |
| 选题推荐 | {len(self.topic_recommendations)}个 |
| 多模态内容建议 | {len(self.multimodal_recommendations)}个 |

---

## 🔍 内容质量审计

### 质量分布

| 质量等级 | 文章数 | 占比 |
|----------|--------|------|
"""

        status_dist = defaultdict(int)
        for r in self.content_inventory:
            status_dist[r.quality_status] += 1

        for status in ["excellent", "good", "average", "poor"]:
            count = status_dist.get(status, 0)
            pct = count / total * 100 if total > 0 else 0
            report += f"| {status} | {count} | {pct:.1f}% |\n"

        report += """
### 各维度平均分

| 维度 | 平均分 | 说明 |
|------|--------|------|
"""

        dimension_names = {
            "depth": "内容深度",
            "structure": "结构完整性",
            "seo": "SEO优化",
            "readability": "可读性",
            "multimedia": "多媒体丰富度",
            "engagement": "互动性",
            "freshness": "内容新鲜度"
        }

        all_scores = defaultdict(list)
        for r in self.content_inventory:
            for dim, score in r.quality_scores.items():
                all_scores[dim].append(score)

        for dim, scores in sorted(all_scores.items()):
            avg = sum(scores) / len(scores) if scores else 0
            name = dimension_names.get(dim, dim)
            report += f"| {name} | {avg:.1f}/100 | |\n"

        report += f"""
---

## 🎯 高优先级优化文章（Top 10）

| 排名 | 文章 | 质量分 | 展示量 | 点击量 | 排名 | 主要问题 |
|------|------|--------|--------|--------|------|----------|
"""

        for i, record in enumerate(high_priority[:10], 1):
            issues_short = "; ".join(record.issues[:2])[:50]
            report += f"| {i} | {record.title[:40]} | {record.overall_score:.0f} | {record.impressions_28d} | {record.clicks_28d} | {record.position_28d:.0f} | {issues_short} |\n"

        report += """
---

## 💡 内容优化建议

### 通用优化建议

1. **内容深度**：将<1500词的文章扩充至2000+词，增加详细步骤、案例和FAQ
2. **结构优化**：所有长文章添加目录（TOC），每篇至少3条内链
3. **SEO优化**：优化高展示低CTR页面的Title和Meta描述
4. **多媒体**：每篇文章至少2张图片，攻略类添加信息图
5. **转化优化**：所有文章添加相关的联盟推荐区块和CTA
6. **内容更新**：定期更新过时内容，确保信息准确

---

## 📝 智能选题推荐（Top 10）

| 优先级 | 选题 | 关键词 | 搜索意图 | 搜索量 | 竞争 | 内容类型 |
|--------|------|--------|----------|--------|------|----------|
"""

        for rec in self.topic_recommendations[:10]:
            priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(rec.priority, "⚪")
            report += f"| {priority_icon} {rec.priority} | {rec.topic[:40]} | {rec.keyword[:30]} | {rec.search_intent} | {rec.search_volume} | {rec.competition} | {rec.content_type} |\n"

        report += """
---

## 🖼️ 多模态内容生成计划

### 媒体类型分布

| 媒体类型 | 数量 | 说明 |
|----------|------|------|
"""

        type_dist = defaultdict(int)
        for rec in self.multimodal_recommendations:
            type_dist[rec.media_type] += 1

        type_descriptions = {
            "image": "普通图片",
            "infographic": "信息图",
            "video_script": "视频脚本",
            "image_carousel": "轮播图",
            "step_diagram": "步骤示意图"
        }

        for media_type, count in sorted(type_dist.items(), key=lambda x: x[1], reverse=True):
            desc = type_descriptions.get(media_type, media_type)
            report += f"| {desc} | {count} | |\n"

        report += """
### 高优先级多模态任务（Top 5）

| 优先级 | 文章 | 媒体类型 | 建议 | 目的 |
|--------|------|----------|------|------|
"""

        high_mm = [r for r in self.multimodal_recommendations if r.priority == "high"][:5]
        for rec in high_mm:
            report += f"| 🔴 high | {rec.content_title[:30]} | {rec.media_type} | {rec.description[:40]} | {rec.purpose} |\n"

        report += f"""
---

## 🚀 下一步行动计划

### 立即执行（1-3天）
1. 优化{len(high_priority)}篇高优先级文章的Title和Meta描述
2. 为无图片的文章添加2-3张高质量图片
3. 提交未索引页面到GSC

### 短期优化（1-2周）
1. 扩充<1500词的文章至2000+词，增加FAQ和内链
2. 创建3-5个信息图（高流量页面优先）
3. 启动1-2个新选题（高优先级推荐）

### 中期建设（1个月）
1. 建立内容更新机制（每月更新5篇旧内容）
2. 创建视频脚本和短视频内容
3. 建立主题集群和支柱页面结构

### 长期战略（3个月）
1. 实现内容质量自动评分和优化建议
2. 多模态内容自动生成（图片、信息图、视频脚本）
3. 基于用户行为的内容个性化推荐
4. 内容效果自动追踪和迭代优化

---

*报告由内容智能优化Agent自动生成 | {now.strftime('%Y-%m-%d %H:%M:%S')}*
*引擎版本: v1.0 | 成熟度目标: L3 → L4*
"""

        # 保存报告
        with open(CONTENT_REPORT_FILE, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"\n  ✅ 报告已生成: {CONTENT_REPORT_FILE}")
        print(f"  📊 报告长度: {len(report)} 字符")

        return report

    # ==================== 5. 完整优化流程 ====================

    def run_full_optimization(self):
        """运行完整的内容智能优化流程"""
        print("\n" + "=" * 60)
        print("  ChinaBound Travel - 内容智能优化Agent")
        print("  完整优化流程")
        print("=" * 60)

        print(f"\n📅 运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Step 1: 内容质量审计
        self.audit_content_quality()

        # Step 2: 选题推荐
        self.generate_topic_recommendations()

        # Step 3: 多模态内容规划
        self.generate_multimodal_plan()

        # Step 4: 生成报告
        self.generate_full_report()

        print("\n" + "=" * 60)
        print("  ✅ 完整内容智能优化流程完成！")
        print("=" * 60)
        print(f"\n📁 报告目录: {CONTENT_DIR}")
        print(f"📄 内容优化报告: {CONTENT_REPORT_FILE}")
        print(f"🔍 内容审计报告: {CONTENT_AUDIT_FILE}")
        print(f"📝 选题推荐: {TOPIC_RECOMMENDATIONS_FILE}")
        print(f"🖼️ 多模态计划: {MULTIMODAL_PLAN_FILE}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="ChinaBound Travel 内容智能优化Agent")
    parser.add_argument("--all", action="store_true", help="运行完整优化流程")
    parser.add_argument("--audit", action="store_true", help="仅内容质量审计")
    parser.add_argument("--topics", action="store_true", help="仅选题推荐")
    parser.add_argument("--multimodal", action="store_true", help="仅多模态内容规划")
    parser.add_argument("--report", action="store_true", help="仅生成报告")

    args = parser.parse_args()

    agent = ContentIntelligenceAgent()

    if args.all or not any([args.audit, args.topics, args.multimodal, args.report]):
        agent.run_full_optimization()
    elif args.audit:
        agent.audit_content_quality()
    elif args.topics:
        agent.audit_content_quality()
        agent.generate_topic_recommendations()
    elif args.multimodal:
        agent.audit_content_quality()
        agent.generate_multimodal_plan()
    elif args.report:
        agent.audit_content_quality()
        agent.generate_full_report()


if __name__ == "__main__":
    main()
