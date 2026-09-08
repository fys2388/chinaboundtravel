# ChinaBound Travel — 自动化闭环配置文档

> **版本**: v1.0 | **配置日期**: 2026-09-08 | **自动化程度**: 90%+
> **站点**: Hugo + PaperMod + Cloudflare Pages | **baseURL**: https://www.chinaboundtravel.com/

---

## 一、闭环总览

4 个自动化闭环覆盖"数据→分析→决策→执行→验证→学习"完整链路，按优先级和执行日排列：

| 闭环 | 名称 | 优先级 | 运行日 (UTC) | 核心数据源 | 自动动作 | 安全阈值 |
|------|------|--------|-------------|-----------|---------|---------|
| 1 | 内容生产自动优化 | P1 | 周一 02:00 | GSC + GA4 | Title/Description/首段/FAQ/内链优化 | ≤2 篇/周 |
| 2 | SEO 增长自动闭环 | P1 | 周二 02:00 | GSC 关键词 | 内链补充/Title优化/FAQ Schema/重新索引 | ≤20内链, ≤10 Title |
| 3 | Affiliate 转化优化 | P2 | 周三 02:00 | GA4 + Travelpayouts | CTA A/B测试/意图匹配调整/RPM优化 | ≤10 CTA/周 |
| 4 | Email 增长自动化 | P2 | 周四 02:00 | MailerLite + GA4 | 7天序列追踪/效果报告 | 无修改阈值 |

---

## 二、闭环 1：内容生产自动优化闭环

### 2.1 触发条件（每周一扫描 GSC 页面数据）

| 条件 | 阈值 | 问题类型 |
|------|------|---------|
| Impressions > 10 且 Clicks = 0 | CTR 问题 | Title/Description 不吸引 |
| 排名下降 > 5 位（与上周基线对比） | 排名衰退 | 内容过时/竞争加剧 |
| 平均停留 < 10 秒 | 内容质量 | 首段不匹配意图/内容深度不足 |

### 2.2 自动分析与执行

脚本 `scripts/content_auto_optimizer.py` 对每个问题页面执行原因分类：

- **Title CTR 问题** → 自动优化 front matter `title`（含数字/年份/情感词，≤60字符）
- **首段不匹配搜索意图** → 自动重写首段（包含目标关键词，150-200字符）
- **内容深度不足** → 标记为高风险，生成 PR 待人工审核（>30% 重写）
- **内链缺失** → 自动从相关文章添加内链（按关键词重叠度排序）
- **FAQ 缺失** → 自动添加 `## FAQ` section（按主题生成 3-5 个问答）

**低风险动作**（Title/Description/首段/FAQ/内链）自动执行并提交 main，触发 Cloudflare Pages 部署。
**高风险动作**（>30% 内容重写）创建 git branch + PR 描述，不自动合并。

### 2.3 安全阈值

- **每周最多自动修改 2 篇文章**（`MAX_AUTO_OPTIMIZE_PER_WEEK = 2`）
- 所有修改必须通过 Hugo 构建验证（`hugo --gc --minify`），构建失败自动回滚该文件
- 支持 `--dry-run` 模式（只分析不修改）
- 支持 `--max-pages N` 覆盖默认阈值

### 2.4 自动验证与学习

- 每次优化记录到 `reports/content-optimization-log.json`（页面、动作、时间戳、修改前指标）
- 部署后 2 周自动跟踪 impressions/clicks/CTR/排名变化
- 生成效果报告 `reports/content-optimization-results-YYYY-MM-DD.md`
- 优化有效 → 记录到 `reports/learning-library.json`；无效 → 标记需回滚

### 2.5 工作流

- **文件**: `.github/workflows/content-auto-optimize.yml`
- **Schedule**: `cron: '0 2 * * 1'`（周一 UTC 02:00 = 北京时间 10:00）
- **手动触发**: `workflow_dispatch`（含 `dry_run` 和 `max_pages` 参数）
- **步骤**: Checkout → Python 3.12 → 安装依赖 → Hugo 0.147.0 → 写入 GSC 密钥 → 运行优化器 → Hugo 构建验证 → Git commit & push → 上传报告 artifact
- **Concurrency**: `content-auto-optimize`（防止并发）

---

## 三、闭环 2：SEO 增长自动闭环

### 3.1 触发条件（每周二扫描 GSC 关键词数据）

| 条件 | 阈值 | 机会类型 |
|------|------|---------|
| 新关键词进入 Top 20 | 排名 ≤ 20 且上期 > 20 | 增长潜力 |
| 关键词排名下降 > 5 位 | 本期 - 上期 > 5 | 衰退预警 |
| 关键词 CTR < 1% | 有展示无点击 | Title/摘要优化 |
| 页面内链数 < 3 | 内链不足 | 内链建设 |

### 3.2 自动动作

脚本 `scripts/seo_auto_optimizer.py` 执行：

1. **搜索意图匹配分析**：对比关键词与页面 title/首段的匹配度
2. **内链优化**：扫描所有文章，按主题相关度添加指向目标页面的内链（优先从 Top 20 Growth Pages 链接）
3. **Title 优化**：在 front matter title 中自然融入目标关键词（colon 策略，已包含核心词时保守跳过）
4. **FAQ Schema 补充**：针对长尾关键词添加 FAQ section（visa/payment/transport 四套模板）
5. **Sitemap 更新 + 重新索引**：Hugo 重建后自动生成 sitemap，通过 GSC Indexing API（`urlNotifications:publish`，SCOPE_INDEXING）请求重新索引

### 3.3 安全阈值

- **每周最多添加 20 个内链**（`MAX_INTERNAL_LINKS_PER_WEEK = 20`）
- **每周最多优化 10 个页面 Title**（`MAX_TITLE_OPTIMIZATIONS_PER_WEEK = 10`）
- 所有修改必须通过 Hugo 构建验证
- 支持 `--dry-run` 模式

### 3.4 自动跟踪与学习

- 每周跟踪关键词排名变化，生成 `reports/seo-growth-report-YYYY-MM-DD.md`
- 记录有效优化动作到学习库
- 扩展 `scripts/gsc_keyword_baseline.py`：新增 `--json` 输出、`--compare` 基线对比、`--baseline` 指定对比文件

### 3.5 工作流

- **文件**: `.github/workflows/seo-growth-loop.yml`
- **Schedule**: `cron: '0 2 * * 2'`（周二 UTC 02:00）
- **手动触发**: `workflow_dispatch`（含 `dry_run`、`max_internal_links`、`max_title_optimizations`）
- **步骤**: 同闭环1，运行 `seo_auto_optimizer.py`
- **Concurrency**: `seo-growth-loop`

---

## 四、闭环 3：Affiliate 转化自动优化闭环

### 4.1 触发条件（每周三扫描 GA4 + Travelpayouts 数据）

| 条件 | 阈值 | 问题类型 |
|------|------|---------|
| CTA 展示 > 100 但点击 < 1 | CTR 极低 | CTA 位置/文案/类型问题 |
| CTA 点击率 < 0.5% | 低于基准 | 需要 A/B 测试 |
| 页面有流量但无 Affiliate 点击 | 转化漏斗断裂 | CTA 缺失或意图不匹配 |

### 4.2 自动动作

脚本 `scripts/affiliate_ab_tester.py` 执行：

1. **GA4 数据拉取**：页面级 sessions、page views、affiliate click 事件（GA4 不可用时降级为 CTA inventory 静态分析）
2. **CTA 表现分析**：展示量、点击量、CTR、RPM（Revenue Per Mille）
3. **A/B 测试建议**：对低表现 CTA 建议替换为更高意图匹配的 affiliate（如 Visa 文章优先 Flight+Insurance+eSIM）
4. **自动调整**：修改 front matter `cta_variant` 字段或替换 CTA shortcode 参数
5. **UTM 归因**：`utm_source=blog&utm_medium=cta&utm_campaign=ab_test&utm_content=<variant_id>`

### 4.3 CTA Shortcode

新建 `layouts/shortcodes/affiliate-cta.html`，支持参数：
- `partner`：esim / vpn / hotel / klook / safetywing / trip / flight
- `text`：CTA 文案
- `variant`：button / text / card
- `utm_content`：A/B 测试变体 ID

### 4.4 安全阈值

- **每周最多调整 10 个 CTA**（`--max-adjustments 10`）
- **最小样本量**：展示 > 200 才做判断（流量低时标记"数据不足，继续观察"）
- 所有修改必须通过 Hugo 构建验证
- 支持 `--dry-run` 模式（workflow_dispatch 默认 dry-run=true，schedule 触发时自动执行）

### 4.5 自动归因与学习

- 通过 UTM 参数追踪点击→订单→佣金（Travelpayouts API）
- 计算每个 CTA 的 RPM，自动淘汰低 RPM CTA，增加高 RPM CTA 展示
- 记录到 `reports/affiliate-learning-library.json`
- 生成 `reports/affiliate-ab-test-YYYY-MM-DD.md`

### 4.6 工作流

- **文件**: `.github/workflows/affiliate-optimize.yml`
- **Schedule**: `cron: '0 2 * * 3'`（周三 UTC 02:00）
- **手动触发**: `workflow_dispatch`（默认 dry-run=true）
- **所需 Secrets**: `GA4_SERVICE_ACCOUNT_JSON`、`GA4_API_KEY`、`GA4_PROPERTY_ID`、`TRAVELPAYOUTS_API_TOKEN`、`TRAVELPAYOUTS_MARKER`
- **Concurrency**: `affiliate-optimize`

---

## 五、闭环 4：Email 增长自动化闭环

### 5.1 7 天自动化邮件序列

通过 `scripts/mailerlite_sequence_setup.py` 配置 MailerLite 自动化序列：

| Day | 主题 | 核心内容 | Affiliate 推荐 |
|-----|------|---------|---------------|
| 1 | 欢迎 + 中国旅行基础 | 行前准备、必备应用 | eSIM (Airalo) |
| 2 | Visa 指南 | 签证类型、免签政策、申请流程 | Travel Insurance (SafetyWing) |
| 3 | 支付指南 | Alipay/WeChat Pay 绑定、现金备用 | eSIM + Insurance |
| 4 | eSIM/VPN 深度 | 网络配置、推荐方案 | Airalo eSIM |
| 5 | 酒店选择 | 住宿区域、预订技巧 | Booking |
| 6 | 交通指南 | 高铁购票、机票比价 | Aviasales + Trip.com |
| 7 | 10 天行程模板 | 完整行程规划 + 全品类汇总 | 全品类 Affiliate |

每封邮件 UTM 参数：`utm_source=email&utm_medium=sequence&utm_campaign=7day_china&utm_content=dayN`

### 5.2 MailerLite API 配置状态

- **API 连通性**: ✅ 已验证（account active, 14 active subscribers）
- **Automation Workflow**: ✅ 已创建（name: "7-Day China Onboarding Sequence"）
- **Campaign 创建**: ⚠️ 需验证发件人 `joran@chinaboundtravel.com`（MailerLite 要求 Sender email verified）
- **邮件 HTML 模板**: 7 封已生成，可通过 `python scripts/mailerlite_sequence_setup.py` 重新创建
- **手动配置指南**: `docs/mailerlite-7day-sequence-setup.md`（含后台步骤说明）

### 5.3 自动追踪

脚本 `scripts/email_sequence_tracker.py` 每周拉取：

- **MailerLite API**: 订阅者数、活跃/退订、campaign 打开率、点击率
- **GA4 Data API**: email 渠道流量、落地页、转化事件
- **Travelpayouts API**: email 渠道 affiliate 收入（过滤 utm_source=email）

生成 `reports/email-marketing-report-YYYY-MM-DD.md`，包含：订阅数、打开率、点击率、CTR、affiliate 点击、收入、RPM。

### 5.4 工作流

- **文件**: `.github/workflows/email-growth-loop.yml`
- **Schedule**: `cron: '0 2 * * 4'`（周四 UTC 02:00）
- **手动触发**: `workflow_dispatch`（含 `dry_run`、`days` 回看天数）
- **此 workflow 只读不修改内容**，仅生成并提交报告
- **所需 Secrets**: `MAILERLITE_API_TOKEN`、`GA4_SERVICE_ACCOUNT_JSON`、`GA4_API_KEY`、`GA4_PROPERTY_ID`、`TRAVELPAYOUTS_API_TOKEN`
- **Concurrency**: `email-growth-loop`

---

## 六、文件清单

### 工作流（.github/workflows/）

| 文件 | 闭环 | 大小 |
|------|------|------|
| `content-auto-optimize.yml` | 1 | 3.4 KB |
| `seo-growth-loop.yml` | 2 | 3.6 KB |
| `affiliate-optimize.yml` | 3 | 3.5 KB |
| `email-growth-loop.yml` | 4 | 2.7 KB |

### 脚本（scripts/）

| 文件 | 闭环 | 大小 | 说明 |
|------|------|------|------|
| `content_auto_optimizer.py` | 1 | 38.7 KB | 内容自动优化核心 |
| `seo_auto_optimizer.py` | 2 | 31.8 KB | SEO 增长优化核心 |
| `gsc_keyword_baseline.py` | 2 | 21.6 KB | 扩展版（新增 --json/--compare） |
| `affiliate_ab_tester.py` | 3 | 36.8 KB | Affiliate A/B 测试 |
| `mailerlite_sequence_setup.py` | 4 | 47.8 KB | MailerLite 序列配置 |
| `email_sequence_tracker.py` | 4 | 23.1 KB | 邮件效果追踪 |

### 模板与文档

| 文件 | 说明 |
|------|------|
| `layouts/shortcodes/affiliate-cta.html` | CTA shortcode（5.7 KB） |
| `docs/auto-optimization-loops.md` | 本文档 |
| `docs/mailerlite-7day-sequence-setup.md` | MailerLite 手动配置指南 |

### 测试文件（tests/）

| 文件 | 说明 |
|------|------|
| `test_content_optimizer_logic.py` | 闭环1 单元测试（8/8 通过） |
| `test_seo_optimizer_logic.py` | 闭环2 单元测试 |

---

## 七、GitHub Secrets 配置清单

在 GitHub 仓库 Settings → Secrets and variables → Actions 中配置：

| Secret 名称 | 用途 | 闭环 | 状态 |
|-------------|------|------|------|
| `GSC_SERVICE_ACCOUNT_JSON` | GSC 服务账号密钥全文 | 1, 2 | 需配置 |
| `GA4_SERVICE_ACCOUNT_JSON` | GA4 服务账号密钥 | 3, 4 | 需配置 |
| `GA4_API_KEY` | GA4 API Key | 3, 4 | 需配置 |
| `GA4_PROPERTY_ID` | GA4 属性 ID (541752321) | 3, 4 | 需配置 |
| `TRAVELPAYOUTS_API_TOKEN` | Travelpayouts API Token | 3, 4 | 需配置 |
| `TRAVELPAYOUTS_MARKER` | Travelpayouts Marker (730795) | 3, 4 | 需配置 |
| `MAILERLITE_API_TOKEN` | MailerLite API Token | 3, 4 | 需配置 |
| `CLOUDFLARE_API_TOKEN` | Cloudflare Pages 部署 | 部署 | 已配置 |

---

## 八、首次运行测试结果

### 构建与语法验证

| 检查项 | 结果 |
|--------|------|
| Python 脚本 py_compile（6个） | ✅ 全部通过 |
| Workflow YAML 语法（4个） | ✅ 全部通过 |
| Hugo 构建（441 页面） | ✅ 通过（13秒，无错误） |

### 闭环 1 测试

- Dry-run 执行：GSC API 因本地网络超时（WinError 10060，中国境内访问 Google API），脚本**优雅退出**并生成错误报告，未修改任何文件
- 核心逻辑测试：8/8 通过（find_post_by_url、parse_post、analyze_page_issues、optimize_title、optimize_description、generate_faq_section、find_related_posts、modify_front_matter_field）
- GitHub Actions ubuntu-22.04 环境无网络限制，可正常拉取 GSC 数据

### 闭环 2 测试

- gsc_keyword_baseline 扩展：`--json`、`--compare`、`--baseline` 全部通过
- seo_auto_optimizer 逻辑：Title 优化、内链查找、FAQ 生成、低内链页面检测（识别 10 篇内链<3）全部通过
- Indexing API 函数已实现（SCOPE_INDEXING）

### 闭环 3 测试

- CTA inventory 加载：187 条记录
- GA4 API：本地超时 → 自动降级为静态分析
- Travelpayouts API：直连成功（28天 89 clicks, $0.00）
- 低表现 CTA：0（全部因无 GA4 流量数据标记 insufficient_data）
- Hugo 构建：新 shortcode 不影响现有站点

### 闭环 4 测试

- MailerLite API：连通成功（14 active subscribers）
- Automation workflow：创建成功
- Campaign 创建：发件人未验证（需手动验证 joran@chinaboundtravel.com）
- email_sequence_tracker：运行成功，报告已生成

---

## 九、需要手动完成的事项

1. **验证 MailerLite 发件人**：在 MailerLite 后台 Settings → Sender addresses 验证 `joran@chinaboundtravel.com`，验证后重新运行 `python scripts/mailerlite_sequence_setup.py` 创建 7 个 campaign
2. **配置 MailerLite Automation 步骤**：workflow 容器已创建，按 `docs/mailerlite-7day-sequence-setup.md` 添加 7 个 "Send email" 节点和 6 个 "Wait 1 day" 节点
3. **配置 GitHub Secrets**：按第七节清单配置所有 secrets
4. **清理测试 Automation**：调试过程中创建了多个同名空 workflow，在 MailerLite 后台保留一个即可

---

## 十、闭环运行时间表（北京时间）

| 日期 | 时间 | 闭环 | 动作 |
|------|------|------|------|
| 周一 | 10:00 | 1 | 内容优化 → 自动部署 |
| 周二 | 10:00 | 2 | SEO 增长 → 自动部署 |
| 周三 | 10:00 | 3 | Affiliate 优化 → 自动部署 |
| 周四 | 10:00 | 4 | Email 报告 → 仅报告 |
| 持续 | — | 部署 | push to main 触发 Cloudflare Pages 部署 |

---

*文档生成时间: 2026-09-08 | 维护者: ChinaBound Travel 自动化系统*
