# Commercial Cluster Progress

Date: 2026-08-16 | Program: P1-GROWTH series

| Cluster | Node | Status | Experiment | Next |
|---|---|---|---|---|
| Visa | 144-Hour Visa | CTR experiment RUNNING (cbt-b4ff4381a014) | GROWTH-05 | observe to 2026-09-13 |
| Payment | WeChat Pay Strong | indexed | — | monitor |
| Payment | WeChat Pay Weak | index recovery REQUESTED | GROWTH-07C | WAITING_RECRAWL |
| Transportation | Guide | authority upgraded (17A) | REV002 RUNNING | review gate 2026-09-13 |
| Transportation | Card | NEW page (18) | none (isolated) | REV004 candidate (P1-GROWTH-19) |
| Transportation | Airport Transfer | HOLD (17C) | — | CREATE after first release |
| Food Delivery | Meituan/Ele.me | REV001 RUNNING | REV001 | observe |

## Active experiments
- DRIVE-001 RUNNING (start 2026-08-16) — untouched
- REV001 RUNNING (Food Delivery CTA) — untouched
- REV002 RUNNING (Transportation mid-cta) — untouched, frozen
- REV003 PENDING (copy variant; waits for REV002 gate)
- REV004 not started (Transportation Card CTA candidate)

## Low-sample guard
- affiliate_clicks < 20 → INSUFFICIENT_SAMPLE; no WIN/LOSE declarations
