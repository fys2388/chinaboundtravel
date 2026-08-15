# P1-GROWTH-07 — WeChat Pay Differentiation + First SEO Expansion — Report

- Date: 2026-08-16
- WORKDIR: `E:\AI\dulizhan\travel-blog`
- GitHub main baseline: `ee55b3c` (HEAD == origin/main at start)
- Final verdict: **P1-GROWTH-07 = PASS_WITH_PARTIAL**

---

## 1. Scope

Per P1-GROWTH-07 instruction: exactly 3 content objects.

1. WECHAT STRONG (differentiation owner) — `cbt-707a8899c0a7`
2. WECHAT WEAK (differentiation re-position) — `cbt-255af4ed003a`
3. TRANSPORT (first SEO expansion) — `cbt-cc4549872c92`

No other articles, no legacy persona batch edits, no URL / slug / canonical / affiliate / UTM / `_redirects` / layouts / `hugo.toml` changes.

## 2. Selected A / B / C

| Role | content_id | Page | Evidence |
|---|---|---|---|
| STRONG (A) | `cbt-707a8899c0a7` | [Can Foreigners Use WeChat Pay in China?](https://www.chinaboundtravel.com/posts/how-to-use-wechat-pay-as-a-foreigner/) | INDEXED; 28d 83 imp / 0 clicks / pos 62.45 |
| WEAK (B) | `cbt-255af4ed003a` | [How to Set Up & Use WeChat Pay Step by Step](https://www.chinaboundtravel.com/posts/wechat-pay-for-foreigners-step-by-step-setup-and-common-mistakes-to-avoid-guide/) | NOT_INDEXED ("Alternate page with proper canonical tag"); 28d 1 imp / pos 11.0 |
| TRANSPORT (C) | `cbt-cc4549872c92` | [How to Book China High-Speed Train Tickets](https://www.chinaboundtravel.com/posts/china-high-speed-rail-how-to-book-tickets/) | 28d 138 imp / 0 clicks / pos 30.14; ~20 HSR-booking queries ("china high speed rail tickets" 10, "china high speed train tickets" 6, "how to buy china high speed rail tickets" 3, "china bullet train tickets" 4, etc.) |

Owner decision (pre-confirmed): **WECHAT PAY = DIFFERENTIATE** (not merge).

## 3. Differentiation Plan (WeChat Pay)

| Dimension | STRONG (`cbt-707a8899c0a7`) | WEAK (`cbt-255af4ed003a`) |
|---|---|---|
| Positioning | Eligibility & overview: CAN foreigners use WeChat Pay | How-to: step-by-step setup, QR payment, troubleshooting |
| Primary intent | WECHAT_PAY_FOR_FOREIGNERS | HOW_TO_USE_WECHAT_PAY_STEP_BY_STEP |
| Title | Can Foreigners Use WeChat Pay in China? (2026 Guide) | How to Set Up & Use WeChat Pay Step by Step (2026 Guide) |
| Meta description | Eligibility / cards / basics / limitations | Register / verify / add foreign card / pay with QR / fix errors |

Both pages keep their URL, canonical, slug, content_id, affiliate, and UTM; they now cross-link each other as complementary (overview ⇄ how-to).

## 4. Actual Changes

### 4.1 STRONG — `content/posts/2026-05-22-how-to-use-wechat-pay-as-a-foreigner.md`
- Title: → `Can Foreigners Use WeChat Pay in China? (2026 Guide)`
- Description: → `Can foreigners use WeChat Pay in China in 2026? Yes — eligibility, supported cards, payment basics, and limitations, explained.` (127 chars, within limits)
- Summary aligned; H1 `## Can Foreigners Use WeChat Pay in China?`
- Removed fabricated anecdotes ("When I first landed in Chengdu…", "I tried linking my U.S. Chase Visa…", "my friend once sent himself 50 RMB…").
- H2s re-aimed: What You Need to Get Started / cards & limitations / payment basics / The Bottom Line.
- Added `## FAQ: Foreigners and WeChat Pay` with 5 Q&A (`### question` / `回答` style, renders in-page).
- Kept contextual internal links (WEAK how-to, Alipay guide, Klook pro-tip, HSR page).

### 4.2 WEAK — `content/posts/2026-07-02-wechat-pay-for-foreigners-step-by-step-setup-and-common-mistakes-to-avoid-guide.md`
- Title: → `How to Set Up & Use WeChat Pay Step by Step (2026 Guide)`
- Description: → `Set up and use WeChat Pay in China step by step: register your account, verify your identity, add a foreign card, pay with QR codes, and fix common errors.`
- H1 `# How to Set Up & Use WeChat Pay Step by Step (2026)`; removed fabricated Berlin narrative.
- Added `## How to Pay with WeChat Pay: QR Codes and Merchant Payments` and `## Troubleshooting: Common Errors and Fixes`.
- Added 5 FAQ Q&A; added reciprocal link to STRONG page.

### 4.3 TRANSPORT — `content/posts/2026-05-25-china-high-speed-rail-how-to-book-tickets.md`
- Front-matter FAQ: replaced 3 off-topic generic Q&A (safety/best-time/VPN) with 4 booking-relevant Q&A.
- Removed fabricated "Hey, Joran Here" intro and claims ("I've taken 200+ trips", "I watched a guy…"); replaced with `## The Quick Answer`.
- "Joran's Tip" → "Tip".
- Added `## When Do Tickets Go on Sale?` (advance booking, holiday sell-out coverage).
- Added body FAQ section (4 Q&A).
- Added internal link to the transportation hub guide.
- Meta: `*Last updated … | Joran*` → editorial team.

## 5. SEO Safety (verified)

- content_id, canonicalURL, slug: **unchanged** for all 3 pages.
- Affiliate / URL / UTM tokens: **0 removed, 0 added** (diff + tests).
- `python scripts/persona_guard.py` on all 3 pages: **PASS**.
- `python scripts/audit_meta_descriptions.py`: too_long = 0; P0 duplicate = 0.
- No new noindex, no robots/sitemap change, no canonical change.

## 6. Tests

- New: `tests/test_growth07_content_differentiation.py` — 10 checks (title diff, meta diff, H1 intent, H2 count, reciprocal links, URL/canonical/content_id stable, affiliate stable, persona guard, meta dup, scope control).
- Updated: `tests/test_growth05_first_content_action.py` scope allow-list (3 new GROWTH-07 objects).
- Full suite: **186 passed / 0 failed / 0 skipped**.
- `hugo --gc --minify`: exit 0; `public/robots.txt` + `public/sitemap.xml` exist.
- `content_id_audit audit --strict`: PASS.
- Internal link audit: 0 published 404 / 0 malformed.
- Secret scan (HEAD + full history): 0 real secret hits.
- Workflow YAML validation: 0 invalid.

## 7. Production Deployment

- Deployment method: normal `git push origin main` (fast-forward) → GitHub Actions `deploy-cloudflare-pages.yml` auto-deploy on `content/**`.
- No manual `wrangler pages deploy` in this round.
- Deployment status will be verified after push (workflow run + live URLs).

## 8. Observation Plan

| Experiment | PRIMARY | SECONDARY | Start | Min observation |
|---|---|---|---|---|
| GROWTH07-WX-001 (WeChat differentiation) | Indexing status, query diversity, impressions | CTR, position | 2026-08-16 | 28 days (indexing may need 2 GSC windows) |
| GROWTH07-TR-001 (HSR expansion) | Impressions, position | CTR, clicks | 2026-08-16 | 28 days |

- **LOW_SAMPLE_WARNING**: site 28d clicks = 3. No success/failure call before two consecutive 28-day windows.
- No social publishing, no Buffer/Stripe/Resend changes, no LLM-generated content.

## 9. Remaining Manual Items (not this round's scope)

1. **TRANSPORT page canonical folding (technical)**: `/posts/china-high-speed-rail-how-to-book-tickets/` is consumed by `2026-07-16-china-transportation-complete-guide…` Hugo `aliases` (noindex refresh stub) and `static/_redirects` 301s the dated URL to it → 138 impressions currently flow to the folded page. Content is improved and ready; unfolding needs a separate technical round touching `_redirects` / aliases and the persona-listed transportation guide (owner approval required).
2. **FAQPage JSON-LD not rendered**: pre-existing template defect — `layouts/partials/schema_faq.html` looks for the literal string `"## FAQ"` in rendered HTML and never matches, so no FAQPage rich-result markup is emitted (also true for the existing zhangjiajie FAQ page). Fixing requires a layouts change → separate technical round (out of this round's boundary).
3. **WEAK page index recovery**: after differentiation the page still needs GSC re-crawl / indexing request once it is re-crawled; no auto Indexing API call in this round.
4. WeChat Pay duplicate pair: decision = DIFFERENTIATE executed; monitor 28d, re-evaluate via GROWTH-06 measurement loop.

## 10. Files in this commit

- `content/posts/2026-05-22-how-to-use-wechat-pay-as-a-foreigner.md`
- `content/posts/2026-07-02-wechat-pay-for-foreigners-step-by-step-setup-and-common-mistakes-to-avoid-guide.md`
- `content/posts/2026-05-25-china-high-speed-rail-how-to-book-tickets.md`
- `tests/test_growth07_content_differentiation.py` (new)
- `tests/test_growth05_first_content_action.py` (scope update)
- `reports/seo/P1_GROWTH_07_EXPERIMENT_LOG.md` (new)
- `reports/seo/TOP_10_CONTENT_PRIORITIES.md`, `reports/seo/CONTENT_EXECUTION_BATCHES.md`, `reports/seo/FIRST_CONTENT_REVIEW_QUEUE.csv` (title sync for the two WeChat pages)

## 11. Verdict

**P1-GROWTH-07 = PASS_WITH_PARTIAL**

- WeChat STRONG/WEAK differentiation: PASS (content + tests).
- Transportation expansion: PASS on content, PARTIAL on technical (canonical folding blocks live impact until a separate approved technical round).
- Tests / Hugo / content_id / secret scan: PASS.
- Next: monitor 28d via GROWTH-06 measurement loop → decide WECHAT index request + transportation unfold technical round → then next batch from TOP_10_CONTENT_PRIORITIES.
