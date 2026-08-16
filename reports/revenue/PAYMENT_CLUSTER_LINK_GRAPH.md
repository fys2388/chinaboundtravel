# Payment Cluster Link Graph (P1-GROWTH-22E)

Date: 2026-08-16 | Scope: Payment Cluster internal linking — read/write snapshot

## HUB: Alipay for Foreigners
- content_id: cbt-0adceab18b53
- URL: /posts/alipay-for-foreigners-guide/
- Role: Payment Cluster authority page (new, 2026-08-16)

## Outbound links (Alipay → cluster)
| Target | Page | Direction |
|---|---|---|
| WeChat Pay setup guide | /posts/wechat-pay-for-foreigners-step-by-step-setup-and-common-mistakes-to-avoid-guide/ | payment |
| Internet / eSIM-VPN guide | /posts/internet-connection-china-esim-vpn-guide/ | connectivity |
| China Transportation Guide | /posts/china-transportation-complete-guide-trains-subways-taxis-and-more/ | transport |

Outbound count: 3 — topic authority path Alipay → WeChat → eSIM → Transportation established.

## Inbound links (→ Alipay)
| Source page | Placements | Note |
|---|---|---|
| China Transportation Guide | 1 | Final Tips: WeChat Pay + Alipay setup |
| China Transportation Card Guide | 2 | QR-payment section + FAQ card-linking |
| China Packing List | 1 | Money and Payments section |
| Internet / eSIM-VPN guide | 1 | Setup verification needs data |
| Resources | 1 | Money & Payments section |

Inbound count: 6 (≥5 required) — sources: Transportation Guide / Transportation Card / Packing List / eSIM guide / Resources.

## Cluster health
- WeChat Pay strong page: INDEXED (cached), inbound links unchanged this round.
- WeChat Pay weak page: WAITING_RECRAWL (frozen, cached verdict "Alternate page with proper canonical tag").
- eSIM / VPN guide: links out to legacy Alipay combined page (unchanged) + new Alipay hub.
- No orphan within cluster: every payment-related post has ≥1 in/out link.

## Frozen objects (not touched)
- REV001 food delivery CTA / REV002 transportation CTA / Drive script / GA4 schema: byte-identical.
- WeChat Pay articles: not modified (22-round rule).
