# REVENUE EXPERIMENT READINESS

- Generated: 2026-08-16

## Affiliate click tracking
- Event: `affiliate_click`
- Status: `OK`
- Fields present: content_id, partner, placement, channel, timestamp, destination
- Missing fields: none
- gtag event: True | dataLayer push: True

## Experiment types
| Experiment | Ready | Notes |
|---|---|---|
| A. CTA placement test | READY | article_cta exists; can A/B placement via shortcode |
| B. Affiliate partner comparison | READY | partner field tracked per click |
| C. Content-to-affiliate conversion | PARTIAL | needs affiliate sessions/revenue API |
| D. Travelpayouts Drive experiment | NOT_READY | Drive NOT enabled this round |

## Data quality note
- Duplicate articles by URL: 9 (existing repo issue, not modified this round; kept for manual review)

## Revenue availability
- affiliate_click 28d = 0 (source: GA4_API(28d, per-page))
- affiliate_sessions / revenue: **NULL** until an affiliate revenue API is connected.

DRIVE_STATUS = NOT_ENABLED（本轮不启用 Travelpayouts Drive）

LOW_DATA_WARNING: GSC 28d clicks 极低（全站 3），GA4 affiliate_click 数据接近 0。不要基于当前数据宣布盈利结论。