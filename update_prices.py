#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

# Update these with your TEST mode Price IDs from Stripe Dashboard
TEST_PRICES = {
    'monthly': 'price_TEST_MONTHLY',   # Replace with actual test price ID
    'annual': 'price_TEST_ANNUAL',    # Replace with actual test price ID
    'onetime': 'price_TEST_ONETIME',  # Replace with actual test price ID
}

def update_checkout_js():
    with open('functions/api/checkout.js', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace price IDs
    content = content.replace(
        "monthly: { priceId: 'price_1TbjHO9rCn6b9ZnBDg6wfaLJ'",
        f"monthly: {{ priceId: '{TEST_PRICES['monthly']}'"
    )
    content = content.replace(
        "annual: { priceId: 'price_1TaVSM9rCn6b9ZnBurUqHyLw'",
        f"annual: {{ priceId: '{TEST_PRICES['annual']}'"
    )
    content = content.replace(
        "onetime: { priceId: 'price_1TaVOT9rCn6b9ZnBYZFq2dHx'",
        f"onetime: {{ priceId: '{TEST_PRICES['onetime']}'"
    )
    
    with open('functions/api/checkout.js', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Updated functions/api/checkout.js")

def update_hugo_toml():
    with open('hugo.toml', 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("ℹ️ hugo.toml Payment Links are currently using Stripe Payment Links format")
    print("   These will continue to work for direct links")

if __name__ == '__main__':
    print("=" * 60)
    print("Stripe Price ID Update Script")
    print("=" * 60)
    print()
    print("Current TEST Price IDs:")
    print(f"  Monthly: {TEST_PRICES['monthly']}")
    print(f"  Annual: {TEST_PRICES['annual']}")
    print(f"  One-time: {TEST_PRICES['onetime']}")
    print()
    
    if 'TEST' in TEST_PRICES['monthly']:
        print("⚠️ WARNING: Replace the placeholder Price IDs with actual test IDs!")
        print("   Go to Stripe Dashboard (Test Mode) → Products → Create Products")
        print()
    
    update_checkout_js()
    update_hugo_toml()
    
    print()
    print("✅ Configuration update script ready!")
    print("   Remember to update TEST_PRICES dictionary with actual IDs")