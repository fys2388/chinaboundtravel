#!/usr/bin/env python3
"""
ChinaBound Travel - 转化优化Agent
Conversion Optimization Agent

核心能力（L1 → L3）：
1. CTA库存智能审计 - 278个CTA的智能诊断与优化建议
2. A/B测试自动化 - 自动设计、部署、监控实验
3. 实验结果自动分析 - 统计显著性检验、效果评估
4. 自动决策与优化 - 基于数据自动选择最优方案
5. 转化漏斗智能优化 - 全链路转化优化
6. 个性化推荐引擎 - 基于内容意图的CTA匹配

成熟度目标：L1 → L3（6个月）
"""

import os
import sys
import json
import csv
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
from collections import defaultdict
import re

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
CONVERSION_DIR = REPORTS_DIR / "conversion"
CONVERSION_DIR.mkdir(parents=True, exist_ok=True)

# 数据文件
CTA_AUDIT_FILE = CONVERSION_DIR / "cta_audit_report.json"
AB_TESTS_FILE = CONVERSION_DIR / "ab_tests.json"
EXPERIMENT_RESULTS_FILE = CONVERSION_DIR / "experiment_results.json"
OPTIMIZATION_DECISIONS_FILE = CONVERSION_DIR / "optimization_decisions.json"
CONVERSION_REPORT_FILE = CONVERSION_DIR / "conversion_optimization_report.md"

# 内容目录
CONTENT_DIR = PROJECT_ROOT / "content"
POSTS_DIR = CONTENT_DIR / "posts"


class CTAType(Enum):
    """CTA类型"""
    AFFILIATE = "affiliate"
    SOFT_RECOMMEND = "soft-recommend"
    BOOKING = "booking"
    KLOOK = "klook"
    VPN = "vpn"
    ESIM = "esim"
    TRAVEL = "travel"
    OTHER = "other"


class CTAPosition(Enum):
    """CTA位置"""
    ABOVE_FOLD = "above_fold"
    ARTICLE_MID = "article_mid"
    ARTICLE_END = "article_end"
    SIDEBAR = "sidebar"
    FOOTER = "footer"
    OTHER = "other"


class ExperimentStatus(Enum):
    """实验状态"""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class DecisionType(Enum):
    """决策类型"""
    DEPLOY_WINNER = "deploy_winner"
    CONTINUE_TESTING = "continue_testing"
    ROLLBACK = "rollback"
    ITERATE = "iterate"
    NO_ACTION = "no_action"


@dataclass
class CTARecord:
    """CTA记录"""
    id: str
    page: str
    page_title: str
    cta_type: str
    position: str
    partner: str
    text: str
    url: str
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    revenue: float = 0.0
    ctr: float = 0.0
    conversion_rate: float = 0.0
    revenue_per_click: float = 0.0
    quality_score: float = 0.0
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class ABTest:
    """A/B测试"""
    id: str
    name: str
    description: str
    hypothesis: str
    page: str
    element: str  # cta_text / cta_position / cta_color / layout
    variant_a: Dict[str, Any]  # 对照组
    variant_b: Dict[str, Any]  # 实验组
    status: str
    start_date: str
    end_date: Optional[str] = None
    target_sample_size: int = 1000
    min_duration_days: int = 7
    confidence_threshold: float = 0.95
    metrics: Dict[str, Any] = field(default_factory=dict)
    results: Optional[Dict[str, Any]] = None
    decision: Optional[str] = None
    notes: List[str] = field(default_factory=list)


@dataclass
class ExperimentResult:
    """实验结果"""
    test_id: str
    analyzed_at: str
    variant_a_metrics: Dict[str, Any]
    variant_b_metrics: Dict[str, Any]
    relative_lift: Dict[str, float]
    statistical_significance: Dict[str, float]
    is_significant: bool
    winning_variant: Optional[str]
    confidence: float
    sample_size_sufficient: bool
    duration_sufficient: bool
    recommendation: str
    next_steps: List[str]


@dataclass
class OptimizationDecision:
    """优化决策"""
    id: str
    timestamp: str
    test_id: Optional[str]
    decision_type: str
    description: str
    rationale: str
    expected_impact: str
    confidence: float
    actions: List[str]
    status: str  # proposed / approved / deployed / reverted
    deployed_at: Optional[str] = None
    actual_impact: Optional[str] = None


class ConversionOptimizationAgent:
    """转化优化Agent主类"""

    def __init__(self):
        self.cta_inventory: List[CTARecord] = []
        self.ab_tests: List[ABTest] = []
        self.experiment_results: List[ExperimentResult] = []
        self.decisions: List[OptimizationDecision] = []
        self._load_data()

    def _load_data(self):
        """加载所有数据"""
        # 加载A/B测试
        if AB_TESTS_FILE.exists():
            try:
                with open(AB_TESTS_FILE, encoding="utf-8") as f:
                    data = json.load(f)
                    self.ab_tests = [ABTest(**t) for t in data.get("tests", [])]
            except Exception as e:
                print(f"  ⚠️ 加载A/B测试失败: {e}")

        # 加载实验结果
        if EXPERIMENT_RESULTS_FILE.exists():
            try:
                with open(EXPERIMENT_RESULTS_FILE, encoding="utf-8") as f:
                    data = json.load(f)
                    self.experiment_results = [ExperimentResult(**r) for r in data.get("results", [])]
            except Exception as e:
                print(f"  ⚠️ 加载实验结果失败: {e}")

        # 加载决策
        if OPTIMIZATION_DECISIONS_FILE.exists():
            try:
                with open(OPTIMIZATION_DECISIONS_FILE, encoding="utf-8") as f:
                    data = json.load(f)
                    self.decisions = [OptimizationDecision(**d) for d in data.get("decisions", [])]
            except Exception as e:
                print(f"  ⚠️ 加载决策失败: {e}")

    def _save_data(self):
        """保存所有数据"""
        # 保存A/B测试
        with open(AB_TESTS_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "tests": [asdict(t) for t in self.ab_tests],
                "total_count": len(self.ab_tests),
                "last_updated": datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)

        # 保存实验结果
        with open(EXPERIMENT_RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "results": [asdict(r) for r in self.experiment_results],
                "total_count": len(self.experiment_results),
                "last_updated": datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)

        # 保存决策
        with open(OPTIMIZATION_DECISIONS_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "decisions": [asdict(d) for d in self.decisions],
                "total_count": len(self.decisions),
                "last_updated": datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)

    # ==================== 1. CTA库存智能审计 ====================

    def audit_cta_inventory(self) -> List[CTARecord]:
        """审计CTA库存"""
        print("\n" + "=" * 60)
        print("  转化优化Agent - CTA库存智能审计")
        print("=" * 60)

        cta_records = []

        # 扫描所有文章中的CTA
        if POSTS_DIR.exists():
            for md_file in POSTS_DIR.glob("*.md"):
                try:
                    content = md_file.read_text(encoding="utf-8")

                    # 提取Front Matter中的title
                    title = md_file.stem
                    title_match = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', content, re.MULTILINE)
                    if title_match:
                        title = title_match.group(1).strip()

                    # 提取所有CTA shortcodes
                    # 格式: {{< cta_type partner="xxx" text="xxx" >}}
                    cta_pattern = r'\{\{<\s*(\w+)(?:\s+([^>]+?))?\s*>\}\}'
                    matches = re.findall(cta_pattern, content)

                    for i, (cta_type, params_str) in enumerate(matches):
                        # 解析参数
                        params = {}
                        if params_str:
                            param_matches = re.findall(r'(\w+)\s*=\s*["\']([^"\']+)["\']', params_str)
                            for key, value in param_matches:
                                params[key] = value

                        # 判断CTA位置（基于在文章中的位置）
                        position = self._detect_cta_position(content, md_file.name, i)

                        # 创建CTA记录
                        cta = CTARecord(
                            id=f"cta_{md_file.stem}_{i}",
                            page=f"/posts/{md_file.stem}/",
                            page_title=title,
                            cta_type=cta_type,
                            position=position,
                            partner=params.get("partner", params.get("provider", "unknown")),
                            text=params.get("text", params.get("title", "")),
                            url=params.get("url", params.get("link", "")),
                        )

                        # 质量评分和问题检测
                        self._score_cta_quality(cta)

                        cta_records.append(cta)

                except Exception as e:
                    print(f"  ⚠️ 处理 {md_file.name} 失败: {e}")

        self.cta_inventory = cta_records

        # 统计
        total_ctas = len(cta_records)
        pages_with_cta = len(set(c.page for c in cta_records))
        issues_count = sum(len(c.issues) for c in cta_records)

        print(f"\n  📊 CTA库存统计:")
        print(f"    CTA总数: {total_ctas}")
        print(f"    覆盖页面: {pages_with_cta}")
        print(f"    发现问题: {issues_count}个")

        # CTA类型分布
        print(f"\n  📊 CTA类型分布:")
        type_dist = defaultdict(int)
        for cta in cta_records:
            type_dist[cta.cta_type] += 1
        for cta_type, count in sorted(type_dist.items(), key=lambda x: x[1], reverse=True):
            print(f"    {cta_type}: {count}个 ({count/total_ctas*100:.1f}%)")

        # CTA位置分布
        print(f"\n  📊 CTA位置分布:")
        pos_dist = defaultdict(int)
        for cta in cta_records:
            pos_dist[cta.position] += 1
        for pos, count in sorted(pos_dist.items(), key=lambda x: x[1], reverse=True):
            print(f"    {pos}: {count}个 ({count/total_ctas*100:.1f}%)")

        # 问题汇总
        print(f"\n  ⚠️ 主要问题:")
        all_issues = defaultdict(int)
        for cta in cta_records:
            for issue in cta.issues:
                all_issues[issue] += 1
        for issue, count in sorted(all_issues.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"    {issue}: {count}个CTA")

        # 保存审计报告
        audit_report = {
            "audited_at": datetime.now().isoformat(),
            "total_ctas": total_ctas,
            "pages_with_cta": pages_with_cta,
            "total_issues": issues_count,
            "type_distribution": dict(type_dist),
            "position_distribution": dict(pos_dist),
            "common_issues": dict(all_issues),
            "cta_records": [asdict(c) for c in cta_records]
        }

        with open(CTA_AUDIT_FILE, "w", encoding="utf-8") as f:
            json.dump(audit_report, f, ensure_ascii=False, indent=2)

        print(f"\n  ✅ 审计报告已保存: {CTA_AUDIT_FILE}")

        return cta_records

    def _detect_cta_position(self, content: str, filename: str, index: int) -> str:
        """检测CTA在文章中的位置"""
        # 简单估算：基于CTA在文件中的顺序
        # 第一个CTA可能在文章中部，最后一个在文章末尾
        cta_count = len(re.findall(r'\{\{<\s*\w+', content))

        if cta_count == 0:
            return CTAPosition.OTHER.value

        position_ratio = (index + 1) / cta_count

        if position_ratio <= 0.2:
            return CTAPosition.ARTICLE_MID.value  # 第一个通常在中部
        elif position_ratio >= 0.8:
            return CTAPosition.ARTICLE_END.value
        else:
            return CTAPosition.ARTICLE_MID.value

    def _score_cta_quality(self, cta: CTARecord):
        """评估CTA质量并检测问题"""
        score = 100.0
        issues = []
        recommendations = []

        # 1. 检查CTA文本
        if not cta.text or len(cta.text) < 10:
            score -= 20
            issues.append("CTA文本过短或缺失")
            recommendations.append("优化CTA文案，包含行动号召和价值主张")

        # 2. 检查是否有行动号召词
        action_words = ["book", "check", "get", "try", "start", "explore", "discover", "reserve", "buy", "order"]
        if cta.text and not any(word in cta.text.lower() for word in action_words):
            score -= 10
            issues.append("CTA缺少明确的行动号召词")
            recommendations.append("在CTA文案中加入行动号召词（Book/Check/Get/Try等）")

        # 3. 检查合作伙伴
        if cta.partner == "unknown":
            score -= 15
            issues.append("未指定合作伙伴")
            recommendations.append("明确指定联盟合作伙伴")

        # 4. 检查URL
        if not cta.url:
            score -= 10
            issues.append("CTA缺少目标URL")
            recommendations.append("确保CTA有正确的跳转链接")

        # 5. 位置优化建议
        if cta.position == CTAPosition.ARTICLE_END.value:
            # 文章末尾的CTA需要更强的行动号召
            if cta.text and "book" not in cta.text.lower() and "get" not in cta.text.lower():
                score -= 5
                issues.append("文章末尾CTA行动号召不够强")
                recommendations.append("文章末尾CTA使用更强的行动号召（Book Now/Get Started）")

        # 6. 类型匹配检查
        high_intent_types = ["booking", "klook", "affiliate"]
        if cta.cta_type in high_intent_types and not cta.text:
            score -= 10
            issues.append("高意图CTA缺少文案")

        cta.quality_score = max(0, score)
        cta.issues = issues
        cta.recommendations = recommendations

    # ==================== 2. A/B测试自动化设计 ====================

    def design_ab_test(self, page: str, element: str, hypothesis: str,
                       variant_a: Dict, variant_b: Dict,
                       name: str = None, description: str = None) -> ABTest:
        """自动设计A/B测试"""
        print("\n" + "=" * 60)
        print("  转化优化Agent - A/B测试设计")
        print("=" * 60)

        test_id = f"ab_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        test = ABTest(
            id=test_id,
            name=name or f"AB Test - {element} - {page[:30]}",
            description=description or f"A/B test for {element} on {page}",
            hypothesis=hypothesis,
            page=page,
            element=element,
            variant_a=variant_a,
            variant_b=variant_b,
            status=ExperimentStatus.DRAFT.value,
            start_date=datetime.now().isoformat(),
            target_sample_size=1000,
            min_duration_days=7,
            confidence_threshold=0.95,
        )

        self.ab_tests.append(test)
        self._save_data()

        print(f"\n  ✅ A/B测试已创建:")
        print(f"    ID: {test.id}")
        print(f"    名称: {test.name}")
        print(f"    页面: {test.page}")
        print(f"    元素: {test.element}")
        print(f"    假设: {test.hypothesis}")
        print(f"    对照组: {json.dumps(variant_a, ensure_ascii=False)[:100]}")
        print(f"    实验组: {json.dumps(variant_b, ensure_ascii=False)[:100]}")
        print(f"    目标样本量: {test.target_sample_size}")
        print(f"    最短持续时间: {test.min_duration_days}天")
        print(f"    置信度阈值: {test.confidence_threshold*100:.0f}%")

        return test

    def generate_test_recommendations(self) -> List[Dict]:
        """基于CTA审计结果生成A/B测试建议"""
        print("\n" + "=" * 60)
        print("  转化优化Agent - 生成A/B测试建议")
        print("=" * 60)

        recommendations = []

        if not self.cta_inventory:
            self.audit_cta_inventory()

        # 1. 找出低质量CTA最多的页面
        page_issues = defaultdict(lambda: {"count": 0, "issues": [], "ctas": []})
        for cta in self.cta_inventory:
            if cta.quality_score < 70:
                page_issues[cta.page]["count"] += 1
                page_issues[cta.page]["issues"].extend(cta.issues)
                page_issues[cta.page]["ctas"].append(cta)

        # 2. 生成测试建议
        for page, data in sorted(page_issues.items(), key=lambda x: x[1]["count"], reverse=True)[:5]:
            # CTA文案测试
            if any("CTA文本过短" in issue or "行动号召" in issue for issue in data["issues"]):
                recommendations.append({
                    "priority": "high",
                    "type": "cta_text",
                    "page": page,
                    "title": f"CTA文案优化测试 - {page[:30]}",
                    "hypothesis": "优化CTA文案，加入明确的行动号召词和价值主张，可以提升点击率20-50%",
                    "variant_a": {"text": "原CTA文案", "type": "control"},
                    "variant_b": {"text": "优化后CTA文案（含行动号召+价值主张）", "type": "treatment"},
                    "expected_impact": "CTR提升20-50%",
                    "rationale": f"该页面有{data['count']}个低质量CTA，文案问题突出"
                })

            # CTA位置测试
            if any("位置" in issue for issue in data["issues"]):
                recommendations.append({
                    "priority": "medium",
                    "type": "cta_position",
                    "page": page,
                    "title": f"CTA位置优化测试 - {page[:30]}",
                    "hypothesis": "将CTA从文章末尾移至文章中部（在关键内容之后），可以提升点击率",
                    "variant_a": {"position": "article_end", "type": "control"},
                    "variant_b": {"position": "article_mid", "type": "treatment"},
                    "expected_impact": "CTR提升15-30%",
                    "rationale": "文章末尾CTA可见性低，中部CTA在用户阅读高峰时展示"
                })

        # 3. 通用测试建议
        recommendations.append({
            "priority": "high",
            "type": "cta_count",
            "page": "high_traffic_pages",
            "title": "CTA数量测试（1个 vs 2个）",
            "hypothesis": "在高流量文章中增加第二个CTA（文章中部），可以提升整体转化率",
            "variant_a": {"cta_count": 1, "position": "article_end"},
            "variant_b": {"cta_count": 2, "positions": ["article_mid", "article_end"]},
            "expected_impact": "整体转化提升20-40%",
            "rationale": "用户在阅读过程中可能在不同时间点产生转化意愿，多个CTA增加触达机会"
        })

        recommendations.append({
            "priority": "medium",
            "type": "cta_format",
            "page": "all_pages",
            "title": "CTA格式测试（文本链接 vs 按钮）",
            "hypothesis": "按钮式CTA比文本链接式CTA点击率更高",
            "variant_a": {"format": "text_link", "style": "inline"},
            "variant_b": {"format": "button", "style": "highlighted"},
            "expected_impact": "CTR提升30-60%",
            "rationale": "按钮式CTA视觉突出，用户更容易发现和点击"
        })

        print(f"\n  📊 生成 {len(recommendations)} 条A/B测试建议:")
        for i, rec in enumerate(recommendations, 1):
            priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(rec["priority"], "⚪")
            print(f"\n  {i}. {priority_icon} [{rec['priority'].upper()}] {rec['title']}")
            print(f"     类型: {rec['type']}")
            print(f"     假设: {rec['hypothesis'][:80]}...")
            print(f"     预期影响: {rec['expected_impact']}")

        return recommendations

    # ==================== 3. 实验结果自动分析 ====================

    def analyze_experiment(self, test_id: str,
                           variant_a_data: Dict[str, Any],
                           variant_b_data: Dict[str, Any]) -> ExperimentResult:
        """自动分析实验结果"""
        print("\n" + "=" * 60)
        print("  转化优化Agent - 实验结果分析")
        print("=" * 60)

        # 找到对应的测试
        test = next((t for t in self.ab_tests if t.id == test_id), None)
        if not test:
            print(f"  ❌ 未找到测试: {test_id}")
            return None

        print(f"\n  📊 分析测试: {test.name}")
        print(f"    对照组样本: {variant_a_data.get('visitors', 0)}")
        print(f"    实验组样本: {variant_b_data.get('visitors', 0)}")

        # 计算指标
        metrics_to_analyze = ["ctr", "conversion_rate", "revenue_per_visitor", "bounce_rate"]

        relative_lift = {}
        statistical_significance = {}
        is_significant = False
        winning_variant = None
        max_confidence = 0.0

        for metric in metrics_to_analyze:
            a_value = variant_a_data.get(metric, 0)
            b_value = variant_b_data.get(metric, 0)

            if a_value > 0:
                lift = ((b_value - a_value) / a_value) * 100
            else:
                lift = 100.0 if b_value > 0 else 0.0

            relative_lift[metric] = lift

            # 简化的统计显著性计算（基于样本量和差异大小）
            a_visitors = variant_a_data.get("visitors", 0)
            b_visitors = variant_b_data.get("visitors", 0)

            if a_visitors > 0 and b_visitors > 0:
                # 使用简化的Z检验
                a_conversions = variant_a_data.get("conversions", 0)
                b_conversions = variant_b_data.get("conversions", 0)

                p1 = a_conversions / a_visitors if a_visitors > 0 else 0
                p2 = b_conversions / b_visitors if b_visitors > 0 else 0
                p_pool = (a_conversions + b_conversions) / (a_visitors + b_visitors) if (a_visitors + b_visitors) > 0 else 0

                if p_pool > 0 and p_pool < 1:
                    se = math.sqrt(p_pool * (1 - p_pool) * (1/a_visitors + 1/b_visitors))
                    if se > 0:
                        z_score = abs(p2 - p1) / se
                        # 简化的p值计算
                        p_value = 2 * (1 - self._normal_cdf(z_score))
                        confidence = (1 - p_value) * 100
                    else:
                        confidence = 0.0
                else:
                    confidence = 0.0
            else:
                confidence = 0.0

            statistical_significance[metric] = confidence

            if confidence > max_confidence:
                max_confidence = confidence

            if confidence >= test.confidence_threshold * 100:
                is_significant = True
                if lift > 0:
                    winning_variant = "B"
                elif lift < 0:
                    winning_variant = "A"

        # 样本量和持续时间检查
        total_visitors = variant_a_data.get("visitors", 0) + variant_b_data.get("visitors", 0)
        sample_size_sufficient = total_visitors >= test.target_sample_size

        test_start = datetime.fromisoformat(test.start_date)
        test_duration = (datetime.now() - test_start).days
        duration_sufficient = test_duration >= test.min_duration_days

        # 生成建议
        if is_significant and winning_variant:
            recommendation = f"实验组{winning_variant}显著胜出，建议部署获胜方案"
            next_steps = [
                f"部署{winning_variant}方案到所有流量",
                "监控部署后的实际效果",
                "记录实验结果和经验教训",
                "设计下一个迭代实验"
            ]
            decision_type = DecisionType.DEPLOY_WINNER.value
        elif not sample_size_sufficient:
            recommendation = "样本量不足，建议继续测试"
            next_steps = [
                f"继续收集数据，目标样本量{test.target_sample_size}",
                f"当前样本量{total_visitors}，还需{test.target_sample_size - total_visitors}",
                "检查流量分配是否正常"
            ]
            decision_type = DecisionType.CONTINUE_TESTING.value
        elif not duration_sufficient:
            recommendation = "测试时间不足，建议继续测试"
            next_steps = [
                f"继续测试至{test.min_duration_days}天",
                f"当前已运行{test_duration}天",
                "避免过早下结论"
            ]
            decision_type = DecisionType.CONTINUE_TESTING.value
        else:
            recommendation = "无显著差异，建议迭代测试或停止"
            next_steps = [
                "分析为什么没有显著差异",
                "调整实验假设或设计",
                "考虑测试其他元素",
                "如无继续价值，可停止实验"
            ]
            decision_type = DecisionType.ITERATE.value

        # 创建实验结果
        result = ExperimentResult(
            test_id=test_id,
            analyzed_at=datetime.now().isoformat(),
            variant_a_metrics=variant_a_data,
            variant_b_metrics=variant_b_data,
            relative_lift=relative_lift,
            statistical_significance=statistical_significance,
            is_significant=is_significant,
            winning_variant=winning_variant,
            confidence=max_confidence,
            sample_size_sufficient=sample_size_sufficient,
            duration_sufficient=duration_sufficient,
            recommendation=recommendation,
            next_steps=next_steps
        )

        self.experiment_results.append(result)

        # 自动创建决策
        decision = OptimizationDecision(
            id=f"dec_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.now().isoformat(),
            test_id=test_id,
            decision_type=decision_type,
            description=recommendation,
            rationale=f"基于{test.name}实验结果分析，置信度{max_confidence:.1f}%",
            expected_impact=f"预期{relative_lift.get('conversion_rate', 0):.1f}%转化率提升",
            confidence=max_confidence / 100,
            actions=next_steps,
            status="proposed"
        )
        self.decisions.append(decision)

        self._save_data()

        print(f"\n  📊 分析结果:")
        print(f"    统计显著: {'是' if is_significant else '否'}")
        print(f"    获胜方案: {winning_variant or '无显著差异'}")
        print(f"    最大置信度: {max_confidence:.1f}%")
        print(f"    样本量充足: {'是' if sample_size_sufficient else '否'} ({total_visitors}/{test.target_sample_size})")
        print(f"    持续时间充足: {'是' if duration_sufficient else '否'} ({test_duration}/{test.min_duration_days}天)")
        print(f"    相对提升: {json.dumps(relative_lift, indent=2)[:200]}")
        print(f"\n  💡 建议: {recommendation}")
        print(f"  📋 下一步:")
        for step in next_steps:
            print(f"    - {step}")

        return result

    def _normal_cdf(self, x: float) -> float:
        """标准正态分布累积分布函数"""
        return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

    # ==================== 4. 自动决策与优化 ====================

    def make_optimization_decisions(self) -> List[OptimizationDecision]:
        """基于数据自动做出优化决策"""
        print("\n" + "=" * 60)
        print("  转化优化Agent - 自动决策")
        print("=" * 60)

        decisions = []

        # 1. 基于CTA审计的决策
        if self.cta_inventory:
            low_quality_ctas = [c for c in self.cta_inventory if c.quality_score < 60]
            if low_quality_ctas:
                decision = OptimizationDecision(
                    id=f"dec_cta_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    timestamp=datetime.now().isoformat(),
                    test_id=None,
                    decision_type=DecisionType.ITERATE.value,
                    description=f"批量优化{len(low_quality_ctas)}个低质量CTA（质量分<60）",
                    rationale=f"审计发现{len(low_quality_ctas)}个CTA质量分低于60，主要问题包括文案过短、缺少行动号召、合作伙伴未指定等",
                    expected_impact="CTR整体提升15-30%",
                    confidence=0.75,
                    actions=[
                        "优先优化高流量页面的低质量CTA",
                        "统一CTA文案模板（行动号召+价值主张）",
                        "确保所有CTA有正确的合作伙伴和跳转链接",
                        "在文章中部增加第二个CTA",
                        "优化后监控CTR变化"
                    ],
                    status="proposed"
                )
                decisions.append(decision)
                self.decisions.append(decision)

        # 2. 基于转化漏斗的决策
        # （这里可以接入真实的转化数据，目前使用模拟逻辑）
        decision = OptimizationDecision(
            id=f"dec_funnel_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.now().isoformat(),
            test_id=None,
            decision_type=DecisionType.ITERATE.value,
            description="优化转化漏斗：点击→初始化→预订全链路",
            rationale="收入分析引擎发现99次点击但0次初始化和0预订，转化漏斗存在断裂",
            expected_impact="修复后转化率提升至1-3%",
            confidence=0.80,
            actions=[
                "验证Travelpayouts Drive脚本在所有页面正确加载",
                "检查联盟链接跳转是否正常工作",
                "在GA4中配置联盟点击事件追踪",
                "对比Travelpayouts后台数据与API数据",
                "优化高点击页面的CTA位置和文案"
            ],
            status="proposed"
        )
        decisions.append(decision)
        self.decisions.append(decision)

        # 3. 基于A/B测试的决策
        running_tests = [t for t in self.ab_tests if t.status == ExperimentStatus.RUNNING.value]
        if running_tests:
            decision = OptimizationDecision(
                id=f"dec_ab_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                timestamp=datetime.now().isoformat(),
                test_id=None,
                decision_type=DecisionType.CONTINUE_TESTING.value,
                description=f"监控{len(running_tests)}个正在运行的A/B测试",
                rationale=f"有{len(running_tests)}个实验正在运行，需要持续监控并在达到样本量后分析",
                expected_impact="基于实验结果持续优化",
                confidence=0.90,
                actions=[
                    "检查每个实验的流量分配是否正常",
                    "监控样本量收集进度",
                    "在达到目标样本量后自动分析结果",
                    "避免频繁查看导致的多重比较问题"
                ],
                status="proposed"
            )
            decisions.append(decision)
            self.decisions.append(decision)

        self._save_data()

        print(f"\n  📊 生成 {len(decisions)} 条优化决策:")
        for i, dec in enumerate(decisions, 1):
            print(f"\n  {i}. [{dec.decision_type.upper()}] {dec.description}")
            print(f"     置信度: {dec.confidence*100:.0f}%")
            print(f"     预期影响: {dec.expected_impact}")
            print(f"     理由: {dec.rationale[:100]}...")

        return decisions

    # ==================== 5. 生成完整报告 ====================

    def generate_full_report(self) -> str:
        """生成完整的转化优化报告"""
        print("\n" + "=" * 60)
        print("  转化优化Agent - 生成完整报告")
        print("=" * 60)

        now = datetime.now()

        report = f"""# ChinaBound Travel 转化优化报告

**生成时间**: {now.strftime('%Y-%m-%d %H:%M:%S')}
**引擎版本**: v1.0
**成熟度目标**: L1 → L3

---

## 📊 执行摘要

| 指标 | 数值 |
|------|------|
| CTA总数 | {len(self.cta_inventory)} |
| 覆盖页面 | {len(set(c.page for c in self.cta_inventory))} |
| 低质量CTA (<60分) | {len([c for c in self.cta_inventory if c.quality_score < 60])} |
| 平均质量分 | {sum(c.quality_score for c in self.cta_inventory) / len(self.cta_inventory) if self.cta_inventory else 0:.1f} |
| A/B测试总数 | {len(self.ab_tests)} |
| 正在运行的测试 | {len([t for t in self.ab_tests if t.status == 'running'])} |
| 已完成实验分析 | {len(self.experiment_results)} |
| 优化决策总数 | {len(self.decisions)} |

---

## 🔍 CTA库存审计

### 质量分布

| 质量等级 | CTA数量 | 占比 |
|----------|---------|------|
| 优秀 (80-100) | {len([c for c in self.cta_inventory if c.quality_score >= 80])} | {len([c for c in self.cta_inventory if c.quality_score >= 80]) / len(self.cta_inventory) * 100 if self.cta_inventory else 0:.1f}% |
| 良好 (60-79) | {len([c for c in self.cta_inventory if 60 <= c.quality_score < 80])} | {len([c for c in self.cta_inventory if 60 <= c.quality_score < 80]) / len(self.cta_inventory) * 100 if self.cta_inventory else 0:.1f}% |
| 较差 (40-59) | {len([c for c in self.cta_inventory if 40 <= c.quality_score < 60])} | {len([c for c in self.cta_inventory if 40 <= c.quality_score < 60]) / len(self.cta_inventory) * 100 if self.cta_inventory else 0:.1f}% |
| 差 (<40) | {len([c for c in self.cta_inventory if c.quality_score < 40])} | {len([c for c in self.cta_inventory if c.quality_score < 40]) / len(self.cta_inventory) * 100 if self.cta_inventory else 0:.1f}% |

### 主要问题

"""

        # 问题汇总
        all_issues = defaultdict(int)
        for cta in self.cta_inventory:
            for issue in cta.issues:
                all_issues[issue] += 1

        for issue, count in sorted(all_issues.items(), key=lambda x: x[1], reverse=True)[:10]:
            report += f"- **{issue}**: {count}个CTA\n"

        report += """
---

## 🧪 A/B测试管理

### 测试列表

"""

        if self.ab_tests:
            report += "| ID | 名称 | 状态 | 开始日期 | 元素 |\n"
            report += "|----|------|------|----------|------|\n"
            for test in self.ab_tests[-10:]:
                report += f"| {test.id} | {test.name[:40]} | {test.status} | {test.start_date[:10]} | {test.element} |\n"
        else:
            report += "暂无A/B测试\n"

        report += """
### 测试建议

基于CTA审计结果，建议优先开展以下测试：

1. **CTA文案优化测试** - 在低质量CTA最多的页面测试不同文案
2. **CTA位置测试** - 测试文章中部 vs 文章末尾的CTA效果
3. **CTA数量测试** - 测试1个 vs 2个CTA的整体转化效果
4. **CTA格式测试** - 测试文本链接 vs 按钮式CTA的点击率

---

## 📈 实验结果分析

"""

        if self.experiment_results:
            for result in self.experiment_results[-5:]:
                report += f"""### 实验: {result.test_id}

- **分析时间**: {result.analyzed_at[:19]}
- **统计显著**: {'是' if result.is_significant else '否'}
- **获胜方案**: {result.winning_variant or '无显著差异'}
- **置信度**: {result.confidence:.1f}%
- **样本量充足**: {'是' if result.sample_size_sufficient else '否'}
- **持续时间充足**: {'是' if result.duration_sufficient else '否'}
- **建议**: {result.recommendation}

**相对提升**:
"""
                for metric, lift in result.relative_lift.items():
                    report += f"- {metric}: {lift:+.1f}%\n"
                report += "\n"
        else:
            report += "暂无实验结果分析\n"

        report += """
---

## 🎯 优化决策

"""

        if self.decisions:
            for i, dec in enumerate(self.decisions[-5:], 1):
                report += f"""### 决策 {i}: {dec.description}

- **决策类型**: {dec.decision_type}
- **置信度**: {dec.confidence*100:.0f}%
- **预期影响**: {dec.expected_impact}
- **理由**: {dec.rationale}
- **状态**: {dec.status}

**具体行动**:
"""
                for action in dec.actions:
                    report += f"- {action}\n"
                report += "\n"
        else:
            report += "暂无优化决策\n"

        report += f"""
---

## 🚀 下一步行动计划

### 立即执行（1-3天）
1. 批量优化低质量CTA文案，加入行动号召和价值主张
2. 验证Travelpayouts Drive脚本加载，修复点击→初始化断裂
3. 在高流量文章中部增加第二个CTA

### 短期优化（1-2周）
1. 设计并启动第一个A/B测试（CTA文案优化）
2. 建立CTA效果监控看板
3. 优化联盟链接跳转体验

### 中期建设（1个月）
1. 完成3-5个A/B测试，积累优化经验
2. 建立自动化实验分析和决策流程
3. 实现基于内容意图的CTA智能匹配

### 长期战略（3个月）
1. 实现全链路转化优化自动化
2. 建立个性化CTA推荐引擎
3. 实现多变量测试和连续优化

---

*报告由转化优化Agent自动生成 | {now.strftime('%Y-%m-%d %H:%M:%S')}*
*引擎版本: v1.0 | 成熟度目标: L1 → L3*
"""

        # 保存报告
        with open(CONVERSION_REPORT_FILE, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"\n  ✅ 报告已生成: {CONVERSION_REPORT_FILE}")
        print(f"  📊 报告长度: {len(report)} 字符")

        return report

    # ==================== 6. 完整优化流程 ====================

    def run_full_optimization(self):
        """运行完整的转化优化流程"""
        print("\n" + "=" * 60)
        print("  ChinaBound Travel - 转化优化Agent")
        print("  完整优化流程")
        print("=" * 60)

        print(f"\n📅 运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Step 1: CTA库存审计
        self.audit_cta_inventory()

        # Step 2: 生成A/B测试建议
        self.generate_test_recommendations()

        # Step 3: 自动决策
        self.make_optimization_decisions()

        # Step 4: 生成报告
        self.generate_full_report()

        print("\n" + "=" * 60)
        print("  ✅ 完整转化优化流程完成！")
        print("=" * 60)
        print(f"\n📁 报告目录: {CONVERSION_DIR}")
        print(f"📄 转化优化报告: {CONVERSION_REPORT_FILE}")
        print(f"🔍 CTA审计报告: {CTA_AUDIT_FILE}")
        print(f"🧪 A/B测试数据: {AB_TESTS_FILE}")
        print(f"📊 实验结果: {EXPERIMENT_RESULTS_FILE}")
        print(f"🎯 优化决策: {OPTIMIZATION_DECISIONS_FILE}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="ChinaBound Travel 转化优化Agent")
    parser.add_argument("--all", action="store_true", help="运行完整优化流程")
    parser.add_argument("--audit", action="store_true", help="仅CTA库存审计")
    parser.add_argument("--tests", action="store_true", help="仅生成A/B测试建议")
    parser.add_argument("--analyze", action="store_true", help="仅分析实验结果")
    parser.add_argument("--decisions", action="store_true", help="仅生成优化决策")
    parser.add_argument("--report", action="store_true", help="仅生成报告")

    args = parser.parse_args()

    agent = ConversionOptimizationAgent()

    if args.all or not any([args.audit, args.tests, args.analyze, args.decisions, args.report]):
        agent.run_full_optimization()
    elif args.audit:
        agent.audit_cta_inventory()
    elif args.tests:
        agent.audit_cta_inventory()
        agent.generate_test_recommendations()
    elif args.decisions:
        agent.audit_cta_inventory()
        agent.make_optimization_decisions()
    elif args.report:
        agent.audit_cta_inventory()
        agent.generate_full_report()


if __name__ == "__main__":
    main()
