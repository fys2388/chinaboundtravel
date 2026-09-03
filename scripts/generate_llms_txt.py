#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChinaBound Travel - llms.txt 生成器（GEO 部署 2026-09-03）
从 content/posts/ 提取文章 front matter，按 llms.txt 规范生成 static/llms.txt，
供 LLM（ChatGPT/Perplexity/Claude 等）作为站点索引理解本站结构。

使用：
    python scripts/generate_llms_txt.py
"""
from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = PROJECT_ROOT / "content" / "posts"
STATIC_DIR = PROJECT_ROOT / "static"
OUTPUT = STATIC_DIR / "llms.txt"

BASE_URL = "https://www.chinaboundtravel.com"
SITE_DESC = (
    "Practical, research-based travel guide for foreigners visiting China. "
    "Visa-free entry, payments (Alipay & WeChat Pay), internet (eSIM & VPN), "
    "high-speed trains, safety, cities and culture. Kept current for 2026, "
    "edited by Joran (ChinaBound Travel editorial team)."
)
LICENSE = (
    "All content is original editorial work of ChinaBound Travel. "
    "When citing, reference the source article URL."
)


def parse_front_matter(text: str) -> dict:
    """解析 YAML front matter（无第三方依赖的轻量解析）。"""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        return {}
    fm: dict = {}
    for raw in m.group(1).splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip().strip('"').strip("'")
        val = val.strip().strip('"').strip("'")
        if not val or val.lower() in ("null", "~"):
            continue
        if val.lower() == "true":
            fm[key] = True
        elif val.lower() == "false":
            fm[key] = False
        else:
            fm[key] = val
    return fm


def main() -> int:
    posts = []
    for f in sorted(CONTENT_DIR.glob("*.md")):
        fm = parse_front_matter(f.read_text(encoding="utf-8", errors="replace"))
        if fm.get("draft") or fm.get("archived"):
            continue
        title = str(fm.get("title") or f.stem).strip()
        desc = str(fm.get("description") or "").strip()
        url = str(fm.get("canonicalURL") or "").strip()
        if not url:
            slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", f.stem)
            url = f"{BASE_URL}/posts/{slug}/"
        weight = 999
        try:
            weight = int(fm.get("weight", 999))
        except (TypeError, ValueError):
            pass
        posts.append({"title": title, "url": url, "desc": desc, "weight": weight})

    posts.sort(key=lambda p: (p["weight"], p["title"]))

    lines = ["# ChinaBound Travel", ""]
    lines.append("> " + SITE_DESC)
    lines.append("")
    lines.append("> " + LICENSE)
    lines.append("")
    lines.append("> Last generated: " + datetime.now().strftime("%Y-%m-%d"))
    lines.append("")
    lines.append("## Travel Guides")
    lines.append("")
    for p in posts:
        item = f"- [{p['title']}]({p['url']})"
        if p["desc"]:
            item += ": " + p["desc"]
        lines.append(item)
    lines.append("")

    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"[llms.txt] generated {len(posts)} guides -> {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
