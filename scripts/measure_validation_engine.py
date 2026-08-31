#!/usr/bin/env python3
"""
ChinaBound Travel - Measure Validation Engine
Measure验证引擎

核心功能：解决"学习闭环没有Measure，无法验证学得对不对"的问题
- 记录每轮学习前的基线指标（Before）
- 记录每轮学习后的指标（After）
- 计算前后变化（Delta）
- 验证学习策略是否有效
- 生成可验证的学习效果报告

验收标准：
- 每轮学习必须能回答"上一轮改变了什么？对应指标变了多少？"
- 策略变化必须有对应的指标变化
- 无效策略必须被识别并标记

使用方式：
    python scripts/measure_validation_engine.py --run
    python scripts/measure_validation_engine.py --baseline
    python scripts/measure_validation_engine.py --compare
    python scripts/measure_validation_engine.py --report
"""

import os
import sys
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
MEASUREMENT_DIR = REPORTS_DIR / "measurement"
MEASUREMENT_DIR.mkdir(parents=True, exist_ok=True)

# 输出文件
BASELINE_FILE = MEASUREMENT_DIR / "baseline_metrics.json"
CURRENT_METRICS_FILE = MEASUREMENT_DIR / "current_metrics.json"
MEASURE_VALIDATION_JSON = MEASUREMENT_DIR / "measure_validation_report.json"
MEASURE_VALIDATION_MD = MEASUREMENT_DIR / "measure_validation_report.md"
LEARNING_EFFECTIVENESS_FILE = MEASUREMENT_DIR / "learning_effectiveness.json"


class MeasureValidationEngine:
    """Measure验证引擎"""

    def __init__(self):
        self.baseline = {}
        self.current = {}
        self.comparison = {}
        self.effectiveness = {}

    def _load_json(self, file_path: Path) -> Dict:
        """安全加载JSON"""
        if file_path.exists():
            try:
                with open(file_path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _collect_current_metrics(self) -> Dict:
        """收集当前指标"""
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "traffic": {},
            "content": {},
            "social": {},
            "conversion": {},
            "revenue": {},
            "seo": {}
        }

        # 1. 流量指标（从真实数据拉取结果）
        ga4_data = self._load_json(REPORTS_DIR / "real_data" / "ga4_real_data.json")
        if ga4_data.get("metrics"):
            metrics["traffic"] = ga4_data["metrics"]

        # 2. 内容指标
        content_data = self._load_json(REPORTS_DIR / "real_data" / "content_real_data.json")
        if content_data.get("metrics"):
            metrics["content"] = content_data["metrics"]

        # 3. 社媒指标
        social_data = self._load_json(REPORTS_DIR / "real_data" / "social_real_data.json")
        if social_data.get("metrics"):
            metrics["social"] = social_data["metrics"]

        # 4. SEO指标
        gsc_data = self._load_json(REPORTS_DIR / "real_data" / "gsc_real_data.json")
        if gsc_data.get("metrics"):
            metrics["seo"] = gsc_data["metrics"]

        # 5. 统计本地文章数
        content_dir = PROJECT_ROOT / "content" / "posts"
        if content_dir.exists():
            articles = list(content_dir.glob("*.md"))
            metrics["content"]["total_articles"] = len(articles)

        return metrics

    def capture_baseline(self) -> Dict:
        """捕获基线指标（学习前）"""
        print("\n" + "=" * 60)
        print("  捕获基线指标（学习前 Before）")
        print("=" * 60)

        self.baseline = self._collect_current_metrics()

        # 保存基线
        with open(BASELINE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.baseline, f, ensure_ascii=False, indent=2)

        print(f"  ✅ 基线指标已捕获: {BASELINE_FILE}")
        print(f"  📅 基线日期: {self.baseline.get('date')}")
        print(f"  📊 流量指标: {len(self.baseline.get('traffic', {}))} 项")
        print(f"  📝 内容指标: {len(self.baseline.get('content', {}))} 项")
        print(f"  📱 社媒指标: {len(self.baseline.get('social', {}))} 项")
        print(f"  🔍 SEO指标: {len(self.baseline.get('seo', {}))} 项")

        return self.baseline

    def capture_current(self) -> Dict:
        """捕获当前指标（学习后 After）"""
        print("\n" + "=" * 60)
        print("  捕获当前指标（学习后 After）")
        print("=" * 60)

        self.current = self._collect_current_metrics()

        # 保存当前指标
        with open(CURRENT_METRICS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.current, f, ensure_ascii=False, indent=2)

        print(f"  ✅ 当前指标已捕获: {CURRENT_METRICS_FILE}")
        print(f"  📅 当前日期: {self.current.get('date')}")

        return self.current

    def compare_before_after(self) -> Dict:
        """前后对照比较"""
        print("\n" + "=" * 60)
        print("  前后对照比较（Before vs After）")
        print("=" * 60)

        # 确保有基线和当前数据
        if not self.baseline:
            self.baseline = self._load_json(BASELINE_FILE)
        if not self.current:
            self.current = self._load_json(CURRENT_METRICS_FILE)

        if not self.baseline:
            print("  ⚠️ 没有基线数据，先捕获基线")
            self.capture_baseline()

        comparison = {
            "comparison_time": datetime.now().isoformat(),
            "baseline_date": self.baseline.get("date"),
            "current_date": self.current.get("date"),
            "categories": {},
            "summary": {
                "total_metrics": 0,
                "improved": 0,
                "declined": 0,
                "unchanged": 0,
                "overall_score": 0
            }
        }

        # 比较每个类别
        categories = ["traffic", "content", "social", "conversion", "revenue", "seo"]
        for category in categories:
            baseline_cat = self.baseline.get(category, {})
            current_cat = self.current.get(category, {})

            if not baseline_cat and not current_cat:
                continue

            cat_comparison = {
                "metrics": {},
                "improved": 0,
                "declined": 0,
                "unchanged": 0
            }

            all_keys = set(baseline_cat.keys()) | set(current_cat.keys())
            for key in all_keys:
                baseline_val = baseline_cat.get(key, 0)
                current_val = current_cat.get(key, 0)

                # 只比较数值型指标
                if isinstance(baseline_val, (int, float)) and isinstance(current_val, (int, float)):
                    delta = current_val - baseline_val
                    delta_pct = (delta / baseline_val * 100) if baseline_val != 0 else 0

                    # 判断方向（更高更好的指标）
                    higher_is_better = key not in ["bounce_rate", "index_errors", "avg_position"]
                    if higher_is_better:
                        trend = "improved" if delta > 0 else "declined" if delta < 0 else "unchanged"
                    else:
                        trend = "improved" if delta < 0 else "declined" if delta > 0 else "unchanged"

                    cat_comparison["metrics"][key] = {
                        "baseline": baseline_val,
                        "current": current_val,
                        "delta": delta,
                        "delta_pct": round(delta_pct, 2),
                        "trend": trend
                    }

                    if trend == "improved":
                        cat_comparison["improved"] += 1
                    elif trend == "declined":
                        cat_comparison["declined"] += 1
                    else:
                        cat_comparison["unchanged"] += 1

                    comparison["summary"]["total_metrics"] += 1

            comparison["categories"][category] = cat_comparison
            comparison["summary"]["improved"] += cat_comparison["improved"]
            comparison["summary"]["declined"] += cat_comparison["declined"]
            comparison["summary"]["unchanged"] += cat_comparison["unchanged"]

        # 计算整体评分
        total = comparison["summary"]["total_metrics"]
        if total > 0:
            comparison["summary"]["overall_score"] = round(
                (comparison["summary"]["improved"] / total) * 100, 1
            )

        print(f"\n  📊 比较结果:")
        print(f"    基线日期: {comparison['baseline_date']}")
        print(f"    当前日期: {comparison['current_date']}")
        print(f"    总指标数: {total}")
        print(f"    ✅ 改善: {comparison['summary']['improved']}")
        print(f"    ❌ 下降: {comparison['summary']['declined']}")
        print(f"    ➖ 不变: {comparison['summary']['unchanged']}")
        print(f"    🎯 整体评分: {comparison['summary']['overall_score']}/100")

        # 打印各类别详情
        for cat, cat_data in comparison["categories"].items():
            if cat_data["metrics"]:
                print(f"\n  📂 {cat.upper()}:")
                for metric, data in list(cat_data["metrics"].items())[:5]:
                    icon = "📈" if data["trend"] == "improved" else "📉" if data["trend"] == "declined" else "➖"
                    print(f"    {icon} {metric}: {data['baseline']} → {data['current']} ({data['delta_pct']:+.1f}%)")

        self.comparison = comparison
        return comparison

    def validate_learning_effectiveness(self) -> Dict:
        """验证学习有效性"""
        print("\n" + "=" * 60)
        print("  验证学习有效性")
        print("=" * 60)

        if not self.comparison:
            self.compare_before_after()

        effectiveness = {
            "validation_time": datetime.now().isoformat(),
            "overall_score": self.comparison.get("summary", {}).get("overall_score", 0),
            "is_effective": False,
            "effective_strategies": [],
            "ineffective_strategies": [],
            "needs_more_data": [],
            "recommendations": []
        }

        # 判断整体有效性
        score = effectiveness["overall_score"]
        if score >= 60:
            effectiveness["is_effective"] = True
            effectiveness["recommendations"].append("学习策略整体有效，继续当前方向")
        elif score >= 40:
            effectiveness["recommendations"].append("学习策略部分有效，需要优化低效策略")
        else:
            effectiveness["recommendations"].append("学习策略效果不佳，需要重新评估策略方向")

        # 分析各类别
        for cat, cat_data in self.comparison.get("categories", {}).items():
            total = cat_data["improved"] + cat_data["declined"] + cat_data["unchanged"]
            if total == 0:
                effectiveness["needs_more_data"].append(cat)
                continue

            improve_rate = cat_data["improved"] / total * 100
            if improve_rate >= 60:
                effectiveness["effective_strategies"].append({
                    "category": cat,
                    "improve_rate": round(improve_rate, 1),
                    "improved": cat_data["improved"],
                    "total": total
                })
            elif improve_rate <= 30:
                effectiveness["ineffective_strategies"].append({
                    "category": cat,
                    "improve_rate": round(improve_rate, 1),
                    "improved": cat_data["improved"],
                    "declined": cat_data["declined"],
                    "total": total
                })

        # 生成建议
        if effectiveness["ineffective_strategies"]:
            effectiveness["recommendations"].append(
                f"低效策略需要优化: {', '.join(s['category'] for s in effectiveness['ineffective_strategies'])}"
            )
        if effectiveness["needs_more_data"]:
            effectiveness["recommendations"].append(
                f"需要更多数据验证: {', '.join(effectiveness['needs_more_data'])}"
            )

        print(f"\n  🎯 整体评分: {score}/100")
        print(f"  ✅ 学习有效: {'是' if effectiveness['is_effective'] else '否'}")
        print(f"  📈 有效策略: {len(effectiveness['effective_strategies'])} 个")
        print(f"  📉 低效策略: {len(effectiveness['ineffective_strategies'])} 个")
        print(f"  ⏳ 需更多数据: {len(effectiveness['needs_more_data'])} 个")
        print(f"\n  💡 建议:")
        for rec in effectiveness["recommendations"]:
            print(f"    - {rec}")

        # 保存
        with open(LEARNING_EFFECTIVENESS_FILE, "w", encoding="utf-8") as f:
            json.dump(effectiveness, f, ensure_ascii=False, indent=2)

        self.effectiveness = effectiveness
        return effectiveness

    def generate_report(self) -> str:
        """生成Measure验证报告"""
        print("\n" + "=" * 60)
        print("  生成Measure验证报告")
        print("=" * 60)

        if not self.comparison:
            self.compare_before_after()
        if not self.effectiveness:
            self.validate_learning_effectiveness()

        report = f"""# Measure验证报告（前后对照）

**验证时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**基线日期**: {self.comparison.get('baseline_date', 'N/A')}
**当前日期**: {self.comparison.get('current_date', 'N/A')}
**整体评分**: {self.comparison.get('summary', {}).get('overall_score', 0)}/100
**学习有效**: {'✅ 是' if self.effectiveness.get('is_effective') else '❌ 否'}

---

## 🎯 核心问题回答

> **上一轮我们改变了什么？对应指标变了多少？**

| 类别 | 改善指标 | 下降指标 | 不变指标 | 改善率 |
|------|---------|---------|---------|--------|
"""

        for cat, cat_data in self.comparison.get("categories", {}).items():
            total = cat_data["improved"] + cat_data["declined"] + cat_data["unchanged"]
            improve_rate = (cat_data["improved"] / total * 100) if total > 0 else 0
            report += f"| {cat.upper()} | {cat_data['improved']} | {cat_data['declined']} | {cat_data['unchanged']} | {improve_rate:.1f}% |\n"

        report += f"""
---

## 📊 详细指标变化

"""

        for cat, cat_data in self.comparison.get("categories", {}).items():
            if not cat_data["metrics"]:
                continue
            report += f"### {cat.upper()}\n\n"
            report += "| 指标 | 基线(Before) | 当前(After) | 变化 | 变化率 | 趋势 |\n"
            report += "|------|-------------|------------|------|--------|------|\n"
            for metric, data in cat_data["metrics"].items():
                icon = "📈" if data["trend"] == "improved" else "📉" if data["trend"] == "declined" else "➖"
                report += f"| {metric} | {data['baseline']} | {data['current']} | {data['delta']:+.2f} | {data['delta_pct']:+.1f}% | {icon} {data['trend']} |\n"
            report += "\n"

        report += f"""
---

## ✅ 有效策略

"""
        if self.effectiveness["effective_strategies"]:
            for s in self.effectiveness["effective_strategies"]:
                report += f"- **{s['category'].upper()}**: 改善率 {s['improve_rate']}% ({s['improved']}/{s['total']} 指标改善)\n"
        else:
            report += "暂无显著有效策略\n"

        report += f"""
---

## ❌ 低效策略（需要优化）

"""
        if self.effectiveness["ineffective_strategies"]:
            for s in self.effectiveness["ineffective_strategies"]:
                report += f"- **{s['category'].upper()}**: 改善率 {s['improve_rate']}% ({s['improved']}改善 / {s['declined']}下降 / {s['total']}总计)\n"
        else:
            report += "暂无显著低效策略\n"

        report += f"""
---

## 💡 建议和下一步

"""
        for i, rec in enumerate(self.effectiveness["recommendations"], 1):
            report += f"{i}. {rec}\n"

        report += f"""
---

## 📝 验证说明

本报告由Measure验证引擎自动生成，核心目的是解决"学习闭环没有Measure，无法验证学得对不对"的问题。

**验证方法**:
1. 学习前捕获基线指标（Before）
2. 学习后捕获当前指标（After）
3. 计算前后变化（Delta）
4. 验证学习策略是否有效

**验收标准**:
- 每轮学习必须能回答"上一轮改变了什么？对应指标变了多少？"
- 策略变化必须有对应的指标变化
- 无效策略必须被识别并标记

---

*报告由Measure验证引擎自动生成*
*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

        # 保存报告
        with open(MEASURE_VALIDATION_MD, "w", encoding="utf-8") as f:
            f.write(report)

        # 保存JSON
        validation_json = {
            "validation_time": datetime.now().isoformat(),
            "overall_score": self.comparison.get("summary", {}).get("overall_score", 0),
            "is_effective": self.effectiveness.get("is_effective", False),
            "comparison": self.comparison,
            "effectiveness": self.effectiveness
        }
        with open(MEASURE_VALIDATION_JSON, "w", encoding="utf-8") as f:
            json.dump(validation_json, f, ensure_ascii=False, indent=2)

        print(f"  ✅ Measure验证报告已生成: {MEASURE_VALIDATION_MD}")
        print(f"  ✅ Measure验证JSON已生成: {MEASURE_VALIDATION_JSON}")

        return report

    def run_full_validation(self) -> Dict:
        """运行完整验证流程"""
        print("\n" + "=" * 60)
        print("  Measure验证引擎 - 完整验证流程")
        print("=" * 60)
        print(f"\n  开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("  流程: 捕获基线 → 学习执行 → 捕获当前 → 前后对照 → 有效性验证 → 生成报告")

        # 步骤1: 捕获基线（如果不存在）
        if not BASELINE_FILE.exists():
            self.capture_baseline()
        else:
            print("\n  ⏭️  基线已存在，跳过基线捕获")
            self.baseline = self._load_json(BASELINE_FILE)

        # 步骤2: 捕获当前指标
        self.capture_current()

        # 步骤3: 前后对照
        self.compare_before_after()

        # 步骤4: 有效性验证
        self.validate_learning_effectiveness()

        # 步骤5: 生成报告
        self.generate_report()

        # 总结
        print("\n" + "=" * 60)
        print("  Measure验证完成")
        print("=" * 60)
        print(f"\n  🎯 整体评分: {self.comparison.get('summary', {}).get('overall_score', 0)}/100")
        print(f"  ✅ 学习有效: {'是' if self.effectiveness.get('is_effective') else '否'}")
        print(f"  📈 有效策略: {len(self.effectiveness.get('effective_strategies', []))} 个")
        print(f"  📉 低效策略: {len(self.effectiveness.get('ineffective_strategies', []))} 个")
        print(f"\n  📝 核心回答: 上一轮改变了什么？对应指标变了多少？")
        print(f"    → 已在报告中详细列出每个类别的前后对照")
        print(f"\n  📄 报告: {MEASURE_VALIDATION_MD}")

        return {
            "overall_score": self.comparison.get("summary", {}).get("overall_score", 0),
            "is_effective": self.effectiveness.get("is_effective", False),
            "report": str(MEASURE_VALIDATION_MD)
        }


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Measure验证引擎")
    parser.add_argument("--run", action="store_true", help="运行完整验证流程")
    parser.add_argument("--baseline", action="store_true", help="仅捕获基线")
    parser.add_argument("--current", action="store_true", help="仅捕获当前指标")
    parser.add_argument("--compare", action="store_true", help="仅前后对照比较")
    parser.add_argument("--report", action="store_true", help="仅生成报告")

    args = parser.parse_args()

    engine = MeasureValidationEngine()

    if args.run:
        engine.run_full_validation()
    elif args.baseline:
        engine.capture_baseline()
    elif args.current:
        engine.capture_current()
    elif args.compare:
        engine.compare_before_after()
    elif args.report:
        engine.generate_report()
    else:
        engine.run_full_validation()


if __name__ == "__main__":
    main()
