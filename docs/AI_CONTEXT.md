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
- 本地 HEAD：`247e686` — `fix: correct monthly promo prefill url parameter`（2026-08-17 实测）
- 线上状态：部署由 Cloudflare Pages 触发；最新已记录的线上验证为 2026-08-16（GROWTH-05/07/BRAND-03）；勿在任务中自动 fetch/合并

## 3. Content / Reporting baseline（2.0）

- 发布文章：60 posts；content_id：60/60（`content_id_audit.py audit --strict` = PASS，2026-08-17）
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

- P1-REPORT-01：ChinaBound 2.0 Reporting Rebuild — **PASS**（2026-08-17）
  - REV001 报告冲突已修复（144h/Booking 旧定义已清除）
  - 报告引擎已按 60-post inventory 重跑：brand legacy / SEO opportunity / revenue / commercial conversion
  - 验证：pytest 595 passed（0 failed / 0 skipped）；content_id 60/60 PASS；`hugo --gc --minify` SUCCESS
  - 提交：`chore: reconcile ChinaBound 2.0 reporting baselines`（已 push origin/main）
- 下一任务：待用户指派（建议：GROWTH-22 线上验证，或按 `reports/seo/TOP_10_CONTENT_PRIORITIES.md` 执行下一批内容优化）

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
- 搜索：仅限任务相关目录；勿全仓扫描