# P1-GROWTH-11 — REVENUE OPTIMIZATION ENGINE

- Generated: 2026-08-16
- WORKDIR: `E:\AI\dulizhan\travel-blog`
- GitHub main: `f863f39` (本 commit 前)
- GSC Property: `https://www.chinaboundtravel.com/`

## 结论

**P1-GROWTH-11 = PASS**

Revenue Opportunity Engine 已建立：57 篇文章完成评分，Tier A=1 / B=4 / C=20 / D=32；报告、测试、构建全部通过。

**NEXT = P1-GROWTH-12 FIRST REVENUE EXPERIMENT**

## 1. Revenue Scoring Model

透明、可解释、确定性规则（无 LLM）。

| 维度 | 满分 | 说明 |
|---|---|---|
| Traffic Potential | 20 | 28d impressions + position（position 1-10 加分） |
| Commercial Intent | 20 | VISA/HOTEL/FLIGHT/TRAIN/INTERNET/ESIM/VPN/PAYMENT/TOUR/INSURANCE=HIGH(20)；CITY/TRANSPORT/TRAVEL GUIDE/FOOD=MEDIUM(12)；其余=LOW(5) |
| Affiliate Presence | 15 | 已有 affiliate + partner 数量 |
| Conversion Gap | 15 | 高曝光零点击 / 高意图无 affiliate / 商业化页低 CTR |
| SEO Opportunity | 10 | 复用 CONTENT_OPPORTUNITY_FEED 的 opportunity_score |
| Drive Opportunity | 10 | 高意图 + 足够流量 |
| Execution Ease | 5 | indexed + 已有 affiliate 更易执行 |
| Data Confidence | 5 | impressions/clicks 分层 × 全站 sessions<500 阻尼 0.95 |
| **Total** | **100** | Tier A=80+ / B=60-79 / C=40-59 / D<40 |

强制保护规则：
- `confidence < 50%` 或 `impressions < 20 + 0 clicks` → PRIMARY_ACTION 只能 `MEASURE_MORE` / `MONITOR`
- revenue 一律 `NULL` / `REVENUE_NOT_AVAILABLE`，绝不伪造
- 站点级小样本阻尼：全站 sessions=162 < 500，任何页面 confidence 上限 95%

## 2. Top 20 Opportunities

完整表：`reports/revenue/REVENUE_OPPORTUNITY_SCORES.csv`（57 行）与 `reports/revenue/TOP_20_REVENUE_OPPORTUNITIES.md`。

| # | content_id | 页面 | score | tier | imp | aff clicks | intent | action | conf |
|---|---|---|---|---|---|---|---|---|---|
| 1 | cbt-b4ff4381a014 | 144-Hour Visa-Free Transit Guide | 82.5 | A | 107 | 0 | VISA | CTA_OPTIMIZATION | 80.7% |
| 2 | cbt-52a577c1b2b8 | China Transportation Guide | 73.4 | B | 107 | 0 | TRAIN | CTA_OPTIMIZATION | 80.7% |
| 3 | cbt-e464169c4991 | Chinese Food Delivery: Meituan & Ele.me | 72.5 | B | 159 | 0 | FOOD | CONTENT_COMMERCIALIZATION | 80.7% |
| 4 | cbt-244822dc113b | 144-Hour Visa: 15 New Countries | 67.0 | B | 87 | 0 | VISA | CTA_OPTIMIZATION | 66.5% |
| 5 | cbt-707a8899c0a7 | How to Use WeChat Pay (2026) | 65.5 | B | 83 | 0 | PAYMENT | CTA_OPTIMIZATION | 66.5% |
| 6 | cbt-34777b6c17c1 | Zhangjiajie Avatar Mountains | 53.4 | C | 20 | 0 | TOUR | MONITOR | 66.5% |
| 7 | cbt-17c6738ffb32 | China Transportation Guide (Transport) | 50.6 | C | 107 | 0 | TRANSPORT | MONITOR | 80.7% |
| 8 | cbt-80ac63165adb | China Travel Guide: Aug 2026 | 47.5 | C | 52 | 0 | GENERAL | MONITOR | 66.5% |
| 9 | cbt-673e981fe6f2 | Is China Safe for Tourists 2026 | 47.2 | C | 3 | 0 | TOUR | MEASURE_MORE | 57.0% |
| 10 | cbt-ae69cb9f84b0 | How to Use Alipay (2026) | 47.2 | C | 1 | 0 | PAYMENT | MEASURE_MORE | 57.0% |
| 11-20 | — | 见 CSV / TOP_20 报告 | 41.5-45.8 | C | — | 0 | — | MONITOR/MEASURE_MORE | — |

## 3. Top 5 Revenue Actions

详见 `reports/revenue/TOP_5_REVENUE_ACTIONS.md`：

1. `cbt-b4ff4381a014` 144-Hour Visa — 82.5 / A — CTA_OPTIMIZATION（VISA 高意图 + 107 imp + 0 affiliate clicks）
2. `cbt-52a577c1b2b8` Transportation — 73.4 / B — CTA_OPTIMIZATION（TRAIN）
3. `cbt-e464169c4991` Food Delivery — 72.5 / B — CONTENT_COMMERCIALIZATION（FOOD，imp=159 为全站最高）
4. `cbt-244822dc113b` 144-Hour Visa: 15 Countries — 67.0 / B — CTA_OPTIMIZATION（VISA）
5. `cbt-707a8899c0a7` WeChat Pay — 65.5 / B — CTA_OPTIMIZATION（PAYMENT）

## 4. Drive Opportunities

DRIVE-001 RUNNING（观察至 2026-09-13）。详见 `reports/revenue/DRIVE_OPPORTUNITIES.md`。

最值得观察 5 页：144-Hour Visa、Transportation、144-Hour Visa(15 Countries)、WeChat Pay、Zhangjiajie — 全部 Drive ACTIVE、已有 affiliate、高商业意图。

## 5. Partner Opportunity Matrix

详见 `reports/revenue/PARTNER_OPPORTUNITY_MATRIX.csv`（9 个 partner，revenue=null，全部 LOW confidence / MEASURE_MORE）。

| partner | pages | sessions | aff clicks | impressions | comm pages | clicks/1k sessions | confidence |
|---|---|---|---|---|---|---|---|
| Klook | 38 | 162 | 0 | 828 | 22 | 0.0 | LOW |
| Aviasales | 35 | 162 | 0 | 805 | 20 | 0.0 | LOW |
| Booking | 33 | 162 | 0 | 739 | 18 | 0.0 | LOW |
| Airalo | 30 | 162 | 0 | 646 | 16 | 0.0 | LOW |
| SafetyWing | 27 | 162 | 0 | 504 | 17 | 0.0 | LOW |
| NordVPN | 14 | 162 | 0 | 150 | 5 | 0.0 | LOW |
| Trip.com / Allianz / World Nomads | ≤3 | 162 | 0 | ≤12 | ≤1 | 0.0 | LOW |

## 6. Revenue Funnel Baseline

详见 `reports/revenue/REVENUE_FUNNEL_BASELINE.md`：

| Stage | 28d 值 | 状态 |
|---|---|---|
| sessions | 162 | GA4 实测 |
| pageviews | 365 | GA4 实测 |
| affiliate_clicks | 0 | GA4 affiliate_click 实测 |
| affiliate_sessions | NOT_AVAILABLE | 无 affiliate API |
| revenue | NOT_AVAILABLE | 无 affiliate revenue API（不伪造） |

## 7. Experiment Candidates

详见 `reports/revenue/REVENUE_EXPERIMENT_CANDIDATES.md`：

- A. CTA placement test — PLANNED（等 DRIVE-001 满 28d）
- B. affiliate placement test — PLANNED（不批量加链接）
- C. commercial content update — PLANNED（仅 Top 5 单项）
- D. Drive effect — RUNNING（DRIVE-001，至 2026-09-13）
- E. partner comparison — PLANNED（需 affiliate clicks 样本）

## 8. Low Data Warning

**LOW_DATA_WARNING**：28d 全站 sessions=162 / pageviews=365 / affiliate_clicks=0 / GSC clicks=3。

- 样本极小：任何结论只能标记 INSUFFICIENT_SAMPLE，不能宣布成败
- CTR、position 波动大，不基于单个 query 做极端决策
- revenue 无真实来源，全部 `NULL` / `REVENUE_NOT_AVAILABLE`
- 本评分是 INTERNAL OPPORTUNITY RANKING，不代表收入保证
- 至少再观察一个完整 28d 周期（至 2026-09-13）后再重新评分

## 9. Tests

新增 `tests/test_revenue_opportunity_engine.py`（21 项）：
- score bounds 0-100 / tier 边界 / score 不超 100
- commercial intent tier 与分值（HIGH=20/MEDIUM=12/LOW=5）
- data confidence 分层 + 站点小样本阻尼（上限 0.95）
- conversion gap（高曝光零点击 / 高意图无 affiliate）
- small-sample guard：imp<20+0 clicks → MEASURE_MORE；imp=0 → MONITOR
- primary action 规则（AFFILIATE_PLACEMENT / CTA_OPTIMIZATION / CONTENT_COMMERCIALIZATION / INTERNAL_LINK）
- revenue 恒为 NULL、drive_active 恒为 True
- 确定性排序 + URL tie-breaker

回归结果：

| 检查 | 结果 |
|---|---|
| `python -m pytest tests/ -q` | 283 passed, 0 failed, 0 skipped |
| `hugo --gc --minify` | PASS |
| `python scripts/content_id_audit.py audit --strict` | PASS (57/57, 0 missing) |
| secret scan（pytest test_no_hardcoded_secrets / test_secret_name_contract） | PASS |
| workflow YAML validation（pytest test_workflow_yaml） | PASS |

## 10. Git

提交内容（仅本轮相关）：
- `scripts/revenue_opportunity_engine.py`
- `tests/test_revenue_opportunity_engine.py`
- `reports/revenue/REVENUE_OPPORTUNITY_SCORES.csv`、`TOP_20_REVENUE_OPPORTUNITIES.md`、`TOP_5_REVENUE_ACTIONS.md`、`DRIVE_OPPORTUNITIES.md`、`PARTNER_OPPORTUNITY_MATRIX.csv`、`REVENUE_FUNNEL_BASELINE.md`、`REVENUE_EXPERIMENT_CANDIDATES.md`
- 本报告

commit: `feat: add revenue opportunity engine` → 正常 fast-forward push。

## 边界合规

- 未修改 content/posts、layouts、Drive script、affiliate URL、UTM、canonical、robots、sitemap
- 未请求 Google Indexing API，未调用 LLM，未伪造 revenue

---
**P1-GROWTH-11 = PASS** ｜ NEXT = **P1-GROWTH-12 FIRST REVENUE EXPERIMENT**