# Transportation Card CTA Readiness (P1-GROWTH-20B)

Generated: 2026-08-29  |  Candidate: cbt-55aef784e6aa

## Score (100)
| Dimension | Weight | Score |
|---|---|---|
| GSC Demand | 25 | 2 |
| Commercial Intent | 30 | 24 |
| Affiliate Fit | 25 | 18 |
| Index Status | 10 | 2 |
| Risk | 10 | 6 |
| **Total** | 100 | **52** |

## Verdict: REJECT

## Constraints if READY
- 1 page / 1 CTA / 1 partner / 1 placement only
- Preferred partner: Trip.com (city movement + train booking intent)
- Do not touch Transportation Guide / REV002 / Airport Transfer simultaneously
- Sample guard: affiliate_clicks < 20 -> INSUFFICIENT_SAMPLE

## Rules
- REV002 must remain the only active transportation CTA experiment until its gate (2026-09-13).
- No new affiliate partner / tracking / UTM.
