#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
policy_content_sync.py — 官方政策变化 → 同步既有博文（过境免签事实）

在 news_monitor.py 检测到官方公告变化（policy_change）后运行，
把 content/posts/ 下博文里的**过时过境免签事实**（144 小时）更新为官方最新值
（240 小时，来自 config/official_policy_state.json 的官方事实签名）。

安全性（硬性）：
  - **只改正文里的小写事实文本**（"144-hour" / "144 hours"），
    用负向断言排除 slug/URL/连字符（如 /posts/144-hour-visa-free-transit-guide/），
    绝不动 URL、slug、canonical、content_id、内链锚文本（大写 "144-Hour" 不匹配）。
  - 幂等：替换后再跑一次无任何变化。
  - 默认 dry-run：只打印报告，不写文件。--apply 才实际写入。
  - 国家数（55+/53 国→57 国）、"6 天→10 天"、删除"240 试点"错误表述，
    属核心指南篇的精细修订，交给人工/核心篇处理，本脚本不做（避免误伤）。

用法：
  python scripts/policy_content_sync.py                  # dry-run（推荐，先看报告）
  python scripts/policy_content_sync.py --apply          # 实际写入
  python scripts/policy_content_sync.py --social         # 同时生成政策更新社媒帖文案
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BLOG_ROOT = SCRIPT_DIR.parent
CONFIG_DIR = BLOG_ROOT / "config"
CONTENT_DIR = BLOG_ROOT / "content" / "posts"
DIGEST_PATH = CONFIG_DIR / "news_digest.json"
STATE_PATH = CONFIG_DIR / "official_policy_state.json"
SOCIAL_QUEUE_PATH = CONFIG_DIR / "policy_social_queue.json"

# 官方过境免签时长锚点（用于确认官方事实已就位、以及目标值）
DEFAULT_FACTS = {"hours": 240}

# 过时 → 更新 的精确替换（大小写敏感；小写事实文本，锚文本大写不匹配）
# 负向断言 (?<![-\w.]) ... (?![-\w])：前后不能是连字符/单词字符/点，
# 从而跳过 slug/URL（如 144-hour-visa-free-transit-guide 前后是 / 或 -）。
REPLACEMENTS = [
    (re.compile(r"(?<![-\w.])144\s*-\s*hour\b(?![-\w])"), "240-hour"),
    (re.compile(r"(?<![-\w.])144\s*hours\b(?![-\w])"), "240 hours"),
    (re.compile(r"(?<![-\w.])144\s*hour\b(?!s)(?![-\w])"), "240 hour"),
]

# 链接锚文本（[ ... ] 内）的 "144-Hour" / "144 - Hour" → "240-Hour" / "240 - Hour"。
# 只动 [] 内的文字，URL 在 ( ... ) 内完全不动（slug 保留，避免断链）。
ANCHOR_RE = re.compile(r"\[([^\]]*?)\b144\s*-\s*Hour\b([^\]]*?)\]")


def _fix_anchor(m):
    return "[" + m.group(1).replace("144-Hour", "240-Hour").replace("144 - Hour", "240 - Hour") + m.group(2) + "]"


def load_json(path: Path):
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def official_facts() -> dict:
    """返回官方事实签名（hours 优先），否则默认。"""
    state = load_json(STATE_PATH)
    facts = state.get("facts", {}) or {}
    if facts.get("hours"):
        return facts
    # 回退到 digest 里的 official_facts
    digest = load_json(DIGEST_PATH)
    d_facts = digest.get("official_facts", {}) or {}
    if d_facts.get("hours"):
        return d_facts
    return dict(DEFAULT_FACTS)


def sync_content(apply: bool = False) -> dict:
    """扫描博文，替换过时过境免签时长事实。返回统计。"""
    target_hours = official_facts().get("hours", 240)
    stats = {"files_scanned": 0, "files_changed": 0, "total_replacements": 0, "files": []}

    if not CONTENT_DIR.exists():
        print(f"[WARN] content/posts not found: {CONTENT_DIR}")
        return stats

    for md in sorted(CONTENT_DIR.glob("*.md")):
        stats["files_scanned"] += 1
        text = md.read_text(encoding="utf-8")
        orig = text
        file_repls = 0
        for rx, repl in REPLACEMENTS:
            text, n = rx.subn(repl, text)
            file_repls += n
            stats["total_replacements"] += n
        # 链接锚文本大写变体（URL 在 () 内不动）
        text, n = ANCHOR_RE.subn(_fix_anchor, text)
        file_repls += n
        stats["total_replacements"] += n
        if file_repls and text != orig:
            stats["files_changed"] += 1
            stats["files"].append({"file": md.name, "replacements": file_repls})
            if apply:
                md.write_text(text, encoding="utf-8")
                print(f"  [APPLY] {md.name}: {file_repls} replacement(s)")
            else:
                print(f"  [DRY]  {md.name}: {file_repls} replacement(s)")

    return stats


def build_social_caption(facts: dict) -> str:
    """生成"政策更新"社媒帖文案（英文），供发布/人工确认。"""
    h = facts.get("hours", 240)
    c = facts.get("countries")
    p = facts.get("ports")
    prov = facts.get("provinces")
    parts = [
        f"⚠️ CHINA TRANSIT POLICY UPDATE",
        f"",
        f"China's visa-free transit is now **{h} hours ({h // 24} days)**.",
    ]
    if c:
        parts.append(f"It applies to citizens of **{c} countries**.")
    if prov:
        parts.append(f"It covers **{prov} provinces**.")
    if p:
        parts.append(f"Through **{p} designated ports**.")
    parts += [
        f"",
        f"Requirements: confirmed onward ticket to a third country + passport valid 3+ months.",
        f"Always confirm with official sources (NIA / State Council) before travel.",
        f"",
        f"Full guide → link in bio",
        f"#ChinaTravel #ChinaVisa #VisaFree #VisitChina",
    ]
    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser(description="Sync stale visa-free transit facts in blog posts")
    parser.add_argument("--apply", action="store_true", help="Actually write files (default dry-run)")
    parser.add_argument("--social", action="store_true", help="Also generate policy-update social caption")
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    facts = official_facts()
    digest = load_json(DIGEST_PATH)
    change = digest.get("policy_change")

    print("=" * 60)
    print("ChinaBound Travel - Policy Content Sync")
    print(f"Mode: {'APPLY' if args.apply else 'DRY RUN'} | Official facts: {facts}")
    if change:
        print(f"policy_change detected: {json.dumps(change.get('changed_fields', {}), ensure_ascii=False)}")
    else:
        print("policy_change: none (no official change since last run)")
    print("=" * 60)

    stats = sync_content(apply=args.apply)

    print("\n── Summary ──")
    print(f"Scanned {stats['files_scanned']} posts | changed {stats['files_changed']} | total replacements {stats['total_replacements']}")
    if stats["files_changed"] and not args.apply:
        print("(dry-run: run with --apply to write)")

    # 社媒帖子文案（政策更新）
    if args.social or change:
        caption = build_social_caption(facts)
        queue = {"generated_at": datetime.now(timezone.utc).isoformat(),
                 "caption": caption,
                 "facts": facts,
                 "policy_change": change,
                 "status": "pending_review"}
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(SOCIAL_QUEUE_PATH, "w", encoding="utf-8") as f:
                json.dump(queue, f, ensure_ascii=False, indent=2)
            print(f"\n[OK] Policy-update social caption written to {SOCIAL_QUEUE_PATH} (pending review, not auto-posted)")
            print("── Caption ──")
            print(caption)
        except Exception as e:
            print(f"  [WARN] write social queue failed: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
