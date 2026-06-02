/**
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
