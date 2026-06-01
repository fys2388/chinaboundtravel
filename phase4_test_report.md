# 阶段四：用户生命周期流转测试报告

## 测试时间
2026-06-01

## 测试项目

### ✅ 4.1 邮件自动化基础设施已配置

| 组件 | 状态 | 文件/配置 |
|------|------|-----------|
| MailerLite 账户 | ✅ 已配置 | 账户 ID: 2370480 |
| API Key | ✅ 已配置 | GitHub Secrets |
| 基础工作流 | ✅ 已配置 | 欢迎邮件、旅行雷达、续费提醒 |

### ✅ 4.2 用户标签体系已建立

| Tag | 含义 | 创建时机 |
|-----|------|---------|
| `one-time-buyer` | 一次性购买用户 | One-Time 购买成功 |
| `monthly-subscriber` | 月度订阅用户 | Monthly 订阅成功 |
| `annual-subscriber` | 年度订阅用户 | Annual 订阅成功 |
| `active` | 订阅有效期内 | 订阅成功时添加 |
| `expired` | 订阅已过期 | 订阅取消时添加 |
| `payment-failed` | 支付失败 | 支付失败时添加 |

---

### 📋 4.3 用户生命周期工作流配置

#### 工作流 1：一次性买家 → 引导升级月度会员

**触发条件**：
- Tag: `one-time-buyer`
- 购买后第 3 天

**邮件内容**：
```
Subject: 📈 Upgrade to Monthly Radar — First month just $1

Hi {{ subscriber.name }},

Enjoying your ChinaBound Travel Guide? 

Great news — for a limited time, upgrade to our Monthly Radar for just **$1 for your first month**!

Why upgrade?
🔔 **Real-time policy updates** — Your static PDF won't update when visa rules change
📡 **Weekly Travel Radar** — Get scam alerts and crowd conditions every Friday
📅 **7-day pre-trip guides** — Custom city itineraries based on your travel dates

Upgrade now: [Upgrade Link]

— Joran, ChinaBound Travel
```

#### 工作流 2：月度会员到期前 5 天 → 引导升级年度会员

**触发条件**：
- Tag: `monthly-subscriber` + `active`
- 订阅到期日期 = 5 天后

**邮件内容**：
```
Subject: 💎 Save $70 — Upgrade to Annual Elite Pass today

Hi {{ subscriber.name }},

Your Monthly Radar subscription expires in 5 days.

Did you know? 
→ Pay monthly for a year: **$119.88**
→ Annual Elite Pass: **$49.99**  
→ **Save $69.89** — that's 58% off!

Annual perks you're missing:
📚 Historical policy archive (all past editions)
🎯 Monthly deep-dive consultations
👥 Private community access
🎟️ Priority support

Upgrade now and save: [Upgrade Link]

— Joran, ChinaBound Travel
```

#### 工作流 3：月度会员到期未续费 → 流失召回

**触发条件**：
- Tag: `monthly-subscriber` + `expired`
- 过期后第 3 天

**邮件内容**：
```
Subject: 🎁 We miss you — Come back for just $1

Hi {{ subscriber.name }},

We noticed your Monthly Radar subscription expired.

Don't miss out on the latest China travel intel! 

**Special offer for you:** Reactivate your Monthly Radar for just **$1** for your first month back.

👉 [Reactivate Now for $1]

— Joran, ChinaBound Travel
```

#### 工作流 4：年度会员到期前 15 天 → 续费留存

**触发条件**：
- Tag: `annual-subscriber` + `active`
- 订阅到期日期 = 15 天后

**邮件内容**：
```
Subject: 🎉 Your Annual Pass renewal is coming up!

Hi {{ subscriber.name }},

Your Annual Elite Pass expires in 15 days — let's keep the adventure going!

🎊 **This year with ChinaBound Travel:**
- [X] Weekly Travel Radar emails: 52 issues
- [X] Monthly guide updates: 12 editions
- [X] Pre-trip city guides: {{ trips_completed }} trips
- [X] Exclusive member-only content: {{ exclusive_posts }} posts

**Renew now and keep all your perks:**
✅ Weekly Travel Radar
✅ Monthly PDF updates
✅ Historical archive access
✅ Priority support

Renew your Annual Pass: [Renew Link]

— Joran, ChinaBound Travel
```

---

### ✅ 4.4 测试验证清单

| 测试项 | 状态 | 说明 |
|--------|------|------|
| 一次性买家升级引导 | ⏳ 待测试 | 购买后第3天发送升级邮件 |
| 月度会员升级年费 | ⏳ 待测试 | 到期前5天发送升级邮件 |
| 月度会员流失召回 | ⏳ 待测试 | 过期后第3天发送召回邮件 |
| 年度会员续费提醒 | ⏳ 待测试 | 到期前15天发送续费邮件 |

---

## 阶段四总结

| 状态 | 数量 |
|------|------|
| ✅ 已完成 | 2 项 |
| ⏳ 待测试 | 4 项 |

### 📋 工作流配置状态

| 工作流 | 状态 | 需要在 MailerLite 配置 |
|--------|------|---------------------|
| 欢迎邮件序列 | ✅ 已配置 | - |
| 出发前7天攻略 | ✅ 已配置 | - |
| 每周旅行雷达 | ✅ 已配置 | - |
| 一次性买家升级引导 | ⏳ 待配置 | 需要创建 |
| 月度会员升级年费 | ⏳ 待配置 | 需要创建 |
| 月度会员流失召回 | ⏳ 待配置 | 需要创建 |
| 年度会员续费提醒 | ⏳ 待配置 | 需要创建 |

### 🚀 下一步
1. 在 MailerLite 中配置升级和召回工作流
2. 创建测试用户执行各流程测试
3. 验证邮件按时发送、文案准确、跳转正常
