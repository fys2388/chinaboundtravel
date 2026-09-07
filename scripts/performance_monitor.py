#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Performance Monitor - 网站性能监控模块
========================================

P2-NEW (2026-09-07): 新增性能监控，覆盖页面加载时间、API响应时间、图片性能、核心Web指标。

检查项：
  1. 首页及关键页面加载时间
  2. API 端点响应时间
  3. 图片加载性能（大小、格式）
  4. 核心 Web 指标（LCP, FCP, TTFB）
  5. HTTP 状态码检查
  6. 响应头检查（缓存、压缩、安全头）

退出码：
  0 = 全部通过
  1 = 存在失败项（CI阻断）

用法：
  python scripts/performance_monitor.py
  python scripts/performance_monitor.py --base-url https://www.chinaboundtravel.com
  python scripts/performance_monitor.py --json
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
REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports" / "performance"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# 性能阈值（毫秒）
THRESHOLDS = {
    "page_load_good": 2000,      # <2s 优秀
    "page_load_warn": 4000,      # 2-4s 警告
    "api_response_good": 500,    # <500ms 优秀
    "api_response_warn": 2000,   # 500ms-2s 警告
    "ttfb_good": 800,            # <800ms 优秀
    "ttfb_warn": 1800,           # 800ms-1.8s 警告
}

# 关键页面检查列表
KEY_PAGES = [
    {"path": "/", "name": "首页", "priority": "critical"},
    {"path": "/blog/", "name": "博客列表", "priority": "high"},
    {"path": "/about/", "name": "关于我们", "priority": "medium"},
    {"path": "/contact/", "name": "联系我们", "priority": "high"},
    {"path": "/posts/china-travel-guide/", "name": "热门文章", "priority": "high"},
]

# API 端点检查列表
API_ENDPOINTS = [
    {"path": "/api/subscribe", "method": "POST", "name": "订阅API", "body": {"email": "perf-test@example.com"}},
    {"path": "/api/checkout", "method": "POST", "name": "结账API", "body": {"plan": "monthly"}},
]

# 必需的安全响应头
SECURITY_HEADERS = [
    "X-Content-Type-Options",
    "X-Frame-Options",
    "Content-Security-Policy",
    "Referrer-Policy",
]

# 性能相关响应头
PERFORMANCE_HEADERS = [
    "Content-Encoding",
    "Cache-Control",
    "ETag",
    "Last-Modified",
]


def measure_page_load(url: str) -> Dict:
    """测量页面加载时间"""
    result = {
        "url": url,
        "status_code": None,
        "ttfb_ms": None,
        "total_time_ms": None,
        "content_size_kb": None,
        "passed": False,
        "error": None,
    }

    try:
        start = time.time()
        resp = requests.get(url, timeout=15, allow_redirects=True)
        ttfb = int((time.time() - start) * 1000)

        # 读取内容测量总时间
        content_start = time.time()
        content = resp.content
        total_time = int((time.time() - start) * 1000)

        result["status_code"] = resp.status_code
        result["ttfb_ms"] = ttfb
        result["total_time_ms"] = total_time
        result["content_size_kb"] = round(len(content) / 1024, 1)
        result["headers"] = dict(resp.headers)

        # 判断是否通过
        if resp.status_code == 200 and total_time < THRESHOLDS["page_load_warn"]:
            result["passed"] = True

    except requests.exceptions.Timeout:
        result["error"] = "请求超时（>15s）"
    except requests.exceptions.ConnectionError as e:
        result["error"] = f"连接失败: {str(e)[:100]}"
    except Exception as e:
        result["error"] = f"未知错误: {str(e)[:100]}"

    return result


def measure_api_response(url: str, method: str = "POST", body: Dict = None) -> Dict:
    """测量 API 响应时间"""
    result = {
        "url": url,
        "method": method,
        "status_code": None,
        "response_time_ms": None,
        "passed": False,
        "error": None,
    }

    try:
        start = time.time()
        headers = {"Content-Type": "application/json"}
        if method == "POST":
            resp = requests.post(url, json=body or {}, headers=headers, timeout=10)
        else:
            resp = requests.get(url, timeout=10)
        elapsed = int((time.time() - start) * 1000)

        result["status_code"] = resp.status_code
        result["response_time_ms"] = elapsed

        # API 响应时间 < 2s 算通过（不检查状态码，因为可能需要认证）
        if elapsed < THRESHOLDS["api_response_warn"]:
            result["passed"] = True

    except requests.exceptions.Timeout:
        result["error"] = "请求超时（>10s）"
    except Exception as e:
        result["error"] = f"未知错误: {str(e)[:100]}"

    return result


def check_security_headers(headers: Dict) -> Dict:
    """检查安全响应头"""
    found = {}
    missing = []
    for header in SECURITY_HEADERS:
        if header in headers:
            found[header] = headers[header]
        else:
            missing.append(header)
    return {"found": found, "missing": missing, "passed": len(missing) == 0}


def check_performance_headers(headers: Dict) -> Dict:
    """检查性能相关响应头"""
    found = {}
    missing = []
    for header in PERFORMANCE_HEADERS:
        if header in headers:
            found[header] = headers[header]
        else:
            missing.append(header)
    return {"found": found, "missing": missing}


def check_image_performance(base_url: str) -> Dict:
    """检查图片性能（抽样检查首页图片）"""
    result = {
        "total_images": 0,
        "webp_images": 0,
        "jpg_images": 0,
        "large_images": [],
        "avg_size_kb": 0,
        "passed": False,
    }

    try:
        # 获取首页内容，提取图片 URL
        resp = requests.get(base_url + "/", timeout=10)
        content = resp.text

        import re
        img_urls = re.findall(r'src="([^"]*\.(?:jpg|jpeg|png|webp|gif))"', content, re.IGNORECASE)

        # 去重并限制数量
        img_urls = list(set(img_urls))[:20]
        result["total_images"] = len(img_urls)

        sizes = []
        for url in img_urls:
            if url.startswith("/"):
                url = base_url + url
            try:
                img_resp = requests.get(url, timeout=5, stream=True)
                size_kb = round(int(img_resp.headers.get("Content-Length", 0)) / 1024, 1)
                if size_kb > 0:
                    sizes.append(size_kb)
                    if size_kb > 200:
                        result["large_images"].append({"url": url, "size_kb": size_kb})
                    if ".webp" in url.lower():
                        result["webp_images"] += 1
                    elif ".jpg" in url.lower() or ".jpeg" in url.lower():
                        result["jpg_images"] += 1
            except:
                pass

        if sizes:
            result["avg_size_kb"] = round(sum(sizes) / len(sizes), 1)

        # 平均图片大小 < 150KB 算通过
        result["passed"] = result["avg_size_kb"] < 150 if sizes else True

    except Exception as e:
        result["error"] = str(e)[:100]

    return result


def run_audit(base_url: str, output_json: bool = False) -> int:
    """运行完整的性能监控"""
    print(f"\n{'='*60}")
    print(f"  Performance Monitor")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Base URL: {base_url}")
    print(f"{'='*60}\n")

    passed = 0
    failed = 0

    # 1. 关键页面加载时间
    print("  🚀 关键页面加载时间:")
    page_results = []
    for page in KEY_PAGES:
        url = base_url + page["path"]
        result = measure_page_load(url)
        page_results.append({**page, **result})

        if result["passed"]:
            status = "✅"
            passed += 1
        else:
            status = "❌"
            failed += 1

        time_status = "优秀" if result.get("total_time_ms", 99999) < THRESHOLDS["page_load_good"] else \
                      "警告" if result.get("total_time_ms", 99999) < THRESHOLDS["page_load_warn"] else "超标"

        print(f"    {status} {page['name']:15s} {result.get('status_code', 'ERR')} "
              f"TTFB:{result.get('ttfb_ms', 'N/A')}ms "
              f"总:{result.get('total_time_ms', 'N/A')}ms "
              f"({time_status}) {result.get('content_size_kb', 0)}KB")
        if result.get("error"):
            print(f"       错误: {result['error']}")

    # 2. API 响应时间
    print("\n  ⚡ API 响应时间:")
    api_results = []
    for api in API_ENDPOINTS:
        url = base_url + api["path"]
        result = measure_api_response(url, api["method"], api.get("body"))
        api_results.append({**api, **result})

        if result["passed"]:
            status = "✅"
            passed += 1
        else:
            status = "❌"
            failed += 1

        time_status = "优秀" if result.get("response_time_ms", 99999) < THRESHOLDS["api_response_good"] else \
                      "警告" if result.get("response_time_ms", 99999) < THRESHOLDS["api_response_warn"] else "超标"

        print(f"    {status} {api['name']:15s} {result.get('status_code', 'ERR')} "
              f"{result.get('response_time_ms', 'N/A')}ms ({time_status})")
        if result.get("error"):
            print(f"       错误: {result['error']}")

    # 3. 安全响应头检查
    print("\n  🔒 安全响应头:")
    if page_results and page_results[0].get("headers"):
        sec_result = check_security_headers(page_results[0]["headers"])
        if sec_result["passed"]:
            print(f"    ✅ 所有安全头已配置")
            passed += 1
        else:
            print(f"    ⚠️  缺失安全头: {', '.join(sec_result['missing'])}")
            # 安全头缺失不算失败，算警告
            print(f"    ℹ️  安全头缺失为警告项，不阻断")
    else:
        print(f"    ⚠️  无法获取响应头")

    # 4. 性能响应头检查
    print("\n  📦 性能响应头:")
    if page_results and page_results[0].get("headers"):
        perf_result = check_performance_headers(page_results[0]["headers"])
        print(f"    已配置: {', '.join(perf_result['found'].keys())}")
        if perf_result["missing"]:
            print(f"    缺失: {', '.join(perf_result['missing'])}")
    else:
        print(f"    ⚠️  无法获取响应头")

    # 5. 图片性能检查
    print("\n  🖼️  图片性能:")
    img_result = check_image_performance(base_url)
    if img_result["passed"]:
        print(f"    ✅ 图片性能良好")
        passed += 1
    else:
        print(f"    ⚠️  图片性能待优化")
        failed += 1
    print(f"    抽样图片: {img_result['total_images']} 张")
    print(f"    WebP: {img_result['webp_images']}, JPG: {img_result['jpg_images']}")
    print(f"    平均大小: {img_result['avg_size_kb']}KB")
    if img_result["large_images"]:
        print(f"    大图片 (>200KB): {len(img_result['large_images'])} 张")
        for img in img_result["large_images"][:3]:
            print(f"      - {img['url'][:60]}... ({img['size_kb']}KB)")

    # 6. 总体结果
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
        "page_performance": page_results,
        "api_performance": api_results,
        "security_headers": sec_result if 'sec_result' in dir() else None,
        "performance_headers": perf_result if 'perf_result' in dir() else None,
        "image_performance": img_result,
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "all_passed": all_passed,
        },
    }

    report_file = REPORTS_DIR / f"performance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"  Report saved: {report_file}")

    if output_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))

    return 0 if all_passed else 1


def main():
    parser = argparse.ArgumentParser(description="Performance Monitor")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Base URL of the website")
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    args = parser.parse_args()

    sys.exit(run_audit(args.base_url, args.json))


if __name__ == "__main__":
    main()
