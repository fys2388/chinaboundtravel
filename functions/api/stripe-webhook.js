/**
 * Stripe Webhook Handler - ChinaBound Travel
 * Receives checkout.session.completed → sends ebook via Resend
 *
 * Env vars (set in Cloudflare Pages → Settings → Environment Variables):
 *   STRIPE_WEBHOOK_SECRET   = whsec_xxx
 *   RESEND_API_KEY          = re_xxx (from resend.com)
 *   STRIPE_SECRET_KEY       = sk_live_xxx
 *   EBOOK_URL              = https://chinaboundtravel.com/ebook/china-bound-travel-guide.pdf
 */

const allowedOrigin = 'https://chinaboundtravel.com';

export async function onRequestPost({ request, env }) {
  // CORS preflight
  if (request.method === 'OPTIONS') {
    return new Response(null, {
      status: 204,
      headers: {
        'Access-Control-Allow-Origin': allowedOrigin,
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, stripe-signature',
        'Access-Control-Max-Age': '86400',
      },
    });
  }

  const corsHeaders = {
    'Access-Control-Allow-Origin': allowedOrigin,
    'Content-Type': 'application/json',
  };

  try {
    // 1. Read raw body for signature verification
    const rawBody = await request.text();
    const signature = request.headers.get('stripe-signature');

    if (!signature) {
      return jsonResponse({ error: 'Missing stripe-signature header' }, 400, corsHeaders);
    }

    // 2. Verify Stripe signature
    const Stripe = (await import('stripe')).default;
    const stripe = new Stripe(env.STRIPE_SECRET_KEY);
    
    let event;
    try {
      event = stripe.webhooks.constructEvent(
        rawBody,
        signature,
        env.STRIPE_WEBHOOK_SECRET
      );
    } catch (verifyErr) {
      console.error('Stripe signature verification failed:', verifyErr.message);
      return jsonResponse({ error: 'Signature verification failed: ' + verifyErr.message }, 400, corsHeaders);
    }

    // 3. Handle checkout.session.completed
    if (event.type !== 'checkout.session.completed') {
      return jsonResponse({ received: true, skipped: `Event type ${event.type} not handled` }, 200, corsHeaders);
    }

    const session = event.data.object;
    const customerEmail = session.customer_details?.email;

    if (!customerEmail) {
      return jsonResponse({ error: 'No customer email in session' }, 400, corsHeaders);
    }

    // 4. Send transactional email with PDF download link via Resend
    const ebookUrl = env.EBOOK_URL || 'https://chinaboundtravel.com/ebook/china-bound-travel-guide.pdf';
    const plan = session.metadata?.plan || 'unknown';

    const { Resend } = await import('resend');
    const resend = new Resend(env.RESEND_API_KEY);

    const sendRes = await resend.emails.send({
      from: 'Joran @ ChinaBound Travel <hello@chinaboundtravel.com>',
      to: customerEmail,
      subject: 'Your China Bound Travel Guide – Download Now 🎋',
      html: buildWelcomeEmail(customerEmail, ebookUrl, plan),
      text: buildWelcomeEmailText(customerEmail, ebookUrl, plan),
    });

    if (sendRes.error) {
      console.error('Resend email error:', sendRes.error);
      return jsonResponse({
        received: true,
        warning: 'Email send failed',
        detail: sendRes.error.message,
      }, 200, corsHeaders);
    }

    return jsonResponse({
      success: true,
      email: customerEmail,
      message_id: sendRes.data.id,
      plan: plan,
    }, 200, corsHeaders);

  } catch (err) {
    console.error('Webhook error:', err);
    return jsonResponse({ error: 'Internal server error', detail: err.message }, 500, corsHeaders);
  }
}

function jsonResponse(body, status, headers) {
  return new Response(JSON.stringify(body), { status, headers });
}

function buildWelcomeEmail(email, ebookUrl, plan) {
  const planName = {
    monthly: 'Monthly Radar',
    annual: 'Annual Elite Pass',
    onetime: 'One-Time Buyout',
  }[plan] || plan;

  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>China Bound Travel Guide</title>
</head>
<body style="margin:0;padding:0;background:#f6f8fa;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f6f8fa;">
    <tr>
      <td align="center" style="padding:40px 16px;">
        <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,#1a3a5c,#2d5a8a);border-radius:12px 12px 0 0;padding:32px 32px 24px;text-align:center;">
              <p style="margin:0 0 8px;font-size:36px;">📍</p>
              <h1 style="margin:0;font-size:24px;font-weight:800;color:#ffffff;letter-spacing:-0.02em;">China Bound Travel Guide</h1>
              <p style="margin:8px 0 0;font-size:14px;color:rgba(255,255,255,0.75);">Your ${planName} · Access Granted</p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="background:#ffffff;padding:32px;">
              <p style="margin:0 0 20px;font-size:16px;color:#333;line-height:1.6;">
                Hey there 👋
              </p>
              <p style="margin:0 0 20px;font-size:16px;color:#333;line-height:1.6;">
                Thanks for grabbing the <strong>China Bound Travel Guide</strong>! Here's your instant download link:
              </p>

              <!-- Ebook Download Card -->
              <table width="100%" cellpadding="0" cellspacing="0" style="background:linear-gradient(135deg,#1a3a5c,#2d5a8a);border-radius:10px;margin:24px 0;">
                <tr>
                  <td style="padding:24px;text-align:center;">
                    <p style="margin:0 0 8px;font-size:32px;">📖</p>
                    <h2 style="margin:0 0 8px;font-size:18px;font-weight:700;color:#ffffff;">Your Ultimate China Travel Bible</h2>
                    <p style="margin:0 0 20px;font-size:13px;color:rgba(255,255,255,0.7);">Visa rules · Internet access · Payment apps · Transport · City guides</p>
                    <a href="${ebookUrl}"
                       style="display:inline-block;background:#FF6B35;color:#ffffff;font-weight:700;font-size:15px;padding:14px 32px;border-radius:8px;text-decoration:none;box-shadow:0 4px 14px rgba(255,107,53,0.35);">
                      Download PDF →
                    </a>
                    <p style="margin:12px 0 0;font-size:11px;color:rgba(255,255,255,0.5);">File size: ~8MB · PDF format · Works on any device</p>
                  </td>
                </tr>
              </table>

              <p style="margin:0 0 20px;font-size:16px;color:#333;line-height:1.6;">
                Save this email — you'll need it to re-download if you switch devices.
              </p>

              <p style="margin:0;font-size:14px;color:#555;line-height:1.6;">
                Safe travels,<br>
                <strong>Joran</strong><br>
                <span style="font-size:12px;color:#888;">California native, Chengdu son-in-law, 6 years of China travel mistakes</span>
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background:#f0f4f8;border-radius:0 0 12px 12px;padding:20px 32px;text-align:center;border-top:1px solid #e0e8f0;">
              <p style="margin:0;font-size:12px;color:#888;">
                © 2026 ChinaBound Travel · <a href="https://chinaboundtravel.com" style="color:#3A6EA5;">chinaboundtravel.com</a><br>
                You're receiving this because you purchased the ${planName}.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>`;
}

function buildWelcomeEmailText(email, ebookUrl, plan) {
  const planName = {
    monthly: 'Monthly Radar',
    annual: 'Annual Elite Pass',
    onetime: 'One-Time Buyout',
  }[plan] || plan;

  return `Hey there!

Thanks for grabbing the China Bound Travel Guide - ${planName}!

📖 Download your PDF here:
${ebookUrl}

Save this email — you'll need it to re-download if you switch devices.

Safe travels,
Joran
California native, Chengdu son-in-law
chinaboundtravel.com

---
© 2026 ChinaBound Travel`;
}