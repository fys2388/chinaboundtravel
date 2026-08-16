# ChatGPT 指令 — P1-GROWTH-18 CHINA TRANSPORTATION CARD COMMERCIAL CONTENT CREATION

来源: ChatGPT「ChinaBound Travel评测」对话 (2026-08-16)
前轮: P1-GROWTH-17 = PASS (commit 5e2a6a7)

## 背景要点（ChatGPT 原话）
根据当前状态，P1-GROWTH-18 不应继续扩大商业实验面，重点应该进入 Transportation Commercial Cluster 的内容资产补齐 + 内链闭环 + 商业意图捕获。
- ✅ Transportation Authority Page 已完成升级（17A）
- ✅ REV002 Trip.com CTA RUNNING（冻结）
- ⏳ REV003 CTA Copy 等待 REV002 gate
- ⏳ China Transportation Card 已确定 CREATE_ONE
- ⛔ 不应同时新增 Airport Transfer（避免 cluster 稀释）
- ⛔ 不应修改 REV002 CTA
- ⛔ 不应继续扩大 affiliate CTA

## 目标
创建 China Transportation Card 独立商业信息页，补齐 Transportation Cluster 缺失节点，承接 Google 商业搜索流量，并为 REV004 后续实验准备。

## 18A Content Strategy Lock
- 新页面建议: content/posts/china-transportation-card-guide.md
- Content ID: cbt-xxxxxxxxxxxx（由系统生成）
- 不要做: "Best China Travel Card" / "Top China Transport Card Deals" / Affiliate landing page
- 定位: Editorial travel guide
- 标题建议: China Transportation Card Guide (2026): Metro Cards, Transit Apps & Payment Options for Foreign Travelers
- Alternative: How to Use Public Transportation in China: Metro Cards, Transit Apps and Payment Guide

## 18B Search Intent Coverage
- Primary: china transportation card
- Secondary: china metro card for foreigners / china subway card tourist / how to pay subway in china / china public transportation app / beijing subway card tourist / shanghai metro card foreigner

## 18C Content Structure
- H1: China Transportation Card Guide (2026)
- Introduction 禁止: I used this card / My experience / When I arrived in China / My wife told me / Living in China
- 使用: This guide explains... / ChinaBound Travel compares... / Based on official transport information...
- H2 必须:
  - ## Do Foreign Travelers Need a Transportation Card in China?
  - ## China Transportation Card Options Compared
    - ### 1. Metro IC Cards (Physical Transit Cards)
    - ### 2. Transit Apps and Digital Payments
    - ### 3. Mobile Payment Options (Alipay / WeChat Pay)
  - ## City Examples
    - ### Beijing Transportation Card
    - ### Shanghai Transportation Card
    - ### Guangzhou / Shenzhen Transportation Card
  - ## How to Buy a Transportation Card
  - ## Which Option Is Best for Tourists?
  - ## Recommended Travel Tools

## 18D Commercial Layer
- 增加 "Recommended Travel Services"，不要硬卖
- 结构: Need | Option
  - Train tickets | Trip.com
  - Attraction tickets | Klook
  - Mobile data | Airalo
  - Hotels | Booking
- 复用已有 affiliate shortcode
- 禁止: 新 affiliate partner / 新 tracking / 新 UTM

## 18E CTA Strategy
- 本轮不启动 CTA Experiment（REV002 RUNNING，only one active transportation CTA experiment）
- commercial-resource-block 可以存在
- affiliate_click experiment = disabled

## 18F Internal Linking
- 从现有页面 → 新页面，至少:
  - Transportation Guide（Transportation payment section 新增链接）
  - High Speed Rail Page（"Before taking trains, travelers may also need a local transportation card..." + 链接）
  - China Travel Resources（新增入口）
- 目标: internal_links >= 5

## 18G SEO Constraints
- 绝对禁止修改: existing URL / canonical / aliases / affiliate URLs / UTM / REV002 CTA / Drive script / GA4 schema
- 新页面 front matter 必须完整: title / description / date / slug / content_id / canonical

## 18H Persona 2.0 Compliance
- PersonaGuard；禁止: I used / I tried / my experience / my wife / living in China / 5 years / American
- 允许: Editorial review / Research-based comparison / ChinaBound Travel recommendation

## 18I Tests
- 新增 tests/test_growth18_transportation_card.py，至少 15 项:
  - Content: file exists / title exists / description exists / content_id exists / slug exists
  - SEO: canonical self / no noindex / sitemap included
  - Commercial: affiliate disclosure exists / partner URLs unchanged / no new partner
  - Persona: forbidden phrase scan
  - Regression: REV002 unchanged / Drive unchanged / GA4 unchanged

## 18J Reports（reports/revenue/ 新增）
- TRANSPORTATION_CARD_CONTENT_RELEASE.md
- TRANSPORTATION_CLUSTER_MAP.md
- COMMERCIAL_CLUSTER_PROGRESS.md

## 18K Deployment Rules
- 允许: content/ / layouts? / tests/ / reports/
- 不要修改: layouts/single.html / head.html / affiliate component / GA4 tracking

## 完成标准（P1-GROWTH-18 PASS 条件）
| 项目 | 要求 |
|---|---|
| 新页面上线 | ✅ |
| Google 可索引 | ✅ |
| Persona 2.0 | ✅ |
| Commercial intent | ✅ |
| 内链闭环 | ≥5 |
| REV002 不受影响 | ✅ |
| affiliate tracking 不变 | ✅ |
| pytest | 全部通过 |
| Hugo build | PASS |

## 下一阶段路线
P1-GROWTH-19 ↓ Transportation Cluster Authority Expansion：
- China Airport Transfer（CREATE）
- Transportation Card → CTA Experiment 候选
- REV002 数据评估准备
- Transportation Cluster SEO Authority 评估
- 当前路线正确，不建议跳到 Payment Cluster
