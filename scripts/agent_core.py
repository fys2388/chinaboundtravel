#!/usr/bin/env python3
"""
ChinaBound Travel - Autonomous Agent Core
真正的自主思考 Agent：LLM 决策 → 工具执行 → 反思学习 → 升级策略

架构：
  SenseNova LLM  ──→  Planner  ──→  Executor  ──→  Reflector  ──→  Learner
       ↑                                                              │
       └──────────────── Memory (短期 + 长期) ←──────────────────────┘

权限边界遵循 config/ai_governance.json，启动时检查 Kill Switch。
"""

from __future__ import annotations

import json
import os
import sys
import time
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 项目路径
BLOG_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = BLOG_ROOT / "config"
REPORTS_DIR = BLOG_ROOT / "reports"
AGENT_DIR = REPORTS_DIR / "agent"
AGENT_DIR.mkdir(parents=True, exist_ok=True)

# 治理模块
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ai_governance import check_kill_switch, check_permission, GovernanceError  # noqa: E402

# ── 日志 ──────────────────────────────────────────────────────────────
AGENT_LOG_DIR = AGENT_DIR / "logs"
AGENT_LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(AGENT_LOG_DIR / f"agent_{datetime.now().strftime('%Y%m%d')}.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("agent_core")


# ══════════════════════════════════════════════════════════════════════
# LLM 客户端 — 使用已有的 config/llm_config.json
# ══════════════════════════════════════════════════════════════════════

class LLMClient:
    """调用 SenseNova / DeepSeek / OpenAI，与现有 config 对齐。"""

    def __init__(self):
        self._config = self._load_config()
        self._provider = self._config.get("default_provider", "sensenova")
        self._provider_cfg = self._config.get(self._provider, {})
        self._base_url = self._provider_cfg.get("base_url", "")
        self._model = self._provider_cfg.get("model", "")
        self._api_key = os.getenv(self._provider_cfg.get("api_key_env", "SENSENOVA_API_KEY"), "")
        self._max_tokens = self._provider_cfg.get("max_tokens", 4000)
        self._temperature = self._provider_cfg.get("temperature", 0.7)
        self._timeout = self._provider_cfg.get("timeout_seconds", 120)

        # 日调用计数（从文件恢复）
        self._call_count = self._load_call_count()

    def _load_config(self) -> dict:
        path = CONFIG_DIR / "llm_config.json"
        if path.exists():
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        log.warning("llm_config.json not found, using defaults")
        return {}

    def _load_call_count(self) -> int:
        path = AGENT_DIR / "call_count.json"
        if path.exists():
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                    if data.get("date") == today:
                        return data.get("count", 0)
            except Exception:
                pass
        return 0

    def _save_call_count(self):
        data = {"date": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "count": self._call_count}
        with open(AGENT_DIR / "call_count.json", "w", encoding="utf-8") as f:
            json.dump(data, f)

    def chat(self, messages: List[Dict[str, str]], max_tokens: int = None, temperature: float = None) -> str:
        """调用 LLM，返回文本回复。"""
        import requests

        limit = self._config.get("limits", {}).get("daily_call_limit", 200)
        if self._call_count >= limit:
            raise RuntimeError(f"Daily call limit reached ({self._call_count}/{limit})")

        if not self._api_key:
            raise RuntimeError(f"API key not set for provider '{self._provider}'")

        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": messages,
            "max_tokens": max_tokens or self._max_tokens,
            "temperature": temperature if temperature is not None else self._temperature,
        }

        self._call_count += 1
        self._save_call_count()

        resp = requests.post(url, headers=headers, json=payload, timeout=self._timeout)
        if resp.status_code != 200:
            raise RuntimeError(f"LLM API error {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def chat_json(self, messages: List[Dict[str, str]], max_tokens: int = None) -> dict:
        """调用 LLM 并要求返回 JSON。自动提取第一个 { ... } 块。"""
        raw = self.chat(messages, max_tokens=max_tokens or 4000)
        # 提取 JSON
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start == -1 or end == 0:
            log.warning("LLM did not return JSON, raw: %.200s", raw)
            return {}
        try:
            return json.loads(raw[start:end])
        except json.JSONDecodeError as e:
            log.warning("JSON decode error: %s, raw: %.300s", e, raw)
            return {}


# ══════════════════════════════════════════════════════════════════════
# Agent Memory — 短期 + 长期记忆
# ══════════════════════════════════════════════════════════════════════

class AgentMemory:
    """双层记忆：短期（当前会话上下文）+ 长期（历史经验 JSON 文件）。"""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.short_term: List[Dict[str, str]] = []  # [{role, content}]
        self.long_term_path = AGENT_DIR / f"memory_{agent_name}.json"
        self.insights_path = AGENT_DIR / f"insights_{agent_name}.json"
        self._long_term: List[Dict] = []
        self._insights: Dict[str, Any] = {}
        self._load()

    def _load(self):
        if self.long_term_path.exists():
            try:
                with open(self.long_term_path, encoding="utf-8") as f:
                    self._long_term = json.load(f)
            except Exception:
                self._long_term = []
        if self.insights_path.exists():
            try:
                with open(self.insights_path, encoding="utf-8") as f:
                    self._insights = json.load(f)
            except Exception:
                self._insights = {}

    def _save_long_term(self):
        with open(self.long_term_path, "w", encoding="utf-8") as f:
            json.dump(self._long_term, f, ensure_ascii=False, indent=2)

    def _save_insights(self):
        with open(self.insights_path, "w", encoding="utf-8") as f:
            json.dump(self._insights, f, ensure_ascii=False, indent=2)

    def add_short_term(self, role: str, content: str):
        self.short_term.append({"role": role, "content": content})
        # 保留最近 20 条
        if len(self.short_term) > 20:
            self.short_term = self.short_term[-20:]

    def get_short_term_messages(self) -> List[Dict[str, str]]:
        return list(self.short_term)

    def store_experience(self, goal: str, plan: List[str], results: List[Dict], success: bool, insight: str = ""):
        """将一次执行的经验存入长期记忆。"""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "goal": goal,
            "plan": plan,
            "results": results,
            "success": success,
            "insight": insight,
        }
        self._long_term.append(entry)
        # 保留最近 100 条
        if len(self._long_term) > 100:
            self._long_term = self._long_term[-100:]
        self._save_long_term()

    def recall(self, query: str, top_k: int = 5) -> List[Dict]:
        """从长期记忆中检索与查询最相关的经验（简单关键词匹配）。"""
        query_words = set(query.lower().split())
        scored = []
        for entry in self._long_term:
            text = json.dumps(entry, ensure_ascii=False).lower()
            score = sum(1 for w in query_words if w in text)
            scored.append((score, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:top_k]]

    def update_insight(self, key: str, value: Any):
        """更新学习到的经验规则。"""
        self._insights[key] = value
        self._save_insights()

    def get_insights(self) -> Dict[str, Any]:
        return dict(self._insights)

    def get_insight_text(self) -> str:
        """将经验规则格式化为 LLM 可读的文本。"""
        if not self._insights:
            return "No prior insights learned yet."
        lines = []
        for k, v in self._insights.items():
            lines.append(f"- {k}: {v}")
        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════
# Agent Tools — 工具注册表
# ══════════════════════════════════════════════════════════════════════

class ToolRegistry:
    """注册可被 Agent 调用的工具。每个工具 = (name, schema, handler)。"""

    def __init__(self):
        self._tools: Dict[str, Dict] = {}

    def register(self, name: str, description: str, parameters: Dict, handler: Any):
        self._tools[name] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "handler": handler,
        }

    def list_tools(self) -> List[Dict]:
        return [
            {"name": t["name"], "description": t["description"], "parameters": t["parameters"]}
            for t in self._tools.values()
        ]

    def get_tool(self, name: str) -> Optional[Dict]:
        return self._tools.get(name)

    def execute(self, name: str, arguments: Dict) -> Dict[str, Any]:
        tool = self._tools.get(name)
        if not tool:
            return {"success": False, "error": f"Unknown tool: {name}"}
        try:
            result = tool["handler"](**arguments)
            return {"success": True, "result": result}
        except Exception as e:
            log.error("Tool '%s' execution error: %s", name, e)
            return {"success": False, "error": str(e)}

    def build_tools_prompt(self) -> str:
        """生成 LLM 可读的工具说明文本。"""
        if not self._tools:
            return "No tools registered."
        lines = ["Available tools you can use:"]
        for t in self._tools.values():
            params_str = ", ".join(t["parameters"].keys()) if t["parameters"] else ""
            lines.append(f"  - {t['name']}({params_str}): {t['description']}")
        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════
# AutonomousAgent — 主类
# ══════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are an autonomous AI agent for ChinaBound Travel website optimization.

You have access to tools and can plan, execute, reflect, and learn from your actions.

## Governance Rules (MUST FOLLOW)
1. Check kill switch before any action.
2. Respect permission levels: L0=Read, L1=Safe Auto, L2=Controlled Opt, L3=Human Review Only.
3. NEVER modify visa/legal/financial/factual content without human review.
4. All changes must be rollback-capable.
5. Log every action with timestamp.

## Current Permissions
- You operate at {permission_level} level.
- Allowed actions: {allowed_actions}
- Denied actions: {denied_actions}

## Prior Insights (Learned from Past Experience)
{insights}

## Your Goal
{goal}

## Context
{context}

## Available Tools
{tools}

## Instructions
1. THINK: Analyze the goal and decide what to do first.
2. PLAN: Break the goal into concrete steps (each step uses one tool).
3. ACT: Execute steps one by one using the tool format.
4. REFLECT: After each step, evaluate the result and decide next action.
5. LEARN: Summarize what you learned and how to improve next time.

Use this exact format for each step:
THINK: [your reasoning]
PLAN: [list of steps]
STEP: [tool_name](arg1=value1, arg2=value2)
RESULT: [paste tool result here]
REFLECT: [did it work? what next?]

When done, output:
FINAL_RESULT: {{"success": true/false, "summary": "...", "actions_taken": [...], "insight": "..."}}

Remember: Think carefully before acting. Prefer safe, reversible actions. If unsure, report instead of acting."""


class AutonomousAgent:
    """自主思考 Agent：Think → Plan → Act → Reflect → Learn"""

    def __init__(self, agent_name: str, tools: ToolRegistry):
        self.name = agent_name
        self.tools = tools
        self.llm = LLMClient()
        self.memory = AgentMemory(agent_name)
        self._check_governance()

    def _check_governance(self):
        """启动时检查 Kill Switch。"""
        is_safe, reason = check_kill_switch()
        if not is_safe:
            raise GovernanceError(f"Agent '{self.name}' blocked: {reason}")

    def _get_permission_text(self) -> Dict[str, str]:
        """获取当前 Agent 的权限文本。"""
        gov_path = CONFIG_DIR / "ai_governance.json"
        if not gov_path.exists():
            return {"permission_level": "L2", "allowed_actions": "all_safe", "denied_actions": "high_risk"}

        with open(gov_path, encoding="utf-8") as f:
            gov = json.load(f)

        agents = gov.get("agent_permissions", {})
        agent = agents.get(self.name, {})
        level = agent.get("permission_level", "L2")
        allowed = ", ".join(agent.get("allowed", [])) or "all_safe"
        denied = ", ".join(agent.get("denied", [])) or "none"

        return {
            "permission_level": level,
            "allowed_actions": allowed,
            "denied_actions": denied,
        }

    def run(self, goal: str, context: Dict[str, Any] = None, max_steps: int = 10) -> Dict[str, Any]:
        """执行自主循环：Think → Plan → Act → Reflect → Learn"""
        log.info("=" * 60)
        log.info("Agent '%s' starting", self.name)
        log.info("Goal: %s", goal)
        log.info("=" * 60)

        if context is None:
            context = {}

        # 构建系统提示
        perms = self._get_permission_text()
        insights_text = self.memory.get_insight_text()
        tools_text = self.tools.build_tools_prompt()

        system_prompt = SYSTEM_PROMPT.format(
            permission_level=perms["permission_level"],
            allowed_actions=perms["allowed_actions"],
            denied_actions=perms["denied_actions"],
            insights=insights_text,
            goal=goal,
            context=json.dumps(context, ensure_ascii=False, indent=2),
            tools=tools_text,
        )

        # 初始消息
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Your goal is: {goal}\n\nPlease begin."},
        ]

        self.memory.add_short_term("system", system_prompt[:500])
        self.memory.add_short_term("user", goal)

        actions_taken = []
        step = 0

        while step < max_steps:
            step += 1
            log.info("--- Step %d/%d ---", step, max_steps)

            # 调用 LLM
            try:
                response = self.llm.chat(messages, max_tokens=3000, temperature=0.3)
            except Exception as e:
                log.error("LLM call failed at step %d: %s", step, e)
                return {
                    "success": False,
                    "summary": f"LLM error at step {step}: {e}",
                    "actions_taken": actions_taken,
                    "insight": "",
                }

            log.debug("LLM response (step %d): %.500s", step, response)
            messages.append({"role": "assistant", "content": response})
            self.memory.add_short_term("assistant", response)

            # 检查是否完成
            if "FINAL_RESULT:" in response:
                # 解析最终结果
                final_text = response.split("FINAL_RESULT:")[-1].strip()
                try:
                    final = json.loads(final_text)
                except json.JSONDecodeError:
                    final = {"success": False, "summary": final_text[:500], "actions_taken": actions_taken, "insight": ""}

                insight = final.get("insight", "")
                success = final.get("success", False)

                # 存入记忆
                self.memory.store_experience(
                    goal=goal,
                    plan=actions_taken,
                    results=[{"step": step, "response": response[:500]}],
                    success=success,
                    insight=insight,
                )

                if insight:
                    self.memory.update_insight(f"lesson_{step}", insight)

                log.info("Agent '%s' completed. Success: %s", self.name, success)
                return final

            # 检查是否要执行工具
            tool_call = self._parse_tool_call(response)
            if tool_call:
                tool_name, args = tool_call
                log.info("Executing tool: %s(%s)", tool_name, json.dumps(args, ensure_ascii=False))

                result = self.tools.execute(tool_name, args)
                actions_taken.append({"step": step, "tool": tool_name, "args": args, "result": result})

                result_str = json.dumps(result, ensure_ascii=False, indent=2)
                messages.append({"role": "user", "content": f"RESULT: {result_str}"})
                self.memory.add_short_term("user", f"RESULT: {result_str[:500]}")

            else:
                # LLM 没有调用工具，可能是在思考/总结，继续
                log.info("LLM responded without tool call, continuing...")
                messages.append({"role": "user", "content": "Continue. If you're done, output FINAL_RESULT."})

        # 超过最大步数
        log.warning("Agent '%s' exceeded max steps (%d)", self.name, max_steps)
        return {
            "success": False,
            "summary": f"Exceeded max steps ({max_steps})",
            "actions_taken": actions_taken,
            "insight": "",
        }

    def _parse_tool_call(self, text: str) -> Optional[Tuple[str, Dict]]:
        """从 LLM 回复中解析工具调用。

        格式: STEP: tool_name(arg1=value1, arg2=value2)
        """
        import re

        # 匹配 STEP: tool_name(args)
        match = re.search(r"STEP:\s*(\w+)\(([^)]*)\)", text)
        if not match:
            return None

        tool_name = match.group(1)
        args_str = match.group(2).strip()

        if not args_str:
            return (tool_name, {})

        # 解析参数
        args = {}
        for pair in args_str.split(","):
            if "=" in pair:
                k, v = pair.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'\"")
                # 尝试解析为 JSON
                try:
                    args[k] = json.loads(v)
                except (json.JSONDecodeError, ValueError):
                    args[k] = v
        return (tool_name, args)

    def get_memory_summary(self) -> Dict[str, Any]:
        """获取记忆摘要。"""
        return {
            "agent": self.name,
            "short_term_count": len(self.memory.short_term),
            "long_term_count": len(self.memory._long_term),
            "insights_count": len(self.memory._insights),
            "last_experience": self.memory._long_term[-1] if self.memory._long_term else None,
        }
