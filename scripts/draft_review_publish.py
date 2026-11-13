#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
draft_review_publish.py — 草稿自主审核发布 gate

自主决定/优化/修复：agent 在此判断 content/content/drafts/ 下的草稿是否达到
发布标准（质量 + 事实 + 非重复）。达标草稿可发布，不达标留待人工（绝不盲目发）。

默认 dry-run（只审核并输出结论）。--apply 才执行发布（draft:false + 移入
content/posts/ + slug 清理）。当前所有草稿均为旧 attempt3（2026-06-06），
主题与已有正式文章重复且存在质量问题，预期全部判为「不达标，留待人工」。

发布标准（全部满足才发布）：
  1. draft == "true"（仅处理未发布草稿）
  2. 无质量问题（标题截断 / 正文重复 **Title: / 占位符 / 空链接 / 缺 Alt / 字数过少）
  3. 无事实问题（过时事实标记，如 144-hour 未同步 240-hour）
  4. 非重复（标题关键词与已有 content/posts/ 文章高度重叠）

用法：
  python scripts/draft_review_publish.py          # dry-run 审核
  python scripts/draft_review_publish.py --apply  # 发布达标草稿
"""

import argparse
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BLOG_ROOT = SCRIPT_DIR.parent
DRAFTS_DIR = BLOG_ROOT / "content" / "content" / "drafts"
POSTS_DIR = BLOG_ROOT / "content" / "posts"

# 过时事实标记（未同步 240 的草稿）
STALE_FACT_MARKERS = (
    "144-hour", "144 hour", "144 hours",
    "6-day visa-free transit", "6 day visa-free",
)
# 质量问题标记
QUALITY_ISSUE_MARKERS = ("{{", "TODO", "XXX", "lorem ipsum", "**Title:")

# 停用词（重复性关键词提取用）
_STOPWORDS = {
    "the", "a", "an", "to", "of", "for", "in", "on", "and", "or", "with",
    "while", "around", "guide", "china", "chinese", "travel", "traveling",
    "traveling", "travellers", "travellers", "california", "kids", "kid",
    "native", "getting", "into", "kingdom", "based", "years", "experience",
}


# 人工核实的重复映射：草稿 slug -> 已存在的正式文章。
# 启发式标题词匹配会漏判同主题不同标题词的草稿（如 "Safety Tips Guide" vs
# "Is China Safe for Tourists" 仅共享 "safety" 一词），此处登记经人工复核确认的重复。
EXPLICIT_DUPES = {
    "safety-tips-guide": "2026-07-16-is-china-safe-for-tourists-2026-honest-safety-assessment.md",
}


def _parse_frontmatter(text: str) -> dict:
    """提取 frontmatter 字段（简单 key: value 解析）。

    去除 UTF-8 BOM（部分草稿文件带 BOM，导致 ^--- 不匹配、title 提取失败）。
    """
    fm = {}
    text = text.lstrip("\ufeff")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        return fm
    for line in m.group(1).splitlines():
        mm = re.match(r"^(\w+):\s*(.+)$", line.strip())
        if mm:
            fm[mm.group(1)] = mm.group(2).strip().strip('"')
    return fm


def _keywords(title: str) -> set:
    """标题关键词（去停用词）。"""
    words = re.findall(r"[a-z]{4,}", title.lower())
    return {w for w in words if w not in _STOPWORDS}


def review_draft(path: Path) -> dict:
    """审核单篇草稿，返回 {path, title, slug, issues, reasons, pass}。"""
    text = path.read_text(encoding="utf-8", errors="ignore")
    fm = _parse_frontmatter(text)
    title = fm.get("title", "")
    slug = fm.get("slug", path.stem)
    draft = fm.get("draft", "true").lower()

    issues = []
    reasons = []

    # 1. 仅处理未发布草稿
    if draft != "true":
        reasons.append(f"非草稿(draft={draft})")

    # 2. 质量问题
    body = text.split("---", 2)[-1] if text.count("---") >= 2 else text
    if title.endswith("...") or len(title) > 80:
        issues.append("标题截断")
    if "**Title:" in body:
        issues.append("正文重复 **Title:")
    for m in QUALITY_ISSUE_MARKERS:
        if m in body:
            issues.append(f"占位/异常标记:{m}")
    if re.search(r"\]\(\s*\)", body):
        issues.append("空链接")
    word_count = len(re.findall(r"\w+", body))
    if word_count < 600:
        issues.append(f"字数过少({word_count})")

    # 3. 过时事实
    for m in STALE_FACT_MARKERS:
        if m.lower() in body.lower():
            issues.append(f"过时事实:{m}")
            break

    # 4. 重复性：标题关键词 vs 已有 posts 文件名
    kws = _keywords(title)
    dup_hits = []
    if kws:
        for post in POSTS_DIR.glob("*.md"):
            if post.name.startswith("."):
                continue
            post_kws = _keywords(post.stem)
            overlap = len(kws & post_kws)
            if overlap >= 2 and overlap >= len(kws) * 0.6:
                dup_hits.append((post.name, overlap))
    if dup_hits:
        dup_hits.sort(key=lambda x: -x[1])
        issues.append(f"主题重复:{dup_hits[0][0]}")
    elif slug in EXPLICIT_DUPES:
        issues.append(f"主题重复(人工核实):{EXPLICIT_DUPES[slug]}")

    pass_ = (not issues) and not reasons
    if not pass_:
        reasons.extend(issues)
    return {
        "path": str(path.relative_to(BLOG_ROOT)),
        "title": title,
        "slug": slug,
        "issues": issues,
        "reasons": reasons,
        "pass": pass_,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="发布达标草稿")
    args = ap.parse_args()

    if not DRAFTS_DIR.is_dir():
        print(f"无草稿目录: {DRAFTS_DIR}")
        return 0

    drafts = sorted(DRAFTS_DIR.glob("*.md"))
    if not drafts:
        print("无草稿待审")
        return 0

    results = [review_draft(p) for p in drafts]
    ready = [r for r in results if r["pass"]]
    blocked = [r for r in results if not r["pass"]]

    print(f"=== 草稿自主审核 ({len(drafts)} 篇) ===")
    for r in results:
        flag = "✅ 达标" if r["pass"] else "⛔ 不达标"
        print(f"\n{flag}  {r['path']}")
        if not r["pass"]:
            for why in r["reasons"]:
                print(f"   - {why}")

    print(f"\n达标 {len(ready)} 篇 / 不达标 {len(blocked)} 篇")

    if not args.apply:
        print("\n[dry-run] 未发布。用 --apply 发布达标草稿。")
        return 0

    if not ready:
        print("无达标草稿可发布，全部留待人工（不盲目发布）。")
        return 0

    # --apply：发布达标草稿（draft:false + git mv 到 content/posts/ + slug 清理）
    for r in ready:
        src = Path(r["path"])
        if not src.exists():
            continue
        text = src.read_text(encoding="utf-8", errors="ignore")
        # 清理文件名 slug（去 attempt3 / guide 后缀）
        stem = src.stem
        new_stem = re.sub(r"-attempt\d+$", "", stem)
        new_stem = re.sub(r"-guide$", "", new_stem)
        dst = POSTS_DIR / f"{new_stem}.md"
        # draft:false
        text = re.sub(r'^(draft:\s*)"true"', r'\1"false"', text, flags=re.MULTILINE)
        dst.write_text(text, encoding="utf-8")
        src.unlink()
        print(f"  发布: {r['path']} -> content/posts/{new_stem}.md")

    print("\n注意: 已发布草稿需人工复核 canonical/slug/SEO 后推送。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
