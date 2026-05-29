/**
 * Stripe Webhook Handler - ChinaBound Travel
 * Receives checkout.session.completed → sends ebook via MailerLite
 *
 * Env vars (set in Cloudflare Pages → Settings → Environment Variables):
 *   STRIPE_WEBHOOK_SECRET   = whsec_xxx
 *   MAILERLITE_API_KEY     = MailerLite REST API key
 *   Ebook PDF URL (in email body, no secret needed):
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
    let event;
    try {
      const parts = signature.split(',');
      const sigParts = {};
      for (const part of parts) {
        const [k, v] = part.split('=');
        sigParts[k.trim()] = v.trim();
      }
      const timestamp = sigParts['t'];
      const expectedSig = sigParts['v1'];

      // Manual HMAC verification (Cloudflare Workers compatible)
      const crypto = await import('crypto');
      const signedPayload = `${timestamp}.${rawBody}`;
      const computedSig = crypto
        .createHmac('sha256', env.STRIPE_WEBHOOK_SECRET)
        .update(signedPayload, 'utf8')
        .digest('hex');

      if (computedSig !== expectedSig) {
        // Try without hashing (in case secret is already the raw secret)
        if (expectedSig !== env.STRIPE_WEBHOOK_SECRET) {
          return jsonResponse({ error: 'Invalid signature' }, 400, corsHeaders);
        }
      }

      event = JSON.parse(rawBody);
    } catch (verifyErr) {
      console.error('Stripe signature verification failed:', verifyErr.message);
      return jsonResponse({ error: 'Signature verification failed' }, 400, corsHeaders);
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

    // 4. Add subscriber to MailerLite
    const mlApiKey = env.MAILERLITE_API_KEY;
    const mlAccountId = '2370480'; // ChinaBound MailerLite account

    // Find or create the subscriber
    let subscriberId = null;

    // Try to find existing subscriber
    const searchRes = await fetch(
      `https://api.mailerlite.com/api/v2/subscribers?search=${encodeURIComponent(customerEmail)}`,
      {
        headers: {
          'Authorization': `Bearer ${mlApiKey}`,
          'Content-Type': 'application/json',
        },
      }
    );

    if (searchRes.ok) {
      const searchData = await searchRes.json();
      const existing = searchData.data?.find(s => s.email === customerEmail);
      if (existing) {
        subscriberId = existing.id;
      }
    }

    // Create or update subscriber
    const subscriberPayload = {
      email: customerEmail,
      fields: {
        name: session.customer_details?.name || '',
      },
      tags: ['ebook-buyer', 'annual-pass'],
      status: 'active',
    };

    let mlRes;
    if (subscriberId) {
      // Update existing
      mlRes = await fetch(`https://api.mailerlite.com/api/v2/subscribers/${subscriberId}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${mlApiKey}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(subscriberPayload),
      });
    } else {
      // Create new
      mlRes = await fetch('https://api.mailerlite.com/api/v2/subscribers', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${mlApiKey}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(subscriberPayload),
      });
    }

    if (!mlRes.ok) {
      const mlErr = await mlRes.text();
      console.error('MailerLite error:', mlErr);
      // Don't fail the webhook - email might already exist, that's OK
      return jsonResponse({
        received: true,
        warning: 'MailerLite subscriber creation failed',
        detail: mlErr,
      }, 200, corsHeaders);
    }

    const mlData = await mlRes.json();

    // 5. Send transactional email with PDF download link
    const ebookUrl = env.EBOOK_URL || 'https://chinaboundtravel.com/ebook/china-bound-travel-guide.pdf';

    const emailPayload = {
      to: [{
        email: customerEmail,
        name: session.customer_details?.name || customerEmail,
      }],
      subject: 'Your China Bound Travel Guide – Download Now 🎋',
      html: buildWelcomeEmail(customerEmail, ebookUrl),
      text: buildWelcomeEmailText(customerEmail, ebookUrl),
      from: {
        email: 'hello@chinaboundtravel.com',
        name: 'Joran @ ChinaBound Travel',
      },
      inline_css: false,
    };

    const sendRes = await fetch('https://api.mailerlite.com/api/v2/send', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${mlApiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(emailPayload),
    });

    if (!sendRes.ok) {
      const sendErr = await sendRes.text();
      console.error('MailerLite send error:', sendErr);
      return jsonResponse({
        received: true,
        warning: 'Email send failed',
        detail: sendErr,
      }, 200, corsHeaders);
    }

    return jsonResponse({
      success: true,
      email: customerEmail,
      ml_subscriber_id: mlData.id || subscriberId,
    }, 200, corsHeaders);

  } catch (err) {
    console.error('Webhook error:', err);
    return jsonResponse({ error: 'Internal server error', detail: err.message }, 500, corsHeaders);
  }
}

function jsonResponse(body, status, headers) {
  return new Response(JSON.stringify(body), { status, headers });
}

function buildWelcomeEmail(email, ebookUrl) {
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
              <p style="margin:8px 0 0;font-size:14px;color:rgba(255,255,255,0.75);">Your Annual Digital Pass · Valid for 1 Year</p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="background:#ffffff;padding:32px;">
              <p style="margin:0 0 20px;font-size:16px;color:#333;line-height:1.6;">
                Hey there 👋
              </p>
              <p style="margin:0 0 20px;font-size:16px;color:#333;line-height:1.6;">
                Thanks for grabbing the <strong>China Bound Travel Guide – Annual Pass</strong>! You've got full access for the next 12 months.
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

              <p style="margin:0 0 20px;font-size:16px;color:#333;line-height:1.6;">
                And if you haven't yet, subscribe to the newsletter for fresh China travel intel every month:
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
                You're receiving this because you purchased the Annual Pass.
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

function buildWelcomeEmailText(email, ebookUrl) {
  return `Hey there!

Thanks for grabbing the China Bound Travel Guide – Annual Pass! You've got full access for the next 12 months.

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
