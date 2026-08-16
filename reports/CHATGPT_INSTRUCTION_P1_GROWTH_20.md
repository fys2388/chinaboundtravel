# ChatGPT 指令 — P1-GROWTH-20 TRANSPORTATION CLUSTER MONETIZATION PHASE

来源: ChatGPT「ChinaBound Travel评测」对话 (2026-08-16)
前轮: P1-GROWTH-19 = PASS (commit 34b1d54)

## 评测结论
P1-GROWTH-19 = PASS ✅。Transportation Cluster 从 Content Coverage 进入 Commercial Monetization Optimization 阶段。
P1-GROWTH-20 不应继续扩张内容，应验证：已有商业流量资产 → 是否能产生有效 affiliate funnel。

## 目标
建立 Transportation Cluster 第一个商业转化闭环。
范围: Transportation Guide → High Speed Rail → Transportation Card → Airport Transfer → REV002 Trip.com CTA

## 20A REV002 COMMERCIAL EXPERIMENT REVIEW
前置条件: date >= 2026-09-13
- 如果未达到 → 状态 WAITING_REVIEW_GATE，禁止判断
- 如果达到 → 读取 REV002_EXPERIMENT_REGISTRY.csv + GA4(affiliate_impression/affiliate_click/affiliate_outbound) + GSC(clicks/impressions/position)
- 禁止: 只看 CTR / 只看 1-7 天 / 只看 impressions
- Sample Guard: affiliate_clicks < 20 → INSUFFICIENT_SAMPLE（不允许 WIN/LOSE）
- Positive Gate（同时满足）: clicks >= 20 AND affiliate_click_rate improvement >= 20% AND outbound_rate not worse than baseline -10% → PROMISING；否则 NEUTRAL
- 输出: reports/revenue/REV002_FINAL_REVIEW.md

## 20B TRANSPORTATION CARD CTA EXPERIMENT PREPARATION（只准备，不一定上线）
- Candidate: cbt-55aef784e6aa China Transportation Card（当前 score 61 WAIT，重新评估）
- 新增: scripts/transportation_card_conversion_analysis.py
- 评分 100: GSC Demand 25 / Commercial Intent 30 / Affiliate Fit 25 / Index Status 10 / Risk 10
- 输出: TRANSPORTATION_CARD_CTA_READINESS.md → 三选一: READY_FOR_EXPERIMENT / WAIT_FOR_DATA / REJECT
- 如果 READY: 只能 1 page / 1 CTA / 1 partner / 1 placement
- 禁止同时修改: Transportation Guide / REV002 / Airport
- 候选 Partner 优先: Trip.com（Card 用户后续需求 city movement + train booking 匹配最高）

## 20C Airport Transfer Commercial Candidate（只分析）
- 目标: cbt-02a3e0d6ed4f
- 输出: AIRPORT_TRANSFER_MONETIZATION_ANALYSIS.md
- 维度: Search intent 30 / Booking intent 25 / CTA fit 25 / Authority 10 / Risk 10
- 禁止本轮新增 CTA（避免 REV002 + Airport CTA + Card CTA 三个变量同时变化）

## 20D Transportation Cluster Revenue Map
- 新增: scripts/transportation_revenue_map.py → TRANSPORTATION_REVENUE_FUNNEL.md
- 结构: Traffic Entry → Informational Page → Commercial Intent → Affiliate CTA → Outbound → Revenue
- 页面分类: Discovery (Transportation Guide) / Transaction (High Speed Rail, Airport Transfer) / Utility (Transportation Card)

## 20E Payment Cluster Preparation（只 research，不创建）
- 已有: WeChat Pay / Alipay
- 覆盖关键词: alipay for foreigners / wechat pay foreign card / china mobile payment / china payment problems
- 输出: PAYMENT_CLUSTER_READINESS.md → READY / WAIT / BLOCKED

## 20F Regression Protection
- 新增: tests/test_growth20_monetization.py（至少 25 项）
- REV002: CTA unchanged / partner unchanged / tracking unchanged
- Transportation Cluster: pages >= 4 / no orphan
- Affiliate: shortcode unchanged / Drive=1
- SEO: canonical unchanged / sitemap

## 禁止（严格）
- content/posts/china-transportation-complete-guide* 中 REV002 CTA
- layouts/ / head.html / GA4 event schema / affiliate shortcode / Drive script

## Git Scope
- 允许: scripts/ tests/ reports/
- content/ 仅限: 20B 最终 READY 才允许增加 CTA（1 page）

## PASS 标准
| 项目 | 要求 |
|---|---|
| REV002 Review Framework | 完成 |
| Card CTA readiness | 完成 |
| Airport monetization analysis | 完成 |
| Revenue Map | 完成 |
| Payment Cluster Research | 完成 |
| 实验隔离 | PASS |
| pytest | >520 |
| Hugo | PASS |
| content_id audit | PASS |

## 后续路线
P1-GROWTH-21 PAYMENT CLUSTER AUTHORITY BUILD:
- Alipay for Foreigners 页面评估
- WeChat Pay Index Recovery 复查
- Payment → eSIM → Travel Services 商业链路
- 战略: Transportation ✅ → Payment → Connectivity（保持，不建议同时启动 Payment 新内容）
