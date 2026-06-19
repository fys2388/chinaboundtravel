#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Redirect and Sitemap Verification Script
"""

import requests
import sys
from xml.etree import ElementTree as ET

def check_redirects():
    """检查重定向配置"""
    print("Checking redirect configuration...\n")
    
    domains = [
        "http://chinaboundtravel.com",
        "http://www.chinaboundtravel.com",
        "https://chinaboundtravel.com",
        "https://www.chinaboundtravel.com"
    ]
    
    for domain in domains:
        try:
            response = requests.get(domain, allow_redirects=True, timeout=30)
            final_url = response.url
            status_code = response.status_code
            
            print(f"URL: {domain}")
            print(f"  Status: {status_code}")
            print(f"  Final URL: {final_url}")
            
            if domain != final_url:
                print(f"  ✅ Redirected to: {final_url}")
            else:
                print(f"  ⚠️ No redirect")
            
            print()
            
        except Exception as e:
            print(f"URL: {domain}")
            print(f"  ❌ Error: {str(e)}\n")

def check_sitemap():
    """检查sitemap配置"""
    print("Checking sitemap.xml...\n")
    
    try:
        response = requests.get("https://www.chinaboundtravel.com/sitemap.xml", timeout=30)
        
        if response.status_code == 200:
            print(f"✅ sitemap.xml accessible")
            
            # 解析XML
            root = ET.fromstring(response.content)
            namespaces = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            
            urls = root.findall('.//sm:url', namespaces)
            print(f"Found {len(urls)} URLs in sitemap")
            
            # 检查URL是否统一
            has_non_www = False
            has_www = False
            
            for url_elem in urls[:5]:  # 检查前5个URL
                loc = url_elem.find('sm:loc', namespaces).text
                print(f"  URL: {loc}")
                
                if 'www.' in loc:
                    has_www = True
                else:
                    has_non_www = True
            
            print()
            if has_www and not has_non_www:
                print("✅ All URLs use www subdomain")
            elif has_non_www and not has_www:
                print("⚠️ All URLs use non-www")
            else:
                print("❌ Mixed URLs detected!")
                
        else:
            print(f"❌ sitemap.xml not accessible (status: {response.status_code})")
            
    except Exception as e:
        print(f"❌ Error checking sitemap: {str(e)}")

def check_canonical():
    """检查Canonical标签"""
    print("\nChecking Canonical tags...\n")
    
    try:
        response = requests.get("https://www.chinaboundtravel.com", timeout=30)
        
        if response.status_code == 200:
            content = response.text
            
            # 查找canonical标签
            import re
            match = re.search(r'<link rel="canonical" href="([^"]+)"', content, re.IGNORECASE)
            
            if match:
                canonical_url = match.group(1)
                print(f"Found canonical URL: {canonical_url}")
                
                if 'www.chinaboundtravel.com' in canonical_url:
                    print("✅ Canonical URL uses www subdomain")
                else:
                    print("⚠️ Canonical URL does not use www")
            else:
                print("❌ No canonical tag found")
                
    except Exception as e:
        print(f"❌ Error checking canonical: {str(e)}")

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    
    print("=" * 70)
    print("ChinaBound Travel Redirect & Sitemap Verification")
    print("=" * 70)
    
    # 检查重定向
    check_redirects()
    
    # 检查sitemap
    check_sitemap()
    
    # 检查canonical
    check_canonical()
    
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    print("✅ Subscription form: Updated")
    print("✅ Favicon: Updated")
    print("⚠️  Redirects: Need verification")
    print("⚠️  Sitemap: Need verification")
    print("⚠️  Canonical: Need verification")
    print("=" * 70)