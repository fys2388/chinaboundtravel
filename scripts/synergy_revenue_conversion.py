#!/usr/bin/env python3
"""
ChinaBound Travel - SYN-003 收入-转化协同机制
Revenue-Conversion Synergy Mechanism

功能：实现高佣金产品自动使用最佳CTA类型和位置
- 从Revenue Learning策略读取高佣金产品列表
- 从Conversion Learning策略读取最佳CTA类型和位置
- 生成高佣金产品CTA优化配置
- 输出可供内容模板和转化Agent消费的配置文件

协同流程：
Revenue Agent识别高佣金产品 → 匹配最佳CTA类型/位置 → 生成CTA优化配置 → 内容模板/转化Agent消费 → 效果回流 → 更新双方策略

使用方式：
    python scripts/synergy_revenue_conversion.py --run
    python scripts/synergy_revenue_conversion.py --generate-config
    python scripts/synergy_revenue_conversion.py --show-config
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
REVENUE_DIR = REPORTS_DIR / "revenue"
CONVERSION_DIR = REPORTS_DIR / "conversion"
SYNERGY_DIR = REPORTS_DIR / "synergy"
SYNERGY_DIR.mkdir(parents=True, exist_ok=True)

# 输出文件
CTA_OPTIMIZATION_CONFIG = SYNERGY_DIR / "high_commission_cta_config.json"
SYNERGY_REPORT_FILE = SYNERGY_DIR / "syn003_revenue_conversion_report.md"
SYNERGY_HISTORY_FILE = SYNERGY_DIR / "syn003_history.json"


class RevenueConversionSynergy:
    """收入-转化协同机制"""

    def __init__(self):
        self.revenue_strategy = self._load_revenue_strategy()
        self.conversion_strategy = self._load_conversion_strategy()
        self.cta_config = self._load_cta_config()
        self.history = self._load_history()

    def _load_revenue_strategy(self) -> Dict:
        """加载收入优化策略"""
        strategy_file = REVENUE_DIR / "revenue_optimization_strategy.json"
        if strategy_file.exists():
            try:
                with open(strategy_file, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"  ⚠️ 加载收入策略失败: {e}")
        return {"high_commission_products": [], "best_products": [], "learning_insights": []}

    def _load_conversion_strategy(self) -> Dict:
        """加载转化优化策略"""
        strategy_file = CONVERSION_DIR / "conversion_optimization_strategy.json"
        if strategy_file.exists():
            try:
                with open(strategy_file, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"  ⚠️ 加载转化策略失败: {e}")
        return {"best_cta_types": [], "best_cta_positions": [], "learning_insights": []}

    def _load_cta_config(self) -> Dict:
        """加载CTA优化配置"""
        if CTA_OPTIMIZATION_CONFIG.exists():
            try:
                with open(CTA_OPTIMIZATION_CONFIG, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "synergy_id": "SYN-003",
            "high_commission_products": [],
            "best_cta_types": [],
            "best_cta_positions": [],
            "product_cta_mapping": [],
            "stats": {
                "total_products_optimized": 0,
                "total_cta_configs": 0,
                "expected_ctr_boost": 0,
                "expected_revenue_boost": 0
            }
        }

    def _save_cta_config(self):
        """保存CTA优化配置"""
        self.cta_config["last_updated"] = datetime.now().isoformat()
        with open(CTA_OPTIMIZATION_CONFIG, "w", encoding="utf-8") as f:
            json.dump(self.cta_config, f, ensure_ascii=False, indent=2)

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

    def identify_high_commission_products(self) -> List[Dict]:
        """识别高佣金产品"""
        print("\n" + "=" * 60)
        print("  步骤1: 识别高佣金产品")
        print("=" * 60)

        high_commission = []

        # 从收入策略获取高佣金产品
        strategy_products = self.revenue_strategy.get("high_commission_products", [])
        if strategy_products:
            print(f"  📋 从收入策略获取 {len(strategy_products)} 个高佣金产品")
            high_commission.extend(strategy_products)

        # 从收入表现历史获取
        performance_file = REVENUE_DIR / "revenue_performance_history.json"
        if performance_file.exists():
            try:
                with open(performance_file, encoding="utf-8") as f:
                    perf_data = json.load(f)
                records = perf_data.get("records", [])
                # 按佣金率排序，取Top 5
                sorted_by_commission = sorted(records, key=lambda x: x["metrics"].get("commission_rate", 0), reverse=True)
                for product in sorted_by_commission[:5]:
                    product_name = product.get("product", "")
                    if product_name and not any(p.get("product") == product_name for p in high_commission):
                        high_commission.append({
                            "product": product_name,
                            "commission_rate": product["metrics"].get("commission_rate", 0),
                            "revenue": product["metrics"].get("revenue", 0),
                            "clicks": product["metrics"].get("clicks", 0),
                            "partner": product.get("partner", ""),
                            "source": "revenue_performance",
                            "priority": "high" if product["metrics"].get("commission_rate", 0) >= 0.10 else "medium"
                        })
                print(f"  📊 从收入表现获取 Top 5 高佣金产品")
            except Exception as e:
                print(f"  ⚠️ 读取收入表现失败: {e}")

        # 如果没有真实数据，使用示例数据
        if not high_commission:
            print("  📝 暂无真实高佣金产品，使用示例数据演示协同机制")
            sample_products = [
                {"product": "esim", "commission_rate": 0.20, "revenue": 200.0, "clicks": 300, "partner": "airalo", "source": "sample", "priority": "high"},
                {"product": "insurance", "commission_rate": 0.10, "revenue": 180.0, "clicks": 160, "partner": "safetywing", "source": "sample", "priority": "high"},
                {"product": "transfers", "commission_rate": 0.08, "revenue": 75.0, "clicks": 100, "partner": "getyourguide", "source": "sample", "priority": "medium"},
                {"product": "tours", "commission_rate": 0.05, "revenue": 360.0, "clicks": 250, "partner": "klook", "source": "sample", "priority": "medium"},
                {"product": "car_rental", "commission_rate": 0.06, "revenue": 120.0, "clicks": 120, "partner": "rentalcars", "source": "sample", "priority": "medium"},
            ]
            high_commission = sample_products

        print(f"\n  ✅ 识别高佣金产品: {len(high_commission)} 个")
        for i, product in enumerate(high_commission[:5], 1):
            print(f"    {i}. {product['product']} (佣金率:{product.get('commission_rate', 0)*100:.1f}%, 收入:${product.get('revenue', 0):.2f})")

        return high_commission

    def get_best_cta_practices(self) -> Dict:
        """获取最佳CTA实践"""
        print("\n" + "=" * 60)
        print("  步骤2: 获取最佳CTA实践")
        print("=" * 60)

        best_practices = {
            "best_cta_types": [],
            "best_cta_positions": [],
            "cta_copy_templates": {}
        }

        # 从转化策略获取最佳CTA类型和位置
        best_types = self.conversion_strategy.get("best_cta_types", [])
        best_positions = self.conversion_strategy.get("best_cta_positions", [])

        if best_types:
            best_practices["best_cta_types"] = best_types
            print(f"  📋 从转化策略获取 {len(best_types)} 个最佳CTA类型")
            for cta_type in best_types[:3]:
                print(f"    - {cta_type.get('type', '')}: CTR {cta_type.get('ctr', 0)*100:.1f}%, 每次点击收入 ${cta_type.get('revenue_per_click', 0):.2f}")

        if best_positions:
            best_practices["best_cta_positions"] = best_positions
            print(f"  📍 从转化策略获取 {len(best_positions)} 个最佳CTA位置")
            for position in best_positions[:3]:
                print(f"    - {position.get('position', '')}: CTR {position.get('ctr', 0)*100:.1f}%")

        # 如果没有真实数据，使用默认最佳实践
        if not best_practices["best_cta_types"]:
            print("  📝 使用默认最佳CTA实践")
            best_practices["best_cta_types"] = [
                {"type": "product_card", "ctr": 0.05, "revenue_per_click": 1.50, "description": "产品卡片，包含图片、价格、评分"},
                {"type": "button", "ctr": 0.04, "revenue_per_click": 1.20, "description": "醒目的按钮CTA，使用行动导向文案"},
                {"type": "text_link", "ctr": 0.03, "revenue_per_click": 0.80, "description": "上下文相关的文本链接"},
                {"type": "banner", "ctr": 0.02, "revenue_per_click": 0.60, "description": "横幅广告，适合高流量页面"}
            ]

        if not best_practices["best_cta_positions"]:
            best_practices["best_cta_positions"] = [
                {"position": "article_bottom", "ctr": 0.045, "description": "文章底部，用户读完内容后"},
                {"position": "article_middle", "ctr": 0.035, "description": "文章中部，相关内容处"},
                {"position": "sidebar", "ctr": 0.025, "description": "侧边栏，全站可见"},
                {"position": "article_top", "ctr": 0.020, "description": "文章顶部，首屏可见"}
            ]

        # CTA文案模板
        best_practices["cta_copy_templates"] = {
            "esim": "Stay connected in China — compare eSIM plans",
            "insurance": "Travel worry-free — get China travel insurance",
            "transfers": "Skip the taxi line — book your airport transfer",
            "tours": "Skip the line — book top China tours",
            "car_rental": "Drive China your way — compare car rentals",
            "hotels": "Check today's best hotel rates",
            "flights": "Find the cheapest flights to China",
            "default": "Check prices and book now"
        }

        return best_practices

    def generate_product_cta_mapping(self, high_commission: List[Dict], best_practices: Dict) -> List[Dict]:
        """生成产品-CTA映射配置"""
        print("\n" + "=" * 60)
        print("  步骤3: 生成产品-CTA映射配置")
        print("=" * 60)

        mapping = []
        best_types = best_practices.get("best_cta_types", [])
        best_positions = best_practices.get("best_cta_positions", [])
        copy_templates = best_practices.get("cta_copy_templates", {})

        for product in high_commission:
            product_name = product.get("product", "")
            commission_rate = product.get("commission_rate", 0)

            # 根据佣金率选择CTA类型（高佣金用高转化类型）
            if commission_rate >= 0.10:
                recommended_types = [t for t in best_types if t.get("type") in ["product_card", "button"]][:2]
            else:
                recommended_types = best_types[:2]

            # 推荐位置（高佣金产品多位置覆盖）
            if commission_rate >= 0.10:
                recommended_positions = best_positions[:3]  # 3个位置
            else:
                recommended_positions = best_positions[:2]  # 2个位置

            # CTA文案
            cta_copy = copy_templates.get(product_name, copy_templates.get("default", "Check prices and book now"))

            mapping_item = {
                "mapping_id": f"SYN003_{product_name}",
                "product": product_name,
                "commission_rate": commission_rate,
                "current_revenue": product.get("revenue", 0),
                "partner": product.get("partner", ""),
                "priority": product.get("priority", "medium"),
                "recommended_cta_types": [t.get("type", "") for t in recommended_types],
                "recommended_positions": [p.get("position", "") for p in recommended_positions],
                "cta_copy": cta_copy,
                "expected_ctr_boost": 0.20 if commission_rate >= 0.10 else 0.10,
                "expected_revenue_boost": 0.25 if commission_rate >= 0.10 else 0.15,
                "status": "ready",
                "created_at": datetime.now().isoformat(),
                "synergy_id": "SYN-003"
            }
            mapping.append(mapping_item)

        # 按优先级排序
        priority_order = {"high": 0, "medium": 1, "low": 2}
        mapping.sort(key=lambda x: priority_order.get(x["priority"], 1))

        print(f"\n  ✅ 生成产品-CTA映射: {len(mapping)} 个")
        for i, item in enumerate(mapping[:5], 1):
            print(f"    {i}. {item['product']}: CTA类型 {item['recommended_cta_types'][:2]}, 位置 {item['recommended_positions'][:2]}")

        return mapping

    def update_cta_config(self, high_commission: List[Dict], best_practices: Dict, mapping: List[Dict]):
        """更新CTA优化配置"""
        print("\n" + "=" * 60)
        print("  步骤4: 更新CTA优化配置")
        print("=" * 60)

        self.cta_config["high_commission_products"] = high_commission
        self.cta_config["best_cta_types"] = best_practices.get("best_cta_types", [])
        self.cta_config["best_cta_positions"] = best_practices.get("best_cta_positions", [])
        self.cta_config["product_cta_mapping"] = mapping
        self.cta_config["stats"]["total_products_optimized"] = len(mapping)
        self.cta_config["stats"]["total_cta_configs"] = sum(len(m["recommended_cta_types"]) * len(m["recommended_positions"]) for m in mapping)
        self.cta_config["stats"]["expected_ctr_boost"] = sum(m["expected_ctr_boost"] for m in mapping) / len(mapping) if mapping else 0
        self.cta_config["stats"]["expected_revenue_boost"] = sum(m["expected_revenue_boost"] for m in mapping) / len(mapping) if mapping else 0

        self._save_cta_config()

        print(f"  ✅ 高佣金产品: {len(high_commission)} 个")
        print(f"  ✅ 产品-CTA映射: {len(mapping)} 个")
        print(f"  📊 预期CTR提升: {self.cta_config['stats']['expected_ctr_boost']*100:.1f}%")
        print(f"  💰 预期收入提升: {self.cta_config['stats']['expected_revenue_boost']*100:.1f}%")
        print(f"  📄 配置文件: {CTA_OPTIMIZATION_CONFIG}")

    def generate_synergy_report(self, high_commission: List[Dict], mapping: List[Dict]):
        """生成协同报告"""
        print("\n" + "=" * 60)
        print("  步骤5: 生成SYN-003协同报告")
        print("=" * 60)

        report = f"""# SYN-003 收入-转化协同机制报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**协同ID**: SYN-003
**机制**: 高佣金产品自动使用最佳CTA类型和位置

---

## 📊 协同统计

| 指标 | 数值 |
|------|------|
| 识别高佣金产品 | {len(high_commission)} 个 |
| 生成产品-CTA映射 | {len(mapping)} 个 |
| 高优先级产品 | {sum(1 for m in mapping if m['priority'] == 'high')} 个 |
| 中优先级产品 | {sum(1 for m in mapping if m['priority'] == 'medium')} 个 |
| 预期CTR提升 | {self.cta_config['stats']['expected_ctr_boost']*100:.1f}% |
| 预期收入提升 | {self.cta_config['stats']['expected_revenue_boost']*100:.1f}% |

---

## 💰 高佣金产品列表

| 排名 | 产品 | 佣金率 | 当前收入 | 合作伙伴 | 优先级 |
|------|------|--------|----------|----------|--------|
"""

        for i, product in enumerate(high_commission[:10], 1):
            report += f"| {i} | {product['product']} | {product.get('commission_rate', 0)*100:.1f}% | ${product.get('revenue', 0):.2f} | {product.get('partner', '')} | {product.get('priority', '')} |\n"

        report += f"""
---

## 🎯 产品-CTA映射配置

| 产品 | 推荐CTA类型 | 推荐位置 | CTA文案 | 预期CTR提升 |
|------|------------|----------|---------|------------|
"""

        for item in mapping[:10]:
            cta_types = ", ".join(item["recommended_cta_types"][:2])
            positions = ", ".join(item["recommended_positions"][:2])
            report += f"| {item['product']} | {cta_types} | {positions} | {item['cta_copy'][:30]}... | +{item['expected_ctr_boost']*100:.0f}% |\n"

        report += f"""
---

## 🔄 协同流程

```
Revenue Agent识别高佣金产品
         ↓
匹配Conversion Agent学习到的最佳CTA类型/位置
         ↓
生成产品-CTA映射配置（带推荐文案和预期提升）
         ↓
内容模板/转化Agent消费配置，自动应用最佳CTA
         ↓
转化效果回流到Growth Memory
         ↓
更新Revenue和Conversion双方策略
         ↓
持续优化协同效果
```

---

## 🎯 预期效果

- **CTR提升**: 高佣金产品使用最佳CTA类型，预期CTR提升15-25%
- **收入提升**: 高佣金产品曝光和转化增加，预期收入提升15-25%
- **ROI优化**: 资源向高佣金产品倾斜，提升整体ROI
- **协同效应**: 收入和转化双向反馈，持续优化双方策略

---

## 📝 实施状态

- ✅ 高佣金产品识别机制
- ✅ 最佳CTA实践加载
- ✅ 产品-CTA映射生成
- ✅ 配置文件输出（供内容模板/转化Agent消费）
- ✅ 协同报告生成
- ⏳ 内容模板/转化Agent消费配置（待集成）
- ⏳ 效果测量和反馈（待积累数据）

---

*报告由SYN-003收入-转化协同机制自动生成*
*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

        with open(SYNERGY_REPORT_FILE, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"  ✅ 协同报告已生成: {SYNERGY_REPORT_FILE}")

    def run_synergy(self) -> Dict:
        """运行完整协同机制"""
        print("\n" + "=" * 60)
        print("  SYN-003 收入-转化协同机制运行")
        print("=" * 60)
        print(f"\n  运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # 步骤1: 识别高佣金产品
        high_commission = self.identify_high_commission_products()

        # 步骤2: 获取最佳CTA实践
        best_practices = self.get_best_cta_practices()

        # 步骤3: 生成产品-CTA映射
        mapping = self.generate_product_cta_mapping(high_commission, best_practices)

        # 步骤4: 更新CTA优化配置
        self.update_cta_config(high_commission, best_practices, mapping)

        # 步骤5: 生成协同报告
        self.generate_synergy_report(high_commission, mapping)

        # 记录历史
        run_record = {
            "run_id": f"SYN003_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.now().isoformat(),
            "high_commission_count": len(high_commission),
            "mapping_count": len(mapping),
            "expected_ctr_boost": self.cta_config["stats"]["expected_ctr_boost"],
            "expected_revenue_boost": self.cta_config["stats"]["expected_revenue_boost"],
            "status": "success"
        }
        self.history["runs"].append(run_record)
        self._save_history()

        # 总结
        print("\n" + "=" * 60)
        print("  SYN-003 协同机制运行完成")
        print("=" * 60)
        print(f"\n  ✅ 高佣金产品识别: {len(high_commission)} 个")
        print(f"  ✅ 产品-CTA映射生成: {len(mapping)} 个")
        print(f"  ✅ 配置文件输出: {CTA_OPTIMIZATION_CONFIG}")
        print(f"  ✅ 协同报告生成: {SYNERGY_REPORT_FILE}")
        print(f"\n  📊 预期CTR提升: {self.cta_config['stats']['expected_ctr_boost']*100:.1f}%")
        print(f"  💰 预期收入提升: {self.cta_config['stats']['expected_revenue_boost']*100:.1f}%")
        print(f"\n  🎯 协同状态: SYN-003机制已建立，等待内容模板/转化Agent消费配置")

        return {
            "high_commission_count": len(high_commission),
            "mapping_count": len(mapping),
            "config_file": str(CTA_OPTIMIZATION_CONFIG),
            "report_file": str(SYNERGY_REPORT_FILE),
            "expected_ctr_boost": self.cta_config["stats"]["expected_ctr_boost"],
            "expected_revenue_boost": self.cta_config["stats"]["expected_revenue_boost"],
            "status": "success"
        }


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="SYN-003 收入-转化协同机制")
    parser.add_argument("--run", action="store_true", help="运行完整协同机制")
    parser.add_argument("--generate-config", action="store_true", help="仅生成CTA优化配置")
    parser.add_argument("--show-config", action="store_true", help="显示当前CTA优化配置")

    args = parser.parse_args()

    synergy = RevenueConversionSynergy()

    if args.run:
        synergy.run_synergy()
    elif args.generate_config:
        high_commission = synergy.identify_high_commission_products()
        best_practices = synergy.get_best_cta_practices()
        mapping = synergy.generate_product_cta_mapping(high_commission, best_practices)
        synergy.update_cta_config(high_commission, best_practices, mapping)
    elif args.show_config:
        config = synergy.cta_config
        print(f"\n当前CTA优化配置:")
        print(f"  高佣金产品: {len(config.get('high_commission_products', []))} 个")
        print(f"  产品-CTA映射: {len(config.get('product_cta_mapping', []))} 个")
        for item in config.get("product_cta_mapping", [])[:5]:
            print(f"    - {item['product']}: {item['recommended_cta_types'][:2]} @ {item['recommended_positions'][:2]}")
    else:
        synergy.run_synergy()


if __name__ == "__main__":
    main()
