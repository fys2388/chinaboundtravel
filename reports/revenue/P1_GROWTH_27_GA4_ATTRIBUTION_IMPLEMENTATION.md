# P1-GROWTH-27 Task A — GA4 Page-Level Attribution Implementation

- Date: 2026-08-19
- Prerequisite: `reports/revenue/P1_GROWTH_26_GA4_ATTRIBUTION_AUDIT.md` was NOT present in the repo at execution time (removed by earlier report reconciliation). Gaps were re-confirmed directly from the current code.

## 1. Confirmed gaps (before)

| Field | Status before |
|---|---|
| content_id | present (data-content-id) |
| partner | present (data-affiliate-partner) |
| placement | present (data-affiliate-placement) |
| page_path | MISSING |
| cta_id | MISSING |
| experiment_id | MISSING |

## 2. Changes (minimal, event-attribution only)

1. `layouts/shortcodes/affiliate-mid-cta.html`
   - Added optional `cta_id` (default = placement) and `experiment_id` params; rendered as `data-cta-id` / `data-experiment-id` on the CTA anchor. CTA text/placement unchanged.
2. `layouts/_default/single.html`
   - Both event builders (`affiliate_click` send() and `affiliate_impression`/`affiliate_outbound` paramsFor()) now include:
     - `page_path: window.location.pathname`
     - `cta_id` (from `data-cta-id`, fallback placement)
     - `experiment_id` (from `data-experiment-id`, default empty)
   - All existing fields preserved (content_id, partner, placement, channel, timestamp, destination, tracking_parameter) - event compatibility kept.
3. `layouts/shortcodes/ab-cta.html`
   - A/B CTA anchors now carry `affiliate-link` class + `data-affiliate-partner` (affiliate_key), `data-affiliate-placement` (test_id), `data-cta-id` (analytics_id), `data-experiment-id` so funnel events (impression/click/outbound) cover A/B CTAs too. Existing `ab_cta_click` untouched.
4. `content/posts/2026-05-28-chinese-food-delivery-meituan-eleme-guide.md` (REV001)
   - CTA now: `cta_id="rev001-food-delivery-esim" experiment_id="REV001"` (link, text, placement unchanged)
5. `content/posts/2026-07-16-china-transportation-complete-guide-trains-subways-taxis-and-more.md` (REV002)
   - CTA now: `cta_id="rev002-transportation-trip" experiment_id="REV002"` (link, text, placement unchanged)

## 3. Validation

- `hugo --gc --minify` → PASS
- Rendered REV001 page contains `data-cta-id="rev001-food-delivery-esim"`, `data-experiment-id="REV001"` and JS `page_path`/`cta_id`/`experiment_id` in all three events.
- Rendered REV002 page contains `data-cta-id="rev002-transportation-trip"`, `data-experiment-id="REV002"` and same JS fields.
- `affiliate_impression` / `affiliate_click` / `affiliate_outbound` all present with new context fields.

## 4. Not changed

- CTA wording/placement, affiliate URLs, UTM, Drive, GA4 config (TrackingID), REV001/REV002/DRIVE-001 experiment logic, Stripe, Buffer.
