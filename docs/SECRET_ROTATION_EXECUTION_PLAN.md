# SECRET_ROTATION_EXECUTION_PLAN — 先新后旧执行计划（仅供审核，未执行）

> 日期：2026-08-13 | 原则：先部署新值 → 验证 → 再废弃旧值。不输出任何真实值。

| # | Secret | 旧 credential | 新 credential | 更新位置 | 验证 | 废弃旧值 |
|---|---|---|---|---|---|---|
| 1 | Buffer token（Pinterest/account_a） | 历史泄漏（历史泄漏，值已脱敏） | Buffer 后台重新生成 | Cloudflare Worker secret `BUFFER_WORKER_URL`；GH Secret `BUFFER_WORKER_URL` | 只读 query（不发布）返回 200 | Buffer 后台 revoke 旧 OAuth |
| 2 | Buffer token（FB+IG+X/account_b） | 历史泄漏（历史泄漏） | Buffer 后台重新生成 | Worker secret `NEW_BUFFER_WORKER_URL`；GH Secret `NEW_BUFFER_WORKER_URL` | 同上 | 后台 revoke |
| 3 | Buffer token（config fallback） | 历史泄漏（根 commit 明文） | 已删除 fallback；只保留环境变量 | 环境变量 `BUFFER_ACCESS_TOKEN`（新值） | `python -c` 读 env 成功且非空 | 废弃旧值 |
| 4 | Stripe webhook secret | 历史 .env（whsec，值已脱敏） | Stripe 后台 roll webhook secret | Pages encrypted secret `STRIPE_WEBHOOK_SECRET` | 测试 event 验签通过 | Stripe 后台确认旧值失效 |
| 5 | Stripe secret key | 历史仅占位符；本地 .env 为测试态 | 若生产曾用 live key 则换新 | Pages encrypted secret `STRIPE_SECRET_KEY` | test mode checkout 200 | 后台 revoke |
| 6 | Feishu webhook URL | 历史 .env/脚本/文档 | 飞书后台重置 webhook | GH Secret `FEISHU_WEBHOOK_URL`；Worker/Pages 环境 | 发送测试消息成功 | 旧 URL 失效（飞书重置即失效） |
| 7 | Resend API key | 本地 .env（gitignored） | Resend 后台新 key | Pages encrypted secret `RESEND_API_KEY` | 测试邮件发送成功 | 后台 revoke 旧 key |
| 8 | 其他历史 credential（若确认入库） | 审计未发现其他真实值入库（仅占位符） | — | — | — | 按需 |

## 执行顺序约束
1. 每项严格「先新后旧」：先写入新值并验证引用方可用，再 revoke 旧值。
2. 轮换与历史重写相互独立、都必须做（重写无法撤销已泄露值）。
3. 全部完成后复跑 `pytest tests/` 与一次只读集成检查。