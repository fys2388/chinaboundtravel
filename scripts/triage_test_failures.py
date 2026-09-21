"""存量测试失败分类器：把基线里的失败按根因分桶。

为什么需要它
------------
基线里有几十个存量失败，但它们不是一类东西：
  - 有的测试把「某次已知缺陷」写死成期望（stale test），仓库修好后测试永久红；
  - 有的要改内容才能修，且内容在保护区，需要人拍板（content drift）；
  - 有的是 CI 接线问题（本地有 hugo、CI 没有）；
  - 有的依赖本机凭证或外部数据。
不分桶地报「30 个失败」会让运维无从下手——修哪个、谁修、要不要人介入，全都不清楚。

本脚本纯静态分类：不跑 pytest、不联网、不改任何文件，只读基线 JSON + 测试文件
源码，按启发式给出桶 + 修复动作 + 是否可自动修复。

用法::

    python scripts/triage_test_failures.py                        # 读现有基线
    python scripts/triage_test_failures.py --baseline <path>      # 指定基线
    python scripts/triage_test_failures.py --json                 # 机器可读
    python scripts/triage_test_failures.py --write                # 写 reports/quality/

桶的判定顺序（先命中先归类）：
  1. stale-test        测试名/断言把已知缺陷写死成期望
  2. content-drift     需要修改 content/posts/ 才能修复（保护区，需人拍板）
  3. ci-wiring         失败来自 CI 环境差异（hugo 二进制缺失、编码等）
  4. env-data          依赖本机凭证 / 外部数据 / 未配置的第三方
  5. code-defect       其余，需要逐个人工看
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BASELINE = PROJECT_ROOT / "reports" / "quality" / "test_failure_baseline.json"
TESTS_DIR = PROJECT_ROOT / "tests"
OUT_MD = PROJECT_ROOT / "reports" / "quality" / "test_failure_triage.md"

BUCKET_ORDER = ["stale-test", "content-drift", "ci-wiring", "env-data", "code-defect"]

BUCKET_LABEL = {
    "stale-test": "过时测试断言（把已知缺陷写死成期望）",
    "content-drift": "内容漂移（需改 content/posts/，保护区，需人拍板）",
    "ci-wiring": "CI 接线问题（本地能过、CI 不能过）",
    "env-data": "环境/数据依赖（本机凭证或外部数据）",
    "code-defect": "代码缺陷（需逐个人工看）",
}

BUCKET_ACTION = {
    "stale-test": "改测试：用受控夹具替代「断言真实仓库当前状态」。可自动修。",
    "content-drift": "先由人决定「恢复内容」还是「更新测试」，然后改。不可自动修。",
    "ci-wiring": "在 workflow 里补齐依赖（如安装 hugo），或让测试在缺失时 skip。可自动修。",
    "env-data": "配置对应 secret / 凭证；无法配置则改成显式跳过。半自动。",
    "code-defect": "逐个人工排查。不可自动修。",
}

# 桶 1：stale-test。特征是把某个具体的历史状态写死成期望。
STALE_TEST_PATTERNS = (
    "title_unchanged",
    "urls_unchanged",
    "unchanged_vs_head",
    "url_unchanged",
    "destination_unchanged",
    "cta_unchanged",
    "cta_not_modified",
    "cta_untouched",
    "rev002_unchanged",
    "no_new_cta_added",
    "required_h2_structure",
    "recommended_tools_table",
    "recommended_services_table",
    "title_and_h2_structure_retained",
    "title_and_description_updated",
    "titles_differ",
    "descriptions_differ",
    "title_unchanged",
)

# 桶 2：content-drift。测试名里直接点名了内容语义。
CONTENT_DRIFT_PATTERNS = (
    "title_and_h2_structure",
    "required_h2_structure",
    "recommended_tools_table",
    "recommended_services_table",
    "titles_differ",
    "descriptions_differ",
    "144h_title_and_description",
    "candidate_has_affiliate_partners",
    "rev002_cta",
    "rev002_partner",
    "rev002_placement",
)

# 桶 3：ci-wiring。这些测试文件依赖 hugo 二进制或会踩 Windows 编码坑。
HUGO_DEPENDENT_FILES = (
    "test_growth12_revenue_experiment.py",
    "test_growth12b_revenue_experiment.py",
    "test_growth07b_technical_seo.py",
    "test_growth22_payment_release.py",
    "test_internal_links.py",
    "test_og_tags.py",
    "test_robots.py",
    "test_travelpayouts_drive.py",
)

# 桶 4：env-data。依赖本机凭证或外部服务状态。
ENV_DATA_PATTERNS = (
    "secret_name_contract",
    "social_analytics",
    "content_agent",
    "inventory_has_100_items",
    "inventory_platform_balance",
    "local_kpi",
    "site_health_dashboard",
    "audit_summary_md",
)


def _load_baseline(path: Path) -> List[str]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data.get("failures", []))


def _test_file(node_id: str) -> Path:
    m = re.match(r"^([^:]+)\.py::", node_id)
    return TESTS_DIR / m.group(1).replace(".", "/") + ".py" if m else TESTS_DIR / "_unknown.py"


def _test_name(node_id: str) -> str:
    return node_id.split("::", 1)[1] if "::" in node_id else node_id


def _file_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def classify(node_id: str) -> Tuple[str, str]:
    """返回 (bucket, evidence)。"""
    name = _test_name(node_id)
    fname = _test_file(node_id).name
    src = _file_text(_test_file(node_id))

    # 1) stale-test：名字命中「写死期望」特征
    for pat in STALE_TEST_PATTERNS:
        if pat in name:
            return "stale-test", f"测试名含 `{pat}`"

    # 2) content-drift：需要改保护区内容
    for pat in CONTENT_DRIFT_PATTERNS:
        if pat in name:
            return "content-drift", f"测试名含 `{pat}`，修复需改 content/posts/"

    # 3) ci-wiring：hugo 依赖文件
    if fname in HUGO_DEPENDENT_FILES:
        return "ci-wiring", f"测试文件 `{fname}` 依赖 hugo 二进制"

    # 4) env-data
    for pat in ENV_DATA_PATTERNS:
        if pat in name or pat in fname:
            return "env-data", f"命中环境/数据特征 `{pat}`"
    if re.search(r"git show|subprocess\.run", src) and "HEAD:" in src:
        return "ci-wiring", "测试用 `git show HEAD:` 比对工作区，仅脏工作区会红"

    return "code-defect", "无自动特征命中，需人工看"


def _top_evidence(items: List[str]) -> str:
    return items[0] if items else ""


def main() -> int:
    parser = argparse.ArgumentParser(description="存量测试失败分类器（只读）")
    parser.add_argument("--baseline", type=Path, default=BASELINE)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write", action="store_true", help="写 markdown 报告到 reports/quality/")
    args = parser.parse_args()

    baseline = args.baseline if args.baseline.is_absolute() else PROJECT_ROOT / args.baseline
    failures = _load_baseline(baseline)

    buckets: Dict[str, List[str]] = defaultdict(list)
    details: Dict[str, List[Dict]] = defaultdict(list)
    for node_id in failures:
        bucket, evidence = classify(node_id)
        buckets[bucket].append(node_id)
        details[bucket].append({"node_id": node_id, "evidence": evidence})

    summary = {
        "total": len(failures),
        "buckets": {b: len(v) for b, v in buckets.items()},
        "auto_fixable": sum(len(buckets[b]) for b in ("stale-test", "ci-wiring")),
        "needs_human": sum(len(buckets[b]) for b in ("content-drift",)),
    }

    if args.json:
        print(json.dumps({
            "summary": summary,
            "buckets": {b: details[b] for b in BUCKET_ORDER if details[b]},
        }, ensure_ascii=False, indent=2))
        return 0

    if args.write:
        lines = [
            "# 存量测试失败分类",
            "",
            f"总数: {summary['total']}  |  可自动修: {summary['auto_fixable']}  "
            f"|  需人拍板: {summary['needs_human']}",
            "",
        ]
        for b in BUCKET_ORDER:
            if not details[b]:
                continue
            lines += [
                f"## {b} — {BUCKET_LABEL[b]}（{len(details[b])}）",
                "",
                f"**修复动作**: {BUCKET_ACTION[b]}",
                "",
            ]
            for d in details[b]:
                lines.append(f"- `{d['node_id']}`")
                lines.append(f"  - {_test_file(d['node_id']).relative_to(PROJECT_ROOT)} — {d['evidence']}")
            lines.append("")
        OUT_MD.write_text("\n".join(lines), encoding="utf-8")
        print(f"已写 {OUT_MD.relative_to(PROJECT_ROOT)}")

    print("=" * 66)
    print("  存量测试失败分类")
    print("=" * 66)
    print(f"  总数: {summary['total']}")
    print(f"  可自动修: {summary['auto_fixable']}   需人拍板: {summary['needs_human']}")
    print()
    for b in BUCKET_ORDER:
        if not details[b]:
            continue
        print(f"  [{len(details[b]):2d}] {b:15s} {BUCKET_LABEL[b]}")
        for d in details[b][:6]:
            print(f"        - {d['node_id'].split('::')[1]}")
        if len(details[b]) > 6:
            print(f"        …… 另 {len(details[b]) - 6} 个")
        print()
    print(f"  完整报告: python scripts/triage_test_failures.py --write")
    print("=" * 66)
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main())
