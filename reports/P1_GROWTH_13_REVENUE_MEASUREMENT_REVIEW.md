# P1-GROWTH-13 — Revenue Measurement Review Report

- 日期：2026-08-16
- 基线：GitHub main `cea6382`
- 状态：**PASS / WAITING**（系统建立成功；所有实验处于观察窗口内，不判 BLOCKED）
- 本轮仅读取与分析，未修改任何实验/文章/Drive/SEO 页面

## 1. REV001（CTA_PLACEMENT）
- Page：Chinese Food Delivery（cbt-e464169c4991）
- Start：2026-08-16；observation_days = 0
- Baseline：sessions 162 / pageviews 365（sitewide）、affiliate_clicks 0、per1000 0.0、GSC 159/0/19.55
- Current：post-CTA 无数据（0 天）→ **INSUFFICIENT_SAMPLE**
- DATA_SOURCE = CACHED

## 2. DRIVE-001
- Start：2026-08-16；post 0 天
- Pre-drive baseline：sessions 162 / pageviews 365 / affiliate_clicks 0 / per1000_sessions 0.0
- → **INSUFFICIENT_SAMPLE**；Drive 配置未变

## 3. 144-Hour Visa（GROWTH05-CTR-001）
- Impressions 107 → 131；position 74.05 → 46.02；clicks 0；CTR 0.0%
- clicks < 20 → **INSUFFICIENT_SAMPLE**（position 改善属早期信号，不判定成功）
- DATA_SOURCE = LIVE（GSC comparison）

## 4. WeChat Weak（GROWTH07C-INDEX-001）
- Index：**WAITING_RECRAWL**（Alternate page with proper canonical tag，last crawl 2026-07-28）
- 不再次 Request Indexing

## 5. High-Speed Rail（GROWTH07B-TECH-001）
- Index：**WAITING_RECRAWL**（旧 crawl 2026-08-06 仍显示 noindex；修复已上线）
- 不请求 indexing

## 6. Unified Comparison（EXPERIMENT_COMPARISON.csv）
| experiment | days | baseline | current | delta | sample | source | status |
|---|---|---|---|---|---|---|---|
| REV001 | 0 | 0.0 | 0.0 | 0.0 | 0 | CACHED | INSUFFICIENT_SAMPLE |
| DRIVE-001 | 0 | 0.0 | 0.0 | 0.0 | 0 | CACHED | INSUFFICIENT_SAMPLE |
| GROWTH05-CTR-001 | 0 | 0.0 | 0.0 | 0.0 | 0 | LIVE | INSUFFICIENT_SAMPLE |
| GROWTH07C-INDEX-001 | 0 | 0.0 | 0.0 | 0.0 | 0 | LIVE | INSUFFICIENT_SAMPLE |
| GROWTH07B-TECH-001 | 0 | 0.0 | 0.0 | 0.0 | 0 | LIVE | INSUFFICIENT_SAMPLE |

## 7. Revenue Availability
- **REVENUE_NOT_AVAILABLE**：无 affiliate revenue API；revenue 一律 NULL；禁止伪造 orders/commission

## 8. Sample Warnings
- 全站 28d GSC clicks=3；所有实验 clicks=0；观察 <28d
- LOW_SAMPLE / INSUFFICIENT_SAMPLE 全局生效；任何短期波动不得判定成败

## 9. Next Actions（NEXT_REVENUE_ACTIONS.md，不自动执行）
- REV001：KEEP_RUNNING / DO_NOT_CHANGE（最早 2026-09-13 评审）
- DRIVE-001：KEEP_RUNNING / DO_NOT_CHANGE（2026-09-13）
- 144h：MEASURE_MORE（position 改善，等待点击样本）
- WeChat Weak：等待 recrawl；Rail：等待 recrawl

## 10. Tests
- 新增 `scripts/revenue_experiment_review.py` + `tests/test_revenue_experiment_review.py`（11 项：sample guard / per1000 / delta / percent / revenue null / classification / cached fallback / deterministic）
- `python -m pytest tests/ -q` → **351 passed, 0 failed, 0 skipped**
- `hugo --gc --minify` PASS；`content_id_audit --strict` PASS；secret scan / affiliate regression / workflow YAML PASS

## 11. Git
- commit `feat: add unified revenue experiment review` → push main（fast-forward）
- 仅提交 scripts / tests / reports；未修改 content/posts、layouts、affiliate URLs、Drive、SEO 实验页

## Final Verdict
- **P1-GROWTH-13 = PASS / WAITING**
- NEXT = 2026-09-13 首次满观察窗口测量（REV001 / DRIVE-001 / GROWTH05-CTR-001）
