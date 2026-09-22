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
import hashlib
from datetime import datetime, date
from pathlib import Path
from typing import Optional

# Add scripts dir to path
sys.path.insert(0, str(Path(__file__).parent))
from agent_task_queue import enqueue_issues

try:
    # 能力矩阵的单一事实源在 agent_task_executor 里。失败时退回本文件内的
    # 兜底集合，避免执行器侧改动导致路由整体崩溃。
    from agent_task_executor import AUTO_FIXABLE_TYPES
except Exception:  # pragma: no cover - 兜底路径
    AUTO_FIXABLE_TYPES = frozenset({
        "ai_forbidden_word",
        "title_too_long",
        "meta_description_too_short",
        "workflow_missing_guard",
    })

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
    # Site Health 巡检问题
    "ai_forbidden_word": {
        "agent": "content",
        "severity": "medium",
        "description": "AI禁用词检测（Best/Cheapest/Guaranteed等），需保守改写",
        "action": "safe_normalize",
    },
    "persona_violation": {
        "agent": "content",
        "severity": "high",
        "description": "Persona违规（I lived in China/My wife/As a local等），需清理编辑视角",
        "action": "persona_cleanup",
    },
    "content_placeholder": {
        "agent": "content",
        "severity": "high",
        "description": "内容占位符残留（Review needed/TODO等），需补全或移除",
        "action": "fix_placeholder",
    },
    "image_missing_alt": {
        "agent": "content",
        "severity": "medium",
        "description": "图片缺少alt属性，需补充描述性文本",
        "action": "add_alt_text",
    },
    "title_too_short": {
        "agent": "seo",
        "severity": "medium",
        "description": "Title过短（<20字符），需扩展关键词",
        "action": "optimize_title",
    },
    "title_too_long": {
        "agent": "seo",
        "severity": "medium",
        "description": "Title过长（>65字符），需精简",
        "action": "optimize_title",
    },
    "meta_description_too_long": {
        "agent": "seo",
        "severity": "low",
        "description": "Meta Description过长（>165字符），需精简",
        "action": "optimize_meta",
    },
    "meta_description_too_short": {
        "agent": "seo",
        "severity": "low",
        "description": "Meta Description过短（<70字符），需扩展",
        "action": "optimize_meta",
    },
    "site_unreachable": {
        "agent": "site_health",
        "severity": "critical",
        "description": "网站无法访问（可能是本地网络误报），需核实线上状态",
        "action": "verify_and_alert",
    },
    "ssl_check_failed": {
        "agent": "site_health",
        "severity": "high",
        "description": "SSL证书检查失败（可能是本地网络误报），需核实线上状态",
        "action": "verify_and_alert",
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
    "social_analytics_unavailable": {
        "agent": "ops",
        "severity": "high",
        "description": "社媒分析数据不可用，需修复Buffer Token、权限或指标拉取链路",
        "action": "restore_social_analytics",
    },
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
    "frontend": "Frontend Agent (页面/视觉/响应式)",
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


def classify_social_metrics(data: dict) -> Optional[str]:
    """Return the social issue implied by a daily report without guessing.

    Zero impressions are only an engagement problem when analytics provenance
    is explicitly available. Legacy or unavailable snapshots route to Ops.
    """
    published = int(data.get("total_published", 0) or 0)
    if published <= 0:
        return None
    if str(data.get("analytics_status", "unavailable")).lower() != "ok":
        return "social_analytics_unavailable"
    impressions = int(data.get("total_impressions", 0) or 0)
    clicks = int(data.get("total_clicks", 0) or 0)
    if impressions <= 0:
        return "social_zero_engagement"
    if clicks <= 0:
        return "social_no_traffic"
    return None


class DailyIssueRouter:
    """日报运营问题→Agent任务分配器"""

    def __init__(self, target_date: Optional[str] = None, dry_run: bool = False):
        self.target_date = target_date or date.today().isoformat()
        self.dry_run = dry_run
        self.issues = []
        self.manual_issues = []
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

        # 6. 扫描Site Health巡检报告
        issues.extend(self._scan_site_health_reports())

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
                issue_type = classify_social_metrics(data)
                published = int(data.get("total_published", 0) or 0)
                if issue_type == "social_analytics_unavailable":
                    reason = data.get("analytics_reason") or "Buffer分析数据未接通"
                    issues.append(self._create_issue(
                        issue_type,
                        f"社媒已发布{published}条，但分析指标不可用，不能据此判定零互动（{reason}）",
                        source_file=str(latest.name),
                    ))
                elif issue_type == "social_zero_engagement":
                    issues.append(self._create_issue(
                        issue_type,
                        f"分析数据可用，社媒已发布{published}条但曝光为0，需检查发布与指标归属",
                        source_file=str(latest.name),
                    ))
                elif issue_type == "social_no_traffic":
                    issues.append(self._create_issue(
                        issue_type,
                        f"社媒曝光{data.get('total_impressions', 0)}但点击为0，需检查帖子链接和CTA",
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
                        # 口径不统一：user_behavior_audit.json 把 bounce_rate 嵌在
                        # behavior_analysis 下且存小数(0.13)；部分 learning 产物存百分数(75)。
                        # 同时兼容两种结构，并统一归一化为小数后再判断。
                        raw_bounce = data.get("bounce_rate")
                        if raw_bounce is None and isinstance(data.get("behavior_analysis"), dict):
                            raw_bounce = data["behavior_analysis"].get("bounce_rate")
                        if isinstance(raw_bounce, (int, float)):
                            raw_bounce = float(raw_bounce)
                            bounce_rate = raw_bounce / 100.0 if raw_bounce > 1.5 else raw_bounce
                            if bounce_rate > 0.8:
                                issues.append(self._create_issue(
                                    "bounce_rate",
                                    f"跳出率{bounce_rate:.1%}偏高（>80%）",
                                    source_file=f.name,
                                ))
                except (json.JSONDecodeError, KeyError):
                    pass

        return issues

    def _scan_site_health_reports(self) -> list:
        """扫描Site Health巡检报告，提取未自动修复的问题"""
        issues = []
        sh_dir = ISSUES_DIR

        # 优先读取今天的检测文件，再读取audit followup文件
        target_file = sh_dir / f"site_health_issues_{self.target_date}.json"
        files_to_scan = []
        if target_file.exists():
            files_to_scan.append(target_file)
        audit_files = sorted(sh_dir.glob("site_health_issues_audit_*.json"), reverse=True)
        files_to_scan.extend(audit_files[:2])

        resolved_statuses = {"resolved", "fixed", "false_positive", "closed"}
        for latest in files_to_scan:
            try:
                data = json.loads(latest.read_text(encoding="utf-8"))
                sh_issues = data.get("issues", [])
                before_count = len(issues)
                for item in sh_issues:
                    issue_type = item.get("type", "unknown")
                    message = item.get("message", "")
                    file_ref = item.get("file", "")
                    if str(item.get("status", "")).lower() in resolved_statuses:
                        continue
                    if issue_type in ("site_unreachable", "ssl_check_failed"):
                        message = message + "（可能是本地网络误报，需核实线上状态）"
                    issue = self._create_issue(
                        issue_type,
                        message,
                        source_file=str(latest.name),
                    )
                    if file_ref:
                        issue["file"] = file_ref
                    if item.get("suggested_title"):
                        issue["suggested_title"] = item["suggested_title"]
                    issues.append(issue)
                print(
                    "  [Site Health] 从 "
                    + latest.name
                    + " 提取 "
                    + str(len(issues) - before_count)
                    + " 个开放问题（共 "
                    + str(len(sh_issues))
                    + " 条记录）"
                )
            except (json.JSONDecodeError, KeyError) as e:
                print("  [Site Health] 解析 " + latest.name + " 失败: " + str(e))
        return issues


    def _create_issue(self, issue_type: str, description: str, source_file: str = "") -> dict:
        """创建问题对象"""
        route = ISSUE_ROUTES.get(issue_type, ISSUE_ROUTES.get("workflow_failure"))
        seed = f"{issue_type}|{description}|{source_file}"
        issue_id = "issue_" + hashlib.sha1(
            seed.encode("utf-8")
        ).hexdigest()[:12]
        return {
            "id": issue_id,
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
        """将问题分配给对应 Agent。

        分流（AUDIT-OPS-002 方案 A）：只有 executor 能力矩阵内（AUTO_FIXABLE_TYPES）的
        type 才会生成 agent 任务；其余进人工队列文件，不再每天被重派。
        理由见 agent_task_executor.AUTO_FIXABLE_TYPES 的注释。
        """
        assignments = []

        # 按「能否自动修」分流，再按 Agent 分组
        auto_issues = []
        self.manual_issues = []
        for issue in self.issues:
            issue.setdefault("auto_fixable", issue["type"] in AUTO_FIXABLE_TYPES)
            if issue["auto_fixable"]:
                auto_issues.append(issue)
            else:
                self.manual_issues.append(issue)

        by_agent = {}
        for issue in auto_issues:
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

        # Pass one complete snapshot so cross-agent cleanup cannot clear
        # sibling tasks created by the same router run.
        all_issues = [
            issue
            for task in self.assignments
            for issue in task.get("issues", [])
        ]
        enqueue_issues(
            all_issues,
            task_source="daily_issue_router",
            target_date=self.target_date,
        )

        print(f"✅ Agent任务文件已合并到: {ISSUES_DIR / 'agent_tasks'}")

        # 人工队列：不在 executor 能力矩阵内的 type 不再派 agent 任务，
        # 单独落盘以免静默丢失，也避免每天重派同一批 need_manual。
        self._save_manual_queue()

        # 回写分配状态到原始问题文件（site_health_issues等）
        self._writeback_assigned_status()

    def _save_manual_queue(self):
        """保存无法自动修复的问题到人工队列（与 agent_tasks 分离）。

        这是 AUDIT-OPS-002 方案 A 的核心：让「派不出去」变成显式的、
        一次性的输出，而不是每天重复的 need_manual 轮次。
        """
        if not self.manual_issues:
            return

        by_agent = {}
        for issue in self.manual_issues:
            by_agent.setdefault(issue.get("agent", "ops"), []).append(issue)

        queue = {
            "queue_type": "manual",
            "reason": "issue type 不在 agent_task_executor.AUTO_FIXABLE_TYPES 内，"
                      "executor 会返回 need_manual。改为一次性落盘，不再每天重派 agent 任务。",
            "generated_at": datetime.now().isoformat(),
            "target_date": self.target_date,
            "issue_count": len(self.manual_issues),
            "by_agent": {
                agent: {
                    "count": len(issues),
                    "types": sorted({i.get("type") for i in issues}),
                }
                for agent, issues in sorted(by_agent.items())
            },
            "issues": self.manual_issues,
        }

        output_file = ISSUES_DIR / f"manual_queue_{self.target_date}.json"
        output_file.write_text(
            json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(
            f"📋 人工队列已保存: {output_file.name}（{len(self.manual_issues)} 个，"
            f"{len(by_agent)} 个 agent）—— 不再派 agent 任务"
        )

    def _writeback_assigned_status(self):
        """把已分配状态回写到原始问题来源文件，确保看板显示正确"""
        try:
            # 按来源文件分组
            by_source = {}
            for issue in self.issues:
                src = issue.get("source_file", "")
                if src and src.startswith("site_health_issues_"):
                    by_source.setdefault(src, []).append(issue)

            for src_file, src_issues in by_source.items():
                src_path = ISSUES_DIR / src_file
                if not src_path.exists():
                    continue
                try:
                    data = json.loads(src_path.read_text(encoding="utf-8"))
                    # 建立 type -> assigned issue 映射
                    assigned_map = {}
                    for ai in src_issues:
                        if ai.get("assigned"):
                            assigned_map[ai["type"]] = ai

                    updated = 0
                    for orig in data.get("issues", []):
                        if orig["type"] in assigned_map and not orig.get("assigned"):
                            ai = assigned_map[orig["type"]]
                            orig["assigned"] = True
                            orig["assigned_to"] = ai.get("assigned_to", ai.get("agent", ""))
                            orig["assigned_at"] = datetime.now().isoformat()
                            orig["status"] = "assigned"
                            updated += 1

                    # 更新汇总
                    if "pending" in data:
                        data["pending"] = sum(
                            1 for i in data.get("issues", [])
                            if i.get("status") in ("new", "", None) or not i.get("assigned")
                        )

                    src_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                    if updated > 0:
                        print(f"  ↩️ 回写 {src_file}: {updated} 个问题标记为已分配")
                except Exception as e:
                    print(f"  ⚠️ 回写 {src_file} 失败: {e}")
        except Exception as e:
            print(f"  ⚠️ 回写分配状态失败: {e}")

    def generate_summary(self) -> str:
        """生成分配摘要（用于飞书通知）"""
        lines = []
        lines.append(f"📋 日报问题分配摘要 | {self.target_date}")
        lines.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        auto_count = len(self.issues) - len(self.manual_issues)
        lines.append(
            f"发现问题: {len(self.issues)} 个 | "
            f"自动修复: {auto_count} 个 | 人工队列: {len(self.manual_issues)} 个"
        )
        lines.append(f"分配Agent: {len(self.assignments)} 个")
        lines.append("")
        if self.manual_issues:
            types = sorted({i.get("type") for i in self.manual_issues})
            lines.append(
                f"📋 人工队列 {len(self.manual_issues)} 个（不在 executor 能力矩阵内，"
                f"不派 agent 任务，见 manual_queue_{self.target_date}.json）："
            )
            lines.append(f"   {', '.join(types)}")
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

    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(errors="replace")
            except (OSError, ValueError):
                pass

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
