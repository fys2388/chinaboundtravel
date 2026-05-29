# Cloudflare Pages 部署说明

## 问题原因

API 接口 `/api/checkout` 返回 404 和 500 错误的原因：

1. **部署平台混淆**：项目同时有 Vercel 和 Cloudflare Pages 部署配置
2. **函数文件位置错误**：`_worker.js` 放在 `static/` 目录，但 Cloudflare Pages Functions 需要放在 `functions/` 目录
3. **环境变量未配置**：Stripe 密钥等环境变量没有在 Cloudflare Pages 中设置

## 已完成的修复

1. ✅ 创建了 `functions/api/checkout.js` - 使用正确的 Cloudflare Pages Functions 格式
2. ✅ 创建了 `functions/api/stripe-webhook.js` - Webhook 处理
3. ✅ 更新了 `wrangler.toml` - 配置了 Pages 项目配置
4. ✅ 创建了 GitHub Actions 工作流
5. ✅ 删除了旧的 `static/_worker.js`
6. ✅ 使用正确的函数导出格式

## 需要完成的步骤

### 1. 在 Cloudflare Pages 控制台配置

1. 访问 https://dash.cloudflare.com/ → Pages → chinaboundtravel

2. 设置以下环境变量：

```
STRIPE_SECRET_KEY = [你的 Stripe 密钥]
SUCCESS_URL = https://chinaboundtravel.com/success/
CANCEL_URL = https://chinaboundtravel.com/pricing/
```

### 2. 重新部署

将代码推送到 `main` 分支，GitHub Actions 会自动部署到 Cloudflare Pages

### 3. 如果使用手动部署

```bash
# 构建
hugo

# 部署
wrangler pages deploy public --project-name=chinaboundtravel
```

## 项目结构

```
travel-blog/
├── functions/
│   └── api/
│       ├── checkout.js      → /api/checkout
│       └── stripe-webhook.js → /api/stripe-webhook
├── content/
├── layouts/
├── static/
├── public/                 → 构建输出
├── wrangler.toml
└── .github/workflows/
    └── deploy-cloudflare-pages.yml
```

## 验证部署

部署完成后，访问：
- 生产：https://chinaboundtravel.com/pricing/
- 预览：https://[你的分支名].chinaboundtravel.pages.dev/pricing/

## 常见问题

### 如果 API 仍然错误
- 检查环境变量是否正确设置
- 检查 Stripe 密钥是否有效
- 检查 Cloudflare Pages 构建日志
