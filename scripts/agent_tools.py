#!/usr/bin/env python3
"""
ChinaBound Travel - Agent Tools Registry
为 AutonomousAgent 注册实际可用的工具函数。

每个工具 = 一个可被 LLM 通过 STEP: tool_name(args) 调用的函数。
工具执行结果以 JSON 返回给 LLM，LLM 根据结果决定下一步。
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# 项目路径
BLOG_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = BLOG_ROOT / "config"
REPORTS_DIR = BLOG_ROOT / "reports"
SCRIPTS_DIR = BLOG_ROOT / "scripts"

from agent_core import ToolRegistry, log  # noqa: E402


# ══════════════════════════════════════════════════════════════════════
# 工具实现
# ══════════════════════════════════════════════════════════════════════

def tool_read_file(file_path: str) -> Dict[str, Any]:
    """读取项目文件内容。file_path 为相对于项目根目录的路径。"""
    path = BLOG_ROOT / file_path
    if not path.exists():
        return {"error": f"File not found: {file_path}", "exists": False}
    if path.stat().st_size > 1024 * 1024:
        return {"error": "File too large (>1MB)", "size": path.stat().st_size}
    content = path.read_text(encoding="utf-8", errors="replace")
    return {
        "path": file_path,
        "size": len(content),
        "lines": content.count("\n"),
        "content": content[:8000],  # 限制返回大小
        "truncated": len(content) > 8000,
    }


def tool_read_config(config_name: str) -> Dict[str, Any]:
    """读取 config/ 目录下的配置文件。"""
    path = CONFIG_DIR / f"{config_name}.json"
    if not path.exists():
        return {"error": f"Config not found: {config_name}.json"}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return {"config": config_name, "data": data}
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON in {config_name}.json: {e}"}


def tool_list_files(directory: str, pattern: str = "*.json") -> Dict[str, Any]:
    """列出指定目录下的文件。"""
    path = BLOG_ROOT / directory
    if not path.exists():
        return {"error": f"Directory not found: {directory}"}
    files = []
    for f in path.iterdir():
        if f.is_file():
            if pattern == "*" or f.name.endswith(pattern.replace("*", "")):
                files.append({
                    "name": f.name,
                    "size": f.stat().st_size,
                    "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                })
    return {"directory": directory, "count": len(files), "files": files[:50]}


def tool_read_report(report_path: str) -> Dict[str, Any]:
    """读取 reports/ 目录下的报告文件。"""
    full_path = REPORTS_DIR / report_path
    if not full_path.exists():
        return {"error": f"Report not found: {report_path}"}
    content = full_path.read_text(encoding="utf-8", errors="replace")
    return {
        "path": report_path,
        "size": len(content),
        "content": content[:8000],
        "truncated": len(content) > 8000,
    }


def tool_list_reports(category: str = "") -> Dict[str, Any]:
    """列出 reports/ 目录下的报告。"""
    path = REPORTS_DIR / category if category else REPORTS_DIR
    if not path.exists():
        return {"error": f"Directory not found: {path}"}
    reports = []
    for f in sorted(path.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if f.is_file():
            reports.append({
                "name": f.name,
                "size": f.stat().st_size,
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            })
    return {"category": category, "count": len(reports), "reports": reports[:30]}


def tool_list_agents() -> Dict[str, Any]:
    """列出所有已知的 Agent 及其权限。"""
    gov_path = CONFIG_DIR / "ai_governance.json"
    if not gov_path.exists():
        return {"error": "ai_governance.json not found"}

    with open(gov_path, encoding="utf-8") as f:
        gov = json.load(f)

    agents = {}
    for name, cfg in gov.get("agent_permissions", {}).items():
        agents[name] = {
            "level": cfg.get("permission_level"),
            "name": cfg.get("name"),
            "allowed": cfg.get("allowed", []),
            "denied": cfg.get("denied", []),
        }

    # 检查 kill switch
    ks = gov.get("kill_switch", {})
    agents["__kill_switch__"] = {
        "global_enabled": ks.get("global_enabled", False),
        "reason": ks.get("reason", ""),
    }

    return {"agents": agents}


def tool_check_governance(agent_name: str, action: str) -> Dict[str, Any]:
    """检查指定 agent 是否被允许执行指定 action。"""
    sys.path.insert(0, str(SCRIPTS_DIR))
    from ai_governance import check_permission
    is_permitted, reason = check_permission(agent_name, action)
    return {"agent": agent_name, "action": action, "permitted": is_permitted, "reason": reason}


def tool_run_script(script_name: str, args: List[str] = None) -> Dict[str, Any]:
    """运行 scripts/ 目录下的 Python 脚本。args 为命令行参数。"""
    script_path = SCRIPTS_DIR / script_name
    if not script_path.exists():
        return {"error": f"Script not found: {script_name}"}

    cmd = [sys.executable, str(script_path)]
    if args:
        cmd.extend(args)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(BLOG_ROOT),
        )
        return {
            "script": script_name,
            "returncode": result.returncode,
            "stdout": result.stdout[:4000],
            "stderr": result.stderr[:2000],
            "truncated_stdout": len(result.stdout) > 4000,
        }
    except subprocess.TimeoutExpired:
        return {"error": "Script timed out (120s)"}
    except Exception as e:
        return {"error": str(e)}


def tool_read_memory(agent_name: str) -> Dict[str, Any]:
    """读取指定 agent 的长期记忆。"""
    memory_path = REPORTS_DIR / "agent" / f"memory_{agent_name}.json"
    if not memory_path.exists():
        return {"agent": agent_name, "experiences": [], "count": 0}

    try:
        with open(memory_path, encoding="utf-8") as f:
            data = json.load(f)
        # 只返回最近 10 条
        recent = data[-10:] if len(data) > 10 else data
        return {
            "agent": agent_name,
            "total_count": len(data),
            "experiences": recent,
        }
    except Exception as e:
        return {"error": str(e)}


def tool_read_insights(agent_name: str) -> Dict[str, Any]:
    """读取指定 agent 学到的经验规则。"""
    insights_path = REPORTS_DIR / "agent" / f"insights_{agent_name}.json"
    if not insights_path.exists():
        return {"agent": agent_name, "insights": {}, "count": 0}

    try:
        with open(insights_path, encoding="utf-8") as f:
            data = json.load(f)
        return {"agent": agent_name, "insights": data, "count": len(data)}
    except Exception as e:
        return {"error": str(e)}


def tool_generate_insight(agent_name: str, key: str, value: str) -> Dict[str, Any]:
    """为指定 agent 添加一条学习到的经验。"""
    insights_path = REPORTS_DIR / "agent" / f"insights_{agent_name}.json"
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    data = {}
    if insights_path.exists():
        try:
            with open(insights_path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

    data[key] = value
    with open(insights_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return {"success": True, "agent": agent_name, "key": key, "value": value}


def tool_get_date() -> Dict[str, Any]:
    """获取当前日期和时间信息。"""
    now = datetime.now()
    return {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "day_of_week": now.strftime("%A"),
        "timestamp": now.isoformat(),
        "timezone": "UTC",
    }


# ══════════════════════════════════════════════════════════════════════
# 工具注册
# ══════════════════════════════════════════════════════════════════════

def create_default_tools() -> ToolRegistry:
    """创建并注册所有默认工具。"""
    registry = ToolRegistry()

    registry.register(
        "read_file",
        "Read a file from the project. Returns file content (max 8KB).",
        {"file_path": "str"},
        tool_read_file,
    )

    registry.register(
        "read_config",
        "Read a configuration file from config/ directory.",
        {"config_name": "str"},
        tool_read_config,
    )

    registry.register(
        "list_files",
        "List files in a directory. Optional pattern filter.",
        {"directory": "str", "pattern": "str"},
        tool_list_files,
    )

    registry.register(
        "read_report",
        "Read a report from reports/ directory.",
        {"report_path": "str"},
        tool_read_report,
    )

    registry.register(
        "list_reports",
        "List reports in reports/ directory. Optional category filter.",
        {"category": "str"},
        tool_list_reports,
    )

    registry.register(
        "list_agents",
        "List all known AI agents and their permission levels.",
        {},
        tool_list_agents,
    )

    registry.register(
        "check_governance",
        "Check if an agent is permitted to perform an action.",
        {"agent_name": "str", "action": "str"},
        tool_check_governance,
    )

    registry.register(
        "run_script",
        "Run a Python script from scripts/ directory. Optional command-line args.",
        {"script_name": "str", "args": "list"},
        tool_run_script,
    )

    registry.register(
        "read_memory",
        "Read an agent's long-term memory (past experiences).",
        {"agent_name": "str"},
        tool_read_memory,
    )

    registry.register(
        "read_insights",
        "Read an agent's learned insights/knowledge.",
        {"agent_name": "str"},
        tool_read_insights,
    )

    registry.register(
        "generate_insight",
        "Save a new learned insight for an agent.",
        {"agent_name": "str", "key": "str", "value": "str"},
        tool_generate_insight,
    )

    registry.register(
        "get_date",
        "Get current date and time.",
        {},
        tool_get_date,
    )

    return registry


def create_social_tools() -> ToolRegistry:
    """创建社媒专用工具集。"""
    registry = create_default_tools()
    # 社媒 Agent 可以注册更多专用工具
    # 例如：检查 Buffer 状态、获取社媒数据等
    return registry


def create_seo_tools() -> ToolRegistry:
    """创建 SEO 专用工具集。"""
    registry = create_default_tools()
    # SEO Agent 可以注册更多专用工具
    return registry


def create_content_tools() -> ToolRegistry:
    """创建内容专用工具集。"""
    registry = create_default_tools()
    # Content Agent 可以注册更多专用工具
    return registry
