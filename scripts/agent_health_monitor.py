#!/usr/bin/env python3
"""
AI Agent 健康监控器
检查 8 大 Agent + 7 学习闭环 + 跨Agent编排 的运行状态，输出健康摘要。
被 feishu_daily_report.py 运维板块调用，也可独立运行。
"""
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"

# Agent 定义：名称 -> (报告目录, 预期周期天数)
AGENTS = {
    "SEO智能优化": ("seo", 8),
    "自我学习引擎": ("learning", 8),
    "收入分析引擎": ("revenue", 8),
    "转化优化Agent": ("conversion", 8),
    "内容智能优化": ("content", 2),
    "社媒智能优化": ("social", 2),
    "用户智能运营": ("user", 8),
    "网站健康巡检": ("site_health", 1),
}

CLOSED_LOOPS = {
    "SEO闭环": "seo_learning_closed_loop",
    "内容闭环": "content_learning_closed_loop",
    "社媒闭环": "social_learning_closed_loop",
    "转化闭环": "conversion_learning_closed_loop",
    "收入闭环": "revenue_learning_closed_loop",
    "用户闭环": "user_learning_closed_loop",
    "健康巡检闭环": "site_health_closed_loop",
}


def _latest_file_time(directory: str) -> datetime | None:
    """返回目录下最新文件的修改时间"""
    d = REPORTS / directory
    if not d.exists():
        return None
    files = [f for f in d.iterdir() if f.is_file()]
    if not files:
        return None
    return datetime.fromtimestamp(max(f.stat().st_mtime for f in files))


def _parse_unified_report() -> dict:
    """解析 latest_unified_report.md，提取运行概览"""
    path = REPORTS / "orchestration" / "latest_unified_report.md"
    result = {"generated_at": None, "total": 0, "success": 0, "failed": 0, "agents": {}}
    if not path.exists():
        return result
    text = path.read_text(encoding="utf-8")
    m = re.search(r"\*\*生成时间\*\*:\s*(.+)", text)
    if m:
        result["generated_at"] = m.group(1).strip()
    m = re.search(r"\*\*运行Agent数\*\*:\s*(\d+)", text)
    if m:
        result["total"] = int(m.group(1))
    m = re.search(r"\*\*成功\*\*:\s*(\d+)", text)
    if m:
        result["success"] = int(m.group(1))
    m = re.search(r"\*\*失败\*\*:\s*(\d+)", text)
    if m:
        result["failed"] = int(m.group(1))
    # 解析各Agent行
    for line in text.splitlines():
        m = re.match(r"\|\s*(.+?Agent|.+?引擎)\s*\|\s*(L\d)\s*\|\s*([✅❌])", line)
        if m:
            name = m.group(1).strip()
            result["agents"][name] = {"maturity": m.group(2), "status": m.group(3)}
    return result


def check_kill_switch() -> tuple[bool, str]:
    """检查 kill switch 状态（复用 ai_governance）"""
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        from ai_governance import check_kill_switch as _cks
        return _cks()
    except Exception:
        return True, "governance module unavailable"


def check_health() -> dict:
    """主入口：返回完整健康摘要"""
    now = datetime.now()
    unified = _parse_unified_report()
    kill_safe, kill_reason = check_kill_switch()

    agent_status = []
    healthy_count = 0
    stale_count = 0
    for name, (directory, max_age_days) in AGENTS.items():
        last_time = _latest_file_time(directory)
        if last_time is None:
            status = "❌ 无输出"
            age_days = None
            stale_count += 1
        else:
            age_days = (now - last_time).days
            if age_days <= max_age_days:
                status = "✅ 正常"
                healthy_count += 1
            else:
                status = f"⚠️ 过期({age_days}d)"
                stale_count += 1
        agent_status.append({
            "name": name,
            "status": status,
            "last_run": last_time.strftime("%Y-%m-%d") if last_time else "N/A",
            "max_age_days": max_age_days,
        })

    # 跨Agent学习
    cross_agent_time = _latest_file_time("cross_agent")
    cross_agent_status = "✅ 正常" if cross_agent_time and (now - cross_agent_time).days <= 2 else "⚠️ 过期"

    # 统一报告新鲜度
    unified_fresh = False
    if unified.get("generated_at"):
        try:
            gen_dt = datetime.strptime(unified["generated_at"], "%Y-%m-%d %H:%M:%S")
            unified_fresh = (now - gen_dt).days <= 8
        except ValueError:
            pass

    overall = "✅ 健康" if (kill_safe and stale_count <= 1 and unified_fresh) else ("⚠️ 注意" if stale_count <= 3 else "❌ 异常")

    return {
        "checked_at": now.strftime("%Y-%m-%d %H:%M"),
        "overall": overall,
        "kill_switch": "✅ 未激活" if kill_safe else f"🔴 已激活: {kill_reason}",
        "unified_report": {
            "generated_at": unified.get("generated_at", "N/A"),
            "success": unified.get("success", 0),
            "failed": unified.get("failed", 0),
            "fresh": "✅" if unified_fresh else "⚠️",
        },
        "agents": agent_status,
        "healthy_count": healthy_count,
        "stale_count": stale_count,
        "cross_agent_learning": cross_agent_status,
    }


def format_feishu_block(health: dict) -> str:
    """格式化为飞书日报运维板块的 Agent 健康子段"""
    lines = [
        f"**🤖 AI Agent 健康**: {health['overall']} | {health['healthy_count']}/{len(health['agents'])} 正常 | {health['kill_switch']}",
        "",
        "| Agent | 状态 | 最后运行 | 周期 |",
        "| --- | --- | --- | --- |",
    ]
    for a in health["agents"]:
        lines.append(f"| {a['name']} | {a['status']} | {a['last_run']} | {a['max_age_days']}d |")
    lines.append(f"| 跨Agent学习 | {health['cross_agent_learning']} | - | 日度 |")
    ur = health["unified_report"]
    lines.append(f"| 统一报告 | {ur['fresh']} 成功{ur['success']}/失败{ur['failed']} | {ur['generated_at'][:10] if ur['generated_at']!='N/A' else 'N/A'} | 周度 |")
    return "\n".join(lines)


if __name__ == "__main__":
    health = check_health()
    print(json.dumps(health, ensure_ascii=False, indent=2))
    print("\n=== Feishu block ===")
    print(format_feishu_block(health))
