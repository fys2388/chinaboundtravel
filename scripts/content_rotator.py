#!/usr/bin/env python3
"""
Content Rotator - 自动轮播分发博客文章到社媒平台

功能：
  - 扫描 content/posts/ 下所有 .md 文章
  - 使用 manifest_rotator.json 跟踪分发记录
  - 每次选取最久未分发的文章，生成 2 种风格社媒文案
  - 调用 Buffer Worker 发布，避免 7 天内重复发到同一平台

用法：
  python scripts/content_rotator.py [--count N] [--dry-run]
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

# P1-OPS-04: 社媒文案清理/校验公共工具（shortcode 剥离、目的地提取、URL 保证、lint）
sys.path.insert(0, str(Path(__file__).resolve().parent))
from social_text_utils import (  # noqa: E402
    clean_social_text,
    ensure_article_url,
    extract_destination,
    first_meaningful_desc,
    image_rejection_reason,
    validate_social_copy,
)

# ============================================================
# 配置
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
POSTS_DIR = BASE_DIR / "content" / "posts"
MANIFEST_PATH = BASE_DIR / "manifest_rotator.json"

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

# P1-GROWTH-28A: Worker 地址从 .env 读取，禁止硬编码旧地址。
LEGACY_WORKER_URL = "https://buffer-worker.chinaboundtravel.com"
BUFFER_WORKER_URL = (os.getenv("BUFFER_WORKER_URL") or LEGACY_WORKER_URL).strip().rstrip("/")  # 主账户 FB/IG/X
NEW_BUFFER_WORKER_URL = (os.getenv("NEW_BUFFER_WORKER_URL") or "").strip().rstrip("/")  # 长尾账户 Pinterest

# 双账户路由（P1-GROWTH-28A）：主账户平台 -> BUFFER_WORKER_URL；Pinterest -> NEW_BUFFER_WORKER_URL
MAIN_PLATFORMS = ["x", "facebook", "instagram"]
PINTEREST_PLATFORMS = ["pinterest"]
PLATFORM_BY_STYLE = {"informative": MAIN_PLATFORMS, "inspirational": PINTEREST_PLATFORMS}

try:
    from zoneinfo import ZoneInfo
    EST_TZ = ZoneInfo("America/New_York")
except Exception:
    EST_TZ = timezone(timedelta(hours=-5))

# 活跃发布窗口（美东时间 EST，面向欧美受众）—— 分时段发布，避免集中轰炸：
#   早通勤 08:00-10:00 / 午休 12:00-14:00 / 晚间黄金 20:00-22:00
ACTIVE_WINDOWS_EST = [
    {"name": "morning", "start": 8,  "end": 10},
    {"name": "lunch",   "start": 12, "end": 14},
    {"name": "prime",   "start": 20, "end": 22},
]
# P2-SOCIAL-01: 单平台每日发布目标：3-5 条（3 个窗口 × 每窗口 1-2 条）
# 注意：此常量目前为目标参考值，实际限制逻辑在 social_content_agent.py 和 social_backfill.py 中实现
DAILY_POSTS_PER_ACCOUNT_MIN, DAILY_POSTS_PER_ACCOUNT_MAX = 3, 5

def now_est():
    """当前时间统一转换为美东时间（发布/排期口径）。"""
    return datetime.now(EST_TZ)

def active_window_est(dt=None):
    """返回当前所处的活跃发布窗口名（morning/lunch/prime），不在窗口内返回 None。"""
    dt = dt or now_est()
    for w in ACTIVE_WINDOWS_EST:
        if w["start"] <= dt.hour < w["end"]:
            return w["name"]
    return None

def is_golden_hour_est(dt=None):
    """兼容旧接口：黄金时段 == prime 窗口（20:00-22:00 EST）。"""
    dt = dt or now_est()
    return 20 <= dt.hour < 22

def worker_url_for_platforms(platforms):
    """双账户路由：仅 Pinterest -> NEW_BUFFER_WORKER_URL；其余 -> BUFFER_WORKER_URL。"""
    wants_pin = bool(set(platforms) & set(PINTEREST_PLATFORMS))
    wants_main = bool(set(platforms) & set(MAIN_PLATFORMS))
    if wants_pin and not wants_main:
        if not NEW_BUFFER_WORKER_URL:
            print("[WARN] NEW_BUFFER_WORKER_URL 未配置，Pinterest 请求回退到 BUFFER_WORKER_URL（需配置 .env）")
            return BUFFER_WORKER_URL + "/publish", True
        return NEW_BUFFER_WORKER_URL + "/publish", False
    return BUFFER_WORKER_URL + "/publish", False
SITE_DOMAIN = "chinaboundtravel.com"

# 7 天冷却期：同一篇文章不重复发到同一平台
COOLDOWN_DAYS = 7

# 所有分发目标平台
ALL_PLATFORMS = ["x", "facebook", "instagram", "pinterest"]

# ============================================================
# 文章解析
# ============================================================


def parse_frontmatter(content: str) -> dict:
    """解析 Markdown 文件的 frontmatter，返回键值对字典。"""
    fm_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    frontmatter = {}
    if fm_match:
        fm_text = fm_match.group(1)
        for line in fm_text.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and value:
                    frontmatter[key] = value
    return frontmatter


def parse_article(md_path: Path) -> dict:
    """
    解析一篇 Markdown 文章，提取标题、描述、slug、正文和图片。

    返回:
        {
            "title": str,
            "description": str,
            "slug": str,
            "url": str,
            "body_text": str,
            "images": list[str],
            "source_file": str
        }
    """
    # 读取文件内容（兼容编码）
    try:
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        with open(md_path, "r", encoding="latin-1") as f:
            content = f.read()
        content = content.encode("utf-8", errors="replace").decode("utf-8", errors="replace")

    fm = parse_frontmatter(content)

    # 提取字段
    title = fm.get("title", md_path.stem.replace("-", " ").title())
    slug = fm.get("slug", md_path.stem)
    canonical_url = fm.get("canonicalURL", "")

    # 构建文章 URL
    if canonical_url:
        if not canonical_url.startswith("http"):
            canonical_url = f"https://{canonical_url}"
        url = canonical_url
    else:
        url = f"https://{SITE_DOMAIN}/posts/{slug}/"

    # 提取正文文本（去除 markdown 标记、Hugo shortcode、HTML）
    fm_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    body_text = content[fm_match.end():] if fm_match else content
    body_clean = clean_social_text(body_text)
    # 优先使用 frontmatter description/summary（质量更高），否则从正文提取
    fm_desc = fm.get("description", "") or fm.get("summary", "")
    if fm_desc and len(fm_desc) > 30:
        description = first_meaningful_desc(fm_desc, title, 300)
    else:
        description = first_meaningful_desc(body_clean, title, 300)

    # 提取图片 URL
    images = []

    # 1. frontmatter 中的 cover 图片
    if fm_match:
        fm_text = fm_match.group(1)
        cover_match = re.search(
            r'^\s*cover\s*:\s*\n\s*image\s*:\s*"?([^"\n]+)"?',
            fm_text, re.MULTILINE,
        )
        if not cover_match:
            cover_match = re.search(
                r'^\s*cover\s*:\s*"?([^"\n]+)"?',
                fm_text, re.MULTILINE,
            )
        if cover_match:
            cover_url = cover_match.group(1).strip()
            if cover_url:
                if not cover_url.startswith("http"):
                    cover_url = f"https://{SITE_DOMAIN}{cover_url}"
                images.append(cover_url)

    # 2. 正文中的图片（发布规则：禁止人物/头像、禁止抽象图 —— 不合规图片丢弃）
    body_content = content[fm_match.end():] if fm_match else content
    img_pattern = r"!\[([^\]]*)\]\(([^)]+)\)"
    for match in re.finditer(img_pattern, body_content):
        img_alt = match.group(1)
        img_url = match.group(2)
        if img_url and ("pollinations" in img_url or "picsum" in img_url or SITE_DOMAIN in img_url):
            if not img_url.startswith("http"):
                img_url = f"https://{SITE_DOMAIN}{img_url}"
            if image_rejection_reason(alt=img_alt, url=img_url):
                print(f"  [IMG-SKIP] 正文图 {img_url[-50:]} 含人物/抽象特征被过滤（{img_alt[:40]}）")
                continue
            images.append(img_url)

    return {
        "title": title,
        "description": description,
        "slug": slug,
        "url": url,
        "content_id": fm.get("content_id", ""),
        "body_text": body_clean,
        "images": images,
        "source_file": str(md_path),
    }


def discover_articles() -> list:
    """
    扫描 content/posts/ 目录下所有 .md 文件（排除子目录如 .archived/.audit_backup/drafts）。
    返回按文件名排序的文章列表。
    """
    skip_dirs = {".archived", ".audit_backup", "drafts", "_draft"}
    articles = []
    for md_file in POSTS_DIR.glob("*.md"):
        if md_file.name.startswith("."):
            continue
        articles.append(md_file)
    return sorted(articles, key=lambda p: p.name)


# ============================================================
# Manifest 管理
# ============================================================


def load_manifest() -> dict:
    """加载 manifest_rotator.json，不存在则创建空结构。"""
    if MANIFEST_PATH.exists():
        try:
            with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"[WARN] 读取 manifest 失败: {e}，将创建新的")
            return _empty_manifest()
    return _empty_manifest()


def save_manifest(manifest: dict):
    """保存 manifest 到文件。"""
    manifest["last_run"] = datetime.now(timezone.utc).isoformat()
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)


def _empty_manifest() -> dict:
    return {
        "articles": {},
        "last_run": None,
        "total_distributions": 0,
    }


def update_article_record(manifest: dict, slug: str, title: str, platform: str, success: bool):
    """
    更新某篇文章在某个平台的分发记录。

    成功：记录当前日期；失败：不更新平台日期（下次可重试）。
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if slug not in manifest["articles"]:
        manifest["articles"][slug] = {
            "title": title,
            "last_distributed": today,
            "platforms": {},
            "distribute_count": 0,
        }

    record = manifest["articles"][slug]

    if success:
        record["platforms"][platform] = today
        record["last_distributed"] = today
        record["distribute_count"] = record.get("distribute_count", 0) + 1
        manifest["total_distributions"] = manifest.get("total_distributions", 0) + 1


# ============================================================
# 选取策略
# ============================================================


def select_articles(manifest: dict, all_articles_info: list, count: int) -> list:
    """
    选取 count 篇"最久未分发"的文章。

    排序优先级：
      1. 从未分发过的文章优先（last_distributed 为 None 或不存在）
      2. last_distributed 日期最早的优先
      3. distribute_count 最少的优先（同日期时）

    如果可选文章不足，返回实际可选取的数量。
    """
    scored = []
    for article in all_articles_info:
        slug = article["slug"]
        record = manifest.get("articles", {}).get(slug)

        if record is None:
            # 从未分发 — 优先级最高
            scored.append((article, "0000-01-01", 0))
        else:
            last_date = record.get("last_distributed", "0000-01-01")
            dist_count = record.get("distribute_count", 0)
            scored.append((article, last_date, dist_count))

    # 排序：last_date 最早优先，同日期则 distribute_count 少的优先
    scored.sort(key=lambda x: (x[1], x[2]))

    return [item[0] for item in scored[:count]]


def get_eligible_platforms(manifest: dict, slug: str) -> list:
    """
    获取某篇文章当前可以分发的平台列表。
    排除在 COOLDOWN_DAYS 内已分发的平台。
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cutoff = (
        datetime.now(timezone.utc) - timedelta(days=COOLDOWN_DAYS)
    ).strftime("%Y-%m-%d")

    record = manifest.get("articles", {}).get(slug)
    if record is None:
        return list(ALL_PLATFORMS)

    eligible = []
    for platform in ALL_PLATFORMS:
        last_post_date = record.get("platforms", {}).get(platform)
        if last_post_date is None or last_post_date < cutoff:
            eligible.append(platform)

    return eligible


# ============================================================
# 社媒文案生成
# ============================================================


def truncate_text(text: str, max_chars: int) -> str:
    """截断文本到指定字符数，尽量在单词边界处截断。"""
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars].rsplit(" ", 1)[0]
    return truncated if truncated else text[:max_chars]


def generate_social_copies(article: dict) -> list:
    """
    为一篇文章生成 2 种风格的社媒文案。

    P1修复：所有链接统一加 UTM 参数，与 social_content_agent 新链路对齐。
    返回:
        [
            {"style": "informative", "text": "..."},
            {"style": "inspirational", "text": "..."},
        ]
    """
    title = article["title"]
    description = article["description"]
    base_url = ensure_article_url(article.get("url", ""), article.get("slug", ""), SITE_DOMAIN)
    campaign = f"cbt_social_{datetime.now().strftime('%Y%m%d')}"

    def _utm(platform, variant):
        sep = "&" if "?" in base_url else "?"
        return f"{base_url}{sep}utm_source={platform}&utm_medium=social&utm_campaign={campaign}&utm_content=rotator_{variant}"

    # 目的地提取：白名单优先，绝不截取标题前几个大写词（修复 'Can Foreigners Use, Pay, China?' 语序错乱）
    destination = extract_destination(title)

    copies = []

    # 风格 1: 信息型 — 适合 X/Facebook（带 UTM）
    desc_info = first_meaningful_desc(description, title, 150)
    url_fb = _utm("fb", "informative")
    info_text = (
        f"{title}\n\n"
        f"{desc_info}\n\n"
        f"Full guide: {url_fb}\n\n"
        f"#ChinaTravel #TravelChina"
    )
    copies.append({"style": "informative", "text": info_text})

    # 风格 2: 激发型 — 适合 Instagram/Pinterest（带 UTM）
    desc_inspire = first_meaningful_desc(description, title, 120)
    url_ig = _utm("ig", "inspirational")
    inspire_text = (
        f"Dreaming of exploring {destination}?\n\n"
        f"{desc_inspire}\n\n"
        f"Read the full guide: {url_ig}\n\n"
        f"#ChinaBucketList #TravelGoals #VisitChina"
    )
    copies.append({"style": "inspirational", "text": inspire_text})

    return copies


# ============================================================
# Buffer Worker 调用
# ============================================================

def check_worker_health(timeout: int = 10) -> list:
    """P1-GROWTH-28A: 探测两个 Worker 的 /health 接口，异常返回列表（供自动告警）。"""
    issues = []
    for label, base in (("BUFFER_WORKER_URL", BUFFER_WORKER_URL),
                        ("NEW_BUFFER_WORKER_URL", NEW_BUFFER_WORKER_URL)):
        if not base:
            issues.append(f"{label}: 未配置（.env 缺少该键）")
            continue
        try:
            r = requests.get(base + "/health", timeout=timeout)
            if r.status_code != 200:
                issues.append(f"{label}: HTTP {r.status_code} ({base}/health)")
            else:
                print(f"[HEALTH] {label} OK ({base}/health)")
        except Exception as e:
            issues.append(f"{label}: {e} ({base}/health)")
    return issues


def publish_to_buffer(article: dict, social_text: str, image_url: str, variant: str = "default") -> dict:
    """
    调用 Buffer Worker 发布一条社媒内容。

    返回 Worker 的 JSON 响应。
    """
    # P1-GROWTH-28A: 双账户路由 - informative -> 主账户(FB/IG/X)；inspirational -> Pinterest 长尾账户
    platforms = PLATFORM_BY_STYLE.get(variant, MAIN_PLATFORMS)
    worker_url, fell_back = worker_url_for_platforms(platforms)
    if fell_back:
        print("[ROUTE] Pinterest 目标回退到主 Worker（NEW_BUFFER_WORKER_URL 未配置）")
    else:
        print(f"[ROUTE] style={variant} -> {worker_url}")
    payload = {
        "title": article["title"],
        "desc": social_text,
        "cover": image_url,
        "url": ensure_article_url(article.get("url", ""), article.get("slug", ""), SITE_DOMAIN),
        "custom_text": social_text,
        "content_id": article.get("content_id", ""),
        "content_variant": variant,
        "source_workflow": "content_rotation",
        "platforms": platforms,
    }

    try:
        resp = requests.post(worker_url, json=payload, timeout=90)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Timeout after 90s"}
    except requests.exceptions.HTTPError as e:
        return {"success": False, "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "Connection failed"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# 飞书通知
# ============================================================


def send_feishu_notification(results: list):
    """发送飞书 Webhook 通知（如果配置了 FEISHU_WEBHOOK_URL）。"""
    webhook = os.getenv("FEISHU_WEBHOOK_URL")
    if not webhook:
        print("[INFO] 未配置 FEISHU_WEBHOOK_URL，跳过飞书通知")
        return

    summary_lines = []
    for r in results:
        status = "OK" if r["success"] else "FAIL"
        summary_lines.append(
            f"[{status}] {r['article_title'][:50]} ({r['style']}) -> {r['platforms_summary']}"
        )
        if r.get("error"):
            summary_lines.append(f"    Error: {r['error'][:100]}")

    content = "\n".join(summary_lines)
    total_ok = sum(1 for r in results if r["success"])
    total_fail = sum(1 for r in results if not r["success"])
    header = f"Content Rotator: {total_ok} OK, {total_fail} FAIL"

    payload = {
        "msg_type": "text",
        "content": {"text": f"{header}\n\n{content}"},
    }

    try:
        requests.post(webhook, json=payload, timeout=15)
    except Exception as e:
        print(f"[WARN] 飞书通知发送失败: {e}")


# ============================================================
# 主流程
# ============================================================


def run(count: int = 2, dry_run: bool = False):
    """
    主流程：选取文章 -> 生成文案 -> 发布 -> 更新 manifest。
    """
    # P1-GROWTH-28A: 健康检查（探测两个 Worker 的 /health，异常自动告警）
    health_issues = check_worker_health()
    if health_issues:
        for issue in health_issues:
            print(f"[HEALTH][WARN] {issue}")
    windows_desc = " / ".join(f"{w['name']} {w['start']}:00-{w['end']}:00" for w in ACTIVE_WINDOWS_EST)
    print(f"{'=' * 60}")
    print(f"Content Rotator - UTC {datetime.now(timezone.utc).isoformat()} / EST {now_est().isoformat(timespec='seconds')} (活跃窗口: {windows_desc} EST)")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'} | Count: {count}")
    print(f"{'=' * 60}")

    # 1. 扫描文章
    md_files = discover_articles()
    print(f"\n[SCAN] 发现 {len(md_files)} 篇文章")

    # 2. 解析所有文章
    all_articles = []
    for md_file in md_files:
        try:
            article = parse_article(md_file)
            all_articles.append(article)
        except Exception as e:
            print(f"[WARN] 解析失败 {md_file.name}: {e}")

    print(f"[SCAN] 成功解析 {len(all_articles)} 篇文章")

    # 3. 加载 manifest
    manifest = load_manifest()
    total_prev = manifest.get("total_distributions", 0)
    print(f"[MANIFEST] 累计分发 {total_prev} 次 | 上次运行 {manifest.get('last_run', 'N/A')}")

    # 4. 选取文章
    selected = select_articles(manifest, all_articles, count)
    if not selected:
        print("\n[DONE] 没有可分发的文章")
        return

    print(f"\n[SELECT] 选取 {len(selected)} 篇文章:")
    for i, article in enumerate(selected):
        record = manifest.get("articles", {}).get(article["slug"])
        last_date = record.get("last_distributed", "Never") if record else "Never"
        dist_count = record.get("distribute_count", 0) if record else 0
        print(f"  {i+1}. {article['title'][:60]}")
        print(f"     slug={article['slug']} | last={last_date} | count={dist_count}")

    # 5. 逐文章处理
    all_results = []

    for article in selected:
        slug = article["slug"]
        title = article["title"]
        print(f"\n{'─' * 50}")
        print(f"[ARTICLE] {title[:70]}")
        print(f"{'─' * 50}")

        # 获取可用平台
        eligible = get_eligible_platforms(manifest, slug)
        if not eligible:
            print(f"[SKIP] 所有平台均在 {COOLDOWN_DAYS} 天冷却期内，跳过")
            continue

        print(f"[PLATFORMS] 可用: {', '.join(eligible)}")

        # 选择配图（优先正文实景图）
        images = article["images"]
        if not images:
            print(f"[WARN] 无可用图片，跳过发布")
            # 即使无图片，仍然更新 manifest 以免反复选取
            continue

        cover_image = images[0]
        print(f"[IMAGE] 使用图片: {cover_image[-60:]}")

        # 生成 2 种风格文案
        copies = generate_social_copies(article)
        print(f"[COPY] 生成 {len(copies)} 种文案风格")

        # 发布前 lint（P1-OPS-04）：有致命问题的文案一律拒绝发布
        publishable = []
        for copy in copies:
            problems = validate_social_copy(
                copy["text"], title=title,
                url=ensure_article_url(article.get("url", ""), slug, SITE_DOMAIN),
            )
            if problems:
                print(f"  [LINT][{copy['style']}] 文案未通过校验，跳过发布:")
                for p in problems:
                    print(f"    - {p}")
                all_results.append({
                    "article_title": title,
                    "slug": slug,
                    "style": copy["style"],
                    "success": False,
                    "error": "LINT_FAILED: " + "; ".join(problems),
                    "platforms_summary": "lint_failed",
                    "image": images[0] if images else "",
                })
            else:
                publishable.append(copy)
        if not publishable:
            print(f"  [SKIP] 该文章无任何通过校验的文案，跳过发布")
            continue
        print(f"[COPY] 通过 lint 的文案风格: {', '.join(c['style'] for c in publishable)}")

        # 对每种文案调用 Buffer Worker
        for copy in publishable:
            style = copy["style"]
            print(f"\n  [{style.upper()}] 发布中...")
            print(f"  文案: {copy['text'][:80]}...")

            if dry_run:
                print(f"  [DRY RUN] 跳过实际发布")
                all_results.append({
                    "article_title": title,
                    "slug": slug,
                    "style": style,
                    "success": True,
                    "dry_run": True,
                    "platforms_summary": "dry_run",
                    "image": cover_image,
                })
                continue

            try:
                worker_resp = publish_to_buffer(article, copy["text"], cover_image, copy.get("style", "default"))

                if worker_resp.get("success"):
                    platforms = worker_resp.get("platforms", {})
                    ok_platforms = platforms.get("success", [])
                    fail_platforms = platforms.get("failed", [])
                    platforms_summary = f"OK: {','.join(ok_platforms)}"
                    if fail_platforms:
                        platforms_summary += f" | FAIL: {','.join(fail_platforms)}"

                    print(f"  [OK] Worker 成功 | 平台: {platforms_summary}")

                    # 更新 manifest（为每个成功的平台记录）
                    for platform in ok_platforms:
                        update_article_record(manifest, slug, title, platform, True)

                    all_results.append({
                        "article_title": title,
                        "slug": slug,
                        "style": style,
                        "success": True,
                        "platforms_summary": platforms_summary,
                        "image": cover_image,
                    })
                else:
                    error = worker_resp.get("error", "Unknown error")
                    print(f"  [FAIL] Worker 失败: {error[:100]}")

                    all_results.append({
                        "article_title": title,
                        "slug": slug,
                        "style": style,
                        "success": False,
                        "error": error,
                        "platforms_summary": "failed",
                        "image": cover_image,
                    })

            except Exception as e:
                print(f"  [ERROR] 异常: {e}")
                all_results.append({
                    "article_title": title,
                    "slug": slug,
                    "style": style,
                    "success": False,
                    "error": str(e),
                    "platforms_summary": "error",
                    "image": cover_image,
                })

            # 发布间隔（避免触发限流）
            if not dry_run:
                time.sleep(5)

    # 6. 保存 manifest
    save_manifest(manifest)
    total_new = manifest.get("total_distributions", 0) - total_prev
    print(f"\n{'=' * 60}")
    print(f"[DONE] 本次分发 {total_new} 次 | 累计 {manifest.get('total_distributions', 0)} 次")
    print(f"[DONE] Manifest 已更新: {MANIFEST_PATH.name}")

    # 7. 结果汇总
    success_count = sum(1 for r in all_results if r.get("success"))
    fail_count = sum(1 for r in all_results if not r.get("success"))
    print(f"[DONE] 发布结果: {success_count} 成功 / {fail_count} 失败")

    # 8. 发送飞书通知
    if all_results:
        send_feishu_notification(all_results)

    print(f"{'=' * 60}")


# ============================================================
# CLI 入口
# ============================================================


def main():
    parser = argparse.ArgumentParser(
        description="Content Rotator - 自动轮播分发博客文章到社媒平台"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=2,
        help="每次选取的文章数量 (1-5, 默认 2)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="试运行模式，不实际发布",
    )

    args = parser.parse_args()

    # 参数校验
    count = max(1, min(5, args.count))
    if count != args.count:
        print(f"[WARN] count 已限制在 1-5 范围内: {args.count} -> {count}")

    run(count=count, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
