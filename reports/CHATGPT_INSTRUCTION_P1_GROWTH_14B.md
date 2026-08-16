# ChatGPT 指令 — P1-GROWTH-14B COMMERCIAL CONTENT PIPELINE

来源: ChatGPT「ChinaBound Travel评测」对话 (2026-08-16)
前轮: P1-GROWTH-14A = PASS (commit d867881)

## 项目判断
商业化基础设施已达到 Revenue Experiment Ready。下一阶段从「测量收入」进入「提高商业转化概率」。

## 执行范围
1. Commercial Content Opportunity Engine
   - 新增 scripts/commercial_content_engine.py（确定性模型，禁止 LLM/主观评分/假数据）
   - 评分模型 100 分: Commercial Intent 30 / Search Demand 25 / Affiliate Fit 20 / Existing Authority 15 / Content Gap 10
   - 输入: reports/seo/ reports/revenue/ GSC baseline affiliate inventory content inventory
   - 输出: reports/revenue/COMMERCIAL_CONTENT_PRIORITY.csv
   - 字段: keyword_cluster, target_url, intent, affiliate_match, score, priority, action

2. Commercial Topic Clusters
   - 输出: reports/revenue/COMMERCIAL_TOPIC_CLUSTERS.md
   - Cluster A China Transportation ★★★★★ (train tickets / railway app / high speed rail booking / airport transfer / transportation card) Affiliate: Trip.com, Booking, Klook
   - Cluster B China Payment ★★★★★ (Alipay for foreigners / WeChat Pay foreign card / China mobile payment / payment problems) Affiliate: eSIM, VPN, Travel services
   - Cluster C China Connectivity ★★★★ (China eSIM / China VPN / China mobile data / Google services China) Affiliate: Airalo, NordVPN

3. Revenue Content Gap Analysis
   - 输出: reports/revenue/CONTENT_REVENUE_GAPS.md
   - 分析已有 57 posts / 277 CTA / 0 revenue: 哪些页面有流量+商业意图但 CTA 不匹配
   - 例: Food Delivery 当前 Airalo CTA，可能扩展 Trip.com/Klook/eSIM/Payment——只分析，不修改 CTA

4. REV001 / DRIVE-001 状态保护
   - REV001 RUNNING (观察至 2026-09-13) / DRIVE-001 RUNNING
   - 禁止: 修改 CTA / 删除 CTA / 增加 affiliate / 改 UTM

## 测试要求
pytest > 390 passed
必须保持: content_id 57/57 / canonical unchanged / affiliate URL unchanged / Drive exactly 1 / GA4 event schema unchanged

## Git / Deploy
仅 scripts/tests/reports 变化 -> 不需要生产部署
若改 layouts/static/ -> 需要 Hugo build + Cloudflare deploy + smoke test

## 最终报告
reports/P1_GROWTH_14B_COMMERCIAL_PIPELINE.md
包含: Commercial scoring model / Topic clusters / Revenue gaps / Priority queue / No execution changes

## 运行
pytest / hugo --gc --minify / content_id audit / secret scan / workflow validation

## 下一阶段
P1-GROWTH-15 FIRST COMMERCIAL CONTENT EXPANSION:
1 个高价值商业页面 + 1 个 CTA 实验 + 28 天测量（非批量写文章）
