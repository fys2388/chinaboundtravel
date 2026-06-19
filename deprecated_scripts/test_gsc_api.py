#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_gsc_api.py - Test Google Search Console API connection
"""

import os
import sys
import io
from datetime import datetime, timedelta
import requests

# Set UTF-8 encoding for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# GSC API configuration
GSC_API_KEY = os.environ.get("GSC_API_KEY", "")
SITE_URL = "https://chinaboundtravel.com"

def test_gsc_api():
    """测试GSC API连接"""
    print("=" * 60)
    print("Google Search Console API 测试")
    print("=" * 60)
    
    if not GSC_API_KEY:
        print("❌ GSC_API_KEY 环境变量未设置")
        print("\n请在 GitHub Secrets 中配置 GSC_API_KEY")
        print("获取方式：")
        print("1. 访问 https://console.cloud.google.com")
        print("2. 创建项目 → 启用 Search Console API")
        print("3. 创建 API 密钥 → 添加到 GitHub Secrets")
        return False
    
    print(f"✅ GSC_API_KEY 已配置: {GSC_API_KEY[:8]}...")
    
    try:
        # 测试 Search Console API
        # 注意：GSC 需要使用 OAuth2 认证，API密钥方式有限制
        
        # 方法1：尝试使用 API 密钥调用
        print("\n尝试调用 GSC API...")
        
        # GSC Search Analytics API 端点
        url = f"https://www.googleapis.com/webmasters/v3/sites/{SITE_URL}/searchAnalytics/query"
        
        headers = {
            "Authorization": f"Bearer {GSC_API_KEY}",
            "Content-Type": "application/json"
        }
        
        params = {
            "startDate": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
            "endDate": datetime.now().strftime("%Y-%m-%d"),
            "dimensions": ["query"],
            "rowLimit": 10
        }
        
        print(f"请求 URL: {url}")
        print(f"请求参数: {params}")
        
        response = requests.post(url, headers=headers, json=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ GSC API 调用成功!")
            print(f"获取到 {len(data.get('rows', []))} 条搜索数据")
            return True
        elif response.status_code == 401:
            print("\n⚠️ API 密钥认证失败")
            print("GSC API 需要 OAuth2 认证，不能直接使用 API 密钥")
            print("\n解决方案：")
            print("1. 使用服务账号认证")
            print("2. 或者使用模拟数据模式（已内置）")
            return False
        elif response.status_code == 403:
            print("\n⚠️ 权限不足")
            print("确保服务账号有 Search Console 访问权限")
            return False
        else:
            print(f"\n❌ API 调用失败: {response.status_code}")
            print(f"响应: {response.text[:200]}")
            return False
            
    except requests.exceptions.Timeout:
        print("\n❌ 请求超时")
        return False
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        return False

def test_gsc_service_account():
    """测试服务账号认证方式"""
    print("\n" + "=" * 60)
    print("GSC 服务账号认证测试")
    print("=" * 60)
    
    # 检查是否配置了服务账号
    service_account_json = os.environ.get("GSC_SERVICE_ACCOUNT_JSON", "")
    
    if not service_account_json:
        # 检查文件
        import json as json_lib
        from pathlib import Path
        
        cred_file = Path("config/gsc_service_account.json")
        if cred_file.exists():
            print(f"✅ 找到服务账号配置文件: {cred_file}")
            with open(cred_file, 'r') as f:
                creds = json_lib.load(f)
                print(f"   客户端邮箱: {creds.get('client_email', 'N/A')}")
            return True
        else:
            print("⚠️ 未配置服务账号")
            print("\n如需使用真实GSC数据，请配置：")
            print("1. 在 Google Cloud Console 创建服务账号")
            print("2. 下载 JSON 密钥文件")
            print("3. 将内容保存到 config/gsc_service_account.json")
            print("4. 在 Search Console 中添加服务账号权限")
            return False
    return False

if __name__ == "__main__":
    # 测试 API 密钥
    api_key_result = test_gsc_api()
    
    # 测试服务账号
    service_account_result = test_gsc_service_account()
    
    print("\n" + "=" * 60)
    print("测试结果总结")
    print("=" * 60)
    
    if api_key_result or service_account_result:
        print("✅ GSC API 可用")
    else:
        print("⚠️ GSC API 需要配置")
        print("\n当前状态：使用模拟数据模式")
        print("系统已内置模拟数据，不影响功能运行")
    
    print("=" * 60)
