# P1-GROWTH-30 — Social Growth Control Metrics Model

- Date: 2026-08-29
- Scope: `scripts/social_content_agent.py`、`content/social/inventory.json`、
  `scripts/social_reports.py`
- Round 约束：只审计，不改变生产社媒行为。

## Canonical Fields

| 规范字段 | 当前实现 | 就绪度 |
|---|---|---|
| `social_content_id` | 资产库 `id`（`soc-000001`）；排期 CSV 已用该列名 | READY |
| `content_id` | 资产条目未持久化；排期 CSV 由 `source_article` 映射得到 | PARTIAL |
| `platform` | `platform`（ig/pinterest/x/fb） | READY |
| `post_type` | `type`（knowledge/tip/story/visual/conversion） | READY |
| `publish_time` | 资产库只有 `publish_date`（日期级）；排期有 `scheduled_at_utc/et` | PARTIAL |
| `impressions` | `metrics.impressions` | READY |
| `clicks` | `metrics.clicks` | READY |
| `website_sessions` | 未实现（计划对应 `metrics.uv`，口径不等价） | MISSING |
| `engaged_sessions` | 未实现 | MISSING |
| `affiliate_clicks` | 未实现 | MISSING |
| `revenue` | 未实现，当前全站无 revenue 数据源 | MISSING |

## 当前实现能力

- 资产库结构：`id`、`source_article`、`source_title`、`platform`、`type`、
  `caption`、`utm_params`、`status`、`publish_date`、`metrics`。
- 排期 CSV（P1-GROWTH-29 pilot）已输出
  `social_content_id/content_id/platform/content_type/scheduled_at_utc/scheduled_at_et/utm/status`。
- 回流：`backfill-metrics` 支持 `impressions/clicks/engagements/uv`。
- 日/周报：汇总 `published/impressions/clicks/uv`。

## 就绪度判定

**PARTIAL**：核心标识与曝光/点击字段已具备；网站会话、参与会话、
联盟点击和收入字段缺失。

实证：

- 资产库 100 条，已发布 9 条，仅 1 条有非零 metrics。
- `REPORTING_SNAPSHOT.json` 引用的
  `reports/social/P1_GROWTH_29_GROWTH_FUNNEL.csv` 不存在，社交增长漏斗尚未落盘。
- GA4 会话级归因尚未接入社媒资产库。

## 下轮实施契约（本轮不执行）

1. 资产条目增加 `social_content_id`（与 `id` 同值）、`content_id`（由
   `source_article` 解析并持久化）、`publish_time`（ISO datetime）。
2. `metrics` 扩展 `website_sessions`、`engaged_sessions`、`affiliate_clicks`、
   `revenue`，旧字段保留兼容。
3. 新增 `P1_GROWTH_29_GROWTH_FUNNEL.csv` 生成逻辑，统一按规范字段输出。
4. 所有社媒报表只读该规范模型，禁止在资产库外另立指标系统。
