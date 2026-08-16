# Payment → eSIM Experiment Candidate (P1-GROWTH-22F)

Date: 2026-08-16 | Analysis only — experiment NOT started.

## Purpose
Evaluate whether a Payment-cluster → eSIM/connectivity CTA experiment (future REV candidate)
is viable after the Alipay authority page is indexed and stable. No launch this round.

## Scoring model (100 points, internal)
| Dimension | Weight | Rationale |
|---|---|---|
| Traffic | 25 | Enough page-level traffic to observe a delta |
| Payment intent | 25 | Users on payment pages need connectivity to complete setup |
| eSIM relevance | 25 | Natural fit between payment setup and data/eSIM need |
| Current authority | 15 | Page already indexed with stable canonical |
| Risk | 10 | Low risk = high score (no risk = 10) |

## Candidates

### C1. Alipay for Foreigners (new hub)
- content_id: cbt-0adceab18b53 | /posts/alipay-for-foreigners-guide/
- Traffic: 0 impressions cached (page published 2026-08-16, no observation window) → 0/25
- Payment intent: 25/25 (core payment setup intent)
- eSIM relevance: 22/25 (setup section explicitly needs data/network)
- Current authority: 5/15 (published, indexable, self canonical — but not yet crawled/indexed)
- Risk: 8/10 (soft reference links only, no CTA yet)
- Score: 60 → **WAIT** (needs index + ≥28d traffic observation)

### C2. WeChat Pay setup (weak page)
- content_id: cbt-255af4ed003a | WAITING_RECRAWL
- Traffic: 1 impression cached → 1/25
- Payment intent: 25/25 | eSIM relevance: 20/25
- Current authority: 3/15 (not indexed, frozen)
- Risk: 6/10
- Score: 55 → **WAIT** (recrawl pending, page frozen)

### C3. China Transportation Card Guide
- content_id: cbt-55aef784e6aa | /posts/china-transportation-card-guide/
- Traffic: 0 impressions cached (new page, no window) → 0/25
- Payment intent: 22/25 | eSIM relevance: 12/25
- Current authority: 5/15 (published, indexable)
- Risk: 9/10
- Score: 48 → **WAIT**

## Verdict
- READY: none this round (no page with observed traffic + stable index).
- WAIT: C1 (primary next candidate once indexed and observed 28d), C2 (after recrawl), C3.
- REJECT: none.

## Recommendation
1. Observe Alipay hub 14–28 days after indexing (GSC URL Inspection read-only).
2. Re-run scoring at P1-GROWTH-23/24; if impressions ≥ meaningful threshold, propose REV CTA:
   soft mid-content reference link to eSIM/VPN guide (Airalo), placement `payment-esim-connectivity-mid`.
3. Do not add CTA before index confirmation; do not modify page content while observing.
