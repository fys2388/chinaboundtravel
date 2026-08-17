# ChinaBound Travel 2.0 — WEEKLY REPORT

- Generated: 2026-08-17 (Asia/Shanghai)
- as_of: 2026-08-17
- Data source: ONE unified snapshot — reports/management/REPORTING_SNAPSHOT.json
- Labels: LIVE / CACHED / LOCAL / NOT_AVAILABLE
- Revenue: NULL (REVENUE_NOT_AVAILABLE) — never fabricated
- Low data: True — see ALERTS.md
- Period comparison: WoW (INSUFFICIENT_SAMPLE until a prior snapshot exists)
- Consistency: same KPI definitions / experiment IDs / content count / brand status across all periods

## Executive status

- Published posts: 60 posts
- Sessions 28d: 166 sessions | Pageviews 28d: 374 pageviews
- GSC clicks 28d: 0 clicks | Impressions: 234 impressions
- Revenue: NULL (REVENUE_NOT_AVAILABLE)
- Drive: ACTIVE (DRIVE-001 RUNNING since 2026-08-16)
- Overall alert level: YELLOW (low sample + open recovery queues, see ALERTS.md)


## 1. Executive summary

Week in observation: 3 revenue experiments running (REV001, REV002, DRIVE-001), 2 index recoveries waiting for recrawl, 60-post inventory stable, revenue NULL.

## 2. Traffic

## Traffic

| KPI | Value | Baseline | Source type | Status |
|---|---|---|---|---|
| users_28d | NULL | NULL | NOT_AVAILABLE | NOT_AVAILABLE |
| sessions_28d | 166 sessions | 162 | CACHED | OK |
| pageviews_28d | 374 pageviews | 365 | CACHED | OK |
| engagement_rate_28d | NULL | NULL | NOT_AVAILABLE | NOT_AVAILABLE |

## 3. SEO / GSC

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

## 4. Content asset health

## Content asset health

| KPI | Value | Source type |
|---|---|---|
| published_posts | 60 posts | CACHED |
| content_id_coverage | 60 posts | CACHED |
| new_pages_30d | 19 posts | CACHED |
| updated_pages | NULL | NOT_AVAILABLE |
| indexed_posts | 47 posts | CACHED |
| asset_tier_distribution | {'B': 8, 'C': 24, 'D': 28} | CACHED |
| opportunity_pipeline | 51 items | CACHED |
| legacy_persona_pages | 25 posts | LOCAL |
| migrated_persona_pages | 3 posts | LOCAL |
| canonical_conflicts | 6 urls | CACHED |
| duplicate_risk_rows | 14 rows | CACHED |

## 5. Brand 2.0

## Brand 2.0

| KPI | Value | Source type |
|---|---|---|
| editorial_persona_compliance | 11/13 layers | LOCAL |
| legacy_persona_remaining | 25 posts | LOCAL |
| migrated_this_period | 3 posts | LOCAL |
| logo_favicon_status | LOGO_REPLACEMENT_READY | LOCAL |
| core_brand_compliance | WARN | LOCAL |
| brand_asset_avatar | PRESENT | LOCAL |

## 6. Affiliate funnel

## Affiliate funnel

| KPI | Value | Source type | Status |
|---|---|---|---|
| cta_inventory_rows | 277 rows | CACHED | OK |
| cta_inventory_pages | 45 pages | CACHED | OK |
| affiliate_clicks_28d | 0 clicks | CACHED | INSUFFICIENT_SAMPLE |
| cta_impressions | 0 impressions | CACHED | INSUFFICIENT_SAMPLE |
| outbound_success | 0 events | CACHED | INSUFFICIENT_SAMPLE |
| click_rate | 0.0 % | CACHED | INSUFFICIENT_SAMPLE |
| outbound_rate | 0.0 % | CACHED | INSUFFICIENT_SAMPLE |
| clicks_per_1000_sessions | 0.0 clicks/1000 | CACHED | INSUFFICIENT_SAMPLE |

## 7. Revenue

### Revenue

Revenue: **NULL** (REVENUE_NOT_AVAILABLE) — no affiliate revenue API; nothing fabricated.

| KPI | Value | Source type |
|---|---|---|
| revenue | NULL | NOT_AVAILABLE |
| orders_conversions | NULL | NOT_AVAILABLE |
| commission | NULL | NOT_AVAILABLE |
| rpm | NULL | NOT_AVAILABLE |
| revenue_per_1000_sessions | NULL | NOT_AVAILABLE |

## 8. Experiments

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

## 9. Commercial clusters

## Commercial clusters

| Cluster | Intent | Status | Priority | Score | Impressions 28d | Best pos | Affiliate fit | Experiments | Revenue |
|---|---|---|---|---|---|---|---|---|---|
| China Transportation | TRAIN | READY | A | 77.0 | 321 | 22.33 | 1.0 | REV002; REV003; REV004(candidate) | NULL |
| China Payment | PAYMENT | HOLD | B | 64.0 | 85 | 11.0 | 0.5 | GROWTH07C-INDEX-001; Payment->eSIM(WAIT) | NULL |
| China Connectivity | INTERNET | HOLD | C | 39.0 | 0 | 0.0 | 0.5 | none | NULL |

## 10. Completed work

- P1-REPORT-01: reporting baselines reconciled (60 posts, REV001 corrected, dashboards rebuilt)
- P1-BRAND-04: favicon.png replaced (LOGO_REPLACEMENT_READY)
- Engine re-runs on 60-post inventory: brand legacy, SEO opportunity/priority, revenue, commercial conversion

## 11. Blockers

- Revenue API absent -> revenue NULL (never fabricated)
- No fresh GSC pull since 2026-08-16
- 6 HIGH canonical conflicts await technical review
- GROWTH07B / GROWTH07C WAITING_RECRAWL

## 12. Next-week priorities

- Execute top content priorities (reports/seo/TOP_10_CONTENT_PRIORITIES.md)
- Fresh GSC/GA4 pull; refresh daily_search_performance + SEO snapshot reports
- Resolve canonical conflict queue (6 HIGH)
- Continue brand legacy persona migration beyond the 3 pilots

### Period comparison (WoW)

All metrics: **INSUFFICIENT_SAMPLE** — no prior unified snapshot exists yet. Comparisons become available once a second snapshot is generated.

