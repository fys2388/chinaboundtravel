# P1-GROWTH-30 — Growth Control Plane

- Date: 2026-08-29
- Round: AUDIT + MODEL CONSOLIDATION
- Final status: **PARTIAL**

已完成全部 8 项审计与模型产物；验证中 3 项通过，全量 pytest 有 14 个
既有失败（与本轮改动无关），社媒增长漏斗字段为 PARTIAL，因此整体为
PARTIAL。

## 1. Canonical Content Count

**CANONICAL_CONTENT_COUNT = 58**

- `content/posts/*.md`：58
- `CONTENT_SEO_INVENTORY.csv`：60（含 2 个草稿历史变体）
- `REPORTING_SNAPSHOT.json -> published_posts`：58（正确）
- 主仪表盘旧值 60：过时，需读取快照

详情：`reports/management/P1_GROWTH_30_CONTENT_COUNT_RECONCILIATION.md`

## 2. Trust Decision Counts

| 决策 | 数量 |
|---:|---:|
| AUTO_FIX | 294 |
| SAFE_NORMALIZE | 89 |
| FACT_CHECK_REQUIRED | 479 |
| NO_CHANGE | 0 |

详情：`reports/content_audit/P1_GROWTH_30_TRUST_DECISION_MODEL.csv/.md`

## 3. Social Metrics Readiness

**PARTIAL**

- READY：`social_content_id`（资产库 `id`）、`platform`、`post_type`（`type`）、
  `publish_date`、`impressions`、`clicks`
- PARTIAL：`content_id`（仅排期层解析）、`publish_time`（仅日期）
- MISSING：`website_sessions`、`engaged_sessions`、`affiliate_clicks`、`revenue`
- 资产库 100 条，已发布 9 条，仅 1 条有非零 metrics
- `P1_GROWTH_29_GROWTH_FUNNEL.csv` 不存在，社交增长漏斗未落盘

详情：`reports/social/P1_GROWTH_30_SOCIAL_METRICS_MODEL.md`

## 4. Unified Priority TOP 10

| # | content_id | priority | action | status | 统一分 |
|---|---|---|---|---:|---:|
| 1 | cbt-b4ff4381a014 | P0 | FROZEN | FROZEN | 72.3 |
| 2 | cbt-244822dc113b | P0 | FACT_CHECK | READY | 65.3 |
| 3 | cbt-52a577c1b2b8 | P1 | FACT_CHECK | READY | 61.9 |
| 4 | cbt-707a8899c0a7 | P1 | FACT_CHECK | READY | 61.5 |
| 5 | cbt-e464169c4991 | P1 | FROZEN | FROZEN | 56.3 |
| 6 | cbt-80f6c218ad94 | P1 | FACT_CHECK | READY | 53.3 |
| 7 | cbt-de065751769e | P1 | FACT_CHECK | READY | 52.8 |
| 8 | cbt-34777b6c17c1 | P1 | FACT_CHECK | READY | 51.3 |
| 9 | cbt-9e2f5ffa1b6d | P1 | FACT_CHECK | READY | 51.0 |
| 10 | cbt-bf4ec5e57a07 | P1 | FACT_CHECK | READY | 50.3 |

全量 58 行：`reports/management/GROWTH_PRIORITY_QUEUE.csv`

## 5. Next 7-Day Queue

文件：`reports/management/NEXT_7_DAY_GROWTH_QUEUE.csv`

- P0：`cbt-244822dc113b`（FACT_CHECK）
- P1：`cbt-52a577c1b2b8`、`cbt-707a8899c0a7`、`cbt-80f6c218ad94`、
  `cbt-de065751769e`、`cbt-34777b6c17c1`、`cbt-9e2f5ffa1b6d`（FACT_CHECK）
- WATCH：`cbt-b4ff4381a014`、`cbt-e464169c4991`（FROZEN）、
  `cbt-255af4ed003a`、`cbt-cc4549872c92`（WAIT/RECRAWL）

## 6. Blockers

1. 全站无 revenue API / 转化数据：`revenue_score` 全部为 0。
2. 社媒增长漏斗未落盘：`P1_GROWTH_29_GROWTH_FUNNEL.csv` 缺失。
3. GA4 会话/参与会话未回流到社媒资产库。
4. 6 条 canonical 冲突与重定向链未关闭。
5. `GROWTH07B` / `GROWTH07C` 仍 WAITING_RECRAWL。

## 7. Validation

| 检查 | 结果 |
|---|---|
| `pytest tests/ -q` | 676 passed, 14 failed, 0 skipped（均为既有问题，非本轮改动） |
| `python scripts/content_id_audit.py audit --strict` | PASS，58/58 |
| `hugo --gc --minify` | PASS |
| 联盟专项（61 tests） | PASS |
| 工作流 + 社媒专项（39 tests） | PASS |

全量 pytest 14 个失败：

- `test_avatar_webp.py`（5）：`static/images/joran-avatar.png` 缺失且页面未引用 webp
- `test_buffer_dedup.py`（6）：Node 启动时输出 `[proxy-inject]` 污染 stdout，测试断言方式与当前环境不兼容
- `test_redirect_chains.py`（2）：`_redirects` 存在 6 条重定向链
- `test_travelpayouts_drive.py`（1）：head partial 未包含 `nowprocket`

未提交、未推送、未部署。
