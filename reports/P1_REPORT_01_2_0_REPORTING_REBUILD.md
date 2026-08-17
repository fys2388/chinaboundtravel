# P1-REPORT-01 — ChinaBound 2.0 Reporting Rebuild

- Generated: 2026-08-17
- HEAD: `60fa428`（rebase 至 origin/main 4619aba 之上；本地基线 247e686）
- Status: **PASS**

## 1. Reports rebuilt

| Artifact | Result |
|---|---|
| reports/P1_GROWTH_12_FIRST_REVENUE_EXPERIMENT.md | Rebuilt — REV001 = Food Delivery / Airalo（144h/Booking 旧定义已清除） |
| reports/revenue/GROWTH12_BASELINE.csv | Rebuilt — Food Delivery baseline |
| reports/revenue/REVENUE_EXPERIMENT_DASHBOARD.md | Rebuilt — UTF-8、无 GBK 乱码、generated_at 2026-08-17、data_source、当前实验状态 |
| reports/revenue/REVENUE_EXPERIMENT_REGISTRY.csv | Normalized — REV-001 → REV001 |
| reports/revenue/REVENUE_EXPERIMENT_CANDIDATE_LOCK.md | Normalized — REV-001 → REV001 |
| reports/GROWTH_MASTER_DASHBOARD.md | Rebuilt — GBK → UTF-8、A 段旧 REV-001 引用修正 |
| reports/P1_GROWTH_12A_REVENUE_CANDIDATE_LOCK.md | Normalized — REV-001 引用更新为 REV001 新定义 |
| reports/P1_BRAND_02_LEGACY_PERSONA_REVIEW.md | Re-run on 60 posts（25 legacy persona hits） |
| reports/P1_BRAND_02_BRAND_IDENTITY_AUDIT.md | Refreshed |
| reports/seo/（TIER_A/B、CONTENT_OPPORTUNITY_FEED、TOP_10、BATCHES、FIRST_CONTENT_REVIEW_QUEUE、INDEX_RECOVERY_QUEUE、TOPIC_CLUSTER_GAPS、CANONICAL_CONFLICT_QUEUE、content_opportunity_scores.csv） | Re-run on 60 posts（B=8 / C=24 / D=28；top score 88） |
| reports/revenue/（REVENUE_OPPORTUNITY_SCORES、TOP_20、TOP_5、DRIVE_OPPORTUNITIES、PARTNER_MATRIX、REVENUE_FUNNEL、CANDIDATES、COMMERCIAL_CONTENT_PRIORITY、COMMERCIAL_CONVERSION_TARGETS、CONTENT_REVENUE_GAPS） | Re-run on 60 pages（A=1 / B=4 / C=20 / D=35；13 priority rows） |
| reports/revenue/（REVENUE_DASHBOARD、PRE_DRIVE_BASELINE、TOP_COMMERCIAL_PAGES_DRIVE、TRAVELPAYOUTS_DRIVE_BASELINE） | Regenerated from GA4 live read（2026-08-17；sessions 166 / pageviews 374 / affiliate_clicks 0） |
| reports/revenue/EXPERIMENT_COMPARISON.csv | Regenerated via `--as-of 2026-08-17`（REV001/DRIVE-001 days=1） |
| docs/AI_CONTEXT.md | Refreshed（94 行；HEAD、60/60、BRAND-04、实验注册表、2.0 报告状态） |

## 2. Stale reports retired / rebuilt

- REV001 冲突（144h Visa / Booking 定义）→ 已重建为 Food Delivery / Airalo，旧定义未保留。
- `reports/revenue/GROWTH12_BASELINE.csv` 孤儿 144h 基线 → 已重建为 Food Delivery 基线。
- `reports/GROWTH_MASTER_DASHBOARD.md` GBK 乱码 + 旧 REV-001 描述 → 已重建为 UTF-8 并修正。
- 57-post 时代报告引擎输出 → 已按 60-post inventory 重跑（brand legacy / SEO opportunity / revenue / commercial conversion）。

## 3. Current 2.0 baseline

- Published posts: **60**；content_id: **60/60**（`content_id_audit.py audit --strict` = PASS）
- Revenue: **NULL**（REVENUE_NOT_AVAILABLE，未编造收入）
- GA4（fetch 2026-08-17）：28d sitewide sessions 166 / pageviews 374 / affiliate_clicks 0
- GSC：缓存基线为 2026-08-16 快照（报告中均标注实际抓取日期）
- Drive: **ACTIVE**（DRIVE-001 RUNNING，start 2026-08-16）

## 4. REV001 corrected identity

| Field | Value |
|---|---|
| content_id | `cbt-e464169c4991` |
| Page | Chinese Food Delivery: Meituan & Ele.me Guide |
| partner | Airalo |
| placement | food-delivery-mid-content |
| status | RUNNING |
| start | 2026-08-16 |

## 5. Current experiment registry

| Experiment | Definition | status |
|---|---|---|
| REV001 | Food Delivery · cbt-e464169c4991 · Airalo · food-delivery-mid-content | RUNNING（start 2026-08-16） |
| REV002 | Transportation Guide · cbt-17c6738ffb32 · Trip.com mid-CTA | RUNNING（frozen，review gate >= 2026-09-13） |
| REV003 | CTA_COPY variant（Transportation） | PENDING（等待 REV002 评审） |
| DRIVE-001 | Site-wide Travelpayouts Drive | RUNNING（ACTIVE） |
| GROWTH05-CTR-001 / GROWTH07B-TECH-001 / GROWTH07C-INDEX-001 | SEO 观察 | INSUFFICIENT_SAMPLE / WAITING_RECRAWL |

## 6. Content ID drift fix

- `reports/revenue/TOP_COMMERCIAL_PAGES_DRIVE.md` / `.csv`：Transportation Guide 已更正为实际 content_id `cbt-17c6738ffb32`（原 `cbt-52a577c1b2b8` 为 legacy alias）。文章内容未改动。

## 7. Validation results

| Check | Result |
|---|---|
| `python -m pytest tests/ -q` | 595 passed，0 failed，0 skipped |
| `python scripts/content_id_audit.py audit --strict` | PASS（60/60，0 missing/malformed/duplicate） |
| `hugo --gc --minify` | SUCCESS（377 pages） |
| Secret findings | 无新增（pytest 全绿，无新 secret 扫描告警） |

## 8. Remaining stale reports（未自动重写）

- reports/P1_GROWTH_03_CONTENT_OPPORTUNITY_ENGINE.md — 标题仍为 57-post 基线（数据 feed 已按 60 重跑）
- reports/P1_GROWTH_04_CONTENT_PRIORITIZATION.md — 同上
- reports/P1_GROWTH_09_AFFILIATE_REVENUE_BASELINE.md — 46-page / 57-post 基线
- reports/P1_GROWTH_11_REVENUE_OPTIMIZATION.md — 57-page 分数叙述（底层 CSV 已按 60 重跑）
- reports/P1_GROWTH_22_PAYMENT_CONTENT_RELEASE.md — 线上部署验证章节不完整
- reports/seo/content_inventory.csv — 57 行，已由 CONTENT_SEO_INVENTORY.csv（60 行）取代
- reports/seo/daily_search_performance*.csv — 2026-08-16 01:41 快照，待下次 GSC 拉取刷新
- 08-16 GSC 快照衍生报告：SEO_OPPORTUNITIES.md / seo_opportunities.csv / PAGE_1_OPPORTUNITIES.md / LOW_CTR_OPPORTUNITIES.md / QUERY_INTENT_DISTRIBUTION.md / query_intent_distribution.csv / SITEMAP_INDEX_GAP.md — 数据窗口 2026-08-16，待新 GSC 拉取后重建

## 9. Git

- Commit：`chore: reconcile ChinaBound 2.0 reporting baselines`（60fa428，已 push origin/main；先 rebase 集成远端 4 个 chore 提交，无 force push）
- 仅包含本任务 reporting/code/doc 变更（scripts/、reports/、docs/AI_CONTEXT.md）

---

## Final

**P1-REPORT-01 = PASS**