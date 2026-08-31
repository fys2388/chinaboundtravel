#!/usr/bin/env python3
"""
ChinaBound Travel - 自我学习与进化引擎
Self-Learning & Evolution Engine

核心能力：
1. 优化历史数据库 - 记录所有优化动作和效果
2. 效果自动追踪与归因 - 分析哪些优化有效
3. 成功模式提取与复用 - 自动发现高ROI优化模式
4. 失败案例分析与避坑 - 记录无效优化，避免重复
5. 策略自动迭代更新 - 根据数据自动调整优化策略

成熟度目标：L0 → L2（6个月）
"""

import json
import os
import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib


# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
LEARNING_DIR = REPORTS_DIR / "learning"
LEARNING_DIR.mkdir(parents=True, exist_ok=True)

# 数据文件
OPTIMIZATION_HISTORY_FILE = LEARNING_DIR / "optimization_history.json"
SUCCESS_PATTERNS_FILE = LEARNING_DIR / "success_patterns.json"
FAILURE_CASES_FILE = LEARNING_DIR / "failure_cases.json"
STRATEGY_CONFIG_FILE = LEARNING_DIR / "strategy_config.json"
LEARNING_REPORT_FILE = LEARNING_DIR / "learning_report.md"


class OptimizationType(Enum):
    """优化类型枚举"""
    TITLE_META = "title_meta"
    CONTENT = "content"
    INTERNAL_LINK = "internal_link"
    TECHNICAL_SEO = "technical_seo"
    CTA = "cta"
    SOCIAL = "social"
    EMAIL = "email"
    AFFILIATE = "affiliate"
    OTHER = "other"


class EffectivenessLevel(Enum):
    """效果等级枚举"""
    EXCELLENT = "excellent"  # 效果显著，超出预期
    GOOD = "good"            # 效果良好，符合预期
    AVERAGE = "average"      # 效果一般，略有提升
    POOR = "poor"            # 效果较差，几乎无提升
    NEGATIVE = "negative"    # 负面效果，需要回滚
    UNKNOWN = "unknown"      # 数据不足，无法判断


@dataclass
class OptimizationRecord:
    """优化记录数据结构"""
    id: str
    timestamp: str
    type: str
    target: str  # URL或文件路径
    description: str
    before_metrics: Dict[str, Any]
    after_metrics: Dict[str, Any]
    effectiveness: str
    roi_score: float  # 投入产出比分数 0-100
    learnings: List[str]
    tags: List[str]
    status: str  # completed, rolled_back, in_progress


@dataclass
class SuccessPattern:
    """成功模式数据结构"""
    id: str
    name: str
    description: str
    type: str
    conditions: List[str]  # 适用条件
    steps: List[str]       # 执行步骤
    expected_impact: str   # 预期效果
    success_rate: float    # 历史成功率
    times_applied: int     # 应用次数
    avg_roi: float         # 平均ROI
    last_used: str
    tags: List[str]


@dataclass
class FailureCase:
    """失败案例数据结构"""
    id: str
    timestamp: str
    type: str
    target: str
    description: str
    what_went_wrong: str
    root_cause: str
    prevention: str  # 如何避免
    impact: str      # 影响范围
    recovered: bool  # 是否已恢复
    recovery_action: str
    tags: List[str]


class SelfLearningEngine:
    """自我学习引擎主类"""

    def __init__(self):
        self.history: List[OptimizationRecord] = []
        self.success_patterns: List[SuccessPattern] = []
        self.failure_cases: List[FailureCase] = []
        self.strategy_config: Dict[str, Any] = {}
        self._load_data()

    def _load_data(self):
        """加载所有学习数据"""
        # 加载优化历史
        if OPTIMIZATION_HISTORY_FILE.exists():
            with open(OPTIMIZATION_HISTORY_FILE, encoding="utf-8") as f:
                data = json.load(f)
                self.history = [OptimizationRecord(**r) for r in data.get("records", [])]

        # 加载成功模式
        if SUCCESS_PATTERNS_FILE.exists():
            with open(SUCCESS_PATTERNS_FILE, encoding="utf-8") as f:
                data = json.load(f)
                self.success_patterns = [SuccessPattern(**p) for p in data.get("patterns", [])]

        # 加载失败案例
        if FAILURE_CASES_FILE.exists():
            with open(FAILURE_CASES_FILE, encoding="utf-8") as f:
                data = json.load(f)
                self.failure_cases = [FailureCase(**c) for c in data.get("cases", [])]

        # 加载策略配置
        if STRATEGY_CONFIG_FILE.exists():
            with open(STRATEGY_CONFIG_FILE, encoding="utf-8") as f:
                self.strategy_config = json.load(f)
        else:
            self.strategy_config = self._get_default_strategy()

    def _save_data(self):
        """保存所有学习数据"""
        # 保存优化历史
        with open(OPTIMIZATION_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "records": [asdict(r) for r in self.history],
                "total_count": len(self.history),
                "last_updated": datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)

        # 保存成功模式
        with open(SUCCESS_PATTERNS_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "patterns": [asdict(p) for p in self.success_patterns],
                "total_count": len(self.success_patterns),
                "last_updated": datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)

        # 保存失败案例
        with open(FAILURE_CASES_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "cases": [asdict(c) for c in self.failure_cases],
                "total_count": len(self.failure_cases),
                "last_updated": datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)

        # 保存策略配置
        with open(STRATEGY_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.strategy_config, f, ensure_ascii=False, indent=2)

    def _get_default_strategy(self) -> Dict[str, Any]:
        """获取默认优化策略"""
        return {
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "priority_weights": {
                "high_impression_low_ctr": 10,
                "position_4_10": 8,
                "position_11_20": 6,
                "content_quality": 5,
                "zero_click": 7,
                "technical_issue": 9
            },
            "title_optimization": {
                "ideal_length": "50-60 chars",
                "include_year": True,
                "include_target_audience": True,
                "include_action_verb": True,
                "power_words": ["Complete", "Ultimate", "Essential", "Step-by-Step", "2026", "Guide", "Tips", "Best"]
            },
            "meta_description": {
                "ideal_length": "150-160 chars",
                "include_cta": True,
                "include_keyword": True,
                "include_benefit": True
            },
            "content_optimization": {
                "min_word_count": 1000,
                "include_faq": True,
                "include_internal_links": True,
                "min_internal_links": 3,
                "include_examples": True
            },
            "ab_testing": {
                "enabled": False,
                "min_sample_size": 100,
                "confidence_threshold": 0.95
            },
            "learning_rules": {
                "auto_extract_patterns": True,
                "min_pattern_occurrences": 3,
                "pattern_success_threshold": 0.7,
                "auto_avoid_failures": True
            }
        }

    def _generate_id(self, prefix: str, content: str) -> str:
        """生成唯一ID"""
        hash_input = f"{prefix}_{content}_{datetime.now().isoformat()}"
        return f"{prefix}_{hashlib.md5(hash_input.encode()).hexdigest()[:12]}"

    # ==================== 1. 优化历史记录 ====================

    def record_optimization(self, opt_type: str, target: str, description: str,
                             before_metrics: Dict, after_metrics: Dict = None,
                             effectiveness: str = "unknown", roi_score: float = 0,
                             learnings: List[str] = None, tags: List[str] = None) -> OptimizationRecord:
        """记录一次优化动作"""
        record = OptimizationRecord(
            id=self._generate_id("opt", f"{opt_type}_{target}"),
            timestamp=datetime.now().isoformat(),
            type=opt_type,
            target=target,
            description=description,
            before_metrics=before_metrics,
            after_metrics=after_metrics or {},
            effectiveness=effectiveness,
            roi_score=roi_score,
            learnings=learnings or [],
            tags=tags or [],
            status="completed"
        )
        self.history.append(record)
        self._save_data()
        print(f"  ✅ 已记录优化: {opt_type} - {target[:50]}")
        return record

    def update_optimization_effectiveness(self, opt_id: str, after_metrics: Dict,
                                           effectiveness: str, roi_score: float,
                                           learnings: List[str] = None):
        """更新优化效果（追踪后回填）"""
        for record in self.history:
            if record.id == opt_id:
                record.after_metrics = after_metrics
                record.effectiveness = effectiveness
                record.roi_score = roi_score
                if learnings:
                    record.learnings.extend(learnings)
                self._save_data()
                print(f"  ✅ 已更新优化效果: {opt_id} -> {effectiveness} (ROI: {roi_score})")
                return True
        print(f"  ⚠️ 未找到优化记录: {opt_id}")
        return False

    # ==================== 2. 效果自动追踪与归因 ====================

    def track_optimization_effects(self, days: int = 14) -> List[Dict]:
        """追踪近期优化的效果"""
        print("\n" + "=" * 60)
        print("  自我学习引擎 - 效果追踪与归因")
        print("=" * 60)

        cutoff_date = datetime.now() - timedelta(days=days)
        recent_optimizations = [
            r for r in self.history
            if datetime.fromisoformat(r.timestamp) > cutoff_date
        ]

        print(f"\n📊 追踪最近 {days} 天的优化: {len(recent_optimizations)} 项")

        results = []
        for record in recent_optimizations:
            # 计算效果变化
            before = record.before_metrics
            after = record.after_metrics

            changes = {}
            for key in before:
                if key in after and isinstance(before[key], (int, float)) and isinstance(after[key], (int, float)):
                    if before[key] != 0:
                        change_pct = ((after[key] - before[key]) / before[key]) * 100
                        changes[key] = {
                            "before": before[key],
                            "after": after[key],
                            "change_pct": round(change_pct, 2)
                        }

            result = {
                "id": record.id,
                "type": record.type,
                "target": record.target,
                "description": record.description,
                "effectiveness": record.effectiveness,
                "roi_score": record.roi_score,
                "changes": changes,
                "learnings": record.learnings
            }
            results.append(result)

            status_icon = {"excellent": "🚀", "good": "✅", "average": "🟡",
                          "poor": "⚠️", "negative": "🔴", "unknown": "❓"}.get(record.effectiveness, "❓")
            print(f"\n  {status_icon} [{record.type}] {record.description[:60]}")
            print(f"     效果: {record.effectiveness} | ROI: {record.roi_score}/100")
            if changes:
                for key, change in changes.items():
                    direction = "📈" if change["change_pct"] > 0 else "📉"
                    print(f"     {direction} {key}: {change['before']} → {change['after']} ({change['change_pct']:+.1f}%)")

        return results

    # ==================== 3. 成功模式提取与复用 ====================

    def extract_success_patterns(self) -> List[SuccessPattern]:
        """从历史优化中提取成功模式"""
        print("\n" + "=" * 60)
        print("  自我学习引擎 - 成功模式提取")
        print("=" * 60)

        # 筛选高ROI的优化记录
        successful = [r for r in self.history if r.roi_score >= 70 and r.effectiveness in ["excellent", "good"]]
        print(f"\n📊 高ROI优化记录: {len(successful)} 项 (ROI>=70)")

        # 按类型分组
        by_type = {}
        for record in successful:
            if record.type not in by_type:
                by_type[record.type] = []
            by_type[record.type].append(record)

        new_patterns = []
        for opt_type, records in by_type.items():
            if len(records) >= self.strategy_config["learning_rules"]["min_pattern_occurrences"]:
                # 检查是否已有该模式
                existing = [p for p in self.success_patterns if p.type == opt_type]

                if existing:
                    # 更新已有模式
                    pattern = existing[0]
                    pattern.times_applied += len(records)
                    pattern.avg_roi = sum(r.roi_score for r in records) / len(records)
                    pattern.last_used = datetime.now().isoformat()
                    print(f"  🔄 更新模式: {pattern.name} (应用次数: {pattern.times_applied}, 平均ROI: {pattern.avg_roi:.1f})")
                else:
                    # 创建新模式
                    pattern = SuccessPattern(
                        id=self._generate_id("pat", opt_type),
                        name=f"{opt_type.replace('_', ' ').title()} Optimization Pattern",
                        description=f"Automatically extracted pattern for {opt_type} optimizations based on {len(records)} successful cases",
                        type=opt_type,
                        conditions=self._extract_conditions(records),
                        steps=self._extract_steps(records),
                        expected_impact=self._calculate_expected_impact(records),
                        success_rate=len(records) / max(len([r for r in self.history if r.type == opt_type]), 1),
                        times_applied=len(records),
                        avg_roi=sum(r.roi_score for r in records) / len(records),
                        last_used=datetime.now().isoformat(),
                        tags=[opt_type, "auto_extracted"]
                    )
                    self.success_patterns.append(pattern)
                    new_patterns.append(pattern)
                    print(f"  ✨ 发现新模式: {pattern.name} (成功率: {pattern.success_rate:.0%}, 平均ROI: {pattern.avg_roi:.1f})")

        self._save_data()
        print(f"\n📊 成功模式总数: {len(self.success_patterns)} (新增: {len(new_patterns)})")
        return self.success_patterns

    def _extract_conditions(self, records: List[OptimizationRecord]) -> List[str]:
        """从记录中提取适用条件"""
        conditions = set()
        for record in records:
            if "high_impression" in record.tags:
                conditions.add("高展示量页面 (impressions >= 50)")
            if "low_ctr" in record.tags:
                conditions.add("低CTR页面 (CTR < 2%)")
            if "position_4_20" in record.tags:
                conditions.add("排名4-20位页面")
            if "content_quality" in record.tags:
                conditions.add("内容质量较低 (字数 < 1000)")
        return list(conditions) if conditions else ["需要根据具体情况判断"]

    def _extract_steps(self, records: List[OptimizationRecord]) -> List[str]:
        """从记录中提取执行步骤"""
        return [
            "分析当前页面数据（展示量、CTR、排名）",
            "识别优化机会类型",
            "执行优化动作",
            "提交GSC重新索引",
            "追踪14天后的效果变化",
            "记录经验教训"
        ]

    def _calculate_expected_impact(self, records: List[OptimizationRecord]) -> str:
        """计算预期效果"""
        avg_roi = sum(r.roi_score for r in records) / len(records)
        if avg_roi >= 80:
            return f"效果显著 (平均ROI: {avg_roi:.0f}/100)"
        elif avg_roi >= 60:
            return f"效果良好 (平均ROI: {avg_roi:.0f}/100)"
        else:
            return f"效果一般 (平均ROI: {avg_roi:.0f}/100)"

    def get_recommended_patterns(self, context: Dict = None) -> List[SuccessPattern]:
        """根据当前上下文推荐适用的成功模式"""
        print("\n" + "=" * 60)
        print("  自我学习引擎 - 推荐成功模式")
        print("=" * 60)

        # 按平均ROI排序
        sorted_patterns = sorted(self.success_patterns, key=lambda p: p.avg_roi, reverse=True)

        print(f"\n📊 可用成功模式: {len(sorted_patterns)} 个")
        for i, pattern in enumerate(sorted_patterns[:5], 1):
            print(f"\n  {i}. {pattern.name}")
            print(f"     类型: {pattern.type} | 成功率: {pattern.success_rate:.0%} | 平均ROI: {pattern.avg_roi:.1f}")
            print(f"     应用次数: {pattern.times_applied} | 最后使用: {pattern.last_used[:10]}")
            print(f"     预期效果: {pattern.expected_impact}")

        return sorted_patterns

    # ==================== 4. 失败案例分析与避坑 ====================

    def record_failure(self, opt_type: str, target: str, description: str,
                       what_went_wrong: str, root_cause: str, prevention: str,
                       impact: str = "localized", recovered: bool = False,
                       recovery_action: str = "", tags: List[str] = None) -> FailureCase:
        """记录一次失败案例"""
        case = FailureCase(
            id=self._generate_id("fail", f"{opt_type}_{target}"),
            timestamp=datetime.now().isoformat(),
            type=opt_type,
            target=target,
            description=description,
            what_went_wrong=what_went_wrong,
            root_cause=root_cause,
            prevention=prevention,
            impact=impact,
            recovered=recovered,
            recovery_action=recovery_action,
            tags=tags or []
        )
        self.failure_cases.append(case)
        self._save_data()
        print(f"  ⚠️ 已记录失败案例: {opt_type} - {target[:50]}")
        print(f"     根因: {root_cause}")
        print(f"     预防: {prevention}")
        return case

    def get_failure_prevention_tips(self) -> List[Dict]:
        """获取失败预防建议"""
        print("\n" + "=" * 60)
        print("  自我学习引擎 - 失败预防建议")
        print("=" * 60)

        print(f"\n📊 历史失败案例: {len(self.failure_cases)} 个")

        tips = []
        # 按根因分组
        by_root_cause = {}
        for case in self.failure_cases:
            if case.root_cause not in by_root_cause:
                by_root_cause[case.root_cause] = []
            by_root_cause[case.root_cause].append(case)

        for root_cause, cases in by_root_cause.items():
            tip = {
                "root_cause": root_cause,
                "occurrences": len(cases),
                "prevention": cases[0].prevention,
                "examples": [c.description[:50] for c in cases[:3]]
            }
            tips.append(tip)
            print(f"\n  ⚠️ 根因: {root_cause} (发生 {len(cases)} 次)")
            print(f"     预防: {cases[0].prevention}")

        # 如果没有失败案例，提供通用建议
        if not tips:
            print("\n  ✅ 暂无失败案例记录")
            print("\n  💡 通用预防建议:")
            general_tips = [
                "优化前备份原始文件",
                "小批量测试，观察效果后再推广",
                "不要同时修改多个变量，便于归因",
                "优化后提交GSC重新索引",
                "追踪至少14天的数据再判断效果"
            ]
            for tip in general_tips:
                print(f"     - {tip}")

        return tips

    # ==================== 5. 策略自动迭代更新 ====================

    def update_strategy_based_on_data(self):
        """根据历史数据自动更新优化策略"""
        print("\n" + "=" * 60)
        print("  自我学习引擎 - 策略自动迭代")
        print("=" * 60)

        if len(self.history) < 5:
            print("\n  ⚠️ 历史数据不足（<5条），暂不自动更新策略")
            print(f"     当前记录数: {len(self.history)}")
            return

        print(f"\n📊 基于 {len(self.history)} 条历史记录更新策略")

        # 按类型计算平均ROI
        roi_by_type = {}
        for record in self.history:
            if record.type not in roi_by_type:
                roi_by_type[record.type] = []
            roi_by_type[record.type].append(record.roi_score)

        avg_roi_by_type = {t: sum(scores)/len(scores) for t, scores in roi_by_type.items() if scores}

        print("\n  📈 各类型平均ROI:")
        for opt_type, avg_roi in sorted(avg_roi_by_type.items(), key=lambda x: x[1], reverse=True):
            print(f"     {opt_type}: {avg_roi:.1f}/100 (n={len(roi_by_type[opt_type])})")

        # 更新优先级权重
        old_weights = self.strategy_config["priority_weights"].copy()
        for opt_type, avg_roi in avg_roi_by_type.items():
            # 将ROI映射到权重（0-10）
            new_weight = max(1, min(10, int(avg_roi / 10)))
            type_key = opt_type.lower().replace(" ", "_")
            if type_key in self.strategy_config["priority_weights"]:
                self.strategy_config["priority_weights"][type_key] = new_weight

        # 检查权重变化
        weight_changes = []
        for key, old_val in old_weights.items():
            new_val = self.strategy_config["priority_weights"].get(key, old_val)
            if old_val != new_val:
                weight_changes.append(f"{key}: {old_val} → {new_val}")

        if weight_changes:
            print("\n  🔄 优先级权重更新:")
            for change in weight_changes:
                print(f"     - {change}")
        else:
            print("\n  ✅ 优先级权重无需调整")

        # 更新策略版本和时间
        self.strategy_config["version"] = f"1.{len(self.history) // 10}"
        self.strategy_config["last_updated"] = datetime.now().isoformat()
        self.strategy_config["total_optimizations_analyzed"] = len(self.history)

        self._save_data()
        print(f"\n  ✅ 策略已更新至版本 {self.strategy_config['version']}")

    # ==================== 6. 生成学习报告 ====================

    def generate_learning_report(self) -> str:
        """生成自我学习报告"""
        print("\n" + "=" * 60)
        print("  自我学习引擎 - 生成学习报告")
        print("=" * 60)

        now = datetime.now()
        report = f"""# ChinaBound Travel 自我学习与进化报告

**生成时间**: {now.strftime('%Y-%m-%d %H:%M:%S')}
**引擎版本**: {self.strategy_config.get('version', '1.0')}
**策略版本**: {self.strategy_config.get('version', '1.0')}

---

## 📊 学习数据总览

| 指标 | 数值 |
|------|------|
| 累计优化记录 | {len(self.history)} 条 |
| 成功模式 | {len(self.success_patterns)} 个 |
| 失败案例 | {len(self.failure_cases)} 个 |
| 策略迭代次数 | {self.strategy_config.get('total_optimizations_analyzed', 0) // 10} 次 |

---

## 📈 优化效果统计

### 按效果等级分布
"""

        # 效果分布
        effectiveness_dist = {}
        for record in self.history:
            eff = record.effectiveness
            effectiveness_dist[eff] = effectiveness_dist.get(eff, 0) + 1

        for eff, count in sorted(effectiveness_dist.items(), key=lambda x: x[1], reverse=True):
            icons = {"excellent": "🚀", "good": "✅", "average": "🟡",
                    "poor": "⚠️", "negative": "🔴", "unknown": "❓"}
            pct = (count / len(self.history) * 100) if self.history else 0
            report += f"- {icons.get(eff, '❓')} **{eff}**: {count} 条 ({pct:.1f}%)\n"

        # 平均ROI
        if self.history:
            avg_roi = sum(r.roi_score for r in self.history) / len(self.history)
            report += f"\n**平均ROI分数**: {avg_roi:.1f}/100\n"

        report += """
---

## 🏆 Top 成功模式

"""

        if self.success_patterns:
            sorted_patterns = sorted(self.success_patterns, key=lambda p: p.avg_roi, reverse=True)
            for i, pattern in enumerate(sorted_patterns[:5], 1):
                report += f"""### {i}. {pattern.name}

- **类型**: {pattern.type}
- **成功率**: {pattern.success_rate:.0%}
- **平均ROI**: {pattern.avg_roi:.1f}/100
- **应用次数**: {pattern.times_applied}
- **预期效果**: {pattern.expected_impact}
- **适用条件**:
"""
                for condition in pattern.conditions[:3]:
                    report += f"  - {condition}\n"
                report += "\n"
        else:
            report += "暂无成功模式（需要至少3次同类优化才能提取模式）\n"

        report += """
---

## ⚠️ 失败案例与预防

"""

        if self.failure_cases:
            for i, case in enumerate(self.failure_cases[:5], 1):
                report += f"""### {i}. {case.description[:60]}

- **类型**: {case.type}
- **时间**: {case.timestamp[:10]}
- **问题**: {case.what_went_wrong}
- **根因**: {case.root_cause}
- **预防**: {case.prevention}
- **状态**: {'✅ 已恢复' if case.recovered else '🔄 处理中'}

"""
        else:
            report += """### 通用预防建议

- ✅ 优化前备份原始文件
- ✅ 小批量测试，观察效果后再推广
- ✅ 不要同时修改多个变量，便于归因
- ✅ 优化后提交GSC重新索引
- ✅ 追踪至少14天的数据再判断效果
"""

        report += """
---

## 🔄 策略配置

### 当前优先级权重

| 优化类型 | 权重 |
|----------|------|
"""

        for opt_type, weight in sorted(self.strategy_config["priority_weights"].items(),
                                        key=lambda x: x[1], reverse=True):
            report += f"| {opt_type} | {weight}/10 |\n"

        report += f"""
### Title优化规则
- 理想长度: {self.strategy_config['title_optimization']['ideal_length']}
- 包含年份: {'✅' if self.strategy_config['title_optimization']['include_year'] else '❌'}
- 包含目标人群: {'✅' if self.strategy_config['title_optimization']['include_target_audience'] else '❌'}

### Meta描述规则
- 理想长度: {self.strategy_config['meta_description']['ideal_length']}
- 包含CTA: {'✅' if self.strategy_config['meta_description']['include_cta'] else '❌'}

---

## 🎯 下一步学习建议

"""

        # 基于当前状态生成建议
        if len(self.history) < 10:
            report += """1. **积累更多优化数据**: 当前记录较少，建议继续执行优化并记录效果
2. **建立追踪习惯**: 每次优化后14天回填效果数据
3. **开始小批量A/B测试**: 选择1-2个高展示页面测试不同Title格式
"""
        elif len(self.success_patterns) == 0:
            report += """1. **提取成功模式**: 已有足够数据，可以开始自动提取成功模式
2. **分类记录优化**: 确保每条优化都有明确的类型标签
3. **计算ROI分数**: 为每条优化打分，便于模式提取
"""
        else:
            report += """1. **复用成功模式**: 将提取的成功模式应用到新的优化中
2. **避免失败案例**: 检查失败预防清单，避免重复犯错
3. **深化A/B测试**: 基于成功模式设计更精细的对比实验
4. **跨维度学习**: 将SEO优化的成功经验迁移到社媒、邮件等其他维度
"""

        report += f"""
---

*报告由自我学习引擎自动生成 | 数据更新至 {now.strftime('%Y-%m-%d')}*
"""

        # 保存报告
        with open(LEARNING_REPORT_FILE, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"\n  ✅ 学习报告已生成: {LEARNING_REPORT_FILE}")
        print(f"     报告长度: {len(report)} 字符")

        return report

    # ==================== 7. 完整学习流程 ====================

    def run_full_learning_cycle(self):
        """运行完整的自我学习周期"""
        print("\n" + "=" * 60)
        print("  ChinaBound Travel - 自我学习与进化引擎")
        print("  完整学习周期")
        print("=" * 60)

        print(f"\n📅 运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 当前数据: {len(self.history)} 条优化记录, {len(self.success_patterns)} 个成功模式, {len(self.failure_cases)} 个失败案例")

        # Step 1: 效果追踪
        self.track_optimization_effects(days=30)

        # Step 2: 提取成功模式
        self.extract_success_patterns()

        # Step 3: 失败预防建议
        self.get_failure_prevention_tips()

        # Step 4: 策略自动迭代
        self.update_strategy_based_on_data()

        # Step 5: 推荐成功模式
        self.get_recommended_patterns()

        # Step 6: 生成学习报告
        self.generate_learning_report()

        print("\n" + "=" * 60)
        print("  ✅ 完整学习周期完成！")
        print("=" * 60)
        print(f"\n📁 学习数据目录: {LEARNING_DIR}")
        print(f"📄 学习报告: {LEARNING_REPORT_FILE}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="ChinaBound Travel 自我学习与进化引擎")
    parser.add_argument("--cycle", action="store_true", help="运行完整学习周期")
    parser.add_argument("--track", action="store_true", help="仅追踪优化效果")
    parser.add_argument("--patterns", action="store_true", help="仅提取成功模式")
    parser.add_argument("--failures", action="store_true", help="仅获取失败预防建议")
    parser.add_argument("--strategy", action="store_true", help="仅更新策略")
    parser.add_argument("--report", action="store_true", help="仅生成学习报告")
    parser.add_argument("--record", type=str, help="记录一次优化（JSON格式）")

    args = parser.parse_args()

    engine = SelfLearningEngine()

    if args.cycle or (not any([args.track, args.patterns, args.failures, args.strategy, args.report, args.record])):
        engine.run_full_learning_cycle()
    elif args.track:
        engine.track_optimization_effects()
    elif args.patterns:
        engine.extract_success_patterns()
        engine.get_recommended_patterns()
    elif args.failures:
        engine.get_failure_prevention_tips()
    elif args.strategy:
        engine.update_strategy_based_on_data()
    elif args.report:
        engine.generate_learning_report()
    elif args.record:
        # 记录优化（简化版）
        try:
            data = json.loads(args.record)
            engine.record_optimization(
                opt_type=data.get("type", "other"),
                target=data.get("target", ""),
                description=data.get("description", ""),
                before_metrics=data.get("before", {}),
                after_metrics=data.get("after", {}),
                effectiveness=data.get("effectiveness", "unknown"),
                roi_score=data.get("roi", 0),
                tags=data.get("tags", [])
            )
        except json.JSONDecodeError:
            print("❌ JSON格式错误")


if __name__ == "__main__":
    main()
