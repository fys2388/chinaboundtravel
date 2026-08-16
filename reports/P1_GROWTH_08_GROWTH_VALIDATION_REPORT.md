# P1-GROWTH-08 GROWTH VALIDATION REPORT

WORKDIR: `E:\AI\dulizhan\travel-blog`
GitHub HEAD == origin/main: `1a21a6a`
GSC Property: `https://www.chinaboundtravel.com/`
DATA_SOURCE: **LIVE**（GSC Search Analytics + URL Inspection API，2026-08-16）

---

## 1. Experiment A — 144-Hour Visa CTR Experiment

- content_id: `cbt-b4ff4381a014`
- URL: `https://www.chinaboundtravel.com/posts/144-hour-visa-free-transit-guide/`
- 变化: Title + Meta Description（2026-08-16 上线）
- 28d 基线 → 当前：impressions `107 → 131`（+22.4%），clicks `0 → 0`，CTR `0% → 0%`，avg position `74.05 → 46.02`
- Query count: `16 → 18`；NEW: `do i need transit visa in china`, `shanghai 24 hour visa free transit`
- 状态: **INSUFFICIENT_SAMPLE**（clicks = 0 < 20）— 不宣布 WIN/LOSE

## 2. Experiment B — WeChat Pay Weak Page Index Recovery

- content_id: `cbt-255af4ed003a`
- URL: `https://www.chinaboundtravel.com/posts/wechat-pay-for-foreigners-step-by-step-setup-and-common-mistakes-to-avoid-guide/`
- HTTP: 200；Indexable；self canonical；无 noindex（线上实测）
- GSC URL Inspection: coverageState = `Alternate page with proper canonical tag`，verdict = `NEUTRAL`，indexingState = `INDEXING_ALLOWED`，lastCrawl = `2026-07-28`（差异化前的旧抓取）
- googleCanonical == userCanonical == `https://chinaboundtravel.com/posts/wechat-pay-.../`（非 www，与 www property 并存记录）
- 状态: **WAITING_RECRAWL**（已 REQUESTED，等待 Google 重爬后重新判定；本轮不再次请求）

## 3. Observation C — High-Speed Rail Booking Page

- content_id: `cbt-cc4549872c92`
- URL: `https://www.chinaboundtravel.com/posts/china-high-speed-rail-how-to-book-tickets/`
- 线上实测: HTTP 200，self canonical，无 noindex；旧 dated URL `2026-05-25-...` 返回 301 → slug URL
- GSC URL Inspection: coverageState = `Excluded by 'noindex' tag`，indexingState = `BLOCKED_BY_META_TAG`，lastCrawl = `2026-08-06` — 这是 **07B 修复（2026-08-16 04:07）之前的旧抓取快照**
- GSC 数据仍归因于旧 dated URL（`legacy_url_used = True`）：28d imp `138`，position `30.14 → 12.42`（数据迁移前旧窗口对比，仅作参考）
- 状态: **NOT_INDEXED（旧快照）**，实际线上已 indexable，等待 Google 重爬 → 应转为 WAITING_RECRAWL / INDEXED

## 4. Search Performance Comparison

见 `reports/seo/GROWTH_VALIDATION_COMPARISON.csv`（28d）：

| 对象 | baseline imp | current imp | baseline ctr | current ctr | baseline pos | current pos | index_status | sample |
|---|---|---|---|---|---|---|---|---|
| A 144VISA | 107 | 131 | 0% | 0% | 74.05 | 46.02 | UNKNOWN* | INSUFFICIENT_SAMPLE |
| B WeChat Weak | 1 | 1 | 0% | 0% | 11.0 | 0.41 | WAITING_RECRAWL | INSUFFICIENT_SAMPLE |
| C Rail | 138 | 138 | 0% | 0% | 30.14 | 12.42 | NOT_INDEXED (旧快照) | INSUFFICIENT_SAMPLE |

\* A 为 CTR 实验，不执行 URL Inspection；index_status 不适用（观测指标为 CTR/impressions/position）。

## 5. Query Movement

见 `reports/seo/GROWTH_QUERY_MOVEMENT.md`：

- A: NEW queries = 2（`do i need transit visa in china`, `shanghai 24 hour visa free transit`）；EMERGING = 0；LOST = 0
- B: 当前 query 数据极少（28d imp=1），movement N/A
- C: 26 → 26 queries（同一 legacy URL 对比），NEW/EMERGING/LOST = 0

## 6. Internal Experiment Score

- 定义见 `scripts/growth_validation.py::impact_score`（INDEX_GAIN / POSITION_GAIN / IMPRESSION_GAIN / CTR_GAIN / QUERY_EXPANSION，满分 100）
- 本报告为观察评分，**INTERNAL EXPERIMENT SCORE**，非 Google 官方评分
- 当前所有对象 clicks < 20，不输出高置信分数，仅记录结构可用

## 7. Revenue Readiness

- 见 `reports/seo/REVENUE_MEASUREMENT_READINESS.md`
- Schema 已建立：`content_id / page / affiliate_click / affiliate_sessions / affiliate_revenue`；当前全部 **NULL**（未开始 revenue 实验，无伪造数据）
- 待 affiliate tracking 启用后可 join content_id

## 8. Low Sample Warnings

- 全站 28d clicks = 3；本报告三个对象 28d clicks 均为 0
- **LOW_SAMPLE_WARNING 生效**：任何 CTR/click/position 变化在 clicks < 20 时不得判定成功/失败
- A 的 position 变化（74→46）与 B/C 的 position 数值均视为低置信度信号，仅作观察

## 9. Next Action

- 等待期（14–28 天）内保持三页稳定：不改 title/description/canonical/URL/affiliate/UTM
- 下一轮用 `python scripts/growth_validation.py`（live）或 `--cached` 对比快照
- 若 Google 重爬完成：B/C 应从 WAITING_RECRAWL/NOT_INDEXED 转为 INDEXED，再评估请求索引或内容调整

---

## Regression

- `python -m pytest tests/ -q` → **223 passed, 0 failed, 0 skipped**
- `hugo --gc --minify` → exit 0
- `python scripts/content_id_audit.py audit --strict` → **PASS**（0 missing / 0 malformed / 0 duplicate）
- secret scan（test_no_hardcoded_secrets / test_secret_name_contract）→ 包含于 pytest，PASS
- workflow YAML validation（test_workflow_yaml）→ 包含于 pytest，PASS
- 未修改任何 content/、affiliate、UTM、canonical、URL

## 判定

**P1-GROWTH-08 = PASS（实验观察期内 → PASS / WAITING）**

- 系统与数据链路正常（GSC LIVE 可用，报告全部生成）
- 实验仍处于观察期（A 28 天、B/C 等待 Google 重爬）
- NEXT = P1-GROWTH-09（或按用户路线进入下一轮增长验证/内容动作）
