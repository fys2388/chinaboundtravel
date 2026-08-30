# P1-GROWTH-32 — Social Growth Pilot Plan

- Date: 2026-08-29
- Status: PLANNED (registry created, no publish)
- Pilot window: 2026-08-30 .. 2026-09-12 (14 days)
- Input: `reports/management/GROWTH_PRIORITY_QUEUE.csv`
- Output:
  - `reports/social/P1_GROWTH_32_SOCIAL_PILOT_REGISTRY.csv`
  - `reports/social/P1_GROWTH_32_SOCIAL_PILOT_BASELINE.csv`

## 1. Selection Methodology

Selection follows the required priority order:
indexed -> meaningful GSC impressions -> commercial relevance -> no active
experiment -> no unresolved canonical conflict -> trust issues present.

Exclusions applied:

- Status not READY (FROZEN / WAIT / TECHNICAL_FIX removed)
- Canonical conflict queue URLs removed
- Low trust pages (trust_score below 50) removed
- Social assets must never repeat dynamic facts from FACT_CHECK entries

Interpretation note: every eligible high-value page in the current queue still
carries `FACT_CHECK_REQUIRED` rows for dynamic article facts (visa, prices,
schedules, distances). For this pilot the exclusion is applied at the caption
level: no social asset repeats or introduces a dynamic fact. The 10 selected
articles are publishable for static, editorial, and topic-level social content.

## 2. Selected Source Articles (TOP 10)

| # | content_id | title | URL | priority | GSC impressions | trust |
|---|---|---|---|---|---|---|
| 1 | cbt-cfd5d7b39f09 | Chinese Language Survival Phrases Guide 2026 | /posts/chinese-language-survival-phrases-guide/ | P2 | 11 | 65 |
| 2 | cbt-c59607760fee | Chinese Street Food: Night Markets & What to Eat | /posts/chinese-street-food-a-first-timers-guide-to-night-markets-and-street-stalls/ | P2 | 6 | 79 |
| 3 | cbt-550a6e3e929c | Sichuan Hotpot Guide: History & Best Restaurants | /posts/sichuan-hotpot-guide-history-best-restaurants-and-cultural-significance/ | P2 | 11 | 69 |
| 4 | cbt-302467d853db | Shanghai 48-Hour Guide: Bund & French Concession | /posts/shanghai-bund-french-concession-2-day-guide/ | P2 | 11 | 67 |
| 5 | cbt-bf4ec5e57a07 | Guilin & Yangshuo: Complete 2026 Travel Guide | /posts/guilin-and-yangshuo-the-ultimate-karst-landscape-guide-for-2026/ | P1 | 24 | 59 |
| 6 | cbt-34777b6c17c1 | Zhangjiajie Guide: Avatar Mountains & Itinerary | /posts/zhangjiajie-avatar-mountains-complete-guide-to-chinas-most-spectacular-park/ | P1 | 20 | 52 |
| 7 | cbt-baa2f6fba2f0 | Where to Stay in China: Complete 2026 Guide | /posts/accommodation-tips-guide/ | P2 | 17 | 66 |
| 8 | cbt-80f6c218ad94 | Western Sichuan Overland Camping Route: 7 Days | /posts/western-sichuan-overland-camping-route/ | P1 | 26 | 54 |
| 9 | cbt-244822dc113b | China's 144-Hour Visa-Free Transit: 15 New Countries | /posts/china-extends-144-hour-visa-free-transit-policy-to-more-countries/ | P0 | 87 | 63 |
| 10 | cbt-707a8899c0a7 | Can Foreigners Use WeChat Pay in China? (2026 Guide) | /posts/how-to-use-wechat-pay-as-a-foreigner/ | P1 | 83 | 71 |

Articles 9 and 10 are fact-sensitive. Their social captions are written as
static planning guidance only: no policy counts, eligibility rules, fees, or
availability claims appear in any asset.

## 3. Asset Inventory

30 assets, one `soc-p32-*` ID per asset. IDs do not collide with the existing
`content/social/inventory.json` namespace (`soc-000001`..`soc-000100`) and are
not written into the production inventory this round.

Per article:

| required asset | registry post_type | platform |
|---|---|---|
| Pinterest Knowledge / Tip post | knowledge | pinterest |
| Pinterest Checklist / Saveable post | tip | pinterest |
| Instagram Visual / Story post | visual | ig |

Platform distribution:

| platform | count |
|---|---:|
| pinterest | 20 |
| ig | 10 |
| total | 30 |

## 4. 14-Day Schedule

Cadence: Pinterest 2/day, Instagram 1/day, max 3 posts/day. The approved pool is
capped at 30 assets (10 articles x 3), so active posting runs on days 1-10.
Days 11-14 are marked SKIP because no additional approved asset exists; no
filler is created to force volume. Measurement continues through day 14.

Slots use the existing pilot convention (America/New_York, EDT):
20:00 Pinterest, 20:30 Instagram, 21:00 Pinterest.

| ET date | 20:00 ET (Pinterest) | 20:30 ET (Instagram) | 21:00 ET (Pinterest) |
|---|---|---|---|
| 2026-08-30 | soc-p32-001 Language phrases | soc-p32-024 Western Sichuan | soc-p32-017 Zhangjiajie checklist |
| 2026-08-31 | soc-p32-004 Street food | soc-p32-027 Policy update | soc-p32-020 Accommodation checklist |
| 2026-09-01 | soc-p32-007 Hotpot | soc-p32-030 Mobile payments | soc-p32-023 Western Sichuan checklist |
| 2026-09-02 | soc-p32-010 Shanghai | soc-p32-003 Language phrases IG | soc-p32-026 Policy checklist |
| 2026-09-03 | soc-p32-013 Guilin | soc-p32-006 Street food IG | soc-p32-029 Mobile payment checklist |
| 2026-09-04 | soc-p32-016 Zhangjiajie | soc-p32-009 Hotpot IG | soc-p32-002 Mandarin checklist |
| 2026-09-05 | soc-p32-019 Accommodation | soc-p32-012 Shanghai IG | soc-p32-005 Night market checklist |
| 2026-09-06 | soc-p32-022 Western Sichuan | soc-p32-015 Guilin IG | soc-p32-008 Hotpot checklist |
| 2026-09-07 | soc-p32-025 Policy update | soc-p32-018 Zhangjiajie IG | soc-p32-011 Shanghai checklist |
| 2026-09-08 | soc-p32-028 Mobile payments | soc-p32-021 Accommodation IG | soc-p32-014 Guilin checklist |
| 2026-09-09 | SKIP | SKIP | SKIP |
| 2026-09-10 | SKIP | SKIP | SKIP |
| 2026-09-11 | SKIP | SKIP | SKIP |
| 2026-09-12 | SKIP | SKIP | SKIP |

UTC equivalents are stored in `publish_at` in the registry and baseline CSVs
(e.g. 2026-08-31T00:00:00+00:00 for the 2026-08-30 20:00 ET slot).

## 5. Brand and Quality Rules

- Editorial voice only: ChinaBound Travel editorial team, research-based guidance.
- No fake first-person experience, fake local expertise, fake family experience,
  "I lived in China", "my wife", "I personally tested", or "my favorite".
- No unsupported absolutes: best, always, never, cheapest, perfect, guaranteed.
- No invented dynamic facts: prices, visa rules, schedules, opening hours,
  distances, current availability, or statistics.
- No identical captions across platforms. Pinterest copy is save/search oriented;
  Instagram copy is visual and emotional, not an article summary.
- Captions were checked with `persona_guard`, `brand_identity_audit.scan_text`,
  and `social_text_utils.validate_social_copy`.

## 6. Publishing Strategy and Buffer

- Existing Buffer Worker only: `buffer-worker/worker.js` with `dedup.mjs`.
- Account routing unchanged: Pinterest -> Buffer-B; Instagram -> Buffer-A.
- Deterministic dedup: `social_content_id` is unique (`soc-p32-001`..`030`) and
  no duplicate ID exists in this registry.
- Status is `PENDING_APPROVAL`. This round does not call the worker, does not
  schedule externally, and does not deploy. Publishing remains a separate
  human-approved step.

## 7. Tracking Readiness

Every asset has:

- `utm_source`: pinterest or ig
- `utm_medium`: social
- `utm_campaign`: cbt_social_20260830
- `utm_content`: social_content_id (soc-p32-*)

No website GA4 event schema is changed. No affiliate URL, affiliate partner, or
UTM convention is changed. `affiliate_flag = NO` on every asset because the
social copy itself contains no affiliate link.

## 8. Data Feedback and Measurement

Primary metrics:

- social impressions
- social clicks
- website sessions

Secondary metrics:

- engaged sessions
- affiliate clicks

Baseline is all NULL (`NOT_AVAILABLE`): no pilot asset has published data yet.
Revenue stays NULL whenever no valid revenue source exists; unavailable revenue
is never converted to 0. Pilot review happens after the full 14-day window; no
success or failure is declared after 1-3 days.

## 9. Guardrails

- No new blog articles, no URL/slug/canonical/content_id changes.
- No changes to REV001 / REV002 / DRIVE-001.
- No new affiliate partners, no affiliate URL or UTM changes.
- No modification to `content/social/inventory.json`.
- No commit, no push, no deployment.

## 10. Validation (to be completed in final report)

- pytest tests/ -q
- content_id audit --strict
- hugo --gc --minify
- brand audit
- internal link audit
- meta audit
- affiliate regression
- secret scan
- workflow validation
