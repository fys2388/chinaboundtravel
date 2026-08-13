# ChinaBound Travel — Secret Rotation Checklist

> 生成日期：2026-08-13
> 依据：P0 Security Recovery 历史泄漏审计（SECRET_TYPE | REF | COMMIT | FILE | STATUS）
> 原则：**任何进入过 Git history 的真实 credential → MUST ROTATE。**
> 本文档只记录 secret 类型与处理状态，**不包含任何 secret 值**。

## 审计结论速览

| 泄漏类型 | 影响的 refs | 当前 tip 状态 |
|---|---|---|
| Buffer OAuth token ×3 | main（本地历史）、origin/main、origin/trae/* ×3 | 本地 main tip 已 CLEAN（b9cc09b1）；origin/main 与 trae tip 仍 LEAKED |
| Stripe webhook secret | origin/main、origin/trae/* ×3（历史 .env） | 历史 LEAKED；origin/main tip 未跟踪 .env；trae tip 仍含 .env |
| Feishu webhook URL/secret | origin/main、origin/trae/* ×3（.env 与脚本/文档） | 历史 LEAKED |
| 根 .env（本地磁盘） | 未入库（gitignored） | 磁盘存在真实值，含与历史同值 whsec |

## Rotation Checklist

| # | Secret | Where exposed | Must rotate? | Rotation owner | New storage location | Old secret revoke status | Verification status |
|---|---|---|---|---|---|---|---|
| 1 | Buffer token（Pinterest / account_a） | Git history（main、origin/main、trae ×3）；origin/main 与 trae tip 仍明文 | **YES** | 账号所有者（fys2388） | Cloudflare Worker secret `BUFFER_WORKER_URL` / GitHub Actions secret `BUFFER_WORKER_URL` | 未撤销（生成新 token 后撤销旧值） | 待执行 |
| 2 | Buffer token（FB+IG+X / account_b） | Git history（main、origin/main、trae ×3）；origin/main 与 trae tip 仍明文 | **YES** | 账号所有者（fys2388） | Cloudflare Worker secret `NEW_BUFFER_WORKER_URL` / GitHub Actions secret `NEW_BUFFER_WORKER_URL` | 未撤销 | 待执行 |
| 3 | Buffer token（config fallback） | Git history（main 根 commit、origin/main、trae ×3） | **YES** | 账号所有者 | 不再使用 fallback；仅环境变量 `BUFFER_ACCESS_TOKEN` | 未撤销 | 待执行 |
| 4 | Stripe webhook secret | Git history（origin/main、trae ×3 的 .env）；根 .env（本地磁盘，与历史同值） | **YES** | 站长（Stripe 后台） | Cloudflare Pages 加密 secret `STRIPE_WEBHOOK_SECRET` | 未撤销 | 待执行 |
| 5 | Stripe secret key（live key 前缀） | 历史仅发现占位符（setup-secrets.ps1 全 x）；根 .env 中的 STRIPE_SECRET_KEY 为测试态格式（非 live 前缀） | **VERIFY**（若生产曾用 live key 则 YES） | 站长 | Cloudflare Pages 加密 secret `STRIPE_SECRET_KEY` | 未撤销 | 待核验是否曾为 live key |
| 6 | Feishu webhook URL | Git history（origin/main、trae ×3：.env、deprecated_scripts/*、CONFIGURATION_GUIDE.md、full-chain-test.ps1、run-generator.ps1 等） | **YES** | 站长（飞书后台重置 webhook） | GitHub Actions secret `FEISHU_WEBHOOK_URL` / Cloudflare 环境 | 未撤销 | 待执行 |
| 7 | Feishu secret（签名校验） | 根 .env（本地磁盘，gitignored） | **YES**（若曾入库则必轮换） | 站长 | GitHub Actions secret `FEISHU_SECRET` | 未撤销 | 待核验历史是否入库 |
| 8 | Resend API key（Resend 前缀） | 根 .env（本地磁盘，gitignored）；**Pages 生产未配置** | **YES**（策略：凡进入过历史即轮换；当前未见历史入库记录，但必须修复生产配置） | 站长 | Cloudflare Pages 加密 secret `RESEND_API_KEY` | 未撤销 | Pages 生产缺失 → 待配置 |
| 9 | 根 .env 第三方 credentials（DeepSeek / Doubao / MailerLite / GA4 / GSC / NordVPN / Partnerize / Travelpayouts 等） | 根 .env（本地磁盘，gitignored，未入库） | **POLICY**（未发现历史入库则保留，但建议定期轮换） | 站长 | 各平台后台 + GitHub Actions / Cloudflare Secrets | 未撤销 | 确认无 git 入库记录 |
| 10 | video-pipeline 第三方 key（.env，gitignored） | video-pipeline/.env（本地磁盘，未入库） | **POLICY** | 站长 | 环境变量 / GitHub Actions Secrets | 未撤销 | 确认无 git 入库记录 |
| 11 | GitHub/Cloudflare OAuth（wrangler 本地配置） | 本机 `~/.wrangler/config/default.toml`（未入库） | 否（本地凭据） | 站长 | 本机凭据管理器 | — | 本地存在 |

## 通用轮换流程（每项适用）

1. 在对应平台后台生成新 credential（Buffer / Stripe / Feishu / Resend）。
2. 先把新值写入目标存储（Cloudflare Pages encrypted secret / Worker secret / GitHub Actions secret），确认引用方生效。
3. 再撤销旧值（Buffer OAuth、Stripe webhook、Feishu webhook、Resend key 均支持轮换/重置）。
4. 复跑 `pytest tests/` + 一次只读集成检查，确认无 401/403。
5. 更新本表状态为「已轮换 / 已撤销 / 已验证」。

## 强制顺序

- **先部署新 secret，再撤销旧 secret**（避免停机）。
- **历史重写（rewrite_sensitive_history.sh）与 secret 轮换相互独立**：重写不能撤销已泄露值，轮换是唯一兜底，两者都必须做。
- 未完成轮换前，不得把重写后的历史推送上线（防止旧值在新历史中仍可用时被误用）。