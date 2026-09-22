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
# 2026-09-18 修复：移除 "/blog/"。线上实测 404——博客在 /posts/
# （hugo.toml [[menu.main]] identifier="posts" url="/posts/"），且
# content/ + layouts/ + static/ 全站 0 处链接指向 /blog/，是纯孤儿 URL。
# 留着它让每次审计都产生一个假失败，把真实健康度压低。
SUBSCRIPTION_PAGES = [
    "/",
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
        # 2026-09-18 修复：原先要求 ["success", "message"]，但线上实际响应是
        # {"success":true,"subscriber_created":true,"delivered_pdf":false,
        #  "lead_magnet":"china-visa-free-entry-checklist","detail":...}
        # ——没有 message 字段。期望过时导致每次审计都把一个工作正常的接口
        # 判成 critical 失败。success 才是真正的契约字段。
        "expected_fields": ["success"],
        # 2026-09-18：捕获成功响应体，用来判断线上 MailerLite/Resend 真实配置。
        # 本机 env 里没有 token 不等于线上没配——生产走 GitHub Actions secrets，
        # 本机只能看到本机 .env。端点自报的 subscriber_created / delivered_pdf /
        # detail 才是线上真实状态（见 derive_endpoint_provider_status）。
        "capture_body_on_pass": True,
        "description": "有效邮箱应返回 200 + success=true",
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
        # 2026-09-18 修复：原先只认 200。线上实测 204 No Content——
        # 对 OPTIONS 预检这是标准且更正确的响应（预检无需响应体）。
        # 只认 200 会把正常工作的预检判成失败。
        "expected_status": [200, 204],
        "expected_headers": ["Access-Control-Allow-Origin"],
        "description": "CORS 预检应返回 200/204 + CORS 头",
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

        # 检查状态码。expected_status 可以是单个值，也可以是可接受值的列表
        #（OPTIONS 预检 200 与 204 都合法）。
        expected = test["expected_status"]
        ok_statuses = list(expected) if isinstance(expected, (list, tuple)) else [expected]
        if resp.status_code not in ok_statuses:
            result["error"] = f"期望状态码 {ok_statuses}，实际 {resp.status_code}"
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

        # 显式声明的用例在通过时也保留响应体，供下游读取端点自报的状态。
        if test.get("capture_body_on_pass"):
            try:
                result["response_body"] = resp.json()
            except Exception:
                result["response_body"] = resp.text[:500]

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


def derive_endpoint_provider_status(api_results: List[Dict]) -> Dict:
    """从端点自身响应推导线上服务商配置状态。

    check_mailerlite_connection() 读的是本机 env。本机没有 MAILERLITE_API_TOKEN
    只说明本机没配——生产环境由 GitHub Actions secrets 注入，本机根本看不到。
    实测线上 /api/subscribe 返回 subscriber_created=true，即 MailerLite 已配置
    且真的在创建订阅者；本机审计却报「未配置」，是一个持续误导运营者的假信号。

    functions/api/subscribe.js 会自报状态：
      subscriber_created / delivered_pdf / detail（含 "MailerLite:not_configured"
      或 "Resend:422" 之类的标记）。读这些比读本机 env 准。

    注意：detail 里的 422 不代表 Resend 没配。Resend 拒绝向 example.com 这类
    RFC 保留域名发信，所以审计用的测试邮箱拿到 422 恰恰证明 Resend 已配置
    并且真的发出了请求。真实订阅者邮箱不受此限制。
    """
    info: Dict[str, Any] = {
        "source": "endpoint_response",
        "mailerlite": "unknown",
        "resend": "unknown",
        "evidence": {},
    }

    for r in api_results:
        if r.get("name") != "subscribe_valid_email":
            continue
        body = r.get("response_body")
        if not isinstance(body, dict):
            info["evidence"]["note"] = "有效邮箱用例未捕获响应体，无法判断线上配置"
            return info

        created = bool(body.get("subscriber_created"))
        delivered = bool(body.get("delivered_pdf"))
        detail = str(body.get("detail") or "")

        info["mailerlite"] = "configured_and_accepting" if created else "not_accepting"

        if delivered:
            info["resend"] = "configured_and_delivering"
        elif "Resend:not_configured" in detail:
            info["resend"] = "not_configured"
        elif "Resend:" in detail:
            # 已配置并已发出请求，只是被收件方校验拒掉（常见于保留域名）
            info["resend"] = "configured_but_rejected_by_provider"
        else:
            info["resend"] = "unknown"

        info["evidence"] = {
            "subscriber_created": created,
            "delivered_pdf": delivered,
            # 截断避免报告膨胀；该字段不含任何 token/key
            "detail_excerpt": detail[:200],
        }
        return info

    info["evidence"]["note"] = "未找到有效邮箱用例"
    return info


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
    # 本机 env 看不到的线上配置，改读端点自报
    ep = derive_endpoint_provider_status(api_results)
    ml_result["endpoint_reported"] = ep
    print(f"    🔎 端点自报: MailerLite={ep['mailerlite']}  Resend={ep['resend']}")

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
        # AUDIT-RV-003: summary.all_passed 只统计测试用例的 HTTP 状态码是否匹配
        # expected_status（HTTP 200 + success=true 即通过），不区分「PDF 真的
        # 送达了」与「Resend 拒绝向测试邮箱发信」。测试邮箱是 @example.com
        # （RFC 6761 保留域名），Resend 强制返回 422；真实用户邮箱不受此限。
        # delivery_unverifiable=true 表示审计无法验证 PDF 送达，需要人工
        # 登录 Resend / MailerLite 后台核实。不 claim 真实用户收不到 PDF。
        "delivery_unverifiable": ep["resend"] in (
            "configured_but_rejected_by_provider", "unknown",
        ),
        "delivery_evidence": {
            "test_email_domain": "example.com",
            "resend_status": ep["resend"],
            "resend_note": (
                "Resend 拒绝向 RFC 6761 保留域名（example.com）发信并返回 422；"
                "该拒绝恰恰证明 Resend 已配置并真的发出了请求。真实用户邮箱"
                "不在保留域名内，不受此限。"
                if ep["resend"] == "configured_but_rejected_by_provider" else
                "Resend 未配置或状态未知，PDF 送达无法验证"
                if ep["resend"] in ("not_configured", "unknown") else
                "Resend 已配置且已送达（delivered_pdf=true）"
            ),
        },
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
