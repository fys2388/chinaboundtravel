#!/usr/bin/env python3
"""
Closed Loop Audit — 闭环审计脚本

每日验证"检测→分配→执行→回写→看板"闭环完整性，
输出审计报告，发现断裂时触发告警。

审计维度：
1. 检测覆盖：问题是否被检测到
2. 分配覆盖：检测到的问题是否全部分配
3. 执行覆盖：分配的任务是否被执行
4. 回写覆盖：执行结果是否回写到原始文件
5. 看板一致：看板数据是否与原始数据一致

Usage:
    python scripts/closed_loop_audit.py [--date YYYY-MM-DD] [--notify]
"""
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from status_writeback import ISSUES_DIR, SITE_HEALTH_DIR, AGENT_TASKS_DIR, EXECUTION_LOG

BASE_DIR = Path(__file__).parent.parent
REPORTS_DIR = BASE_DIR / "reports"
AUDIT_DIR = REPORTS_DIR / "closed_loop_audit"
AUDIT_DIR.mkdir(parents=True, exist_ok=True)


def audit_detection(target_date: str) -> dict:
    """审计：问题检测环节"""
    result = {"stage": "detection", "status": "pass", "issues": [], "details": {}}

    # 检查 site_health 报告
    sh_file = SITE_HEALTH_DIR / f"site_health_{target_date}.json"
    if sh_file.exists():
        sh = json.loads(sh_file.read_text(encoding="utf-8"))
        total = sh.get("summary", {}).get("total_issues", 0)
        result["details"]["site_health_total"] = total
        result["details"]["site_health_file"] = sh_file.name
        if total == 0:
            result["issues"].append("site_health 检测到0个问题（可能检测未运行）")
            result["status"] = "warn"
    else:
        result["issues"].append(f"缺少 site_health_{target_date}.json")
        result["status"] = "fail"

    # 检查 daily_issues
    issues_file = ISSUES_DIR / f"site_health_issues_{target_date}.json"
    if issues_file.exists():
        issues = json.loads(issues_file.read_text(encoding="utf-8"))
        result["details"]["daily_issues_count"] = len(issues.get("issues", []))
    else:
        result["issues"].append(f"缺少 site_health_issues_{target_date}.json")
        result["status"] = "fail"

    return result


def audit_assignment(target_date: str) -> dict:
    """审计：问题分配环节"""
    result = {"stage": "assignment", "status": "pass", "issues": [], "details": {}}

    issues_file = ISSUES_DIR / f"site_health_issues_{target_date}.json"
    if not issues_file.exists():
        result["issues"].append("缺少问题文件，无法审计分配")
        result["status"] = "fail"
        return result

    issues = json.loads(issues_file.read_text(encoding="utf-8")).get("issues", [])
    total = len(issues)
    assigned = sum(1 for i in issues if i.get("assigned"))
    unassigned = total - assigned

    result["details"]["total"] = total
    result["details"]["assigned"] = assigned
    result["details"]["unassigned"] = unassigned
    result["details"]["assignment_rate"] = f"{assigned/total*100:.1f}%" if total > 0 else "N/A"

    if unassigned > 0:
        result["issues"].append(f"{unassigned}/{total} 个问题未分配")
        result["status"] = "fail"

    # 检查 agent 任务文件
    task_files = list(AGENT_TASKS_DIR.glob(f"task_{target_date}_*.json"))
    result["details"]["agent_tasks"] = len(task_files)
    if total > 0 and len(task_files) == 0:
        result["issues"].append("没有生成任何 Agent 任务文件")
        result["status"] = "fail"

    return result


def audit_execution(target_date: str) -> dict:
    """审计：任务执行环节"""
    result = {"stage": "execution", "status": "pass", "issues": [], "details": {}}

    task_files = list(AGENT_TASKS_DIR.glob(f"task_{target_date}_*.json"))
    if not task_files:
        result["issues"].append("没有 Agent 任务文件")
        result["status"] = "warn"
        return result

    total_tasks = len(task_files)
    completed = 0
    pending = 0
    failed = 0
    partial = 0
    total_issues = 0
    resolved_issues = 0

    for tf in task_files:
        task = json.loads(tf.read_text(encoding="utf-8"))
        status = task.get("status", "pending")
        total_issues += task.get("issue_count", 0)
        if status == "completed":
            completed += 1
            resolved_issues += task.get("issue_count", 0)
        elif status == "pending":
            pending += 1
        elif status == "failed":
            failed += 1
        elif status == "partial":
            partial += 1
            resolved_issues += task.get("execution", {}).get("resolved_count", 0)

    result["details"] = {
        "total_tasks": total_tasks,
        "completed": completed,
        "pending": pending,
        "failed": failed,
        "partial": partial,
        "total_issues": total_issues,
        "resolved_issues": resolved_issues,
    }

    if pending > 0:
        result["issues"].append(f"{pending}/{total_tasks} 个任务仍 pending（未执行）")
        result["status"] = "fail"
    if failed > 0:
        result["issues"].append(f"{failed} 个任务执行失败")
        result["status"] = "fail"

    return result


def audit_writeback(target_date: str) -> dict:
    """审计：状态回写环节"""
    result = {"stage": "writeback", "status": "pass", "issues": [], "details": {}}

    # 检查 site_health summary 是否更新
    sh_file = SITE_HEALTH_DIR / f"site_health_{target_date}.json"
    if sh_file.exists():
        sh = json.loads(sh_file.read_text(encoding="utf-8"))
        summary = sh.get("summary", {})
        need_manual = summary.get("need_manual", -1)
        resolved = summary.get("resolved", -1)
        result["details"]["need_manual"] = need_manual
        result["details"]["resolved"] = resolved

        # 如果有问题但 need_manual 等于总数，说明没有回写
        total = summary.get("total_issues", 0)
        if total > 0 and need_manual == total and resolved == 0:
            result["issues"].append("回写缺失：所有问题仍显示 need_manual，resolved=0")
            result["status"] = "fail"
    else:
        result["issues"].append("缺少 site_health 文件")
        result["status"] = "fail"

    # 检查 execution_log
    if EXECUTION_LOG.exists():
        log = json.loads(EXECUTION_LOG.read_text(encoding="utf-8"))
        result["details"]["execution_log_exists"] = True
        result["details"]["total_executions"] = log.get("total_executions", 0)
    else:
        result["details"]["execution_log_exists"] = False
        result["issues"].append("execution_log.json 不存在")
        result["status"] = "warn"

    return result


def audit_dashboard(target_date: str) -> dict:
    """审计：看板数据一致性"""
    result = {"stage": "dashboard", "status": "pass", "issues": [], "details": {}}

    dash_file = BASE_DIR / "ops-dashboard" / "dashboard_data.json"
    if not dash_file.exists():
        result["issues"].append("缺少 dashboard_data.json")
        result["status"] = "fail"
        return result

    dash = json.loads(dash_file.read_text(encoding="utf-8"))
    sh_dash = dash.get("site_health", {})
    pending_dash = sh_dash.get("pending", -1)

    # 对比原始数据
    sh_file = SITE_HEALTH_DIR / f"site_health_{target_date}.json"
    if sh_file.exists():
        sh = json.loads(sh_file.read_text(encoding="utf-8"))
        pending_actual = sh.get("summary", {}).get("need_manual", -1)
        result["details"]["dashboard_pending"] = pending_dash
        result["details"]["actual_pending"] = pending_actual

        if pending_dash != pending_actual:
            result["issues"].append(f"看板 pending({pending_dash}) 与实际({pending_actual}) 不一致")
            result["status"] = "warn"

    # 检查 GA4/GSC 数据
    ga4 = dash.get("metrics", {}).get("ga4_daily", {}).get("daily", [])
    gsc = dash.get("metrics", {}).get("gsc_daily", {}).get("daily", [])
    result["details"]["ga4_daily_days"] = len(ga4)
    result["details"]["gsc_daily_days"] = len(gsc)
    if len(ga4) == 0:
        result["issues"].append("看板 GA4 趋势数据为空")
        result["status"] = "warn"

    return result


def calculate_score(audits: list) -> dict:
    """计算闭环完整性评分"""
    weights = {
        "detection": 20,
        "assignment": 25,
        "execution": 25,
        "writeback": 20,
        "dashboard": 10,
    }
    score = 0
    max_score = 0
    stage_scores = {}

    for audit in audits:
        stage = audit["stage"]
        weight = weights.get(stage, 10)
        max_score += weight
        if audit["status"] == "pass":
            score += weight
            stage_scores[stage] = weight
        elif audit["status"] == "warn":
            score += weight * 0.5
            stage_scores[stage] = weight * 0.5
        else:
            stage_scores[stage] = 0

    return {
        "total_score": round(score, 1),
        "max_score": max_score,
        "percentage": round(score / max_score * 100, 1) if max_score > 0 else 0,
        "stage_scores": stage_scores,
        "grade": "A" if score >= max_score * 0.9 else "B" if score >= max_score * 0.7 else "C" if score >= max_score * 0.5 else "D",
    }


def main():
    parser = argparse.ArgumentParser(description="Closed Loop Audit")
    parser.add_argument("--date", type=str, default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--notify", action="store_true", help="发送飞书告警")
    args = parser.parse_args()

    target_date = args.date
    print("=" * 60)
    print(f"Closed Loop Audit — 闭环审计")
    print(f"日期: {target_date}")
    print(f"时间: {datetime.now().isoformat()}")
    print("=" * 60)

    # 执行各环节审计
    audits = [
        audit_detection(target_date),
        audit_assignment(target_date),
        audit_execution(target_date),
        audit_writeback(target_date),
        audit_dashboard(target_date),
    ]

    # 输出审计结果
    all_issues = []
    for audit in audits:
        status_icon = {"pass": "✅", "warn": "⚠️", "fail": "🔴"}.get(audit["status"], "❓")
        print(f"\n{status_icon} {audit['stage'].upper()}")
        for k, v in audit["details"].items():
            print(f"  {k}: {v}")
        if audit["issues"]:
            for issue in audit["issues"]:
                print(f"  ⚠️  {issue}")
                all_issues.append(f"[{audit['stage']}] {issue}")

    # 计算评分
    score = calculate_score(audits)
    print(f"\n{'='*60}")
    print(f"闭环完整性评分: {score['total_score']}/{score['max_score']} ({score['percentage']}%) — 等级 {score['grade']}")
    print(f"各环节得分: {score['stage_scores']}")
    print(f"发现问题: {len(all_issues)} 个")
    for issue in all_issues:
        print(f"  - {issue}")

    # 保存审计报告
    report = {
        "audit_date": target_date,
        "audited_at": datetime.now().isoformat(),
        "score": score,
        "audits": audits,
        "all_issues": all_issues,
    }
    report_file = AUDIT_DIR / f"audit_{target_date}.json"
    report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n审计报告已保存: {report_file}")

    # 如果有严重问题且开启通知，发送告警
    if args.notify and any(a["status"] == "fail" for a in audits):
        print("\n⚠️  闭环断裂，建议发送告警")
        # 这里可以调用飞书 webhook

    print("=" * 60)
    return 0 if score["percentage"] >= 70 else 1


if __name__ == "__main__":
    sys.exit(main())
