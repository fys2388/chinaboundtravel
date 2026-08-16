# ChatGPT 指令 — P1-GROWTH-14A REVENUE FOUNDATION

来源: ChatGPT「ChinaBound Travel评测」对话 (2026-08-16)
前轮: P1-GROWTH-13 = PASS/WAITING (commit 40049ed)

## 项目判断
当前 SEO、品牌、内容、Affiliate 基础设施已经完成，进入 Revenue Infrastructure → Commercial Optimization 阶段。
P1-GROWTH-13 最大价值是确认实验框架可运行、样本保护机制有效、不会错误宣布增长成功、Revenue 数据链路仍缺失。

NEXT = P1-GROWTH-14 REVENUE FOUNDATION

## 总目标
建立完整商业漏斗: Traffic → Page View → CTA Impression → Affiliate Click → Partner Conversion → Commission Revenue
当前状态: Traffic ✅ / SEO ✅ / Affiliate URL ✅ / CTA 🟡 / Click Tracking 🟡 / Revenue API ❌

## P1-GROWTH-14A Affiliate Funnel Measurement Layer
目标: 升级现有 affiliate_click 为完整事件体系。
新增: affiliate_impression / affiliate_click / affiliate_outbound

Scope 允许: layouts/ static/ scripts/ tests/ reports/
禁止: content/posts/ URL / slug / canonical / affiliate ID / UTM

### 1. CTA Inventory Engine
新增 scripts/affiliate_funnel_audit.py
扫描全站: Booking / Klook / Airalo / Travelpayouts / SafetyWing / NordVPN
输出 reports/revenue/AFFILIATE_FUNNEL_INVENTORY.csv
字段: content_id, url, partner, cta_type, placement, tracking_event, utm_source, utm_campaign

### 2. GA4 Event Upgrade
统一事件模型:
- affiliate_impression: 用户看到 CTA。{event, partner, content_id, placement}
- affiliate_click: 保持兼容 {event, partner, content_id, placement}
- affiliate_outbound: 用于判断点击是否成功离站。

### 3. Revenue Provider Abstraction
新增 scripts/revenue_provider.py
class RevenueProvider: def get_revenue(): return None
当前 status: REVENUE_NOT_AVAILABLE
未来接: Travelpayouts API / Booking affiliate / Klook reports / Airalo dashboard
禁止: 模拟收入 / 假订单 / 推算佣金

### 4. REV001 Measurement Upgrade
REV001 Food Delivery CTA 升级后增加: CTA impressions / CTA CTR / Outbound rate
Primary: affiliate_clicks_per_1000_sessions
Secondary: CTA CTR

## 测试要求
完成后 pytest > 370 passed
必须保持: content_id 57/57, canonical unchanged, URL unchanged, affiliate unchanged, Drive exactly 1

## 输出报告
reports/P1_GROWTH_14A_REVENUE_FOUNDATION.md
包含: Funnel architecture / CTA inventory / Event specification / Revenue readiness / Regression result

## P1-GROWTH-14B（同时准备，不执行）
建立商业内容优先级: reports/revenue/COMMERCIAL_CONTENT_PIPELINE.md（只排序，不发布）
- Tier 1 中国交通: China train tickets / China railway app / Airport transfer
- 中国支付: Alipay vs WeChat Pay / Foreign cards in China / Payment troubleshooting
- 网络通讯: China eSIM / VPN China / Mobile data

## 当前实验冻结规则（直到 2026-09-13）
REV001 CTA = RUNNING / DRIVE-001 = RUNNING / 144h Meta = MEASURE MORE / WeChat Index = WAITING / High Speed Rail = WAITING
禁止: 改 CTA 文案 / 新增 affiliate / 大量发文章 / 判断 WIN/LOSE / 删除实验

## 执行指令
Execute P1-GROWTH-14A REVENUE FOUNDATION.
Objectives: Build affiliate funnel measurement layer / Create CTA inventory audit / Add affiliate impression/click/outbound event specification / Create revenue provider abstraction / Upgrade REV001 measurement readiness
Constraints: deterministic only / no LLM / no fake revenue / no content changes / no URL/canonical changes / no affiliate ID changes / preserve SEO invariants
Run: pytest / hugo --gc --minify / content_id_audit / secret scan / workflow validation
Generate: reports/P1_GROWTH_14A_REVENUE_FOUNDATION.md
Do not deploy unless production code changes are required.
