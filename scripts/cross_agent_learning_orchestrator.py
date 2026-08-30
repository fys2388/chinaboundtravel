#!/usr/bin/env python3
"""
ChinaBound Travel - 跨Agent协同学习编排器
Cross-Agent Learning Orchestrator

功能：统一编排6大Agent学习闭环，建立跨Agent协同学习机制
- 统一Growth Memory数据管理
- 跨Agent数据共享和协同决策
- 统一学习洞察和优化建议
- 全局策略协调和冲突解决

6大Agent学习闭环：
1. Social Learning - 社媒发布策略学习
2. Content Learning - 内容优化策略学习
3. Conversion Learning - 转化优化策略学习
4. SEO Learning - SEO优化策略学习
5. User Learning - 用户运营策略学习
6. Revenue Learning - 收入分析策略学习

使用方式：
    python scripts/cross_agent_learning_orchestrator.py --run-all
    python scripts/cross_agent_learning_orchestrator.py --social
    python scripts/cross_agent_learning_orchestrator.py --content
    python scripts/cross_agent_learning_orchestrator.py --conversion
    python scripts/cross_agent_learning_orchestrator.py --seo
    python scripts/cross_agent_learning_orchestrator.py --user
    python scripts/cross_agent_learning_orchestrator.py --revenue
    python scripts/cross_agent_learning_orchestrator.py --generate-report
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
GROWTH_MEMORY_DIR = REPORTS_DIR / "growth_memory"
CROSS_AGENT_DIR = REPORTS_DIR / "cross_agent"
CROSS_AGENT_DIR.mkdir(parents=True, exist_ok=True)

# 输出文件
CROSS_AGENT_REPORT = CROSS_AGENT_DIR / "cross_agent_learning_report.md"
CROSS_AGENT_STRATEGY = CROSS_AGENT_DIR / "cross_agent_coordination_strategy.json"
GLOBAL_GROWTH_MEMORY = GROWTH_MEMORY_DIR / "global_growth_memory.json"

# 6大Agent学习闭环配置
AGENT_LEARNING_CONFIG = {
    "social": {
        "name": "Social Learning",
        "script": "social_learning_closed_loop.py",
        "strategy_file": REPORTS_DIR / "social" / "social_publish_strategy.json",
        "report_file": REPORTS_DIR / "social" / "social_learning_report.md",
        "description": "社媒发布策略学习"
    },
    "content": {
        "name": "Content Learning",
        "script": "content_learning_closed_loop.py",
        "strategy_file": REPORTS_DIR / "content" / "content_optimization_strategy.json",
        "report_file": REPORTS_DIR / "content" / "content_learning_report.md",
        "description": "内容优化策略学习"
    },
    "conversion": {
        "name": "Conversion Learning",
        "script": "conversion_learning_closed_loop.py",
        "strategy_file": REPORTS_DIR / "conversion" / "conversion_optimization_strategy.json",
        "report_file": REPORTS_DIR / "conversion" / "conversion_learning_report.md",
        "description": "转化优化策略学习"
    },
    "seo": {
        "name": "SEO Learning",
        "script": "seo_learning_closed_loop.py",
        "strategy_file": REPORTS_DIR / "seo" / "seo_optimization_strategy.json",
        "report_file": REPORTS_DIR / "seo" / "seo_learning_report.md",
        "description": "SEO优化策略学习"
    },
    "user": {
        "name": "User Learning",
        "script": "user_learning_closed_loop.py",
        "strategy_file": REPORTS_DIR / "user" / "user_optimization_strategy.json",
        "report_file": REPORTS_DIR / "user" / "user_learning_report.md",
        "description": "用户运营策略学习"
    },
    "revenue": {
        "name": "Revenue Learning",
        "script": "revenue_learning_closed_loop.py",
        "strategy_file": REPORTS_DIR / "revenue" / "revenue_optimization_strategy.json",
        "report_file": REPORTS_DIR / "revenue" / "revenue_learning_report.md",
        "description": "收入分析策略学习"
    }
}


class CrossAgentLearningOrchestrator:
    """跨Agent协同学习编排器"""

    def __init__(self):
        self.agent_results = {}
        self.global_memory = self._load_global_memory()
        self.coordination_strategy = self._load_coordination_strategy()

    def _load_global_memory(self) -> Dict:
        """加载全局Growth Memory"""
        if GLOBAL_GROWTH_MEMORY.exists():
            try:
                with open(GLOBAL_GROWTH_MEMORY, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "agents": {},
            "cross_agent_insights": [],
            "global_recommendations": [],
            "coordination_log": []
        }

    def _save_global_memory(self):
        """保存全局Growth Memory"""
        self.global_memory["last_updated"] = datetime.now().isoformat()
        with open(GLOBAL_GROWTH_MEMORY, "w", encoding="utf-8") as f:
            json.dump(self.global_memory, f, ensure_ascii=False, indent=2)

    def _load_coordination_strategy(self) -> Dict:
        """加载协同策略"""
        if CROSS_AGENT_STRATEGY.exists():
            try:
                with open(CROSS_AGENT_STRATEGY, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "coordination_rules": {
                "priority_order": ["revenue", "conversion", "user", "content", "seo", "social"],
                "conflict_resolution": "higher_priority_agent_wins",
                "data_sharing": "all_agents_share_growth_memory",
                "strategy_alignment": "weekly_cross_agent_review"
            },
            "agent_dependencies": {
                "social": ["content", "seo"],
                "content": ["seo", "user"],
                "conversion": ["content", "user", "revenue"],
                "seo": ["content"],
                "user": ["content", "conversion"],
                "revenue": ["conversion", "user"]
            },
            "synergy_opportunities": [],
            "active_initiatives": []
        }

    def _save_coordination_strategy(self):
        """保存协同策略"""
        self.coordination_strategy["last_updated"] = datetime.now().isoformat()
        with open(CROSS_AGENT_STRATEGY, "w", encoding="utf-8") as f:
            json.dump(self.coordination_strategy, f, ensure_ascii=False, indent=2)

    def run_agent_learning(self, agent_key: str) -> Dict:
        """运行单个Agent学习闭环"""
        config = AGENT_LEARNING_CONFIG.get(agent_key)
        if not config:
            return {"status": "error", "message": f"Unknown agent: {agent_key}"}

        print(f"\n{'='*60}")
        print(f"  运行: {config['name']}")
        print(f"{'='*60}")

        script_path = SCRIPTS_DIR / config["script"]
        if not script_path.exists():
            return {"status": "error", "message": f"Script not found: {script_path}"}

        try:
            result = subprocess.run(
                [sys.executable, str(script_path), "--run"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(PROJECT_ROOT)
            )

            # 读取策略文件
            strategy_data = {}
            if config["strategy_file"].exists():
                try:
                    with open(config["strategy_file"], encoding="utf-8") as f:
                        strategy_data = json.load(f)
                except Exception:
                    pass

            agent_result = {
                "status": "success" if result.returncode == 0 else "failed",
                "returncode": result.returncode,
                "stdout": result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout,
                "stderr": result.stderr[-1000:] if len(result.stderr) > 1000 else result.stderr,
                "strategy_version": strategy_data.get("version", "unknown"),
                "strategy_changes": len(strategy_data.get("strategy_changes", [])),
                "learning_insights": len(strategy_data.get("learning_insights", [])),
                "strategy_file": str(config["strategy_file"]),
                "report_file": str(config["report_file"])
            }

            # 更新全局Memory
            self.global_memory["agents"][agent_key] = {
                "name": config["name"],
                "last_run": datetime.now().isoformat(),
                "status": agent_result["status"],
                "strategy_version": agent_result["strategy_version"],
                "strategy_changes": agent_result["strategy_changes"],
                "learning_insights": agent_result["learning_insights"]
            }

            print(f"  ✅ 状态: {agent_result['status']}")
            print(f"  📋 策略版本: {agent_result['strategy_version']}")
            print(f"  🔄 策略变更: {agent_result['strategy_changes']} 项")
            print(f"  💡 学习洞察: {agent_result['learning_insights']} 个")

            return agent_result

        except subprocess.TimeoutExpired:
            return {"status": "timeout", "message": "Agent learning timed out after 120 seconds"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def run_all_agents(self) -> Dict:
        """运行所有Agent学习闭环"""
        print("\n" + "=" * 60)
        print("  跨Agent协同学习编排器 - 运行全部6大Agent")
        print("=" * 60)
        print(f"\n  运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Agent数量: {len(AGENT_LEARNING_CONFIG)}")

        results = {}
        for agent_key in AGENT_LEARNING_CONFIG.keys():
            results[agent_key] = self.run_agent_learning(agent_key)
            self.agent_results[agent_key] = results[agent_key]

        # 生成跨Agent洞察
        cross_agent_insights = self._generate_cross_agent_insights(results)
        self.global_memory["cross_agent_insights"] = cross_agent_insights

        # 生成全局建议
        global_recommendations = self._generate_global_recommendations(results, cross_agent_insights)
        self.global_memory["global_recommendations"] = global_recommendations

        # 识别协同机会
        synergy_opportunities = self._identify_synergy_opportunities(results)
        self.coordination_strategy["synergy_opportunities"] = synergy_opportunities

        # 保存
        self._save_global_memory()
        self._save_coordination_strategy()

        # 生成报告
        self._generate_cross_agent_report(results, cross_agent_insights, global_recommendations, synergy_opportunities)

        return {
            "total_agents": len(results),
            "successful": sum(1 for r in results.values() if r.get("status") == "success"),
            "failed": sum(1 for r in results.values() if r.get("status") != "success"),
            "cross_agent_insights": len(cross_agent_insights),
            "global_recommendations": len(global_recommendations),
            "synergy_opportunities": len(synergy_opportunities),
            "results": results
        }

    def _generate_cross_agent_insights(self, results: Dict) -> List[Dict]:
        """生成跨Agent洞察"""
        insights = []

        # 洞察1：Social + Content协同
        social_result = results.get("social", {})
        content_result = results.get("content", {})
        if social_result.get("status") == "success" and content_result.get("status") == "success":
            insights.append({
                "type": "synergy",
                "agents": ["social", "content"],
                "title": "社媒-内容协同效应",
                "description": "Social Learning识别的高表现Hook和内容类型，可以指导Content Agent生成更易传播的内容；Content Agent识别的高表现文章，可以优先用于社媒分发",
                "impact": "提升内容传播效率和社媒转化率",
                "action": "建立内容-社媒双向反馈机制，高表现文章优先社媒分发，高表现社媒Hook指导内容创作"
            })

        # 洞察2：Conversion + Revenue协同
        conversion_result = results.get("conversion", {})
        revenue_result = results.get("revenue", {})
        if conversion_result.get("status") == "success" and revenue_result.get("status") == "success":
            insights.append({
                "type": "synergy",
                "agents": ["conversion", "revenue"],
                "title": "转化-收入协同效应",
                "description": "Conversion Learning识别的最佳CTA类型和位置，可以直接提升Revenue Agent关注的高佣金产品转化；Revenue Agent识别的高收入产品，可以指导Conversion Agent优化CTA布局",
                "impact": "提升联盟收入和ROI",
                "action": "高佣金产品优先使用最佳CTA类型和位置，建立转化-收入双向优化闭环"
            })

        # 洞察3：SEO + Content协同
        seo_result = results.get("seo", {})
        if seo_result.get("status") == "success" and content_result.get("status") == "success":
            insights.append({
                "type": "synergy",
                "agents": ["seo", "content"],
                "title": "SEO-内容协同效应",
                "description": "SEO Learning识别的高潜力关键词，可以指导Content Agent生成针对性内容；Content Agent识别的高质量文章，可以优先进行SEO优化和GSC提交",
                "impact": "提升自然搜索流量和内容质量",
                "action": "建立关键词-内容匹配机制，高潜力关键词优先生成内容，高质量文章优先SEO优化"
            })

        # 洞察4：User + 全Agent协同
        user_result = results.get("user", {})
        if user_result.get("status") == "success":
            insights.append({
                "type": "synergy",
                "agents": ["user", "all"],
                "title": "用户分层驱动全Agent优化",
                "description": "User Learning识别的高价值用户分层和行为模式，可以指导所有Agent：Social针对高价值用户偏好发布内容，Content生成高价值用户感兴趣的主题，Conversion针对高转化用户优化CTA",
                "impact": "提升用户生命周期价值和整体运营效率",
                "action": "建立用户分层标签系统，所有Agent策略都参考用户分层数据"
            })

        return insights

    def _generate_global_recommendations(self, results: Dict, insights: List[Dict]) -> List[Dict]:
        """生成全局建议"""
        recommendations = []

        # 统计成功Agent
        successful_agents = [k for k, v in results.items() if v.get("status") == "success"]
        failed_agents = [k for k, v in results.items() if v.get("status") != "success"]

        if failed_agents:
            recommendations.append({
                "priority": "high",
                "type": "stability",
                "title": f"修复 {len(failed_agents)} 个Agent学习闭环",
                "description": f"以下Agent学习闭环运行失败: {', '.join(failed_agents)}",
                "action": "检查失败原因，修复脚本和数据接入"
            })

        if len(successful_agents) >= 4:
            recommendations.append({
                "priority": "high",
                "type": "integration",
                "title": "深化跨Agent数据共享",
                "description": "大部分Agent学习闭环已成功运行，需要建立更深度的数据共享和协同决策机制",
                "action": "建立统一Growth Memory API，所有Agent实时共享学习数据"
            })

        recommendations.append({
            "priority": "medium",
            "type": "automation",
            "title": "建立周度跨Agent学习例会",
            "description": "每周自动运行所有Agent学习闭环，生成跨Agent协同报告",
            "action": "配置GitHub Actions每周一自动运行cross_agent_learning_orchestrator.py"
        })

        recommendations.append({
            "priority": "medium",
            "type": "measurement",
            "title": "建立跨Agent效果测量体系",
            "description": "测量跨Agent协同优化的整体效果，而不是单个Agent的孤立指标",
            "action": "建立全局KPI仪表盘，跟踪跨Agent协同优化的整体ROI"
        })

        return recommendations

    def _identify_synergy_opportunities(self, results: Dict) -> List[Dict]:
        """识别协同机会"""
        opportunities = []

        # 机会1：高表现内容 + 社媒分发
        opportunities.append({
            "id": "SYN-001",
            "name": "高表现内容社媒分发",
            "agents": ["content", "social"],
            "description": "Content Agent识别的高表现文章，自动进入Social Agent的优先分发队列",
            "expected_impact": "提升社媒内容质量和点击率",
            "implementation_complexity": "medium",
            "status": "identified"
        })

        # 机会2：高潜力关键词 + 内容生成
        opportunities.append({
            "id": "SYN-002",
            "name": "高潜力关键词内容生成",
            "agents": ["seo", "content"],
            "description": "SEO Agent识别的高潜力低难度关键词，自动触发Content Agent生成针对性内容",
            "expected_impact": "提升自然搜索流量和关键词覆盖",
            "implementation_complexity": "high",
            "status": "identified"
        })

        # 机会3：高佣金产品 + CTA优化
        opportunities.append({
            "id": "SYN-003",
            "name": "高佣金产品CTA优化",
            "agents": ["revenue", "conversion"],
            "description": "Revenue Agent识别的高佣金产品，自动使用Conversion Agent识别的最佳CTA类型和位置",
            "expected_impact": "提升联盟收入和ROI",
            "implementation_complexity": "medium",
            "status": "identified"
        })

        # 机会4：高价值用户 + 个性化推荐
        opportunities.append({
            "id": "SYN-004",
            "name": "高价值用户个性化推荐",
            "agents": ["user", "content", "conversion"],
            "description": "User Agent识别的高价值用户分层，自动触发Content和Conversion Agent的个性化内容和CTA推荐",
            "expected_impact": "提升用户生命周期价值和转化率",
            "implementation_complexity": "high",
            "status": "identified"
        })

        return opportunities

    def _generate_cross_agent_report(self, results: Dict, insights: List[Dict],
                                       recommendations: List[Dict], opportunities: List[Dict]):
        """生成跨Agent学习报告"""
        report = f"""# ChinaBound Travel 跨Agent协同学习报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**编排器版本**: 1.0
**运行Agent数**: {len(results)}

---

## 📊 Agent运行状态

| Agent | 状态 | 策略版本 | 策略变更 | 学习洞察 |
|-------|------|----------|----------|----------|
"""

        for agent_key, result in results.items():
            config = AGENT_LEARNING_CONFIG.get(agent_key, {})
            status_icon = "✅" if result.get("status") == "success" else "❌"
            report += f"| {config.get('name', agent_key)} | {status_icon} {result.get('status', 'unknown')} | {result.get('strategy_version', 'N/A')} | {result.get('strategy_changes', 0)} | {result.get('learning_insights', 0)} |\n"

        report += f"""
---

## 🔗 跨Agent协同洞察

"""

        for i, insight in enumerate(insights, 1):
            agents_str = ", ".join(insight.get("agents", []))
            report += f"### {i}. {insight['title']}\n"
            report += f"**涉及Agent**: {agents_str}\n\n"
            report += f"{insight['description']}\n\n"
            report += f"**预期影响**: {insight['impact']}\n\n"
            report += f"**行动建议**: {insight['action']}\n\n"

        report += """---

## 🚀 全局优化建议

"""

        for i, rec in enumerate(recommendations, 1):
            icon = "🔴" if rec["priority"] == "high" else "🟡" if rec["priority"] == "medium" else "🟢"
            report += f"{icon} **{rec['title']}**\n"
            report += f"- {rec['description']}\n"
            report += f"- 行动: {rec['action']}\n\n"

        report += """---

## 🤝 协同机会识别

| ID | 名称 | 涉及Agent | 预期影响 | 复杂度 | 状态 |
|----|------|-----------|----------|--------|------|
"""

        for opp in opportunities:
            agents_str = ", ".join(opp.get("agents", []))
            report += f"| {opp['id']} | {opp['name']} | {agents_str} | {opp['expected_impact']} | {opp['implementation_complexity']} | {opp['status']} |\n"

        report += f"""
---

## 🎯 总结

**运行统计**:
- 总Agent数: {len(results)}
- 成功: {sum(1 for r in results.values() if r.get('status') == 'success')}
- 失败: {sum(1 for r in results.values() if r.get('status') != 'success')}
- 跨Agent洞察: {len(insights)}
- 全局建议: {len(recommendations)}
- 协同机会: {len(opportunities)}

**核心价值**:
- 6大Agent学习闭环统一编排
- 跨Agent数据共享和协同决策
- 全局Growth Memory统一管理
- 协同机会自动识别和优先级排序

**下一步**:
1. 修复失败的Agent学习闭环
2. 实施高优先级协同机会（SYN-001, SYN-003）
3. 建立周度跨Agent学习例会
4. 深化跨Agent数据共享机制

---

*报告由跨Agent协同学习编排器自动生成*
*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

        with open(CROSS_AGENT_REPORT, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"\n  ✅ 跨Agent学习报告已生成: {CROSS_AGENT_REPORT}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="跨Agent协同学习编排器")
    parser.add_argument("--run-all", action="store_true", help="运行所有Agent学习闭环")
    parser.add_argument("--social", action="store_true", help="仅运行Social Learning")
    parser.add_argument("--content", action="store_true", help="仅运行Content Learning")
    parser.add_argument("--conversion", action="store_true", help="仅运行Conversion Learning")
    parser.add_argument("--seo", action="store_true", help="仅运行SEO Learning")
    parser.add_argument("--user", action="store_true", help="仅运行User Learning")
    parser.add_argument("--revenue", action="store_true", help="仅运行Revenue Learning")
    parser.add_argument("--generate-report", action="store_true", help="仅生成跨Agent报告")

    args = parser.parse_args()

    orchestrator = CrossAgentLearningOrchestrator()

    if args.run_all:
        result = orchestrator.run_all_agents()
        print(f"\n{'='*60}")
        print(f"  跨Agent协同学习完成")
        print(f"{'='*60}")
        print(f"\n  总Agent数: {result['total_agents']}")
        print(f"  成功: {result['successful']}")
        print(f"  失败: {result['failed']}")
        print(f"  跨Agent洞察: {result['cross_agent_insights']}")
        print(f"  全局建议: {result['global_recommendations']}")
        print(f"  协同机会: {result['synergy_opportunities']}")
    elif any([args.social, args.content, args.conversion, args.seo, args.user, args.revenue]):
        agent_map = {
            "social": args.social,
            "content": args.content,
            "conversion": args.conversion,
            "seo": args.seo,
            "user": args.user,
            "revenue": args.revenue
        }
        for agent_key, should_run in agent_map.items():
            if should_run:
                orchestrator.run_agent_learning(agent_key)
    else:
        # 默认运行全部
        result = orchestrator.run_all_agents()
        print(f"\n完成: {result['successful']}/{result['total_agents']} Agent成功")


if __name__ == "__main__":
    main()
