# P1-GROWTH-30R — Growth Control Plane Closure

- Date: 2026-08-29
- Final status: **PASS**
- 未提交、未推送、未部署，未启动 Social Pilot。

## Task A — 14 个测试失败已修复

| 原因 | 数量 | 修复 |
|---|---:|---|
| avatar PNG 缺失 | 5 | 恢复 `static/images/joran-avatar.png`，sidebar/about/schema 回退引用改为 `joran-avatar.png`，WebP 仍优先 |
| `[proxy-inject]` stdout 污染 | 6 | `test_buffer_dedup.py` 子进程剥离 `NODE_OPTIONS`，隔离全局代理 preload |
| redirect chain | 2 | `static/_redirects` 6 条链全部改为直达最终 301 目标 |
| Drive nowprocket 缺失 | 1 | `head.html` Drive 外层 script 增加 `nowprocket`、`data-cfasync`、`data-no-defer` |

结果：`pytest tests/ -q` = **690 passed / 0 failed / 0 skipped**。

## Task B — Social Growth Funnel

已创建规范模型：

- `reports/social/P1_GROWTH_30R_SOCIAL_FUNNEL_MODEL.md`
- `reports/social/P1_GROWTH_30R_SOCIAL_FUNNEL_SCHEMA.json`

模型字段：
`social_content_id / content_id / platform / post_type / published_at /
impressions / clicks / website_sessions / engaged_sessions /
affiliate_clicks / revenue / data_source / snapshot_date`

规则：不编造数据；revenue 无来源时保持 NULL /
`REVENUE_NOT_AVAILABLE`；网站会话/参与会话仅接受 GA4 归因；联盟点击仅接受
可归因事件。Social Pilot 未启动。

就绪度：模型 READY；数据管道 PARTIAL（GA4 会话归因与联盟 API 未接入）。

## Task C — Fact Check Governance

已创建：

- `reports/content_audit/P1_GROWTH_30R_FACT_CHECK_POLICY.md`
- `reports/content_audit/P1_GROWTH_30R_FACT_CHECK_QUEUE.csv`（479 行）

类别计数：

| 类别 | 数量 |
|---|---:|
| prices / fees | 160 |
| visa / immigration | 119 |
| opening hours | 50 |
| law / regulation | 43 |
| distances / durations | 37 |
| transportation | 26 |
| unclassified | 44 |

策略：已有验证来源标记 `VERIFIED` 并允许受控修正；无来源时标记
`NO_VERIFIED_SOURCE`，只允许保守移除无支持主张，禁止编造事实。本轮未修改
任何文章。

## Validation

| 检查 | 结果 |
|---|---|
| `pytest tests/ -q` | 690 passed / 0 failed / 0 skipped |
| `content_id_audit --strict` | PASS 58/58 |
| `hugo --gc --minify` | PASS |
| internal link audit | PASS：572 内链，0 broken / 0 redirect / 0 malformed |
| meta audit | PASS（6 条 description >155 为 advisory，非阻断） |
| brand audit | PASS：58 篇，0 legacy hits |
| affiliate tests | PASS：71 passed |
| affiliate config check | PASS（外部 URL 检查：Airalo TIMEOUT、Klook 403，均为第三方网络状态，非回归） |
| workflow validation | PASS：11 passed |
| redirect chain audit | PASS：chains 0 / loops 0 |
| schema JSON | PASS：可解析 |

## Remaining Blockers

1. 无联盟 revenue API：revenue 保持 NULL / REVENUE_NOT_AVAILABLE。
2. GA4 `sessionSource=social` 会话与参与会话未回流到社媒漏斗。
3. 外部联盟 URL 可达性依赖第三方：Airalo TIMEOUT、Klook 403，与本轮改动无关。
