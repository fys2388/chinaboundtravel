#!/usr/bin/env python3
"""
ChinaBound Travel - Social Learning 闭环系统
Social Learning Closed Loop

核心功能：打通 Observe → Learn → Decide → Act → Measure → Learn 完整闭环

闭环流程：
1. Observe: 从Buffer/社媒报告获取发布效果数据
2. Record: 记录到Growth Memory
3. Analyze: 分析哪些Hook/CTA/发布时间/平台效果好
4. Learn: 提取成功模式和失败模式
5. Decide: 生成下一批社媒发布策略
6. Act: 输出更新后的策略文件，供Social Engine消费
7. Measure: 下一轮运行时对比效果

使用方式：
    python scripts/social_learning_closed_loop.py --run
    python scripts/social_learning_closed_loop.py --analyze-only
    python scripts/social_learning_closed_loop.py --generate-strategy
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
GROWTH_MEMORY_DIR = REPORTS_DIR / "growth_memory"
SOCIAL_DIR = REPORTS_DIR / "social"
SOCIAL_DIR.mkdir(parents=True, exist_ok=True)

# 输出文件
SOCIAL_STRATEGY_FILE = SOCIAL_DIR / "social_publish_strategy.json"
SOCIAL_LEARNING_REPORT = SOCIAL_DIR / "social_learning_report.md"
SOCIAL_PERFORMANCE_HISTORY = SOCIAL_DIR / "social_performance_history.json"


class SocialLearningClosedLoop:
    """Social Learning 闭环系统"""

    def __init__(self):
        self.growth_memory = self._load_growth_memory()
        self.performance_history = self._load_performance_history()
        self.current_strategy = self._load_current_strategy()

    def _load_growth_memory(self) -> Dict[str, Any]:
        """加载Growth Memory"""
        social_memory_file = GROWTH_MEMORY_DIR / "social_memory.json"
        if social_memory_file.exists():
            try:
                with open(social_memory_file, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"  ⚠️ 加载Growth Memory失败: {e}")
        return {"records": [], "last_updated": None}

    def _load_performance_history(self) -> Dict[str, Any]:
        """加载社媒表现历史"""
        if SOCIAL_PERFORMANCE_HISTORY.exists():
            try:
                with open(SOCIAL_PERFORMANCE_HISTORY, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"  ⚠️ 加载社媒表现历史失败: {e}")
        return {"records": [], "last_updated": None, "version": "1.0"}

    def _load_current_strategy(self) -> Dict[str, Any]:
        """加载当前发布策略"""
        if SOCIAL_STRATEGY_FILE.exists():
            try:
                with open(SOCIAL_STRATEGY_FILE, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"  ⚠️ 加载当前策略失败: {e}")
        # 默认策略
        return {
            "version": "1.0-default",
            "last_updated": datetime.now().isoformat(),
            "platforms": {
                "pinterest": {
                    "best_times": ["09:00", "14:00", "20:00"],
                    "best_hooks": ["travel tips", "itinerary", "guide"],
                    "best_ctas": ["save for later", "click to read"],
                    "content_types": ["guide", "tips", "itinerary"],
                    "max_posts_per_day": 3
                },
                "instagram": {
                    "best_times": ["10:00", "18:00", "21:00"],
                    "best_hooks": ["beautiful places", "travel inspiration"],
                    "best_ctas": ["link in bio", "swipe up"],
                    "content_types": ["visual", "lifestyle", "tips"],
                    "max_posts_per_day": 2
                },
                "facebook": {
                    "best_times": ["09:00", "13:00", "19:00"],
                    "best_hooks": ["travel tips", "guide", "checklist"],
                    "best_ctas": ["read more", "click here"],
                    "content_types": ["guide", "tips", "news"],
                    "max_posts_per_day": 2
                },
                "x": {
                    "best_times": ["08:00", "12:00", "17:00"],
                    "best_hooks": ["quick tips", "thread", "facts"],
                    "best_ctas": ["read thread", "click link"],
                    "content_types": ["tips", "facts", "thread"],
                    "max_posts_per_day": 3
                }
            },
            "global_rules": {
                "max_posts_per_day_per_platform": 3,
                "min_interval_minutes": 120,
                "use_utm_tracking": True,
                "brand_voice": "editorial",
                "avoid_legacy_persona": True
            },
            "learning_insights": [],
            "strategy_changes": []
        }

    def observe_and_record(self) -> List[Dict[str, Any]]:
        """步骤1+2: Observe观察社媒表现并Record记录到Growth Memory"""
        print("\n" + "=" * 60)
        print("  步骤1+2: Observe + Record - 观察并记录社媒表现")
        print("=" * 60)

        new_records = []

        # 从社媒报告文件中提取数据
        social_report_files = list(SOCIAL_DIR.glob("*report*.json")) + list(SOCIAL_DIR.glob("*performance*.json"))

        for report_file in social_report_files:
            try:
                with open(report_file, encoding="utf-8") as f:
                    report_data = json.load(f)

                # 提取帖子数据
                posts = report_data.get("posts", report_data.get("social_posts", []))
                if isinstance(posts, list):
                    for post in posts:
                        platform = post.get("platform", post.get("channel", "unknown")).lower()
                        post_id = post.get("id", post.get("post_id", ""))

                        # 检查是否已记录
                        if not any(r.get("post_id") == post_id for r in self.performance_history["records"]):
                            record = {
                                "post_id": post_id,
                                "platform": platform,
                                "date": post.get("publish_time", post.get("date", datetime.now().isoformat())),
                                "content": {
                                    "hook": post.get("hook", post.get("caption", post.get("title", ""))),
                                    "cta": post.get("cta", ""),
                                    "content_id": post.get("content_id", post.get("article_id", "")),
                                    "content_type": post.get("type", post.get("content_type", ""))
                                },
                                "metrics": {
                                    "impressions": post.get("impressions", post.get("views", 0)),
                                    "clicks": post.get("clicks", post.get("link_clicks", 0)),
                                    "likes": post.get("likes", 0),
                                    "comments": post.get("comments", 0),
                                    "shares": post.get("shares", 0),
                                    "saves": post.get("saves", 0)
                                }
                            }
                            record["metrics"]["engagement"] = (
                                record["metrics"]["likes"] +
                                record["metrics"]["comments"] +
                                record["metrics"]["shares"] +
                                record["metrics"]["saves"]
                            )
                            record["calculated"] = {
                                "ctr": record["metrics"]["clicks"] / max(1, record["metrics"]["impressions"]) if record["metrics"]["impressions"] > 0 else 0,
                                "engagement_rate": record["metrics"]["engagement"] / max(1, record["metrics"]["impressions"]) if record["metrics"]["impressions"] > 0 else 0
                            }

                            self.performance_history["records"].append(record)
                            new_records.append(record)
                            print(f"  ✅ 记录: [{platform}] {record['content']['hook'][:40]}... (CTR: {record['calculated']['ctr']*100:.2f}%)")

            except Exception as e:
                print(f"  ⚠️ 处理 {report_file.name} 失败: {e}")

        # 保存表现历史
        self.performance_history["last_updated"] = datetime.now().isoformat()
        with open(SOCIAL_PERFORMANCE_HISTORY, "w", encoding="utf-8") as f:
            json.dump(self.performance_history, f, ensure_ascii=False, indent=2)

        print(f"\n  📊 新增记录: {len(new_records)} 条")
        print(f"  📊 历史总记录: {len(self.performance_history['records'])} 条")

        return new_records

    def analyze_and_learn(self) -> Dict[str, Any]:
        """步骤3+4: Analyze分析 + Learn学习成功模式"""
        print("\n" + "=" * 60)
        print("  步骤3+4: Analyze + Learn - 分析并学习成功模式")
        print("=" * 60)

        insights = {
            "generated_at": datetime.now().isoformat(),
            "platform_performance": {},
            "best_hooks": [],
            "best_ctas": [],
            "best_times": [],
            "best_content_types": [],
            "success_patterns": [],
            "failure_patterns": [],
            "recommendations": []
        }

        records = self.performance_history["records"]
        if not records:
            print("  ⚠️ 没有足够的历史数据进行分析，使用默认策略")
            return insights

        print(f"\n  📊 分析 {len(records)} 条历史记录...")

        # 1. 平台表现分析
        platform_stats = defaultdict(lambda: {
            "impressions": 0, "clicks": 0, "engagement": 0,
            "count": 0, "ctr_list": [], "engagement_list": []
        })

        for r in records:
            platform = r["platform"]
            platform_stats[platform]["impressions"] += r["metrics"]["impressions"]
            platform_stats[platform]["clicks"] += r["metrics"]["clicks"]
            platform_stats[platform]["engagement"] += r["metrics"]["engagement"]
            platform_stats[platform]["count"] += 1
            platform_stats[platform]["ctr_list"].append(r["calculated"]["ctr"])
            platform_stats[platform]["engagement_list"].append(r["calculated"]["engagement_rate"])

        for platform, stats in platform_stats.items():
            avg_ctr = sum(stats["ctr_list"]) / len(stats["ctr_list"]) if stats["ctr_list"] else 0
            avg_engagement = sum(stats["engagement_list"]) / len(stats["engagement_list"]) if stats["engagement_list"] else 0
            insights["platform_performance"][platform] = {
                "total_posts": stats["count"],
                "total_impressions": stats["impressions"],
                "total_clicks": stats["clicks"],
                "avg_ctr": avg_ctr,
                "avg_engagement_rate": avg_engagement,
                "performance_rating": "excellent" if avg_ctr > 0.05 else "good" if avg_ctr > 0.02 else "average" if avg_ctr > 0.01 else "needs_improvement"
            }
            print(f"  📱 {platform}: {stats['count']}条, 平均CTR {avg_ctr*100:.2f}%, 评级: {insights['platform_performance'][platform]['performance_rating']}")

        # 2. 按CTR排序，找出Top表现
        sorted_by_ctr = sorted(records, key=lambda x: x["calculated"]["ctr"], reverse=True)
        top_20_percent = sorted_by_ctr[:max(1, len(sorted_by_ctr) // 5)]
        bottom_20_percent = sorted_by_ctr[-max(1, len(sorted_by_ctr) // 5):]

        # 3. 分析Top表现的Hook模式
        hook_keywords = defaultdict(lambda: {"count": 0, "total_ctr": 0, "posts": []})
        for r in top_20_percent:
            hook = r["content"]["hook"].lower()
            # 提取关键词
            keywords = re.findall(r'\b\w{4,}\b', hook)
            for kw in keywords[:5]:
                hook_keywords[kw]["count"] += 1
                hook_keywords[kw]["total_ctr"] += r["calculated"]["ctr"]
                hook_keywords[kw]["posts"].append(r["post_id"])

        sorted_hooks = sorted(hook_keywords.items(), key=lambda x: x[1]["total_ctr"] / max(1, x[1]["count"]), reverse=True)
        insights["best_hooks"] = [{"keyword": kw, "avg_ctr": stats["total_ctr"] / max(1, stats["count"]), "count": stats["count"]} for kw, stats in sorted_hooks[:10]]

        # 4. 分析最佳发布时间
        time_performance = defaultdict(lambda: {"count": 0, "total_ctr": 0})
        for r in records:
            try:
                publish_time = datetime.fromisoformat(r["date"].replace("Z", "+00:00"))
                hour = publish_time.hour
                time_performance[hour]["count"] += 1
                time_performance[hour]["total_ctr"] += r["calculated"]["ctr"]
            except:
                pass

        sorted_times = sorted(time_performance.items(), key=lambda x: x[1]["total_ctr"] / max(1, x[1]["count"]), reverse=True)
        insights["best_times"] = [{"hour": hour, "avg_ctr": stats["total_ctr"] / max(1, stats["count"]), "count": stats["count"]} for hour, stats in sorted_times[:5]]

        # 5. 识别成功模式
        if top_20_percent:
            avg_top_ctr = sum(r["calculated"]["ctr"] for r in top_20_percent) / len(top_20_percent)
            avg_bottom_ctr = sum(r["calculated"]["ctr"] for r in bottom_20_percent) / len(bottom_20_percent) if bottom_20_percent else 0

            insights["success_patterns"].append({
                "pattern": "高CTR帖子特征",
                "description": f"Top 20%帖子平均CTR {avg_top_ctr*100:.2f}%，比Bottom 20%高 {(avg_top_ctr - avg_bottom_ctr)*100:.2f}个百分点",
                "common_hooks": [h["keyword"] for h in insights["best_hooks"][:5]],
                "best_times": [f"{t['hour']}:00" for t in insights["best_times"][:3]]
            })

        # 6. 生成建议
        insights["recommendations"] = self._generate_strategy_recommendations(insights)

        print(f"\n  💡 识别成功模式: {len(insights['success_patterns'])} 个")
        print(f"  🚀 生成优化建议: {len(insights['recommendations'])} 条")

        return insights

    def _generate_strategy_recommendations(self, insights: Dict[str, Any]) -> List[Dict[str, Any]]:
        """基于学习洞察生成策略建议"""
        recommendations = []

        # 平台表现建议
        for platform, perf in insights.get("platform_performance", {}).items():
            if perf["performance_rating"] == "needs_improvement":
                recommendations.append({
                    "priority": "high",
                    "type": "platform_optimization",
                    "platform": platform,
                    "title": f"优化{platform}表现",
                    "description": f"{platform}当前CTR {perf['avg_ctr']*100:.2f}%，低于平均水平，需要优化Hook和发布时间",
                    "action": f"增加{platform}高CTR Hook类型，调整发布时间到最佳时段"
                })

        # 最佳Hook建议
        if insights.get("best_hooks"):
            best_hook = insights["best_hooks"][0]
            recommendations.append({
                "priority": "high",
                "type": "hook_optimization",
                "title": f"推广高CTR Hook: {best_hook['keyword']}",
                "description": f"包含'{best_hook['keyword']}'的帖子平均CTR {best_hook['avg_ctr']*100:.2f}%，建议在更多帖子中使用",
                "action": "下一批帖子中50%使用此类Hook"
            })

        # 最佳发布时间建议
        if insights.get("best_times"):
            best_time = insights["best_times"][0]
            recommendations.append({
                "priority": "medium",
                "type": "timing_optimization",
                "title": f"调整发布时间到 {best_time['hour']}:00",
                "description": f"{best_time['hour']}:00发布的帖子平均CTR {best_time['avg_ctr']*100:.2f}%，是最佳时段",
                "action": f"将主要发布时间调整到 {best_time['hour']}:00"
            })

        return recommendations

    def decide_and_update_strategy(self, insights: Dict[str, Any]) -> Dict[str, Any]:
        """步骤5+6: Decide决策 + Act行动 - 更新发布策略"""
        print("\n" + "=" * 60)
        print("  步骤5+6: Decide + Act - 决策并更新发布策略")
        print("=" * 60)

        strategy_changes = []

        # 1. 更新平台最佳时间
        if insights.get("best_times"):
            for platform in self.current_strategy["platforms"]:
                old_times = self.current_strategy["platforms"][platform]["best_times"]
                new_times = [f"{t['hour']:02d}:00" for t in insights["best_times"][:3]]
                if old_times != new_times:
                    self.current_strategy["platforms"][platform]["best_times"] = new_times
                    strategy_changes.append({
                        "field": f"{platform}.best_times",
                        "old": old_times,
                        "new": new_times,
                        "reason": f"基于历史数据分析，最佳CTR时段为 {', '.join(new_times)}"
                    })
                    print(f"  ✅ 更新{platform}发布时间: {old_times} → {new_times}")

        # 2. 更新最佳Hook
        if insights.get("best_hooks"):
            for platform in self.current_strategy["platforms"]:
                old_hooks = self.current_strategy["platforms"][platform]["best_hooks"]
                new_hooks = [h["keyword"] for h in insights["best_hooks"][:5]]
                if old_hooks != new_hooks:
                    self.current_strategy["platforms"][platform]["best_hooks"] = new_hooks
                    strategy_changes.append({
                        "field": f"{platform}.best_hooks",
                        "old": old_hooks,
                        "new": new_hooks,
                        "reason": "基于Top 20%高CTR帖子的Hook关键词分析"
                    })
                    print(f"  ✅ 更新{platform}Hook关键词: {len(old_hooks)}个 → {len(new_hooks)}个")

        # 3. 更新学习洞察
        self.current_strategy["learning_insights"] = insights.get("success_patterns", [])
        self.current_strategy["strategy_changes"] = strategy_changes
        self.current_strategy["last_updated"] = datetime.now().isoformat()
        self.current_strategy["version"] = f"2.0-{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 保存策略
        with open(SOCIAL_STRATEGY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.current_strategy, f, ensure_ascii=False, indent=2)

        print(f"\n  📊 策略变更: {len(strategy_changes)} 项")
        print(f"  📄 策略文件: {SOCIAL_STRATEGY_FILE}")

        return self.current_strategy

    def generate_learning_report(self, insights: Dict[str, Any], strategy: Dict[str, Any]):
        """生成学习报告"""
        print("\n" + "=" * 60)
        print("  生成Social Learning闭环报告")
        print("=" * 60)

        report = f"""# ChinaBound Travel Social Learning 闭环报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**闭环版本**: 2.0
**策略版本**: {strategy.get('version', 'unknown')}

---

## 🔄 闭环状态

```
Observe ✅ → Record ✅ → Analyze ✅ → Learn ✅ → Decide ✅ → Act ✅ → Measure ⏳ → Learn Again 🔄
```

**当前状态**: 完整闭环已建立，等待下一轮效果测量验证

---

## 📊 数据统计

| 指标 | 数值 |
|------|------|
| 历史帖子总数 | {len(self.performance_history['records'])} |
| 本轮新增记录 | {len(insights.get('new_records', []))} |
| 平台数量 | {len(insights.get('platform_performance', {}))} |
| 识别成功模式 | {len(insights.get('success_patterns', []))} |
| 策略变更项 | {len(strategy.get('strategy_changes', []))} |

---

## 📱 平台表现

"""

        for platform, perf in insights.get("platform_performance", {}).items():
            rating_icon = "🟢" if perf["performance_rating"] in ["excellent", "good"] else "🟡" if perf["performance_rating"] == "average" else "🔴"
            report += f"### {rating_icon} {platform}\n"
            report += f"- 帖子数: {perf['total_posts']}\n"
            report += f"- 总展示: {perf['total_impressions']}\n"
            report += f"- 总点击: {perf['total_clicks']}\n"
            report += f"- 平均CTR: {perf['avg_ctr']*100:.2f}%\n"
            report += f"- 平均互动率: {perf['avg_engagement_rate']*100:.2f}%\n"
            report += f"- 表现评级: {perf['performance_rating']}\n\n"

        report += """---

## 🏆 学习洞察

### 最佳Hook关键词

"""

        for i, hook in enumerate(insights.get("best_hooks", [])[:5], 1):
            report += f"{i}. **{hook['keyword']}** - 平均CTR: {hook['avg_ctr']*100:.2f}% (出现{hook['count']}次)\n"

        report += """

### 最佳发布时间

"""

        for i, time in enumerate(insights.get("best_times", [])[:3], 1):
            report += f"{i}. **{time['hour']:02d}:00** - 平均CTR: {time['avg_ctr']*100:.2f}% (出现{time['count']}次)\n"

        report += """

---

## 🎯 策略变更

"""

        if strategy.get("strategy_changes"):
            for i, change in enumerate(strategy["strategy_changes"], 1):
                report += f"{i}. **{change['field']}**\n"
                report += f"   - 旧值: {change['old']}\n"
                report += f"   - 新值: {change['new']}\n"
                report += f"   - 原因: {change['reason']}\n\n"
        else:
            report += "本轮无策略变更（数据不足或当前策略已最优）\n"

        report += """---

## 🚀 下一步行动

1. **Social Engine消费新策略**: 下一批社媒发布使用更新后的 `social_publish_strategy.json`
2. **效果测量**: 下一轮运行时对比新策略的CTR和互动率
3. **持续学习**: 每周运行本脚本，积累更多数据，优化策略
4. **扩展闭环**: 将学习闭环扩展到内容优化、转化优化等其他Agent

---

## 💡 核心价值

这个闭环系统实现了：
- **从经验驱动到数据驱动**: 发布策略基于真实历史数据，而非主观判断
- **从静态策略到动态优化**: 策略每周自动更新，持续进化
- **从人工分析到自动学习**: AI自动识别成功模式，生成优化建议
- **从单点优化到系统进化**: 形成完整的学习闭环，持续提升运营效果

---

*报告由Social Learning闭环系统自动生成*
*生成时间: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "*\n"

        with open(SOCIAL_LEARNING_REPORT, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"  ✅ 学习报告已生成: {SOCIAL_LEARNING_REPORT}")

    def run_full_closed_loop(self):
        """运行完整闭环"""
        print("\n" + "=" * 60)
        print("  ChinaBound Travel Social Learning 完整闭环运行")
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
        print("  Social Learning 完整闭环运行完成")
        print("=" * 60)
        print(f"\n  ✅ Observe: 观察完成")
        print(f"  ✅ Record: 记录完成 ({len(new_records)}条新记录)")
        print(f"  ✅ Analyze: 分析完成")
        print(f"  ✅ Learn: 学习完成 ({len(insights.get('success_patterns', []))}个模式)")
        print(f"  ✅ Decide: 决策完成")
        print(f"  ✅ Act: 行动完成 ({len(strategy.get('strategy_changes', []))}项策略变更)")
        print(f"  ⏳ Measure: 等待下一轮效果测量")
        print(f"\n  📄 策略文件: {SOCIAL_STRATEGY_FILE}")
        print(f"  📄 学习报告: {SOCIAL_LEARNING_REPORT}")
        print(f"\n  🎯 闭环状态: 完整闭环已建立，持续进化中")

        return {
            "new_records": len(new_records),
            "insights": insights,
            "strategy_changes": len(strategy.get("strategy_changes", [])),
            "strategy_file": str(SOCIAL_STRATEGY_FILE),
            "report_file": str(SOCIAL_LEARNING_REPORT)
        }


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="ChinaBound Travel Social Learning 闭环系统")
    parser.add_argument("--run", action="store_true", help="运行完整闭环")
    parser.add_argument("--analyze-only", action="store_true", help="仅分析不更新策略")
    parser.add_argument("--generate-strategy", action="store_true", help="仅生成策略")
    parser.add_argument("--show-insights", action="store_true", help="显示学习洞察")

    args = parser.parse_args()

    loop = SocialLearningClosedLoop()

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
        # 默认运行完整闭环
        loop.run_full_closed_loop()


if __name__ == "__main__":
    main()
