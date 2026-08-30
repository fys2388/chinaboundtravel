#!/usr/bin/env python3
"""
ChinaBound Travel - Social Priority Queue Consumer
社媒优先分发队列消费者

功能：集成SYN-001优先分发队列到Social Engine
- 读取SYN-001优先分发队列
- 读取社媒发布策略
- 合并队列和策略，生成最终的社媒发布计划
- 高优先级内容优先发布
- 输出可供社媒发布工作流消费的发布计划

使用方式：
    python scripts/social_priority_queue_consumer.py --run
    python scripts/social_priority_queue_consumer.py --generate-plan
    python scripts/social_priority_queue_consumer.py --show-queue
    python scripts/social_priority_queue_consumer.py --consume-next
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
SOCIAL_DIR = REPORTS_DIR / "social"
SYNERGY_DIR = REPORTS_DIR / "synergy"

# 输入文件
PRIORITY_QUEUE_FILE = SYNERGY_DIR / "social_priority_queue.json"
SOCIAL_STRATEGY_FILE = SOCIAL_DIR / "social_publish_strategy.json"

# 输出文件
SOCIAL_PUBLISH_PLAN = SOCIAL_DIR / "social_publish_plan.json"
INTEGRATION_REPORT = SYNERGY_DIR / "syn001_integration_report.md"


class SocialPriorityQueueConsumer:
    """社媒优先分发队列消费者"""

    def __init__(self):
        self.priority_queue = self._load_priority_queue()
        self.social_strategy = self._load_social_strategy()
        self.publish_plan = self._load_publish_plan()

    def _load_priority_queue(self) -> Dict:
        """加载优先分发队列"""
        if PRIORITY_QUEUE_FILE.exists():
            try:
                with open(PRIORITY_QUEUE_FILE, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"  ⚠️ 加载优先分发队列失败: {e}")
        return {"queue": [], "distributed": [], "stats": {}}

    def _load_social_strategy(self) -> Dict:
        """加载社媒发布策略"""
        if SOCIAL_STRATEGY_FILE.exists():
            try:
                with open(SOCIAL_STRATEGY_FILE, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"  ⚠️ 加载社媒发布策略失败: {e}")
        return {"platforms": {}, "global_rules": {}}

    def _load_publish_plan(self) -> Dict:
        """加载发布计划"""
        if SOCIAL_PUBLISH_PLAN.exists():
            try:
                with open(SOCIAL_PUBLISH_PLAN, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "integration_id": "SYN-001",
            "pending_posts": [],
            "published_posts": [],
            "stats": {
                "total_queued": 0,
                "total_published": 0,
                "priority_distribution": {},
                "platform_distribution": {}
            }
        }

    def _save_publish_plan(self):
        """保存发布计划"""
        self.publish_plan["last_updated"] = datetime.now().isoformat()
        with open(SOCIAL_PUBLISH_PLAN, "w", encoding="utf-8") as f:
            json.dump(self.publish_plan, f, ensure_ascii=False, indent=2)

    def get_pending_queue(self) -> List[Dict]:
        """获取待发布队列"""
        queue = self.priority_queue.get("queue", [])
        # 过滤状态为queued的项
        pending = [item for item in queue if item.get("status") == "queued"]
        # 按优先级和发布时间排序
        priority_order = {"high": 0, "medium": 1, "low": 2}
        pending.sort(key=lambda x: (priority_order.get(x.get("priority", "medium"), 1), x.get("publish_time", "")))
        return pending

    def generate_publish_plan(self, days: int = 7) -> List[Dict]:
        """生成发布计划"""
        print("\n" + "=" * 60)
        print("  步骤1: 生成社媒发布计划")
        print("=" * 60)

        pending = self.get_pending_queue()
        print(f"  📋 待发布队列: {len(pending)} 条")

        # 获取平台限制
        platforms = self.social_strategy.get("platforms", {})
        global_rules = self.social_strategy.get("global_rules", {})
        max_per_day_per_platform = global_rules.get("max_posts_per_day_per_platform", 3)

        # 按平台分组
        platform_posts = defaultdict(list)
        for item in pending:
            platform = item.get("platform", "unknown")
            platform_posts[platform].append(item)

        # 生成未来N天的发布计划
        publish_plan = []
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        for day_offset in range(days):
            current_date = today + timedelta(days=day_offset)
            date_str = current_date.strftime("%Y-%m-%d")

            for platform, posts in platform_posts.items():
                # 获取该平台当天的最佳发布时间
                platform_config = platforms.get(platform, {})
                best_times = platform_config.get("best_times", ["10:00", "14:00", "18:00"])

                # 限制每天每平台的发布数量
                daily_count = 0
                for post in posts:
                    if daily_count >= max_per_day_per_platform:
                        break

                    # 检查是否已经在发布计划中
                    post_id = post.get("queue_id", "")
                    if any(p.get("queue_id") == post_id for p in publish_plan):
                        continue

                    # 分配发布时间
                    time_index = daily_count % len(best_times)
                    publish_time_str = best_times[time_index]
                    hour, minute = map(int, publish_time_str.split(":"))
                    publish_time = current_date.replace(hour=hour, minute=minute)

                    # 创建发布计划项
                    plan_item = {
                        "plan_id": f"PUBLISH_{date_str}_{platform}_{daily_count}",
                        "queue_id": post_id,
                        "content_id": post.get("content_id", ""),
                        "title": post.get("title", ""),
                        "platform": platform,
                        "priority": post.get("priority", "medium"),
                        "quality_score": post.get("quality_score", 0),
                        "scheduled_time": publish_time.isoformat(),
                        "recommended_hook": post.get("recommended_hook", ""),
                        "recommended_cta": post.get("recommended_cta", ""),
                        "status": "scheduled",
                        "created_at": datetime.now().isoformat(),
                        "integration_id": "SYN-001"
                    }
                    publish_plan.append(plan_item)
                    daily_count += 1

        # 按发布时间排序
        publish_plan.sort(key=lambda x: x.get("scheduled_time", ""))

        print(f"  ✅ 生成发布计划: {len(publish_plan)} 条")
        print(f"     高优先级: {sum(1 for p in publish_plan if p['priority'] == 'high')} 条")
        print(f"     中优先级: {sum(1 for p in publish_plan if p['priority'] == 'medium')} 条")
        print(f"     覆盖平台: {len(set(p['platform'] for p in publish_plan))} 个")
        print(f"     覆盖天数: {days} 天")

        return publish_plan

    def consume_next_post(self) -> Optional[Dict]:
        """消费下一个待发布帖子"""
        print("\n" + "=" * 60)
        print("  步骤2: 消费下一个待发布帖子")
        print("=" * 60)

        pending = self.get_pending_queue()
        if not pending:
            print("  ⚠️ 没有待发布的帖子")
            return None

        # 获取最高优先级的帖子
        next_post = pending[0]
        print(f"  📋 下一个待发布帖子:")
        print(f"     标题: {next_post.get('title', '')[:50]}")
        print(f"     平台: {next_post.get('platform', '')}")
        print(f"     优先级: {next_post.get('priority', '')}")
        print(f"     质量分: {next_post.get('quality_score', 0)}")

        # 更新队列状态
        for item in self.priority_queue.get("queue", []):
            if item.get("queue_id") == next_post.get("queue_id"):
                item["status"] = "consumed"
                item["consumed_at"] = datetime.now().isoformat()
                break

        # 添加到已发布列表
        self.priority_queue.setdefault("distributed", []).append({
            **next_post,
            "status": "consumed",
            "consumed_at": datetime.now().isoformat()
        })

        # 保存队列
        with open(PRIORITY_QUEUE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.priority_queue, f, ensure_ascii=False, indent=2)

        print(f"  ✅ 已消费帖子，队列状态已更新")
        return next_post

    def update_publish_plan(self, publish_plan: List[Dict]):
        """更新发布计划"""
        print("\n" + "=" * 60)
        print("  步骤3: 更新发布计划")
        print("=" * 60)

        self.publish_plan["pending_posts"] = publish_plan
        self.publish_plan["stats"]["total_queued"] = len(publish_plan)
        self.publish_plan["stats"]["priority_distribution"] = {
            "high": sum(1 for p in publish_plan if p["priority"] == "high"),
            "medium": sum(1 for p in publish_plan if p["priority"] == "medium"),
            "low": sum(1 for p in publish_plan if p["priority"] == "low")
        }
        self.publish_plan["stats"]["platform_distribution"] = {}
        for p in publish_plan:
            platform = p["platform"]
            self.publish_plan["stats"]["platform_distribution"][platform] = \
                self.publish_plan["stats"]["platform_distribution"].get(platform, 0) + 1

        self._save_publish_plan()

        print(f"  ✅ 发布计划已更新: {len(publish_plan)} 条")
        print(f"  📄 发布计划文件: {SOCIAL_PUBLISH_PLAN}")

    def generate_integration_report(self, publish_plan: List[Dict]):
        """生成集成报告"""
        print("\n" + "=" * 60)
        print("  步骤4: 生成SYN-001集成报告")
        print("=" * 60)

        pending = self.get_pending_queue()
        high_priority = [p for p in pending if p["priority"] == "high"]
        medium_priority = [p for p in pending if p["priority"] == "medium"]

        report = f"""# SYN-001 优先分发队列集成报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**集成ID**: SYN-001
**状态**: ✅ 已集成到Social Engine

---

## 📊 集成统计

| 指标 | 数值 |
|------|------|
| 优先分发队列总数 | {len(self.priority_queue.get('queue', []))} 条 |
| 待发布队列 | {len(pending)} 条 |
| 已消费/已发布 | {len(self.priority_queue.get('distributed', []))} 条 |
| 高优先级待发布 | {len(high_priority)} 条 |
| 中优先级待发布 | {len(medium_priority)} 条 |
| 生成发布计划 | {len(publish_plan)} 条 |

---

## 📋 发布计划概览

### 按优先级分布
| 优先级 | 数量 | 占比 |
|--------|------|------|
| 🔴 高优先级 | {self.publish_plan['stats']['priority_distribution'].get('high', 0)} | {self.publish_plan['stats']['priority_distribution'].get('high', 0)/max(len(publish_plan),1)*100:.1f}% |
| 🟡 中优先级 | {self.publish_plan['stats']['priority_distribution'].get('medium', 0)} | {self.publish_plan['stats']['priority_distribution'].get('medium', 0)/max(len(publish_plan),1)*100:.1f}% |
| 🟢 低优先级 | {self.publish_plan['stats']['priority_distribution'].get('low', 0)} | {self.publish_plan['stats']['priority_distribution'].get('low', 0)/max(len(publish_plan),1)*100:.1f}% |

### 按平台分布
| 平台 | 数量 | 占比 |
|------|------|------|
"""

        for platform, count in self.publish_plan["stats"]["platform_distribution"].items():
            report += f"| {platform} | {count} | {count/max(len(publish_plan),1)*100:.1f}% |\n"

        report += f"""
---

## 🎯 高优先级待发布内容Top 5

| 排名 | 标题 | 平台 | 质量分 | 推荐Hook |
|------|------|------|--------|----------|
"""

        for i, post in enumerate(high_priority[:5], 1):
            report += f"| {i} | {post.get('title', '')[:40]} | {post.get('platform', '')} | {post.get('quality_score', 0)} | {post.get('recommended_hook', '')[:20]} |\n"

        report += f"""
---

## 🔄 集成流程

```
SYN-001协同机制生成优先分发队列
         ↓
Social Priority Queue Consumer读取队列
         ↓
合并社媒发布策略（最佳时间/Hook/CTA）
         ↓
生成最终发布计划（高优先级优先）
         ↓
Social Engine消费发布计划，自动发布
         ↓
发布效果回流到Growth Memory
         ↓
更新Social Learning和Content Learning策略
```

---

## 📝 集成状态

- ✅ 优先分发队列读取机制
- ✅ 社媒发布策略合并
- ✅ 发布计划自动生成（高优先级优先）
- ✅ 发布计划文件输出（供Social Engine消费）
- ✅ 队列消费和状态更新
- ✅ 集成报告生成
- ⏳ Social Engine自动消费发布计划（待工作流集成）
- ⏳ 发布效果测量和反馈（待积累数据）

---

## 🎯 预期效果

- **高表现内容优先曝光**: 质量分高的内容优先进入社媒发布
- **发布时间优化**: 使用学习到的最佳发布时间，提升点击率
- **Hook/CTA优化**: 使用学习到的最佳Hook和CTA，提升互动率
- **协同效应**: Content和Social双向反馈，持续优化双方策略

---

*报告由SYN-001优先分发队列集成自动生成*
*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

        with open(INTEGRATION_REPORT, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"  ✅ 集成报告已生成: {INTEGRATION_REPORT}")

    def run_integration(self) -> Dict:
        """运行完整集成流程"""
        print("\n" + "=" * 60)
        print("  SYN-001 优先分发队列集成运行")
        print("=" * 60)
        print(f"\n  运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # 步骤1: 生成发布计划
        publish_plan = self.generate_publish_plan(days=7)

        # 步骤2: 更新发布计划
        self.update_publish_plan(publish_plan)

        # 步骤3: 生成集成报告
        self.generate_integration_report(publish_plan)

        # 总结
        print("\n" + "=" * 60)
        print("  SYN-001 集成完成")
        print("=" * 60)
        print(f"\n  ✅ 待发布队列: {len(self.get_pending_queue())} 条")
        print(f"  ✅ 生成发布计划: {len(publish_plan)} 条")
        print(f"  ✅ 发布计划文件: {SOCIAL_PUBLISH_PLAN}")
        print(f"  ✅ 集成报告: {INTEGRATION_REPORT}")
        print(f"\n  🎯 集成状态: SYN-001优先分发队列已集成到Social Engine")

        return {
            "pending_queue": len(self.get_pending_queue()),
            "publish_plan_count": len(publish_plan),
            "publish_plan_file": str(SOCIAL_PUBLISH_PLAN),
            "integration_report": str(INTEGRATION_REPORT),
            "status": "success"
        }


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="社媒优先分发队列消费者")
    parser.add_argument("--run", action="store_true", help="运行完整集成流程")
    parser.add_argument("--generate-plan", action="store_true", help="仅生成发布计划")
    parser.add_argument("--show-queue", action="store_true", help="显示待发布队列")
    parser.add_argument("--consume-next", action="store_true", help="消费下一个待发布帖子")

    args = parser.parse_args()

    consumer = SocialPriorityQueueConsumer()

    if args.run:
        consumer.run_integration()
    elif args.generate_plan:
        publish_plan = consumer.generate_publish_plan(days=7)
        consumer.update_publish_plan(publish_plan)
    elif args.show_queue:
        pending = consumer.get_pending_queue()
        print(f"\n待发布队列: {len(pending)} 条")
        for i, item in enumerate(pending[:10], 1):
            print(f"  {i}. [{item['priority']}] {item['title'][:40]}... ({item['platform']})")
    elif args.consume_next:
        consumer.consume_next_post()
    else:
        consumer.run_integration()


if __name__ == "__main__":
    main()
