# P1-GROWTH-06 — SEO Measurement Loop Report

- Date: 2026-08-16
- GitHub main baseline: `37a78c7` (origin/main == HEAD at start)
- Production: P1-GROWTH-05 live (deployment `a4c33bef-b90f-4986-88c2-568e4986978f`)

## 1. Experiment Registry

- File: `reports/seo/EXPERIMENT_REGISTRY.csv`
- Registered experiment: **GROWTH05-CTR-001**
  - content_id: `cbt-b4ff4381a014` (144-Hour Visa-Free Transit)
  - type: TITLE_META; start 2026-08-16; baseline 2026-08-16
  - primary_metric: CTR; secondary: Impressions; Clicks; Average_Position
  - minimum_observation_days: 28; status: RUNNING; decision: PENDING
  - Revenue fields (`affiliate_clicks`, `affiliate_sessions`, `revenue`) present and null — reserved for future affiliate measurement.

## 2. Current Experiment

- GROWTH05-CTR-001 measures the GROWTH-05 title/meta change on the 144-hour page:
  - OLD_TITLE → NEW_TITLE: `144-Hour Visa-Free Transit in China (2026 Guide)` → `China 144-Hour Visa-Free Transit (2026 Guide)`
  - OLD_DESC → NEW_DESC: question-form → statement-form (same facts, <=160 chars)
- Protection invariants locked by regression test: URL, canonical, affiliate, UTM, content_id unchanged.

## 3. Measurement Logic

- Script: `scripts/seo_experiment_measurement.py`
  - `--experiment-id <id>` / `--all`, `--days`, `--output`, `--fetch-live`, `--snapshot-dir`
  - Live GSC via existing `gsc_utils.py` (`--fetch-live`); on any failure it falls back to raw CSVs and records `data_source=RAW`
  - Offline default reads `reports/seo/raw_pages_{days}d.csv`
  - Emits baseline/current/delta (abs + %) for CTR, impressions, clicks, position
  - Snapshot: `reports/seo/experiment_snapshots/<id>_<date>.json` + persisted `_baseline.json` (created on first run)
- Classification (transparent, no LLM):
  - INSUFFICIENT_SAMPLE: observed days < minimum OR current clicks < 20
  - POSITIVE: CTR delta >= +20% AND impressions delta >= -10%
  - NEUTRAL: CTR delta within +/-20%
  - NEGATIVE: CTR delta <= -20%

## 4. Current Baseline (T0, 2026-08-16)

- GROWTH05-CTR-001 (28d): impressions 107 / clicks 0 / CTR 0.00% / avg position 74.05
- Snapshot persisted: `reports/seo/experiment_snapshots/GROWTH05-CTR-001_baseline.json`
- Results: `reports/seo/EXPERIMENT_RESULTS.md`

## 5. Current Status

- GROWTH05-CTR-001 = **INSUFFICIENT_SAMPLE** (0 observed days, 0 clicks) — expected at T0. No success/failure claim.
- GSC live fetch: **UNAVAILABLE this session** (3 attempts, network timeout to Google APIs). Per boundary, only reported, nothing modified. Offline raw CSVs (fetched 2026-08-16 01:41) used as current data; refresh with `--fetch-live` when network allows.

## 6. WeChat Recommendation (MANUAL_REVIEW, no change)

- File: `reports/seo/WECHAT_PAY_DUPLICATE_DECISION.md`
- Evidence: INDEXED page `how-to-use-wechat-pay-as-a-foreigner` (cbt-707a8899c0a7): 83 imp / 0 clicks / pos 62.45. NOT_INDEXED `wechat-pay-for-foreigners-...` (cbt-255af4ed003a): 1 imp / 0 clicks / pos 11.0. Both self-canonical; Google treats the newer page as alternate.
- Similarity heuristic: unique-token Jaccard 0.248; 46% of A's tokens in B, 35% of B's in A; verbatim 10-gram overlap 0.0021 (not duplicate prose).
- Recommendation: **B. Differentiate** (split intents: how-to-use vs setup+mistakes), fallback **A. Merge** (301 into INDEXED page). Default principle applied: keep the stronger INDEXED page. Owner approval required; execution deferred to GROWTH-07.

## 7. Next Experiment Candidates (Top 5, not executed)

- File: `reports/seo/NEXT_EXPERIMENT_CANDIDATES.md`
- 1. China Transportation Guide (cbt-17c6738ffb32) — 107 imp, pos 22.33, TRANSPORT → TITLE_META + INTERNAL_LINK
- 2. WeChat Pay setup guide (cbt-255af4ed003a) — PAYMENT, pos 11, 1 imp → depends on WeChat decision
- 3. China Travel Safety (cbt-dfe3904705ea) — 7 imp → TITLE_META monitor (low data)
- 4/5. July Update (cbt-95d9a1b95440) and Foodie's Guide (cbt-acae8a973429) — 0 imp → MONITOR
- Data note: 144h policy article (87 imp, pos 41.87) is outside TOP-10; add to next prioritization re-run.
- No candidate ranked high on near-zero impressions.

## 8. Affiliate Measurement Readiness

- Registry schema reserves `affiliate_clicks`, `affiliate_sessions`, `revenue` (all null now).
- GSC does not expose affiliate/revenue; no fabricated values. Future affiliate experiments can attach revenue at the registry/measurement layer without schema changes.

## 9. Tests

- New: `tests/test_seo_experiment_measurement.py` (12 tests) — CTR/impression/click/position deltas, POSITIVE/NEUTRAL/NEGATIVE thresholds, INSUFFICIENT_SAMPLE guard (clicks < 20, days < 28), deterministic end-to-end output, registry schema, 144-hour protection invariants.
- Updated: `tests/test_growth05_first_content_action.py` (2 stale pre-commit guards → durable regression vs commit `60f1c17`; body/affiliate/UTM byte-identical, no layouts/config/other-post changes since).
- Full suite: **176 passed / 0 failed / 0 skipped**
- `hugo --gc --minify` exit 0; content_id audit PASS (57 posts, 0 missing/malformed/duplicates)
- Secret scan: tracked-file scan PASS; git history scan **0 hits**
- Internal link audit: 0 404 / 0 malformed / 0 301
- Workflow YAML: 18/18 valid (validated in GROWTH-05; unchanged this round)

## 10. Git Status

- Committed files (only): `scripts/seo_experiment_measurement.py`, `tests/test_seo_experiment_measurement.py`, `tests/test_growth05_first_content_action.py` (stale-guard update), `reports/seo/EXPERIMENT_REGISTRY.csv`, `reports/seo/EXPERIMENT_RESULTS.md`, `reports/seo/experiment_snapshots/*`, `reports/seo/CONTENT_EXPERIMENT_DASHBOARD.md`, `reports/seo/WECHAT_PAY_DUPLICATE_DECISION.md`, `reports/seo/NEXT_EXPERIMENT_CANDIDATES.md`, `reports/P1_GROWTH_06_MEASUREMENT_LOOP.md`
- No `content/posts/*`, `layouts/*`, `hugo.toml`, or affiliate config changed.
- Commit: `feat: add seo experiment measurement loop` → normal fast-forward push.

## Final Verdict

- Registry = PASS; measurement script = PASS; classification rules = PASS; T0 baseline = recorded; WeChat recommendation = documented (no change); candidates = documented; tests = PASS.

**P1-GROWTH-06 = PASS**

NEXT = P1-GROWTH-07 WECHAT PAY CONTENT DECISION + FIRST SEO EXPANSION
