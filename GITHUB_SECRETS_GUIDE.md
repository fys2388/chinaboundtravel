# GitHub Secrets 配置完整指南

## 仓库信息
- **仓库**: fys2388/chinaboundtravel
- **远程地址**: git@github.com:fys2388/chinaboundtravel.git
- **分支**: main

---

## 📋 必需添加的GitHub Secrets

### 🔴 高优先级（必须添加）

| Secret名称 | 来源 | 长度/格式 | 说明 |
|-----------|------|----------|------|
| `CLOUDFLARE_API_TOKEN` | Cloudflare Dashboard → API Tokens | 40字符 | 用于部署到Cloudflare Pages |
| `CLOUDFLARE_ZONE_ID` | Cloudflare Dashboard → 域名设置 | 32字符 | 用于清除CDN缓存 |
| `FEISHU_WEBHOOK_URL` | 飞书群机器人设置 | URL格式 | 用于发送通知到飞书群 |
| `DOUBAO_ARK_API_KEY` | 豆包大模型平台 | ark-xxx格式 | AI博客生成API密钥 |
| `DEEPSEEK_API_KEY` | DeepSeek平台 | sk-xxx格式 | AI辅助写作API密钥 |
| `GA4_API_KEY` | Google Analytics | 长字符串 | Google Analytics数据查询 |
| `GA4_PROPERTY_ID` | Google Analytics | 数字(如541752321) | GA4属性ID |
| `MAILERLITE_API_TOKEN` | MailerLite账户 | eyJ格式JWT | 邮件营销API密钥 |
| `STRIPE_SECRET_KEY` | Stripe Dashboard | sk_live_xxx | 电子书支付处理 |
| `STRIPE_WEBHOOK_SECRET` | Stripe Dashboard | whsec_xxx | Stripe回调验证 |

### 🟡 中优先级（推荐添加）

| Secret名称 | 来源 | 说明 |
|-----------|------|------|
| `BUFFER_API_TOKEN` | Buffer账户 | 社交媒体管理 |
| `FACEBOOK_PAGE_ID` | Facebook开发者 | Facebook发布 |
| `FACEBOOK_PAGE_ACCESS_TOKEN` | Facebook开发者 | Facebook访问令牌 |
| `TWITTER_BEARER_TOKEN` | Twitter开发者 | Twitter API认证 |
| `LINKEDIN_ACCESS_TOKEN` | LinkedIn开发者 | LinkedIn发布 |
| `YOUTUBE_OAUTH_REFRESH_TOKEN` | Google Cloud Console | YouTube上传认证 |

### 🟢 低优先级（可选）

| Secret名称 | 来源 | 说明 |
|-----------|------|------|
| `NORDVPN_API_KEY` | TravelPayouts | VPN联盟推广 |
| `TRAVELPAYOUTS_API_TOKEN` | TravelPayouts | 联盟营销平台 |
| `GSC_SERVICE_ACCOUNT_JSON` | Google Cloud Console | Google Search Console JSON密钥 |
| `RESEND_API_KEY` | Resend平台 | 邮件发送服务 |
| `PARTNERIZE_API_KEY` | Partnerize平台 | 联盟营销 |

---

## 🚀 添加步骤

### 方法1：通过GitHub Web界面

1. 打开仓库：https://github.com/fys2388/chinaboundtravel
2. 点击 **Settings** 标签
3. 左侧菜单选择 **Secrets and variables** → **Actions**
4. 点击 **New repository secret**
5. 填写名称和值，点击 **Add secret**

### 方法2：使用GitHub CLI（推荐）

```bash
# 安装GitHub CLI（如果没有）
# https://github.com/cli/cli#installation

# 登录GitHub
gh auth login

# 添加Secrets
gh secret set CLOUDFLARE_API_TOKEN
gh secret set CLOUDFLARE_ZONE_ID
gh secret set FEISHU_WEBHOOK_URL
# ... 依次添加其他Secrets
```

---

## 🔐 获取各Secret值的方法

### 1. CLOUDFLARE_API_TOKEN
1. 登录 https://dash.cloudflare.com
2. 点击右上角头像 → **My Profile**
3. 左侧选择 **API Tokens**
4. 点击 **Create Token**
5. 使用模板 **Edit zone DNS** 或自定义
6. 复制生成的Token

### 2. CLOUDFLARE_ZONE_ID
1. 在Cloudflare Dashboard选择域名
2. 右上角可以看到 Zone ID（32位字符）
3. 或访问：Settings → General → Zone ID

### 3. FEISHU_WEBHOOK_URL
1. 打开飞书群聊 → **设置** → **群机器人**
2. 添加自定义机器人
3. 复制Webhook地址（格式：https://open.feishu.cn/open-apis/bot/v2/hook/***REMOVED***）

### 4. DOUBAO_ARK_API_KEY
1. 登录 https://console.volcengine.com/doubao
2. 左侧菜单：**API Keys**
3. 点击创建新密钥

### 5. DEEPSEEK_API_KEY
1. 登录 https://platform.deepseek.com
2. 点击右上角头像 → **API Keys**
3. 点击创建新密钥

### 6. GA4_API_KEY
1. 登录 https://analytics.google.com
2. 管理员 → 属性 → 数据访问权限 → API权限
3. 生成API密钥

### 7. GA4_PROPERTY_ID
1. 在Google Analytics → 管理员 → 属性设置
2. 复制属性ID（10位数字）

### 8. MAILERLITE_API_TOKEN
1. 登录MailerLite账户
2. 左侧菜单：**Account** → **API Keys**
3. 点击生成新密钥

### 9. STRIPE_SECRET_KEY
1. 登录 https://dashboard.stripe.com
2. 开发 → API密钥
3. 复制Secret key（sk_live_xxx）

---

## ✅ 验证配置

添加完Secrets后，运行以下命令验证：

```bash
cd E:\AI\dulizhan\travel-blog

# 测试环境变量检查
python scripts/env_check.py

# 手动触发工作流
gh workflow run env-check.yml
```

---

## 📝 当前.env文件中的Secrets列表

根据项目分析，以下Secret需要从.env迁移到GitHub：

```
✅ 必需迁移（10个）:
- CLOUDFLARE_API_TOKEN
- CLOUDFLARE_ZONE_ID
- FEISHU_WEBHOOK_URL
- DOUBAO_ARK_API_KEY
- DEEPSEEK_API_KEY
- GA4_API_KEY
- GA4_PROPERTY_ID
- MAILERLITE_API_TOKEN
- STRIPE_SECRET_KEY
- STRIPE_WEBHOOK_SECRET

⚠️  可选迁移（12个）:
- BUFFER_API_TOKEN
- FACEBOOK_PAGE_ID
- FACEBOOK_PAGE_ACCESS_TOKEN
- TWITTER_BEARER_TOKEN
- LINKEDIN_ACCESS_TOKEN
- YOUTUBE_OAUTH_REFRESH_TOKEN
- NORDVPN_API_KEY
- TRAVELPAYOUTS_API_TOKEN
- RESEND_API_KEY
- PARTNERIZE_API_KEY
- FEISHU_SECRET
- GITHUB_TOKEN
```

---

## 🔒 安全建议

1. **立即执行**
   - [ ] 将所有Secrets添加到GitHub
   - [ ] 从.env文件删除真实密钥（保留占位符）
   - [ ] 提交.gitignore更新

2. **定期维护**
   - [ ] 每季度检查Secrets有效期
   - [ ] 轮换过期的API密钥
   - [ ] 审计GitHub Actions运行日志

3. **访问控制**
   - [ ] 限制仓库访问权限
   - [ ] 启用分支保护规则
   - [ ] 要求PR审查

---

## 📞 紧急联系

如果发现密钥泄露：

1. 立即在服务商后台禁用密钥
2. 在GitHub删除泄露的Secret
3. 生成新密钥并更新
4. 检查访问日志确认影响范围
