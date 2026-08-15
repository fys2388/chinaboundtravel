# P1-GROWTH-05 — First Content Action Report

- Date: 2026-08-16
- GitHub main baseline: `8a844ce` (P1-GROWTH-04, origin/main == HEAD)
- Release SHA: `ccad9cd987994dc208c4716095a29dfea20433b5` (production) — not modified this round
- Scope: 3 growth objects maximum. Only 1 content object changed; 2 verified/locked.

## 1. Selected A / B / C

| ID | content_id | title | url | reason |
|---|---|---|---|---|
| A | cbt-17c6738ffb32 | China Transportation Guide (canonical cluster) | https://www.chinaboundtravel.com/posts/china-transportation-complete-guide-trains-subways-taxis-and-more/ | Highest-priority canonical conflict (priority 88.0, 6 conflict URLs, severity HIGH) |
| B | cbt-255af4ed003a | WeChat Pay for Foreigners: Setup Guide & Mistakes | https://www.chinaboundtravel.com/posts/wechat-pay-for-foreigners-step-by-step-setup-and-common-mistakes-to-avoid-guide/ | Highest-priority not-indexed + highest commercial intent (priority 80.0, PAYMENT) |
| C | cbt-b4ff4381a014 | 144-Hour Visa-Free Transit in China | https://www.chinaboundtravel.com/posts/144-hour-visa-free-transit-guide/ | Confirmed canonical page; P2 CTR opportunity (107 imp / 0 clicks / pos 74.05) |

## 2. ACTION A — Canonical Technical Fix

- Root cause analysis: 6 canonical conflict URLs were inspected against built HTML. All 6 render the expected final canonical today; declared `canonicalURL` == rendered canonical for all 55 checked pages; aliases (`transportation-guide-guide`, etc.) resolve normally. Canonical standardization was completed upstream in `05426ab`.
- Google's remaining conflicts are **content-based judgment** on legacy persona duplicate pages (e.g., food/gastronomic, travel-safety), which are out of scope (41 legacy persona posts must not be touched).
- Change: **none** (no code defect to fix). Result locked with regression tests:
  - `test_canonical_declarations_match_expected`
  - `test_transportation_main_page_keeps_alias_for_old_slug`
  - `test_canonical_rendered_output_when_built`
- Checks: published URL 200 (local build), canonical = final canonical, sitemap/robots unaffected (robots.txt allows; sitemap 71 URLs all exist).
- Verdict: A = **PASS (verified, no change required)**

## 3. ACTION B — Index Recovery

- GSC URL Inspection state: `Alternate page with proper canonical tag` (NOT_INDEXED).
- Investigation: built page is `index, follow`; self-canonical present; `draft: false`; no `robotsNoIndex`; no redirect chain. Root cause is **content overlap** with `how-to-use-wechat-pay-as-a-foreigner` (`cbt-707a8899c0a7`, INDEXED).
- This is not fixable at code level under the no-body-edit boundary.
- Verdict: B = **MANUAL_REVIEW** — decide merge vs differentiation of the two WeChat Pay articles (owner decision, next phase).

## 4. ACTION C — 144-Hour Visa CTR Experiment

- Object: `content/posts/144-hour-visa-free-transit-guide.md` (only title/description changed; body untouched)
- OLD_TITLE: `144-Hour Visa-Free Transit in China (2026 Guide)`
- NEW_TITLE: `China 144-Hour Visa-Free Transit (2026 Guide)`
- OLD_DESCRIPTION: `Who qualifies for China's 144-hour visa-free transit in 2026? Eligible cities, required documents, and the border process, step by step.`
- NEW_DESCRIPTION: `China's 144-hour visa-free transit explained: who qualifies, eligible cities and ports, required documents, and the border process step by step.`
- Rationale: front-load the exact high-volume query pattern ("144 hour visa china"), keep description <= 160 chars, factual, no fabrication, no keyword stuffing (title+desc contain "144-hour" at most twice).
- Rendered output verified (hugo build): title `China 144-Hour Visa-Free Transit (2026 Guide) | ChinaBound Travel`; meta description as above (~152 chars); canonical unchanged; `googlebot: index, follow`; content_id / date / weight unchanged.
- Verdict: C = **PASS**

## 5. Expected Metrics (ACTION C)

- PRIMARY: CTR (28d)
- SECONDARY: Impressions, Position
- Target: CTR > 0.26% baseline; impressions stable or up; position stable or up
- Observation window: at least 28 days after production deploy; LOW_SAMPLE_WARNING active (28d clicks = 3). No success/failure judgment before two consecutive data windows.

## 6. Tests

- New: `tests/test_growth05_first_content_action.py` — 10 tests covering canonical fix lock, indexability state, title/meta validity, no forbidden persona claims, identity fields unchanged, affiliate/UTM unchanged (byte-identical body vs HEAD), and scope control.
- Full suite: `python -m pytest tests/ -q` → **164 passed, 0 failed, 0 skipped**
- `hugo --gc --minify` → exit 0; `public/robots.txt` and `public/sitemap.xml` exist
- `python scripts/content_id_audit.py audit --strict` → PASS (57 posts, 0 missing/malformed/duplicates)
- Secret scan: tracked-file scan (pytest) PASS; git history scan (HEAD + all branches, DOUBAO/MailerLite/Stripe/Resend/Buffer/Feishu/GSC/OAuth/.env patterns) → **0 hits**
- Internal link audit: 558 links, **0 404 / 0 malformed / 0 301**
- Workflow YAML validation: 18/18 valid
- Affiliate regression: Booking / Klook / Aviasales / NordVPN / SafetyWing URLs and UTM unchanged (diff shows only title/description lines changed in the article)

## 7. Git Commit

- Files staged this round (only):
  - `content/posts/144-hour-visa-free-transit-guide.md` (ACTION C)
  - `tests/test_growth05_first_content_action.py`
  - `reports/seo/P1_GROWTH_05_EXPERIMENT_LOG.md`
  - `reports/seo/CONTENT_EXECUTION_BATCHES.md` (title reference sync)
  - `reports/seo/FIRST_CONTENT_REVIEW_QUEUE.csv` (title reference sync)
  - `reports/seo/TOP_10_CONTENT_PRIORITIES.md` (title reference sync)
  - `reports/P1_GROWTH_05_FIRST_CONTENT_ACTION.md`
- Commit: `feat: execute first content growth experiments` (normal fast-forward push)

## 8. Production Deployment Status

- No manual Cloudflare deploy performed (per boundary). Deployment handled by GitHub Actions `deploy-cloudflare-pages.yml` (Post-deploy Tasks), auto-triggered by the push.
- GitHub Actions run: `31903884831` — success (build, deploy, social manifest, CDN purge all OK).
- Cloudflare Pages deployment ID: `a4c33bef-b90f-4986-88c2-568e4986978f` (Production, branch main, source `60f1c17`).
- Production smoke checks: `/` 200; `chinaboundtravel.com` 301 → `https://www.chinaboundtravel.com/`; `robots.txt` 200; `sitemap.xml` 200 (71 URLs, includes 144-hour post); `/posts/144-hour-visa-free-transit-guide/` 200 with new title + meta description live.

## 9. Manual Review Items

- ACTION B: WeChat Pay duplicate content decision (merge vs differentiate) — owner decision required.
- Legacy persona duplicates behind canonical conflicts — out of scope, requires content-dedup policy.
- 41 legacy persona posts — untouched.

## 10. Final Verdict

- A = PASS (verified, no code change)
- B = MANUAL_REVIEW (explicit, not a code fix)
- C = PASS (title/meta experiment)
- Tests = PASS

**P1-GROWTH-05 = PASS**

NEXT = P1-GROWTH-06 MEASUREMENT LOOP
