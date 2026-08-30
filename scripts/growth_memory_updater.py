#!/usr/bin/env python3
"""
ChinaBound Travel - Growth Memory 学习记忆系统
Growth Memory Updater

核心功能：记录所有运营动作的效果，形成可学习的记忆库
记录维度：
- 内容：文章ID、标题、关键词、分类、发布时间
- 社媒：平台、帖子ID、Hook、CTA、发布时间、展示、点击、互动
- 流量：页面浏览、访客、停留时长、跳出率
- 转化：联盟点击、订单、佣金、CTA类型、位置
- 效果：ROI、转化率、互动率、留存率

学习闭环：
Observe → Record → Analyze → Learn → Decide → Act → Measure → Update Memory

使用方式：
    python scripts/growth_memory_updater.py --weekly
    python scripts/growth_memory_updater.py --daily
    python scripts/growth_memory_updater.py --record-social --platform pinterest --post-id xxx --impressions 1000 --clicks 50
    python scripts/growth_memory_updater.py --record-content --content-id xxx --views 100 --affiliate-clicks 5
    python scripts/growth_memory_updater.py --analyze --top-performers
"""

import os
import sys
import json
import csv
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
GROWTH_MEMORY_DIR = REPORTS_DIR / "growth_memory"
GROWTH_MEMORY_DIR.mkdir(parents=True, exist_ok=True)

# Growth Memory 文件
CONTENT_MEMORY_FILE = GROWTH_MEMORY_DIR / "content_memory.json"
SOCIAL_MEMORY_FILE = GROWTH_MEMORY_DIR / "social_memory.json"
CONVERSION_MEMORY_FILE = GROWTH_MEMORY_DIR / "conversion_memory.json"
TRAFFIC_MEMORY_FILE = GROWTH_MEMORY_DIR / "traffic_memory.json"
LEARNING_INSIGHTS_FILE = GROWTH_MEMORY_DIR / "learning_insights.json"
GROWTH_MEMORY_SUMMARY_FILE = GROWTH_MEMORY_DIR / "growth_memory_summary.md"


class GrowthMemoryUpdater:
    """Growth Memory 学习记忆系统"""

    def __init__(self):
        self.content_memory = self._load_memory(CONTENT_MEMORY_FILE)
        self.social_memory = self._load_memory(SOCIAL_MEMORY_FILE)
        self.conversion_memory = self._load_memory(CONVERSION_MEMORY_FILE)
        self.traffic_memory = self._load_memory(TRAFFIC_MEMORY_FILE)
        self.learning_insights = self._load_memory(LEARNING_INSIGHTS_FILE)

    def _load_memory(self, file_path: Path) -> Dict[str, Any]:
        """加载记忆数据"""
        if file_path.exists():
            try:
                with open(file_path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"  ⚠️ 加载 {file_path.name} 失败: {e}")
        return {"records": [], "last_updated": None, "version": "1.0"}

    def _save_memory(self, file_path: Path, memory: Dict[str, Any]):
        """保存记忆数据"""
        memory["last_updated"] = datetime.now().isoformat()
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(memory, f, ensure_ascii=False, indent=2)

    def record_content_performance(self, content_id: str, title: str = "",
                                     views: int = 0, visitors: int = 0,
                                     avg_duration: float = 0, bounce_rate: float = 0,
                                     affiliate_clicks: int = 0, conversions: int = 0,
                                     revenue: float = 0.0, keywords: List[str] = None,
                                     category: str = "", publish_date: str = ""):
        """记录内容表现"""
        record = {
            "content_id": content_id,
            "title": title,
            "date": datetime.now().isoformat(),
            "metrics": {
                "views": views,
                "visitors": visitors,
                "avg_duration_seconds": avg_duration,
                "bounce_rate": bounce_rate,
                "affiliate_clicks": affiliate_clicks,
                "conversions": conversions,
                "revenue": revenue
            },
            "metadata": {
                "keywords": keywords or [],
                "category": category,
                "publish_date": publish_date
            },
            "calculated": {
                "ctr": affiliate_clicks / max(1, views) if views > 0 else 0,
                "conversion_rate": conversions / max(1, affiliate_clicks) if affiliate_clicks > 0 else 0,
                "revenue_per_1000_views": (revenue / max(1, views) * 1000) if views > 0 else 0
            }
        }

        # 检查是否已存在该content_id的记录，更新或追加
        existing = next((r for r in self.content_memory["records"] if r["content_id"] == content_id), None)
        if existing:
            # 累加数据
            existing["metrics"]["views"] += views
            existing["metrics"]["visitors"] += visitors
            existing["metrics"]["affiliate_clicks"] += affiliate_clicks
            existing["metrics"]["conversions"] += conversions
            existing["metrics"]["revenue"] += revenue
            existing["date"] = datetime.now().isoformat()
            existing["calculated"]["ctr"] = existing["metrics"]["affiliate_clicks"] / max(1, existing["metrics"]["views"])
            existing["calculated"]["conversion_rate"] = existing["metrics"]["conversions"] / max(1, existing["metrics"]["affiliate_clicks"])
            existing["calculated"]["revenue_per_1000_views"] = (existing["metrics"]["revenue"] / max(1, existing["metrics"]["views"]) * 1000)
        else:
            self.content_memory["records"].append(record)

        self._save_memory(CONTENT_MEMORY_FILE, self.content_memory)
        print(f"  ✅ 内容表现已记录: {content_id} (浏览:{views}, 联盟点击:{affiliate_clicks}, 收入:${revenue})")

    def record_social_performance(self, platform: str, post_id: str = "",
                                    hook: str = "", cta: str = "", content_id: str = "",
                                    impressions: int = 0, clicks: int = 0,
                                    likes: int = 0, comments: int = 0,
                                    shares: int = 0, saves: int = 0,
                                    publish_time: str = "", content_type: str = ""):
        """记录社媒表现"""
        engagement = likes + comments + shares + saves
        record = {
            "post_id": post_id or f"{platform}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "platform": platform,
            "date": datetime.now().isoformat(),
            "content": {
                "hook": hook,
                "cta": cta,
                "content_id": content_id,
                "content_type": content_type,
                "publish_time": publish_time
            },
            "metrics": {
                "impressions": impressions,
                "clicks": clicks,
                "likes": likes,
                "comments": comments,
                "shares": shares,
                "saves": saves,
                "engagement": engagement
            },
            "calculated": {
                "ctr": clicks / max(1, impressions) if impressions > 0 else 0,
                "engagement_rate": engagement / max(1, impressions) if impressions > 0 else 0,
                "click_per_engagement": clicks / max(1, engagement) if engagement > 0 else 0
            }
        }

        self.social_memory["records"].append(record)
        self._save_memory(SOCIAL_MEMORY_FILE, self.social_memory)
        print(f"  ✅ 社媒表现已记录: {platform} (展示:{impressions}, 点击:{clicks}, 互动:{engagement})")

    def record_conversion_event(self, cta_type: str, cta_position: str,
                                  cta_copy: str = "", content_id: str = "",
                                  impressions: int = 0, clicks: int = 0,
                                  conversions: int = 0, revenue: float = 0.0,
                                  partner: str = ""):
        """记录转化事件"""
        record = {
            "event_id": f"conv_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "date": datetime.now().isoformat(),
            "cta": {
                "type": cta_type,
                "position": cta_position,
                "copy": cta_copy,
                "content_id": content_id,
                "partner": partner
            },
            "metrics": {
                "impressions": impressions,
                "clicks": clicks,
                "conversions": conversions,
                "revenue": revenue
            },
            "calculated": {
                "ctr": clicks / max(1, impressions) if impressions > 0 else 0,
                "conversion_rate": conversions / max(1, clicks) if clicks > 0 else 0,
                "revenue_per_click": revenue / max(1, clicks) if clicks > 0 else 0
            }
        }

        self.conversion_memory["records"].append(record)
        self._save_memory(CONVERSION_MEMORY_FILE, self.conversion_memory)
        print(f"  ✅ 转化事件已记录: {cta_type} @ {cta_position} (点击:{clicks}, 转化:{conversions}, 收入:${revenue})")

    def analyze_top_performers(self, limit: int = 10) -> Dict[str, Any]:
        """分析Top表现内容和社媒帖子"""
        print("\n" + "=" * 60)
        print("  Growth Memory 分析 - Top表现")
        print("=" * 60)

        insights = {
            "generated_at": datetime.now().isoformat(),
            "top_content": [],
            "top_social_posts": [],
            "best_cta_types": [],
            "best_publish_times": [],
            "patterns": [],
            "recommendations": []
        }

        # Top内容（按收入/1000浏览排序）
        content_records = self.content_memory["records"]
        if content_records:
            sorted_content = sorted(content_records, key=lambda x: x["calculated"].get("revenue_per_1000_views", 0), reverse=True)
            insights["top_content"] = sorted_content[:limit]
            print(f"\n  📊 Top {limit} 内容（按RPM排序）:")
            for i, c in enumerate(sorted_content[:5], 1):
                print(f"    {i}. {c['title'][:50]}... RPM: ${c['calculated'].get('revenue_per_1000_views', 0):.2f}")

        # Top社媒帖子（按CTR排序）
        social_records = self.social_memory["records"]
        if social_records:
            sorted_social = sorted(social_records, key=lambda x: x["calculated"].get("ctr", 0), reverse=True)
            insights["top_social_posts"] = sorted_social[:limit]
            print(f"\n  📱 Top {limit} 社媒帖子（按CTR排序）:")
            for i, s in enumerate(sorted_social[:5], 1):
                print(f"    {i}. [{s['platform']}] {s['content'].get('hook', '')[:40]}... CTR: {s['calculated'].get('ctr', 0)*100:.2f}%")

        # 最佳CTA类型
        conversion_records = self.conversion_memory["records"]
        if conversion_records:
            cta_performance = defaultdict(lambda: {"clicks": 0, "conversions": 0, "revenue": 0, "count": 0})
            for c in conversion_records:
                cta_type = c["cta"]["type"]
                cta_performance[cta_type]["clicks"] += c["metrics"]["clicks"]
                cta_performance[cta_type]["conversions"] += c["metrics"]["conversions"]
                cta_performance[cta_type]["revenue"] += c["metrics"]["revenue"]
                cta_performance[cta_type]["count"] += 1

            for cta_type, perf in cta_performance.items():
                perf["ctr"] = perf["clicks"] / max(1, perf["count"] * 100)  # 假设每次展示100
                perf["conversion_rate"] = perf["conversions"] / max(1, perf["clicks"])

            sorted_cta = sorted(cta_performance.items(), key=lambda x: x[1]["conversion_rate"], reverse=True)
            insights["best_cta_types"] = [{"type": k, **v} for k, v in sorted_cta[:5]]
            print(f"\n  🎯 最佳CTA类型:")
            for cta_type, perf in sorted_cta[:3]:
                print(f"    - {cta_type}: 转化率 {perf['conversion_rate']*100:.2f}%, 收入 ${perf['revenue']:.2f}")

        # 模式识别
        patterns = self._identify_patterns()
        insights["patterns"] = patterns

        # 生成建议
        recommendations = self._generate_recommendations(insights)
        insights["recommendations"] = recommendations

        # 保存洞察
        self.learning_insights["latest"] = insights
        self.learning_insights["history"] = self.learning_insights.get("history", [])
        self.learning_insights["history"].append({
            "generated_at": insights["generated_at"],
            "top_content_count": len(insights["top_content"]),
            "top_social_count": len(insights["top_social_posts"]),
            "pattern_count": len(patterns),
            "recommendation_count": len(recommendations)
        })
        self._save_memory(LEARNING_INSIGHTS_FILE, self.learning_insights)

        # 生成摘要报告
        self._generate_summary_report(insights)

        return insights

    def _identify_patterns(self) -> List[Dict[str, Any]]:
        """识别成功模式"""
        patterns = []

        # 社媒平台表现模式
        social_records = self.social_memory["records"]
        if social_records:
            platform_stats = defaultdict(lambda: {"impressions": 0, "clicks": 0, "engagement": 0, "count": 0})
            for s in social_records:
                platform = s["platform"]
                platform_stats[platform]["impressions"] += s["metrics"]["impressions"]
                platform_stats[platform]["clicks"] += s["metrics"]["clicks"]
                platform_stats[platform]["engagement"] += s["metrics"]["engagement"]
                platform_stats[platform]["count"] += 1

            for platform, stats in platform_stats.items():
                avg_ctr = stats["clicks"] / max(1, stats["impressions"]) if stats["impressions"] > 0 else 0
                patterns.append({
                    "type": "platform_performance",
                    "platform": platform,
                    "avg_ctr": avg_ctr,
                    "total_posts": stats["count"],
                    "insight": f"{platform}平均CTR {avg_ctr*100:.2f}%，共{stats['count']}条帖子"
                })

        # 内容分类表现模式
        content_records = self.content_memory["records"]
        if content_records:
            category_stats = defaultdict(lambda: {"views": 0, "revenue": 0, "count": 0})
            for c in content_records:
                category = c["metadata"].get("category", "unknown")
                category_stats[category]["views"] += c["metrics"]["views"]
                category_stats[category]["revenue"] += c["metrics"]["revenue"]
                category_stats[category]["count"] += 1

            for category, stats in category_stats.items():
                rpm = (stats["revenue"] / max(1, stats["views"]) * 1000) if stats["views"] > 0 else 0
                patterns.append({
                    "type": "category_performance",
                    "category": category,
                    "rpm": rpm,
                    "total_articles": stats["count"],
                    "insight": f"{category}分类RPM ${rpm:.2f}，共{stats['count']}篇文章"
                })

        return patterns

    def _generate_recommendations(self, insights: Dict[str, Any]) -> List[Dict[str, Any]]:
        """基于学习洞察生成建议"""
        recommendations = []

        # 基于Top内容的建议
        if insights["top_content"]:
            top_content = insights["top_content"][0]
            recommendations.append({
                "priority": "high",
                "type": "content_replication",
                "title": f"复制Top内容模式: {top_content['title'][:40]}...",
                "description": f"该内容RPM ${top_content['calculated'].get('revenue_per_1000_views', 0):.2f}，分析其关键词、结构和CTA，复制到类似主题",
                "action": "创建3篇类似主题和结构的文章"
            })

        # 基于Top社媒帖子的建议
        if insights["top_social_posts"]:
            top_post = insights["top_social_posts"][0]
            recommendations.append({
                "priority": "high",
                "type": "social_replication",
                "title": f"复制Top社媒帖子模式: [{top_post['platform']}] {top_post['content'].get('hook', '')[:40]}...",
                "description": f"该帖子CTR {top_post['calculated'].get('ctr', 0)*100:.2f}%，分析其Hook、CTA和发布时间，复制到其他平台",
                "action": "创建5条类似Hook和CTA的社媒帖子"
            })

        # 基于最佳CTA类型的建议
        if insights["best_cta_types"]:
            best_cta = insights["best_cta_types"][0]
            recommendations.append({
                "priority": "medium",
                "type": "cta_optimization",
                "title": f"推广最佳CTA类型: {best_cta['type']}",
                "description": f"该CTA类型转化率 {best_cta.get('conversion_rate', 0)*100:.2f}%，在全站推广使用",
                "action": "在所有文章底部添加该CTA类型"
            })

        # 通用建议
        recommendations.append({
            "priority": "medium",
            "type": "memory_continuous",
            "title": "持续记录Growth Memory",
            "description": "确保所有运营动作都记录到Growth Memory，形成完整的学习闭环",
            "action": "每周运行growth_memory_updater.py --weekly"
        })

        return recommendations

    def _generate_summary_report(self, insights: Dict[str, Any]):
        """生成Growth Memory摘要报告"""
        report = f"""# ChinaBound Travel Growth Memory 学习记忆摘要

**生成时间**: {insights['generated_at']}
**记忆版本**: 1.0

---

## 📊 记忆库统计

| 记忆类型 | 记录数 |
|---------|--------|
| 内容记忆 | {len(self.content_memory['records'])} |
| 社媒记忆 | {len(self.social_memory['records'])} |
| 转化记忆 | {len(self.conversion_memory['records'])} |
| 流量记忆 | {len(self.traffic_memory['records'])} |

---

## 🏆 Top表现内容

"""

        for i, c in enumerate(insights["top_content"][:5], 1):
            report += f"{i}. **{c['title'][:60]}**\n"
            report += f"   - RPM: ${c['calculated'].get('revenue_per_1000_views', 0):.2f}\n"
            report += f"   - 浏览: {c['metrics']['views']}, 联盟点击: {c['metrics']['affiliate_clicks']}, 收入: ${c['metrics']['revenue']:.2f}\n\n"

        report += """---

## 📱 Top社媒帖子

"""

        for i, s in enumerate(insights["top_social_posts"][:5], 1):
            report += f"{i}. **[{s['platform']}]** {s['content'].get('hook', '')[:60]}\n"
            report += f"   - CTR: {s['calculated'].get('ctr', 0)*100:.2f}%, 互动率: {s['calculated'].get('engagement_rate', 0)*100:.2f}%\n"
            report += f"   - 展示: {s['metrics']['impressions']}, 点击: {s['metrics']['clicks']}, 互动: {s['metrics']['engagement']}\n\n"

        report += """---

## 🎯 识别的成功模式

"""

        for p in insights["patterns"][:5]:
            report += f"- **{p['type']}**: {p['insight']}\n"

        report += """

---

## 🚀 学习建议

"""

        for r in insights["recommendations"]:
            priority_icon = "🔴" if r["priority"] == "high" else "🟡" if r["priority"] == "medium" else "🟢"
            report += f"{priority_icon} **{r['title']}**\n"
            report += f"   - 描述: {r['description']}\n"
            report += f"   - 行动: {r['action']}\n\n"

        report += f"""---

## 🔄 学习闭环状态

```
Observe ✅ → Record ✅ → Analyze ✅ → Learn 🟡 → Decide 🟡 → Act 🟡 → Measure 🟡 → Update Memory ✅
```

**当前阶段**: 从"分析推荐型"向"学习决策型"过渡中

---

*报告由Growth Memory学习记忆系统自动生成*
*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

        with open(GROWTH_MEMORY_SUMMARY_FILE, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"\n  ✅ Growth Memory摘要报告已生成: {GROWTH_MEMORY_SUMMARY_FILE}")

    def run_weekly_update(self):
        """运行周度更新"""
        print("\n" + "=" * 60)
        print("  Growth Memory 周度更新")
        print("=" * 60)

        # 1. 从现有报告中提取数据并记录
        print("\n  📥 从现有报告提取数据...")

        # 从内容审计报告提取
        content_audit_file = REPORTS_DIR / "content" / "content_audit_report.json"
        if content_audit_file.exists():
            try:
                with open(content_audit_file, encoding="utf-8") as f:
                    audit_data = json.load(f)
                # 记录每篇文章的基础数据
                articles = audit_data.get("articles", audit_data.get("content", []))
                if isinstance(articles, list):
                    for article in articles[:20]:  # 只记录前20篇
                        content_id = article.get("content_id", article.get("id", ""))
                        if content_id:
                            self.record_content_performance(
                                content_id=content_id,
                                title=article.get("title", ""),
                                views=article.get("views", article.get("page_views", 0)),
                                affiliate_clicks=article.get("affiliate_clicks", 0),
                                revenue=article.get("revenue", 0.0),
                                category=article.get("category", "")
                            )
            except Exception as e:
                print(f"  ⚠️ 提取内容审计数据失败: {e}")

        # 从社媒报告提取
        social_report_file = REPORTS_DIR / "social" / "social_audit_report.json"
        if social_report_file.exists():
            try:
                with open(social_report_file, encoding="utf-8") as f:
                    social_data = json.load(f)
                posts = social_data.get("posts", social_data.get("social_posts", []))
                if isinstance(posts, list):
                    for post in posts[:20]:
                        platform = post.get("platform", post.get("channel", "unknown"))
                        self.record_social_performance(
                            platform=platform,
                            post_id=post.get("id", post.get("post_id", "")),
                            hook=post.get("hook", post.get("caption", "")),
                            impressions=post.get("impressions", post.get("views", 0)),
                            clicks=post.get("clicks", post.get("link_clicks", 0)),
                            likes=post.get("likes", 0),
                            comments=post.get("comments", 0),
                            shares=post.get("shares", 0),
                            saves=post.get("saves", 0),
                            content_type=post.get("type", post.get("content_type", ""))
                        )
            except Exception as e:
                print(f"  ⚠️ 提取社媒数据失败: {e}")

        # 2. 分析Top表现
        print("\n  🔍 分析Top表现...")
        insights = self.analyze_top_performers()

        # 3. 输出统计
        print("\n" + "=" * 60)
        print("  Growth Memory 周度更新完成")
        print("=" * 60)
        print(f"\n  📊 内容记忆: {len(self.content_memory['records'])} 条")
        print(f"  📱 社媒记忆: {len(self.social_memory['records'])} 条")
        print(f"  🎯 转化记忆: {len(self.conversion_memory['records'])} 条")
        print(f"  💡 学习洞察: {len(insights.get('patterns', []))} 个模式")
        print(f"  🚀 优化建议: {len(insights.get('recommendations', []))} 条")
        print(f"\n  📄 摘要报告: {GROWTH_MEMORY_SUMMARY_FILE}")

        return insights


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="ChinaBound Travel Growth Memory 学习记忆系统")
    parser.add_argument("--weekly", action="store_true", help="运行周度更新")
    parser.add_argument("--daily", action="store_true", help="运行日度更新")
    parser.add_argument("--analyze", action="store_true", help="仅分析Top表现")
    parser.add_argument("--top-performers", action="store_true", help="显示Top表现")
    parser.add_argument("--record-social", action="store_true", help="记录社媒表现")
    parser.add_argument("--record-content", action="store_true", help="记录内容表现")
    parser.add_argument("--platform", type=str, default="", help="社媒平台")
    parser.add_argument("--post-id", type=str, default="", help="帖子ID")
    parser.add_argument("--content-id", type=str, default="", help="内容ID")
    parser.add_argument("--impressions", type=int, default=0, help="展示量")
    parser.add_argument("--clicks", type=int, default=0, help="点击量")
    parser.add_argument("--views", type=int, default=0, help="浏览量")
    parser.add_argument("--revenue", type=float, default=0.0, help="收入")

    args = parser.parse_args()

    updater = GrowthMemoryUpdater()

    if args.weekly:
        updater.run_weekly_update()
    elif args.daily:
        updater.run_weekly_update()  # 日度使用相同逻辑
    elif args.analyze or args.top_performers:
        updater.analyze_top_performers()
    elif args.record_social:
        updater.record_social_performance(
            platform=args.platform,
            post_id=args.post_id,
            impressions=args.impressions,
            clicks=args.clicks
        )
    elif args.record_content:
        updater.record_content_performance(
            content_id=args.content_id,
            views=args.views,
            affiliate_clicks=args.clicks,
            revenue=args.revenue
        )
    else:
        # 默认运行周度更新
        updater.run_weekly_update()


if __name__ == "__main__":
    main()
