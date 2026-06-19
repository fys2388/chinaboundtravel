#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stripe Checkout API Test Script
Simulate user clicking pay button to verify payment flow
"""

import argparse
import json
import urllib.request
import urllib.error
import sys

# Fix Windows encoding issue
sys.stdout.reconfigure(encoding='utf-8')

def test_checkout_api(plan: str):
    """测试 Checkout API 是否正常工作"""
    url = "https://www.chinaboundtravel.com/api/checkout"
    data = json.dumps({"plan": plan}).encode("utf-8")
    
    headers = {
        "Content-Type": "application/json",
        "Origin": "https://www.chinaboundtravel.com",
        "Referer": "https://www.chinaboundtravel.com/pricing/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
    }
    
    print(f"Testing {plan} plan payment flow...")
    print(f"Request URL: {url}")
    print(f"Request data: {json.dumps({'plan': plan})}")
    print("-" * 50)
    
    try:
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as response:
            status_code = response.getcode()
            response_body = response.read().decode("utf-8")
            
            print(f"HTTP Status: {status_code}")
            print(f"Response: {response_body}")
            
            try:
                response_json = json.loads(response_body)
                if "url" in response_json:
                    print(f"Success! Got Stripe Checkout URL: {response_json['url'][:50]}...")
                    print("Test passed! Payment flow working correctly")
                    return True
                elif "error" in response_json:
                    print(f"API Error: {response_json['error']}")
                    return False
            except json.JSONDecodeError:
                print(f"Response is not valid JSON: {response_body}")
                return False
                
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} - {e.reason}")
        try:
            error_body = e.read().decode("utf-8")
            print(f"Error details: {error_body}")
        except:
            pass
        return False
    except urllib.error.URLError as e:
        print(f"Network Error: {e.reason}")
        return False
    except Exception as e:
        print(f"Unknown Error: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Stripe Checkout API Test")
    parser.add_argument("--plan", required=True, choices=["monthly", "annual", "onetime"],
                        help="Plan type to test")
    args = parser.parse_args()
    
    print("=" * 60)
    print("Stripe Payment Flow Test")
    print("=" * 60)
    
    success = test_checkout_api(args.plan)
    
    print("=" * 60)
    if success:
        print("TEST PASSED! Payment flow is working")
        print("\nNext steps for testing:")
        print("1. Use Stripe test card 4242 4242 4242 4242 to complete payment")
        print("2. Verify Success page displays correctly")
        print("3. Check email for download link")
    else:
        print("TEST FAILED! Please check:")
        print("1. Cloudflare Pages deployment status")
        print("2. Stripe API Key configuration")
        print("3. Network connectivity")

if __name__ == "__main__":
    main()