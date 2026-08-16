# P1-GROWTH-07C — WeChat Pay Index Recovery Report

- Date: 2026-08-16
- GitHub main baseline: `167b837`
- Final verdict: **P1-GROWTH-07C = PASS**

## 1. Weak page (WEAK)

- content_id: `cbt-255af4ed003a`
- URL: `https://www.chinaboundtravel.com/posts/wechat-pay-for-foreigners-step-by-step-setup-and-common-mistakes-to-avoid-guide/`
- Title: `How to Set Up & Use WeChat Pay Step by Step (2026 Guide)`
- H1: `How to Set Up & Use WeChat Pay Step by Step (2026)`
- Meta description: setup / identity verification / foreign card / QR payment / errors
- Word count (body): ~2,782; H2 x11; FAQ section with 5 Q&A
- canonicalURL: self; slug stable; content_id stable; draft=false

## 2. Strong page (STRONG)

- content_id: `cbt-707a8899c0a7`
- URL: `https://www.chinaboundtravel.com/posts/how-to-use-wechat-pay-as-a-foreigner/`
- Title: `Can Foreigners Use WeChat Pay in China? (2026 Guide)`
- Word count (body): ~1,246; H2 x8; FAQ section with 5 Q&A
- Indexed: PASS (Submitted and indexed)

## 3. HTTP state

| Check | WEAK | STRONG |
|---|---|---|
| HTTP | 200 | 200 |
| noindex | absent | absent |
| canonical | self (www) | self (www) |
| robots | allowed | allowed |
| size | ~86.9KB | ~64.3KB |

## 4. Current GSC state (URL Inspection API + browser, 2026-08-16)

WEAK:
- verdict: `NEUTRAL`
- coverageState: `Alternate page with proper canonical tag`
- robotsTxtState: `ALLOWED`
- indexingState: `INDEXING_ALLOWED`
- lastCrawlTime: `2026-07-28T07:58:29Z` (BEFORE differentiation live on 2026-08-16)
- pageFetchState: `SUCCESSFUL`
- googleCanonical = userCanonical = `https://chinaboundtravel.com/posts/wechat-pay-for-foreigners-step-by-step-setup-and-common-mistakes-to-avoid-guide/` (self, non-www form after www->non-www 301)
- sitemap: submitted; referringUrls: self + homepage
- Search Analytics 28d (07-19..08-16): 0 clicks / 1 impression

STRONG: verdict `PASS`, `Submitted and indexed`; last crawl 2026-08-09; 28d: 0 clicks / 108 impressions.

## 5. Duplicate analysis (STRONG vs WEAK)

- Exact overlapping sentences: 1 (shared Tour Card factual sentence)
- 6-gram overlap: 3.1% of STRONG / 1.3% of WEAK
- Intents distinct: eligibility/overview vs step-by-step setup
- Unique sections in WEAK: setup steps, QR/merchant payment, troubleshooting, European tips, WeChat vs Alipay
- Reciprocal internal links present both directions
- Detail: `reports/seo/WECHAT_PAY_INDEX_DIFFERENTIATION_REVIEW.md`

## 6. Technical issues

- None found. No noindex, no wrong canonical, no redirect, robots allowed, fetch successful, not draft.
- The "Alternate page with proper canonical tag" state reflects the **pre-differentiation crawl (07-28)**, not the current differentiated page. No code change required.

## 7. Decision

- Decision engine: case C (duplicate signal + sufficient differentiation) -> **REQUEST_INDEXING = YES**
- Precondition checklist all satisfied: HTTP 200, indexable, user canonical = self, google canonical not conflicting, robots allowed, title/H1 distinct, intent distinct, no high-duplicate sections, affiliate/UTM unchanged.

## 8. Request indexing result

- Method: GSC browser UI (logged-in account Joran Fan), URL Inspection -> Request indexing
- URL requested: WEAK page (1 URL only; no batch)
- Result: GSC confirmation "已请求编入索引" — URL added to priority crawl queue (2026-08-16)
- No quota / permission / network / manual-verification blocking encountered.

## 9. Tracker

- `reports/seo/WECHAT_PAY_INDEX_RECOVERY_TRACKER.csv`
- WEAK status: `REQUESTED`; STRONG status: `INDEXED`

## 10. Observation plan

- Keep WEAK page stable for 14–28 days (no further edits).
- Re-inspect weekly via the tracker; expect coverageState to move from
  "Alternate page with proper canonical tag" -> "Submitted and indexed" (or equivalent PASS).
- Use GROWTH-06 measurement loop for CTR/impressions/position after indexing.

## 11. Tests / regression

- Full test suite, Hugo build, content_id audit, internal link audit, meta audit, secret scan — see run results in this round (all PASS, 0 failed / 0 skipped).

## 12. Production state

- Production: `167b837` (latest main); no code change in this round (GSC-only action + reports).
- STRONG page unchanged; WEAK page unchanged (differentiation from GROWTH-07 remains live).

## Next

- P1-GROWTH-08 GROWTH VALIDATION (per instruction, since PASS).
