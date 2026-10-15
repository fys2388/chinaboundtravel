#!/usr/bin/env python3
"""
ChinaBound Travel - Autonomous Agent Test Suite
测试 Agent 系统的各个组件是否正常工作。

用法:
    python scripts/test_agent.py                    # 运行所有测试
    python scripts/test_agent.py --verbose           # 详细输出
    python scripts/test_agent.py --llm               # 包含 LLM 测试（需要 API Key）
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# 项目路径
ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

PASS = 0
FAIL = 0
TESTS = []


def test(name: str):
    """装饰器：注册测试。"""
    def decorator(func):
        TESTS.append((name, func))
        return func
    return decorator


# ══════════════════════════════════════════════════════════════════════
# 测试用例
# ══════════════════════════════════════════════════════════════════════

@test("AgentCore: 导入")
def test_core_import():
    from agent_core import AutonomousAgent, LLMClient, AgentMemory, ToolRegistry
    assert AutonomousAgent is not None
    assert LLMClient is not None
    assert AgentMemory is not None
    assert ToolRegistry is not None


@test("AgentCore: LLMClient 初始化")
def test_llm_client():
    from agent_core import LLMClient
    client = LLMClient()
    assert client._base_url != ""
    assert client._model != ""


@test("AgentCore: AgentMemory 创建")
def test_agent_memory():
    from agent_core import AgentMemory
    import uuid
    name = f"test_agent_{uuid.uuid4().hex[:8]}"
    memory = AgentMemory(name)
    assert memory.agent_name == name
    assert memory._long_term == []
    assert memory._insights == {}
    # 清理测试文件
    import os
    for path in [memory.long_term_path, memory.insights_path]:
        if path.exists():
            os.unlink(path)


@test("AgentCore: AgentMemory 存储经验")
def test_memory_store():
    from agent_core import AgentMemory
    import uuid
    name = f"test_agent_{uuid.uuid4().hex[:8]}"
    memory = AgentMemory(name)
    memory.store_experience(
        goal="测试目标",
        plan=["步骤1", "步骤2"],
        results=[{"step": 1, "result": "ok"}],
        success=True,
        insight="学到了一个东西",
    )
    assert len(memory._long_term) == 1
    assert memory._long_term[0]["goal"] == "测试目标"
    assert memory._long_term[0]["success"] == True
    # 清理测试文件
    import os
    for path in [memory.long_term_path, memory.insights_path]:
        if path.exists():
            os.unlink(path)


@test("AgentCore: AgentMemory 更新经验")
def test_memory_insight():
    from agent_core import AgentMemory
    import uuid
    name = f"test_agent_{uuid.uuid4().hex[:8]}"
    memory = AgentMemory(name)
    memory.update_insight("lesson_1", "这个方法是有效的")
    assert "lesson_1" in memory._insights
    assert memory._insights["lesson_1"] == "这个方法是有效的"
    # 清理测试文件
    import os
    for path in [memory.long_term_path, memory.insights_path]:
        if path.exists():
            os.unlink(path)


@test("AgentCore: AgentMemory 检索")
def test_memory_recall():
    from agent_core import AgentMemory
    import uuid
    name = f"test_agent_{uuid.uuid4().hex[:8]}"
    memory = AgentMemory(name)
    memory.store_experience("测试SEO优化", [], [], True, "SEO优化需要数据支撑")
    memory.store_experience("测试社媒发布", [], [], True, "社媒发布要注意时间")
    results = memory.recall("SEO优化")
    assert len(results) >= 1
    # 清理测试文件
    import os
    for path in [memory.long_term_path, memory.insights_path]:
        if path.exists():
            os.unlink(path)


@test("AgentCore: ToolRegistry 注册工具")
def test_tool_registry():
    from agent_core import ToolRegistry
    registry = ToolRegistry()
    registry.register("test_tool", "测试工具", {"arg": "str"}, lambda arg: {"result": arg})
    tools = registry.list_tools()
    assert len(tools) == 1
    assert tools[0]["name"] == "test_tool"


@test("AgentCore: ToolRegistry 执行工具")
def test_tool_execute():
    from agent_core import ToolRegistry
    registry = ToolRegistry()
    registry.register("test_tool", "测试工具", {"arg": "str"}, lambda arg: {"result": arg})
    result = registry.execute("test_tool", {"arg": "hello"})
    assert result["success"] == True
    assert result["result"] == {"result": "hello"}


@test("AgentCore: ToolRegistry 未知工具")
def test_tool_unknown():
    from agent_core import ToolRegistry
    registry = ToolRegistry()
    result = registry.execute("nonexistent", {})
    assert result["success"] == False
    assert "Unknown tool" in result["error"]


@test("AgentTools: 默认工具集")
def test_default_tools():
    from agent_tools import create_default_tools
    tools = create_default_tools()
    assert len(tools._tools) == 12
    assert "read_file" in tools._tools
    assert "read_config" in tools._tools
    assert "run_script" in tools._tools
    assert "get_date" in tools._tools


@test("AgentTools: get_date")
def test_tool_get_date():
    from agent_tools import tool_get_date
    result = tool_get_date()
    assert "date" in result
    assert "time" in result
    assert "day_of_week" in result


@test("AgentTools: read_config")
def test_tool_read_config():
    from agent_tools import tool_read_config
    result = tool_read_config("llm_config")
    assert "data" in result
    assert "default_provider" in result["data"]


@test("AgentTools: list_agents")
def test_tool_list_agents():
    from agent_tools import tool_list_agents
    result = tool_list_agents()
    assert "agents" in result
    assert "social" in result["agents"]
    assert "seo" in result["agents"]


@test("AgentTools: check_governance")
def test_tool_governance():
    from agent_tools import tool_check_governance
    result = tool_check_governance("social", "optimize_social_hook")
    assert "permitted" in result
    assert "reason" in result


@test("AgentTools: read_memory")
def test_tool_read_memory():
    from agent_tools import tool_read_memory
    result = tool_read_memory("test_agent")
    assert "experiences" in result
    assert "total_count" in result


@test("AgentTools: generate_insight")
def test_tool_generate_insight():
    from agent_tools import tool_generate_insight
    result = tool_generate_insight("test_agent", "test_key", "test_value")
    assert result["success"] == True
    # 清理测试文件
    insights_path = ROOT / "reports" / "agent" / "insights_test_agent.json"
    if insights_path.exists():
        insights_path.unlink()


@test("AgentRunner: 导入")
def test_runner_import():
    from agent_runner import _get_agent_configs
    configs = _get_agent_configs()
    assert "social" in configs
    assert "seo" in configs
    assert "content" in configs
    assert "general" in configs


@test("AgentRunner: 上下文提供者")
def test_context_providers():
    from agent_runner import get_social_context, get_seo_context, get_content_context, get_general_context
    # 这些函数不应该抛出异常
    social_ctx = get_social_context()
    seo_ctx = get_seo_context()
    content_ctx = get_content_context()
    general_ctx = get_general_context()
    assert isinstance(social_ctx, dict)
    assert isinstance(seo_ctx, dict)
    assert isinstance(content_ctx, dict)
    assert isinstance(general_ctx, dict)


@test("Governance: Kill Switch 检查")
def test_kill_switch():
    from ai_governance import check_kill_switch
    is_safe, reason = check_kill_switch()
    assert is_safe == True  # Kill switch 应该关闭


@test("Governance: 权限检查")
def test_permission_check():
    from ai_governance import check_permission
    # social agent 应该可以 optimize_social_hook
    permitted, reason = check_permission("social", "optimize_social_hook")
    assert permitted == True


@test("Governance: 禁止权限")
def test_permission_denied():
    from ai_governance import check_permission
    # social agent 不应该可以 modify_visa_policy
    permitted, reason = check_permission("social", "modify_visa_policy")
    assert permitted == False


@test("LLM: API Key 检查（可选）")
def test_llm_api_key():
    from agent_core import LLMClient
    client = LLMClient()
    if not client._api_key:
        print("    (跳过 - API Key 未配置)")
        return
    # 如果有关键字，可以测试实际调用
    # 这里只做初始化测试，不做实际调用


# ══════════════════════════════════════════════════════════════════════
# 运行测试
# ══════════════════════════════════════════════════════════════════════

def run_tests(include_llm: bool = False, verbose: bool = False):
    global PASS, FAIL

    print("=" * 60)
    print("Autonomous Agent Test Suite")
    print("=" * 60)
    print()

    for name, func in TESTS:
        if not include_llm and "LLM:" in name:
            continue
        try:
            func()
            PASS += 1
            status = "[PASS]  "
        except Exception as e:
            FAIL += 1
            status = "[FAIL]  "
            if verbose:
                import traceback
                traceback.print_exc()
            else:
                print(f"       Error: {e}")

        print(f"{status}  {name}")

    print()
    print("=" * 60)
    total = PASS + FAIL
    print(f"Results: {PASS}/{total} passed, {FAIL} failed")
    if FAIL == 0:
        print("All tests passed!")
    else:
        print(f"{FAIL} test(s) failed")
    print("=" * 60)

    return FAIL == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Autonomous Agent Test Suite")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--llm", action="store_true", help="Include LLM tests (requires API key)")
    args = parser.parse_args()

    success = run_tests(include_llm=args.llm, verbose=args.verbose)
    sys.exit(0 if success else 1)
