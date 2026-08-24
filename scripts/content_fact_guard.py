#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
content_fact_guard.py - 动态事实守卫
====================================

P1-CONTENT-TRUST-FIX-01：对动态事实（价格/时间/政策/距离等）不做编造，
只做「守卫」：
  1. 检测正文中的动态事实关键词
  2. 若无官方验证提示或 last_updated 字段，则：
     - 在文末追加验证提示（不改变任何事实内容）
     - 在 front matter 添加 last_updated（若不存在）
  3. 绝不自动修正/编造任何事实数值

规则（与内容治理一致）：
  - visa / price / ticket / opening hours / distance / duration / policy / fee 等
  - 检测到即需守卫

用法：
  python scripts/content_fact_guard.py                 # 扫描并报告
  python scripts/content_fact_guard.py --apply          # 实际添加守卫提示
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

BLOG_ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = BLOG_ROOT / "content" / "posts"

FACT_KEYWORDS = [
    "visa", "visa-free", "144-hour", "240-hour", "transit", "immigration",
    "price", "prices", "cost", "costs", "fee", "fees", "charge", "charges",
    "opening hours", "operating hours", "hours", "ticket price", "fare",
    "distance", "duration", "policy", "rules", "restriction",
    "passport", "entry requirement",
]
FACT_RE = re.compile(r"\b(" + "|".join(FACT_KEYWORDS) + r")\b", re.IGNORECASE)

VERIFY_HINT = ("*Note: visa, pricing, schedule, and policy details can change. "
               "Please verify the latest information from official sources "
               "before your trip.*")


def split_frontmatter(text: str):
    for delim in ("---", "+++"):
        ed = re.escape(delim)
        m = re.match(r"^%s\s*\n(.*?)\n%s\s*\n" % (ed, ed), text, re.DOTALL)
        if m:
            return m.group(1), text[m.end():], delim
    return None, text, ""


def has_guard(text: str, fm: str) -> bool:
    if "verify the latest information from official sources" in text.lower():
        return True
    if "last_updated" in fm or "lastmod" in fm:
        return True
    return False


def guard_article(path: Path, apply: bool = False) -> dict:
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    bom = ""
    if text.startswith("\ufeff"):
        bom = "\ufeff"
        text = text[1:]
    fm, body, delim = split_frontmatter(text)
    result = {
        "file": path.name,
        "fact_keywords": sorted(set(FACT_RE.findall(body.lower()))),
        "already_guarded": has_guard(text, fm or ""),
        "changed": False,
    }
    if fm is None:
        result["error"] = "no_frontmatter"
        return result
    if result["already_guarded"]:
        return result

    # 1) 正文末尾追加验证提示（不改变事实）
    new_body = body.rstrip()
    if VERIFY_HINT not in new_body:
        new_body = new_body + "\n\n---\n\n" + VERIFY_HINT + "\n"

    # 2) front matter 添加 last_updated（若不存在）
    new_fm = fm
    if "last_updated" not in fm and "lastmod" not in fm:
        today = datetime.now().strftime("%Y-%m-%d")
        if delim == "+++":
            new_fm = new_fm.rstrip() + f'\nlast_updated = "{today}"\n'
        else:
            new_fm = new_fm.rstrip() + f'\nlast_updated: "{today}"\n'

    if apply:
        # 统一换行：先合并 \r+\n -> \n（双CR/CRLF 归并为单换行），再处理孤立 \r -> \n。
        # 顺序不可颠倒，否则 \r\r\n 会变成 \n\n（空行）。
        new_fm = re.sub(r"\r+", "\n", re.sub(r"\r+\n", "\n", new_fm))
        new_body = re.sub(r"\r+", "\n", re.sub(r"\r+\n", "\n", new_body))
        new_text = bom + delim + "\n" + new_fm + "\n" + delim + "\n" + new_body
        # 保留 CRLF
        if raw.count(b"\r\n") > raw.count(b"\n") // 2:
            new_text = new_text.replace("\n", "\r\n")
        # 重要：newline="" 禁用换行翻译，否则 Windows 会把 \r\n 再转成 \r\r\n
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(new_text)
        result["changed"] = True
    else:
        result["changed"] = True  # 标记"需要守卫"
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="动态事实守卫")
    ap.add_argument("--apply", action="store_true", help="实际添加守卫（默认只报告）")
    args = ap.parse_args()

    results = []
    for f in sorted(POSTS_DIR.glob("*.md")):
        results.append(guard_article(f, apply=args.apply))

    need = [r for r in results if not r["already_guarded"]]
    print(f"事实守卫（{'APPLY' if args.apply else 'DRY-RUN'}）:")
    print(f"  共 {len(results)} 篇 | 需守卫 {len(need)} 篇 | 已守卫 {len(results) - len(need)} 篇")
    if need:
        print("\n  需守卫的文章:")
        for r in need[:20]:
            kws = ", ".join(r["fact_keywords"][:5])
            print(f"    {r['file'][:45]:47s} 关键词: {kws}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
