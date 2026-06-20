# Joran 学习笔记 - 2026-06-16 工作流闭环完整版

## 📊 全站自动化流水线概览

共 6 条自动化流水线，覆盖「内容生产 → 批量优化 → 日常巡检 → 站点部署 → 定期复盘 → 衍生品生产」全链路。

### 工作流闭环状态

| 工作流 | 状态 | 说明 |
|--------|------|------|
| weekly-blog-update.yml | ✅ 完整闭环 | 博文生成 → 自动部署 |
| deploy-cloudflare-pages.yml | ✅ 完整闭环 | 统一部署入口 |
| content-pipeline.yml | ✅ 已修复闭环 | 批量优化 → 自动部署 |
| daily-inspection.yml | ✅ 完整闭环 | 巡检修复 → 自动部署 + 失败告警 |
| annual-content-review.yml | ✅ 已修复闭环 | 年度审查 → 自动部署 |
| monthly-ebook-update.yml | ✅ 已修复闭环 | 电子书 → 自动部署 |

---

## 🚨 工作流闭环核心问题

### 问题1：Commit Message 中的 [skip ci] 导致部署断裂

**问题描述**：
- 工作流代码中使用 `git commit -m "[skip ci] xxx"` 导致 GitHub Actions 检测到后跳过部署
- 修复后的代码不会发布到线上，用户看不到更新

**影响范围**：
- content-pipeline.yml（原第51行、第88行）
- annual-content-review.yml（原第43行）
- monthly-ebook-update.yml（原第47行）

**修复方案**：
```yaml
# 错误写法 ❌
git commit -m "chore: [skip ci] auto-generated post"

# 正确写法 ✅
git commit -m "chore: auto-generated post"
```

### 问题2：工作流缺少部署步骤

**问题描述**：
- 工作流只做了代码提交，没有部署到 Cloudflare Pages
- 导致内容生成了，但网站没有更新

**修复方案**：
在 workflow 中添加 Cloudflare Pages 部署步骤：
```yaml
- name: Deploy to Cloudflare Pages
  uses: cloudflare/pages-action@v1
  with:
    apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
    accountId: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
    projectName: chinaboundtravel
    directory: public
```

---

## ⚠️ 待优化点及状态

| 待优化点 | 状态 | 说明 |
|----------|------|------|
| 依赖版本警告 | ✅ 已优化 | 升级 actions/checkout@v4.2.2 → v4 |
| 失败告警缺失 | ✅ 已优化 | 添加飞书失败通知 |
| 流量数据真实性 | ✅ 已配置 | GA4 Property ID: 538482322 |
| 回滚能力缺失 | ℹ️ 需手动 | Cloudflare Pages 不支持自动回滚 |

---

## 💡 工作流设计原则

1. **闭环完整性**：每个工作流必须有明确的产出 → 提交 → 部署链路
2. **无 [skip ci]**：永远不要在 commit message 中使用 [skip ci]
3. **失败通知**：关键工作流必须配置失败告警
4. **单一出口**：所有部署统一通过 deploy-cloudflare-pages.yml

---

## 🔧 关键配置文件

| 配置项 | 值 | 位置 |
|--------|-----|------|
| GA4 Property ID | 538482322 | .env |
| Google Credentials | gen-lang-client-0594957837-9e3f7ac5fd24.json | Downloads |
| Cloudflare Account ID | 76b6c886ece7149115e3d334fcec8a02 | GitHub Secrets |
| Cloudflare Zone ID | 76b6c886ece7149115e3d334fcec8a02 | GitHub Secrets |

---

## 🚫 编码规范 - 避免乱码（CRITICAL）

### 问题背景
2026-06-20 扫描发现 3 篇文章存在乱码字符（� / U+FFFD），导致网站显示异常。

### 影响文件
- `144-hour-visa-free-transit-guide.md`
- `western-sichuan-overland-camping-route.md`
- `2026-05-22-how-to-use-wechat-pay-as-a-foreigner.md`

### 乱码原因
- 中文字符、emoji、特殊引号在文件传输/处理过程中编码损坏
- 生成内容包含非 ASCII 字符，在 Windows/PowerShell 环境下保存时出错

### 生成规范（必须遵守）

| 禁止项 | 替代方案 | 示例 |
|--------|----------|------|
| 中文汉字 | 拼音或英文 | 成都 → Chengdu, 火锅 → hotpot |
| Emoji 表情 | 文字描述 | ✅ → "YES", ❌ → "NO" |
| 特殊箭头 → | ASCII 箭头或文字 | → → -> 或 "leads to" |
| 中文引号「」『』 | 标准英文引号 | 「」→ " " |
| 中文标点符号 | 英文标点 | ，。！？ → , . ! ? |
| 特殊符号 | ASCII 替代 | … → ..., — → -- |

### 验证清单
生成文章后，必须检查：
- [ ] 全文无中文字符
- [ ] 无 Emoji（可用 emoji 检测工具）
- [ ] 所有引号为标准 ASCII 引号
- [ ] 文件保存为 UTF-8 编码
- [ ] 在 Hugo 构建前无 � 字符

---

**学习日期**: 2026-06-16
**更新人**: AI运维专员
**状态**: 已沉淀到错误知识库
**GitHub**: https://github.com/fys2388/chinaboundtravel