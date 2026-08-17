# ChinaBound Travel 2.0 — Reporting KPI Definitions

- Generated: 2026-08-17
- One definition set shared by daily / weekly / monthly / quarterly / yearly reports.
- All formulas are evaluated by scripts/reporting_kpi_engine.py and stored in REPORTING_SNAPSHOT.json. Reports only format values; they never re-derive KPIs.

## 1. KPI domains

The unified model has nine domains. Every period report uses the same nine domains and the same KPI names.

| Domain | Content |
|---|---|
| A. Traffic | users, sessions, pageviews, engagement, source/channel |
| B. SEO / GSC | index coverage, impressions, clicks, CTR, position, opportunities |
| C. Content assets | published/new/updated pages, tier distribution, pipeline, persona, stale/duplicate risk |
| D. Brand 2.0 | persona compliance, legacy remaining, migrations, asset status |
| E. Affiliate funnel | impressions, clicks, outbound, rates, per-1000, partner breakdown |
| F. Revenue | revenue, orders, commission, RPM, revenue per 1000 sessions |
| G. Experiments | id, type, start, days, primary metric, baseline, current, delta, sample, status |
| H. Commercial clusters | Transportation / Payment / Connectivity |
| I. Operations | automation, workflow, deployment, backup, security |

## 2. Formulas

### Traffic
- sessions_28d = GA4 totalSessions (28d)
- pageviews_28d = GA4 totalPageviews (28d)
- users / engagement / source-channel: NOT_AVAILABLE until GA4 dimensions are persisted

### SEO / GSC
- gsc_ctr_28d = clicks / impressions × 100
- gsc_avg_position_28d = GSC average position (28d)
- page_level_clicks_28d = Σ inventory.clicks_28d
- page_level_impressions_28d = Σ inventory.impressions_28d
- indexed_pages / not_indexed_pages = GSC UI totals (snapshot dated)
- pages_newly_indexed / pages_losing_visibility = NOT_AVAILABLE until a second snapshot exists

### Content assets
- published_posts = inventory row count (= content_id count when audit PASS)
- content_id_coverage = posts with content_id / published_posts
- new_pages_30d = count(published_date ≥ as_of − 30d)
- asset_tier_distribution = count by opportunity_tier (A/B/C/D)
- opportunity_pipeline = CONTENT_OPPORTUNITY_FEED item count
- legacy_persona_pages = posts matching legacy phrase list (brand_identity_audit --legacy)
- canonical_conflicts = rows in CANONICAL_CONFLICT_QUEUE with a URL
- duplicate_risk_rows = inventory rows with duplicate_count > 1

### Brand 2.0
- editorial_persona_compliance = PASS layers / 13 audited layers
- legacy_persona_remaining = legacy phrase hit posts
- migrated_this_period = pilot migrations completed in period (BRAND-03 = 3 on 2026-08-16)
- logo_favicon_status = P1-BRAND-04 migration state (LOGO_REPLACEMENT_READY)
- core_brand_compliance = PASS when no forbidden/fictional claims and editorial present

### Affiliate funnel
- click_rate (REV001 scope) = affiliate_clicks / cta_impressions × 100
- outbound_rate (REV001 scope) = outbound_success / affiliate_clicks × 100
- clicks_per_1000_sessions = affiliate_clicks / sessions × 1000
- cta_inventory_rows / pages = AFFILIATE_FUNNEL_INVENTORY counts
- partner_breakdown = per-partner pages_count / link_count / status from AFFILIATE_PARTNER_INVENTORY

### Revenue
- All = NULL (REVENUE_NOT_AVAILABLE). Formulas exist but are never evaluated without a real API:
  - rpm = revenue / pageviews × 1000
  - revenue_per_1000_sessions = revenue / sessions × 1000

### Experiments
- observation_days = as_of − start_date (0 if start date == as_of)
- baseline = pre-experiment period value (REV001_BASELINE / comparison artifact)
- current = in-window value; delta = current − baseline; delta_pct = delta / |baseline| × 100 (NULL if baseline 0)
- sample = INSUFFICIENT_SAMPLE when observation_days < 28 OR clicks < 20
- status follows REPORTING_STATUS_MODEL.md §4

### Commercial clusters
- cluster score / impressions_28d / best_position / affiliate_fit_ratio from COMMERCIAL_CLUSTER_PRIORITY.csv
- per-cluster indexed_pages / commercial_pages / revenue = NULL (no per-cluster mapping artifact yet)

### Operations
- automation_health / workflow_health / security_scan = PASS when the referenced test suites are green
- deployment_health = latest recorded live verification date
- backup_rollback = NOT_AVAILABLE

## 3. Rollup rules (which reports use which KPIs)

All period reports use the full snapshot; period-specific sections only change the narrative and comparison label, never the numbers.

| Report | Focus KPIs |
|---|---|
| Daily | DoD changes, anomalies, blockers, production incidents |
| Weekly | growth, experiments, content value, commercial performance |
| Monthly | MoM delta, trend direction, winner/loser, content investment efficiency |
| Quarterly | strategic review, resource allocation, scale/stop decisions |
| Yearly | traffic growth vs content asset value vs commercial value vs operational maturity |

## 4. No-duplication rule

- KPI values exist only in REPORTING_SNAPSHOT.json.
- A report that needs a value reads it from the snapshot. If a value is missing, the report prints NULL/NOT_AVAILABLE — it never computes a substitute.
- Any formula change happens in reporting_kpi_engine.py only, then all five periods are regenerated from the same snapshot.