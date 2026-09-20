#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChinaBound Travel - LLM Analyzer
LLM 统一调用层 — 支持 SenseNova / DeepSeek / OpenAI 兼容 API

设计原则:
  1. 确定性降级：未配置 key 或调用失败时，返回 None（不抛异常）
  2. 结果缓存：相同输入 24 小时内不重复调用
  3. 治理合规：所有调用走 ai_governance.check_kill_switch()
  4. 成本可控：max_tokens 限制 + 每日调用计数

支持的 LLM 提供商:
  - SenseNova (商汤日日新): https://token.sensenova.cn/v1
  - DeepSeek: https://api.deepseek.com
  - OpenAI: https://api.openai.com/v1

使用方式:
    from llm_analyzer import LLMAnalyzer

    llm = LLMAnalyzer()
    if llm.available:
        result = llm.analyze("分析这篇文章的内容质量", {"content": "..."})
"""

from __future__ import annotations

import json
import hashlib
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("llm_analyzer")

# === 项目路径 ===
PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
LLM_REPORTS_DIR = REPORTS_DIR / "llm"
LLM_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

CACHE_DIR = LLM_REPORTS_DIR / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LLM_REPORTS_DIR / "llm_usage_log.json"

# === LLM 配置 ===
CONFIG_PATH = PROJECT_ROOT / "config" / "llm_config.json"

# 默认配置（可被 config/llm_config.json 覆盖）
DEFAULT_CONFIG = {
    "default_provider": "sensenova",
    "enabled": True,
    "sensenova": {
        "base_url": "https://token.sensenova.cn/v1",
        "api_key_env": "SENSENOVA_API_KEY",
        "model": "sensenova-6.8-flash-lite",
        "models": ["sensenova-6.8-flash-lite", "sensenova-u1.5-lite"],
        "max_tokens": 4000,
        "timeout_seconds": 120,
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "api_key_env": "DEEPSEEK_API_KEY",
        "model": "deepseek-chat",
        "max_tokens": 4000,
        "timeout_seconds": 120,
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
        "model": "gpt-4o",
        "max_tokens": 4000,
        "timeout_seconds": 120,
    },
    "limits": {
        "daily_call_limit": 200,
        "max_tokens_per_call": 4000,
        "cache_ttl_hours": 24,
        "retry_attempts": 2,
        "retry_delay_seconds": 3,
    },
}

# 缓存 TTL
CACHE_TTL_SECONDS = 86400  # 24 小时

# 每日调用计数（运行时）
_daily_call_count = 0
_daily_call_date = datetime.now(timezone.utc).date()


def _load_config() -> dict:
    """加载 LLM 配置，文件不存在时使用默认配置"""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                user_config = json.load(f)
            # 合并：用户配置覆盖默认配置
            merged = {**DEFAULT_CONFIG, **user_config}
            # 深合并提供商配置
            for provider in ("sensenova", "deepseek", "openai"):
                if provider in user_config and provider in DEFAULT_CONFIG:
                    merged[provider] = {**DEFAULT_CONFIG[provider], **user_config.get(provider, {})}
            return merged
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("LLM config load failed, using defaults: %s", e)
    return {k: v.copy() if isinstance(v, dict) else v for k, v in DEFAULT_CONFIG.items()}


def _load_usage_log() -> dict:
    """加载调用日志"""
    if LOG_FILE.exists():
        try:
            with open(LOG_FILE, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"total_calls": 0, "total_tokens": 0, "by_provider": {}, "by_date": {}, "errors": []}


def _save_usage_log(log: dict):
    """保存调用日志"""
    try:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(log, f, ensure_ascii=False, indent=2)
    except OSError as e:
        logger.warning("Failed to save usage log: %s", e)


def _get_cache_key(prompt: str, context: Optional[dict]) -> str:
    """生成缓存 key"""
    data = json.dumps({"prompt": prompt, "context": context}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()[:16]


def _check_cache(cache_key: str) -> Optional[str]:
    """检查缓存"""
    cache_file = CACHE_DIR / f"{cache_key}.json"
    if not cache_file.exists():
        return None
    try:
        with open(cache_file, encoding="utf-8") as f:
            data = json.load(f)
        # 检查 TTL
        cached_at = data.get("cached_at", 0)
        if time.time() - cached_at > CACHE_TTL_SECONDS:
            return None
        return data.get("response", "")
    except (json.JSONDecodeError, OSError):
        return None


def _save_cache(cache_key: str, response: str):
    """保存缓存"""
    cache_file = CACHE_DIR / f"{cache_key}.json"
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump({"response": response, "cached_at": time.time()}, f, ensure_ascii=False)
    except OSError as e:
        logger.warning("Failed to save cache: %s", e)


def _clean_old_cache():
    """清理过期缓存（每日调用时执行一次）"""
    now = time.time()
    for cache_file in CACHE_DIR.glob("*.json"):
        try:
            with open(cache_file, encoding="utf-8") as f:
                data = json.load(f)
            if now - data.get("cached_at", 0) > CACHE_TTL_SECONDS:
                cache_file.unlink()
        except (json.JSONDecodeError, OSError):
            pass


class LLMAnalyzer:
    """LLM 统一调用层。

    支持 SenseNova / DeepSeek / OpenAI 兼容 API。
    未配置 key 或调用失败时，返回 None（确定性降级）。
    """

    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        self.config = _load_config()

        # 检查全局开关
        if not self.config.get("enabled", True):
            logger.info("LLM disabled by config/llm_config.json")
            self.available = False
            return

        # 确定提供商
        self.provider = provider or self.config.get("default_provider", "sensenova")
        provider_config = self.config.get(self.provider)
        if not provider_config:
            logger.warning("Unknown LLM provider: %s", self.provider)
            self.available = False
            return

        # 获取 API key
        api_key_env = provider_config.get("api_key_env", "")
        self.api_key = os.environ.get(api_key_env, "")
        if not self.api_key:
            logger.info("LLM %s: %s not set, LLM calls disabled", self.provider, api_key_env)
            self.available = False
            return

        self.base_url = provider_config.get("base_url", "")
        self.model = model or provider_config.get("model", "")
        self.max_tokens = provider_config.get("max_tokens", 4000)
        self.timeout = provider_config.get("timeout_seconds", 120)

        limits = self.config.get("limits", {})
        self.daily_limit = limits.get("daily_call_limit", 200)
        self.max_tokens_per_call = limits.get("max_tokens_per_call", 4000)
        self.retry_attempts = limits.get("retry_attempts", 2)
        self.retry_delay = limits.get("retry_delay_seconds", 3)

        self.available = True
        logger.info("LLM %s initialized: model=%s, base_url=%s", self.provider, self.model, self.base_url)

    def _check_daily_limit(self) -> bool:
        """检查每日调用限额"""
        global _daily_call_count, _daily_call_date
        today = datetime.now(timezone.utc).date()
        if today != _daily_call_date:
            _daily_call_count = 0
            _daily_call_date = today

        if _daily_call_count >= self.daily_limit:
            logger.warning("Daily LLM call limit reached: %d/%d", _daily_call_count, self.daily_limit)
            return False
        return True

    def _increment_counter(self):
        """递增调用计数器"""
        global _daily_call_count
        _daily_call_count += 1

    def _log_call(self, model: str, prompt_tokens: int, completion_tokens: int, success: bool):
        """记录调用日志"""
        usage = _load_usage_log()
        usage["total_calls"] += 1
        usage["total_tokens"] += prompt_tokens + completion_tokens

        provider_usage = usage["by_provider"].setdefault(self.provider, {"calls": 0, "tokens": 0})
        provider_usage["calls"] += 1
        provider_usage["tokens"] += prompt_tokens + completion_tokens

        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        day_usage = usage["by_date"].setdefault(today_str, {"calls": 0, "tokens": 0})
        day_usage["calls"] += 1
        day_usage["tokens"] += prompt_tokens + completion_tokens

        if not success:
            usage["errors"].append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "provider": self.provider,
                "model": model,
            })
            # 只保留最近 100 条错误
            usage["errors"] = usage["errors"][-100:]

        _save_usage_log(usage)

    def chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[dict] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        use_cache: bool = True,
        force_refresh: bool = False,
    ) -> Optional[dict]:
        """调用 LLM 进行对话。

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            context: 附加上下文数据（用于缓存 key 和日志）
            max_tokens: 最大生成 token 数
            temperature: 生成温度
            use_cache: 是否使用缓存
            force_refresh: 强制跳过缓存

        Returns:
            {"content": str, "model": str, "usage": dict, "cached": bool} 或 None（降级）
        """
        if not self.available:
            return None

        if not self._check_daily_limit():
            return None

        # 治理检查
        try:
            from ai_governance import check_kill_switch
            is_safe, reason = check_kill_switch("strategy_updates")
            if not is_safe:
                logger.warning("LLM blocked by Kill Switch: %s", reason)
                return None
        except ImportError:
            pass

        # 缓存检查
        cache_key = _get_cache_key(prompt, context)
        if use_cache and not force_refresh:
            cached = _check_cache(cache_key)
            if cached:
                logger.debug("LLM cache hit: %s", cache_key)
                return {
                    "content": cached,
                    "model": self.model,
                    "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                    "cached": True,
                }

        # 定期清理过期缓存
        if _daily_call_count % 50 == 0:
            _clean_old_cache()

        # 构建消息
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        effective_max_tokens = min(max_tokens or self.max_tokens, self.max_tokens_per_call)

        # 调用 API（带重试）
        import requests

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": effective_max_tokens,
            "stream": False,
        }

        last_error = None
        for attempt in range(self.retry_attempts + 1):
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
                resp.raise_for_status()
                data = resp.json()

                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                usage_info = data.get("usage", {})
                prompt_tokens = usage_info.get("prompt_tokens", 0)
                completion_tokens = usage_info.get("completion_tokens", 0)

                # 保存到缓存
                if use_cache and content:
                    _save_cache(cache_key, content)

                # 记录日志
                self._increment_counter()
                self._log_call(self.model, prompt_tokens, completion_tokens, True)

                logger.info(
                    "LLM call success: provider=%s model=%s tokens=%d/%d cached=%s",
                    self.provider, self.model, completion_tokens, prompt_tokens, use_cache,
                )

                return {
                    "content": content,
                    "model": self.model,
                    "usage": {
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": prompt_tokens + completion_tokens,
                    },
                    "cached": False,
                }

            except requests.exceptions.Timeout:
                last_error = "Timeout"
                logger.warning("LLM call timeout (attempt %d/%d)", attempt + 1, self.retry_attempts + 1)
            except requests.exceptions.HTTPError as e:
                last_error = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
                logger.warning("LLM HTTP error (attempt %d/%d): %s", attempt + 1, self.retry_attempts + 1, last_error)
            except Exception as e:
                last_error = str(e)
                logger.warning("LLM call error (attempt %d/%d): %s", attempt + 1, self.retry_attempts + 1, e)

            if attempt < self.retry_attempts:
                time.sleep(self.retry_delay * (attempt + 1))

        # 所有重试失败
        self._increment_counter()
        self._log_call(self.model, 0, 0, False)
        logger.error("LLM call failed after %d attempts: %s", self.retry_attempts + 1, last_error)
        return None

    def analyze(self, prompt: str, data: Optional[dict] = None, **kwargs) -> Optional[str]:
        """便捷方法：分析数据并返回文本结果。

        未配置 key 或调用失败时返回 None。
        """
        if not self.available:
            return None

        full_prompt = prompt
        if data:
            data_str = json.dumps(data, ensure_ascii=False, indent=2)
            full_prompt += f"\n\n数据:\n{data_str}"

        result = self.chat(full_prompt, context=data, **kwargs)
        if result:
            return result["content"]
        return None

    def evaluate(
        self,
        item_description: str,
        evaluation_criteria: List[str],
        output_schema: Optional[str] = None,
    ) -> Optional[dict]:
        """使用 LLM 进行结构化评估。

        返回 JSON 对象，结构由 output_schema 定义。
        """
        if not self.available:
            return None

        criteria_text = "\n".join(f"- {c}" for c in evaluation_criteria)
        schema_hint = f"\n请返回 JSON 格式: {output_schema}" if output_schema else "\n请返回 JSON 格式。"

        prompt = (
            f"请对以下内容进行评估：\n\n"
            f"待评估对象: {item_description}\n\n"
            f"评估标准:\n{criteria_text}\n"
            f"{schema_hint}"
        )

        result = self.chat(prompt, system_prompt="你是一个严谨的评估专家。请按照评估标准进行客观评估，返回 JSON 格式结果。")
        if not result:
            return None

        # 尝试解析 JSON
        content = result["content"].strip()
        # 提取 JSON 块
        if content.startswith("```"):
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if "```" in line and i > 0:
                    content = "\n".join(lines[i-1:])
                    break
            content = content.split("```")[0].strip()

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            logger.warning("LLM returned non-JSON: %s", content[:200])
            return {"raw_response": content}

    def suggest(
        self,
        context: str,
        suggestion_type: str = "general",
        constraints: Optional[List[str]] = None,
    ) -> Optional[str]:
        """使用 LLM 生成优化建议。

        Args:
            context: 当前上下文描述
            suggestion_type: 建议类型（seo/title/content/socail）
            constraints: 约束条件列表

        Returns:
            建议文本 或 None
        """
        if not self.available:
            return None

        constraints_text = ""
        if constraints:
            constraints_text = "\n约束条件:\n" + "\n".join(f"- {c}" for c in constraints)

        type_prompts = {
            "seo": "你是一个 SEO 专家。请基于数据分析结果，提供具体的 SEO 优化建议。",
            "title": "你是一个标题优化专家。请生成吸引人的标题建议。",
            "content": "你是一个内容策略专家。请提供内容优化和选题建议。",
            "social": "你是一个社媒运营专家。请提供社媒内容优化建议。",
            "general": "你是一个运营策略专家。请提供优化建议。",
        }

        system_prompt = type_prompts.get(suggestion_type, type_prompts["general"])

        prompt = (
            f"当前情况:\n{context}\n"
            f"{constraints_text}\n"
            f"\n请提供具体、可执行的建议。"
        )

        return self.analyze(prompt, system_prompt=system_prompt)


def get_llm_analyzer(provider: Optional[str] = None) -> LLMAnalyzer:
    """获取 LLM 分析器实例（单例模式）。"""
    key = provider or "default"
    if not hasattr(get_llm_analyzer, "_instances"):
        get_llm_analyzer._instances = {}
    if key not in get_llm_analyzer._instances:
        get_llm_analyzer._instances[key] = LLMAnalyzer(provider=provider)
    return get_llm_analyzer._instances[key]


# === CLI 测试 ===
if __name__ == "__main__":
    import sys
    import io

    # Windows 编码修复
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

    print("=" * 60)
    print("  LLM Analyzer - 配置检查")
    print("=" * 60)

    analyzer = get_llm_analyzer()
    print(f"\n  可用: {analyzer.available}")

    if analyzer.available:
        print(f"  提供商: {analyzer.provider}")
        print(f"  模型: {analyzer.model}")
        print(f"  API URL: {analyzer.base_url}")
        print(f"  每日限额: {analyzer.daily_limit}")
        print(f"  最大 tokens: {analyzer.max_tokens_per_call}")

        print("\n  测试调用...")
        result = analyzer.chat("你好，请回复'LLM 连接成功'")
        if result:
            print(f"  [OK] 调用成功")
            print(f"  响应: {result['content'][:100]}")
            print(f"  Tokens: {result['usage']['total_tokens']}")
        else:
            print(f"  [FAIL] 调用失败（降级为 None）")

    else:
        print("\n  [WARN]  LLM 不可用。请设置环境变量:")
        print(f"    export SENSENOVA_API_KEY=sk-xxxxx")
        print(f"    或 export DEEPSEEK_API_KEY=sk-xxxxx")
        print(f"\n  获取 Key: https://platform.sensenova.cn/console/keys")

    print("\n" + "=" * 60)
