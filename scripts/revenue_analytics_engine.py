#!/usr/bin/env python3
"""
ChinaBound Travel - 收入数据闭环与深度分析引擎
Revenue Analytics Engine

核心能力：
1. 收入数据采集闭环 - 从Travelpayouts API获取真实数据，确保流入报告
2. 点击→订单→收入完整归因 - 建立完整的转化漏斗分析
3. 分产品深度分析 - 酒店、机票、保险、eSIM、当地游等产品维度
4. 分渠道深度分析 - 页面、文章、CTA位置等渠道维度
5. 趋势预测与预警 - 收入趋势分析、异常检测、预警机制
6. ROI分析与优化建议 - 基于数据的收入优化建议

成熟度目标：L2 → L3（6个月）
"""

import os
import sys
import json
import csv
from datetime import datetime, timedelta

# P1-AI-OPS-03: Consume revenue optimization strategy from Learning Closed Loop
try:
    from strategy_consumer import StrategyConsumer
    _STRATEGY_CONSUMER = None
except Exception:
    _STRATEGY_CONSUMER = None
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
import requests
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(Path(__file__).parent.parent / ".env")

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
REVENUE_DIR = REPORTS_DIR / "revenue"
REVENUE_DIR.mkdir(parents=True, exist_ok=True)

# 数据文件
REVENUE_SNAPSHOT_FILE = REVENUE_DIR / "revenue_snapshot.json"
REVENUE_HISTORY_FILE = REVENUE_DIR / "revenue_history.json"
PRODUCT_BREAKDOWN_FILE = REVENUE_DIR / "product_breakdown.csv"
CHANNEL_BREAKDOWN_FILE = REVENUE_DIR / "channel_breakdown.csv"
REVENUE_REPORT_FILE = REVENUE_DIR / "revenue_analytics_report.md"

# Travelpayouts API配置
TRAVELPAYOUTS_API_URL = "https://api.travelpayouts.com/statistics/v1/execute_query"
TRAVELPAYOUTS_API_TOKEN = os.environ.get("TRAVELPAYOUTS_API_TOKEN", "").strip()
TRAVELPAYOUTS_MARKER = os.environ.get("TRAVELPAYOUTS_MARKER", "")


class FunnelStage(Enum):
    """转化漏斗阶段"""
    IMPRESSION = "impression"  # 展示
    CLICK = "click"            # 点击
    INIT = "init"              # 初始化（跳转成功）
    SEARCH = "search"          # 搜索
    BOOKING = "booking"        # 预订
    REVENUE = "revenue"        # 收入


class ProductType(Enum):
    """产品类型"""
    HOTEL = "hotel"                    # 酒店
    FLIGHT = "flight"                  # 机票
    INSURANCE = "insurance"            # 保险
    ESIM = "esim"                      # eSIM
    TOUR = "tour"                      # 当地游/一日游
    TRANSFER = "transfer"              # 接送机
    CAR_RENTAL = "car_rental"          # 租车
    OTHER = "other"                    # 其他


@dataclass
class RevenueMetrics:
    """收入指标数据结构"""
    period_start: str
    period_end: str
    days: int

    # 漏斗指标
    impressions: int = 0
    clicks: int = 0
    inits: int = 0
    searches: int = 0
    bookings: int = 0
    revenue: float = 0.0

    # 转化率
    click_through_rate: float = 0.0    # 展示→点击
    init_rate: float = 0.0             # 点击→初始化
    booking_rate: float = 0.0          # 点击→预订
    conversion_rate: float = 0.0       # 点击→收入转化

    # 价值指标
    revenue_per_click: float = 0.0     # 每次点击收入
    revenue_per_booking: float = 0.0   # 每笔订单收入
    avg_order_value: float = 0.0       # 平均订单价值

    # 数据质量
    data_source: str = "api"            # api / cache / unknown
    data_quality: str = "good"          # good / warning / error
    notes: List[str] = field(default_factory=list)


@dataclass
class ProductMetrics:
    """产品维度指标"""
    product_type: str
    clicks: int = 0
    bookings: int = 0
    revenue: float = 0.0
    conversion_rate: float = 0.0
    revenue_per_click: float = 0.0
    share_of_clicks: float = 0.0
    share_of_revenue: float = 0.0
    trend: str = "stable"  # growing / declining / stable / new


@dataclass
class ChannelMetrics:
    """渠道维度指标"""
    channel_name: str
    channel_type: str  # page / article / cta_position / source
    clicks: int = 0
    bookings: int = 0
    revenue: float = 0.0
    conversion_rate: float = 0.0
    revenue_per_click: float = 0.0
    share_of_clicks: float = 0.0
    share_of_revenue: float = 0.0
    top_pages: List[str] = field(default_factory=list)


class RevenueAnalyticsEngine:
    """收入数据分析引擎主类"""

    def __init__(self):
        self.current_metrics: Optional[RevenueMetrics] = None
        self.historical_metrics: List[RevenueMetrics] = []
        self.product_metrics: List[ProductMetrics] = []
        self.channel_metrics: List[ChannelMetrics] = []
        self._load_history()


        # P1-AI-OPS-03: Load revenue optimization strategy
        self.strategy = None
        if _STRATEGY_CONSUMER is not None:
            try:
                self.strategy = _STRATEGY_CONSUMER("reports/revenue/revenue_optimization_strategy.json", "revenue")
            except Exception as _e:
                print(f"  ⚠️ Strategy load skipped: {_e}")

    def _load_history(self):
        """加载历史数据"""
        if REVENUE_HISTORY_FILE.exists():
            try:
                with open(REVENUE_HISTORY_FILE, encoding="utf-8") as f:
                    data = json.load(f)
                    self.historical_metrics = [RevenueMetrics(**m) for m in data.get("snapshots", [])]
            except Exception as e:
                print(f"  ⚠️ 加载历史数据失败: {e}")
                self.historical_metrics = []

    def _save_history(self):
        """保存历史数据"""
        with open(REVENUE_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "snapshots": [asdict(m) for m in self.historical_metrics[-52:]],  # 保留最近52周
                "total_snapshots": len(self.historical_metrics),
                "last_updated": datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)

    # ==================== 1. 收入数据采集闭环 ====================

    def fetch_revenue_data(self, days: int = 28) -> RevenueMetrics:
        """从Travelpayouts API获取收入数据（复用已验证的travelpayouts_client）"""
        print("\n" + "=" * 60)
        print("  收入分析引擎 - 数据采集")
        print("=" * 60)

        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)

        metrics = RevenueMetrics(
            period_start=start_date.isoformat(),
            period_end=end_date.isoformat(),
            days=days
        )

        if not TRAVELPAYOUTS_API_TOKEN:
            print("  ⚠️ TRAVELPAYOUTS_API_TOKEN 未配置")
            metrics.data_quality = "error"
            metrics.notes.append("API token未配置")
            self.current_metrics = metrics
            return metrics

        print(f"\n  📅 时间范围: {start_date} ~ {end_date} ({days}天)")
        print(f"  🔌 使用 travelpayouts_client (已验证的API客户端)")

        try:
            # 复用已验证的travelpayouts_client
            sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
            from travelpayouts_client import fetch_affiliate_stats

            result = fetch_affiliate_stats(days=days)

            if result is not None:
                metrics.clicks = int(result.get("clicks", 0))
                metrics.bookings = int(result.get("bookings", 0))
                metrics.revenue = float(result.get("revenue", 0.0))
                metrics.inits = int(result.get("inits", 0))
                metrics.searches = int(result.get("searches", 0))

                metrics.data_source = "api"
                metrics.data_quality = "good"

                print(f"  ✅ API调用成功")
                print(f"  📊 点击: {metrics.clicks} | 预订: {metrics.bookings} | 收入: ${metrics.revenue:.2f}")
                print(f"  📊 初始化: {metrics.inits} | 搜索: {metrics.searches}")

                # 数据质量检查
                if metrics.clicks > 0 and metrics.bookings == 0:
                    metrics.notes.append("有点击但无预订（新站正常，需关注转化）")
                if metrics.revenue == 0 and metrics.bookings > 0:
                    metrics.notes.append("有预订但无收入（可能是结算延迟）")
                if metrics.inits == 0 and metrics.clicks > 0:
                    metrics.notes.append("有点击但inits=0（可能是追踪问题）")

            else:
                print(f"  ⚠️ API返回None（调用失败或无数据）")
                metrics.data_quality = "warning"
                metrics.notes.append("API返回None")

        except Exception as e:
            print(f"  ❌ API调用异常: {e}")
            import traceback
            traceback.print_exc()
            metrics.data_quality = "error"
            metrics.notes.append(f"API异常: {str(e)}")

        # 计算衍生指标
        self._calculate_derived_metrics(metrics)

        # 保存当前指标
        self.current_metrics = metrics

        # 添加到历史
        self.historical_metrics.append(metrics)
        self._save_history()

        return metrics

    def _calculate_derived_metrics(self, metrics: RevenueMetrics):
        """计算衍生指标"""
        # 转化率
        if metrics.impressions > 0:
            metrics.click_through_rate = (metrics.clicks / metrics.impressions) * 100

        if metrics.clicks > 0:
            metrics.init_rate = (metrics.inits / metrics.clicks) * 100
            metrics.booking_rate = (metrics.bookings / metrics.clicks) * 100
            metrics.conversion_rate = (metrics.bookings / metrics.clicks) * 100
            metrics.revenue_per_click = metrics.revenue / metrics.clicks

        if metrics.bookings > 0:
            metrics.revenue_per_booking = metrics.revenue / metrics.bookings
            metrics.avg_order_value = metrics.revenue / metrics.bookings

    # ==================== 2. 点击→订单→收入完整归因 ====================

    def analyze_funnel(self) -> Dict[str, Any]:
        """分析转化漏斗"""
        print("\n" + "=" * 60)
        print("  收入分析引擎 - 转化漏斗分析")
        print("=" * 60)

        if not self.current_metrics:
            print("  ⚠️ 请先调用fetch_revenue_data()")
            return {}

        m = self.current_metrics

        funnel = [
            {"stage": "展示 (Impressions)", "value": m.impressions, "rate_from_prev": 100.0},
            {"stage": "点击 (Clicks)", "value": m.clicks, "rate_from_prev": m.click_through_rate},
            {"stage": "初始化 (Inits)", "value": m.inits, "rate_from_prev": m.init_rate},
            {"stage": "搜索 (Searches)", "value": m.searches, "rate_from_prev": (m.searches / m.inits * 100) if m.inits > 0 else 0},
            {"stage": "预订 (Bookings)", "value": m.bookings, "rate_from_prev": m.booking_rate},
            {"stage": "收入 (Revenue)", "value": f"${m.revenue:.2f}", "rate_from_prev": 100.0 if m.bookings > 0 else 0},
        ]

        print(f"\n  📊 转化漏斗 ({m.days}天):")
        for stage in funnel:
            value = stage["value"]
            rate = stage["rate_from_prev"]
            if isinstance(value, (int, float)):
                print(f"    {stage['stage']}: {value:,} ({rate:.1f}%)")
            else:
                print(f"    {stage['stage']}: {value}")

        # 漏斗问题诊断
        issues = []
        if m.clicks > 0 and m.inits == 0:
            issues.append("🔴 点击→初始化断裂：有点击但无初始化，可能是跳转链接或追踪问题")
        if m.inits > 0 and m.searches == 0:
            issues.append("🟡 初始化→搜索断裂：用户跳转后未搜索，可能是落地页体验问题")
        if m.clicks > 0 and m.bookings == 0:
            issues.append("🟠 点击→预订为0：新站正常，但需关注转化路径优化")
        if m.revenue == 0 and m.bookings > 0:
            issues.append("🔴 有预订但无收入：可能是佣金结算延迟或数据问题")

        if issues:
            print(f"\n  ⚠️ 漏斗问题诊断:")
            for issue in issues:
                print(f"    {issue}")
        else:
            print(f"\n  ✅ 漏斗健康，无明显断裂")

        return {
            "funnel": funnel,
            "issues": issues,
            "overall_health": "good" if len(issues) == 0 else "warning"
        }

    # ==================== 3. 分产品深度分析 ====================

    def analyze_by_product(self) -> List[ProductMetrics]:
        """按产品维度分析"""
        print("\n" + "=" * 60)
        print("  收入分析引擎 - 分产品分析")
        print("=" * 60)

        # 由于Travelpayouts API的分产品数据可能需要不同的查询，
        # 这里先基于已知的联盟链接覆盖情况进行估算
        # 实际API支持时可以替换为真实数据

        products = [
            ProductMetrics(product_type="hotel", clicks=0, bookings=0, revenue=0.0),
            ProductMetrics(product_type="flight", clicks=0, bookings=0, revenue=0.0),
            ProductMetrics(product_type="insurance", clicks=0, bookings=0, revenue=0.0),
            ProductMetrics(product_type="esim", clicks=0, bookings=0, revenue=0.0),
            ProductMetrics(product_type="tour", clicks=0, bookings=0, revenue=0.0),
            ProductMetrics(product_type="transfer", clicks=0, bookings=0, revenue=0.0),
        ]

        # 尝试从API获取分产品数据
        if TRAVELPAYOUTS_API_TOKEN and self.current_metrics:
            total_clicks = self.current_metrics.clicks

            # 基于内容覆盖度估算点击分布（实际应从API获取）
            # 酒店类链接覆盖最广，估算占比最高
            estimated_distribution = {
                "hotel": 0.40,      # 酒店 40%
                "flight": 0.25,     # 机票 25%
                "tour": 0.15,       # 当地游 15%
                "transfer": 0.10,   # 接送机 10%
                "insurance": 0.05,  # 保险 5%
                "esim": 0.05,       # eSIM 5%
            }

            for product in products:
                share = estimated_distribution.get(product.product_type, 0)
                product.clicks = int(total_clicks * share)
                product.share_of_clicks = share * 100
                product.trend = "new" if total_clicks < 50 else "stable"

                # 计算转化率（基于行业基准，新站通常为0）
                product.conversion_rate = 0.0  # 实际数据
                product.revenue = 0.0
                product.revenue_per_click = 0.0

        self.product_metrics = products

        print(f"\n  📊 分产品点击分布 (估算，基于内容覆盖度):")
        print(f"  {'产品':<15} {'点击':>8} {'占比':>8} {'预订':>8} {'收入':>10}")
        print(f"  {'-'*55}")
        for p in sorted(products, key=lambda x: x.clicks, reverse=True):
            print(f"  {p.product_type:<15} {p.clicks:>8} {p.share_of_clicks:>7.1f}% {p.bookings:>8} ${p.revenue:>9.2f}")

        print(f"\n  ⚠️ 注意: 分产品数据为估算值，API完整支持后将替换为真实数据")
        print(f"  💡 建议: 在Travelpayouts后台查看分产品报表，验证估算准确性")

        return products

    # ==================== 4. 分渠道深度分析 ====================

    def analyze_by_channel(self) -> List[ChannelMetrics]:
        """按渠道维度分析"""
        print("\n" + "=" * 60)
        print("  收入分析引擎 - 分渠道分析")
        print("=" * 60)

        # 基于GA4数据和CTA库存分析渠道表现
        channels = []

        # 1. 按页面类型分析
        page_types = [
            ("指南文章 (Guide Posts)", "article", 0.50),
            ("资源页面 (Resources)", "page", 0.20),
            ("城市页面 (City Pages)", "page", 0.15),
            ("首页 (Homepage)", "page", 0.10),
            ("其他页面 (Other)", "page", 0.05),
        ]

        if self.current_metrics:
            total_clicks = self.current_metrics.clicks

            for name, ctype, share in page_types:
                channel = ChannelMetrics(
                    channel_name=name,
                    channel_type=ctype,
                    clicks=int(total_clicks * share),
                    bookings=0,
                    revenue=0.0,
                    share_of_clicks=share * 100,
                    share_of_revenue=0.0,
                    conversion_rate=0.0,
                    revenue_per_click=0.0
                )
                channels.append(channel)

        self.channel_metrics = channels

        print(f"\n  📊 分渠道点击分布 (估算):")
        print(f"  {'渠道':<25} {'类型':<10} {'点击':>8} {'占比':>8}")
        print(f"  {'-'*55}")
        for c in sorted(channels, key=lambda x: x.clicks, reverse=True):
            print(f"  {c.channel_name:<25} {c.channel_type:<10} {c.clicks:>8} {c.share_of_clicks:>7.1f}%")

        print(f"\n  💡 优化建议:")
        print(f"    1. 指南文章贡献50%点击，应重点优化这类文章的CTA位置和文案")
        print(f"    2. 资源页面和城市页面有提升空间，可增加联盟链接覆盖")
        print(f"    3. 首页CTA点击率偏低，建议优化首屏转化区块")

        return channels

    # ==================== 5. 趋势预测与预警 ====================

    def analyze_trends(self) -> Dict[str, Any]:
        """分析收入趋势并预警"""
        print("\n" + "=" * 60)
        print("  收入分析引擎 - 趋势分析与预警")
        print("=" * 60)

        if len(self.historical_metrics) < 2:
            print(f"  ⚠️ 历史数据不足 ({len(self.historical_metrics)}个快照)，至少需要2个进行趋势分析")
            print(f"  💡 建议: 每周运行一次，积累4-8周数据后进行趋势分析")
            return {"status": "insufficient_data"}

        # 计算周环比
        current = self.historical_metrics[-1]
        previous = self.historical_metrics[-2]

        trends = {
            "clicks_change": self._calc_change(current.clicks, previous.clicks),
            "bookings_change": self._calc_change(current.bookings, previous.bookings),
            "revenue_change": self._calc_change(current.revenue, previous.revenue),
            "conversion_rate_change": self._calc_change(current.conversion_rate, previous.conversion_rate),
        }

        print(f"\n  📊 周环比变化:")
        print(f"    点击: {previous.clicks} → {current.clicks} ({trends['clicks_change']['pct']:+.1f}%)")
        print(f"    预订: {previous.bookings} → {current.bookings} ({trends['bookings_change']['pct']:+.1f}%)")
        print(f"    收入: ${previous.revenue:.2f} → ${current.revenue:.2f} ({trends['revenue_change']['pct']:+.1f}%)")

        # 预警检测
        alerts = []
        if trends["clicks_change"]["pct"] < -30:
            alerts.append(f"🔴 点击量大幅下降 ({trends['clicks_change']['pct']:.1f}%)，需检查联盟链接和追踪")
        if trends["clicks_change"]["pct"] > 50:
            alerts.append(f"🟢 点击量大幅增长 ({trends['clicks_change']['pct']:.1f}%)，分析增长原因并复用")
        if current.clicks > 50 and current.bookings == 0:
            alerts.append(f"🟡 有{current.clicks}次点击但0预订，转化率为0，需优化转化路径")
        if current.data_quality == "error":
            alerts.append(f"🔴 数据质量错误: {', '.join(current.notes)}")

        if alerts:
            print(f"\n  ⚠️ 预警:")
            for alert in alerts:
                print(f"    {alert}")
        else:
            print(f"\n  ✅ 无预警，指标正常")

        return {
            "trends": trends,
            "alerts": alerts,
            "status": "healthy" if len(alerts) == 0 else "warning"
        }

    def _calc_change(self, current: float, previous: float) -> Dict[str, float]:
        """计算变化率"""
        if previous == 0:
            return {"absolute": current, "pct": 100.0 if current > 0 else 0.0}
        pct = ((current - previous) / previous) * 100
        return {"absolute": current - previous, "pct": pct}

    # ==================== 6. ROI分析与优化建议 ====================

    def generate_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """生成收入优化建议"""
        print("\n" + "=" * 60)
        print("  收入分析引擎 - 优化建议")
        print("=" * 60)

        recommendations = []

        if not self.current_metrics:
            print("  ⚠️ 请先调用fetch_revenue_data()")
        # P1-AI-OPS-03: Strategy-informed recommendations
        if getattr(self, "strategy", None) and self.strategy.available:
            best_products = self.strategy.get_priority_list("best_products")
            high_commission = self.strategy.get_priority_list("high_commission_products")
            best_channels = self.strategy.get_priority_list("best_channels")
            if best_products:
                recommendations.append({
                    "priority": "medium",
                    "category": "strategy",
                    "title": f"策略驱动：优先推广高转化产品（{', '.join(best_products[:3])}）",
                    "description": f"基于Learning闭环分析，以下产品历史表现最优：{', '.join(best_products[:5])}。建议在内容和社媒中优先推荐。",
                    "expected_impact": "提升产品匹配度和转化率",
                    "actions": [f"在新文章中优先推荐: {p}" for p in best_products[:3]],
                    "strategy_version": self.strategy.version,
                })
            if high_commission:
                recommendations.append({
                    "priority": "medium",
                    "category": "strategy",
                    "title": f"策略驱动：高佣金产品聚焦（{', '.join(high_commission[:3])}）",
                    "description": f"以下产品佣金率最高，适合作为重点推广对象：{', '.join(high_commission[:5])}",
                    "expected_impact": "单次预订佣金收入提升",
                    "actions": [f"增加高佣金产品曝光: {p}" for p in high_commission[:2]],
                    "strategy_version": self.strategy.version,
                })
            print(f"  📋 策略已消费: version={self.strategy.version}, best_products={len(best_products)}, high_commission={len(high_commission)}")


            return recommendations

        m = self.current_metrics

        # 基于数据生成建议
        if m.clicks > 0 and m.bookings == 0:
            recommendations.append({
                "priority": "high",
                "category": "conversion",
                "title": "优化转化路径：点击→预订断裂",
                "description": f"有{m.clicks}次点击但0预订。需检查：1)联盟链接是否正确跳转 2)落地页加载速度 3)CTA文案与目标页面匹配度",
                "expected_impact": "转化率提升至1-3%，每月增加1-3个预订",
                "actions": [
                    "抽查5个高点击页面的联盟链接是否正常工作",
                    "A/B测试CTA文案（'Book Now' vs 'Check Prices' vs 'See Deals'）",
                    "在高流量文章中部增加第二个CTA",
                    "确保所有联盟链接带正确的UTM参数和marker"
                ]
            })

        if m.clicks > 0 and m.revenue == 0:
            recommendations.append({
                "priority": "high",
                "category": "revenue",
                "title": "收入为0诊断与突破",
                "description": "点击量正常但收入为0。可能原因：1)新站正常（用户还在研究阶段）2)佣金结算延迟 3)产品匹配度低",
                "expected_impact": "建立收入基线，首个订单突破",
                "actions": [
                    "在Travelpayouts后台确认点击是否被正确追踪",
                    "检查佣金结算周期（酒店通常是入住后结算）",
                    "优先推广高转化产品（酒店、接送机）",
                    "在出行旺季前加大内容推广力度"
                ]
            })

        if m.clicks < 50:
            recommendations.append({
                "priority": "medium",
                "category": "traffic",
                "title": "提升联盟链接点击量",
                "description": f"当前{m.days}天仅{m.clicks}次点击，基数较小。需提升：1)联盟链接覆盖率 2)CTA可见性 3)高流量页面的转化区块",
                "expected_impact": "点击量提升50-100%",
                "actions": [
                    "确保所有攻略文章都有至少2个联盟CTA",
                    "在文章末尾添加'旅行工具推荐'区块",
                    "优化高流量页面（首页、热门文章）的首屏CTA",
                    "在相关文章之间增加交叉推荐"
                ]
            })

        if m.inits == 0 and m.clicks > 0:
            recommendations.append({
                "priority": "high",
                "category": "tracking",
                "title": "修复点击→初始化追踪断裂",
                "description": "有点击但inits=0，可能是：1)Travelpayouts Drive未正确加载 2)跳转追踪代码缺失 3)API数据字段映射问题",
                "expected_impact": "完整的转化漏斗数据，准确的归因分析",
                "actions": [
                    "验证Travelpayouts Drive脚本是否在所有页面正确加载",
                    "检查联盟链接是否包含正确的marker参数",
                    "在GA4中配置联盟点击事件追踪",
                    "对比Travelpayouts后台数据与API数据是否一致"
                ]
            })

        # 通用建议
        recommendations.append({
            "priority": "low",
            "category": "strategy",
            "title": "建立收入数据监控闭环",
            "description": "将收入数据纳入日报/周报/月报，建立持续监控机制。设置关键指标预警阈值。",
            "expected_impact": "及时发现问题，数据驱动决策",
            "actions": [
                "在日报中显示真实的联盟点击和收入数据",
                "设置周环比预警（点击下降>30%触发告警）",
                "每月进行收入深度分析，生成优化报告",
                "建立A/B测试机制，持续优化CTA和转化路径"
            ]
        })

        print(f"\n  📊 生成 {len(recommendations)} 条优化建议:")
        for i, rec in enumerate(recommendations, 1):
            priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(rec["priority"], "⚪")
            print(f"\n  {i}. {priority_icon} [{rec['priority'].upper()}] {rec['title']}")
            print(f"     类别: {rec['category']}")
            print(f"     描述: {rec['description'][:100]}...")
            print(f"     预期影响: {rec['expected_impact']}")

        return recommendations

    # ==================== 7. 生成完整分析报告 ====================

    def generate_full_report(self) -> str:
        """生成完整的收入分析报告"""
        print("\n" + "=" * 60)
        print("  收入分析引擎 - 生成完整报告")
        print("=" * 60)

        if not self.current_metrics:
            print("  ⚠️ 请先调用fetch_revenue_data()")
            return ""

        m = self.current_metrics
        now = datetime.now()

        report = f"""# ChinaBound Travel 收入数据分析报告

**生成时间**: {now.strftime('%Y-%m-%d %H:%M:%S')}
**统计周期**: {m.period_start} ~ {m.period_end} ({m.days}天)
**数据来源**: {m.data_source}
**数据质量**: {m.data_quality}

---

## 📊 核心指标概览

| 指标 | 数值 | 说明 |
|------|------|------|
| 联盟点击量 | **{m.clicks}** 次 | 用户点击联盟链接的次数 |
| 初始化 (Inits) | {m.inits} 次 | 成功跳转到合作伙伴页面的次数 |
| 搜索量 | {m.searches} 次 | 用户在合作伙伴页面的搜索次数 |
| 预订量 | {m.bookings} 单 | 成功预订的订单数 |
| 佣金收入 | **${m.revenue:.2f}** | 已结算的佣金收入 |
| 点击率 (CTR) | {m.click_through_rate:.2f}% | 展示→点击转化率 |
| 预订转化率 | {m.booking_rate:.2f}% | 点击→预订转化率 |
| 每次点击收入 | ${m.revenue_per_click:.4f} | 平均每次点击带来的收入 |
| 平均订单价值 | ${m.avg_order_value:.2f} | 平均每笔订单的佣金 |

---

## 🔄 转化漏斗分析

```
展示 (Impressions): {m.impressions:,}
    ↓ {m.click_through_rate:.1f}%
点击 (Clicks): {m.clicks:,}
    ↓ {m.init_rate:.1f}%
初始化 (Inits): {m.inits:,}
    ↓ {((m.searches/m.inits)*100) if m.inits > 0 else 0:.1f}%
搜索 (Searches): {m.searches:,}
    ↓ {m.booking_rate:.1f}%
预订 (Bookings): {m.bookings:,}
    ↓
收入 (Revenue): ${m.revenue:.2f}
```

### 漏斗诊断
"""

        # 添加漏斗问题
        funnel_analysis = self.analyze_funnel()
        if funnel_analysis.get("issues"):
            report += "**发现的问题:**\n\n"
            for issue in funnel_analysis["issues"]:
                report += f"- {issue}\n"
        else:
            report += "✅ 漏斗健康，无明显断裂\n"

        report += f"""
---

## 📦 分产品分析

| 产品类型 | 点击量 | 占比 | 预订量 | 收入 | 转化率 |
|----------|--------|------|--------|------|--------|
"""

        for p in sorted(self.product_metrics, key=lambda x: x.clicks, reverse=True):
            report += f"| {p.product_type} | {p.clicks} | {p.share_of_clicks:.1f}% | {p.bookings} | ${p.revenue:.2f} | {p.conversion_rate:.2f}% |\n"

        report += """
> ⚠️ 分产品数据为估算值，基于内容覆盖度分布。API完整支持后将替换为真实数据。

---

## 📈 分渠道分析

| 渠道 | 类型 | 点击量 | 占比 | 预订量 | 收入 |
|------|------|--------|------|--------|------|
"""

        for c in sorted(self.channel_metrics, key=lambda x: x.clicks, reverse=True):
            report += f"| {c.channel_name} | {c.channel_type} | {c.clicks} | {c.share_of_clicks:.1f}% | {c.bookings} | ${c.revenue:.2f} |\n"

        # 趋势分析
        trend_analysis = self.analyze_trends()
        if trend_analysis.get("trends"):
            t = trend_analysis["trends"]
            report += f"""
---

## 📊 趋势分析（周环比）

| 指标 | 上周 | 本周 | 变化 |
|------|------|------|------|
| 点击量 | - | {m.clicks} | {t['clicks_change']['pct']:+.1f}% |
| 预订量 | - | {m.bookings} | {t['bookings_change']['pct']:+.1f}% |
| 收入 | - | ${m.revenue:.2f} | {t['revenue_change']['pct']:+.1f}% |

> 💡 积累4-8周数据后可进行更准确的趋势分析
"""

        if trend_analysis.get("alerts"):
            report += "\n### ⚠️ 预警\n\n"
            for alert in trend_analysis["alerts"]:
                report += f"- {alert}\n"

        # 优化建议
        recommendations = self.generate_optimization_recommendations()
        report += """
---

## 🎯 优化建议

"""

        for i, rec in enumerate(recommendations, 1):
            priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(rec["priority"], "⚪")
            report += f"""### {i}. {priority_icon} [{rec['priority'].upper()}] {rec['title']}

**类别**: {rec['category']}
**预期影响**: {rec['expected_impact']}

**描述**: {rec['description']}

**具体行动**:
"""
            for action in rec["actions"]:
                report += f"- {action}\n"
            report += "\n"

        report += f"""
---

## 📋 数据质量说明

- **数据来源**: Travelpayouts Statistics API (实时调用)
- **API状态**: {'✅ 正常' if m.data_quality == 'good' else '⚠️ ' + m.data_quality}
- **数据延迟**: 收入数据通常有30-90天结算延迟
- **分产品数据**: 估算值，待API完整支持
- **分渠道数据**: 基于内容覆盖度估算

---

*报告由收入分析引擎自动生成 | {now.strftime('%Y-%m-%d %H:%M:%S')}*
*引擎版本: v1.0 | 成熟度目标: L2 → L3*
"""

        # 保存报告
        with open(REVENUE_REPORT_FILE, "w", encoding="utf-8") as f:
            f.write(report)

        # 保存快照
        snapshot = {
            "generated_at": now.isoformat(),
            "period": {"start": m.period_start, "end": m.period_end, "days": m.days},
            "metrics": asdict(m),
            "products": [asdict(p) for p in self.product_metrics],
            "channels": [asdict(c) for c in self.channel_metrics],
            "recommendations_count": len(recommendations)
        }

        with open(REVENUE_SNAPSHOT_FILE, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)

        print(f"\n  ✅ 报告已生成: {REVENUE_REPORT_FILE}")
        print(f"  ✅ 快照已保存: {REVENUE_SNAPSHOT_FILE}")
        print(f"  📊 报告长度: {len(report)} 字符")

        return report

    # ==================== 8. 完整分析流程 ====================

    def run_full_analysis(self, days: int = 28):
        """运行完整的收入分析流程"""
        print("\n" + "=" * 60)
        print("  ChinaBound Travel - 收入数据闭环与深度分析引擎")
        print("  完整分析流程")
        print("=" * 60)

        print(f"\n📅 运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 分析周期: 最近 {days} 天")

        # Step 1: 数据采集
        self.fetch_revenue_data(days=days)

        # Step 2: 转化漏斗分析
        self.analyze_funnel()

        # Step 3: 分产品分析
        self.analyze_by_product()

        # Step 4: 分渠道分析
        self.analyze_by_channel()

        # Step 5: 趋势分析
        self.analyze_trends()

        # Step 6: 优化建议
        self.generate_optimization_recommendations()

        # Step 7: 生成报告
        self.generate_full_report()

        print("\n" + "=" * 60)
        print("  ✅ 完整收入分析流程完成！")
        print("=" * 60)
        print(f"\n📁 报告目录: {REVENUE_DIR}")
        print(f"📄 分析报告: {REVENUE_REPORT_FILE}")
        print(f"💾 数据快照: {REVENUE_SNAPSHOT_FILE}")
        print(f"📜 历史数据: {REVENUE_HISTORY_FILE}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="ChinaBound Travel 收入数据闭环与深度分析引擎")
    parser.add_argument("--all", action="store_true", help="运行完整分析流程")
    parser.add_argument("--fetch", action="store_true", help="仅采集收入数据")
    parser.add_argument("--funnel", action="store_true", help="仅分析转化漏斗")
    parser.add_argument("--products", action="store_true", help="仅分产品分析")
    parser.add_argument("--channels", action="store_true", help="仅分渠道分析")
    parser.add_argument("--trends", action="store_true", help="仅趋势分析")
    parser.add_argument("--report", action="store_true", help="仅生成报告")
    parser.add_argument("--days", type=int, default=28, help="分析天数（默认28）")

    args = parser.parse_args()

    engine = RevenueAnalyticsEngine()

    if args.all or not any([args.fetch, args.funnel, args.products,
                            args.channels, args.trends, args.report]):
        engine.run_full_analysis(days=args.days)
    elif args.fetch:
        engine.fetch_revenue_data(days=args.days)
    elif args.funnel:
        engine.fetch_revenue_data(days=args.days)
        engine.analyze_funnel()
    elif args.products:
        engine.fetch_revenue_data(days=args.days)
        engine.analyze_by_product()
    elif args.channels:
        engine.fetch_revenue_data(days=args.days)
        engine.analyze_by_channel()
    elif args.trends:
        engine.analyze_trends()
    elif args.report:
        engine.fetch_revenue_data(days=args.days)
        engine.analyze_by_product()
        engine.analyze_by_channel()
        engine.generate_full_report()


if __name__ == "__main__":
    main()
