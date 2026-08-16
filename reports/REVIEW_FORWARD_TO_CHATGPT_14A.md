【ChinaBound Travel 评测项目 · 本轮交付】P1-GROWTH-14A REVENUE FOUNDATION — PASS

GitHub main: d867881（已推送，fast-forward）
提交: feat: build affiliate funnel measurement layer
日期: 2026-08-16

一、Funnel Measurement Layer 已建立
- 新增 scripts/affiliate_funnel_audit.py（CTA Inventory Engine）
- 新增 scripts/revenue_provider.py（Revenue 抽象层，REVENUE_NOT_AVAILABLE，禁止伪造）
- 升级 scripts/revenue_experiment_review.py：新增 per1000_sessions / CTA CTR / outbound rate
- 升级 layouts/_default/single.html：GA4 事件模型完整化

二、GA4 事件模型（已上线）
- affiliate_impression：IntersectionObserver，CTA 进入视口触发，每 partner+placement 一次
- affiliate_click：保持兼容（payload 未变）
- affiliate_outbound：pagehide/visibilitychange 确认离站（3s 窗口，outbound_success）
- 事件同时推送 gtag + dataLayer，无第二套 tracking

三、CTA Inventory（全站盘点）
- 277 条 CTA / 45 页：SHORTCODE 235 / INLINE 33 / AB_CTA 7 / MID_CTA 2
- Partners: Booking 53, Klook 54, Airalo 45, Aviasales 50, SafetyWing 47, NordVPN 17, Trip.com 5, Allianz 3, World Nomads 3
- Travelpayouts Drive 全站 exactly 1 次/页

四、REV001 Measurement Upgrade
- REV001_FUNNEL_METRICS.csv：clicks 0 / sessions 162 / per1000 0.0 / CTA impressions 0 / CTA CTR 0.0 / outbound 0.0 / revenue NULL / INSUFFICIENT_SAMPLE
- 无 CTA impressions 数据，未伪造，等 GA4 采集

五、P1-GROWTH-14B（已准备，未执行）
- reports/revenue/COMMERCIAL_CONTENT_PIPELINE.md：Tier1 交通（train tickets / railway app / airport transfer）、Tier2 支付、Tier3 网络通讯；只排序不发布

六、Regression（全部 PASS）
- pytest: 379 passed, 0 failed, 0 skipped（>370 达标）
- hugo --gc --minify: PASS
- content_id_audit --strict: 57/57, 0 missing, 0 duplicates
- secret scan: 0 findings
- workflow yaml: PASS
- Drive script exactly 1（home/article/about 线上验证）

七、生产验证（线上已部署）
- 首页 HTTP 200, drive=1
- REV001 页 HTTP 200, drive=1, impression=1, outbound=1
- WeChat Weak 页 HTTP 200, drive=1, impression=1, outbound=1
- 未改：URL / canonical / content_id / affiliate URL / UTM / Drive / 文章正文

八、实验冻结（遵守）
- REV001 RUNNING / DRIVE-001 RUNNING / 144h MEASURE MORE / WeChat WAITING / Rail WAITING
- 未改 CTA 文案，未新增 affiliate，未发布文章，未判断 WIN/LOSE

请评测项目基于以上结果生成下一轮指令。
