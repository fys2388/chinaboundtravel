# 部署视频支持更新

## 已完成的修改

`worker.js` 已添加视频自动识别和发布支持：
- 根据 URL 后缀（.mp4/.mov/.avi/.webm/.m4v/.mkv）自动判断是视频还是图片
- 视频使用 `{ video: { url: mediaUrl } }` 格式
- Instagram 视频自动设置 `type: 'video'`（Reels）
- Facebook/Pinterest/Twitter/X 均支持视频发布

## 部署步骤（在你的本地终端执行）

### 方法一：Wrangler CLI（推荐）

```powershell
cd e:\AI\dulizhan\travel-blog\buffer-worker

# 如果还没登录 wrangler
npx wrangler login

# 部署到生产环境
npx wrangler deploy
```

### 方法二：使用 API Token

```powershell
cd e:\AI\dulizhan\travel-blog\buffer-worker

# 设置 API Token（从 GitHub Secrets 中获取，或在 Cloudflare Dashboard > Profile > API Tokens 创建）
$env:CLOUDFLARE_API_TOKEN = "你的_API_Token"

# 部署
npx wrangler deploy
```

## 部署后验证

1. 访问 https://buffer-auto-poster.fys2388.workers.dev/ 确认 Worker 正常
2. 发送一条带视频 URL 的测试请求确认视频发布功能
