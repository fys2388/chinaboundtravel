# P1-GROWTH-14A — Revenue Foundation (Affiliate Funnel Measurement Layer)

- Date: 2026-08-16
- Status: PASS
- Git: (see commit)
- Source instruction: reports/CHATGPT_INSTRUCTION_P1_GROWTH_14A.md (ChatGPT ChinaBound Travel评测)

## 1. Funnel Architecture

Traffic -> Page View -> CTA Impression -> Affiliate Click -> Partner Conversion -> Commission Revenue

| Stage | Status | Mechanism |
|---|---|---|
| Traffic / SEO | OK | GSC + GA4 (existing) |
| Page View | OK | GA4 page_view (existing) |
| CTA Impression | NEW | `affiliate_impression` (IntersectionObserver, once per partner+placement) |
| Affiliate Click | OK (kept compatible) | `affiliate_click` (existing event, unchanged payload) |
| Outbound | NEW | `affiliate_outbound` (pagehide/visibilitychange confirms exit, 3s window) |
| Partner Conversion / Commission | NOT_AVAILABLE | `RevenueProvider` returns NULL; never fabricated |

## 2. CTA Inventory

- Engine: `scripts/affiliate_funnel_audit.py`
- Output: `reports/revenue/AFFILIATE_FUNNEL_INVENTORY.csv` (277 CTA rows across 45 pages)

| cta_type | count |
|---|---|
| SHORTCODE (affiliate-esim/hotel/flight/tour/insurance) | 235 |
| INLINE (raw affiliate URL) | 33 |
| AB_CTA (ab-cta component) | 7 |
| MID_CTA (REV001 mid-content) | 2 |

Partners: Booking 53, Klook 54, Airalo 45, Aviasales 50, SafetyWing 47, NordVPN 17, Trip.com 5, Allianz 3, World Nomads 3.
Travelpayouts Drive is site-wide via head partial (exactly 1 occurrence per page) and is not a per-page CTA.

## 3. Event Specification (GA4 / dataLayer)

All events push to both `gtag('event', ...)` and `window.dataLayer.push({event, ...})`.

`affiliate_impression` (fires once per partner+placement when CTA enters viewport):
```json
{ "event": "affiliate_impression", "content_id": "...", "partner": "airalo", "placement": "food-delivery-mid-content", "channel": "organic", "timestamp": "...", "destination": "...", "tracking_parameter": "..." }
```

`affiliate_click` (compatible, unchanged from P0-7 / GROWTH-12):
```json
{ "event": "affiliate_click", "content_id": "...", "partner": "...", "placement": "...", "channel": "organic", "timestamp": "...", "destination": "...", "tracking_parameter": "..." }
```

`affiliate_outbound` (click + exit confirmation within 3s):
```json
{ "event": "affiliate_outbound", "content_id": "...", "partner": "...", "placement": "...", "outbound_success": true, "channel": "organic", "timestamp": "...", "destination": "..." }
```

Implementation: `layouts/_default/single.html` (funnel events block added; existing affiliate_click block untouched).

## 4. Revenue Provider Abstraction

- `scripts/revenue_provider.py`
- `class RevenueProvider`: `get_revenue() -> None`, `get_affiliate_clicks() -> None`
- `status = REVENUE_NOT_AVAILABLE`
- Future plug-ins: Travelpayouts API / Booking / Klook / Airalo dashboards behind same interface.
- Forbidden: simulated revenue, fake orders, inferred commissions.

## 5. REV001 Measurement Upgrade

- `scripts/revenue_experiment_review.py` new metrics:
  - `calc_clicks_per_1000_sessions` (primary: affiliate_clicks_per_1000_sessions)
  - `calc_cta_ctr` (secondary: CTA CTR)
  - `calc_outbound_rate` (secondary: outbound rate)
- Snapshot: `reports/revenue/REV001_FUNNEL_METRICS.csv`
  - REV001: clicks 0, sessions 162, per1000 0.0, CTA impressions 0, CTA CTR 0.0, outbound rate 0.0, revenue NULL, status INSUFFICIENT_SAMPLE

## 6. Regression Result

- pytest: 379 passed, 0 failed, 0 skipped (>370 required)
- hugo --gc --minify: PASS
- content_id_audit --strict: PASS (57/57, 0 missing, 0 duplicates)
- secret scan: PASS (0 findings)
- workflow yaml validation: PASS
- Drive script: exactly 1 occurrence per rendered page (home, article, about)
- Affiliate URLs / UTM / canonical / URL / content_id: unchanged (tests enforce)

## 7. P1-GROWTH-14B (prepared, not executed)

- `reports/revenue/COMMERCIAL_CONTENT_PIPELINE.md` — ranked pipeline only, no publication.
