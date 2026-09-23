"""Check MailerLite hygiene: prevent fake-subscriber pollution regression.

AUDIT-OPS-006 收尾 P3: 静态扫 MailerLite 相关脚本里的 @example.* 字面量，
确保全部命中 scripts/ml_utils.py 的 TEST_EMAIL_WHITELIST。

设计原则:
- 只扫 MailerLite 相关脚本（POST 到 MailerLite /api/subscribe 或 /api/subscribers）
- 用 AST 精准识别字符串字面量，跳过 Module/Class/Function 的 docstring
- 正则提取邮箱边界（word chars + dot/hyphen 到 @example.(com|org|net)），
  拒绝中文标点/HTML 等噪声
- 命中 @example.com/.org/.net 但不在 TEST_EMAIL_WHITELIST
  → 视为未来污染源回归，exit 1 阻止合并

运行:
    python scripts/lint/check_mailerlite_hygiene.py

集成建议:
    可作为 pre-merge gate 或 site-health-daily.yml 步骤，
    阻止未来任何新增脚本又用 test-<timestamp>@example.com 污染 MailerLite。
"""
import ast
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
SCRIPTS = REPO / "scripts"

# MailerLite 相关脚本（POST 到 MailerLite /api/subscribe 或 /api/subscribers）
# 只有这些脚本里的 @example.com 才算 MailerLite 污染源；
# contact_form_health_audit.py 里的 health-check@example.com 是 Web3Forms 用的，不在此列。
MAILERLITE_RELATED_SCRIPTS = {
    "subscription_health_audit.py",
    "api_health_audit.py",
    "performance_monitor.py",
    "mailerlite_sequence_setup.py",
    "email_sequence_tracker.py",
    "ml_utils.py",  # 白名单定义本身（用于豁免校验）
}

# 允许的固定测试邮箱（与 scripts/ml_utils.py 的 TEST_EMAIL_WHITELIST 保持同步）
# 修改这个集合时必须同时更新 scripts/ml_utils.py 的 TEST_EMAIL_WHITELIST
ALLOWED_TEST_EMAILS = {
    "healthcheck.chinaboundtravel@example.com",
    "test-api-health@example.com",
    "perf-test@example.com",
}

# 正则：合法邮箱字面量（word chars 到 @example.(com|org|net)，右边界为词尾）
EMAIL_RE = re.compile(r'[\w.-]+@example\.(?:com|org|net)\b')


def collect_docstring_nodes(tree: ast.AST) -> set:
    """结构性收集 docstring 节点（Module/ClassDef/FunctionDef 的 body 首个 Expr(Constant)）。"""
    docstring_ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                docstring_ids.add(id(body[0].value))
    return docstring_ids


def scan_file(path: Path) -> list:
    """用 AST 精准扫描字符串字面量，返回违规项列表 [(path, lineno, source_value, email)]."""
    issues = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except Exception as e:
        return [(path, 0, f"AST parse failed: {e}", "N/A")]

    docstring_ids = collect_docstring_nodes(tree)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        if id(node) in docstring_ids:
            continue
        value = node.value
        if "@example." not in value:
            continue
        for email in EMAIL_RE.findall(value):
            if email.lower() in ALLOWED_TEST_EMAILS:
                continue
            issues.append((path, node.lineno, value[:120], email.lower()))

    return issues


def main():
    all_issues = []
    for script_name in sorted(MAILERLITE_RELATED_SCRIPTS):
        script_path = SCRIPTS / script_name
        if not script_path.exists():
            print(f"  SKIP (missing): {script_name}")
            continue
        all_issues.extend(scan_file(script_path))

    if not all_issues:
        print(f"OK: no unauthorized @example.com/.org/.net literals in "
              f"{len(MAILERLITE_RELATED_SCRIPTS)} MailerLite-related scripts")
        print(f"    Allowed fixed test emails: {sorted(ALLOWED_TEST_EMAILS)}")
        sys.exit(0)

    print(f"FAIL: found {len(all_issues)} unauthorized @example.com/.org/.net literal(s):\n")
    for path, lineno, value, email in all_issues:
        rel = path.relative_to(REPO)
        print(f"  {rel}:{lineno}")
        print(f"    value: {value!r}")
        print(f"    email: {email!r} 不在 TEST_EMAIL_WHITELIST")
    print("\n修复建议:")
    print("  1. 用固定测试邮箱（3 选 1，MailerLite 幂等更新不新增）:")
    print(f"     - {'healthcheck.chinaboundtravel@example.com':<50} (subscription_health_audit.py)")
    print(f"     - {'test-api-health@example.com':<50} (api_health_audit.py)")
    print(f"     - {'perf-test@example.com':<50} (performance_monitor.py)")
    print("  2. 禁止 test-<timestamp>@example.com 模式（这是 AUDIT-OPS-006 的历史污染源）")
    print("  3. 若必须用新固定测试邮箱，先在 scripts/ml_utils.py 的 TEST_EMAIL_WHITELIST 追加，")
    print("     再在本脚本的 ALLOWED_TEST_EMAILS 同步追加，然后重跑此 lint。")
    print("  4. 若历史假订阅者已污染 MailerLite，跑:")
    print("     python scripts/subscription_health_audit.py --cleanup --cleanup-apply")
    sys.exit(1)


if __name__ == "__main__":
    main()
