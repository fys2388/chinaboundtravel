#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""打印 api_health / subscription_health 最新报告的 GitHub Actions 摘要块。

用法:
    python scripts/audit_summary_md.py            # 只打印摘要
    python scripts/audit_summary_md.py --fail     # 有失败用例时返回非零
    python scripts/audit_summary_md.py --root X   # 指定报告根目录

输出 markdown 表格到 stdout，供 workflow 追加进 $GITHUB_STEP_SUMMARY。

为什么不把这段 python -c 内联进 workflow YAML：
多层 f-string 里再嵌 dict 取值引号，引号转义在 YAML 解析层极易写错，
而且错了只能在 CI 上才发现。抽成脚本可以在本地直接跑验证。
"""
import argparse
import glob
import json
import os
import sys
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        return {"_error": f"{type(exc).__name__}: {exc}"}


def _latest(pattern: str, root: Optional[Path] = None) -> str:
    """最新的报告文件。文件名自带时间戳（api_health_YYYYMMDD_HHMMSS.json），
    字典序即时间序；用 mtime 兜底，防止有人手改了文件名。"""
    if root is None:
        root = PROJECT_ROOT
    files = sorted(glob.glob(str(root / pattern)))
    if not files:
        return ""
    return max(files, key=lambda p: (os.path.getmtime(p), p))


def _failures(report: dict) -> list:
    return [t.get("name", "?") for t in report.get("api_tests", [])
            if not t.get("passed")]


def build_summary(root: Optional[Path] = None) -> tuple:
    """生成 (markdown 文本, 是否有失败用例)。纯函数，方便测试。"""
    if root is None:
        root = PROJECT_ROOT

    lines = ["### Endpoint Health Audit", ""]
    any_failed = False

    api_path = _latest("reports/api_health/api_health_*.json", root)
    sub_path = _latest("reports/subscription_health/subscription_health_*.json", root)

    if not api_path and not sub_path:
        lines.append("⚠️ 未找到任何审计报告——审计脚本可能未执行或输出路径变了。")
        return "\n".join(lines), any_failed

    lines += ["| 报告 | 结果 | 失败用例 |", "| --- | --- | --- |"]

    for path, label in ((api_path, "api_health"), (sub_path, "subscription")):
        if not path:
            continue
        report = _load(path)
        name = Path(path).name

        if "_error" in report:
            lines.append(f"| {label} | ❌ 读取失败 {report['_error']} | - |")
            any_failed = True
            continue

        s = report.get("summary", {})
        passed, total = s.get("passed", 0), s.get("total", 0)
        fails = _failures(report)
        mark = "✅" if not fails else "❌"

        if label == "api_health":
            rate = s.get("pass_rate")
            extra = f" ({rate}%)" if rate is not None else " (无通过率字段)"
        else:
            ep = report.get("mailerlite", {}).get("endpoint_reported", {})
            extra = (f" · MailerLite={ep.get('mailerlite', '?')}"
                     f" Resend={ep.get('resend', '?')}")

        shown = ", ".join(fails) if fails else "无"
        lines.append(f"| {label} | {mark} {passed}/{total}{extra} — {name} | {shown} |")
        if fails:
            any_failed = True

    lines += ["", "> 报告新鲜度：本流水线每 6 小时刷新一次。",
              "> 若某报告的时间戳明显落后，说明对应审计步骤未产出新文件。"]
    return "\n".join(lines), any_failed


def main() -> int:
    ap = argparse.ArgumentParser(description="审计报告摘要")
    ap.add_argument("--fail", action="store_true",
                    help="有失败用例时返回非零退出码")
    ap.add_argument("--root", type=str, default=None,
                    help="报告根目录（默认仓库根，测试用）")
    args = ap.parse_args()

    root = Path(args.root) if args.root else None
    text, any_failed = build_summary(root)
    print(text)
    return 1 if (args.fail and any_failed) else 0


if __name__ == "__main__":
    # Windows 控制台默认 GBK，打印 ✅/⚠️ 会 UnicodeEncodeError 崩溃——
    # 后果是 --fail 的退出码不可信：全绿也会因编码崩溃而返回非零，
    # 依赖这个退出码的 CI 门控就形同虚设。
    # 2026-09-21 修；同 affiliate_link_audit.py 的处理方式。
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main())
