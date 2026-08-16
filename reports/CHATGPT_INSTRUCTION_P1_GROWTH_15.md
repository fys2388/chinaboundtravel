# ChatGPT 指令 — P1-GROWTH-15 COMMERCIAL CONVERSION OPTIMIZATION

来源: ChatGPT「ChinaBound Travel评测」对话 (2026-08-16)
前轮: P1-GROWTH-14B = PASS (commit 94a144c)

## 目标
将已有高商业意图流量页面从 Information Page 升级为 Decision Support Page。
提升 CTA Impression -> CTA Click -> Affiliate Outbound -> Revenue。
禁止: 垃圾 CTA / 改 URL / 改 canonical / 改 affiliate tracking / 大量新文章 / 影响 SEO。

## 15A Commercial Page Selection
输入: COMMERCIAL_CONTENT_PRIORITY.csv + AFFILIATE_FUNNEL_INVENTORY.csv + GSC
评分: Commercial Conversion Score 100 = Traffic Potential 25 + Commercial Intent 30 + CTA Match 25 + Current CTA Gap 15 + Risk Adjustment 5
输出: reports/revenue/COMMERCIAL_CONVERSION_TARGETS.csv + TOP_COMMERCIAL_PAGES.md
TOP3 条件: GSC impressions > 50 / page indexed / 商业意图 query (book,buy,ticket,card,SIM,VPN,insurance,hotel,transfer,app)
候选: China Transportation / WeChat Pay+Alipay / Food Delivery(REV001 保护，只分析)

## 15B CTA Gap Analysis
TOP3 生成 CTA_EXISTING / CTA_INTENT_MATCH / CTA_GAP / RECOMMENDED_ACTION
只分析，不执行。
- Transportation: train tickets -> Trip.com CTA; attraction tickets -> Klook; airport transfer -> Booking/Klook
- Payment: SIM -> Airalo; VPN -> NordVPN; travel booking -> Trip.com

## 15C First CTA Experiment REV002
只选一个页面: China Transportation Guide
CTA: Trip.com Train Ticket CTA, 位置 High Speed Rail section 之后, mid-content CTA
1 page / 1 CTA / 1 partner / 1 placement
新增: reports/revenue/REV002_EXPERIMENT_REGISTRY.csv / REV002_BASELINE.csv / REV002_EXPERIMENT_LOG.md

## 15D Measurement
复用 affiliate_impression / affiliate_click / affiliate_outbound
Primary: affiliate_click_rate; Secondary: outbound_rate, clicks_per_1000_sessions; Revenue NULL until API

## 测试
pytest 400+ passed
保持: content_id 57/57 / canonical unchanged / URL unchanged / affiliate URL unchanged / UTM unchanged / Drive exactly 1 / GA4 schema unchanged

## Git Scope Guard
允许: content/posts/ (recommended only one page) + scripts/ + tests/ + reports/
禁止: hugo.toml / layouts/ / schema / redirects / canonical / sitemap / robots (除非 blocker)

## 禁止
发布新文章 / 修改 REV001 / 修改 Drive / 修改 144h 实验 / 修改 WeChat index recovery / 批量迁移 legacy persona

## 最终报告
reports/P1_GROWTH_15_COMMERCIAL_CONVERSION.md (P1-GROWTH-15 = PASS)

## 下一阶段
P1-GROWTH-16 Commercial Content Expansion
