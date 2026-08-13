# PRODUCTION_SMOKE_TEST_PLAN — 生产冒烟测试计划（仅供审核，未执行真实发布）

> 日期：2026-08-13 | 本计划描述测试方法；执行前需人工授权，且不进行真实社媒发布/真实支付。

| # | 项 | 方法 | 期望 | 类型 |
|---|---|---|---|---|
| A | Website 200 | `curl -I https://www.chinaboundtravel.com/` | HTTP 200 | 只读 |
| B | non-www → www 301 | `curl -I https://chinaboundtravel.com/` | 301 → www | 只读 |
| C | sitemap | `curl https://www.chinaboundtravel.com/sitemap.xml` | 200 + 365 URLs | 只读 |
| D | canonical | 抽样文章页含 `rel=canonical` 指向 www URL | 匹配 | 只读 |
| E | Stripe webhook signature | Stripe CLI `stripe listen` 转发测试事件 | HMAC 校验通过（200） | 测试事件，非真实支付 |
| F | duplicate webhook | 同一测试 event 投递 3 次 | 第 1 次 execute；第 2/3 次 blocked(duplicate:true) | 测试事件 |
| G | Buffer Worker health | `GET {worker}/health`（若存在）或只读 queue 查询 | 200，无鉴权错误 | 只读 |
| H | Buffer dedup | 同 content_id+account+platform+variant 提交 dry-run | 第 2 次 skipped | 需 dry-run 支持，否则待发布后 |
| I | content_id propagation | 构造 payload 含 content_id，检查 KV track 记录 | track 记录存在 | 发布后 |
| J | tracking | 查 `track:*` KV 记录字段（content_id/platform/account/scheduled_at/source_workflow/post_url） | 字段完整 | 发布后 |
| K | GitHub Actions | 手动触发一次 deploy（workflow_dispatch） | 绿 | 人工 |
| L | social scheduling | 只读查询 Buffer queue（不创建真实帖子） | 无报错 | 只读 |

## 执行顺序
1. A–D（网站/SEO）随时可做。
2. E–F（Stripe）在 Phase 3/4（RESEND + KV）完成后做。
3. G–J（Buffer）在 Phase 5（Worker 部署）后做。
4. K–L 最后（Phase 6–7）。

## 红线
- 任何涉及真实发布/真实支付的项都不得执行；L 仅只读查询队列。