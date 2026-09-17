# 运营看板交接记录（/ops-dashboard/ · /ops/ops-center）

> 2026-09-16 事故修复留档。入口文档见 `docs/AI_CONTEXT.md`。
> 本文是「为什么这么配」的唯一权威来源；改 `_redirects` 或 `build.py` 前必读。

## 一句话现状

`https://www.chinaboundtravel.com/ops-dashboard/` → 301 → `/ops/ops-center`（200），
落地「统一运营中心 v3.0」，966 行，手工维护，线上已验证。

## 三份产物的分工（核心）

| 路径 | 性质 | 谁写 |
|---|---|---|
| `ops-dashboard/ops-center.html` → `static/ops/ops-center.html` | **手工维护**：统一运营中心（看板/监控/考核/成长/营收/KPI） | 无生成方。只由 workflow `cp` 原样同步，**任何脚本都不得写入** |
| `ops-dashboard/index.html` → `static/ops-dashboard/index.html` | 生成物：精简监控页（5 板块） | `ops-dashboard/build.py` |
| `dashboard_data.json`（3 份副本） | 运行时数据 | `ops-dashboard/collect_data.py` |

统一中心 HTML 里写死 4 个绝对路径依赖，缺一不可：
`/ops/dashboard_data.json`、`/ops/agent_kpi_data.json`、`/ops/agent_growth_data.json`、`./js/echarts.min.js`

## 事故：看板每 30 分钟被刷回旧版

- **根因**：`3a92c477`（2026-09-13 15:28 +08，"feat: P0-P2 quality remediation + five-path quality gate pipeline"）
  给 `ops-dashboard/build.py` 加了一行 `(ROOT / "ops-center.html").write_text(html, ...)`。
  此后 `ops-dashboard-hourly.yml` 每 30 分钟跑一次 build.py，就把 09-07 手工维护的统一运营中心
  整页覆盖成精简监控页。
- **叠加因素**：同期 `static/_redirects` 把方向配反（`/ops/ops-center` → `/ops-dashboard/`），
  两个入口都指向内容更少的那一版。
- **修复**：build.py 移除对 `ops-center.html` 的写入；hourly workflow 改为
  `cp ops-dashboard/ops-center.html static/ops/ops-center.html`；`_redirects` 5 条规则改指向统一中心。
- **恢复源**：`3a92c477^:ops-dashboard/ops-center.html`（74375 B / 966 行 / sha `02f086cd9a55ce1c`）
- **提交**：`ea2d5001`（恢复 + build.py + workflow + echarts）、`4f4be36b`（修重定向死循环）

## 两个必须记住的坑

### 坑 1：`_redirects` 绝不能加 `/ops/ops-center` 这条规则

Cloudflare 对**真实 `.html` 文件**启用无扩展名规范化：
`/ops/ops-center.html` → **308** → `/ops/ops-center`。

若同时配置 `/ops/ops-center` → `/ops/ops-center.html`，两条规则首尾相接构成死循环，
浏览器直接报「超过 5 次重定向」（exceeded the maximum of 5 redirects）。

规则：
- 规则目标一律写**无扩展名** `/ops/ops-center`（省掉 308 那跳，单跳落地）
- 规则必须**精确匹配**（不带 `*`），否则 `/ops/*.json` 数据请求会被重定向吞掉
- 该 308 是 Cloudflare 行为，不是 `_redirects` 产生的（本文件里只写过 301）
- 旁证：`/posts/xxx.html` → 404（那是目录页，不存在同名 .html 文件）；
  `/about/index.html` → 308 → `/about/`（剥 index.html）

### 坑 2：任何自动化都不得写 `ops-center.html`

- `build.py` 只写 `index.html`
- `ops-dashboard-hourly.yml` 用**白名单** `git add`，`cp` 方向为 源目录 → static
- `site-health-daily.yml` 第 98 行 `python ops-dashboard/build.py || true`、第 108 行 `git add -A`
  —— 这是历史上 `Closed Loop Agent` 能改到 `ops-center.html` 的通道（`52c6e89c`、`e07b8a6b` 等）。
  build.py 不再写该文件后这条通道已失效，但 `git add -A` 仍会把工作区**任何**残留文件（临时脚本等）
  一起提交。**提交前务必 `git status` 确认干净。**
- `site-health-daily.yml` 的 `build.py || true` 会静默吞掉构建失败

## 恢复 / 丢失对照

**恢复**：北极星指标、Agent 得分总览/对比/分布、等级分布、奖惩规则、数字员工成长档案、
能力值对比、营收渠道占比、营收因果链、营收实验列表、转化漏斗、用户增长漏斗、28 天流量趋势、
邮件订阅健康度、社媒平台分布、API 健康检查、性能监控、内容库存/覆盖率

**丢失**（生成版专有，统一中心里 0 命中）：
- **全站质量门禁**（09-13 新增的五路径质量门，488 问题 / 157 P0 / 阻断发布）
- **时间范围选择器**（今天 / 昨日 / 7天 / 30天 / 上个月 / 90天）

## 遗留待办（按优先级）

1. **考核/成长数据已修复并闭环**：`agent-kpi-monthly.yml` 现在会把
   `ops-dashboard/agent_kpi_data.json` 和 `ops-dashboard/agent_growth_data.json`
   同时发布到 `static/ops/`，并通过 workflow 校验保证 source/target 一致、JSON 可解析、
   `updated_at` / `month` / `group` / `employees` 等关键字段存在。
   手动触发记录见 GitHub Actions run `35231157737`，结果 `success`。
   后续如果再次发现陈旧数据，优先检查：
   1) workflow 是否真的运行到 publish step；
   2) `ops-dashboard/*` 源 JSON 是否被重新生成；
   3) `static/ops/*` 是否被后续 job 覆盖回旧值。

   历史根因留档：旧 workflow 只 `cp` 到 `static/ops-dashboard/`，**不写 `static/ops/`**，
   导致线上 `/ops/agent_kpi_data.json` 和 `/ops/agent_growth_data.json` 停留在 `2026-09-07`。
   已修复项：补上 `static/ops/` 发布、补上 Growth refresh 入口、补上回归测试。
2. **生成版精简监控页现已无任何 URL 可达**：`/ops-dashboard/index.html` → 308 → `/ops-dashboard/`
   → 301 → 统一中心。build.py 仍在生成它，但被重定向盖住。要恢复可访问性，
   给它单独路径（如 `/ops/monitor/`）。
3. **方案 B（根治）**：把「全站质量门禁 + 时间范围选择器」并进 `build.py`，
   合成单一产物，彻底消除两条平行产物与由此产生的所有覆盖事故。
4. **精简页数据 bug**：`metrics.ga4_daily` 是单日数据，卡片标签却写「过去7天」
   （09-16 实测单日 1 会话，真实 7 日为 56 会话 / 61 页浏览）；`metrics.gsc_28d.date` 为 09-12，
   页面「最新」却显示 2026-08-17。要改 `ops-dashboard/collect_data.py`。
5. `site-health-daily.yml` 的 `build.py || true` 静默吞失败。

## 线上验证清单

```
GET /ops-dashboard/           → 301 → /ops/ops-center
GET /ops/ops-center           → 200，966 行，<title> 含「统一运营中心 v3.0」
GET /ops/dashboard_data.json  → 200，generated_at 应在 30 分钟内
GET /ops/js/echarts.min.js    → 200，1029203 B
```

echarts 源文件只存在于 `ops-dashboard/js/echarts.min.js`，**必须** `cp` 到 `static/ops/js/`。
origin 上原本从未发布它，不补则统一中心所有图表 404（页面能开但全白）。

## 同批修复：日报链路

- `feishu_daily_report.py::_save_report()`：文件名 `report_` → `daily_`，用 `datetime.now(timezone.utc)`
  对齐 workflow 的 `date -u`。旧名导致 workflow 去重闸门永远读不到文件 → 重复触发重复推送飞书。
- GA4 新增 7 日滚动口径（D-7..D-1）+ 30 会话门槛；单日值仍原样展示
- `report_advice.py` 修正死别名 `avg_duration` → `avg_session_duration`（时长告警此前从不触发）
- `daily_issue_router.py` 兼容 `bounce_rate` 嵌套于 `behavior_analysis` + 百分数/小数双口径
- `feishu-daily-report.yml` 加失败门 `if: steps.send_report.outcome == 'failure'` → `exit 1`。
  否则 `continue-on-error: true` 吞掉 step 失败、job conclusion 仍为 success，
  `retry-failed.yml`（按 `conclusion == 'failure'` 触发）永不重跑。

## GA4 Data API 备忘

指标顺序固定：`[activeUsers(0), sessions(1), screenPageViews(2), engagementRate(3),
averageSessionDuration(4), bounceRate(5)]`

- `bounceRate` = 单页会话占比；实测 bounce + engagement = 恰 100%（真实 GA4 输出，非 bug）
- 跳出不宜用单日低样本（5 会话的日子会得出 100%）
- 参考值 2026-09-15：`['5','5','5','0','10.0469576','1']`
- 7 日滚动 09-09..09-15：`['37','56','61','0.4642857142857143','174.89227660714283','0.5357142857142857']`
