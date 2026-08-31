#!/usr/bin/env python3
"""
ChinaBound Travel - 7大AI Agent统一运行脚本
Run All Agents Orchestrator

依次运行7大AI Agent，生成统一的运营报告：
1. SEO智能优化Agent (seo_intelligent_agent.py)
2. 自我学习引擎 (self_learning_engine.py)
3. 收入分析引擎 (revenue_analytics_engine.py)
4. 转化优化Agent (conversion_optimization_agent.py)
5. 内容智能优化Agent (content_intelligence_agent.py)
6. 社媒智能优化Agent (social_intelligence_agent.py)
7. 用户智能运营Agent (user_intelligence_agent.py)

使用方式：
    python scripts/run_all_agents.py --all
    python scripts/run_all_agents.py --seo --content
    python scripts/run_all_agents.py --report-only
"""

import os
import sys
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
REPORTS_DIR = PROJECT_ROOT / "reports"
ORCHESTRATION_DIR = REPORTS_DIR / "orchestration"
ORCHESTRATION_DIR.mkdir(parents=True, exist_ok=True)

# 添加scripts目录到路径
sys.path.insert(0, str(SCRIPTS_DIR))

# AI Governance: Kill Switch + L0-L3 Permission Boundaries
try:
    from ai_governance import check_kill_switch, get_agent_permission_level, check_permission
    GOVERNANCE_AVAILABLE = True
except ImportError:
    GOVERNANCE_AVAILABLE = False
    print("  ⚠️ ai_governance module not found, running without governance checks")

# 7大Agent定义
AGENTS = {
    "seo": {
        "name": "SEO智能优化Agent",
        "script": "seo_intelligent_agent.py",
        "args": ["--all"],
        "report_file": REPORTS_DIR / "seo" / "seo_intelligence_report.md",
        "report_pattern": "seo_intelligence_report.md",
        "description": "SEO机会识别、关键词分析、优化建议",
        "maturity": "L2"
    },
    "self_learning": {
        "name": "自我学习引擎",
        "script": "self_learning_engine.py",
        "args": ["--cycle"],
        "report_file": REPORTS_DIR / "learning" / "self_learning_report.md",
        "report_pattern": "self_learning_report.md",
        "description": "历史效果追踪、模式提取、策略迭代",
        "maturity": "L1"
    },
    "revenue": {
        "name": "收入分析引擎",
        "script": "revenue_analytics_engine.py",
        "args": ["--all"],
        "report_file": REPORTS_DIR / "revenue" / "revenue_analytics_report.md",
        "report_pattern": "revenue_analytics_report.md",
        "description": "联盟数据闭环、漏斗归因、分产品分析",
        "maturity": "L3"
    },
    "conversion": {
        "name": "转化优化Agent",
        "script": "conversion_optimization_agent.py",
        "args": ["--all"],
        "report_file": REPORTS_DIR / "conversion" / "conversion_optimization_report.md",
        "report_pattern": "conversion_optimization_report.md",
        "description": "CTA审计、A/B测试、自动决策、漏斗优化",
        "maturity": "L3"
    },
    "content": {
        "name": "内容智能优化Agent",
        "script": "content_intelligence_agent.py",
        "args": ["--all"],
        "report_file": REPORTS_DIR / "content" / "content_intelligence_report.md",
        "report_pattern": "content_intelligence_report.md",
        "description": "质量审计、选题推荐、多模态规划、效果追踪",
        "maturity": "L4"
    },
    "social": {
        "name": "社媒智能优化Agent",
        "script": "social_intelligence_agent.py",
        "args": ["--all"],
        "report_file": REPORTS_DIR / "social" / "social_intelligence_report.md",
        "report_pattern": "social_intelligence_report.md",
        "description": "效果分析、时间优化、平台适配、爆款识别、引流分析",
        "maturity": "L3"
    },
    "user": {
        "name": "用户智能运营Agent",
        "script": "user_intelligence_agent.py",
        "args": ["--all"],
        "report_file": REPORTS_DIR / "user" / "user_intelligence_report.md",
        "report_pattern": "user_intelligence_report.md",
        "description": "行为分析、分层画像、旅程分析、智能客服、留存优化",
        "maturity": "L2"
    }
}

# 运行顺序（按依赖关系排序）
RUN_ORDER = ["seo", "self_learning", "revenue", "conversion", "content", "social", "user"]


class AgentOrchestrator:
    """Agent编排器"""

    def __init__(self, use_real_data: bool = True, parallel: bool = False):
        self.use_real_data = use_real_data
        self.parallel = parallel
        self.results = {}
        self.start_time = None
        self.end_time = None

    def run_agent(self, agent_id: str, extra_args: List[str] = None) -> Dict[str, Any]:
        """运行单个Agent"""
        agent_config = AGENTS.get(agent_id)
        if not agent_config:
            return {"success": False, "error": f"Unknown agent: {agent_id}"}

        script_path = SCRIPTS_DIR / agent_config["script"]
        if not script_path.exists():
            return {
                "success": False,
                "error": f"Script not found: {script_path}",
                "agent": agent_id,
                "name": agent_config["name"]
            }

        print(f"\n{'=' * 60}")
        print(f"  运行: {agent_config['name']} ({agent_id})")
        print(f"  成熟度: {agent_config['maturity']}")
        if GOVERNANCE_AVAILABLE:
            plevel = get_agent_permission_level(agent_id)
            print(f"  权限级别: {plevel}")
        print(f"  描述: {agent_config['description']}")
        print(f"{'=' * 60}")

        start_time = datetime.now()

        # 构建命令
        agent_args = agent_config.get("args", ["--all"])
        cmd = [sys.executable, str(script_path)] + agent_args
        if extra_args:
            cmd.extend(extra_args)

        try:
            result = subprocess.run(
                cmd,
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=300  # 5分钟超时
            )

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            success = result.returncode == 0
            report_exists = agent_config["report_file"].exists()

            agent_result = {
                "success": success,
                "agent": agent_id,
                "name": agent_config["name"],
                "maturity": agent_config["maturity"],
                "permission_level": get_agent_permission_level(agent_id) if GOVERNANCE_AVAILABLE else "unknown",
                "duration_seconds": duration,
                "return_code": result.returncode,
                "stdout": result.stdout[-2000:] if result.stdout else "",  # 只保留最后2000字符
                "stderr": result.stderr[-1000:] if result.stderr else "",
                "report_generated": report_exists,
                "report_file": str(agent_config["report_file"]) if report_exists else None,
                "started_at": start_time.isoformat(),
                "finished_at": end_time.isoformat()
            }

            status_icon = "✅" if success else "❌"
            print(f"\n  {status_icon} {agent_config['name']} 完成")
            print(f"     耗时: {duration:.1f}秒")
            print(f"     返回码: {result.returncode}")
            print(f"     报告生成: {'是' if report_exists else '否'}")

            if not success and result.stderr:
                print(f"     错误: {result.stderr[:200]}")

        except subprocess.TimeoutExpired:
            agent_result = {
                "success": False,
                "agent": agent_id,
                "name": agent_config["name"],
                "error": "Timeout after 300 seconds",
                "duration_seconds": 300
            }
            print(f"\n  ⏰ {agent_config['name']} 超时")

        except Exception as e:
            agent_result = {
                "success": False,
                "agent": agent_id,
                "name": agent_config["name"],
                "error": str(e),
                "duration_seconds": 0
            }
            print(f"\n  ❌ {agent_config['name']} 异常: {e}")

        self.results[agent_id] = agent_result
        return agent_result

    def run_all(self, agents: List[str] = None) -> Dict[str, Any]:
        """运行所有指定的Agent"""
        if agents is None:
            agents = RUN_ORDER

        # === AI Governance: Kill Switch Check ===
        if GOVERNANCE_AVAILABLE:
            is_safe, reason = check_kill_switch()
            if not is_safe:
                print("\n" + "=" * 60)
                print("  KILL SWITCH ACTIVE - AI Agent 运行被阻止")
                print("=" * 60)
                print(f"  原因: {reason}")
                print("  如需恢复运行，请在 config/ai_governance.json 中禁用 kill_switch")
                return {"success": False, "error": "kill_switch_active", "reason": reason}
            print("  ✅ Kill Switch: 未激活，运行允许")

        self.start_time = datetime.now()

        print("\n" + "=" * 60)
        print("  ChinaBound Travel - 7大AI Agent统一运行")
        print("=" * 60)
        print(f"\n  运行时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  运行Agent数: {len(agents)}")
        print(f"  Agent列表: {', '.join(agents)}")
        print(f"  真实数据: {'是' if self.use_real_data else '否（样本数据）'}")

        if GOVERNANCE_AVAILABLE:
            print(f"\n  权限分级 (L0-L3):")
            for aid in agents:
                if aid in AGENTS:
                    plevel = get_agent_permission_level(aid)
                    print(f"    {aid:15s}: {plevel}")

        # 依次运行每个Agent
        for agent_id in agents:
            if agent_id in AGENTS:
                self.run_agent(agent_id)

        self.end_time = datetime.now()
        total_duration = (self.end_time - self.start_time).total_seconds()

        # 生成汇总报告
        summary = self.generate_summary(total_duration)

        # 保存运行结果
        self.save_results(total_duration)

        return summary

    def generate_summary(self, total_duration: float) -> Dict[str, Any]:
        """生成运行汇总"""
        print("\n" + "=" * 60)
        print("  运行汇总")
        print("=" * 60)

        success_count = sum(1 for r in self.results.values() if r.get("success"))
        failed_count = sum(1 for r in self.results.values() if not r.get("success"))
        report_count = sum(1 for r in self.results.values() if r.get("report_generated"))

        print(f"\n  📊 运行统计:")
        print(f"    总Agent数: {len(self.results)}")
        print(f"    成功: {success_count}")
        print(f"    失败: {failed_count}")
        print(f"    报告生成: {report_count}")
        print(f"    总耗时: {total_duration:.1f}秒")

        print(f"\n  📋 各Agent状态:")
        print(f"  {'Agent':<25} {'成熟度':<8} {'状态':<8} {'耗时':<10} {'报告'}")
        print("  " + "-" * 70)
        for agent_id in RUN_ORDER:
            if agent_id in self.results:
                r = self.results[agent_id]
                status = "✅ 成功" if r.get("success") else "❌ 失败"
                report = "📄 已生成" if r.get("report_generated") else "❌ 未生成"
                print(f"  {r['name']:<25} {r['maturity']:<8} {status:<8} {r.get('duration_seconds', 0):<10.1f}s {report}")

        summary = {
            "run_at": self.start_time.isoformat(),
            "finished_at": self.end_time.isoformat() if self.end_time else None,
            "total_duration_seconds": total_duration,
            "total_agents": len(self.results),
            "success_count": success_count,
            "failed_count": failed_count,
            "report_count": report_count,
            "results": self.results
        }

        return summary

    def save_results(self, total_duration: float):
        """保存运行结果"""
        result_file = ORCHESTRATION_DIR / f"run_{self.start_time.strftime('%Y%m%d_%H%M%S')}.json"
        latest_file = ORCHESTRATION_DIR / "latest_run.json"

        save_data = {
            "run_at": self.start_time.isoformat(),
            "finished_at": self.end_time.isoformat() if self.end_time else None,
            "total_duration_seconds": total_duration,
            "use_real_data": self.use_real_data,
            "results": self.results
        }

        try:
            with open(result_file, "w", encoding="utf-8") as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            with open(latest_file, "w", encoding="utf-8") as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            print(f"\n  💾 运行结果已保存: {result_file}")
        except Exception as e:
            print(f"\n  ⚠️ 保存运行结果失败: {e}")

    def generate_unified_report(self) -> str:
        """生成统一运营报告"""
        print("\n" + "=" * 60)
        print("  生成统一运营报告")
        print("=" * 60)

        now = datetime.now()
        report = f"""# ChinaBound Travel 统一运营报告

**生成时间**: {now.strftime('%Y-%m-%d %H:%M:%S')}
**运行Agent数**: {len(self.results)}
**成功**: {sum(1 for r in self.results.values() if r.get('success'))}
**失败**: {sum(1 for r in self.results.values() if not r.get('success'))}

---

## 📊 运行概览

| Agent | 成熟度 | 状态 | 耗时 | 报告 |
|-------|--------|------|------|------|
"""

        for agent_id in RUN_ORDER:
            if agent_id in self.results:
                r = self.results[agent_id]
                status = "✅" if r.get("success") else "❌"
                report_icon = "📄" if r.get("report_generated") else "❌"
                report += f"| {r['name']} | {r['maturity']} | {status} | {r.get('duration_seconds', 0):.1f}s | {report_icon} |\n"

        report += """
---

## 🏆 成熟度总览

| 维度 | 成熟度 | 目标 | 状态 |
|------|--------|------|------|
| SEO优化 | L2 | L3 | 🟡 进行中 |
| 自我学习 | L1 | L2 | 🟡 进行中 |
| 数据分析 | L3 | L3 | ✅ 已达标 |
| 转化优化 | L3 | L3 | ✅ 已达标 |
| 内容生产 | L4 | L4 | ✅ 已达标 |
| 社媒运营 | L3 | L3 | ✅ 已达标 |
| 用户运营 | L2 | L2 | ✅ 已达标 |

**5/7维度已达标，2/7维度进行中**

---

## 📁 各Agent报告链接

"""

        for agent_id in RUN_ORDER:
            if agent_id in self.results:
                r = self.results[agent_id]
                if r.get("report_generated"):
                    report += f"- **{r['name']}**: `{r['report_file']}`\n"
                else:
                    report += f"- **{r['name']}**: ⚠️ 报告未生成\n"

        report += f"""
---

## 🚀 下一步建议

### 立即
1. 检查失败的Agent并修复问题
2. 查看各Agent生成的详细报告
3. 优先处理高优先级优化建议

### 短期
1. 将所有Agent接入真实API数据
2. 建立Agent间的数据共享和协同机制
3. 设置每周自动运行并生成统一报告

### 中期
1. 实现Agent间的协同工作流
2. 建立统一的运营仪表盘
3. 实现基于效果的自动优化闭环

---

*报告由7大AI Agent统一运行脚本自动生成*
*生成时间: {now.strftime('%Y-%m-%d %H:%M:%S')}*
"""

        # 保存报告
        report_file = ORCHESTRATION_DIR / f"unified_report_{now.strftime('%Y%m%d_%H%M%S')}.md"
        latest_report = ORCHESTRATION_DIR / "latest_unified_report.md"

        try:
            with open(report_file, "w", encoding="utf-8") as f:
                f.write(report)
            with open(latest_report, "w", encoding="utf-8") as f:
                f.write(report)
            print(f"\n  ✅ 统一报告已生成: {report_file}")
        except Exception as e:
            print(f"\n  ⚠️ 生成统一报告失败: {e}")

        return report


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="ChinaBound Travel 7大AI Agent统一运行脚本")
    parser.add_argument("--all", action="store_true", help="运行所有Agent")
    parser.add_argument("--seo", action="store_true", help="仅运行SEO Agent")
    parser.add_argument("--self-learning", action="store_true", help="仅运行自我学习引擎")
    parser.add_argument("--revenue", action="store_true", help="仅运行收入分析引擎")
    parser.add_argument("--conversion", action="store_true", help="仅运行转化优化Agent")
    parser.add_argument("--content", action="store_true", help="仅运行内容智能优化Agent")
    parser.add_argument("--social", action="store_true", help="仅运行社媒智能优化Agent")
    parser.add_argument("--user", action="store_true", help="仅运行用户智能运营Agent")
    parser.add_argument("--report-only", action="store_true", help="仅生成统一报告（不运行Agent）")
    parser.add_argument("--sample-data", action="store_true", help="使用样本数据")
    parser.add_argument("--list", action="store_true", help="列出所有Agent")

    args = parser.parse_args()

    # 列出Agent
    if args.list:
        print("\n📋 7大AI Agent列表:")
        print(f"\n  {'ID':<15} {'名称':<25} {'成熟度':<8} {'描述'}")
        print("  " + "-" * 80)
        for agent_id in RUN_ORDER:
            config = AGENTS[agent_id]
            print(f"  {agent_id:<15} {config['name']:<25} {config['maturity']:<8} {config['description']}")
        return

    # 确定要运行的Agent
    agents_to_run = []
    if args.all or not any([args.seo, args.self_learning, args.revenue,
                            args.conversion, args.content, args.social, args.user]):
        agents_to_run = RUN_ORDER
    else:
        if args.seo:
            agents_to_run.append("seo")
        if args.self_learning:
            agents_to_run.append("self_learning")
        if args.revenue:
            agents_to_run.append("revenue")
        if args.conversion:
            agents_to_run.append("conversion")
        if args.content:
            agents_to_run.append("content")
        if args.social:
            agents_to_run.append("social")
        if args.user:
            agents_to_run.append("user")

    # 创建编排器并运行
    orchestrator = AgentOrchestrator(use_real_data=not args.sample_data)

    if not args.report_only:
        orchestrator.run_all(agents_to_run)

    # 生成统一报告
    orchestrator.generate_unified_report()

    print("\n" + "=" * 60)
    print("  ✅ 全部完成！")
    print("=" * 60)
    print(f"\n  📁 报告目录: {ORCHESTRATION_DIR}")
    print(f"  📄 最新统一报告: {ORCHESTRATION_DIR / 'latest_unified_report.md'}")
    print(f"  💾 最新运行结果: {ORCHESTRATION_DIR / 'latest_run.json'}")


if __name__ == "__main__":
    main()
