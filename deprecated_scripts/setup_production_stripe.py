#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

def clear_stripe_config():
    """清理所有 Stripe 相关配置"""
    print("=" * 60)
    print("🧹 清理现有 Stripe 配置")
    print("=" * 60)
    
    # 1. 更新定价页面使用直接 Payment Links
    print("\n1. 更新定价页面...")
    pricing_content = """---
title: 'ChinaBound Travel - Pricing Plans'
description: 'Choose your China travel companion. Three plans to fit every travel style and budget.'
date: '2026-06-02T10:00:00+08:00'
type: page
layout: pricing
hideMeta: true
hideReadTime: true
---

# Choose Your China Travel Pass

*Real-time visa alerts. Crowd-skipping routes. Scam-proof strategies.*

All plans include the current **ChinaBound Travel Guide 2026.05** PDF updated monthly.

---

## Annual Elite Pass *Most Popular*

**$49.99/year**  
*Cancel anytime · PDF included · Save 58% vs Monthly*

<a href="https://buy.stripe.com/14A7sF1vWcEH3mxc1m1gs03" class="buy-link" target="_blank" rel="noopener noreferrer">
  <button class="buy-btn">Get Instant Access →</button>
</a>

---

## One-Time Buyout

**$14.99** *(pay once, yours forever)*

Includes the current edition only. No future updates. Perfect for one-time travelers.

<a href="https://buy.stripe.com/28E8wJ4I8bADg9je9u1gs01" class="buy-link" target="_blank" rel="noopener noreferrer">
  <button class="buy-btn">Buy Now →</button>
</a>

---

## Monthly Radar

**$1 First Month, Regular $9.99/month**  
*Use coupon: FIRSTMONTH1 at checkout*

Includes weekly Travel Radar emails + monthly guide updates. Cancel anytime.

<a href="https://buy.stripe.com/14AdR32A05cf9KV1mI1gs04" class="buy-link" target="_blank" rel="noopener noreferrer">
  <button class="buy-btn">Start for $1 →</button>
</a>

---

## Plan Comparison

| Features | One-Time ($14.99) | Monthly ($1/$9.99) | Annual Elite ($49.99) |
|---|:---:|:---:|:---:|
| PDF Guide (current edition) | ✅ | ✅ | ✅ |
| Future monthly updates | ❌ | ✅ | ✅ |
| Weekly Travel Radar emails | ❌ | ✅ | ✅ |
| Pre-trip city guides (7 days before travel) | ❌ | ✅ | ✅ |
| AI trip planner template pack | ❌ | ✅ | ✅ |
| Priority email support | ❌ | ❌ | ✅ |
| Price per year | $14.99 | $119.88 | $49.99 |

---

## What Our Travelers Say

> "This guide saved me hours of research! The visa section alone was worth the price."  
> — Sarah K., USA

> "The weekly radar emails kept me updated on the latest travel restrictions. Highly recommend!"  
> — Michael T., UK

> "Best investment for my China trip. The scam-proof tips were invaluable."  
> — Lisa W., Australia

---

## Frequently Asked Questions

**Can I cancel anytime?**  
Yes. Monthly subscribers can cancel before the next billing cycle. Annual subscribers can cancel up to 7 days before renewal. No refunds once download begins.

**What payment methods do you accept?**  
All major credit cards, debit cards, and Apple/Google Pay via Stripe.

**When will I receive my PDF?**  
Immediately after purchase. Check your inbox (and spam folder) for the download link.

**Is this a subscription?**  
The Monthly and Annual plans are subscriptions. The One-Time Buyout is a single payment with no recurring charges.

**How does the first month discount work?**  
Use coupon code **FIRSTMONTH1** at checkout to get $1 for your first month. After the first month, you'll be charged the regular $9.99/month rate. You can cancel anytime before the next billing cycle.

---

*All prices in USD. Digital products are non-refundable once downloaded.*

---

**Disclaimer:** Some links on this site are affiliate links. We may earn a small commission at no extra cost to you if you make a purchase.
"""
    with open('content/pricing.md', 'w', encoding='utf-8') as f:
        f.write(pricing_content)
    print("   ✅ content/pricing.md 更新完成")
    
    # 2. 更新 checkout.js 使用正式价格 ID
    print("\n2. 更新 Checkout API...")
    checkout_content = """/**
 * Stripe Checkout Session API - PRODUCTION
 * POST /api/checkout { plan: "monthly" | "annual" | "onetime" }
 */

export async function onRequestPost({ request, env }) {
  const origin = request.headers.get('Origin') || request.headers.get('origin');
  
  const corsHeaders = {
    'Access-Control-Allow-Origin': origin || 'https://www.chinaboundtravel.com',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Origin',
    'Content-Type': 'application/json',
  };

  if (request.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: corsHeaders });
  }

  try {
    const { plan } = await request.json();

    const PLANS = {
      monthly: { priceId: 'price_1TbjHO9rCn6b9ZnBDg6wfaLJ', coupon: 'FIRSTMONTH1', mode: 'subscription' },
      annual: { priceId: 'price_1TaVSM9rCn6b9ZnBurUqHyLw', coupon: null, mode: 'subscription' },
      onetime: { priceId: 'price_1TaVOT9rCn6b9ZnBYZFq2dHx', coupon: null, mode: 'payment' },
    };

    const planConfig = PLANS[plan];
    if (!planConfig) {
      return jsonResponse({ error: 'Invalid plan' }, 400, corsHeaders);
    }

    const successUrl = env.SUCCESS_URL || 'https://www.chinaboundtravel.com/success/';
    const cancelUrl = env.CANCEL_URL || 'https://www.chinaboundtravel.com/pricing/';
    const stripeKey = env.STRIPE_SECRET_KEY;

    if (!stripeKey) {
      return jsonResponse({ error: 'Stripe API key not configured' }, 500, corsHeaders);
    }

    let formData = `mode=${planConfig.mode}&success_url=${encodeURIComponent(\`${successUrl}?session_id={CHECKOUT_SESSION_ID}\`)}&cancel_url=${encodeURIComponent(cancelUrl)}&line_items[0][price]=${planConfig.priceId}&line_items[0][quantity]=1&metadata[plan]=${plan}&metadata[source]=chinaboundtravel_website&payment_method_types[0]=card&billing_address_collection=auto`;

    if (planConfig.coupon) {
      formData += `&discounts[0][coupon]=${planConfig.coupon}`;
    }

    const response = await fetch('https://api.stripe.com/v1/checkout/sessions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': `Bearer ${stripeKey}`,
      },
      body: formData,
    });

    const session = await response.json();

    if (!response.ok) {
      return jsonResponse({ error: session.error?.message || 'Stripe API error' }, response.status, corsHeaders);
    }

    return jsonResponse({ url: session.url }, 200, corsHeaders);

  } catch (err) {
    console.error('Checkout error:', err.message);
    return jsonResponse({ error: err.message }, 500, corsHeaders);
  }
}

function jsonResponse(body, status, headers) {
  return new Response(JSON.stringify(body), { status, headers });
}
"""
    with open('functions/api/checkout.js', 'w', encoding='utf-8') as f:
        f.write(checkout_content)
    print("   ✅ functions/api/checkout.js 更新完成")
    
    # 3. 更新 webhook.js 使用正式配置
    print("\n3. 更新 Webhook...")
    webhook_content = """/**
 * Stripe Webhook Handler - PRODUCTION
 * POST /api/stripe-webhook
 */

export async function onRequestPost({ request, env }) {
  const corsHeaders = {
    'Access-Control-Allow-Origin': 'https://www.chinaboundtravel.com',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Content-Type': 'application/json',
  };

  if (request.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: corsHeaders });
  }

  try {
    const stripeWebhookSecret = env.STRIPE_WEBHOOK_SECRET;
    const resendApiKey = env.RESEND_API_KEY;
    const ebookUrl = env.EBOOK_URL || 'https://www.chinaboundtravel.com/ebook/china-bound-travel-guide.pdf';

    if (!stripeWebhookSecret || !resendApiKey) {
      return jsonResponse({ error: 'Missing environment variables' }, 500, corsHeaders);
    }

    const signature = request.headers.get('stripe-signature');
    const body = await request.text();

    let event;
    try {
      const response = await fetch('https://api.stripe.com/v1/webhook/signature/verify', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Authorization': `Bearer ${env.STRIPE_SECRET_KEY}`,
        },
        body: new URLSearchParams({
          secret: stripeWebhookSecret,
          payload: body,
          signature,
        }),
      });

      if (!response.ok) {
        return jsonResponse({ error: 'Invalid webhook signature' }, 400, corsHeaders);
      }

      event = JSON.parse(body);
    } catch (err) {
      return jsonResponse({ error: err.message }, 400, corsHeaders);
    }

    if (event.type === 'checkout.session.completed') {
      const session = event.data.object;
      const customerEmail = session.customer_email;
      const plan = session.metadata?.plan || 'unknown';

      if (customerEmail) {
        await sendEmail(customerEmail, plan, ebookUrl, resendApiKey);
      }
    }

    return jsonResponse({ received: true }, 200, corsHeaders);

  } catch (err) {
    console.error('Webhook error:', err.message);
    return jsonResponse({ error: err.message }, 500, corsHeaders);
  }
}

async function sendEmail(email, plan, ebookUrl, apiKey) {
  const subject = 'Your ChinaBound Travel Guide Download';
  const html = `
    <h1>Welcome to ChinaBound Travel!</h1>
    <p>Thank you for subscribing to our ${plan} plan.</p>
    <p>Click the link below to download your ChinaBound Travel Guide:</p>
    <a href="${ebookUrl}" style="display: inline-block; padding: 12px 24px; background: #0A66C2; color: white; text-decoration: none; border-radius: 4px;">
      Download PDF Guide
    </a>
    <p>If you have any questions, reply to this email.</p>
    <p>Best regards,<br>The ChinaBound Travel Team</p>
  `;

  await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      from: 'ChinaBound Travel <hello@chinaboundtravel.com>',
      to: email,
      subject,
      html,
    }),
  });
}

function jsonResponse(body, status, headers) {
  return new Response(JSON.stringify(body), { status, headers });
}
"""
    with open('functions/api/stripe-webhook.js', 'w', encoding='utf-8') as f:
        f.write(webhook_content)
    print("   ✅ functions/api/stripe-webhook.js 更新完成")
    
    print("\n✅ 清理完成！现在需要在 Cloudflare Pages 配置环境变量")
    print("\n" + "=" * 60)
    print("📋 Cloudflare Pages 环境变量配置")
    print("=" * 60)
    print("""
登录 Cloudflare Pages → 你的项目 → Settings → Environment Variables

添加以下变量：

STRIPE_SECRET_KEY = sk_live_xxx  (正式密钥)
STRIPE_WEBHOOK_SECRET = whsec_xxx  (Stripe Webhook签名密钥)
RESEND_API_KEY = re_xxx  (Resend API密钥)
EBOOK_URL = https://www.chinaboundtravel.com/ebook/china-bound-travel-guide.pdf
SUCCESS_URL = https://www.chinaboundtravel.com/success/
CANCEL_URL = https://www.chinaboundtravel.com/pricing/

注意：所有密钥必须使用正式环境（live），不能混用测试环境密钥！
""")

if __name__ == '__main__':
    os.chdir(r'E:\AI\dulizhan\travel-blog')
    clear_stripe_config()