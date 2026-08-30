#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P1-GROWTH-30 Growth Control Plane generator (audit + model consolidation).

This script is read-only against production content. It consumes existing
inventory/report artifacts and emits three deterministic model outputs:

  reports/content_audit/P1_GROWTH_30_TRUST_DECISION_MODEL.csv
  reports/management/GROWTH_PRIORITY_QUEUE.csv
  reports/management/NEXT_7_DAY_GROWTH_QUEUE.csv

The scoring model is intentionally independent from previous rankings. It
derives every sub-score from raw inventory fields so the unified queue is not a
merge of older priority reports.
# Output paths are relative to the travel-blog repository root.
"""
from __future__ import annotations

import csv
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

BLOG_ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = BLOG_ROOT / "content" / "posts"
REPORTS_DIR = BLOG_ROOT / "reports"
ID_RE = re.compile(r"^cbt-[0-9a-f]{12}$")


def read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    return path


def num(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def front_matter_dict(text: str) -> dict:
    m = re.match(r"^(---|\+\+\+)\r?\n(.*?)\r?\n\1", text, re.DOTALL)
    if not m:
        return {}
    data = {}
    for line in m.group(2).splitlines():
        kv = re.match(r"^([A-Za-z0-9_]+)\s*(?::|=)\s*(.*)$", line)
        if not kv:
            continue
        key = kv.group(1)
        value = kv.group(2).strip().strip('"').strip("'")
        if value and not value.startswith("["):
            data[key] = value
    return data


def load_posts() -> dict[str, dict]:
    posts = {}
    for path in sorted(POSTS_DIR.glob("*.md")):
        fm = front_matter_dict(path.read_text(encoding="utf-8", errors="replace"))
        cid = (fm.get("content_id") or "").strip()
        if not ID_RE.match(cid):
            continue
        slug = (fm.get("slug") or path.stem).strip()
        url = (
            fm.get("canonicalURL")
            or fm.get("canonical")
            or f"https://www.chinaboundtravel.com/posts/{slug}/"
        )
        posts[cid] = {
            "file": path.name,
            "slug": slug,
            "title": fm.get("title", ""),
            "url": url,
        }
    return posts


def canonical_content_count(posts: dict[str, dict]) -> dict:
    inventory = read_csv(REPORTS_DIR / "seo" / "CONTENT_SEO_INVENTORY.csv")
    inventory_ids = [row["content_id"] for row in inventory]
    extra = [
        row
        for row in inventory
        if row["content_id"] not in posts and row["content_id"] not in ("", "content_id")
    ]
    missing = [cid for cid in posts if cid not in inventory_ids]
    return {
        "post_files": len(posts),
        "inventory_rows": len(inventory),
        "extra_inventory_rows": extra,
        "posts_missing_from_inventory": missing,
    }


def classify_trust(row: dict) -> tuple[str, str]:
    issue_type = row.get("issue_type", "")
    suggestion = row.get("suggestion", "")
    if issue_type == "事实风险":
        return (
            "FACT_CHECK_REQUIRED",
            "visa/policy/law/price/fee/hours/schedule/distance 等动态事实必须核对官方来源并注明日期；禁止凭空替换事实",
        )
    if issue_type == "中文残留":
        return "AUTO_FIX", "明显不需要的中文残留，按已知规则翻译为英文或移除"
    if issue_type == "品牌风险":
        return "AUTO_FIX", "已知 legacy 人称/本地宣称，机械改为编辑部口吻"
    if issue_type == "AI幻觉":
        if suggestion.startswith("虚构个人经历"):
            return "AUTO_FIX", "虚构第一人称经历，按 legacy persona 规则改写"
        if suggestion.startswith("绝对化/无依据描述"):
            return "SAFE_NORMALIZE", "明显夸大措辞且语义可保留，弱化为保守表达"
        if suggestion.startswith("无来源数据"):
            return "FACT_CHECK_REQUIRED", "数值/价格/里程等主张必须核对来源；禁止自行编造"
    if issue_type == "SEO问题":
        if "内部链接" in suggestion:
            return "SAFE_NORMALIZE", "内链补充需人工选择相关链接，属低风险规范化"
        return "AUTO_FIX", "确定性 SEO 格式问题（标题/描述长度、H2 结构）"
    return "NO_CHANGE", "未命中任何规则，保留人工复核"


def build_trust_decision_model() -> Counter:
    rows = read_csv(REPORTS_DIR / "content_audit" / "CONTENT_TRUST_AUDIT.csv")
    output = []
    counts = Counter()
    for row in rows:
        decision, reason = classify_trust(row)
        output.append(
            {
                "content_id": row.get("content_id", ""),
                "title": row.get("title", ""),
                "risk_level": row.get("risk_level", ""),
                "issue_type": row.get("issue_type", ""),
                "location": row.get("location", ""),
                "suggestion": row.get("suggestion", ""),
                "auto_fix_possible": row.get("auto_fix_possible", ""),
                "decision": decision,
                "decision_reason": reason,
            }
        )
        counts[decision] += 1
    write_csv(
        REPORTS_DIR / "content_audit" / "P1_GROWTH_30_TRUST_DECISION_MODEL.csv",
        output,
        [
            "content_id",
            "title",
            "risk_level",
            "issue_type",
            "location",
            "suggestion",
            "auto_fix_possible",
            "decision",
            "decision_reason",
        ],
    )
    return counts


FACT_CATEGORY_RULES = [
    (
        "visa / immigration",
        ["visa", "passport", "immigration", "transit", "144-hour", "240-hour",
         "entry requirement", "border", "entry"],
    ),
    (
        "law / regulation",
        ["law", "legal", "regulation", "policy", "rules", "restriction", "requirement"],
    ),
    (
        "prices / fees",
        ["price", "prices", "cost", "costs", "fee", "fees", "charge", "charges",
         "fare", "ticket price", "rmb", "cny", "yuan", "usd", "dollar"],
    ),
    (
        "opening hours",
        ["hours", "open", "opens", "closes", "operating"],
    ),
    (
        "schedules",
        ["schedule", "schedules", "timetable", "train schedule"],
    ),
    (
        "transportation",
        ["high-speed rail", "high speed rail", "train", "subway", "metro",
         "taxi", "bus", "transport"],
    ),
    (
        "distances / durations",
        ["km", "miles", "minute", "minutes", "hour", "duration", "distance"],
    ),
    (
        "current availability",
        ["available", "availability", "seasonal", "temporarily", "closed", "currently"],
    ),
]

EVIDENCE_REQUIRED = {
    "visa / immigration": "官方政府签证/出入境页面（如中国驻外使领馆、国家移民管理局）及生效日期",
    "law / regulation": "官方法律法规原文或政府通知及生效日期",
    "prices / fees": "官方承运方/场馆/运营方价格页或合作方费率表及核验日期",
    "opening hours": "官方场馆/运营方页面及核验日期",
    "schedules": "官方承运方时刻表页面及核验日期",
    "transportation": "官方运营方/线路页面及核验日期",
    "distances / durations": "官方线路/地图/运营方文档及核验日期",
    "current availability": "官方场馆/运营方/状态页面及核验日期",
    "unclassified": "人工判断所需证据类型及核验日期",
}


def fact_category(suggestion: str) -> str:
    text = suggestion.lower()
    for category, keywords in FACT_CATEGORY_RULES:
        if any(kw in text for kw in keywords):
            return category
    return "unclassified"


def build_fact_check_queue() -> Counter:
    decision_rows = read_csv(
        REPORTS_DIR / "content_audit" / "P1_GROWTH_30_TRUST_DECISION_MODEL.csv"
    )
    output = []
    counts = Counter()
    for row in decision_rows:
        if row.get("decision") != "FACT_CHECK_REQUIRED":
            continue
        category = fact_category(row.get("suggestion", ""))
        output.append(
            {
                "content_id": row.get("content_id", ""),
                "title": row.get("title", ""),
                "issue_type": row.get("issue_type", ""),
                "location": row.get("location", ""),
                "suggestion": row.get("suggestion", ""),
                "category": category,
                "source_status": "NO_VERIFIED_SOURCE",
                "evidence_required": EVIDENCE_REQUIRED[category],
                "action": "VERIFY_OR_REMOVE",
            }
        )
        counts[category] += 1
    write_csv(
        REPORTS_DIR / "content_audit" / "P1_GROWTH_30R_FACT_CHECK_QUEUE.csv",
        output,
        [
            "content_id",
            "title",
            "issue_type",
            "location",
            "suggestion",
            "category",
            "source_status",
            "evidence_required",
            "action",
        ],
    )
    return counts


AUTO_FIX_FROZEN_IDS = {
    "cbt-e464169c4991",  # REV001
    "cbt-17c6738ffb32",  # REV002 / REV003
    "cbt-b4ff4381a014",  # GROWTH05-CTR-001
    "cbt-80ac63165adb",  # GROWTH28-CTR-001
    "cbt-bfeaa5ca9007",  # GROWTH28-CTR-002
    "cbt-23c31fe5b281",  # GROWTH28-CTR-003
}

AUTO_FIX_WAITING_IDS = {
    "cbt-cc4549872c92",  # GROWTH07B-TECH-001
    "cbt-255af4ed003a",  # GROWTH07C-INDEX-001
}


def auto_fix_candidates(posts: dict[str, dict], limit: int = 15) -> list[dict]:
    inventory_rows = read_csv(REPORTS_DIR / "seo" / "CONTENT_SEO_INVENTORY.csv")
    seo_rows = {row["content_id"]: row for row in inventory_rows}
    opp_rows = {
        row["content_id"]: row
        for row in read_csv(REPORTS_DIR / "seo" / "content_opportunity_scores.csv")
    }
    queue_rows = read_csv(REPORTS_DIR / "management" / "GROWTH_PRIORITY_QUEUE.csv")
    conflicts = load_canonical_conflicts(posts, inventory_rows)

    candidates = []
    for row in queue_rows:
        cid = row["content_id"]
        if cid not in posts:
            continue
        if row.get("status") != "READY":
            continue
        if row.get("recommended_action") in ("FROZEN", "WAIT", "TECHNICAL_FIX"):
            continue
        if cid in AUTO_FIX_FROZEN_IDS or cid in AUTO_FIX_WAITING_IDS or cid in conflicts:
            continue
        seo = seo_rows.get(cid, {})
        if seo.get("indexed_status") != "INDEXED":
            continue
        if num(seo.get("impressions_28d")) <= 0:
            continue
        opp = opp_rows.get(cid, {})
        if str(opp.get("is_primary", "")).lower() != "true" and num(opp.get("duplicate_count")) > 1:
            continue
        candidates.append(
            {
                "content_id": cid,
                "url": row["url"],
                "file": posts[cid]["file"],
                "priority": row["priority"],
                "action": row["recommended_action"],
                "impressions": num(seo.get("impressions_28d")),
                "position": num(seo.get("position_28d")),
                "commercial": num(row["commercial_score"]),
                "trust": num(row["trust_score"]),
                "status": row["status"],
            }
        )
    rank = {"P0": 0, "P1": 1, "P2": 2, "WATCH": 3}
    candidates.sort(
        key=lambda c: (
            rank.get(c["priority"], 9),
            -c["impressions"],
            -c["commercial"],
        )
    )
    return candidates[:limit]


def print_auto_fix_candidates(posts: dict[str, dict]) -> None:
    print("\n===== AUTO-FIX CANDIDATES (eligible) =====")
    for idx, c in enumerate(auto_fix_candidates(posts), 1):
        print(
            f"{idx:2d}. {c['content_id']} {c['priority']} {c['file']} "
            f"imp={c['impressions']:.0f} pos={c['position']:.1f} "
            f"commercial={c['commercial']} trust={c['trust']} action={c['action']}"
        )


def load_social_metrics(posts: dict[str, dict]) -> dict[str, dict]:
    path = BLOG_ROOT / "content" / "social" / "inventory.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("items", data if isinstance(data, list) else [])
    slug_to_cid = {post["slug"]: cid for cid, post in posts.items()}
    result = defaultdict(lambda: {"impressions": 0, "clicks": 0, "engagements": 0, "uv": 0, "published": 0})
    for item in items:
        cid = slug_to_cid.get(item.get("source_article"))
        if not cid:
            continue
        metrics = item.get("metrics") or {}
        result[cid]["impressions"] += num(metrics.get("impressions"))
        result[cid]["clicks"] += num(metrics.get("clicks"))
        result[cid]["engagements"] += num(metrics.get("engagements"))
        result[cid]["uv"] += num(metrics.get("uv"))
        if item.get("status") == "已发布":
            result[cid]["published"] += 1
    return result


def load_canonical_conflicts(posts: dict[str, dict], inventory_rows: list[dict]) -> set[str]:
    path = REPORTS_DIR / "seo" / "CANONICAL_CONFLICT_QUEUE.md"
    text = path.read_text(encoding="utf-8", errors="replace")
    url_map = {row["url"].strip(): row["content_id"] for row in inventory_rows}
    conflicts = set()
    for line in text.splitlines():
        if not line.startswith("| https:"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 3:
            continue
        url, canonical, user_canonical = cells[:3]
        cid = (
            url_map.get(url)
            or url_map.get(canonical)
            or url_map.get(user_canonical)
        )
        if cid:
            conflicts.add(cid)
    return conflicts


def traffic_score(row: dict, max_impressions: float) -> float:
    impressions = num(row.get("impressions_28d"))
    clicks = num(row.get("clicks_28d"))
    if impressions <= 0:
        return 5.0 if row.get("indexed_status") == "INDEXED" else 0.0
    score = 15.0 + 85.0 * math.log1p(impressions) / math.log1p(max(max_impressions, 1.0))
    score += min(10.0, clicks * 2.0)
    return round(min(100.0, score), 1)


def seo_score(row: dict, opp_row: dict) -> float:
    indexed = row.get("indexed_status", "")
    indexed_points = {
        "INDEXED": 30,
        "Alternate page with proper canonical tag": 20,
    }.get(indexed, 10 if indexed == "NOT_INDEXED" else 0)
    position = num(row.get("position_28d"))
    if position > 0:
        if position <= 10:
            position_points = 50
        elif position <= 20:
            position_points = 40
        elif position <= 30:
            position_points = 30
        elif position <= 50:
            position_points = 20
        else:
            position_points = 10
    else:
        position_points = 0
    ctr = num(row.get("ctr_28d"))
    clicks = num(row.get("clicks_28d"))
    if clicks > 0 and ctr >= 5:
        ctr_points = 20
    elif clicks > 0 and ctr >= 2:
        ctr_points = 15
    elif clicks > 0 and ctr >= 0.5:
        ctr_points = 10
    else:
        ctr_points = 0
    query_points = min(20.0, num(opp_row.get("query_count")) * 2.0)
    return round(min(100.0, indexed_points + position_points + ctr_points + query_points), 1)


COMMERCIAL_INTENT_POINTS = {
    "VISA": 90,
    "PAYMENT": 85,
    "INSURANCE": 85,
    "TRAIN": 80,
    "TRANSPORT": 80,
    "HOTEL": 75,
    "INTERNET": 65,
    "FOOD": 60,
    "TOUR": 55,
    "CITY": 45,
    "TRAVEL_GUIDE": 40,
    "GENERAL": 25,
}


def commercial_score(rev_row: dict, opp_row: dict) -> float:
    intent = rev_row.get("commercial_intent", "")
    intent_points = COMMERCIAL_INTENT_POINTS.get(intent, 30)
    query_points = min(15.0, num(opp_row.get("query_count")) * 1.2)
    return round(min(100.0, intent_points * 0.85 + query_points), 1)


def affiliate_score(rev_row: dict, cta_count: int) -> float:
    cta_points = min(100.0, cta_count * 12.0)
    partner_points = min(20.0, num(rev_row.get("partner_count")) * 4.0)
    has_affiliate = 10.0 if str(rev_row.get("has_affiliate", "")).lower() == "true" else 0.0
    return round(min(100.0, cta_points + partner_points + has_affiliate), 1)


def engagement_score(social: dict, max_social_impressions: float) -> float:
    impressions = social["impressions"]
    clicks = social["clicks"]
    if impressions <= 0 and clicks <= 0:
        return 10.0 if social["published"] > 0 else 0.0
    score = 20.0 + 70.0 * math.log1p(impressions) / math.log1p(max(max_social_impressions, 1.0))
    score += 10.0 * min(1.0, clicks / max(1.0, float(clicks)))
    return round(min(100.0, score), 1)


def build_priority_queue(posts: dict[str, dict]) -> list[dict]:
    inventory_rows = read_csv(REPORTS_DIR / "seo" / "CONTENT_SEO_INVENTORY.csv")
    seo_rows = {row["content_id"]: row for row in inventory_rows}
    opp_rows = {
        row["content_id"]: row
        for row in read_csv(REPORTS_DIR / "seo" / "content_opportunity_scores.csv")
    }
    rev_rows = {
        row["content_id"]: row
        for row in read_csv(REPORTS_DIR / "revenue" / "REVENUE_OPPORTUNITY_SCORES.csv")
    }
    affiliate_rows = read_csv(REPORTS_DIR / "revenue" / "AFFILIATE_FUNNEL_INVENTORY.csv")
    affiliate_counts = Counter(row["content_id"] for row in affiliate_rows)
    trust_rows = read_csv(REPORTS_DIR / "content_audit" / "CONTENT_TRUST_AUDIT.csv")
    fact_count = Counter()
    ai_count = Counter()
    brand_count = Counter()
    seo_issue_count = Counter()
    for row in trust_rows:
        cid = row["content_id"]
        if cid not in posts:
            continue
        issue_type = row.get("issue_type", "")
        if issue_type == "事实风险":
            fact_count[cid] += 1
        elif issue_type == "AI幻觉":
            ai_count[cid] += 1
        elif issue_type == "品牌风险":
            brand_count[cid] += 1
        elif issue_type == "SEO问题":
            seo_issue_count[cid] += 1

    social = load_social_metrics(posts)
    conflicts = load_canonical_conflicts(posts, inventory_rows)

    frozen_ids = {
        "cbt-e464169c4991",  # REV001
        "cbt-17c6738ffb32",  # REV002 / REV003
        "cbt-b4ff4381a014",  # GROWTH05-CTR-001
        "cbt-80ac63165adb",  # GROWTH28-CTR-001
        "cbt-bfeaa5ca9007",  # GROWTH28-CTR-002
        "cbt-23c31fe5b281",  # GROWTH28-CTR-003
    }
    waiting_ids = {
        "cbt-cc4549872c92",  # GROWTH07B-TECH-001
        "cbt-255af4ed003a",  # GROWTH07C-INDEX-001
    }

    max_impressions = max(
        [num(row.get("impressions_28d")) for row in inventory_rows if row["content_id"] in posts]
        + [1.0]
    )
    max_social_impressions = max(
        [v["impressions"] for v in social.values() if v["impressions"] > 0] + [1.0]
    )

    rows = []
    for cid, post in posts.items():
        row = seo_rows.get(cid, {})
        opp_row = opp_rows.get(cid, {})
        rev_row = rev_rows.get(cid, {})
        traffic = traffic_score(row, max_impressions)
        seo = seo_score(row, opp_row)
        engagement = engagement_score(social[cid], max_social_impressions)
        commercial = commercial_score(rev_row, opp_row)
        affiliate = affiliate_score(rev_row, affiliate_counts.get(cid, 0))
        revenue = 0.0  # no revenue evidence exists in any current artifact
        trust = max(
            0.0,
            100.0
            - fact_count[cid] * 3.0
            - ai_count[cid] * 2.0
            - brand_count[cid] * 1.0
            - seo_issue_count[cid] * 1.0,
        )
        risk = 0.0
        if cid in frozen_ids:
            risk += 50.0
        if cid in conflicts:
            risk += 30.0
        if cid in waiting_ids:
            risk += 20.0
        if fact_count[cid] > 10:
            risk += 10.0
        if num(opp_row.get("duplicate_count")) > 1:
            risk += 10.0
        risk = round(min(100.0, risk), 1)

        if cid in frozen_ids:
            status = "FROZEN"
        elif cid in waiting_ids:
            status = "WAIT"
        elif cid in conflicts:
            status = "TECHNICAL_FIX"
        else:
            status = "READY"

        indexed = row.get("indexed_status", "")
        if cid in frozen_ids:
            action = "FROZEN"
        elif cid in waiting_ids:
            action = "WAIT"
        elif cid in conflicts:
            action = "TECHNICAL_FIX"
        elif indexed in ("NOT_INDEXED", "Page with redirect", "UNKNOWN"):
            action = "TECHNICAL_FIX"
        elif fact_count[cid] > 0:
            action = "FACT_CHECK"
        elif traffic >= 55 and seo >= 40:
            action = "OPTIMIZE"
        elif commercial >= 60 and affiliate >= 40:
            action = "SCALE"
        elif traffic <= 15:
            action = "WAIT"
        elif social[cid]["published"] > 0 or engagement > 0:
            action = "MONITOR"
        else:
            action = "MONITOR"

        priority_score = round(
            max(
                0.0,
                min(
                    100.0,
                    0.25 * traffic
                    + 0.20 * seo
                    + 0.15 * engagement
                    + 0.15 * commercial
                    + 0.10 * affiliate
                    + 0.05 * revenue
                    + 0.10 * trust
                    - 0.15 * risk,
                ),
            ),
            1,
        )
        if priority_score >= 65:
            priority = "P0"
        elif priority_score >= 50:
            priority = "P1"
        elif priority_score >= 35:
            priority = "P2"
        else:
            priority = "WATCH"

        reason = (
            f"impressions={num(row.get('impressions_28d')):.0f}, "
            f"pos={num(row.get('position_28d')):.1f}, indexed={indexed or 'UNKNOWN'}, "
            f"fact_issues={fact_count[cid]}, affiliate_ctas={affiliate_counts.get(cid, 0)}, "
            f"social_published={social[cid]['published']}"
        )
        rows.append(
            {
                "content_id": cid,
                "url": post["url"],
                "priority": priority,
                "recommended_action": action,
                "reason": reason,
                "traffic_score": traffic,
                "seo_score": seo,
                "engagement_score": engagement,
                "commercial_score": commercial,
                "affiliate_score": affiliate,
                "revenue_score": revenue,
                "trust_score": trust,
                "risk_score": risk,
                "status": status,
                "_score": priority_score,
            }
        )

    rows.sort(
        key=lambda r: (
            -r["_score"],
            -r["traffic_score"],
            -r["seo_score"],
            r["content_id"],
        )
    )
    output = [
        {k: v for k, v in row.items() if not k.startswith("_")}
        for row in rows
    ]
    write_csv(
        REPORTS_DIR / "management" / "GROWTH_PRIORITY_QUEUE.csv",
        output,
        [
            "content_id",
            "url",
            "priority",
            "recommended_action",
            "reason",
            "traffic_score",
            "seo_score",
            "engagement_score",
            "commercial_score",
            "affiliate_score",
            "revenue_score",
            "trust_score",
            "risk_score",
            "status",
        ],
    )
    return rows


def governance_for(action: str, status: str) -> str:
    if status == "FROZEN":
        return "FROZEN"
    if action in ("WAIT", "MONITOR"):
        return "WAIT"
    if action == "SCALE":
        return "REVIEW_REQUIRED"
    return "REVIEW_REQUIRED"


def build_next_7_day(priority_rows: list[dict]) -> list[dict]:
    frozen = [r for r in priority_rows if r["status"] == "FROZEN"]
    wait = [r for r in priority_rows if r["status"] == "WAIT"]
    actionable = [
        r
        for r in priority_rows
        if r["status"] not in ("FROZEN", "WAIT")
        and r["recommended_action"] not in ("WAIT",)
    ]
    p0 = [r for r in actionable if r["priority"] == "P0"][:3]
    p1 = [r for r in actionable if r["priority"] == "P1"][:6]
    watch = (frozen[:2] + wait[:2])

    queue = []
    for day, rows, priority_label in (
        (1, p0, None),
        (2, p0, None),
        (3, p1, None),
        (4, p1, None),
        (5, p1, None),
        (6, watch, "WATCH"),
        (7, watch, "WATCH"),
    ):
        for row in rows:
            if any(q["content_id"] == row["content_id"] for q in queue):
                continue
            queue.append(
                {
                    "content_id": row["content_id"],
                    "url": row["url"],
                    "priority": priority_label or row["priority"],
                    "recommended_action": row["recommended_action"],
                    "reason": row["reason"],
                    "status": row["status"],
                    "day_window": day,
                    "governance_class": governance_for(row["recommended_action"], row["status"]),
                }
            )
    write_csv(
        REPORTS_DIR / "management" / "NEXT_7_DAY_GROWTH_QUEUE.csv",
        queue,
        [
            "content_id",
            "url",
            "priority",
            "recommended_action",
            "reason",
            "status",
            "day_window",
            "governance_class",
        ],
    )
    return queue


def main() -> int:
    posts = load_posts()
    count = canonical_content_count(posts)
    print("===== CANONICAL CONTENT COUNT =====")
    print(f"content/posts/*.md with valid unique content_id : {count['post_files']}")
    print(f"CONTENT_SEO_INVENTORY.csv rows                   : {count['inventory_rows']}")
    print(f"inventory-only rows (drafts/historical)          : {len(count['extra_inventory_rows'])}")
    for row in count["extra_inventory_rows"]:
        print(f"  - {row['content_id']} {row['url']} ({row['indexed_status']})")
    if count["posts_missing_from_inventory"]:
        print("posts missing from inventory:", count["posts_missing_from_inventory"])

    print("\n===== TRUST DECISION MODEL =====")
    decision_counts = build_trust_decision_model()
    for key in ("AUTO_FIX", "SAFE_NORMALIZE", "FACT_CHECK_REQUIRED", "NO_CHANGE"):
        print(f"{key}: {decision_counts.get(key, 0)}")
    print("total:", sum(decision_counts.values()))

    print("\n===== FACT CHECK QUEUE =====")
    fact_counts = build_fact_check_queue()
    print("rows:", sum(fact_counts.values()))
    for category, count in fact_counts.most_common():
        print(f"{category}: {count}")

    print("\n===== UNIFIED PRIORITY QUEUE (TOP 10) =====")
    priority_rows = build_priority_queue(posts)
    for idx, row in enumerate(priority_rows[:10], 1):
        print(
            f"{idx:2d}. {row['content_id']} {row['priority']} {row['recommended_action']:14s} "
            f"score={row['_score']:5.1f} status={row['status']}"
        )

    print("\n===== NEXT 7 DAY QUEUE =====")
    queue = build_next_7_day(priority_rows)
    for row in queue:
        print(
            f"day={row['day_window']} {row['priority']:5s} {row['recommended_action']:14s} "
            f"{row['content_id']} {row['governance_class']}"
        )
    print_auto_fix_candidates(posts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
