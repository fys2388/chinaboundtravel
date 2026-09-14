#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
social_reports.py - ChinaBound 社媒日报 / 周报板块生成
======================================================

复用 scripts/social_content_agent.py 的 summarize_daily / summarize_weekly
计算社媒数据，并渲染为飞书卡片富文本 block，供现有日报/周报脚本引用或独立运行。

提供两个渲染接口（返回飞书 card block 列表）：
  social_daily_block(summary)   -> [{"tag":"div",...}, ...]
  social_weekly_block(summary)  -> [{"tag":"div",...}, ...]

以及一个便捷函数 social_daily_summary() / social_weekly_summary()
直接从资产库读取并返回结构化数据 + 飞书文本。

接入现有日报（feishu_daily_report.py）示例：
    from scripts.social_reports import social_daily_block, social_daily_summary
    s = social_daily_summary()
    if s["total_published"] or True:
        card["elements"].extend(social_daily_block(s))

用法：
  python scripts/social_reports.py daily [--date YYYY-MM-DD] [--print-block]
  python scripts/social_reports.py weekly [--end YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

SCRIPT_DIR = Path(__file__).resolve().parent
BLOG_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from social_content_agent import (  # noqa: E402
    INVENTORY_FILE,
    PLATFORMS,
    load_inventory,
    summarize_daily,
    summarize_weekly,
)

# 平台中文名
PLATFORM_CN = {"ig": "Instagram", "pinterest": "Pinterest",
               "x": "X/Twitter", "fb": "Facebook"}
TYPE_CN = {"knowledge": "知识", "tip": "避坑/技巧", "story": "故事",
           "visual": "视觉", "conversion": "转化"}
ANALYTICS_DIR = BLOG_ROOT / "data" / "social"
REAL_SOCIAL_DATA = BLOG_ROOT / "reports" / "real_data" / "social_real_data.json"
PLATFORM_ALIASES = {
    "ig": "ig",
    "instagram": "ig",
    "fb": "fb",
    "facebook": "fb",
    "x": "x",
    "twitter": "x",
    "pinterest": "pinterest",
}


def _fmt(n) -> str:
    try:
        return f"{int(n):,}"
    except (TypeError, ValueError):
        return "0"


def _ctr(imp, clk) -> str:
    imp = int(imp or 0)
    clk = int(clk or 0)
    if imp <= 0:
        return "-"
    return f"{clk / imp * 100:.2f}%"


# ============================================================
# 结构化摘要
# ============================================================


def _date_prefix(value) -> str:
    match = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", str(value or ""))
    if not match:
        return ""
    year, month, day = match.groups()
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def _metric_value(post: dict, name: str) -> int:
    stats = post.get("stats") if isinstance(post.get("stats"), dict) else {}
    metrics = post.get("metrics") if isinstance(post.get("metrics"), dict) else {}
    value = post.get(name, stats.get(name, metrics.get(name, 0)))
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _load_analytics_snapshot():
    candidates = sorted(
        ANALYTICS_DIR.glob("analytics_*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    candidates.append(REAL_SOCIAL_DATA)
    for path in candidates:
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        status = str(payload.get("status", "")).lower()
        if status not in {"ok", "success"}:
            continue
        count = payload.get("metrics_available_count")
        impression_count = payload.get("impression_metric_count")
        if count is None and isinstance(payload.get("posts"), list):
            flags = [
                post.get("metrics_available")
                for post in payload["posts"]
                if isinstance(post, dict)
            ]
            count = sum(1 for flag in flags if flag is True) if flags else 0
            impression_flags = [
                post.get("has_impression_metric")
                for post in payload["posts"]
                if isinstance(post, dict)
            ]
            if any(flag is not None for flag in impression_flags):
                impression_count = sum(
                    1 for flag in impression_flags if flag is True
                )
        if int(count or 0) <= 0 or int(impression_count or 0) <= 0:
            continue
        return payload
    return None


def _augment_with_analytics(summary: dict, target_date: date) -> dict:
    snapshot = _load_analytics_snapshot()
    if not snapshot:
        summary["analytics_status"] = "unavailable"
        summary["analytics_source"] = "unavailable"
        summary["analytics_reason"] = (
            "No Buffer analytics snapshot with verified metric fields"
        )
        summary["analytics_post_count"] = 0
        return summary

    for platform in PLATFORMS:
        summary["by_platform"][platform]["impressions"] = 0
        summary["by_platform"][platform]["clicks"] = 0
        summary["by_platform"][platform]["uv"] = 0

    matched_posts = 0
    target = target_date.isoformat()
    for post in snapshot.get("posts", []):
        if not isinstance(post, dict):
            continue
        published_at = (
            post.get("created_at")
            or post.get("published_at")
            or post.get("sentAt")
            or post.get("dueAt")
        )
        if _date_prefix(published_at) != target:
            continue
        platform = PLATFORM_ALIASES.get(
            str(post.get("platform", "")).lower()
        )
        if platform not in summary["by_platform"]:
            continue
        summary["by_platform"][platform]["impressions"] += _metric_value(
            post, "impressions"
        )
        summary["by_platform"][platform]["clicks"] += _metric_value(post, "clicks")
        matched_posts += 1

    summary["total_impressions"] = sum(
        item["impressions"] for item in summary["by_platform"].values()
    )
    summary["total_clicks"] = sum(
        item["clicks"] for item in summary["by_platform"].values()
    )
    summary["total_uv"] = sum(
        item["uv"] for item in summary["by_platform"].values()
    )
    summary["analytics_status"] = "ok"
    summary["analytics_source"] = (
        snapshot.get("data_source") or snapshot.get("source") or "buffer_api"
    )
    summary["analytics_reason"] = ""
    summary["analytics_post_count"] = matched_posts
    return summary


def social_daily_summary(d: date = None) -> dict:
    data = load_inventory()
    target_date = d or date.today() - timedelta(days=1)
    return _augment_with_analytics(summarize_daily(data, target_date), target_date)


def social_weekly_summary(end: date = None) -> dict:
    data = load_inventory()
    return summarize_weekly(data, end)


# ============================================================
# 飞书卡片 block 渲染
# ============================================================


def social_daily_block(summary: dict) -> list:
    """日报社媒数据板块：昨日发布数、各平台曝光/点击、引流 UV。"""
    bp = summary["by_platform"]
    lines = [f"📣 **社媒数据**｜{summary['date']}",
             f"昨日发布：**{summary['total_published']}** 条 | 总曝光 **{_fmt(summary['total_impressions'])}** | "
             f"点击 **{_fmt(summary['total_clicks'])}** | 引流UV **{_fmt(summary['total_uv'])}**"]
    for p in PLATFORMS:
        d = bp.get(p, {})
        lines.append(f"· {PLATFORM_CN[p]}: 发布 {d['published']} | "
                     f"曝光 {_fmt(d['impressions'])} | 点击 {_fmt(d['clicks'])} | UV {_fmt(d['uv'])}")
    if summary.get("analytics_status") != "ok":
        lines.append("· 分析数据不可用：当前曝光/点击不是可验证的真实值")
    return [{"tag": "div", "text": {"tag": "lark_md", "content": "\n".join(lines)}}]


def social_weekly_block(summary: dict) -> list:
    """周报社媒增长复盘：总量、分平台、Top5/Bottom5、类型对比、下周建议。"""
    blocks = []
    bp = summary["by_platform"]
    lines = [f"📈 **社媒增长复盘**｜{summary['week_start']} ~ {summary['week_end']}",
             f"本周发布 **{summary['total_published']}** 条"]
    plat_lines = [f"· {PLATFORM_CN[p]}: {bp[p]['published']}条, 曝光{_fmt(bp[p]['impressions'])}, "
                  f"点击{_fmt(bp[p]['clicks'])}, UV{_fmt(bp[p]['uv'])}" for p in PLATFORMS]
    lines += plat_lines
    blocks.append({"tag": "div", "text": {"tag": "lark_md",
                                          "content": "\n".join(lines)}})

    # Top5 / Bottom5
    if summary.get("top5"):
        top_lines = ["**高表现 Top5**"]
        for i, t in enumerate(summary["top5"], 1):
            top_lines.append(f"{i}. {t['source_article'][:40]} ({PLATFORM_CN[t['platform']]}/{TYPE_CN.get(t['type'], t['type'])}) "
                             f"曝光{_fmt(t['impressions'])}/点击{_fmt(t['clicks'])}")
        blocks.append({"tag": "div", "text": {"tag": "lark_md", "content": "\n".join(top_lines)}})
    if summary.get("bottom5"):
        bot_lines = ["**低表现 Bottom5**"]
        for i, t in enumerate(summary["bottom5"], 1):
            bot_lines.append(f"{i}. {t['source_article'][:40]} "
                             f"曝光{_fmt(t['impressions'])}/点击{_fmt(t['clicks'])}")
        blocks.append({"tag": "div", "text": {"tag": "lark_md", "content": "\n".join(bot_lines)}})

    # 类型对比
    if summary.get("by_type"):
        type_lines = ["**内容类型效果对比**"]
        for t, bt in sorted(summary["by_type"].items(), key=lambda x: -x[1]["impressions"]):
            type_lines.append(f"· {TYPE_CN.get(t, t)}: {bt['count']}条, "
                              f"曝光{_fmt(bt['impressions'])}, CTR {_ctr(bt['impressions'], bt['clicks'])}")
        blocks.append({"tag": "div", "text": {"tag": "lark_md", "content": "\n".join(type_lines)}})

    # 下周优化建议
    adv_lines = ["**下周优化建议**"]
    for a in (summary.get("type_advice") or []):
        adv_lines.append(f"· {a}")
    adv_lines.append(f"· {summary.get('next_week_suggestion', '')}")
    blocks.append({"tag": "div", "text": {"tag": "lark_md", "content": "\n".join(adv_lines)}})
    return blocks


# ============================================================
# CLI
# ============================================================


def _dump(path: Path, payload: dict) -> Path:
    out = BLOG_ROOT / path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="社媒日报/周报板块生成")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("daily", help="社媒日报")
    p.add_argument("--date", help="YYYY-MM-DD（默认昨日）")
    p.add_argument("--print-block", action="store_true", help="打印飞书卡片 block JSON")
    p.set_defaults(which="daily")

    p = sub.add_parser("weekly", help="社媒周报")
    p.add_argument("--end", help="YYYY-MM-DD（默认今天）")
    p.add_argument("--print-block", action="store_true", help="打印飞书卡片 block JSON")
    p.set_defaults(which="weekly")

    args = ap.parse_args(argv)

    if args.which == "daily":
        d = date.fromisoformat(args.date) if args.date else date.today() - timedelta(days=1)
        summary = social_daily_summary(d)
        path = _dump(f"reports/social/social_daily_{d.isoformat()}.json", summary)
        blocks = social_daily_block(summary)
    else:
        end = date.fromisoformat(args.end) if args.end else date.today()
        summary = social_weekly_summary(end)
        path = _dump(f"reports/social/social_weekly_{end.isoformat()}.json", summary)
        blocks = social_weekly_block(summary)

    print(f"已写入: {path}")
    if args.print_block:
        print(json.dumps(blocks, ensure_ascii=False, indent=2))
    else:
        # 纯文本预览
        for b in blocks:
            print(b["text"]["content"])
            print("-" * 40)
    return 0


if __name__ == "__main__":
    sys.exit(main())
