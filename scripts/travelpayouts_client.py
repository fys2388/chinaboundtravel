#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Travelpayouts Affiliate Statistics client（P1-GROWTH-14A Revenue 接通）。

单一 Travelpayouts 数据入口：Feishu 报告 / KPI 快照 / revenue provider 共用。
原则：只返回真实 API 数值；无凭据或调用失败返回 None（绝不虚构收入）。

端点：POST https://api.travelpayouts.com/statistics/v1/execute_query
认证：X-Access-Token: <TRAVELPAYOUTS_API_TOKEN>（读取仓库根 .env）
字段：redirects_count / inits_count / searches_count / paid_actions_count / paid_profit_usd_sum
"""
import os
from datetime import date, timedelta
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except Exception:
    pass

import requests

API_URL = "https://api.travelpayouts.com/statistics/v1/execute_query"
FIELDS = ["redirects_count", "inits_count", "searches_count",
          "paid_actions_count", "paid_profit_usd_sum"]


def _token() -> str:
    return os.environ.get("TRAVELPAYOUTS_API_TOKEN", "").strip()


# 进程内缓存：同一 (start,end) 窗口只调一次 API（快照多次构建确定性 + 提速）
_CACHE = {}


def fetch_affiliate_stats(start_date=None, end_date=None, days: int = 28):
    """返回近 N 天 Travelpayouts 汇总：

        {"clicks": int, "bookings": int, "revenue": float, "inits": int, "searches": int}

    无凭据 / API 调用失败返回 None（绝不虚构）。
    start_date / end_date: "YYYY-MM-DD" 或 date；默认 end=today、向前 days 天。
    """
    if not _token():
        print("   ⚠️ TRAVELPAYOUTS_API_TOKEN 未配置，返回 None")
        return None
    end = end_date if isinstance(end_date, date) else (
        date.today() if end_date is None else date.fromisoformat(str(end_date)))
    start = start_date if isinstance(start_date, date) else (
        end - timedelta(days=days - 1) if start_date is None
        else date.fromisoformat(str(start_date)))
    if start > end:
        return None
    cache_key = (start.isoformat(), end.isoformat())
    if cache_key in _CACHE:
        return _CACHE[cache_key]

    headers = {"X-Access-Token": _token(), "Content-Type": "application/json"}
    total = {"clicks": 0, "bookings": 0, "revenue": 0.0, "inits": 0, "searches": 0}
    cur = start
    while cur <= end:
        payload = {
            "fields": FIELDS,
            "filters": [{"field": "date", "op": "eq", "value": cur.isoformat()}],
            "offset": 0,
            "limit": 1,
        }
        try:
            resp = requests.post(API_URL, headers=headers, json=payload, timeout=30)
            if resp.status_code != 200:
                print(f"   ⚠️ Travelpayouts API {cur.isoformat()} HTTP {resp.status_code}")
                return None
            rows = resp.json().get("results", [])
            if rows:
                r = rows[0]
                total["clicks"] += int(r.get("redirects_count") or 0)
                total["bookings"] += int(r.get("paid_actions_count") or 0)
                total["revenue"] += float(r.get("paid_profit_usd_sum") or 0.0)
                total["inits"] += int(r.get("inits_count") or 0)
                total["searches"] += int(r.get("searches_count") or 0)
        except Exception as e:
            print(f"   ⚠️ Travelpayouts API 调用失败 ({cur.isoformat()}): {e}")
            return None
        cur += timedelta(days=1)
    _CACHE[cache_key] = total
    return total


if __name__ == "__main__":
    print(fetch_affiliate_stats(days=28))
