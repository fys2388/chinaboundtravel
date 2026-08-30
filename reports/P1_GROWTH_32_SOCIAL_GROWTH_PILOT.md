# P1-GROWTH-32 — Social Growth Pilot

- Date: 2026-08-29
- Final status: **PASS** (planning, assets, registry, baseline, and validation complete)
- Pilot window: 2026-08-30 .. 2026-09-12 (14 days)
- Execution gate: external Buffer scheduling is not executed in this round.
  No auto-publish, no commit, no push, no deployment.

## Selected 10 Source Articles

Selection order: indexed -> meaningful GSC impressions -> commercial relevance ->
no active experiment -> no unresolved canonical conflict -> trust issues present.
All 10 are READY in the Growth Control Plane queue, indexed, and not frozen.

| # | content_id | title | URL | priority | GSC impressions |
|---|---|---|---|---|---|
| 1 | cbt-cfd5d7b39f09 | Chinese Language Survival Phrases Guide 2026 | /posts/chinese-language-survival-phrases-guide/ | P2 | 11 |
| 2 | cbt-c59607760fee | Chinese Street Food: Night Markets & What to Eat | /posts/chinese-street-food-a-first-timers-guide-to-night-markets-and-street-stalls/ | P2 | 6 |
| 3 | cbt-550a6e3e929c | Sichuan Hotpot Guide: History & Best Restaurants | /posts/sichuan-hotpot-guide-history-best-restaurants-and-cultural-significance/ | P2 | 11 |
| 4 | cbt-302467d853db | Shanghai 48-Hour Guide: Bund & French Concession | /posts/shanghai-bund-french-concession-2-day-guide/ | P2 | 11 |
| 5 | cbt-bf4ec5e57a07 | Guilin & Yangshuo: Complete 2026 Travel Guide | /posts/guilin-and-yangshuo-the-ultimate-karst-landscape-guide-for-2026/ | P1 | 24 |
| 6 | cbt-34777b6c17c1 | Zhangjiajie Guide: Avatar Mountains & Itinerary | /posts/zhangjiajie-avatar-mountains-complete-guide-to-chinas-most-spectacular-park/ | P1 | 20 |
| 7 | cbt-baa2f6fba2f0 | Where to Stay in China: Complete 2026 Guide | /posts/accommodation-tips-guide/ | P2 | 17 |
| 8 | cbt-80f6c218ad94 | Western Sichuan Overland Camping Route: 7 Days | /posts/western-sichuan-overland-camping-route/ | P1 | 26 |
| 9 | cbt-244822dc113b | China's 144-Hour Visa-Free Transit: 15 New Countries | /posts/china-extends-144-hour-visa-free-transit-policy-to-more-countries/ | P0 | 87 |
| 10 | cbt-707a8899c0a7 | Can Foreigners Use WeChat Pay in China? (2026 Guide) | /posts/how-to-use-wechat-pay-as-a-foreigner/ | P1 | 83 |

Fact-check rule: no social asset repeats or introduces a dynamic fact. Assets
for the policy and payment articles use static planning language only.

## Generated Assets

30 assets created in `reports/social/P1_GROWTH_32_SOCIAL_PILOT_REGISTRY.csv`.
IDs use the isolated namespace `soc-p32-001`..`soc-p32-030` and do not collide
with the production inventory (`soc-000001`..`soc-000100`).

Platform distribution:

| platform | post_type | count |
|---|---|---:|
| pinterest | knowledge (Knowledge / Tip) | 10 |
| pinterest | tip (Checklist / Saveable) | 10 |
| ig | visual (Visual / Story) | 10 |
| total | | 30 |

Every asset includes `social_content_id`, `content_id`, `source_article`,
`platform`, `post_type`, `caption`, `visual_requirement`, `utm`,
`affiliate_flag`, `status`, and `scheduled_at`.

## 14-Day Schedule

Cadence: Pinterest 2/day, Instagram 1/day, max 3 posts/day. Active posting runs
days 1-10 (30 assets). Days 11-14 are SKIP because the approved pool is capped
at 30 assets; no filler is created to force volume. Measurement continues
through day 14.

Full slot table is in
[P1_GROWTH_32_SOCIAL_PILOT_PLAN.md](reports/social/P1_GROWTH_32_SOCIAL_PILOT_PLAN.md).
Slots follow the existing convention: 20:00 ET Pinterest, 20:30 ET Instagram,
21:00 ET Pinterest; UTC equivalents are stored in `publish_at`.

## Tracking Readiness

- `utm_source`: pinterest or ig
- `utm_medium`: social
- `utm_campaign`: cbt_social_20260830
- `utm_content`: social_content_id (soc-p32-*)
- `affiliate_flag`: NO on all assets; no affiliate link is embedded in social copy
- No GA4 event schema change; no affiliate URL or UTM convention change

## Validation

| Check | Result |
|---|---|
| pytest tests/ -q | 690 passed, 0 failed, 0 skipped |
| content_id audit --strict | PASS 58/58 |
| hugo --gc --minify | PASS 396 pages |
| brand audit (legacy) | PASS 0 legacy hits across content/posts |
| brand audit (layer) | PASS (WARN = editorial language absent in templates, no violations) |
| internal link audit | PASS 571 links, 0 broken / 0 redirect / 0 malformed |
| meta audit | PASS (6 pre-existing description-length advisories, 0 duplicate) |
| affiliate regression | 337 passed |
| secret scan + workflow validation | 10 passed |
| persona / brand / social lint on 30 captions | PASS 0 violations |

## Blockers

1. External Buffer scheduling requires explicit human approval before the pilot
   can publish; this round does not call the worker or deploy automatically.
2. GA4 `sessionSource=social` website sessions and engaged sessions are not yet
   returned to the social funnel; they remain NULL / NOT_AVAILABLE.
3. No affiliate revenue API exists; revenue remains NULL / NOT_AVAILABLE and is
   never converted to 0.

## Deliverables

- reports/social/P1_GROWTH_32_SOCIAL_PILOT_REGISTRY.csv
- reports/social/P1_GROWTH_32_SOCIAL_PILOT_BASELINE.csv
- reports/social/P1_GROWTH_32_SOCIAL_PILOT_PLAN.md
- reports/P1_GROWTH_32_SOCIAL_GROWTH_PILOT.md

No commit, no push, no deployment.
