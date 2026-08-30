# P1-GROWTH-30R — Social Growth Funnel Model

- Date: 2026-08-29
- Status: MODEL READY；Social Pilot 未启动
- Files:
  - `reports/social/P1_GROWTH_30R_SOCIAL_FUNNEL_MODEL.md`
  - `reports/social/P1_GROWTH_30R_SOCIAL_FUNNEL_SCHEMA.json`

## 目标

把社媒「发布 → 网站会话 → 内容 → CTA → 联盟点击 → 收入」收敛为唯一
持久化模型，所有日报/周报/控制平面只读该模型，不另立指标系统。

## Canonical Fields

| 字段 | 类型 | 语义 | 当前来源 |
|---|---|---|---|
| `social_content_id` | string | 社媒素材唯一 ID | `content/social/inventory.json -> id` |
| `content_id` | string | 内容唯一 ID（cbt-*） | `source_article` 解析 front matter |
| `platform` | enum | ig/pinterest/x/fb | `inventory -> platform` |
| `post_type` | enum | knowledge/tip/story/visual/conversion | `inventory -> type` |
| `published_at` | datetime | 实际发布时间 | `publish_date` + 排期 UTC 时间（当前仅日期） |
| `impressions` | int | 平台曝光 | `inventory -> metrics.impressions` |
| `clicks` | int | 平台点击 | `inventory -> metrics.clicks` |
| `website_sessions` | int | 由社媒带来的网站会话 | GA4 `sessionSource/Medium = social`（未接入） |
| `engaged_sessions` | int | 参与会话 | GA4 engaged sessions（未接入） |
| `affiliate_clicks` | int | 归因到该社媒条目的联盟点击 | GA4 `affiliate_click` + UTM 归因（未接入） |
| `revenue` | number | 归因收入 | 联盟 API（未接入，保持 NULL） |
| `data_source` | enum | 本行数据来源 | SOCIAL_PLATFORM_API / GA4 / AFFILIATE_API / MANUAL / NOT_AVAILABLE |
| `snapshot_date` | date | 快照日期 | 生成当日 |

## 数据规则

1. 不编造数据：`revenue` 无有效来源时写入 `null`，状态为
   `REVENUE_NOT_AVAILABLE`。
2. `website_sessions` / `engaged_sessions` 只能来自 GA4 会话级查询，且必须能按
   `social_content_id`（UTM content）或 URL 归因；否则 `null`。
3. `affiliate_clicks` 只取 GA4 `affiliate_click` 事件中可归因到该社媒条目的
   值；无法归因则 `null`。
4. `published_at` 优先使用发布回执时间；只有日期时使用
   `T00:00:00Z` 并标记 PARTIAL。
5. 每行必须有 `social_content_id` 与 `content_id`，保证可回溯。

## 当前就绪度

| 字段 | 就绪度 |
|---|---|
| social_content_id / content_id / platform / post_type | READY（排期层） |
| published_at / impressions / clicks | PARTIAL |
| website_sessions / engaged_sessions | MISSING（GA4 未回流） |
| affiliate_clicks | MISSING |
| revenue | MISSING（无联盟 API） |

## 落地契约（本轮不启动）

1. `scripts/social_content_agent.py backfill-metrics` 扩展上述字段并写入
   `reports/social/P1_GROWTH_29_GROWTH_FUNNEL.csv`。
2. GA4 报表脚本按 `snapshot_date` 增量刷新，不覆盖旧快照。
3. 所有社媒报表改为读取该 CSV；资产库 `metrics` 保持兼容别名。
