#!/usr/bin/env python3
"""
Auto Error Router - 工作流失败自动处理闭环
流程：拉取失败日志 → 错误分类 → 自动修复/告警/分配Agent → 重试 → 记录知识库
"""
import os
import sys
import json
import re
import subprocess
import urllib.request
import urllib.error
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from error_handler import ErrorHandler
from status_writeback import writeback_workflow
from agent_task_queue import enqueue_issues

REPO = os.environ.get("GITHUB_REPOSITORY", "fys2388/chinaboundtravel")
FEISHU_WEBHOOK = os.environ.get("FEISHU_WEBHOOK_URL", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

ERROR_ROUTES = {
    "content_quality_p0": {"action": "alert_with_fix_guide", "agent": "content", "retry": False},
    "mojibake_detected": {"action": "alert_with_fix_guide", "agent": "content", "retry": False},
    "fact_guard_failed": {"action": "alert_with_fix_guide", "agent": "content", "retry": False},
    "brand_violation": {"action": "alert_with_fix_guide", "agent": "content", "retry": False},
    "content_id_error": {"action": "alert_with_fix_guide", "agent": "content", "retry": False},
    "content_audit_script_error": {"action": "alert_with_fix_guide", "agent": "content", "retry": False},
    "visual_quality_failed": {"action": "alert_with_fix_guide", "agent": "frontend", "retry": False},
    "predeploy_quality_failed": {"action": "alert_with_fix_guide", "agent": "frontend", "retry": False},
    "shortcode_missing": {"action": "auto_fix", "agent": "content", "retry": True},
    "encoding_corruption": {"action": "auto_fix", "agent": "content", "retry": True},
    "yaml_parsing": {"action": "auto_fix", "agent": "content", "retry": True},
    "build_timeout": {"action": "alert_only", "agent": "content", "retry": False},
    "git_push_failed": {"action": "alert_only", "agent": "ops", "retry": False},
    "authentication_error": {"action": "alert_with_fix_guide", "agent": "ops", "retry": False},
    "dependency_missing": {"action": "alert_with_fix_guide", "agent": "ops", "retry": True},
    "module_not_found": {"action": "alert_with_fix_guide", "agent": "ops", "retry": True},
    "network_error": {"action": "retry_only", "agent": "ops", "retry": True},
    "permission_denied": {"action": "alert_with_fix_guide", "agent": "ops", "retry": False},
    "unknown": {"action": "create_issue", "agent": "orchestrator", "retry": False},
}

AGENT_CONTACT = {
    "content": "Content Agent (内容质量/构建)",
    "frontend": "Frontend Agent (页面/视觉/响应式)",
    "ops": "Ops Agent (部署/配置/权限)",
    "seo": "SEO Agent (索引/排名)",
    "social": "Social Agent (社媒发布)",
    "orchestrator": "Orchestrator (跨Agent协调)",
}

CATEGORY_LABELS = {
    "content_quality_p0": "内容质量 P0",
    "mojibake_detected": "P0 乱码",
    "fact_guard_failed": "事实检查失败",
    "brand_violation": "品牌审计失败",
    "content_id_error": "内容ID审计失败",
    "content_audit_script_error": "内容巡检脚本异常",
    "visual_quality_failed": "视觉质量门禁失败",
    "predeploy_quality_failed": "部署前质量门禁失败",
    "git_push_failed": "Git 推送失败",
    "authentication_error": "认证失败",
    "dependency_missing": "依赖缺失",
    "module_not_found": "Python 模块缺失",
    "network_error": "网络错误",
    "permission_denied": "权限不足",
    "build_timeout": "构建超时",
    "yaml_parsing": "YAML 解析失败",
    "shortcode_missing": "Shortcode 缺失",
    "encoding_corruption": "编码损坏",
    "unknown": "未分类错误",
}

ANSI_ESCAPE_RE = re.compile(r"(?:\x1b|\^\[)\[[0-9;]*m")
LOG_PREFIX_RE = re.compile(r"^\ufeff?\d{4}-\d{2}-\d{2}T[^\s]+\s*")
SHELL_ECHO_ERROR_RE = re.compile(
    r"""^\s*echo\s+["']?::(?:error|warning)::""",
    re.IGNORECASE,
)
NOISE_RE = re.compile(
    r"(cleaning up orphan processes|post job cleanup|node\.js 20 is deprecated|"
    r"node 20 is being deprecated|git config --local|submodule foreach|extraheader|"
    r"complete job|runner version|github_token permissions|post setup python|"
    r"post checkout repository)",
    re.IGNORECASE,
)


def http_post(url, payload, headers=None):
    """用标准库发 POST 请求"""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, resp.read().decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return 0, str(e)


def run_gh(args):
    try:
        result = subprocess.run(
            ["gh"] + args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            env={**os.environ, "GH_TOKEN": GITHUB_TOKEN} if GITHUB_TOKEN else os.environ
        )
        return result.stdout + result.stderr
    except Exception as e:
        return str(e)


def run_gh_json(args):
    try:
        result = subprocess.run(
            ["gh"] + args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            env={**os.environ, "GH_TOKEN": GITHUB_TOKEN} if GITHUB_TOKEN else os.environ
        )
        if result.returncode != 0:
            return {}
        return json.loads(result.stdout)
    except Exception:
        return {}


def fetch_run_metadata(run_id):
    data = run_gh_json([
        "run", "view", str(run_id), "--repo", REPO,
        "--json", "name,workflowName,conclusion,jobs",
    ])
    failed_jobs = []
    failed_steps = []
    for job in data.get("jobs", []):
        if job.get("conclusion") == "failure":
            failed_jobs.append(job.get("name") or "unknown job")
        for step in job.get("steps", []):
            if step.get("conclusion") == "failure":
                failed_steps.append(
                    f"{job.get('name', 'unknown job')} / "
                    f"{step.get('name', 'unknown step')}"
                )
    return {
        "name": data.get("workflowName") or data.get("name") or "",
        "conclusion": data.get("conclusion") or "",
        "failed_jobs": failed_jobs,
        "failed_steps": failed_steps,
    }


def fetch_failure_log(run_id):
    """优先拉取失败步骤日志，缺失时再降级到完整日志。"""
    for log_flag in ("--log-failed", "--log"):
        log = run_gh(["run", "view", str(run_id), "--repo", REPO, log_flag])
        if log and "no failed logs" not in log.lower():
            return log
    return ""


def normalize_log_line(line):
    line = ANSI_ESCAPE_RE.sub("", line).strip()
    parts = line.split("\t", 2)
    if len(parts) == 3:
        line = parts[2]
    line = LOG_PREFIX_RE.sub("", line).strip()
    return line


def _line_score(line):
    lower = line.lower()
    critical_markers = (
        "traceback (most recent call last)",
        "keyerror:",
        "modulenotfounderror:",
        "syntaxerror:",
        "failed to push",
        "remote rejected",
        "non-fast-forward",
        "permission denied",
        "resource not accessible by integration",
        "403 forbidden",
    )
    if any(marker in lower for marker in critical_markers):
        return 100
    if "::error::" in lower:
        return 95
    if re.search(r"\bvisual quality:.*\bp[01]=[1-9]", line, re.IGNORECASE):
        return 95
    if re.search(r"\bpredeploy quality:.*\bp[01]=[1-9]", line, re.IGNORECASE):
        return 95
    if re.search(r"\b(failed|fatal|error:)\b", lower):
        return 75
    if "process completed with exit code" in lower:
        return 40
    return 0


def extract_error_evidence(error_log, limit=10):
    """过滤 CI 清理噪声，优先返回可执行的失败证据行。"""
    candidates = []
    for index, raw_line in enumerate(error_log.splitlines()):
        line = normalize_log_line(raw_line)
        if not line or SHELL_ECHO_ERROR_RE.search(line) or NOISE_RE.search(line):
            continue
        score = _line_score(line)
        if score:
            candidates.append((score, index, line))
    if not candidates:
        fallback = []
        for raw_line in error_log.splitlines()[-80:]:
            line = normalize_log_line(raw_line)
            if (
                line
                and not SHELL_ECHO_ERROR_RE.search(line)
                and not NOISE_RE.search(line)
            ):
                fallback.append(line)
        return fallback[-limit:]

    selected = sorted(candidates, key=lambda item: (-item[0], item[1]))[:limit]
    selected = sorted(selected, key=lambda item: item[1])
    return [line for _, _, line in selected]


def sanitize_log_for_classification(error_log):
    """Remove echoed workflow source while keeping actual runner output."""
    lines = []
    for raw_line in error_log.splitlines():
        line = normalize_log_line(raw_line)
        if not line or SHELL_ECHO_ERROR_RE.search(line):
            continue
        lines.append(line)
    return "\n".join(lines)


def classify_error_extended(error_message):
    classification_log = sanitize_log_for_classification(error_message)
    specific_rules = (
        ("content_audit_script_error", (
            r"keyerror:\s*['\"]mojibake['\"]",
            r"生成综合内容质量报告.*traceback",
            r"validator_output\.json.*(?:decode|jsondecodeerror)",
        )),
        ("mojibake_detected", (
            r"mojibake_files=[1-9]",
            r"encoding_error_files=[1-9]",
            r"\bmojibake\(p0\)\b",
            r"p0\s*乱码文件[^\n]*[1-9]",
        )),
        ("fact_guard_failed", (
            r"::error::内容事实检查",
            r"content_fact_guard.*exit code=[1-9]",
        )),
        ("brand_violation", (
            r"::error::品牌审计",
            r"brand_identity_audit.*exit code=[1-9]",
        )),
        ("content_id_error", (
            r"::error::内容id审计",
            r"content_id_audit.*(?:failed|exit code=[1-9])",
        )),
        ("content_quality_p0", (
            r"::error::内容质量验证失败",
            r"::error::内容质量门禁失败",
            r"content quality gate failed",
        )),
        ("visual_quality_failed", (
            r"\bvisual quality:.*\bp[01]=[1-9]",
            r"site_visual_audit.*(?:failed|exit code=[1-9])",
            r"visual_audit_failed",
        )),
        ("predeploy_quality_failed", (
            r"\bpredeploy quality:.*\bp[01]=[1-9]",
            r"predeploy_quality_gate.*exit code=[1-9]",
        )),
    )
    for category, patterns in specific_rules:
        if any(re.search(pattern, classification_log, re.IGNORECASE | re.DOTALL)
               for pattern in patterns):
            return category

    handler = ErrorHandler(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    category = handler.classify_error(classification_log)
    if category != "unknown":
        return category
    msg_lower = classification_log.lower()
    if (
        "bad credentials" in msg_lower
        or "authentication failed" in msg_lower
        or "invalid token" in msg_lower
        or "token expired" in msg_lower
    ):
        return "authentication_error"
    if re.search(
        r"failed to push|remote rejected|non-fast-forward|fetch first|"
        r"protected branch|push declined",
        msg_lower,
    ):
        return "git_push_failed"
    if "no module named" in msg_lower or "module not found" in msg_lower:
        return "module_not_found"
    if "could not find" in msg_lower and "version" in msg_lower:
        return "dependency_missing"
    if "connection" in msg_lower and ("refused" in msg_lower or "timeout" in msg_lower or "reset" in msg_lower):
        return "network_error"
    if (
        "permission denied" in msg_lower
        or "resource not accessible by integration" in msg_lower
        or "403 forbidden" in msg_lower
        or re.search(r"http(?: status)?[ =:]+403\b", msg_lower)
    ):
        return "permission_denied"
    if "exit code 127" in classification_log or "command not found" in msg_lower:
        return "dependency_missing"
    return "unknown"


def get_fix_guide(category):
    guides = {
        "authentication_error": "检查 CI Secrets 中的 API Token 是否过期或权限不足。例如 Cloudflare API Token 需要 Workers Scripts:Edit + User Details:Read 权限。",
        "permission_denied": "检查 GitHub Token 权限或文件系统权限。GITHUB_TOKEN 需要 contents:write, actions:write 权限。",
        "dependency_missing": "检查 requirements.txt / package.json 依赖是否完整，在 workflow 中添加缺失的安装步骤。",
        "module_not_found": "Python 模块缺失，在 workflow 的 pip install 步骤中添加该模块。",
        "build_timeout": "构建超时，检查是否有死循环或大文件处理，可增加 timeout-minutes 或优化构建流程。",
        "git_push_failed": "Git 推送失败，通常是并发冲突。检查是否有其他 workflow 同时推送，添加 rebase 容错。",
        "network_error": "网络错误，通常是临时问题。可自动重试一次，若持续失败检查外部 API 可用性。",
        "content_quality_p0": "内容质量门禁发现 P0 问题。打开失败运行的内容审计 artifact，按文件和规则修复后重跑。",
        "mojibake_detected": "检测到 P0 乱码或非法 UTF-8。按报告中的文件清单修复编码，并保留原文备份。",
        "fact_guard_failed": "事实检查未通过。核对失败文件中的签证、支付、交通、价格等事实，并补充可追溯来源。",
        "brand_violation": "品牌审计未通过。检查旧人设、禁用表达和品牌名称，统一为当前 Editorial Voice。",
        "content_id_error": "内容 ID 审计未通过。修复缺失、重复或格式不合法的 content_id，禁止在发布流程中自动生成随机 ID。",
        "content_audit_script_error": "内容巡检脚本自身异常，不是内容 P0。查看失败步骤的 Traceback 和 validator_output.json，先修复脚本数据结构或异常处理。",
        "visual_quality_failed": "视觉质量门禁未通过。打开 reports/quality/visual_audit.json，按 P0/P1 页面、视口和 evidence 逐项修复。",
        "predeploy_quality_failed": "部署前静态质量门禁未通过。检查 reports/quality/predeploy_quality.json 中的页面与问题类型。",
    }
    return guides.get(category, "请查看日志详情，人工分析根因。")


def enqueue_workflow_failure(
    workflow_name,
    run_id,
    category,
    route,
    error_snippet,
    failed_steps=None,
    tasks_dir=None,
    target_date=None,
):
    severity = "P0" if category in {
        "content_quality_p0",
        "mojibake_detected",
        "visual_quality_failed",
        "predeploy_quality_failed",
    } else ("P2" if category == "unknown" else "P1")
    issue = {
        "id": f"workflow-{run_id}-{category}",
        "type": category,
        "severity": severity,
        "title": f"{workflow_name} 失败：{CATEGORY_LABELS.get(category, category)}",
        "description": "\n".join(failed_steps or []) or error_snippet[:300],
        "page": workflow_name,
        "evidence": error_snippet[:1000],
        "recommended_action": get_fix_guide(category),
        "owner": route.get("agent", "ops"),
        "source": "workflow_failure",
        "action": "manual_review" if severity != "P0" else "blocking_review",
    }
    return enqueue_issues(
        [issue],
        task_source="workflow_failure",
        target_date=target_date,
        tasks_dir=tasks_dir,
        prune_missing=False,
    )


def enqueue_workflow_failure_safely(*args, **kwargs):
    try:
        return enqueue_workflow_failure(*args, **kwargs)
    except Exception as exc:
        print(f"[TaskQueue] Failed to enqueue Agent task: {exc}")
        return []


def send_feishu_alert(
    workflow_name,
    run_id,
    category,
    error_snippet,
    fix_guide="",
    failed_steps=None,
    detection_source="",
):
    if not FEISHU_WEBHOOK:
        print("[Alert] FEISHU_WEBHOOK_URL not set, skip alert")
        return False
    route = ERROR_ROUTES.get(category, ERROR_ROUTES["unknown"])
    agent = AGENT_CONTACT.get(route["agent"], "未知")
    category_label = CATEGORY_LABELS.get(category, category)
    steps_text = "\n".join(f"- {step}" for step in (failed_steps or [])) or "- 未识别"
    content = f"""**工作流失败自动分析报告**

**工作流**: {workflow_name}
**运行ID**: [{run_id}](https://github.com/{REPO}/actions/runs/{run_id})
**错误分类**: {category_label} (`{category}`)
**分配处理**: {agent}
**处理策略**: {route['action']}
**失败步骤**:
{steps_text}
**判定来源**: {detection_source or '失败日志关键错误行'}

**检测到的证据**:
```
{error_snippet[:1000]}
```
"""
    if fix_guide:
        content += f"\n**修复指引**:\n{fix_guide}\n"
    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {"title": {"tag": "plain_text", "content": f"⚠️ {workflow_name} 失败 - 已自动分类"}, "template": "red"},
            "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": content}}]
        }
    }
    status, _ = http_post(FEISHU_WEBHOOK, payload)
    return status == 200


def create_github_issue(workflow_name, run_id, category, error_snippet):
    if not GITHUB_TOKEN:
        print("[Issue] GITHUB_TOKEN not set, skip issue creation")
        return None
    route = ERROR_ROUTES.get(category, ERROR_ROUTES["unknown"])
    agent = AGENT_CONTACT.get(route["agent"], "未知")
    issue_title = f"⚠️ [自动创建] {workflow_name} 失败 - {category}"
    issue_body = f"""## 工作流信息
- **工作流**: {workflow_name}
- **运行ID**: [{run_id}](https://github.com/{REPO}/actions/runs/{run_id})
- **错误分类**: {category}
- **分配处理**: {agent}
- **失败时间**: {datetime.now().isoformat()}

## 错误摘要
```
{error_snippet[:800]}
```

## 下一步
请 {agent} 分析根因并修复。修复后关闭此 Issue。
"""
    status, body = http_post(
        f"https://api.github.com/repos/{REPO}/issues",
        {"title": issue_title, "body": issue_body, "labels": ["auto-error", category]},
        {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    )
    if status == 201:
        return json.loads(body).get("html_url")
    return None


def retry_workflow(workflow_name):
    result = run_gh(["workflow", "run", workflow_name, "--ref", "main"])
    return "Created" in result or "workflow_dispatch" in result.lower()


def auto_fix_and_commit(category, error_message, handler):
    error_record = handler.add_error(error_message, "auto_router", "cli", category)
    fixed = handler.auto_fix(error_record)
    if fixed:
        try:
            subprocess.run(["git", "add", "-A"], cwd=handler.repo_path, capture_output=True, timeout=10)
            subprocess.run(["git", "commit", "-m", f"fix(auto): auto-fix {category} by error-router"],
                           cwd=handler.repo_path, capture_output=True, timeout=10)
            subprocess.run(["git", "push", "https://github.com/fys2388/chinaboundtravel.git", "main"],
                           cwd=handler.repo_path, capture_output=True, timeout=30)
            return True
        except Exception as e:
            print(f"[AutoFix] Commit/push failed: {e}")
    return False


def main():
    if len(sys.argv) < 3:
        print("Usage: python auto_error_router.py <workflow_name> <run_id>")
        sys.exit(1)

    workflow_name = sys.argv[1]
    run_id = sys.argv[2]

    print(f"=== Auto Error Router ===")
    print(f"Workflow: {workflow_name}")
    print(f"Run ID: {run_id}")

    print("\n[1/5] Fetching failure metadata and log...")
    metadata = fetch_run_metadata(run_id)
    error_log = fetch_failure_log(run_id)
    evidence_lines = extract_error_evidence(error_log)
    error_snippet = "\n".join(evidence_lines)
    failed_steps = metadata.get("failed_steps", [])
    print(f"  Failed steps: {failed_steps or ['unknown']}")
    print(f"  Evidence lines: {len(evidence_lines)}")

    print("[2/5] Classifying error...")
    category = classify_error_extended(error_log)
    route = ERROR_ROUTES.get(category, ERROR_ROUTES["unknown"])
    print(f"  Category: {category}")
    print(f"  Strategy: {route['action']}")
    print(f"  Assigned to: {AGENT_CONTACT.get(route['agent'], '未知')}")

    print("[3/5] Recording to knowledge base...")
    repo_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    handler = ErrorHandler(repo_path)
    handler.add_error(error_snippet or error_log[-500:], workflow_name, run_id, category)

    print("[4/5] Executing route strategy...")
    result = {
        "category": category,
        "action": route["action"],
        "fixed": False,
        "retried": False,
        "issue_url": None,
        "task_files": [],
    }

    if route["action"] in ("alert_with_fix_guide", "alert_only", "create_issue"):
        result["task_files"] = enqueue_workflow_failure_safely(
            workflow_name,
            run_id,
            category,
            route,
            error_snippet or error_log[-1000:],
            failed_steps,
        )

    if route["action"] == "auto_fix":
        fixed = auto_fix_and_commit(category, error_log, handler)
        result["fixed"] = fixed
        if fixed and route["retry"]:
            result["retried"] = retry_workflow(workflow_name)
        elif not fixed:
            result["task_files"] = enqueue_workflow_failure_safely(
                workflow_name,
                run_id,
                category,
                route,
                error_snippet or error_log[-1000:],
                failed_steps,
            )
            send_feishu_alert(
                workflow_name, run_id, category, error_snippet,
                "自动修复失败，请人工处理。", failed_steps,
                "失败步骤 + 关键错误行",
            )

    elif route["action"] in ("alert_with_fix_guide",):
        fix_guide = get_fix_guide(category)
        send_feishu_alert(
            workflow_name, run_id, category, error_snippet, fix_guide,
            failed_steps, "失败步骤 + 关键错误行",
        )
        if route["retry"]:
            result["retried"] = retry_workflow(workflow_name)

    elif route["action"] == "retry_only":
        result["retried"] = retry_workflow(workflow_name)
        send_feishu_alert(
            workflow_name, run_id, category, error_snippet,
            "网络错误，已自动重试一次。", failed_steps,
            "失败步骤 + 关键错误行",
        )

    elif route["action"] == "alert_only":
        send_feishu_alert(
            workflow_name, run_id, category, error_snippet, "",
            failed_steps, "失败步骤 + 关键错误行",
        )

    else:
        issue_url = create_github_issue(workflow_name, run_id, category, error_snippet)
        result["issue_url"] = issue_url
        send_feishu_alert(
            workflow_name, run_id, category, error_snippet,
            f"未知错误，已创建 Issue 分配给 {AGENT_CONTACT.get(route['agent'])}: {issue_url}",
            failed_steps, "失败步骤 + 关键错误行",
        )

    print("\n[5/5] Result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # [6/6] 回写修复状态到 workflow_fix_log
    fix_status = "unknown"
    fix_note = ""
    if result.get("fixed"):
        fix_status = "fixed"
        fix_note = f"自动修复成功(category={category})"
        if result.get("retried"):
            fix_note += ", 已自动重试"
    elif result.get("retried"):
        fix_status = "retried"
        fix_note = f"已自动重试(category={category})"
    elif result.get("issue_url"):
        fix_status = "needs_manual"
        fix_note = f"已创建Issue: {result['issue_url']}"
    else:
        fix_status = "alerted"
        fix_note = f"已发送飞书告警(category={category})"

    writeback_workflow(
        workflow_name=workflow_name,
        status=fix_status,
        fixed_by=f"auto_error_router:{route['agent']}",
        fix_note=fix_note,
    )
    print(f"  [writeback] {workflow_name} -> {fix_status}")

    print("\n=== Auto Error Router complete ===")


if __name__ == "__main__":
    main()
