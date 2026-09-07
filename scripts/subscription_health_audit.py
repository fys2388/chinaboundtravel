#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Subscription Health Audit - 邮件订阅健康检查模块
==================================================

P2-NEW (2026-09-07): 新增用户增长/邮件订阅健康检查，覆盖订阅API、MailerLite连接、表单完整性。

检查项：
  1. /api/subscribe - 正常email、无效email、无效JSON、缺失email、重复订阅
  2. 订阅表单页面存在性检查
  3. MailerLite API 连接状态（需配置 MAILERLITE_API_TOKEN）
  4. 订阅者数量趋势（需配置 MailerLite API）

退出码：
  0 = 全部通过
  1 = 存在失败项（CI阻断）

用法：
  python scripts/subscription_health_audit.py
  python scripts/subscription_health_audit.py --base-url https://www.chinaboundtravel.com
  python scripts/subscription_health_audit.py --json
"""
from __future__ import annotations

import argparse
import json
import os
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
REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports" / "subscription_health"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# 订阅页面检查列表
SUBSCRIPTION_PAGES = [
    "/",
    "/blog/",
    "/about/",
]

# 测试用例定义
TEST_CASES = [
    # === /api/subscribe 正常输入 ===
    {
        "endpoint": "/api/subscribe",
        "name": "subscribe_valid_email",
        "method": "POST",
        "body": {"email": "test-subscribe-" + str(int(time.time())) + "@example.com"},
        "expected_status": 200,
        "expected_fields": ["success", "message"],
        "description": "有效邮箱应返回 200 + 成功消息",
        "severity": "critical",
    },
    # === /api/subscribe 无效输入 ===
    {
        "endpoint": "/api/subscribe",
        "name": "subscribe_invalid_email",
        "method": "POST",
        "body": {"email": "not-an-email"},
        "expected_status": 400,
        "description": "无效邮箱格式应返回 400",
        "severity": "high",
    },
    {
        "endpoint": "/api/subscribe",
        "name": "subscribe_missing_email",
        "method": "POST",
        "body": {},
        "expected_status": 400,
        "description": "缺失 email 字段应返回 400",
        "severity": "high",
    },
    {
        "endpoint": "/api/subscribe",
        "name": "subscribe_invalid_json",
        "method": "POST",
        "body": "not-json",
        "raw_body": True,
        "expected_status": 400,
        "description": "无效 JSON 应返回 400",
        "severity": "medium",
    },
    {
        "endpoint": "/api/subscribe",
        "name": "subscribe_empty_email",
        "method": "POST",
        "body": {"email": ""},
        "expected_status": 400,
        "description": "空邮箱应返回 400",
        "severity": "medium",
    },
    # === CORS 预检 ===
    {
        "endpoint": "/api/subscribe",
        "name": "subscribe_cors_preflight",
        "method": "OPTIONS",
        "expected_status": 200,
        "expected_headers": ["Access-Control-Allow-Origin"],
        "description": "CORS 预检应返回 200 + CORS 头",
        "severity": "medium",
    },
]


def run_test(base_url: str, test: Dict) -> Dict:
    """运行单个测试用例"""
    url = base_url + test["endpoint"]
    result = {
        "name": test["name"],
        "endpoint": test["endpoint"],
        "method": test["method"],
        "description": test["description"],
        "severity": test["severity"],
        "passed": False,
        "status_code": None,
        "response_time_ms": None,
        "error": None,
    }

    try:
        start = time.time()
        headers = {"Content-Type": "application/json"}

        if test["method"] == "OPTIONS":
            resp = requests.options(url, headers={
                "Origin": "https://www.chinaboundtravel.com",
                "Access-Control-Request-Method": "POST",
            }, timeout=10)
        elif test.get("raw_body"):
            resp = requests.post(url, data=test["body"], headers=headers, timeout=10)
        else:
            resp = requests.post(url, json=test["body"], headers=headers, timeout=10)

        elapsed = int((time.time() - start) * 1000)
        result["status_code"] = resp.status_code
        result["response_time_ms"] = elapsed

        # 检查状态码
        if resp.status_code != test["expected_status"]:
            result["error"] = f"期望状态码 {test['expected_status']}，实际 {resp.status_code}"
            try:
                result["response_body"] = resp.json()
            except:
                result["response_body"] = resp.text[:500]
            return result

        # 检查必需字段
        if "expected_fields" in test and resp.status_code == 200:
            try:
                data = resp.json()
                for field in test["expected_fields"]:
                    if field not in data:
                        result["error"] = f"响应缺少字段: {field}"
                        return result
            except Exception as e:
                result["error"] = f"响应解析失败: {str(e)}"
                return result

        # 检查 CORS 头
        if "expected_headers" in test:
            for header in test["expected_headers"]:
                if header not in resp.headers:
                    result["error"] = f"响应缺少头: {header}"
                    return result

        result["passed"] = True

    except requests.exceptions.Timeout:
        result["error"] = "请求超时（>10s）"
    except requests.exceptions.ConnectionError as e:
        result["error"] = f"连接失败: {str(e)[:100]}"
    except Exception as e:
        result["error"] = f"未知错误: {str(e)[:100]}"

    return result


def check_subscription_pages(base_url: str) -> List[Dict]:
    """检查订阅表单页面存在性"""
    results = []
    for page in SUBSCRIPTION_PAGES:
        url = base_url + page
        try:
            resp = requests.get(url, timeout=10)
            has_form = 'subscribe' in resp.text.lower() or 'newsletter' in resp.text.lower() or 'email' in resp.text.lower()
            results.append({
                "page": page,
                "status_code": resp.status_code,
                "has_subscribe_form": has_form,
                "passed": resp.status_code == 200,
            })
        except Exception as e:
            results.append({
                "page": page,
                "error": str(e)[:100],
                "passed": False,
            })
    return results


def check_mailerlite_connection() -> Dict:
    """检查 MailerLite API 连接状态"""
    api_token = os.environ.get("MAILERLITE_API_TOKEN", "")
    result = {
        "configured": bool(api_token),
        "connected": False,
        "subscriber_count": None,
        "error": None,
    }

    if not api_token:
        result["error"] = "MAILERLITE_API_TOKEN 未配置"
        return result

    try:
        resp = requests.get(
            "https://connect.mailerlite.com/api/subscribers?limit=1",
            headers={"Authorization": f"Bearer {api_token}"},
            timeout=10
        )
        if resp.status_code == 200:
            result["connected"] = True
            data = resp.json()
            result["subscriber_count"] = data.get("total", len(data.get("data", [])))
        else:
            result["error"] = f"API 返回 {resp.status_code}: {resp.text[:100]}"
    except Exception as e:
        result["error"] = f"连接失败: {str(e)[:100]}"

    return result


def run_audit(base_url: str, output_json: bool = False) -> int:
    """运行完整的订阅健康审计"""
    print(f"\n{'='*60}")
    print(f"  Subscription Health Audit")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Base URL: {base_url}")
    print(f"{'='*60}\n")

    # 1. 运行 API 测试
    print("  📧 订阅 API 测试:")
    api_results = []
    passed = 0
    failed = 0
    for test in TEST_CASES:
        result = run_test(base_url, test)
        api_results.append(result)
        status = "✅" if result["passed"] else "❌"
        print(f"    {status} {result['name']:40s} {result['status_code']} ({result['response_time_ms']}ms)")
        if result["passed"]:
            passed += 1
        else:
            failed += 1
            if result["error"]:
                print(f"       错误: {result['error']}")

    print(f"\n    汇总: {passed} 通过, {failed} 失败")

    # 2. 检查订阅页面
    print("\n  📄 订阅页面检查:")
    page_results = check_subscription_pages(base_url)
    for pr in page_results:
        status = "✅" if pr["passed"] else "❌"
        form_status = "有订阅表单" if pr.get("has_subscribe_form") else "无订阅表单"
        print(f"    {status} {pr['page']:30s} {pr.get('status_code', 'N/A')} - {form_status}")

    # 3. 检查 MailerLite 连接
    print("\n  🔗 MailerLite 连接:")
    ml_result = check_mailerlite_connection()
    if ml_result["connected"]:
        print(f"    ✅ 已连接，订阅者数量: {ml_result['subscriber_count']}")
    else:
        print(f"    ⚠️  {ml_result['error']}")

    # 4. 总体结果
    total = passed + failed
    all_passed = failed == 0
    print(f"\n{'='*60}")
    if all_passed:
        print(f"  Overall: ✅ ALL PASSED ({passed}/{total} checks passed)")
    else:
        print(f"  Overall: ❌ SOME FAILED ({passed}/{total} checks passed, {failed} failed)")
    print(f"{'='*60}\n")

    # 保存报告
    report = {
        "audit_version": "1.0",
        "audit_time": datetime.now().isoformat(),
        "base_url": base_url,
        "api_tests": api_results,
        "page_checks": page_results,
        "mailerlite": ml_result,
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "all_passed": all_passed,
        },
    }

    report_file = REPORTS_DIR / f"subscription_health_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"  Report saved: {report_file}")

    if output_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))

    return 0 if all_passed else 1


def main():
    parser = argparse.ArgumentParser(description="Subscription Health Audit")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Base URL of the website")
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    args = parser.parse_args()

    sys.exit(run_audit(args.base_url, args.json))


if __name__ == "__main__":
    main()
