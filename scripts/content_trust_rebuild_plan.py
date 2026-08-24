#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P1-CONTENT-TRUST-REBUILD-PLAN-01 (阶段1: 只读审计)
==================================================

基于 CONTENT_TRUST_AUDIT.csv 生成 2.0 Editorial Voice 重构计划。

生成队列（reports/content_rebuild/）：
  - VOICE_FIX_PREVIEW.csv      品牌风险修复预览（第一人称→编辑部口吻）
  - FACT_CHECK_QUEUE.csv       事实风险人工核对队列（价格/时间/政策）
  - AI_HALLUCINATION_QUEUE.csv AI幻觉修复队列（绝对化/无来源数据）
  - LANGUAGE_FIX_QUEUE.csv     语言修复队列（中文残留）

要求：
  - 禁止修改任何 content 文件（只读审计）
  - 保持 URL / slug / canonical / content_id / SEO metadata 不变
  - 输出统计：修改数量预测、高风险文章TOP20、自动修复比例、人工审核比例

用法：
  python scripts/content_trust_rebuild_plan.py
"""
from __future__ import annotations

import csv
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

BLOG_ROOT = Path(__file__).resolve().parent.parent
AUDIT_CSV = BLOG_ROOT / "reports" / "content_audit" / "CONTENT_TRUST_AUDIT.csv"
OUT_DIR = BLOG_ROOT / "reports" / "content_rebuild"
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_FILES = {
    "voice": OUT_DIR / "VOICE_FIX_PREVIEW.csv",
    "fact": OUT_DIR / "FACT_CHECK_QUEUE.csv",
    "hallucination": OUT_DIR / "AI_HALLUCINATION_QUEUE.csv",
    "language": OUT_DIR / "LANGUAGE_FIX_QUEUE.csv",
}
SUMMARY_OUT = OUT_DIR / "REBUILD_PLAN_SUMMARY.md"


def load_audit_rows() -> list[dict]:
    rows = []
    with open(AUDIT_CSV, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            rows.append(r)
    return rows


def extract_file_location(location: str) -> tuple[str, str]:
    """从 'xxx.md:L26' 拆出 (文件名, 行号)。"""
    m = re.match(r"(.+?\.md):?(.*)", location)
    if m:
        return m.group(1), m.group(2)
    return location, ""


def build_queues(rows: list[dict]) -> dict:
    """按 issue_type 分派到 4 个修复队列。"""
    queues = {"voice": [], "fact": [], "hallucination": [], "language": []}

    for r in rows:
        itype = r["issue_type"]
        fname, lineno = extract_file_location(r["location"])
        base = {
            "content_id": r["content_id"],
            "title": r["title"],
            "file": fname,
            "line": lineno,
            "risk_level": r["risk_level"],
            "suggestion": r["suggestion"],
            "auto_fix_possible": r["auto_fix_possible"],
        }
        if itype == "品牌风险":
            queues["voice"].append(base)
        elif itype == "事实风险":
            queues["fact"].append(base)
        elif itype == "AI幻觉":
            queues["hallucination"].append(base)
        elif itype == "中文残留":
            queues["language"].append(base)
        # SEO问题 不进入修复队列（SEO metadata 保持不变），仅统计

    return queues


def top_risky_articles(rows: list[dict], n: int = 20) -> list[tuple[str, str, int]]:
    """高风险文章 TOP20（按问题数量加权：HIGH×2 + MEDIUM×1）。"""
    score = Counter()
    for r in rows:
        w = 2 if r["risk_level"] == "HIGH" else 1
        score[r["content_id"]] += w
    titles = {}
    for r in rows:
        titles.setdefault(r["content_id"], r["title"])
    ranked = sorted(score.items(), key=lambda x: -x[1])[:n]
    return [(cid, titles.get(cid, ""), s) for cid, s in ranked]


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    rows = load_audit_rows()
    queues = build_queues(rows)

    # 写队列 CSV
    voice_fields = ["content_id", "title", "file", "line", "risk_level",
                    "suggestion", "auto_fix_possible"]
    write_csv(OUT_FILES["voice"], queues["voice"], voice_fields)
    write_csv(OUT_FILES["fact"], queues["fact"], voice_fields)
    write_csv(OUT_FILES["hallucination"], queues["hallucination"], voice_fields)
    write_csv(OUT_FILES["language"], queues["language"], voice_fields)

    # ---- 统计 ----
    total_issues = len(rows)
    auto_fixable = sum(1 for r in rows if r["auto_fix_possible"] == "yes")
    manual_required = total_issues - auto_fixable

    # 修改数量预测：修复队列中的问题（voice/hallucination/language 可自动，fact 需人工）
    predicted_voice = len(queues["voice"])
    predicted_halluc = len(queues["hallucination"])
    predicted_lang = len(queues["language"])
    predicted_fact = len(queues["fact"])
    predicted_total = predicted_voice + predicted_halluc + predicted_lang + predicted_fact

    auto_in_queues = sum(1 for q in ("voice", "hallucination", "language")
                         for r in queues[q] if r["auto_fix_possible"] == "yes")
    manual_in_queues = predicted_total - auto_in_queues

    risky = top_risky_articles(rows)

    # 各文章修改预估
    per_article = defaultdict(lambda: {"voice": 0, "fact": 0, "hallucination": 0, "language": 0})
    for qname, qrows in queues.items():
        for r in qrows:
            per_article[r["content_id"]][qname] += 1
    articles_affected = len(per_article)

    # ---- Summary MD ----
    lines = [
        "# P1-CONTENT-TRUST-REBUILD-PLAN-01 重构计划（阶段1 只读审计）",
        "",
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 概述",
        "",
        f"- 审计问题总数: **{total_issues}**",
        f"- 涉及文章数: **{articles_affected}**",
        f"- 预计修改问题数: **{predicted_total}**（voice+hallucination+language+fact 队列）",
        "",
        "> 本阶段为**只读**：未修改任何 content 文件。",
        "> 保持 **URL / slug / canonical / content_id / SEO metadata** 不变。",
        "",
        "## 修复队列",
        "",
        "| 队列 | 问题数 | 自动修复 | 人工审核 | 说明 |",
        "| :--- | :--- | :--- | :--- | :--- |",
        f"| VOICE_FIX_PREVIEW | {predicted_voice} | {sum(1 for r in queues['voice'] if r['auto_fix_possible']=='yes')} | {predicted_voice - sum(1 for r in queues['voice'] if r['auto_fix_possible']=='yes')} | 第一人称→编辑部口吻 |",
        f"| AI_HALLUCINATION | {predicted_halluc} | {sum(1 for r in queues['hallucination'] if r['auto_fix_possible']=='yes')} | {predicted_halluc - sum(1 for r in queues['hallucination'] if r['auto_fix_possible']=='yes')} | 绝对化/无来源数据 |",
        f"| LANGUAGE_FIX | {predicted_lang} | {sum(1 for r in queues['language'] if r['auto_fix_possible']=='yes')} | {predicted_lang - sum(1 for r in queues['language'] if r['auto_fix_possible']=='yes')} | 中文残留 |",
        f"| FACT_CHECK_QUEUE | {predicted_fact} | 0 | {predicted_fact} | 价格/时间/政策 人工核对 |",
        "",
        "## 修改数量预测",
        "",
        f"- **预计总修改问题数**: {predicted_total}",
        f"- **可自动修复**: {auto_in_queues}（{round(auto_in_queues/max(predicted_total,1)*100,1)}%）",
        f"- **需人工审核**: {manual_in_queues}（{round(manual_in_queues/max(predicted_total,1)*100,1)}%）",
        "",
        "## 高风险文章 TOP20",
        "",
        "| # | content_id | 文章 | 风险分 |",
        "| :--- | :--- | :--- | :--- |",
    ]
    for i, (cid, title, s) in enumerate(risky, 1):
        t = title[:50] if title else "(无标题)"
        lines.append(f"| {i} | {cid} | {t} | {s} |")

    lines += ["", "## 每篇文章修改预估（前10）", "",
              "| 文章 | voice | hallucination | language | fact | 合计 |",
              "| :--- | :--- | :--- | :--- | :--- | :--- |"]
    for cid, counts in sorted(per_article.items(), key=lambda x: -sum(x[1].values()))[:10]:
        title = next((r["title"] for r in rows if r["content_id"] == cid), cid)[:40]
        total = sum(counts.values())
        lines.append(f"| {title} | {counts['voice']} | {counts['hallucination']} | "
                     f"{counts['language']} | {counts['fact']} | {total} |")
    SUMMARY_OUT.write_text("\n".join(lines), encoding="utf-8")

    # ---- 控制台输出 ----
    print(f"重构计划（阶段1 只读）完成")
    print(f"  修改数量预测: {predicted_total} 个问题")
    print(f"  自动修复比例: {auto_in_queues}/{predicted_total} ({round(auto_in_queues/max(predicted_total,1)*100,1)}%)")
    print(f"  人工审核比例: {manual_in_queues}/{predicted_total} ({round(manual_in_queues/max(predicted_total,1)*100,1)}%)")
    print(f"  涉及文章: {articles_affected} 篇")
    print(f"\n  高风险文章 TOP20:")
    for i, (cid, title, s) in enumerate(risky, 1):
        print(f"    {i:2}. {cid} (风险分{s}) {title[:40]}")
    print(f"\n  输出:")
    for name, p in OUT_FILES.items():
        print(f"    - {p.name}: {len(queues[name])} 条")
    print(f"    - REBUILD_PLAN_SUMMARY.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
