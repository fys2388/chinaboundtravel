#!/usr/bin/env python3
"""
ChinaBound Travel - 营收智能分析Agent
Revenue Intelligence Agent

核心能力（L1 → L2）：
1. 营收数据追踪与分析 - 联盟收入、订阅收入、广告收入
2. 收入趋势预测 - 基于历史数据的营收趋势分析
3. 收入机会识别 - 基于流量和转化数据的优化机会
4. 风险预警 - 营收下降、流量异常等风险检测
5. ROI 分析 - 各渠道/内容的投资回报率分析
6. LLM 营收洞察 - AI 驱动的营收分析与建议

成熟度目标：L1 → L2（6个月）
"""

import os
import sys
import json
import csv
import math
from datetime import datetime, timedelta

# P1-AI-OPS-03: Consume revenue optimization strategy from Learning Closed Loop
try:
    from strategy_consumer import StrategyConsumer
    _STRATEGY_CONSUMER = None
except Exception:
    _STRATEGY_CONSUMER = None

# LLM Agent Enhancer (可选)
try:
    from llm_agent_enhancer import get_enhancer
    _LLM_ENHANCER = get_enhancer()
except Exception:
    _LLM_ENHANCER = None

from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
from collections import defaultdict


# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
REVENUE_DIR = REPORTS_DIR / "revenue"
REVENUE_DIR.mkdir(parents=True, exist_ok=True)

# 数据文件
REVENUE_DATA_FILE = REVENUE_DIR / "revenue_data.json"
REVENUE_TRENDS_FILE = REVENUE_DIR / "revenue_trends.json"
REVENUE_OPPORTUNITIES_FILE = REVENUE_DIR / "revenue_opportunities.json"
REVENUE_RISKS_FILE = REVENUE_DIR / "revenue_risks.json"
REVENUE_ROI_FILE = REVENUE_DIR / "revenue_roi_analysis.json"
REVENUE_REPORT_FILE = REVENUE_DIR / "revenue_intelligence_report.md"


class RevenueType(Enum):
    """收入类型"""
    AFFILIATE = "affiliate"
    SUBSCRIPTION = "subscription"
    ADVERTISING = "advertising"
    SPONSORSHIP = "sponsorship"
    OTHER = "other"


class TrendDirection(Enum):
    """趋势方向"""
    UP = "up"
    DOWN = "down"
    STABLE = "stable"


class RiskLevel(Enum):
    """风险级别"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class OpportunityPriority(Enum):
    """机会优先级"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class RevenueRecord:
    """营收记录"""
    date: str
    revenue_type: str
    amount: float
    clicks: int
    conversions: int
    channel: str
    campaign: str = ""
    source_url: str = ""
    description: str = ""


@dataclass
class RevenueTrend:
    """营收趋势"""
    period: str
    total_revenue: float
    previous_revenue: float
    change_amount: float
    change_percentage: float
    direction: str
    daily_average: float
    projection: float


@dataclass
class RevenueOpportunity:
    """营收机会"""
    id: str
    category: str
    description: str
    estimated_impact: float
    priority: str
    confidence: float
    recommended_action: str


@dataclass
class RevenueRisk:
    """营收风险"""
    id: str
    risk_type: str
    description: str
    severity: str
    probability: float
    impact: float
    mitigation: str


@dataclass
class ROIResult:
    """ROI 分析结果"""
    channel: str
    total_investment: float
    total_revenue: float
    roi_percentage: float
    cost_per_click: float
    cost_per_conversion: float
    efficiency_score: float


class RevenueIntelligenceAgent:
    """营收智能分析Agent主类"""

    def __init__(self):
        self.revenue_records: List[RevenueRecord] = []
        self.revenue_trends: List[RevenueTrend] = []
        self.opportunities: List[RevenueOpportunity] = []
        self.risks: List[RevenueRisk] = []
        self.roi_results: List[ROIResult] = []
        self._load_data()
        # P1-AI-OPS-03: Load revenue optimization strategy
        self.strategy = None
        if _STRATEGY_CONSUMER is not None:
            try:
                self.strategy = _STRATEGY_CONSUMER("reports/revenue/revenue_optimization_strategy.json", "revenue")
            except Exception as _e:
                print(f"  ⚠️ Revenue Strategy load skipped: {_e}")

    def _load_data(self):
        """加载所有数据"""
        if REVENUE_DATA_FILE.exists():
            try:
                with open(REVENUE_DATA_FILE, encoding="utf-8") as f:
                    data = json.load(f)
                    self.revenue_records = [RevenueRecord(**r) for r in data.get("records", [])]
            except Exception as e:
                print(f"  ⚠️ 加载营收数据失败: {e}")

        if not self.revenue_records:
            self._generate_sample_data()

    def _save_data(self):
        """保存所有数据"""
        with open(REVENUE_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "last_updated": datetime.now().isoformat(),
                "records": [asdict(r) for r in self.revenue_records]
            }, f, ensure_ascii=False, indent=2)

    def _generate_sample_data(self):
        """生成模拟营收数据用于演示"""
        print("  📊 生成模拟营收数据用于演示...")

        today = datetime.now()
        channels = ["organic_search", "direct", "social_media", "email", "affiliate"]
        campaigns = ["china_travel_guide", "visa_guide", "payment_guide", "esim_guide", "transport_guide"]

        for i in range(90):
            date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            for channel in channels:
                for campaign in campaigns[:3]:
                    base_amount = 50.0
                    if channel == "organic_search":
                        base_amount *= 1.5
                    elif channel == "email":
                        base_amount *= 2.0

                    amount = base_amount * (0.5 + math.sin(i / 10) * 0.3)
                    clicks = int(amount / 0.5)
                    conversions = max(1, int(clicks * 0.03))

                    record = RevenueRecord(
                        date=date,
                        revenue_type="affiliate",
                        amount=round(amount, 2),
                        clicks=clicks,
                        conversions=conversions,
                        channel=channel,
                        campaign=campaign,
                        source_url=f"/posts/{campaign}/",
                        description=f"Affiliate revenue from {campaign}"
                    )
                    self.revenue_records.append(record)

        print(f"  ✅ 生成 {len(self.revenue_records)} 条营收记录")

    # ==================== 1. 营收数据追踪与分析 ====================

    def analyze_revenue(self) -> Dict[str, Any]:
        """分析营收数据"""
        print("\n" + "=" * 60)
        print("  营收智能分析Agent - 营收数据分析")
        print("=" * 60)

        if not self.revenue_records:
            print("  ⚠️ 无营收数据")
            return {}

        total_revenue = sum(r.amount for r in self.revenue_records)
        total_clicks = sum(r.clicks for r in self.revenue_records)
        total_conversions = sum(r.conversions for r in self.revenue_records)

        # 按类型分组
        by_type = defaultdict(list)
        for r in self.revenue_records:
            by_type[r.revenue_type].append(r)

        # 按渠道分组
        by_channel = defaultdict(list)
        for r in self.revenue_records:
            by_channel[r.channel].append(r)

        # 按活动分组
        by_campaign = defaultdict(list)
        for r in self.revenue_records:
            by_campaign[r.campaign].append(r)

        # 计算关键指标
        conversion_rate = total_conversions / total_clicks if total_clicks > 0 else 0
        revenue_per_click = total_revenue / total_clicks if total_clicks > 0 else 0
        revenue_per_conversion = total_revenue / total_conversions if total_conversions > 0 else 0

        # 按类型汇总
        type_summary = {}
        for rtype, records in by_type.items():
            type_summary[rtype] = {
                "total_revenue": sum(r.amount for r in records),
                "total_clicks": sum(r.clicks for r in records),
                "total_conversions": sum(r.conversions for r in records),
                "percentage": sum(r.amount for r in records) / total_revenue * 100 if total_revenue > 0 else 0
            }

        # 按渠道汇总
        channel_summary = {}
        for channel, records in by_channel.items():
            channel_summary[channel] = {
                "total_revenue": sum(r.amount for r in records),
                "total_clicks": sum(r.clicks for r in records),
                "percentage": sum(r.amount for r in records) / total_revenue * 100 if total_revenue > 0 else 0
            }

        analysis = {
            "total_revenue": round(total_revenue, 2),
            "total_clicks": total_clicks,
            "total_conversions": total_conversions,
            "conversion_rate": round(conversion_rate * 100, 2),
            "revenue_per_click": round(revenue_per_click, 2),
            "revenue_per_conversion": round(revenue_per_conversion, 2),
            "by_type": type_summary,
            "by_channel": channel_summary,
            "record_count": len(self.revenue_records)
        }

        print(f"\n  📊 营收概览:")
        print(f"    总收入: ${analysis['total_revenue']:.2f}")
        print(f"    总点击: {analysis['total_clicks']:,}")
        print(f"    总转化: {analysis['total_conversions']:,}")
        print(f"    转化率: {analysis['conversion_rate']:.2f}%")
        print(f"    每次点击收入: ${analysis['revenue_per_click']:.2f}")

        print(f"\n  📊 按类型:")
        for rtype, data in sorted(type_summary.items(), key=lambda x: x[1]['total_revenue'], reverse=True):
            print(f"    {rtype}: ${data['total_revenue']:.2f} ({data['percentage']:.1f}%)")

        print(f"\n  📊 按渠道 Top 5:")
        for channel, data in sorted(channel_summary.items(), key=lambda x: x[1]['total_revenue'], reverse=True)[:5]:
            print(f"    {channel}: ${data['total_revenue']:.2f} ({data['percentage']:.1f}%)")

        # 保存分析结果
        with open(REVENUE_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "analyzed_at": datetime.now().isoformat(),
                "analysis": analysis,
                "records": [asdict(r) for r in self.revenue_records]
            }, f, ensure_ascii=False, indent=2)

        print(f"\n  ✅ 营收分析已保存: {REVENUE_DATA_FILE}")

        return analysis

    # ==================== 2. 收入趋势预测 ====================

    def analyze_revenue_trends(self) -> List[RevenueTrend]:
        """分析营收趋势"""
        print("\n" + "=" * 60)
        print("  营收智能分析Agent - 营收趋势分析")
        print("=" * 60)

        if not self.revenue_records:
            print("  ⚠️ 无营收数据")
            return []

        # 按日期分组
        by_date = defaultdict(float)
        for r in self.revenue_records:
            by_date[r.date] += r.amount

        # 排序日期
        sorted_dates = sorted(by_date.keys())

        # 按周分组
        weekly_revenue = []
        for i in range(0, len(sorted_dates), 7):
            week_dates = sorted_dates[i:i+7]
            week_total = sum(by_date[d] for d in week_dates)
            week_start = week_dates[0] if week_dates else ""
            weekly_revenue.append({
                "week_start": week_start,
                "total_revenue": round(week_total, 2)
            })

        # 计算趋势
        trends = []
        for i in range(1, len(weekly_revenue)):
            current = weekly_revenue[i]
            previous = weekly_revenue[i-1]

            change_amount = current["total_revenue"] - previous["total_revenue"]
            change_percentage = (change_amount / previous["total_revenue"] * 100) if previous["total_revenue"] > 0 else 0

            if change_percentage > 10:
                direction = TrendDirection.UP.value
            elif change_percentage < -10:
                direction = TrendDirection.DOWN.value
            else:
                direction = TrendDirection.STABLE.value

            trend = RevenueTrend(
                period=current["week_start"],
                total_revenue=current["total_revenue"],
                previous_revenue=previous["total_revenue"],
                change_amount=round(change_amount, 2),
                change_percentage=round(change_percentage, 2),
                direction=direction,
                daily_average=round(current["total_revenue"] / 7, 2),
                projection=round(current["total_revenue"] * (1 + change_percentage / 100), 2)
            )
            trends.append(trend)

        print(f"\n  📊 营收趋势 ({len(trends)} 周):")
        for trend in trends[-4:]:  # 只显示最近 4 周
            direction_icon = {"up": "📈", "down": "📉", "stable": "➡️"}.get(trend.direction, "➡️")
            print(f"    {trend.period}: ${trend.total_revenue:.2f} "
                  f"({trend.change_percentage:+.1f}%) {direction_icon}")

        # 保存趋势
        with open(REVENUE_TRENDS_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "analyzed_at": datetime.now().isoformat(),
                "trends": [asdict(t) for t in trends]
            }, f, ensure_ascii=False, indent=2)

        print(f"\n  ✅ 营收趋势已保存: {REVENUE_TRENDS_FILE}")

        return trends

    # ==================== 3. 收入机会识别 ====================

    def identify_opportunities(self, analysis: Dict = None) -> List[RevenueOpportunity]:
        """识别营收机会"""
        print("\n" + "=" * 60)
        print("  营收智能分析Agent - 营收机会识别")
        print("=" * 60)

        if not analysis:
            analysis = self.analyze_revenue()

        if not analysis:
            return []

        opportunities = []
        opportunity_id = 1

        # 1. 高转化低流量渠道
        channel_data = analysis.get("by_channel", {})
        avg_conversion = analysis.get("conversion_rate", 0)
        for channel, data in channel_data.items():
            channel_clicks = data.get("total_clicks", 0)
            channel_revenue = data.get("total_revenue", 0)
            if channel_clicks < 1000 and channel_revenue > 100:
                opportunities.append(RevenueOpportunity(
                    id=f"opp_{opportunity_id:03d}",
                    category="channel_expansion",
                    description=f"渠道 '{channel}' 转化率高但流量低，建议增加投入",
                    estimated_impact=round(channel_revenue * 0.5, 2),
                    priority=OpportunityPriority.HIGH.value,
                    confidence=0.75,
                    recommended_action=f"增加 {channel} 渠道的营销预算，目标提升 50% 流量"
                ))
                opportunity_id += 1

        # 2. 高收入低转化活动
        campaign_data = defaultdict(list)
        for r in self.revenue_records:
            if r.campaign:
                campaign_data[r.campaign].append(r)

        for campaign, records in campaign_data.items():
            total_clicks = sum(r.clicks for r in records)
            total_conversions = sum(r.conversions for r in records)
            conversion_rate = total_conversions / total_clicks if total_clicks > 0 else 0

            if conversion_rate < avg_conversion * 0.5 and total_conversions > 10:
                opportunities.append(RevenueOpportunity(
                    id=f"opp_{opportunity_id:03d}",
                    category="conversion_optimization",
                    description=f"活动 '{campaign}' 转化率低于平均，有优化空间",
                    estimated_impact=round(total_clicks * conversion_rate * 0.5 * analysis.get("revenue_per_conversion", 0), 2),
                    priority=OpportunityPriority.MEDIUM.value,
                    confidence=0.65,
                    recommended_action=f"优化 {campaign} 的落地页和CTA，目标提升转化率 50%"
                ))
                opportunity_id += 1

        # 3. 季节性机会
        recent_trends = self.revenue_trends[-4:] if self.revenue_trends else []
        if recent_trends:
            growing_trends = [t for t in recent_trends if t.direction == "up"]
            if len(growing_trends) >= 2:
                opportunities.append(RevenueOpportunity(
                    id=f"opp_{opportunity_id:03d}",
                    category="seasonal_growth",
                    description="营收呈持续增长趋势，建议趁势增加内容投入",
                    estimated_impact=round(analysis.get("total_revenue", 0) * 0.1, 2),
                    priority=OpportunityPriority.HIGH.value,
                    confidence=0.70,
                    recommended_action="增加高质量内容创作，利用增长势头扩大市场份额"
                ))
                opportunity_id += 1

        print(f"\n  📊 识别 {len(opportunities)} 个营收机会:")
        for opp in opportunities:
            priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(opp.priority, "⚪")
            print(f"\n  {priority_icon} [{opp.priority.upper()}] {opp.description}")
            print(f"     预期影响: ${opp.estimated_impact:.2f}")
            print(f"     置信度: {opp.confidence*100:.0f}%")
            print(f"     建议: {opp.recommended_action[:80]}...")

        # 保存机会
        with open(REVENUE_OPPORTUNITIES_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "analyzed_at": datetime.now().isoformat(),
                "opportunities": [asdict(o) for o in opportunities]
            }, f, ensure_ascii=False, indent=2)

        print(f"\n  ✅ 营收机会已保存: {REVENUE_OPPORTUNITIES_FILE}")

        return opportunities

    # ==================== 4. 风险预警 ====================

    def identify_risks(self, analysis: Dict = None) -> List[RevenueRisk]:
        """识别营收风险"""
        print("\n" + "=" * 60)
        print("  营收智能分析Agent - 营收风险预警")
        print("=" * 60)

        if not analysis:
            analysis = self.analyze_revenue()

        if not analysis:
            return []

        risks = []
        risk_id = 1

        # 1. 转化率下降风险
        conversion_rate = analysis.get("conversion_rate", 0)
        if conversion_rate < 2.0:
            risks.append(RevenueRisk(
                id=f"risk_{risk_id:03d}",
                risk_type="conversion_decline",
                description=f"转化率偏低 ({conversion_rate:.2f}%)，可能导致营收下降",
                severity=RiskLevel.HIGH.value,
                probability=0.60,
                impact=round(analysis.get("total_revenue", 0) * 0.2, 2),
                mitigation="优化CTA和落地页，提升用户体验"
            ))
            risk_id += 1

        # 2. 收入集中风险
        channel_data = analysis.get("by_channel", {})
        for channel, data in channel_data.items():
            if data.get("percentage", 0) > 60:
                risks.append(RevenueRisk(
                    id=f"risk_{risk_id:03d}",
                    risk_type="channel_concentration",
                    description=f"收入过度集中在 '{channel}' 渠道 ({data['percentage']:.1f}%)",
                    severity=RiskLevel.MEDIUM.value,
                    probability=0.40,
                    impact=round(data["total_revenue"] * 0.3, 2),
                    mitigation="多元化收入来源，发展其他渠道"
                ))
                risk_id += 1

        # 3. 趋势下降风险
        if self.revenue_trends:
            recent_down = sum(1 for t in self.revenue_trends[-4:] if t.direction == "down")
            if recent_down >= 2:
                risks.append(RevenueRisk(
                    id=f"risk_{risk_id:03d}",
                    risk_type="trend_decline",
                    description="营收连续下降，需要立即关注",
                    severity=RiskLevel.HIGH.value,
                    probability=0.70,
                    impact=round(analysis.get("total_revenue", 0) * 0.3, 2),
                    mitigation="分析下降原因，调整内容策略和营销预算"
                ))
                risk_id += 1

        print(f"\n  📊 识别 {len(risks)} 个营收风险:")
        for risk in risks:
            severity_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(risk.severity, "⚪")
            print(f"\n  {severity_icon} [{risk.severity.upper()}] {risk.description}")
            print(f"     概率: {risk.probability*100:.0f}%")
            print(f"     影响: ${risk.impact:.2f}")
            print(f"     缓解: {risk.mitigation[:80]}...")

        # 保存风险
        with open(REVENUE_RISKS_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "analyzed_at": datetime.now().isoformat(),
                "risks": [asdict(r) for r in risks]
            }, f, ensure_ascii=False, indent=2)

        print(f"\n  ✅ 营收风险已保存: {REVENUE_RISKS_FILE}")

        return risks

    # ==================== 5. ROI 分析 ====================

    def analyze_roi(self) -> List[ROIResult]:
        """分析各渠道 ROI"""
        print("\n" + "=" * 60)
        print("  营收智能分析Agent - ROI 分析")
        print("=" * 60)

        if not self.revenue_records:
            print("  ⚠️ 无营收数据")
            return []

        # 按渠道分组
        by_channel = defaultdict(list)
        for r in self.revenue_records:
            by_channel[r.channel].append(r)

        # 计算各渠道 ROI
        # 假设成本：organic=免费, direct=免费, social=500/月, email=200/月, affiliate=300/月
        channel_costs = {
            "organic_search": 0,
            "direct": 0,
            "social_media": 500,
            "email": 200,
            "affiliate": 300
        }

        results = []
        for channel, records in by_channel.items():
            total_revenue = sum(r.amount for r in records)
            total_clicks = sum(r.clicks for r in records)
            total_conversions = sum(r.conversions for r in records)
            total_investment = channel_costs.get(channel, 0)

            roi_percentage = ((total_revenue - total_investment) / total_investment * 100) if total_investment > 0 else float('inf')
            cpc = total_investment / total_clicks if total_clicks > 0 else 0
            cpa = total_investment / total_conversions if total_conversions > 0 else 0

            # 效率评分 (0-100)
            efficiency_score = min(100, (total_revenue / total_investment * 10) if total_investment > 0 else 100)

            result = ROIResult(
                channel=channel,
                total_investment=total_investment,
                total_revenue=round(total_revenue, 2),
                roi_percentage=round(roi_percentage, 2) if roi_percentage != float('inf') else 9999,
                cost_per_click=round(cpc, 2),
                cost_per_conversion=round(cpa, 2),
                efficiency_score=round(efficiency_score, 1)
            )
            results.append(result)

        # 按 ROI 排序
        results.sort(key=lambda x: x.roi_percentage, reverse=True)

        print(f"\n  📊 各渠道 ROI:")
        for result in results:
            roi_icon = "🟢" if result.roi_percentage > 500 else "🟡" if result.roi_percentage > 100 else "🔴"
            print(f"    {roi_icon} {result.channel}: ROI={result.roi_percentage:.0f}% "
                  f"(${result.total_revenue:.2f}/${result.total_investment})")

        # 保存 ROI
        with open(REVENUE_ROI_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "analyzed_at": datetime.now().isoformat(),
                "results": [asdict(r) for r in results]
            }, f, ensure_ascii=False, indent=2)

        print(f"\n  ✅ ROI 分析已保存: {REVENUE_ROI_FILE}")

        return results

    # ==================== 6. LLM 营收洞察 ====================

    def analyze_revenue_with_llm(self, analysis: Dict = None) -> Optional[Dict]:
        """使用 LLM 生成营收洞察"""
        if not _LLM_ENHANCER or not _LLM_ENHANCER.available:
            print("  ⚠️ LLM 不可用，跳过营收洞察")
            return None

        if not analysis:
            analysis = self.analyze_revenue()

        if not analysis:
            return None

        try:
            result = _LLM_ENHANCER.analyze_revenue_trends(
                revenue_data={
                    "period": "Last 30 days",
                    "total_revenue": analysis.get("total_revenue", 0),
                    "affiliate_clicks": analysis.get("total_clicks", 0),
                    "conversion_rate": analysis.get("conversion_rate", 0),
                    "aov": analysis.get("revenue_per_conversion", 0),
                    "top_categories": list(analysis.get("by_type", {}).keys())
                },
                traffic_data={
                    "total_visits": analysis.get("total_clicks", 0) * 3,  # 估算
                    "pages_per_visit": 3.2,
                    "bounce_rate": 45,
                    "organic_traffic": 60,
                    "direct_traffic": 20
                }
            )

            if result:
                print(f"\n  🤖 LLM 营收洞察:")
                print(f"    趋势: {result.get('trend', 'N/A')}")
                print(f"    增长: {result.get('growth', 'N/A')}")
                print(f"    摘要: {result.get('summary', 'N/A')[:100]}...")

                # 保存 LLM 洞察
                with open(REVENUE_DIR / "llm_insights.json", "w", encoding="utf-8") as f:
                    json.dump({
                        "analyzed_at": datetime.now().isoformat(),
                        "insights": result
                    }, f, ensure_ascii=False, indent=2)

                print(f"  ✅ LLM 洞察已保存")

            return result
        except Exception as e:
            print(f"  ⚠️ LLM 营收分析失败: {e}")
            return None

    # ==================== 7. 生成报告 ====================

    def generate_report(self) -> str:
        """生成营收智能报告"""
        print("\n" + "=" * 60)
        print("  营收智能分析Agent - 生成报告")
        print("=" * 60)

        analysis = self.analyze_revenue()
        trends = self.analyze_revenue_trends()
        opportunities = self.identify_opportunities(analysis)
        risks = self.identify_risks(analysis)
        roi_results = self.analyze_roi()

        # LLM 洞察 (可选)
        llm_insights = None
        if _LLM_ENHANCER and _LLM_ENHANCER.available:
            llm_insights = self.analyze_revenue_with_llm(analysis)

        # 生成 Markdown 报告
        report = f"""# 📊 营收智能分析报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
**分析周期**: 最近 90 天

## 📈 营收概览

| 指标 | 数值 |
|------|------|
| 总收入 | ${analysis.get('total_revenue', 0):.2f} |
| 总点击 | {analysis.get('total_clicks', 0):,} |
| 总转化 | {analysis.get('total_conversions', 0):,} |
| 转化率 | {analysis.get('conversion_rate', 0):.2f}% |
| 每次点击收入 | ${analysis.get('revenue_per_click', 0):.2f} |

## 📊 收入分布

### 按类型
"""
        for rtype, data in analysis.get('by_type', {}).items():
            report += f"- **{rtype}**: ${data['total_revenue']:.2f} ({data['percentage']:.1f}%)\n"

        report += "\n### 按渠道\n"
        for channel, data in sorted(analysis.get('by_channel', {}).items(),
                                     key=lambda x: x[1]['total_revenue'], reverse=True):
            report += f"- **{channel}**: ${data['total_revenue']:.2f} ({data['percentage']:.1f}%)\n"

        if trends:
            report += "\n## 📈 营收趋势\n"
            for trend in trends[-4:]:
                direction_icon = {"up": "📈", "down": "📉", "stable": "➡️"}.get(trend.direction, "➡️")
                report += f"- **{trend.period}**: ${trend.total_revenue:.2f} " \
                          f"({trend.change_percentage:+.1f}%) {direction_icon}\n"

        if opportunities:
            report += "\n## 💡 营收机会\n"
            for opp in opportunities:
                priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(opp.priority, "⚪")
                report += f"- {priority_icon} **{opp.description}**\n"
                report += f"  - 预期影响: ${opp.estimated_impact:.2f}\n"
                report += f"  - 建议: {opp.recommended_action}\n"

        if risks:
            report += "\n## ⚠️ 营收风险\n"
            for risk in risks:
                severity_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(risk.severity, "⚪")
                report += f"- {severity_icon} **{risk.description}**\n"
                report += f"  - 概率: {risk.probability*100:.0f}%\n"
                report += f"  - 缓解: {risk.mitigation}\n"

        if roi_results:
            report += "\n## 💰 ROI 分析\n"
            report += "| 渠道 | 收入 | 投资 | ROI | 效率 |\n"
            report += "|------|------|------|-----|------|\n"
            for result in roi_results:
                report += f"| {result.channel} | ${result.total_revenue:.2f} | " \
                          f"${result.total_investment} | {result.roi_percentage:.0f}% | " \
                          f"{result.efficiency_score:.0f}/100 |\n"

        if llm_insights:
            report += "\n## 🤖 LLM 营收洞察\n"
            report += f"- **趋势**: {llm_insights.get('trend', 'N/A')}\n"
            report += f"- **增长**: {llm_insights.get('growth', 'N/A')}\n"
            report += f"- **摘要**: {llm_insights.get('summary', 'N/A')}\n"

            if llm_insights.get('opportunities'):
                report += "\n### 推荐机会\n"
                for opp in llm_insights['opportunities'][:3]:
                    report += f"- **{opp.get('category', 'N/A')}**: {opp.get('opportunity', 'N/A')}\n"

            if llm_insights.get('risks'):
                report += "\n### 风险提示\n"
                for risk in llm_insights['risks'][:3]:
                    report += f"- **{risk.get('risk', 'N/A')}**: {risk.get('mitigation', 'N/A')}\n"

        report += f"\n---\n*报告由 Revenue Intelligence Agent 自动生成*\n"

        with open(REVENUE_REPORT_FILE, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"\n  ✅ 营收报告已生成: {REVENUE_REPORT_FILE}")

        return report

    # ==================== 主入口 ====================

    def run_all(self):
        """运行所有分析"""
        print("\n" + "=" * 60)
        print("  营收智能分析Agent - 运行所有分析")
        print("=" * 60)

        # 1. 营收分析
        analysis = self.analyze_revenue()

        # 2. 趋势分析
        trends = self.analyze_revenue_trends()

        # 3. 机会识别
        opportunities = self.identify_opportunities(analysis)

        # 4. 风险预警
        risks = self.identify_risks(analysis)

        # 5. ROI 分析
        roi_results = self.analyze_roi()

        # 6. LLM 洞察 (可选)
        if _LLM_ENHANCER and _LLM_ENHANCER.available:
            llm_insights = self.analyze_revenue_with_llm(analysis)
        else:
            llm_insights = None

        # 7. 生成报告
        self.generate_report()

        return {
            "analysis": analysis,
            "trends": [asdict(t) for t in trends],
            "opportunities": [asdict(o) for o in opportunities],
            "risks": [asdict(r) for r in risks],
            "roi": [asdict(r) for r in roi_results],
            "llm_insights": llm_insights
        }


# ============ 便捷函数 ============

def get_revenue_agent() -> RevenueIntelligenceAgent:
    """获取 RevenueAgent 实例"""
    return RevenueIntelligenceAgent()


# ============ 测试入口 ============

if __name__ == '__main__':
    print("🧪 Revenue Intelligence Agent Test")
    print("=" * 50)

    agent = RevenueIntelligenceAgent()

    print(f"\nLLM Available: {bool(_LLM_ENHANCER and _LLM_ENHANCER.available)}")

    # 运行所有分析
    result = agent.run_all()

    print(f"\n✅ Test completed!")
    print(f"   Revenue: ${result.get('analysis', {}).get('total_revenue', 0):.2f}")
    print(f"   Opportunities: {len(result.get('opportunities', []))}")
    print(f"   Risks: {len(result.get('risks', []))}")
    print(f"   LLM Insights: {'Yes' if result.get('llm_insights') else 'No'}")
