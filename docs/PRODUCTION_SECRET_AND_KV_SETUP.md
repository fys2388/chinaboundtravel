# ChinaBound Travel — Production Secret & KV Setup（配置方案，不执行修改）

> 生成日期：2026-08-13
> 状态：**方案文档**。本文档不修改任何生产配置；所有命令需人工审核后手动执行。
> 约束：不输出任何 secret 值；不使用真实值示例。

## 1. 现状（P0.7 只读审计结论）

| 项 | 现状 |
|---|---|
| Pages 项目 | `chinaboundtravel`（域名：chinaboundtravel.com / www / pages.dev）存在 |
| Pages production env vars | 仅 3 个明文 var：STRIPE_SECRET_KEY、STRIPE_WEBHOOK_SECRET、MAILERLITE_API_KEY |
| RESEND_API_KEY | **未配置** → stripe-webhook 将返回 500 |
| PROCESSED_EVENTS KV | **不存在** → Stripe 幂等 Layer-1 静默降级 |
| Buffer Worker KV | `buffer-auto-poster-BUFFER_KV_STORE`（id 与 wrangler.toml 一致）存在 |
| Buffer Worker 生产部署 | 最后部署 2026-06-30，不含 P0.6 content_id/dedup |

## 2. 目标配置（全部为加密 secret，不用明文 var）

### 2.1 Pages 加密 secrets（production environment）

| Secret 名 | 用途 | 来源 | 类型 |
|---|---|---|---|
| RESEND_API_KEY | 支付成功邮件（stripe-webhook.js） | Resend 后台 | encrypted secret |
| STRIPE_SECRET_KEY | Checkout Session 创建（checkout.js） | Stripe 后台 | encrypted secret |
| STRIPE_WEBHOOK_SECRET | Webhook 验签（stripe-webhook.js） | Stripe 后台 | encrypted secret |

操作（人工，在 Cloudflare Dashboard → Pages → chinaboundtravel → Settings → Environment variables，或 `wrangler pages secret put`）：
1. 为 production environment 添加上述 3 个加密 secret（不要使用 `wrangler.toml [vars]` 明文）。
2. 删除/替换现有同名明文 var，避免明文与 secret 冲突。
3. 重新部署（`wrangler pages deploy public --project-name chinaboundtravel --branch production` 或 GH Actions 触发）。

### 2.2 PROCESSED_EVENTS KV

用途：Stripe webhook 事件幂等 Layer-1（key `evt:{event_id}`，TTL 7 天）。

1. 创建 KV namespace：
   - `wrangler kv namespace create PROCESSED_EVENTS`
   - 记录返回的 namespace id。
2. 绑定到 Pages production environment（Dashboard → Pages → chinaboundtravel → Settings → Functions → KV namespace bindings → 添加 `PROCESSED_EVENTS` → 选择新 namespace）。
3. 验证：`wrangler kv key list --namespace-id <id>` 可用；代码 feature-detect（`env.PROCESSED_EVENTS || null`）在绑定缺失时降级，绑定后生效。

### 2.3 Buffer Worker 环境（已存在，核对）

| 变量 | 用途 |
|---|---|
| BUFFER_WORKER_URL（历史命名，实为 Buffer-A token） | FB + IG + X |
| NEW_BUFFER_WORKER_URL（历史命名，实为 Buffer-B token） | Pinterest |
| FEISHU_WEBHOOK_URL | 预警通知 |
| PINTEREST_BOARD_SERVICE_ID | Pinterest board（可选） |
| KV binding `KV_STORE` | dedup/track/retry/quota（已绑定 id 匹配） |

轮换后需用新值更新这些 secret，并重新部署 Worker（包含 P0.6 worker.js 变更）。

## 3. 部署顺序（人工执行，先 secret 后代码）

1. 轮换并写入：RESEND / Stripe（Pages encrypted secrets）+ Buffer token（Worker secrets）→ 见 docs/SECURITY_SECRET_ROTATION_CHECKLIST.md
2. 创建并绑定 PROCESSED_EVENTS KV。
3. 部署 Buffer Worker（P0.6 worker.js + dedup.mjs）。
4. 部署 Pages（当前提交后的内容）。
5. 验证。

## 4. 验证清单（全部只读/低风险）

| 检查 | 方法 | 期望 |
|---|---|---|
| Pages env | Dashboard 查看 secret 存在（不显示值） | 3 个 encrypted secret 存在 |
| KV binding | Dashboard Functions → KV bindings | PROCESSED_EVENTS 已绑定 production |
| webhook endpoint | `POST /api/stripe-webhook`（用 Stripe CLI `stripe listen --forward-to` 或本地 mock，**不调用真实支付**） | 返回 200 / HMAC 校验生效 |
| Resend | 一次受控测试邮件（可选） | 发送成功、无 401/403 |
| Stripe | checkout 创建测试 session（test mode） | 200 + session.url |
| Idempotency | 同一测试 event 投递 3 次 | 第 1 次 execute，第 2/3 次 blocked（duplicate:true） |
| Buffer | dry-run / 只读 queue 查询（不真实发布） | 200，无鉴权错误 |

## 5. 明确不做

- 本方案不执行任何生产修改；不调用真实 Stripe/Buffer/Resend API；不做真实社媒发布。