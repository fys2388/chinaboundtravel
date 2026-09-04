# ChinaBound Travel 2.0 — DAILY REPORT

- Generated: 2026-09-04 (Asia/Shanghai)
- as_of: 2026-09-04
- Data source: ONE unified snapshot — reports/management/REPORTING_SNAPSHOT.json
- Labels: LIVE / CACHED / LOCAL / NOT_AVAILABLE
- Revenue: NULL (REVENUE_NOT_AVAILABLE) — never fabricated
- Low data: True — see ALERTS.md
- Period comparison: DoD (INSUFFICIENT_SAMPLE until a prior snapshot exists)
- Consistency: same KPI definitions / experiment IDs / content count / brand status across all periods

## Executive status

- Published posts: 61 posts
- Sessions 28d: 166 sessions | Pageviews 28d: 374 pageviews
- GSC clicks 28d: 0 clicks | Impressions: 234 impressions
- Revenue: NULL (REVENUE_NOT_AVAILABLE)
- Drive: ACTIVE (DRIVE-001 RUNNING since 2026-08-16)
- Overall alert level: YELLOW (low sample + open recovery queues, see ALERTS.md)


## 1. Traffic today

Daily window metrics are NOT available (no daily GA4 pull). 28d rolling figures shown with fetch date.

## Traffic

| KPI | Value | Baseline | Source type | Status |
|---|---|---|---|---|
| users_28d | NULL | NULL | NOT_AVAILABLE | NOT_AVAILABLE |
| sessions_28d | 166 sessions | 162 | CACHED | OK |
| pageviews_28d | 374 pageviews | 365 | CACHED | OK |
| engagement_rate_28d | NULL | NULL | NOT_AVAILABLE | NOT_AVAILABLE |

## 2. SEO changes

Change vs previous day: **INSUFFICIENT_SAMPLE** (no prior daily snapshot).

## SEO / GSC

| KPI | Value | Source type | Status |
|---|---|---|---|
| gsc_clicks_28d | 0 clicks | CACHED | OK |
| gsc_impressions_28d | 234 impressions | CACHED | OK |
| gsc_ctr_28d | 0.0 % | CACHED | INSUFFICIENT_SAMPLE |
| gsc_avg_position_28d | 56.5 position | CACHED | OK |
| indexed_pages | 69 pages | CACHED | OK |
| not_indexed_pages | 89 pages | CACHED | OK |
| inspected_urls | 98 urls | CACHED | OK |
| inspection_pass | 49 urls | CACHED | OK |
| page_level_clicks_28d | 2 clicks | CACHED | INSUFFICIENT_SAMPLE |
| page_level_impressions_28d | 1073 impressions | CACHED | OK |
| pages_newly_indexed | NULL | NOT_AVAILABLE | NOT_AVAILABLE |
| pages_losing_visibility | NULL | NOT_AVAILABLE | NOT_AVAILABLE |

Top opportunities: China 144-Hour Visa-Free Transit (2026 Guide) (77.0, B); China Transportation Guide for European Travelers (75.0, B); China Transportation Guide: Trains, Subways & Taxis (75.0, B)

## 3. Indexing changes

- Indexed: 69 pages | Not indexed: 89 pages (GSC UI 2026-08-16, CACHED)
- Newly indexed this period: NULL (requires prior snapshot: INSUFFICIENT_SAMPLE)
- Losing visibility: NULL (INSUFFICIENT_SAMPLE)

## 4. Revenue / affiliate events

## Affiliate funnel

| KPI | Value | Source type | Status |
|---|---|---|---|
| cta_inventory_rows | 278 rows | CACHED | OK |
| cta_inventory_pages | 45 pages | CACHED | OK |
| affiliate_clicks_28d | 0 clicks | CACHED | INSUFFICIENT_SAMPLE |
| cta_impressions | 0 impressions | CACHED | INSUFFICIENT_SAMPLE |
| outbound_success | 0 events | CACHED | INSUFFICIENT_SAMPLE |
| click_rate | 0.0 % | CACHED | INSUFFICIENT_SAMPLE |
| outbound_rate | 0.0 % | CACHED | INSUFFICIENT_SAMPLE |
| clicks_per_1000_sessions | 0.0 clicks/1000 | CACHED | INSUFFICIENT_SAMPLE |

### Revenue

Revenue: see snapshot.

## 5. Experiment events

All experiments in observation window; no WIN/LOSE declarations.

## Experiments

| ID | Type | Page | Start | Days | Primary metric | Baseline | Current | Delta | Sample | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| REV001 | CTA_PLACEMENT | Chinese Food Delivery: Meituan & Ele.me Guide | 2026-08-16 | 1 | 0.0 | 0.0 | 0.0 | 0.0 | INSUFFICIENT_SAMPLE | RUNNING |
| REV002 | CTA_PLACEMENT | China Transportation Guide | 2026-08-16 | - | affiliate_click_rate | NULL | NULL | NULL | - | RUNNING |
| REV003 | CTA_COPY | China Transportation Guide | 2026-08-16 | - | affiliate_click_rate | NULL | NULL | NULL | - | PENDING |
| DRIVE-001 | SITE_WIDE_DRIVE | Site-wide Travelpayouts Drive | 2026-08-16 | 1 | 0.0 | 0.0 | 0.0 | 0.0 | INSUFFICIENT_SAMPLE | RUNNING |
| GROWTH05-CTR-001 | CTR_TITLE_META | 144-Hour Visa | 2026-08-16 | 0 | 0.0 | 0.0 | 0.0 | 0.0 | INSUFFICIENT_SAMPLE | RUNNING |
| GROWTH07B-TECH-001 | TECHNICAL_INDEX_FIX | High-Speed Rail Booking | 2026-08-16 | 0 | 0.0 | 0.0 | 0.0 | 0.0 | INSUFFICIENT_SAMPLE | WAITING_RECRAWL |
| GROWTH07C-INDEX-001 | INDEX_RECOVERY | WeChat Pay Weak | 2026-08-16 | 0 | 0.0 | 0.0 | 0.0 | 0.0 | INSUFFICIENT_SAMPLE | WAITING_RECRAWL |

Guard: observation < 28d or clicks < 20 => INSUFFICIENT_SAMPLE. No WIN/LOSE declarations on insufficient data.

## 6. Production health

## Operations

| KPI | Value | Source type | Status |
|---|---|---|---|
| automation_health | PASS | LOCAL | OK |
| workflow_health | PASS | LOCAL | OK |
| deployment_health | VERIFIED_2026-08-16 | CACHED | OK |
| backup_rollback | NULL | NOT_AVAILABLE | NOT_AVAILABLE |
| security_scan | PASS | LOCAL | OK |
| okr_plan_items | 13 items | LOCAL | OK |

## 7. Brand compliance changes

No brand changes today. Last brand event: P1-BRAND-04 favicon.png replacement 2026-08-17 (LOGO_REPLACEMENT_READY, favicon.svg retained).

## Brand 2.0

| KPI | Value | Source type |
|---|---|---|
| editorial_persona_compliance | NULL | LOCAL |
| legacy_persona_remaining | 0 posts | LOCAL |
| migrated_this_period | 3 posts | LOCAL |
| logo_favicon_status | LOGO_REPLACEMENT_READY | LOCAL |
| core_brand_compliance | WARN | LOCAL |
| brand_asset_avatar | PRESENT | LOCAL |

## 8. Alerts / anomalies

- LOW_DATA_WARNING: 8 low-data reasons (see ALERTS.md)
- Anomalies: none beyond expected low-sample state
- Blockers: canonical conflicts (6 HIGH), WAITING_RECRAWL x2, no revenue API, no fresh GSC pull since 2026-08-16

## 9. Today's actions

- Keep REV001 / REV002 / DRIVE-001 untouched until review gate 2026-09-13
- Monitor WAITING_RECRAWL experiments (WeChat Pay weak, High-Speed Rail)
- Plan fresh GSC + GA4 pull for next snapshot

