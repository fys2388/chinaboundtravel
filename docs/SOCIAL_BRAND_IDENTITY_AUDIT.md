# ChinaBound Travel — Social / Brand Identity Audit (P0.5-6)

> 审计日期：2026-08-12
> 审计前提：Joran = ChinaBound Travel 的 Editorial Persona（编辑人格），不是需要被包装成真实旅游博主的真人。
> ChinaBound Travel = China Travel Information Platform（中国旅行信息平台）。
> 本审计只做扫描与分类，不修改任何线上内容、社媒账号、历史帖子与网站正文。

## 1. 审计范围与方法

- 全仓扫描 833 个文件，排除 `node_modules/`、`public/`、`.git/`、构建产物/缓存/日志目录。
- 检索 40+ 组关键词：`5 years in China`、`lived in China`、`married to a Chinese`、`my wife`、`I personally`、`I visited/stayed/traveled`、`firsthand experience`、`California native`、`Chengdu son-in-law` 等，共 376 处匹配。
- 覆盖：Instagram / Facebook / X(Twitter) / Pinterest / TikTok 相关文案、YouTube channel description、YouTube video templates、Buffer 相关 social templates、`social_distributor.yml`、`content-rotation.yml`、`chinaboundtravel_social_bot/` 全部 prompt 与模板、newsletter/email 模板、网站 About / Author / JSON-LD。

## 2. 总体结果

| 项目 | 结果 |
|---|---|
| 扫描文件数 | 833 |
| 匹配总数 | 376 |
| 涉及问题文件 | 约 60 |
| A（安全，无需修改） | 约 30（workflows / bot 无 persona 逻辑 / 治理配置 / 日志 / SEO slug 与 URL 引用） |
| B（第一人称但不构成虚假经历） | 4 |
| C（明确虚构真人经历，需要修改） | 约 26 处模板/配置 + 41 篇线上文章正文 |

**重要结论：自动社媒生成系统仍在大量使用旧 Joran 人格。** 除 `joran_blog_generator.py`（P0-1 已改为 editorial persona 并加禁止规则）外，`social_publisher.py`、`config.py` 的 AUTHOR_BIO、`medium_templates.md`、Quora CSV 等仍在使用"加州人 + 成都女婿 + 5/10 年旅居"的虚构人设，属于 P0。

## 3. P0 — 站点元数据 / 自动社媒系统 / 模板中的虚构人设（共 19 项）

### 3.1 站点元数据 / SEO / JSON-LD

| # | platform | file | line | current wording | risk | classification | priority |
|---|---|---|---|---|---|---|---|
| 1 | Site meta | `hugo.toml` | 21 | `Written by an American married into a Chengdu family.` | 全站 description 把 Joran 写成真实旅居者 | C | P0 |
| 2 | Homepage | `hugo.toml` | 39 | `A California native married into a Chengdu family. I've spent 5 years making every single travel mistake in China so you don't have to.` | 首页副标题虚构真实经历 | C | P0 |
| 3 | JSON-LD | `layouts/partials/templates/schema_json.html` | 102 | `"A California native married into a Chengdu family with 5 years of China travel experience."` | Google 结构化数据宣称虚构履历，存在内容质量与合规风险 | C | P0 |
| 4 | Ebook | `ebook_data.json` | 48 | `I'm Joran - American, based in Chengdu, married into a Sichuan family since 2017. I've visited 23 of China's 34 provinces.` | 电子书作者简介虚构旅行履历 | C | P0 |

推荐替换为 editorial 表述：
- `hugo.toml` → `Practical travel guides for China — visa, payments, transport, and city guides, researched and verified by the ChinaBound Travel editorial team.`
- `schema_json.html` → `Editorial persona of ChinaBound Travel, a China travel information platform. All guides are researched and verified from official sources.`
- `ebook_data.json` → `Joran is the editorial voice of ChinaBound Travel. This guide is compiled and verified by the ChinaBound Travel editorial team.`

### 3.2 自动社媒生成系统（chinaboundtravel_social_bot）

| # | platform | file | line | current wording | risk | classification | priority |
|---|---|---|---|---|---|---|---|
| 5 | Social (all) | `chinaboundtravel_social_bot/social_publisher.py` | 368 | `✅ Expert tips from 5 years living in China` | 每条社媒帖子模板虚构 5 年旅居 | C | P0 |
| 6 | Social (all) | `chinaboundtravel_social_bot/social_publisher.py` | 396 | `• Local secrets from a 5-year expat` | 同上 | C | P0 |
| 7 | Social (all) | `chinaboundtravel_social_bot/social_publisher.py` | 414 | `I've lived in China for 5 years & here's what I WISH I knew before my first trip:` | 第一人称虚构经历 | C | P0 |
| 8 | Bio (all) | `chinaboundtravel_social_bot/config.py` | 105 | `AUTHOR_BIO = """I'm a travel writer ... I've lived in Beijing, Shanghai, and Chengdu, and traveled to over 30 Chinese cities.` | 社媒账号 bio 虚构真实履历 | C | P0 |
| 9 | Medium | `chinaboundtravel_social_bot/content/templates/medium_templates.md` | 15 | `A practical guide by Joran, California native and Chengdu son-in-law` | Medium 文末作者行虚构身份 | C | P0 |
| 10 | Medium | `chinaboundtravel_social_bot/content/templates/medium_templates.md` | 54 | `I'm Joran, a California native married into a Chengdu family. I've spent the last 10 years ...` | Medium 模板开篇虚构经历 | C | P0 |
| 11 | Quora | `chinaboundtravel_social_bot/content/social_media_dataset_cbt_2026.csv` | 51 | `I have been living in and traveling China for 10+ years. ...` | Quora 答案数据集虚构 10+ 年经历 | C | P0 |
| 12 | Quora | `chinaboundtravel_social_bot/content/write_csv.py` | 13 | `["...", "I have been living in and traveling China for 10+ years..."]` | 生成 Quora 数据的脚本同样虚构 | C | P0 |
| 13 | Social ops | `chinaboundtravel_social_bot/六大社媒发帖规则界面手册.md` | 28/83 附近 | `Just spent 7 days overlanding through Western Sichuan — here's what no one tells you` / `From Chengdu to Kangding, Tagong Grassland to Yajiang...` | 运营手册示例帖虚构第一人称经历 | C | P0 |

推荐替换：
- 帖子模板 → `China travel tips researched and verified by the ChinaBound Travel editorial team` / `What every first-time China traveler should know`
- `AUTHOR_BIO` → `Joran is the editorial voice of ChinaBound Travel — a China travel information platform. Guides are researched from official sources and verified by the editorial team.`

### 3.3 站点模板 / 联盟披露 / About

| # | platform | file | line | current wording | risk | classification | priority |
|---|---|---|---|---|---|---|---|
| 14 | Website | `layouts/partials/travel-promo.html` | 4 | `Hand-picked services Joran uses personally after 5 years of living in China — tested, trusted, no fluff` | 全站服务推荐虚构个人使用经历 | C | P0 |
| 15 | Website | `layouts/partials/travel-promo.html` | 76 | `We only recommend tools we've personally used.` | FTC 披露声明断言虚构使用经历 | C | P0 |
| 16 | Website | `layouts/_default/single.html` | 41 | `I only recommend products I personally use and trust.` | 文章页联盟披露虚构个人使用 | C | P0 |
| 17 | Website | `layouts/_default/single.html` | 44 | `Save time & money with Joran's personally tested recommendations:` | 文章页联盟 CTA 虚构"亲自测试" | C | P0 |
| 18 | Website | `layouts/partials/affiliate-disclosure.html` | 8 | `We only recommend tools and services Joran has personally used and trusts.` | 联盟披露组件虚构个人使用 | C | P0 |
| 19 | Website | `layouts/shortcodes/affiliate-disclosure.html` | 7 | 同 18 | 与 18 重复的 shortcode 版本 | C | P0 |

推荐替换：`We only recommend services evaluated by the ChinaBound Travel editorial team. As an affiliate we may earn a commission at no extra cost to you.`（避免断言"Joran 本人使用过/测试过"；如确需保留个人背书，必须改为可验证事实。）

## 4. P1 — 线上文章正文与 bot 内容/草稿中的虚构人设

线上 43 篇文章中约 41 篇正文含虚构第一人称经历（`I remember my first trip`、`my wife`、`5 years living in China`、`California native`、`expat` 等）。按用户要求，本次只审计不修改正文。

### 4.1 content/posts/ 线上文章（41 篇 C 类 + 1 篇 B 类 + 1 篇 A 类）

144-hour-visa-free-transit-guide.md、2026-05-20-china-just-made-it-way-easier-to-visit-my-mother-i.md、2026-05-20-dude-wheres-my-panda-a-beijing-guys-guide-to-the-c.md、2026-05-20-shanghai-like-a-local-hidden-neighborhoods-tourist.md、2026-05-26-7-day-china-itinerary-beijing-xian-shanghai-first-timers.md、2026-05-26-hangzhou-west-lake-tea-culture-g20-guide.md、2026-06-19-the-history-and-culture-of-the-great-wall-beyond-the-tourist-trail-guide.md、2026-06-22-chinese-tea-culture-history-types-and-tea-ceremony-guide.md、2026-06-22-shanghai-beyond-the-bund-hidden-neighborhoods-and-local-culture.md、2026-06-23-sichuan-hotpot-guide-history-best-restaurants-and-cultural-significance.md、2026-06-30-xian-terracotta-army-history-discovery-and-insider-tips.md、2026-07-01-chinese-street-food-a-first-timers-guide-to-night-markets-and-street-stalls.md、2026-07-02-how-to-use-alipay-as-a-foreigner-complete-setup-guide-2026-guide.md、2026-07-02-wechat-pay-for-foreigners-step-by-step-setup-and-common-mistakes-to-avoid-guide.md、2026-07-03-guilin-and-yangshuo-the-ultimate-karst-landscape-guide-for-2026-guide.md、2026-07-04-china-high-speed-train-survival-guide-booking-classes-and-insider-tips.md、2026-07-05-yunnan-adventure-rice-terraces-ancient-towns-and-ethnic-minorities-guide.md、2026-07-06-a-gastronomic-adventure-in-china-a-foodies-guide-for-european-travelers.md、2026-07-07-navigating-chinas-accommodation-maze-a-californians-guide-for-aussie-and-kiwi-travelers.md、2026-07-10-a-gastronomic-adventure-in-china-food-recommendations-for-international-travelers.md、2026-07-12-navigating-chinas-transportation-a-californians-guide-for-european-travelers.md、2026-07-13-navigating-china-with-confidence-a-californians-guide-to-travel-safety.md、2026-07-14-transportation-guide-guide.md、2026-07-16-china-transportation-complete-guide-trains-subways-taxis-and-more.md、2026-07-16-food-recommendations-guide.md、2026-07-16-is-china-safe-for-tourists-2026-honest-safety-assessment.md、2026-07-20-travel-safety-guide.md、2026-07-21-cultural-etiquette-guide.md、2026-07-22-cultural-etiquette-guide.md、2026-07-23-foodies-guide-to-china-a-gastronomic-adventure.md、2026-07-31-china-remote-work-guide-a-californians-5-year-chengdu-experience.md、2026-08-01-chinabound-travel-guide-2026-08-monthly-update.md、2026-08-05-china-family-travel-tips-a-californians-guide.md、2026-08-07-china-bargaining-and-shopping-guide.md、2026-08-09-china-packing-list-2026-what-to-bring-and-what-to-leave-at-home.md、2026-08-10-chinas-food-through-the-ages-guide.md、2026-08-10-shanghai-vs-beijing-which-chinese-city-should-you-visit-first-guide.md、2026-08-11-chinese-tea-culture-where-to-experience-authentic-teahouses.md、2026-08-12-china-national-parks-zhangjiajie-jiuzhaigou-and-beyond-guide.md、best-travel-insurance-china.md、china-extends-144-hour-visa-free-transit-policy-to-more-countries.md、internet-connection-china-esim-vpn-guide.md、western-sichuan-overland-camping-route.md

典型高风险示例：
- `content/posts/2026-07-20-travel-safety-guide.md:262` → `I've lived in China for 5 years, traveled to 23 provinces, and I've never felt threatened.`
- `content/posts/2026-07-20-travel-safety-guide.md:33` → `...standing at Chengdu Tianfu Airport, fresh off a 14-hour flight from LA with my wife Xiao Li...`
- `content/posts/2026-07-23-foodies-guide-to-china-a-gastronomic-adventure.md:30` → `As an American expat who has lived in Chengdu for over 5 years...`
- `content/posts/2026-08-10-chinas-food-through-the-ages-guide.md:31` → `I have lived in Chengdu for over a decade...`
- `content/posts/2026-08-12-china-national-parks-zhangjiajie-jiuzhaigou-and-beyond-guide.md:33` → `I remember my first trip to China... I was a wide-eyed California native...`
- `content/posts/best-travel-insurance-china.md:103` → `After personally using SafetyWing for 2+ years (and helping hundreds of readers pick plans over my 5 years in China)...`
- `content/posts/china-extends-144-hour-visa-free-transit-policy-to-more-countries.md:27` → `I'm Joran, your friendly California guy who married a local Chengdu girl and has been living in China for years.`
- `content/posts/internet-connection-china-esim-vpn-guide.md:27/31` → `my wife` Wi-Fi 故事（虚构对话与经历）
- `content/posts/western-sichuan-overland-camping-route.md:31/33/45` → 妻子 + 露营 + "Five years living in China" 虚构故事

注：`2026-08-01-chinabound-travel-guide-2026-08-monthly-update.md` 为 B 类（工作流程第一人称，不构成虚假旅行经历）；`2026-08-03-chinese-language-survival-phrases-guide.md` 仅 summary 提到受众（for American travelers），为 A 类。

### 4.2 bot 内容 / 草稿 / 归档（14 个文件，不对外发布，处理优先级低）

- `chinaboundtravel_social_bot/content/posts/*.md`：5/15 篇含虚构，如 `7-day-china-first-timer-itinerary-beijing-xian-shanghai.md:29`、`best-time-to-visit-china-2026-monthly-guide.md:27`、`china-packing-list-2026-what-to-bring.md:92`。
- `content/posts/drafts/`：2/2 篇含 `my wife`、`married to a Chengdu woman` 等虚构（`2026-05-20-*.md`）。
- `content/posts/.audit_backup/`：7/8 篇含 `my wife Xiao Li`、`Six years living in China` 等（历史备份，不发布）。
- `content/posts/.archived/`：4 篇含虚构（`2026-07-08`、`2026-07-09`、`2026-07-11`、`2026-08-08`，已归档不发布）。

## 5. B 类 — 第一人称但不构成虚假经历（4 处，建议顺手改为团队口径）

| # | platform | file | line | current wording | note |
|---|---|---|---|---|---|
| B1 | Blog | `content/posts/2026-08-01-chinabound-travel-guide-2026-08-monthly-update.md` | 32 | `updates that I personally verified throughout July` | 改为 `verified by the editorial team` 更稳妥 |
| B2 | Blog | `chinaboundtravel_social_bot/content/posts/2026-05-27-7-day-china-first-timer-itinerary-beijing-xian-shanghai.md` | 148 | `I personally respond to every legitimate question within 48 hours` | 改为 `We respond to every legitimate question within 48 hours` |
| B3 | Doc | `SAFETYWING_AFFILIATE_GUIDE.md` | 195 | `I only recommend products I personally use and trust.` | 内部文档，不影响线上；如沿用需与 3.3 联盟披露口径一致 |
| B4 | Blog | `content/posts/2026-05-27-china-packing-list-2026-what-to-bring.md`（bot 目录 92 行处） | 92 | `the VPN I personally use, and the eSIM service that has never let me down` | 建议改为 `our top-rated VPN and eSIM services, evaluated by the editorial team` |

## 6. A 类 — 安全，无需修改（摘要）

- **Workflows**：`social_distributor.yml`、`content-rotation.yml`、`youtube-auto-publish.yml` 无 persona 相关内容。
- **Bot 无 persona 逻辑模块**：`social_distributor.py`、`weekly_update.py`、`ai_editor.py`、`content_manager.py`、`all_in_one_poster.py`、`article_to_video.py`、`youtube_auto_upload.py`、`buffer_scheduler.py`、`publisher.py`、`auto_post_all.py`、`auto_post_v2.py` 等。
- **治理配置（P0-1 产物）**：`config/content_governance.json`、`scripts/persona_guard.py`、`tests/test_persona_governance.py`、`chinaboundtravel_social_bot/joran_blog_generator.py` 中新增的 editorial 规则与禁止清单。
- **站点模板无虚构部分**：`layouts/partials/author.html`、`sidebar-author.html`、`email-subscribe.html`、`ebook-promo.html`。
- **日志/报告/缓存**：`reports/*`、`*.log`、`manifest*.json`、`.pytest_cache`；slug 与 URL 中的 `californians-guide` 属于既有 SEO URL，**不允许改动**；`TAG_NAMING_CONVENTION.md`/`keyword_research.py` 中的 `expat` 等仅为 SEO 关键词，不构成 persona 声明。

## 7. 需要修改的自动系统清单

| 系统 | 结论 |
|---|---|
| 生成端 `joran_blog_generator.py` | 已由 P0-1 改为 editorial persona 并加入禁止规则 ✅ |
| 审核端 `ai_editor.py` / 其他 AI 审核 | 无 persona 虚构内容 ✅ |
| 社媒发布端 `social_publisher.py` | 3 处模板文案为虚构人设，P0，需修改 |
| 账号 bio `config.py` AUTHOR_BIO | 虚构履历，P0，需修改 |
| Medium 模板 `medium_templates.md` | 3 处虚构，P0，需修改 |
| Quora 数据集 CSV / write_csv.py | 虚构答案数据，P0，需修改 |
| 站点模板/披露文案 | 6 处虚构"个人使用/测试"声明，P0，需修改 |

## 8. 风险总结

- **最高风险（线上可见 + 自动系统）**：3 个区域共 19 项 P0 —— 全站 meta、JSON-LD、电子书、社媒发布模板、账号 bio、Medium/Quora 模板、联盟披露组件。这些是 Google 结构化数据、全站文案与自动发帖的直接来源，必须优先改为 editorial persona（建议 `persona_guard.py` 同步覆盖）。
- **高风险（文章正文，暂不修改）**：41 篇线上文章 + 14 篇 bot 内容/草稿/归档。文章正文的 `I've lived in China for 5 years` 等需人工/批量改写为 `ChinaBound Travel editors have spent 5 years covering China travel` 之类的团队口径（P1，人工审核后处理，防止破坏 SEO 正文结构）。
- **中风险（账号后台）**：bio/简介在 Instagram、Facebook、X、Pinterest、TikTok、YouTube、Buffer 账号后台的现有文案，需人工在账号后台更新（本次不改线上账号）。
- **优先级**：P0 = 上述 19 项代码/模板/配置；P1 = 41 篇正文与 bot 内容；P2 = 4 处 B 类措辞。

## 9. 建议

- 本阶段仅审计，未修改任何线上可见内容；线上账号与历史帖子保持原样。
- SEO URL（含 `-californians-guide` 类 slug）、canonical、redirects、affiliate URL 一律不改。
- 修复顺序建议：3.1 站点 meta/JSON-LD → 3.2 社媒模板/账号 bio → 3.3 联盟披露 → 4.1 文章正文（人工审核批次改写）。
