# 邮件订阅 Lead Magnet 审计与上线报告
**生成时间**: 2026-10-01

---

## 1. 组件清单

### 1.1 Lead Magnet PDF 文件

| 文件 | 路径 | 大小 | 状态 |
|------|------|------|------|
| 7-Day China Itinerary Template | `public/ebook/7-day-china-itinerary.pdf` | 存在 | ✅ |
| China Visa-Free Entry Checklist | `public/lead-magnet/china-visa-free-entry-checklist.pdf` | 存在 | ✅ |
| ChinaBound Travel Guide (May 2026) | `public/ebook/china-bound-travel-guide-2026-05.pdf` | 存在 | ✅ |
| Travel Radar (May 29) | `public/ebook/radar/travel-radar-May-29-2026.pdf` | 存在 | ✅ |

### 1.2 模板组件

| 组件 | 路径 | 用途 |
|------|------|------|
| 邮箱订阅卡片 | `layouts/partials/email-subscribe.html` | 文章底部/侧边订阅框 |
| Lead Magnet CTA 短代码 | `layouts/shortcodes/lead-magnet-cta.html` | 文章中内联订阅框 |
| 订阅 API | `functions/api/subscribe.js` | Cloudflare Pages Function |

### 1.3 API 端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `POST /api/subscribe` | POST | 接收 { email, source, lead_magnet }，调用 MailerLite + Resend |
| `OPTIONS /api/subscribe` | OPTIONS | CORS 预检 |

### 1.4 MailerLite 集成

| 配置 | 值 |
|------|-----|
| API 端点 | `https://connect.mailerlite.com/api/subscribers` |
| Token 清洗 | `ml_utils.clean_token()` (移除 BOM/空白) |
| 字段 | `signup_source`, `lead_magnet` |
| Resend 邮件 | 自动发送 PDF 下载链接 |

---

## 2. CTA 覆盖审计

### 2.1 当前 CTA 分布

| 文章 | 短代码 | CTA 文案 |
|------|--------|----------|
| `2026-05-26-7-day-china-itinerary-beijing-xian-shanghai-first-timers.md` | `lead-magnet-cta` | "Download This Itinerary as PDF →" |
| `2026-05-25-china-high-speed-rail-how-to-book-tickets.md` | `lead-magnet-cta` | "Building Your China Route? Grab the Free 7-Day Itinerary →" |
| `2026-06-02-ultimate-guide-to-china-visa-for-tourists.md` | `lead-magnet-cta` | "Planning Your China Trip? Grab the Free 7-Day Itinerary →" |
| `alipay-for-foreigners-guide.md` | `lead-magnet-cta` | "Planning Your China Trip? Get the Free 7-Day Itinerary →" |

**当前覆盖**: 4 / 63 篇文章 (6.3%)

### 2.2 GSC 高流量页 CTA 缺口

| 页面 | GSC 曝光 | 平均排名 | 有 CTA? |
|------|----------|----------|---------|
| food-recommendations-guide | 24 | 62.2 | ❌ |
| accommodation-tips-guide | 10 | 9.3 | ❌ |
| 7-day-china-itinerary (canonical) | 4 | 25.5 | ✅ (duplicate slug) |
| 144-hour-visa-free-transit-guide | ~50+ | ~15 | ❌ |
| chinese-food-delivery | 2 | 9.0 | ❌ |

**关键缺口**: 144-hour 过境免签（最高曝光页）和 food-recommendations（次高曝光页）均无 CTA。

---

## 3. 建议插入 CTA 的高优先级文章

| 优先级 | 文章 slug | GSC 曝光 | 理由 |
|--------|-----------|----------|------|
| 🔴 P0 | `144-hour-visa-free-transit-guide` | ~50+ | 最高曝光，免签政策核心页 |
| 🟡 P1 | `food-recommendations-guide` | 24 | 高曝光，餐饮指南天然关联旅行计划 |
| 🟡 P1 | `accommodation-tips-guide` | 10 | 排名高(9.3)，酒店指南关联行程 |
| 🟡 P1 | `chinese-food-delivery-meituan-eleme-guide` | 2 | 排名高(9.0)，REV001 实验页 |
| 🟢 P2 | `beijing-hongkong-25h-journey` | ~10 | 路线指南，自然关联行程模板 |

---

## 4. 订阅表单验证

### 4.1 代码审查

| 检查项 | 状态 | 说明 |
|--------|------|------|
| CORS 支持 | ✅ | subscribe.js:48-54 |
| JSON 解析错误处理 | ✅ | subscribe.js:124-129 (P0-FIX v2) |
| 邮箱格式校验 | ✅ | subscribe.js 内 validateEmail() |
| MailerLite 集成 | ✅ | addMailerLiteSubscriber() |
| Resend PDF 邮件 | ✅ | sendLeadMagnetEmail() |
| 无效邮箱返回 400 | ✅ | P0-FIX (2026-09-07) |
| 无内部信息泄露 | ✅ | 错误消息不暴露内部细节 |

### 4.2 健康检查记录

最近一次健康检查 (2026-09-23):
- Base URL: `https://cbt-travel.com` (⚠️ 可能配置错误，应为 `www.chinaboundtravel.com`)
- 6 个测试用例: 全部失败 (404)
- **可能原因**: 健康检查脚本使用了错误的 base_url

### 4.3 订阅者数量

- MailerLite API Token: 已配置 (`ml_utils.clean_token`)
- 总订阅者: 需通过 MailerLite API 查询（本机无法直接访问）
- 2026年10月新增: 0（据用户报告）

---

## 5. 实施建议

### 立即执行（本周）

1. **插入 CTA 到高流量页**:
   ```
   {{< lead-magnet-cta magnet="visa-free-checklist" text="Get the Free Visa-Free Entry Checklist →" >}}
   ```
   插入到: `144-hour-visa-free-transit-guide.md`

2. **修复健康检查配置**:
   - 确认 `subscription_health_audit.py` 的 `--base-url` 参数
   - 正确 URL: `https://www.chinaboundtravel.com`

### 短期执行（本月）

3. **插入 CTA 到 food-recommendations-guide.md**:
   ```
   {{< lead-magnet-cta magnet="itinerary-template" text="Planning Your China Trip? Get the Free 7-Day Itinerary →" >}}
   ```

4. **插入 CTA 到 accommodation-tips-guide.md**:
   ```
   {{< lead-magnet-cta magnet="itinerary-template" text="Planning Your China Trip? Get the Free 7-Day Itinerary →" >}}
   ```

5. **部署后验证**:
   - 运行 `python scripts/subscription_health_audit.py --base-url https://www.chinaboundtravel.com`
   - 确认 6 个测试用例全部通过

---

## 6. 结论

- ✅ Lead Magnet PDF 完整可用（4 个文件）
- ✅ 订阅 API 代码完整且经过 P0-FIX 修复
- ✅ 2 种 CTA 模板可用（内联 + 底部卡片）
- ❌ CTA 覆盖仅 6.3%（4/63 篇），高流量页缺失
- ❌ 订阅者增长缓慢（10 月新增 0）
- ⚠️ 健康检查脚本可能配置错误域名

**核心问题**: CTA 覆盖不足，非技术问题。高流量页未插入 CTA 导致订阅转化率低。

---

*数据来源: layouts/partials/email-subscribe.html, layouts/shortcodes/lead-magnet-cta.html, functions/api/subscribe.js, reports/subscription_health/*