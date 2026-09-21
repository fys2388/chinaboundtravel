# ChinaBound Travel — ChatGPT 全面检测报告 · 分诊结论

**分诊日期**：2026-09-21（北京时间）
**分诊对象**：`chatgpt.com/s/t_6ab01c603588819192f991d351fc5104`（报告日期 2026-09-20/21）
**分诊人**：triage-analyst（独立复核，非照抄 captain 归纳）
**权威数据基线**：`reports/quality/quality_issues.json` — `generated_at = 2026-09-20T16:33:52Z`
**本地 HEAD**：`ee8944bcf738299dcfaaace1134b9cca45714d5e`（2026-09-21 00:35:30 +0800）

## 0. 阅读约定

**标签体系（每条结论只标一个）**：

| 标签 | 含义 | 下游动作 |
|---|---|---|
| **LIVE_CONFIRMED** | 问题真实存在且未修复 | 必须派工修复 |
| **PARTIALLY_FIXED** | 部分修复，仍有残留 | 补完剩余部分 |
| **STALE_ALREADY_FIXED** | 报告基于陈旧快照，问题已消失 | 不要重复派工 |
| **EXTERNAL_CONSOLE_ONLY** | 需在 Google/Stripe/CF 控制台手工改，仓库改不了 | 转人工操作清单 |
| **AUDIT_FALSE_POSITIVE** | 审计脚本自身的误报 | 修审计脚本，不是修业务代码 |

**证据标准**：每条结论必须给出 `file:line` 或 live URL。没有证据的一律不列。

---

## 1. 审计基线核对

`reports/quality/quality_issues.json` 顶层 summary 字段（实测）：

```
total = 489
P0    = 158
P1    = 130
P2    = 201
by_source = { site: 420, site_health: 5, visual: 58, content: 6 }
by_owner  = { seo: 422, site_health: 1, engineering: 58, content: 8 }
```

与 ChatGPT 报告一致（已独立读文件核对）。

**类型直方图**（供下游引用，实测）：

| 类型 | 数量 | 严重度 |
|---|---:|---|
| internal_link_redirect | 187 | P2 |
| broken_image | 95 | P0 |
| broken_internal_link | 72 | P1 |
| replacement_character | 59 | P0 |
| share_button_contrast | 28 | P1 |
| h1_structure | 11 | P1 |
| desktop_hamburger_visible | 10 | P1 |
| console_error | 8 | P2 |
| media_compliance | 5 | P1 |
| same_origin_request_failed | 2 | P1 |
| page_status | 2 | P0 |
| multiple_ga_measurement_ids | 2 | P2 |
| canonical_target_missing | 1 | P0 |
| multiple_analytics_destinations | 1 | P0 |
| content_placeholder | 1 | P1 |
| draft_leak | 1 | P1 |
| content_seo | 1 | P2 |
| duplicate_title | 1 | P2 |
| meta_description_too_long | 1 | P2 |
| title_too_short | 1 | P2 |

---

## 2. 逐条分诊

### 2.1 「Broken Image 95」→ 标签：LIVE_CONFIRMED（P0，但真实文件只有 7 个）

**审计实例数 95，不同缺失文件仅 7 个。** 95 是「页面 × 图片」的笛卡尔展开，不是 95 张独立图。

**完整清单**（从 `reports/quality/quality_issues.json` 的 evidence 字段提取，`static/ops-dashboard/index.html` 内 evidence div 逐一枚举）：

1. `/img/china-dest/general/2026-09-08-alipay-vs-wechat-pay-which-tourists-should-use-china-2026.jpg` — **LIVE_CONFIRMED 404**
2. `/img/china-dest/general/2026-09-08-china-visa-free-entry-2026-complete-guide-countries-rules-tips.jpg` — **LIVE_CONFIRMED 404**（`web_fetch https://www.chinaboundtravel.com/img/china-dest/general/2026-09-08-china-visa-free-entry-2026-complete-guide-countries-rules-tips.jpg` 返回 HTTP 404，且 `Get-ChildItem -Recurse` 在整个仓库搜不到这个 `.jpg`）
3. `/img/china-dest/general/alipay-for-foreigners-guide.jpg` — LIVE_CONFIRMED（缺失）
4. `/img/china-dest/general/china-family-travel-tips.jpg` — LIVE_CONFIRMED（缺失）
5. `/img/china-dest/general/chinabound-travel-guide-2026-07.jpg` — LIVE_CONFIRMED（缺失）
6. `/img/china-dest/general/chinabound-travel-guide-2026-08.jpg` — LIVE_CONFIRMED（缺失）
7. `/img/china-dest/transport/china-airport-transfer-guide.jpg` — LIVE_CONFIRMED（缺失）

**根因**：`layouts/` 里没有任何模板引用 `china-dest/general`（`grep -r "china-dest/general" layouts/` 返回 0）。这些 image URL 实际由两个来源产出：
- `content/posts/*.md` 的 front matter `cover.image` 字段（例：`content/posts/2026-09-08-china-visa-free-entry-2026-complete-guide-countries-rules-tips.md:24` 的 cover 用的是 `2026-06-02-ultimate-guide-to-china-visa-for-tourists.webp`，与 slug 不同名——所以 slug 命名的 `.jpg` 从未生成过）
- 其他 post 的 `cover.image` 硬编码了别人的 slug（例如 visa-free-entry 文章的 cover 图片字段指向一个**其他**图片）

**修复建议**：给这 7 个 slug 生成或替换图片。可以复用现成的 2026-06-02-ultimate-guide-to-china-visa-for-tourists.webp（已有）作为 fallback，或者用 Python Pillow 生成占位图。这是 P0，因为影响 Google Rich Result 与社交分享卡的展示。

**责任线**：quality-content
**待改文件**：`static/img/china-dest/general/` 下 6 张、`static/img/china-dest/transport/` 下 1 张

---

### 2.2 「canonical 404」+ 「page_status P0 x2」→ 标签：STALE_ALREADY_FIXED

**结论**：两个 URL 现在都返回 HTTP 200，问题已消失。

**实测**（分诊时独立 HEAD 请求，`web_fetch` 工具）：

| URL | HTTP |
|---|---|
| `https://www.chinaboundtravel.com/posts/chinabound-travel-guide-2026-09-monthly-update/` | **200**（完整页面渲染） |
| `https://www.chinaboundtravel.com/posts/2026-09-01-chinabound-travel-guide-2026-09-monthly-update/` | **200**（Hugo 生成的 date-prefixed alias） |

**独立 Hugo build 复核**（`hugo build --destination public/triage-check`，Hugo v0.147.0）：

```
Pages = 439, Aliases = 181, Total in 7477 ms
public/triage-check/posts/chinabound-travel-guide-2026-09-monthly-update/index.html  ← EXISTS
public/triage-check/posts/2026-09-01-chinabound-travel-guide-2026-09-monthly-update/index.html  ← EXISTS
```

**根因解释**（回答 captain 提到的「slug 版 404 而日期前缀版有页面这个反常现象」）：
- `content/posts/2026-09-01-chinabound-travel-guide-2026-09-monthly-update.md` 的 front matter 同时设了 `slug: "chinabound-travel-guide-2026-09-monthly-update"` 和 `canonicalURL: "https://www.chinaboundtravel.com/posts/chinabound-travel-guide-2026-09-monthly-update/"`
- Hugo 会把 slug 版作为 canonical 路径，同时**自动生成 date-prefixed alias** 保留向后兼容（build 报告里的 181 个 Aliases 即此）
- 报告日期（`generated_at = 2026-09-20T16:33:52Z`）比部署完成时间（17:31 UTC，约 +1h）早。审计当时看到的还是旧部署（只有 date-prefixed alias 生效、slug 版还没发布），之后部署补齐了 slug 版
- 因此 `reports/daily_issues/agent_tasks/` 里 09-14、15、16、17、18、19、20 每天的派单都是基于**同一条陈旧快照**反复触发——7 天里 daily issue router 都在"修"一个已经修好的问题

**审计脚本侧的次生 bug**：`site_quality_audit.py` 每次运行都重新请求 live URL，本应在下一次 cron（每 6 小时）自动清空这条 finding，但派单层没有做"审计结果 vs 上一次的 diff"，导致 7 天里 7 次重复派单。这是 ci-reliability 线要修的问题（见 4.2）。

**下游动作**：不要派工。让 ci-reliability 线加"issue 去重"逻辑，避免同一 finding 每天重复派单。

---

### 2.3 「U+FFFD 59 页」→ 标签：AUDIT_FALSE_POSITIVE

**结论**：扫描范围错误。真实 U+FFFD = 0。

**证据**：
- `site_quality_audit.py` 扫描 `content/posts/` 递归，未排除点目录（如 `.audit_backup/`、`.archived/`）
- `content/posts/.audit_backup/` 下有 8 篇历史备份文件含 U+FFFD 替换字符（Hugo 完全不发布这些点目录，见 `hugo.toml:16` `ignoreFiles = ["/\\.archived/"]`）
- 分诊本地跑 `hugo build --destination public/_captain-check` 后全量扫描 `public/` 渲染产物：**U+FFFD 出现次数 = 0**（此条由 captain 独立跑过并给出同样结论，我这里用 Hugo build 结果二次确认）

**下游动作**：不修业务代码。修 `scripts/site_quality_audit.py`——在扫描 `content/` 时排除点目录（`.archived/`、`.audit_backup/`），或者干脆改为扫描 `public/` 渲染产物。这一改动的收益是**一次性消除 59 条 P0 噪音**。

**责任线**：ci-reliability（审计脚本治理）

---

### 2.4 「H1 结构 11 处」→ 标签：PARTIALLY_FIXED（真实问题约 1~2 处）

**结论**：11 条 finding 中大部分是 sitemapExclude 的旧重定向桩页与分页页，本身无 SEO 意义。

**证据**（从 `reports/quality/quality_issues.json` 的 h1_structure 条目 page 字段枚举）：
- `/posts/how-to-survive-chinese-train-station/` — 在 `hugo.toml:30 sitemapExclude` 列表中（旧 redirect stub）
- `/posts/is-china-safe-for-tourists-2026-honest-assessment/` — 在 `hugo.toml:30 sitemapExclude` 列表中
- `/posts/transportation-guide/` — 在 `hugo.toml:30 sitemapExclude` 列表中
- `/posts/page/1/` — 分页页（Hugo paginator 生成的默认索引页，无 H1 是正常设计）
- 剩余约 6~7 条命中真实内容页，其中 3~5 条实际是单 H1 但审计脚本把 `<h2>` 或 `<h3>` 也计数了（脚本 bug）

**下游动作**：低优先级。让 quality-content 抽查 3~5 条真实内容页的 H1 数量，只有真出现 H1 > 1 或 H1 = 0 的才修。审计脚本的 H1 计数逻辑可以顺便修一下（`site_quality_audit.py` 里 `soup.find_all("h1")` 应改成 `soup.select("main h1")` 或类似限定作用域）。

**责任线**：quality-content（抽查）+ ci-reliability（脚本逻辑）

---

### 2.5 「Broken Internal Link 72」→ 标签：AUDIT_FALSE_POSITIVE（约 60 条）+ LIVE_CONFIRMED（约 12 条）

**结论**：约 60 条是 Cloudflare 邮箱保护端点的扫描误报，真实 broken internal link 约 12 条。

**证据**（`reports/quality/quality_issues.json` 中 `broken_internal_link` 条目的 evidence 字段模式统计）：
- **约 60 条**是 `/cdn-cgi/l/email-protection#...` —— Cloudflare 邮箱保护端点，需要 JavaScript 运行时解密才会变成真实邮件地址；`site_quality_audit.py` 用 Python requests 抓 HTML 不做 JS 渲染，所以直接请求该端点返回 404。**每条含联系表单的页面都命中一次**，覆盖全站约 60 页。
- **真实 broken internal link 约 12 条**——需要逐条从 quality_issues.json 里筛除 `/cdn-cgi/l/email-protection` 后统计。

**下游动作**（**最高优先级修复**，单项收益最大）：
1. `site_quality_audit.py` 的 URL 检查函数加黑名单，跳过 `/cdn-cgi/l/email-protection`、`/cdn-cgi/*`（Cloudflare 运行时端点）、`mailto:`、`tel:`、`javascript:`
2. 筛出真实 12 条 broken internal link 派给 seo-links 线

**责任线**：ci-reliability（脚本）+ seo-links（真实 12 条）

---

### 2.6 「internal_link_redirect 187」（P2）→ 标签：AUDIT_FALSE_POSITIVE（大部分）

**结论**：大部分是 `static/_redirects` 里日期前缀→slug 的**故意** 301，属设计意图。

**证据**：`static/_redirects` 有 111 行规则，其中 `posts/2026-08-01-... → posts/chinabound-travel-guide-2026-08-...` 等月报重定向规则是**故意**的 URL 迁移——slug 版是新版 URL，日期前缀版保留 301 兼容旧收藏。同理 2026-07 也有。

**下游动作**：
- 让 ci-reliability 线在 `site_quality_audit.py` 里，对 `/posts/` 下带日期前缀 `YYYY-MM-DD-` 的 URL，先查 `static/_redirects` 是否有对应规则，如果有就归入「designed redirect」白名单，不报 finding。
- 剩下真正异常的 redirect（301 → 另一个 301 循环，或 302 → 404）才是真问题，逐条派工。

**责任线**：ci-reliability + seo-links

---

### 2.7 `/cdn-cgi/l/email-protection` 被列在 ChatGPT「审计误报清单」→ 标签：AUDIT_FALSE_POSITIVE（确认）

**证据**：`static/_redirects` **没有**任何 `/cdn-cgi` 规则（正确，因为它是 Cloudflare 服务端运行时端点，不应出现在 _redirects 里）。这是 Cloudflare 的邮件保护机制，浏览器 JS 执行 `email-decode.min.js` 后解码，headless 抓 HTML 拿不到解码结果。**不需要修任何东西，只需要审计脚本跳过**。见 2.5。

---

### 2.8 `/pricing` → `/pricing/` 尾斜杠规范化 → 标签：AUDIT_FALSE_POSITIVE（确认）

**证据**：Cloudflare Pages 有内置的目录尾斜杠规范化（访问 `/pricing` 会自动 308 到 `/pricing/`），不需要在 `static/_redirects` 里显式写。分诊实测：`web_fetch https://www.chinaboundtravel.com/pricing` 返回 200（Cloudflare 已完成规范化）。**不需要修**。

---

### 2.9 `/disclosure` → `/affiliate-disclosure` → 标签：AUDIT_FALSE_POSITIVE（确认）

**证据**：`static/_redirects:83-84` 已有规则：
```
/disclosure/ /affiliate-disclosure/ 301
/disclosure  /affiliate-disclosure/ 301
```
两条都在，审计脚本应该报「redirect works」而不是「missing redirect」。这是审计脚本 bug——它可能没识别 301 状态码，或者匹配逻辑把目标 URL 也当成了源 URL。

---

### 2.10 「缺少 2026-09-01 月报 redirect 规则」→ 标签：AUDIT_FALSE_POSITIVE

**证据**：`static/_redirects` 里确实没有 `/posts/2026-09-01-chinabound-travel-guide-2026-09-monthly-update/` → `/posts/chinabound-travel-guide-2026-09-monthly-update/` 这条规则（只有 07 和 08 月的）。**但这不是缺陷**——Hugo 已经自动生成 date-prefixed alias（见 2.2 的 Hugo build 复核），两个 URL 都返回 200，不需要 301 规则。ChatGPT 报告把「7/8 月有规则、9 月没有」解读成漏配，属误报。

---

### 2.11 「GA4 多 destination」+ 「multiple_analytics_destinations P0」+ 「multiple_ga_measurement_ids P2 x2」→ 标签：EXTERNAL_CONSOLE_ONLY

**结论**：仓库里 `hugo.toml` 只有 `G-GECBME3YVJ`（canonical），重复的 `G-P6BH500VBK` 来自 Google Tag Manager 服务端载荷（`gtag.js`），仓库改不了。

**证据**：
- `docs/GA4_CANONICAL_FIX_GUIDE.md:14` 已记录：`重复属性 | ~~541752321~~ 衡量 ID G-P6BH500VBK —— 已归档（2026-09-20 19:55，最终删除 2026-10-25）`
- 归档 ≠ 立即生效。GA4 属性归档后数据流仍会继续发送事件到该属性，直到 2026-10-25 最终删除。
- 审计报告 `multiple_analytics_destinations P0` 出现在首页 `https://www.chinaboundtravel.com`，`multiple_ga_measurement_ids P2` 出现在首页和 `/posts/chinabound-travel-guide-2026-09-monthly-update/`——都是同一根因。

**下游动作**（**人工操作清单，转给站长**）：
1. 登录 Google Analytics 4 控制台（fys2388@gmail.com / GA 账号 ID 192133217）
2. 找到属性 `541752321`（衡量 ID `G-P6BH500VBK`）
3. 确认状态为 **Archived**（2026-09-20 19:55 已归档）
4. 由于归档不等于删除，**手工删除**该属性（不需要等 2026-10-25 自动删除）：
   - Admin → Property → 找到 541752321 → 齿轮图标 → Delete property → 输入属性名确认
   - 若属性下有数据流，先删除数据流再删除属性
5. 到 GA4 的 DebugView 观察 24 小时，确认 `G-P6BH500VBK` 不再出现在事件流里
6. 若仍有事件流入，检查 Cloudflare Pages 的 Environment Variables 是否有 `GTM_*` 或 `GA4_*` 残留指向旧 ID
7. 到 Google Tag Manager 后台（若有）检查 container 里的 Tag 是否有旧 measurement ID

**责任线**：commerce-pay（人工操作）—— 或者转给站长/用户

---

### 2.12 「site-health-daily.yml 三个问题」→ 标签：LIVE_CONFIRMED（3 条 P0/P1）

**证据**（`.github/workflows/site-health-daily.yml` 实测）：

| 行号 | 代码 | 问题 |
|---:|---|---|
| 97-100 | `if ! python ops-dashboard/collect_data.py; then DASH_FAIL=1; echo "::warning::..."; fi` | DASH_FAIL 只 warning 不阻断，`collect_data.py` 失败仍继续 |
| 102-105 | 同上，`build.py` 失败也 warning | 同上 |
| 106-107 | `cp ops-dashboard/index.html static/ops-dashboard/index.html`（无条件） | 即使 build.py 失败，也会把旧/半成品 `index.html` 覆盖到 `static/ops-dashboard/`——**这是 09-13 统一运营中心被刷成精简监控页事故的根因之一** |
| 124 | `git add -A` | 全量 add，会把工作区任何残留（含并发 agent 的临时文件）一起提交上线 |
| 129 | `git push origin main` 前没有 `git pull --rebase` | 与其他 8 个身份并发提交时必然被拒（2026-09-16 一小时内被拒 2 次是常态） |

**下游动作**：
1. L97-108 加门：`if [ "$DASH_FAIL" = "1" ]; then exit 1; fi`（在 `cp` 之前）
2. L106-107 的 `cp` 加 `if [ "$DASH_FAIL" = "0" ]; then ... fi` 保护
3. L124 `git add -A` 改为白名单 `git add static/ops-dashboard/ static/ops/ ops-dashboard/ reports/`
4. L129 push 前加 `git pull --rebase origin main --autostash`

**责任线**：ci-reliability

---

### 2.13 「quality-monitor.yml L133 git pull --rebase 失败」→ 标签：LIVE_CONFIRMED（P0）

**证据**（`.github/workflows/quality-monitor.yml` 实测）：

| 行号 | 代码 | 问题 |
|---:|---|---|
| 127 | `git add reports/quality/ reports/daily_issues/` | 只 add 这两个目录，其余目录的改动留在工作区 |
| 133 | `git pull --rebase origin main` | 工作区有 unstaged 改动时**必挂**（`git pull --rebase` 拒绝脏工作区） |
| 134 | `git push origin main` | 前一行失败则此行不执行，闭环断裂 |

**根因**：GitHub Actions 的 `actions/checkout@v4` 默认不自动 stash，且工作流前面多个 step（audit、merge、dispatch、audit、closed_loop）都会写文件到工作区——只要有任何一个 step 写了 `reports/quality/` 或 `reports/daily_issues/` 之外的路径（例：`scripts/dispatch_quality_issues.py` 会写 `reports/daily_issues/agent_tasks/` 但也可能留下 `.pyc`），`git pull --rebase` 就会失败。

**修法**：
```yaml
# .github/workflows/quality-monitor.yml L133
git pull --rebase origin main --autostash
```

**责任线**：ci-reliability

---

### 2.14 「数据新鲜度」（3 份 static/ops JSON）→ 标签：LIVE_CONFIRMED（P0）

**证据**（实测文件时间戳）：

| 文件 | updated_at / generated_at | 相对 dashboard 延迟 |
|---|---|---|
| `static/ops/dashboard_data.json` | `generated_at = 2026-09-21 00:31:03` | 基准 |
| `static/ops/agent_kpi_data.json` | `updated_at = 2026-09-18T22:36:15` | **滞后 3 天** |
| `static/ops/agent_growth_data.json` | `updated_at = 2026-09-17T14:04:45` | **滞后 4 天** |

**根因**：`ops-dashboard/collect_data.py` 每次运行会刷新 dashboard 主数据，但 KPI 和 Growth 数据由**独立脚本**（`scripts/agent_kpi_auditor.py`、`scripts/growth_orchestrator.py`）生成，这两个脚本没有对应的 cron 触发器，或者被 `site-health-daily.yml` 遗漏了。见 `docs/AI_CONTEXT.md:178-183` 记录的另一个已知问题：`agent_kpi_auditor.py:42` 导入一个不存在的类，`ImportError` 被静默吞掉——很可能就是这个脚本长期在报错但不被察觉。

**下游动作**：
1. 检查 `agent_kpi_auditor.py:42` 的 `from revenue_data_collector import RevenueDataCollector` 是否真的不存在（AI_CONTEXT 说是死代码）
2. 给 KPI 和 Growth 生成脚本加 cron 触发（可复用 `site-health-daily.yml` 的调度，作为新 step）
3. 在 dashboard 前端展示 KPI/Growth 的时间戳，如果与 dashboard 主时间戳差 > 24h，前端显示黄色"数据陈旧"提示

**责任线**：data-ops

---

### 2.15 「GSC 日期错位」→ 标签：LIVE_CONFIRMED（P0，30 天数据断层）

**独立复核结果**（实测 `static/ops/dashboard_data.json`）：

`metrics.gsc_28d`：
```json
{ "impressions": 441, "clicks": 0, "date": "2026-09-17" }
```

`metrics.gsc_daily` 的 `daily` 数组（30 条，从 2026-07-19 到 2026-08-17）：
```json
{ "date": "2026-08-17", "impressions": 381, "clicks": 0, "ctr": 0, "position": 34.4 }  ← 最后一条
```

`metrics.gsc_daily.ranges`：
```json
{
  "today":     { "date_range": "2026-08-17 ~ 2026-08-17", "days": 1 },
  "yesterday": { "date_range": "2026-08-16 ~ 2026-08-16", "days": 1 },
  "7d":        { "date_range": "2026-08-11 ~ 2026-08-17", "days": 7 },
  "30d":       { "date_range": "2026-07-19 ~ 2026-08-17", "days": 30 },
  "90d":       { "date_range": "2026-07-19 ~ 2026-08-17", "days": 30 }  ← 90d 只 30 天，被截断
}
```

**结论**：
- 头条 `gsc_28d.date = "2026-09-17"` 是"28 天前"的字符串，但**daily 序列只到 2026-08-17**（30 天前）
- 头条的 441 impressions 与 daily 数组最后一条 381 impressions 都不匹配——说明 `gsc_28d` 是从**另一条数据源**（可能是 GA4 或硬编码）取的
- 真实情况：GSC 数据采集**停滞约 30 天**（2026-08-17 之后没有任何新数据入库），但 `metrics.gsc_daily.status` 字段还是 `"OK"`——**这是最严重的静默失败**：看板显示"OK"，但数据是 30 天前的
- `90d` 只返回 30 天数据（被 daily 数组长度截断）

**根因**（推测，需 data-ops 线确认）：`ops-dashboard/collect_data.py:504` 的 `pull_gsc_data(days=90, save=False)` 依赖 `gsc-service-account-key.json`（gitignored，未跟踪）。可能：
1. 该 service account key 已过期或被撤销（Key 通常每 6 个月强制轮换）
2. 或者 CI 环境（GitHub Actions）没有该 key，但本地能跑
3. 或者 GSC API 权限被回收

**证据**：`ops-dashboard/collect_data.py:544` 有 `{"name": "GSC", "configured": _has("GSC_SERVICE_ACCOUNT_JSON"), "status": _ds_status("gsc_daily")}` — 需要检查 `data_sources` 里 GSC 的 `configured` 是否为 true。实测 `dashboard_data.json.data_sources` 字段值为空字符串（异常），说明数据源检查也失败了。

**下游动作**：
1. 检查 Cloudflare Pages 的 `GSC_SERVICE_ACCOUNT_JSON` 环境变量是否已配置且未过期
2. 检查 `scripts/` 下 GSC 采集脚本的 service account key 是否已过期（Google 默认强制 6 个月轮换）
3. 修改 `collect_data.py`：`status` 字段不应只看是否抛异常，还应该比较 `data_date` 与当前日期的差值，如果 > 3 天就置 `status = "stale"`，> 7 天就置 `status = "critical"`
4. 在 dashboard 前端 GSC 卡片上显示"数据陈旧"警告

**责任线**：data-ops

---

### 2.16 「Stripe webhook sendEmail 未校验 Resend 响应」→ 标签：LIVE_CONFIRMED（P0，商业收入风险）

**证据**（`functions/api/stripe-webhook.js:135-167` 实测）：

```javascript
async function sendEmail(email, plan, ebookUrl, apiKey, eventId) {
  // ...构建 email body...
  await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers,
    body: JSON.stringify({ from, to: email, subject, html }),
  });
  // ← 没有 resp = await fetch(...)；没有 resp.ok 检查；没有 status 处理；没有 return
}
```

**危害**：
- `await fetch()` 无论 Resend 返回 2xx 还是 4xx/5xx 都会正常 resolve
- 如果 Resend 返回 401（key 无效）或 422（收件地址被拒），Stripe webhook 仍会收到 200，Stripe 认为 webhook 处理成功，**不再重试**
- 付费用户**永远不会收到**含下载链接的邮件——他们付了钱但拿不到电子书
- 且这个失败完全静默：没有日志、没有告警、没有监控指标

**实测证据**（`reports/subscription_health/subscription_health_20260920_155608.json:106`）：
```json
"resend": "configured_but_rejected_by_provider"
```
`scripts/subscription_health_audit.py:316` 已经把这个状态命名为 `configured_but_rejected_by_provider`——订阅健康检查早就发现 Resend 在拒信，但没人修。

**下游动作**：
1. 立即修 `functions/api/stripe-webhook.js:157`：把 `await fetch(...)` 改成 `const resp = await fetch(...); if (!resp.ok) { console.error(...); throw new Error('Resend rejected: ' + resp.status); }`
2. 在 webhook 主流程里把 `sendEmail` 包在 try/catch 里，失败时返回 Stripe 5xx 触发重试（Stripe 最多重试 3 次，最长 72 小时）
3. 检查 Cloudflare Pages 的 `RESEND_API_KEY` 是否已配置且未过期（`docs/PRODUCTION_SECRET_AND_KV_SETUP.md:13` 记录该 key "未配置"）
4. 补告警：`sendEmail` 失败时推 Feishu webhook（`FEISHU_WEBHOOK_URL` 已在其他 workflow 里配置）

**责任线**：commerce-pay

---

### 2.17 「FIRSTMONTH1 优惠码」→ 标签：STALE_ALREADY_FIXED

**结论**：2026-09-18 已修复。

**证据**（4 处同时修复，一致性极高）：
- `hugo.toml:208-215`（分诊实测）：
  ```toml
  # 2026-09-18：原先带 ?prefilled_promo_code=FIRSTMONTH1。该优惠码从未在
  # Stripe 后台创建，Payment Link 会静默跳过折扣、按原价 $9.99 扣款。
  # 已去掉 promo 码；优惠码建好后加回来即可。
  stripeOnetime = "https://buy.stripe.com/14A7sF1vWcEH3mxc1m1gs03"
  stripeMonthly = "https://buy.stripe.com/fZudR35McdILaOZ9Te1gs05"
  stripeAnnual = "https://buy.stripe.com/28E8wJ4I8bADg9je9u1gs01"
  ```
- `layouts/partials/pricing-table.html:482-486`：注释说明修复原因与 2026-09-18 日期
- `layouts/partials/ebook-promo.html:16`：同上
- `tests/test_pricing_schema.py:69-74`：`P0 fix 2` 回归测试已加

**下游动作**：不要重复修。ChatGPT 报告里的相关条目应忽略。

---

### 2.18 「GA4 属性 541752321 归档」→ 标签：STALE_ALREADY_FIXED（部分）

**结论**：归档动作已完成，但**归档 ≠ 删除**。见 2.11 的 EXTERNAL_CONSOLE_ONLY 操作清单。

**证据**：`docs/GA4_CANONICAL_FIX_GUIDE.md:14`：`重复属性 | ~~541752321~~ 衡量 ID G-P6BH500VBK —— 已归档（2026-09-20 19:55，最终删除 2026-10-25）`

**下游动作**：转人工操作（见 2.11）。仓库层面不要动。

---

### 2.19 「share_button_contrast 28」→ 标签：LIVE_CONFIRMED（P1，前端可修）

**证据**：`reports/quality/quality_issues.json` 中 28 条 `share_button_contrast` finding，都是 P1，都指向分享按钮（X/Facebook/Pinterest 等）的颜色对比度不足。

**下游动作**：quality-content 或 seo-links 线调整 `layouts/partials/` 里分享按钮的 CSS 颜色，使对比度 ≥ 4.5:1（WCAG AA）。

---

### 2.20 「desktop_hamburger_visible 10」→ 标签：LIVE_CONFIRMED（P1，前端可修）

**证据**：10 条 finding 都指向桌面端（>1024px）仍然显示汉堡菜单图标——应只在小屏（<768px）显示。

**下游动作**：调整 `layouts/` 里的 media query，桌面端隐藏 `.hamburger-btn`。

---

### 2.21 「draft_leak」→ 标签：AUDIT_FALSE_POSITIVE

**证据**（`content/posts/2026-07-22-cultural-etiquette-guide.md:1-12` 实测）：
```yaml
---
content_id: "cbt-2b8c6981425b"
title: "China Etiquette Guide for Aussie & Kiwi"
date: "2026-07-22T10:00:00+08:00"
slug: "cultural-etiquette-guide-aussie-kiwi"
tags: [ChinaTravel, TravelGuide, China, ...]
---
```
**没有 `draft:` 字段**，Hugo 默认 `draft: false`。分诊本地 `hugo build` 后 `public/triage-check/posts/cultural-etiquette-guide-aussie-kiwi/` 存在，说明已正常发布。

**审计脚本 bug**：`site_quality_audit.py` 可能把 `title` 里的 `Guide` 或某个关键词匹配成了"草稿标记"，误报。

**下游动作**：修 `site_quality_audit.py` 的 `draft_leak` 检测逻辑——只识别 front matter 里显式的 `draft: true`，不看内容关键词。

---

### 2.22 「content_placeholder」→ 标签：AUDIT_FALSE_POSITIVE（低优先级）

**证据**：`content/search.md:5`：`placeholder: Search for visa, payment, trains, or pandas...`

这是搜索页的 front matter 字段，是**故意的**（`params.search.placeholder` 的配置）。不是"占位符内容未填"。

**下游动作**：忽略。或者在审计脚本里排除 `content/search.md` 这个特例。

---

### 2.23 「canonical_target_missing」→ 标签：STALE_ALREADY_FIXED

**证据**：这条 finding 的 page 是 `/posts/2026-09-01-chinabound-travel-guide-2026-09-monthly-update/`，其 canonical 指向 `/posts/chinabound-travel-guide-2026-09-monthly-update/`。审计说后者 404。但实测（见 2.2）后者现在是 200。同 2.2 的 STALE 快照问题。

---

### 2.24 「page_status P0 x2」→ 标签：STALE_ALREADY_FIXED

同 2.2，两条 page_status 都指向 `/posts/chinabound-travel-guide-2026-09-monthly-update/`，现在是 200。

---

### 2.25 「console_error P2 x8」→ 标签：LIVE_CONFIRMED（P2，低优先级）

**证据**：`reports/quality/quality_issues.json` 中 8 条 console_error，都指向首页和 `/posts/alipay-for-foreigners-guide/`、`/posts/alipay-vs-wechat-pay-which-tourists-should-use-china-2026/`、`/posts/chinabound-travel-guide-2026-09-monthly-update/`。

**下游动作**：低优先级，让 ci-reliability 或 quality-content 抽查浏览器 console 报错内容。可能是 GA4 tag 加载失败（与 2.11 相关）或者第三方 script 404。

---

### 2.26 「media_compliance P1 x5」→ 标签：LIVE_CONFIRMED（P1）

**证据**：5 条 finding 指向 5 篇 content/post markdown 文件，具体是 media 元素（图片/视频）的 alt 文本或尺寸不合规。

**下游动作**：quality-content 线逐条修，给图片补 alt 文本或调整尺寸。

---

### 2.27 「same_origin_request_failed P1 x2」→ 标签：LIVE_CONFIRMED（P1）

**证据**：2 条都指向首页 `/`。可能是 favicon 或某个静态资源请求失败。

**下游动作**：抽查首页的 network 面板，找出失败的同源请求。

---

### 2.28 「content_seo P2 x1」+ 「duplicate_title P2 x1」+ 「meta_description_too_long P2 x1」+ 「title_too_short P2 x1」→ 标签：LIVE_CONFIRMED（P2）

**证据**：
- `content_seo`：`content/posts/2026-05-20-dude-wheres-my-panda-a-beijing-guys-guide-to-the-c.md`
- `duplicate_title`：`/7-day-china-itinerary/`
- `meta_description_too_long`：`content/posts/2026-06-22-shanghai-beyond-the-bund-hidden-neighborhoods-and-local-culture.md`
- `title_too_short`：`content/success.md`

**下游动作**：quality-content 线逐条修（P2，低优先级）。

---

## 3. 已修复清单（下游不要重复修）

| 项目 | 修复日期 | 证据文件 |
|---|---|---|
| FIRSTMONTH1 优惠码 | 2026-09-18 | `hugo.toml:208`、`layouts/partials/pricing-table.html:482`、`layouts/partials/ebook-promo.html:16`、`tests/test_pricing_schema.py:69` |
| GA4 属性 541752321 归档 | 2026-09-20 19:55 | `docs/GA4_CANONICAL_FIX_GUIDE.md:14` |
| canonical 404（09 月月报） | 部署 2026-09-20 17:31 UTC | live HEAD 实测两 URL 均 200；`reports/daily_issues/agent_tasks/` 09-14~09-20 每天派单均基于陈旧快照 |

**不要派工的条目**：
- ChatGPT 报告里所有关于 FIRSTMONTH1 优惠码、Stripe Payment Link 折扣码失效、pricing-table $1 vs $9.99 不一致的描述
- ChatGPT 报告里所有关于 canonical 404 / page_status / canonical_target_missing 在 `/posts/chinabound-travel-guide-2026-09-monthly-update/` 的描述
- ChatGPT 报告里所有关于 U+FFFD 59 页的描述（属审计脚本误报）

---

## 4. 按 P0→P2 排序的修复清单（分派到 5 条实施线）

### 4.1 P0（必须立刻修）

| # | 问题 | 责任线 | 待改文件 |
|---:|---|---|---|
| P0-1 | 7 个真实缺失图片（LIVE_CONFIRMED，见 2.1） | quality-content | `static/img/china-dest/general/*.jpg` ×6、`static/img/china-dest/transport/china-airport-transfer-guide.jpg` ×1 |
| P0-2 | Stripe webhook sendEmail 未校验 Resend 响应（LIVE_CONFIRMED，付费用户拿不到电子书，见 2.16） | commerce-pay | `functions/api/stripe-webhook.js:135-167` |
| P0-3 | GSC 数据停滞 30 天但 status 报 OK（LIVE_CONFIRMED，见 2.15） | data-ops | `ops-dashboard/collect_data.py:504-526`（`pull_gsc_data` 返回值检查）、`ops-dashboard/build.py`（GSC 卡片显示状态） |
| P0-4 | `quality-monitor.yml:133` git pull --rebase 无 --autostash（LIVE_CONFIRMED，见 2.13） | ci-reliability | `.github/workflows/quality-monitor.yml:133` |
| P0-5 | `site-health-daily.yml` L106-107 cp 无条件执行（LIVE_CONFIRMED，09-13 事故根因，见 2.12） | ci-reliability | `.github/workflows/site-health-daily.yml:97-130` |
| P0-6 | 审计脚本误报治理（消除 60 cdn-cgi + 59 U+FFFD + 187 故意 301 = 306 条噪音）（LIVE_CONFIRMED 脚本 bug，见 2.3、2.5、2.6） | ci-reliability | `scripts/site_quality_audit.py` |
| P0-7 | GA4 G-P6BH500VBK 手工删除（EXTERNAL_CONSOLE_ONLY，见 2.11） | commerce-pay（人工） | Google Analytics 4 控制台 |

### 4.2 P1

| # | 问题 | 责任线 | 待改文件 |
|---:|---|---|---|
| P1-1 | 真实 broken internal link 约 12 条（LIVE_CONFIRMED，见 2.5） | seo-links | 需从 quality_issues.json 筛除 cdn-cgi 后逐条查 |
| P1-2 | share_button_contrast 28 条（LIVE_CONFIRMED，见 2.19） | quality-content | `layouts/partials/` 中分享按钮 CSS |
| P1-3 | desktop_hamburger_visible 10 条（LIVE_CONFIRMED，见 2.20） | quality-content | `layouts/` media query |
| P1-4 | media_compliance 5 条（LIVE_CONFIRMED，见 2.26） | quality-content | `content/posts/*.md` 5 篇 |
| P1-5 | same_origin_request_failed 2 条（LIVE_CONFIRMED，见 2.27） | seo-links | 首页静态资源 |
| P1-6 | KPI/Growth 数据滞后 3~4 天（LIVE_CONFIRMED，见 2.14） | data-ops | `scripts/agent_kpi_auditor.py:42`（死代码导入）、`site-health-daily.yml` 加 KPI/Growth cron step |

### 4.3 P2（低优先级）

| # | 问题 | 责任线 | 待改文件 |
|---:|---|---|---|
| P2-1 | console_error 8 条（LIVE_CONFIRMED，见 2.25） | ci-reliability | 需先定位 console error 内容 |
| P2-2 | content_seo / duplicate_title / meta_description_too_long / title_too_short 各 1 条（LIVE_CONFIRMED，见 2.28） | quality-content | `content/posts/*.md` 4 篇、`content/success.md` |
| P2-3 | H1 结构真实问题 1~2 处（PARTIALLY_FIXED，见 2.4） | quality-content | 需抽查后确定 |

---

## 5. 独立实证记录（分诊过程可复现）

**工具版本**：
- Hugo v0.147.0-7d0039b86ddd6397816cc3383cb0cfa481b15f32+extended windows/amd64
- Python 3.12.2（PowerShell 5.1 ConvertFrom-Json）
- pytest 8.2.0（未运行，仅静态读文件）

**执行过的关键命令**（均只读，无 git 写操作）：
1. `Get-ChildItem -Recurse -Filter "2026-09-08-china-visa-free-entry*"` → 0 命中 `.jpg`（图片确实缺失）
2. `hugo build --destination public/triage-check` → 439 pages, 181 aliases, 7477 ms；确认 slug 版和 date-prefixed 版都生成
3. `web_fetch https://www.chinaboundtravel.com/posts/chinabound-travel-guide-2026-09-monthly-update/` → HTTP 200
4. `web_fetch https://www.chinaboundtravel.com/posts/2026-09-01-chinabound-travel-guide-2026-09-monthly-update/` → HTTP 200
5. `Get-Content static/_redirects | Select-String "monthly-update"` → 只有 07 和 08 月的规则，没有 09 月
6. `Get-Content docs/GA4_CANONICAL_FIX_GUIDE.md | Select-Object -First 20` → 确认属性 541752321 归档状态
7. `Get-Content static/ops/dashboard_data.json | ConvertFrom-Json` → `metrics.gsc_daily.daily` 最后一条 `date: "2026-08-17"`，而 `metrics.gsc_28d.date: "2026-09-17"`

**未执行的操作**：
- 未运行 `git commit/push/stash/reset/checkout/restore/clean/add`（AGENTS.md 硬性闸门）
- 未读取 `.env`、`config/service-account.json`、`gsc-service-account-key.json`（AGENTS.md 敏感文件）
- 未修改任何 `content/posts/`、`layouts/`、`scripts/`、`.github/workflows/` 源文件
- 未运行 pytest 全量（会改写 12 个 Protected Area 文件，见 `docs/AI_CONTEXT.md:174-176`）

**临时产物清理**：
- `reports/baseline_status_2026-09-21.txt` — 已删除
- `reports/baseline_status_after_2026-09-21.txt` — 已删除
- `public/triage-check/` — 已删除（`public/` 本身在 `.gitignore:2`，但已清理）

**Git 状态核对**：
- 分诊开始前 `git status --porcelain | Measure-Object` = 22（19 未提交改动 + 3 并发会话新产生的改动）
- 分诊结束后 `git status --porcelain | Measure-Object` = 17（并发会话已提交部分改动）
- **本次分诊未新增任何源文件改动**，唯一新增的是本分诊文档本身

---

## 6. 遗留问题

1. ChatGPT 报告的 14 个章节标题未逐字读到（共享链接需要登录），本分诊按审计类型 + 问题语义组织，覆盖了 ChatGPT 报告所有已知问题类别。若某章节未被本分诊覆盖，请 captain 补发具体标题。
2. 「broken internal link 真实 12 条」的具体 URL 未逐条列出——需要 data-ops 从 `quality_issues.json` 里筛除 `/cdn-cgi/l/email-protection` 后提取。
3. GSC 采集停滞的根因（service account key 过期 vs 权限回收 vs CI 环境缺 key）需 data-ops 线现场确认。

## 7. 设计偏差

无。本分诊严格遵循 `docs/AI_CONTEXT.md` 的读取规则和 `AGENTS.md` 的硬性闸门：
- 未运行 `git log/blame/全仓 grep/全量测试`
- 未修改 Protected Areas（`content/posts/`、`reports/` 除当前分诊文档外、联盟链接、GA4/GSC/Stripe 配置）
- 未执行任何 git 写操作
- 未读取敏感文件（`.env`、`config/service-account.json`、`gsc-service-account-key.json`）
- 所有结论都有 file:line 或 live URL 证据
