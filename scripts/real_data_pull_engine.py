#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChinaBound Travel - Real Data Pull Engine v2.1
真实数据拉取引擎（API直连版）

v2.1 变更：
- GA4: 直接调用 GA4 Data API REST 端点（不再从本地日报二次提取）
- GSC: 直接调用 Search Console API（利用 gsc_utils 认证）
- Social: 直接调用 Buffer GraphQL API 拉取已发布帖子 metrics
- Content: 保持本地扫描（本地文件即真实数据源）
- 集成 ai_governance Kill Switch 检查

原则：只返回真实 API 数值；无凭据或调用失败返回明确状态（绝不虚构数据）。

使用方式：
    python scripts/real_data_pull_engine.py --all
    python scripts/real_data_pull_engine.py --ga4
    python scripts/real_data_pull_engine.py --gsc
    python scripts/real_data_pull_engine.py --social
    python scripts/real_data_pull_engine.py --content
    python scripts/real_data_pull_engine.py --validate
"""
from __future__ import annotations

import os
import sys
import json
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except Exception:
    pass

import requests

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
REPORTS_DIR = PROJECT_ROOT / "reports"
REAL_DATA_DIR = REPORTS_DIR / "real_data"
REAL_DATA_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(SCRIPTS_DIR))

# 输出文件
GA4_REAL_DATA = REAL_DATA_DIR / "ga4_real_data.json"
GSC_REAL_DATA = REAL_DATA_DIR / "gsc_real_data.json"
SOCIAL_REAL_DATA = REAL_DATA_DIR / "social_real_data.json"
CONTENT_REAL_DATA = REAL_DATA_DIR / "content_real_data.json"
PARTNERIZE_REAL_DATA = REAL_DATA_DIR / "partnerize_real_data.json"
IMPACT_REAL_DATA = REAL_DATA_DIR / "impact_real_data.json"
MULTI_PARTNER_REAL_DATA = REAL_DATA_DIR / "multi_partner_real_data.json"
DATA_VALIDATION_REPORT = REAL_DATA_DIR / "data_validation_report.md"
DATA_VALIDATION_JSON = REAL_DATA_DIR / "data_validation.json"

# Buffer API 配置
BUFFER_API_URL = "https://api.buffer.com"
BUFFER_ORGS = {
    "A": {"id": "6a17ddf5e051bed5895272f0", "platforms": ["facebook", "instagram", "twitter"]},
    "B": {"id": "6a20329943b37a7289e25b6d", "platforms": ["pinterest"]},
}

# GA4 API 配置
GA4_API_BASE = "https://analyticsdata.googleapis.com/v1beta"

# Partnerize API 配置
PARTNERIZE_API_BASE = "https://api.partnerize.com"

# Impact.com API 配置 (NordVPN 等)
IMPACT_API_BASE = "https://api.impact.com"


# ============================================================
# 工具函数
# ============================================================

def _is_sample_data(data: Any) -> bool:
    """检测是否是Sample/模拟/空数据"""
    if data is None:
        return True
    if isinstance(data, dict):
        sample_markers = ["sample", "mock", "demo", "test", "example", "placeholder"]
        for key, value in data.items():
            key_lower = str(key).lower()
            if any(marker in key_lower for marker in sample_markers):
                return True
            if isinstance(value, str):
                if any(marker in value.lower() for marker in sample_markers):
                    return True
                if value.strip() == "":
                    return True
    if isinstance(data, list):
        if len(data) == 0:
            return True
        for item in data[:3]:
            if _is_sample_data(item):
                return True
    return False


def _check_freshness(data_date: Optional[str], max_age_days: int = 2) -> Dict:
    """检查数据新鲜度"""
    today = datetime.now().date()
    if not data_date:
        return {"fresh": False, "reason": "No date field", "age_days": 999}
    try:
        for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"]:
            try:
                parsed = datetime.strptime(data_date[:10], fmt).date()
                age = (today - parsed).days
                return {
                    "fresh": age <= max_age_days,
                    "reason": f"Data is {age} days old" if age > max_age_days else "Fresh",
                    "age_days": age,
                    "data_date": str(parsed),
                }
            except ValueError:
                continue
        return {"fresh": False, "reason": f"Cannot parse date: {data_date}", "age_days": 999}
    except Exception:
        return {"fresh": False, "reason": "Date parsing error", "age_days": 999}


def _save_json(path: Path, data: Dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ============================================================
# GA4 数据拉取（REST API 直连）
# ============================================================

def _get_ga4_access_token() -> Optional[str]:
    """从 service account 获取 OAuth2 access token"""
    try:
        from gsc_utils import load_service_account_info
        from google.oauth2 import service_account
    except ImportError:
        return None

    # GA4 可以复用 GSC 的 service account（同一个 Google Cloud 项目）
    info = load_service_account_info(env_name="GA4_SERVICE_ACCOUNT_JSON")
    if not info:
        info = load_service_account_info(env_name="GSC_SERVICE_ACCOUNT_JSON")
    if not info:
        return None

    try:
        creds = service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/analytics.readonly"]
        )
        from google.auth.transport.requests import Request
        creds.refresh(Request())
        return creds.token
    except Exception as e:
        print(f"   GA4 token refresh failed: {e}")
        return None


def pull_ga4_data(days: int = 28, save: bool = True) -> Dict:
    """直接调用 GA4 Data API 拉取真实流量数据"""
    print("\n" + "=" * 60)
    print("  拉取GA4真实数据（API直连）")
    print("=" * 60)

    property_id = os.environ.get("GA4_PROPERTY_ID", "").strip()
    result = {
        "source": "ga4_api",
        "pull_time": datetime.now().isoformat(),
        "data_date": None,
        "is_real_data": False,
        "is_fresh": False,
        "metrics": {},
        "daily": [],
        "top_pages": [],
        "traffic_sources": [],
        "raw_source": "GA4 Data API v1beta",
        "status": "UNKNOWN",
        "error": None,
    }

    if not property_id:
        result["status"] = "NOT_CONFIGURED"
        result["error"] = "GA4_PROPERTY_ID not set in .env or GitHub Secrets"
        print("  GA4_PROPERTY_ID 未配置，跳过 API 调用")
        if save: _save_json(GA4_REAL_DATA, result)
        return result

    token = _get_ga4_access_token()
    if not token:
        result["status"] = "AUTH_FAILED"
        result["error"] = "Failed to obtain GA4 access token from service account"
        print("  GA4 access token 获取失败")
        if save: _save_json(GA4_REAL_DATA, result)
        return result

    end_date = date.today() - timedelta(days=1)  # GA4 数据延迟1天
    start_date = end_date - timedelta(days=days - 1)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # 1. 汇总指标
    try:
        url = f"{GA4_API_BASE}/properties/{property_id}:runReport"
        body = {
            "dateRanges": [{"startDate": start_date.isoformat(), "endDate": end_date.isoformat()}],
            "metrics": [
                {"name": "activeUsers"},
                {"name": "sessions"},
                {"name": "screenPageViews"},
                {"name": "engagedSessions"},
                {"name": "bounceRate"},
                {"name": "averageSessionDuration"},
                {"name": "engagementRate"},
                {"name": "newUsers"},
            ],
        }
        resp = requests.post(url, headers=headers, json=body, timeout=30)
        if resp.status_code != 200:
            result["status"] = "API_ERROR"
            result["error"] = f"HTTP {resp.status_code}: {resp.text[:500]}"
            print(f"  GA4 API 错误: HTTP {resp.status_code}")
            if save: _save_json(GA4_REAL_DATA, result)
            return result

        data = resp.json()
        rows = data.get("rows", [])
        if rows:
            metrics = rows[0].get("metricValues", [])
            metric_names = [m["name"] for m in body["metrics"]]
            for i, name in enumerate(metric_names):
                if i < len(metrics):
                    val = metrics[i].get("value", "0")
                    try:
                        result["metrics"][name] = float(val) if "." in val else int(val)
                    except (ValueError, TypeError):
                        result["metrics"][name] = val

            result["is_real_data"] = True
            result["data_date"] = end_date.isoformat()
            freshness = _check_freshness(result["data_date"])
            result["is_fresh"] = freshness["fresh"]
            result["freshness_info"] = freshness
            result["status"] = "OK"
            print(f"  GA4 API 成功: {result['metrics'].get('sessions', 0)} sessions, {result['metrics'].get('activeUsers', 0)} users")
        else:
            result["status"] = "NO_DATA"
            result["error"] = "GA4 API returned no rows (property may have no traffic or wrong ID)"
            print("  GA4 API 返回空数据")

    except Exception as e:
        result["status"] = "EXCEPTION"
        result["error"] = str(e)
        print(f"  GA4 API 异常: {e}")

    # 2. 每日趋势（近7天）
    if result["is_real_data"]:
        try:
            daily_end = date.today()  # 含今日实时数据
            week_start = daily_end - timedelta(days=6)
            body_daily = {
                "dateRanges": [{"startDate": week_start.isoformat(), "endDate": daily_end.isoformat()}],
                "dimensions": [{"name": "date"}],
                "metrics": [{"name": "sessions"}, {"name": "activeUsers"}, {"name": "screenPageViews"}],
            }
            resp = requests.post(url, headers=headers, json=body_daily, timeout=30)
            if resp.status_code == 200:
                for row in resp.json().get("rows", []):
                    dims = row.get("dimensionValues", [])
                    vals = row.get("metricValues", [])
                    raw_date = dims[0].get("value", "") if dims else ""
                    # GA4 returns YYYYMMDD, convert to YYYY-MM-DD
                    if len(raw_date) == 8 and raw_date.isdigit():
                        fmt_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
                    else:
                        fmt_date = raw_date
                    result["daily"].append({
                        "date": fmt_date,
                        "sessions": int(vals[0].get("value", 0)) if len(vals) > 0 else 0,
                        "activeUsers": int(vals[1].get("value", 0)) if len(vals) > 1 else 0,
                        "pageviews": int(vals[2].get("value", 0)) if len(vals) > 2 else 0,
                    })
                result["daily"].sort(key=lambda x: x["date"])
                print(f"  GA4 daily trend: {len(result['daily'])} 天")
            else:
                print(f"  GA4 daily trend API 返回 {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            print(f"  GA4 daily trend 跳过: {e}")

        # 3. Top Pages
        try:
            body_pages = {
                "dateRanges": [{"startDate": start_date.isoformat(), "endDate": end_date.isoformat()}],
                "dimensions": [{"name": "pagePath"}, {"name": "pageTitle"}],
                "metrics": [{"name": "screenPageViews"}, {"name": "sessions"}, {"name": "activeUsers"}],
                "orderBys": [{"field": {"fieldName": "screenPageViews"}, "sortOrder": "DESCENDING"}],
                "limit": 15,
            }
            resp = requests.post(url, headers=headers, json=body_pages, timeout=30)
            if resp.status_code == 200:
                for row in resp.json().get("rows", []):
                    dims = row.get("dimensionValues", [])
                    vals = row.get("metricValues", [])
                    result["top_pages"].append({
                        "path": dims[0].get("value", "") if len(dims) > 0 else "",
                        "title": dims[1].get("value", "") if len(dims) > 1 else "",
                        "pageviews": int(vals[0].get("value", 0)) if len(vals) > 0 else 0,
                        "sessions": int(vals[1].get("value", 0)) if len(vals) > 1 else 0,
                    })
        except Exception as e:
            print(f"  GA4 top pages 跳过: {e}")

        # 4. Traffic Sources
        try:
            body_src = {
                "dateRanges": [{"startDate": start_date.isoformat(), "endDate": end_date.isoformat()}],
                "dimensions": [{"name": "sessionDefaultChannelGroup"}],
                "metrics": [{"name": "sessions"}, {"name": "activeUsers"}, {"name": "engagementRate"}],
                "orderBys": [{"field": {"fieldName": "sessions"}, "sortOrder": "DESCENDING"}],
            }
            resp = requests.post(url, headers=headers, json=body_src, timeout=30)
            if resp.status_code == 200:
                for row in resp.json().get("rows", []):
                    dims = row.get("dimensionValues", [])
                    vals = row.get("metricValues", [])
                    result["traffic_sources"].append({
                        "channel": dims[0].get("value", "") if dims else "",
                        "sessions": int(vals[0].get("value", 0)) if len(vals) > 0 else 0,
                        "activeUsers": int(vals[1].get("value", 0)) if len(vals) > 1 else 0,
                    })
        except Exception as e:
            print(f"  GA4 traffic sources 跳过: {e}")

    if save: _save_json(GA4_REAL_DATA, result)
    return result


# ============================================================
# GSC 数据拉取（Search Console API 直连）
# ============================================================

def pull_gsc_data(days: int = 28, save: bool = True) -> Dict:
    """直接调用 Search Console REST API 拉取真实搜索数据。

    使用 requests 直接调用 REST API，绕过 googleapiclient 的超时问题。
    """
    print("\n" + "=" * 60)
    print("  拉取GSC真实数据（REST API直连）")
    print("=" * 60)

    result = {
        "source": "gsc_api",
        "pull_time": datetime.now().isoformat(),
        "data_date": None,
        "is_real_data": False,
        "is_fresh": False,
        "metrics": {},
        "daily": [],
        "top_queries": [],
        "top_pages": [],
        "raw_source": "Google Search Console REST API v3",
        "status": "UNKNOWN",
        "error": None,
    }

    try:
        from gsc_utils import load_service_account_info, build_credentials, get_site_url, normalize_site_url
        from urllib.parse import quote
    except ImportError as e:
        result["status"] = "IMPORT_ERROR"
        result["error"] = str(e)
        print(f"  gsc_utils 导入失败: {e}")
        if save: _save_json(GSC_REAL_DATA, result)
        return result

    info = load_service_account_info()
    if not info:
        result["status"] = "NOT_CONFIGURED"
        result["error"] = "GSC_SERVICE_ACCOUNT_JSON not configured"
        print("  GSC service account 未配置")
        if save: _save_json(GSC_REAL_DATA, result)
        return result

    creds = build_credentials(info)
    if not creds or not creds.token:
        result["status"] = "AUTH_FAILED"
        result["error"] = "Failed to build/refresh GSC credentials"
        print("  GSC credentials 构建或refresh失败")
        if save: _save_json(GSC_REAL_DATA, result)
        return result

    site_url = normalize_site_url(get_site_url())
    site_encoded = quote(site_url, safe="")

    # Verify site access via REST API (sites.list)
    try:
        verify_resp = requests.get(
            "https://searchconsole.googleapis.com/webmasters/v3/sites",
            headers={"Authorization": f"Bearer {creds.token}"},
            timeout=30,
        )
        if verify_resp.status_code != 200:
            result["status"] = "SITE_ACCESS_ERROR"
            result["error"] = f"sites.list HTTP {verify_resp.status_code}: {verify_resp.text[:300]}"
            print(f"  GSC sites.list 错误: HTTP {verify_resp.status_code}")
            if save: _save_json(GSC_REAL_DATA, result)
            return result

        sites_data = verify_resp.json()
        accessible_sites = sites_data.get("siteEntry", [])
        site_urls = {s.get("siteUrl", "").rstrip("/") for s in accessible_sites}
        has_access = site_url.rstrip("/") in site_urls or any(
            s.get("siteUrl", "").startswith("sc-domain:") and site_url.rstrip("/").endswith(s.get("siteUrl", "").split(":", 1)[-1])
            for s in accessible_sites
        )

        if not has_access:
            result["status"] = "SITE_ACCESS_DENIED"
            accessible_list = ", ".join(s.get("siteUrl", "") for s in accessible_sites)
            result["error"] = (
                f"Service account does not have access to '{site_url}'. "
                f"Accessible sites: {accessible_list}. "
                f"Add the service account email as a user in Google Search Console."
            )
            print(f"  GSC 站点访问被拒绝: {site_url}")
            print(f"  可访问站点: {accessible_list}")
            if save: _save_json(GSC_REAL_DATA, result)
            return result

        print(f"  GSC 站点访问确认: {site_url} (共 {len(accessible_sites)} 个可访问站点)")
    except Exception as e:
        result["status"] = "VERIFY_ERROR"
        result["error"] = str(e)
        print(f"  GSC 站点验证异常: {e}")
        if save: _save_json(GSC_REAL_DATA, result)
        return result

    # GSC 数据延迟约3天
    end_date = date.today() - timedelta(days=3)
    start_date = end_date - timedelta(days=days - 1)

    api_url = f"https://searchconsole.googleapis.com/webmasters/v3/sites/{site_encoded}/searchAnalytics/query"
    headers = {
        "Authorization": f"Bearer {creds.token}",
        "Content-Type": "application/json",
    }

    # 1. 汇总指标（按 query 维度，rowLimit=25000）
    try:
        request_body = {
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
            "searchType": "web",
            "dimensions": ["query"],
            "rowLimit": 25000,
        }
        resp = requests.post(api_url, headers=headers, json=request_body, timeout=60)
        if resp.status_code != 200:
            result["status"] = "API_ERROR"
            result["error"] = f"HTTP {resp.status_code}: {resp.text[:500]}"
            print(f"  GSC API 错误: HTTP {resp.status_code}")
            if save: _save_json(GSC_REAL_DATA, result)
            return result

        data = resp.json()
        all_rows = data.get("rows", [])

        total_impressions = sum(r.get("impressions", 0) for r in all_rows)
        total_clicks = sum(r.get("clicks", 0) for r in all_rows)
        avg_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        avg_position = (
            sum(r.get("position", 0) * r.get("impressions", 0) for r in all_rows) / total_impressions
        ) if total_impressions > 0 else 0

        result["metrics"] = {
            "impressions": round(total_impressions, 0),
            "clicks": round(total_clicks, 0),
            "ctr": round(avg_ctr, 2),
            "average_position": round(avg_position, 1),
        }
        result["data_date"] = end_date.isoformat()
        result["is_real_data"] = True
        freshness = _check_freshness(result["data_date"], max_age_days=5)
        result["is_fresh"] = freshness["fresh"]
        result["freshness_info"] = freshness
        result["status"] = "OK"
        print(f"  GSC API 成功: {total_impressions:.0f} impressions, {total_clicks:.0f} clicks, avg pos {avg_position:.1f}")

        # Top Queries
        for row in all_rows[:20]:
            result["top_queries"].append({
                "query": row.get("keys", [""])[0] if row.get("keys") else "",
                "impressions": row.get("impressions", 0),
                "clicks": row.get("clicks", 0),
                "ctr": round(row.get("ctr", 0), 2),
                "position": round(row.get("position", 0), 1),
            })

    except Exception as e:
        result["status"] = "API_EXCEPTION"
        result["error"] = str(e)
        print(f"  GSC API 异常: {e}")
        if save: _save_json(GSC_REAL_DATA, result)
        return result

    # 2. Top Pages (按 page 维度)
    try:
        page_body = {
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
            "searchType": "web",
            "dimensions": ["page"],
            "rowLimit": 20,
        }
        resp = requests.post(api_url, headers=headers, json=page_body, timeout=60)
        if resp.status_code == 200:
            for row in resp.json().get("rows", []):
                result["top_pages"].append({
                    "page": row.get("keys", [""])[0] if row.get("keys") else "",
                    "impressions": row.get("impressions", 0),
                    "clicks": row.get("clicks", 0),
                    "ctr": round(row.get("ctr", 0), 2),
                    "position": round(row.get("position", 0), 1),
                })
    except Exception as e:
        print(f"  GSC top pages 跳过: {e}")

    # 2b. 每日趋势（按 date 维度，最近7天）
    try:
        daily_end = end_date
        daily_start = daily_end - timedelta(days=6)
        daily_body = {
            "startDate": daily_start.isoformat(),
            "endDate": daily_end.isoformat(),
            "searchType": "web",
            "dimensions": ["date"],
            "rowLimit": 30,
        }
        resp = requests.post(api_url, headers=headers, json=daily_body, timeout=60)
        if resp.status_code == 200:
            for row in resp.json().get("rows", []):
                keys = row.get("keys", [])
                result["daily"].append({
                    "date": keys[0] if keys else "",
                    "impressions": row.get("impressions", 0),
                    "clicks": row.get("clicks", 0),
                    "ctr": round(row.get("ctr", 0), 2),
                    "position": round(row.get("position", 0), 1),
                })
            result["daily"].sort(key=lambda x: x["date"])
            print(f"  GSC daily trend: {len(result['daily'])} 天")
    except Exception as e:
        print(f"  GSC daily trend 跳过: {e}")

    # 3. Sitemap 状态
    try:
        sitemap_url = f"https://searchconsole.googleapis.com/webmasters/v3/sites/{site_encoded}/sitemaps"
        resp = requests.get(sitemap_url, headers={"Authorization": f"Bearer {creds.token}"}, timeout=30)
        if resp.status_code == 200:
            sitemaps = resp.json().get("sitemap", [])
            result["metrics"]["sitemap_count"] = len(sitemaps)
            if sitemaps:
                result["metrics"]["sitemap_last_submitted"] = sitemaps[0].get("lastSubmitted", "")
    except Exception:
        pass

    if save: _save_json(GSC_REAL_DATA, result)
    return result


def _buffer_graphql_query(token: str, query: str, variables: Optional[Dict] = None) -> Dict:
    """执行 Buffer GraphQL 查询"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    resp = requests.post(BUFFER_API_URL, headers=headers, json=payload, timeout=30)
    if resp.status_code != 200:
        return {"error": f"HTTP {resp.status_code}: {resp.text[:300]}"}
    return resp.json()


def pull_social_data(days: int = 28) -> Dict:
    """直接调用 Buffer GraphQL API 拉取已发布帖子 metrics"""
    print("\n" + "=" * 60)
    print("  拉取社媒真实数据（Buffer API直连）")
    print("=" * 60)

    result = {
        "source": "buffer_api",
        "pull_time": datetime.now().isoformat(),
        "data_date": None,
        "is_real_data": False,
        "is_fresh": False,
        "metrics": {
            "total_posts": 0,
            "total_impressions": 0,
            "total_clicks": 0,
            "total_likes": 0,
            "total_comments": 0,
            "total_shares": 0,
        },
        "posts": [],
        "by_platform": {},
        "raw_source": "Buffer GraphQL API",
        "status": "UNKNOWN",
        "error": None,
    }

    token_a = os.environ.get("BUFFER_API_TOKEN_A", "").strip().lstrip("\ufeff")
    token_b = os.environ.get("BUFFER_API_TOKEN_B", "").strip().lstrip("\ufeff")

    if not token_a and not token_b:
        result["status"] = "NOT_CONFIGURED"
        result["error"] = "BUFFER_API_TOKEN_A/B not configured"
        print("  Buffer API tokens 未配置")
        _save_json(SOCIAL_REAL_DATA, result)
        return result

    # Buffer GraphQL: 查询已发布帖子
    # Buffer API Post.metrics 是 PostMetric 数组: [{name, value, type, unit, description}]
    posts_query = """
    query GetPublishedPosts($input: PostsInput!) {
      posts(input: $input) {
        edges {
          node {
            id
            text
            dueAt
            createdAt
            sentAt
            status
            channelService
            channel { id name service }
            metrics {
              name
              value
              type
              unit
            }
          }
        }
      }
    }
    """

    all_posts = []
    api_errors = []

    for account_key, token in [("A", token_a), ("B", token_b)]:
        if not token:
            continue
        org_config = BUFFER_ORGS.get(account_key, {})
        org_id = org_config.get("id", "")
        if not org_id:
            continue

        try:
            variables = {
                "input": {
                    "organizationId": org_id,
                    "sort": [{"field": "dueAt", "direction": "desc"}],
                    "filter": {"status": ["sent"]},
                }
            }
            data = _buffer_graphql_query(token, posts_query, variables)

            if "error" in data:
                api_errors.append(f"Account {account_key}: {data['error']}")
                print(f"  Buffer Account {account_key} 错误: {data['error'][:100]}")
                continue

            if data.get("errors"):
                api_errors.append(f"Account {account_key}: {data['errors'][0].get('message', 'unknown')}")
                print(f"  Buffer Account {account_key} GraphQL 错误: {data['errors'][0].get('message', '')[:100]}")
                continue

            edges = data.get("data", {}).get("posts", {}).get("edges", [])
            print(f"  Buffer Account {account_key}: 找到 {len(edges)} 条已发布帖子")

            for edge in edges:
                node = edge.get("node", {})
                # Buffer metrics is an array of {name, value, type, unit}
                metrics_array = node.get("metrics") or []
                stats = {}
                for m in metrics_array:
                    mname = (m.get("name") or "").lower()
                    mval = m.get("value", 0) or 0
                    stats[mname] = mval
                channel = node.get("channel") or {}
                post = {
                    "id": node.get("id", ""),
                    "text": (node.get("text", "") or "")[:200],
                    "platform": node.get("channelService") or channel.get("service", "unknown"),
                    "channel_name": channel.get("name", ""),
                    "published_at": node.get("sentAt") or node.get("dueAt") or node.get("createdAt", ""),
                    "status": node.get("status", ""),
                    "likes": int(stats.get("likes", stats.get("like", 0)) or 0),
                    "comments": int(stats.get("comments", stats.get("comment", 0)) or 0),
                    "shares": int(stats.get("shares", stats.get("share", stats.get("retweets", 0))) or 0),
                    "clicks": int(stats.get("clicks", stats.get("click", 0)) or 0),
                    "impressions": int(stats.get("impressions", stats.get("impression", stats.get("reach", stats.get("views", 0)))) or 0),
                    "engagement_rate": float(stats.get("engagement_rate", stats.get("engagementrate", 0)) or 0),
                }
                all_posts.append(post)

        except Exception as e:
            api_errors.append(f"Account {account_key}: {str(e)}")
            print(f"  Buffer Account {account_key} 异常: {e}")

    if all_posts:
        # 过滤时间范围
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        recent_posts = [p for p in all_posts if p.get("published_at", "") >= cutoff]
        if not recent_posts:
            recent_posts = all_posts[:20]  # 如果时间过滤后为空，取最近20条

        result["posts"] = recent_posts[:30]
        result["metrics"]["total_posts"] = len(recent_posts)
        result["metrics"]["total_impressions"] = sum(p["impressions"] for p in recent_posts)
        result["metrics"]["total_clicks"] = sum(p["clicks"] for p in recent_posts)
        result["metrics"]["total_likes"] = sum(p["likes"] for p in recent_posts)
        result["metrics"]["total_comments"] = sum(p["comments"] for p in recent_posts)
        result["metrics"]["total_shares"] = sum(p["shares"] for p in recent_posts)

        # 按平台分组
        by_platform = {}
        for p in recent_posts:
            plat = p["platform"]
            if plat not in by_platform:
                by_platform[plat] = {"posts": 0, "impressions": 0, "clicks": 0, "likes": 0}
            by_platform[plat]["posts"] += 1
            by_platform[plat]["impressions"] += p["impressions"]
            by_platform[plat]["clicks"] += p["clicks"]
            by_platform[plat]["likes"] += p["likes"]
        result["by_platform"] = by_platform

        result["is_real_data"] = True
        result["data_date"] = datetime.now().strftime("%Y-%m-%d")
        freshness = _check_freshness(result["data_date"])
        result["is_fresh"] = freshness["fresh"]
        result["freshness_info"] = freshness
        result["status"] = "OK"
        print(f"  Buffer API 成功: {len(recent_posts)} 条帖子, {result['metrics']['total_impressions']} impressions, {result['metrics']['total_clicks']} clicks")
    else:
        result["status"] = "NO_DATA" if not api_errors else "PARTIAL_ERROR"
        result["error"] = "; ".join(api_errors) if api_errors else "No published posts found"
        print(f"  Buffer API: 未找到帖子数据 ({result['status']})")

    _save_json(SOCIAL_REAL_DATA, result)
    return result


# ============================================================
# Content 数据拉取（本地扫描 - 保持不变）
# ============================================================

def pull_content_data() -> Dict:
    """扫描本地文章，获取真实内容数据"""
    print("\n" + "=" * 60)
    print("  拉取内容真实数据（本地扫描）")
    print("=" * 60)

    content_dir = PROJECT_ROOT / "content" / "posts"
    articles = sorted(content_dir.glob("*.md")) if content_dir.exists() else []

    result = {
        "source": "content_analytics",
        "pull_time": datetime.now().isoformat(),
        "data_date": datetime.now().strftime("%Y-%m-%d"),
        "is_real_data": True,
        "is_fresh": True,
        "metrics": {
            "total_articles": len(articles),
            "articles_this_week": 0,
            "avg_word_count": 0,
            "articles_with_affiliate_links": 0,
            "articles_with_internal_links": 0,
        },
        "top_articles": [],
        "raw_source": "local_content_scan",
    }

    word_counts = []
    for article in articles:
        try:
            text = article.read_text(encoding="utf-8", errors="replace")
            wc = len(text.split())
            word_counts.append(wc)
            has_affiliate = any(x in text for x in ["booking.com", "trip.com", "travelpayouts", "agoda", "klook", "airalo", "safetywing"])
            has_internal = "](/posts/" in text or "](/cities/" in text or "](/guides/" in text

            if has_affiliate:
                result["metrics"]["articles_with_affiliate_links"] += 1
            if has_internal:
                result["metrics"]["articles_with_internal_links"] += 1

            if len(result["top_articles"]) < 15:
                result["top_articles"].append({
                    "slug": article.stem,
                    "word_count": wc,
                    "has_affiliate_links": has_affiliate,
                    "has_internal_links": has_internal,
                })
        except Exception:
            pass

    if word_counts:
        result["metrics"]["avg_word_count"] = sum(word_counts) // len(word_counts)

    print(f"  文章总数: {len(articles)}")
    print(f"  平均字数: {result['metrics']['avg_word_count']}")
    print(f"  含联盟链接: {result['metrics']['articles_with_affiliate_links']}")
    print(f"  含内链: {result['metrics']['articles_with_internal_links']}")

    _save_json(CONTENT_REAL_DATA, result)
    return result


# ============================================================
# Partnerize 数据拉取（API直连 v3 Brand API）
# ============================================================

def pull_partnerize_data() -> Dict:
    """从 Partnerize API 拉取联盟收入数据

    认证方式: Basic Auth (username=APP_KEY, password=API_KEY)
    API 文档: https://api-docs.partnerize.com/brand
    """
    print("\n" + "=" * 60)
    print("  Partnerize 数据拉取（v3 Brand API）")
    print("=" * 60)

    app_key = os.environ.get("PARTNERIZE_APP_KEY", "")
    api_key = os.environ.get("PARTNERIZE_API_KEY", "")
    user_id = os.environ.get("PARTNERIZE_USER_ID", "")

    if not app_key or not api_key:
        print("  ⚠️ PARTNERIZE_APP_KEY 或 PARTNERIZE_API_KEY 未配置")
        result = {"status": "NO_CREDENTIALS", "is_real_data": False, "campaigns": [], "conversions": [],
                  "message": "Partnerize API credentials not configured", "fetched_at": datetime.now().isoformat()}
        _save_json(PARTNERIZE_REAL_DATA, result)
        return result

    import base64
    auth = base64.b64encode(f"{app_key}:{api_key}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}", "Accept": "application/json"}

    # Step 1: 获取 campaigns 列表
    print("  📥 拉取 campaigns 列表...")
    campaigns = []
    try:
        r = requests.get(f"{PARTNERIZE_API_BASE}/v3/brand/campaigns", headers=headers, timeout=30)
        if r.status_code == 200:
            data = r.json()
            campaigns = data.get("data", [])
            print(f"  ✅ 获取到 {len(campaigns)} 个 campaign")
        elif r.status_code in [401, 403]:
            print(f"  ❌ 认证失败: {r.status_code}")
            result = {"status": "AUTH_FAILED", "is_real_data": False, "campaigns": [], "conversions": [],
                      "message": f"Partnerize auth failed: {r.status_code}", "fetched_at": datetime.now().isoformat()}
            _save_json(PARTNERIZE_REAL_DATA, result)
            return result
        else:
            print(f"  ⚠️ Campaigns API 返回 {r.status_code}: {r.text[:150]}")
    except Exception as e:
        print(f"  ❌ Campaigns API 调用失败: {e}")

    # Step 2: 如果有 campaign，拉取每个 campaign 的 conversions
    conversions = []
    if campaigns:
        print(f"  📥 拉取 {len(campaigns)} 个 campaign 的 conversions...")
        for camp in campaigns:
            camp_id = camp.get("id", "")
            camp_name = camp.get("name", "")
            if not camp_id:
                continue
            try:
                url = f"{PARTNERIZE_API_BASE}/v3/brand/campaigns/{camp_id}/conversions"
                r = requests.get(url, headers=headers, timeout=30)
                if r.status_code == 200:
                    conv_data = r.json()
                    camp_conversions = conv_data.get("data", [])
                    for c in camp_conversions:
                        c["_campaign_id"] = camp_id
                        c["_campaign_name"] = camp_name
                        conversions.append(c)
                    print(f"    ✅ {camp_name}: {len(camp_conversions)} conversions")
                else:
                    print(f"    ⚠️ {camp_name}: {r.status_code}")
            except Exception as e:
                print(f"    ❌ {camp_name}: {e}")
    else:
        print("  ℹ️ 账户下无 campaign，跳过 conversions 拉取")
        print("  💡 请登录 Partnerize 后台加入相关 campaign 后即可获取数据")

    # 汇总统计
    total_conversions = len(conversions)
    total_revenue = sum(float(c.get("sale_amount", 0) or 0) for c in conversions)
    total_commission = sum(float(c.get("commission_amount", 0) or 0) for c in conversions)

    print(f"\n  📊 Partnerize 汇总:")
    print(f"    Campaigns: {len(campaigns)}")
    print(f"    Conversions: {total_conversions}")
    print(f"    Revenue: ${total_revenue:.2f}")
    print(f"    Commission: ${total_commission:.2f}")

    result = {
        "status": "SUCCESS" if campaigns else "NO_CAMPAIGNS",
        "is_real_data": True,
        "user_id": user_id,
        "campaigns": campaigns,
        "conversions": conversions,
        "summary": {
            "total_campaigns": len(campaigns),
            "total_conversions": total_conversions,
            "total_revenue": round(total_revenue, 2),
            "total_commission": round(total_commission, 2),
        },
        "message": "API connected. No campaigns configured yet." if not campaigns else "Data fetched successfully.",
        "fetched_at": datetime.now().isoformat(),
    }

    _save_json(PARTNERIZE_REAL_DATA, result)
    print(f"  💾 已保存: {PARTNERIZE_REAL_DATA}")
    return result


# ============================================================
# Impact.com 数据拉取（NordVPN 等联盟）
# ============================================================

def pull_impact_data() -> Dict:
    """从 Impact.com API 拉取联盟数据（NordVPN 等）

    认证方式: Basic Auth (username=Account_SID, password=Auth_Token)
    API 文档: https://developer.impact.com/

    前置条件: 在 .env 中配置 IMPACT_ACCOUNT_SID 和 IMPACT_AUTH_TOKEN
    """
    print("\n" + "=" * 60)
    print("  Impact.com 数据拉取（NordVPN 等）")
    print("=" * 60)

    account_sid = os.environ.get("IMPACT_ACCOUNT_SID", "")
    auth_token = os.environ.get("IMPACT_AUTH_TOKEN", "")

    if not account_sid or not auth_token:
        print("  ⚠️ IMPACT_ACCOUNT_SID 或 IMPACT_AUTH_TOKEN 未配置")
        print("  💡 请登录 https://app.impact.com/ → Settings → API Access 获取凭证")
        result = {"status": "NO_CREDENTIALS", "is_real_data": False, "actions": [], "clicks": [],
                  "message": "Impact API credentials not configured", "fetched_at": datetime.now().isoformat()}
        _save_json(IMPACT_REAL_DATA, result)
        return result

    import base64
    auth = base64.b64encode(f"{account_sid}:{auth_token}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}", "Accept": "application/json"}

    # Step 1: 获取转化数据 (Actions)
    print("  📥 拉取 Impact Actions (转化)...")
    actions = []
    try:
        url = f"{IMPACT_API_BASE}/Advertisers/{account_sid}/Actions"
        params = {"PageSize": 100, "State": "APPROVED,PENDING,REVERSED"}
        r = requests.get(url, headers=headers, params=params, timeout=30)
        if r.status_code == 200:
            data = r.json()
            actions = data.get("Actions", data.get("data", []))
            print(f"  ✅ 获取到 {len(actions)} 条转化记录")
        elif r.status_code in [401, 403]:
            print(f"  ❌ 认证失败: {r.status_code}")
            result = {"status": "AUTH_FAILED", "is_real_data": False, "actions": [], "clicks": [],
                      "message": f"Impact auth failed: {r.status_code}", "fetched_at": datetime.now().isoformat()}
            _save_json(IMPACT_REAL_DATA, result)
            return result
        else:
            print(f"  ⚠️ Actions API 返回 {r.status_code}: {r.text[:150]}")
    except Exception as e:
        print(f"  ❌ Actions API 调用失败: {e}")

    # Step 2: 获取点击数据
    print("  📥 拉取 Impact Clicks...")
    clicks = []
    try:
        url = f"{IMPACT_API_BASE}/Advertisers/{account_sid}/Clicks"
        r = requests.get(url, headers=headers, params={"PageSize": 100}, timeout=30)
        if r.status_code == 200:
            data = r.json()
            clicks = data.get("Clicks", data.get("data", []))
            print(f"  ✅ 获取到 {len(clicks)} 条点击记录")
        else:
            print(f"  ⚠️ Clicks API 返回 {r.status_code}")
    except Exception as e:
        print(f"  ❌ Clicks API 调用失败: {e}")

    # 汇总统计
    total_actions = len(actions)
    total_clicks = len(clicks)
    total_payout = sum(float(a.get("Payout", a.get("payout", 0)) or 0) for a in actions)
    total_sale_amount = sum(float(a.get("SaleAmount", a.get("sale_amount", 0)) or 0) for a in actions)

    print(f"\n  📊 Impact 汇总:")
    print(f"    Clicks: {total_clicks}")
    print(f"    Actions (转化): {total_actions}")
    print(f"    Sale Amount: ${total_sale_amount:.2f}")
    print(f"    Payout (佣金): ${total_payout:.2f}")

    result = {
        "status": "SUCCESS" if actions or clicks else "NO_DATA",
        "is_real_data": True,
        "account_sid": account_sid,
        "actions": actions,
        "clicks": clicks,
        "summary": {
            "total_clicks": total_clicks,
            "total_actions": total_actions,
            "total_sale_amount": round(total_sale_amount, 2),
            "total_payout": round(total_payout, 2),
        },
        "fetched_at": datetime.now().isoformat(),
    }

    _save_json(IMPACT_REAL_DATA, result)
    print(f"  💾 已保存: {IMPACT_REAL_DATA}")
    return result


# ============================================================
# 多 Partner 统一数据拉取框架（Klook/Booking/Airalo 等）
# ============================================================

def pull_multi_partner_data() -> Dict:
    """统一拉取多个联盟 Partner 的数据

    支持的 Partner（需在 .env 中配置对应凭证）:
    - klook: KLOOK_API_KEY + KLOOK_API_SECRET
    - airalo: AIRALO_CLIENT_ID + AIRALO_CLIENT_SECRET
    - safetywing: SAFETYWING_API_KEY
    - trip: TRIP_APP_ID + TRIP_APP_SECRET
    - cj: CJ_API_TOKEN (World Nomads 等)

    无凭证的 Partner 自动跳过并标记 NO_CREDENTIALS。
    """
    print("\n" + "=" * 60)
    print("  多 Partner 统一数据拉取")
    print("=" * 60)

    partners_config = {
        "klook": {
            "env_keys": ["KLOOK_API_KEY", "KLOOK_API_SECRET"],
            "api_base": "https://affiliate.klook.com/api",
            "endpoint": "/conversions",
        },
        "airalo": {
            "env_keys": ["AIRALO_CLIENT_ID", "AIRALO_CLIENT_SECRET"],
            "api_base": "https://api.airalo.com/v2",
            "endpoint": "/orders",
        },
        "safetywing": {
            "env_keys": ["SAFETYWING_API_KEY"],
            "api_base": "https://api.safetywing.com/v1",
            "endpoint": "/affiliate/conversions",
        },
        "trip": {
            "env_keys": ["TRIP_APP_ID", "TRIP_APP_SECRET"],
            "api_base": "https://affiliate.trip.com/api",
            "endpoint": "/conversions",
        },
        "cj": {
            "env_keys": ["CJ_API_TOKEN"],
            "api_base": "https://advertiser.api.cj.com/v3",
            "endpoint": "/events",
        },
    }

    results = {}
    for partner_name, config in partners_config.items():
        print(f"\n  --- {partner_name.upper()} ---")

        # 检查凭证
        credentials = {k: os.environ.get(k, "") for k in config["env_keys"]}
        missing = [k for k, v in credentials.items() if not v]

        if missing:
            print(f"    ⚠️ 缺少凭证: {', '.join(missing)}")
            print(f"    💡 请参考 docs/AFFILIATE_API_INTEGRATION_GUIDE.md 申请凭证")
            results[partner_name] = {
                "status": "NO_CREDENTIALS",
                "is_real_data": False,
                "missing_keys": missing,
                "message": f"Missing: {', '.join(missing)}",
                "fetched_at": datetime.now().isoformat(),
            }
            continue

        # 尝试拉取数据（通用框架，具体 API 格式需根据各 Partner 文档调整）
        try:
            headers = {"Accept": "application/json"}
            if partner_name == "cj":
                headers["Authorization"] = f"Bearer {credentials['CJ_API_TOKEN']}"
            elif partner_name == "klook":
                headers["X-API-Key"] = credentials["KLOOK_API_KEY"]

            url = f"{config['api_base']}{config['endpoint']}"
            r = requests.get(url, headers=headers, timeout=30)

            if r.status_code == 200:
                data = r.json()
                conversions = data.get("data", data.get("conversions", data.get("orders", [])))
                if isinstance(conversions, dict):
                    conversions = [conversions]
                total_revenue = sum(float(c.get("revenue", c.get("amount", 0)) or 0) for c in conversions)
                print(f"    ✅ 获取到 {len(conversions)} 条转化, 收入: ${total_revenue:.2f}")
                results[partner_name] = {
                    "status": "SUCCESS",
                    "is_real_data": True,
                    "conversions": conversions,
                    "summary": {"total_conversions": len(conversions), "total_revenue": round(total_revenue, 2)},
                    "fetched_at": datetime.now().isoformat(),
                }
            elif r.status_code in [401, 403]:
                print(f"    ❌ 认证失败: {r.status_code}")
                results[partner_name] = {"status": "AUTH_FAILED", "is_real_data": False, "message": f"{r.status_code}", "fetched_at": datetime.now().isoformat()}
            else:
                print(f"    ⚠️ API 返回 {r.status_code}: {r.text[:100]}")
                results[partner_name] = {"status": f"HTTP_{r.status_code}", "is_real_data": False, "message": r.text[:200], "fetched_at": datetime.now().isoformat()}
        except Exception as e:
            print(f"    ❌ 调用失败: {e}")
            results[partner_name] = {"status": "ERROR", "is_real_data": False, "message": str(e), "fetched_at": datetime.now().isoformat()}

    # 汇总
    total_partners = len(results)
    connected = sum(1 for r in results.values() if r.get("status") == "SUCCESS")
    total_revenue_all = sum(r.get("summary", {}).get("total_revenue", 0) for r in results.values() if r.get("status") == "SUCCESS")

    print(f"\n  📊 多 Partner 汇总:")
    print(f"    总 Partner: {total_partners}")
    print(f"    已接通: {connected}")
    print(f"    总收入: ${total_revenue_all:.2f}")

    result = {
        "status": "SUCCESS" if connected > 0 else "NO_CONNECTED_PARTNERS",
        "is_real_data": connected > 0,
        "partners": results,
        "summary": {"total_partners": total_partners, "connected": connected, "total_revenue": round(total_revenue_all, 2)},
        "fetched_at": datetime.now().isoformat(),
    }

    _save_json(MULTI_PARTNER_REAL_DATA, result)
    print(f"  💾 已保存: {MULTI_PARTNER_REAL_DATA}")
    return result


# ============================================================
# 数据验证
# ============================================================

def validate_all_data(results: Dict[str, Dict]) -> Dict:
    """验证所有数据的真实性和新鲜度"""
    print("\n" + "=" * 60)
    print("  数据真实性和新鲜度验证")
    print("=" * 60)

    validation = {
        "validation_time": datetime.now().isoformat(),
        "overall_status": "PENDING",
        "sources": {},
        "summary": {"total_sources": 4, "real_data_count": 0, "fresh_data_count": 0, "issues": []},
    }

    for source_name, source_data in results.items():
        is_real = source_data.get("is_real_data", False)
        is_fresh = source_data.get("is_fresh", False)
        status = source_data.get("status", "UNKNOWN")

        validation["sources"][source_name] = {
            "is_real_data": is_real,
            "is_fresh": is_fresh,
            "data_date": source_data.get("data_date"),
            "status": status,
            "error": source_data.get("error"),
            "validation_status": "PASS" if (is_real and is_fresh) else "WARN" if is_real else "FAIL",
        }

        if is_real:
            validation["summary"]["real_data_count"] += 1
        if is_fresh:
            validation["summary"]["fresh_data_count"] += 1

        if not is_real:
            issue = f"{source_name}: {status} - {source_data.get('error', 'not real data')}"
            validation["summary"]["issues"].append(issue)
        elif not is_fresh:
            validation["summary"]["issues"].append(f"{source_name}: data not fresh ({source_data.get('data_date', 'no date')})")

    real_count = validation["summary"]["real_data_count"]
    fresh_count = validation["summary"]["fresh_data_count"]
    if real_count == 4 and fresh_count == 4:
        validation["overall_status"] = "PASS"
    elif real_count >= 3:
        validation["overall_status"] = "PARTIAL"
    else:
        validation["overall_status"] = "FAIL"

    print(f"\n  验证结果: {validation['overall_status']}")
    print(f"  真实数据源: {real_count}/4")
    print(f"  新鲜数据源: {fresh_count}/4")
    if validation["summary"]["issues"]:
        print("  问题:")
        for issue in validation["summary"]["issues"]:
            print(f"    - {issue}")

    _save_json(DATA_VALIDATION_JSON, validation)

    # Markdown 报告
    report = f"""# 数据真实性和新鲜度验证报告

**验证时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**整体状态**: {validation['overall_status']}

---

## 验证概览

| 数据源 | 真实数据 | 新鲜度 | 数据日期 | API状态 | 验证状态 |
|--------|---------|--------|---------|---------|---------|
"""
    for source_name, info in validation["sources"].items():
        real_icon = "✅" if info["is_real_data"] else "❌"
        fresh_icon = "✅" if info["is_fresh"] else "❌"
        report += f"| {source_name.upper()} | {real_icon} | {fresh_icon} | {info.get('data_date', 'N/A')} | {info.get('status', 'N/A')} | {info['validation_status']} |\n"

    report += f"""
---

## 统计

- 真实数据源: {real_count}/4
- 新鲜数据源: {fresh_count}/4
- 问题数: {len(validation['summary']['issues'])}

---

## 问题清单

"""
    if validation["summary"]["issues"]:
        for i, issue in enumerate(validation["summary"]["issues"], 1):
            report += f"{i}. {issue}\n"
    else:
        report += "无问题，所有数据源均为真实且新鲜的数据。\n"

    report += f"""
---

## 修复指引

- **GA4 NOT_CONFIGURED**: 在 .env 或 GitHub Secrets 中设置 GA4_PROPERTY_ID，并确保 service account 已添加为 GA4 媒体资源的查看者
- **GSC SITE_ACCESS_DENIED**: 在 Google Search Console > Settings > Users and permissions 中添加 service account 邮箱（角色：Full 或 Restricted）
- **Social NOT_CONFIGURED**: 在 .env 或 GitHub Secrets 中设置 BUFFER_API_TOKEN_A 和 BUFFER_API_TOKEN_B

---

*报告由真实数据拉取引擎 v2.1 自动生成*
*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    with open(DATA_VALIDATION_REPORT, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n  验证报告已生成: {DATA_VALIDATION_REPORT}")
    return validation


# ============================================================
# 主入口
# ============================================================

def run_all() -> Dict:
    """运行所有数据拉取"""
    # Kill Switch 检查
    try:
        from ai_governance import check_kill_switch
        is_safe, reason = check_kill_switch()
        if not is_safe:
            print(f"KILL SWITCH ACTIVE: {reason}")
            print("数据拉取被 Kill Switch 阻止")
            return {}
    except ImportError:
        pass

    print("\n" + "=" * 60)
    print("  真实数据拉取引擎 v2.1 - 全量运行（API直连）")
    print("=" * 60)
    print(f"  开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = {}
    results["ga4"] = pull_ga4_data()
    results["gsc"] = pull_gsc_data()
    results["social"] = pull_social_data()
    results["content"] = pull_content_data()
    results["partnerize"] = pull_partnerize_data()
    results["impact"] = pull_impact_data()
    results["multi_partner"] = pull_multi_partner_data()

    validation = validate_all_data(results)

    print("\n" + "=" * 60)
    print("  真实数据拉取完成")
    print("=" * 60)
    for name, data in results.items():
        status = data.get("status", "UNKNOWN")
        real = "REAL" if data.get("is_real_data") else "NOT_REAL"
        print(f"  {name.upper():8s}: {status:20s} | {real}")
    print(f"\n  整体验证: {validation.get('overall_status', 'UNKNOWN')}")
    print(f"  验证报告: {DATA_VALIDATION_REPORT}")

    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="真实数据拉取引擎 v2.1（API直连）")
    parser.add_argument("--all", action="store_true", help="拉取所有数据源")
    parser.add_argument("--ga4", action="store_true", help="仅拉取GA4数据")
    parser.add_argument("--gsc", action="store_true", help="仅拉取GSC数据")
    parser.add_argument("--social", action="store_true", help="仅拉取社媒数据")
    parser.add_argument("--content", action="store_true", help="仅拉取内容数据")
    parser.add_argument("--partnerize", action="store_true", help="仅拉取Partnerize数据")
    parser.add_argument("--impact", action="store_true", help="仅拉取Impact.com数据(NordVPN等)")
    parser.add_argument("--multi-partner", action="store_true", help="拉取所有已配置凭证的多Partner数据")
    parser.add_argument("--validate", action="store_true", help="拉取所有数据并验证")
    args = parser.parse_args()

    if args.all or args.validate:
        run_all()
    elif args.ga4:
        pull_ga4_data()
    elif args.gsc:
        pull_gsc_data()
    elif args.social:
        pull_social_data()
    elif args.content:
        pull_content_data()
    elif args.partnerize:
        pull_partnerize_data()
    elif args.impact:
        pull_impact_data()
    elif args.multi_partner:
        pull_multi_partner_data()
    else:
        run_all()


if __name__ == "__main__":
    main()
