"""测试回归闸门：只对本次新增的失败报错，基线内的存量失败只记录不阻断。

为什么需要它
------------
2026-09-21 之前本仓库没有任何 CI 跑 pytest，导致三类缺陷直接上了 main：
同义替换提交带着 4 个坏测试上线、REV002 时间炸弹以永久失败形式入库、
审计脚本的全绿假象上线。根因不是测试写得不够严，而是**没有反馈边**——
测试红了也没人知道，报告越写越多但没人回头看报告对不对。

设计原则
--------
- 基线（reports/quality/test_failure_baseline.json）记录已知存量失败。
- 只有**不在基线里的新失败**才让闸门失败（exit 1）。
  这是刻意的：仓库存量失败 ~30 个，做成硬阻断会挡住所有 bot 推送。
- 已修复的基线失败会被报告出来，配合 --update-baseline 逐轮收敛。
- 对每个新失败，用 git log 定位最后一次改到该测试文件的提交（作者+消息）。
  这就是「谁引入的」——闭环的第一根反馈边。

只读为主：本脚本不改任何源代码，只写 reports/quality/ 下的报告。

用法::

    python scripts/test_regression_gate.py                     # 跑全套，与基线比对
    python scripts/test_regression_gate.py --update-baseline   # 用当前结果重建基线
    python scripts/test_regression_gate.py tests/test_x.py     # 只跑指定路径（快）
    python scripts/test_regression_gate.py --no-run --junit x  # 解析已有的 junit 文件

退出码：0 = 无新增失败；1 = 有新增失败；2 = 基线缺失（先用 --update-baseline 建立）。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BASELINE = PROJECT_ROOT / "reports" / "quality" / "test_failure_baseline.json"
REPORT_JSON = PROJECT_ROOT / "reports" / "quality" / "test_regression.json"
REPORT_MD = PROJECT_ROOT / "reports" / "quality" / "test_regression_report.md"
JUNIT_XML = PROJECT_ROOT / "reports" / "quality" / "pytest_junit.xml"

# 存量失败里「测试本身有问题」的特征：断言把某次已知的缺陷/时间戳/标题
# 写死成期望，真实仓库修好后该测试就会永久红。
STALE_TEST_HINTS = (
    "title_unchanged",
    "affiliates_url_unchanged",
    "partner_urls_unchanged",
    "required_h2_structure",
    "recommended_tools_table",
    "recommended_services_table",
)


def run_pytest(scope: List[str]) -> int:
    """跑 pytest 并产出 junit 文件，返回 pytest 退出码。"""
    JUNIT_XML.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable, "-m", "pytest",
        *(scope or ["tests"]),
        "--junitxml", str(JUNIT_XML),
        "--tb=no", "-q", "--no-header", "-p", "no:cacheprovider",
    ]
    proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    return proc.returncode


def _node_id(case: ET.Element) -> str:
    """junit testcase → pytest node id。

    classname 形如 "tests.test_x.Y" 或 "tests.test_x"；Hugo 模块级 fixture 的
    测试类名可能带参数化后缀，原样保留以便精确匹配。
    """
    cls = case.get("classname") or ""
    name = case.get("name") or ""
    cls = re.sub(r"\.py$", "", cls.replace("/", "."))
    return f"{cls}::{name}" if cls else name


def parse_junit(path: Path) -> Dict[str, List[str]]:
    """解析 junit xml，返回 {status: [node_id, ...]}。"""
    out = {"failed": [], "passed": [], "skipped": [], "error": []}
    if not path.exists():
        return out
    root = ET.parse(path).getroot()
    # 支持 <testsuites><testsuite>... 与顶层 <testsuite> 两种结构
    cases: List[ET.Element] = []
    if root.tag == "testsuites":
        for suite in root.findall("testsuite"):
            cases.extend(suite.findall("testcase"))
    elif root.tag == "testsuite":
        cases = root.findall("testcase")
    for case in cases:
        nid = _node_id(case)
        if case.find("failure") is not None:
            out["failed"].append(nid)
        elif case.find("error") is not None:
            out["error"].append(nid)
        elif case.find("skipped") is not None:
            out["skipped"].append(nid)
        else:
            out["passed"].append(nid)
    return out


def _git_line(args: List[str]) -> str:
    try:
        r = subprocess.run(
            ["git", *args], cwd=str(PROJECT_ROOT),
            capture_output=True, text=True, encoding="utf-8",
        )
        return r.stdout.strip()
    except Exception:
        return ""


def _test_file_of(node_id: str) -> Optional[str]:
    m = re.match(r"^((?:tests|[^:]+)\.py)", node_id)
    return m.group(1) if m else None


def attribute(node_id: str) -> Dict[str, str]:
    """定位最后一次改到该测试文件的提交，作为「谁引入的」反馈信号。"""
    f = _test_file_of(node_id)
    if not f:
        return {"file": "", "commit": "", "author": "", "subject": ""}
    line = _git_line(["log", "-1", "--format=%h%x09%an%x09%ae%x09%s", "--", f])
    parts = line.split("\t") if line else []
    return {
        "file": f,
        "commit": parts[0] if len(parts) > 0 else "",
        "author": parts[1] if len(parts) > 1 else "",
        "subject": parts[3] if len(parts) > 3 else "",
    }


def load_baseline() -> Optional[set]:
    if not BASELINE.exists():
        return None
    data = json.loads(BASELINE.read_text(encoding="utf-8"))
    return set(data.get("failures", []))


def save_baseline(failures: List[str], fixed: List[str]) -> None:
    BASELINE.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "note": "已知存量失败基线。回归闸门只对不在本列表中的新失败报错。",
        "failures": sorted(failures),
        "last_fixed": fixed,
    }
    BASELINE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _likely_stale(node_id: str) -> bool:
    return any(h in node_id for h in STALE_TEST_HINTS)


def write_reports(
    failed: List[str], baseline: set, new: List[str], fixed: List[str],
    counts: Dict[str, int],
) -> None:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "node_id": n,
            "likely_stale_test": _likely_stale(n),
            **attribute(n),
        }
        for n in new
    ]
    REPORT_JSON.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "counts": counts,
        "new_failures": rows,
        "fixed_baseline_failures": fixed,
        "all_current_failures": sorted(failed),
        "blocking": bool(new),
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# 测试回归报告",
        "",
        f"生成时间: {datetime.now().isoformat(timespec='seconds')}",
        "",
        f"- 本次运行: {counts.get('collected', 0)} collected, "
        f"{counts.get('failed', 0)} failed",
        f"- 基线存量失败: {len(baseline)}",
        f"- **新增失败: {len(new)}**（阻断条件）",
        f"- 已修复的基线失败: {len(fixed)}（建议 --update-baseline 收敛）",
        "",
    ]
    if new:
        lines += ["## 新增失败（需要处理）", ""]
        for r in rows:
            lines.append(f"- `{r['node_id']}`")
            if r["likely_stale_test"]:
                lines.append("  - ⚠️ 疑似过时测试断言（断言把已知缺陷写死成期望）")
            if r["commit"]:
                lines.append(f"  - 最后一次改动: `{r['commit']}` {r['author']} — {r['subject']}")
            lines.append("")
    if fixed:
        lines += ["## 已修复的基线失败（更新基线可收敛）", ""]
        lines += [f"- `{n}`" for n in fixed]
        lines.append("")
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="测试回归闸门（只阻断新增失败）")
    parser.add_argument("scope", nargs="*", help="pytest 路径子集（默认 tests/）")
    parser.add_argument("--update-baseline", action="store_true",
                        help="用当前失败结果重建基线")
    parser.add_argument("--no-run", action="store_true", help="跳过 pytest，直接解析已有 junit")
    parser.add_argument("--junit", type=Path, default=JUNIT_XML, help="junit xml 路径")
    args = parser.parse_args()

    junit = args.junit if args.junit.is_absolute() else PROJECT_ROOT / args.junit
    if not args.no_run:
        run_pytest(args.scope)

    result = parse_junit(junit)
    failed = sorted(set(result["failed"]) | set(result["error"]))
    counts = {
        "collected": len(failed) + len(result["passed"]) + len(result["skipped"]),
        "failed": len(failed),
        "passed": len(result["passed"]),
        "skipped": len(result["skipped"]),
    }

    baseline = load_baseline()
    if args.update_baseline:
        save_baseline(failed, [])
        print(f"基线已重建: {len(failed)} 个存量失败 -> {BASELINE.relative_to(PROJECT_ROOT)}")
        return 0

    if baseline is None:
        print(
            f"❌ 缺少基线 {BASELINE.relative_to(PROJECT_ROOT)}。\n"
            "   存量失败尚未登记，闸门无法判断哪些是新失败。\n"
            "   运行一次: python scripts/test_regression_gate.py --update-baseline",
            file=sys.stderr,
        )
        return 2

    new = sorted(set(failed) - baseline)
    fixed = sorted(baseline - set(failed))
    counts["baseline"] = len(baseline)
    counts["new_failures"] = len(new)
    counts["fixed_failures"] = len(fixed)

    write_reports(failed, baseline, new, fixed, counts)

    print("=" * 66)
    print("  测试回归闸门")
    print("=" * 66)
    print(f"  collected {counts['collected']}  failed {counts['failed']}  "
          f"passed {counts['passed']}")
    print(f"  基线存量失败: {len(baseline)}")
    print(f"  已修复的基线失败: {len(fixed)}")
    print(f"  新增失败: {len(new)}")
    print()
    if new:
        rows = [{**{"node_id": n}, **attribute(n)} for n in new]
        print("  ❌ 新增失败（本次改动引入，需处理）:")
        for r in rows:
            tag = "  ⚠️ 疑似过时测试断言" if _likely_stale(r["node_id"]) else ""
            print(f"    - {r['node_id']}{tag}")
            if r["commit"]:
                print(f"        最后改动 {r['commit']} {r['author']} — {r['subject']}")
        print()
        print(f"  详见 {REPORT_MD.relative_to(PROJECT_ROOT)}")
    else:
        print("  ✅ 无新增失败")
    if fixed:
        print(f"  ℹ️  有 {len(fixed)} 个基线失败已修复，可 --update-baseline 收敛")
    print("=" * 66)

    return 1 if new else 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main())
