#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
content_category_normalizer.py - 全站分类体系规范化
====================================================

任务3a：梳理分类体系，合并重复分类，统一命名规范。

背景：
  - 全站 60 篇帖子中 43 篇缺少 categories，其余分类名混乱
    （"China Travel Guide"/"China Essentials"/"China Itinerary"/"Practical Travel Tips" 混用）。
  - tags 大小写/空格重复（Shanghai/shanghai、ChinaTravel/China Travel 等）。
  - content/categories/{internet,payment,visa}/ 存在独立分类页但未被文章关联。

本脚本：
  1. 定义规范分类体系（CANONICAL_CATEGORIES），与 content/categories 一致。
  2. 基于文章主题（复用 affiliate_link_builder 的主题检测 + 关键词）为
     缺少分类的文章分配规范分类。
  3. 将旧分类映射到规范分类（合并重复）。
  4. 统一 tags：去重、归一大小写（首字母大写的驼峰统一为首字母大写），
     保留原始中文/特殊 tag。
  5. 兼容 YAML(---) 与 TOML(+++) front matter。

用法：
  python scripts/content_category_normalizer.py             # dry-run 预览
  python scripts/content_category_normalizer.py --apply     # 实际写文件
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

SCRIPT_DIR = Path(__file__).resolve().parent
BLOG_ROOT = SCRIPT_DIR.parent
POSTS_DIR = BLOG_ROOT / "content" / "posts"
REPORTS_DIR = BLOG_ROOT / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(SCRIPT_DIR))

# 规范分类体系（slug -> 展示名）
CANONICAL_CATEGORIES = {
    "visa": "Visa & Entry",
    "payment": "Payments",
    "internet": "Internet & Apps",
    "transport": "Transport",
    "cities": "City Guides",
    "food": "Food & Culture",
    "travel-tips": "Travel Tips",
    "itinerary": "Itineraries",
    "news": "News & Updates",
}

# 旧分类 -> 规范分类（合并重复）
CATEGORY_MAP = {
    "china travel guide": "travel-tips",
    "china essentials": "travel-tips",
    "china itinerary": "itinerary",
    "practical travel tips": "travel-tips",
    "visa": "visa",
    "china visa": "visa",
    "visa & entry": "visa",
    "payment": "payment",
    "payments": "payment",
    "internet": "internet",
    "internet & apps": "internet",
    "transport": "transport",
    "transportation": "transport",
    "cities": "cities",
    "city guides": "cities",
    "food": "food",
    "food & culture": "food",
    "itineraries": "itinerary",
    "news": "news",
    "news & updates": "news",
}

# 主题关键词 -> 规范分类（用于缺分类文章）
THEME_KEYWORDS = {
    "visa": ["visa", "visa-free", "transit", "144-hour", "240-hour", "immigration",
             "entry requirement", "passport", "border"],
    "payment": ["payment", "alipay", "wechat pay", "paypal", "qr code", "mobile pay"],
    "internet": ["esim", "sim card", "internet", "vpn", "wifi", "data", "app", "connectivity"],
    "transport": ["train", "high-speed rail", "subway", "metro", "taxi", "airport",
                  "flight", "transfer", "station", "transport"],
    "cities": ["city", "beijing", "shanghai", "chengdu", "xian", "hangzhou", "guilin",
               "destination", "neighborhood", "bund", "great wall", "west lake"],
    "food": ["food", "cuisine", "hotpot", "noodles", "tea", "street food", "restaurant",
             "dining", "culture", "etiquette"],
    "travel-tips": ["packing", "safety", "insurance", "scam", "etiquette", "travel tips",
                    "budget", "planning", "what to bring"],
    "itinerary": ["itinerary", "day trip", "route", "7-day", "itinerary"],
    "news": ["update", "news", "monthly", "guide 2026"],
}


def normalize_tag(tag: str) -> str:
    """统一 tag 命名：去空白，首字母大写驼峰归一。保留中文/特殊。"""
    t = tag.strip()
    if not t:
        return ""
    # 全小写英文 -> 首字母大写（如 "china travel tips" -> "China Travel Tips"）
    if re.fullmatch(r"[a-z][a-z0-9 \-]*", t):
        return " ".join(w[:1].upper() + w[1:] for w in t.split())
    return t


def split_frontmatter(text: str):
    if text.startswith("\ufeff"):
        text = text[1:]
    for delim in ("---", "+++"):
        ed = re.escape(delim)
        m = re.match(r"^%s\s*\n(.*?)\n%s\s*\n" % (ed, ed), text, re.DOTALL)
        if m:
            return m.group(1), text[m.end():], delim
    return None, text, ""


def read_frontmatter_array(fm_text: str, key: str) -> list:
    """从 front matter 提取列表值（兼容 YAML 列表与内联数组）。"""
    values = []
    # 内联数组: key: ["a", "b"] 或 key = ["a","b"]
    m = re.search(rf'^{key}\s*[=:]\s*\[(.*?)\]', fm_text, re.MULTILINE | re.DOTALL)
    if m:
        values = [x.strip().strip('"').strip("'")
                  for x in m.group(1).split(",") if x.strip()]
        return values
    # YAML 列表: key:\n  - a\n  - b
    m = re.search(rf'^{key}\s*:\s*\n((?:^[ \t]*-[ \t].*\n?)+)', fm_text, re.MULTILINE)
    if m:
        values = [re.sub(r"^[ \t]*-[ \t]", "", ln).strip().strip('"').strip("'")
                  for ln in m.group(1).splitlines() if ln.strip()]
        return values
    # TOML 列表: key = ["a","b"] (同上内联) - 已覆盖
    return values


def set_frontmatter_array(fm_text: str, key: str, values: list, delim: str) -> str:
    """替换 front matter 中的列表字段为内联数组格式。"""
    quoted = ", ".join(f'"{v}"' for v in values)
    if not values:
        quoted = ""
    new_line = f'{key} = [{quoted}]' if delim == "+++" else f'{key}: [{quoted}]'
    # 移除旧的 key 行及其列表
    lines = fm_text.split("\n")
    out = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        m = re.match(rf'^{re.escape(key)}\s*[=:]\s*\[', ln)
        if m:
            # 跳过内联数组（可能多行）
            if not ln.rstrip().endswith("]"):
                while i < len(lines) and not lines[i].rstrip().endswith("]"):
                    i += 1
            i += 1
            continue
        m = re.match(rf'^{re.escape(key)}\s*:\s*$', ln)
        if m:
            i += 1
            while i < len(lines) and re.match(r"^[ \t]*-[ \t]", lines[i]):
                i += 1
            continue
        out.append(ln)
        i += 1
    # 插入位置：TOML 中顶层字段必须在任何 [table] 之前；否则追加到末尾
    insert_at = len(out)
    if delim == "+++":
        for j, ln in enumerate(out):
            if re.match(r"^\[[^\]]+\]\s*$", ln):
                insert_at = j
                break
    out.insert(insert_at, new_line)
    return "\n".join(out)


def detect_category_from_text(text: str) -> list:
    """基于标题+正文关键词推断规范分类（可多个）。

    强主题（visa/payment/internet/transport/cities/food）按关键词计数排序；
    travel-tips（安全/保险/打包/避坑）在强主题命中不足时作为主导，避免
    被正文泛化词（如 "food" 出现在安全文章）误判。
    """
    low = " ".join(re.findall(r"[A-Za-z0-9\- ]+", text)).lower()
    strong_cats = ["visa", "payment", "internet", "transport", "cities", "food"]
    scores = {}
    for cat, kws in THEME_KEYWORDS.items():
        scores[cat] = sum(1 for kw in kws if kw in low)

    strong_scored = [(c, scores.get(c, 0)) for c in strong_cats if scores.get(c, 0) > 0]
    strong_scored.sort(key=lambda x: -x[1])
    top_strong = strong_scored[0] if strong_scored else None

    # travel-tips 主导条件：命中 >=2 个 travel-tips 关键词，且其命中数 >= 最强强主题
    # （安全/保险文章常含 "food/transport" 泛化词，此时应归 travel-tips）
    tt = scores.get("travel-tips", 0)
    if tt >= 2 and (top_strong is None or tt >= top_strong[1]):
        result = ["travel-tips"]
        if top_strong:
            result.append(top_strong[0])
        return result[:2]

    result = [c for c, _ in strong_scored[:2]]
    if not result:
        if scores.get("itinerary", 0) > 0:
            result = ["itinerary"]
        else:
            result = ["travel-tips"]
    return result


def process_file(path: Path, apply: bool = False) -> dict:
    raw = path.read_bytes()
    # 记录原始换行风格（TOML front matter 对 \r\n 敏感）
    use_crlf = raw.count(b"\r\n") > raw.count(b"\n") // 2 and raw.count(b"\r\n") > 0
    text = raw.decode("utf-8", errors="ignore")
    # 统一换行为 \n（兼容 \r\n 与孤立 \r，避免残留导致 \r\r\n）
    if use_crlf or b"\r" in raw:
        text = re.sub(r"\r\n?", "\n", text)
    bom = ""
    if text.startswith("\ufeff"):
        bom = "\ufeff"
        text = text[1:]
    fm_text, body, delim = split_frontmatter(text)
    if fm_text is None:
        return {"file": path.name, "status": "no_frontmatter", "changes": 0}

    # 读取现有 categories / tags
    cats = read_frontmatter_array(fm_text, "categories")
    tags = read_frontmatter_array(fm_text, "tags")

    # 标题 + 正文用于关键词推断（正文仅取前 800 字符，减少导航/相关推荐噪音）
    title_m = re.search(r'^title\s*[=:]\s*"([^"]+)"', fm_text, re.MULTILINE)
    title_text = title_m.group(1) if title_m else ""
    desc_m = re.search(r'^description\s*[=:]\s*"([^"]+)"', fm_text, re.MULTILINE)
    desc_text = desc_m.group(1) if desc_m else ""
    inferred = detect_category_from_text(title_text + " " + desc_text + " " + body[:800])

    # 规范分类：以关键词推断为主（主题准确），旧分类能映射则补充
    new_cats = []
    # 1) 关键词推断的 top 分类优先
    for c in inferred:
        if c not in new_cats:
            new_cats.append(c)
    # 2) 旧分类映射补充（不覆盖推断出的主题）
    if cats:
        for c in cats:
            mapped = CATEGORY_MAP.get(c.lower().strip(), None)
            if mapped and mapped not in new_cats:
                new_cats.append(mapped)
    # 3) 兜底
    if not new_cats:
        new_cats = ["travel-tips"]
    # 限制最多 2 个分类（推断的主题优先，避免过度分类）
    new_cats = new_cats[:2]

    # 统一 tags
    seen, new_tags = set(), []
    for t in tags:
        nt = normalize_tag(t)
        if nt and nt.lower() not in seen:
            seen.add(nt.lower())
            new_tags.append(nt)

    # 计算变更
    changes = 0
    new_fm = fm_text
    if cats != new_cats:
        new_fm = set_frontmatter_array(new_fm, "categories", new_cats, delim)
        changes += 1
    if tags != new_tags:
        new_fm = set_frontmatter_array(new_fm, "tags", new_tags, delim)
        changes += 1

    if changes and apply:
        # 最小侵入写回：仅替换 front matter 文本，其余（body、换行）保持不变。
        # 在原始文本（保留原始换行）中定位 front matter 起止，仅替换中间内容。
        orig_text = text  # \n 归一化版本（写回时按 use_crlf 决定换行）
        new_text = bom + delim + "\n" + new_fm + "\n" + delim + "\n" + body
        # 统一写回为 LF。源文件可能因 core.autocrlf 是混合换行（\r\r\n），
        # 保留 CRLF 反而引入解析错误；LF 对 Hugo/TOML 完全兼容。
        path.write_text(new_text, encoding="utf-8", newline="\n")

    return {
        "file": path.name, "status": "updated" if changes else "ok",
        "old_categories": cats, "new_categories": new_cats,
        "old_tags_count": len(tags), "new_tags_count": len(new_tags),
        "changes": changes,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="全站分类体系规范化")
    ap.add_argument("--apply", action="store_true", help="实际写文件（默认 dry-run）")
    args = ap.parse_args(argv)

    cat_counter = Counter()
    updated = 0
    ok = 0
    rows = []
    for p in sorted(POSTS_DIR.glob("*.md")):
        r = process_file(p, apply=args.apply)
        rows.append(r)
        if r["changes"]:
            updated += 1
        else:
            ok += 1
        for c in r["new_categories"]:
            cat_counter[c] += 1

    print(f"分类规范化（{'APPLY' if args.apply else 'DRY-RUN'}）:")
    print(f"  总文章: {updated + ok} | 需更新: {updated} | 已合规: {ok}")
    print("\n  规范分类分布:")
    for c, n in sorted(cat_counter.items(), key=lambda x: -x[1]):
        print(f"    - {c}: {n} 篇")
    if not args.apply:
        print("\n  预览（前 20 篇待更新）:")
        for r in [x for x in rows if x["changes"]][:20]:
            print(f"    {r['file'][:45]:47s} cats: {','.join(r['old_categories']) or '(无)'} -> {','.join(r['new_categories'])}")

    # 保存报告
    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "mode": "apply" if args.apply else "dry_run",
        "updated": updated, "ok": ok,
        "category_distribution": dict(cat_counter),
        "rows": rows,
    }
    out = REPORTS_DIR / "content_category_report.json"
    out.write_text(__import__("json").dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  报告: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
