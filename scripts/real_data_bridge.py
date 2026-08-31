#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Real Data Bridge - 将 reports/real_data/ 下的真实数据转换为各 Learning Closed Loop 的标准记录格式。

每个 learning loop 调用对应的 bridge 函数，获取标准化的记录列表，
然后追加到各自的 performance_history 中，供后续 analyze/learn/decide 使用。

数据源：
- reports/real_data/ga4_real_data.json
- reports/real_data/gsc_real_data.json
- reports/real_data/social_real_data.json
- reports/real_data/content_real_data.json
- reports/revenue/revenue_snapshot.json
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

PROJECT_ROOT = Path(__file__).parent.parent
REAL_DATA_DIR = PROJECT_ROOT / "reports" / "real_data"
REVENUE_DIR = PROJECT_ROOT / "reports" / "revenue"


def _load_json(path: Path) -> Optional[Dict]:
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def _is_real(data: Optional[Dict]) -> bool:
    return bool(data and data.get("is_real_data", False))


# ============================================================
# Social Learning Bridge
# ============================================================

def get_social_records() -> List[Dict]:
    """从 social_real_data.json 转换为 Social Learning 标准记录格式。"""
    data = _load_json(REAL_DATA_DIR / "social_real_data.json")
    if not _is_real(data):
        return []

    records = []
    for post in data.get("posts", []):
        record = {
            "post_id": post.get("id", ""),
            "platform": post.get("platform", "unknown"),
            "text": post.get("text", ""),
            "published_at": post.get("published_at", ""),
            "date": post.get("published_at", "")[:10] if post.get("published_at") else "",
            "metrics": {
                "impressions": post.get("impressions", 0),
                "clicks": post.get("clicks", 0),
                "likes": post.get("likes", 0),
                "comments": post.get("comments", 0),
                "shares": post.get("shares", 0),
                "engagement": post.get("likes", 0) + post.get("comments", 0) + post.get("shares", 0),
                "engagement_rate": post.get("engagement_rate", 0),
            },
            "metadata": {
                "channel_name": post.get("channel_name", ""),
                "status": post.get("status", ""),
            },
            "calculated": {
                "ctr": (post.get("clicks", 0) / max(1, post.get("impressions", 1)) * 100) if post.get("impressions", 0) > 0 else 0,
                "engagement_rate": post.get("engagement_rate", 0),
                "engagement_per_impression": (
                    (post.get("likes", 0) + post.get("comments", 0) + post.get("shares", 0))
                    / max(1, post.get("impressions", 1))
                ) if post.get("impressions", 0) > 0 else 0,
                "engagement": post.get("likes", 0) + post.get("comments", 0) + post.get("shares", 0),
            },
        }
        records.append(record)
    return records


# ============================================================
# SEO Learning Bridge
# ============================================================

def get_seo_records() -> List[Dict]:
    """从 gsc_real_data.json 转换为 SEO Learning 标准记录格式。"""
    data = _load_json(REAL_DATA_DIR / "gsc_real_data.json")
    if not _is_real(data):
        return []

    records = []
    # Top queries
    for q in data.get("top_queries", []):
        record = {
            "type": "query",
            "keyword": q.get("query", ""),
            "date": data.get("data_date", ""),
            "metrics": {
                "impressions": q.get("impressions", 0),
                "clicks": q.get("clicks", 0),
                "ctr": q.get("ctr", 0),
                "position": q.get("position", 0),
            },
            "metadata": {
                "search_type": "web",
            },
            "calculated": {
                "traffic_potential": q.get("impressions", 0) * max(0, (10 - q.get("position", 10)) / 10),
                "is_opportunity": 5 <= q.get("position", 0) <= 30 and q.get("ctr", 0) < 5,
            },
        }
        records.append(record)

    # Top pages
    for p in data.get("top_pages", []):
        record = {
            "type": "page",
            "keyword": p.get("page", ""),
            "page": p.get("page", ""),
            "date": data.get("data_date", ""),
            "metrics": {
                "impressions": p.get("impressions", 0),
                "clicks": p.get("clicks", 0),
                "ctr": p.get("ctr", 0),
                "position": p.get("position", 0),
            },
            "metadata": {},
            "calculated": {
                "traffic_potential": p.get("impressions", 0) * max(0, (10 - p.get("position", 10)) / 10),
                "is_opportunity": 5 <= p.get("position", 0) <= 30 and p.get("ctr", 0) < 5,
                "is_optimization_candidate": 5 <= p.get("position", 0) <= 30,
            },
        }
        records.append(record)

    return records


# ============================================================
# Content Learning Bridge
# ============================================================

def get_content_records() -> List[Dict]:
    """从 content_real_data.json 转换为 Content Learning 标准记录格式。"""
    data = _load_json(REAL_DATA_DIR / "content_real_data.json")
    if not _is_real(data):
        return []

    records = []
    for article in data.get("top_articles", []):
        record = {
            "title": article.get("slug", "").replace("-", " ").title(),
            "slug": article.get("slug", ""),
            "date": data.get("data_date", ""),
            "metrics": {
                "views": 0,  # Content real data doesn't have views per article
                "revenue": 0,
                "quality_score": 0,
                "word_count": article.get("word_count", 0),
                "has_affiliate_links": article.get("has_affiliate_links", False),
                "has_internal_links": article.get("has_internal_links", False),
            },
            "metadata": {
                "category": "article",
                "keywords": [],
                "publish_date": "",
                "cta_count": 1 if article.get("has_affiliate_links", False) else 0,
                "internal_links": 1 if article.get("has_internal_links", False) else 0,
                "external_links": 0,
            },
            "calculated": {
                "ctr": 0,
                "revenue_per_1000_views": 0,
                "engagement_score": 0,
            },
        }
        records.append(record)
    return records


def normalize_content_record(record: Dict) -> Dict:
    """兼容旧格式和新格式的 content record，确保有 metrics 键。"""
    if "metrics" in record:
        return record
    # 旧格式: {title, slug, word_count, has_affiliate_links, has_internal_links}
    return {
        "title": record.get("title", record.get("slug", "")),
        "slug": record.get("slug", ""),
        "date": record.get("date", ""),
        "metrics": {
            "views": record.get("views", 0),
            "revenue": record.get("revenue", 0),
            "quality_score": record.get("quality_score", 0),
            "word_count": record.get("word_count", 0),
            "has_affiliate_links": record.get("has_affiliate_links", False),
            "has_internal_links": record.get("has_internal_links", False),
        },
        "metadata": record.get("metadata", {}),
        "calculated": record.get("calculated", {}),
    }


# ============================================================
# Conversion Learning Bridge
# ============================================================

def get_conversion_records() -> List[Dict]:
    """从 real_data + affiliate 数据转换为 Conversion Learning 标准记录格式。"""
    ga4 = _load_json(REAL_DATA_DIR / "ga4_real_data.json")
    revenue = _load_json(REVENUE_DIR / "revenue_snapshot.json")

    records = []

    # GA4 engagement data
    if _is_real(ga4):
        metrics = ga4.get("metrics", {})
        record = {
            "type": "site_overall",
            "date": ga4.get("data_date", ""),
            "metrics": {
                "sessions": metrics.get("sessions", 0),
                "users": metrics.get("activeUsers", 0),
                "pageviews": metrics.get("screenPageViews", 0),
                "engaged_sessions": metrics.get("engagedSessions", 0),
                "bounce_rate": metrics.get("bounceRate", 0),
                "avg_session_duration": metrics.get("averageSessionDuration", 0),
                "engagement_rate": metrics.get("engagementRate", 0),
            },
            "metadata": {},
            "calculated": {
                "engagement_ratio": (
                    metrics.get("engagedSessions", 0) / max(1, metrics.get("sessions", 1))
                ) if metrics.get("sessions", 0) > 0 else 0,
            },
        }
        records.append(record)

    # Revenue / affiliate data
    if revenue and revenue.get("is_real_data", True):
        tp = revenue.get("travelpayouts", {})
        if tp:
            record = {
                "type": "affiliate_travelpayouts",
                "date": revenue.get("snapshot_date", ""),
                "metrics": {
                    "clicks": tp.get("clicks", tp.get("total_clicks", 0)),
                    "bookings": tp.get("bookings", tp.get("total_bookings", 0)),
                    "revenue": tp.get("revenue", tp.get("total_revenue", 0)),
                    "conversion_rate": (
                        tp.get("bookings", 0) / max(1, tp.get("clicks", 1)) * 100
                    ) if tp.get("clicks", 0) > 0 else 0,
                },
                "metadata": {"partner": "travelpayouts"},
                "calculated": {},
            }
            records.append(record)

    return records


# ============================================================
# User Learning Bridge
# ============================================================

def get_user_records() -> List[Dict]:
    """从 ga4_real_data.json 转换为 User Learning 标准记录格式。"""
    data = _load_json(REAL_DATA_DIR / "ga4_real_data.json")
    if not _is_real(data):
        return []

    records = []
    metrics = data.get("metrics", {})

    # Overall user metrics
    record = {
        "type": "overall",
        "date": data.get("data_date", ""),
        "metrics": {
            "total_users": metrics.get("activeUsers", 0),
            "sessions": metrics.get("sessions", 0),
            "pageviews": metrics.get("screenPageViews", 0),
            "engaged_sessions": metrics.get("engagedSessions", 0),
            "new_users": metrics.get("newUsers", 0),
            "bounce_rate": metrics.get("bounceRate", 0),
            "avg_session_duration": metrics.get("averageSessionDuration", 0),
            "engagement_rate": metrics.get("engagementRate", 0),
        },
        "metadata": {},
        "calculated": {
            "returning_users": max(0, metrics.get("activeUsers", 0) - metrics.get("newUsers", 0)),
            "pages_per_session": metrics.get("screenPageViews", 0) / max(1, metrics.get("sessions", 1)),
        },
    }
    records.append(record)

    # Traffic source segments
    for src in data.get("traffic_sources", []):
        record = {
            "type": "traffic_source",
            "segment": src.get("channel", "unknown"),
            "date": data.get("data_date", ""),
            "metrics": {
                "sessions": src.get("sessions", 0),
                "users": src.get("activeUsers", 0),
            },
            "metadata": {"channel": src.get("channel", "")},
            "calculated": {},
        }
        records.append(record)

    # Top pages (user engagement)
    for page in data.get("top_pages", []):
        record = {
            "type": "page_engagement",
            "page": page.get("path", ""),
            "title": page.get("title", ""),
            "date": data.get("data_date", ""),
            "metrics": {
                "pageviews": page.get("pageviews", 0),
                "sessions": page.get("sessions", 0),
                "users": page.get("activeUsers", 0),
            },
            "metadata": {},
            "calculated": {},
        }
        records.append(record)

    return records


# ============================================================
# Revenue Learning Bridge
# ============================================================

def get_revenue_records() -> List[Dict]:
    """从 revenue_snapshot.json + real_data 转换为 Revenue Learning 标准记录格式。"""
    revenue = _load_json(REVENUE_DIR / "revenue_snapshot.json")
    ga4 = _load_json(REAL_DATA_DIR / "ga4_real_data.json")

    records = []

    if revenue:
        # Overall revenue
        total_clicks = revenue.get("total_clicks", 0)
        total_bookings = revenue.get("total_bookings", 0)
        total_revenue = revenue.get("total_revenue", 0)

        record = {
            "type": "overall",
            "date": revenue.get("snapshot_date", revenue.get("pull_time", "")),
            "metrics": {
                "total_clicks": total_clicks,
                "total_bookings": total_bookings,
                "total_revenue": total_revenue,
                "conversion_rate": (total_bookings / max(1, total_clicks) * 100) if total_clicks > 0 else 0,
                "avg_booking_value": (total_revenue / max(1, total_bookings)) if total_bookings > 0 else 0,
            },
            "metadata": {},
            "calculated": {
                "revenue_per_click": (total_revenue / max(1, total_clicks)) if total_clicks > 0 else 0,
            },
        }
        records.append(record)

        # Per-partner breakdown
        partners = revenue.get("partners", revenue.get("by_partner", {}))
        if isinstance(partners, dict):
            for partner_name, partner_data in partners.items():
                if isinstance(partner_data, dict):
                    record = {
                        "type": "partner",
                        "partner": partner_name,
                        "date": revenue.get("snapshot_date", ""),
                        "metrics": {
                            "clicks": partner_data.get("clicks", 0),
                            "bookings": partner_data.get("bookings", 0),
                            "revenue": partner_data.get("revenue", 0),
                            "conversion_rate": partner_data.get("conversion_rate", 0),
                        },
                        "metadata": {"partner": partner_name},
                        "calculated": {},
                    }
                    records.append(record)

    # GA4 traffic for revenue context
    if _is_real(ga4):
        metrics = ga4.get("metrics", {})
        record = {
            "type": "traffic_context",
            "date": ga4.get("data_date", ""),
            "metrics": {
                "sessions": metrics.get("sessions", 0),
                "users": metrics.get("activeUsers", 0),
                "pageviews": metrics.get("screenPageViews", 0),
            },
            "metadata": {},
            "calculated": {
                "clicks_per_session": (total_clicks / max(1, metrics.get("sessions", 1))) if metrics.get("sessions", 0) > 0 else 0,
            },
        }
        records.append(record)

    return records


# ============================================================
# Utility: 检查所有 real_data 源的状态
# ============================================================

def get_data_status() -> Dict[str, Any]:
    """返回所有 real_data 源的状态摘要。"""
    status = {}
    for name in ["ga4", "gsc", "social", "content"]:
        data = _load_json(REAL_DATA_DIR / f"{name}_real_data.json")
        status[name] = {
            "available": data is not None,
            "is_real_data": _is_real(data),
            "status": data.get("status", "unknown") if data else "missing",
            "data_date": data.get("data_date", None) if data else None,
        }
    return status


if __name__ == "__main__":
    # CLI: 打印各 bridge 的记录数
    print("=== Real Data Bridge Status ===")
    status = get_data_status()
    for name, s in status.items():
        print(f"  {name:8s}: real={s['is_real_data']} status={s['status']} date={s['data_date']}")

    print("\n=== Bridge Record Counts ===")
    bridges = {
        "social": get_social_records,
        "seo": get_seo_records,
        "content": get_content_records,
        "conversion": get_conversion_records,
        "user": get_user_records,
        "revenue": get_revenue_records,
    }
    for name, func in bridges.items():
        records = func()
        print(f"  {name:12s}: {len(records)} records")
        if records:
            print(f"    first: {json.dumps(records[0], ensure_ascii=False)[:150]}")
