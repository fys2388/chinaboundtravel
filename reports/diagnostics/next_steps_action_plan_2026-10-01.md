# 下一步行动清单 — ChinaBound Travel
**生成时间**: 2026-10-01

---

## 本轮已完成 ✅

| 任务 | 状态 | 成果 |
|------|------|------|
| SNAPSHOT 流量数据修正 | ✅ | sessions 166→364, pageviews 374→654 |
| SNAPSHOT 日期刷新 | ✅ | as_of → 2026-10-01 |
| GSC source_age 修正 | ✅ | age 3→11 天, stale_sources 6→4 |
| Q4 OKR 调整 | ✅ | content target 20→40 |
| 联盟转化诊断 | ✅ | 报告: reports/diagnostics/affiliate_conversion_diagnostic_2026-10-01.md |
| 订阅 CTA 审计 | ✅ | 报告: reports/diagnostics/subscription_lead_magnet_audit_2026-10-01.md |
| 根因分析 | ✅ | 报告: reports/diagnostics/root_cause_analysis_2026-10-01.md |
| **CTA 覆盖率** | ✅ | **6.3% → 100% (63/63 篇)** |
| internal_traffic_filter 验证 | ✅ | 已被 feishu_daily_report.py + real_data_bridge.py 调用 |
| 健康检查域名验证 | ✅ | DEFAULT_BASE_URL 已正确为 www.chinaboundtravel.com |

---

## 待执行行动清单

### 🔴 P0 — 本周必须完成

| # | 行动 | 操作 | 预计耗时 | 负责方 |
|---|------|------|----------|--------|
| 1 | **运行 GSC 索引提交** | `python scripts/gsc_index_submit.py` | 5 分钟 | Captain 手动或 GitHub Actions |
| 2 | **配置 Travelpayouts 提现** | 登录 travelpayouts.com → Withdrawal Settings | 10 分钟 | 人工（需账号密码） |
| 3 | **验证 CTA 部署** | 构建 Hugo 站点 + 部署到 Cloudflare Pages | 10 分钟 | `hugo build && git push` |

### 🟡 P1 — 两周内完成

| # | 行动 | 操作 | 预计耗时 | 负责方 |
|---|------|------|----------|--------|
| 4 | **刷新 GSC 收录数据** | 登录 GSC UI 查看最新收录率，更新 INDEX_COVERAGE_BASELINE.md | 15 分钟 | 人工 |
| 5 | **排查 89 页未收录原因** | GSC → Indexing → Pages 查看具体排除原因 | 30 分钟 | 人工 |
| 6 | **配置 GA4 IP 排除** | GA4 Admin → Data Streams → Configuration Settings → Internal Traffic | 15 分钟 | 人工（需团队 IP） |
| 7 | **增加内部链接密度** | 在高权重页添加向低权重页的互链 | 2 小时 | 内容编辑 |
| 8 | **SEO 内容优化** | 选择 5 篇排名 50-80 的文章做关键词优化 | 4 小时 | 内容编辑 |

### 🟢 P2 — 一个月内完成

| # | 行动 | 操作 | 预计耗时 | 负责方 |
|---|------|------|----------|--------|
| 9 | **申请 Impact/Partnerize 凭证** | 注册 Impact.com + Partnerize，获取 API key | 30 分钟 | 人工 |
| 10 | **排查 tp_inits 字段** | 检查 Travelpayouts API 字段映射 | 1 小时 | 开发 |
| 11 | **Trip.com 程序申请准备** | 等待 3 个月稳定流量后提交审核 | — | 人工（时间门槛） |
| 12 | **GTM 容器清理** | 找到 GTM 容器所有者，删除 G-P6BH500VBK destination | 30 分钟 | 人工（需联系持有人） |
| 13 | **订阅健康检查 CI 集成** | 将 subscription_health_audit.py 加入 GitHub Actions 定时任务 | 30 分钟 | 开发 |

---

## 预期效果

### 短期（1 周）

| 指标 | 当前 | 预期 | 变化 |
|------|------|------|------|
| CTA 覆盖率 | 6.3% | **100%** | +93.7pp |
| GSC 收录率 | 44% (69/158) | **60%+** (95+/158) | +16pp |
| 联盟佣金 | $0 | **$0**（需提现配置 + 流量） | 不变 |
| 订阅增长 | 0/月 | **5-15/月**（CTA 覆盖后自然增长） | 首次增长 |

### 中期（1 个月）

| 指标 | 当前 | 预期 | 变化 |
|------|------|------|------|
| GSC 平均排名 | 71.5 | **50-60** | 提升 11-21 位 |
| GSC 点击 (28d) | 0 | **5-15** | 首次点击 |
| 日均会话 | ~6 | **10-20** | 2-3x |
| affiliate_click | 0 | **1-5/天** | 首次点击 |

### 长期（3 个月）

| 指标 | 当前 | 预期 | 变化 |
|------|------|------|------|
| 月会话 | ~180 | **500-1000** | 3-5x |
| 联盟佣金 | $0 | **$10-50/月** | 首次收入 |
| 订阅者 | ~1 | **50-100** | 50-100x |
| GSC 收录率 | 44% | **80%+** | +36pp |

---

## 阻塞项（需要人工操作）

| 阻塞项 | 原因 | 解决方案 |
|--------|------|----------|
| GTM 双目的地 | 容器不在当前 Google 账号下 | 联系容器所有者或 Google Support |
| Travelpayouts 提现 | 余额 $0，需配置提现方式 | 登录后台操作 |
| Trip.com 程序 | "25 programs unavailable" | 等 3 个月稳定流量 |
| GA4 IP 排除 | 需获取团队 IP 段 | 收集开发/办公 IP |

---

## 立即执行命令

```bash
# 1. 构建站点并部署
cd E:\AI\dulizhan\travel-blog
hugo build
git add -A
git commit -m "feat: add lead-magnet-cta to all articles, update SNAPSHOT and diagnostics"
git push

# 2. 提交未收录页面到 GSC
python scripts/gsc_index_submit.py

# 3. 运行订阅健康检查
python scripts/subscription_health_audit.py --base-url https://www.chinaboundtravel.com

# 4. 刷新 GA4 数据
python scripts/real_data_pull_engine.py
```

---

*下一步优先级: 构建部署 → GSC 索引提交 → Travelpayouts 提现配置*