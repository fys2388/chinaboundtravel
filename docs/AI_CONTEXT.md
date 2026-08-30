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

- 本地分支：`main`
- 本地 HEAD：`698e64b` — `fix(encoding): convert GBK-encoded report + archived content files to UTF-8`（2026-08-30 实测）
- 线上状态：部署由 Cloudflare Pages 触发；线上验证 2026-08-30（首页 200 / canonical / Drive 正常）；GSC 服务账号已提 Owner，索引提交 20/20 success；勿在任务中自动 fetch/合并

## 3. Content / Reporting baseline（2.0）

- 发布文章：59 posts；content_id：59/59（扫描复核，2026-08-30）
- 单 inventory 源：`reports/seo/CONTENT_SEO_INVENTORY.csv`（60 行；`content_inventory.csv` 已废弃）
- Revenue：NULL（REVENUE_NOT_AVAILABLE，无真实收入数据前不编造）
- GA4（fetch 2026-08-17）：28d sitewide sessions 166 / pageviews 374 / affiliate_clicks 0
- GSC：缓存基线为 2026-08-16 快照（impressions/clicks 标注实际抓取日期）

## 4. Experiments（当前注册表）

| ID | 定义 | status |
|---|---|---|
| REV001 | Food Delivery（Meituan & Ele.me）· cbt-e464169c4991 · Airalo · food-delivery-mid-content | RUNNING（start 2026-08-16） |
| REV002 | Transportation Guide · cbt-17c6738ffb32 · Trip.com mid-CTA | RUNNING（frozen，review gate >= 2026-09-13） |
| REV003 | CTA_COPY variant（Transportation） | PENDING（等待 REV002 评审） |
| DRIVE-001 | Site-wide Travelpayouts Drive | RUNNING（start 2026-08-16，ACTIVE） |
| GROWTH05-CTR-001 / GROWTH07B-TECH-001 / GROWTH07C-INDEX-001 | SEO 观察 | INSUFFICIENT_SAMPLE / WAITING_RECRAWL |

- 观察窗口 >= 28 天；clicks < 20 = INSUFFICIENT_SAMPLE，禁止判定成败。
- 2026-09-13 前不得修改 REV001/REV002 CTA 文案、位置或 partner。

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

## 7. Current task

- 当前任务：2.0 工作流符合度修复（2026-08-30）
  - P0-1：`REPORTING_SNAPSHOT.json` 中文乱码已修复（源 CSV 已转 UTF-8 后重生成，issue_types 中文正常，as_of 2026-08-26 保留）
  - P0-2：weekly-blog-update cron 由每日 `0 0 * * *` 改每周 `0 0 * * 1`（落实 P1-OPS-02A）
  - P0-3：GSC 服务账号提 Owner，gsc-index-submit 20/20 success
  - 待办 P1：周/月/季/年 Feishu 报告改读 SNAPSHOT；新增 SNAPSHOT 每日自动刷新；补 `reports/2.0_REPORTING_RECONCILIATION.md`；social_distributor 收敛到 Buffer Worker
- 前序：P1-REPORT-02 统一报告（PASS，2026-08-17，SNAPSHOT 单一 KPI 源）；P1-OPS-03 2.0 就绪审计（PARTIAL_READY）
- 下一任务：待用户指派（建议：按上述 P1 待办推进，或 GROWTH-22 线上验证）## 8. Known architecture（架构速览）

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