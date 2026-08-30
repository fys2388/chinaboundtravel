#!/usr/bin/env python3
"""
ChinaBound Travel - SYN-001 内容-社媒协同机制
Content-Social Synergy Mechanism

功能：实现高表现内容自动进入社媒优先分发队列
- 从Content Learning策略读取高表现文章列表
- 从Social Learning策略读取最佳发布时间和Hook
- 生成社媒优先分发队列
- 输出可供Social Engine消费的优先分发列表

协同流程：
Content Agent识别高表现文章 → 进入Social优先分发队列 → Social Engine优先分发 → 效果回流 → 更新双方策略

使用方式：
    python scripts/synergy_content_social.py --run
    python scripts/synergy_content_social.py --generate-queue
    python scripts/synergy_content_social.py --show-queue
"""

import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
CONTENT_DIR = REPORTS_DIR / "content"
SOCIAL_DIR = REPORTS_DIR / "social"
SYNERGY_DIR = REPORTS_DIR / "synergy"
SYNERGY_DIR.mkdir(parents=True, exist_ok=True)

# 输出文件
PRIORITY_QUEUE_FILE = SYNERGY_DIR / "social_priority_queue.json"
SYNERGY_REPORT_FILE = SYNERGY_DIR / "syn001_content_social_report.md"
SYNERGY_HISTORY_FILE = SYNERGY_DIR / "syn001_history.json"


class ContentSocialSynergy:
    """内容-社媒协同机制"""

    def __init__(self):
        self.content_strategy = self._load_content_strategy()
        self.social_strategy = self._load_social_strategy()
        self.priority_queue = self._load_priority_queue()
        self.history = self._load_history()

    def _load_content_strategy(self) -> Dict:
        """加载内容优化策略"""
        strategy_file = CONTENT_DIR / "content_optimization_strategy.json"
        if strategy_file.exists():
            try:
                with open(strategy_file, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"  ⚠️ 加载内容策略失败: {e}")
        return {"high_priority_articles": [], "best_categories": [], "learning_insights": []}

    def _load_social_strategy(self) -> Dict:
        """加载社媒发布策略"""
        strategy_file = SOCIAL_DIR / "social_publish_strategy.json"
        if strategy_file.exists():
            try:
                with open(strategy_file, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"  ⚠️ 加载社媒策略失败: {e}")
        return {"platforms": {}, "best_hooks": [], "learning_insights": []}

    def _load_priority_queue(self) -> Dict:
        """加载优先分发队列"""
        if PRIORITY_QUEUE_FILE.exists():
            try:
                with open(PRIORITY_QUEUE_FILE, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "queue": [],
            "distributed": [],
            "stats": {
                "total_queued": 0,
                "total_distributed": 0,
                "avg_ctr_boost": 0,
                "success_rate": 0
            }
        }

    def _save_priority_queue(self):
        """保存优先分发队列"""
        self.priority_queue["last_updated"] = datetime.now().isoformat()
        with open(PRIORITY_QUEUE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.priority_queue, f, ensure_ascii=False, indent=2)

    def _load_history(self) -> Dict:
        """加载协同历史"""
        if SYNERGY_HISTORY_FILE.exists():
            try:
                with open(SYNERGY_HISTORY_FILE, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"runs": [], "version": "1.0"}

    def _save_history(self):
        """保存协同历史"""
        with open(SYNERGY_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)

    def identify_high_performance_content(self) -> List[Dict]:
        """识别高表现内容"""
        print("\n" + "=" * 60)
        print("  步骤1: 识别高表现内容")
        print("=" * 60)

        high_performance = []

        # 从内容策略中获取高优先级文章
        high_priority_articles = self.content_strategy.get("high_priority_articles", [])
        if high_priority_articles:
            print(f"  📋 从内容策略获取 {len(high_priority_articles)} 篇高优先级文章")
            for article in high_priority_articles:
                high_performance.append({
                    "content_id": article.get("content_id", ""),
                    "title": article.get("title", ""),
                    "quality_score": article.get("quality_score", 0),
                    "source": "content_strategy",
                    "priority": "high"
                })

        # 从内容审计报告获取高表现文章
        content_audit_file = CONTENT_DIR / "content_audit_report.json"
        if content_audit_file.exists():
            try:
                with open(content_audit_file, encoding="utf-8") as f:
                    audit_data = json.load(f)
                articles = audit_data.get("articles", audit_data.get("content", []))
                if isinstance(articles, list):
                    # 按质量分排序，取Top 10
                    sorted_articles = sorted(articles, key=lambda x: x.get("quality_score", x.get("score", 0)), reverse=True)
                    for article in sorted_articles[:10]:
                        content_id = article.get("content_id", article.get("id", ""))
                        if content_id and not any(a["content_id"] == content_id for a in high_performance):
                            high_performance.append({
                                "content_id": content_id,
                                "title": article.get("title", ""),
                                "quality_score": article.get("quality_score", article.get("score", 0)),
                                "views": article.get("views", 0),
                                "source": "content_audit",
                                "priority": "medium"
                            })
                    print(f"  📊 从内容审计获取 Top 10 高表现文章")
            except Exception as e:
                print(f"  ⚠️ 读取内容审计失败: {e}")

        # 如果没有真实数据，使用示例数据
        if not high_performance:
            print("  📝 暂无真实高表现内容，使用示例数据演示协同机制")
            sample_articles = [
                {"content_id": "article_001", "title": "144-Hour Visa-Free Transit Guide", "quality_score": 92, "views": 500, "source": "sample", "priority": "high"},
                {"content_id": "article_002", "title": "China High-Speed Rail Complete Guide", "quality_score": 88, "views": 450, "source": "sample", "priority": "high"},
                {"content_id": "article_003", "title": "Chengdu Hotpot Food Guide", "quality_score": 85, "views": 400, "source": "sample", "priority": "medium"},
                {"content_id": "article_004", "title": "Zhangjiajie Photography Guide", "quality_score": 82, "views": 350, "source": "sample", "priority": "medium"},
                {"content_id": "article_005", "title": "China Payment Guide for Foreigners", "quality_score": 80, "views": 300, "source": "sample", "priority": "medium"},
            ]
            high_performance = sample_articles

        print(f"\n  ✅ 识别高表现内容: {len(high_performance)} 篇")
        for i, article in enumerate(high_performance[:5], 1):
            print(f"    {i}. {article['title'][:50]}... (质量分:{article.get('quality_score', 0)})")

        return high_performance

    def get_social_best_practices(self) -> Dict:
        """获取社媒最佳实践"""
        print("\n" + "=" * 60)
        print("  步骤2: 获取社媒最佳实践")
        print("=" * 60)

        best_practices = {
            "best_times": {},
            "best_hooks": {},
            "best_ctas": {},
            "platform_priority": ["pinterest", "x", "facebook", "instagram"]
        }

        # 从社媒策略获取最佳时间和Hook
        platforms = self.social_strategy.get("platforms", {})
        for platform, strategy in platforms.items():
            best_practices["best_times"][platform] = strategy.get("best_times", [])
            best_practices["best_hooks"][platform] = strategy.get("best_hooks", [])
            best_practices["best_ctas"][platform] = strategy.get("best_ctas", [])

        if platforms:
            print(f"  📱 加载 {len(platforms)} 个平台的最佳实践")
            for platform in list(platforms.keys())[:4]:
                times = best_practices["best_times"].get(platform, [])
                hooks = best_practices["best_hooks"].get(platform, [])
                print(f"    {platform}: 最佳时间 {times[:2]}, 最佳Hook {hooks[:2]}")
        else:
            print("  📝 使用默认社媒最佳实践")
            best_practices["best_times"] = {
                "pinterest": ["09:00", "14:00", "20:00"],
                "instagram": ["10:00", "18:00", "21:00"],
                "facebook": ["09:00", "13:00", "19:00"],
                "x": ["08:00", "12:00", "17:00"]
            }

        return best_practices

    def generate_priority_queue(self, high_performance: List[Dict], best_practices: Dict) -> List[Dict]:
        """生成优先分发队列"""
        print("\n" + "=" * 60)
        print("  步骤3: 生成社媒优先分发队列")
        print("=" * 60)

        queue = []
        today = datetime.now()

        for i, article in enumerate(high_performance):
            # 为每篇高表现文章生成多平台分发计划
            for platform in best_practices["platform_priority"]:
                best_times = best_practices["best_times"].get(platform, [])
                best_hooks = best_practices["best_hooks"].get(platform, [])
                best_ctas = best_practices["best_ctas"].get(platform, [])

                # 计算发布时间（未来7天内）
                day_offset = (i % 7) + 1
                time_index = i % len(best_times) if best_times else 0
                publish_time = today + timedelta(days=day_offset)
                if best_times and time_index < len(best_times):
                    time_str = best_times[time_index]
                    hour, minute = map(int, time_str.split(":"))
                    publish_time = publish_time.replace(hour=hour, minute=minute, second=0)

                queue_item = {
                    "queue_id": f"SYN001_{article['content_id']}_{platform}_{i}",
                    "content_id": article["content_id"],
                    "title": article["title"],
                    "platform": platform,
                    "quality_score": article.get("quality_score", 0),
                    "priority": article.get("priority", "medium"),
                    "publish_time": publish_time.isoformat(),
                    "recommended_hook": best_hooks[0] if best_hooks else "",
                    "recommended_cta": best_ctas[0] if best_ctas else "",
                    "status": "queued",
                    "created_at": datetime.now().isoformat(),
                    "synergy_id": "SYN-001"
                }
                queue.append(queue_item)

        # 按优先级和发布时间排序
        priority_order = {"high": 0, "medium": 1, "low": 2}
        queue.sort(key=lambda x: (priority_order.get(x["priority"], 1), x["publish_time"]))

        print(f"\n  ✅ 生成优先分发队列: {len(queue)} 条")
        print(f"     高优先级: {sum(1 for q in queue if q['priority'] == 'high')} 条")
        print(f"     中优先级: {sum(1 for q in queue if q['priority'] == 'medium')} 条")
        print(f"\n  📋 Top 5 队列项:")
        for i, item in enumerate(queue[:5], 1):
            print(f"    {i}. [{item['platform']}] {item['title'][:40]}... (发布:{item['publish_time'][:10]}, 优先级:{item['priority']})")

        return queue

    def update_priority_queue(self, queue: List[Dict]):
        """更新优先分发队列"""
        print("\n" + "=" * 60)
        print("  步骤4: 更新优先分发队列")
        print("=" * 60)

        # 合并新队列和已有队列
        existing_ids = {q["queue_id"] for q in self.priority_queue.get("queue", [])}
        new_items = [q for q in queue if q["queue_id"] not in existing_ids]

        self.priority_queue["queue"].extend(new_items)
        self.priority_queue["stats"]["total_queued"] += len(new_items)

        self._save_priority_queue()

        print(f"  ✅ 新增队列项: {len(new_items)} 条")
        print(f"  📊 当前队列总数: {len(self.priority_queue['queue'])} 条")
        print(f"  📄 队列文件: {PRIORITY_QUEUE_FILE}")

    def generate_synergy_report(self, high_performance: List[Dict], queue: List[Dict]):
        """生成协同报告"""
        print("\n" + "=" * 60)
        print("  步骤5: 生成SYN-001协同报告")
        print("=" * 60)

        report = f"""# SYN-001 内容-社媒协同机制报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**协同ID**: SYN-001
**机制**: 高表现内容自动进入社媒优先分发队列

---

## 📊 协同统计

| 指标 | 数值 |
|------|------|
| 识别高表现内容 | {len(high_performance)} 篇 |
| 生成队列项 | {len(queue)} 条 |
| 高优先级队列 | {sum(1 for q in queue if q['priority'] == 'high')} 条 |
| 中优先级队列 | {sum(1 for q in queue if q['priority'] == 'medium')} 条 |
| 覆盖平台 | {len(set(q['platform'] for q in queue))} 个 |

---

## 🏆 高表现内容Top 10

| 排名 | 文章标题 | 质量分 | 来源 | 优先级 |
|------|---------|--------|------|--------|
"""

        for i, article in enumerate(high_performance[:10], 1):
            report += f"| {i} | {article['title'][:50]} | {article.get('quality_score', 0)} | {article.get('source', '')} | {article.get('priority', '')} |\n"

        report += f"""
---

## 📋 优先分发队列Top 10

| 排名 | 平台 | 文章标题 | 发布时间 | 优先级 | 推荐Hook |
|------|------|---------|----------|--------|----------|
"""

        for i, item in enumerate(queue[:10], 1):
            report += f"| {i} | {item['platform']} | {item['title'][:40]} | {item['publish_time'][:10]} | {item['priority']} | {item.get('recommended_hook', '')[:20]} |\n"

        report += f"""
---

## 🔄 协同流程

```
Content Agent识别高表现文章
         ↓
进入Social优先分发队列（带推荐Hook/CTA/时间）
         ↓
Social Engine优先消费队列项
         ↓
发布效果回流到Growth Memory
         ↓
更新Content和Social双方策略
         ↓
持续优化协同效果
```

---

## 🎯 预期效果

- **社媒内容质量提升**: 优先分发高表现内容，提升整体内容质量
- **社媒点击率提升**: 使用学习到的最佳Hook和发布时间，预期CTR提升20-30%
- **内容曝光增加**: 高表现内容获得更多社媒曝光，带动网站流量
- **协同效应形成**: 内容和社媒双向反馈，持续优化双方策略

---

## 📝 实施状态

- ✅ 高表现内容识别机制
- ✅ 社媒最佳实践加载
- ✅ 优先分发队列生成
- ✅ 队列文件输出（供Social Engine消费）
- ✅ 协同报告生成
- ⏳ Social Engine消费队列（待集成）
- ⏳ 效果测量和反馈（待积累数据）

---

*报告由SYN-001内容-社媒协同机制自动生成*
*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

        with open(SYNERGY_REPORT_FILE, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"  ✅ 协同报告已生成: {SYNERGY_REPORT_FILE}")

    def run_synergy(self) -> Dict:
        """运行完整协同机制"""
        print("\n" + "=" * 60)
        print("  SYN-001 内容-社媒协同机制运行")
        print("=" * 60)
        print(f"\n  运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # 步骤1: 识别高表现内容
        high_performance = self.identify_high_performance_content()

        # 步骤2: 获取社媒最佳实践
        best_practices = self.get_social_best_practices()

        # 步骤3: 生成优先分发队列
        queue = self.generate_priority_queue(high_performance, best_practices)

        # 步骤4: 更新优先分发队列
        self.update_priority_queue(queue)

        # 步骤5: 生成协同报告
        self.generate_synergy_report(high_performance, queue)

        # 记录历史
        run_record = {
            "run_id": f"SYN001_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.now().isoformat(),
            "high_performance_count": len(high_performance),
            "queue_count": len(queue),
            "status": "success"
        }
        self.history["runs"].append(run_record)
        self._save_history()

        # 总结
        print("\n" + "=" * 60)
        print("  SYN-001 协同机制运行完成")
        print("=" * 60)
        print(f"\n  ✅ 高表现内容识别: {len(high_performance)} 篇")
        print(f"  ✅ 优先分发队列生成: {len(queue)} 条")
        print(f"  ✅ 队列文件输出: {PRIORITY_QUEUE_FILE}")
        print(f"  ✅ 协同报告生成: {SYNERGY_REPORT_FILE}")
        print(f"\n  🎯 协同状态: SYN-001机制已建立，等待Social Engine消费队列")

        return {
            "high_performance_count": len(high_performance),
            "queue_count": len(queue),
            "queue_file": str(PRIORITY_QUEUE_FILE),
            "report_file": str(SYNERGY_REPORT_FILE),
            "status": "success"
        }


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="SYN-001 内容-社媒协同机制")
    parser.add_argument("--run", action="store_true", help="运行完整协同机制")
    parser.add_argument("--generate-queue", action="store_true", help="仅生成优先分发队列")
    parser.add_argument("--show-queue", action="store_true", help="显示当前优先分发队列")

    args = parser.parse_args()

    synergy = ContentSocialSynergy()

    if args.run:
        synergy.run_synergy()
    elif args.generate_queue:
        high_performance = synergy.identify_high_performance_content()
        best_practices = synergy.get_social_best_practices()
        queue = synergy.generate_priority_queue(high_performance, best_practices)
        synergy.update_priority_queue(queue)
    elif args.show_queue:
        queue = synergy.priority_queue.get("queue", [])
        print(f"\n当前优先分发队列: {len(queue)} 条")
        for i, item in enumerate(queue[:10], 1):
            print(f"  {i}. [{item['platform']}] {item['title'][:40]}... (发布:{item['publish_time'][:10]})")
    else:
        synergy.run_synergy()


if __name__ == "__main__":
    main()
