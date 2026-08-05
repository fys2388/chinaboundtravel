#!/usr/bin/env python3
"""
健康检查脚本 - 验证所有关键服务和API连通性
"""

import os
import sys
import json
import requests
from datetime import datetime
from pathlib import Path

# 配置
BASE_DIR = Path(__file__).parent
ENV_FILE = BASE_DIR / ".env"
FEISHU_WEBHOOK = os.getenv("FEISHU_WEBHOOK_URL", "")

# 检查项
CHECKS = [
    {
        "name": "Cloudflare Pages",
        "url": "https://www.chinaboundtravel.com",
        "expected_status": 200
    },
    {
        "name": "Google Analytics",
        "url": "https://www.google-analytics.com/analytics.js",
        "expected_status": 200
    },
    {
        "name": "Buffer API",
        "url": "https://api.buffer.com/1/account.json",
        "expected_status": 200,
        "headers": {"Authorization": f"Bearer {os.getenv('BUFFER_API_TOKEN', '')}"}
    }
]


def load_env():
    """加载.env文件"""
    if ENV_FILE.exists():
        with open(ENV_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip().strip('"').strip("'")


def check_url(check: dict) -> dict:
    """检查单个URL"""
    try:
        headers = check.get("headers", {})
        resp = requests.get(check["url"], headers=headers, timeout=10)
        return {
            "name": check["name"],
            "status": resp.status_code,
            "expected": check["expected_status"],
            "passed": resp.status_code == check["expected_status"],
            "error": None
        }
    except Exception as e:
        return {
            "name": check["name"],
            "status": None,
            "expected": check["expected_status"],
            "passed": False,
            "error": str(e)
        }


def send_feishu_notification(results: list):
    """发送飞书通知"""
    if not FEISHU_WEBHOOK:
        return
    
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    
    lines = [f"## 🔍 健康检查结果 ({datetime.now().strftime('%Y-%m-%d %H:%M')})\n"]
    lines.append(f"总计: {total} | 通过: {passed} | 失败: {total - passed}\n")
    
    for r in results:
        icon = "✅" if r["passed"] else "❌"
        line = f"{icon} **{r['name']}**: {r['status'] or 'ERROR'}"
        if r["error"]:
            line += f" - {r['error'][:50]}"
        lines.append(line)
    
    payload = {
        "msg_type": "text",
        "content": {"text": "\n".join(lines)}
    }
    
    try:
        requests.post(FEISHU_WEBHOOK, json=payload, timeout=10)
    except:
        pass


def main():
    print(f"[{datetime.now()}] 开始健康检查...")
    
    load_env()
    
    results = []
    for check in CHECKS:
        print(f"检查 {check['name']}...")
        result = check_url(check)
        results.append(result)
        status = "✅" if result["passed"] else "❌"
        print(f"  {status} {result['name']}: {result['status']}")
    
    passed = sum(1 for r in results if r["passed"])
    print(f"\n结果: {passed}/{len(results)} 通过")
    
    # 发送飞书通知
    send_feishu_notification(results)
    
    # 返回退出码
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
