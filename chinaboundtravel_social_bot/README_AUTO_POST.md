# ChinaBound Travel — Auto Poster 使用指南

## 文件说明

| 文件 | 作用 |
|------|------|
| `start_chrome_debug.ps1` | 启动 Chrome 调试浏览器（需先运行） |
| `auto_post_final.py` | 六平台自动发帖脚本 |
| `config.py` | 账号配置 |
| `六大社媒发帖规则界面手册.md` | 平台规则参考文档 |

---

## 快速启动（Step A 完成后的正确顺序）

### 第一步：启动 Chrome 调试浏览器

**先关闭所有已打开的 Chrome 窗口**，然后：

```
双击运行：start_chrome_debug.ps1
```

或 PowerShell 中运行：
```powershell
cd e:\AI\dulizhan\travel-blog\chinaboundtravel_social_bot
.\start_chrome_debug.ps1
```

成功标志：看到 `[OK] Chrome started successfully` 和 `[OK] Port 9222 is listening`

### 第二步：确保账号已登录

在打开的 Chrome 调试浏览器中，手动检查并登录以下账号（只需操作一次，以后自动保持）：

- [ ] Reddit — `reddit.com` → 右上角登录（fys2388@gmail.com）
- [ ] Pinterest — `pinterest.com` → 登录
- [ ] Quora — `quora.com` → 登录
- [ ] Medium — `medium.com` → 用 Google 账号登录（fys2388@gmail.com）
- [ ] Instagram — `instagram.com` → 登录
- [ ] Facebook — `facebook.com` → 登录

### 第三步：运行发帖脚本

```powershell
cd e:\AI\dulizhan\travel-blog\chinaboundtravel_social_bot
& "C:\ProgramData\WorkBuddy\chromium-env\1uvcuj0\.workbuddy\binaries\python\envs\social-bot\Scripts\python.exe" auto_post_final.py
```

---

## 运行逻辑

```
Reddit (文本帖，无外链正文) → [等待60秒] →
Pinterest (描述含链接) → [等待60秒] →
Quora (回答形式，含链接) → [等待60秒] →
Medium (长文，文末CTA) → [等待60秒] →
Instagram (跳过，网页限流) → [等待60秒] →
Facebook (图文帖)
```

---

## 每次发完后

**不要关闭 Chrome 调试浏览器** — 下次运行脚本时直接执行，账号状态保持。

---

## 常见问题

**Q: 脚本报错 "Cannot connect to Chrome"**
A: Chrome 调试浏览器没有启动，或端口被占用。先运行 `start_chrome_debug.ps1`

**Q: Reddit 发帖失败**
A: Reddit 对同一 IP 每日发帖次数有限制。尝试换 Subreddit，或等待 24 小时

**Q: Pinterest 找不到图片上传入口**
A: 脚本使用 Pinterest 网页 API，如果 Pinterest 更新了 UI 可能需要调整选择器

**Q: Instagram / Facebook 建议替代方案**
A: 这两个平台反自动化检测最强，建议使用 **Facebook Creator Studio**（可以管理 Instagram + Facebook）来发帖

---

## 定时自动发帖（可选）

使用 Windows 任务计划程序定时运行脚本：

1. 打开「任务计划程序」
2. 创建基本任务
3. 触发器：每天 09:00 执行
4. 操作：启动程序
   - 程序：`powershell.exe`
   - 参数：`-ExecutionPolicy Bypass -File "e:\AI\dulizhan\travel-blog\chinaboundtravel_social_bot\start_chrome_debug.ps1"`
5. 再创建一个任务，在启动 Chrome 后 10 秒运行 Python 脚本

---

*Last updated: 2026-05-27*
