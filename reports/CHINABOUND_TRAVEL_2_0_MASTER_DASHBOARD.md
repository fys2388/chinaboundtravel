# ChinaBound Travel 2.0 — Master Dashboard

- Generated: 2026-08-17 | as_of: 2026-08-17
- Alert level: **YELLOW**
- Single source of truth: reports/management/REPORTING_SNAPSHOT.json

## Latest period reports

| Period | Report |
|---|---|
| Daily | reports/management/daily/CHINABOUND_TRAVEL_2_0_DAILY.md |
| Weekly | reports/management/weekly/CHINABOUND_TRAVEL_2_0_WEEKLY.md |
| Monthly | reports/management/monthly/CHINABOUND_TRAVEL_2_0_MONTHLY.md |
| Quarterly | reports/management/quarterly/CHINABOUND_TRAVEL_2_0_QUARTERLY.md |
| Yearly | reports/management/yearly/CHINABOUND_TRAVEL_2_0_YEARLY.md |

## Current KPI baseline (2.0)

| KPI | Value | Data source |
|---|---|---|
| published_posts | 60 posts | CACHED |
| content_id_coverage | 60 posts | CACHED |
| sessions_28d | 166 sessions | CACHED |
| pageviews_28d | 374 pageviews | CACHED |
| gsc_impressions_28d | 234 impressions | CACHED |
| gsc_clicks_28d | 0 clicks | CACHED |
| affiliate_clicks_28d | 0 clicks | CACHED |
| legacy_persona_pages | 25 posts | LOCAL |
| logo_favicon_status | LOGO_REPLACEMENT_READY | LOCAL |

## Current experiments

| ID | Status | Sample |
|---|---|---|
| REV001 | RUNNING | INSUFFICIENT_SAMPLE |
| REV002 | RUNNING | - |
| REV003 | PENDING | - |
| DRIVE-001 | RUNNING | INSUFFICIENT_SAMPLE |
| GROWTH05-CTR-001 | RUNNING | INSUFFICIENT_SAMPLE |
| GROWTH07B-TECH-001 | WAITING_RECRAWL | INSUFFICIENT_SAMPLE |
| GROWTH07C-INDEX-001 | WAITING_RECRAWL | INSUFFICIENT_SAMPLE |

## Current commercial clusters

| Cluster | Status | Score | Impressions 28d | Revenue |
|---|---|---|---|---|
| China Transportation | READY | 77.0 | 321 | NULL |
| China Payment | HOLD | 64.0 | 85 | NULL |
| China Connectivity | HOLD | 39.0 | 0 | NULL |

## Current blockers

- Revenue API absent -> revenue NULL
- 6 HIGH canonical conflicts (technical review pending)
- GROWTH07B / GROWTH07C WAITING_RECRAWL
- No fresh GSC pull since 2026-08-16

## Growth Control Plane (P1-GROWTH-30)

- Canonical content count: **58**（58 posts vs 60 inventory rows；2 行为草稿历史变体，不计入发布内容）
- Trust decision model: 294 AUTO_FIX / 89 SAFE_NORMALIZE / 479 FACT_CHECK_REQUIRED / 0 NO_CHANGE
- Unified queue: reports/management/GROWTH_PRIORITY_QUEUE.csv
- Next 7 days: reports/management/NEXT_7_DAY_GROWTH_QUEUE.csv
- Social metrics readiness: **PARTIAL**（缺 website_sessions / engaged_sessions / affiliate_clicks / revenue）

## Alerts

# ChinaBound Travel 2.0 — Management Alerts

- Generated: 2026-08-17
- Overall level: **YELLOW**

| Level | Meaning |
|---|---|
| GREEN | no action needed |
| YELLOW | attention / low data / open queues |
| ORANGE | escalate within the week |
| RED | act immediately |

## RED

- none

## ORANGE

- none

## YELLOW

- LOW_DATA_WARNING (9 reasons): affiliate_funnel.affiliate_clicks_28d: sample below guard; affiliate_funnel.click_rate: sample below guard; affiliate_funnel.clicks_per_1000_sessions: sample below guard; affiliate_funnel.cta_impressions: sample below guard
- 6 HIGH canonical conflicts awaiting technical review
- 25 legacy-persona posts remaining
- WAITING_RECRAWL: GROWTH07B-TECH-001, GROWTH07C-INDEX-001

## GREEN

- none

## Trigger definitions

- Traffic drop / indexing drop / revenue anomaly / experiment failure / production outage / secret-security issue / brand regression: detected only when snapshot evidence exists.
- Every alert below the level of RED is advisory; no WIN/LOSE or success/failure claims on insufficient data.

