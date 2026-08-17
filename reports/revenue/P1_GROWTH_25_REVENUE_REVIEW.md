# P1-GROWTH-25 — Revenue & Experiment Review

- Generated: 2026-08-17
- Data sources: reports/revenue/ registry + baseline artifacts (CACHED); GA4 API snapshot 2026-08-17 (sitewide 28d: sessions 166 / pageviews 374 / affiliate_clicks 0); GSC cached snapshot 2026-08-16 (sitewide 234 impressions / 0 clicks); Revenue API: REVENUE_NOT_AVAILABLE
- Observation rule applied: observation < 28 days OR affiliate_clicks < 20 -> INSUFFICIENT_SAMPLE. No WIN/LOSE declarations. No revenue invented.

## REV001 — Food Delivery + Airalo (cbt-e464169c4991)

| item | value |
|---|---|
| baseline (2026-07-19..2026-08-15) | sessions 162; pageviews 365; affiliate_clicks 0; clicks/1000 0.0; GSC 159 imp / 0 clk / pos 19.55 |
| current (2026-08-17) | sitewide sessions 166 (+4); pageviews 374 (+9); affiliate_clicks 0 (delta 0); page-level NOT_AVAILABLE (DATA_SCOPE=sitewide) |
| delta | +4 sessions / +9 pageviews sitewide (not attributable to page); clicks 0 -> 0 |
| sample | 1 observation day (< 28d); affiliate_clicks 0 (< 20) |
| data source | CACHED baseline + GA4_API 2026-08-17 + GSC CACHED 2026-08-16 |
| decision | INSUFFICIENT_SAMPLE -> WAITING_REVIEW_GATE (gate >= 2026-09-13). CTA unchanged. |

## REV002 — Transportation + Trip.com mid-CTA (cbt-17c6738ffb32)

| item | value |
|---|---|
| baseline (2026-07-19..2026-08-15) | sessions/pageviews NULL (page-level not measured); affiliate_clicks 0; GSC 107 imp / 0 clk / pos 22.33; revenue NULL |
| current (2026-08-17) | FROZEN (no CTA changes since freeze); sitewide sessions 166 / pageviews 374 / affiliate_clicks 0 |
| delta | none measurable (page-level NOT_AVAILABLE; frozen) |
| sample | 1 observation day (< 28d); affiliate_clicks 0 (< 20) |
| data source | CACHED baseline + GA4_API 2026-08-17 + GSC CACHED 2026-08-16 |
| decision | INSUFFICIENT_SAMPLE -> WAITING_REVIEW_GATE (gate >= 2026-09-13). CTA unchanged. |

## DRIVE-001 — Site-wide Travelpayouts Drive

| item | value |
|---|---|
| status | ACTIVE (activation 2026-08-16; script INSTALLED_ONCE_ALL_PAGES, capacity FULL) |
| observation_days | 1 (< 28d) |
| CTA impressions | NOT_AVAILABLE (funnel cta_impressions below guard; not exposed in sitewide GA4 snapshot) |
| affiliate clicks | 0 (sitewide 28d GA4) |
| outbound | 0 / NOT_AVAILABLE (no outbound tracking yet) |
| revenue | NULL (REVENUE_NOT_AVAILABLE) |
| data source | TRAVELPAYOUTS_DRIVE_BASELINE.md (CACHED) + GA4_API 2026-08-17 |
| decision | INSUFFICIENT_SAMPLE -> KEEP_RUNNING. Drive NOT modified. |

## Consolidated status

| experiment | status | sample | decision |
|---|---|---|---|
| REV001 | RUNNING | INSUFFICIENT_SAMPLE (1d / 0 clicks) | WAITING_REVIEW_GATE |
| REV002 | RUNNING (FROZEN) | INSUFFICIENT_SAMPLE (1d / 0 clicks) | WAITING_REVIEW_GATE |
| DRIVE-001 | ACTIVE | INSUFFICIENT_SAMPLE (1d / 0 clicks) | KEEP_RUNNING |
| REV003 | PENDING | - | WAIT (needs REV002 gate) |

## Guards

- No CTA / placement / partner changes in this round.
- 2026-09-13 review gate applies to REV001 / REV002.
- Revenue stays NULL until a real affiliate revenue API exists.
