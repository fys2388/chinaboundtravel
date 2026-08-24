# ChinaBound Travel 2.0 — 部署达标与工作流闭环审计（P1-OPS-03）

- 审计日期：2026-08-20（Asia/Shanghai）
- 性质：只读审计 + 升级建议；未修改代码/内容/工作流，未 commit / push / deploy
- 结论：**PARTIAL_READY（部分达标）** —— 质量门与品牌/归因闭环已达标，运行配置与社媒/报告闭环存在 7 项未闭合缺口
- 依据：`docs/AI_CONTEXT.md`、`reports/management/REPORTING_SNAPSHOT.json`、`reports/CHINABOUND_TRAVEL_2_0_MASTER_DASHBOARD.md`、`reports/management/ALERTS.md`、`reports/P1_GROWTH_27R_TEST_ENVIRONMENT_REPAIR.md`、`reports/revenue/P1_GROWTH_27_*`、`.github/workflows/*.yml`（18 个）、相关脚本源码

## 1. 2.0 基线核对（真实来源）

| 维度 | 状态 | 证据 |
|---|---|---|
| 内容资产 | 60 posts / 60 content_id | content_id_audit --strict PASS（2026-08-19） |
| 构建 | 377 pages，0 错误 | hugo --gc --minify PASS（2026-08-19） |
| 测试 | 626 passed / 0 failed / 0 skipped | P1_GROWTH_27R（2026-08-19） |
| 品牌 2.0 | Editorial Voice；brand audit 106 文件 0 FAIL | 四项紧急修复验证 |
| OG/Twitter 标签 | 247 页 0 failed | scripts/audit_og_tags.py |
| Drive | ACTIVE + 营销 Cookie 门控 + 渲染唯一性 PASS | scripts/audit_drive_loader.py |
| GA4 归因 | page_path/content_id/partner/placement/cta_id/experiment_id 已入事件 | P1_GROWTH_27（2026-08-19，REV001/REV002 渲染验证） |
| 统一报告 | REPORTING_SNAPSHOT.json → reporting_engine.py → 五期报告 | P1-REPORT-02 PASS（2026-08-17） |
| 实验 | REV001 RUNNING / REV002 RUNNING(FROZEN) / REV003 PENDING / DRIVE-001 RUNNING | SNAPSHOT |
| Revenue | NULL（REVENUE_NOT_AVAILABLE） | SNAPSHOT |
| 索引 | 69 indexed / 89 not indexed；6 HIGH canonical；2 WAITING_RECRAWL | GSC 快照 2026-08-16 |
| 流量 | GA4 28d：166 sessions / 374 pageviews；GSC clicks 0 | fetch 2026-08-17（低样本） |

## 2. 工作流清单与闭环矩阵（18 个 workflow 实测）

| 工作流 | 触发 | 角色 | 2.0 状态 | 问题 |
|---|---|---|---|---|
| weekly-blog-update.yml | cron `0 0 * * *` + dispatch | 内容生成/双 AI 审核/QA/发布 | **配置滞后** | P1-OPS-02A 要求改 `0 0 * * 1`，未执行；仍每日运行 |
| deploy-cloudflare-pages.yml | push(main) + dispatch | Cloudflare Pages 部署 + 社媒发布 + 清缓存 | 冗余触发 | 与 weekly 显式 `gh workflow run` 双触发（concurrency 兜底）；且自带 social_publisher.py |
| content-rotation.yml | cron `0 2,10 * * *` + dispatch | 旧文轮换分发（content_rotator.py） | 多入口 | 与 social_publisher/social_distributor 无统一幂等 |
| social_distributor.yml | cron `0 9 * * *` + dispatch | 直连 FB/Twitter/LinkedIn/TikTok API | **重复风险** | 未走 Buffer Worker；独立 distribution_manifest.json，FB/X 可与 Worker 双发 |
| youtube-auto-publish.yml | cron `0 3 * * 1` + dispatch | YouTube 发布 | 正常 | 与社媒入口并存，属独立平台可接受 |
| deploy-buffer-worker.yml | push(main, buffer-worker/**) + dispatch | Worker 部署 | 正常 | - |
| feishu-daily-report.yml | cron `0 1 * * *` | 日报（读 SNAPSHOT） | 正常 | 只消费，不刷新 SNAPSHOT |
| feishu-weekly/monthly/quarterly/yearly-report.yml | cron 各自 | 飞书周/月/季/年报告 | **口径分裂** | 各自直连 GA4/GSC 重算，未消费 SNAPSHOT |
| env-check.yml | cron 每日 + PR + dispatch | 环境变量检查 | 正常 | - |
| health-check.yml | cron `0 1 * * *` | 站点/Buffer API/GA4 数据源 | 正常 | 依赖 BUFFER_API_TOKEN / GA4 服务账号 |
| error-alert.yml | workflow_run completed | 飞书告警 + Issue | 正常 | - |
| retry-failed.yml | workflow_run failure | 失败重试 | 有界 | 排除 workflow_dispatch → 最多自动重试 1 次；重试仍失败时无人工升级态 |
| manual-deploy.yml / purge-cache.yml | 仅 dispatch | 手动部署/清缓存 | 正常 | 不会自动循环 |
| monthly-ebook-update.yml | cron 每月 | Ebook 更新 | 正常 | - |

## 3. 闭环能力评估（8 环节）

| 环节 | 现状 | 结论 |
|---|---|---|
| 触发→执行 | 内容/报告/社媒/健康检查均有 schedule；weekly 仍每日 | 部分达标 |
| 质量验证 | Hugo build、brand、OG、Drive、risk gate、content_id 全绿 | 达标 |
| 失败告警 | error-alert → 飞书 + 自动 Issue | 达标 |
| 失败重试 | retry-failed 有界重试 1 次 | 达标（缺“重试仍失败”升级态） |
| 社媒健康 | /health 探测已实现 | **未闭环**：异常仅 print，未进飞书/ALERTS |
| 报告闭环 | SNAPSHOT 单源；五期报告 | **部分达标**：周/月/季/年飞书各自重算；SNAPSHOT 08-17 后未刷新 |
| 配置闭环 | NEW_BUFFER_WORKER_URL 为空；GSC 服务账号本地缺失 | **未闭环** |
| 索引/SEO 恢复 | 队列与审计有；6 HIGH canonical 未裁决 | 未闭环（可自动化复检） |

## 4. 关键缺口（按严重度）

1. **P1-OPS-02A 未落地**：weekly-blog-update.yml cron 仍为 `0 0 * * *`；`reports/P1_OPS_02_BLOG_AUTOMATION_CHANGE.md` 不存在。工作流名称“weekly”与实际每日运行不一致。
2. **Pinterest 长尾账户未生效**：`.env` 中 `NEW_BUFFER_WORKER_URL` 为空，`social_publisher.py`/`content_rotator.py` 会告警并回退主 Worker。
3. **社媒三入口未统一**：social_publisher（weekly + post-deploy 两个调用点）、content_rotator（每日 2 次）、social_distributor（每日直连 API）使用三份独立 manifest；FB/X/IG 存在同文双发风险；`social_distributor.py` 未接入 Buffer Worker，与“Buffer Worker 为唯一执行层”的目标不符。
4. **报告口径分裂 + 数据陈旧**：只有 feishu_daily_report.py 读 SNAPSHOT；周/月/季/年各自调用 GA4/GSC API 重算；SNAPSHOT generated_at=2026-08-17（3 天前），GSC 基线停在 08-15/16，且无每日自动刷新工作流。
5. **报告引用断裂**：REPORTING_SNAPSHOT 引用的 `reports/2.0_REPORTING_RECONCILIATION.md`、P1-OPS-01 审计、P1_GROWTH_26 GA4 审计均不存在。
6. **工作区/上下文漂移**：HEAD=`727841c`（P1-REPORT-03R），但 AI_CONTEXT.md 仍写 `247e686`；工作区 154 项未提交（含已批准任务产物与 buffer_config.json 的 staged 删除）。
7. **Revenue 未接通**：Travelpayouts/NordVPN 凭据存在但未验证；Airalo/Trip.com/Allianz/World Nomads/NordPass 为裸链无归因；Revenue=NULL 属真实状态。
8. **低样本约束**：GA4 28d sessions=166、affiliate clicks=0、GSC clicks=0，任何 SEO/转化成败结论必须保持 INSUFFICIENT_SAMPLE。

## 5. 升级路线

### P0（本周，阻断闭环的配置项）
1. weekly-blog-update.yml：cron 改为 `0 0 * * 1`，保留 workflow_dispatch（最小改动，已授权范围）。
2. 补齐 `NEW_BUFFER_WORKER_URL`（Pinterest 长尾 Worker 真实地址）；将两个脚本的 /health 异常写入飞书告警并置入 ALERTS。
3. 社媒执行层收敛：以 Buffer Worker 为唯一执行层；social_distributor.yml 的每日直连调度改为 KEEP/MODIFY（复用统一幂等键 slug+platform+date），消除 FB/X 双发。
4. 每日刷新 SNAPSHOT（reporting_kpi_engine.py --as-of today → reporting_engine.py --daily），周/月/季/年飞书脚本改为只读 SNAPSHOT。
5. 清理工作区：提交已批准产物或明确搁置，同步 AI_CONTEXT（HEAD=727841c、60/60、P1-BRAND-04=LOGO_REPLACEMENT_READY）。

### P1（两周）
6. 裁决 6 个 HIGH canonical conflict，并按 P1-GROWTH-24/25 队列执行 TOP5/TOP10 修复。
7. 配置 GSC 服务账号（Actions secrets）并新增每周索引快照拉取 → pages_newly_indexed / pages_losing_visibility 从 NOT_AVAILABLE 变为 CACHED。
8. 只读验证 Travelpayouts/NordVPN 凭据，接通真实 Revenue 数据源。
9. 处理 buffer_config.json 删除后的 token fallback：明确改由 secrets 提供 BUFFER_API_TOKEN 或移除 fallback。

### P2（一个月）
10. 社媒幂等键与每日限额跨 manifest 统一；去除 post-deploy 与 weekly 的重复部署触发（保留 push 唯一路径或显式单入口）。
11. legacy persona 25 篇按 3 篇/轮分批复审迁移。
12. 89 not indexed 纳入每周自动复检，与 canonical 队列联动。

## 6. 结论

- **部署构建面**：达标（Hugo/测试/品牌/OG/Drive/归因全部 PASS）。
- **闭环面**：内容生成、质量门、告警、有界重试已闭环；社媒幂等、Worker 配置、报告刷新、索引复检未闭环。
- **总状态**：PARTIAL_READY；完成 P0 后可达 READY（仍需低样本期观察）。
- 本次未提交、未推送、未部署；所有修改均需另行批准。
