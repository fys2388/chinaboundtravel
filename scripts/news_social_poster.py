#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
news_social_poster.py — 将实时新闻 / 行业动态 / 政策更新转化为社媒帖子

与 content_rotator.py 不同，本脚本从 config/news_digest.json 读取最新新闻，
为每条新闻生成社媒文案并发布到 Buffer Worker。

与 content_rotator.py 互补：
  - content_rotator.py: 从存量博客文章分发（经典内容轮播）
  - news_social_poster.py: 从最新新闻生成帖子（时效性内容）

流程：
  1. 读取 config/news_digest.json（由 news_monitor.py 每日更新）
  2. 按分类选取优先级最高的新闻（签证政策 > 安全预警 > 行业动态 > 目的地）
  3. 为每条新闻生成 2 种风格文案（news-alert + news-insight）
  4. 通过 Buffer Worker 发布（带 UTM 追踪）
  5. 去重检查：同一新闻标题 7 天内不重复发帖
  6. 飞书通知发布结果

用法：
  python scripts/news_social_poster.py                    # 正常发布
  python scripts/news_social_poster.py --dry-run          # 仅打印文案
  python scripts/news_social_poster.py --count 3          # 每分类最多 3 条
  python scripts/news_social_poster.py --categories visa_policy,safety_alerts
"""

import argparse
import json
import os
import random
import re
import sys
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

# ── paths ────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
BLOG_ROOT = SCRIPT_DIR.parent
CONFIG_DIR = BLOG_ROOT / "config"
NEWS_DIGEST_PATH = CONFIG_DIR / "news_digest.json"
MANIFEST_PATH = CONFIG_DIR / "news_social_manifest.json"

SITE_DOMAIN = "chinaboundtravel.com"
BASE_URL = f"https://www.{SITE_DOMAIN}"

# ── 环境变量 ─────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(BLOG_ROOT / ".env")
except ImportError:
    pass

def _normalize_worker_urls():
    """归一化 Worker URLs：返回 (base_url, publish_url, new_base_url, new_publish_url)。

    环境变量 BUFFER_WORKER_URL 可能含或不含 /publish，统一处理。
    """
    raw = (os.getenv("BUFFER_WORKER_URL", "") or "").strip()
    new_raw = (os.getenv("NEW_BUFFER_WORKER_URL", "") or "").strip()

    # 基础 URL（不含 /publish，用于 /health 端点）
    if raw:
        base = raw.rstrip("/").removesuffix("/publish")
    else:
        base = "https://buffer-worker.chinaboundtravel.com"

    # 发布 URL（含 /publish）
    publish = base + "/publish"

    # NEW 默认回退到主
    if new_raw:
        new_base = new_raw.rstrip("/").removesuffix("/publish")
    else:
        new_base = base
    new_publish = new_base + "/publish"

    return base, publish, new_base, new_publish

(
    BUFFER_BASE_URL,
    BUFFER_WORKER_URL,
    NEW_BUFFER_BASE_URL,
    NEW_BUFFER_WORKER_URL,
) = _normalize_worker_urls()

# ── 发布窗口（美东时间） ────────────────────────────────────────────
try:
    from zoneinfo import ZoneInfo
    EST_TZ = ZoneInfo("America/New_York")
except Exception:
    EST_TZ = timezone(timedelta(hours=-5))

# 活跃发布窗口（EST）
ACTIVE_WINDOWS_EST = [
    {"name": "morning", "start": 8,  "end": 10},
    {"name": "lunch",   "start": 12, "end": 14},
    {"name": "prime",   "start": 20, "end": 22},
]

# 分类优先级（数值越高越优先）
CATEGORY_PRIORITY = {
    "visa_policy": 100,
    "safety_alerts": 90,
    "travel_industry": 70,
    "destination_news": 60,
    "general": 10,
}

# 分类对应文案风格
CATEGORY_STYLE_MAP = {
    "visa_policy": {
        "headline_prefix": "VISAS UPDATE",
        "hashtags": "#ChinaVisa #VisaPolicy #ChinaTravel #TravelTips",
        "emoji_prefix": "📋",
        "urgency": "IMPORTANT",
    },
    "safety_alerts": {
        "headline_prefix": "SAFETY ADVISORY",
        "hashtags": "#TravelSafety #ChinaSafety #TravelAlert #ChinaTravel",
        "emoji_prefix": "⚠️",
        "urgency": "URGENT",
    },
    "travel_industry": {
        "headline_prefix": "INDUSTRY NEWS",
        "hashtags": "#ChinaTravel #TourismNews #TravelIndustry #ChinaTourism",
        "emoji_prefix": "📊",
        "urgency": "",
    },
    "destination_news": {
        "headline_prefix": "DESTINATION UPDATE",
        "hashtags": "#ChinaTravel #VisitChina #TravelChina #ChinaDestinations",
        "emoji_prefix": "🗺️",
        "urgency": "",
    },
    "general": {
        "headline_prefix": "TRAVEL NEWS",
        "hashtags": "#ChinaTravel #TravelChina #TravelNews",
        "emoji_prefix": "📰",
        "urgency": "",
    },
}

# 7 天去重窗口
COOLDOWN_DAYS = 7


# ══════════════════════════════════════════════════════════════════════
# 工具函数
# ══════════════════════════════════════════════════════════════════════


def make_hash(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:12]


def now_est():
    return datetime.now(EST_TZ)


def active_window_est(dt=None):
    dt = dt or now_est()
    for w in ACTIVE_WINDOWS_EST:
        if w["start"] <= dt.hour < w["end"]:
            return w["name"]
    return None


def clean_title(title: str, max_len: int = 100) -> str:
    """清理新闻标题：去 HTML 实体、截断。"""
    if not title:
        return ""
    # 去 HTML 实体
    title = re.sub(r"&#?\w+;", " ", title)
    title = re.sub(r"<[^>]+>", " ", title)
    title = re.sub(r"\s+", " ", title).strip()
    if len(title) > max_len:
        title = title[:max_len].rsplit(" ", 1)[0] + "..."
    return title


def load_manifest() -> dict:
    """加载 news_social_manifest.json（去重记录）。

    加载时自动清理超过 30 天的旧条目，保持文件精简。
    """
    if MANIFEST_PATH.exists():
        try:
            with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"[WARN] Manifest load failed: {e}, starting fresh")
            return _empty_manifest()
    else:
        data = _empty_manifest()

    # 自动清理 > 30 天的旧条目
    data = _purge_old_entries(data)
    return data


def _empty_manifest() -> dict:
    return {"posts": {}, "last_run": None, "total_posts": 0, "total_failures": 0}


def _purge_old_entries(manifest: dict) -> dict:
    """移除超过 30 天的旧去重记录，防止 manifest 膨胀。"""
    now = datetime.now(timezone.utc)
    max_age = timedelta(days=30)
    purged = 0
    for hash_key in list(manifest["posts"].keys()):
        record = manifest["posts"][hash_key]
        try:
            posted = datetime.fromisoformat(record["posted_at"])
            if now - posted > max_age:
                del manifest["posts"][hash_key]
                purged += 1
        except (ValueError, KeyError):
            del manifest["posts"][hash_key]
            purged += 1
    if purged:
        manifest["total_posts"] = len(manifest["posts"])
        print(f"[MANIFEST] Purged {purged} expired entries")
    return manifest


def save_manifest(manifest: dict):
    """保存 manifest（原子写入，防损坏）。"""
    manifest["last_run"] = datetime.now(timezone.utc).isoformat()
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = MANIFEST_PATH.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    tmp_path.replace(MANIFEST_PATH)


def is_deduplicated(manifest: dict, news_hash: str) -> bool:
    """检查新闻是否在冷却期内已发布过。

    - 成功发布：7 天冷却
    - 失败发布：1 天冷却（允许次日重试）
    """
    record = manifest.get("posts", {}).get(news_hash)
    if not record:
        return False
    try:
        last_date = datetime.fromisoformat(record["posted_at"])
        delta = datetime.now(timezone.utc) - last_date
        cooldown = timedelta(days=COOLDOWN_DAYS) if record.get("success") else timedelta(days=1)
        return delta < cooldown
    except (ValueError, KeyError):
        return False


def record_post(manifest: dict, news_hash: str, title: str, platforms: list, success: bool):
    """记录发布结果。成功和失败都记录，但冷却期不同。"""
    today = datetime.now(timezone.utc).isoformat()
    manifest["posts"][news_hash] = {
        "title": title,
        "posted_at": today,
        "platforms": platforms,
        "success": success,
    }
    if success:
        manifest["total_posts"] = manifest.get("total_posts", 0) + 1
    else:
        manifest["total_failures"] = manifest.get("total_failures", 0) + 1


# ══════════════════════════════════════════════════════════════════════
# 图片选择（buffer-worker 要求 /img/china-dest/ 路径）
# ══════════════════════════════════════════════════════════════════════

_CHINA_DEST_SOCIAL_DIR = BLOG_ROOT / "static" / "img" / "china-dest" / "social"


def _pick_random_china_dest_image() -> str:
    """从已有 china-dest/social 图片池中随机选一张返回绝对 URL。

    buffer-worker 的 ALLOWED_IMAGE_PATH = '/img/china-dest/'，拒绝
    /img/og-default.jpg 等不在该路径下的图片。新闻条目没有自然配图，
    从图片池随机取一张做封面以保证提交成功。

    Hugo 部署时会把 static/ 前缀剥掉，所以静态文件
    static/img/china-dest/social/foo.jpg 在站点上访问路径为
    /img/china-dest/social/foo.jpg。
    """
    if not _CHINA_DEST_SOCIAL_DIR.exists():
        return ""
    files = list(_CHINA_DEST_SOCIAL_DIR.glob("*.jpg")) + list(_CHINA_DEST_SOCIAL_DIR.glob("*.jpeg"))
    if not files:
        return ""
    chosen = random.choice(files)
    # Hugo 去掉 static/ 前缀：static/img/china-dest/... → /img/china-dest/...
    rel = str(chosen.relative_to(BLOG_ROOT)).replace("\\", "/")
    if rel.startswith("static/"):
        rel = rel[len("static/"):]
    return f"https://www.{SITE_DOMAIN}/{rel}"


# ══════════════════════════════════════════════════════════════════════
# 文案生成
# ══════════════════════════════════════════════════════════════════════


def generate_social_copy(item: dict, category: str) -> dict:
    """
    为一条新闻生成社媒文案。

    返回：
      {
        "style": "news-alert" | "news-insight",
        "text": "...",
        "image_url": "...",
        "article_url": "...",
      }
    """
    title = clean_title(item.get("title", ""), 100)
    summary = item.get("summary", "")
    date = item.get("date", "")
    source = item.get("source", "")
    url = item.get("url", "")

    style_map = CATEGORY_STYLE_MAP.get(category, CATEGORY_STYLE_MAP["general"])
    headline = style_map["headline_prefix"]
    hashtags = style_map["hashtags"]
    emoji = style_map.get("emoji_prefix", "📰")
    urgency = style_map.get("urgency", "")

    # 构建文章 URL（用新闻关键词生成 slug）
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60]
    article_url = f"{BASE_URL}/posts/{slug}/"
    campaign = f"cbt_news_{datetime.now().strftime('%Y%m%d')}"

    def _utm(platform):
        sep = "&" if "?" in article_url else "?"
        return f"{article_url}{sep}utm_source={platform}&utm_medium=social&utm_campaign={campaign}&utm_content=news_{category}"

    # ── 风格 1: news-alert（适合 X / Facebook，简洁有力） ──
    info_lines = [f"{emoji} {headline}"]
    if urgency:
        info_lines.append(f"\n{urgency}: {title}")
    else:
        info_lines.append(f"\n{title}")
    if summary and len(summary) > 20:
        info_lines.append(f"\n{summary[:150]}")
    if source:
        info_lines.append(f"\nSource: {source}")
    info_lines.append(f"\n{url if url else article_url}")
    info_lines.append(f"\n{hashtags}")
    info_text = "\n".join(info_lines)

    # ── 风格 2: news-insight（适合 Instagram / Pinterest，更有深度） ──
    insight_lines = [f"{emoji} China Travel Update"]
    insight_lines.append(f"\n{title}")
    if summary and len(summary) > 20:
        insight_lines.append(f"\n{summary[:200]}")
    if date:
        insight_lines.append(f"\n(As of {date})")
    insight_lines.append(f"\nRead more on chinaboundtravel.com:")
    insight_lines.append(f"{_utm('ig')}")
    insight_lines.append(f"\n{hashtags} #TravelChina #VisitChina")
    insight_text = "\n".join(insight_lines)

    # 图片：buffer-worker 要求路径必须以 /img/china-dest/ 开头。
    # 新闻条目没有自然配图，从已有 china-dest/social 图片池随机取一张做封面。
    # 避免使用 /img/og-default.jpg（不在 china-dest/ 下，被 worker 拒绝）。
    image_url = _pick_random_china_dest_image()

    return {
        "title": title,
        "category": category,
        "source": source,
        "url": url,
        "article_url": article_url,
        "styles": [
            {"style": "news-alert", "text": info_text, "image_url": image_url, "platforms": ["x", "facebook"]},
            {"style": "news-insight", "text": insight_text, "image_url": image_url, "platforms": ["instagram", "pinterest"]},
        ],
    }


# ══════════════════════════════════════════════════════════════════════
# Buffer Worker 发布
# ══════════════════════════════════════════════════════════════════════


def check_worker_health(timeout: int = 10) -> list:
    """探测 Worker 健康状态。"""
    issues = []
    for label, base in (("BUFFER_WORKER_URL", BUFFER_BASE_URL),
                        ("NEW_BUFFER_WORKER_URL", NEW_BUFFER_BASE_URL)):
        if not base:
            issues.append(f"{label}: not configured")
            continue
        try:
            r = requests.get(base + "/health", timeout=timeout)
            if r.status_code != 200:
                issues.append(f"{label}: HTTP {r.status_code}")
            else:
                print(f"[HEALTH] {label} OK")
        except Exception as e:
            issues.append(f"{label}: {e}")
    return issues


def publish_to_buffer(item_data: dict, worker_url: str, platforms: list, dry_run: bool = False) -> dict:
    """调用 Buffer Worker 发布一条新闻帖。"""
    style = item_data["styles"][0] if item_data["styles"][0]["style"] == "news-alert" else item_data["styles"][0]
    # 选择正确的风格
    alert_style = next((s for s in item_data["styles"] if s["style"] == "news-alert"), item_data["styles"][0])
    insight_style = next((s for s in item_data["styles"] if s["style"] == "news-insight"), item_data["styles"][0])

    # 根据目标平台选择文案
    if any(p in ["instagram", "pinterest"] for p in platforms):
        selected = insight_style
    else:
        selected = alert_style

    payload = {
        "title": item_data["title"][:100],
        "desc": selected["text"],
        "cover": selected["image_url"],
        "url": selected.get("article_url", item_data.get("article_url", "")),
        "custom_text": selected["text"],
        "content_id": make_hash(item_data["title"]),
        "content_variant": f"news_{item_data['category']}",
        "source_workflow": "news_social_poster",
        "platforms": platforms,
    }

    if dry_run:
        return {"success": True, "dry_run": True, "payload": payload}

    try:
        resp = requests.post(worker_url, json=payload, timeout=90)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Timeout after 90s"}
    except requests.exceptions.HTTPError as e:
        return {"success": False, "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ══════════════════════════════════════════════════════════════════════
# 飞书通知
# ══════════════════════════════════════════════════════════════════════


def send_feishu_notification(results: list, dry_run: bool = False):
    """发送飞书通知。"""
    webhook = os.getenv("FEISHU_WEBHOOK_URL")
    if not webhook:
        return

    mode = "DRY RUN" if dry_run else "LIVE"
    total_ok = sum(1 for r in results if r.get("success"))
    total_fail = sum(1 for r in results if not r.get("success"))
    total_skipped = sum(1 for r in results if r.get("skipped"))

    lines = [f"📰 News Social Poster [{mode}]"]
    lines.append(f"  Published: {total_ok} | Failed: {total_fail} | Skipped: {total_skipped}")
    lines.append("")
    for r in results[:10]:
        status = "OK" if r.get("success") else ("SKIP" if r.get("skipped") else "FAIL")
        title = r.get("title", "?")[:50]
        cat = r.get("category", "?")
        lines.append(f"  [{status}] {cat}: {title}")

    payload = {
        "msg_type": "text",
        "content": {"text": "\n".join(lines)},
    }

    try:
        requests.post(webhook, json=payload, timeout=15)
        print("[Feishu] Notification sent")
    except Exception as e:
        print(f"[Feishu] Notification failed: {e}")


# ══════════════════════════════════════════════════════════════════════
# 主流程
# ══════════════════════════════════════════════════════════════════════


def run(dry_run: bool = False, count: int = 3, categories: str = "all"):
    """执行新闻社媒发布。"""
    print("=" * 60)
    print("News Social Poster")
    print(f"Started: {datetime.now(timezone.utc).isoformat()}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'} | Per-category max: {count}")
    print("=" * 60)

    # ── 1. 加载新闻数据 ──
    if not NEWS_DIGEST_PATH.exists():
        print(f"[ERROR] {NEWS_DIGEST_PATH} not found. Run news_monitor.py first.")
        sys.exit(1)

    with open(NEWS_DIGEST_PATH, "r", encoding="utf-8") as f:
        digest_data = json.load(f)

    digest = digest_data.get("digest", {})
    last_updated = digest_data.get("last_updated_date", "unknown")

    print(f"[DATA] News digest from: {last_updated}")
    total_raw = sum(len(items) for items in digest.values())
    print(f"[DATA] Total news items: {total_raw}")

    if total_raw == 0:
        print("[INFO] No news items in digest. Nothing to do.")
        return []

    # ── 2. 加载去重 manifest ──
    manifest = load_manifest()
    print(f"[MANIFEST] Previously posted: {manifest.get('total_posts', 0)} | Failed: {manifest.get('total_failures', 0)}")

    # ── 3. 筛选新闻项 ──
    cat_filter = set(c.strip().lower() for c in categories.split(",")) if categories != "all" else None

    all_selected = []
    for cat, items in sorted(digest.items(), key=lambda x: -CATEGORY_PRIORITY.get(x[0], 0)):
        if cat_filter and cat not in cat_filter:
            continue
        if not items:
            continue
        selected = []
        for item in items[:count]:
            h = make_hash(item.get("title", ""))
            if is_deduplicated(manifest, h):
                print(f"  [SKIP] Deduplicated: {item.get('title', '?')[:50]}")
                continue
            item["_hash"] = h
            selected.append(item)
        all_selected.extend(selected)

    print(f"\n[SELECT] {len(all_selected)} items to process (after dedup)")

    # ── 4. 健康检查 ──
    if not dry_run:
        health_issues = check_worker_health()
        if health_issues:
            for issue in health_issues:
                print(f"[HEALTH][WARN] {issue}")

    # ── 5. 生成文案并发布 ──
    all_results = []
    active_window = active_window_est()

    for idx, item in enumerate(all_selected, 1):
        cat = item.get("category", "general")
        title = item.get("title", "?")[:60]
        print(f"\n  [{idx}/{len(all_selected)}] [{cat}] {title}")

        # 生成文案
        item_data = generate_social_copy(item, cat)

        # 打印文案预览
        if dry_run:
            for s in item_data["styles"]:
                print(f"    [{s['style']}] {s['text'][:120]}...")

        if dry_run:
            all_results.append({"success": True, "dry_run": True, "title": title, "category": cat})
            continue

        # 确定目标平台（根据当前活跃窗口）
        if active_window == "prime":
            # 晚间黄金时段：所有平台
            platforms = ["x", "facebook", "instagram", "pinterest"]
        elif active_window == "morning":
            platforms = ["x", "facebook"]
        elif active_window == "lunch":
            platforms = ["x", "facebook", "instagram"]
        else:
            # 非活跃窗口：仅发布到 Twitter/X
            platforms = ["x"]

        # 选择 Worker URL（URL 已在初始化时归一化，已包含 /publish）
        if any(p == "pinterest" for p in platforms):
            worker_url = NEW_BUFFER_WORKER_URL or BUFFER_WORKER_URL
        else:
            worker_url = BUFFER_WORKER_URL

        print(f"    -> {worker_url} [{', '.join(platforms)}]")

        # 发布
        result = publish_to_buffer(item_data, worker_url, platforms, dry_run=False)
        success = result.get("success", False)
        error = result.get("error", "")

        if success:
            print(f"    [OK] Published")
        else:
            print(f"    [FAIL] {error[:100]}")

        # 记录到 manifest
        record_post(manifest, item["_hash"], title, platforms, success)

        all_results.append({
            "success": success,
            "title": title,
            "category": cat,
            "platforms": platforms,
            "error": error,
        })

    # ── 6. 保存 manifest ──
    if not dry_run:
        save_manifest(manifest)
        print(f"\n[MANIFEST] Saved: {manifest.get('total_posts', 0)} posts | {manifest.get('total_failures', 0)} failures")

    # ── 7. 飞书通知 ──
    if all_results:
        send_feishu_notification(all_results, dry_run=dry_run)

    # ── 8. 汇总 ──
    ok = sum(1 for r in all_results if r.get("success"))
    fail = sum(1 for r in all_results if not r.get("success"))
    skip = sum(1 for r in all_results if r.get("skipped"))
    print(f"\n{'=' * 60}")
    print(f"Done: {ok} OK, {fail} FAIL, {skip} SKIP")
    print(f"{'=' * 60}")

    return all_results


def main():
    parser = argparse.ArgumentParser(description="News Social Poster")
    parser.add_argument("--dry-run", action="store_true", help="Print only, do not publish")
    parser.add_argument("--count", type=int, default=3, help="Max items per category (default: 3)")
    parser.add_argument("--categories", default="all",
                        help="Comma-separated categories (default: all)")
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    run(dry_run=args.dry_run, count=args.count, categories=args.categories)


if __name__ == "__main__":
    main()
