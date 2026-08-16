# REV003 Experiment Log — Transportation CTA Copy Variant (PENDING)

## Experiment
- experiment_id: REV003
- test_id: REV003_TRANSPORTATION_CTA
- type: CTA_COPY (copy variant only)
- page: China Transportation Guide (cbt-17c6738ffb32)
- partner: Trip.com (unchanged)
- placement: existing (transportation-train-tickets-mid)
- tracking: existing affiliate_impression / affiliate_click / affiliate_outbound

## Variants (defined, not yet deployed)
- Variant A: "Book China Train Tickets Online"
- Variant B: "Compare China Train Tickets & Routes"

## Status: PENDING
- REV002 is RUNNING on this page with placement=transportation-train-tickets-mid.
- Changing its copy would break the REV002 baseline -> REV003 waits for the
  REV002 review gate (>= 2026-09-13) before any copy change.
- If the site cannot support a client-side A/B for copy, deploy a single
  version upgrade at that time (Variant A recommended).

## Rules
- Do not modify REV002 CTA copy / placement / partner.
- affiliate_clicks < 20 at review -> INSUFFICIENT_SAMPLE.
