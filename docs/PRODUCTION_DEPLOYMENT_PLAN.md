# PRODUCTION_DEPLOYMENT_PLAN — 生产部署计划（仅供审核，未执行）

> 日期：2026-08-13 | 状态：PLAN ONLY，不执行任何部署

| Phase | 内容 | 关键动作 | 完成标准 |
|---|---|---|---|
| 1 | Git history recovery | 重写演练已通过（2dcb595，0 泄漏）；待人工授权后 force-with-lease 推送 | origin/main = 重写后 main；远程 secret 扫描 0 |
| 2 | Secret rotation | 按 SECRET_ROTATION_EXECUTION_PLAN 先新后旧 | 全部新值生效、旧值 revoke |
| 3 | Cloudflare Pages configuration | RESEND_API_KEY / STRIPE_SECRET_KEY / STRIPE_WEBHOOK_SECRET 改为 encrypted secret；删除明文 var | 3 个 encrypted secret 存在；明文 var 移除 |
| 4 | PROCESSED_EVENTS KV | `wrangler kv namespace create` + Pages production binding | KV 存在；binding 名 `PROCESSED_EVENTS` 生效 |
| 5 | Buffer Worker deployment | 部署含 P0.6 的 worker.js + dedup.mjs（含 KV binding） | deployments 列表出现新版本；dedup/track 逻辑上线 |
| 6 | Pages deployment | 部署当前 main（Hugo build 后） | Pages 生产版本 = 当前 main；www 200 |
| 7 | Production smoke test | 按 PRODUCTION_SMOKE_TEST_PLAN 执行（不含真实发布） | 全部 A–L 通过 |
| 8 | Post-deployment audit | 复跑 P0.7 全量审计 | P0 blocker 清空；评分达标 |

## 当前缺口（Phase 3/4 前置）
- Pages production：RESEND_API_KEY 缺失；STRIPE×2/MAILERLITE 为明文 var；无 encrypted secret
- PROCESSED_EVENTS KV：不存在、无 binding
- Buffer Worker：生产部署停留在 2026-06-30，P0.6 未上线