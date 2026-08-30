# NEXT REVENUE ACTIONS（观察决策，不自动执行）

- Generated: 2026-08-16

| Experiment | Recommended Action | Rationale | Earliest Review |
|---|---|---|---|
| REV001 (Food Delivery CTA) | KEEP_RUNNING / DO_NOT_CHANGE | 观察 0 天，affiliate_clicks=0；28 天内禁止调整 CTA | 2026-09-13 |
| DRIVE-001 | KEEP_RUNNING / DO_NOT_CHANGE | 观察 0 天；Drive 配置保持稳定 | 2026-09-13 |
| GROWTH05-CTR-001 (144h) | MEASURE_MORE | clicks=0；position 已从 74→46 改善但无点击样本 | 2026-09-13 |
| GROWTH07C-INDEX-001 (WeChat Weak) | KEEP_RUNNING（等待 recrawl） | 差异化已上线，等待 Google recrawl；不再次请求 indexing | 下次 URL Inspection |
| GROWTH07B-TECH-001 (Rail) | KEEP_RUNNING（等待 recrawl） | 技术修复已上线，等待 recrawl 清除 noindex 旧 crawl | 下次 URL Inspection |

## 规则
- SAMPLE SUFFICIENT = observation >= 28d AND clicks >= 20
- 未达阈值 → 一律 MEASURE_MORE / KEEP_RUNNING
- 达阈值后：POSITIVE → SCALE_WINNER；NEUTRAL → KEEP_RUNNING；NEGATIVE → END_EXPERIMENT / RETEST
- 本轮不执行任何动作；下一次自动测量在 2026-09-13（REV001/DRIVE-001 满 28 天）

## Revenue API
- REVENUE_NOT_AVAILABLE：继续允许 revenue=NULL，禁止伪造订单/佣金
