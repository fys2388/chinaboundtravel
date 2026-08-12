/**
 * Stripe Webhook Handler - PRODUCTION
 * POST /api/stripe-webhook
 *
 * P0-4 changes:
 *  - Signature verification now uses local HMAC-SHA256 via WebCrypto
 *    (previously called a non-existent Stripe endpoint which always failed).
 *  - Idempotency: repeated deliveries of the same event are safe.
 *    Layer 1: optional Cloudflare KV binding PROCESSED_EVENTS (feature-detected).
 *    Layer 2: Resend `Idempotency-Key` derived from event.id (server-side dedup).
 *  - Business logic unchanged: checkout.session.completed -> send ebook email.
 */

const EBOK_URL_DEFAULT = 'https://www.chinaboundtravel.com/ebook/china-bound-travel-guide.pdf';
const SIGNATURE_TOLERANCE_SECONDS = 300;

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
    const ebookUrl = env.EBOOK_URL || EBOK_URL_DEFAULT;

    if (!stripeWebhookSecret || !resendApiKey) {
      return jsonResponse({ error: 'Missing environment variables' }, 500, corsHeaders);
    }

    const signature = request.headers.get('stripe-signature');
    const body = await request.text();

    // Verify signature locally with HMAC-SHA256 (Stripe webhook scheme: t=<ts>,v1=<hex>)
    const valid = await verifyStripeSignature(body, signature, stripeWebhookSecret);
    if (!valid) {
      return jsonResponse({ error: 'Invalid webhook signature' }, 400, corsHeaders);
    }

    const event = JSON.parse(body);
    const eventId = event.id || '';
    const eventType = event.type || '';

    // Idempotency layer 1: KV-based processed-event tracking (optional binding).
    const kv = env.PROCESSED_EVENTS || null;
    if (kv && eventId) {
      const seen = await kv.get(`evt:${eventId}`).catch(() => null);
      if (seen) {
        return jsonResponse({ received: true, duplicate: true }, 200, corsHeaders);
      }
    }

    if (eventType === 'checkout.session.completed') {
      const session = event.data.object;
      const customerEmail = session.customer_email;
      const plan = session.metadata?.plan || 'unknown';

      if (customerEmail) {
        // Idempotency layer 2: deterministic idempotency key -> Resend dedupes
        // repeated sends of the same logical email even without KV.
        await sendEmail(customerEmail, plan, ebookUrl, resendApiKey, eventId);
      }
    }

    // Mark processed only after the core action succeeded, so a failed send can retry.
    if (kv && eventId) {
      await kv.put(
        `evt:${eventId}`,
        JSON.stringify({ id: eventId, type: eventType, processed_at: new Date().toISOString() }),
        { expirationTtl: 60 * 60 * 24 * 7 }
      ).catch(() => {});
    }

    return jsonResponse({ received: true }, 200, corsHeaders);

  } catch (err) {
    console.error('Webhook error:', err.message);
    return jsonResponse({ error: err.message }, 500, corsHeaders);
  }
}

/**
 * Verify a Stripe webhook signature using WebCrypto (HMAC-SHA256).
 * Header format: t=<timestamp>,v1=<hex signature>
 * Expected HMAC input: `${timestamp}.${payload}` keyed by the webhook secret.
 */
export async function verifyStripeSignature(payload, signatureHeader, secret) {
  if (!signatureHeader) return false;
  const parts = {};
  for (const item of signatureHeader.split(',')) {
    const [key, value] = item.split('=');
    if (key && value) parts[key.trim()] = value.trim();
  }
  const timestamp = parts['t'];
  const providedSignature = parts['v1'];
  if (!timestamp || !providedSignature) return false;

  // Replay protection: reject signatures older than the tolerance window.
  const now = Math.floor(Date.now() / 1000);
  if (Math.abs(now - parseInt(timestamp, 10)) > SIGNATURE_TOLERANCE_SECONDS) return false;

  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    'raw',
    encoder.encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );
  const signatureBuffer = await crypto.subtle.sign(
    'HMAC',
    key,
    encoder.encode(`${timestamp}.${payload}`)
  );

  const expected = [...new Uint8Array(signatureBuffer)].map((b) => b.toString(16).padStart(2, '0')).join('');
  return constantTimeEqual(expected, providedSignature.toLowerCase());
}

function constantTimeEqual(a, b) {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) {
    diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return diff === 0;
}

async function sendEmail(email, plan, ebookUrl, apiKey, eventId) {
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

  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${apiKey}`,
  };
  if (eventId) {
    // Deterministic idempotency key: duplicate webhook deliveries cannot send the email twice.
    headers['Idempotency-Key'] = `stripe-${eventId}`;
  }

  await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers,
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