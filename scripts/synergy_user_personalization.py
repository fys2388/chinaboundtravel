#!/usr/bin/env python3
"""
ChinaBound Travel - SYN-004 用户-内容-转化协同机制
User-Content-Conversion Synergy Mechanism

功能：实现高价值用户分层驱动个性化内容和CTA推荐
- 从User Learning策略读取高价值用户分层和行为模式
- 从Content Learning策略读取最佳内容类型和主题
- 从Conversion Learning策略读取最佳CTA类型和位置
- 生成个性化推荐配置（用户分层→内容推荐→CTA推荐）
- 输出可供内容模板和转化Agent消费的个性化配置

协同流程：
User Agent识别高价值用户分层 → 匹配最佳内容类型和CTA → 生成个性化推荐配置 → 内容模板/转化Agent消费 → 效果回流 → 更新三方策略

使用方式：
    python scripts/synergy_user_personalization.py --run
    python scripts/synergy_user_personalization.py --generate-config
    python scripts/synergy_user_personalization.py --show-config
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
USER_DIR = REPORTS_DIR / "user"
CONTENT_DIR = REPORTS_DIR / "content"
CONVERSION_DIR = REPORTS_DIR / "conversion"
SYNERGY_DIR = REPORTS_DIR / "synergy"
SYNERGY_DIR.mkdir(parents=True, exist_ok=True)

# 输出文件
PERSONALIZATION_CONFIG = SYNERGY_DIR / "user_personalization_config.json"
SYNERGY_REPORT_FILE = SYNERGY_DIR / "syn004_user_personalization_report.md"
SYNERGY_HISTORY_FILE = SYNERGY_DIR / "syn004_history.json"


class UserPersonalizationSynergy:
    """用户-内容-转化协同机制"""

    def __init__(self):
        self.user_strategy = self._load_user_strategy()
        self.content_strategy = self._load_content_strategy()
        self.conversion_strategy = self._load_conversion_strategy()
        self.personalization_config = self._load_personalization_config()
        self.history = self._load_history()

    def _load_user_strategy(self) -> Dict:
        """加载用户运营策略"""
        strategy_file = USER_DIR / "user_optimization_strategy.json"
        if strategy_file.exists():
            try:
                with open(strategy_file, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"  ⚠️ 加载用户策略失败: {e}")
        return {"high_value_segments": [], "user_segments": [], "learning_insights": []}

    def _load_content_strategy(self) -> Dict:
        """加载内容优化策略"""
        strategy_file = CONTENT_DIR / "content_optimization_strategy.json"
        if strategy_file.exists():
            try:
                with open(strategy_file, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"  ⚠️ 加载内容策略失败: {e}")
        return {"best_content_types": [], "best_topics": [], "learning_insights": []}

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

    def _load_personalization_config(self) -> Dict:
        """加载个性化推荐配置"""
        if PERSONALIZATION_CONFIG.exists():
            try:
                with open(PERSONALIZATION_CONFIG, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "synergy_id": "SYN-004",
            "high_value_segments": [],
            "personalization_rules": [],
            "segment_content_mapping": [],
            "segment_cta_mapping": [],
            "stats": {
                "total_segments_identified": 0,
                "total_personalization_rules": 0,
                "expected_ltv_boost": 0,
                "expected_conversion_boost": 0
            }
        }

    def _save_personalization_config(self):
        """保存个性化推荐配置"""
        self.personalization_config["last_updated"] = datetime.now().isoformat()
        with open(PERSONALIZATION_CONFIG, "w", encoding="utf-8") as f:
            json.dump(self.personalization_config, f, ensure_ascii=False, indent=2)

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

    def identify_high_value_segments(self) -> List[Dict]:
        """识别高价值用户分层"""
        print("\n" + "=" * 60)
        print("  步骤1: 识别高价值用户分层")
        print("=" * 60)

        high_value_segments = []

        # 从用户策略获取高价值分层
        strategy_segments = self.user_strategy.get("high_value_segments", [])
        if strategy_segments:
            print(f"  📋 从用户策略获取 {len(strategy_segments)} 个高价值分层")
            high_value_segments.extend(strategy_segments)

        # 从用户表现历史获取
        segments_file = USER_DIR / "user_performance_history.json"
        if segments_file.exists():
            try:
                with open(segments_file, encoding="utf-8") as f:
                    seg_data = json.load(f)
                records = seg_data.get("records", [])
                # 按LTV排序，取Top 5
                sorted_by_ltv = sorted(records, key=lambda x: x["metrics"].get("ltv", 0), reverse=True)
                for segment in sorted_by_ltv[:5]:
                    segment_name = segment.get("segment", "")
                    if segment_name and not any(s.get("segment") == segment_name for s in high_value_segments):
                        high_value_segments.append({
                            "segment": segment_name,
                            "user_count": segment["metrics"].get("user_count", 0),
                            "ltv": segment["metrics"].get("ltv", 0),
                            "conversion_rate": segment["metrics"].get("conversion_rate", 0),
                            "retention_rate": segment["metrics"].get("retention_rate", 0),
                            "avg_session_duration": segment["metrics"].get("avg_session_duration", 0),
                            "source": "user_performance",
                            "priority": "high" if segment["metrics"].get("ltv", 0) >= 10 else "medium"
                        })
                print(f"  📊 从用户表现获取 Top 5 高价值分层")
            except Exception as e:
                print(f"  ⚠️ 读取用户表现失败: {e}")

        # 如果没有真实数据，使用示例数据
        if not high_value_segments:
            print("  📝 暂无真实高价值分层，使用示例数据演示协同机制")
            sample_segments = [
                {"segment": "converter", "user_count": 30, "ltv": 16.67, "conversion_rate": 1.0, "retention_rate": 0.95, "avg_session_duration": 300, "source": "sample", "priority": "high"},
                {"segment": "subscriber", "user_count": 50, "ltv": 4.00, "conversion_rate": 0.08, "retention_rate": 0.90, "avg_session_duration": 180, "source": "sample", "priority": "high"},
                {"segment": "engaged_user", "user_count": 80, "ltv": 1.88, "conversion_rate": 0.05, "retention_rate": 0.85, "avg_session_duration": 120, "source": "sample", "priority": "medium"},
                {"segment": "returning_user", "user_count": 200, "ltv": 0.40, "conversion_rate": 0.02, "retention_rate": 0.60, "avg_session_duration": 60, "source": "sample", "priority": "medium"},
                {"segment": "new_user", "user_count": 500, "ltv": 0.05, "conversion_rate": 0.005, "retention_rate": 0.15, "avg_session_duration": 30, "source": "sample", "priority": "low"},
            ]
            high_value_segments = sample_segments

        print(f"\n  ✅ 识别高价值用户分层: {len(high_value_segments)} 个")
        for i, segment in enumerate(high_value_segments[:5], 1):
            print(f"    {i}. {segment['segment']} (用户数:{segment.get('user_count', 0)}, LTV:${segment.get('ltv', 0):.2f}, 转化率:{segment.get('conversion_rate', 0)*100:.1f}%)")

        return high_value_segments

    def get_best_content_and_cta_practices(self) -> Dict:
        """获取最佳内容和CTA实践"""
        print("\n" + "=" * 60)
        print("  步骤2: 获取最佳内容和CTA实践")
        print("=" * 60)

        best_practices = {
            "best_content_types": [],
            "best_topics": [],
            "best_cta_types": [],
            "best_cta_positions": []
        }

        # 从内容策略获取最佳内容类型
        content_types = self.content_strategy.get("best_content_types", [])
        if content_types:
            best_practices["best_content_types"] = content_types
            print(f"  📋 从内容策略获取 {len(content_types)} 个最佳内容类型")

        # 从转化策略获取最佳CTA
        cta_types = self.conversion_strategy.get("best_cta_types", [])
        cta_positions = self.conversion_strategy.get("best_cta_positions", [])
        if cta_types:
            best_practices["best_cta_types"] = cta_types
            print(f"  📋 从转化策略获取 {len(cta_types)} 个最佳CTA类型")
        if cta_positions:
            best_practices["best_cta_positions"] = cta_positions
            print(f"  📍 从转化策略获取 {len(cta_positions)} 个最佳CTA位置")

        # 如果没有真实数据，使用默认最佳实践
        if not best_practices["best_content_types"]:
            print("  📝 使用默认最佳内容实践")
            best_practices["best_content_types"] = [
                {"type": "complete_guide", "avg_duration": 240, "conversion_rate": 0.030, "description": "完整指南，全面覆盖"},
                {"type": "how_to_guide", "avg_duration": 180, "conversion_rate": 0.035, "description": "操作指南，步骤清晰"},
                {"type": "comparison", "avg_duration": 150, "conversion_rate": 0.040, "description": "对比分析，帮助决策"},
                {"type": "review", "avg_duration": 200, "conversion_rate": 0.045, "description": "评测内容，可信度高"}
            ]

        if not best_practices["best_cta_types"]:
            best_practices["best_cta_types"] = [
                {"type": "product_card", "ctr": 0.05, "revenue_per_click": 1.50, "description": "产品卡片"},
                {"type": "button", "ctr": 0.04, "revenue_per_click": 1.20, "description": "按钮CTA"},
                {"type": "text_link", "ctr": 0.03, "revenue_per_click": 0.80, "description": "文本链接"}
            ]

        if not best_practices["best_cta_positions"]:
            best_practices["best_cta_positions"] = [
                {"position": "article_bottom", "ctr": 0.045, "description": "文章底部"},
                {"position": "article_middle", "ctr": 0.035, "description": "文章中部"},
                {"position": "sidebar", "ctr": 0.025, "description": "侧边栏"}
            ]

        # 最佳主题（根据用户分层）
        best_practices["best_topics"] = {
            "converter": ["visa-free transit", "high-speed rail", "payment guide", "travel insurance", "esim"],
            "subscriber": ["travel guides", "itinerary planning", "cultural tips", "food guides", "photography"],
            "engaged_user": ["city guides", "attraction guides", "transportation", "accommodation", "local experiences"],
            "returning_user": ["new articles", "updated guides", "seasonal travel", "event guides", "travel news"],
            "new_user": ["china travel overview", "first-timer guide", "travel basics", "visa guide", "safety tips"]
        }

        return best_practices

    def generate_personalization_rules(self, high_value_segments: List[Dict], best_practices: Dict) -> List[Dict]:
        """生成个性化推荐规则"""
        print("\n" + "=" * 60)
        print("  步骤3: 生成个性化推荐规则")
        print("=" * 60)

        personalization_rules = []
        best_content_types = best_practices.get("best_content_types", [])
        best_cta_types = best_practices.get("best_cta_types", [])
        best_cta_positions = best_practices.get("best_cta_positions", [])
        best_topics = best_practices.get("best_topics", {})

        for segment in high_value_segments:
            segment_name = segment.get("segment", "")
            ltv = segment.get("ltv", 0)
            conversion_rate = segment.get("conversion_rate", 0)

            # 根据用户价值选择内容类型
            if ltv >= 10:  # 高价值用户
                recommended_content_types = [t["type"] for t in best_content_types if t["type"] in ["complete_guide", "comparison", "review"]][:3]
            elif ltv >= 1:  # 中价值用户
                recommended_content_types = [t["type"] for t in best_content_types if t["type"] in ["how_to_guide", "complete_guide"]][:2]
            else:  # 低价值用户
                recommended_content_types = [t["type"] for t in best_content_types if t["type"] in ["how_to_guide", "listicle"]][:2]

            # 根据转化率选择CTA类型
            if conversion_rate >= 0.05:  # 高转化用户
                recommended_cta_types = [t["type"] for t in best_cta_types if t["type"] in ["product_card", "button"]][:2]
                recommended_cta_positions = [p["position"] for p in best_cta_positions[:3]]  # 多位置
            else:  # 低转化用户
                recommended_cta_types = [t["type"] for t in best_cta_types if t["type"] in ["text_link", "button"]][:2]
                recommended_cta_positions = [p["position"] for p in best_cta_positions[:2]]  # 少位置

            # 推荐主题
            recommended_topics = best_topics.get(segment_name, best_topics.get("new_user", []))

            rule_item = {
                "rule_id": f"SYN004_{segment_name}",
                "segment": segment_name,
                "segment_priority": segment.get("priority", "medium"),
                "user_count": segment.get("user_count", 0),
                "ltv": ltv,
                "conversion_rate": conversion_rate,
                "retention_rate": segment.get("retention_rate", 0),
                "recommended_content_types": recommended_content_types,
                "recommended_topics": recommended_topics,
                "recommended_cta_types": recommended_cta_types,
                "recommended_cta_positions": recommended_cta_positions,
                "personalization_level": "high" if ltv >= 10 else "medium" if ltv >= 1 else "basic",
                "expected_ltv_boost": 0.15 if ltv >= 10 else 0.10 if ltv >= 1 else 0.05,
                "expected_conversion_boost": 0.20 if conversion_rate >= 0.05 else 0.10,
                "status": "ready",
                "created_at": datetime.now().isoformat(),
                "synergy_id": "SYN-004"
            }
            personalization_rules.append(rule_item)

        # 按优先级和LTV排序
        priority_order = {"high": 0, "medium": 1, "low": 2}
        personalization_rules.sort(key=lambda x: (priority_order.get(x["segment_priority"], 1), -x["ltv"]))

        print(f"\n  ✅ 生成个性化推荐规则: {len(personalization_rules)} 个")
        for i, rule in enumerate(personalization_rules[:5], 1):
            print(f"    {i}. [{rule['segment']}] 内容类型:{rule['recommended_content_types'][:2]}, CTA:{rule['recommended_cta_types'][:2]}, 个性化级别:{rule['personalization_level']}")

        return personalization_rules

    def update_personalization_config(self, high_value_segments: List[Dict], personalization_rules: List[Dict]):
        """更新个性化推荐配置"""
        print("\n" + "=" * 60)
        print("  步骤4: 更新个性化推荐配置")
        print("=" * 60)

        self.personalization_config["high_value_segments"] = high_value_segments
        self.personalization_config["personalization_rules"] = personalization_rules
        self.personalization_config["segment_content_mapping"] = [
            {"segment": r["segment"], "content_types": r["recommended_content_types"], "topics": r["recommended_topics"]}
            for r in personalization_rules
        ]
        self.personalization_config["segment_cta_mapping"] = [
            {"segment": r["segment"], "cta_types": r["recommended_cta_types"], "cta_positions": r["recommended_cta_positions"]}
            for r in personalization_rules
        ]
        self.personalization_config["stats"]["total_segments_identified"] = len(high_value_segments)
        self.personalization_config["stats"]["total_personalization_rules"] = len(personalization_rules)
        self.personalization_config["stats"]["expected_ltv_boost"] = sum(r["expected_ltv_boost"] for r in personalization_rules) / len(personalization_rules) if personalization_rules else 0
        self.personalization_config["stats"]["expected_conversion_boost"] = sum(r["expected_conversion_boost"] for r in personalization_rules) / len(personalization_rules) if personalization_rules else 0

        self._save_personalization_config()

        print(f"  ✅ 高价值用户分层: {len(high_value_segments)} 个")
        print(f"  ✅ 个性化推荐规则: {len(personalization_rules)} 个")
        print(f"  📊 预期LTV提升: {self.personalization_config['stats']['expected_ltv_boost']*100:.1f}%")
        print(f"  💰 预期转化率提升: {self.personalization_config['stats']['expected_conversion_boost']*100:.1f}%")
        print(f"  📄 配置文件: {PERSONALIZATION_CONFIG}")

    def generate_synergy_report(self, high_value_segments: List[Dict], personalization_rules: List[Dict]):
        """生成协同报告"""
        print("\n" + "=" * 60)
        print("  步骤5: 生成SYN-004协同报告")
        print("=" * 60)

        report = f"""# SYN-004 用户-内容-转化协同机制报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**协同ID**: SYN-004
**机制**: 高价值用户分层驱动个性化内容和CTA推荐

---

## 📊 协同统计

| 指标 | 数值 |
|------|------|
| 识别高价值用户分层 | {len(high_value_segments)} 个 |
| 生成个性化推荐规则 | {len(personalization_rules)} 个 |
| 高优先级分层 | {sum(1 for r in personalization_rules if r['segment_priority'] == 'high')} 个 |
| 中优先级分层 | {sum(1 for r in personalization_rules if r['segment_priority'] == 'medium')} 个 |
| 预期LTV提升 | {self.personalization_config['stats']['expected_ltv_boost']*100:.1f}% |
| 预期转化率提升 | {self.personalization_config['stats']['expected_conversion_boost']*100:.1f}% |

---

## 👥 高价值用户分层

| 排名 | 用户分层 | 用户数 | LTV | 转化率 | 留存率 | 优先级 |
|------|---------|--------|-----|--------|--------|--------|
"""

        for i, segment in enumerate(high_value_segments[:10], 1):
            report += f"| {i} | {segment['segment']} | {segment.get('user_count', 0)} | ${segment.get('ltv', 0):.2f} | {segment.get('conversion_rate', 0)*100:.1f}% | {segment.get('retention_rate', 0)*100:.1f}% | {segment.get('priority', '')} |\n"

        report += f"""
---

## 🎯 个性化推荐规则

| 用户分层 | 个性化级别 | 推荐内容类型 | 推荐CTA类型 | 推荐CTA位置 | 预期LTV提升 |
|---------|-----------|-------------|------------|------------|------------|
"""

        for rule in personalization_rules[:10]:
            content_types = ", ".join(rule["recommended_content_types"][:2])
            cta_types = ", ".join(rule["recommended_cta_types"][:2])
            cta_positions = ", ".join(rule["recommended_cta_positions"][:2])
            report += f"| {rule['segment']} | {rule['personalization_level']} | {content_types} | {cta_types} | {cta_positions} | +{rule['expected_ltv_boost']*100:.0f}% |\n"

        report += f"""
---

## 🔄 协同流程

```
User Agent识别高价值用户分层和行为模式
         ↓
匹配Content Agent学习到的最佳内容类型/主题
匹配Conversion Agent学习到的最佳CTA类型/位置
         ↓
生成个性化推荐规则（用户分层→内容推荐→CTA推荐）
         ↓
内容模板/转化Agent消费配置，自动应用个性化推荐
         ↓
用户行为和转化效果回流到Growth Memory
         ↓
更新User、Content、Conversion三方策略
         ↓
持续优化协同效果
```

---

## 🎯 预期效果

- **用户LTV提升**: 个性化推荐预期提升用户LTV {self.personalization_config['stats']['expected_ltv_boost']*100:.1f}%
- **转化率提升**: 个性化CTA预期提升转化率 {self.personalization_config['stats']['expected_conversion_boost']*100:.1f}%
- **用户留存提升**: 个性化内容推荐提升用户留存和 engagement
- **协同效应形成**: User、Content、Conversion三方双向反馈，持续优化

---

## 📝 实施状态

- ✅ 高价值用户分层识别机制
- ✅ 最佳内容和CTA实践加载
- ✅ 个性化推荐规则生成（内容+CTA+主题）
- ✅ 配置文件输出（供内容模板/转化Agent消费）
- ✅ 协同报告生成
- ⏳ 内容模板/转化Agent消费配置（待集成）
- ⏳ 效果测量和反馈（待积累数据）

---

*报告由SYN-004 用户-内容-转化协同机制自动生成*
*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

        with open(SYNERGY_REPORT_FILE, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"  ✅ 协同报告已生成: {SYNERGY_REPORT_FILE}")

    def run_synergy(self) -> Dict:
        """运行完整协同机制"""
        print("\n" + "=" * 60)
        print("  SYN-004 用户-内容-转化协同机制运行")
        print("=" * 60)
        print(f"\n  运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # 步骤1: 识别高价值用户分层
        high_value_segments = self.identify_high_value_segments()

        # 步骤2: 获取最佳内容和CTA实践
        best_practices = self.get_best_content_and_cta_practices()

        # 步骤3: 生成个性化推荐规则
        personalization_rules = self.generate_personalization_rules(high_value_segments, best_practices)

        # 步骤4: 更新个性化推荐配置
        self.update_personalization_config(high_value_segments, personalization_rules)

        # 步骤5: 生成协同报告
        self.generate_synergy_report(high_value_segments, personalization_rules)

        # 记录历史
        run_record = {
            "run_id": f"SYN004_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.now().isoformat(),
            "segments_count": len(high_value_segments),
            "rules_count": len(personalization_rules),
            "expected_ltv_boost": self.personalization_config["stats"]["expected_ltv_boost"],
            "expected_conversion_boost": self.personalization_config["stats"]["expected_conversion_boost"],
            "status": "success"
        }
        self.history["runs"].append(run_record)
        self._save_history()

        # 总结
        print("\n" + "=" * 60)
        print("  SYN-004 协同机制运行完成")
        print("=" * 60)
        print(f"\n  ✅ 高价值用户分层识别: {len(high_value_segments)} 个")
        print(f"  ✅ 个性化推荐规则: {len(personalization_rules)} 个")
        print(f"  ✅ 配置文件输出: {PERSONALIZATION_CONFIG}")
        print(f"  ✅ 协同报告生成: {SYNERGY_REPORT_FILE}")
        print(f"\n  📊 预期LTV提升: {self.personalization_config['stats']['expected_ltv_boost']*100:.1f}%")
        print(f"  💰 预期转化率提升: {self.personalization_config['stats']['expected_conversion_boost']*100:.1f}%")
        print(f"\n  🎯 协同状态: SYN-004机制已建立，等待内容模板/转化Agent消费配置")

        return {
            "segments_count": len(high_value_segments),
            "rules_count": len(personalization_rules),
            "config_file": str(PERSONALIZATION_CONFIG),
            "report_file": str(SYNERGY_REPORT_FILE),
            "expected_ltv_boost": self.personalization_config["stats"]["expected_ltv_boost"],
            "expected_conversion_boost": self.personalization_config["stats"]["expected_conversion_boost"],
            "status": "success"
        }


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="SYN-004 用户-内容-转化协同机制")
    parser.add_argument("--run", action="store_true", help="运行完整协同机制")
    parser.add_argument("--generate-config", action="store_true", help="仅生成个性化推荐配置")
    parser.add_argument("--show-config", action="store_true", help="显示当前个性化推荐配置")

    args = parser.parse_args()

    synergy = UserPersonalizationSynergy()

    if args.run:
        synergy.run_synergy()
    elif args.generate_config:
        high_value_segments = synergy.identify_high_value_segments()
        best_practices = synergy.get_best_content_and_cta_practices()
        personalization_rules = synergy.generate_personalization_rules(high_value_segments, best_practices)
        synergy.update_personalization_config(high_value_segments, personalization_rules)
    elif args.show_config:
        config = synergy.personalization_config
        print(f"\n当前个性化推荐配置:")
        print(f"  高价值分层: {len(config.get('high_value_segments', []))} 个")
        print(f"  个性化规则: {len(config.get('personalization_rules', []))} 个")
        for rule in config.get("personalization_rules", [])[:5]:
            print(f"    - [{rule['segment']}] 内容:{rule['recommended_content_types'][:2]}, CTA:{rule['recommended_cta_types'][:2]}")
    else:
        synergy.run_synergy()


if __name__ == "__main__":
    main()
