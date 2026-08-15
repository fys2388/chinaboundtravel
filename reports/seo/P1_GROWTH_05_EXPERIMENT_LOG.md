# P1-GROWTH-05 Experiment Log

- Date: 2026-08-16
- GitHub main baseline: `8a844ce`
- Observation window: at least 28 days after deployment
- PRIMARY_METRIC: **CTR**
- SECONDARY: Impressions, Position
- LOW_SAMPLE_WARNING: current 28d clicks = 3, CTR = 0.26%. Short-term fluctuations are NOT success/failure signals; judge only after 2 consecutive data windows.

## Experiment 1 — ACTION A: Canonical conflict verification (technical)

- Object: China Transportation Guide canonical cluster (`cbt-17c6738ffb32`)
- Original state: GSC URL Inspection showed 6 canonical conflicts (google_canonical != user_canonical), all severity HIGH
- Investigation result: **code layer already correct** — all 6 conflict pages render the expected final canonical today (verified on built HTML). Canonicals were standardized upstream (commit `05426ab`). Remaining mismatches are Google's content-based judgment on legacy duplicate pages (persona posts with near-duplicate content), not code defects.
- Change: none (verified + locked with regression tests `tests/test_growth05_first_content_action.py`)
- Reason: no code fix is warranted without a content-dedup decision (legacy persona pages are out of scope)
- Expected metrics: canonical conflicts disappear from GSC URL Inspection after Google re-crawls; sitemap/robots unaffected
- Publish date: n/a (no content publish)

## Experiment 2 — ACTION B: WeChat Pay index recovery check

- Object: `cbt-255af4ed003a` WeChat Pay for Foreigners: Setup Guide & Mistakes
- Original state: GSC coverage "Alternate page with proper canonical tag" (NOT_INDEXED)
- Investigation result: built page is `index, follow` with self-canonical; no `robotsNoIndex`; `draft: false`. The "alternate" verdict comes from content overlap with `how-to-use-wechat-pay-as-a-foreigner` (`cbt-707a8899c0a7`, INDEXED). Not a code defect.
- Change: none (verified + locked; **MANUAL_REVIEW**: decide merge vs differentiation of the two WeChat Pay articles)
- Reason: cannot fix content overlap under the no-body-edit boundary
- Expected metrics: n/a until dedup decision
- Publish date: n/a

## Experiment 3 — ACTION C: 144-hour visa-free transit CTR title/meta test

- Object: `cbt-b4ff4381a014` 144-Hour Visa-Free Transit in China
- Original state: 107 impressions / 0 clicks / CTR 0.00% / avg position 74.05 (28d); INDEXED
- OLD_TITLE: `144-Hour Visa-Free Transit in China (2026 Guide)`
- NEW_TITLE: `China 144-Hour Visa-Free Transit (2026 Guide)`
- OLD_DESCRIPTION: `Who qualifies for China's 144-hour visa-free transit in 2026? Eligible cities, required documents, and the border process, step by step.`
- NEW_DESCRIPTION: `China's 144-hour visa-free transit explained: who qualifies, eligible cities and ports, required documents, and the border process step by step.`
- Reason: lead with the exact high-volume query pattern ("144 hour visa china" / "144 hour visa free transit"), keep length within 160, stay factual
- Expected metrics (28d): CTR > 0.26% baseline, impressions stable or up, position stable or up
- Publish date: 2026-08-16 (deployed with next GitHub Actions / Pages build)
- Constraints: body unchanged, canonical unchanged, URL unchanged, affiliate/UTM unchanged, content_id unchanged
