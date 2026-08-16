# ChatGPT 指令 — P1-GROWTH-22 PAYMENT CONTENT RELEASE

来源: ChatGPT「ChinaBound Travel评测」对话 (2026-08-16)
前轮: P1-GROWTH-21 = PASS (commit 4e9bde3)

## 评测结论
P1-GROWTH-21 = PASS ✅。Payment Cluster: Authority Layer ✅ / Index Recovery ⏳ WAITING / Commercial Strategy ✅ / Content Decision ✅ Alipay CREATE_READY。
P1-GROWTH-22 进入内容发布阶段。核心原则: Alipay 可以创建，但不要做 affiliate landing page；先建立搜索权威，再连接 eSIM / Travel Tools 商业链路。

## 总目标
China Payment Hub: Alipay for Foreigners → WeChat Pay Setup → Payment Problems → China Travel Money → eSIM/VPN/Travel Tools，完成 Payment Cluster 第一版闭环。

## 22A CREATE Alipay for Foreigners Authority Page
- content/posts/alipay-for-foreigners-guide.md（content_id 由系统生成）
- 定位: Editorial Travel Guide
- 禁止: Best Alipay Apps / Cheapest / Deals / Coupon / Affiliate page
- SEO Target: primary=alipay for foreigners china；secondary=can foreigners use alipay in china / alipay foreign card / how to pay in china as tourist / alipay china travel guide / alipay verification foreign passport

## 22B 页面结构要求
- H1 示例: Alipay for Foreigners in China: Setup Guide and Payment Tips (2026)
- H2:
  1. Can Foreigners Use Alipay in China?（foreign passport / international cards / supported payment methods）
  2. What You Need Before Setting Up Alipay（passport / phone number / international card / internet connection，连接未来 eSIM）
  3. How to Set Up Alipay Step by Step（download app / create account / verify identity / link card / activate payment）
  4. Common Alipay Problems（verification failed / foreign card declined / SMS problem / payment unavailable）
  5. Alipay vs WeChat Pay for Foreign Travelers（表格: Setup / Foreign card / Transport / Daily payment / Tourist suitability）
  6. Recommended Travel Preparation Tools（不是 CTA，只做 Before visiting China: mobile data / translation / transport / booking）
- FAQ ≥5（Can tourists use Alipay without a Chinese bank account? / Can foreigners link Visa or Mastercard? / Does Alipay work for subway payments? / Why is Alipay verification failing?）

## 22C Commercial Layer（Trust first, Monetization second）
- 允许已有 shortcode
- Airalo（位置: Before setting up payment — 手机号/SMS/网络）
- NordVPN（位置: Accessing travel services）
- SafetyWing（位置: Travel preparation）
- 禁止: Alipay 页面放 Trip.com CTA / 首屏 affiliate / Popup / 强购买语言

## 22D WeChat Pay Review（只读取状态）
- 重新检查 cbt-255af4ed003a
- Indexed + canonical=self → WECHAT_RECOVERED（允许进入 23 轮优化）
- WAITING_RECRAWL → 保持冻结
- 禁止: 修改正文 / 修改 title / Request indexing
- 输出 WECHAT_PAYMENT_STATUS.md

## 22E Payment Internal Link Graph
- 建立 PAYMENT_CLUSTER_LINK_GRAPH.md
- 新 Alipay 页面入链 ≥5: China Transportation Guide / Transportation Card / Resources / WeChat Pay / China Travel Preparation
- 新页面出链: Alipay → WeChat Pay → eSIM → Transportation（形成 topic authority）

## 22F Payment → eSIM Experiment Candidate（只分析，不启动）
- 新增 PAYMENT_ESIM_EXPERIMENT_CANDIDATE.md
- 评分 100: Traffic 25 / Payment intent 25 / eSIM relevance 25 / Current authority 15 / Risk 10
- 输出 READY / WAIT / REJECT

## 22G Regression
- 新增 tests/test_growth22_payment_release.py（至少 30 项）
- SEO: canonical / sitemap / content_id
- Cluster: internal links / no orphan
- Persona 禁止: I used Alipay / My Chinese friends showed me / Living in China
- Experiments 必须: REV001 unchanged / REV002 unchanged / DRIVE unchanged

## 本轮允许
content/posts/（新增 Alipay 页）、scripts/、tests/、reports/

## 本轮禁止
❌ 修改 WeChat Pay 正文（除非 recovered 后下一轮）❌ 修改 REV001 CTA ❌ 修改 REV002 CTA ❌ 新 affiliate partner ❌ 新 tracking ❌ 修改 GA4 schema ❌ 修改 Drive

## PASS 标准
| 项目 | 要求 |
|---|---|
| Alipay 页面上线 | ✅ |
| Indexable | ✅ |
| canonical self | ✅ |
| FAQ | ≥5 |
| Payment cluster link | ≥5 inbound |
| Commercial layer | soft only |
| WeChat review | 完成 |
| Experiment candidate | 完成 |
| pytest | >580 |
| Hugo | PASS |
| content_id | PASS |

## 下一阶段路线
P1-GROWTH-23 PAYMENT MONETIZATION EXPERIMENT:
- Alipay 页面数据观察
- WeChat recovered 后优化
- Payment → eSIM CTA 候选
- REV004 商业实验设计
- 路线: Transportation ✅ → Payment Authority → Alipay Release → Connectivity Monetization → Revenue Scale（不提前堆 CTA）
