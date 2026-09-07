#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Health Audit - API 健康检查模块
=====================================

P1-FIX (2026-09-07): 新增 API 健康检查，覆盖3个API端点的正常/异常输入测试。

检查项：
  1. /api/checkout - 正常plan、无效plan、无效JSON、缺失plan
  2. /api/subscribe - 正常email、无效email、无效JSON、缺失email
  3. /api/stripe-webhook - 无效签名、空body

退出码：
  0 = 全部通过
  1 = 存在失败项（CI阻断）

用法：
  python scripts/api_health_audit.py
  python scripts/api_health_audit.py --base-url https://www.chinaboundtravel.com
  python scripts/api_health_audit.py --json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

try:
    import requests
except ImportError:
    print("ERROR: requests library required. Run: pip install requests")
    sys.exit(1)

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

DEFAULT_BASE_URL = "https://www.chinaboundtravel.com"
REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports" / "api_health"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# 测试用例定义
TEST_CASES = [
    # === /api/checkout ===
    {
        "endpoint": "/api/checkout",
        "name": "checkout_valid_plan_monthly",
        "method": "POST",
        "body": {"plan": "monthly"},
        "expected_status": 200,
        "expected_fields": ["url"],
        "description": "正常 monthly plan 应返回 200 + checkout URL",
        "severity": "critical",
    },
    {
        "endpoint": "/api/checkout",
        "name": "checkout_valid_plan_annual",
        "method": "POST",
        "body": {"plan": "annual"},
        "expected_status": 200,
        "expected_fields": ["url"],
        "description": "正常 annual plan 应返回 200 + checkout URL",
        "severity": "critical",
    },
    {
        "endpoint": "/api/checkout",
        "name": "checkout_valid_plan_onetime",
        "method": "POST",
        "body": {"plan": "onetime"},
        "expected_status": 200,
        "expected_fields": ["url"],
        "description": "正常 onetime plan 应返回 200 + checkout URL",
        "severity": "critical",
    },
    {
        "endpoint": "/api/checkout",
        "name": "checkout_invalid_plan",
        "method": "POST",
        "body": {"plan": "invalid_plan_xyz"},
        "expected_status": 400,
        "expected_fields": ["error"],
        "description": "P0: 无效 plan 应返回 400，不是 500",
        "severity": "critical",
    },
    {
        "endpoint": "/api/checkout",
        "name": "checkout_invalid_json",
        "method": "POST",
        "body": "not valid json {{{",
        "raw_body": True,
        "expected_status": 400,
        "expected_fields": ["error"],
        "description": "P0: 无效 JSON 应返回 400 'Invalid JSON body'，不是 500",
        "severity": "critical",
    },
    {
        "endpoint": "/api/checkout",
        "name": "checkout_missing_plan",
        "method": "POST",
        "body": {},
        "expected_status": 400,
        "expected_fields": ["error"],
        "description": "缺失 plan 字段应返回 400",
        "severity": "high",
    },
    {
        "endpoint": "/api/checkout",
        "name": "checkout_options_preflight",
        "method": "OPTIONS",
        "body": None,
        "expected_status": 204,
        "expected_fields": [],
        "description": "CORS preflight 应返回 204",
        "severity": "medium",
    },

    # === /api/subscribe ===
    {
        "endpoint": "/api/subscribe",
        "name": "subscribe_valid_email",
        "method": "POST",
        "body": {"email": "test-api-health@example.com", "source": "api_health_audit"},
        "expected_status": 200,
        "expected_fields": ["success"],
        "description": "正常 email 订阅应返回 200",
        "severity": "critical",
    },
    {
        "endpoint": "/api/subscribe",
        "name": "subscribe_invalid_email_no_at",
        "method": "POST",
        "body": {"email": "invalid-email"},
        "expected_status": 400,
        "expected_fields": ["error"],
        "description": "P0: 无效 email（无@）应返回 400，不是 500",
        "severity": "critical",
    },
    {
        "endpoint": "/api/subscribe",
        "name": "subscribe_invalid_email_no_domain",
        "method": "POST",
        "body": {"email": "test@"},
        "expected_status": 400,
        "expected_fields": ["error"],
        "description": "P0: 无效 email（无域名）应返回 400",
        "severity": "critical",
    },
    {
        "endpoint": "/api/subscribe",
        "name": "subscribe_empty_email",
        "method": "POST",
        "body": {"email": ""},
        "expected_status": 400,
        "expected_fields": ["error"],
        "description": "空 email 应返回 400",
        "severity": "high",
    },
    {
        "endpoint": "/api/subscribe",
        "name": "subscribe_invalid_json",
        "method": "POST",
        "body": "broken json ]]]",
        "raw_body": True,
        "expected_status": 400,
        "expected_fields": ["error"],
        "description": "P0: 无效 JSON 应返回 400，不是 500",
        "severity": "critical",
    },
    {
        "endpoint": "/api/subscribe",
        "name": "subscribe_missing_email",
        "method": "POST",
        "body": {"source": "test"},
        "expected_status": 400,
        "expected_fields": ["error"],
        "description": "缺失 email 字段应返回 400",
        "severity": "high",
    },

    # === /api/stripe-webhook ===
    {
        "endpoint": "/api/stripe-webhook",
        "name": "webhook_invalid_signature",
        "method": "POST",
        "body": {"type": "checkout.session.completed", "data": {"object": {}}},
        "headers": {"stripe-signature": "t=invalid,v1=invalid"},
        "expected_status": 400,
        "expected_fields": ["error"],
        "description": "无效 webhook 签名应返回 400 'Invalid webhook signature'",
        "severity": "critical",
    },
    {
        "endpoint": "/api/stripe-webhook",
        "name": "webhook_missing_signature",
        "method": "POST",
        "body": {"type": "checkout.session.completed"},
        "expected_status": 400,
        "expected_fields": ["error"],
        "description": "缺失 stripe-signature 头应返回 400",
        "severity": "critical",
    },
    {
        "endpoint": "/api/stripe-webhook",
        "name": "webhook_empty_body",
        "method": "POST",
        "body": "",
        "raw_body": True,
        "expected_status": 400,
        "expected_fields": ["error"],
        "description": "空 body 应返回 400",
        "severity": "high",
    },
]


def run_test(base_url: str, test_case: Dict) -> Dict:
    """运行单个测试用例，返回结果"""
    url = base_url + test_case["endpoint"]
    method = test_case["method"]
    result = {
        "name": test_case["name"],
        "endpoint": test_case["endpoint"],
        "method": method,
        "description": test_case["description"],
        "severity": test_case["severity"],
        "expected_status": test_case["expected_status"],
        "actual_status": None,
        "passed": False,
        "error": None,
        "response_time_ms": None,
        "response_body": None,
    }

    try:
        headers = {"Content-Type": "application/json"}
        if "headers" in test_case:
            headers.update(test_case["headers"])

        start = time.time()
        if method == "GET":
            resp = requests.get(url, timeout=15, headers=headers)
        elif method == "OPTIONS":
            resp = requests.options(url, timeout=15, headers=headers)
        elif method == "POST":
            if test_case.get("raw_body"):
                resp = requests.post(url, data=test_case["body"], timeout=15, headers=headers)
            elif test_case["body"] is None:
                resp = requests.post(url, timeout=15, headers=headers)
            else:
                resp = requests.post(url, json=test_case["body"], timeout=15, headers=headers)
        else:
            result["error"] = f"Unsupported method: {method}"
            return result

        elapsed = (time.time() - start) * 1000
        result["actual_status"] = resp.status_code
        result["response_time_ms"] = round(elapsed, 1)

        # 检查状态码
        if resp.status_code != test_case["expected_status"]:
            result["error"] = f"Status mismatch: expected {test_case['expected_status']}, got {resp.status_code}"
            try:
                result["response_body"] = resp.text[:500]
            except Exception:
                pass
            return result

        # 检查响应字段
        if test_case.get("expected_fields"):
            try:
                body = resp.json()
                result["response_body"] = str(body)[:300]
                for field in test_case["expected_fields"]:
                    if field not in body:
                        result["error"] = f"Missing field in response: {field}"
                        return result
            except Exception as e:
                result["error"] = f"Response is not valid JSON: {e}"
                return result

        result["passed"] = True

    except requests.exceptions.Timeout:
        result["error"] = "Request timeout (15s)"
    except requests.exceptions.ConnectionError as e:
        result["error"] = f"Connection error: {str(e)[:200]}"
    except Exception as e:
        result["error"] = f"Unexpected error: {type(e).__name__}: {str(e)[:200]}"

    return result


def run_all(base_url: str) -> Dict:
    """运行全部测试"""
    print(f"\n{'='*60}")
    print(f"  API Health Audit")
    print(f"  Target: {base_url}")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Test cases: {len(TEST_CASES)}")
    print(f"{'='*60}\n")

    results = []
    for tc in TEST_CASES:
        result = run_test(base_url, tc)
        results.append(result)
        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        time_str = f" ({result['response_time_ms']}ms)" if result["response_time_ms"] else ""
        print(f"  {status} [{result['severity'].upper()}] {result['name']}{time_str}")
        if not result["passed"] and result["error"]:
            print(f"         → {result['error']}")
            if result["response_body"]:
                print(f"         → Response: {result['response_body'][:200]}")

    # 统计
    passed = [r for r in results if r["passed"]]
    failed = [r for r in results if not r["passed"]]
    critical_failed = [r for r in failed if r["severity"] == "critical"]
    high_failed = [r for r in failed if r["severity"] == "high"]

    print(f"\n{'='*60}")
    print(f"  Summary: {len(passed)}/{len(results)} passed")
    print(f"  Failed: {len(failed)} (critical: {len(critical_failed)}, high: {len(high_failed)})")
    if critical_failed:
        print(f"  ⚠️  CRITICAL FAILURES EXIST — CI should block")
    print(f"{'='*60}\n")

    report = {
        "audit_version": "1.0",
        "audit_time": datetime.now().isoformat(),
        "base_url": base_url,
        "summary": {
            "total": len(results),
            "passed": len(passed),
            "failed": len(failed),
            "critical_failed": len(critical_failed),
            "high_failed": len(high_failed),
            "pass_rate": round(len(passed) / len(results) * 100, 1),
        },
        "results": results,
    }

    # 保存报告
    report_path = REPORTS_DIR / f"api_health_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"  Report saved: {report_path}")

    return report


def main():
    parser = argparse.ArgumentParser(description="API Health Audit")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Target base URL")
    parser.add_argument("--json", action="store_true", help="JSON output only")
    args = parser.parse_args()

    report = run_all(args.base_url)

    if args.json:
        print(json.dumps(report["summary"], ensure_ascii=False, indent=2))

    # 退出码：有 critical 失败则 exit 1
    if report["summary"]["critical_failed"] > 0:
        print("\n  ❌ EXIT 1: Critical API health failures detected")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
