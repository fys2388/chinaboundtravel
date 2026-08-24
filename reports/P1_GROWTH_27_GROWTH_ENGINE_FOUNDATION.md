# P1-GROWTH-27 — Growth Engine Foundation

- Date: 2026-08-19
- Final status: **PARTIAL** (all 3 tasks delivered; `pytest` could not run due to environment blocker - system Python stub unavailable and network restricted, so pytest could not be installed into the bundled runtime)

## Task A — GA4 Page-Level Attribution (DONE)

- Report: `reports/revenue/P1_GROWTH_27_GA4_ATTRIBUTION_IMPLEMENTATION.md`
- Gaps fixed: `page_path`, `cta_id`, `experiment_id` added to `affiliate_impression` / `affiliate_click` / `affiliate_outbound`.
- Files: `layouts/shortcodes/affiliate-mid-cta.html`, `layouts/shortcodes/ab-cta.html`, `layouts/_default/single.html`, REV001/REV002 post CTAs tagged with `cta_id` + `experiment_id`.
- Existing event fields and `ab_cta_click` preserved; CTA wording/placement, URLs, UTM, Drive untouched.
- Validated on rendered REV001 and REV002 pages (Hugo build + attribute/JS inspection).

## Task B — Affiliate Revenue Capability Audit (DONE)

- Files: `reports/revenue/P1_GROWTH_27_AFFILIATE_REVENUE_CAPABILITY.csv` + `.md`
- Credentials present in `.env` (names only, values not inspected): TRAVELPAYOUTS_API_TOKEN/MARKER/DRIVE_ID, NORDVPN_API_KEY/AFFILIATE_ID. All UNVERIFIED.
- Partners with attribution and GA4-side click data: Klook, Booking, Aviasales, SafetyWing, NordVPN, Travelpayouts.
- Not integrated (bare URLs): Airalo, Trip.com, Allianz, World Nomads, NordPass.
- Revenue availability: NULL. No partner APIs called, no credentials added.

## Task C — SEO Money Opportunity Queue (DONE)

- Files: `reports/seo/P1_GROWTH_27_SEO_MONEY_OPPORTUNITIES.csv` + `.md`
- TOP 10 from 19 candidates: 6x T1 (impressions>=20, position 5-30, CTR<5%), 2x T2 (position 8-20), 2x T3.
- Excluded: REV001, REV002, WAITING_RECRAWL / not-indexed pages, 6 HIGH canonical conflicts; indexed pages only.
- Top T1 examples: 2026-08 monthly update (imp 52, pos 11.4), photography guide (imp 51, pos 20.9), Yunnan (imp 40, pos 20.7).

## Validation

| Check | Result |
|---|---|
| `python scripts/content_id_audit.py audit --strict` | PASS - 60/60 content_id, 0 missing, 0 malformed, 0 duplicates |
| `hugo --gc --minify` | PASS |
| secret scan (pattern scan of 5 changed files) | PASS - no secret patterns |
| affiliate regression (node check_affiliate_links.cjs) | BLOCKED by sandbox network (all links unreachable) - false negative, not a code regression |
| `pytest` | BLOCKED - system Python unavailable (WindowsApps stub) and network restricted (cannot install pytest into bundled Python 3.12.13) |

## Blockers

1. `pytest` cannot run in this environment until the system Python runtime is restored or network access to PyPI is allowed. Previously (2026-08-18) the same test suite ran 66 passed for affiliate/link tests.
2. Node affiliate link check requires outbound network; sandbox currently blocks all outbound HTTPS.

## Next actions (not executed)

- Restore Python/pytest environment, then run: `python -m pytest tests/ -q` (expect 0 failed / 0 skipped).
- Review TASK C TOP 10: apply title/meta/H1 + internal links on the 6 T1 pages after approval.
- Verify Travelpayouts API token with a read-only call after network is restored.
