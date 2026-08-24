# 转化与排名优化 — 实现说明

> 项目路径：`e:\AI\dulizhan\travel-blog`
> 目标：联盟变现精细化、邮件订阅零突破、内容质量与内链优化，持续提升转化与排名。

---

## 任务1：联盟变现精细化布局 ✅

### 核心成果
- **联盟链接覆盖率 17.9% → 100%**（60/60 篇文章均含联盟推荐）。
- 按文章主题自动匹配对应联盟产品组合。
- 每篇插入 1-3 处 Editorial Voice 软推荐（避免硬广）。
- 新增分产品转化统计，周报自动对比各品类点击率。

### 主题 → 产品组合映射
| 文章主题 | 联盟产品 |
|----------|----------|
| 签证/出行准备 | 机票(flight) + 旅行保险(insurance/safetywing) + eSIM(esim) |
| 城市攻略 | 酒店(hotel) + 一日游/门票(tour/klook) + eSIM(esim) |
| 交通攻略 | 机票(flight) + 高铁接送/门票(tour) |
| 通用兜底 | eSIM(esim) + 保险(insurance) |

### 脚本
- **`scripts/affiliate_link_builder.py`**（v2.0 升级）：
  - 主题检测 `detect_themes()` → 产品组合 `products_for()`
  - Editorial 软推荐 `soft_recommend_shortcode()`（新建 `layouts/shortcodes/soft-recommend.html`）
  - 真实 URL 从 `hugo.toml [params.affiliate]` 解析（`parse_affiliate_urls()`），不在正文硬编码
  - `--dry-run`（默认）预览 / `--apply` 写入
- **`scripts/affiliate_product_stats.py`**：分产品 CTA 统计（posts/cta_count/clicks/ctr），输出
  `reports/revenue/AFFILIATE_PRODUCT_STATS.json` + `.csv`。
- **周报接入**：`scripts/feishu_weekly_report.py` 的「联盟变现诊断」板块新增「分产品转化对比」表格。

### 用法
```bash
python scripts/affiliate_link_builder.py            # 预览
python scripts/affiliate_link_builder.py --apply    # 实际插入软推荐
python scripts/affiliate_link_builder.py --coverage # 覆盖率 + 分产品统计
python scripts/affiliate_product_stats.py           # 分产品转化统计
```

---

## 任务2：邮件订阅零突破 ✅

### 核心成果
- 上线首个 Lead Magnet：《China Visa-Free Entry Checklist》PDF。
- 所有签证/出行类文章侧边栏 + 文末自动展示该 Lead Magnet 订阅 CTA。
- 对接 MailerLite + Resend，订阅后自动发送 PDF。
- 日报新增订阅统计 + 零增长自动告警。

### 交付
- **`static/lead-magnet/china-visa-free-entry-checklist.pdf`**：Lead Magnet PDF
  （由 `scripts/generate_lead_magnet_pdf.py` 生成）。
- **`layouts/partials/email-subscribe.html`**（重写）：按页面类型切换 Lead Magnet——
  签证/出行类显示「China Visa-Free Entry Checklist」，其余显示「7-Day Itinerary」；
  表单改为 fetch `/api/subscribe`，AJAX 提交，无刷新。
- **`functions/api/subscribe.js`**（新建）：Cloudflare Pages Function，
  创建 MailerLite 订阅者 + 用 Resend 发送 PDF 链接。环境变量：
  `MAILERLITE_API_TOKEN`、`RESEND_API_KEY`、`LEAD_MAGNET_URL`、`FROM_EMAIL`。
- **`scripts/feishu_daily_report.py`**（增强）：订阅板块新增「零增长告警」——
  渠道已接入但昨日新增为 0 时，在卡片标注 ⚠️ 并写入待办。

### 用法
- PDF 生成：`python scripts/generate_lead_magnet_pdf.py`
- 订阅 API 部署：Cloudflare Pages Functions 自动部署 `functions/api/subscribe.js`

---

## 任务3：内容质量与内链优化 ✅

### 3a 分类体系梳理
- **`scripts/content_category_normalizer.py`**：梳理全站分类，合并重复，统一命名。
  - 规范分类：`visa / payment / internet / transport / cities / food / travel-tips / itinerary / news`
  - 兼容 YAML(`---`) 与 TOML(`+++`) front matter；统一 tags 大小写/去重。
  - `--dry-run` 预览 / `--apply` 写入；保存 `reports/content_category_report.json`。
- 结果：全站 60 篇文章均分配了规范分类（之前 43 篇缺失），tags 统一规范。

### 3b Top10 核心文章深度优化
- **`scripts/content_deep_optimizer.py`**：对 Top10 核心文章做深度优化：
  - 扩充内容至 2000 字以上（确定性规则补充，不编造政策/价格）
  - 补充长尾关键词（title）
  - 增加 3-5 条相关内链（自动从全站文章库按主题匹配，排除 redirect 文章）
  - 优化 title 与 meta description
- 用法：`python scripts/content_deep_optimizer.py --apply`

### 3c 批量提交 GSC 重新索引
- **`scripts/gsc_index_submit.py`**（增强）：新增 `submit_optimized_pages()`，
  从 `reports/content_deep_optimize_report.json` 提取优化文章 URL 批量提交 Indexing API。
- 用法：`python scripts/gsc_index_submit.py --optimized`
  （需配置 `GSC_SERVICE_ACCOUNT_JSON`；无凭据时安全降级并打印指引）。

---

## 测试

```bash
cd e:\AI\dulizhan\travel-blog
python -m pytest tests -q -p no:cacheprovider
```

新增专项测试：`tests/test_conversion_optimizations.py`（26 项），覆盖：
主题→产品映射、软推荐短代码格式、产品统计、分类映射/规范化、深度优化内容补充、
Lead Magnet PDF 生成、GSC 优化页 URL 提取。

> 注：本任务有意修改了多篇文章（联盟链接、分类、深度优化），因此更新了部分
> 既有监管测试的"允许修改白名单"以纳入本次优化范围，但保留了 content_id、
> canonical、URL 驱动、禁止虚构体验等核心不变式检查。

---

## 新增/修改文件清单

| 文件 | 类型 | 说明 |
|------|------|------|
| `scripts/affiliate_link_builder.py` | 重写 | 主题匹配 + 软推荐 + 100%覆盖 |
| `layouts/shortcodes/soft-recommend.html` | 新建 | Editorial 软推荐短代码 |
| `scripts/affiliate_product_stats.py` | 新建 | 分产品转化统计 |
| `scripts/feishu_weekly_report.py` | 修改 | 周报分产品转化对比板块 |
| `scripts/generate_lead_magnet_pdf.py` | 新建 | Lead Magnet PDF 生成 |
| `static/lead-magnet/china-visa-free-entry-checklist.pdf` | 新建 | PDF 产物 |
| `layouts/partials/email-subscribe.html` | 重写 | 分类切换 Lead Magnet + AJAX 订阅 |
| `functions/api/subscribe.js` | 新建 | MailerLite + Resend 自动发 PDF |
| `scripts/feishu_daily_report.py` | 修改 | 订阅零增长告警 |
| `scripts/content_category_normalizer.py` | 新建 | 分类体系规范化 |
| `scripts/content_deep_optimizer.py` | 新建 | Top10 深度优化 |
| `scripts/gsc_index_submit.py` | 修改 | 批量提交优化页索引 |
| `tests/test_conversion_optimizations.py` | 新建 | 优化功能测试 |
| `docs/conversion_optimizations.md` | 新建 | 本说明文档 |
