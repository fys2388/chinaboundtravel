#!/usr/bin/env python3
"""
ChinaBound Travel - Content Learning 闭环系统
Content Learning Closed Loop

功能：打通内容优化的完整学习闭环
Observe → Record → Analyze → Learn → Decide → Act → Measure → Learn

闭环流程：
1. Observe: 从GA4/GSC/内容审计获取文章表现数据
2. Record: 记录到Growth Memory内容记忆库
3. Analyze: 分析哪些文章/关键词/结构/CTA效果好
4. Learn: 提取成功模式和失败模式
5. Decide: 生成下一批内容优化策略
6. Act: 输出内容优化策略文件，供内容Agent消费
7. Measure: 下一轮运行时对比效果

使用方式：
    python scripts/content_learning_closed_loop.py --run
    python scripts/content_learning_closed_loop.py --analyze-only
    python scripts/content_learning_closed_loop.py --generate-strategy
"""

import os
import sys
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
CONTENT_DIR = REPORTS_DIR / "content"
CONTENT_DIR.mkdir(parents=True, exist_ok=True)
GROWTH_MEMORY_DIR = REPORTS_DIR / "growth_memory"

# 输出文件
CONTENT_STRATEGY_FILE = CONTENT_DIR / "content_optimization_strategy.json"
CONTENT_LEARNING_REPORT = CONTENT_DIR / "content_learning_report.md"
CONTENT_PERFORMANCE_HISTORY = CONTENT_DIR / "content_performance_history.json"


class ContentLearningClosedLoop:
    """Content Learning 闭环系统"""

    def __init__(self):
        self.performance_history = self._load_performance_history()
        self.current_strategy = self._load_current_strategy()

    def _load_performance_history(self) -> Dict[str, Any]:
        """加载内容表现历史"""
        if CONTENT_PERFORMANCE_HISTORY.exists():
            try:
                with open(CONTENT_PERFORMANCE_HISTORY, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"  ⚠️ 加载内容表现历史失败: {e}")
        return {"records": [], "last_updated": None, "version": "1.0"}

    def _load_current_strategy(self) -> Dict[str, Any]:
        """加载当前内容优化策略"""
        if CONTENT_STRATEGY_FILE.exists():
            try:
                with open(CONTENT_STRATEGY_FILE, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"  ⚠️ 加载当前策略失败: {e}")
        # 默认策略
        return {
            "version": "1.0-default",
            "last_updated": datetime.now().isoformat(),
            "content_rules": {
                "min_word_count": 1500,
                "target_word_count": 2000,
                "keyword_density_min": 0.5,
                "keyword_density_max": 2.5,
                "internal_links_min": 3,
                "external_links_min": 1,
                "cta_required": True,
                "schema_required": True,
                "image_alt_required": True
            },
            "best_practices": {
                "title_length": "50-60字符",
                "meta_description_length": "150-160字符",
                "heading_structure": "H1-H2-H3层级清晰",
                "paragraph_length": "每段不超过4行",
                "cta_position": "文章中部和底部"
            },
            "high_priority_articles": [],
            "learning_insights": [],
            "strategy_changes": []
        }

    def observe_and_record(self) -> List[Dict[str, Any]]:
        """步骤1+2: Observe观察内容表现并Record记录"""
        print("\n" + "=" * 60)
        print("  步骤1+2: Observe + Record - 观察并记录内容表现")
        print("=" * 60)

        new_records = []

        # 从内容审计报告提取数据
        content_audit_file = REPORTS_DIR / "content" / "content_audit_report.json"
        if content_audit_file.exists():
            try:
                with open(content_audit_file, encoding="utf-8") as f:
                    audit_data = json.load(f)

                articles = audit_data.get("articles", audit_data.get("content", []))
                if isinstance(articles, list):
                    for article in articles:
                        content_id = article.get("content_id", article.get("id", ""))
                        if content_id and not any(r.get("content_id") == content_id for r in self.performance_history["records"]):
                            record = {
                                "content_id": content_id,
                                "title": article.get("title", ""),
                                "date": datetime.now().isoformat(),
                                "metrics": {
                                    "word_count": article.get("word_count", article.get("words", 0)),
                                    "views": article.get("views", article.get("page_views", 0)),
                                    "visitors": article.get("visitors", 0),
                                    "avg_duration": article.get("avg_duration", article.get("time_on_page", 0)),
                                    "bounce_rate": article.get("bounce_rate", 0),
                                    "affiliate_clicks": article.get("affiliate_clicks", 0),
                                    "conversions": article.get("conversions", 0),
                                    "revenue": article.get("revenue", 0.0),
                                    "quality_score": article.get("quality_score", article.get("score", 0))
                                },
                                "metadata": {
                                    "category": article.get("category", ""),
                                    "keywords": article.get("keywords", []),
                                    "publish_date": article.get("publish_date", article.get("date", "")),
                                    "cta_count": article.get("cta_count", 0),
                                    "internal_links": article.get("internal_links", 0),
                                    "external_links": article.get("external_links", 0),
                                    "has_schema": article.get("has_schema", False),
                                    "has_cta": article.get("has_cta", False)
                                },
                                "calculated": {
                                    "ctr": article.get("affiliate_clicks", 0) / max(1, article.get("views", 1)) if article.get("views", 0) > 0 else 0,
                                    "revenue_per_1000_views": (article.get("revenue", 0.0) / max(1, article.get("views", 1)) * 1000) if article.get("views", 0) > 0 else 0,
                                    "engagement_score": (article.get("avg_duration", 0) / 60) * (1 - article.get("bounce_rate", 0) / 100) if article.get("bounce_rate", 0) > 0 else 0
                                }
                            }
                            self.performance_history["records"].append(record)
                            new_records.append(record)
                            print(f"  ✅ 记录: {record['title'][:40]}... (浏览:{record['metrics']['views']}, 质量分:{record['metrics']['quality_score']})")

            except Exception as e:
                print(f"  ⚠️ 处理内容审计数据失败: {e}")

        # 保存表现历史
        self.performance_history["last_updated"] = datetime.now().isoformat()
        with open(CONTENT_PERFORMANCE_HISTORY, "w", encoding="utf-8") as f:
            json.dump(self.performance_history, f, ensure_ascii=False, indent=2)

        print(f"\n  📊 新增记录: {len(new_records)} 条")
        print(f"  📊 历史总记录: {len(self.performance_history['records'])} 条")

        return new_records

    def analyze_and_learn(self) -> Dict[str, Any]:
        """步骤3+4: Analyze分析 + Learn学习成功模式"""
        print("\n" + "=" * 60)
        print("  步骤3+4: Analyze + Learn - 分析并学习内容成功模式")
        print("=" * 60)

        insights = {
            "generated_at": datetime.now().isoformat(),
            "overall_metrics": {},
            "best_categories": [],
            "best_keywords": [],
            "best_structures": [],
            "high_performance_articles": [],
            "low_performance_articles": [],
            "success_patterns": [],
            "failure_patterns": [],
            "recommendations": []
        }

        records = self.performance_history["records"]
        if not records:
            print("  ⚠️ 没有足够的历史数据进行分析，使用默认策略")
            return insights

        print(f"\n  📊 分析 {len(records)} 篇文章...")

        # 整体指标
        total_views = sum(r["metrics"]["views"] for r in records)
        total_revenue = sum(r["metrics"]["revenue"] for r in records)
        avg_quality = sum(r["metrics"]["quality_score"] for r in records) / len(records) if records else 0
        avg_word_count = sum(r["metrics"]["word_count"] for r in records) / len(records) if records else 0

        insights["overall_metrics"] = {
            "total_articles": len(records),
            "total_views": total_views,
            "total_revenue": total_revenue,
            "avg_quality_score": avg_quality,
            "avg_word_count": avg_word_count,
            "avg_rpm": (total_revenue / max(1, total_views) * 1000) if total_views > 0 else 0
        }

        print(f"  📈 整体表现:")
        print(f"     平均质量分: {avg_quality:.1f}")
        print(f"     平均字数: {avg_word_count:.0f}")
        print(f"     总浏览: {total_views}")
        print(f"     总收入: ${total_revenue:.2f}")

        # 按分类统计
        category_stats = defaultdict(lambda: {"count": 0, "views": 0, "revenue": 0, "quality": 0})
        for r in records:
            category = r["metadata"].get("category", "unknown")
            category_stats[category]["count"] += 1
            category_stats[category]["views"] += r["metrics"]["views"]
            category_stats[category]["revenue"] += r["metrics"]["revenue"]
            category_stats[category]["quality"] += r["metrics"]["quality_score"]

        sorted_categories = sorted(category_stats.items(), key=lambda x: x[1]["revenue"] / max(1, x[1]["views"]), reverse=True)
        insights["best_categories"] = [{"category": cat, "count": stats["count"], "avg_rpm": (stats["revenue"] / max(1, stats["views"]) * 1000) if stats["views"] > 0 else 0} for cat, stats in sorted_categories[:5]]

        # 按质量分排序
        sorted_by_quality = sorted(records, key=lambda x: x["metrics"]["quality_score"], reverse=True)
        insights["high_performance_articles"] = sorted_by_quality[:10]
        insights["low_performance_articles"] = sorted_by_quality[-10:]

        # 识别成功模式
        high_quality = sorted_by_quality[:max(1, len(sorted_by_quality) // 5)]
        low_quality = sorted_by_quality[-max(1, len(sorted_by_quality) // 5):]

        if high_quality:
            avg_high_words = sum(r["metrics"]["word_count"] for r in high_quality) / len(high_quality)
            avg_high_links = sum(r["metadata"].get("internal_links", 0) for r in high_quality) / len(high_quality)
            avg_high_cta = sum(r["metadata"].get("cta_count", 0) for r in high_quality) / len(high_quality)

            insights["success_patterns"].append({
                "pattern": "高质量文章特征",
                "description": f"Top 20%高质量文章平均字数 {avg_high_words:.0f}，平均内链 {avg_high_links:.1f}，平均CTA {avg_high_cta:.1f}",
                "recommendations": [
                    f"目标字数: {avg_high_words:.0f}字以上",
                    f"内链数量: 至少 {avg_high_links:.0f} 个",
                    f"CTA数量: 至少 {avg_high_cta:.0f} 个"
                ]
            })

        # 生成建议
        insights["recommendations"] = self._generate_content_recommendations(insights)

        print(f"\n  💡 识别成功模式: {len(insights['success_patterns'])} 个")
        print(f"  🚀 生成优化建议: {len(insights['recommendations'])} 条")

        return insights

    def _generate_content_recommendations(self, insights: Dict[str, Any]) -> List[Dict[str, Any]]:
        """基于学习洞察生成内容优化建议"""
        recommendations = []

        # 低质量文章优化
        if insights.get("low_performance_articles"):
            low_articles = insights["low_performance_articles"][:5]
            recommendations.append({
                "priority": "high",
                "type": "content_optimization",
                "title": f"优化 {len(low_articles)} 篇低质量文章",
                "description": "这些文章质量分低于平均水平，需要深度优化",
                "action": "扩充字数、增加内链、优化CTA、补充结构化数据",
                "articles": [a["title"][:50] for a in low_articles]
            })

        # 高表现分类扩展
        if insights.get("best_categories"):
            best_category = insights["best_categories"][0]
            recommendations.append({
                "priority": "high",
                "type": "content_expansion",
                "title": f"扩展高表现分类: {best_category['category']}",
                "description": f"该分类平均RPM ${best_category['avg_rpm']:.2f}，表现优于其他分类",
                "action": f"新增3-5篇 {best_category['category']} 分类的文章"
            })

        # 通用建议
        recommendations.append({
            "priority": "medium",
            "type": "content_quality",
            "title": "提升整体内容质量",
            "description": f"当前平均质量分 {insights['overall_metrics'].get('avg_quality_score', 0):.1f}，目标提升到80分以上",
            "action": "建立内容质量检查清单，发布前自动审核"
        })

        return recommendations

    def decide_and_update_strategy(self, insights: Dict[str, Any]) -> Dict[str, Any]:
        """步骤5+6: Decide决策 + Act行动 - 更新内容优化策略"""
        print("\n" + "=" * 60)
        print("  步骤5+6: Decide + Act - 决策并更新内容优化策略")
        print("=" * 60)

        strategy_changes = []

        # 更新高优先级文章列表
        if insights.get("low_performance_articles"):
            old_priority = self.current_strategy.get("high_priority_articles", [])
            new_priority = [{"content_id": a["content_id"], "title": a["title"][:60], "quality_score": a["metrics"]["quality_score"], "reason": "质量分低于平均水平"} for a in insights["low_performance_articles"][:10]]
            if old_priority != new_priority:
                self.current_strategy["high_priority_articles"] = new_priority
                strategy_changes.append({
                    "field": "high_priority_articles",
                    "old_count": len(old_priority),
                    "new_count": len(new_priority),
                    "reason": "基于质量分分析，更新高优先级优化文章列表"
                })
                print(f"  ✅ 更新高优先级文章列表: {len(old_priority)}篇 → {len(new_priority)}篇")

        # 更新学习洞察
        self.current_strategy["learning_insights"] = insights.get("success_patterns", [])
        self.current_strategy["strategy_changes"] = strategy_changes
        self.current_strategy["last_updated"] = datetime.now().isoformat()
        self.current_strategy["version"] = f"2.0-{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 保存策略
        with open(CONTENT_STRATEGY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.current_strategy, f, ensure_ascii=False, indent=2)

        print(f"\n  📊 策略变更: {len(strategy_changes)} 项")
        print(f"  📄 策略文件: {CONTENT_STRATEGY_FILE}")

        return self.current_strategy

    def generate_learning_report(self, insights: Dict[str, Any], strategy: Dict[str, Any]):
        """生成学习报告"""
        print("\n" + "=" * 60)
        print("  生成Content Learning闭环报告")
        print("=" * 60)

        report = f"""# ChinaBound Travel Content Learning 闭环报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**闭环版本**: 2.0
**策略版本**: {strategy.get('version', 'unknown')}

---

## 🔄 闭环状态

```
Observe ✅ → Record ✅ → Analyze ✅ → Learn ✅ → Decide ✅ → Act ✅ → Measure ⏳ → Learn Again 🔄
```

**当前状态**: Content Learning完整闭环已建立，等待下一轮效果测量验证

---

## 📊 内容统计

| 指标 | 数值 |
|------|------|
| 文章总数 | {insights['overall_metrics'].get('total_articles', 0)} |
| 总浏览量 | {insights['overall_metrics'].get('total_views', 0)} |
| 总收入 | ${insights['overall_metrics'].get('total_revenue', 0):.2f} |
| 平均质量分 | {insights['overall_metrics'].get('avg_quality_score', 0):.1f} |
| 平均字数 | {insights['overall_metrics'].get('avg_word_count', 0):.0f} |
| 平均RPM | ${insights['overall_metrics'].get('avg_rpm', 0):.2f} |

---

## 🏆 高表现分类

"""

        for i, cat in enumerate(insights.get("best_categories", [])[:5], 1):
            report += f"{i}. **{cat['category']}** - {cat['count']}篇，平均RPM ${cat['avg_rpm']:.2f}\n"

        report += """

---

## 🎯 高优先级优化文章

"""

        for i, article in enumerate(strategy.get("high_priority_articles", [])[:10], 1):
            report += f"{i}. **{article['title']}** - 质量分: {article['quality_score']:.1f}\n"

        report += """

---

## 💡 学习洞察

"""

        for i, pattern in enumerate(insights.get("success_patterns", []), 1):
            report += f"### {i}. {pattern['pattern']}\n"
            report += f"{pattern['description']}\n\n"
            if pattern.get("recommendations"):
                report += "**建议:**\n"
                for rec in pattern["recommendations"]:
                    report += f"- {rec}\n"
            report += "\n"

        report += """---

## 🚀 优化建议

"""

        for i, rec in enumerate(insights.get("recommendations", []), 1):
            priority_icon = "🔴" if rec["priority"] == "high" else "🟡" if rec["priority"] == "medium" else "🟢"
            report += f"{priority_icon} **{rec['title']}**\n"
            report += f"   - 描述: {rec['description']}\n"
            report += f"   - 行动: {rec['action']}\n\n"

        report += f"""---

## 📋 策略变更

"""

        if strategy.get("strategy_changes"):
            for i, change in enumerate(strategy["strategy_changes"], 1):
                report += f"{i}. **{change['field']}**\n"
                report += f"   - 旧值: {change.get('old_count', change.get('old', '-'))}\n"
                report += f"   - 新值: {change.get('new_count', change.get('new', '-'))}\n"
                report += f"   - 原因: {change['reason']}\n\n"
        else:
            report += "本轮无策略变更（数据不足或当前策略已最优）\n"

        report += f"""---

## 💡 核心价值

Content Learning闭环实现了：
- **从经验驱动到数据驱动**: 内容优化基于真实表现数据，而非主观判断
- **从静态策略到动态优化**: 优化策略每周自动更新，持续进化
- **从人工分析到自动学习**: AI自动识别成功模式，生成优化建议
- **从单点优化到系统进化**: 形成完整的学习闭环，持续提升内容质量

---

*报告由Content Learning闭环系统自动生成*
*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

        with open(CONTENT_LEARNING_REPORT, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"  ✅ 学习报告已生成: {CONTENT_LEARNING_REPORT}")

    def run_full_closed_loop(self):
        """运行完整闭环"""
        print("\n" + "=" * 60)
        print("  ChinaBound Travel Content Learning 完整闭环运行")
        print("=" * 60)
        print(f"\n  运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # 步骤1+2: Observe + Record
        new_records = self.observe_and_record()

        # 步骤3+4: Analyze + Learn
        insights = self.analyze_and_learn()
        insights["new_records"] = new_records

        # 步骤5+6: Decide + Act
        strategy = self.decide_and_update_strategy(insights)

        # 生成报告
        self.generate_learning_report(insights, strategy)

        # 总结
        print("\n" + "=" * 60)
        print("  Content Learning 完整闭环运行完成")
        print("=" * 60)
        print(f"\n  ✅ Observe: 观察完成")
        print(f"  ✅ Record: 记录完成 ({len(new_records)}条新记录)")
        print(f"  ✅ Analyze: 分析完成")
        print(f"  ✅ Learn: 学习完成 ({len(insights.get('success_patterns', []))}个模式)")
        print(f"  ✅ Decide: 决策完成")
        print(f"  ✅ Act: 行动完成 ({len(strategy.get('strategy_changes', []))}项策略变更)")
        print(f"  ⏳ Measure: 等待下一轮效果测量")
        print(f"\n  📄 策略文件: {CONTENT_STRATEGY_FILE}")
        print(f"  📄 学习报告: {CONTENT_LEARNING_REPORT}")
        print(f"\n  🎯 闭环状态: 完整闭环已建立，持续进化中")

        return {
            "new_records": len(new_records),
            "insights": insights,
            "strategy_changes": len(strategy.get("strategy_changes", [])),
            "strategy_file": str(CONTENT_STRATEGY_FILE),
            "report_file": str(CONTENT_LEARNING_REPORT)
        }


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Content Learning 闭环系统")
    parser.add_argument("--run", action="store_true", help="运行完整闭环")
    parser.add_argument("--analyze-only", action="store_true", help="仅分析不更新策略")
    parser.add_argument("--generate-strategy", action="store_true", help="仅生成策略")

    args = parser.parse_args()

    loop = ContentLearningClosedLoop()

    if args.run:
        loop.run_full_closed_loop()
    elif args.analyze_only:
        insights = loop.analyze_and_learn()
        print(json.dumps(insights, ensure_ascii=False, indent=2))
    elif args.generate_strategy:
        insights = loop.analyze_and_learn()
        strategy = loop.decide_and_update_strategy(insights)
        print(json.dumps(strategy, ensure_ascii=False, indent=2))
    else:
        loop.run_full_closed_loop()


if __name__ == "__main__":
    main()
