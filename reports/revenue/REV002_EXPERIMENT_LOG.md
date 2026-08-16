# REV002 Experiment Log — Trip.com Train Ticket CTA (China Transportation Guide)

## Experiment
- experiment_id: REV002
- type: CTA_PLACEMENT (mid-content)
- page: China Transportation Guide: Trains, Subways & Taxis
- content_id: cbt-17c6738ffb32
- url: https://www.chinaboundtravel.com/posts/china-transportation-complete-guide-trains-subways-taxis-and-more/
- start_date: 2026-08-16
- minimum observation: 28 days (earliest review 2026-09-13)

## Baseline (2026-07-19 .. 2026-08-15)
- GSC: impressions 107 / clicks 0 / position 22.33 (source: CONTENT_SEO_INVENTORY.csv)
- affiliate_clicks: 0
- sessions/pageviews: sitewide 162/365 (no page-level GA4 baseline; NULL not fabricated)
- revenue: NULL

## CTA change
- Partner: Trip.com (existing affiliate param `trip` in hugo.toml; no URL change)
- Shortcode: `affiliate-mid-cta` (same tracked component as REV001)
- placement: transportation-train-tickets-mid
- position: end of "How to Buy Tickets: Trip.com vs 12306" section (before Station Survival Guide)
- tracking: reuses affiliate_impression / affiliate_click / affiliate_outbound (GA4 funnel events)
- Primary metric: affiliate_click_rate
- Secondary: affiliate_outbound_rate; affiliate_clicks_per_1000_sessions; gsc_impressions; gsc_clicks; position

## Confounders
1. DRIVE-001 runs site-wide; Drive config unchanged this round.
2. REV001 (Food Delivery) runs on a different page; no overlap.
3. 144h Visa / WeChat Index / Rail observation continue; none touch this page.
4. No content rewrite; only one CTA added.
5. Legacy persona phrases on this page were NOT migrated this round (out of scope).

## Rules
- Do not change CTA copy, placement, or partner until 2026-09-13.
- If affiliate_clicks < 20 at review -> INSUFFICIENT_SAMPLE (no WIN/LOSE).
