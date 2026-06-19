#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deployment Verification Script
Checks if the latest changes (new subscription form and favicon) are deployed
"""

import requests
from datetime import datetime
import sys

def check_subscription_form():
    """检查订阅表单是否已更新"""
    print("Checking subscription form...")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }
        
        response = requests.get('https://www.chinaboundtravel.com', headers=headers, timeout=30)
        response.raise_for_status()
        
        content = response.text
        
        new_form_features = [
            'subscribe-fields',
            'subscribe-input',
            'subscribe-btn',
            'btn-text',
            'Enter your email address',
            'Subscribe Now',
            'emailSubscribeForm'
        ]
        
        old_form_features = [
            'subscribe-button',
        ]
        
        print("\nPage status code:", response.status_code)
        print("Response time:", "{:.2f} seconds".format(response.elapsed.total_seconds()))
        print("Page size:", len(content)//1024, "KB")
        
        print("\n--- New subscription form features ---")
        found_new_features = 0
        for feature in new_form_features:
            if feature in content:
                print("FOUND:", feature)
                found_new_features += 1
            else:
                print("MISSING:", feature)
        
        print("\n--- Old subscription form features ---")
        found_old_features = 0
        for feature in old_form_features:
            if feature in content:
                print("OLD FOUND:", feature)
                found_old_features += 1
            else:
                print("OLD REMOVED:", feature)
        
        print("\n--- Result ---")
        if found_new_features >= len(new_form_features) - 2:
            print("SUCCESS: Subscription form updated!")
            return True
        else:
            print("WARNING: Subscription form still old version")
            return False
            
    except Exception as e:
        print("ERROR:", str(e))
        return False

def check_favicon():
    """检查Favicon是否已更新"""
    print("\nChecking favicon...")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Cache-Control': 'no-cache'
        }
        
        response = requests.get('https://www.chinaboundtravel.com/images/favicon/favicon.svg', headers=headers, timeout=30)
        
        print("\nFavicon status code:", response.status_code)
        
        if response.status_code == 200:
            content = response.text
            if '3A6EA5' in content:
                print("SUCCESS: Favicon updated (contains pagoda design)")
                return True
            else:
                print("WARNING: Favicon exists but may not be new version")
                return False
        else:
            print("ERROR: Favicon not found")
            return False
            
    except Exception as e:
        print("ERROR:", str(e))
        return False

def check_deployment_time():
    """检查网站最后修改时间"""
    print("\nChecking last modified time...")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.head('https://www.chinaboundtravel.com', headers=headers, timeout=30)
        
        if 'Last-Modified' in response.headers:
            last_modified = response.headers['Last-Modified']
            print("Last modified:", last_modified)
            return last_modified
        else:
            print("Cannot get last modified time")
            return None
            
    except Exception as e:
        print("ERROR:", str(e))
        return None

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    print("=" * 60)
    print("ChinaBound Travel Deployment Verification")
    print("=" * 60)
    print("Check time:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("-" * 60)
    
    form_ok = check_subscription_form()
    favicon_ok = check_favicon()
    last_modified = check_deployment_time()
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    if form_ok and favicon_ok:
        print("All checks passed! Website updated successfully!")
        print("\nIf browser still shows old version:")
        print("1. Clear browser cache (Ctrl+Shift+R)")
        print("2. Use incognito window")
        print("3. Wait for CDN cache expiration")
    else:
        print("Some checks failed. Please verify deployment status.")
        print("\nPossible reasons:")
        print("1. Cloudflare deployment not completed")
        print("2. CDN cache not cleared")
        print("3. GitHub Actions workflow failed")
        print("\nCheck these links:")
        print("- GitHub Actions: https://github.com/fys2388/chinaboundtravel/actions")
        print("- Cloudflare Pages: https://dash.cloudflare.com/")
    print("=" * 60)