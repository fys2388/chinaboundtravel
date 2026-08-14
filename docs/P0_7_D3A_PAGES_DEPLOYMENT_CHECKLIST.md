# P0.7-D3A Pages Deployment Checklist

Date: 2026-08-14. Release baseline: `bcb7994e83a448843a3a00866a55b1c39a95ba1d`.
No secret values are included in this document.

## Pre-deploy
- [x] PROCESSED_EVENTS KV namespace exists (ID `14eafec3624b4afeb1e22e090a9716d3`)
- [x] `wrangler.toml` declares `[[kv_namespaces]]` binding `PROCESSED_EVENTS` -> namespace ID above
- [x] `wrangler.toml` no longer contains `MAILERLITE_API_KEY` or Stripe plaintext placeholders
- [x] Encrypted Secrets on Cloudflare Pages (Production):
  - [x] `DOUBAO_ARK_API_KEY` (Secret, configured 2026-08-14)
  - [x] `MAILERLITE_API_TOKEN` (Secret, configured 2026-08-14)
  - [x] `RESEND_API_KEY` (Secret, configured 2026-08-14)
  - [ ] `STRIPE_SECRET_KEY` (still placeholder - blocked until wrangler.toml vars cleared by deploy)
  - [ ] `STRIPE_WEBHOOK_SECRET` (still placeholder - blocked until wrangler.toml vars cleared by deploy)
- [x] Secret naming contract enforced (`tests/test_secret_name_contract.py`, 4 tests)
- [x] Build: `hugo --gc --minify` PASS (366 pages)
- [x] Tests: `pytest` 112 passed; `node --test` 8 passed; content_id 57/57; secret scan PASS; workflow YAML PASS

## Deploy (next phase, P0.7-D3B)
Gate: STRIPE_SECRET_KEY + STRIPE_WEBHOOK_SECRET must be configured as encrypted Secrets first.
1. Commit local config (`chore: prepare production pages kv binding`).
2. `wrangler pages deploy public --project-name=chinaboundtravel`
   (clears legacy `MAILERLITE_API_KEY` placeholder var; installs PROCESSED_EVENTS binding).
3. Dashboard: add `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET` as encrypted Secrets
   (values from local `.env`; never print/write them).
4. Verify variables page: 5 encrypted Secrets (DOUBAO, MAILERLITE_TOKEN, RESEND, STRIPE x2);
   no `MAILERLITE_API_KEY`; bindings show `PROCESSED_EVENTS`.

## Post-deploy
- [ ] Verify env: `/functions` runtime sees all 5 secrets + PROCESSED_EVENTS binding
- [ ] Verify KV binding: webhook idempotency writes `evt:{eventId}` with 604800s TTL
- [ ] Verify homepage: https://www.chinaboundtravel.com/ returns 200
- [ ] Verify Stripe endpoint: webhook signature HMAC-SHA256 + replay tolerance 300s + KV dedup
- [ ] Verify robots.txt: 200, sitemap reference https://www.chinaboundtravel.com/sitemap.xml
- [ ] Verify sitemap: 200, contains latest posts
- [ ] Verify canonical / affiliate / UTM regression: 0 unexpected changes
- [ ] Production smoke test (P0.7-D4 scope)

## Current gate
- STRIPE_SECRET_KEY = NOT VERIFIED / PLACEHOLDER
- STRIPE_WEBHOOK_SECRET = NOT VERIFIED / PLACEHOLDER
- => Pages production deploy: BLOCKED. Stop at READY_FOR_PAGES_DEPLOY.
