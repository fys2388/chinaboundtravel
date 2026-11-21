# -*- coding: utf-8 -*-
"""
news_to_topic_pool.py — 把 news_digest.json 里的时政/行业热点转成博文选题，注入 topic_pool.json。

目标：让「紧跟新闻报道时政 → 博文」这条链路自动化。news-monitor 每天抓热点，
本脚本筛选适合写博文的热点，作为 pending 选题追加进 config/topic_pool.json，
由周度 Joran 生成器（weekly-blog-update.yml）自然消费。

设计原则（最小侵入）：
  - 只追加 status=pending 的新选题；绝不修改/删除已有条目。
  - 幂等：用 news_digest 每条的 _hash 记录在 topic_pool.json 顶层
    `news_ingested_hashes`，重复运行不会重复注入同一热点。
  - 防膨胀：pending 选题数超过 MAX_PENDING 水位即停止注入（避免池子被灌满、
    也避免生成器一次性面对过多选题）。
  - 只收适合做 SEO 博文的类别（政策/目的地/行业），跳过 safety_alerts / general 噪音。
  - 标题改写成面向外国游客的 SEO 友好问句/指南式标题，不直接照抄新闻标题。

用法：
  python scripts/news_to_topic_pool.py            # dry-run，只打印将注入什么
  python scripts/news_to_topic_pool.py --apply    # 真正写入 topic_pool.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

BLOG_ROOT = Path(__file__).resolve().parent.parent
DIGEST_PATH = BLOG_ROOT / "config" / "news_digest.json"
TOPIC_POOL_PATH = BLOG_ROOT / "config" / "topic_pool.json"

# 每次运行、每个类别最多注入的选题数（防止单日某类爆量灌满池子）
PER_CATEGORY_LIMIT = 2
# topic_pool 里 pending 选题的水位上限：达到即停止注入
MAX_PENDING = 20
# 只从这些 digest 类别取材（其他类别噪音大或不适合做长文）
ELIGIBLE_CATEGORIES = ("visa_policy", "destination_news", "travel_industry")

# 噪音过滤：标题/摘要命中这些模式的热点不适合做面向游客的博文
NOISE_PATTERNS = [
    r"shipping|freight|hormuz|tanker|vessel",          # 货运/航运，非游客话题
    r"detained|detention|surveillance|espionage",       # 安全警告类，负面且需谨慎
    r"taiwan.*(independence|statement)",                # 政治敏感
    r"factory tour",                                    # 小众，暂不做
    r"weather alert|typhoon|storm",                     # 天气预警时效太短，交社媒
    r"visa.*(expire|end|tighten)",                      # 收紧/到期类，需人工判断再写
    r"investment|offshore wealth|trade agreement|fta|gdp|export",  # 投资/宏观经贸，非游客话题
    r"asia-pacific community|bilateral|diplomat|ambassador",       # 地缘外交宏观叙事
    r"for citizens|its citizens|chinese passport|emigration",      # 中国公民出境向，非外国游客入境
]

# digest 类别 → topic_pool category
CATEGORY_MAP = {
    "visa_policy": "visa",
    "destination_news": "travel",
    "travel_industry": "budget",
}


def _is_noise(text: str) -> bool:
    t = text.lower()
    if any(re.search(p, t) for p in NOISE_PATTERNS):
        return True
    # 站点是英文，含较多 CJK 字符的标题属中文源，跳过（交社媒/人工，不进英文博文池）
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    if cjk >= 4:
        return True
    return False


def _slugify_title(title: str) -> str:
    """把新闻标题改写成面向游客的 SEO 友好标题。去掉来源后缀/前缀、截断长度。"""
    # 去掉常见 " - Source" / " | Source" 来源后缀
    title = re.split(r"\s+[-|]\s+", title)[0].strip()
    # 去掉结尾的标点
    title = title.rstrip("?:!.,")
    # 去掉开头残留的媒体来源前缀，如 "CGTN:" / "Reuters:" / "BBC News -"
    title = re.sub(r"^[A-Z][A-Za-z.\s]{0,20}:\s+", "", title)
    return title


def _geo_for_category(category: str) -> str:
    # 简单轮转分配 geo，保证三个主要市场都有覆盖
    return {"visa": "US", "travel": "AU", "budget": "EU"}.get(category, "US")


def collect_candidates(digest: dict) -> list[dict]:
    """从 digest 提取适合做博文的热点候选。"""
    seen_hashes = set()
    candidates = []
    for cat in ELIGIBLE_CATEGORIES:
        items = digest.get("digest", {}).get(cat, []) or []
        taken = 0
        for item in items:
            if taken >= PER_CATEGORY_LIMIT:
                break
            h = item.get("_hash")
            if not h or h in seen_hashes:
                continue
            title = item.get("title", "")
            summary = item.get("summary", "")
            if _is_noise(title + " " + summary):
                continue
            seen_hashes.add(h)
            pool_category = CATEGORY_MAP.get(cat, "travel")
            candidates.append({
                "source_hash": h,
                "source_category": cat,
                "pool_category": pool_category,
                "title": _slugify_title(title),
                "summary": summary,
                "url": item.get("url", ""),
                "date": item.get("date", ""),
            })
            taken += 1
    return candidates


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject news hotspots into topic_pool.json as pending topics")
    parser.add_argument("--apply", action="store_true", help="Write to topic_pool.json (default dry-run)")
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    if not DIGEST_PATH.exists():
        print(f"[news_to_topic_pool] digest not found: {DIGEST_PATH}", file=sys.stderr)
        return 0
    digest = json.loads(DIGEST_PATH.read_text(encoding="utf-8"))

    if not TOPIC_POOL_PATH.exists():
        print(f"[news_to_topic_pool] topic_pool not found: {TOPIC_POOL_PATH}", file=sys.stderr)
        return 0
    pool = json.loads(TOPIC_POOL_PATH.read_text(encoding="utf-8-sig"))

    ingested = set(pool.get("news_ingested_hashes", []) or [])
    existing_titles = {t.get("title", "").strip().lower() for t in pool.get("topics", [])}
    pending_count = sum(1 for t in pool.get("topics", []) if t.get("status") == "pending")

    candidates = collect_candidates(digest)
    print(f"[news_to_topic_pool] digest total_items={digest.get('total_items')} "
          f"candidates(after category/noise filter)={len(candidates)} "
          f"pending_watermark={pending_count}/{MAX_PENDING}")

    to_add = []
    for c in candidates:
        if pending_count + len(to_add) >= MAX_PENDING:
            print(f"[news_to_topic_pool] pending watermark reached ({MAX_PENDING}), stop injecting")
            break
        if c["source_hash"] in ingested:
            continue
        # 标题级去重（避免与池中已有选题重复）
        if c["title"].strip().lower() in existing_titles:
            continue
        to_add.append(c)

    if not to_add:
        print("[news_to_topic_pool] nothing new to inject")
        return 0

    today = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00")
    new_topics = []
    for i, c in enumerate(to_add):
        # id 用 news-<hash前8>，与现有 new-XXX / pool-XXX 不冲突
        topic = {
            "id": f"news-{c['source_hash'][:8]}",
            "title": c["title"],
            "category": c["pool_category"],
            "geo": _geo_for_category(c["pool_category"]),
            "keywords": [],  # 留空，生成器按标题自行处理
            "priority": 3,
            "status": "pending",
            "source": "news_monitor",
            "created_at": today,
            "depth": "news",
        }
        new_topics.append(topic)
        print(f"  [+{c['source_category']}] {c['title'][:70]}")

    if args.apply:
        pool.setdefault("topics", []).extend(new_topics)
        pool["news_ingested_hashes"] = sorted(ingested | {c["source_hash"] for c in to_add})
        pool["last_update"] = today
        TOPIC_POOL_PATH.write_text(
            json.dumps(pool, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"[news_to_topic_pool] APPLIED: injected {len(new_topics)} topic(s) into topic_pool.json")
    else:
        print(f"[news_to_topic_pool] DRY-RUN: would inject {len(new_topics)} topic(s). Use --apply to write.")
    return 0


if __name__ == "__main__":
    sys.exit(main())