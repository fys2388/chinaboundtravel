# MailerLite 自动化配置指南
# chinaboundtravel.com 邮件营销与内容交付系统

> **操作主体**：需由账户拥有人在 MailerLite Dashboard 中手动执行以下所有步骤。
> **访问地址**：https://www.mailerlite.com/login

---

## 一、账户基础配置

### 1.1 获取 API Key

1. **Settings** → **API Keys** → **Create API key**
2. 命名：`chinaboundtravel-automation`
3. 复制 Key（格式：`eyJ0eXAi...`）
4. 将 Key 填入 Cloudflare Pages Environment Variable：
   - **Variable name**：`MAILERLITE_API_KEY`
   - **Value**：`eyJ0eXAi...`

### 1.2 创建订阅者字段（Custom Fields）

**Settings** → **Fields** → **Add field**：

| Field Key | Field Name | Field Type | Example |
|-----------|-----------|------------|---------|
| `subscription_type` | Subscription Type | Text | `one-time`, `monthly`, `annual` |
| `order_number` | Order Number | Text | `ORD-2026-XXXXX` |
| `order_date` | Order Date | Date | `2026-05-23` |
| `trip_date` | Trip Date | Date | `2026-07-15` |
| `pdf_version` | PDF Version | Text | `2026.05` |

---

## 二、自动化工作流（Automation Workflows）

### 2.1 购买成功触发 → 欢迎序列（立即发送）

**Workflows** → **Create workflow** → **Start from scratch**

**Trigger**：`API`（通过 Stripe Webhook 触发）
或 **Trigger**：`Customer purchases a product`（如果有 Stripe + MailerLite 集成）

**步骤1：发送欢迎邮件**
- **Delay**：Immediate
- **Action**：Send email
- **Email subject**：`📘 Your ChinaBound Travel Guide is ready — here's how to use it`
- **Email body**：

```
Hi {{ subscriber.name | default:"Traveler" }},

You're in. Welcome to ChinaBound Travel.

Your order #{{ order_number }} is confirmed.

📎 ATTACHMENT: ChinaBound Travel Guide 2026.05 (Part 1-2)
This PDF covers:
  - Visa & passport essentials
  - Airport arrival guide
  - Internet & SIM card setup
  - Payment basics (Alipay/WeChat)

---
WHAT'S NEXT:

📅 Every Friday: You'll receive your Weekly Travel Radar
   — Real-time scam alerts, crowd updates, and route changes

📆 7 days before your trip: We'll send your complete
   city-by-city attraction guide based on your travel dates

Questions? Reply to this email anytime.
— Joran
Chengdu, China
```

**步骤2：标记订阅类型**
- **Action**：Update subscriber field
- `subscription_type` = `{{ checkout.subscription_type }}`（one-time / monthly / annual）

**步骤3：设置用户标签**
- **Action**：Add tag
- 对应标签：`one-time-buyer` 或 `monthly-subscriber` 或 `annual-subscriber`

---

### 2.2 出发前7天 → 完整城市攻略发送

**Workflows** → **Create workflow** → **Start from scratch**

**Trigger**：`Subscriber matches conditions`
- Condition：`trip_date` is 7 days from now

**步骤1：发送完整PDF**
- **Action**：Send email
- **Subject**：`🗺️ Your Pre-Trip China Guide — city routes, exact times, and what to skip`
- **Email body**：

```
Hi {{ subscriber.name | default:"Traveler" }},

Your China trip is almost here! Here's your complete guide.

📎 ATTACHMENT: ChinaBound Travel Guide 2026.05 — FULL EDITION
  Including:
  - City-by-city attraction guides (Beijing, Shanghai, Xian, Chengdu)
  - Exact public transport routes & subway instructions
  - Restaurant recommendations Joran personally tested
  - Shopping spots & how to haggle without being rude

⚠️ CHECK YOUR TRIP DATE: {{ trip_date }}
If you need to update your travel dates, reply to this email.

Still haven't booked your eSIM or VPN?
→ eSIM: https://www.airalo.com/promo/38j3e4
→ VPN: https://www.expressrefer.com/refer-friend?referrer_data[handle]=fys2388&handle=join_referral

Safe travels,
— Joran
```

---

### 2.3 每周五 → 旅行雷达（Travel Radar）

**Workflows** → **Create workflow** → **Recurring schedule**

**Schedule**：`Every Friday at 09:00 AM`（用户本地时间或 UTC）

**Audience filter**：
- Tag is one of：`monthly-subscriber`, `annual-subscriber`
- Subscription status：`active`

**Action**：Send email

**Email template — Weekly Radar**：

```
Subject：`📡 China Travel Radar — [City] | Week of [Date]`

---
Hi {{ subscriber.name | default:"Traveler" }},

Here's your weekly China travel update.

🔴 ALERT: [Any urgent visa or policy changes this week]
🟡 UPDATE: [Crowd conditions at major attractions]
🟢 ON THE GROUND: [Joran's local tip for this week]

[City of the Week spotlight]

This week I'm covering: [e.g. "Why the Forbidden City is a trap on weekends — and the secret Tuesday hack"]

That's it for this week. See you next Friday.

— Joran
Chinaboundtravel.com

---
Unsubscribe | Manage preferences | View online
```

---

### 2.4 续费前7天 → 续费提醒

**Workflows** → **Create workflow** → **Recurring schedule**

**Schedule**：`Every day at 08:00 AM`（检查次日续费的订阅）

**Audience filter**：
- Tag is：`annual-subscriber`
- Subscription field `subscription_renewal_date` is tomorrow

**Action**：Send email

**Email template**：

```
Subject：`⚠️ Your ChinaBound subscription renews tomorrow`

Hi {{ subscriber.name }},

Just a heads up — your Annual Elite Pass renews tomorrow.

Renewal date: {{ subscription_renewal_date }}
Amount: $49.99

✅ Your perks continue:
  - Weekly Travel Radar every Friday
  - Monthly guide PDF updates
  - Pre-trip city guides 7 days before your next trip

❌ Don't want to renew?
Cancel here: {{ subscriber.cancel_url }}
(No questions asked, no pressure)

— Joran, ChinaBound Travel
```

---

## 三、邮件模板规范

### 3.1 发件人信息

| 设置项 | 值 |
|--------|-----|
| **From Name** | Joran @ ChinaBound |
| **From Email** | hello@chinaboundtravel.com |
| **Reply-To** | support@chinaboundtravel.com |

### 3.2 品牌视觉风格

- **主色**：`#FF6B35`（活力橙）
- **字体**：Inter, -apple-system, sans-serif
- **Logo**：https://chinaboundtravel.com/images/joran-avatar.png
- **Footer**：
  ```
  ChinaBound Travel · hello@chinaboundtravel.com
  成都，中国 · chinaboundtravel.com

  You received this email because you purchased a ChinaBound Travel subscription.
  {{ unsubscribe_url }} | {{ manage_preferences_url }}
  ```

### 3.3 GDPR 合规退订按钮

在每个邮件模板 Footer 添加：

```
<a href="{{ unsubscribe_url }}" style="color:#888;font-size:12px;text-decoration:underline;">
  Unsubscribe from all emails
</a>
```

MailerLite 会自动在所有邮件底部注入 GDPR 退订链接。

---

## 四、用户标签管理（Tags & Segments）

### 4.1 标签体系

| Tag | 创建时机 | 含义 |
|-----|---------|------|
| `one-time-buyer` | One-Time 购买成功 | 一次性用户，不发送雷达邮件 |
| `monthly-subscriber` | Monthly 订阅成功 | 月度订阅用户 |
| `annual-subscriber` | Annual 订阅成功 | 年度精英用户 |
| `active` | 订阅有效期内 | 可发送付费内容 |
| `expired` | 订阅过期 | 停止发送付费内容 |
| `cancelled` | 用户主动取消 | 移出发送列表 |

### 4.2 订阅者状态管理（自动化规则）

**规则1：订阅成功**
```
IF Stripe Webhook: subscription.created
THEN:
  - Add tag: [monthly-subscriber OR annual-subscriber]
  - Add tag: active
  - Set field: subscription_type = [对应值]
  - Set field: order_date = today
```

**规则2：订阅取消**
```
IF Stripe Webhook: subscription.deleted
THEN:
  - Remove tag: active
  - Add tag: expired
  - Update field: subscription_end_date = today
```

**规则3：续费失败**
```
IF Stripe Webhook: invoice.payment_failed
THEN:
  - Add tag: payment-failed
  - Send email: Payment failed reminder
```

---

## 五、Stripe → MailerLite 集成

### 5.1 通过 Zapier 集成（推荐，无需代码）

**Zap 1: Stripe 购买 → MailerLite 订阅者创建**

```
Trigger: Stripe → Checkout Session Completed
Filter: session.payment_status = "paid"
Action: MailerLite → Create/update subscriber
  - email: session.customer_email
  - name: session.customer_details.name
  - subscription_type: session.metadata.subscription_type
  - order_number: session.metadata.order_id
```

**Zap 2: Stripe 订阅取消 → MailerLite 标签更新**

```
Trigger: Stripe → Customer Subscription Deleted
Action: MailerLite → Update subscriber
  - Remove tag: active, [monthly OR annual]-subscriber
  - Add tag: expired
```

### 5.2 通过 Cloudflare Pages Function（无 Zapier）

当 Stripe Webhook 收到 `checkout.session.completed`：

```javascript
// functions/api/stripe-webhook.js
const mailerlite = require('@mailerlite/mailerlite-nodejs')(
  process.env.MAILERLITE_API_KEY
);

async function handlePurchase(session) {
  const subscriber = {
    email: session.customer_email,
    fields: {
      subscription_type: session.metadata.subscription_type,
      order_number: session.metadata.order_id,
      order_date: new Date().toISOString().split('T')[0],
    }
  };

  // Create or update subscriber
  await mailerlite.subscribers.createOrUpdate(subscriber);

  // Add tags
  const tagMap = {
    'one-time': 'one-time-buyer',
    'monthly': 'monthly-subscriber',
    'annual': 'annual-subscriber'
  };
  const tag = tagMap[session.metadata.subscription_type];
  if (tag) {
    await mailerlite.subscribers.setTags(session.customer_email, [tag, 'active']);
  }

  // Trigger welcome automation
  // (MailerLite的automation由其内部的workflow trigger处理)
}
```

---

## 六、测试验证清单

- [ ] 触发一次测试购买，验证欢迎邮件立即发送
- [ ] 检查欢迎邮件附件（PDF）是否带用户邮箱水印
- [ ] 验证标签 `one-time-buyer` / `monthly-subscriber` / `annual-subscriber` 正确添加
- [ ] 手动设置 `trip_date = today + 7 days`，验证出发前邮件触发
- [ ] 向 `monthly-subscriber` + `active` 标签用户发送测试雷达邮件
- [ ] 触发订阅取消，验证标签从 `active` → `expired` 正确更新
- [ ] 验证退订链接功能正常（退订后不再收到邮件）
