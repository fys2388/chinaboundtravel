#!/usr/bin/env python3
"""
ChinaBound Travel - User Learning 闭环系统
User Learning Closed Loop

功能：打通用户运营的完整学习闭环
Observe → Record → Analyze → Learn → Decide → Act → Measure → Learn

记录维度：用户行为/分层/旅程/留存/互动/订阅/转化

使用方式：
    python scripts/user_learning_closed_loop.py --run
"""

import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict
sys.path.insert(0, str(Path(__file__).parent))
from real_data_bridge import get_user_records


PROJECT_ROOT = Path(__file__).parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
USER_DIR = REPORTS_DIR / "user"
USER_DIR.mkdir(parents=True, exist_ok=True)

STRATEGY_FILE = USER_DIR / "user_optimization_strategy.json"
LEARNING_REPORT = USER_DIR / "user_learning_report.md"
PERFORMANCE_HISTORY = USER_DIR / "user_performance_history.json"


class UserLearningClosedLoop:
    """User Learning 闭环系统"""

    def __init__(self):
        self.performance_history = self._load_json(PERFORMANCE_HISTORY, {"records": [], "version": "1.0"})
        self.current_strategy = self._load_json(STRATEGY_FILE, self._default_strategy())

    def _load_json(self, path: Path, default: Dict) -> Dict:
        if path.exists():
            try:
                with open(path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return default

    def _save_json(self, path: Path, data: Dict):
        data["last_updated"] = datetime.now().isoformat()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _default_strategy(self) -> Dict:
        return {
            "version": "1.0-default",
            "last_updated": datetime.now().isoformat(),
            "segmentation_rules": {
                "new_user": "首次访问，无历史记录",
                "returning_user": "7天内再次访问",
                "engaged_user": "访问≥3次或停留≥3分钟",
                "subscriber": "已订阅邮件",
                "converter": "有联盟点击或转化"
            },
            "retention_rules": {
                "welcome_email": "新用户24小时内发送欢迎邮件",
                "drip_campaign": "7天邮件培育序列",
                "re_engagement": "30天未活跃用户触发召回",
                "personalization": "基于浏览历史推荐相关内容"
            },
            "best_segments": [],
            "best_journey_paths": [],
            "high_retention_pages": [],
            "learning_insights": [],
            "strategy_changes": []
        }

    def observe_and_record(self) -> List[Dict]:
        """步骤1+2: Observe + Record"""
        print("\n" + "=" * 60)
        print("  步骤1+2: Observe + Record - 观察并记录用户表现")
        print("=" * 60)

        new_records = []

        # 从GA4用户报告提取数据
        # 从 real_data 读取真实数据（优先）
        try:
            real_records = get_user_records()
            existing_ids = set()
            for r in self.performance_history.get("records", []):
                rid = r.get("post_id") or r.get("keyword") or r.get("page") or r.get("segment") or r.get("type") or r.get("title") or str(r)
                existing_ids.add(rid)
            added = 0
            for record in real_records:
                rid = record.get("post_id") or record.get("keyword") or record.get("page") or record.get("segment") or record.get("type") or record.get("title") or str(record)
                if rid not in existing_ids:
                    
                    # 补全所有可能需要的字段（兼容 analyze 方法的硬编码字段）
                    for _key, _default in {
                        "type": "overall", "segment": "", "date": "",
                        "page": "", "title": ""
                    }.items():
                        record.setdefault(_key, _default)
                    record.setdefault("metrics", {})
                    record.setdefault("metadata", {})
                    record.setdefault("calculated", {})
                    self.performance_history.setdefault("records", []).append(record)
                    new_records.append(record)
                    added += 1
            print(f"  📥 从 real_data 加载: {added} 条记录 (共 {len(real_records)} 条可用)")
        except Exception as e:
            print(f"  ⚠️ real_data 加载失败: {e}")


        user_report = REPORTS_DIR / "user" / "user_analytics_report.json"
        if user_report.exists():
            try:
                with open(user_report, encoding="utf-8") as f:
                    report_data = json.load(f)

                segments = report_data.get("segments", report_data.get("user_segments", []))
                if isinstance(segments, list):
                    for seg in segments:
                        seg_name = seg.get("name", seg.get("segment", ""))
                        if seg_name and not any(r.get("segment") == seg_name for r in self.performance_history["records"]):
                            record = {
                                "segment": seg_name,
                                "date": datetime.now().isoformat(),
                                "metrics": {
                                    "users": seg.get("users", 0),
                                    "sessions": seg.get("sessions", 0),
                                    "page_views": seg.get("page_views", 0),
                                    "avg_duration": seg.get("avg_duration", 0),
                                    "bounce_rate": seg.get("bounce_rate", 0),
                                    "return_rate": seg.get("return_rate", 0),
                                    "conversion_rate": seg.get("conversion_rate", 0),
                                    "revenue": seg.get("revenue", 0.0)
                                },
                                "calculated": {
                                    "pages_per_session": seg.get("page_views", 0) / max(1, seg.get("sessions", 1)),
                                    "revenue_per_user": seg.get("revenue", 0.0) / max(1, seg.get("users", 1)),
                                    "engagement_score": (seg.get("avg_duration", 0) / 60) * (1 - seg.get("bounce_rate", 0) / 100) * (seg.get("return_rate", 0) / 100 + 1)
                                }
                            }
                            self.performance_history["records"].append(record)
                            new_records.append(record)
                            print(f"  ✅ 记录: {seg_name} (用户:{record['metrics']['users']}, 留存率:{record['metrics']['return_rate']:.1f}%)")
            except Exception as e:
                print(f"  ⚠️ 处理用户报告失败: {e}")

        # 如果没有真实数据，添加示例记录
        if not new_records and not self.performance_history["records"]:
            print("  📝 暂无真实用户数据，使用示例数据演示闭环")
            sample_segments = [
                {"name": "new_user", "users": 500, "sessions": 520, "page_views": 800, "avg_duration": 45, "bounce_rate": 75, "return_rate": 15, "conversion_rate": 0.5, "revenue": 25.0},
                {"name": "returning_user", "users": 200, "sessions": 350, "page_views": 700, "avg_duration": 120, "bounce_rate": 45, "return_rate": 60, "conversion_rate": 2.0, "revenue": 80.0},
                {"name": "engaged_user", "users": 80, "sessions": 200, "page_views": 500, "avg_duration": 240, "bounce_rate": 25, "return_rate": 85, "conversion_rate": 5.0, "revenue": 150.0},
                {"name": "subscriber", "users": 50, "sessions": 120, "page_views": 300, "avg_duration": 180, "bounce_rate": 30, "return_rate": 90, "conversion_rate": 8.0, "revenue": 200.0},
                {"name": "converter", "users": 30, "sessions": 80, "page_views": 200, "avg_duration": 300, "bounce_rate": 20, "return_rate": 95, "conversion_rate": 100.0, "revenue": 500.0},
            ]
            for s in sample_segments:
                record = {
                    "segment": s["name"],
                    "date": datetime.now().isoformat(),
                    "metrics": {k: s[k] for k in ["users", "sessions", "page_views", "avg_duration", "bounce_rate", "return_rate", "conversion_rate", "revenue"]},
                    "calculated": {
                        "pages_per_session": s["page_views"] / max(1, s["sessions"]),
                        "revenue_per_user": s["revenue"] / max(1, s["users"]),
                        "engagement_score": (s["avg_duration"] / 60) * (1 - s["bounce_rate"] / 100) * (s["return_rate"] / 100 + 1)
                    }
                }
                self.performance_history["records"].append(record)
                new_records.append(record)
                print(f"  ✅ 示例记录: {s['name']} (用户:{s['users']}, 每用户收入:${record['calculated']['revenue_per_user']:.2f})")

        self._save_json(PERFORMANCE_HISTORY, self.performance_history)
        print(f"\n  📊 新增记录: {len(new_records)} 条")
        print(f"  📊 历史总记录: {len(self.performance_history['records'])} 条")
        return new_records

    def analyze_and_learn(self) -> Dict:
        """步骤3+4: Analyze + Learn"""
        print("\n" + "=" * 60)
        print("  步骤3+4: Analyze + Learn - 分析并学习用户成功模式")
        print("=" * 60)

        insights = {"generated_at": datetime.now().isoformat(), "best_segments": [], "high_value_segments": [], "best_retention_strategies": [], "success_patterns": [], "recommendations": []}
        records = self.performance_history["records"]
        if not records:
            print("  ⚠️ 没有足够数据进行分析")
            return insights

        print(f"\n  📊 分析 {len(records)} 个用户分层...")

        # 数据规范化：补全所有硬编码字段
        for _r in records:
            _r.setdefault("segment", _r.get("type", _r.get("channel", "unknown")))
            _r.setdefault("metrics", {})
            _r.setdefault("calculated", {})
            for _mk in ["users", "sessions", "page_views", "avg_duration", "bounce_rate", "return_rate", "conversion_rate", "revenue"]:
                _r["metrics"].setdefault(_mk, 0)
            # 从 GA4 数据映射
            if _r["metrics"]["users"] == 0:
                _r["metrics"]["users"] = _r["metrics"].get("activeUsers", 0)
            if _r["metrics"]["page_views"] == 0:
                _r["metrics"]["page_views"] = _r["metrics"].get("screenPageViews", 0)
            for _ck in ["revenue_per_user", "pages_per_session", "engagement_score"]:
                _r["calculated"].setdefault(_ck, 0)


        # 按用户价值排序
        sorted_by_value = sorted(records, key=lambda x: x["calculated"]["revenue_per_user"], reverse=True)
        insights["best_segments"] = [{"segment": r["segment"], "revenue_per_user": r["calculated"]["revenue_per_user"], "users": r["metrics"]["users"], "conversion_rate": r["metrics"]["conversion_rate"]} for r in sorted_by_value]

        # 高价值用户（收入前20%）
        high_value_count = max(1, len(sorted_by_value) // 5)
        insights["high_value_segments"] = insights["best_segments"][:high_value_count]

        # 按留存率排序
        sorted_by_retention = sorted(records, key=lambda x: x["metrics"]["return_rate"], reverse=True)
        insights["best_retention_strategies"] = [{"segment": r["segment"], "return_rate": r["metrics"]["return_rate"], "avg_duration": r["metrics"]["avg_duration"], "bounce_rate": r["metrics"]["bounce_rate"]} for r in sorted_by_retention[:5]]

        # 成功模式
        if insights["high_value_segments"]:
            best_seg = insights["high_value_segments"][0]
            insights["success_patterns"].append({
                "pattern": "高价值用户特征",
                "description": f"'{best_seg['segment']}'用户价值最高，每用户收入 ${best_seg['revenue_per_user']:.2f}，转化率 {best_seg['conversion_rate']:.1f}%",
                "recommendation": f"重点培育和转化更多用户进入'{best_seg['segment']}'分层",
                "key_metrics": {"高留存": ">80%", "高互动": "停留>3分钟", "高转化": ">5%"}
            })

        if insights["best_retention_strategies"]:
            best_retention = insights["best_retention_strategies"][0]
            insights["success_patterns"].append({
                "pattern": "高留存用户行为",
                "description": f"'{best_retention['segment']}'用户留存率最高，达到 {best_retention['return_rate']:.1f}%，平均停留 {best_retention['avg_duration']}秒",
                "recommendation": "分析该分层用户的浏览路径和内容偏好，复制到其他用户",
                "key_metrics": {"低跳出": f"<{best_retention['bounce_rate']}%", "高回访": f">{best_retention['return_rate']}%"}
            })

        # 建议
        insights["recommendations"] = [
            {"priority": "high", "type": "segment_targeting", "title": "重点培育高价值用户分层", "description": f"针对Top {high_value_count}个高价值分层，提供个性化内容和推荐", "action": "建立用户分层标签系统，实现内容个性化推荐"},
            {"priority": "high", "type": "retention_optimization", "title": "优化新用户留存策略", "description": "新用户留存率偏低，需要优化首屏体验和引导流程", "action": "建立7天邮件培育序列，优化新用户引导流程"},
            {"priority": "medium", "type": "journey_optimization", "title": "优化高价值用户旅程", "description": "分析高价值用户的浏览路径，识别关键转化节点", "action": "在关键节点增加CTA和个性化推荐"},
            {"priority": "medium", "type": "re_engagement", "title": "建立流失用户召回机制", "description": "30天未活跃用户需要触发召回流程", "action": "建立自动化召回邮件序列，提供专属优惠"},
        ]

        print(f"\n  🏆 最佳用户分层: {insights['best_segments'][0]['segment'] if insights['best_segments'] else 'N/A'}")
        print(f"  💰 高价值分层: {len(insights['high_value_segments'])} 个")
        print(f"  📈 最佳留存: {insights['best_retention_strategies'][0]['segment'] if insights['best_retention_strategies'] else 'N/A'}")
        print(f"  💡 成功模式: {len(insights['success_patterns'])} 个")
        print(f"  🚀 优化建议: {len(insights['recommendations'])} 条")

        return insights

    def decide_and_update_strategy(self, insights: Dict) -> Dict:
        """步骤5+6: Decide + Act"""
        print("\n" + "=" * 60)
        print("  步骤5+6: Decide + Act - 决策并更新用户运营策略")
        print("=" * 60)

        strategy_changes = []

        if insights.get("best_segments"):
            old_best = self.current_strategy.get("best_segments", [])
            new_best = insights["best_segments"][:5]
            if old_best != new_best:
                self.current_strategy["best_segments"] = new_best
                strategy_changes.append({"field": "best_segments", "reason": "基于用户价值分析，更新最佳用户分层排名"})
                print(f"  ✅ 更新最佳用户分层: {len(new_best)} 个")

        if insights.get("high_value_segments"):
            old_high = self.current_strategy.get("high_value_segments", [])
            new_high = insights["high_value_segments"]
            if old_high != new_high:
                self.current_strategy["high_value_segments"] = new_high
                strategy_changes.append({"field": "high_value_segments", "reason": "基于收入分析，更新高价值用户分层"})
                print(f"  ✅ 更新高价值用户分层: {len(new_high)} 个")

        self.current_strategy["learning_insights"] = insights.get("success_patterns", [])
        self.current_strategy["strategy_changes"] = strategy_changes
        self.current_strategy["last_updated"] = datetime.now().isoformat()
        self.current_strategy["version"] = f"2.0-{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        self._save_json(STRATEGY_FILE, self.current_strategy)
        print(f"\n  📊 策略变更: {len(strategy_changes)} 项")
        print(f"  📄 策略文件: {STRATEGY_FILE}")
        return self.current_strategy

    def generate_report(self, insights: Dict, strategy: Dict):
        """生成学习报告"""
        report = f"""# ChinaBound Travel User Learning 闭环报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**策略版本**: {strategy.get('version', 'unknown')}

---

## 🔄 闭环状态
```
Observe ✅ → Record ✅ → Analyze ✅ → Learn ✅ → Decide ✅ → Act ✅ → Measure ⏳ → Learn Again 🔄
```

---

## 👥 用户分层表现（按每用户收入）

| 分层 | 用户数 | 每用户收入 | 转化率 | 留存率 |
|------|--------|-----------|--------|--------|
"""
        for seg in insights.get("best_segments", [])[:10]:
            report += f"| {seg['segment']} | {seg['users']} | ${seg['revenue_per_user']:.2f} | {seg['conversion_rate']:.1f}% | - |\n"

        report += """
---

## 💰 高价值用户分层

"""
        for i, seg in enumerate(insights.get("high_value_segments", []), 1):
            report += f"{i}. **{seg['segment']}** - 每用户收入 ${seg['revenue_per_user']:.2f}，转化率 {seg['conversion_rate']:.1f}%\n"

        report += """
---

## 📈 最佳留存分层

| 分层 | 留存率 | 平均停留 | 跳出率 |
|------|--------|----------|--------|
"""
        for seg in insights.get("best_retention_strategies", [])[:5]:
            report += f"| {seg['segment']} | {seg['return_rate']:.1f}% | {seg['avg_duration']}秒 | {seg['bounce_rate']:.1f}% |\n"

        report += """
---

## 💡 学习洞察

"""
        for i, pattern in enumerate(insights.get("success_patterns", []), 1):
            report += f"### {i}. {pattern['pattern']}\n{pattern['description']}\n\n**建议:** {pattern.get('recommendation', '')}\n\n"
            if pattern.get("key_metrics"):
                report += "**关键指标:**\n"
                for k, v in pattern["key_metrics"].items():
                    report += f"- {k}: {v}\n"
                report += "\n"

        report += """---

## 🚀 优化建议

"""
        for i, rec in enumerate(insights.get("recommendations", []), 1):
            icon = "🔴" if rec["priority"] == "high" else "🟡"
            report += f"{icon} **{rec['title']}**\n- {rec['description']}\n- 行动: {rec['action']}\n\n"

        report += f"""---

*报告由User Learning闭环系统自动生成*
"""
        with open(LEARNING_REPORT, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"  ✅ 学习报告已生成: {LEARNING_REPORT}")

    def run_full_closed_loop(self):
        """运行完整闭环"""
        print("\n" + "=" * 60)
        print("  ChinaBound Travel User Learning 完整闭环运行")
        print("=" * 60)
        print(f"\n  运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        new_records = self.observe_and_record()
        insights = self.analyze_and_learn()
        strategy = self.decide_and_update_strategy(insights)
        self.generate_report(insights, strategy)

        print("\n" + "=" * 60)
        print("  User Learning 完整闭环运行完成")
        print("=" * 60)
        print(f"\n  ✅ Observe: 观察完成")
        print(f"  ✅ Record: 记录完成 ({len(new_records)}条)")
        print(f"  ✅ Analyze: 分析完成")
        print(f"  ✅ Learn: 学习完成 ({len(insights.get('success_patterns', []))}个模式)")
        print(f"  ✅ Decide: 决策完成")
        print(f"  ✅ Act: 行动完成 ({len(strategy.get('strategy_changes', []))}项变更)")
        print(f"  ⏳ Measure: 等待下一轮效果测量")
        print(f"\n  📄 策略文件: {STRATEGY_FILE}")
        print(f"  📄 学习报告: {LEARNING_REPORT}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="User Learning 闭环系统")
    parser.add_argument("--run", action="store_true", help="运行完整闭环")
    args = parser.parse_args()
    loop = UserLearningClosedLoop()
    if args.run:
        loop.run_full_closed_loop()
    else:
        loop.run_full_closed_loop()


if __name__ == "__main__":
    main()
