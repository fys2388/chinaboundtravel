require('dotenv').config();

const Stripe = require('stripe');
const { Resend } = require('resend');

console.log('=== Environment Variable Test ===');
console.log('');

console.log('1. Loading environment variables...');
console.log(`   - STRIPE_SECRET_KEY: ${process.env.STRIPE_SECRET_KEY ? '✅ Loaded' : '❌ Not set'}`);
console.log(`   - STRIPE_WEBHOOK_SECRET: ${process.env.STRIPE_WEBHOOK_SECRET ? '✅ Loaded' : '❌ Not set'}`);
console.log(`   - RESEND_API_KEY: ${process.env.RESEND_API_KEY ? '✅ Loaded' : '❌ Not set'}`);
console.log(`   - PDF_BASE_URL: ${process.env.PDF_BASE_URL || '❌ Not set'}`);
console.log('');

console.log('2. Initializing Stripe instance...');
try {
  const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);
  console.log(`   ✅ Stripe instance created successfully`);
  console.log(`   - API Version: ${stripe.defaultApiVersion}`);
} catch (error) {
  console.log(`   ❌ Failed to create Stripe instance: ${error.message}`);
}
console.log('');

console.log('3. Initializing Resend instance...');
try {
  const resend = new Resend(process.env.RESEND_API_KEY);
  console.log('   ✅ Resend instance created successfully');
} catch (error) {
  console.log(`   ❌ Failed to create Resend instance: ${error.message}`);
}
console.log('');

console.log('4. PDF Base URL verification...');
if (process.env.PDF_BASE_URL) {
  console.log(`   ✅ PDF_BASE_URL: ${process.env.PDF_BASE_URL}`);
} else {
  console.log('   ⚠️ PDF_BASE_URL not set, using default: https://chinaboundtravel.com/ebook/china-bound-travel-guide.pdf');
}
console.log('');

console.log('=== Test Complete ===');
console.log('');
console.log('Next steps:');
console.log('1. Fill in the values in .env file');
console.log('2. Run: npm install');
console.log('3. Run: npm start');
console.log('4. Configure Stripe Webhook to point to: http://localhost:3000/api/stripe-webhook');
