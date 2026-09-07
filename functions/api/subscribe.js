/**
 * MailerLite Subscribe + Lead Magnet Delivery API
 * POST /api/subscribe  { email, source?, lead_magnet?: "visa-free-checklist" }
 *
 * P0-FIX (2026-09-07):
 *  - Invalid JSON body now returns 400 instead of 500.
 *  - Invalid email returns 400 (was being intercepted by outer catch).
 *  - Error messages no longer expose internal details.
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
function cleanToken(token) {
  if (!token) return '';
  token = token.replace(/^\ufeff/, '').replace(/^\s+|\s+$/g, '');
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
  };
  const resp = await fetch('https://connect.mailerlite.com/api/subscribers', {
    method: 'POST',
    headers,
    body: JSON.stringify(payload),
  });
  if (!resp.ok) {
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

  // P0-FIX v2: 先读 text 再手动 JSON.parse，确保解析错误100%被捕获
  let body;
  try {
    const rawText = await request.text();
    body = JSON.parse(rawText);
  } catch (jsonErr) {
    return jsonResponse({ error: 'Invalid JSON body', success: false }, 400, corsHeaders);
  }

  try {
    const email = (body.email || '').toString().trim().toLowerCase();
    const source = (body.source || 'article_subscribe').toString();
    const magnetUrl = env.LEAD_MAGNET_URL || LEAD_MAGNET_DEFAULT;
    const from = env.FROM_EMAIL || FROM_DEFAULT;

    const emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!email || !emailRe.test(email)) {
      // P0-FIX: 确保无效 email 返回 400，不被外层 catch 拦截
      return jsonResponse({ error: 'Invalid email address', success: false }, 400, corsHeaders);
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

    if (!apiToken && !resendApiKey) {
      result.success = true;
      result.detail = 'No MailerLite/Resend configured — PDF link returned client-side.';
      return jsonResponse({ ...result, pdf_url: magnetUrl }, 200, corsHeaders);
    }

    return jsonResponse(result, 200, corsHeaders);
  } catch (err) {
    console.error('Subscribe error:', err.message);
    // P0-FIX: 不向客户端暴露内部错误细节
    return jsonResponse({ error: 'Internal server error', success: false }, 500, corsHeaders);
  }
}

export async function onRequestOptions() {
  return new Response(null, { status: 204 });
}
