# ChinaBound Travel — Report Index

- Generated: 2026-08-17 (P1-REPORT-02)
- Purpose: classify every important report so managers and agents know what to trust and what to ignore.
- Status values: CURRENT / HISTORICAL / STALE / SUPERSEDED.
  - CURRENT: reflects current 2.0 state; may be used as source of truth.
  - HISTORICAL: frozen snapshot of a past decision/experiment; keep for the record, do not use as current state.
  - STALE: no longer matches current state; rebuild or supersede before use.
  - SUPERSEDED: replaced by a newer artifact (listed in "superseded by").
- Source of truth: the file a report derives its numbers from.
- Completed tasks (PASS) never reappear in action lists (see REPORTING_STATUS_MODEL.md §3).

## 2.0 Unified reporting system (CURRENT)

| Report | Status | Purpose | Source of truth |
|---|---|---|---|
| reports/management/REPORTING_SNAPSHOT.json | CURRENT | single KPI source for all periods | all artifacts listed in data dictionary |
| reports/management/REPORTING_DATA_DICTIONARY.md | CURRENT | metric field definitions | snapshot schema |
| reports/management/REPORTING_KPI_DEFINITIONS.md | CURRENT | formulas and rollup rules | snapshot schema |
| reports/management/REPORTING_STATUS_MODEL.md | CURRENT | labels / states / guards | snapshot schema |
| reports/CHINABOUND_TRAVEL_2_0_MASTER_DASHBOARD.md | CURRENT | management single source of truth | REPORTING_SNAPSHOT.json |
| reports/management/ALERTS.md | CURRENT | alert levels and reasons | REPORTING_SNAPSHOT.json |
| reports/management/daily/…DAILY.md | CURRENT | operations control / anomaly detection | REPORTING_SNAPSHOT.json |
| reports/management/weekly/…WEEKLY.md | CURRENT | growth / experiments / content value | REPORTING_SNAPSHOT.json |
| reports/management/monthly/…MONTHLY.md | CURRENT | business review / MoM | REPORTING_SNAPSHOT.json |
| reports/management/quarterly/…QUARTERLY.md | CURRENT | strategic review | REPORTING_SNAPSHOT.json |
| reports/management/yearly/…YEARLY.md | CURRENT | annual / valuation review | REPORTING_SNAPSHOT.json |

## Core source-of-truth artifacts (CURRENT)

| Report | Status | Purpose | Source of truth |
|---|---|---|---|
| docs/AI_CONTEXT.md | CURRENT | project context for agents | repository state |
| reports/2.0_REPORTING_RECONCILIATION.md | CURRENT | audit of report-vs-state drift (P1-REPORT-00) | source-of-truth files |
| reports/P1_REPORT_01_2_0_REPORTING_REBUILD.md | CURRENT | reporting baseline rebuild record | engines + inventory |
| reports/P1_REPORT_02_UNIFIED_MANAGEMENT_REPORTING.md | CURRENT | this task's final report | unified system |
| reports/seo/CONTENT_SEO_INVENTORY.csv | CURRENT | single content inventory (60 rows) | content_id_audit |
| reports/seo/content_opportunity_scores.csv | CURRENT | content opportunity scoring | content_opportunity_engine |
| reports/seo/CONTENT_OPPORTUNITY_FEED.json | CURRENT | opportunity feed | content_opportunity_engine |
| reports/seo/INDEX_COVERAGE_BASELINE.md | CURRENT | GSC UI index totals (08-16) | GSC UI / inspection API |
| reports/seo/url_inspection_results.json | CURRENT | per-URL inspection verdicts (08-16) | URL Inspection API |
| reports/seo/SEO_BASELINE_2026-08.md | CURRENT | GSC 28d/90d baseline (08-15) | GSC API |
| reports/seo/EXPERIMENT_REGISTRY.csv | CURRENT | GROWTH-05 CTR registry | growth experiment |
| reports/revenue/REVENUE_EXPERIMENT_REGISTRY.csv | CURRENT | REV001 registry | revenue_experiment_review |
| reports/revenue/REV002_EXPERIMENT_REGISTRY.csv | CURRENT | REV002 registry | rev002 review prep |
| reports/revenue/REV003_EXPERIMENT_REGISTRY.csv | CURRENT | REV003 registry | candidate analysis |
| reports/revenue/DRIVE_EXPERIMENT_REGISTRY.csv | CURRENT | DRIVE-001 registry | revenue_measurement |
| reports/revenue/EXPERIMENT_COMPARISON.csv | CURRENT | unified experiment comparison (08-17) | revenue_experiment_review |
| reports/revenue/REVENUE_EXPERIMENT_DASHBOARD.md | CURRENT | revenue experiment dashboard (08-17) | registries + GA4 |
| reports/revenue/REVENUE_DASHBOARD.md | CURRENT | GA4/Drive baseline (08-17) | GA4_API |
| reports/revenue/PRE_DRIVE_BASELINE.csv | CURRENT | pre-drive per-page baseline | revenue_measurement |
| reports/revenue/TOP_COMMERCIAL_PAGES_DRIVE.md/.csv | CURRENT | commercial page ranking for Drive | revenue_measurement |
| reports/revenue/AFFILIATE_FUNNEL_INVENTORY.csv | CURRENT | CTA inventory (277 rows / 45 pages) | affiliate_funnel_audit |
| reports/revenue/AFFILIATE_PARTNER_INVENTORY.csv | CURRENT | partner coverage | affiliate_funnel_audit |
| reports/revenue/COMMERCIAL_CLUSTER_PRIORITY.csv | CURRENT | cluster scoring | commercial cluster expansion |
| reports/revenue/REV001_FUNNEL_METRICS.csv | CURRENT | REV001 funnel events | revenue measurement |
| reports/P1_BRAND_02_BRAND_IDENTITY_AUDIT.md | CURRENT | brand layer audit (08-17) | brand_identity_audit |
| reports/P1_BRAND_02_LEGACY_PERSONA_REVIEW.md | CURRENT | legacy persona hit list (60 posts) | brand_identity_audit --legacy |
| reports/P1_BRAND_04_LOGO_REPLACEMENT_READY.md | CURRENT | favicon replacement record | asset copy + build check |
| reports/GROWTH_MASTER_DASHBOARD.md | CURRENT | SEO+revenue combined status (UTF-8, 08-17) | experiment reports |

## STALE / SUPERSEDED (do not use as current state)

| Report | Status | Purpose | Superseded by |
|---|---|---|---|
| reports/seo/content_inventory.csv | SUPERSEDED | 57-row inventory | CONTENT_SEO_INVENTORY.csv (60 rows) |
| reports/seo/daily_search_performance.csv / _90d.csv | STALE | GSC daily series fetched 08-16 01:41 | next GSC pull |
| reports/seo/SEO_OPPORTUNITIES.md / seo_opportunities.csv | STALE | 08-16 snapshot on pre-22 title set | content_opportunity_engine re-run |
| reports/seo/PAGE_1_OPPORTUNITIES.md | STALE | 08-16 GSC snapshot | fresh GSC pull |
| reports/seo/LOW_CTR_OPPORTUNITIES.md | STALE | 08-16 GSC snapshot | fresh GSC pull |
| reports/seo/QUERY_INTENT_DISTRIBUTION.md / query_intent_distribution.csv | STALE | 08-16 snapshot | query_intent re-run |
| reports/seo/SITEMAP_INDEX_GAP.md | STALE | 08-16 snapshot | fresh inspection |
| reports/P1_GROWTH_03_CONTENT_OPPORTUNITY_ENGINE.md | STALE | headline says 57-post baseline (feeds rebuilt on 60) | content_opportunity_engine re-run |
| reports/P1_GROWTH_04_CONTENT_PRIORITIZATION.md | STALE | headline says 57-post baseline | content_priority_engine re-run |
| reports/P1_GROWTH_09_AFFILIATE_REVENUE_BASELINE.md | STALE | 46-page/57-post baseline | PRE_DRIVE_BASELINE.csv |
| reports/P1_GROWTH_11_REVENUE_OPTIMIZATION.md | STALE | 57-page score narrative (CSV now 60) | REVENUE_OPPORTUNITY_SCORES.csv |
| reports/P1_GROWTH_22_PAYMENT_CONTENT_RELEASE.md | PARTIAL | deployment verification section incomplete | live verification run |

## HISTORICAL (frozen record, keep as-is)

| Report | Status | Purpose | Note |
|---|---|---|---|
| reports/P1_GROWTH_12A_REVENUE_CANDIDATE_LOCK.md | HISTORICAL | REV001 candidate lock process | identity now = Food Delivery + Airalo |
| reports/P1_GROWTH_12B_FIRST_REVENUE_EXPERIMENT.md | HISTORICAL | GROWTH-12B record | REV001 RUNNING |
| reports/P1_BRAND_03_LEGACY_PILOT_REPORT.md / _PILOT.md | HISTORICAL | BRAND-03 3-pilot migration record | migrated 2026-08-16 |
| reports/revenue/REV001_EXPERIMENT_LOG.md / REV002_EXPERIMENT_LOG.md / REV003_EXPERIMENT_LOG.md | HISTORICAL | experiment logs | current state in registries |
| reports/revenue/REV002_FINAL_REVIEW.md / REV002_REVIEW_READY.md | HISTORICAL | REV002 review prep (frozen experiment) | registry is source of truth |
| reports/seo/P1_GROWTH_05_EXPERIMENT_LOG.md / P1_GROWTH_07_EXPERIMENT_LOG.md | HISTORICAL | GROWTH-05/07 experiment logs | registries |
| reports/revenue/PAYMENT_ESIM_EXPERIMENT_CANDIDATE.md | HISTORICAL | eSIM candidate analysis | WAIT |
| reports/revenue/TRANSPORTATION_CARD_CTA_READINESS.md / _CONTENT_RELEASE.md | HISTORICAL | transportation card readiness | REV004 candidate |

## P1-REPORT-01 rebuild artifacts (CURRENT after rebuild)

| Report | Status | Purpose | Note |
|---|---|---|---|
| reports/P1_GROWTH_12_FIRST_REVENUE_EXPERIMENT.md | CURRENT | REV001 authoritative definition | Food Delivery / Airalo / cbt-e464169c4991 |
| reports/revenue/GROWTH12_BASELINE.csv | CURRENT | REV001 baseline | rebuilt 08-17 (was 144h/Booking) |

> Maintenance rule: when a report is rebuilt, update this index and mark the old version SUPERSEDED or HISTORICAL. Never delete historical reports.