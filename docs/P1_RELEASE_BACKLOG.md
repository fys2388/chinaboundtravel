# ChinaBound Travel — P1 Release Backlog

> 生成日期：2026-08-13
> 用途：记录 P0.7 审计发现的 P1/P2 遗留项。**当前只记录，不修改代码。**
> 归属：Codex 可修复项（经批准后执行）与人工项分开标记。

## P1 项

| # | 项 | 位置 | 问题 | 修复方向 | 归属 |
|---|---|---|---|---|---|
| 1 | robots.txt 缺失 | `static/`（无源文件） | 站点无 robots.txt，SEO 基础文件缺失 | 新增 `static/robots.txt`（允许爬取 + sitemap 引用） | Codex |
| 2 | hugo.toml 旧人格 | `hugo.toml`（site params） | `title: "Hi, I'm Joran"`、`subtitle: "A California native married into a Chengdu family…5 years…"` 仍为旧 Joran 传记 | 替换为 ChinaBound Travel 品牌/编辑型表述 | Codex |
| 3 | Medium 模板旧人格 | `chinaboundtravel_social_bot/content/templates/medium_templates.md`（3 处） | “California native…Chengdu son-in-law / married into a Chengdu family” | 改为编辑型模板（需确认 Medium 平台处理时机） | Codex（待平台排期） |
| 4 | Reddit 模板旧人格 | `chinaboundtravel_social_bot/content/templates/reddit_templates.md`（2 处） | 虚构第一人称（“my wife…”“going to Chengdu for 10 years”） | 改为问题导向/编辑型模板 | Codex |
| 5 | checkout.js 缺 Idempotency-Key | `functions/api/checkout.js` | 创建 Checkout Session 未带 Stripe `Idempotency-Key`，重复 POST 可能重复建 session | 生成确定性 key（如 `checkout-{session_id?}` 或客户端 token）并加 header | Codex |
| 6 | Stripe secrets 为明文 var | Cloudflare Pages production env | STRIPE_SECRET_KEY / STRIPE_WEBHOOK_SECRET / MAILERLITE_API_KEY 是明文 var | 迁移为 encrypted secret（见 PRODUCTION_SECRET_AND_KV_SETUP.md） | 人工 |
| 7 | Worker env 命名误导 | `buffer-worker/worker.js` | `BUFFER_WORKER_URL` / `NEW_BUFFER_WORKER_URL` 实际存 token | 更名（如 BUFFER_TOKEN_A/B）并同步 Cloudflare + GH Secrets | Codex+人工 |
| 8 | 无 rollback 机制 | 全仓库 | 社媒发布/Worker 无回滚方案 | 定义发布回滚流程（KV tracking + 人工删除待发队列） | Codex |
| 9 | retry-failed 权限 | `.github/workflows/retry-failed.yml` | 未声明 `permissions: actions: write`，`gh workflow run` 可能失败 | 增加 permissions 或改用 workflow_dispatch 重触发 | Codex |
| 10 | booking affiliate URL | `config/affiliate_data.json` + 渲染 | 链接形如 `www.booking.com/index.html?aid=…`（`/index.html` 冗余） | 核对 Partnerize/Booking 规范后修正 | Codex+人工 |
| 11 | video-pipeline credentials | `video-pipeline/.env`（gitignored） | 含 DeepSeek/Doubao 等第三方 key（未入库） | 按策略轮换；确认永不入库 | 人工 |

## P2 项（记录，低优先）

| # | 项 | 说明 |
|---|---|---|
| 1 | NUL 文件 | 仓库根存在未跟踪 `NUL`（Windows 重定向产物），建议删除 |
| 2 | .bak / backup / archive | `social_publisher.py.bak`、`backup/`、`archive/` 等含旧版本内容，建议清理或归档并加入 .gitignore |
| 3 | 根 .env 管理 | gitignored，含 26 个真实 key；确保永不入库，定期轮换 |
| 4 | 41 篇历史文章旧人格 | 已确认暂缓批量修改（用户决策），后续单独阶段处理 |
| 5 | `test_dual_buffer_workflow.py`（根目录未跟踪） | 干扰根目录 `pytest -q`（capture 错误），不删除，建议迁入 tests/ 或归档 |

## 处理原则

- 本文档只记录；任何修改需在独立阶段经你批准后执行。
- 修复后需复跑：pytest tests/、Hugo build、persona guard、content_id audit、affiliate regression。