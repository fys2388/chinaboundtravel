# ChatGPT 指令 — P1-GROWTH-23 PAYMENT MONETIZATION EXPERIMENT (Alipay Observation + Payment Revenue Readiness)

来源: ChatGPT「ChinaBound Travel评测」对话 (2026-08-16)
前轮: P1-GROWTH-22 = PASS (commit da5fdca)

## 评测结论
P1-GROWTH-22 = PASS ✅。Alipay 权威页上线 / 内链 6 条 / WeChat WAITING_RECRAWL / Payment→eSIM 候选 WAIT。
P1-GROWTH-23 进入 Payment Monetization Gate 阶段：不急于变现，不破坏 SEO，不提前修改 CTA。先验证 Payment Cluster 是否具备商业转化能力。

## 当前状态
- REV001 Food Delivery CTA: RUNNING
- REV002 Transportation CTA: RUNNING
- DRIVE-001: RUNNING
- Alipay 页面: NEW（需观察）
- WeChat Weak: WAITING_RECRAWL

## 23A — Alipay Page Index & SEO Observation
- 目标: cbt-0adceab18b53 | /posts/alipay-for-foreigners-guide/
- 新增 reports/payment/ALIPAY_INDEX_TRACKER.csv
- 字段: date / content_id / indexed / canonical / GSC impressions / clicks / position / affiliate_click / status
- 状态规则: 未收录 → WAITING_INDEX；已收录但 <28天 → OBSERVATION；满 28 天 → PAYMENT_MONETIZATION_READY_CHECK
- 禁止: Request indexing / 修改 title / 修改正文 / 增加 CTA

## 23B — WeChat Pay Recovery Review
- 目标: cbt-255af4ed003a
- 新增 scripts/wechat_payment_recovery_review.py → reports/payment/WECHAT_RECOVERY_STATUS.md
- 检查: canonical / robots / crawl date / index status / query movement
- 决策: Indexed=YES + canonical=self + impressions increase → RECOVERED_OBSERVATION；否则 WAITING_RECRAWL
- 禁止: 再次 Request Indexing / 改 URL / 改 canonical / 大改正文

## 23C — Payment Commercial Opportunity Engine
- 新增 scripts/payment_monetization_engine.py（确定性评分模型 100 分）
- 指标: Search Intent 30 / Commercial Fit 25 / Traffic Evidence 20 / Affiliate Relevance 15 / Risk Control 10
- 输入: CONTENT_SEO_INVENTORY.csv + AFFILIATE_FUNNEL_INVENTORY.csv
- 输出: PAYMENT_MONETIZATION_PRIORITY.csv
- 预期排序: Alipay Guide→OBSERVE / WeChat Pay→WAIT/OPTIMIZE / Transportation Card→OBSERVE / eSIM Guide→Candidate

## 23D — Payment → eSIM Commercial Experiment Design（不执行 CTA，只设计）
- 输出 reports/revenue/REV004_PAYMENT_ESIM_CANDIDATE.md
- Candidate A: Alipay Guide（Payment Problem → Need Mobile Number → Need Data → Airalo）状态 WAITING_DATA
- Candidate B: WeChat Pay（Payment Setup → Google Services → VPN/eSIM）状态 WAITING_INDEX

## 23E — GA4 Payment Funnel Audit
- 复用已有: affiliate_impression / affiliate_click / affiliate_outbound（禁止新增 event）
- 新增 scripts/payment_funnel_audit.py → PAYMENT_FUNNEL_BASELINE.csv
- 字段: page / CTA_count / partner / impressions / clicks / outbound / CTR / outbound_rate / status
- 低样本保护: clicks < 20 → INSUFFICIENT_SAMPLE

## 23F — Commercial Content Protection
- 新增 tests/test_growth23_payment_monetization.py
- 验证: SEO（canonical/slug/content_id/title unchanged）、Affiliate（no new partner / no new UTM / no tracking duplication）、Experiment（REV001/REV002/DRIVE unchanged）

## 23G — Regression
- pytest tests/ -q → 0 failed 0 skipped
- hugo --gc --minify → PASS
- content_id_audit --strict → ALL PASS

## 本轮禁止
❌ 不新增 Payment CTA ❌ 不给 Alipay 加 Airalo CTA ❌ 不修改 WeChat 正文 ❌ 不创建 Payment Hub 新页面 ❌ 不申请 Google indexing ❌ 不调整 affiliate shortcode ❌ 不改变 Drive

## Git / Release
- 允许 scripts/ tests/ reports/ 变化
- 只涉及 scripts/tests/reports → 无需 Cloudflare 发布
- 修改 content/posts/ layouts/ → 必须部署验证

## 最终产出（必须生成 reports/payment/）
- ALIPAY_INDEX_TRACKER.csv
- WECHAT_RECOVERY_STATUS.md
- PAYMENT_MONETIZATION_PRIORITY.csv
- PAYMENT_FUNNEL_BASELINE.csv
- REV004_PAYMENT_ESIM_CANDIDATE.md
- PAYMENT_CLUSTER_MONETIZATION_REPORT.md

## PASS 条件
1. Payment Cluster 商业评分系统建立
2. Alipay 进入观察
3. WeChat 状态明确
4. REV004 候选锁定但未执行
5. 无 SEO / Affiliate 回归
6. 全量测试通过

## 下一阶段
P1-GROWTH-24 = PAYMENT MONETIZATION RELEASE（仅当 Alipay/WeChat 数据满足 gate）
优先：先让 Payment Cluster 获得 Google 信任，再做商业转化。
