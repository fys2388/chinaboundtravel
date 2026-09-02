#!/usr/bin/env python3
"""
Auto Error Router - 工作流失败自动处理闭环
流程：拉取失败日志 → 错误分类 → 自动修复/告警/分配Agent → 重试 → 记录知识库
"""
import os
import sys
import json
import subprocess
import urllib.request
import urllib.error
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from error_handler import ErrorHandler

REPO = os.environ.get("GITHUB_REPOSITORY", "fys2388/chinaboundtravel")
FEISHU_WEBHOOK = os.environ.get("FEISHU_WEBHOOK_URL", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

ERROR_ROUTES = {
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
    "ops": "Ops Agent (部署/配置/权限)",
    "seo": "SEO Agent (索引/排名)",
    "social": "Social Agent (社媒发布)",
    "orchestrator": "Orchestrator (跨Agent协调)",
}


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
            ["gh"] + args, capture_output=True, text=True, timeout=30,
            env={**os.environ, "GH_TOKEN": GITHUB_TOKEN} if GITHUB_TOKEN else os.environ
        )
        return result.stdout + result.stderr
    except Exception as e:
        return str(e)


def fetch_failure_log(run_id):
    log = run_gh(["run", "view", str(run_id), "--log"])
    # 取最后8000字符，确保包含错误信息
    if len(log) > 8000:
        return log[-8000:]
    return log


def classify_error_extended(error_message):
    handler = ErrorHandler(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    category = handler.classify_error(error_message)
    if category != "unknown":
        return category
    msg_lower = error_message.lower()
    if "authentication error" in msg_lower or ("auth" in msg_lower and "token" in msg_lower):
        return "authentication_error"
    if "no module named" in msg_lower or "module not found" in msg_lower:
        return "module_not_found"
    if "could not find" in msg_lower and "version" in msg_lower:
        return "dependency_missing"
    if "connection" in msg_lower and ("refused" in msg_lower or "timeout" in msg_lower or "reset" in msg_lower):
        return "network_error"
    if "permission denied" in msg_lower or "403" in error_message or "forbidden" in msg_lower:
        return "permission_denied"
    if "exit code 127" in error_message or "command not found" in msg_lower:
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
    }
    return guides.get(category, "请查看日志详情，人工分析根因。")


def send_feishu_alert(workflow_name, run_id, category, error_snippet, fix_guide=""):
    if not FEISHU_WEBHOOK:
        print("[Alert] FEISHU_WEBHOOK_URL not set, skip alert")
        return False
    route = ERROR_ROUTES.get(category, ERROR_ROUTES["unknown"])
    agent = AGENT_CONTACT.get(route["agent"], "未知")
    content = f"""**工作流失败自动分析报告**

**工作流**: {workflow_name}
**运行ID**: [{run_id}](https://github.com/{REPO}/actions/runs/{run_id})
**错误分类**: {category}
**分配处理**: {agent}
**处理策略**: {route['action']}

**错误摘要**:
```
{error_snippet[:400]}
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

    print("\n[1/5] Fetching failure log...")
    error_log = fetch_failure_log(run_id)
    error_snippet = error_log[-500:] if len(error_log) > 500 else error_log

    print("[2/5] Classifying error...")
    category = classify_error_extended(error_log)
    route = ERROR_ROUTES.get(category, ERROR_ROUTES["unknown"])
    print(f"  Category: {category}")
    print(f"  Strategy: {route['action']}")
    print(f"  Assigned to: {AGENT_CONTACT.get(route['agent'], '未知')}")

    print("[3/5] Recording to knowledge base...")
    repo_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    handler = ErrorHandler(repo_path)
    handler.add_error(error_log, workflow_name, run_id, category)

    print("[4/5] Executing route strategy...")
    result = {"category": category, "action": route["action"], "fixed": False, "retried": False, "issue_url": None}

    if route["action"] == "auto_fix":
        fixed = auto_fix_and_commit(category, error_log, handler)
        result["fixed"] = fixed
        if fixed and route["retry"]:
            result["retried"] = retry_workflow(workflow_name)
        elif not fixed:
            send_feishu_alert(workflow_name, run_id, category, error_snippet, "自动修复失败，请人工处理。")

    elif route["action"] in ("alert_with_fix_guide",):
        fix_guide = get_fix_guide(category)
        send_feishu_alert(workflow_name, run_id, category, error_snippet, fix_guide)
        if route["retry"]:
            result["retried"] = retry_workflow(workflow_name)

    elif route["action"] == "retry_only":
        result["retried"] = retry_workflow(workflow_name)
        send_feishu_alert(workflow_name, run_id, category, error_snippet, "网络错误，已自动重试一次。")

    elif route["action"] == "alert_only":
        send_feishu_alert(workflow_name, run_id, category, error_snippet)

    else:
        issue_url = create_github_issue(workflow_name, run_id, category, error_snippet)
        result["issue_url"] = issue_url
        send_feishu_alert(workflow_name, run_id, category, error_snippet,
                          f"未知错误，已创建 Issue 分配给 {AGENT_CONTACT.get(route['agent'])}: {issue_url}")

    print("\n[5/5] Result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("\n=== Auto Error Router complete ===")


if __name__ == "__main__":
    main()
