#!/usr/bin/env python3
"""
Daily Issue Router - 日报运营问题→Agent任务自动分配机制

流程：
1. 扫描各类报告文件，提取运营问题和告警（🟡🟠🔴）
2. 按问题类型、严重程度、影响范围分类
3. 路由到对应 Agent（user/revenue/seo/content/social/ops）
4. 生成带具体问题描述的 Agent 任务文件
5. 记录分配历史和跟进状态
6. 输出分配摘要（可用于飞书通知）

与 auto_error_router.py 的区别：
- auto_error_router: 处理工作流/构建/部署的技术错误
- daily_issue_router: 处理日报中的运营/业务问题（流量、转化、内容、社媒等）

Usage:
  python scripts/daily_issue_router.py [--dry-run] [--date YYYY-MM-DD] [--notify]
"""
import os
import sys
import json
import re
from datetime import datetime, date
from pathlib import Path
from typing import Optional

# Add scripts dir to path
sys.path.insert(0, str(Path(__file__).parent))

BASE_DIR = Path(__file__).parent.parent
REPORTS_DIR = BASE_DIR / "reports"
ISSUES_DIR = BASE_DIR / "reports" / "daily_issues"
ISSUES_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# 问题类型→Agent 路由映射
# ============================================================
ISSUE_ROUTES = {
    # 流量与用户行为
    "bounce_rate": {
        "agent": "user",
        "severity": "medium",
        "description": "跳出率偏高，需分析用户行为和页面体验",
        "action": "analyze_and_recommend",
    },
    "engagement_low": {
        "agent": "user",
        "severity": "medium",
        "description": "互动率/平均时长偏低，需优化内容粘性",
        "action": "analyze_and_recommend",
    },
    "traffic_decline": {
        "agent": "user",
        "severity": "high",
        "description": "流量下降，需诊断原因并制定恢复策略",
        "action": "diagnose_and_plan",
    },
    "zero_organic_search": {
        "agent": "seo",
        "severity": "high",
        "description": "自然搜索流量为0或极低，需诊断SEO问题",
        "action": "diagnose_and_fix",
    },
    # SEO与搜索
    "no_search_impressions": {
        "agent": "seo",
        "severity": "medium",
        "description": "搜索曝光为0，需检查索引状态和排名",
        "action": "diagnose_and_submit",
    },
    "low_ctr": {
        "agent": "seo",
        "severity": "medium",
        "description": "搜索点击率偏低，需优化标题和描述",
        "action": "optimize_metadata",
    },
    "index_errors": {
        "agent": "seo",
        "severity": "high",
        "description": "存在索引错误，需修复并重新提交",
        "action": "fix_and_resubmit",
    },
    "waiting_recrawl": {
        "agent": "seo",
        "severity": "low",
        "description": "实验等待重爬，需触发GSC重新抓取",
        "action": "trigger_recrawl",
    },
    # 联盟与收入
    "affiliate_zero_conversion": {
        "agent": "revenue",
        "severity": "medium",
        "description": "联盟有点击但0转化，需分析转化漏斗和CTA",
        "action": "analyze_funnel_and_optimize",
    },
    "zero_revenue": {
        "agent": "revenue",
        "severity": "high",
        "description": "收入为0，需诊断联盟链路和转化路径",
        "action": "diagnose_and_optimize",
    },
    "affiliate_tracking_broken": {
        "agent": "revenue",
        "severity": "high",
        "description": "联盟追踪异常，需验证链接和API连接",
        "action": "verify_and_fix",
    },
    # 内容质量
    "placeholder_remaining": {
        "agent": "content",
        "severity": "high",
        "description": "存在占位符残留文章，需修复或下线",
        "action": "fix_or_retire",
    },
    "empty_links": {
        "agent": "content",
        "severity": "medium",
        "description": "存在空链接，需修复或移除",
        "action": "fix_links",
    },
    "missing_alt_text": {
        "agent": "content",
        "severity": "low",
        "description": "图片缺少alt文本，需补充",
        "action": "add_alt_text",
    },
    "thin_content": {
        "agent": "content",
        "severity": "medium",
        "description": "内容单薄，需扩写深度",
        "action": "expand_content",
    },
    # 社媒
    "social_zero_engagement": {
        "agent": "social",
        "severity": "medium",
        "description": "社媒互动为0，需优化内容策略和发布时间",
        "action": "analyze_and_optimize",
    },
    "social_no_traffic": {
        "agent": "social",
        "severity": "high",
        "description": "社媒引流为0，需检查链接和CTA策略",
        "action": "audit_links_and_cta",
    },
    "social_zero_growth": {
        "agent": "social",
        "severity": "low",
        "description": "社媒粉丝零增长，需优化内容和互动策略",
        "action": "optimize_growth",
    },
    # 邮件订阅
    "email_zero_subscribers": {
        "agent": "user",
        "severity": "medium",
        "description": "邮件订阅零增长，需优化Lead Magnet和CTA覆盖",
        "action": "audit_and_optimize",
    },
    # 系统与运维
    "workflow_failure": {
        "agent": "ops",
        "severity": "high",
        "description": "工作流运行失败，需排查并修复",
        "action": "diagnose_and_fix",
    },
    "site_down": {
        "agent": "ops",
        "severity": "critical",
        "description": "网站不可用，需立即排查",
        "action": "emergency_fix",
    },
    "slow_response": {
        "agent": "ops",
        "severity": "medium",
        "description": "网站响应慢，需优化性能",
        "action": "optimize_performance",
    },
    # 实验
    "experiment_insufficient_sample": {
        "agent": "conversion",
        "severity": "low",
        "description": "实验样本不足，需延长观察期",
        "action": "extend_observation",
    },
    "experiment_frozen": {
        "agent": "conversion",
        "severity": "low",
        "description": "实验处于冻结期，禁止修改变量",
        "action": "maintain_freeze",
    },
}

# Agent 显示名称
AGENT_NAMES = {
    "user": "User Intelligence Agent (用户智能运营)",
    "revenue": "Revenue Analytics Engine (收入分析引擎)",
    "seo": "SEO Intelligent Agent (SEO智能优化)",
    "content": "Content Intelligence Agent (内容智能优化)",
    "social": "Social Intelligence Agent (社媒智能优化)",
    "ops": "Growth Orchestrator / Ops (增长编排/运维)",
    "conversion": "Conversion Optimization Agent (转化优化Agent)",
}

# 严重程度权重
SEVERITY_WEIGHT = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
}

SEVERITY_EMOJI = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🟡",
    "low": "🟢",
}


class DailyIssueRouter:
    """日报运营问题→Agent任务分配器"""

    def __init__(self, target_date: Optional[str] = None, dry_run: bool = False):
        self.target_date = target_date or date.today().isoformat()
        self.dry_run = dry_run
        self.issues = []
        self.assignments = []
        self.router_version = "1.0"

    def scan_reports(self) -> list:
        """扫描各类报告文件，提取运营问题"""
        issues = []

        # 1. 扫描社媒日报
        issues.extend(self._scan_social_reports())

        # 2. 扫描SEO报告
        issues.extend(self._scan_seo_reports())

        # 3. 扫描内容质量报告
        issues.extend(self._scan_content_reports())

        # 4. 扫描收入/联盟报告
        issues.extend(self._scan_revenue_reports())

        # 5. 扫描用户/流量报告
        issues.extend(self._scan_user_reports())

        self.issues = issues
        return issues

    def _scan_social_reports(self) -> list:
        """扫描社媒报告"""
        issues = []
        social_dir = REPORTS_DIR / "social"

        # 检查最新的社媒日报
        daily_files = sorted(social_dir.glob("social_daily_*.json"), reverse=True)
        if daily_files:
            latest = daily_files[0]
            try:
                data = json.loads(latest.read_text(encoding="utf-8"))
                total_clicks = data.get("total_clicks", 0)
                total_impressions = data.get("total_impressions", 0)
                total_uv = data.get("total_uv", 0)

                if total_impressions == 0 and data.get("total_published", 0) > 0:
                    issues.append(self._create_issue(
                        "social_zero_engagement",
                        f"社媒已发布{data.get('total_published', 0)}条但曝光为0，可能是Buffer API数据未接通",
                        source_file=str(latest.name),
                    ))
                if total_clicks == 0 and total_impressions > 0:
                    issues.append(self._create_issue(
                        "social_no_traffic",
                        f"社媒曝光{total_impressions}但点击为0，需检查帖子链接和CTA",
                        source_file=str(latest.name),
                    ))
            except (json.JSONDecodeError, KeyError):
                pass

        # 检查社媒审计报告
        audit_file = social_dir / "social_audit_report.json"
        if audit_file.exists():
            try:
                audit = json.loads(audit_file.read_text(encoding="utf-8"))
                if isinstance(audit, dict):
                    for key in ["issues", "problems", "warnings"]:
                        if key in audit and isinstance(audit[key], list):
                            for item in audit[key][:5]:
                                if isinstance(item, dict):
                                    issues.append(self._create_issue(
                                        "social_zero_engagement",
                                        item.get("description", str(item)),
                                        source_file="social_audit_report.json",
                                    ))
            except (json.JSONDecodeError, KeyError):
                pass

        return issues

    def _scan_seo_reports(self) -> list:
        """扫描SEO报告"""
        issues = []
        seo_dir = REPORTS_DIR / "seo"

        # 检查索引覆盖率
        index_file = seo_dir / "INDEX_COVERAGE_BASELINE.md"
        # 检查URL检查结果中的错误
        url_inspect = seo_dir / "url_inspection_results.json"
        if url_inspect.exists():
            try:
                data = json.loads(url_inspect.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    errors = data.get("errors", [])
                    if errors and isinstance(errors, list):
                        issues.append(self._create_issue(
                            "index_errors",
                            f"发现{len(errors)}个索引错误需修复",
                            source_file="url_inspection_results.json",
                        ))
            except (json.JSONDecodeError, KeyError):
                pass

        # 检查等待重爬的实验
        for pattern in ["GROWTH07*", "*WAITING*"]:
            for f in seo_dir.glob(pattern):
                if f.is_file():
                    content = f.read_text(encoding="utf-8", errors="ignore")
                    if "WAITING_RECRAWL" in content or "waiting_recrawl" in content:
                        issues.append(self._create_issue(
                            "waiting_recrawl",
                            f"实验 {f.stem} 等待重爬，需触发GSC重新抓取",
                            source_file=f.name,
                        ))
                        break

        return issues

    def _scan_content_reports(self) -> list:
        """扫描内容质量报告"""
        issues = []
        content_dir = REPORTS_DIR / "content"

        # 检查内容审计报告
        for audit_file in content_dir.glob("*audit*.json"):
            try:
                data = json.loads(audit_file.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    placeholders = data.get("placeholders", data.get("placeholder_count", 0))
                    if isinstance(placeholders, int) and placeholders > 0:
                        issues.append(self._create_issue(
                            "placeholder_remaining",
                            f"发现{placeholders}篇占位符残留文章",
                            source_file=audit_file.name,
                        ))
                    empty_links = data.get("empty_links", data.get("broken_links", 0))
                    if isinstance(empty_links, int) and empty_links > 0:
                        issues.append(self._create_issue(
                            "empty_links",
                            f"发现{empty_links}个空链接/坏链接",
                            source_file=audit_file.name,
                        ))
            except (json.JSONDecodeError, KeyError):
                pass

        return issues

    def _scan_revenue_reports(self) -> list:
        """扫描收入/联盟报告"""
        issues = []
        revenue_dir = REPORTS_DIR / "revenue"

        # 检查联盟漏斗审计
        for f in revenue_dir.glob("*funnel*"):
            if f.is_file():
                content = f.read_text(encoding="utf-8", errors="ignore")
                if "0" in content and ("conversion" in content.lower() or "转化" in content):
                    issues.append(self._create_issue(
                        "affiliate_zero_conversion",
                        f"联盟转化漏斗存在0转化环节，需分析 {f.name}",
                        source_file=f.name,
                    ))
                    break

        return issues

    def _scan_user_reports(self) -> list:
        """扫描用户/流量报告"""
        issues = []
        user_dir = REPORTS_DIR / "user"

        # 检查用户行为报告
        for f in user_dir.glob("*behavior*"):
            if f.is_file():
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    if isinstance(data, dict):
                        bounce_rate = data.get("bounce_rate", 0)
                        if isinstance(bounce_rate, (int, float)) and bounce_rate > 0.8:
                            issues.append(self._create_issue(
                                "bounce_rate",
                                f"跳出率{bounce_rate:.1%}偏高（>80%）",
                                source_file=f.name,
                            ))
                except (json.JSONDecodeError, KeyError):
                    pass

        return issues

    def _create_issue(self, issue_type: str, description: str, source_file: str = "") -> dict:
        """创建问题对象"""
        route = ISSUE_ROUTES.get(issue_type, ISSUE_ROUTES.get("workflow_failure"))
        return {
            "id": f"issue_{len(self.issues) + 1:03d}",
            "type": issue_type,
            "description": description,
            "severity": route.get("severity", "medium"),
            "agent": route.get("agent", "ops"),
            "action": route.get("action", "analyze"),
            "source_file": source_file,
            "detected_at": datetime.now().isoformat(),
            "status": "new",
            "assigned": False,
        }

    def assign_issues(self) -> list:
        """将问题分配给对应 Agent"""
        assignments = []

        # 按 Agent 分组
        by_agent = {}
        for issue in self.issues:
            agent = issue["agent"]
            if agent not in by_agent:
                by_agent[agent] = []
            by_agent[agent].append(issue)

        # 为每个 Agent 生成任务
        for agent, agent_issues in by_agent.items():
            # 按严重程度排序
            agent_issues.sort(
                key=lambda x: SEVERITY_WEIGHT.get(x["severity"], 0),
                reverse=True,
            )

            task = {
                "agent": agent,
                "agent_name": AGENT_NAMES.get(agent, agent),
                "task_id": f"task_{self.target_date}_{agent}",
                "created_at": datetime.now().isoformat(),
                "target_date": self.target_date,
                "issue_count": len(agent_issues),
                "severity_summary": self._summarize_severity(agent_issues),
                "issues": agent_issues,
                "priority_issue": agent_issues[0] if agent_issues else None,
                "expected_actions": list(set(i["action"] for i in agent_issues)),
                "status": "pending",
            }
            assignments.append(task)

            # 标记问题已分配
            for issue in agent_issues:
                issue["assigned"] = True
                issue["assigned_to"] = agent

        # 按问题数量排序
        assignments.sort(key=lambda x: x["issue_count"], reverse=True)
        self.assignments = assignments
        return assignments

    def _summarize_severity(self, issues: list) -> dict:
        """汇总严重程度"""
        summary = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for issue in issues:
            sev = issue.get("severity", "medium")
            if sev in summary:
                summary[sev] += 1
        return summary

    def save_assignments(self):
        """保存分配结果"""
        if self.dry_run:
            print("[DRY RUN] 跳过保存")
            return

        # 保存完整分配结果
        output = {
            "router_version": self.router_version,
            "generated_at": datetime.now().isoformat(),
            "target_date": self.target_date,
            "total_issues": len(self.issues),
            "total_assignments": len(self.assignments),
            "issues": self.issues,
            "assignments": self.assignments,
        }

        output_file = ISSUES_DIR / f"daily_issues_{self.target_date}.json"
        output_file.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"✅ 分配结果已保存: {output_file}")

        # 为每个 Agent 保存独立任务文件
        tasks_dir = ISSUES_DIR / "agent_tasks"
        tasks_dir.mkdir(exist_ok=True)
        for task in self.assignments:
            task_file = tasks_dir / f"{task['task_id']}.json"
            task_file.write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")

        print(f"✅ Agent任务文件已保存到: {tasks_dir}")

    def generate_summary(self) -> str:
        """生成分配摘要（用于飞书通知）"""
        lines = []
        lines.append(f"📋 日报问题分配摘要 | {self.target_date}")
        lines.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"发现问题: {len(self.issues)} 个 | 分配Agent: {len(self.assignments)} 个")
        lines.append("")

        for task in self.assignments:
            sev = task["severity_summary"]
            sev_parts = []
            for level in ["critical", "high", "medium", "low"]:
                if sev[level] > 0:
                    sev_parts.append(f"{SEVERITY_EMOJI[level]}{sev[level]}")
            sev_str = " ".join(sev_parts)

            lines.append(f"🎯 {task['agent_name']}")
            lines.append(f"   问题数: {task['issue_count']} | {sev_str}")
            if task["priority_issue"]:
                p = task["priority_issue"]
                lines.append(f"   优先级: {SEVERITY_EMOJI.get(p['severity'], '')} {p['description'][:60]}")
            lines.append(f"   预期动作: {', '.join(task['expected_actions'])}")
            lines.append("")

        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("💡 Agent将基于这些任务进行分析和优化建议")
        lines.append("⚠️ 低样本/数据不足时，Agent只生成诊断报告，不自动修改生产")

        return "\n".join(lines)

    def run(self) -> dict:
        """运行完整分配流程"""
        print(f"🔍 开始扫描日报问题 (目标日期: {self.target_date})")

        # 1. 扫描问题
        self.scan_reports()
        print(f"   发现 {len(self.issues)} 个问题")

        # 2. 分配问题
        self.assign_issues()
        print(f"   分配给 {len(self.assignments)} 个 Agent")

        # 3. 保存结果
        self.save_assignments()

        # 4. 生成摘要
        summary = self.generate_summary()
        print("\n" + summary)

        return {
            "issues": self.issues,
            "assignments": self.assignments,
            "summary": summary,
        }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="日报运营问题→Agent任务自动分配")
    parser.add_argument("--dry-run", action="store_true", help="只扫描不保存")
    parser.add_argument("--date", type=str, default=None, help="目标日期 (YYYY-MM-DD)")
    parser.add_argument("--notify", action="store_true", help="发送飞书通知")
    args = parser.parse_args()

    router = DailyIssueRouter(target_date=args.date, dry_run=args.dry_run)
    result = router.run()

    # 发送飞书通知
    if args.notify and not args.dry_run:
        try:
            from send_feishu_notification import send_feishu_message
            send_feishu_message(result["summary"])
            print("\n✅ 飞书通知已发送")
        except Exception as e:
            print(f"\n⚠️ 飞书通知发送失败: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
