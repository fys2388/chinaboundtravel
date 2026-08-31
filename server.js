require('dotenv').config();

const express = require('express');
const Stripe = require('stripe');
const { Resend } = require('resend');

const app = express();
const PORT = process.env.PORT || 3000;

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);
const resend = new Resend(process.env.RESEND_API_KEY);

app.use(express.json());
app.use(express.urlencoded({ extended: true }));

app.post('/api/stripe-webhook', async (req, res) => {
  const sig = req.headers['stripe-signature'];
  const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;
  
  let event;
  
  try {
    event = stripe.webhooks.constructEvent(req.rawBody, sig, webhookSecret);
  } catch (err) {
    return res.status(400).send(`Webhook Error: ${err.message}`);
  }
  
  switch (event.type) {
    case 'checkout.session.completed': {
      const session = event.data.object;
      const customerEmail = session.customer_email || session.customer_details?.email;
      const plan = session.metadata?.plan || 'Unknown';
      const amount = session.amount_total || 0;
      
      console.log(`Payment completed: ${customerEmail}, Plan: ${plan}, Amount: $${(amount / 100).toFixed(2)}`);
      
      if (customerEmail && process.env.RESEND_API_KEY) {
        try {
          const emailResponse = await resend.emails.send({
            from: 'Joran @ ChinaBound Travel <joran@chinaboundtravel.com>',
            to: customerEmail,
            subject: `Welcome to ChinaBound Travel! Your ${plan} Access is Ready`,
            html: `
              <!DOCTYPE html>
              <html lang="en">
              <head>
                <meta charset="UTF-8">
                <title>Welcome to ChinaBound Travel</title>
              </head>
              <body style="font-family: 'Inter', sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 8px; text-align: center;">
                  <h1 style="color: white; margin: 0;">Welcome to ChinaBound Travel!</h1>
                </div>
                <div style="padding: 20px;">
                  <p>Hi there,</p>
                  <p>Thank you for purchasing the <strong>${plan}</strong> plan!</p>
                  <p>Your payment of <strong>$${(amount / 100).toFixed(2)}</strong> has been processed successfully.</p>
                  <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="margin-top: 0;">📥 Download Your Travel Guide</h3>
                    <a href="${process.env.PDF_BASE_URL || 'https://chinaboundtravel.com/ebook/china-bound-travel-guide.pdf'}" style="display: inline-block; background: #667eea; color: white; padding: 12px 24px; border-radius: 4px; text-decoration: none; font-weight: 600;">Get Instant Access →</a>
                  </div>
                  <p>If you have any questions, reply to this email or contact us at joran@chinaboundtravel.com.</p>
                  <p>Happy travels!</p>
                  <p style="font-weight: 600;">— Joran</p>
                </div>
              </body>
              </html>
            `
          });
          
          console.log('Welcome email sent:', emailResponse);
        } catch (emailError) {
          console.error('Failed to send welcome email:', emailError);
        }
      }
      break;
    }
    case 'customer.subscription.created':
      console.log('Subscription created:', event.data.object);
      break;
    case 'customer.subscription.deleted':
      console.log('Subscription cancelled:', event.data.object);
      break;
    case 'invoice.payment_succeeded':
      console.log('Payment succeeded:', event.data.object);
      break;
    case 'invoice.payment_failed':
      console.log('Payment failed:', event.data.object);
      break;
    default:
      console.log(`Unhandled event type ${event.type}`);
  }
  
  res.json({ received: true });
});

app.get('/api/health', (req, res) => {
  res.json({ 
    status: 'ok',
    stripeConfigured: !!process.env.STRIPE_SECRET_KEY,
    resendConfigured: !!process.env.RESEND_API_KEY,
    pdfBaseUrl: process.env.PDF_BASE_URL
  });
});

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
  console.log('Environment variables loaded:');
  console.log(`- STRIPE_SECRET_KEY: ${process.env.STRIPE_SECRET_KEY ? '✅ Configured' : '❌ Not set'}`);
  console.log(`- STRIPE_WEBHOOK_SECRET: ${process.env.STRIPE_WEBHOOK_SECRET ? '✅ Configured' : '❌ Not set'}`);
  console.log(`- RESEND_API_KEY: ${process.env.RESEND_API_KEY ? '✅ Configured' : '❌ Not set'}`);
  console.log(`- PDF_BASE_URL: ${process.env.PDF_BASE_URL || '❌ Not set'}`);
});
