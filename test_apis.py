#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API接口测试工具
支持测试 Cloudflare 和 GSC API
"""

import os
import sys
import io
import json
import requests
from datetime import datetime, timedelta

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def test_cloudflare():
    """测试 Cloudflare API 连接"""
    print("="*60)
    print("☁️ 测试 Cloudflare API")
    print("="*60)
    
    cf_token = os.environ.get("CLOUDFLARE_API_TOKEN", "")
    cf_zone_id = os.environ.get("CLOUDFLARE_ZONE_ID", "")
    
    if not cf_token or not cf_zone_id:
        print("❌ Cloudflare API 未配置")
        print("\n请配置环境变量:")
        print("  set CLOUDFLARE_API_TOKEN=<your_token>")
        print("  set CLOUDFLARE_ZONE_ID=<your_zone_id>")
        return False
    
    print(f"✅ API Token: {cf_token[:8]}...")
    print(f"✅ Zone ID: {cf_zone_id[:8]}...")
    
    try:
        # 测试获取区域信息
        url = f"https://api.cloudflare.com/client/v4/zones/{cf_zone_id}"
        headers = {"Authorization": f"Bearer {cf_token}"}
        
        print("\n📡 正在调用 Cloudflare API...")
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            zone_name = data.get("result", {}).get("name", "N/A")
            status = data.get("result", {}).get("status", "N/A")
            
            print(f"\n✅ API 调用成功!")
            print(f"   域名: {zone_name}")
            print(f"   状态: {status}")
            
            # 尝试获取流量数据
            print("\n📊 获取流量数据...")
            analytics_url = f"https://api.cloudflare.com/client/v4/zones/{cf_zone_id}/analytics/dashboard"
            start_time = (datetime.now() - timedelta(days=1)).isoformat() + "Z"
            end_time = datetime.now().isoformat() + "Z"
            
            params = {"since": start_time, "until": end_time}
            response = requests.get(analytics_url, headers=headers, params=params, timeout=15)
            
            if response.status_code == 200:
                analytics = response.json()
                result = analytics.get("result", {})
                
                if result:
                    print(f"   独立访客: {result.get('requests', {}).get('all', {}).get('visitors', 'N/A'):,}")
                    print(f"   请求数: {result.get('requests', {}).get('all', {}).get('requests', 'N/A'):,}")
                    print(f"   带宽: {result.get('bandwidth', {}).get('all', {}).get('bandwidth', 'N/A'):,} bytes")
                else:
                    print("   ⚠️ 流量数据为空")
            
            return True
        else:
            print(f"\n❌ API 调用失败: {response.status_code}")
            print(f"   响应: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_gsc():
    """测试 Google Search Console API"""
    print("="*60)
    print("🔍 测试 Google Search Console API")
    print("="*60)
    
    gsc_key = os.environ.get("GSC_API_KEY", "")
    
    if not gsc_key:
        print("❌ GSC API 未配置")
        print("\n请配置环境变量:")
        print("  set GSC_API_KEY=<your_api_key>")
        print("\n⚠️ 注意: GSC API 需要 OAuth2 认证")
        print("API Key 方式功能受限，建议使用服务账号")
        return False
    
    print(f"✅ API Key: {gsc_key[:8]}...")
    
    try:
        # 测试调用
        site_url = "https://chinaboundtravel.com"
        url = f"https://www.googleapis.com/webmasters/v3/sites/{site_url}/searchAnalytics/query"
        
        headers = {"Authorization": f"Bearer {gsc_key}"}
        params = {
            "startDate": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
            "endDate": datetime.now().strftime("%Y-%m-%d"),
            "dimensions": ["query"],
            "rowLimit": 10
        }
        
        print("\n📡 正在调用 GSC API...")
        response = requests.post(url, headers=headers, json=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            rows = data.get("rows", [])
            
            print(f"\n✅ API 调用成功!")
            print(f"   获取到 {len(rows)} 条搜索数据")
            
            if rows:
                print("\n   Top 5 关键词:")
                for i, row in enumerate(rows[:5]):
                    query = row.get("keys", [""])[0]
                    clicks = row.get("clicks", 0)
                    impressions = row.get("impressions", 0)
                    position = row.get("position", 0)
                    print(f"   {i+1}. {query} - 点击: {clicks}, 展示: {impressions}, 排名: {position:.1f}")
            
            return True
        elif response.status_code == 401:
            print("\n❌ 认证失败 - API Key 方式不支持")
            print("\n💡 解决方案:")
            print("  1. 使用 OAuth2 认证")
            print("  2. 或使用服务账号")
            print("  3. 当前使用模拟数据模式")
            return False
        else:
            print(f"\n❌ API 调用失败: {response.status_code}")
            print(f"   响应: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_all():
    """测试所有 API"""
    print("\n" + "="*60)
    print("🧪 运行所有 API 测试")
    print("="*60 + "\n")
    
    cf_result = test_cloudflare()
    print("\n" + "="*60)
    gsc_result = test_gsc()
    
    print("\n" + "="*60)
    print("📋 测试结果汇总")
    print("="*60)
    print(f"Cloudflare API: {'✅ 通过' if cf_result else '❌ 未通过'}")
    print(f"GSC API: {'✅ 通过' if gsc_result else '❌ 未通过'}")
    print("="*60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="API接口测试工具")
    parser.add_argument("--test-cf", action="store_true", help="测试 Cloudflare API")
    parser.add_argument("--test-gsc", action="store_true", help="测试 GSC API")
    parser.add_argument("--test-all", action="store_true", help="测试所有 API")
    
    args = parser.parse_args()
    
    if args.test_cf:
        test_cloudflare()
    elif args.test_gsc:
        test_gsc()
    elif args.test_all:
        test_all()
    else:
        parser.print_help()