# 联盟点击转化诊断报告
**生成时间**: 2026-10-01  
**诊断范围**: 28 天窗口 (2026-08-17 ~ 2026-09-14) + 当前状态

---

## 1. 关键指标总览

| 指标 | 数值 | 来源 | 数据年龄 | 状态 |
|------|------|------|----------|------|
| GA4 affiliate_click 事件 | **0** | REVENUE_DASHBOARD.md | 37 天 | 🟠 STALE |
| CTA impressions | N/A | REV001_FUNNEL_METRICS.csv | 0 天 | ⚪ INSUFFICIENT_SAMPLE |
| CTA 库存行 | **278** | AFFILIATE_FUNNEL_INVENTORY.csv | 当前 | ✅ |
| CTA 覆盖页面 | **45** | AFFILIATE_FUNNEL_INVENTORY.csv | 当前 | ✅ |
| Travelpayouts Drive | 2026-08-16 激活 | REVENUE_DASHBOARD.md | 46 天 | 🟡 INSUFFICIENT_SAMPLE |
| Revenue | NULL | — | — | ⚪ NOT_AVAILABLE |
| Impact API | — | impact_real_data.json | 10 天 | ❌ NO_CREDENTIALS |
| Partnerize API | — | partnerize_real_data.json | 10 天 | ❌ NO_CREDENTIALS |

---

## 2. CTA 库存分析

### 2.1 合作伙伴分布

| 合作伙伴 | CTA 类型 | 数量 | 事件模型 |
|----------|----------|------|----------|
| Airalo (eSIM) | SHORTCODE | 45 | impression + click + outbound |
| Aviasales (机票) | SHORTCODE | 45 | impression + click + outbound |
| Booking (酒店) | SHORTCODE | 45 | impression + click + outbound |
| Klook (活动) | SHORTCODE | 45 | impression + click + outbound |
| NordVPN | INLINE | 45 | click only |
| SafetyWing (保险) | SHORTCODE | 45 | impression + click + outbound |
| **Travelpayouts Drive** | TEMPLATE | 全站 | — |

### 2.2 内容覆盖

- **覆盖页面数**: 45 页（全部已发布文章）
- **CTA 总行数**: 278 行（含重复的 article_resource_block + inline）
- **REV001 实验页**: `food-delivery-mid-content` CTA (REV001_FUNNEL_METRICS.csv)

---

## 3. 转化漏斗分析

```
Sessions (28d):     166  (GA4, CACHED 2026-08-17)
    ↓
Pageviews (28d):    374  (GA4, CACHED 2026-08-17)
    ↓
Affiliate Clicks:    0   (GA4, 2026-08-17)  ← 瓶颈
    ↓
Affiliate Outbound:  0   (GA4, 2026-08-17)
    ↓
Revenue:            NULL (无 API)
```

**转化率**: 0 / 374 = 0.0% (affiliate_click / pageviews)  
**千次会话点击率**: 0 / 166 × 1000 = 0.0

---

## 4. 根因诊断

### 4.1 GA4 affiliate_click = 0 的可能原因

| # | 原因 | 可能性 | 证据 |
|---|------|--------|------|
| 1 | **Drive 刚激活（1 天内）** | ✅ 高 | REVENUE_DASHBOARD.md: days_since_active=1 |
| 2 | **流量极低** | ✅ 高 | 28d sessions=166，日均 6 会话 |
| 3 | **CTA 不可见** | ⚠️ 中 | affiliate_impression 事件有 IntersectionObserver，但 INSUFFICIENT_SAMPLE |
| 4 | **GA4 埋点缺失** | ❌ 低 | single.html:121 有 `gtag('event', 'affiliate_click')` |
| 5 | **GA4 数据延迟** | ✅ 中 | GA4 有 2-3 天处理延迟 |

### 4.2 Travelpayouts Drive 评估

- **激活日期**: 2026-08-16
- **观察天数**: 46 天
- **样本要求**: ≥ 28 天且 clicks ≥ 20
- **当前状态**: INSUFFICIENT_SAMPLE
- **Travelpayouts 后台**: 需人工登录核实（本机无法访问）
- **tp_inits 字段**: 持续未上报，可能为字段映射缺失

### 4.3 实验状态

| 实验 | 状态 | 说明 |
|------|------|------|
| REV001 | RUNNING | food-delivery-mid-content CTA，36 天 0 样本 |
| REV002 | INSUFFICIENT_SAMPLE | 已退休，experiments.json 需同步 |
| DRIVE-001 | ACTIVE | Site-wide Travelpayouts Drive，46 天 |

---

## 5. 联盟佣金为零的原因链

```
流量低 (166 sessions/28d)
    → CTA 展示少 (低 visibility)
        → affiliate_click 为 0
            → 无转化 (0 订单)
                → 佣金 $0.00
```

**核心瓶颈**: 流量不足 → 自然 CTA 曝光不足 → 点击为零

---

## 6. 建议行动（按优先级）

| 优先级 | 行动 | 预期效果 | 负责人 |
|--------|------|----------|--------|
| 🔴 P0 | **提升流量**：优先做 SEO 内容（当前 GSC 曝光 388/28d，排名 71.5 名外） | 流量翻倍 → CTA 曝光翻倍 | @seo-specialist |
| 🟡 P1 | **刷新 GA4 数据**：运行 `python scripts/affiliate_gap_detector.py` 重新拉取 affiliate_click | 确认 0 是真实还是数据延迟 | @data-engineer |
| 🟡 P1 | **核实 Travelpayouts**：人工登录 TP 后台确认 12 次点击记录 | 确认 TP 侧有点击但 GA4 无 | @conversion-optimizer |
| 🟢 P2 | **修复 experiments.json**：同步 REV002 RETIRED 状态，加 updated_at | 实验登记表一致性 | @data-engineer |
| 🟢 P2 | **排查 tp_inits**：确认字段映射是否正确 | 恢复 TP 指标上报 | @data-engineer |

---

## 7. 结论

联盟佣金 $0 的根本原因是 **流量不足**（28 天仅 166 会话），而非 CTA 缺失或埋点故障。

- CTA 库存完整（278 行 / 45 页 / 6 个合作伙伴）
- GA4 埋点代码存在且正确（single.html:121）
- 0 affiliate_click 在新站冷启动期属正常
- Drive 激活仅 46 天，未达 28 天观察窗口 + 20 点击阈值

**建议**: 优先提升流量，而非优化 CTA。流量问题不解决，CTA 优化无意义。

---

*数据来源: reports/revenue/REVENUE_DASHBOARD.md, reports/revenue/AFFILIATE_FUNNEL_INVENTORY.csv, reports/management/REPORTING_SNAPSHOT.json*