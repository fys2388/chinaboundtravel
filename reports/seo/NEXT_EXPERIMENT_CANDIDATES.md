# Next Experiment Candidates (Top 5 — NOT executed this round)

- Date: 2026-08-16
- Source: `reports/seo/TOP_10_CONTENT_PRIORITIES.md` (GROWTH-04)
- LOW_DATA_WARNING: 28d site clicks = 3. Candidates with near-zero impressions are de-prioritized regardless of priority score, per measurement-loop guard.

| # | content_id | title | url | issue | expected metric | recommended experiment | risk |
|---|---|---|---|---|---|---|---|
| 1 | cbt-17c6738ffb32 | China Transportation Guide: Trains, Subways & Taxis | /posts/china-transportation-complete-guide-trains-subways-taxis-and-more/ | INDEXED, 107 imp, 0 clicks, pos 22.33 (mid-position); TRANSPORT commercial | CTR; position 4-20 entry | TITLE_META + INTERNAL_LINK (anchor "China transportation guide") | Low; canonical cluster already verified correct in GROWTH-05 |
| 2 | cbt-255af4ed003a | WeChat Pay for Foreigners: Setup Guide & Mistakes | /posts/wechat-pay-for-foreigners-step-by-step-setup-and-common-mistakes-to-avoid-guide/ | NOT_INDEXED (alternate), PAYMENT high commercial, pos 11 on 1 imp | Index status; impressions | WECHAT_PAY_DECISION (Differentiate or Merge) — depends on GROWTH-07 owner decision | Medium; requires content edit per decision |
| 3 | cbt-dfe3904705ea | China Travel Safety 2026: Guide for Travelers | /posts/is-china-safe-for-tourists-2026-honest-safety-assessment/ | INDEXED, 7 imp, pos 42.14, TRAVEL_GUIDE | CTR (low data) | TITLE_META (monitor) | Low; very small sample — do not over-weight |
| 4 | cbt-95d9a1b95440 | China Travel Guide: July 2026 Updates & Visa Rules | /posts/chinabound-travel-guide-2026-07-monthly-update/ | INDEXED, 0 imp | impressions (baseline) | MONITOR (await data) | Low |
| 5 | cbt-acae8a973429 | Foodie's Guide to China: Dishes You Must Try | /posts/food-recommendations-guide/ | INDEXED, 0 imp | impressions (baseline) | MONITOR (await data) | Low |

## Data note (outside TOP-10)

`/posts/china-extends-144-hour-visa-free-transit-policy-to-more-countries/` shows 87 impressions / pos 41.87 in raw 28d data but is not in TOP-10. Add it to the next prioritization run (GROWTH-04 re-run) before choosing the next TITLE_META experiment.

## Priority signal used

- Position 4-20: only WeChat setup guide (pos 11, 1 imp) — sample too small to act alone.
- Meaningful impressions: Transportation (107), 144h policy page (87).
- Commercial intent: TRANSPORT / PAYMENT pages ranked above TRAVEL_GUIDE for next experiment.
- No candidate was promoted purely on priority score with 0 impressions.
