# Transportation Revenue Funnel (P1-GROWTH-20D)

Generated: 2026-08-25  |  Deterministic map, no network

## Funnel
Traffic Entry -> Informational Page -> Commercial Intent -> Affiliate CTA -> Outbound -> Revenue

## Page classification
| Page | content_id | Stage | Commercial element |
|---|---|---|---|
| transportation_guide | cbt-17c6738ffb32 | Discovery | REV002 Trip.com mid-cta (shortcode uses: 2) |
| high_speed_rail | cbt-cc4549872c92 | Transaction | Trip.com/booking links (shortcode uses: 0) |
| transportation_card | cbt-55aef784e6aa | Utility | comparison layer (Trip/Klook/Airalo/Booking) (shortcode uses: 6) |
| airport_transfer | cbt-02a3e0d6ed4f | Transaction | comparison layer (Klook/Booking/Trip/Airalo) (shortcode uses: 6) |

## Stage inventory
- Discovery: Transportation Guide (authority hub, REV002 active)
- Transaction: High-Speed Rail (booking intent), Airport Transfer (transfer intent)
- Utility: Transportation Card (comparison layer, no experiment)

## Measurement readiness
- affiliate_click / affiliate_impression / affiliate_outbound events exist (GA4 schema unchanged)
- Revenue: NULL allowed; never fabricated
- Sample guard: affiliate_clicks < 20 -> INSUFFICIENT_SAMPLE

## Rules
- REV002 frozen; no new CTA this round; no new partner/tracking/UTM.
