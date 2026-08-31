#!/usr/bin/env python3
"""
ChinaBound Travel - Revenue Learning 闭环系统
Revenue Learning Closed Loop

功能：打通收入分析的完整学习闭环
Observe → Record → Analyze → Learn → Decide → Act → Measure → Learn

记录维度：产品/渠道/合作伙伴/点击/转化/佣金/ROI

使用方式：
    python scripts/revenue_learning_closed_loop.py --run
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict
sys.path.insert(0, str(Path(__file__).parent))
from real_data_bridge import get_revenue_records
from strategy_change_logger import make_change, STRATEGY_VERSION, save_rollback


PROJECT_ROOT = Path(__file__).parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
REVENUE_DIR = REPORTS_DIR / "revenue"
REVENUE_DIR.mkdir(parents=True, exist_ok=True)

STRATEGY_FILE = REVENUE_DIR / "revenue_optimization_strategy.json"
LEARNING_REPORT = REVENUE_DIR / "revenue_learning_report.md"
PERFORMANCE_HISTORY = REVENUE_DIR / "revenue_performance_history.json"


class RevenueLearningClosedLoop:
    """Revenue Learning 闭环系统"""

    def __init__(self):
        self.performance_history = self._load_json(PERFORMANCE_HISTORY, {"records": [], "version": "1.0"})
        self.current_strategy = self._load_json(STRATEGY_FILE, self._default_strategy())
        self._using_sample_data = False  # Data quality gate: True when sample/fallback data is used

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
            "product_rules": {
                "priority_products": ["hotels", "flights", "tours", "esim", "insurance", "car_rental", "transfers"],
                "commission_threshold": 0.05,
                "min_commission_rate": 0.03
            },
            "channel_rules": {
                "best_channels": [],
                "channel_optimization": {
                    "organic_search": "提升SEO排名，增加高意图流量",
                    "social": "优化社媒内容，增加联盟链接曝光",
                    "email": "建立邮件列表，推送高转化产品",
                    "direct": "提升品牌认知，增加直接访问"
                }
            },
            "best_products": [],
            "best_partners": [],
            "best_channels": [],
            "high_commission_products": [],
            "learning_insights": [],
            "strategy_changes": []
        }

    def observe_and_record(self) -> List[Dict]:
        """步骤1+2: Observe + Record"""
        print("\n" + "=" * 60)
        print("  步骤1+2: Observe + Record - 观察并记录收入表现")
        print("=" * 60)

        new_records = []
        # 从 real_data 读取真实数据（优先）
        try:
            real_records = get_revenue_records()
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
                        "type": "overall", "partner": "", "date": "",
                        "product": "", "category": ""
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



        # 从Travelpayouts报告提取数据
        revenue_report = REPORTS_DIR / "revenue" / "revenue_analytics_report.json"
        if revenue_report.exists():
            try:
                with open(revenue_report, encoding="utf-8") as f:
                    report_data = json.load(f)

                products = report_data.get("products", report_data.get("product_performance", []))
                if isinstance(products, list):
                    for prod in products:
                        prod_name = prod.get("name", prod.get("product", ""))
                        if prod_name and not any(r.get("product") == prod_name for r in self.performance_history["records"]):
                            record = {
                                "product": prod_name,
                                "date": datetime.now().isoformat(),
                                "partner": prod.get("partner", prod.get("network", "unknown")),
                                "channel": prod.get("channel", "unknown"),
                                "metrics": {
                                    "impressions": prod.get("impressions", 0),
                                    "clicks": prod.get("clicks", 0),
                                    "bookings": prod.get("bookings", prod.get("conversions", 0)),
                                    "revenue": prod.get("revenue", prod.get("commission", 0.0)),
                                    "commission_rate": prod.get("commission_rate", 0.0)
                                },
                                "calculated": {
                                    "ctr": prod.get("clicks", 0) / max(1, prod.get("impressions", 1)) if prod.get("impressions", 0) > 0 else 0,
                                    "conversion_rate": prod.get("bookings", 0) / max(1, prod.get("clicks", 1)) if prod.get("clicks", 0) > 0 else 0,
                                    "revenue_per_click": prod.get("revenue", 0.0) / max(1, prod.get("clicks", 1)) if prod.get("clicks", 0) > 0 else 0,
                                    "roi": (prod.get("revenue", 0.0) / max(1, prod.get("impressions", 1)) * 1000) if prod.get("impressions", 0) > 0 else 0
                                }
                            }
                            self.performance_history["records"].append(record)
                            new_records.append(record)
                            print(f"  ✅ 记录: {prod_name} (点击:{record['metrics']['clicks']}, 收入:${record['metrics']['revenue']:.2f})")
            except Exception as e:
                print(f"  ⚠️ 处理收入报告失败: {e}")

        # 如果没有真实数据，添加示例记录
        if not new_records and not self.performance_history["records"]:
            print("  📝 暂无真实收入数据，使用示例数据演示闭环")
            self._using_sample_data = True  # Data quality gate: sample data cannot update strategy
            sample_products = [
                {"name": "hotels", "partner": "booking", "channel": "organic_search", "impressions": 10000, "clicks": 500, "bookings": 15, "revenue": 450.0, "commission_rate": 0.04},
                {"name": "flights", "partner": "trip", "channel": "social", "impressions": 8000, "clicks": 320, "bookings": 8, "revenue": 320.0, "commission_rate": 0.015},
                {"name": "tours", "partner": "klook", "channel": "email", "impressions": 5000, "clicks": 250, "bookings": 12, "revenue": 360.0, "commission_rate": 0.05},
                {"name": "esim", "partner": "airalo", "channel": "social", "impressions": 6000, "clicks": 300, "bookings": 20, "revenue": 200.0, "commission_rate": 0.20},
                {"name": "insurance", "partner": "safetywing", "channel": "organic_search", "impressions": 4000, "clicks": 160, "bookings": 6, "revenue": 180.0, "commission_rate": 0.10},
                {"name": "car_rental", "partner": "rentalcars", "channel": "direct", "impressions": 3000, "clicks": 120, "bookings": 4, "revenue": 120.0, "commission_rate": 0.06},
                {"name": "transfers", "partner": "getyourguide", "channel": "social", "impressions": 2000, "clicks": 100, "bookings": 5, "revenue": 75.0, "commission_rate": 0.08},
            ]
            for s in sample_products:
                record = {
                    "product": s["name"],
                    "date": datetime.now().isoformat(),
                    "partner": s["partner"],
                    "channel": s["channel"],
                    "metrics": {k: s[k] for k in ["impressions", "clicks", "bookings", "revenue", "commission_rate"]},
                    "calculated": {
                        "ctr": s["clicks"] / s["impressions"],
                        "conversion_rate": s["bookings"] / max(1, s["clicks"]),
                        "revenue_per_click": s["revenue"] / max(1, s["clicks"]),
                        "roi": (s["revenue"] / s["impressions"]) * 1000
                    }
                }
                self.performance_history["records"].append(record)
                new_records.append(record)
                print(f"  ✅ 示例记录: {s['name']} (CTR:{record['calculated']['ctr']*100:.1f}%, 收入:${s['revenue']:.2f})")

        self._save_json(PERFORMANCE_HISTORY, self.performance_history)
        print(f"\n  📊 新增记录: {len(new_records)} 条")
        print(f"  📊 历史总记录: {len(self.performance_history['records'])} 条")
        return new_records

    def analyze_and_learn(self) -> Dict:
        """步骤3+4: Analyze + Learn"""
        print("\n" + "=" * 60)
        print("  步骤3+4: Analyze + Learn - 分析并学习收入成功模式")
        print("=" * 60)

        insights = {"generated_at": datetime.now().isoformat(), "best_products": [], "best_partners": [], "best_channels": [], "high_commission_products": [], "success_patterns": [], "recommendations": []}
        records = self.performance_history["records"]
        if not records:
            print("  ⚠️ 没有足够数据进行分析")
            return insights

        print(f"\n  📊 分析 {len(records)} 个产品...")

        # 数据规范化：补全所有硬编码字段
        for _r in records:
            _r.setdefault("product", _r.get("type", _r.get("partner", "unknown")))
            _r.setdefault("partner", _r.get("partner", "unknown"))
            _r.setdefault("channel", _r.get("channel", "unknown"))
            _r.setdefault("metrics", {})
            _r.setdefault("calculated", {})
            for _mk in ["impressions", "clicks", "bookings", "revenue", "commission_rate"]:
                _r["metrics"].setdefault(_mk, 0)
            # 从 revenue_snapshot 映射
            if _r["metrics"]["bookings"] == 0:
                _r["metrics"]["bookings"] = _r["metrics"].get("conversions", 0)
            for _ck in ["ctr", "conversion_rate", "revenue_per_click", "roi"]:
                _r["calculated"].setdefault(_ck, 0)


        # 按收入排序
        sorted_by_revenue = sorted(records, key=lambda x: x["metrics"]["revenue"], reverse=True)
        insights["best_products"] = [{"product": r["product"], "revenue": r["metrics"]["revenue"], "clicks": r["metrics"]["clicks"], "conversion_rate": r["calculated"]["conversion_rate"], "commission_rate": r["metrics"]["commission_rate"]} for r in sorted_by_revenue]

        # 按ROI排序
        sorted_by_roi = sorted(records, key=lambda x: x["calculated"]["roi"], reverse=True)
        insights["best_roi_products"] = [{"product": r["product"], "roi": r["calculated"]["roi"], "revenue": r["metrics"]["revenue"], "impressions": r["metrics"]["impressions"]} for r in sorted_by_roi[:5]]

        # 按佣金率排序
        sorted_by_commission = sorted(records, key=lambda x: x["metrics"]["commission_rate"], reverse=True)
        insights["high_commission_products"] = [{"product": r["product"], "commission_rate": r["metrics"]["commission_rate"], "revenue": r["metrics"]["revenue"]} for r in sorted_by_commission[:5]]

        # 按合作伙伴统计
        partner_stats = defaultdict(lambda: {"revenue": 0.0, "clicks": 0, "products": 0})
        for r in records:
            partner = r["partner"]
            partner_stats[partner]["revenue"] += r["metrics"]["revenue"]
            partner_stats[partner]["clicks"] += r["metrics"]["clicks"]
            partner_stats[partner]["products"] += 1

        sorted_partners = sorted(partner_stats.items(), key=lambda x: x[1]["revenue"], reverse=True)
        insights["best_partners"] = [{"partner": p, "revenue": s["revenue"], "clicks": s["clicks"], "products": s["products"]} for p, s in sorted_partners[:5]]

        # 按渠道统计
        channel_stats = defaultdict(lambda: {"revenue": 0.0, "clicks": 0, "impressions": 0})
        for r in records:
            channel = r["channel"]
            channel_stats[channel]["revenue"] += r["metrics"]["revenue"]
            channel_stats[channel]["clicks"] += r["metrics"]["clicks"]
            channel_stats[channel]["impressions"] += r["metrics"]["impressions"]

        sorted_channels = sorted(channel_stats.items(), key=lambda x: x[1]["revenue"], reverse=True)
        insights["best_channels"] = [{"channel": c, "revenue": s["revenue"], "clicks": s["clicks"], "ctr": s["clicks"] / max(1, s["impressions"])} for c, s in sorted_channels[:5]]

        # 成功模式
        if insights["best_products"]:
            best_prod = insights["best_products"][0]
            insights["success_patterns"].append({
                "pattern": "高收入产品特征",
                "description": f"'{best_prod['product']}'产品收入最高，达到 ${best_prod['revenue']:.2f}，转化率 {best_prod['conversion_rate']*100:.1f}%",
                "recommendation": f"增加'{best_prod['product']}'产品的曝光和推荐位置",
                "key_metrics": {"高转化": f">{best_prod['conversion_rate']*100:.1f}%", "高点击": f">{best_prod['clicks']}次"}
            })

        if insights["high_commission_products"]:
            high_comm = insights["high_commission_products"][0]
            insights["success_patterns"].append({
                "pattern": "高佣金产品机会",
                "description": f"'{high_comm['product']}'佣金率最高，达到 {high_comm['commission_rate']*100:.1f}%，但当前收入 ${high_comm['revenue']:.2f}",
                "recommendation": f"重点推广高佣金'{high_comm['product']}'产品，提升流量和转化",
                "key_metrics": {"高佣金": f">{high_comm['commission_rate']*100:.1f}%", "增长潜力": "大"}
            })

        # 建议
        total_revenue = sum(r["metrics"]["revenue"] for r in records)
        insights["recommendations"] = [
            {"priority": "high", "type": "product_optimization", "title": "优化高收入产品曝光", "description": f"Top 3产品贡献主要收入，优化其展示位置和CTA", "action": "在高流量页面增加Top 3产品的联盟链接和推荐"},
            {"priority": "high", "type": "commission_optimization", "title": "重点推广高佣金产品", "description": f"高佣金产品当前收入偏低，有较大增长空间", "action": "创建高佣金产品专题内容，增加曝光和转化"},
            {"priority": "medium", "type": "channel_optimization", "title": "优化高转化渠道", "description": f"最佳渠道贡献最多收入，加大该渠道投入", "action": f"增加{insights['best_channels'][0]['channel'] if insights['best_channels'] else '最佳'}渠道的内容和推广"},
            {"priority": "medium", "type": "partner_optimization", "title": "深化高收入合作伙伴", "description": f"与高收入合作伙伴建立更深度的合作", "action": f"争取{insights['best_partners'][0]['partner'] if insights['best_partners'] else '最佳'}合作伙伴的更高佣金或专属优惠"},
        ]

        print(f"\n  🏆 最佳产品: {insights['best_products'][0]['product'] if insights['best_products'] else 'N/A'} (${insights['best_products'][0]['revenue']:.2f})")
        print(f"  💰 高佣金产品: {insights['high_commission_products'][0]['product'] if insights['high_commission_products'] else 'N/A'} ({insights['high_commission_products'][0]['commission_rate']*100:.1f}%)")
        print(f"  🤝 最佳合作伙伴: {insights['best_partners'][0]['partner'] if insights['best_partners'] else 'N/A'}")
        print(f"  📊 最佳渠道: {insights['best_channels'][0]['channel'] if insights['best_channels'] else 'N/A'}")
        print(f"  💡 成功模式: {len(insights['success_patterns'])} 个")
        print(f"  🚀 优化建议: {len(insights['recommendations'])} 条")

        return insights

    def decide_and_update_strategy(self, insights: Dict) -> Dict:
        """步骤5+6: Decide + Act"""
        # Data quality gate: SAMPLE/NOT_AVAILABLE data must NOT update strategy
        if getattr(self, "_using_sample_data", False):
            print("  ⚠️ 数据质量门控: 检测到SAMPLE/回退数据，策略更新已拦截（仅LIVE/CACHED可更新策略）")
            return self.current_strategy
        print("\n" + "=" * 60)
        print("  步骤5+6: Decide + Act - 决策并更新收入优化策略")
        print("=" * 60)

        strategy_changes = []

        if insights.get("best_products"):
            old_best = self.current_strategy.get("best_products", [])
            new_best = insights["best_products"][:5]
            if old_best != new_best:
                self.current_strategy["best_products"] = new_best
                strategy_changes.append({"field": "best_products", "reason": "基于收入分析，更新最佳产品排名"})
                print(f"  ✅ 更新最佳产品: {len(new_best)} 个")

        if insights.get("high_commission_products"):
            old_high = self.current_strategy.get("high_commission_products", [])
            new_high = insights["high_commission_products"]
            if old_high != new_high:
                self.current_strategy["high_commission_products"] = new_high
                strategy_changes.append({"field": "high_commission_products", "reason": "基于佣金率分析，更新高佣金产品列表"})
                print(f"  ✅ 更新高佣金产品: {len(new_high)} 个")

        if insights.get("best_channels"):
            old_channels = self.current_strategy.get("best_channels", [])
            new_channels = insights["best_channels"]
            if old_channels != new_channels:
                self.current_strategy["best_channels"] = new_channels
                strategy_changes.append({"field": "best_channels", "reason": "基于渠道收入分析，更新最佳渠道排名"})
                print(f"  ✅ 更新最佳渠道: {len(new_channels)} 个")

        self.current_strategy["learning_insights"] = insights.get("success_patterns", [])
        # Enrich change records with audit metadata (version/timestamp/evidence)
        _now = datetime.now().isoformat()
        for _ch in strategy_changes:
            _ch.setdefault("version", STRATEGY_VERSION)
            _ch.setdefault("timestamp", _now)
            _ch.setdefault("evidence", "based on performance data analysis")
        self.current_strategy["strategy_changes"] = strategy_changes
        self.current_strategy["last_updated"] = datetime.now().isoformat()
        self.current_strategy["version"] = f"2.0-{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                # P1-AI-OPS-03: Save rollback snapshot before strategy update
        try:
            save_rollback(self.current_strategy, str(STRATEGY_FILE), "revenue", self.current_strategy.get("strategy_changes", []))
        except Exception as _rb_e:
            print(f"  \u26a0\ufe0f Rollback skipped: {_rb_e}")

        self._save_json(STRATEGY_FILE, self.current_strategy)
        print(f"\n  📊 策略变更: {len(strategy_changes)} 项")
        print(f"  📄 策略文件: {STRATEGY_FILE}")
        return self.current_strategy

    def generate_report(self, insights: Dict, strategy: Dict):
        """生成学习报告"""
        report = f"""# ChinaBound Travel Revenue Learning 闭环报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**策略版本**: {strategy.get('version', 'unknown')}

---

## 🔄 闭环状态
```
Observe ✅ → Record ✅ → Analyze ✅ → Learn ✅ → Decide ✅ → Act ✅ → Measure ⏳ → Learn Again 🔄
```

---

## 💰 产品收入排名

| 产品 | 收入 | 点击 | 转化率 | 佣金率 |
|------|------|------|--------|--------|
"""
        for prod in insights.get("best_products", [])[:10]:
            report += f"| {prod['product']} | ${prod['revenue']:.2f} | {prod['clicks']} | {prod['conversion_rate']*100:.1f}% | {prod['commission_rate']*100:.1f}% |\n"

        report += """
---

## 💎 高佣金产品

| 产品 | 佣金率 | 当前收入 |
|------|--------|----------|
"""
        for prod in insights.get("high_commission_products", [])[:5]:
            report += f"| {prod['product']} | {prod['commission_rate']*100:.1f}% | ${prod['revenue']:.2f} |\n"

        report += """
---

## 🤝 最佳合作伙伴

| 合作伙伴 | 收入 | 点击 | 产品数 |
|----------|------|------|--------|
"""
        for partner in insights.get("best_partners", [])[:5]:
            report += f"| {partner['partner']} | ${partner['revenue']:.2f} | {partner['clicks']} | {partner['products']} |\n"

        report += """
---

## 📊 最佳渠道

| 渠道 | 收入 | 点击 | CTR |
|------|------|------|-----|
"""
        for channel in insights.get("best_channels", [])[:5]:
            report += f"| {channel['channel']} | ${channel['revenue']:.2f} | {channel['clicks']} | {channel['ctr']*100:.1f}% |\n"

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

*报告由Revenue Learning闭环系统自动生成*
"""
        with open(LEARNING_REPORT, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"  ✅ 学习报告已生成: {LEARNING_REPORT}")

    def run_full_closed_loop(self):
        """运行完整闭环"""
        print("\n" + "=" * 60)
        print("  ChinaBound Travel Revenue Learning 完整闭环运行")
        print("=" * 60)
        print(f"\n  运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        new_records = self.observe_and_record()
        insights = self.analyze_and_learn()
        strategy = self.decide_and_update_strategy(insights)
        self.generate_report(insights, strategy)

        print("\n" + "=" * 60)
        print("  Revenue Learning 完整闭环运行完成")
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
    parser = argparse.ArgumentParser(description="Revenue Learning 闭环系统")
    parser.add_argument("--run", action="store_true", help="运行完整闭环")
    args = parser.parse_args()
    loop = RevenueLearningClosedLoop()
    if args.run:
        loop.run_full_closed_loop()
    else:
        loop.run_full_closed_loop()


if __name__ == "__main__":
    main()
