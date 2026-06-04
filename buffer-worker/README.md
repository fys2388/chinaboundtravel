# Buffer GraphQL API Auto-Poster 部署指南

## 一、项目结构

```
buffer-worker/
├── worker.js          # Worker主程序
├── wrangler.toml      # Cloudflare配置
├── package.json       # Node.js依赖
└── README.md          # 本文档
```

## 二、前置准备

### 1. 安装Wrangler CLI

```bash
npm install -g wrangler
```

### 2. 登录Cloudflare

```bash
wrangler login
```

### 3. 获取Buffer Personal Token

1. 登录 [Buffer后台](https://buffer.com)
2. 进入 **Settings → API → Personal Keys**
3. 创建新的Personal Key，复制保存

## 三、部署步骤

### 步骤1：安装依赖

```bash
cd buffer-worker
npm install
```

### 步骤2：配置密钥

```bash
# 设置Buffer API Token
wrangler secret put BUFFER_TOKEN
# 输入你的Buffer Personal Token

# 设置飞书Webhook URL
wrangler secret put FEISHU_WEBHOOK_URL
# 输入飞书机器人Webhook地址

# 设置DeepSeek API密钥（用于评论AI回复）
wrangler secret put DEEPSEEK_API_KEY
# 输入DeepSeek API密钥
```

### 步骤3：查询渠道ID

部署后访问以下URL获取渠道ID：

```bash
curl https://buffer-auto-poster.your-subdomain.workers.dev/channels
```

返回示例：
```json
{
  "success": true,
  "channels": [
    { "id": "5f8a9b7c1234567890abcdef", "name": "ChinaBoundTravel", "service": "facebook" },
    { "id": "5f8a9b7c1234567890abcdeg", "name": "chinaboundtravel", "service": "instagram" },
    { "id": "5f8a9b7c1234567890abcdeh", "name": "CBTravel", "service": "x" }
  ]
}
```

### 步骤4：更新渠道ID

编辑 `worker.js`，将渠道ID填入 `CHANNEL_MAP`：

```javascript
const CHANNEL_MAP = {
  facebook: {
    id: '5f8a9b7c1234567890abcdef',  // 替换为实际ID
    name: 'ChinaBoundTravel Facebook Page'
  },
  instagram: {
    id: '5f8a9b7c1234567890abcdeg',  // 替换为实际ID
    name: 'ChinaBoundTravel Instagram'
  },
  x: {
    id: '5f8a9b7c1234567890abcdeh',  // 替换为实际ID
    name: 'ChinaBoundTravel X (Twitter)'
  }
};
```

### 步骤5：部署Worker

```bash
# 开发环境
npm run dev

# 生产环境
npm run deploy:prod
```

## 四、API端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/publish` | POST | 发布文章到社媒 |
| `/channels` | GET | 查询Buffer渠道 |
| `/comments` | GET | 处理评论（预留） |

## 五、GitHub Webhook配置

### 请求格式

```json
{
  "title": "文章标题",
  "desc": "文章正文内容或摘要",
  "cover": "封面图片URL（可选）",
  "url": "文章落地链接（可选）"
}
```

### GitHub Actions集成示例

在 `.github/workflows/auto_blog_publish.yml` 中添加：

```yaml
- name: Publish to Social Media
  run: |
    curl -X POST https://buffer-auto-poster.your-subdomain.workers.dev/publish \
      -H "Content-Type: application/json" \
      -d '{
        "title": "${{ env.POST_TITLE }}",
        "desc": "${{ env.POST_SUMMARY }}",
        "cover": "${{ env.POST_COVER }}",
        "url": "https://chinaboundtravel.com/posts/${{ env.POST_SLUG }}/"
      }'
```

## 六、Cron定时任务

Worker已配置每30分钟自动执行评论处理：

```toml
[triggers]
crons = ["*/30 * * * *"]
```

当前评论处理逻辑为预留状态，需要后续实现：
1. 拉取Buffer各平台最新评论
2. 过滤未回复评论
3. 调用DeepSeek AI生成Joran人设回复
4. 自动发布回复

## 七、测试验证

### 1. 健康检查

```bash
curl https://buffer-auto-poster.your-subdomain.workers.dev/health
```

### 2. 测试发布

```bash
curl -X POST https://buffer-auto-poster.your-subdomain.workers.dev/publish \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Post from ChinaBoundTravel",
    "desc": "This is a test post to verify Buffer API integration.",
    "cover": "",
    "url": "https://chinaboundtravel.com"
  }'
```

## 八、监控与日志

### 查看实时日志

```bash
npm run tail
```

### Cloudflare Dashboard

访问 [Cloudflare Workers Dashboard](https://dash.cloudflare.com) 查看：
- 请求统计
- 错误日志
- Cron执行记录

## 九、常见问题

### Q: 发布失败返回 "No channels configured"

A: 需要先调用 `/channels` 获取渠道ID，并更新 `CHANNEL_MAP` 配置。

### Q: 发布失败返回 "Buffer API error: 401"

A: Buffer Token无效或过期，重新生成Token并更新：
```bash
wrangler secret put BUFFER_TOKEN
```

### Q: Cron任务未执行

A: 检查Cloudflare Dashboard中的Cron触发器状态，确保Worker已部署到生产环境。

## 十、安全建议

1. **Token保护**：所有API密钥通过 `wrangler secret` 设置，不要硬编码
2. **访问控制**：生产环境可添加IP白名单或API Key验证
3. **日志脱敏**：生产日志中不输出敏感信息