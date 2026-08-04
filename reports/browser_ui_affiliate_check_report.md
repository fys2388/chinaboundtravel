# 网站 UI 与联盟链接检查报告

检查时间：2026-08-04
检查方式：浏览器直接访问 + 脚本扫描
检查目标：https://www.chinaboundtravel.com/

---

## 一、网站 UI 配置检查结果

### 1. 首页 (https://www.chinaboundtravel.com/)
- 页面标题、描述完整，品牌信息一致
- 主导航菜单正常：Search、Home、Pricing、City Travel、Resources、Visa Guide、Payment、Blog、Internet、Contact、About Me
- 主题切换按钮存在
- 邮件订阅表单存在
- 最新文章、热门指南、城市旅行指南区块正常渲染
- 页脚链接完整（Privacy Policy、Pricing、Blog 等）
- 未发现明显 UI 错位或死链

### 2. 定价页面 (https://www.chinaboundtravel.com/pricing/)
- 页面标题：Choose Your China Travel Pass
- 版本号已更新为 **2026.08**
- 三个套餐（One-Time Buyout、Monthly、Annual Elite）正常显示
- 订阅条款复选框与退款政策链接存在
- Stripe 结账链接配置正确
- ⚠️ **问题**：购买按钮默认被 JavaScript 禁用，必须勾选退款协议复选框才能点击；实际按钮视觉上没有明显禁用状态，导致用户点击无反应

### 3. 文章页面（张家界示例）
- URL：https://www.chinaboundtravel.com/posts/zhangjiajie-avatar-mountains-complete-guide-to-chinas-most-spectacular-park/
- 标题、图片、目录、正文正常渲染
- 内部链接正常
- 联盟链接区块（eSIM、VPN、Hotels、Flights、Insurance、Tours）正常显示

### 4. Resources 页面
- URL：https://www.chinaboundtravel.com/resources/
- 联盟链接分类清晰：Insurance、eSIM、VPN、Hotels、Flights、Tours、Payments
- 免责声明存在

---

## 二、联盟链接有效性检查

### 2.1 扫描范围
- 扫描文章数：24 篇
- 扫描唯一联盟 URL 数：6 个
- 涉及联盟项目：Airalo、NordVPN（affiliatescn）、Booking.com、Klook、SafetyWing、Trip.com

### 2.2 检查结果

| 联盟项目 | URL | HEAD 状态 | 浏览器访问 | 结论 |
|---|---|---|---|---|
| Airalo eSIM | https://www.airalo.com/ | TIMEOUT | ✅ 正常 | HEAD 请求被限制，实际可访问 |
| NordVPN | https://get.affiliatescn.net/aff_c?offer_id=153&aff_id=150687&url_id=613 | 200 | ✅ 正常 | OK |
| Booking.com | https://www.booking.com/index.html?aid=730795 | 202 | ✅ 正常 | OK |
| Klook | https://klook.tpo.li/vrPkmS2v | 403 (跳转后) | ✅ 正常 | 反爬虫 HEAD 拦截，实际可访问 |
| SafetyWing | https://safetywing.com/nomad-insurance?referenceID=... | 200 | ✅ 正常 | OK |
| Trip.com | https://www.trip.com/ | 200 | ✅ 正常 | OK |

### 2.3 发现的问题与修复

#### 问题 1：Airalo 失效 promo 链接
- **现象**：页面渲染出的 Airalo 链接指向 `https://www.airalo.com/promo/38j3e4`，该页面返回 "Something went wrong"（404）
- **根因**：
  - `layouts/shortcodes/affiliate-esim.html` 中硬编码了旧 promo URL
  - `content/resources/_index.md` 中硬编码了旧 promo URL
  - `content/posts/2026-06-30-zhangjiajie-avatar-mountains-complete-guide-to-chinas-most-spectacular-park.md` 中硬编码了旧 promo URL，且 markdown 语法损坏
- **修复**：
  - shortcode 改为使用 `.Site.Params.affiliate.esim`
  - 硬编码链接全部替换为 `https://www.airalo.com/`
  - 修复张家界文章中的损坏 markdown

#### 问题 2：Trip.com 失效跳转链接
- **现象**：3 篇文章中硬编码了 `https://trip.tpo.li/trains?marker=730795`，该链接返回 404
- **影响文件**：
  - `2026-05-26-hangzhou-west-lake-tea-culture-g20-guide.md`
  - `2026-05-25-shanghai-bund-french-concession-2-day-guide.md`
  - `2026-05-25-china-high-speed-rail-how-to-book-tickets.md`
- **修复**：替换为 `https://www.trip.com/`

#### 问题 3：检查脚本未同步 hugo.toml
- **现象**：`scripts/check_affiliate_config.cjs` 中 URLS 数组仍包含已废弃的 Airalo promo、NordPass 跳转、Trip redirect、Aviasales travelpayouts URL
- **修复**：更新脚本 URLS 数组，与当前 `hugo.toml` 保持一致

#### 问题 4：定价页购买按钮点击无反应
- **现象**：Pricing 页面三个购买按钮（Buy Now / Start for $1 / Get Instant Access）点击后无法进入 Stripe 结账页
- **根因**：`layouts/partials/pricing-table.html` 底部脚本在页面加载后立即移除按钮的 `href` 属性，只有勾选退款协议复选框后才恢复；但按钮视觉样式保持彩色，用户无法识别已禁用
- **修复**：
  - 移除默认禁用逻辑，按钮始终保留 `href`
  - 点击时检查复选框：未勾选则阻止跳转、高亮复选框并提示用户
  - 勾选后正常跳转 Stripe 结账页
- **本地验证**：未勾选时点击会聚焦复选框并提示；勾选后成功跳转到 `https://buy.stripe.com/28E8wJ4I8bADg9je9u1gs01`

---

## 三、部署状态

- 修复已提交并推送至 GitHub：`main` 分支
- 相关 commits：
  - `49bc7ed` fix(affiliate): update Airalo promo link to main site and sync check script with hugo.toml
  - `42adece` fix(affiliate): replace outdated Trip.com redirect with main site URL
  - `4393aff` fix(pricing): make checkout buttons clickable with refund-policy validation
- Cloudflare Pages 将自动部署；部署完成后线上页面才会生效

---

## 四、后续建议

1. **部署后复检**：Cloudflare Pages 部署完成后，重新访问 Pricing 页面，确认购买按钮可直接点击并进入 Stripe
2. **Airalo HEAD 超时**：自动化脚本中对该域名使用 GET 或增加超时；当前浏览器验证已通过
3. **联盟链接常态化监控**：建议每周运行 `check_affiliate_links.cjs` 扫描文章中的联盟链接
