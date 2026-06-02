/**
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

    let successUrlEncoded = encodeURIComponent(successUrl + '?session_id={CHECKOUT_SESSION_ID}');
    let cancelUrlEncoded = encodeURIComponent(cancelUrl);
    let formData = `mode=${planConfig.mode}&success_url=${successUrlEncoded}&cancel_url=${cancelUrlEncoded}&line_items[0][price]=${planConfig.priceId}&line_items[0][quantity]=1&metadata[plan]=${plan}&metadata[source]=chinaboundtravel_website&payment_method_types[0]=card&billing_address_collection=auto`;
    
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
