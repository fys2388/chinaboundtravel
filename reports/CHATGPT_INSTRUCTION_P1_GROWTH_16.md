# ChatGPT 指令 — P1-GROWTH-16 COMMERCIAL CONTENT EXPANSION

来源: ChatGPT「ChinaBound Travel评测」对话 (2026-08-16)
前轮: P1-GROWTH-15 = PASS (commit 7f578a4)

## 目标
从单页面 CTA 实验升级到商业内容资产扩展。原则: 不是大量写文章。
模式: 1 个商业主题 + 1 个核心页面 + 1 个辅助内容 + 1 个 CTA 实验 + 28 天测量。

## 16A Commercial Cluster Expansion
- 新增 scripts/commercial_cluster_expansion.py (deterministic / no LLM / no external API)
- 评分 100: Search Demand 30 + Commercial Intent 30 + Existing Authority 20 + Affiliate Fit 15 + Content Gap 5
- 输出: reports/revenue/COMMERCIAL_CLUSTER_PRIORITY.csv + COMMERCIAL_EXPANSION_ROADMAP.md
- 选择 Cluster A China Transportation (最高优先级; 已有 Trip.com/Klook/Booking + GSC impressions)
- Cluster B Payment 暂缓 (WeChat index 未稳定); Cluster C Connectivity 等 REV001

## 16B First Supporting Content Decision
- 不是写文章; 先判断已有内容是否足够
- 输出: CONTENT_EXPANSION_DECISION.md
- 每个候选: Topic / Search Intent / Existing URL / Action (KEEP/UPDATE/CREATE/IGNORE)
- 候选: 1) China Railway 12306 App Guide (china railway app / 12306 foreigner; Trip.com)
        2) China Transportation Card (china transport card / metro card china tourist; Klook)
        3) China Airport Transfer (airport transfer china / shanghai airport transfer; Booking/Klook)

## 16C REV002 Protection
- REV002 RUNNING; 禁止修改 CTA / placement / partner / 文案; 观察至 >=2026-09-13

## 16D Legacy Persona Cleanup Alignment
- 只分析，禁止修改; 输出 LEGACY_COMMERCIAL_RISK_REPORT.md
- 找 High commercial value + Legacy persona risk 并存页面 (144h Visa / Transportation / Food Delivery / WeChat Pay)

## 回归要求
pytest > 430; content_id 57/57; canonical unchanged; affiliate URL unchanged; UTM unchanged; Drive exactly 1; GA4 schema unchanged

## Git Scope
允许 scripts/ tests/ reports/; content/ 只允许单个明确实验内容; 禁止批量文章修改 / 批量 persona migration

## 禁止
大量 SEO 内容 / 扩充 affiliate / 修改 REV001 / 修改 REV002 / 碰 Drive / 调整 GA4 / 修改 canonical

## 最终报告
reports/P1_GROWTH_16_COMMERCIAL_CONTENT_EXPANSION.md (P1-GROWTH-16 = PASS)

## 后续
P1-GROWTH-17 FIRST COMMERCIAL CONTENT RELEASE (届时才 Create/Update -> CTA -> Experiment -> Measure)
