# AI_CONTEXT.md — 轻量项目上下文（Codex 专用）

> 用途：让 Codex 在不扫描整个仓库的情况下快速了解本项目。
> 规则：每轮任务开始，先只读本文件 + 任务相关文件。禁止全仓扫描。
> 维护：每次涉及品牌/架构/部署/报告基线变更后更新本文件。保持 ≤ 200 行。

## 0. 读取规则（最高优先级）

- 先读本文件，再读任务明确列出的文件。不要读整个仓库。
- 禁止：`git log` / `git blame` / 全仓 `grep` / 遍历 `reports/`、`ai_drafts/`、`logs/`、`node_modules/`、`public/`、`public_verify/`、`.git/`、`.wrangler/`、`__pycache__/`。
- 禁止运行全量测试（pytest 全套 / Hugo 全量构建），除非任务明确要求。
- 禁止修改 Protected Areas（见第 5 节）。
- 除非任务明确要求，禁止 commit / push / deploy。

## 1. Project

- 名称：ChinaBound Travel（chinaboundtravel.com）
- 类型：面向外国游客的中国旅行指南静态博客（英语）
- 技术栈：Hugo（Extended，PaperMod 主题）+ 自定义 layouts 覆盖；Cloudflare Pages 部署
- 根目录：`E:\AI\dulizhan\travel-blog`
- baseURL：`https://www.chinaboundtravel.com/`
- 语言：`en-us`；内容零修改区域见第 5 节

## 2. Current branch / commit

- 本地分支 `main`；本地 HEAD 以 `git pull --rebase` 后的 `git log -1` 为准，
  **不要写死 hash**（机器人每 30 分钟提交，写死即过期）。
- **接手第一件事：`git pull --rebase`。** 要看线上真实代码用 `git show origin/main:<path>`，
  不要相信本地 checkout 的旧内容（随时落后数百个提交）。
- 线上状态：push main → `deploy-cloudflare-pages.yml` → Hugo → Cloudflare Pages，约 1-2 分钟生效。
- 工作区纪律见 `AGENTS.md`；看板专题见 `docs/OPS_DASHBOARD_HANDOVER.md`。

## 3. Content / Reporting baseline（2.0）

- 发布文章：**63 posts，content_id 63/63**（`scripts/content_id_audit.py audit --strict` → PASS，09-18 实测）。
  **别用 glob 数文章数**：glob 到 79 个 .md，但 `.archived/`（6）与 `.audit_backup/`（8）是点号目录
  被 Hugo 跳过，另有 3 个 draft。以审计脚本为唯一口径。
- 单 inventory 源：`reports/seo/CONTENT_SEO_INVENTORY.csv`；`content_inventory.csv` 已废弃
- Revenue：NULL（REVENUE_NOT_AVAILABLE，无真实收入数据前不编造）
- GA4（2026-09-17 单日）：11 sessions / 14 pageviews / bounce 100% / engagement 0% / avg 167s；
  7 日滚动（09-11~17）：41 sessions / 55 pageviews / engagement 38.2% / avg 119s
- GSC：28d 窗口有曝光（234 次）。昨日单日 0 多为 GSC 2-3 天数据延迟，**不作业务结论**

## 4. Experiments（当前注册表）

| ID | 定义 | status |
|---|---|---|
| REV001 | Food Delivery（Meituan & Ele.me）· cbt-e464169c4991 · Airalo · food-delivery-mid-content | RUNNING（start 2026-08-16） |
| REV002 | Transportation Guide · cbt-17c6738ffb32 · Trip.com mid-CTA | INSUFFICIENT_SAMPLE（gate 09-13 已过，样本仍不足） |
| REV003 | CTA_COPY variant（Transportation） | PENDING（等待 REV002 评审） |
| DRIVE-001 | Site-wide Travelpayouts Drive | RUNNING（start 2026-08-16，ACTIVE） |
| GROWTH05-CTR-001 / GROWTH07B-TECH-001 / GROWTH07C-INDEX-001 | SEO 观察 | INSUFFICIENT_SAMPLE / WAITING_RECRAWL |

- 观察窗口 >= 28 天；clicks < 20 = INSUFFICIENT_SAMPLE，禁止判定成败。
- 09-13 的 CTA 冻结期已过（现 09-18）；约束是**样本量而非日期**，日报 gate 已按实际观察天数动态生成。

## 5. Brand definition（品牌定义）

- 站点名：ChinaBound Travel；编辑人格：Joran（Editorial Voice，唯一人格，无 legacy persona）
- 主色：`#3A6EA5`（蓝）／`#2d5a8a`（深蓝）；金色 `#FFD700`/`#DAA520`；宝塔红 `#E74C3C`
- 当前主标识引用：`static/images/favicon/favicon.svg`（模板引用未变：hugo.toml / head.html / header.html / site.webmanifest / schema_json.html）
- P1-BRAND-04 状态（2026-08-17）：**LOGO_REPLACEMENT_READY** — 新品牌 PNG 已复制为 `static/images/favicon/favicon.png`；仓库内无可用的确定性 PNG→SVG 转换工具，favicon.svg 与全部引用路径保持不变（未检查/未重绘 logo 图源）
- 当前头像：`static/images/joran-avatar.webp`（256×256）+ `.png`（1024×1024 fallback）
- 社交缺省图：`static/images/og-default.jpg`（1200×630）、`static/images/twitter-default.jpg`（1200×600）

## 6. Protected areas（禁止触碰，除非任务明确授权）

- `content/posts/`（全部文章，零修改）
- URL / slug / canonical / content_id
- 联盟链接 / affiliate URL / UTM 参数 / Travelpayouts Drive
- GA4（`G-GECBME3YVJ`）／ GSC／ Stripe／ Buffer／ n8n
- `reports/`（除当前任务指定的审计报告）
- 密钥类文件（`.env*`、`*-secrets*`、service-account key）

- 历史闭环（细节在各自交接文档，接手不必重读）：P1-OPS-01 考核数据发布（09-17，run 35231157737）；
  运营看板回退事故（09-16，`docs/OPS_DASHBOARD_HANDOVER.md`）；2.0 工作流符合度（08-30：
  P0-1 SNAPSHOT 乱码 / P0-2 weekly-blog-update 改每周 / P0-3 GSC 提 Owner）；
  P1-REPORT-02 统一报告（08-17）；P1-OPS-03 就绪审计（PARTIAL_READY）。
- 待办 P1：周/月/季/年 Feishu 报告改读 SNAPSHOT；SNAPSHOT 每日自动刷新；
  补 `reports/2.0_REPORTING_RECONCILIATION.md`；social_distributor 收敛到 Buffer Worker。

## 8. Known architecture（架构速览）

- 渲染：`layouts/`（自定义）覆盖 `themes/PaperMod/`（勿改主题源）
- 静态：`static/` 原样发布；`assets/` 走 Hugo 资源管道（`resources.Get`）
- 脚本：`scripts/`（SEO/审计/商化引擎）、`auto-script/`、`deprecated_scripts/`（勿用）
- 辅助模块：`buffer-worker/`（Wrangler）、`chinaboundtravel_social_bot/`、`api/`、`functions/`、`n8n/`、`video-pipeline/`
- 测试：`tests/`（pytest）；关键回归：`test_brand_identity_p2.py`、`test_avatar_webp.py`、`test_mobile_touch.py`、`test_growth12_revenue_experiment.py`
- 性能：`static/_headers` 对 `/images/*` 设 `max-age=31536000, immutable`
- 部署：`auto-deploy.ps1` / `deploy*.ps1` / Cloudflare Pages（生产由 CI 触发）

## 9. 常用命令（仅任务需要时执行）

- 本地构建：`hugo`（Hugo Extended，见 `.hugo.version`）
- 单测：`python -m pytest tests/test_xxx.py -q`（禁止无授权全量跑）
- content_id 审计：`python scripts/content_id_audit.py audit --strict`
- 实验评审：`python scripts/revenue_experiment_review.py --as-of YYYY-MM-DD`
- KPI 快照：`python scripts/reporting_kpi_engine.py --as-of YYYY-MM-DD`
- 管理报告：`python scripts/reporting_engine.py --all --master --alerts --as-of YYYY-MM-DD`
- 搜索：仅限任务相关目录；勿全仓扫描

## 10. 运营看板（`/ops-dashboard/` · `/ops/ops-center`）

- **`ops-dashboard/ops-center.html` 是手工维护文件，任何自动化都不得写入它。**
  09-13 的 `3a92c477` 曾让 `build.py` 写它，导致每 30 分钟把统一运营中心刷成精简监控页。
  现已修复：build.py 只写 `index.html`，hourly workflow 只 `cp` 源目录 → static。
- **`static/_redirects` 绝不能加 `/ops/ops-center` 这条规则。** Cloudflare 会把
  `/ops/ops-center.html` 308 到 `/ops/ops-center`，两条规则首尾相接成死循环（浏览器报超过 5 次重定向）。
  规则目标写无扩展名 `/ops/ops-center`；规则必须精确匹配（不带 `*`），否则 `/ops/*.json` 数据请求被吞。
- 统一中心依赖 4 个绝对路径：`/ops/dashboard_data.json`、`/ops/agent_kpi_data.json`、
  `/ops/agent_growth_data.json`、`./js/echarts.min.js`。echarts 源文件只在 `ops-dashboard/js/`，
  必须 `cp` 到 `static/ops/js/`，否则所有图表 404。
- 详细留档、恢复/丢失对照、遗留待办：`docs/OPS_DASHBOARD_HANDOVER.md`

## 11. 自动化并发纪律（本仓库特有）

- main 上有 8 个提交身份：`fys2388`、`GitHub Action`、`github-actions[bot]`、`AI Agent Orchestrator`、
  `Closed Loop Agent`、`chinabound-bot`、`Joran`、`SenseNova Agent`。
- `ops-dashboard-hourly.yml`（cron `*/30 1-18 * * *` UTC，即北京时间 09:00-02:00）与
  `site-health-daily.yml` **都会写同一批 static 文件并都跑 build.py**。
- 因此 **push 被拒是正常的**（2026-09-16 一小时内被拒 2 次）。流程固定为：
  改动 → 本地验证 → commit（pathspec 限定）→ `git pull --rebase` → push。
  冲突高发文件：`static/ops/ops-center.html`、`ops-dashboard/ops-center.html`、`static/**/index.html`。
- `site-health-daily.yml` 第 108 行是 `git add -A`（全量），会把工作区任何残留文件一起提交；
  `ops-dashboard-hourly.yml` 用白名单。提交前 `git status` 必须干净。
- `continue-on-error: true` 会吞掉 step 失败（job conclusion 仍为 success），
  `retry-failed.yml` 按 `conclusion == 'failure'` 触发因而永不重跑。
  关键 step 后须加门：`if: steps.x.outcome == 'failure'` + `run: exit 1`。
- 敏感文件不可读/不可提交：`.env`、`config/service-account.json`、`gsc-service-account-key.json`。
- **这三份密钥全部 gitignore 且未跟踪（现状正确，勿改为提交），代价是全新 clone 里没有它们。**
  全新 clone / 换机器 / 干净 CI 沙箱中不存在 → 所有 GA4 / GSC 采集与索引提交直接失效。
  线上 workflow 走 GitHub Actions secrets；本地脚本走本机这三份文件。
  缺失时先问用户，**不要创建占位文件或伪造内容**。

## 12. 环境陷阱（Windows / PowerShell，本项目实测）

- PowerShell `>` 重定向产生 **UTF-16**（带 BOM）。`git show ... > file` 写出的 JSON/HTML 会损坏，
  之后 `json.load` 报 `UnicodeDecodeError`。用 Python `subprocess.run(...).stdout` 写 bytes。
- pwsh `-c` 内联 Python：引号会被 PowerShell 拆坏，SyntaxError 信息还显示成乱码。
  **超过一行的 Python 一律写成 .py 文件再运行。**
- `Get-Content` / `ConvertFrom-Json` 对中文 UTF-8 会乱码。用
  `[IO.File]::ReadAllText(path, [Text.Encoding]::UTF8)` 或 python。
- `git commit -m ... -- <path>` 的 pathspec **看不见 untracked 文件**；新文件要先 `git add`。
- `git diff` 的 `CRLF will be replaced by LF` 警告无害。
- `web_search` 工具在本环境不可用（缺 API key）；用 `web_fetch` 直接打 GitHub API（仓库是公开的）。

## 13. 已知测试失败（2026-09-17 全量实测：716 passed / 28 failed）

**先说结论：这 28 个都不是同一种东西，别当成一个"预存失败"包。**

- **20 个是 `content/` 保护区断言**（`test_avatar_webp`×4、`test_brand_identity_p2`、
  `test_brand_legacy_pilot`、`test_growth05`×2、`test_growth07`×2、`test_growth12`×2、
  `test_growth12a`、`test_growth18`×2、`test_growth19`×2、`test_growth22`×3）。
  都是标题 / H2 / front-matter / 联盟链接 / cover image 的具体文案断言，
  修了就要动 `content/posts/`，需单独授权。
- **2 个是报告状态依赖**（`test_growth20_monetization`×2）：断言
  `reports/revenue/REV002_FINAL_REVIEW.md` 的 gate 字段，而 pytest 每次运行都会
  重写该文件（见下条），所以结果跟着本机文件时间戳漂移。
- **2 个是社媒库存**（`test_social_content_agent`×2：100 items / 20 sources 数量断言）。
- **4 个是测试自身的问题**（2026-09-17 已修 3 个，commit `a988c8ed`）：
  - `test_no_hardcoded_secrets` — **误报**：`lh-desktop-0830.json` 内嵌 base64 图片字节
    偶然拼出 `AIza…`。已加 blob 豁免 + 2 个负向对照测试防止豁免过头。
  - `test_robots` — **误报**：旧断言跨组收集所有 `Disallow: /`。生产 robots.txt 按 GEO
    策略在「AI 训练爬虫」组拦 GPTBot/ClaudeBot/Google-Extended/CCBot，通用爬虫 `Allow: /`
    （线上实测）。已改为只判 `User-agent: *` 兜底组，并新增 `test_ai_training_bots_remain_blocked`
    保护 GEO 策略不被误删。
  - `test_meta_description::test_generator_padding_no_longer_loops` — **陈旧哨兵**：生成器已重构为
    「按预算追加一次即 break」（155 字符上限），旧断言 grep 已不存在的原始句。已改断真实不变量。
  - `test_secret_name_contract` — **真违规，已修**。`gh secret list` 证实 secrets 里只有官方名
    `CLOUDFLARE_API_TOKEN` / `CLOUDFLARE_ZONE_ID`，**从来没有过** `CF_API_TOKEN`，故旧代码在 CI 里
    `check_config()["cloudflare"]` 恒 `False`（别名映射只在本机 `.env` 碰巧生效）。已统一改官方名，
    并同步 `.env.revenue.template`（写明旧短别名要改名）。

**⚠️ pytest 有写副作用（实测）**：跑全量 `pytest tests` 会改写 `reports/revenue/*`、
`reports/seo/*`（重新生成，日期戳变当天）与 `static/lead-magnet/*.pdf`，共 12 个
Protected Area 文件。提交前必须 `git status` 核对，**只 add 本任务文件**。

**⚠️ KPI 考核的营收接入是死代码**
`agent_kpi_auditor.py:42` 写 `from revenue_data_collector import RevenueDataCollector`，
但那个模块（383 行）只有函数（`load_env`/`check_config`/`collect_all`/...），**没有这个类**。
`ImportError` 被 try/except 静默吞掉 → `REVENUE_COLLECTOR_AVAILABLE=False`
→ `load_real_revenue_data()` 恒返回 `{}` → **KPI 月度考核从未接入真实营收，一直用默认基础分**。
修需设计（接哪个 `collect_*`、字段映射），属单独任务。
`STRIPE_SECRET_KEY` 在 GitHub secrets 里也不存在（key 在 Cloudflare Pages env），
stripe 恒 `false`（本地与 CI 一致）。

**环境性（网络相关，非代码问题）**：`tests/test_report_03.py::test_zero_revenue_never_converted_to_zero_dollar`
— Travelpayouts `ProxyError`，本机有代理时失败、无代理时通过。

**纪律**：修任何一项前先看 `docs/OPS_DASHBOARD_HANDOVER.md` 与保护区清单；
不要用 stash / reset / `--autostash` 清掉上述 pytest 产生的改动来"骗过"验证。

## 14. 支付与营收（勿再误判）

- `/api/checkout` **前端零调用方**（`git grep` 验证）→ `400 No such coupon`。**别排查"支付挂了"**。
- 定价页走 **Stripe Payment Links**（`hugo.toml:176-178` + `pricing-table.html:681-683`/`:712`），三条均 HTTP 200。
- 唯一问题：`prefilled_promo_code=FIRSTMONTH1` 无效（码未创建），文案「$1」与实价 $9.99 不符；结账可完成。
  `checkout.js` 已加折扣码 fail-open。详见 `docs/stripe-configuration-guide.md` §1.4。
