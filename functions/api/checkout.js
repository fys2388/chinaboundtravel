/**
 * Stripe Checkout Session API - ChinaBound Travel
 * POST /api/checkout { plan: "monthly" | "annual" | "onetime" }
 *
 * Env vars (Cloudflare Pages → Settings → Environment Variables):
 *   STRIPE_SECRET_KEY      = sk_live_xxx
 *   SUCCESS_URL            = https://chinaboundtravel.com/success/
 *   CANCEL_URL             = https://chinaboundtravel.com/pricing/
 */

const allowedOrigin = 'https://chinaboundtravel.com';

export async function onRequestPost({ request, env }) {
  const corsHeaders = {
    'Access-Control-Allow-Origin': allowedOrigin,
    'Content-Type': 'application/json',
  };

  if (request.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: corsHeaders });
  }

  try {
    const { plan } = await request.json();

    const PLANS = {
      monthly: {
        priceId: 'price_1TbjHO9rCn6b9ZnBDg6wfaLJ',   // $9.99/month
        coupon: 'FIRSTMONTH1',                          // first month $1.09
        name: 'Monthly Radar',
        mode: 'subscription',
      },
      annual: {
        priceId: 'price_1TaVSM9rCn6b9ZnBurUqHyLw',    // $49.99/year
        coupon: null,
        name: 'Annual Elite Pass',
        mode: 'subscription',
      },
      onetime: {
        priceId: 'price_1TaVOT9rCn6b9ZnBYZFq2dHx',    // $14.99 once
        coupon: null,
        name: 'One-Time Buyout',
        mode: 'payment',
      },
    };

    const planConfig = PLANS[plan];
    if (!planConfig) {
      return jsonResponse({ error: 'Invalid plan. Use: monthly, annual, or onetime' }, 400, corsHeaders);
    }

    const successUrl = env.SUCCESS_URL || 'https://www.chinaboundtravel.com/success/';
    const cancelUrl = env.CANCEL_URL || 'https://www.chinaboundtravel.com/pricing/';
    const stripeKey = env.STRIPE_SECRET_KEY || '***REMOVED***';

    // Build session payload
    const sessionPayload = {
      mode: planConfig.mode,
      success_url: `${successUrl}?session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: cancelUrl,
      line_items: [{ price: planConfig.priceId, quantity: 1 }],
      metadata: {
        plan,
        source: 'chinaboundtravel_website',
      },
      payment_method_types: ['card'],
      allow_promotion_codes: true,
      billing_address_collection: 'auto',
    };

    // Apply first-month coupon only for monthly plan
    if (planConfig.coupon) {
      sessionPayload.discounts = [{ coupon: planConfig.coupon }];
    }

    const Stripe = (await import('stripe')).default;
    const stripe = new Stripe(stripeKey);

    const session = await stripe.checkout.sessions.create(sessionPayload);

    return jsonResponse({ url: session.url }, 200, corsHeaders);

  } catch (err) {
    console.error('Checkout error:', err.message);
    return jsonResponse({ error: err.message }, 500, corsHeaders);
  }
}

function jsonResponse(body, status, headers) {
  return new Response(JSON.stringify(body), { status, headers });
}
