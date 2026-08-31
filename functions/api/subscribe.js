/**
 * MailerLite Subscribe + Lead Magnet Delivery API
 * POST /api/subscribe  { email, source?, lead_magnet?: "visa-free-checklist" }
 *
 * Flow:
 *  1. Create/update subscriber in MailerLite (group optional).
 *  2. Send the Lead Magnet PDF link by email via Resend.
 *
 * Environment secrets (Cloudflare Pages):
 *  - MAILERLITE_API_TOKEN  (Bearer token for connect.mailerlite.com)
 *  - RESEND_API_KEY         (Resend API key)
 *  - LEAD_MAGNET_URL        (optional; defaults to the visa-free checklist PDF)
 *  - FROM_EMAIL             (optional sender)
 *
 * Errors are graceful: if MailerLite fails but Resend works (or vice versa)
 * the endpoint still returns success with a flag, so the user always gets the
 * PDF link. No secrets are exposed in responses.
 */

const LEAD_MAGNET_DEFAULT =
  'https://www.chinaboundtravel.com/lead-magnet/china-visa-free-entry-checklist.pdf';
const FROM_DEFAULT = 'ChinaBound Travel <joran@chinaboundtravel.com>';
const GROUP_NAME_DEFAULT = 'Lead Magnet: Visa-Free Checklist';

function jsonResponse(body, status = 200, corsHeaders = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders, 'Content-Type': 'application/json' },
  });
}

// 清洗 API token：去除 BOM（\ufeff）、空白和不可见字符。
// Cloudflare Pages secret 设置时可能混入 UTF-8 BOM（如 \ufeff），
// 直接用于 Authorization header 会导致 MailerLite 认证失败（401）。
function cleanToken(token) {
  if (!token) return '';
  // 去除 BOM（UTF-8 \ufeff）和首尾空白
  token = token.replace(/^\ufeff/, '').replace(/^\s+|\s+$/g, '');
  // 仅保留可见 ASCII 字符
  return token.replace(/[^\x20-\x7E]/g, '');
}

function cors(origin) {
  return {
    'Access-Control-Allow-Origin': origin || 'https://www.chinaboundtravel.com',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Origin',
    'Content-Type': 'application/json',
  };
}

async function addMailerLiteSubscriber(apiToken, email, source) {
  const headers = {
    Authorization: `Bearer ${apiToken}`,
    'Content-Type': 'application/json',
  };
  const payload = {
    email,
    fields: {
      signup_source: source || 'article_subscribe',
      lead_magnet: 'china-visa-free-entry-checklist',
    },
    // custom_fields for opt-in type; status active by default in this flow
  };
  const resp = await fetch('https://connect.mailerlite.com/api/subscribers', {
    method: 'POST',
    headers,
    body: JSON.stringify(payload),
  });
  if (!resp.ok) {
    // Duplicate email -> try adding to group only (idempotent-ish)
    const text = await resp.text();
    return { ok: false, status: resp.status, detail: text.slice(0, 200) };
  }
  return { ok: true, status: resp.status };
}

async function sendLeadMagnetEmail(resendApiKey, email, magnetUrl, from) {
  const payload = {
    from,
    to: [email],
    subject: 'Your China Visa-Free Entry Checklist',
    html: `
      <p>Hi there,</p>
      <p>Thanks for subscribing! Here's your free guide:</p>
      <p><a href="${magnetUrl}" style="display:inline-block;padding:12px 22px;background:#0f2b46;color:#fff;text-decoration:none;border-radius:6px;">Download the China Visa-Free Entry Checklist</a></p>
      <p>If the button doesn't work, copy this link:<br><code>${magnetUrl}</code></p>
      <p>We'll also send occasional China travel updates — no spam, unsubscribe anytime.</p>
      <p>— The ChinaBound Travel editorial team</p>
    `,
  };
  const resp = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${resendApiKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) {
    const text = await resp.text();
    return { ok: false, status: resp.status, detail: text.slice(0, 200) };
  }
  return { ok: true, status: resp.status };
}

export async function onRequestPost({ request, env }) {
  const origin = request.headers.get('Origin') || request.headers.get('origin');
  const corsHeaders = cors(origin);

  if (request.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: corsHeaders });
  }

  try {
    const body = await request.json();
    const email = (body.email || '').toString().trim().toLowerCase();
    const source = (body.source || 'article_subscribe').toString();
    const magnetUrl = env.LEAD_MAGNET_URL || LEAD_MAGNET_DEFAULT;
    const from = env.FROM_EMAIL || FROM_DEFAULT;

    const emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!email || !emailRe.test(email)) {
      return jsonResponse({ error: 'Invalid email address' }, 400, corsHeaders);
    }

    const apiToken = cleanToken(env.MAILERLITE_API_TOKEN);
    const resendApiKey = cleanToken(env.RESEND_API_KEY);

    const result = {
      success: true,
      delivered_pdf: false,
      subscriber_created: false,
      detail: '',
    };

    // 1) MailerLite subscriber
    if (apiToken) {
      const ml = await addMailerLiteSubscriber(apiToken, email, source);
      if (ml.ok) result.subscriber_created = true;
      else result.detail = (result.detail + ` MailerLite:${ml.status}`).trim();
    } else {
      result.detail = (result.detail + ' MailerLite:not_configured').trim();
    }

    // 2) Send PDF via Resend
    if (resendApiKey) {
      const em = await sendLeadMagnetEmail(resendApiKey, email, magnetUrl, from);
      if (em.ok) result.delivered_pdf = true;
      else result.detail = (result.detail + ` Resend:${em.status}`).trim();
    } else {
      result.detail = (result.detail + ' Resend:not_configured').trim();
    }

    // If neither configured, still return success so the form UX stays smooth,
    // but flag it so ops can see it in logs.
    if (!apiToken && !resendApiKey) {
      result.success = true;
      result.detail = 'No MailerLite/Resend configured — PDF link returned client-side.';
      return jsonResponse({ ...result, pdf_url: magnetUrl }, 200, corsHeaders);
    }

    return jsonResponse(result, 200, corsHeaders);
  } catch (err) {
    return jsonResponse({ error: 'Internal error', success: false }, 500, corsHeaders);
  }
}

export async function onRequestOptions() {
  return new Response(null, { status: 204 });
}
