# ChinaBound Travel 自动化系统配置教程

---

## 📋 目录

1. [必需配置](#-必需配置)
   - [飞书机器人配置](#11-飞书机器人配置)
   - [DeepSeek API 配置](#12-deepseek-api-配置)

2. [可选配置](#-可选配置)
   - [Cloudflare API 配置](#21-cloudflare-api-配置)
   - [Google Search Console 配置](#22-google-search-console-配置)
   - [Booking.com API 配置](#23-bookingcom-api-配置)
   - [Agoda API 配置](#24-agoda-api-配置)
   - [飞书签名密钥](#25-飞书签名密钥)

3. [配置验证](#-配置验证)

4. [故障排除](#-故障排除)

---

## ✅ 必需配置

### 1.1 飞书机器人配置

**步骤 1**: 创建飞书机器人
1. 打开飞书 → 进入目标群聊 → 点击右上角「...」
2. 选择「群设置」→「群机器人」→「添加机器人」
3. 选择「自定义机器人」
4. 输入机器人名称（如：ChinaBound Travel Bot）
5. 复制 **Webhook 地址**

**步骤 2**: 在 GitHub Secrets 配置
1. 访问 GitHub 仓库 → Settings → Secrets and variables → Actions
2. 点击「New repository secret」
3. Name: `FEISHU_WEBHOOK_URL`
4. Value: 粘贴飞书 Webhook 地址

**示例 Webhook**:
```
https://open.feishu.cn/open-apis/bot/v2/hook/***REMOVED***_FEISHU_WEBHOOK_ID
```

---

### 1.2 DeepSeek API 配置

**步骤 1**: 获取 API Key
1. 访问 [DeepSeek AI Platform](https://platform.deepseek.com/)
2. 注册/登录账号
3. 进入「控制台」→「API Keys」
4. 点击「Create New Key」
5. 复制生成的 API Key

**步骤 2**: 在 GitHub Secrets 配置
- Name: `DEEPSEEK_API_KEY`
- Value: 粘贴 DeepSeek API Key

---

## 🚀 可选配置

### 2.1 Cloudflare API 配置

**步骤 1**: 创建 API Token
1. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. 点击右上角头像 →「My Profile」→「API Tokens」
3. 点击「Create Token」
4. 选择「Analytics Read」模板（或自定义权限）
5. 确保勾选以下权限：
   - Zone → Analytics → Read
6. 点击「Continue to summary」→「Create Token」
7. 复制生成的 Token

**步骤 2**: 获取 Zone ID
1. 进入您的域名管理页面
2. 右侧「Overview」→ 找到「Zone ID」
3. 复制 Zone ID

**步骤 3**: 在 GitHub Secrets 配置
- Name: `CLOUDFLARE_API_TOKEN`
- Value: Cloudflare API Token

- Name: `CLOUDFLARE_ZONE_ID`
- Value: Cloudflare Zone ID

---

### 2.2 Google Search Console 配置

> ⚠️ GSC API 需要 OAuth2 认证，API Key 方式功能受限！

**步骤 1**: 创建 Google Cloud 项目
1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 创建新项目（如：ChinaBound Travel Analytics）
3. 在搜索框输入「Search Console API」
4. 点击「Google Search Console API」→「Enable」

**步骤 2**: 创建服务账号
1. 进入「IAM & Admin」→「Service Accounts」
2. 点击「Create Service Account」
3. 输入服务账号名称和描述
4. 点击「Create and Continue」
5. 分配角色（可选，至少需要 Viewer 权限）
6. 点击「Done」

**步骤 3**: 创建密钥
1. 在服务账号列表中找到刚创建的账号
2. 点击进入 →「Keys」→「Add Key」→「Create new key」
3. 选择「JSON」格式 →「Create」
4. JSON 密钥文件会自动下载

**步骤 4**: 在 Search Console 授权
1. 访问 [Google Search Console](https://search.google.com/search-console/)
2. 选择您的网站
3. 点击「Settings」→「Users and permissions」
4. 点击「Add user」
5. 输入服务账号的邮箱（格式：`xxx@xxx.iam.gserviceaccount.com`）
6. 授予「Owner」权限

**步骤 5**: 在 GitHub Secrets 配置
1. 打开下载的 JSON 密钥文件
2. 复制整个 JSON 内容
3. 在 GitHub Secrets 中创建：
   - Name: `GSC_SERVICE_ACCOUNT`
   - Value: 粘贴完整的 JSON 内容

---

### 2.3 Booking.com API 配置

**步骤 1**: 注册联盟账号
1. 访问 [Booking.com Partner Program](https://partner.booking.com/)
2. 注册并申请成为联盟会员
3. 等待审核通过

**步骤 2**: 获取 API Key
1. 登录联盟后台
2. 找到「API Settings」或「Developer」页面
3. 创建新的 API Key

**步骤 3**: 在 GitHub Secrets 配置
- Name: `BOOKING_API_KEY`
- Value: Booking.com API Key

---

### 2.4 Agoda API 配置

**步骤 1**: 注册联盟账号
1. 访问 [Agoda Affiliate Program](https://www.agoda.com/affiliates/)
2. 注册并申请成为联盟会员
3. 等待审核通过

**步骤 2**: 获取 API Key
1. 登录联盟后台
2. 找到「API」或「Integration」页面
3. 创建新的 API Key

**步骤 3**: 在 GitHub Secrets 配置
- Name: `AGODA_API_KEY`
- Value: Agoda API Key

---

### 2.5 飞书签名密钥

**步骤 1**: 获取签名密钥
1. 在飞书机器人配置页面
2. 开启「签名校验」选项
3. 系统会生成一个 Secret
4. 复制 Secret

**步骤 2**: 在 GitHub Secrets 配置
- Name: `FEISHU_SECRET`
- Value: 飞书签名密钥

---

## 🧪 配置验证

### 测试飞书推送
```bash
# 本地测试
python test_feishu_push.py --webhook "您的飞书Webhook地址"

# 或设置环境变量后测试
set FEISHU_WEBHOOK_URL=您的飞书Webhook地址
python test_feishu_push.py
```

### 测试 API 连接
```bash
# 测试 Cloudflare API
set CLOUDFLARE_API_TOKEN=您的Token
set CLOUDFLARE_ZONE_ID=您的ZoneID
python test_apis.py --test-cf

# 测试 GSC API（需要配置服务账号）
set GSC_SERVICE_ACCOUNT=您的JSON密钥
python test_apis.py --test-gsc
```

### 完整配置检查
```bash
python check_config.py
```

---

## 🔧 故障排除

### 问题 1: 日报未收到

**可能原因**:
- GitHub Actions 定时任务延迟（正常现象）
- Secrets 配置错误
- 飞书 Webhook 地址错误

**解决方法**:
1. 检查 GitHub Actions 运行日志
2. 验证 Secrets 名称是否正确
3. 手动测试飞书推送

### 问题 2: Cloudflare 数据为空

**可能原因**:
- API Token 权限不足
- Zone ID 错误
- 数据延迟

**解决方法**:
1. 确认 Token 有 Analytics Read 权限
2. 验证 Zone ID 是否正确
3. 等待 24 小时后重试

### 问题 3: GSC 数据为空

**可能原因**:
- 使用了错误的认证方式（API Key）
- 服务账号未授权
- JSON 密钥格式错误

**解决方法**:
1. 使用服务账号方式（推荐）
2. 确认服务账号已在 Search Console 中授权
3. 验证 JSON 密钥格式正确

---

## 📊 配置状态参考

| 配置项 | GitHub Secret | 优先级 | 状态 |
|--------|--------------|--------|------|
| 飞书 Webhook | `FEISHU_WEBHOOK_URL` | ⭐⭐⭐ | ✅ |
| DeepSeek API | `DEEPSEEK_API_KEY` | ⭐⭐⭐ | ✅ |
| Cloudflare Token | `CLOUDFLARE_API_TOKEN` | ⭐⭐ | ✅ |
| Cloudflare Zone ID | `CLOUDFLARE_ZONE_ID` | ⭐⭐ | ✅ |
| GSC Service Account | `GSC_SERVICE_ACCOUNT` | ⭐⭐ | ⚠️ |
| Booking API | `BOOKING_API_KEY` | ⭐ | ⚠️ |
| Agoda API | `AGODA_API_KEY` | ⭐ | ⚠️ |
| 飞书 Secret | `FEISHU_SECRET` | ⭐ | ⚠️ |

---

## 📝 配置清单

```
必需配置 (已完成):
├─ FEISHU_WEBHOOK_URL ✅
└─ DEEPSEEK_API_KEY ✅

可选配置 (待完成):
├─ GSC_SERVICE_ACCOUNT ⚠️ 需要配置
├─ BOOKING_API_KEY ⚠️ 需要配置
├─ AGODA_API_KEY ⚠️ 需要配置
└─ FEISHU_SECRET ⚠️ 需要配置
```

---

## 🚀 下一步

1. ✅ 必需配置已完成，系统可正常运行
2. ⚠️ 可选配置完成后将启用真实数据
3. 等待每日 09:00 自动推送日报

如有任何配置问题，请随时告诉我！