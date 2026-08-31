#!/usr/bin/env python3
"""
ChinaBound Travel - Conversion Learning 闭环系统
Conversion Learning Closed Loop

功能：打通转化优化的完整学习闭环
Observe → Record → Analyze → Learn → Decide → Act → Measure → Learn

记录维度：CTA类型/位置/文案、联盟产品、页面、展示/点击/转化/收入

使用方式：
    python scripts/conversion_learning_closed_loop.py --run
"""

import os
import sys
import json
from datetime import datetime
from data_quality_gate import should_block_strategy_update  # P1-AI-OPS-04
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict
sys.path.insert(0, str(Path(__file__).parent))
from real_data_bridge import get_conversion_records


PROJECT_ROOT = Path(__file__).parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
CONVERSION_DIR = REPORTS_DIR / "conversion"
CONVERSION_DIR.mkdir(parents=True, exist_ok=True)

STRATEGY_FILE = CONVERSION_DIR / "conversion_optimization_strategy.json"
LEARNING_REPORT = CONVERSION_DIR / "conversion_learning_report.md"
PERFORMANCE_HISTORY = CONVERSION_DIR / "conversion_performance_history.json"


class ConversionLearningClosedLoop:
    """Conversion Learning 闭环系统"""

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
            "cta_rules": {
                "positions": ["article_middle", "article_bottom", "sidebar"],
                "types": ["text_link", "button", "banner", "product_card"],
                "best_practices": {
                    "button_text": "Check prices",
                    "min_ctas_per_article": 2,
                    "max_ctas_per_article": 4,
                    "use_urgency": True,
                    "use_social_proof": True
                }
            },
            "product_rules": {
                "priority_products": ["hotels", "flights", "trains", "esim", "insurance", "tours"],
                "best_matching": {
                    "city_guide": ["hotels", "tours", "transfers"],
                    "transport_guide": ["flights", "trains", "car_rental"],
                    "travel_tips": ["esim", "insurance", "visa"],
                    "itinerary": ["hotels", "tours", "flights"]
                }
            },
            "best_cta_types": [],
            "best_cta_positions": [],
            "high_conversion_pages": [],
            "learning_insights": [],
            "strategy_changes": []
        }

    def observe_and_record(self) -> List[Dict]:
        """步骤1+2: Observe + Record"""
        print("\n" + "=" * 60)
        print("  步骤1+2: Observe + Record - 观察并记录转化表现")
        print("=" * 60)

        new_records = []
        # 从 real_data 读取真实数据（优先）
        try:
            real_records = get_conversion_records()
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
                        "type": "site_overall", "date": "",
                        "cta_type": "", "cta_position": "", "page": ""
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



        # 从联盟报告提取数据
        affiliate_report = REPORTS_DIR / "revenue" / "revenue_analytics_report.json"
        if affiliate_report.exists():
            try:
                with open(affiliate_report, encoding="utf-8") as f:
                    report_data = json.load(f)

                conversions = report_data.get("conversions", report_data.get("transactions", []))
                if isinstance(conversions, list):
                    for conv in conversions:
                        conv_id = conv.get("id", conv.get("order_id", ""))
                        if conv_id and not any(r.get("conversion_id") == conv_id for r in self.performance_history["records"]):
                            record = {
                                "conversion_id": conv_id,
                                "date": datetime.now().isoformat(),
                                "cta": {
                                    "type": conv.get("cta_type", "unknown"),
                                    "position": conv.get("cta_position", "unknown"),
                                    "copy": conv.get("cta_copy", ""),
                                    "product": conv.get("product", "unknown"),
                                    "partner": conv.get("partner", "unknown")
                                },
                                "metrics": {
                                    "impressions": conv.get("impressions", 0),
                                    "clicks": conv.get("clicks", 0),
                                    "conversions": conv.get("conversions", 1),
                                    "revenue": conv.get("revenue", conv.get("commission", 0.0))
                                },
                                "calculated": {
                                    "ctr": conv.get("clicks", 0) / max(1, conv.get("impressions", 1)) if conv.get("impressions", 0) > 0 else 0,
                                    "conversion_rate": conv.get("conversions", 1) / max(1, conv.get("clicks", 1)) if conv.get("clicks", 0) > 0 else 0,
                                    "revenue_per_click": conv.get("revenue", 0.0) / max(1, conv.get("clicks", 1)) if conv.get("clicks", 0) > 0 else 0
                                }
                            }
                            self.performance_history["records"].append(record)
                            new_records.append(record)
                            print(f"  ✅ 记录: {record['cta']['product']} @ {record['cta']['position']} (点击:{record['metrics']['clicks']}, 收入:${record['metrics']['revenue']:.2f})")
            except Exception as e:
                print(f"  ⚠️ 处理联盟报告失败: {e}")

        # 如果没有真实数据，添加示例记录用于演示
        if not new_records and not self.performance_history["records"]:
            print("  📝 暂无真实转化数据，使用示例数据演示闭环")
            sample_records = [
                {"cta_type": "button", "cta_position": "article_bottom", "product": "hotels", "partner": "booking", "impressions": 1000, "clicks": 50, "conversions": 2, "revenue": 45.0},
                {"cta_type": "text_link", "cta_position": "article_middle", "product": "esim", "partner": "airalo", "impressions": 800, "clicks": 40, "conversions": 3, "revenue": 30.0},
                {"cta_type": "banner", "cta_position": "sidebar", "product": "insurance", "partner": "safetywing", "impressions": 1200, "clicks": 30, "conversions": 1, "revenue": 12.0},
                {"cta_type": "product_card", "cta_position": "article_bottom", "product": "tours", "partner": "klook", "impressions": 600, "clicks": 45, "conversions": 4, "revenue": 80.0},
            ]
            for i, s in enumerate(sample_records):
                record = {
                    "conversion_id": f"sample_{i}",
                    "date": datetime.now().isoformat(),
                    "cta": {"type": s["cta_type"], "position": s["cta_position"], "copy": "", "product": s["product"], "partner": s["partner"]},
                    "metrics": {"impressions": s["impressions"], "clicks": s["clicks"], "conversions": s["conversions"], "revenue": s["revenue"]},
                    "calculated": {
                        "ctr": s["clicks"] / s["impressions"],
                        "conversion_rate": s["conversions"] / max(1, s["clicks"]),
                        "revenue_per_click": s["revenue"] / max(1, s["clicks"])
                    }
                }
                self.performance_history["records"].append(record)
                new_records.append(record)
                print(f"  ✅ 示例记录: {s['product']} @ {s['cta_position']} (CTR:{record['calculated']['ctr']*100:.1f}%, 收入:${s['revenue']:.2f})")

        self._save_json(PERFORMANCE_HISTORY, self.performance_history)
        print(f"\n  📊 新增记录: {len(new_records)} 条")
        print(f"  📊 历史总记录: {len(self.performance_history['records'])} 条")
        return new_records

    def analyze_and_learn(self) -> Dict:
        """步骤3+4: Analyze + Learn"""
        print("\n" + "=" * 60)
        print("  步骤3+4: Analyze + Learn - 分析并学习转化成功模式")
        print("=" * 60)

        insights = {"generated_at": datetime.now().isoformat(), "best_cta_types": [], "best_cta_positions": [], "best_products": [], "success_patterns": [], "recommendations": []}
        records = self.performance_history["records"]
        if not records:
            print("  ⚠️ 没有足够数据进行分析")
            return insights

        print(f"\n  📊 分析 {len(records)} 条转化记录...")

        # 数据规范化：补全所有硬编码字段
        for _r in records:
            _r.setdefault("cta", {})
            _r.setdefault("metrics", {})
            _r.setdefault("calculated", {})
            _r["cta"].setdefault("type", _r.get("type", "unknown"))
            _r["cta"].setdefault("position", _r.get("page", "unknown"))
            _r["cta"].setdefault("product", _r.get("product", "unknown"))
            _r["cta"].setdefault("partner", _r.get("partner", "unknown"))
            for _mk in ["impressions", "clicks", "conversions", "revenue"]:
                _r["metrics"].setdefault(_mk, 0)
            for _ck in ["ctr", "conversion_rate", "revenue_per_click"]:
                _r["calculated"].setdefault(_ck, 0)


        # 按CTA类型统计
        type_stats = defaultdict(lambda: {"count": 0, "impressions": 0, "clicks": 0, "conversions": 0, "revenue": 0.0})
        for r in records:
            cta_type = r["cta"]["type"]
            type_stats[cta_type]["count"] += 1
            type_stats[cta_type]["impressions"] += r["metrics"]["impressions"]
            type_stats[cta_type]["clicks"] += r["metrics"]["clicks"]
            type_stats[cta_type]["conversions"] += r["metrics"]["conversions"]
            type_stats[cta_type]["revenue"] += r["metrics"]["revenue"]

        for cta_type, stats in type_stats.items():
            stats["ctr"] = stats["clicks"] / max(1, stats["impressions"])
            stats["conversion_rate"] = stats["conversions"] / max(1, stats["clicks"])
            stats["revenue_per_click"] = stats["revenue"] / max(1, stats["clicks"])

        sorted_types = sorted(type_stats.items(), key=lambda x: x[1]["revenue_per_click"], reverse=True)
        insights["best_cta_types"] = [{"type": t, "revenue_per_click": s["revenue_per_click"], "ctr": s["ctr"], "conversion_rate": s["conversion_rate"]} for t, s in sorted_types[:5]]

        # 按CTA位置统计
        position_stats = defaultdict(lambda: {"count": 0, "impressions": 0, "clicks": 0, "conversions": 0, "revenue": 0.0})
        for r in records:
            position = r["cta"]["position"]
            position_stats[position]["count"] += 1
            position_stats[position]["impressions"] += r["metrics"]["impressions"]
            position_stats[position]["clicks"] += r["metrics"]["clicks"]
            position_stats[position]["conversions"] += r["metrics"]["conversions"]
            position_stats[position]["revenue"] += r["metrics"]["revenue"]

        for position, stats in position_stats.items():
            stats["ctr"] = stats["clicks"] / max(1, stats["impressions"])
            stats["conversion_rate"] = stats["conversions"] / max(1, stats["clicks"])

        sorted_positions = sorted(position_stats.items(), key=lambda x: x[1]["ctr"], reverse=True)
        insights["best_cta_positions"] = [{"position": p, "ctr": s["ctr"], "conversion_rate": s["conversion_rate"]} for p, s in sorted_positions[:5]]

        # 按产品统计
        product_stats = defaultdict(lambda: {"count": 0, "clicks": 0, "conversions": 0, "revenue": 0.0})
        for r in records:
            product = r["cta"]["product"]
            product_stats[product]["count"] += 1
            product_stats[product]["clicks"] += r["metrics"]["clicks"]
            product_stats[product]["conversions"] += r["metrics"]["conversions"]
            product_stats[product]["revenue"] += r["metrics"]["revenue"]

        sorted_products = sorted(product_stats.items(), key=lambda x: x[1]["revenue"], reverse=True)
        insights["best_products"] = [{"product": p, "revenue": s["revenue"], "conversions": s["conversions"]} for p, s in sorted_products[:5]]

        # 成功模式
        if insights["best_cta_types"]:
            best_type = insights["best_cta_types"][0]
            insights["success_patterns"].append({
                "pattern": "高转化CTA类型",
                "description": f"{best_type['type']}类型CTA表现最好，每次点击收入 ${best_type['revenue_per_click']:.2f}，CTR {best_type['ctr']*100:.1f}%",
                "recommendation": f"优先使用{best_type['type']}类型CTA"
            })

        if insights["best_cta_positions"]:
            best_position = insights["best_cta_positions"][0]
            insights["success_patterns"].append({
                "pattern": "高转化CTA位置",
                "description": f"{best_position['position']}位置CTR最高，达到 {best_position['ctr']*100:.1f}%",
                "recommendation": f"确保每篇文章在{best_position['position']}都有CTA"
            })

        # 建议
        insights["recommendations"] = [
            {"priority": "high", "type": "cta_optimization", "title": "推广高转化CTA类型", "description": f"使用表现最好的CTA类型替换低表现类型", "action": "全站CTA类型统一优化"},
            {"priority": "high", "type": "cta_position", "title": "优化CTA位置布局", "description": "确保高转化位置都有CTA", "action": "每篇文章至少2个CTA，覆盖最佳位置"},
            {"priority": "medium", "type": "product_expansion", "title": "扩展高收入产品覆盖", "description": "增加高收入产品的联盟链接覆盖", "action": "全站补充Top 3产品的联盟链接"},
        ]

        print(f"\n  🏆 最佳CTA类型: {insights['best_cta_types'][0]['type'] if insights['best_cta_types'] else 'N/A'}")
        print(f"  📍 最佳CTA位置: {insights['best_cta_positions'][0]['position'] if insights['best_cta_positions'] else 'N/A'}")
        print(f"  💰 最佳产品: {insights['best_products'][0]['product'] if insights['best_products'] else 'N/A'}")
        print(f"  💡 成功模式: {len(insights['success_patterns'])} 个")
        print(f"  🚀 优化建议: {len(insights['recommendations'])} 条")

        return insights

    def decide_and_update_strategy(self, insights: Dict) -> Dict:
        """步骤5+6: Decide + Act"""
        print("\n" + "=" * 60)
        print("  步骤5+6: Decide + Act - 决策并更新转化优化策略")
        print("=" * 60)

        strategy_changes = []

        if insights.get("best_cta_types"):
            old_types = self.current_strategy.get("best_cta_types", [])
            new_types = insights["best_cta_types"]
            if old_types != new_types:
                self.current_strategy["best_cta_types"] = new_types
                strategy_changes.append({"field": "best_cta_types", "reason": "基于转化数据分析，更新最佳CTA类型排名"})
                print(f"  ✅ 更新最佳CTA类型: {len(new_types)} 种")

        if insights.get("best_cta_positions"):
            old_positions = self.current_strategy.get("best_cta_positions", [])
            new_positions = insights["best_cta_positions"]
            if old_positions != new_positions:
                self.current_strategy["best_cta_positions"] = new_positions
                strategy_changes.append({"field": "best_cta_positions", "reason": "基于转化数据分析，更新最佳CTA位置排名"})
                print(f"  ✅ 更新最佳CTA位置: {len(new_positions)} 个")

        self.current_strategy["learning_insights"] = insights.get("success_patterns", [])
        self.current_strategy["strategy_changes"] = strategy_changes
        self.current_strategy["last_updated"] = datetime.now().isoformat()
        self.current_strategy["version"] = f"2.0-{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # P1-AI-OPS-04: Data Quality Gate
        _dq_records = self.performance_history.get("records", []) if isinstance(self.performance_history, dict) else (self.performance_history if isinstance(self.performance_history, list) else [])
        if should_block_strategy_update(_dq_records, "conversion"):
            print("  \u26a0\ufe0f 策略更新已跳过：数据质量不足")
            return self.current_strategy

        self._save_json(STRATEGY_FILE, self.current_strategy)
        print(f"\n  📊 策略变更: {len(strategy_changes)} 项")
        print(f"  📄 策略文件: {STRATEGY_FILE}")
        return self.current_strategy

    def generate_report(self, insights: Dict, strategy: Dict):
        """生成学习报告"""
        report = f"""# ChinaBound Travel Conversion Learning 闭环报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**策略版本**: {strategy.get('version', 'unknown')}

---

## 🔄 闭环状态
```
Observe ✅ → Record ✅ → Analyze ✅ → Learn ✅ → Decide ✅ → Act ✅ → Measure ⏳ → Learn Again 🔄
```

---

## 🏆 最佳CTA类型

| 类型 | CTR | 转化率 | 每次点击收入 |
|------|-----|--------|-------------|
"""
        for t in insights.get("best_cta_types", [])[:5]:
            report += f"| {t['type']} | {t['ctr']*100:.1f}% | {t['conversion_rate']*100:.1f}% | ${t['revenue_per_click']:.2f} |\n"

        report += """
---

## 📍 最佳CTA位置

| 位置 | CTR | 转化率 |
|------|-----|--------|
"""
        for p in insights.get("best_cta_positions", [])[:5]:
            report += f"| {p['position']} | {p['ctr']*100:.1f}% | {p['conversion_rate']*100:.1f}% |\n"

        report += """
---

## 💰 最佳产品

| 产品 | 收入 | 转化数 |
|------|------|--------|
"""
        for p in insights.get("best_products", [])[:5]:
            report += f"| {p['product']} | ${p['revenue']:.2f} | {p['conversions']} |\n"

        report += """
---

## 💡 学习洞察

"""
        for i, pattern in enumerate(insights.get("success_patterns", []), 1):
            report += f"### {i}. {pattern['pattern']}\n{pattern['description']}\n\n**建议:** {pattern.get('recommendation', '')}\n\n"

        report += """---

## 🚀 优化建议

"""
        for i, rec in enumerate(insights.get("recommendations", []), 1):
            icon = "🔴" if rec["priority"] == "high" else "🟡"
            report += f"{icon} **{rec['title']}**\n- {rec['description']}\n- 行动: {rec['action']}\n\n"

        report += f"""---

*报告由Conversion Learning闭环系统自动生成*
"""
        with open(LEARNING_REPORT, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"  ✅ 学习报告已生成: {LEARNING_REPORT}")

    def run_full_closed_loop(self):
        """运行完整闭环"""
        print("\n" + "=" * 60)
        print("  ChinaBound Travel Conversion Learning 完整闭环运行")
        print("=" * 60)
        print(f"\n  运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        new_records = self.observe_and_record()
        insights = self.analyze_and_learn()
        strategy = self.decide_and_update_strategy(insights)
        self.generate_report(insights, strategy)

        print("\n" + "=" * 60)
        print("  Conversion Learning 完整闭环运行完成")
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
    parser = argparse.ArgumentParser(description="Conversion Learning 闭环系统")
    parser.add_argument("--run", action="store_true", help="运行完整闭环")
    args = parser.parse_args()
    loop = ConversionLearningClosedLoop()
    if args.run:
        loop.run_full_closed_loop()
    else:
        loop.run_full_closed_loop()


if __name__ == "__main__":
    main()
