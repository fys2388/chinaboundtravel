# P1-GROWTH-14B — Commercial Content Pipeline

- Date: 2026-08-16
- Status: PASS (analysis only, no execution changes)
- Git: see commit
- Source instruction: reports/CHATGPT_INSTRUCTION_P1_GROWTH_14B.md

## 1. Commercial Scoring Model (deterministic, 100 pts)

| Component | Weight | Data source |
|---|---|---|
| Commercial Intent | 30 | intent type (TRAIN/PAYMENT/INTERNET/...) |
| Search Demand | 25 | GSC impressions_28d (CONTENT_SEO_INVENTORY.csv) |
| Affiliate Fit | 20 | partner intersection with cluster (AFFILIATE_FUNNEL_INVENTORY.csv) |
| Existing Authority | 15 | best position_28d |
| Content Gap | 10 | page existence + position |

No LLM judgement, no subjective scoring, no fake data.

## 2. Topic Clusters

- Cluster A China Transportation (★★★★★): china train tickets / railway app / high speed rail booking / airport transfer / transportation card — Trip.com, Booking, Klook
- Cluster B China Payment (★★★★★): alipay for foreigners / wechat pay foreign card / china mobile payment / china payment problems — eSIM, VPN, travel services
- Cluster C China Connectivity (★★★★): china esim / china vpn / china mobile data / google services china — Airalo, NordVPN

## 3. Priority Queue (top results)

| cluster | keyword | score | priority | action |
|---|---|---|---|---|
| Transportation | china transportation card | 81 | A | CTA_ALIGN |
| Payment | wechat pay foreign card | 75 | B | CTA_ALIGN |
| Payment | alipay for foreigners | 68 | B | CTA_ALIGN |
| Transportation | china high speed rail booking | 58 | C | MONITOR |
| Transportation | china train tickets | 58 | C | MONITOR |
| Connectivity | china esim | 54 | C | MONITOR |

Full list: reports/revenue/COMMERCIAL_CONTENT_PRIORITY.csv (13 rows)

## 4. Revenue Gaps

- reports/revenue/CONTENT_REVENUE_GAPS.md — pages with traffic + commercial intent but weak/absent CTA alignment (NO_AFFILIATE / PARTIAL).
- Example: Food Delivery page has Airalo mid-content CTA only; possible future alignment Trip.com/Klook/eSIM/Payment. NOT changed this round.

## 5. No Execution Changes

- No content publishing, no content edits, no CTA changes, no affiliate URL changes, no UTM changes.
- REV001 RUNNING (review gate 2026-09-13); DRIVE-001 RUNNING.

## 6. Regression Result

- pytest: 393 passed, 0 failed, 0 skipped (>390 required)
- hugo --gc --minify: PASS
- content_id_audit --strict: PASS (57/57)
- secret scan: PASS (0 findings)
- workflow yaml validation: PASS
- Invariants kept: content_id 57/57, canonical unchanged, affiliate URL unchanged, Drive exactly 1, GA4 event schema unchanged

## 7. Deploy

- Scope changed: scripts/ + tests/ + reports/ only -> no production deployment needed (per instruction).

## Next

P1-GROWTH-15 FIRST COMMERCIAL CONTENT EXPANSION: 1 high-value commercial page + 1 CTA experiment + 28-day measurement.
