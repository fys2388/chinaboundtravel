/**
 * Stripe Checkout Session API - PRODUCTION
 * POST /api/checkout { plan: "monthly" | "annual" | "onetime" }
 *
 * P0-FIX (2026-09-07):
 *  - Invalid JSON body now returns 400 instead of 500.
 *  - Invalid plan returns 400 (already correct).
 *  - Error messages no longer expose internal JSON parse details.
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
    // P0-FIX v2: 先读 text 再手动 JSON.parse，确保解析错误100%被捕获
    let body;
    try {
      const rawText = await request.text();
      body = JSON.parse(rawText);
    } catch (jsonErr) {
      return jsonResponse({ error: 'Invalid JSON body' }, 400, corsHeaders);
    }
    const { plan } = body;

    const PLANS = {
      monthly: { priceId: 'price_1TbjHO9rCn6b9ZnBDg6wfaLJ', mode: 'subscription', coupon: 'FIRSTMONTH1' },
      annual: { priceId: 'price_1TaVSM9rCn6b9ZnBurUqHyLw', mode: 'subscription' },
      onetime: { priceId: 'price_1TaVOT9rCn6b9ZnBYZFq2dHx', mode: 'payment' },
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

    const successUrlEncoded = encodeURIComponent(successUrl + '?session_id={CHECKOUT_SESSION_ID}');
    const cancelUrlEncoded = encodeURIComponent(cancelUrl);
    const baseForm = `mode=${planConfig.mode}&success_url=${successUrlEncoded}&cancel_url=${cancelUrlEncoded}&line_items[0][price]=${planConfig.priceId}&line_items[0][quantity]=1&metadata[plan]=${plan}&metadata[source]=chinaboundtravel_website&payment_method_types[0]=card&billing_address_collection=auto`;

    async function createSession(body) {
      const resp = await fetch('https://api.stripe.com/v1/checkout/sessions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Authorization': `Bearer ${stripeKey}`,
        },
        body,
      });
      const json = await resp.json();
      return { status: resp.status, ok: resp.ok, json };
    }

    let usedCoupon = false;
    let result = await createSession(
      (usedCoupon = Boolean(planConfig.coupon))
        ? baseForm + `&discounts[0][coupon]=${planConfig.coupon}`
        : baseForm
    );

    // 折扣码可能尚未在 Stripe 后台创建（FIRSTMONTH1 当前不存在）。
    // Stripe 因折扣码拒绝请求时，去掉折扣码重试一次：今天按原价成交，
    // 折扣码创建后无需改代码即自动带上折扣。
    // 只处理折扣相关错误；key 无效、price 不存在等错误原样返回，不掩盖真实故障。
    if (!result.ok && usedCoupon && /coupon|discount/i.test(JSON.stringify(result.json.error || {}))) {
      console.warn(`Checkout: coupon ${planConfig.coupon} rejected by Stripe (${result.status}), retrying without discount`);
      usedCoupon = false;
      result = await createSession(baseForm);
    }

    if (!result.ok) {
      return jsonResponse({ error: result.json.error?.message || 'Stripe API error' }, result.status, corsHeaders);
    }

    return jsonResponse({ url: result.json.url, coupon_applied: usedCoupon }, 200, corsHeaders);

  } catch (err) {
    console.error('Checkout error:', err.message);
    // P0-FIX: 不向客户端暴露内部错误细节
    return jsonResponse({ error: 'Internal server error' }, 500, corsHeaders);
  }
}

function jsonResponse(body, status, headers) {
  return new Response(JSON.stringify(body), { status, headers });
}

// P0-FIX: 处理 CORS OPTIONS 预检请求
export async function onRequestOptions({ request }) {
  const origin = request.headers.get('Origin') || request.headers.get('origin');
  return new Response(null, {
    status: 204,
    headers: {
      'Access-Control-Allow-Origin': origin || 'https://www.chinaboundtravel.com',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Origin',
    },
  });
}
