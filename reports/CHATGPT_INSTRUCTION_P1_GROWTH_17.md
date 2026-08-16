# ChatGPT 指令 — P1-GROWTH-17 TRANSPORTATION COMMERCIAL CONTENT RELEASE

来源: ChatGPT「ChinaBound Travel评测」对话 (2026-08-16)
前轮: P1-GROWTH-16 = PASS (commit 8234954)

## 目标
完成第一个商业 Cluster 优化闭环 (Transportation)。

## 17A Transportation Authority Page Upgrade
- 目标页面: China Transportation Guide (cbt-52a577c1b2b8; 注: 实际 front matter content_id=cbt-17c6738ffb32)
- 修改范围: 仅该页面 (content/posts/transportation guide)
- 1. Persona Migration (Brand 2.0): 删除 I lived in China / My wife / American expat / Personally tested / My experience
  替换: Editorial research / Official sources / Transport operators / Traveler-focused analysis
- 2. 保留 SEO 资产: title/slug/URL/canonical/content_id/front matter date/aliases/affiliate URL/UTM 全部不变
- 3. Commercial Trust Layer: 新增 "Recommended Booking Options"
  - Option A Trip.com (English interface / international payment / train tickets)
  - Option B 12306 (official booking)
  - Option C Klook (travel packages)
  - 定位 comparison layer, 非硬广告

## 17B Transportation CTA Optimization
- 已有 Trip.com inline CTA; 不要新增多个 CTA
- 实验 REV003: REV003_TRANSPORTATION_CTA; 变量仅 CTA 文案
- 保持 partner=Trip.com, placement=existing, tracking=existing
- Variant A: "Book China Train Tickets Online" / Variant B: "Compare China Train Tickets & Routes"
- 如果系统不支持 A/B: 只做单版本升级
- 注意: REV002 正在运行 (freeze), REV003 不得修改 REV002 的 mid-cta 文案 -> REV003 注册为 PENDING 等待 REV002 评审

## 17C Create New Commercial Content Decision
- 分析: Transportation Card (Klook) / Airport Transfer (Booking/Klook)
- 新增 scripts/commercial_content_release.py -> 输出 COMMERCIAL_RELEASE_DECISION.md
- 结果: CREATE ONE, 另一个 HOLD

## 17D REV001 / REV002 / DRIVE-001 Freeze
- 继续 RUNNING; 禁止修改/停止/重置 baseline

## 测试要求
pytest > 450; content_id 57/57; canonical unchanged; affiliate regression PASS; Drive exactly 1; GA4 schema unchanged

## Git Scope
允许 content/ scripts/ tests/ reports/; content 只允许 1 page migration; 禁止 bulk persona migration

## 输出报告
reports/P1_GROWTH_17_TRANSPORTATION_COMMERCIAL_RELEASE.md (P1-GROWTH-17 = PASS)

## 后续
P1-GROWTH-18 Commercial Content Creation + New Page Launch + CTA Experiment
优先级: 1. Transportation Guide 商业化升级 / 2. Transportation Card / 3. Airport Transfer / 4. Payment 等 Index Recovery / 5. Connectivity 等 REV001
