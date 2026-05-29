# Stripe 后台配置指南
# chinaboundtravel.com 商业系统

> **操作主体**：需由账户拥有人在 Stripe Dashboard 中手动执行以下所有步骤。
> **访问地址**：https://dashboard.stripe.com

---

## 一、产品与价格创建（Product Catalog）

### 1.1 创建一次性买断产品

1. 进入 **Products** → **Add product**
2. 填写以下信息：
   - **Name**：`ChinaBound Travel Guide — One-Time Buyout`
   - **Description**：`Current edition PDF (Part 1-2). Instant download. No future updates.`
   - **Pricing**：
     - Type: `Standard pricing`
     - Amount: `1499` (即 $14.99)
     - Currency: `USD`
     - Billing period: `One-time`
3. 点击 **Save product**
4. 复制生成页面的 **Price ID**（格式：`price_xxxxxxxxxx`），填入下方配置

### 1.2 创建月度订阅产品

1. **Products** → **Add product**
2. 填写：
   - **Name**：`ChinaBound Travel — Monthly Radar`
   - **Description**：`Weekly Travel Radar + Monthly guide updates. First month $1 with coupon FIRSTMONTH1.`
   - **Pricing**：
     - Type: `Recurring pricing`
     - Amount: `999` ($9.99)
     - Currency: `USD`
     - Billing period: `Monthly`
3. 添加 **Trial**：`No trial`（首月$1优惠通过 Coupon 实现）
4. 保存，复制 **Price ID**

### 1.3 创建年度订阅产品

1. **Products** → **Add product**
2. 填写：
   - **Name**：`ChinaBound Travel — Annual Elite Pass`
   - **Description**：`Everything in Monthly + Pre-trip city guides + AI trip planner + Priority support. ~$4.17/month.`
   - **Pricing**：
     - Type: `Recurring pricing`
     - Amount: `4999` ($49.99)
     - Currency: `USD`
     - Billing period: `Yearly`
3. 保存，复制 **Price ID**

### 1.4 创建首月$1优惠码

1. 进入 **Coupons** → **Create coupon**
2. 填写：
   - **Name**：`FIRSTMONTH1`
   - **Percent or amount**：`Amount off`
   - **Amount off**：`800` (即 $8.00，首月实收 $9.99 - $8.00 = $1.99，**注意**：Stripe 不支持 $1 价格，应设为 $1.99 或调整逻辑)
   - **Currency**：`USD`
   - **Redemption options**：`1 redemption per customer`
   - **Expiration date**：不设过期
3. **替代方案**（推荐）：在月度订阅激活后，手动发放 $1 折扣给用户，或使用 Stripe Invoices 手动生成 $1 首账单

> ⚠️ **Stripe 限制**：Stripe 的 Coupon 最小金额为 $0.50。若要实现"首月$1"，建议：
> - 方案A：创建月度订阅，将首月产品设为 $1，然后再改为 $9.99（需 API 或手动）
> - 方案B：使用 Stripe Checkout 的 `subscription_data.trial_period_days: 30`（让用户30天免费试用后收费）
> - 方案C（推荐）：Checkout Session 中通过 `coupon_codes: ["FIRSTMONTH1"]` + `discounts` 实现首次结算时减免

---

## 二、Checkout Session 配置

### 2.1 创建 One-Time Checkout Session

在 Stripe Dashboard → **Checkout** → **Create a session**：

```
Mode: Payment
Product: ChinaBound Travel Guide — One-Time Buyout
Success URL: https://chinaboundtravel.com/thank-you/
Cancel URL: https://chinaboundtravel.com/pricing/
```

生成后复制 **Session URL**（`https://buy.stripe.com/...`）

### 2.2 创建 Monthly 订阅 Checkout Session

```
Mode: Subscription
Product: ChinaBound Travel — Monthly Radar
Success URL: https://chinaboundtravel.com/thank-you/
Cancel URL: https://chinaboundtravel.com/pricing/
Allow promotion codes: Yes
```

### 2.3 创建 Annual 订阅 Checkout Session

```
Mode: Subscription
Product: ChinaBound Travel — Annual Elite Pass
Success URL: https://chinaboundtravel.com/thank-you/
Cancel URL: https://chinaboundtravel.com/pricing/
Allow promotion codes: No
```

### 2.4 提取 Payment Links

每个 Session 生成后，点击 **Payment links** → **Create payment link**，生成独立 URL 填入 Hugo：

```toml
[params.ebook]
  stripeOnetime = "https://buy.stripe.com/xxx_xxxxx"
  stripeMonthly = "https://buy.stripe.com/xxx_xxxxx"
  stripeAnnual  = "https://buy.stripe.com/xxx_xxxxx"
```

---

## 三、防欺诈配置（Stripe Radar）

### 3.1 开启默认 Radar 规则

1. **Radar** → **Rules** → 确保以下默认规则开启：
   - ❌ Block payments if card is flagged as high risk
   - ❌ Block payments if card country ≠ IP country
   - ❌ Block payments with anonymous VPN/proxy

### 3.2 强制 3D Secure

**Radar** → **Rules** → **Create rule**：

```
If: Payment is from a card that requires 3D Secure authentication
And: 3D Secure is not supported or fails
Then: Block payment
```

### 3.3 强制 CVC 验证

**Radar** → **Rules** → **Create rule**：

```
If: CVC check fails
Then: Block payment
```

### 3.4 限制单卡购买频率

**Radar** → **Rules** → **Create rule**：

```
If: Customer has made 1+ purchase in the last 24 hours with this card
Then: Block payment
```

---

## 四、争议自动响应（Dispute Auto-Response）

### 4.1 开启自动提交证据

1. **Disputes** → **Settings**
2. 开启 **Automatically submit evidence for disputes**
3. 选择提交时机：`When dispute is created`

### 4.2 上传证据模板

**Disputes** → **Evidence documents** → **Upload**：

准备以下截图文件（PNG/JPG，每份 ≤ 5MB）：

| 文件名 | 内容说明 |
|--------|----------|
| `refund_policy_page.png` | `/refund-policy` 页面截图，显示"strict NO REFUND policy" |
| `pricing_checkout_page.png` | `/pricing` 页面截图，显示勾选框和条款文字 |
| `welcome_email_sample.png` | 欢迎邮件截图，显示已发送 PDF 下载链接 |
| `watermarked_pdf_sample.png` | 带用户邮箱水印的 PDF 第1页截图 |

### 4.3 默认争议回复文案

在 **Disputes** → **Responses** → **Default reply** 填入：

```
This is a digital subscription service. The customer has received access to digital content as described in our terms of service. All sales are final for digital products.

We have provided evidence that:
1. The customer agreed to our no-refund policy at checkout (checkbox confirmation on /pricing page)
2. The customer received the purchased digital content immediately after payment
3. Our refund policy is clearly stated on /refund-policy and was presented before purchase
```

---

## 五、自动续费提醒配置

### 5.1 开启续费前提醒邮件

1. **Settings** → **Customer notifications**
2. 开启 **Send emails for upcoming invoice**
3. 设置 **Days before invoice**：`7`
4. 自定义邮件模板：

```
Subject: Your ChinaBound Travel subscription renews in 7 days

Hi {{customer.name}},

Your {{product.name}} subscription will renew on {{invoice.date}} for {{invoice.amount}}.

Amount: {{invoice.amount}}
Next billing date: {{invoice.date}}

To cancel or manage your subscription: {{customer.portal_url}}

— Joran, ChinaBound Travel
```

### 5.2 客户自助管理门户

1. **Settings** → **Customer management**
2. 开启 **Customer Portal**
3. 配置允许的操作：
   - ✅ Cancel subscriptions
   - ✅ Update payment methods
   - ✅ Download invoices
   - ❌ Refunds（禁用）

---

## 六、公共信息配置

**Settings** → **Public details**：

| 字段 | 值 |
|------|-----|
| **Terms of service** | `https://chinaboundtravel.com/refund-policy` |
| **Refund policy** | `https://chinaboundtravel.com/refund-policy` |
| **Privacy policy** | `https://chinaboundtravel.com/privacy-policy/` |
| **Support email** | `support@chinaboundtravel.com` |

---

## 七、Webhook 配置（用于自动化交付）

### 7.1 创建 Webhook Endpoint

1. **Developers** → **Webhooks** → **Add endpoint**
2. **Endpoint URL**：`https://chinaboundtravel.com/api/stripe-webhook`
3. **Events to listen**：
   - ✅ `checkout.session.completed`
   - ✅ `customer.subscription.created`
   - ✅ `customer.subscription.updated`
   - ✅ `customer.subscription.deleted`
   - ✅ `invoice.payment_succeeded`
   - ✅ `invoice.payment_failed`
   - ✅ `charge.dispute.created`
4. 复制 **Signing secret**（`whsec_...`）

### 7.2 Webhook 处理逻辑（在 CF Pages Function 中实现）

```javascript
// functions/api/stripe-webhook.js
const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY);

exports.handler = async (req) => {
  const sig = req.headers['stripe-signature'];
  const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;

  let event;
  try {
    event = stripe.webhooks.constructEvent(req.body, sig, webhookSecret);
  } catch (err) {
    return { statusCode: 400, body: `Webhook Error: ${err.message}` };
  }

  switch (event.type) {
    case 'checkout.session.completed':
      // → 触发 MailerLite 发送欢迎邮件 + PDF
      // → 在 PDF 添加用户邮箱水印
      // → 记录订单到日志
      break;
    case 'customer.subscription.deleted':
      // → 更新 MailerLite 标签：active → cancelled
      // → 停止发送雷达邮件
      break;
    case 'invoice.payment_failed':
      // → 发送提醒邮件
      break;
  }

  return { statusCode: 200 };
};
```

---

## 八、关键环境变量（部署到 Cloudflare Pages）

将以下变量添加到 Cloudflare Pages Settings → Environment Variables：

| 变量名 | 说明 |
|--------|------|
| `STRIPE_SECRET_KEY` | `sk_live_...` 或 `sk_test_...` |
| `STRIPE_WEBHOOK_SECRET` | `whsec_...`（上一步获取） |
| `STRIPE_PRICE_ONETIME` | `price_...` for one-time product |
| `STRIPE_PRICE_MONTHLY` | `price_...` for monthly product |
| `STRIPE_PRICE_ANNUAL` | `price_...` for annual product |
| `MAILERLITE_API_KEY` | MailerLite API Key |
| `MAILERLITE_FORM_ID` | MailerLite Form ID for buyers |

---

## 九、测试验证清单

在 Stripe Test Mode 下完成以下测试：

- [ ] 测试卡片支付 $14.99（One-Time），验证收到确认邮件
- [ ] 测试订阅 $9.99/月（Monthly），验证首月折扣生效
- [ ] 测试订阅 $49.99/年（Annual），验证续费提醒收到
- [ ] 测试争议流程，验证自动响应证据提交
- [ ] 测试订阅取消，验证 MailerLite 标签更新
- [ ] 切换到 Live Mode，验证真实扣款

---

## 十、Stripe 账户安全建议

- 启用 **Two-factor authentication**（强制的）
- API Key 使用最小权限原则（建议 separate restricted keys）
- 定期审查 **Radar** 阻止列表
- 设置 **Bank account alerts** 异常通知
