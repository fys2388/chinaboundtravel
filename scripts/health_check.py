#!/usr/bin/env python3
"""
健康检查脚本 - 验证所有关键服务和API连通性
"""

import os
import sys
import json

# Windows ?????????? emoji ??? GBK ???
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
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
        "name": "Google Analytics JS (CDN)",
        "url": "https://www.google-analytics.com/analytics.js",
        "expected_status": 200
    },
    {
        "name": "Buffer API",
        "url": "https://api.buffer.com",
        "method": "POST",
        "expected_status": 200,
        "headers_func": lambda: {
            "Authorization": f"Bearer {os.getenv('BUFFER_API_TOKEN', '')}",
            "Content-Type": "application/json"
        },
        "json_body": {
            "query": "query { channels(input: {organizationId: \"6a17ddf5e051bed5895272f0\"}) { id service name } }"
        }
    }
]


def check_ga4_data_source() -> dict:
    """验证 GA4 服务账号配置是否可真实查询（数据源检查，而非 CDN 连通性）"""
    sa_json = os.getenv("GA4_SERVICE_ACCOUNT_JSON", "")
    prop = os.getenv("GA4_PROPERTY_ID", "")
    if not sa_json or not prop:
        return {"name": "GA4 数据源", "status": "SKIP", "expected": 200, "passed": True,
                "error": "GA4_SERVICE_ACCOUNT_JSON / GA4_PROPERTY_ID 未配置"}
    try:
        # 支持直接 JSON 内容或本地文件路径（相对路径基于博客根目录解析）
        if not sa_json.strip().startswith("{"):
            p = Path(sa_json)
            if not p.is_absolute():
                p = BASE_DIR.parent / p
            if not p.exists():
                return {"name": "GA4 数据源", "status": "SKIP", "expected": 200, "passed": True,
                        "error": "服务账号文件不存在: " + sa_json}
            sa_json = p.read_text(encoding="utf-8")
        info = json.loads(sa_json)

        from google.oauth2 import service_account
        from google.auth.transport.requests import Request
        creds = service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/analytics.readonly"])
        creds.refresh(Request())

        today = datetime.now().strftime("%Y-%m-%d")
        resp = requests.post(
            "https://analyticsdata.googleapis.com/v1beta/properties/" + prop + ":runReport",
            headers={"Authorization": "Bearer " + creds.token, "Content-Type": "application/json"},
            json={"dateRanges": [{"startDate": today, "endDate": today}],
                  "metrics": [{"name": "activeUsers"}], "dimensions": []},
            timeout=15)
        if resp.status_code == 200:
            return {"name": "GA4 数据源", "status": resp.status_code, "expected": 200, "passed": True, "error": None}
        return {"name": "GA4 数据源", "status": resp.status_code, "expected": 200, "passed": False,
                "error": resp.text[:100]}
    except ImportError:
        return {"name": "GA4 数据源", "status": "SKIP", "expected": 200, "passed": True,
                "error": "google-auth 未安装"}
    except Exception as e:
        return {"name": "GA4 数据源", "status": None, "expected": 200, "passed": False, "error": str(e)[:100]}



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


def load_buffer_token():
    """从 buffer_config.json 加载 Buffer API token（如果环境变量未配置）"""
    if os.getenv("BUFFER_API_TOKEN"):
        return

    # 尝试从 buffer_config.json 加载
    config_paths = [
        BASE_DIR.parent / "chinaboundtravel_social_bot" / "buffer_config.json",
        BASE_DIR / "buffer_config.json",
    ]

    for config_path in config_paths:
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # 优先用 account_b 的 token（Facebook/Twitter 账号）
                token = config.get("accounts", {}).get("account_b", {}).get("access_token")
                if not token:
                    token = config.get("api", {}).get("access_token")
                if token:
                    os.environ["BUFFER_API_TOKEN"] = token
                    print(f"  从 {config_path.name} 加载 Buffer token 成功")
                    return
            except Exception as e:
                print(f"  ⚠️ 加载 buffer_config.json 失败: {e}")
            break


def check_url(check: dict) -> dict:
    """检查单个URL"""
    try:
        # 支持 headers_func（动态生成 headers，用于读取最新的环境变量）
        if "headers_func" in check:
            headers = check["headers_func"]()
        else:
            headers = check.get("headers", {})

        method = check.get("method", "GET")
        if method == "POST":
            json_body = check.get("json_body")
            resp = requests.post(check["url"], headers=headers, json=json_body, timeout=10)
        else:
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
        if r.get("status") == "SKIP":
            icon = "⚪"
            line = f"{icon} **{r['name']}**: 未配置/跳过"
        else:
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
    load_buffer_token()
    
    results = []
    # GA4 数据源检查（验证服务账号可真实查询，而非仅 CDN 连通）
    ga4_check = check_ga4_data_source()
    results.append(ga4_check)
    status_icon = "✅" if ga4_check["passed"] else "❌"
    print(f"  {status_icon} {ga4_check['name']}: {ga4_check.get('status') or 'ERROR'}")


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
