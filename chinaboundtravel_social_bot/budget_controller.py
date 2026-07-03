#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全局成本控制管理器 (月预算 ¥50 严格版)
- 月预算上限 ¥50 (≈ ¥1.67/天)
- 单次调用上限 ¥0.3
- 超过阈值自动暂停所有 API 调用
- 所有脚本必须通过此控制器调用
"""

import json
from datetime import datetime, timezone
from pathlib import Path

# 配置路径：放在项目根目录的 manifest.json (与各脚本同级目录)
CONFIG_FILENAME = "manifest.json"

# 模型价格（人民币）
MODEL_PRICING = {
    "deepseek-chat": {"input": 0.27, "output": 1.1},      # 每百万 tokens (首选)
    "deepseek-v4-flash": {"input": 1.0, "output": 4.0},   # 每百万 tokens (禁用)
    "deepseek-v4-pro": {"input": 4.0, "output": 16.0},    # 每百万 tokens (禁用)
}

# ============== 严格预算控制参数 ==============
MONTHLY_BUDGET_YUAN = 50.0   # ⚠️ 月预算上限 ¥50
DAILY_BUDGET_YUAN = 1.67     # 日预算 ≈ ¥1.67 (50/30)
SINGLE_CALL_MAX_YUAN = 0.30  # 单次调用上限 ¥0.30
WARNING_THRESHOLD = 0.60     # 达到60%告警
STOP_THRESHOLD = 0.90        # 达到90%强制暂停
# ==============================================

# 允许使用的模型白名单（仅限最便宜的）
ALLOWED_MODELS = {"deepseek-chat"}


class BudgetController:
    """严格预算控制器 - 所有 API 调用必须经过此检查"""

    def __init__(self, custom_config_path=None):
        # 优先使用指定路径，其次向上查找项目根目录的 manifest.json
        if custom_config_path:
            self.config_path = Path(custom_config_path)
        else:
            # 从当前脚本目录开始向上查找 manifest.json
            search_dirs = [
                Path(__file__).parent,
                Path(__file__).parent.parent,
                Path.cwd(),
                Path.cwd().parent,
            ]
            self.config_path = None
            for d in search_dirs:
                candidate = d / CONFIG_FILENAME
                if candidate.exists():
                    self.config_path = candidate
                    break
            # 如果未找到，默认放在当前脚本同级目录
            if self.config_path is None:
                self.config_path = Path(__file__).parent / CONFIG_FILENAME

        self.data = self._load()
        self._ensure_cost_tracking()

    def _load(self):
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    def _save(self):
        """保存到 manifest.json（保留原有内容）"""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except OSError:
            pass

    def _ensure_cost_tracking(self):
        """确保成本追踪字段存在"""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        month_key = datetime.now(timezone.utc).strftime("%Y-%m")

        if "cost_tracking" not in self.data:
            self.data["cost_tracking"] = {}

        if today not in self.data["cost_tracking"]:
            self.data["cost_tracking"][today] = {
                "total_cost_yuan": 0.0,
                "input_tokens": 0,
                "output_tokens": 0,
                "api_calls": 0,
                "by_model": {},
            }

        if "monthly" not in self.data["cost_tracking"]:
            self.data["cost_tracking"]["monthly"] = {}

        if month_key not in self.data["cost_tracking"]["monthly"]:
            self.data["cost_tracking"]["monthly"][month_key] = {
                "total_cost_yuan": 0.0,
                "input_tokens": 0,
                "output_tokens": 0,
                "api_calls": 0,
                "budget_yuan": MONTHLY_BUDGET_YUAN,
            }

        # 自动清理 30 天前的旧数据
        self._cleanup_old_data()

    def _cleanup_old_data(self, days_to_keep=30):
        """清理过期的成本数据"""
        if "cost_tracking" in self.data:
            import datetime as dt
            cutoff = (datetime.now(timezone.utc) - dt.timedelta(days=days_to_keep)).strftime("%Y-%m-%d")
            for date_key in list(self.data["cost_tracking"].keys()):
                if date_key == "monthly":
                    continue
                if date_key < cutoff:
                    del self.data["cost_tracking"][date_key]

    def can_call_api(self, model: str = "deepseek-chat") -> bool:
        """检查是否允许发起 API 调用（前置检查）"""
        # 1. 检查模型白名单
        if model not in ALLOWED_MODELS:
            print(f"[BUDGET] ❌ 模型 '{model}' 不在允许列表中（仅限: {ALLOWED_MODELS}）")
            return False

        # 2. 检查月度预算
        month_status = self.get_monthly_status()
        if month_status["used_percent"] >= STOP_THRESHOLD:
            print(
                f"[BUDGET] 🚫 月度预算已用尽: ¥{month_status['used_yuan']:.2f}/¥{month_status['budget_yuan']:.0f} "
                f"({month_status['used_percent']:.0f}%) - 本月停止所有 API 调用"
            )
            return False

        # 3. 检查日预算
        day_status = self.get_daily_status()
        if day_status["used_percent"] >= STOP_THRESHOLD:
            print(
                f"[BUDGET] 🚫 日预算已用尽: ¥{day_status['used_yuan']:.2f}/¥{day_status['budget_yuan']:.2f} "
                f"({day_status['used_percent']:.0f}%) - 明日恢复"
            )
            return False

        return True

    def check_call_cost(self, model: str, input_tokens: int, output_tokens: int) -> dict:
        """预估单次调用成本，判断是否超限"""
        prices = MODEL_PRICING.get(model, MODEL_PRICING["deepseek-chat"])
        est_cost = (input_tokens * prices["input"] + output_tokens * prices["output"]) / 1_000_000

        result = {
            "estimated_cost": round(est_cost, 4),
            "within_budget": est_cost <= SINGLE_CALL_MAX_YUAN,
            "over_threshold": est_cost > SINGLE_CALL_MAX_YUAN,
        }
        return result

    def record_call(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """记录一次 API 调用并返回实际成本"""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        month_key = datetime.now(timezone.utc).strftime("%Y-%m")

        prices = MODEL_PRICING.get(model, MODEL_PRICING["deepseek-chat"])
        cost = (input_tokens * prices["input"] + output_tokens * prices["output"]) / 1_000_000
        cost = round(cost, 4)

        self._ensure_cost_tracking()

        # 记录到日数据
        today_data = self.data["cost_tracking"][today]
        today_data["total_cost_yuan"] = round(today_data["total_cost_yuan"] + cost, 4)
        today_data["input_tokens"] += input_tokens
        today_data["output_tokens"] += output_tokens
        today_data["api_calls"] += 1
        if model not in today_data["by_model"]:
            today_data["by_model"][model] = {"cost": 0.0, "calls": 0}
        today_data["by_model"][model]["cost"] = round(today_data["by_model"][model]["cost"] + cost, 4)
        today_data["by_model"][model]["calls"] += 1

        # 记录到月数据
        month_data = self.data["cost_tracking"]["monthly"][month_key]
        month_data["total_cost_yuan"] = round(month_data["total_cost_yuan"] + cost, 4)
        month_data["input_tokens"] += input_tokens
        month_data["output_tokens"] += output_tokens
        month_data["api_calls"] += 1

        self._save()
        return cost

    def get_daily_status(self) -> dict:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self._ensure_cost_tracking()
        today_data = self.data["cost_tracking"][today]
        used = today_data["total_cost_yuan"]
        used_percent = round((used / DAILY_BUDGET_YUAN * 100), 1) if DAILY_BUDGET_YUAN > 0 else 0

        return {
            "date": today,
            "used_yuan": round(used, 2),
            "budget_yuan": DAILY_BUDGET_YUAN,
            "remaining_yuan": round(max(DAILY_BUDGET_YUAN - used, 0), 2),
            "used_percent": used_percent,
            "input_tokens": today_data["input_tokens"],
            "output_tokens": today_data["output_tokens"],
            "api_calls": today_data["api_calls"],
            "status":
                "exceeded" if used_percent >= STOP_THRESHOLD * 100
                else "warning" if used_percent >= WARNING_THRESHOLD * 100
                else "ok"
        }

    def get_monthly_status(self) -> dict:
        month_key = datetime.now(timezone.utc).strftime("%Y-%m")
        self._ensure_cost_tracking()
        month_data = self.data["cost_tracking"]["monthly"].get(month_key, {
            "total_cost_yuan": 0.0,
            "input_tokens": 0,
            "output_tokens": 0,
            "api_calls": 0,
            "budget_yuan": MONTHLY_BUDGET_YUAN,
        })
        used = month_data.get("total_cost_yuan", 0.0)
        used_percent = round((used / MONTHLY_BUDGET_YUAN * 100), 1) if MONTHLY_BUDGET_YUAN > 0 else 0

        return {
            "month": month_key,
            "used_yuan": round(used, 2),
            "budget_yuan": MONTHLY_BUDGET_YUAN,
            "remaining_yuan": round(max(MONTHLY_BUDGET_YUAN - used, 0), 2),
            "used_percent": used_percent,
            "input_tokens": month_data.get("input_tokens", 0),
            "output_tokens": month_data.get("output_tokens", 0),
            "api_calls": month_data.get("api_calls", 0),
            "status":
                "exceeded" if used_percent >= STOP_THRESHOLD * 100
                else "warning" if used_percent >= WARNING_THRESHOLD * 100
                else "ok"
        }

    def get_report(self) -> str:
        """生成简短成本报告"""
        day = self.get_daily_status()
        month = self.get_monthly_status()
        lines = []
        lines.append("💰 成本监控")
        lines.append(f"  今日: ¥{day['used_yuan']:.2f}/¥{day['budget_yuan']:.2f} ({day['used_percent']}%)")
        lines.append(f"  本月: ¥{month['used_yuan']:.2f}/¥{month['budget_yuan']:.0f} ({month['used_percent']}%)")
        lines.append(f"  今日调用: {day['api_calls']} 次")
        lines.append(f"  本月调用: {month['api_calls']} 次")
        if day["status"] == "warning":
            lines.append("  ⚠️ 警告: 日预算已用60%以上")
        elif day["status"] == "exceeded":
            lines.append("  🚫 暂停: 日预算已用尽")
        if month["status"] == "warning":
            lines.append("  ⚠️ 警告: 月预算已用60%以上")
        elif month["status"] == "exceeded":
            lines.append("  🚫 暂停: 月预算已用尽 - 下月恢复")
        return "\n".join(lines)


# ============== 全局便捷函数 ==============

_global_controller = None


def get_controller() -> BudgetController:
    """获取全局预算控制器实例"""
    global _global_controller
    if _global_controller is None:
        _global_controller = BudgetController()
    return _global_controller


def can_call_api(model: str = "deepseek-chat") -> bool:
    """便捷函数：检查是否可以调用 API"""
    return get_controller().can_call_api(model)


def record_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """便捷函数：记录一次 API 调用成本"""
    return get_controller().record_call(model, input_tokens, output_tokens)


def get_cost_report() -> str:
    """便捷函数：获取成本报告"""
    return get_controller().get_report()


# ============== 命令行测试 ==============

def main():
    controller = BudgetController()
    print(controller.get_report())
    print()
    print("单次调用测试:")
    cost = controller.record_call("deepseek-chat", 500, 300)
    print(f"  模拟: input=500, output=300, cost=¥{cost:.4f}")
    print()
    print(controller.get_report())
    print()
    print(f"是否允许继续调用: {controller.can_call_api('deepseek-chat')}")
    print(f"单调用上限: ¥{SINGLE_CALL_MAX_YUAN}")
    print(f"月预算: ¥{MONTHLY_BUDGET_YUAN}")


if __name__ == "__main__":
    main()
