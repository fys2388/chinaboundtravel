#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SEO 结构化数据与 SEO 基线审计。

只读。可 import 也可作 CLI：
  python scripts/seo_structured_data_audit.py --build public --json
  python scripts/seo_structured_data_audit.py --build public --fail

用途：把「结构化数据覆盖率」变成可实测、可入 CI 的事实。
历史问题（2026-09-18 修复）：
  1. 正则要求引号 —— Hugo/PaperMod 会把无特殊字符的属性渲染成无引号形式
     （<meta charset=utf-8>、<link rel=canonical href=...>、
     <script type=application/ld+json>），要求 href="..." 或 type="..."
     的审计会静默漏掉全部命中，报告「覆盖率 0%」这种假结论。
     本脚本所有属性匹配同时接受 双引号 / 单引号 / 无引号 三种形式。
  2. 旧 site_health_audit（2026-08-31）报「缺 WebSite 结构化数据 / 缺
     BreadcrumbList / 首页缺 canonical」，而实测 WebSite 在 287 页、
     BreadcrumbList 在 105 页、首页 canonical 存在——那份结论已陈旧 18 天。

额外发现（2026-09-18）：content/posts 有 2 篇文章把 {{< soft-recommend >}}
shortcode 写进了 front-matter 的 description 字段。Hugo 只在正文渲染
shortcode，front-matter 是纯文本，于是原始语法泄漏进 <meta name=description>。
本脚本把这类残留单独报告为 template_residue。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Hugo 会把无特殊字符的属性渲染成无引号形式。三种形式都必须匹配。
_QUOTED = r'(?:"([^"]*)"|\'([^\']*)\'|([^\s>]+))'
LD_TAG = re.compile(r"<script[^>]*type=" + _QUOTED + r"[^>]*>(.*?)</script>", re.S | re.I)
LINK_TAG = re.compile(r"<link[^>]+rel=" + _QUOTED + r"[^>]*>", re.I)
TYPE_RE = re.compile(r'"@type"\s*:\s*(?:"([^"]+)"|\[\s*"([^"]+)")')
# 未执行的 Hugo 模板残留：{{< name ... >}} 或 {{% name ... %}}
RESIDUE_RE = re.compile(r"\{\{\s*[<>%]\s*([a-zA-Z][\w-]*)")


def _attr(m: "re.Match", first_group: int = 1) -> str:
    """取出 _QUOTED 三种形式中的实际值。"""
    for i in range(first_group, first_group + 3):
        v = m.group(i)
        if v:
            return v
    return ""


def _is_ld_script(tag: str) -> bool:
    m = re.search(r"type=" + _QUOTED, tag, re.I)
    return bool(m) and _attr(m, 1) == "application/ld+json"


def _ld_blocks(text: str) -> List[str]:
    """返回页面里所有 JSON-LD 正文块。组 1-3 是 type 的三种引号形式，组 4 是正文。"""
    out = []
    for m in LD_TAG.finditer(text):
        if _is_ld_script(m.group(0)):
            out.append(m.group(4) or "")
    return out


def _canonical_present(text: str) -> bool:
    for m in LINK_TAG.finditer(text):
        if _attr(m, 1) == "canonical":
            return True
    return False


def _collect_types(obj: Any, out: List[str]) -> None:
    """递归收集 JSON-LD 里所有 @type（含数组形式与嵌套对象）。

    用 JSON 树遍历而不是正则：正则会漏掉数组形式里第一个之后的类型
    （"@type":["WebPage","BlogPosting"] 只匹配到 WebPage），也会漏掉
    嵌套对象里的 @type。
    """
    if isinstance(obj, dict):
        t = obj.get("@type")
        if isinstance(t, list):
            out.extend(x for x in t if isinstance(x, str))
        elif isinstance(t, str):
            out.append(t)
        for v in obj.values():
            _collect_types(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _collect_types(v, out)


def audit(build_dir: Path) -> Dict[str, Any]:
    """审计构建产物。build_dir 不存在时返回结构完整但 blocking=True 的结果。"""
    result: Dict[str, Any] = {
        "build_dir": str(build_dir),
        "pages_total": 0,
        "post_pages": 0,
        "pages_with_structured_data": 0,
        "post_pages_with_structured_data": 0,
        "structured_data_coverage_pct": 0.0,
        "post_structured_data_coverage_pct": 0.0,
        "json_blocks_valid": 0,
        "json_blocks_invalid": 0,
        "invalid_samples": [],
        "type_counts": {},
        "canonical_pages": 0,
        "canonical_coverage_pct": 0.0,
        "posts_missing_structured_data": [],
        "pages_missing_canonical": [],
        "template_residue_count": 0,
        "template_residue": [],
        "blocking": True,
        "reason": None,
    }

    if not build_dir or not build_dir.is_dir():
        result["reason"] = "构建目录不存在；请先 hugo build 再审计"
        return result

    pages = sorted(build_dir.rglob("*.html"))
    if not pages:
        result["reason"] = "构建目录里没有 HTML 页面"
        return result

    result["pages_total"] = len(pages)
    # 分页页（posts/page/2/index.html）不是文章，不应计入文章页覆盖率，
    # 否则会得出「73/74」这种被分页污染的数字。
    posts = [
        p
        for p in pages
        if "/posts/" in p.as_posix() and not re.search(r"/posts/page/\d+/", p.as_posix())
    ]
    result["post_pages"] = len(posts)

    type_counts: Dict[str, int] = {}
    for p in pages:
        text = p.read_text(encoding="utf-8", errors="ignore")
        rel = p.relative_to(build_dir).as_posix()

        blocks = _ld_blocks(text)
        if blocks:
            result["pages_with_structured_data"] += 1
            if p in posts:
                result["post_pages_with_structured_data"] += 1
        else:
            if p in posts:
                result["posts_missing_structured_data"].append(rel)

        for block in blocks:
            try:
                obj = json.loads(block.strip())
            except json.JSONDecodeError as exc:
                result["json_blocks_invalid"] += 1
                if len(result["invalid_samples"]) < 5:
                    result["invalid_samples"].append(
                        {"page": rel, "error": str(exc)[:120]}
                    )
                continue
            result["json_blocks_valid"] += 1
            found: List[str] = []
            _collect_types(obj, found)
            for t in found:
                type_counts[t] = type_counts.get(t, 0) + 1

        if _canonical_present(text):
            result["canonical_pages"] += 1
        else:
            result["pages_missing_canonical"].append(rel)

        for m in RESIDUE_RE.finditer(text):
            result["template_residue_count"] += 1
            if len(result["template_residue"]) < 10:
                start = max(0, m.start() - 60)
                result["template_residue"].append(
                    {
                        "page": rel,
                        "shortcode": m.group(1),
                        "context": text[start:m.end() + 60].replace("\n", " ")[:180],
                    }
                )

    total = result["pages_total"]
    result["structured_data_coverage_pct"] = round(
        result["pages_with_structured_data"] / total * 100, 1
    )
    result["post_structured_data_coverage_pct"] = (
        round(result["post_pages_with_structured_data"] / result["post_pages"] * 100, 1)
        if result["post_pages"]
        else 0.0
    )
    result["canonical_coverage_pct"] = round(result["canonical_pages"] / total * 100, 1)
    result["type_counts"] = dict(
        sorted(type_counts.items(), key=lambda kv: -kv[1])
    )
    result["blocking"] = (
        result["json_blocks_invalid"] > 0
        or result["template_residue_count"] > 0
        or result["structured_data_coverage_pct"] < 50.0
    )
    return result


def main(argv: List[str] = None) -> int:
    ap = argparse.ArgumentParser(description="SEO 结构化数据审计（只读）")
    ap.add_argument("--build", default="public", help="构建产物目录（默认 public）")
    ap.add_argument("--root", default=str(PROJECT_ROOT), help="仓库根目录")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--fail", action="store_true", help="存在阻塞问题时 exit 1")
    args = ap.parse_args(argv)

    build_dir = Path(args.build)
    if not build_dir.is_absolute():
        build_dir = Path(args.root) / build_dir

    r = audit(build_dir)

    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print("SEO 结构化数据审计")
        print("  构建目录        : %s" % (build_dir or "—"))
        if r.get("reason"):
            print("  ⚠️  %s" % r["reason"])
        else:
            print("  页面总数        : %d（文章页 %d）" % (r["pages_total"], r["post_pages"]))
            print("  结构化数据覆盖  : %d/%d = %.1f%%"
                  % (r["pages_with_structured_data"], r["pages_total"],
                     r["structured_data_coverage_pct"]))
            print("  文章页覆盖      : %d/%d = %.1f%%"
                  % (r["post_pages_with_structured_data"], r["post_pages"],
                     r["post_structured_data_coverage_pct"]))
            print("  canonical 覆盖  : %d/%d = %.1f%%"
                  % (r["canonical_pages"], r["pages_total"], r["canonical_coverage_pct"]))
            print("  JSON 块         : 有效 %d / 无效 %d"
                  % (r["json_blocks_valid"], r["json_blocks_invalid"]))
            print("  @type 分布      : %s" % r["type_counts"])
            if r["template_residue"]:
                print("  🔴 未执行模板残留: %d 处" % r["template_residue_count"])
                for item in r["template_residue"][:5]:
                    print("     [%s] %s" % (item["shortcode"], item["context"][:110]))
            if r["posts_missing_structured_data"]:
                print("  缺结构化数据的文章页 (%d):" % len(r["posts_missing_structured_data"]))
                for rel in r["posts_missing_structured_data"][:8]:
                    print("     %s" % rel)
        print("  阻塞问题        : %s" % ("是" if r["blocking"] else "否"))

    return 1 if (args.fail and r["blocking"]) else 0


if __name__ == "__main__":
    sys.exit(main())
