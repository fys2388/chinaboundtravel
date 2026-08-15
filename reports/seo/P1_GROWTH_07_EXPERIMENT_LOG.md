# P1-GROWTH-07 Experiment Log

- Date: 2026-08-16
- GitHub main baseline: `ee55b3c`
- LOW_SAMPLE_WARNING: site 28d clicks = 3; CTR-based judgments are not meaningful yet. Do NOT declare success/failure before two consecutive 28-day windows.

## Experiment GROWTH07-WX-001 — WeChat Pay Differentiation

- Action: content differentiation (STRONG/WEAK re-positioning)
- Pages:
  - STRONG (INDEXED): `cbt-707a8899c0a7` Can Foreigners Use WeChat Pay in China? — owns WECHAT_PAY_FOR_FOREIGNERS (eligibility, cards, limitations, common issues, payment basics)
  - WEAK (NOT_INDEXED, alternate): `cbt-255af4ed003a` How to Set Up & Use WeChat Pay Step by Step — owns HOW_TO_USE_WECHAT_PAY_STEP_BY_STEP (exact steps, verification, foreign card, QR payment, merchant payment, scan/pay, troubleshooting, errors)
- Baseline:
  - STRONG: 83 impressions / 0 clicks / CTR 0% / pos 62.45 (28d); INDEXED
  - WEAK: 1 impression / 0 clicks / CTR 0% / pos 11.0 (28d); NOT_INDEXED (Alternate page with proper canonical tag)
- Change:
  - STRONG: title/description/summary updated to eligibility-intent; opening rewritten objectively (fabricated anecdotes removed); H2s re-aimed at eligibility/cards/payment basics/limitations; FAQ added (5 Q&A); reciprocal link to WEAK kept.
  - WEAK: title/description/summary updated to step-by-step intent; H1 rewritten; fabricated Berlin anecdote removed; added "How to Pay with WeChat Pay: QR Codes and Merchant Payments" + "Troubleshooting: Common Errors and Fixes" sections; FAQ added (5 Q&A); reciprocal link to STRONG added.
  - URL / canonical / content_id / slug / affiliate / UTM unchanged (verified by tests + diff).
- PRIMARY_METRIC: Indexing status, Query diversity, Impressions
- SECONDARY_METRICS: CTR, Average position
- START_DATE: 2026-08-16
- MINIMUM_OBSERVATION: 28 days (Indexing may take longer; allow 2 GSC windows)

## Experiment GROWTH07-TR-001 — Transportation Expansion (high-speed rail booking)

- Action: existing-content expansion on highest-evidence transport page
- Page: `cbt-cc4549872c92` How to Book China High-Speed Train Tickets (2026)
- Evidence: 138 impressions / 0 clicks / pos 30.14 (28d); query cluster: "china high speed rail tickets" (10 imp), "china high speed train tickets" (6), "how to buy china high speed rail tickets" (3), "china bullet train tickets" (4), "china high speed rail ticket" (4), "book china high speed train" (2), "where to buy china high speed rail tickets" (2) + ~15 more HSR-booking queries.
- Change:
  - Front-matter FAQ replaced (was 3 off-topic generic Q&A: safety/best-time/VPN) with 4 booking-relevant Q&A.
  - "Hey, Joran Here" fabricated section → "The Quick Answer" (objective).
  - Removed fabricated claims ("I've taken 200+ trips", "I watched a guy", etc.); "Joran's Tip" → "Tip".
  - New section "When Do Tickets Go on Sale?" (query coverage: advance booking, holiday sell-out).
  - Internal link added to the canonical transportation hub guide.
  - New body FAQ section (4 Q&A, renders FAQPage-ready content).
  - URL / canonical / content_id / affiliate / UTM unchanged.
- PRIMARY_METRIC: Impressions, Average position
- SECONDARY_METRICS: CTR, clicks
- START_DATE: 2026-08-16
- MINIMUM_OBSERVATION: 28 days
- Technical caveat: the page's canonical URL `/posts/china-high-speed-rail-how-to-book-tickets/` is currently consumed by the transportation guide's Hugo `aliases` (noindex refresh stub), and `static/_redirects` 301s the dated URL to it — the page is folded into the guide today. Content improvements are live-ready once the redirect/alias conflict is resolved (separate technical round, needs owner approval because it touches the persona-listed guide and `_redirects`).

## Common

- Observation window: at least 28 days after deployment.
- No social publishing. No LLM-generated body. No affiliate/UTM changes.
