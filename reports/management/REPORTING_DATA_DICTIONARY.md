# ChinaBound Travel 2.0 — Reporting Data Dictionary

- Generated: 2026-08-17
- Canonical artifact: reports/management/REPORTING_SNAPSHOT.json (scripts/reporting_kpi_engine.py)
- Every KPI below exists in the snapshot with the exact fields listed here.

Fields per metric: name | meaning | source | data source type | calculation | update frequency | baseline | valid period

## A. Traffic

| name | meaning | source | type | calculation | frequency | baseline | valid period |
|---|---|---|---|---|---|---|---|
| users_28d | GA4 unique users, 28d window | GA4 user dimension (not persisted) | NOT_AVAILABLE | sum of active users | daily | NULL | NULL |
| sessions_28d | GA4 sessions, 28d window | reports/revenue/REVENUE_DASHBOARD.md (GA4_API fetch 2026-08-17) | CACHED | GA4 totalSessions | daily | 162 (REV001_BASELINE 07-19..08-15) | 2026-07-20..2026-08-16 |
| pageviews_28d | GA4 pageviews, 28d window | same | CACHED | GA4 totalPageviews | daily | 365 | 2026-07-20..2026-08-16 |
| engagement_rate_28d | GA4 engagement rate, 28d window | not persisted | NOT_AVAILABLE | engaged sessions / sessions | daily | NULL | NULL |
| source_channel_mix | sessions by channel group | not persisted | NOT_AVAILABLE | group by sessionDefaultChannelGroup | weekly | NULL | NULL |

## B. SEO / GSC

| name | meaning | source | type | calculation | frequency | baseline | valid period |
|---|---|---|---|---|---|---|---|
| gsc_clicks_28d | GSC clicks, 28d window (query-level) | reports/seo/SEO_BASELINE_2026-08.md (GSC API 2026-08-15) | CACHED | sum clicks | daily | 0 | 2026-07-19..2026-08-13 |
| gsc_impressions_28d | GSC impressions, 28d window (query-level) | same | CACHED | sum impressions | daily | 0 | same |
| gsc_ctr_28d | GSC CTR | same | CACHED | clicks / impressions * 100 | daily | 0.0 | same |
| gsc_avg_position_28d | GSC average position | same | CACHED | average position | daily | NULL | same |
| indexed_pages | GSC UI indexed total | reports/seo/INDEX_COVERAGE_BASELINE.md (UI 2026-08-16) | CACHED | UI index count | weekly | NULL | 2026-08-16 |
| not_indexed_pages | GSC UI not-indexed total | same | CACHED | UI index count | weekly | NULL | 2026-08-16 |
| inspected_urls | URLs inspected by URL Inspection API | reports/seo/url_inspection_results.json | CACHED | count of inspected URLs | weekly | NULL | 2026-08-16 |
| inspection_pass | URLs with verdict PASS | same | CACHED | count verdict == PASS | weekly | NULL | 2026-08-16 |
| page_level_clicks_28d | inventory sum of clicks_28d | reports/seo/CONTENT_SEO_INVENTORY.csv | CACHED | sum over inventory | daily | 3 | 2026-07-19..2026-08-15 |
| page_level_impressions_28d | inventory sum of impressions_28d | same | CACHED | sum over inventory | daily | 1168 | same |
| pages_newly_indexed | pages newly indexed this period | requires prior snapshot | NOT_AVAILABLE | delta of indexed set | weekly | NULL | NULL |
| pages_losing_visibility | pages losing visibility | requires prior snapshot | NOT_AVAILABLE | delta of impressions/position | weekly | NULL | NULL |
| top_opportunities | top content opportunities | reports/seo/content_opportunity_scores.csv | CACHED | top 3 by opportunity_score | weekly | NULL | same |

## C. Content assets

| name | meaning | source | type | calculation | frequency | baseline | valid period |
|---|---|---|---|---|---|---|---|
| published_posts | published posts | reports/seo/CONTENT_SEO_INVENTORY.csv + content_id_audit | CACHED | count rows (60/60 content_id PASS) | daily | 60 | 2026-08-17 |
| content_id_coverage | posts with unique content_id | content_id_audit --strict | CACHED | posts with content_id / total | daily | 60/60 | 2026-08-17 |
| new_pages_30d | posts published in last 30 days | inventory published_date | CACHED | count published_date >= as_of - 30d | daily | NULL | rolling |
| updated_pages | pages updated this period | no updated_at field | NOT_AVAILABLE | count content changes | weekly | NULL | NULL |
| indexed_posts | inventory posts INDEXED | inventory indexed_status | CACHED | count INDEXED | daily | NULL | 2026-08-17 |
| asset_tier_distribution | A/B/C/D opportunity tiers | content_opportunity_scores.csv | CACHED | count by tier | weekly | B=8/C=24/D=28 | 2026-08-17 |
| opportunity_pipeline | content opportunity feed size | CONTENT_OPPORTUNITY_FEED.json | CACHED | feed item count | weekly | 51 | 2026-08-17 |
| legacy_persona_pages | posts with legacy persona phrases | P1_BRAND_02_LEGACY_PERSONA_REVIEW.md | LOCAL | legacy phrase hit count | weekly | 25 | 2026-08-17 |
| migrated_persona_pages | posts migrated to editorial persona | P1_BRAND_03_LEGACY_PILOT_REPORT.md | LOCAL | pilot articles migrated | weekly | 0 | 2026-08-16 |
| canonical_conflicts | HIGH canonical conflict count | CANONICAL_CONFLICT_QUEUE.md | CACHED | rows with URL | weekly | 6 | 2026-08-16 |
| duplicate_risk_rows | inventory rows duplicate_count > 1 | content_opportunity_scores.csv | CACHED | count duplicate_count > 1 | weekly | NULL | 2026-08-17 |
## D. Brand 2.0

| name | meaning | source | type | calculation | frequency | baseline | valid period |
|---|---|---|---|---|---|---|---|
| editorial_persona_compliance | brand layers passing editorial audit | reports/P1_BRAND_02_BRAND_IDENTITY_AUDIT.md | LOCAL | PASS count over 13 layers | weekly | 11/13 | 2026-08-17 |
| legacy_persona_remaining | posts still containing legacy phrases | P1_BRAND_02_LEGACY_PERSONA_REVIEW.md | LOCAL | legacy phrase hit count | weekly | 25 | 2026-08-17 |
| migrated_this_period | migrations in 2026-08-16 pilot | P1_BRAND_03_LEGACY_PILOT_REPORT.md | LOCAL | pilot count | weekly | 0 | 2026-08-16 |
| logo_favicon_status | logo/favicon migration status | P1_BRAND_04_LOGO_REPLACEMENT_READY.md + docs/AI_CONTEXT.md | LOCAL | favicon.png replaced 08-17; svg retained | weekly | WAITING | 2026-08-17 |
| core_brand_compliance | core brand compliance | P1_BRAND_02_BRAND_IDENTITY_AUDIT.md | LOCAL | no violations / editorial present | weekly | WARN | 2026-08-17 |
| brand_asset_avatar | Joran avatar assets | docs/AI_CONTEXT.md | LOCAL | webp + png present | weekly | PRESENT | 2026-08-17 |

## E. Affiliate funnel

| name | meaning | source | type | calculation | frequency | baseline | valid period |
|---|---|---|---|---|---|---|---|
| cta_inventory_rows | CTA inventory rows | reports/revenue/AFFILIATE_FUNNEL_INVENTORY.csv | CACHED | row count | weekly | 277 | 2026-08-17 |
| cta_inventory_pages | pages with CTA coverage | same | CACHED | unique URLs | weekly | 45 | 2026-08-17 |
| affiliate_clicks_28d | GA4 affiliate_click events 28d | REVENUE_DASHBOARD.md (GA4_API 2026-08-17) | CACHED | event count | daily | 0 | 2026-07-20..2026-08-16 |
| cta_impressions | CTA impressions (REV001 scope) | REV001_FUNNEL_METRICS.csv | CACHED | event count | daily | 0 | 2026-08-17 |
| outbound_success | outbound events (REV001 scope) | same | CACHED | event count | daily | 0 | 2026-08-17 |
| click_rate | CTA click rate (REV001 scope) | same | CACHED | clicks / impressions * 100 | daily | 0.0 | 2026-08-17 |
| outbound_rate | outbound rate (REV001 scope) | same | CACHED | outbound / clicks * 100 | daily | 0.0 | 2026-08-17 |
| clicks_per_1000_sessions | clicks per 1000 sessions (sitewide) | REV001_FUNNEL_METRICS + REVENUE_DASHBOARD | CACHED | clicks / sessions * 1000 | daily | 0.0 | 2026-07-20..2026-08-16 |
| partner_breakdown | partner pages/link counts/status | AFFILIATE_PARTNER_INVENTORY.csv | CACHED | per-partner aggregation | weekly | NULL | 2026-08-17 |

## F. Revenue

| name | meaning | source | type | calculation | frequency | baseline | valid period |
|---|---|---|---|---|---|---|---|
| revenue | affiliate revenue | no API | NOT_AVAILABLE | sum of confirmed earnings | daily | NULL | NULL |
| orders_conversions | affiliate orders | no API | NOT_AVAILABLE | count confirmed conversions | daily | NULL | NULL |
| commission | commission earned | no API | NOT_AVAILABLE | sum of commission | daily | NULL | NULL |
| rpm | revenue per 1000 pageviews | no API | NOT_AVAILABLE | revenue / pageviews * 1000 | daily | NULL | NULL |
| revenue_per_1000_sessions | revenue per 1000 sessions | no API | NOT_AVAILABLE | revenue / sessions * 1000 | daily | NULL | NULL |

All revenue KPIs are NULL (REVENUE_NOT_AVAILABLE) until a real revenue API exists.

## G. Experiments

Records (per experiment): experiment_id, display_name, type, page, content_id, start_date, observation_days, primary_metric, baseline, current, delta, sample (sample_status), status, data_source_type.

Sources:
- reports/revenue/EXPERIMENT_COMPARISON.csv (REV001, DRIVE-001, GROWTH05-CTR-001, GROWTH07B-TECH-001, GROWTH07C-INDEX-001)
- reports/revenue/REV002_EXPERIMENT_REGISTRY.csv
- reports/revenue/REV003_EXPERIMENT_REGISTRY.csv
- reports/revenue/DRIVE_EXPERIMENT_REGISTRY.csv

| experiment_id | type | page / content_id | status (registry) | sample |
|---|---|---|---|---|
| REV001 | CTA_PLACEMENT | Food Delivery / cbt-e464169c4991 | RUNNING | INSUFFICIENT_SAMPLE (1d) |
| REV002 | CTA_PLACEMENT | Transportation Guide / cbt-17c6738ffb32 | RUNNING (frozen) | - |
| REV003 | CTA_COPY | Transportation Guide | PENDING | - |
| DRIVE-001 | SITE_WIDE_DRIVE | Site-wide | RUNNING | INSUFFICIENT_SAMPLE (1d) |
| GROWTH05-CTR-001 | CTR_TITLE_META | 144-Hour Visa / cbt-b4ff4381a014 | RUNNING | INSUFFICIENT_SAMPLE |
| GROWTH07B-TECH-001 | TECHNICAL_INDEX_FIX | High-Speed Rail / cbt-cc4549872c92 | WAITING_RECRAWL | INSUFFICIENT_SAMPLE |
| GROWTH07C-INDEX-001 | INDEX_RECOVERY | WeChat Pay weak / cbt-255af4ed003a | WAITING_RECRAWL | INSUFFICIENT_SAMPLE |

## H. Commercial clusters

Records (per cluster): cluster, intent, status, priority, score, impressions_28d, best_position, affiliate_partners, affiliate_fit_ratio, experiments, authority, indexed_pages, commercial_pages, revenue.

Sources: reports/revenue/COMMERCIAL_CLUSTER_PRIORITY.csv + COMMERCIAL_CLUSTER_PROGRESS.md.

| cluster | intent | status | score | impressions_28d | experiments |
|---|---|---|---|---|---|
| China Transportation | TRAIN | READY | 77 | 321 | REV002, REV003, REV004(candidate) |
| China Payment | PAYMENT | HOLD | 64 | 85 | GROWTH07C-INDEX-001, Payment->eSIM(WAIT) |
| China Connectivity | INTERNET | HOLD | 39 | 0 | none |

indexed_pages / commercial_pages / revenue per cluster: NULL (NOT_AVAILABLE — no per-cluster mapping artifact).

## I. Operations

| name | meaning | source | type | calculation | frequency | baseline | valid period |
|---|---|---|---|---|---|---|---|
| automation_health | workflow YAML/name validation | tests/test_workflow_yaml.py + test_workflow_names.py | LOCAL | tests green | weekly | PASS | 2026-08-17 |
| workflow_health | workflow definitions valid | tests/test_workflow_yaml.py | LOCAL | tests green | weekly | PASS | 2026-08-17 |
| deployment_health | latest recorded production verification | reports/2.0_REPORTING_RECONCILIATION.md | CACHED | last live 200/canonical/Drive checks | weekly | NULL | 2026-08-16 |
| backup_rollback | backup/rollback status | no artifact | NOT_AVAILABLE | n/a | weekly | NULL | NULL |
| security_scan | secret scan status | tests/test_no_hardcoded_secrets.py + test_secret_name_contract.py | LOCAL | tests green | weekly | PASS | 2026-08-17 |
| okr_plan_items | active OKR plan items | reports/okr_progress/weekly_2026-W34.json | LOCAL | plan entry count | weekly | NULL | 2026-W34 |
