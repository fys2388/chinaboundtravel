# P1-GROWTH-04 Content Prioritization — Report

- Date: 2026-08-16
- Workdir: `E:\AI\dulizhan\travel-blog`
- GitHub main baseline: `6f3035b`
- Inputs: P1-GROWTH-03 artifacts only (NO GSC API re-call, NO repo-wide scan)

## 1. Priority model

Priority Score (0-100) is DIFFERENT from the Opportunity Score. Seven transparent components (no LLM):

| component | max | rule |
|---|---|---|
| SEO Opportunity | /25 | scaled from GROWTH-03 opportunity score |
| Search Demand | /20 | impressions tiers (0/1-49/50-99/100-499/500+) + multi-query bonus |
| Business Intent | /15 | business value tier x intent commercial bias (VISA/PAYMENT/TRANSPORT > others) |
| Index/Technical Urgency | /15 | canonical HIGH = 15; not-indexed = 12-15; indexed = 3 |
| Execution Ease | /10 | S-effort fixes (canonical/title/index) score higher than rewrites/new content |
| Expected Impact | /10 | position 4-20 sweet spot; low-data cap at 4 |
| Risk | /5 | higher = safer; low data caps at 3 |
| **total** | **/100** | P0 >=85 / P1 >=75 / P2 >=65 / P3 >=50 / P4 <50 |

Forced rules (applied after component sum):

- Rule A: canonical conflict HIGH -> priority >= 85, action TECHNICAL_FIX
- Rule B: not indexed + high commercial intent -> priority >= 80, action INDEX_RECOVERY
- Rule C: position 4-20 + impressions >= 100 -> +6 boost
- Rule D: position 21-50 + impressions >= 100 -> +3 boost
- Rule E: clicks > 0 + high commercial intent -> +3 commercial boost
- Rule F: impressions < 10 -> priority capped at 60 unless a technical rule already raised it

Implementation: `scripts/content_priority_engine.py` (deterministic, no network).

## 2. TOP 10 Content Priorities

Full table: `reports/seo/TOP_10_CONTENT_PRIORITIES.md`

| # | priority | title | action | effort |
|---|---|---|---|---|
| 1 | 88.0 (P0) | China Transportation Guide: Trains, Subways & Taxis | TECHNICAL_FIX | S |
| 2 | 85.0 (P0) | China Travel Safety 2026: Guide for Travelers | TECHNICAL_FIX | S |
| 3 | 85.0 (P0) | China Travel Guide: July 2026 Updates & Visa Rules | TECHNICAL_FIX | S |
| 4 | 85.0 (P0) | Foodie's Guide to China: Dishes You Must Try | TECHNICAL_FIX | S |
| 5 | 80.0 (P1) | WeChat Pay for Foreigners: Setup Guide & Mistakes | INDEX_RECOVERY | S |
| 6 | 80.0 (P1) | China High-Speed Trains: Booking & Insider Tips | INDEX_RECOVERY | S |
| 7 | 80.0 (P1) | Great Wall of China: History Beyond the Tourist Trail | INDEX_RECOVERY | S |
| 8 | 80.0 (P1) | Chinese Train Stations: Survival Guide for Travelers | INDEX_RECOVERY | S |
| 9 | 80.0 (P1) | How to Book China High-Speed Train Tickets (2026) | INDEX_RECOVERY | S |
| 10 | 72.75 (P2) | 144-Hour Visa-Free Transit in China (2026 Guide) | TITLE_META_UPDATE | S |

- 6 canonical conflicts (all HIGH) map onto ranks 1-4 -> Technical first.
- 5 index-recovery items (ranks 5-9) carry real GSC coverage states (noindex / redirect / alternate canonical / URL unknown).

## 3. Execution batches

`reports/seo/CONTENT_EXECUTION_BATCHES.md` — order is mandatory: A -> B -> C -> D.

| batch | action groups | items |
|---|---|---|
| A - TECHNICAL | TECHNICAL_FIX, INDEX_RECOVERY | 14 |
| B - SEO CONTENT | TITLE_META_UPDATE, CONTENT_REFRESH, CONTENT_EXPANSION, INTERNAL_LINK, FAQ_EXPANSION | 18 |
| C - COMMERCIAL | COMMERCIAL_OPTIMIZATION | 2 |
| D - NEW CONTENT | NEW_CONTENT | 0 |
| MONITOR | MONITOR (queued until more data) | rest |

Priority tier distribution across 48 items: P0=4, P1=5, P2=4, P3=6, P4=29.

## 4. TOP 5 commercial pages

`reports/seo/TOP_5_COMMERCIAL_PAGES.md` — aggregated from the 16 commercial entries (no affiliate added):

1. /posts/144-hour-visa-free-transit-guide — 31 imp / pos 62.8 — SafetyWing present — add visa-related commercial framing
2. /posts/2026-05-25-china-high-speed-rail-how-to-book-tickets — 30 imp / pos 34.9 — NO affiliate — booking/fare comparison gap
3. /posts/how-to-use-wechat-pay-as-a-foreigner — 10 imp / pos 65.7 — Klook present — payment/eSIM angle
4. /7-day-china-itinerary — 3 imp / pos 9.3 — no affiliate — itinerary + booking links
5. /internet — 3 imp / pos 83.7 — no affiliate — eSIM/VPN monetization review

Affiliate check: Booking / Klook / Aviasales / NordVPN / SafetyWing scanned read-only; no new partner.

## 5. TOP 5 new content ideas

`reports/seo/TOP_5_NEW_CONTENT_IDEAS.md` — selected from 14 evidence-backed candidates:

1. china high speed rail tickets (HOW_TO, HIGH, TRANSPORT)
2. china high speed train tickets (HOW_TO, MEDIUM, TRANSPORT)
3. china bound (GUIDE, MEDIUM, OTHER)
4. chinabound (GUIDE, MEDIUM, OTHER)
5. chinabound.online (GUIDE, MEDIUM, OTHER)

Caveat: most candidates' evidence is "query lands on a NOT-indexed page - INDEX_FIX first"; new content is therefore the LAST batch and only 5 qualify. No article created.

## 6. Do-not-do-yet

`reports/seo/CONTENT_DO_NOT_DO_YET.md` — 10 guardrails: no bulk article edits, no bulk canonical changes, no one-pass title rewrites, no extreme decisions on 3 clicks, no mass new-content production, no parallel affiliate experiments, no bulk legacy-persona edits, no auto sitemap/robots changes, no bulk indexing requests, no affiliate URL/UTM changes.

## 7. LOW_DATA_WARNING

- 28d clicks = 3, CTR = 0.26%, impressions = 1168 — search data is early-stage.
- Priority Score reflects technical + demand + business evidence, NOT a Google ranking guarantee.
- First batch decisions are based on verifiable evidence (canonical conflicts, GSC coverage states, impression/position clusters).
- Re-score after two consecutive data windows; treat CTR-based moves as hypotheses.

## 8. Tests

- `tests/test_content_priority_engine.py`: 12 tests — score bounds, technical>content, indexed vs not indexed, commercial weighting, low data guard, deterministic output, tie breaker, Rule A floor, Rule F exemption, artifacts parseable, helpers, no-LLM dependency.
- Full suite: **154 passed, 0 failed, 0 skipped**.
- `hugo --gc --minify`: exit 0.
- `content_id_audit --strict`: PASS (57 posts).
- Workflow YAML: 18/18 valid.
- Secret scan: this round's files = 0 hits.

## 9. Git commit

- commit message: `feat: add content prioritization engine`
- Scope: engine + tests + reports only (no article / front matter / layout / hugo.toml changes).
- Pushed as normal fast-forward (no force).

## 10. Next recommendation

- Execute BATCH A first: 4 canonical fixes + index-recovery items, one page per review cycle, verify in GSC URL Inspection between changes.
- Then BATCH B starting with 144-hour visa-free transit title/meta test.
- Re-score after 2 data windows (P1-GROWTH-06+).

---

## Final status

**P1-GROWTH-04 = PASS**

Next: **P1-GROWTH-05 FIRST CONTENT ACTION**
