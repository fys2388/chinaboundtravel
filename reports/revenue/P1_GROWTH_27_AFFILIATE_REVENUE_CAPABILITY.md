# P1-GROWTH-27 Task B — Affiliate Revenue Capability Audit

- Date: 2026-08-19
- Method: repository config/credential presence check (.env key names only), GA4 event implementation status, P1-AFFILIATE-01 link attribution audit. No partner APIs called. No credentials added.

## Capability Matrix

| Partner | Click data | Order data | Revenue data | API | Dashboard/Manual | Credentials | Verified |
|---|---|---|---|---|---|---|---|
| Travelpayouts | UNKNOWN | UNKNOWN | UNKNOWN | YES (token configured) | YES (dashboard) | YES | NO |
| Klook | UNKNOWN (partner) / YES (GA4) | UNKNOWN | UNKNOWN | YES via Travelpayouts | YES (TP dashboard) | YES (via TP token) | NO |
| Booking | UNKNOWN (partner) / YES (GA4) | UNKNOWN | UNKNOWN | NO (no key configured) | YES (Booking affiliate dashboard) | NO | NO |
| Airalo | NO (bare URL, no tracking) | NO | NO | NO | N/A (not integrated) | NO | NO |
| Aviasales | UNKNOWN (partner) / YES (GA4) | UNKNOWN | UNKNOWN | YES via Travelpayouts | YES (TP dashboard) | YES (via TP token) | NO |
| SafetyWing | UNKNOWN (partner) / YES (GA4) | UNKNOWN | UNKNOWN | NO | YES (ambassador dashboard, manual) | NO | NO |
| Trip.com | NO (bare URL, no tracking) | NO | NO | NO | N/A (not integrated) | NO | NO |
| Allianz | NO (bare URL, no tracking) | NO | NO | NO | N/A (not integrated) | NO | NO |
| World Nomads | NO (bare URL, no tracking) | NO | NO | NO | N/A (not integrated) | NO | NO |
| NordVPN | UNKNOWN (partner) / YES (GA4) | UNKNOWN | UNKNOWN | YES (API key configured) | YES (affiliatescn dashboard) | YES | NO |
| NordPass | NO (0 pages use link) | NO | NO | NO | N/A | NO | NO |

## Summary

- **Website-side click data (GA4)**: available for all deployed links via affiliate_click/impression/outbound (Task A).
- **Partner-side revenue data**: only Travelpayouts and NordVPN have credentials configured; both UNVERIFIED. All other partners are dashboard/manual or not integrated.
- **Revenue availability**: NULL (no real order/commission data exists yet).
- **Not integrated (bare URLs, no attribution)**: Airalo, Trip.com, Allianz, World Nomads, NordPass.
- **Next step (not executed)**: verify Travelpayouts API token with a read-only balance/statistics call after user approval; verify NordVPN API key availability.
