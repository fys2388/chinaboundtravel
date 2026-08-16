# REVENUE EXPERIMENT DASHBOARD

- Generated: 2026-08-16
- DATA_SOURCE: CACHED（registry / baseline / 持久化快照；live 数据未到达观察窗口）
- Revenue API: REVENUE_NOT_AVAILABLE（无 affiliate revenue API，禁止伪造）

## Status Groups

### RUNNING
| Experiment | Page | Start | Days | Baseline per1000 | Current per1000 | Delta | Status |
|---|---|---|---|---|---|---|---|
| REV001 | Food Delivery (cbt-e464169c4991) | 2026-08-16 | 0 | 0.0 | 0.0 | 0.0 | INSUFFICIENT_SAMPLE |
| DRIVE-001 | Site-wide Drive | 2026-08-16 | 0 | 0.0 | 0.0 | 0.0 | INSUFFICIENT_SAMPLE |

### INSUFFICIENT_SAMPLE（全部）
| Experiment | clicks | days | reason |
|---|---|---|---|
| REV001 | 0 | 0 | 观察 <28d 且 clicks <20 |
| DRIVE-001 | 0 | 0 | 观察 <28d 且 clicks <20 |
| GROWTH05-CTR-001 (144h) | 0 | 0 | clicks <20 |
| GROWTH07C-INDEX-001 (WeChat Weak) | 0 | - | 等待 recrawl（Alternate） |
| GROWTH07B-TECH-001 (Rail) | 0 | - | 等待 recrawl（noindex 旧 crawl） |

### EARLY_SIGNAL / VALIDATED / NEGATIVE
- 无（样本不足，禁止判定）

## Metrics（当前已知）

| Experiment | affiliate_clicks | clicks_per_1000 | sessions | pageviews | revenue | revenue_status |
|---|---|---|---|---|---|---|
| REV001 | 0 | 0.0 | 162* | 365* | NULL | REVENUE_NOT_AVAILABLE |
| DRIVE-001 | 0 | 0.0 | 162* | 365* | NULL | REVENUE_NOT_AVAILABLE |

* sitewide 28d（页面级 GA4 不可得，DATA_SCOPE=sitewide）

## Sample Warnings
- 全站 28d GSC clicks=3；REV001 页面 clicks=0
- 所有实验观察 <28 天；affiliate_clicks <20 → 一律 INSUFFICIENT_SAMPLE
- 不得基于 0-7 天数据宣布 WIN/LOSE
