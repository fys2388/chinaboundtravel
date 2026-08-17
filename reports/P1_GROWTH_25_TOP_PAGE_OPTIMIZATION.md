# P1-GROWTH-25 — Top Page Optimization & Revenue Review

- Generated: 2026-08-17 | HEAD: a60a3ba (working tree contains uncommitted P1-GROWTH-24 + P1-GROWTH-25 changes)
- Data labels: GSC 28d = CACHED (fetch 2026-08-16); GA4 28d = CACHED snapshot 2026-08-17 (sitewide); revenue = REVENUE_NOT_AVAILABLE
- Final status: **PASS** (1 content file changed, 2 allowed; tests green; awaiting commit/push approval)

## 1. TOP 5 Page Review

Created: reports/seo/P1_GROWTH_25_TOP_PAGE_REVIEW.csv

| page | content_id | impressions | clicks | CTR | position | indexed | canonical | legacy persona | commercial intent | priority | action |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 144-Hour Visa 15 Countries | cbt-244822dc113b | 87 | 0 | 0.0% | 41.87 | INDEXED | OK | 0 | VISA | P1 | MONITOR |
| WeChat Pay Foreigners | cbt-707a8899c0a7 | 83 | 0 | 0.0% | 62.45 | INDEXED | OK | 0 | PAYMENT | P1 | MONITOR |
| August Monthly Update | cbt-80ac63165adb | 52 | 0 | 0.0% | 11.40 | INDEXED | OK | 0 | TRAVEL_GUIDE | P1 | CONTENT_UPDATE (executed: title) |
| Photography Guide | cbt-bfeaa5ca9007 | 51 | 0 | 0.0% | 20.88 | INDEXED | OK | 0 | TRAVEL_GUIDE | P1 | MONITOR |
| Xi'an Terracotta Warriors | cbt-d7747b73c978 | 1 | 0 | 0.0% | 5.00 | INDEXED | OK | 2 | TRANSPORT | P2 | MONITOR (legacy migration deferred - sample too small) |

Excluded per instructions: Transportation Guide (REV002 frozen) and all active experiment pages.

## 2. Actions & Rationale

- **August Monthly Update -> CONTENT_UPDATE (title only):** indexed, 52 impressions (>= 50), no active experiment, no canonical conflict, CTR opportunity evidenced (0 clicks / 52 impressions at avg position 11.40 - first-page boundary with zero CTR). Title aligned to the sibling monthly format ("China Travel Guide: July 2026 Updates & Visa Rules") and to the page's H1/body hook ("Latest Visa Rules"). URL / slug / canonical / content_id / affiliate / UTM untouched.
- **144-Hour Visa 15 Countries -> MONITOR:** position 41.87 is a ranking/relevance problem, not a title-CTR problem; GROWTH-05 cluster caution applies. Front-matter corruption fix already executed in P1-GROWTH-24.
- **WeChat Pay Foreigners -> MONITOR:** position 62.45 is a ranking problem; page is the STRONG reference page of the WeChat cluster currently under GROWTH07C observation - no edits to avoid interfering.
- **Photography Guide -> MONITOR:** title already strong ("Best Spots & Tips"); 0/51 clicks at position 20.88 is ranking-driven; evidence not clear enough for a title/meta change.
- **Xi'an -> MONITOR:** only legacy-persona candidate from the P1-GROWTH-24 list, but 1 impression does not meet the "meaningful impressions" bar - no migration this round.

## 3. Changes Made (this round)

1. content/posts/2026-08-01-chinabound-travel-guide-2026-08-monthly-update.md - title changed from "China Travel Guide: August 2026 Update" to "China Travel Guide: August 2026 Updates & Visa Rules" (single front-matter line; verified in build: <title> updated, canonical + content_id unchanged).
2. Scope-guard tests x5 extended with P1-GROWTH-25 whitelist entry (tests/test_brand_identity_p2.py, test_brand_legacy_pilot.py, test_growth07_content_differentiation.py, test_growth21_payment_cluster.py, test_travelpayouts_drive.py) - repo convention; assertions unchanged otherwise.
3. Regenerated inventories that mirror the new title (side effect of existing engines): reports/revenue/PAYMENT_CLUSTER_INVENTORY.csv, reports/seo/CONTENT_EXECUTION_BATCHES.md; reports/revenue/AFFILIATE_FUNNEL_INVENTORY.csv refreshed by affiliate regression (stable at 278 rows).

Internal linking: August page already links to the 144-hour guide, payment guide, eSIM guide, insurance, and destination guides - no links added (nothing missing; adding blindly prohibited).

## 4. Revenue Review

Full report: reports/revenue/P1_GROWTH_25_REVENUE_REVIEW.md

| experiment | baseline | current | delta | sample | data source | decision |
|---|---|---|---|---|---|---|
| REV001 | 162 sessions / 365 pv / 0 clicks (2026-07-19..08-15); GSC 159 imp / 0 clk / 19.55 | sitewide 166 sessions / 374 pv / 0 clicks | +4 sessions / +9 pv sitewide (not page-attributable); clicks 0->0 | 1 day; clicks < 20 | CACHED + GA4_API 2026-08-17 | INSUFFICIENT_SAMPLE -> WAITING_REVIEW_GATE |
| REV002 | page sessions/pv NULL; 0 clicks; GSC 107 imp / 0 clk / 22.33 | FROZEN; sitewide 166 / 374 / 0 | none measurable | 1 day; clicks < 20 | CACHED + GA4_API 2026-08-17 | INSUFFICIENT_SAMPLE -> WAITING_REVIEW_GATE |
| DRIVE-001 | pre-drive 28d baseline (2026-07-19..08-16) | ACTIVE, observation 1 day | CTA impressions NOT_AVAILABLE; clicks 0; outbound 0; revenue NULL | 1 day; clicks < 20 | TRAVELPAYOUTS_DRIVE_BASELINE + GA4_API | INSUFFICIENT_SAMPLE -> KEEP_RUNNING |

Revenue: NULL (REVENUE_NOT_AVAILABLE) - nothing fabricated.

## 5. Experiment Status

| experiment | status | gate | this round |
|---|---|---|---|
| REV001 | RUNNING | >= 2026-09-13 | WAITING_REVIEW_GATE (not reached) |
| REV002 | RUNNING / FROZEN | >= 2026-09-13 | WAITING_REVIEW_GATE (not reached) |
| REV003 | PENDING | after REV002 gate | no action |
| DRIVE-001 | ACTIVE | >= 28d observation | KEEP_RUNNING (1 day) |
| GROWTH05 / 07B / 07C | RUNNING / WAITING_RECRAWL | - | no action; no re-request of indexing |

No experiment CTA / placement / partner modified.

## 6. Deferred Items

- 144-Hour Visa 15 Countries: body freshness wording ("announced today") + deeper content update - needs editorial approval.
- WeChat Pay Foreigners: title/meta/content update after GROWTH07C observation window closes.
- Photography Guide: CTR copy + affiliate CTA gap - needs GSC query-level evidence and approval.
- Xi'an: persona migration - needs a real-traffic sample (currently 1 impression) and pilot approval.
- Duplicate-H1 pattern on monthly updates (theme title H1 + body H1) - template-level decision, not content-level.
- Pre-existing non-TOP5 meta descriptions too long (china-airport-transfer-guide 178, china-transportation-card-guide 169).

## 7. Regression Results

| check | result |
|---|---|
| python -m pytest tests/ -q | 615 passed / 0 failed / 0 skipped |
| python scripts/content_id_audit.py audit --strict | PASS - 60/60 content_id, 0 missing, 0 duplicates |
| hugo --gc --minify | SUCCESS (August page verified: new <title>, canonical unchanged) |
| internal link audit | PASS - 589 links, 404=0, 301=0, malformed=0 |
| meta audit | PASS - duplicates 0; 2 pre-existing too_long (non-TOP5) |
| redirect chains | PASS - chains 0 / loops 0 / final-not-200 0 |
| affiliate regression | PASS - Klook OK (341 days); funnel inventory stable (278 CTA rows); affiliate pytest tests green |
| secret scan | PASS (pytest test_no_hardcoded_secrets + test_secret_name_contract) |
| workflow validation | PASS (pytest test_workflow_names + test_workflow_yaml) |

## 8. Next Actions

1. Commit after approval (recommended message below), then re-check the built monthly update on production after deployment.
2. Re-pull GSC after 28 days; re-run TOP page review with fresh data (especially Xi'an and WeChat positions).
3. GROWTH07C / GROWTH07B: wait for recrawl; verify coverage at end of observation window; no re-request.
4. REV001 / REV002 / DRIVE-001: keep running; review at 2026-09-13 gate; add page-level GA4 attribution before the gate if possible.
5. Next content round: approved title/meta candidates (Photography, WeChat foreigners) once evidence or cluster gates allow.

## 9. Git Status (waiting for approval)

- Do not push automatically.
- Recommended commit message: `chore: P1-GROWTH-25 top page optimization and revenue review`
- Suggested scope: this round's changes only, OR combined with the uncommitted P1-GROWTH-24 changes (`chore: P1-GROWTH-24/25 content quality, indexing and top page optimization`) - user decision.
