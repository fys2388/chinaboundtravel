# P1-GROWTH-12A — Revenue Experiment Candidate Lock Report

- 日期：2026-08-16
- 基线：GitHub main `0cde7e4`
- 状态：**PASS**
- 本轮仅执行：读取、排除冲突、baseline、candidate lock；**未修改任何文章**

## 1. 排除（实验隔离）

| 页面 | 排除原因 |
|---|---|
| 144-Hour Visa (cbt-b4ff4381a014) | GROWTH-05 CTR experiment RUNNING（REV-001 已占用） |
| WeChat Pay strong (cbt-707a8899c0a7) | Index recovery RUNNING |
| High-Speed Rail / Transportation (cbt-52a577c1b2b8) | Technical SEO / indexing observation + canonical cluster |
| 144-Hour Visa 15 Countries (cbt-244822dc113b) | 与 144h 主题簇重叠（隔离风险）；summary malformed 既有问题；legacy persona 严重，应先内容修复 |
| Brand-03 3 篇（Western Sichuan / Guilin / Hotpot） | Legacy persona migration 观察中 |

## 2. Locked Candidate

| Field | Value |
|---|---|
| REV001_CANDIDATE | **Chinese Food Delivery: Meituan & Ele.me Guide** |
| content_id | `cbt-e464169c4991` |
| url | https://www.chinaboundtravel.com/posts/chinese-food-delivery-meituan-eleme-guide/ |
| partner | Airalo, Aviasales, Booking, Klook（4 个，全部 INLINE） |
| commercial_intent | FOOD / APP GUIDE (HIGH) |
| sessions / pageviews (28d sitewide) | 162 / 365 |
| gsc_impressions / clicks / position (28d) | 159 / 0 / 19.55 |
| affiliate_clicks (28d) | 0 |
| current_cta | 4 个页尾 INLINE shortcode，无 mid-content CTA |
| drive_status | ACTIVE (DRIVE-001 RUNNING, exactly 1/page) |
| brand_migration_status | NOT in Brand-03 pilot |
| conflicts | 无 canonical conflict / 无 index blocker / 旧 URL 已 301 |

## 3. 选择依据

- TOP-20 Revenue #3（score 72.5，confidence 80.7%，action CONTENT_COMMERCIALIZATION）。
- GSC 28d impressions=159（TOP 20 中最高之一）→ 有真实搜索曝光可观察。
- 已有 4 个 affiliate partner 且全部 INLINE → 只需增加 mid-content CTA，不新增合作。
- 页面稳定：draft=false、canonical=self、无 canonical conflict、无 index blocker、旧日期 URL 已 301 到 canonical。
- 与所有运行中实验零重叠（隔离检查全部 PASS）。

## 4. Baseline（REV001_BASELINE.csv）

| Field | Value |
|---|---|
| content_id | cbt-e464169c4991 |
| url | .../posts/chinese-food-delivery-meituan-eleme-guide/ |
| baseline_start / end | 2026-07-19 / 2026-08-15（28d 窗口） |
| sessions / pageviews | 162 / 365（sitewide；页面级 GA4 不可得） |
| affiliate_clicks / per_1000 | 0 / 0.0 |
| gsc_impressions / clicks / position | 159 / 0 / 19.55 |
| revenue | NULL（REVENUE_NOT_AVAILABLE，不伪造） |

## 5. 实验隔离确认

- [x] Brand-03 no overlap（pilot = Western Sichuan / Guilin / Hotpot）
- [x] Drive-001 no overlap（全站 script 保持不动）
- [x] GROWTH-05 no overlap（144h）
- [x] GROWTH-07 no overlap（WeChat 2 篇 + transport）
- [x] 无 canonical / index / redirect blocker

## 6. 已知限制（随候选锁定）

1. 页面仍含 legacy persona 内容（本轮不修；CTA 必须避开 persona 段落）。
2. 页面存在既有 UTF-8 乱码字符（记录不修）。
3. 页面级 GA4 数据不可得 → baseline 用全站值并标注 DATA_SCOPE=sitewide。
4. LOW_DATA_WARNING ACTIVE：全站 28d GSC clicks=3，任何结论必须 INSUFFICIENT_SAMPLE。

## 7. 产出文件

- reports/revenue/REVENUE_EXPERIMENT_CANDIDATE_LOCK.md
- reports/revenue/REV001_BASELINE.csv
- tests/test_growth12a_candidate_lock.py

## 8. Git

- commit: `docs: lock first revenue experiment candidate`（仅 baseline / candidate lock / tests）

## Final Verdict

- **P1-GROWTH-12A = PASS**
- REV001_CANDIDATE = `cbt-e464169c4991` / https://www.chinaboundtravel.com/posts/chinese-food-delivery-meituan-eleme-guide/
- NEXT = P1-GROWTH-12B CTA EXPERIMENT
