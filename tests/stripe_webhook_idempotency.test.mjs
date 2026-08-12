/**
 * P0-4: Stripe webhook idempotency tests.
 *
 * Verifies that repeated deliveries of the same webhook event never repeat the
 * core business action (sending the fulfillment email), and that signature
 * verification actually validates the Stripe HMAC scheme.
 *
 * Run: node --test tests/stripe_webhook_idempotency.test.mjs
 */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createHmac, randomUUID } from 'node:crypto';
import { verifyStripeSignature, onRequestPost } from '../functions/api/stripe-webhook.js';

const SECRET = '***REMOVED***';

function sign(payload, ts = Math.floor(Date.now() / 1000)) {
  const sig = createHmac('sha256', SECRET).update(`${ts}.${payload}`).digest('hex');
  return { header: `t=${ts},v1=${sig}`, ts };
}

function makeEvent(overrides = {}) {
  return {
    id: `evt_test_${randomUUID().replace(/-/g, '').slice(0, 16)}`,
    type: 'checkout.session.completed',
    data: { object: { customer_email: 'buyer@example.com', metadata: { plan: 'monthly' } } },
    ...overrides,
  };
}

function mockKv() {
  const store = new Map();
  return {
    async get(key) { return store.has(key) ? store.get(key) : null; },
    async put(key, value) { store.set(key, value); },
    _store: store,
  };
}

function makeRequest(payload, signatureHeader) {
  return {
    method: 'POST',
    headers: { get: (name) => (name.toLowerCase() === 'stripe-signature' ? signatureHeader : null) },
    text: async () => payload,
  };
}

function makeEnv(kv) {
  return {
    STRIPE_WEBHOOK_SECRET: SECRET,
    RESEND_API_KEY: 're_test_key',
    PROCESSED_EVENTS: kv,
  };
}

function makeFetchRecorder() {
  const calls = [];
  globalThis.fetch = async (url, opts) => {
    calls.push({ url, opts });
    return { ok: true, status: 200 };
  };
  return calls;
}

test('valid signature passes verification', async () => {
  const payload = JSON.stringify(makeEvent());
  const { header } = sign(payload);
  assert.equal(await verifyStripeSignature(payload, header, SECRET), true);
});

test('tampered payload fails verification', async () => {
  const payload = JSON.stringify(makeEvent());
  const { header } = sign(payload);
  const tampered = payload.replace('buyer@example.com', 'attacker@example.com');
  assert.equal(await verifyStripeSignature(tampered, header, SECRET), false);
});

test('missing signature fails', async () => {
  const payload = JSON.stringify(makeEvent());
  assert.equal(await verifyStripeSignature(payload, null, SECRET), false);
});

test('old replayed signature fails (timestamp tolerance)', async () => {
  const payload = JSON.stringify(makeEvent());
  const { header } = sign(payload, Math.floor(Date.now() / 1000) - 3600);
  assert.equal(await verifyStripeSignature(payload, header, SECRET), false);
});

test('same event delivered 3 times: core action runs exactly once', async () => {
  const kv = mockKv();
  const calls = makeFetchRecorder();
  const event = makeEvent();
  const payload = JSON.stringify(event);
  const { header } = sign(payload);

  const env = makeEnv(kv);

  const r1 = await onRequestPost({ request: makeRequest(payload, header), env });
  assert.equal(r1.status, 200);

  const r2 = await onRequestPost({ request: makeRequest(payload, header), env });
  assert.equal(r2.status, 200);

  const r3 = await onRequestPost({ request: makeRequest(payload, header), env });
  assert.equal(r3.status, 200);

  // Only ONE email request must have been sent despite 3 deliveries.
  const emailCalls = calls.filter((c) => String(c.url).includes('api.resend.com/emails'));
  assert.equal(emailCalls.length, 1);
});

test('different events are processed independently', async () => {
  const kv = mockKv();
  const calls = makeFetchRecorder();
  const env = makeEnv(kv);

  for (const plan of ['monthly', 'annual', 'onetime']) {
    const event = makeEvent({ data: { object: { customer_email: `u-${plan}@example.com`, metadata: { plan } } } });
    const payload = JSON.stringify(event);
    const { header } = sign(payload);
    const res = await onRequestPost({ request: makeRequest(payload, header), env });
    assert.equal(res.status, 200);
  }

  const emailCalls = calls.filter((c) => String(c.url).includes('api.resend.com/emails'));
  assert.equal(emailCalls.length, 3);
});

test('without KV, idempotency key still dedupes at Resend layer', async () => {
  const calls = makeFetchRecorder();
  const event = makeEvent();
  const payload = JSON.stringify(event);
  const { header } = sign(payload);

  // No PROCESSED_EVENTS binding configured.
  const env = { STRIPE_WEBHOOK_SECRET: SECRET, RESEND_API_KEY: 're_test_key' };

  await onRequestPost({ request: makeRequest(payload, header), env });
  await onRequestPost({ request: makeRequest(payload, header), env });

  const emailCalls = calls.filter((c) => String(c.url).includes('api.resend.com/emails'));
  assert.equal(emailCalls.length, 2, 'without KV both deliveries reach Resend');
  const [first, second] = emailCalls;
  const key1 = first.opts.headers['Idempotency-Key'];
  const key2 = second.opts.headers['Idempotency-Key'];
  assert.ok(key1 && key1.startsWith('stripe-'), 'idempotency key must be present');
  assert.equal(key1, key2, 'same event must use the same idempotency key');
});

test('invalid signature returns 400 and does nothing', async () => {
  const calls = makeFetchRecorder();
  const payload = JSON.stringify(makeEvent());
  const env = makeEnv(mockKv());
  const res = await onRequestPost({ request: makeRequest(payload, 't=123,v1=deadbeef'), env });
  assert.equal(res.status, 400);
  assert.equal(calls.filter((c) => String(c.url).includes('api.resend.com/emails')).length, 0);
});