# REV002 Final Review (P1-GROWTH-20A)

Generated: 2026-08-25  |  Gate: 2026-09-13

## Status: WAITING_REVIEW_GATE
- review date 2026-08-25 < gate 2026-09-13
- No judgement is allowed before the gate.
- Sample guard remains: affiliate_clicks < 20 -> INSUFFICIENT_SAMPLE.

## Experiment (frozen)
- experiment_id: REV002
- content_id: cbt-17c6738ffb32
- status: RUNNING

## Framework (applied at gate)
- clicks >= 20 AND affiliate_click_rate improvement >= 20%
  AND outbound_rate not worse than baseline -10% -> PROMISING
- otherwise -> NEUTRAL
- clicks < 20 -> INSUFFICIENT_SAMPLE (no WIN/LOSE)
