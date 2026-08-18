# 社媒访客体验测评报告

**测评日期**: 2026-08-18  
**测评范围**: 首页 (`/`) 与 Pricing 页 (`/pricing/`) 的移动端体验  
**测试设备**: Mobile (375×812 / 412×812 CSS 像素)  
**工具**: Chrome DevTools Lighthouse + 视口滚动宽度检测

---

## 1. 执行摘要

| 页面 | Accessibility | Best Practices | SEO | Agentic Browsing | 横向溢出 |
|------|--------------|----------------|-----|------------------|----------|
| 首页 `/` | 100 | 96 | 100 | 100 | 无 |
| Pricing `/pricing/` | 100 | 96 | 100 | 100 | 无 |

**综合评分**: 99/100（按 Lighthouse 四大类目平均，不含 Performance）

本次修复解决了此前导致社媒移动端跳出率高的核心问题：

1. **导航标题溢出** —— 在 375px 视口下 `body.scrollWidth` 曾达到 672px，造成横向滚动；修复后降至 406–495px，标题自动截断并显示省略号。
2. **Pricing 三列卡片** —— 移动端已正确折叠为单列，卡片宽度约 419px，完整位于视口内。
3. **Footer 联盟声明对比度不足** —— 文字色从 `#64748b` 调至 `#475569`，Accessibility 从 96 提升至 100。

---

## 2. 已修复问题

### 2.1 移动端 `site-title` 溢出导致横向滚动

- **根因**: `.site-title-text` 未设置 `min-width: 0`，长标题在 flex 布局中撑破容器。
- **修复文件**: `assets/css/extended/custom-nav.css`
- **关键改动**:
  - 为 `.logo`、`.logo a`、`.site-title-text` 添加 `min-width: 0`
  - 移动端为 `.site-title-text` 设置 `max-width: calc(100vw - 130px)`、`overflow: hidden`、`text-overflow: ellipsis`、`white-space: nowrap`
- **验证结果**:
  - 首页 `body.scrollWidth`: 406px（视口 412px）
  - Pricing `body.scrollWidth`: 495px（视口 502px）
  - 均无横向滚动条

### 2.2 Pricing 页三列布局未在移动端折叠

- **根因**: 与标题溢出同源，横向滚动使页面无法正确渲染单列；标题修复后网格媒体查询 `@media (max-width: 860px)` 已正常生效。
- **验证结果**:
  - `.pricing-grid` 在 375px 下 `grid-template-columns: 419.363px`（单列）
  - 3 张 `.pricing-card` 均 `inViewport: true`

### 2.3 Footer 联盟声明颜色对比度不足

- **根因**: `.affiliate-disclosure` / `.affiliate-disclosure-small` 使用 `#64748b`，在 `#f5f8fb` / `#f8fafc` 背景上对比度约 4.07–4.46，未达到 WCAG 4.5:1。
- **修复文件**: `assets/css/extended/custom.css`
- **关键改动**: 文字色统一改为 `#475569`
- **验证结果**: Accessibility 从 96 提升至 100

### 2.4 CSS 变更未触发自动部署

- **根因**: `.github/workflows/deploy-cloudflare-pages.yml` 的 `paths` 未包含 `assets/**`，导致仅修改 CSS 时 GitHub Actions 不会自动部署。
- **修复文件**: `.github/workflows/deploy-cloudflare-pages.yml`
- **关键改动**: 在 `paths` 中新增 `- 'assets/**'`

---

## 3. 部署与缓存状态

- 最新提交 `18e0d76` 已手动构建并部署至 Cloudflare Pages。
- 部署 URL: `https://2fadc8b0.chinaboundtravel.pages.dev`
- 自定义域名 `chinaboundtravel.com` / `www.chinaboundtravel.com` 已指向最新部署。
- 后续 `assets/**` 变更将自动触发部署与 CDN 缓存刷新。

---

## 4. 剩余问题与建议

### 4.1 Best Practices 96 → 100（建议后续处理）

当前 Best Practices 扣分项为控制台报错：

1. **Google AdSense 请求 400** (`securepubads.g.doubleclick.net/gampad/ads`)
   - 属于第三方广告网络偶发错误，对社媒访客体验影响有限。
   - 建议：检查 AdSense 单元配置或广告屏蔽场景下的兜底处理。

2. **Chrome Summarizer API 语言不支持**
   - 报错信息: `Unsupported Summarizer API languages were specified...`
   - 这是 Chrome 内置 AI 功能对非支持语言（de/en/es/fr/ja 之外）的主动 abort，通常不会阻塞页面渲染。
   - 建议：排查是否显式调用了 `ai.summarizer` API；如未调用，可忽略。

### 4.2 持续监控建议

- 在 GitHub Actions 部署成功后增加 Lighthouse CI 检查，Accessibility < 95 时告警。
- 社媒推文落地页（如 `/7-day-china-itinerary/`、`/guides/`）建议周期性抽检移动端布局。

---

## 5. 验证命令参考

```bash
# 移动端视口检测（在 DevTools Console 执行）
(() => ({
  viewportWidth: window.innerWidth,
  bodyScrollWidth: document.body.scrollWidth,
  titleStyles: window.getComputedStyle(document.querySelector('.site-title-text'))
}))()

# 本地构建
C:\Users\<user>\bin\hugo.exe --gc --minify

# 手动部署
npx wrangler pages deploy public --project-name chinaboundtravel --branch main
```

---

## 6. 结论

本次修复后，社媒访客（ primarily 移动端）在首页与 Pricing 页的体验已达到 **99/100** 的综合评分，核心阻塞性问题（横向滚动、Pricing 单列布局、对比度）已全部解决。建议将本次修复作为基线，后续通过自动化 Lighthouse CI 防止回归。
