#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
域名重定向 & HTTPS 测试脚本
"""

import requests
import sys

def test_url(url, expected_redirect=None):
    """测试 URL 重定向和状态"""
    print(f"\n{'='*60}")
    print(f"测试: {url}")
    print(f"{'='*60}")
    
    try:
        response = requests.head(url, allow_redirects=True, timeout=30)
        
        print(f"最终 URL: {response.url}")
        print(f"状态码: {response.status_code}")
        
        if response.history:
            print(f"重定向链:")
            for i, resp in enumerate(response.history):
                print(f"  {i+1}. {resp.status_code} -> {resp.url}")
        else:
            print(f"无重定向")
        
        if expected_redirect:
            if expected_redirect in response.url:
                print(f"✅ 重定向符合预期")
                return True
            else:
                print(f"❌ 重定向不符合预期: 期望包含 {expected_redirect}")
                return False
                
        if response.status_code == 200:
            print(f"✅ 页面访问正常")
            return True
        else:
            print(f"❌ 页面访问失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        return False

def main():
    print("="*60)
    print("域名重定向 & HTTPS 测试")
    print("="*60)
    
    results = []
    
    # 测试 1: 裸域重定向
    results.append(("裸域 -> www 重定向", test_url("https://chinaboundtravel.com", "www.chinaboundtravel.com")))
    
    # 测试 2: www 域访问
    results.append(("www 域名访问", test_url("https://www.chinaboundtravel.com")))
    
    # 测试 3: HTTP -> HTTPS 重定向
    results.append(("HTTP -> HTTPS 重定向", test_url("http://www.chinaboundtravel.com", "https://")))
    
    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    all_passed = True
    for test_name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n🎉 所有测试通过！")
    else:
        print("\n⚠️ 部分测试失败，请检查！")
    return all_passed

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    success = main()
    sys.exit(0 if success else 1)
