# GitHub Secrets 配置检查清单

**检查时间**: 2026-08-05  
**仓库**: fys2388/chinaboundtravel

---

## 📋 检查步骤

### 步骤 1：访问 GitHub Secrets 页面
1. 在浏览器中打开：https://github.com/fys2388/chinaboundtravel/settings/secrets/actions
2. 确认已登录 GitHub 账号

---

## ✅ P0 - 必须配置（阻塞部署）

### 1. CLOUDFLARE_API_TOKEN
- **状态**: ❌ 空值（需要添加）
- **用途**: Cloudflare Pages 部署 + CDN 缓存清除
- **影响**: 部署失败 + 缓存无法清除
- **获取方式**:
  1. 访问 https://dash.cloudflare.com/profile/api-tokens
  2. 点击 "Create Token"
  3. 使用模板 "Edit Cloudflare DNS" 或自定义权限
  4. 必须包含：
     - Zone → Zone → Read
     - Zone → Workers Routes → Edit
  5. 复制 Token 并粘贴到 GitHub Secrets

### 2. FEISHU_SECRET
- **状态**: ❌ 空值（需要添加）
- **用途**: 飞书应用认证
- **影响**: 飞书日报/周报/月报发送失败
- **获取方式**:
  1. 访问 https://open.feishu.cn/app
  2. 点击你的应用进入详情
  3. 进入 "安全设置" 或 "凭证与基础信息"
  4. 复制 App Secret
  5. 粘贴到 GitHub Secrets

---

## ⚠️ P1 - 建议配置（社交功能）

### 3. BUFFER_API_TOKEN
- **状态**: ❌ 缺失
- **用途**: 健康检查中的 Buffer API 调用
- **获取方式**: https://buffer.com/settings/api

### Twitter API 密钥（5个）
| Secret | 用途 | 获取方式 |
|--------|------|----------|
| TWITTER_BEARER_TOKEN | Twitter 读取 | developer.twitter.com |
| TWITTER_API_KEY | Twitter API | 同上 |
| TWITTER_API_SECRET | Twitter API | 同上 |
| TWITTER_ACCESS_TOKEN | Twitter 发布 | 同上 |
| TWITTER_ACCESS_TOKEN_SECRET | Twitter 发布 | 同上 |

### YouTube OAuth 密钥（2个）
| Secret | 用途 | 获取方式 |
|--------|------|----------|
| YOUTUBE_CLIENT_SECRETS | YouTube OAuth | Google Cloud Console |
| YOUTUBE_OAUTH_REFRESH_TOKEN | YouTube 刷新 | 运行 OAuth 流程 |

---

## 🔧 P2 - 可选配置（社交扩展）

### Facebook 发布
- FACEBOOK_PAGE_ID
- FACEBOOK_PAGE_ACCESS_TOKEN

### LinkedIn 发布
- LINKEDIN_ACCESS_TOKEN
- LINKEDIN_COMPANY_URN

### TikTok 发布
- TIKTOK_ACCESS_TOKEN

---

## 📝 配置方法

### 方法 1：手动添加（推荐）
1. 访问 GitHub Secrets 页面
2. 点击 "New repository secret"
3. 输入 Name 和 Secret
4. 点击 "Add secret"

### 方法 2：使用命令行
```powershell
# 安装 GitHub CLI（如果未安装）
winget install --id GitHub.cli -e --silent --accept-source-agreements

# 登录 GitHub
gh auth login

# 添加 Secret
gh secret set CLOUDFLARE_API_TOKEN --body "your-token-here" --repo fys2388/chinaboundtravel
gh secret set FEISHU_SECRET --body "your-secret-here" --repo fys2388/chinaboundtravel
```

### 方法 3：使用脚本
```powershell
# 运行批量添加脚本
.\scripts\Add-GitHubSecrets.ps1
```

---

## ✅ 验证步骤

### 1. 确认 Secrets 已配置
访问：https://github.com/fys2388/chinaboundtravel/settings/secrets/actions
确认以下 Secrets 显示为已配置（非空）：
- [ ] CLOUDFLARE_API_TOKEN
- [ ] FEISHU_SECRET

### 2. 测试部署工作流
1. 访问：https://github.com/fys2388/chinaboundtravel/actions/workflows/deploy-cloudflare-pages.yml
2. 点击 "Run workflow"
3. 观察执行结果

### 3. 测试飞书日报
1. 访问：https://github.com/fys2388/chinaboundtravel/actions/workflows/feishu-daily-report.yml
2. 点击 "Run workflow"
3. 检查飞书机器人是否收到消息

---

## 🔗 快速链接

| 资源 | 链接 |
|------|------|
| GitHub Secrets | https://github.com/fys2388/chinaboundtravel/settings/secrets/actions |
| Cloudflare API | https://dash.cloudflare.com/profile/api-tokens |
| 飞书开发者 | https://open.feishu.cn/app |
| GitHub Actions | https://github.com/fys2388/chinaboundtravel/actions |
| Twitter Developer | https://developer.twitter.com/en/portal/dashboard |
| Google Cloud | https://console.cloud.google.com/apis/credentials |

---

**备注**: 请优先配置 P0 级别的 Secrets，以确保部署和通知功能正常。
