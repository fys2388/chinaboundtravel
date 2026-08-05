# GitHub Secrets 配置修复指南
# 生成时间：2026-08-05

## 问题清单

### P0 - 阻塞部署（必须修复）
1. CLOUDFLARE_API_TOKEN - 空值
2. FEISHU_SECRET - 空值

### P1 - 功能缺失（建议修复）
3. BUFFER_API_TOKEN
4. TWITTER_BEARER_TOKEN
5. TWITTER_API_KEY
6. TWITTER_API_SECRET
7. TWITTER_ACCESS_TOKEN
8. TWITTER_ACCESS_TOKEN_SECRET
9. YOUTUBE_CLIENT_SECRETS
10. YOUTUBE_OAUTH_REFRESH_TOKEN

### P2 - 可选功能（按需修复）
11. FACEBOOK_PAGE_ID
12. FACEBOOK_PAGE_ACCESS_TOKEN
13. LINKEDIN_ACCESS_TOKEN
14. LINKEDIN_COMPANY_URN
15. TIKTOK_ACCESS_TOKEN

---

## 修复步骤

### 步骤 1：添加 CLOUDFLARE_API_TOKEN

1. 访问：https://dash.cloudflare.com/profile/api-tokens
2. 点击 "Create Token"
3. 使用模板 "Edit Cloudflare DNS" 或自定义：
   - Zone → Zone → Read
   - Zone → Workers Routes → Edit
4. 复制生成的 Token
5. 访问：https://github.com/fys2388/chinaboundtravel/settings/secrets/actions
6. 点击 "New repository secret"
7. Name: CLOUDFLARE_API_TOKEN
8. Secret: [粘贴 Token]
9. 点击 "Add secret"

### 步骤 2：添加 FEISHU_SECRET

1. 访问：https://open.feishu.cn/app
2. 点击你的应用进入详情
3. 进入 "安全设置" 或 "凭证与基础信息"
4. 复制 App Secret
5. 访问：https://github.com/fys2388/chinaboundtravel/settings/secrets/actions
6. 点击 "New repository secret"
7. Name: FEISHU_SECRET
8. Secret: [粘贴 App Secret]
9. 点击 "Add secret"

### 步骤 3：添加 Twitter API 密钥（可选）

1. 访问：https://developer.twitter.com/en/portal/dashboard
2. 创建项目和应用
3. 获取以下密钥：
   - Bearer Token
   - API Key
   - API Key Secret
   - Access Token
   - Access Token Secret
4. 逐个添加到 GitHub Secrets

### 步骤 4：添加 Buffer API Token（可选）

1. 访问：https://buffer.com/settings/api
2. 复制 API Token
3. 添加到 GitHub Secrets: BUFFER_API_TOKEN

### 步骤 5：添加 YouTube OAuth 密钥（可选）

1. 访问：https://console.cloud.google.com/apis/credentials
2. 创建 OAuth 2.0 Client ID
3. 下载 client secrets JSON
4. 将内容添加到 GitHub Secrets: YOUTUBE_CLIENT_SECRETS
5. 运行 OAuth 流程获取 refresh token
6. 添加到 GitHub Secrets: YOUTUBE_OAUTH_REFRESH_TOKEN

---

## 验证步骤

### 1. 检查 Secrets 是否配置成功
访问：https://github.com/fys2388/chinaboundtravel/settings/secrets/actions

确认以下 Secrets 已添加：
- [ ] CLOUDFLARE_API_TOKEN
- [ ] FEISHU_SECRET
- [ ] BUFFER_API_TOKEN (可选)
- [ ] TWITTER_* (可选)
- [ ] YOUTUBE_* (可选)

### 2. 测试部署工作流
访问：https://github.com/fys2388/chinaboundtravel/actions/workflows/deploy-cloudflare-pages.yml
点击 "Run workflow" → 手动触发

### 3. 测试飞书日报工作流
访问：https://github.com/fys2388/chinaboundtravel/actions/workflows/feishu-daily-report.yml
点击 "Run workflow" → 手动触发

### 4. 检查飞书机器人通知
确认飞书群收到测试消息

---

## 快速链接

- GitHub Secrets 设置：https://github.com/fys2388/chinaboundtravel/settings/secrets/actions
- Cloudflare API Tokens：https://dash.cloudflare.com/profile/api-tokens
- 飞书开发者后台：https://open.feishu.cn/app
- GitHub Actions：https://github.com/fys2388/chinaboundtravel/actions
