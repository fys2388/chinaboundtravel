# ChatGPT 指令 — P1-GROWTH-19 TRANSPORTATION CLUSTER AUTHORITY EXPANSION

来源: ChatGPT「ChinaBound Travel评测」对话 (2026-08-16)
前轮: P1-GROWTH-18 = PASS (commit 7f94718)

## 评测结论
P1-GROWTH-18 = PASS ✅。17→18 已形成第一个完整闭环：
Authority Page → Persona 2.0 → Commercial Trust Layer → Supporting Content → Internal Link Cluster → Affiliate Measurement Ready

## 当前 Transportation Cluster 状态
| 页面 | 状态 | 角色 |
|---|---|---|
| China Transportation Guide | ✅ | Authority Hub |
| High-Speed Rail Guide | ✅ | Transaction Intent |
| China Transportation Card | ✅ | Supporting Commercial Guide |
| REV002 Trip.com CTA | 🟡 Running | Conversion Experiment |

## 19 目标
TRANSPORTATION CLUSTER AUTHORITY EXPANSION —— 不新增大量内容，完成 Transportation Cluster 商业闭环和权威结构。

## 19A China Airport Transfer Content Decision → CREATE
- 新页面: /posts/china-airport-transfer-guide/（content_id 系统生成）
- 禁止: Best Airport Transfer China / Cheapest Airport Transfer / Airport Transfer Deals
- 定位: Editorial transportation guide
- 覆盖查询: airport transfer china / shanghai airport transfer / beijing airport transfer / how to get from china airport to city

### 19A Content Structure
- Front matter YAML 必须完整: title/description/slug/date/content_id/canonical
- H1: China Airport Transfer Guide (2026): From Airports to City Centers
- H2 必须:
  - ## How to Get From Chinese Airports to Cities
  - ## Airport Transfer Options Compared
    - ### 1. Airport Express Trains
    - ### 2. Metro Systems
    - ### 3. Taxi and Ride-Hailing Apps
    - ### 4. Private Airport Transfers
  - ## Beijing Airport Transfer Guide
  - ## Shanghai Airport Transfer Guide
  - ## Guangzhou Airport Transfer Guide
  - ## Which Airport Transfer Option Is Best?
  - ## Recommended Travel Services
  - ## FAQ

## 19B Search Intent
- Primary: airport transfer china
- Secondary: shanghai airport transfer / beijing airport transfer / china airport taxi / china airport to city / airport express china

## 19C Commercial Layer（仅已有 Partner）
| 服务 | Partner |
|---|---|
| Airport transfer | Klook |
| Hotels | Booking |
| Train connection | Trip.com |
| eSIM | Airalo |
- 禁止: 新 affiliate partner / 新 tracking / 新 UTM

## 19D Transportation Cluster Internal Linking
- Transportation Guide → Airport Transfer（位置: Getting Around China）
- Transportation Card → Airport Transfer（位置: Before entering city transportation）
- High-Speed Rail → Airport Transfer（位置: Arrival planning）
- 目标: Inbound links >= 5

## 19E Transportation Card CTA Candidate Analysis（仅建立候选，不执行）
- 原因: REV002 = ACTIVE，不能同时修改 Transportation 商业 CTA
- 新增 reports/revenue/REV003_CANDIDATE_ANALYSIS.md
- Candidate: cbt-55aef784e6aa China Transportation Card
- 评估维度: Traffic Potential 25 / Commercial Intent 30 / Affiliate Fit 25 / Index Status 10 / Risk 10
- 输出: READY / WAIT / REJECT

## 19F REV002 Review Preparation（不评判，只准备）
- 新增 scripts/rev002_review_preparation.py
- 读取: REV002 registry / GA4 events / GSC snapshot
- 输出: REV002_REVIEW_READY.md
- Primary: affiliate_click_rate
- Secondary: affiliate_outbound_rate / clicks_per_1000_sessions / CTA impressions
- 保护: clicks < 20 → INSUFFICIENT_SAMPLE

## 19G Cluster Authority Audit
- 新增 scripts/transportation_cluster_audit.py
- 检查: Content Coverage（Train/Metro/Card/Airport/Payment/Apps）+ Internal Link Graph
- 输出: TRANSPORTATION_CLUSTER_GRAPH.md
- 指标: orphan pages / inbound links / commercial coverage

## 禁止（本轮）
REV002 CTA / Transportation Guide CTA / Drive script / GA4 tracking / Affiliate shortcode / Existing URLs / Canonical

## 测试
- 新增 tests/test_growth19_transportation_cluster.py，至少 20 项
- Airport Page: exists / indexable / canonical / content_id / sitemap
- Commercial: partner unchanged / disclosure exists / no new tracking
- Cluster: links >= 5 / no orphan
- Regression: REV002 unchanged / Drive=1 / GA4 schema unchanged

## Git Scope
- 允许: content/ scripts/ tests/ reports/
- content 最多 +1 新文章；禁止 bulk content migration

## 完成标准（P1-GROWTH-19 PASS）
| 项目 | 要求 |
|---|---|
| Airport Transfer 页面上线 | ✅ |
| Transportation Cluster 完整 | ✅ |
| 内链 >= 5 | ✅ |
| Commercial Layer | ✅ |
| REV002 Freeze | ✅ |
| REV002 Review Ready | ✅ |
| CTA 未污染 | ✅ |
| pytest | >500 目标 |
| Hugo PASS | ✅ |
| content_id audit | PASS |

## 后续路线
P1-GROWTH-20 Transportation Cluster Monetization Phase:
- REV002 数据评估（若达到 gate）
- Transportation Card CTA 实验
- Airport Transfer CTA 实验候选
- Payment Cluster 准备
- 路线: Transportation → Payment → Connectivity（保持，不建议提前切换）
