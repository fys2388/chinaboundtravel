# ChatGPT 指令 — P1-GROWTH-21 PAYMENT CLUSTER AUTHORITY BUILD

来源: ChatGPT「ChinaBound Travel评测」对话 (2026-08-16)
前轮: P1-GROWTH-20 = PASS (commit 75f92fc)

## 评测结论
P1-GROWTH-20 = PASS ✅。Transportation Cluster: Authority ✅ / Commercial Framework ✅ / Revenue Validation ⏳。
进入 Payment Cluster Authority Build。注意：Payment 当前不能直接商业化（WeChat Weak WAITING_RECRAWL / REV001-REV002-DRIVE001 同时运行 / revenue sample 极低 / 支付是高信任主题）。
目标：建立 Payment Cluster 内容权威 + 商业路径设计，不是立即卖 affiliate。

## 总目标
China Payment Cluster: Alipay for Foreigners → WeChat Pay for Foreigners → Payment Problems → eSIM/Banking/Travel Tools（未来商业漏斗）

## 21A Payment Existing Asset Audit
- 新增 scripts/payment_cluster_audit.py
- 扫描 content/posts/*，识别关键词: wechat pay / wechat wallet / alipay / mobile payment / cashless china / foreign card / visa mastercard / payment problem
- 输出 reports/revenue/PAYMENT_CLUSTER_INVENTORY.csv
- 字段: content_id / URL / title / payment topic / GSC impressions / index status / persona status / affiliate status / commercial score

## 21B WeChat Pay Index Recovery Review
- 重新检查 cbt-255af4ed003a（How to Set Up & Use WeChat Pay Step by Step）
- 读取 GSC: coverageState / lastCrawlTime / canonical
- 分类: Indexed + canonical=self → RECOVERED；Alternate page with proper canonical → WAITING_RECRAWL；Excluded → TECHNICAL_REVIEW_REQUIRED
- 禁止: 再次 Request Indexing / 修改正文 / 修改 canonical
- 输出 WECHAT_INDEX_RECOVERY_REVIEW.md

## 21C Alipay for Foreigners Opportunity Analysis（不创建页面，只评估）
- 新增 scripts/payment_content_opportunity.py
- 评分 100: Search Demand 30 / Commercial Intent 25 / Existing Authority 20 / Content Gap 15 / Risk 10
- 输出 ALIPAY_CONTENT_DECISION.md → CREATE_READY / HOLD / REJECT

## 21D Payment Commercial Funnel Design
- 建立 PAYMENT_COMMERCIAL_FUNNEL.md
- 用户路径: Discovery（can foreigners use alipay china / wechat pay foreign card）→ Trust Content（Alipay Guide / WeChat Pay Guide）→ Supporting Need（eSIM / VPN / Travel Insurance / Booking）→ Monetization（Affiliate: 优先 Airalo / NordVPN / SafetyWing / Booking）
- 禁止: 支付页面直接硬推

## 21E Payment → Connectivity Link Analysis
- 新增 PAYMENT_CONNECTIVITY_MAP.md
- 分析: WeChat Pay→Airalo / Alipay→Airalo / Google services→NordVPN / Travel preparation→SafetyWing
- 本轮不修改链接

## 21F Payment Cluster SEO Architecture
- 输出 PAYMENT_CLUSTER_ARCHITECTURE.md
- 目标结构: Payment Hub → Alipay for Foreigners / WeChat Pay Setup / Payment Troubleshooting / China Travel Money Guide
- 判断: CREATE_ONE 或 OPTIMIZE_EXISTING

## 21G Regression Protection
- 新增 tests/test_growth21_payment_cluster.py（至少 25 项）
- SEO: canonical unchanged / content_id unchanged
- Experiments: REV001 unchanged / REV002 unchanged / Drive unchanged
- Persona 禁止: I used WeChat Pay / My Chinese wife showed me / Living in China
- Affiliate: 禁止新增 partner

## 本轮允许
scripts/ tests/ reports/；content/ 仅限未来 CREATE_READY

## 本轮禁止
❌ 新建 Alipay 页面 ❌ 新增 CTA ❌ 修改 WeChat 页面正文 ❌ 修改 REV001 ❌ 修改 REV002 ❌ 修改 Drive ❌ 修改 GA4 schema

## PASS 标准
| 项目 | 要求 |
|---|---|
| Payment inventory | 完成 |
| WeChat recovery review | 完成 |
| Alipay decision | 完成 |
| Payment funnel | 完成 |
| Connectivity map | 完成 |
| Architecture | 完成 |
| pytest | >550 |
| Hugo | PASS |
| content_id audit | PASS |

## 后续路线
P1-GROWTH-22 PAYMENT CONTENT RELEASE:
- Alipay 页面创建（如果 CREATE_READY）
- WeChat 优化（如果 recovered）
- Payment Cluster 内链闭环
- Payment → eSIM 商业实验候选
- 战略: Transportation ✅ → Payment (Authority Build) → Connectivity → Revenue Scale（不要提前商业化 Payment）
