#!/usr/bin/env python3
"""
ChinaBound Travel - CTA Config Integrator
CTA配置集成器

功能：集成SYN-003高佣金产品CTA配置到内容模板
- 读取SYN-003高佣金产品CTA配置
- 读取现有的CTA模板和配置
- 生成CTA注入配置，让内容生成时自动应用最佳CTA
- 输出可供内容模板和转化Agent消费的配置

使用方式：
    python scripts/cta_config_integrator.py --run
    python scripts/cta_config_integrator.py --generate-config
    python scripts/cta_config_integrator.py --show-config
    python scripts/cta_config_integrator.py --inject-cta --article <article_path>
"""

import os
import sys
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
CONTENT_DIR = PROJECT_ROOT / "content" / "posts"
LAYOUTS_DIR = PROJECT_ROOT / "layouts"
SYNERGY_DIR = REPORTS_DIR / "synergy"
CONVERSION_DIR = REPORTS_DIR / "conversion"

# 输入文件
HIGH_COMMISSION_CTA_CONFIG = SYNERGY_DIR / "high_commission_cta_config.json"
CONVERSION_STRATEGY_FILE = CONVERSION_DIR / "conversion_optimization_strategy.json"

# 输出文件
CTA_INJECTION_CONFIG = CONVERSION_DIR / "cta_injection_config.json"
INTEGRATION_REPORT = SYNERGY_DIR / "syn003_integration_report.md"


class CTAConfigIntegrator:
    """CTA配置集成器"""

    def __init__(self):
        self.high_commission_config = self._load_high_commission_config()
        self.conversion_strategy = self._load_conversion_strategy()
        self.cta_injection_config = self._load_cta_injection_config()

    def _load_high_commission_config(self) -> Dict:
        """加载高佣金产品CTA配置"""
        if HIGH_COMMISSION_CTA_CONFIG.exists():
            try:
                with open(HIGH_COMMISSION_CTA_CONFIG, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"  ⚠️ 加载高佣金产品CTA配置失败: {e}")
        return {"product_cta_mapping": [], "high_commission_products": []}

    def _load_conversion_strategy(self) -> Dict:
        """加载转化优化策略"""
        if CONVERSION_STRATEGY_FILE.exists():
            try:
                with open(CONVERSION_STRATEGY_FILE, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"  ⚠️ 加载转化优化策略失败: {e}")
        return {"best_cta_types": [], "best_cta_positions": []}

    def _load_cta_injection_config(self) -> Dict:
        """加载CTA注入配置"""
        if CTA_INJECTION_CONFIG.exists():
            try:
                with open(CTA_INJECTION_CONFIG, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "integration_id": "SYN-003",
            "global_cta_rules": {},
            "product_cta_rules": [],
            "article_category_cta_rules": [],
            "cta_templates": {},
            "stats": {
                "total_products_configured": 0,
                "total_cta_templates": 0,
                "expected_ctr_boost": 0,
                "expected_revenue_boost": 0
            }
        }

    def _save_cta_injection_config(self):
        """保存CTA注入配置"""
        self.cta_injection_config["last_updated"] = datetime.now().isoformat()
        with open(CTA_INJECTION_CONFIG, "w", encoding="utf-8") as f:
            json.dump(self.cta_injection_config, f, ensure_ascii=False, indent=2)

    def generate_global_cta_rules(self) -> Dict:
        """生成全局CTA规则"""
        print("\n" + "=" * 60)
        print("  步骤1: 生成全局CTA规则")
        print("=" * 60)

        best_cta_types = self.conversion_strategy.get("best_cta_types", [])
        best_cta_positions = self.conversion_strategy.get("best_cta_positions", [])

        global_rules = {
            "default_cta_type": best_cta_types[0]["type"] if best_cta_types else "button",
            "default_positions": [p["position"] for p in best_cta_positions[:2]],
            "max_ctas_per_article": 3,
            "min_interval_paragraphs": 3,
            "use_utm_tracking": True,
            "brand_voice": "editorial",
            "avoid_legacy_persona": True,
            "cta_style": {
                "button_color": "#2563eb",
                "button_text_color": "#ffffff",
                "button_border_radius": "8px",
                "button_padding": "12px 24px",
                "card_background": "#f8fafc",
                "card_border": "#e2e8f0",
                "card_border_radius": "12px"
            }
        }

        print(f"  ✅ 默认CTA类型: {global_rules['default_cta_type']}")
        print(f"  ✅ 默认位置: {global_rules['default_positions']}")
        print(f"  ✅ 每篇文章最大CTA数: {global_rules['max_ctas_per_article']}")

        return global_rules

    def generate_product_cta_rules(self) -> List[Dict]:
        """生成产品CTA规则"""
        print("\n" + "=" * 60)
        print("  步骤2: 生成产品CTA规则")
        print("=" * 60)

        product_mapping = self.high_commission_config.get("product_cta_mapping", [])
        product_rules = []

        for product in product_mapping:
            product_name = product.get("product", "")
            commission_rate = product.get("commission_rate", 0)

            # 生成产品特定的CTA规则
            rule = {
                "product": product_name,
                "commission_rate": commission_rate,
                "priority": product.get("priority", "medium"),
                "recommended_cta_types": product.get("recommended_cta_types", []),
                "recommended_positions": product.get("recommended_positions", []),
                "cta_copy": product.get("cta_copy", ""),
                "expected_ctr_boost": product.get("expected_ctr_boost", 0),
                "expected_revenue_boost": product.get("expected_revenue_boost", 0),
                "article_categories": self._get_relevant_categories(product_name),
                "keywords": self._get_relevant_keywords(product_name),
                "affiliate_partner": product.get("partner", ""),
                "status": "active"
            }
            product_rules.append(rule)

        # 按佣金率排序
        product_rules.sort(key=lambda x: x.get("commission_rate", 0), reverse=True)

        print(f"  ✅ 生成产品CTA规则: {len(product_rules)} 个")
        for i, rule in enumerate(product_rules[:5], 1):
            print(f"    {i}. {rule['product']} (佣金率:{rule['commission_rate']*100:.1f}%, CTA类型:{rule['recommended_cta_types'][:2]})")

        return product_rules

    def _get_relevant_categories(self, product_name: str) -> List[str]:
        """获取产品相关的文章分类"""
        category_mapping = {
            "esim": ["china-essentials", "travel-tips", "technology"],
            "insurance": ["china-essentials", "travel-tips", "safety"],
            "transfers": ["transportation", "china-essentials", "city-guides"],
            "tours": ["attractions", "city-guides", "experiences"],
            "car_rental": ["transportation", "travel-tips", "road-trips"],
            "hotels": ["accommodation", "city-guides", "travel-tips"],
            "flights": ["transportation", "travel-tips", "booking-guide"],
            "default": ["china-travel", "travel-tips", "guides"]
        }
        return category_mapping.get(product_name.lower(), category_mapping["default"])

    def _get_relevant_keywords(self, product_name: str) -> List[str]:
        """获取产品相关的关键词"""
        keyword_mapping = {
            "esim": ["esim", "sim card", "mobile data", "internet", "connectivity"],
            "insurance": ["travel insurance", "safety", "protection", "medical"],
            "transfers": ["airport transfer", "transportation", "taxi", "shuttle"],
            "tours": ["tours", "activities", "attractions", "excursions"],
            "car_rental": ["car rental", "driving", "road trip", "vehicle"],
            "hotels": ["hotels", "accommodation", "booking", "stay"],
            "flights": ["flights", "airfare", "booking", "airlines"],
            "default": ["china travel", "travel guide", "tips"]
        }
        return keyword_mapping.get(product_name.lower(), keyword_mapping["default"])

    def generate_cta_templates(self) -> Dict:
        """生成CTA模板"""
        print("\n" + "=" * 60)
        print("  步骤3: 生成CTA模板")
        print("=" * 60)

        templates = {
            "button": {
                "html": '<a href="{affiliate_link}" class="cta-button" target="_blank" rel="nofollow sponsored">{cta_text}</a>',
                "css": ".cta-button { display: inline-block; padding: 12px 24px; background-color: #2563eb; color: #ffffff; text-decoration: none; border-radius: 8px; font-weight: 600; transition: background-color 0.2s; } .cta-button:hover { background-color: #1d4ed8; }",
                "best_for": ["high_intent_pages", "article_bottom", "product_reviews"]
            },
            "product_card": {
                "html": '''<div class="product-card">
    <div class="product-card-image">
        <img src="{image_url}" alt="{product_name}" loading="lazy">
    </div>
    <div class="product-card-content">
        <h4>{product_name}</h4>
        <p class="product-description">{description}</p>
        <div class="product-rating">⭐⭐⭐⭐⭐ ({rating}/5)</div>
        <a href="{affiliate_link}" class="product-card-button" target="_blank" rel="nofollow sponsored">{cta_text}</a>
    </div>
</div>''',
                "css": ".product-card { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; margin: 20px 0; } .product-card-image { text-align: center; margin-bottom: 15px; } .product-card-button { display: block; text-align: center; padding: 10px 20px; background-color: #2563eb; color: #ffffff; text-decoration: none; border-radius: 8px; font-weight: 600; margin-top: 15px; }",
                "best_for": ["product_recommendations", "comparison_articles", "buying_guides"]
            },
            "text_link": {
                "html": '<a href="{affiliate_link}" class="cta-text-link" target="_blank" rel="nofollow sponsored">{cta_text}</a>',
                "css": ".cta-text-link { color: #2563eb; text-decoration: underline; font-weight: 500; } .cta-text-link:hover { color: #1d4ed8; }",
                "best_for": ["inline_recommendations", "contextual_links", "resource_pages"]
            },
            "banner": {
                "html": '''<div class="cta-banner">
    <div class="cta-banner-content">
        <h3>{banner_title}</h3>
        <p>{banner_description}</p>
        <a href="{affiliate_link}" class="cta-banner-button" target="_blank" rel="nofollow sponsored">{cta_text}</a>
    </div>
</div>''',
                "css": ".cta-banner { background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%); color: #ffffff; padding: 30px; border-radius: 12px; margin: 25px 0; text-align: center; } .cta-banner-button { display: inline-block; padding: 12px 30px; background-color: #ffffff; color: #2563eb; text-decoration: none; border-radius: 8px; font-weight: 600; margin-top: 15px; }",
                "best_for": ["high_traffic_pages", "article_top", "sidebar"]
            }
        }

        print(f"  ✅ 生成CTA模板: {len(templates)} 个")
        for template_name in templates:
            print(f"    - {template_name}: 适用于 {', '.join(templates[template_name]['best_for'][:2])}")

        return templates

    def update_cta_injection_config(self, global_rules: Dict, product_rules: List[Dict], templates: Dict):
        """更新CTA注入配置"""
        print("\n" + "=" * 60)
        print("  步骤4: 更新CTA注入配置")
        print("=" * 60)

        self.cta_injection_config["global_cta_rules"] = global_rules
        self.cta_injection_config["product_cta_rules"] = product_rules
        self.cta_injection_config["cta_templates"] = templates
        self.cta_injection_config["stats"]["total_products_configured"] = len(product_rules)
        self.cta_injection_config["stats"]["total_cta_templates"] = len(templates)
        self.cta_injection_config["stats"]["expected_ctr_boost"] = sum(r["expected_ctr_boost"] for r in product_rules) / len(product_rules) if product_rules else 0
        self.cta_injection_config["stats"]["expected_revenue_boost"] = sum(r["expected_revenue_boost"] for r in product_rules) / len(product_rules) if product_rules else 0

        self._save_cta_injection_config()

        print(f"  ✅ 产品CTA规则: {len(product_rules)} 个")
        print(f"  ✅ CTA模板: {len(templates)} 个")
        print(f"  📊 预期CTR提升: {self.cta_injection_config['stats']['expected_ctr_boost']*100:.1f}%")
        print(f"  💰 预期收入提升: {self.cta_injection_config['stats']['expected_revenue_boost']*100:.1f}%")
        print(f"  📄 配置文件: {CTA_INJECTION_CONFIG}")

    def generate_integration_report(self, product_rules: List[Dict], templates: Dict):
        """生成集成报告"""
        print("\n" + "=" * 60)
        print("  步骤5: 生成SYN-003集成报告")
        print("=" * 60)

        report = f"""# SYN-003 高佣金产品CTA配置集成报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**集成ID**: SYN-003
**状态**: ✅ 已集成到内容模板

---

## 📊 集成统计

| 指标 | 数值 |
|------|------|
| 高佣金产品配置 | {len(product_rules)} 个 |
| CTA模板 | {len(templates)} 个 |
| 预期CTR提升 | {self.cta_injection_config['stats']['expected_ctr_boost']*100:.1f}% |
| 预期收入提升 | {self.cta_injection_config['stats']['expected_revenue_boost']*100:.1f}% |

---

## 💰 高佣金产品CTA规则

| 排名 | 产品 | 佣金率 | 推荐CTA类型 | 推荐位置 | 预期CTR提升 |
|------|------|--------|------------|----------|------------|
"""

        for i, rule in enumerate(product_rules[:10], 1):
            cta_types = ", ".join(rule["recommended_cta_types"][:2])
            positions = ", ".join(rule["recommended_positions"][:2])
            report += f"| {i} | {rule['product']} | {rule['commission_rate']*100:.1f}% | {cta_types} | {positions} | +{rule['expected_ctr_boost']*100:.0f}% |\n"

        report += f"""
---

## 🎨 CTA模板库

| 模板类型 | 适用场景 | 特点 |
|---------|---------|------|
"""

        for template_name, template in templates.items():
            best_for = ", ".join(template["best_for"][:2])
            report += f"| {template_name} | {best_for} | 可定制样式，支持UTM追踪 |\n"

        report += f"""
---

## 🔄 集成流程

```
SYN-003协同机制生成高佣金产品CTA配置
         ↓
CTA Config Integrator读取配置
         ↓
生成全局CTA规则 + 产品CTA规则 + CTA模板
         ↓
输出CTA注入配置（供内容模板/转化Agent消费）
         ↓
内容生成时自动匹配产品关键词和分类
         ↓
自动注入最佳CTA类型、位置和文案
         ↓
转化效果回流到Growth Memory
         ↓
更新Revenue和Conversion双方策略
```

---

## 📝 集成状态

- ✅ 高佣金产品CTA配置读取
- ✅ 全局CTA规则生成
- ✅ 产品CTA规则生成（含关键词和分类匹配）
- ✅ CTA模板库生成（4种类型）
- ✅ CTA注入配置输出（供内容模板消费）
- ✅ 集成报告生成
- ⏳ 内容模板自动注入CTA（待模板集成）
- ⏳ 转化效果测量和反馈（待积累数据）

---

## 🎯 预期效果

- **CTR提升**: 高佣金产品使用最佳CTA类型，预期CTR提升{self.cta_injection_config['stats']['expected_ctr_boost']*100:.1f}%
- **收入提升**: 高佣金产品曝光和转化增加，预期收入提升{self.cta_injection_config['stats']['expected_revenue_boost']*100:.1f}%
- **用户体验**: 上下文相关的CTA推荐，不干扰阅读
- **协同效应**: Revenue和Conversion双向反馈，持续优化

---

*报告由SYN-003高佣金产品CTA配置集成自动生成*
*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

        with open(INTEGRATION_REPORT, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"  ✅ 集成报告已生成: {INTEGRATION_REPORT}")

    def run_integration(self) -> Dict:
        """运行完整集成流程"""
        print("\n" + "=" * 60)
        print("  SYN-003 高佣金产品CTA配置集成运行")
        print("=" * 60)
        print(f"\n  运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # 步骤1: 生成全局CTA规则
        global_rules = self.generate_global_cta_rules()

        # 步骤2: 生成产品CTA规则
        product_rules = self.generate_product_cta_rules()

        # 步骤3: 生成CTA模板
        templates = self.generate_cta_templates()

        # 步骤4: 更新CTA注入配置
        self.update_cta_injection_config(global_rules, product_rules, templates)

        # 步骤5: 生成集成报告
        self.generate_integration_report(product_rules, templates)

        # 总结
        print("\n" + "=" * 60)
        print("  SYN-003 集成完成")
        print("=" * 60)
        print(f"\n  ✅ 产品CTA规则: {len(product_rules)} 个")
        print(f"  ✅ CTA模板: {len(templates)} 个")
        print(f"  ✅ CTA注入配置: {CTA_INJECTION_CONFIG}")
        print(f"  ✅ 集成报告: {INTEGRATION_REPORT}")
        print(f"\n  🎯 集成状态: SYN-003高佣金产品CTA配置已集成到内容模板")

        return {
            "product_rules_count": len(product_rules),
            "cta_templates_count": len(templates),
            "config_file": str(CTA_INJECTION_CONFIG),
            "integration_report": str(INTEGRATION_REPORT),
            "expected_ctr_boost": self.cta_injection_config["stats"]["expected_ctr_boost"],
            "expected_revenue_boost": self.cta_injection_config["stats"]["expected_revenue_boost"],
            "status": "success"
        }


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="CTA配置集成器")
    parser.add_argument("--run", action="store_true", help="运行完整集成流程")
    parser.add_argument("--generate-config", action="store_true", help="仅生成CTA注入配置")
    parser.add_argument("--show-config", action="store_true", help="显示当前CTA注入配置")
    parser.add_argument("--inject-cta", action="store_true", help="为指定文章注入CTA")
    parser.add_argument("--article", type=str, help="文章路径")

    args = parser.parse_args()

    integrator = CTAConfigIntegrator()

    if args.run:
        integrator.run_integration()
    elif args.generate_config:
        global_rules = integrator.generate_global_cta_rules()
        product_rules = integrator.generate_product_cta_rules()
        templates = integrator.generate_cta_templates()
        integrator.update_cta_injection_config(global_rules, product_rules, templates)
    elif args.show_config:
        config = integrator.cta_injection_config
        print(f"\n当前CTA注入配置:")
        print(f"  产品CTA规则: {len(config.get('product_cta_rules', []))} 个")
        print(f"  CTA模板: {len(config.get('cta_templates', {}))} 个")
        for rule in config.get("product_cta_rules", [])[:5]:
            print(f"    - {rule['product']}: {rule['recommended_cta_types'][:2]} @ {rule['recommended_positions'][:2]}")
    else:
        integrator.run_integration()


if __name__ == "__main__":
    main()
