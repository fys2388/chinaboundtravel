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

/**
 * P0-6 (2026-09-21): sendEmail 必须严格校验 Resend HTTP 响应。
 *
 * 历史行为（本 bug 的根因）：只 await fetch()，从不读 res.ok / res.status。
 * 后果：Stripe payment 成功 → webhook 收到 → Resend 邮件接口返回 500
 * → 代码仍然往下走 → webhook 返回 200 给 Stripe → Stripe 认为已处理，
 * 不再重试 → 付费用户永远收不到电子书下载链接。
 *
 * 修复：
 *  - 3 次指数退避重试（300ms / 1s），每次携带同一 Idempotency-Key，
 *    让 Resend 自己去重，不会造成重复邮件。
 *  - 任一尝试返回 2xx 立即返回（成功）。
 *  - 全部尝试失败 / 抛错 → 抛 Error 到上层 catch → webhook 返回 500
 *    → Stripe 自动重试整个 webhook delivery。KV 里只在成功后写入，
 *    所以重试不会被误判成 duplicate。
 *  - 每次非 2xx 都 console.error，方便 Cloudflare Workers logs 观测。
 */
const RESEND_MAX_ATTEMPTS = 3;
const RESEND_BACKOFF_MS = [300, 1000]; // 两次重试之间的等待
const RESEND_TIMEOUT_MS = 10000;

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
    // Deterministic idempotency key: 同一 event 的多次尝试 / 多次 webhook
    // delivery 共享同一 key，Resend 侧天然去重，不会造成重复邮件。
    headers['Idempotency-Key'] = `stripe-${eventId}`;
  }

  let lastError = null;
  for (let attempt = 1; attempt <= RESEND_MAX_ATTEMPTS; attempt++) {
    let res;
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), RESEND_TIMEOUT_MS);
      try {
        res = await fetch('https://api.resend.com/emails', {
          method: 'POST',
          headers,
          body: JSON.stringify({
            from: 'ChinaBound Travel <joran@chinaboundtravel.com>',
            to: email,
            subject,
            html,
          }),
          signal: controller.signal,
        });
      } finally {
        clearTimeout(timer);
      }
    } catch (netErr) {
      // Network / abort error: 网络层失败，可重试。
      lastError = netErr;
      console.error(
        `Resend email network error (attempt ${attempt}/${RESEND_MAX_ATTEMPTS}) for ${email}: ${netErr.message}`
      );
      if (attempt < RESEND_MAX_ATTEMPTS) {
        await sleep(RESEND_BACKOFF_MS[attempt - 1]);
        continue;
      }
      break;
    }

    // 严格校验 HTTP 响应：非 2xx 视为失败。
    if (res.ok && res.status >= 200 && res.status < 300) {
      return { ok: true, status: res.status, attempt };
    }

    // 客户端错误（4xx，除 429）一般是永久性：邮箱格式非法 / API key 无效等，
    // 重试也不会好；直接抛错让 Stripe 重试整个 webhook 并触发人工排查。
    let bodyText = '';
    try { bodyText = (await res.text()).slice(0, 500); } catch (_) { /* ignore */ }

    console.error(
      `Resend email HTTP ${res.status} (attempt ${attempt}/${RESEND_MAX_ATTEMPTS}) for ${email}: ${bodyText}`
    );
    lastError = new Error(`Resend returned HTTP ${res.status} for ${email}: ${bodyText}`);

    // 429 限流、5xx 服务器错误 → 可重试；其他 4xx → 重试无意义，直接抛错。
    const retryable = res.status === 429 || res.status >= 500;
    if (!retryable || attempt >= RESEND_MAX_ATTEMPTS) {
      break;
    }
    await sleep(RESEND_BACKOFF_MS[attempt - 1]);
  }

  // 全部尝试失败：抛错让上层 catch 把 webhook 变成 5xx，Stripe 会重试整个 delivery。
  throw lastError instanceof Error
    ? lastError
    : new Error(`Resend email failed for ${email}: ${lastError}`);
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function jsonResponse(body, status, headers) {
  return new Response(JSON.stringify(body), { status, headers });
}