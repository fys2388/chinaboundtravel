# Payment Commercial Funnel Design (P1-GROWTH-21D)

Date: 2026-08-16 | Status: DESIGN ONLY — no implementation

## User path
Discovery
- Search: "can foreigners use alipay china" / "wechat pay foreign card"
  ↓
Trust Content
- Alipay Guide / WeChat Pay Guide (authority pages, high trust required)
  ↓
Supporting Need
- eSIM (SMS verification, connectivity) / VPN (Google services) / Travel Insurance / Booking
  ↓
Monetization
- Affiliate: Airalo / NordVPN / SafetyWing / Booking (soft, contextual)

## Rules
- Payment pages must NOT hard-sell affiliate links (high-trust topic).
- Supporting-need links are contextual (SMS/verification/internet prep), not banners.
- Revenue stays NULL until real data; sample guard: clicks < 20 -> INSUFFICIENT_SAMPLE.

## Status
- Design ready; execution deferred until Payment Cluster index stability (WeChat recovery).
