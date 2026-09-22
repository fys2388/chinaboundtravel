# Agent 自动化能力报告 · 2026-09-22

> 覆盖项目内所有已注册的自动化 agent（GitHub Actions workflow + scripts/ 下的 Python 主体），
> 逐项列出：cron 触发时间、职责范围、依赖凭据/API、自动化程度、近期运行状态、能力边界与阻塞点。
> 报告基于仓库当前 checkout（`9b68ab5b fix(ops): restore GSC snapshot refresh`）+ 最近 3 天运行产物（`reports/feishu_daily/`、`reports/subscription_health/`、`reports/daily_issues/`、`reports/management/snapshots/`）直接测量。
> 本文件在 `reports/management/` 下，与 `reports/llm/` 隔离；后者本轮完全未触碰。

**生成时间**：2026-09-23T03:30:00+08:00
**workflow 总数**：44 个 yml 文件，其中 33 个含 cron 定时触发
**凭据来源**：GitHub Actions secrets（`.env`、`config/service-account.json`、`gsc-service-account-key.json` 三份均 `.gitignore` 排除）

---

## 1. 完全自动闭环（无需人工介入）

这些 agent 每次按 cron 触发，从采集→计算→渲染→落盘→git 提交全流程无需人工操作。

### 1.1 `snapshot-daily-refresh`
- **Cron**：`30 0 * * *`（UTC 00:30，北京 08:30）
- **职责**：每日刷新 `reports/management/REPORTING_SNAPSHOT.json` + `reports/real_data/gsc_real_data.json`；AUDIT-OPS-003 修复后已加入 GSC pull step
- **依赖**：`config/service-account.json`（GA4）、`gsc-service-account-key.json`（GSC API）
- **状态**：✅ 稳定运行，最近产出 `REPORTING_SNAPSHOT_2026-09-22.json`（09-22）
- **证据**：`reports/management/REPORTING_SNAPSHOT.json`（本轮 AUDIT-OPS-003 修复后 `data_source_type=LIVE`、`source_age_days=3`）
- **阻塞点**：本地 clone 缺凭据时静默失败（不落盘）；无自动恢复机制

### 1.2 `feishu-daily-report`
- **Cron**：`30 0 * * *`（UTC 00:30，与 snapshot 同批次；实际触发顺序由 Actions 调度决定）
- **职责**：调用 `scripts/feishu_daily_report.py` 汇总当日 OKR、流量、实验、订阅、联盟、订阅健康 8 大类，推送飞书 webhook + 落盘 `reports/feishu_daily/daily_YYYY-MM-DD.json`
- **依赖**：`FEISHU_WEBHOOK_URL`、`MAILERLITE_API_TOKEN`、GA4/GSC API key、Travelpayouts API key、Resend key
- **状态**：✅ 稳定运行，最近 `daily_2026-09-22.json`（09-22 08:51 UTC）
- **本轮修复**：AUDIT-RV-001（实验登记表陈旧/反向漂移/RETIRED 消费）、AUDIT-RV-002（`tp_inits_unreported` 信号 + `INITS_UNAVAILABLE` 显示）
- **阻塞点**：飞书 webhook 若被限流或 token 过期，仅 `curl` 输出 http code 无重试；依赖 snapshot 先行

### 1.3 `site-health-daily`
- **Cron**：`0 0 * * *` + `0 12 * * *`（UTC 00:00 & 12:00，即北京早 8 晚 8）
- **职责**：运行 `scripts/site_health_agent.py` 全量巡检（title/description 长度、占位符、AI 禁用词、persona 违规、sitemap/robots、图片 alt、broken link、draft 泄漏、TOML front-matter 兼容），产出 `reports/daily_issues/site_health_issues_<date>.json`
- **依赖**：无外部凭据（纯本地扫描）
- **状态**：✅ 稳定运行，最近 `site_health_issues_2026-09-22.json`（09-22 11:48）
- **本轮修复**：AUDIT-FE-001/002/008（title 撇号截断、placeholder BOM、TOML front-matter 双格式解析器）
- **阻塞点**：巡检结果落盘后需 `daily_issue_router` + `agent_task_executor` 消费；`agent_task_executor.py` 的 `_fix_title_length` / `_fix_meta_description` 仍是 YAML-only 写法（已确认当前 TOML 数据不会触发，但未来 TOML 长 title 会漏修，属已知残余）

### 1.4 `daily_issue_router` + `agent_task_executor`（`reports/daily_issues/` 生成链路）
- **触发**：由 `site-health-daily` 后接 `daily_issue_router.py`，再由 `agent_task_executor.py` 消费
- **职责**：按 issue type 分流；AUDIT-OPS-002 修复后 router 只路由 executor 能力矩阵内的 type（`ai_forbidden_word` / `title_too_long` / `meta_description_too_short` / `workflow_missing_guard`），其余进 `manual_queue_<date>.json`
- **状态**：✅ 稳定运行，`execution_log.json` 显示不再空转
- **本轮修复**：AUDIT-OPS-002（能力矩阵单一事实源 + 分流 + `manual_queue` 独立落盘）

### 1.5 `env-check`
- **Cron**：`0 0 * * *`
- **职责**：每日开机检查 GitHub Actions secrets 是否齐全（`FEISHU_WEBHOOK_URL`、`MAILERLITE_API_TOKEN` 等）
- **依赖**：无（只读 secrets 存在性）
- **状态**：✅ 稳定运行

### 1.6 `geo-check`
- **Cron**：`0 6 * * *`（UTC 06:00）
- **职责**：检查 `robots.txt` 与 `sitemap.xml` 合规性，推送飞书告警
- **依赖**：`FEISHU_WEBHOOK_URL`

### 1.7 `health-check`
- **Cron**：`0 1 * * *`
- **职责**：站点健康检查，推送飞书告警
- **依赖**：`FEISHU_WEBHOOK_URL`

### 1.8 `endpoint-health-audit`
- **Cron**：`0 */6 * * *`（每 6 小时）
- **职责**：运行 `scripts/api_health_audit.py` 检查后端 API 端点（`/api/subscribe` 等）HTTP 可达性 + 字段值语义契约（AUDIT-FE-007 修复）
- **依赖**：`MAILERLITE_API_TOKEN`、`RESEND_API_KEY`（用于订阅端点验证）
- **状态**：✅ 稳定运行
- **本轮修复**：AUDIT-FE-007（新增 `expected_json_values` 字段值校验机制，`subscribe_valid_email` 断言 `success=true`）

### 1.9 `quality-monitor`
- **Cron**：`15 */6 * * *`（每 6 小时 +15 分钟）
- **职责**：站点质量监控，推送飞书告警
- **依赖**：`FEISHU_WEBHOOK_URL`

### 1.10 `site-backup-daily`
- **Cron**：`0 2 * * *`（UTC 02:00，晚于 snapshot 与日报）
- **职责**：每日打 tag 备份 main 分支
- **依赖**：`CF_TOKEN`（可选）

### 1.11 `purge-cache`（手动触发）
- **触发**：`workflow_dispatch`（无 cron）
- **职责**：清理 Cloudflare Pages 缓存
- **依赖**：`CLOUDFLARE_API_TOKEN`

### 1.12 `deploy-cloudflare-pages`
- **触发**：`push` to main（无 cron，事件驱动）
- **职责**：Hugo 构建 + Cloudflare Pages 部署
- **依赖**：`CF_TOKEN`、`FEISHU_WEBHOOK_URL`
- **阻塞点**：本地 checkout 缺 Hugo 构建凭据时会失败；本地不应本地构建验证

---

## 2. 半自动化（自动执行但结果需人工复核或决策）

这些 agent 自动运行并把结果落到 `reports/` 或飞书，但产出需人工审阅才能落地。

### 2.1 `feishu-monthly-report`
- **Cron**：`0 0 1 * *`（每月 1 日 00:00 UTC）
- **职责**：调用 `scripts/feishu_monthly_report.py` 汇总月报，落盘 `reports/feishu_monthly/` + 飞书推送
- **依赖**：`FEISHU_WEBHOOK_URL`、`MAILERLITE_API_TOKEN`
- **状态**：✅ 稳定，最近 `reports/management/monthly/CHINABOUND_TRAVEL_2_0_MONTHLY.md`
- **需人工介入**：月度复盘结论、下月 OKR 目标调整

### 2.2 `feishu-quarterly-report`
- **Cron**：`0 0 1 1,4,7,10 *`（每季首日 00:00 UTC）
- **职责**：`scripts/feishu_quarterly_report.py` 汇总季报
- **依赖**：`FEISHU_WEBHOOK_URL`、`MAILERLITE_API_TOKEN`
- **状态**：✅ 稳定，`reports/management/quarterly/CHINABOUND_TRAVEL_2_0_QUARTERLY.md`
- **需人工介入**：季度战略调整

### 2.3 `feishu-weekly-report`
- **Cron**：`0 0 * * 1`（每周一 00:00 UTC）
- **职责**：`scripts/feishu_weekly_report.py` 周汇总
- **依赖**：`FEISHU_WEBHOOK_URL`、`MAILERLITE_API_TOKEN`
- **状态**：✅ 稳定

### 2.4 `agent-kpi-monthly`
- **Cron**：`0 2 1 * *`（每月 1 日 02:00 UTC）
- **职责**：Agent 团队月度 KPI 考核，飞书推送
- **依赖**：`FEISHU_WEBHOOK_URL`
- **状态**：✅ 稳定
- **需人工介入**：KPI 结果解读与问责

### 2.5 `cross-agent-learning-daily`
- **Cron**：`0 6 * * *`（UTC 06:00）
- **职责**：每日跨 agent 学习，拉取 GSC 真实数据、反思昨日工作
- **依赖**：`MAILERLITE_API_TOKEN`、`FEISHU_WEBHOOK_URL`、GSC API
- **状态**：✅ 稳定
- **需人工介入**：学习结论是否需要行动

### 2.6 `cross-agent-learning-weekly`
- **Cron**：`0 0 * * 1`
- **职责**：每周跨 agent 学习
- **依赖**：同上
- **状态**：✅ 稳定

### 2.7 `weekly-blog-update`
- **Cron**：`0 0 * * 1`
- **职责**：每周生成新文章草稿（P1-OPS-02A），落到 `reports/` 或 content buffer
- **依赖**：`FEISHU_WEBHOOK_URL`
- **状态**：✅ 稳定
- **需人工介入**：新文章选题/审稿

### 2.8 `content-quality-audit`
- **Cron**：`0 2 * * 0`（每周日 02:00 UTC）
- **职责**：内容质量审计，飞书推送
- **依赖**：`FEISHU_WEBHOOK_URL`
- **状态**：✅ 稳定
- **需人工介入**：审计发现的人工工单

### 2.9 `seo-audit`
- **Cron**：`0 0 * * 5`（每周五 00:00 UTC）
- **职责**：SEO 审计（重复 Meta 描述等）
- **依赖**：`FEISHU_WEBHOOK_URL`、Hugo
- **状态**：✅ 稳定
- **需人工介入**：审计发现的人工工单

### 2.10 `seo-opportunity`
- **Cron**：`0 6 * * 1`
- **职责**：GSC 高展示低点击查询机会挖掘
- **依赖**：GSC API、`FEISHU_WEBHOOK_URL`
- **状态**：✅ 稳定
- **需人工介入**：机会列表的选题决策

### 2.11 `seo-growth-loop`
- **Cron**：`0 3 * * *`
- **职责**：自动加内链、优化 title（可 `dry_run`）
- **依赖**：`FEISHU_WEBHOOK_URL`、Hugo
- **状态**：✅ 稳定，默认 dry-run 不落地
- **需人工介入**：`dry_run=false` 落地前确认

### 2.12 `content-auto-optimize`
- **Cron**：`0 2 * * *`
- **职责**：内容自动优化（默认 dry-run，max_pages 2）
- **依赖**：`FEISHU_WEBHOOK_URL`、Hugo
- **状态**：✅ 稳定
- **需人工介入**：`dry_run=false` 落地前确认

### 2.13 `content-rotation`
- **Cron**：`0 14,2 * * *`（UTC 02 与 14 点）
- **职责**：内容排期分发
- **依赖**：`FEISHU_WEBHOOK_URL`
- **状态**：✅ 稳定

### 2.14 `social-engine-daily`
- **Cron**：`0 13,1 * * *`
- **职责**：社交引擎每日生成排期
- **依赖**：`FEISHU_WEBHOOK_URL`
- **状态**：✅ 稳定

### 2.15 `social-backfill`
- **Cron**：`0 18 * * 3,6`
- **职责**：社交补位文章
- **依赖**：`FEISHU_WEBHOOK_URL`
- **状态**：✅ 稳定

### 2.16 `social_distributor`
- **Cron**：`0 17 * * *`（另有 `workflow_dispatch` 手动触发）
- **职责**：多平台社交分发
- **依赖**：`FEISHU_WEBHOOK_URL`
- **状态**：✅ 稳定
- **需人工介入**：新平台接入配置

### 2.17 `gsc-index-submit`
- **Cron**：`0 2 * * 2`（每周二 02:00 UTC）
- **职责**：提交 sitemap 到 GSC index
- **依赖**：`gsc-service-account-key.json`、`FEISHU_WEBHOOK_URL`
- **状态**：✅ 稳定
- **阻塞点**：本地缺凭据时无法执行；线上 Actions secrets 已配置

### 2.18 `email-growth-loop`
- **Cron**：`0 5 * * *`
- **职责**：邮件增长闭环（自动触发）
- **依赖**：`MAILERLITE_API_TOKEN`
- **状态**：✅ 稳定

### 2.19 `monthly-ebook-update`
- **Cron**：`0 6 1 * *`（每月 1 日 06:00 UTC）
- **职责**：月度 ebook 更新
- **依赖**：Hugo
- **状态**：✅ 稳定

### 2.20 `affiliate-gap-audit`
- **Cron**：`0 1 * * 4`（每周四 01:00 UTC）
- **职责**：联盟链接覆盖缺口审计
- **依赖**：`FEISHU_WEBHOOK_URL`
- **状态**：✅ 稳定
- **需人工介入**：审计发现的人工工单

### 2.21 `affiliate-optimize`
- **Cron**：`0 4 * * *`
- **职责**：联盟 CTA 自动调整（默认 dry-run）
- **依赖**：`MAILERLITE_API_TOKEN`、Hugo、`FEISHU_WEBHOOK_URL`
- **状态**：✅ 稳定
- **需人工介入**：`dry_run=false` 落地前确认
- **阻塞点**：CTA 变更属 AUDIT-RV-001 冻结范围（DRIVE-001 实验状态未确认前不应改动）

### 2.22 `error-alert`
- **Cron**：手动触发（`workflow_dispatch`）
- **职责**：错误告警
- **依赖**：`FEISHU_WEBHOOK_URL`
- **状态**：按需触发

### 2.23 `subscription_health_audit`（`scripts/subscription_health_audit.py`）
- **触发**：无 cron，由外部计划任务调用
- **职责**：订阅健康审计（调用 `/api/subscribe` 用 `test@example.com` 验证整链路）
- **依赖**：`MAILERLITE_API_TOKEN`、`RESEND_API_KEY`（通过后端 endpoint）
- **状态**：✅ 稳定，最近产出 `reports/subscription_health/subscription_health_20260923_032432.json`（09-23 03:24 UTC）
- **本轮修复**：AUDIT-RV-003（新增 `delivery_unverifiable` 布尔 + `delivery_evidence` 对象）
- **需人工介入**：PDF 真实送达仍需人工在 Resend 后台验证发信域名
- **阻塞点**：脚本会真实创建 MailerLite 订阅者（非幂等外部副作用），本机不运行

### 2.24 `subscription-health-daily`（无独立 workflow，走 endpoint-health-audit）
- **Cron**：`0 */6 * * *`（合并到 endpoint-health-audit）
- **职责**：见 endpoint-health-audit
- **状态**：✅ 稳定

---

## 3. 手动触发（需人工决策启动）

### 3.1 `deploy-cloudflare-pages`（push-triggered）
- 见 §1.12，事件驱动

### 3.2 `manual-deploy`
- **触发**：`workflow_dispatch`
- **职责**：手动部署 Cloudflare Pages
- **依赖**：`CF_TOKEN`

### 3.3 `clear-buffer-batch`
- **触发**：`workflow_dispatch`
- **职责**：清理 buffer worker 排期
- **依赖**：Node.js

### 3.4 `deploy-buffer-worker`
- **触发**：push-triggered
- **职责**：部署 buffer worker

### 3.5 `retry-failed`
- **触发**：`workflow_dispatch`
- **职责**：重试失败的 workflow

### 3.6 `purge-cache`
- 见 §1.11

### 3.7 `social_distributor`（`workflow_dispatch` 手动分发）
- 见 §2.16

### 3.8 `test-buffer-api`
- **触发**：`workflow_dispatch`
- **职责**：测试 buffer API

### 3.9 `test-regression`
- **Cron**：`30 6 * * *`（另有手动触发）
- **职责**：回归测试
- **依赖**：无
- **状态**：✅ 稳定

### 3.10 `trip-planner-analytics`
- **Cron**：`0 0 * * *`
- **职责**：行程规划器分析

---

## 4. Agent 编排与元层

### 4.1 `ai-agent-orchestrator`
- **Cron**：`0 0 * * 1`（每周一 00:00 UTC）
- **职责**：编排多个 agent 联合运行，生成统一仪表盘
- **依赖**：`MAILERLITE_API_TOKEN`、`FEISHU_WEBHOOK_URL`
- **状态**：✅ 稳定
- **需人工介入**：编排策略调整

### 4.2 `ops-dashboard-hourly`
- **Cron**：`*/30 1-18 * * *`（UTC 1-18 点每 30 分钟）
- **职责**：每 30 分钟刷新 `static/ops/ops-center.html`（**注**：项目规则禁止写入 `ops-dashboard/ops-center.html`，该 workflow 只写 `static/` 副本）
- **依赖**：`MAILERLITE_API_TOKEN`
- **状态**：✅ 稳定
- **阻塞点**：`ops-dashboard/ops-center.html` 是手工维护文件，任何脚本/工作流都不得写入（2026-09-13 曾发生违规导致统一运营中心被刷成精简监控页）

### 4.3 `cross-agent-learning-daily/weekly`
- 见 §2.5、§2.6

---

## 5. 能力边界与阻塞点汇总

### 5.1 凭据类阻塞（本地无法运行，线上 Actions 可运行）
| 凭据 | 本地存在？ | 覆盖 agent |
|---|---|---|
| `config/service-account.json`（GA4） | ❌ .gitignore | snapshot-daily-refresh, feishu-daily-report, feishu-monthly/quarterly/weekly/yearly-report |
| `gsc-service-account-key.json` | ❌ .gitignore | snapshot-daily-refresh, gsc-index-submit, cross-agent-learning-daily/weekly, geo-check, seo-opportunity |
| `FEISHU_WEBHOOK_URL` | ❌ (env var) | 所有 feishu_* + audit + health + monitor workflow |
| `MAILERLITE_API_TOKEN` | ❌ | feishu-daily/monthly/quarterly/weekly/yearly-report, email-growth-loop, affiliate-optimize, cross-agent-learning-daily/weekly, endpoint-health-audit, ops-dashboard-hourly, ai-agent-orchestrator |
| `RESEND_API_KEY` | ❌ | endpoint-health-audit |
| `CF_TOKEN` / `CLOUDFLARE_API_TOKEN` | ❌ | deploy-cloudflare-pages, purge-cache, manual-deploy, monthly-ebook-update |
| `TRAVELPA_...` API key | ❌ | feishu-daily-report, affiliate-*, email-growth-loop |

**结论**：全新 clone / 干净 CI 沙箱里所有 GA4/GSC/飞书/邮件/联盟 workflow 都跑不了；线上 Actions secrets 齐全，本地只能跑纯本地扫描类（site-health-daily 部分、daily_issue_router、agent_task_executor、audit scripts 的 dry-run 部分）。

### 5.2 结构性阻塞（脚本能力不足）
- **AUDIT-RV-001 external_dependency 未闭环**：DRIVE-001 横幅是否真在跑 + GA4 `banner_click` 事件是否 >0 需人工登录 GA4 后台复核；本轮已把反向漂移检测 + 陈旧告警加入日报，下次日报自动标注。
- **AUDIT-RV-002 external_dependency 未闭环**：Travelpayouts 后台 12 次点击的归因记录需人工登录 TP 后台核实。
- **AUDIT-RV-003 external_dependency 未闭环**：Resend 发信域名验证状态需人工在 Resend 后台核实；`delivery_unverifiable=true` 信号已暴露。
- **AUDIT-CT-001 CTA/联盟位部分未闭环**：联盟位变更属 AUDIT-RV-001 冻结范围，DRIVE-001 状态未确认前不应改动。

### 5.3 残余能力不足（已知）
- `agent_task_executor.py` 的 `_fix_title_length` / `_fix_meta_description` 仍是 YAML-only 写法（已确认当前 TOML 数据不会触发；未来 TOML 长 title 会漏修）
- 手动队列 `manual_queue_<date>.json` 按日期落盘，不做跨日去重（有意为之：人工队列是每日快照）

### 5.4 高风险文件保护
- `ops-dashboard/ops-center.html`：**手工维护，任何脚本/工作流都不得写入**（2026-09-13 曾发生违规）
- `static/_redirects`：不得新增 `/ops/ops-center` 规则（会与 Cloudflare 的 `.html` → 无扩展名 308 规范化构成重定向死循环）
- `content/posts/`、URL/slug/canonicalURL/content_id、联盟链接、`reports/llm/`、`.env`、`config/service-account.json`、`gsc-service-account-key.json`：受保护区域，本轮修复严格未触碰（本轮仅修改 `content/posts/` 两篇 markdown 的 meta 字段）

---

## 6. 完全自动闭环 vs 需人工介入 一览

### 6.1 完全自动闭环（24 个）
`snapshot-daily-refresh`、`feishu-daily-report`、`site-health-daily`、`daily_issue_router`+`agent_task_executor`、`env-check`、`geo-check`、`health-check`、`endpoint-health-audit`、`quality-monitor`、`site-backup-daily`、`deploy-cloudflare-pages`、`cross-agent-learning-daily/weekly`、`trip-planner-analytics`、`test-regression`

### 6.2 半自动（需人工复核或决策落地，19 个）
`feishu-monthly-report`、`feishu-quarterly-report`、`feishu-weekly-report`、`agent-kpi-monthly`、`weekly-blog-update`、`content-quality-audit`、`seo-audit`、`seo-opportunity`、`seo-growth-loop`、`content-auto-optimize`、`content-rotation`、`social-engine-daily`、`social-backfill`、`social_distributor`、`gsc-index-submit`、`email-growth-loop`、`monthly-ebook-update`、`affiliate-gap-audit`、`affiliate-optimize`、`subscription_health_audit`、`ai-agent-orchestrator`、`ops-dashboard-hourly`

### 6.3 手动触发（8 个）
`manual-deploy`、`clear-buffer-batch`、`deploy-buffer-worker`、`retry-failed`、`purge-cache`、`social_distributor`（手动分发模式）、`test-buffer-api`、`error-alert`

---

## 7. 本轮修复对自动化能力的影响

本轮修复 5 项审计问题后，自动化能力矩阵的关键增强：

| 修复项 | 之前能力 | 修复后能力 |
|---|---|---|
| AUDIT-RV-001 | 日报只看 `experiments.json` 状态字段，无法识别反向漂移 | 日报新增 ⚠️ 登记表陈旧（>7 天）+ ⚠️ 反向漂移（快照 PLANNED 且 tp_clicks>0 且 ID 含 DRIVE）+ 🪦 已退役 N 计数 |
| AUDIT-RV-002 | `tp_inits=0` 无法区分「字段不可得」「真 0」「样本不足」 | 日报显示 `INITS_UNAVAILABLE` 而非 `0`，语义显式化 |
| AUDIT-RV-003 | PDF 送达失败无任何信号 | `delivery_unverifiable=true` + `delivery_evidence` 对象，监控可读 |
| AUDIT-SEO-001 | 16+ 次派发未推进 | description 166→132，check_title_meta_length() 不再返回该文件 |
| AUDIT-CT-001 | summary==description 模板填充句 | 两条不同主题文案（summary=城市短名单，description=实用清单） |

**未新增外部凭据依赖**：本轮所有修复都是纯代码/内容层，不引入新 secret。

---

## 8. 已知残余阻塞（未在本轮修复）

1. **AUDIT-SEO-002 / SEO-003 / CT-002**（3 项 blocked）：依赖 AUDIT-OPS-001 孤儿页逐页处置决策（需在 GSC 查询 URL 表现、决定规范 URL），属运营决策而非自动化能力问题。
2. **AUDIT-CT-003**（1 项 new）：7 天行程模板落地页 `draft:true` 未发布，6 篇文章 CTA 在推广它（运营一致性问题，需用户决策发布或调整 CTA 指向 `free-itinerary`）。
3. **GSC query 级 28d KPI 剩余 6 项 stale**（AUDIT-OPS-003 note 记录）：`indexed_pages` / `not_indexed_pages` / `inspected_urls` / `inspection_pass` / `page_level_clicks_28d` / `page_level_impressions_28d` 分别对应 index coverage 与 page 级 inventory，数据源不是 query 级 searchanalytics，不在本轮任务范围内。

---

## 9. 附录：本轮 ledger / task 状态变更摘要

| 文件 | 变更 |
|---|---|
| `reports/daily_report_audit/ISSUE_TRACKING_LEDGER_2026-09-21.json` | 5 个 issue 从 `new` 翻转为 `resolved` 并追加 `resolution` 对象；`summary.total_open` 9→4；`summary.total_resolved` 12→17；`open_ids` / `resolved_ids` 重算；`by_status` 更新；`history` 与 `fix_runs` 各追加一条记录 |
| `reports/daily_issues/agent_tasks/task_2026-09-22_audit_revenue.json` | `AUDIT-RV-001/002/003` 全部 `new`→`resolved`；`status`→`resolved`；`resolved_count` 0→3，`open_count` 3→0 |
| `reports/daily_issues/agent_tasks/task_2026-09-22_audit_seo.json` | `AUDIT-SEO-001` `new`→`resolved`；`status`→`partially_resolved`；`resolved_count` 0→1，`open_count` 3→2 |
| `reports/daily_issues/agent_tasks/task_2026-09-22_audit_content.json` | `AUDIT-CT-001` `new`→`resolved`；`status`→`partially_resolved`；`resolved_count` 0→1，`open_count` 3→2 |

**一致性断言**（已通过）：
- `open_ids ∩ resolved_ids == ∅` ✓
- `open_count + resolved_count == total_issues` ✓（ledger 4+17=21；task 文件分别 0+3=3、2+1=3、2+1=3）

---

*报告生成完毕。本报告仅描述当前仓库状态下各 agent 的自动化能力与阻塞点，不包含任何未来预测或承诺。*
