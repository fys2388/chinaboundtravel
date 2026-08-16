# P1-GROWTH-15 — Commercial Conversion Optimization

- Date: 2026-08-16
- Status: PASS
- Git: see commit
- Source instruction: reports/CHATGPT_INSTRUCTION_P1_GROWTH_15.md

## 15A Commercial Page Selection
- Engine: scripts/commercial_conversion_engine.py (deterministic, no LLM)
- Score 100: Traffic Potential 25 + Commercial Intent 30 + CTA Match 25 + Current CTA Gap 15 + Risk Adjustment 5
- Output: reports/revenue/COMMERCIAL_CONVERSION_TARGETS.csv (48 pages, URL-deduped, ground-truth content_id)
- Top 3 (impressions > 50 + indexed + commercial query + not frozen):
  1. cbt-17c6738ffb32 China Transportation Guide (TRAIN, 107 imp, 75)
  2. cbt-244822dc113b 144h visa extended (VISA, 87 imp, 72)
  3. cbt-707a8899c0a7 WeChat Pay (PAYMENT, 83 imp, 69)
- TOP_COMMERCIAL_PAGES.md includes CTA gap table for top 3 (analysis only).

## 15B CTA Gap Analysis (top 3, no changes)
| page | existing partners | intent match | gap |
|---|---|---|---|
| Transportation Guide | Trip.com (inline) | Trip.com/Booking/Klook | CTA_ALIGN -> REV002 |
| 144h visa extended | Airalo/Booking/Klook | Booking/Klook/Airalo | MONITOR (informational) |
| WeChat Pay (strong) | none in funnel | Airalo/NordVPN/Trip.com | MONITOR (index recovery active) |

## 15C REV002 CTA Experiment (launched)
- Page: China Transportation Guide (cbt-17c6738ffb32), 1 page / 1 CTA / 1 partner / 1 placement
- CTA: `affiliate-mid-cta` partner=trip placement=transportation-train-tickets-mid
- Position: end of "How to Buy Tickets: Trip.com vs 12306" (after High Speed Rail section)
- Copy: booking-first Train Ticket CTA, English, transparent affiliate disclosure, no persona claims
- Artifacts: REV002_EXPERIMENT_REGISTRY.csv / REV002_BASELINE.csv / REV002_EXPERIMENT_LOG.md
- Baseline: GSC impressions 107 / clicks 0 / position 22.33; affiliate clicks 0; revenue NULL

## 15D Measurement
- Reuses GA4 funnel events: affiliate_impression / affiliate_click / affiliate_outbound
- Primary: affiliate_click_rate; Secondary: outbound_rate, clicks_per_1000_sessions
- Revenue NULL until API available (never fabricated)

## Regression
- pytest: 413 passed, 0 failed, 0 skipped (>400 required)
- hugo --gc --minify: PASS; REV002 CTA renders exactly once with correct placement/partner
- content_id_audit --strict: PASS (57/57, 0 duplicates)
- secret scan: PASS (0 findings)
- workflow yaml validation: PASS
- Invariants: URL/canonical/content_id unchanged; affiliate URL (trip) unchanged; UTM unchanged; Drive exactly 1; GA4 schema unchanged

## Guards honored
- No new article, no REV001/Drive/144h/WeChat changes, no legacy persona migration
- Scope guard tests updated to authorize the single REV002 post (per P1-GROWTH-15 Git Scope Guard)
