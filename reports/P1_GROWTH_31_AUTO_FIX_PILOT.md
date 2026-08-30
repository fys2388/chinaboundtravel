# P1-GROWTH-31 Content Trust Auto-Fix Pilot

- Status: PASS
- Date: 2026-08-29
- Scope: 10 content posts (maximum allowed), body text only
- No new content, no experiments started
- Immutable fields preserved: URL, slug, canonical, content_id, title, affiliate URLs, UTM

## Selected Candidates

Selection followed the required priority order: indexed > meaningful GSC impressions >
commercial relevance > no active experiment > no unresolved canonical conflict > trust issues present.
All 10 posts came from the Growth Control Plane queue with status READY and were not frozen.

| content_id | file | priority | impressions |
|---|---|---|---|
| cbt-244822dc113b | china-extends-144-hour-visa-free-transit-policy-to-more-countries.md | P0 | 87 |
| cbt-707a8899c0a7 | 2026-05-22-how-to-use-wechat-pay-as-a-foreigner.md | P1 | 83 |
| cbt-80f6c218ad94 | western-sichuan-overland-camping-route.md | P1 | 26 |
| cbt-bf4ec5e57a07 | 2026-07-03-guilin-and-yangshuo-the-ultimate-karst-landscape-guide-for-2026-guide.md | P1 | 24 |
| cbt-34777b6c17c1 | 2026-06-30-zhangjiajie-avatar-mountains-complete-guide-to-chinas-most-spectacular-park.md | P1 | 20 |
| cbt-baa2f6fba2f0 | 2026-07-27-accommodation-tips-guide.md | P2 | 17 |
| cbt-550a6e3e929c | 2026-06-23-sichuan-hotpot-guide-history-best-restaurants-and-cultural-significance.md | P2 | 11 |
| cbt-302467d853db | 2026-05-25-shanghai-bund-french-concession-2-day-guide.md | P2 | 11 |
| cbt-cfd5d7b39f09 | 2026-08-03-chinese-language-survival-phrases-guide.md | P2 | 11 |
| cbt-c59607760fee | 2026-07-01-chinese-street-food-a-first-timers-guide-to-night-markets-and-street-stalls.md | P2 | 6 |

## Fixes Applied

- AUTO_FIX: removed fabricated first-person experience, fake family/local claims, invented
  local quotes, legacy conversational persona wording, and broken instruction wording.
- SAFE_NORMALIZE: repaired corrupted superlative/absolute wording (malformed `a popular`
  artifacts) without introducing new factual claims; softened unsupported absolutes.
- AUTO_FIX (formatting): repaired NUL-byte heading corruption, malformed markdown links and
  shortcodes, broken parentheticals, duplicated labels, heading structure, and table headers.
- Preserved: legitimate Chinese names, place names, food names, and language content.
- No replacement facts were invented for visa, policy, price, fee, opening hours, transport
  schedule, distance, duration, availability, or numerical claims. Those remain
  FACT_CHECK_REQUIRED and unchanged.

## Counts

| Outcome | Count |
|---|---|
| Auto-fixed | 33 |
| Safe-normalized | 20 |
| Preserved (immutable / no safe fix) | 0 targeted rewrites |
| Downgraded | 0 |
| Still FACT_CHECK_REQUIRED | 5 (claims preserved, not rewritten) |

## Validation

| Check | Result |
|---|---|
| pytest tests/ -q | 690 passed, 0 failed, 0 skipped |
| content_id audit --strict | PASS (58/58) |
| hugo --gc --minify | PASS (396 pages) |
| Internal link audit | PASS (571 links, 0 broken/malformed) |
| Meta audit | PASS (6 known pre-existing description-length warnings, none in pilot files) |
| Brand identity audit --legacy | 0 legacy persona hits across content/posts |
| Persona guard | PASS on all 10 edited posts |
| Affiliate regression | 71 passed |
| Secret scan / workflow validation | 10 passed |

## Governance

- The risk gate was not part of this pilot; no publish/deploy action was taken.
- Protected surfaces (REV001, REV002, DRIVE-001, GA4 event schema, Drive, social workflow,
  affiliate partners/URLs, UTM) were not modified.
- Scope guardrails in `test_growth07_content_differentiation.py` and
  `test_growth21_payment_cluster.py` were updated to authorize the 10 P1-GROWTH-31 files;
  assertions were not weakened.

## Deliverables

- reports/content_audit/P1_GROWTH_31_AUTO_FIX_REPORT.csv
- reports/content_audit/P1_GROWTH_31_AUTO_FIX_REPORT.md

No commit, no push, no deployment.
