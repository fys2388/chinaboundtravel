# 正式密钥切换指南

## 概述

本指南用于将测试模式切换为正式发布模式。当您的 Reddit 账号权重足够、可以正常创建应用后，只需按照以下步骤操作即可无缝切换到正式发布模式。

## 切换步骤

### 步骤 1：获取 Reddit API 密钥

1. 访问 [Reddit Apps](https://www.reddit.com/prefs/apps)
2. 点击 "Create App" 或 "Create Another App"
3. 填写应用信息：
   - **Name**: ChinaBound Travel Bot
   - **Type**: Script
   - **Description**: Social media automation bot for ChinaBound Travel blog
   - **About URL**: https://chinaboundtravel.com
   - **Redirect URI**: http://localhost:8080
4. 点击 "Create App"
5. 记录以下信息：
   - **Client ID**: 在应用名称下方的一串字符
   - **Client Secret**: 标有 "secret" 的字段

### 步骤 2：更新环境变量

编辑 `.env` 文件，替换以下配置：

```env
# Reddit 正式配置
REDDIT_CLIENT_ID=YOUR_ACTUAL_CLIENT_ID
REDDIT_CLIENT_SECRET=YOUR_ACTUAL_CLIENT_SECRET
REDDIT_USERNAME=YOUR_REDDIT_USERNAME
REDDIT_PASSWORD=YOUR_REDDIT_PASSWORD
REDDIT_USER_AGENT=python:chinaboundtravel_bot:1.0 (by /u/YOUR_REDDIT_USERNAME)
```

### 步骤 3：重启服务

```bash
# 停止当前运行的服务（按 Ctrl+C）
# 重新启动服务
python main.py --mode schedule
```

## 验证切换成功

运行测试命令验证连接：

```bash
python main.py --mode test
```

预期输出应显示：
```
2. Testing Reddit Publisher...
   [OK] Reddit connected successfully
```

## 注意事项

1. **账号安全**：确保 Reddit 账号已启用双因素认证
2. **发布频率**：初始阶段建议降低发布频率，避免触发风控
3. **内容质量**：确保发布内容符合各子版块规则
4. **密钥保护**：不要将 `.env` 文件提交到版本控制
5. **日志监控**：定期检查日志文件，及时处理异常

## 故障排除

### 问题：401 Unauthorized
- 检查 Client ID 和 Client Secret 是否正确
- 确认密码是否正确（注意特殊字符）

### 问题：账号被限制
- 降低发布频率
- 手动发布一段时间积累账号权重
- 检查是否违反了 Reddit 规则

### 问题：子版块发布失败
- 检查子版块是否需要审核才能发布
- 确认账号已加入该子版块
- 检查内容是否符合子版块规则

---

**最后更新**: 2026-05-28
**版本**: 1.0