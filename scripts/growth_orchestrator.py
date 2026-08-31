#!/usr/bin/env python3
"""
Growth Orchestrator — lightweight decision coordination layer (NOT a new learning agent).

Reads all 6 strategy files + 7 agent reports, cross-references priorities,
and generates a unified growth decision report with ranked actions.

Architecture:
    DATA (strategies + reports)
        ↓
    Growth Orchestrator (read + prioritize + decide)
        ↓
    Unified Decision Report (ranked actions across domains)

Usage:
    python scripts/growth_orchestrator.py --run
    python scripts/growth_orchestrator.py --run --output reports/orchestration/growth_decision.md
"""
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
ORCHESTRATION_DIR = REPORTS_DIR / "orchestration"
ORCHESTRATION_DIR.mkdir(parents=True, exist_ok=True)

# Strategy files produced by Learning Closed Loops
STRATEGY_FILES = {
    "seo": REPORTS_DIR / "seo" / "seo_optimization_strategy.json",
    "revenue": REPORTS_DIR / "revenue" / "revenue_optimization_strategy.json",
    "conversion": REPORTS_DIR / "conversion" / "conversion_optimization_strategy.json",
    "content": REPORTS_DIR / "content" / "content_optimization_strategy.json",
    "social": REPORTS_DIR / "social" / "social_publish_strategy.json",
    "user": REPORTS_DIR / "user" / "user_optimization_strategy.json",
}

# Agent reports
AGENT_REPORTS = {
    "seo": REPORTS_DIR / "seo" / "seo_intelligence_report.md",
    "self_learning": REPORTS_DIR / "learning" / "self_learning_report.md",
    "revenue": REPORTS_DIR / "revenue" / "revenue_analytics_report.md",
    "conversion": REPORTS_DIR / "conversion" / "conversion_optimization_report.md",
    "content": REPORTS_DIR / "content" / "content_intelligence_report.md",
    "social": REPORTS_DIR / "social" / "social_intelligence_report.md",
    "user": REPORTS_DIR / "user" / "user_intelligence_report.md",
}

# Priority weights for action ranking
DOMAIN_WEIGHTS = {
    "revenue": 1.0,      # Direct revenue impact
    "conversion": 0.9,   # Conversion rate impact
    "seo": 0.8,          # Organic traffic growth
    "content": 0.7,      # Content quality and coverage
    "social": 0.6,       # Traffic acquisition
    "user": 0.5,         # Retention and engagement
}


class GrowthOrchestrator:
    """Read strategies + reports, prioritize actions, generate unified decision."""

    def __init__(self):
        self.strategies: Dict[str, Dict[str, Any]] = {}
        self.reports_available: Dict[str, bool] = {}
        self.actions: List[Dict[str, Any]] = []
        self.run_time = datetime.now().isoformat()

    def load_strategies(self) -> Dict[str, bool]:
        """Load all strategy files. Returns dict of domain -> loaded."""
        loaded = {}
        for domain, path in STRATEGY_FILES.items():
            if path.exists():
                try:
                    with open(path, encoding="utf-8") as f:
                        self.strategies[domain] = json.load(f)
                    loaded[domain] = True
                except Exception as e:
                    print(f"  ⚠️ {domain} strategy load failed: {e}")
                    loaded[domain] = False
            else:
                loaded[domain] = False
        return loaded

    def check_reports(self) -> Dict[str, bool]:
        """Check which agent reports exist."""
        for agent, path in AGENT_REPORTS.items():
            self.reports_available[agent] = path.exists()
        return self.reports_available

    def extract_actions(self) -> List[Dict[str, Any]]:
        """Extract prioritized actions from each strategy."""
        actions = []

        # SEO: high_priority_keywords + best_keywords
        seo = self.strategies.get("seo", {})
        for kw in seo.get("high_priority_keywords", [])[:5]:
            actions.append({
                "domain": "seo",
                "action": f"优先优化关键词/页面: {kw}",
                "priority_score": 0.9 * DOMAIN_WEIGHTS["seo"],
                "source": "seo_strategy.high_priority_keywords",
                "strategy_version": seo.get("version", "unknown"),
            })
        on_page = seo.get("on_page_rules", [])
        if isinstance(on_page, dict):
            on_page = [{"rule": k, "description": v} for k, v in list(on_page.items())[:3]]
        elif isinstance(on_page, list):
            on_page = on_page[:3]
        for rule in on_page:
            if isinstance(rule, dict):
                actions.append({
                    "domain": "seo",
                    "action": f"页面优化: {rule.get('rule', rule.get('description', str(rule)))[:80]}",
                    "priority_score": 0.7 * DOMAIN_WEIGHTS["seo"],
                    "source": "seo_strategy.on_page_rules",
                    "strategy_version": seo.get("version", "unknown"),
                })

        # Revenue: best_products + high_commission_products
        rev = self.strategies.get("revenue", {})
        for prod in rev.get("best_products", [])[:3]:
            name = prod.get("product", "") if isinstance(prod, dict) else str(prod)
            if name:
                actions.append({
                    "domain": "revenue",
                    "action": f"优先推广高转化产品: {name}",
                    "priority_score": 1.0 * DOMAIN_WEIGHTS["revenue"],
                    "source": "revenue_strategy.best_products",
                    "strategy_version": rev.get("version", "unknown"),
                })
        for prod in rev.get("high_commission_products", [])[:3]:
            name = prod.get("product", "") if isinstance(prod, dict) else str(prod)
            if name:
                actions.append({
                    "domain": "revenue",
                    "action": f"高佣金产品聚焦: {name}",
                    "priority_score": 0.85 * DOMAIN_WEIGHTS["revenue"],
                    "source": "revenue_strategy.high_commission_products",
                    "strategy_version": rev.get("version", "unknown"),
                })

        # Conversion: CTA optimization rules
        conv = self.strategies.get("conversion", {})
        cta_rules = conv.get("cta_rules", {})
        if cta_rules:
            for key, val in list(cta_rules.items())[:3]:
                actions.append({
                    "domain": "conversion",
                    "action": f"CTA优化: {key} = {str(val)[:60]}",
                    "priority_score": 0.8 * DOMAIN_WEIGHTS["conversion"],
                    "source": "conversion_strategy.cta_rules",
                    "strategy_version": conv.get("version", "unknown"),
                })

        # Content: topic priorities
        content = self.strategies.get("content", {})
        for topic in content.get("high_priority_topics", [])[:5]:
            actions.append({
                "domain": "content",
                "action": f"内容选题优先: {topic}",
                "priority_score": 0.75 * DOMAIN_WEIGHTS["content"],
                "source": "content_strategy.high_priority_topics",
                "strategy_version": content.get("version", "unknown"),
            })

        # Social: best publish times + hooks
        social = self.strategies.get("social", {})
        best_times = social.get("best_publish_times", {})
        if best_times:
            for platform, times in list(best_times.items())[:3]:
                actions.append({
                    "domain": "social",
                    "action": f"社媒发布时间优化: {platform} → {times}",
                    "priority_score": 0.6 * DOMAIN_WEIGHTS["social"],
                    "source": "social_strategy.best_publish_times",
                    "strategy_version": social.get("version", "unknown"),
                })

        # User: retention strategies
        user = self.strategies.get("user", {})
        for seg in user.get("high_intent_segments", [])[:3]:
            actions.append({
                "domain": "user",
                "action": f"高意向用户运营: {seg}",
                "priority_score": 0.65 * DOMAIN_WEIGHTS["user"],
                "source": "user_strategy.high_intent_segments",
                "strategy_version": user.get("version", "unknown"),
            })

        self.actions = sorted(actions, key=lambda x: x["priority_score"], reverse=True)
        return self.actions

    def generate_report(self, output_path: Optional[Path] = None) -> Path:
        """Generate unified growth decision report (Markdown + JSON)."""
        if output_path is None:
            output_path = ORCHESTRATION_DIR / "growth_decision_report.md"

        # JSON version
        json_path = output_path.with_suffix(".json")
        report_data = {
            "orchestrator_version": "1.0",
            "run_time": self.run_time,
            "strategies_loaded": {k: v for k, v in self.strategies.items()},
            "reports_available": self.reports_available,
            "total_actions": len(self.actions),
            "actions": self.actions[:20],
            "domain_summary": self._domain_summary(),
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)

        # Markdown version
        lines = [
            "# 🚀 Growth Orchestrator — 统一增长决策报告",
            "",
            f"**生成时间**: {self.run_time}",
            f"**Orchestrator 版本**: 1.0",
            "",
            "## 📊 数据源状态",
            "",
            "| 域 | 策略文件 | Agent报告 | 策略版本 |",
            "|---|---|---|---|",
        ]
        for domain in STRATEGY_FILES:
            strat_loaded = "✅" if domain in self.strategies else "❌"
            report_ok = "✅" if self.reports_available.get(domain, False) else "❌"
            version = self.strategies.get(domain, {}).get("version", "-")
            lines.append(f"| {domain} | {strat_loaded} | {report_ok} | {version} |")

        lines.extend([
            "",
            f"## 🎯 统一优先级行动（共 {len(self.actions)} 项，Top 15）",
            "",
            "| 排名 | 域 | 优先级分 | 行动 | 来源 |",
            "|---|---|---|---|---|",
        ])
        for i, action in enumerate(self.actions[:15], 1):
            lines.append(
                f"| {i} | {action['domain']} | {action['priority_score']:.2f} | "
                f"{action['action'][:80]} | {action['source']} |"
            )

        # Domain summary
        summary = self._domain_summary()
        lines.extend([
            "",
            "## 📈 各域行动分布",
            "",
            "| 域 | 行动数 | 最高优先级 |",
            "|---|---|---|",
        ])
        for domain, info in summary.items():
            lines.append(f"| {domain} | {info['count']} | {info['max_priority']:.2f} |")

        lines.extend([
            "",
            "## 📋 执行建议",
            "",
            "1. **P0（今日）**: 执行 Top 3 最高优先级行动",
            "2. **P1（本周）**: 执行 Top 4-10 行动",
            "3. **P2（本月）**: 执行剩余行动",
            "4. 所有行动均来自 Learning Closed Loop 策略，数据可追溯",
            "5. 策略变更前自动保存回滚快照（rollback mechanism）",
            "",
            "---",
            f"*本报告由 Growth Orchestrator v1.0 自动生成 | {self.run_time}*",
        ])

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        print(f"  ✅ Growth Decision Report: {output_path}")
        print(f"  ✅ JSON data: {json_path}")
        return output_path

    def _domain_summary(self) -> Dict[str, Dict[str, Any]]:
        """Generate per-domain action summary."""
        summary = {}
        for action in self.actions:
            domain = action["domain"]
            if domain not in summary:
                summary[domain] = {"count": 0, "max_priority": 0}
            summary[domain]["count"] += 1
            summary[domain]["max_priority"] = max(
                summary[domain]["max_priority"], action["priority_score"]
            )
        return summary

    def run(self, output_path: Optional[Path] = None) -> Dict[str, Any]:
        """Run full orchestration: load → extract → prioritize → report."""
        print("=" * 60)
        print("  Growth Orchestrator — 统一增长决策编排")
        print("=" * 60)

        print("\n📂 1. 加载策略文件...")
        loaded = self.load_strategies()
        for domain, ok in loaded.items():
            print(f"  {'✅' if ok else '❌'} {domain}")

        print("\n📋 2. 检查 Agent 报告...")
        reports = self.check_reports()
        for agent, ok in reports.items():
            print(f"  {'✅' if ok else '❌'} {agent}")

        print("\n🎯 3. 提取并排序行动...")
        actions = self.extract_actions()
        print(f"  共提取 {len(actions)} 项行动，按优先级排序")

        print("\n📝 4. 生成统一决策报告...")
        report_path = self.generate_report(output_path)

        print("\n" + "=" * 60)
        print(f"  ✅ Growth Orchestrator 完成: {len(actions)} actions")
        print("=" * 60)

        return {
            "success": True,
            "actions_count": len(actions),
            "report_path": str(report_path),
            "strategies_loaded": sum(1 for v in loaded.values() if v),
            "reports_available": sum(1 for v in reports.values() if v),
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Growth Orchestrator — 统一增长决策编排层")
    parser.add_argument("--run", action="store_true", help="运行完整编排")
    parser.add_argument("--output", type=str, default=None, help="输出报告路径")
    args = parser.parse_args()

    if args.run:
        orchestrator = GrowthOrchestrator()
        output = Path(args.output) if args.output else None
        result = orchestrator.run(output)
        sys.exit(0 if result["success"] else 1)
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
