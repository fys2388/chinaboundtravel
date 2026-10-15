#!/usr/bin/env python3
"""
ChinaBound Travel - Autonomous Agent Runner
CLI 入口：启动自主 Agent 执行指定目标。

用法:
    # 运行社媒智能优化 Agent
    python scripts/agent_runner.py --agent social --goal "分析最近7天社媒数据，优化发布时间"

    # 运行 SEO Agent
    python scripts/agent_runner.py --agent seo --goal "找出排名5-15位的关键词，优化标题"

    # 运行内容优化 Agent
    python scripts/agent_runner.py --agent content --goal "检查内容重复和元数据缺失"

    # 指定最大步数
    python scripts/agent_runner.py --agent social --goal "优化发布时间" --max-steps 15

    # 列出所有可用 Agent
    python scripts/agent_runner.py --list-agents

    # 查看 Agent 记忆
    python scripts/agent_runner.py --agent social --show-memory

    # 查看 Agent 学到的经验
    python scripts/agent_runner.py --agent social --show-insights

环境变量:
    SENSENOVA_API_KEY  - LLM API Key (必需)
    SENSENOVA_MODEL    - 覆盖默认模型 (可选)
"""

from __future__ import annotations

import argparse
import json
import sys
import os
from pathlib import Path
from typing import Optional

# 项目路径
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from agent_core import AutonomousAgent, LLMClient, AgentMemory  # noqa: E402
from agent_tools import (  # noqa: E402
    create_default_tools,
    create_social_tools,
    create_seo_tools,
    create_content_tools,
)


# ══════════════════════════════════════════════════════════════════════
# Agent 配置（延迟解析，避免前向引用问题）
# ══════════════════════════════════════════════════════════════════════

def _get_agent_configs() -> dict:
    """返回 Agent 配置字典。"""
    return {
        "social": {
            "name": "social",
            "label": "社媒智能优化Agent",
            "default_goal": "分析社媒数据，优化发布时间和内容策略",
            "tools_factory": create_social_tools,
            "context_provider": get_social_context,
        },
        "seo": {
            "name": "seo",
            "label": "SEO智能优化Agent",
            "default_goal": "分析GSC数据，找出SEO优化机会",
            "tools_factory": create_seo_tools,
            "context_provider": get_seo_context,
        },
        "content": {
            "name": "content",
            "label": "内容智能优化Agent",
            "default_goal": "检查内容质量，发现优化机会",
            "tools_factory": create_content_tools,
            "context_provider": get_content_context,
        },
        "general": {
            "name": "general",
            "label": "通用智能Agent",
            "default_goal": "分析项目状态，发现优化机会",
            "tools_factory": create_default_tools,
            "context_provider": get_general_context,
        },
    }


# ══════════════════════════════════════════════════════════════════════
# 上下文提供者
# ══════════════════════════════════════════════════════════════════════

def get_social_context() -> dict:
    """提供社媒相关上下文。"""
    context = {}

    # 检查社媒报告
    social_reports = Path(__file__).resolve().parent.parent / "reports" / "social"
    if social_reports.exists():
        reports = []
        for f in sorted(social_reports.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
            if f.is_file():
                reports.append(f.name)
        context["recent_reports"] = reports

    # 读取社媒策略配置
    strategy_path = Path(__file__).resolve().parent.parent / "config" / "social_strategy.json"
    if strategy_path.exists():
        try:
            with open(strategy_path, encoding="utf-8") as f:
                context["strategy"] = json.load(f)
        except Exception:
            pass

    return context


def get_seo_context() -> dict:
    """提供 SEO 相关上下文。"""
    context = {}

    # 检查 GSC 关键词数据
    gsc_path = Path(__file__).resolve().parent.parent / "config" / "gsc_hot_keyword.json"
    if gsc_path.exists():
        try:
            with open(gsc_path, encoding="utf-8") as f:
                context["hot_keywords"] = json.load(f)
        except Exception:
            pass

    # 检查 SEO 报告
    seo_reports = Path(__file__).resolve().parent.parent / "reports" / "seo"
    if seo_reports.exists():
        reports = []
        for f in sorted(seo_reports.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
            if f.is_file():
                reports.append(f.name)
        context["recent_reports"] = reports

    return context


def get_content_context() -> dict:
    """提供内容相关上下文。"""
    context = {}

    # 读取内容知识库
    kb_path = Path(__file__).resolve().parent.parent / "config" / "content_knowledge_base.json"
    if kb_path.exists():
        try:
            with open(kb_path, encoding="utf-8") as f:
                data = json.load(f)
                # 只返回摘要
                if isinstance(data, list):
                    context["knowledge_base_count"] = len(data)
                    context["sample_entries"] = data[:3]
                else:
                    context["knowledge_base"] = data
        except Exception:
            pass

    return context


def get_general_context() -> dict:
    """提供通用上下文。"""
    context = {}

    # 项目基本信息
    root = Path(__file__).resolve().parent.parent

    # 内容统计
    posts_dir = root / "content" / "posts"
    if posts_dir.exists():
        posts = [f for f in posts_dir.rglob("*.md") if f.is_file()]
        context["total_posts"] = len(posts)

    # 报告统计
    reports_dir = root / "reports"
    if reports_dir.exists():
        report_dirs = [d.name for d in reports_dir.iterdir() if d.is_dir()]
        context["report_categories"] = report_dirs

    # Agent 状态
    agent_dir = reports_dir / "agent" if reports_dir.exists() else None
    if agent_dir and agent_dir.exists():
        agents = [f.stem for f in agent_dir.glob("memory_*.json")]
        context["active_agents"] = agents

    return context


# ══════════════════════════════════════════════════════════════════════
# CLI 入口
# ══════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="ChinaBound Travel - Autonomous Agent Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument("--agent", "-a", type=str, help="Agent name (social, seo, content, general)")
    parser.add_argument("--goal", "-g", type=str, help="Goal for the agent to achieve")
    parser.add_argument("--max-steps", "-m", type=int, default=10, help="Maximum steps (default: 10)")
    parser.add_argument("--list-agents", action="store_true", help="List all available agents")
    parser.add_argument("--show-memory", action="store_true", help="Show agent's memory")
    parser.add_argument("--show-insights", action="store_true", help="Show agent's learned insights")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without executing")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # 列出所有 Agent
    if args.list_agents:
        print("Available Agents:")
        print("=" * 60)
        configs = _get_agent_configs()
        for key, cfg in configs.items():
            print(f"\n  {key} ({cfg['label']})")
            print(f"    Default goal: {cfg['default_goal']}")
        return

    # 需要指定 agent
    if not args.agent:
        parser.print_help()
        sys.exit(1)

    # 检查 agent 是否存在
    configs = _get_agent_configs()
    if args.agent not in configs:
        print(f"Error: Unknown agent '{args.agent}'. Available: {', '.join(configs.keys())}")
        sys.exit(1)

    cfg = configs[args.agent]

    # 查看记忆
    if args.show_memory:
        memory = AgentMemory(args.agent)
        print(f"Agent: {args.agent}")
        print(f"Total experiences: {len(memory._long_term)}")
        if memory._long_term:
            print("\nRecent experiences:")
            for exp in memory._long_term[-5:]:
                print(f"  [{exp['timestamp']}] Success: {exp['success']}")
                print(f"    Goal: {exp['goal'][:100]}")
                if exp.get("insight"):
                    print(f"    Insight: {exp['insight'][:100]}")
        return

    # 查看经验
    if args.show_insights:
        insights_path = Path(__file__).resolve().parent.parent / "reports" / "agent" / f"insights_{args.agent}.json"
        if insights_path.exists():
            with open(insights_path, encoding="utf-8") as f:
                insights = json.load(f)
            print(f"Agent: {args.agent}")
            print(f"Insights: {len(insights)}")
            for k, v in insights.items():
                print(f"  {k}: {v}")
        else:
            print(f"No insights found for agent '{args.agent}'")
        return

    # 确定目标
    goal = args.goal or cfg["default_goal"]

    # 检查 API Key
    api_key = os.getenv("SENSENOVA_API_KEY", "")
    if not api_key and not args.dry_run:
        print("Error: SENSENOVA_API_KEY environment variable not set")
        print("Please set it before running the agent.")
        sys.exit(1)

    print(f"Agent: {cfg['label']} ({args.agent})")
    print(f"Goal: {goal}")
    print(f"Max steps: {args.max_steps}")
    if args.dry_run:
        print("Mode: DRY RUN (no LLM calls)")

    # Dry run 模式
    if args.dry_run:
        print("\n--- DRY RUN OUTPUT ---")
        print(f"Would create agent: {args.agent}")
        print(f"Would register tools: {len(cfg['tools_factory']()._tools)}")
        print(f"Would execute goal: {goal}")
        print(f"Max steps: {args.max_steps}")
        print("--- END DRY RUN ---")
        return

    # 创建 Agent
    try:
        tools = cfg["tools_factory"]()
        agent = AutonomousAgent(args.agent, tools)
    except Exception as e:
        print(f"Error creating agent: {e}")
        sys.exit(1)

    # 获取上下文
    context = {}
    if cfg.get("context_provider"):
        try:
            context = cfg["context_provider"]()
        except Exception as e:
            print(f"Warning: Failed to get context: {e}")

    # 运行 Agent
    try:
        result = agent.run(goal, context, max_steps=args.max_steps)

        # 输出结果
        print("\n" + "=" * 60)
        print("AGENT EXECUTION RESULT")
        print("=" * 60)
        print(json.dumps(result, ensure_ascii=False, indent=2))

        # 输出记忆摘要
        memory_summary = agent.get_memory_summary()
        print("\n" + "-" * 40)
        print("Memory Summary:")
        print(f"  Experiences: {memory_summary['long_term_count']}")
        print(f"  Insights: {memory_summary['insights_count']}")

        if not result.get("success", False):
            sys.exit(1)

    except Exception as e:
        print(f"\nError during agent execution: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
