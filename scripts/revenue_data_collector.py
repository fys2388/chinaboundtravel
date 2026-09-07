#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Revenue Data Collector - 统一营收数据收集框架
==================================================

接入真实营收 API，为 Agent KPI 考核提供真实数据。

支持的数据源：
  1. GA4 Data API - 自然流量、转化率、用户行为
  2. Stripe API - eBook 销售额、订阅收入
  3. Travelpayouts API - 联盟佣金收入
  4. Cloudflare Analytics - 网站流量、性能

配置方式：
  复制 .env.revenue.template 为 .env.revenue，填入 API 凭证。

用法:
  python scripts/revenue_data_collector.py
  python scripts/revenue_data_collector.py --source ga4
  python scripts/revenue_data_collector.py --source stripe
  python scripts/revenue_data_collector.py --source travelpayouts
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REVENUE_DIR = PROJECT_ROOT / "reports" / "revenue_data"
REVENUE_DIR.mkdir(parents=True, exist_ok=True)
ENV_FILE = PROJECT_ROOT / ".env.revenue"


def load_env() -> Dict[str, str]:
    """加载环境变量配置"""
    env = {}
    if ENV_FILE.exists():
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env[key.strip()] = value.strip().strip('"').strip("'")
    # 同时从系统环境变量读取
    for key in ["GA4_PROPERTY_ID", "GA4_CREDENTIALS_JSON", "STRIPE_SECRET_KEY",
                "TRAVELPAYOUTS_API_TOKEN", "TRAVELPAYOUTS_MARKER",
                "CF_API_TOKEN", "CF_ZONE_ID"]:
        if key in os.environ:
            env[key] = os.environ[key]
    return env


def check_config(env: Dict[str, str], source: str) -> Dict[str, bool]:
    """检查各数据源的配置状态"""
    status = {
        "ga4": all([env.get("GA4_PROPERTY_ID"), env.get("GA4_CREDENTIALS_JSON")]),
        "stripe": bool(env.get("STRIPE_SECRET_KEY")),
        "travelpayouts": all([env.get("TRAVELPAYOUTS_API_TOKEN"), env.get("TRAVELPAYOUTS_MARKER")]),
        "cloudflare": all([env.get("CF_API_TOKEN"), env.get("CF_ZONE_ID")]),
    }
    return status


def collect_ga4(env: Dict[str, str], days: int = 30) -> Dict[str, Any]:
    """
    从 GA4 Data API 收集数据
    需要: GA4_PROPERTY_ID, GA4_CREDENTIALS_JSON (Service Account JSON)
    """
    if not env.get("GA4_PROPERTY_ID") or not env.get("GA4_CREDENTIALS_JSON"):
        return {"error": "GA4 未配置", "configured": False}

    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import (
            DateRange, Dimension, Metric, RunReportRequest,
        )
        from google.oauth2 import service_account

        credentials_info = json.loads(env["GA4_CREDENTIALS_JSON"])
        credentials = service_account.Credentials.from_service_account_info(credentials_info)
        client = BetaAnalyticsDataClient(credentials=credentials)

        property_id = env["GA4_PROPERTY_ID"]
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        request = RunReportRequest(
            property=f"properties/{property_id}",
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            dimensions=[Dimension(name="sessionDefaultChannelGrouping")],
            metrics=[
                Metric(name="activeUsers"),
                Metric(name="sessions"),
                Metric(name="screenPageViews"),
                Metric(name="conversions"),
                Metric(name="totalRevenue"),
                Metric(name="bounceRate"),
                Metric(name="averageSessionDuration"),
            ],
        )

        response = client.run_report(request)

        data = {
            "source": "ga4",
            "collected_at": datetime.now().isoformat(),
            "period": f"{start_date} to {end_date}",
            "configured": True,
            "totals": {},
            "channels": {},
        }

        for row in response.rows:
            channel = row.dimension_values[0].value
            metrics = {m.name: float(v.value) for m, v in zip(response.metric_headers, row.metric_values)}
            data["channels"][channel] = metrics

        # 汇总
        if response.rows:
            totals = response.rows[0].metric_values
            data["totals"] = {
                "activeUsers": float(totals[0].value),
                "sessions": float(totals[1].value),
                "pageViews": float(totals[2].value),
                "conversions": float(totals[3].value),
                "totalRevenue": float(totals[4].value),
                "bounceRate": float(totals[5].value),
                "avgSessionDuration": float(totals[6].value),
            }

        return data

    except ImportError:
        return {"error": "google-analytics-data 未安装，运行: pip install google-analytics-data", "configured": True}
    except Exception as e:
        return {"error": str(e), "configured": True}


def collect_stripe(env: Dict[str, str], days: int = 30) -> Dict[str, Any]:
    """
    从 Stripe API 收集 eBook 销售数据
    需要: STRIPE_SECRET_KEY
    """
    if not env.get("STRIPE_SECRET_KEY"):
        return {"error": "Stripe 未配置", "configured": False}

    try:
        import stripe
        stripe.api_key = env["STRIPE_SECRET_KEY"]

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # 获取支付意图（一次性支付）
        payment_intents = stripe.PaymentIntent.list(
            created={"gte": int(start_date.timestamp()), "lte": int(end_date.timestamp())},
            limit=100,
        )

        # 获取订阅
        subscriptions = stripe.Subscription.list(
            created={"gte": int(start_date.timestamp()), "lte": int(end_date.timestamp())},
            limit=100,
        )

        # 获取余额交易（实际收入）
        balance_transactions = stripe.BalanceTransaction.list(
            created={"gte": int(start_date.timestamp()), "lte": int(end_date.timestamp())},
            limit=100,
        )

        total_revenue = sum(bt.amount / 100 for bt in balance_transactions.data if bt.amount > 0)
        total_fees = sum(bt.fee / 100 for bt in balance_transactions.data)
        net_revenue = total_revenue - total_fees

        data = {
            "source": "stripe",
            "collected_at": datetime.now().isoformat(),
            "period": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            "configured": True,
            "total_revenue": round(total_revenue, 2),
            "total_fees": round(total_fees, 2),
            "net_revenue": round(net_revenue, 2),
            "payment_intents_count": len(payment_intents.data),
            "subscriptions_count": len(subscriptions.data),
            "successful_payments": sum(1 for pi in payment_intents.data if pi.status == "succeeded"),
        }

        return data

    except ImportError:
        return {"error": "stripe 未安装，运行: pip install stripe", "configured": True}
    except Exception as e:
        return {"error": str(e), "configured": True}


def collect_travelpayouts(env: Dict[str, str], days: int = 30) -> Dict[str, Any]:
    """
    从 Travelpayouts API 收集联盟佣金数据
    需要: TRAVELPAYOUTS_API_TOKEN, TRAVELPAYOUTS_MARKER
    """
    if not env.get("TRAVELPAYOUTS_API_TOKEN") or not env.get("TRAVELPAYOUTS_MARKER"):
        return {"error": "Travelpayouts 未配置", "configured": False}

    try:
        import requests

        token = env["TRAVELPAYOUTS_API_TOKEN"]
        marker = env["TRAVELPAYOUTS_MARKER"]
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        # 获取统计数据
        url = "https://api.travelpayouts.com/v2/statistics/balance"
        headers = {"X-Access-Token": token}
        params = {"marker": marker, "start_date": start_date, "end_date": end_date}

        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        result = response.json()

        data = {
            "source": "travelpayouts",
            "collected_at": datetime.now().isoformat(),
            "period": f"{start_date} to {end_date}",
            "configured": True,
            "raw": result.get("data", {}),
        }

        # 提取关键指标
        if result.get("success") and result.get("data"):
            stats = result["data"]
            data.update({
                "total_commission": float(stats.get("total", 0)),
                "approved_commission": float(stats.get("approved", 0)),
                "pending_commission": float(stats.get("pending", 0)),
                "bookings_count": int(stats.get("bookings", 0)),
                "clicks_count": int(stats.get("clicks", 0)),
                "conversion_rate": float(stats.get("conversion", 0)),
            })

        return data

    except ImportError:
        return {"error": "requests 未安装，运行: pip install requests", "configured": True}
    except Exception as e:
        return {"error": str(e), "configured": True}


def collect_all(env: Dict[str, str], days: int = 30) -> Dict[str, Any]:
    """收集所有数据源"""
    print(f"\n{'='*60}")
    print(f"  营收数据收集 - 最近 {days} 天")
    print(f"{'='*60}\n")

    status = check_config(env, "all")
    print("数据源配置状态:")
    for source, configured in status.items():
        icon = "✅" if configured else "❌"
        print(f"  {icon} {source}: {'已配置' if configured else '未配置'}")

    results = {}
    sources = [
        ("ga4", collect_ga4),
        ("stripe", collect_stripe),
        ("travelpayouts", collect_travelpayouts),
    ]

    for source_name, collector in sources:
        print(f"\n--- 收集 {source_name} ---")
        result = collector(env, days)
        results[source_name] = result
        if result.get("error"):
            print(f"  ⚠️  {result['error']}")
        elif result.get("configured"):
            print(f"  ✅ 收集成功")
            # 打印关键指标
            for k, v in result.items():
                if k not in ("source", "collected_at", "period", "configured", "raw", "channels", "totals"):
                    print(f"     {k}: {v}")

    # 汇总
    print(f"\n{'='*60}")
    print(f"  营收汇总")
    print(f"{'='*60}")

    total_revenue = 0
    if results.get("stripe", {}).get("net_revenue"):
        total_revenue += results["stripe"]["net_revenue"]
        print(f"  Stripe 净收入: ${results['stripe']['net_revenue']:.2f}")
    if results.get("travelpayouts", {}).get("approved_commission"):
        total_revenue += results["travelpayouts"]["approved_commission"]
        print(f"  Travelpayouts 佣金: ${results['travelpayouts']['approved_commission']:.2f}")

    print(f"  总营收: ${total_revenue:.2f}")

    # 保存
    output = {
        "collected_at": datetime.now().isoformat(),
        "period_days": days,
        "total_revenue": round(total_revenue, 2),
        "sources": results,
    }
    output_file = REVENUE_DIR / f"revenue_data_{datetime.now().strftime('%Y%m%d')}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n  💾 数据已保存: {output_file}")

    return output


def main():
    parser = argparse.ArgumentParser(description="Revenue Data Collector")
    parser.add_argument("--source", choices=["ga4", "stripe", "travelpayouts", "all"], default="all")
    parser.add_argument("--days", type=int, default=30, help="收集最近多少天的数据")
    parser.add_argument("--check-config", action="store_true", help="只检查配置状态")
    args = parser.parse_args()

    env = load_env()

    if args.check_config:
        status = check_config(env, "all")
        print("数据源配置状态:")
        for source, configured in status.items():
            icon = "✅" if configured else "❌"
            print(f"  {icon} {source}: {'已配置' if configured else '未配置'}")
        if not ENV_FILE.exists():
            print(f"\n  💡 配置文件不存在: {ENV_FILE}")
            print(f"     请复制 .env.revenue.template 为 .env.revenue 并填入凭证")
        return

    if args.source == "all":
        collect_all(env, args.days)
    else:
        collectors = {"ga4": collect_ga4, "stripe": collect_stripe, "travelpayouts": collect_travelpayouts}
        result = collectors[args.source](env, args.days)
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
