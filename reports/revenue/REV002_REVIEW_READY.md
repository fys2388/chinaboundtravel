# REV002 Review Readiness (P1-GROWTH-19F)

Generated: 2026-08-16  |  Status: PREPARATION ONLY (no judgement)

## Experiment
- experiment_id: REV002
- content_id: cbt-17c6738ffb32
- url: https://www.chinaboundtravel.com/posts/china-transportation-complete-guide-trains-subways-taxis-and-more/
- type: CTA_PLACEMENT
- start_date: 2026-08-16
- baseline_period: 2026-07-19..2026-08-15
- review gate (min observation): 28 days
- status: RUNNING

## Metrics for review
- Primary: affiliate_click_rate
- Secondary: affiliate_outbound_rate; affiliate_clicks_per_1000_sessions; CTA impressions

## Data availability
- GA4 events: AVAILABLE
- GSC snapshot: AVAILABLE (file: gsc_index_report.json)

## Baseline snapshot (frozen at experiment start)
- content_id: cbt-17c6738ffb32
- url: https://www.chinaboundtravel.com/posts/china-transportation-complete-guide-trains-subways-taxis-and-more/
- baseline_start: 2026-07-19
- baseline_end: 2026-08-15
- sessions: NULL
- pageviews: NULL
- affiliate_clicks: 0
- affiliate_clicks_per_1000: 0
- gsc_impressions: 107
- gsc_clicks: 0
- gsc_position: 22.33
- revenue: NULL

## Sample-size guard
- threshold: affiliate/gsc clicks < 20 -> INSUFFICIENT_SAMPLE
- current known clicks (baseline gsc_clicks): 0
- verdict at review time: INSUFFICIENT_SAMPLE

## Rules
- Do not declare WIN/LOSE at review time if clicks < 20.
- Do not modify REV002 CTA before the gate (>= 2026-09-13).
- No revenue data: keep NULL; never fabricate.
