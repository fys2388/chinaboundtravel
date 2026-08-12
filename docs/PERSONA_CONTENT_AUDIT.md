# ChinaBound Travel — Persona 历史内容审计（P0.5 第 5 项）

> 审计日期：2026-08-12
> 原则：Joran = ChinaBound Travel 的 Editorial Persona（编辑人格）。禁止虚构真实旅游经历、家庭经历、住宿/出行/支付/签证等个人经验。
> 本审计只列出问题与建议，不直接修改任何线上正文 / About / JSON-LD / SEO 元数据。

## 1. 审计范围

搜索整个站点（833 文件，排除构建/缓存/日志），重点关键词：`married into a Chengdu family`、`5 years of China travel experience`、`personal travel experience`、`I stayed`、`I visited`、`my wife`、`my family`、`personally experienced`、`lived in China`、`California native`、`Chengdu son-in-law`、`American expat` 等，共 376 处匹配。

重点检查对象：JSON-LD、About 页、author bio、首页（hugo.toml）、电子书、已有文章正文、社媒发布模板。

## 2. 站点级高风险项（P0，代码/配置/模板层）

| # | file | line | current claim | risk | recommended replacement | priority |
|---|---|---|---|---|---|---|
| 1 | `hugo.toml` | 21 | `Written by an American married into a Chengdu family.` | 全站 meta description 把 Joran 写成真实旅居者 | `Practical travel guides for China — visa, payments, transport, and city guides, researched and verified by the ChinaBound Travel editorial team.` | P0 |
| 2 | `hugo.toml` | 39 | `A California native married into a Chengdu family. I've spent 5 years making every single travel mistake in China so you don't have to.` | 首页副标题虚构真实经历 | `Practical, verified China travel guides — visa, payments, transport, and city guides, researched by the ChinaBound Travel editorial team.` | P0 |
| 3 | `layouts/partials/templates/schema_json.html` | 102 | `"A California native married into a Chengdu family with 5 years of China travel experience."` | JSON-LD 宣称虚构履历，Google 结构化数据风险 | `"Editorial persona of ChinaBound Travel, a China travel information platform. All guides are researched and verified from official sources."` | P0 |
| 4 | `ebook_data.json` | 48 | `I'm Joran - American, based in Chengdu, married into a Sichuan family since 2017. I've visited 23 of China's 34 provinces.` | 电子书作者简介虚构旅行履历 | `Joran is the editorial voice of ChinaBound Travel. This guide is compiled and verified by the ChinaBound Travel editorial team.` | P0 |
| 5 | `content/about/_index.md` | 12 | `American Expat &middot; Chengdu Husband &middot; China Travel Guy` | About 页标题虚构身份 | `China Travel Information Platform &middot; Editorial Voice` | P0 |
| 6 | `content/about/_index.md` | 38 | `...Chinese visa rules change faster than my wife's mood during mango season.` | 虚构家庭经历 | 删除该比喻，改为团队口径 | P0 |
| 7 | `content/about/_index.md` | 49 | `American expat, Sichuan husband, and your go-to China travel guy` | About 页简介虚构身份 | `ChinaBound Travel is a China travel information platform. Joran is its editorial voice.` | P0 |
| 8 | `content/cities/chengdu.md` | 9 | `Chengdu is my home. I've lived here for years, married into a Sichuan family...` | 城市页虚构居住经历 | `Chengdu, covered extensively by the ChinaBound Travel editorial team — local logistics, food, and transport for first-time visitors.` | P0 |
| 9 | `chinaboundtravel_social_bot/config.py` | 105 | `AUTHOR_BIO = """I'm a travel writer ... I've lived in Beijing, Shanghai, and Chengdu, and traveled to over 30 Chinese cities.` | 社媒账号 bio 虚构履历 | `Joran is the editorial voice of ChinaBound Travel — a China travel information platform. Guides are researched from official sources and verified by the editorial team.` | P0 |
| 10 | `config/global_rules.py` | 10 | `AUTHOR_BIO = "A California native married to a Chengdu local, Joran has been traveling across China for over 10 years..."` | 全局规则中的虚构 bio（如仍被引用需同步修改） | 同上 editorial bio | P0 |
| 11 | `chinaboundtravel_social_bot/README.md` | 24 | `**Joran** - California native, Chengdu son-in-law, 10+ years of China travel experience.` | bot 文档虚构身份 | `**Joran** - editorial voice of ChinaBound Travel.` | P0 |
| 12 | `chinaboundtravel_social_bot/social_publisher.py` | 368 / 396 / 414 | `Expert tips from 5 years living in China` / `Local secrets from a 5-year expat` / `I've lived in China for 5 years & here's what I WISH I knew...` | 社媒发帖模板虚构经历 | `China travel tips researched and verified by the ChinaBound Travel editorial team` / `What every first-time China traveler should know` | P0 |
| 13 | `chinaboundtravel_social_bot/content/templates/medium_templates.md` | 15 / 54 / 189 | `Joran, California native and Chengdu son-in-law` / `I'm Joran, a California native married into a Chengdu family...` / `Joran is a California native married to a Chengdu local...` | Medium 模板虚构身份 | `A guide by ChinaBound Travel's editorial team` / `Joran is the editorial voice of ChinaBound Travel...` | P0 |
| 14 | `chinaboundtravel_social_bot/content/social_media_dataset_cbt_2026.csv` | 51 | `I have been living in and traveling China for 10+ years. ...` | Quora 数据集虚构经历 | 改写为团队口径或删除该条 | P0 |
| 15 | `chinaboundtravel_social_bot/content/write_csv.py` | 13 | `["...", "I have been living in and traveling China for 10+ years..."]` | Quora 数据集生成脚本同样虚构 | 同步改写 | P0 |
| 16 | `layouts/partials/travel-promo.html` | 4 | `Hand-picked services Joran uses personally after 5 years of living in China` | 服务推荐虚构个人使用 | `Services evaluated by the ChinaBound Travel editorial team` | P0 |
| 17 | `layouts/_default/single.html` | 41 / 44 | `I only recommend products I personally use and trust.` / `Joran's personally tested recommendations` | 联盟披露虚构个人测试 | `We only recommend services evaluated by the ChinaBound Travel editorial team.` | P0 |
| 18 | `layouts/cities/single.html` | 33 | `Save time & money with Joran's personally tested recommendations:` | 城市页联盟 CTA 虚构测试 | 同 17 | P0 |
| 19 | `layouts/partials/affiliate-disclosure.html` | 8 | `We only recommend tools and services Joran has personally used and trusts.` | 联盟披露组件 | 同 17 | P0 |
| 20 | `layouts/shortcodes/affiliate-disclosure.html` | 7 | 同 19 | 重复 shortcode | 同 17 | P0 |
| 21 | `layouts/partials/travel-promo.html` | 76 | `We only recommend tools we've personally used.` | 联盟披露声明 | 同 17 | P0 |

## 3. 线上文章正文高风险代表（P1，本次不修改，需人工审核）

| file | line | current claim | risk | recommended replacement | priority |
|---|---|---|---|---|---|
| `content/posts/2026-07-20-travel-safety-guide.md` | 33 | `...standing at Chengdu Tianfu Airport, fresh off a 14-hour flight from LA with my wife Xiao Li...` | 虚构家庭+抵达经历 | `Travelers arriving at Chengdu Tianfu Airport should plan for a long international flight; here's what to expect...` | P1 |
| `content/posts/2026-07-20-travel-safety-guide.md` | 262 | `I've lived in China for 5 years, traveled to 23 provinces, and I've never felt threatened.` | 虚构旅居经历 | `ChinaBound Travel editors have spent 5 years covering China travel and consistently find it safe for tourists who follow basic precautions.` | P1 |
| `content/posts/2026-07-23-foodies-guide-to-china-a-gastronomic-adventure.md` | 30 | `As an American expat who has lived in Chengdu for over 5 years...` | 虚构 expat 身份 | `From a team that has covered Chengdu's food scene for over 5 years...` | P1 |
| `content/posts/2026-08-10-chinas-food-through-the-ages-guide.md` | 31 | `I have lived in Chengdu for over a decade...` | 虚构十年旅居 | `The ChinaBound Travel editorial team has covered Chengdu's food culture for over a decade...` | P1 |
| `content/posts/2026-08-12-china-national-parks-zhangjiajie-jiuzhaigou-and-beyond-guide.md` | 33 | `I remember my first trip to China like it was yesterday. I was a wide-eyed California native...` | 虚构第一次旅行经历 | `For many first-time visitors, a trip to China's national parks is unforgettable. Here's what to expect...` | P1 |
| `content/posts/best-travel-insurance-china.md` | 103 | `After personally using SafetyWing for 2+ years (and helping hundreds of readers pick plans over my 5 years in China)...` | 虚构个人使用+读者规模 | `SafetyWing is a top recommendation in our editorial evaluation of travel insurance for China...` | P1 |
| `content/posts/best-travel-insurance-china.md` | 37 / 95 / 227 | `my personal experience with travel insurance` / `Based on personal experience...` | 虚构个人经验 | 改为 `based on our editorial research` / `based on documented coverage and pricing research` | P1 |
| `content/posts/china-extends-144-hour-visa-free-transit-policy-to-more-countries.md` | 27 | `I'm Joran, your friendly California guy who married a local Chengdu girl and has been living in China for years.` | 虚构身份开场 | `China has expanded its visa-free transit policy — here's what travelers need to know.` | P1 |
| `content/posts/china-extends-144-hour-visa-free-transit-policy-to-more-countries.md` | 43 / 141 | `## My Take as a Local Expat` / `### My Personal Experience` | 虚构小标题 | 改为 `## Editorial Analysis` / `### What This Means for Travelers` | P1 |
| `content/posts/internet-connection-china-esim-vpn-guide.md` | 27 / 31 | `my wife` Wi-Fi 故事 + 虚构对话 | 虚构家庭经历 | 删除故事，改为客观说明 | P1 |
| `content/posts/western-sichuan-overland-camping-route.md` | 31 / 33 / 45 | 妻子 + SUV + `Five years living in China` + `my first trip` | 虚构自驾/露营经历 | 改为路线客观介绍 | P1 |
| `content/posts/2026-08-07-china-bargaining-and-shopping-guide.md` | 35 | `I remember my first shopping spree in Chengdu...` | 虚构购物经历 | 改为客观攻略 | P1 |
| `content/posts/2026-08-09-china-packing-list-2026-what-to-bring-and-what-to-leave-at-home.md` | 30 / 38 | `my very first journey to China... wide-eyed Californian` / `I remember my first visa application...` | 虚构经历 | 改为客观清单 | P1 |
| `content/posts/2026-06-30-xian-terracotta-army-history-discovery-and-insider-tips.md` | 33 / 37 / 119 | `I remember my first trip to Xi'an...` / `share my personal experiences` / `As an American expat who has lived in China for over 5 years...` | 虚构经历 | 改为历史/攻略客观介绍 | P1 |
| `content/posts/2026-07-13-navigating-china-with-confidence-a-californians-guide-to-travel-safety.md` | 29 / 45 | `As an American expat who has called Chengdu home for over 5 years...` / `I remember my first time taking the high-speed rail...` | 虚构经历 | 改为客观安全指南 | P1 |

## 4. 线上文章完整清单（41 篇 C 类正文，详见 SOCIAL_BRAND_IDENTITY_AUDIT.md 4.1）

144-hour-visa-free-transit-guide.md、2026-05-20-china-just-made-it-way-easier-to-visit-my-mother-i.md、2026-05-20-dude-wheres-my-panda-a-beijing-guys-guide-to-the-c.md、2026-05-20-shanghai-like-a-local-hidden-neighborhoods-tourist.md、2026-05-26-7-day-china-itinerary-beijing-xian-shanghai-first-timers.md、2026-05-26-hangzhou-west-lake-tea-culture-g20-guide.md、2026-06-19-the-history-and-culture-of-the-great-wall-beyond-the-tourist-trail-guide.md、2026-06-22-chinese-tea-culture-history-types-and-tea-ceremony-guide.md、2026-06-22-shanghai-beyond-the-bund-hidden-neighborhoods-and-local-culture.md、2026-06-23-sichuan-hotpot-guide-history-best-restaurants-and-cultural-significance.md、2026-06-30-xian-terracotta-army-history-discovery-and-insider-tips.md、2026-07-01-chinese-street-food-a-first-timers-guide-to-night-markets-and-street-stalls.md、2026-07-02-how-to-use-alipay-as-a-foreigner-complete-setup-guide-2026-guide.md、2026-07-02-wechat-pay-for-foreigners-step-by-step-setup-and-common-mistakes-to-avoid-guide.md、2026-07-03-guilin-and-yangshuo-the-ultimate-karst-landscape-guide-for-2026-guide.md、2026-07-04-china-high-speed-train-survival-guide-booking-classes-and-insider-tips.md、2026-07-05-yunnan-adventure-rice-terraces-ancient-towns-and-ethnic-minorities-guide.md、2026-07-06-a-gastronomic-adventure-in-china-a-foodies-guide-for-european-travelers.md、2026-07-07-navigating-chinas-accommodation-maze-a-californians-guide-for-aussie-and-kiwi-travelers.md、2026-07-10-a-gastronomic-adventure-in-china-food-recommendations-for-international-travelers.md、2026-07-12-navigating-chinas-transportation-a-californians-guide-for-european-travelers.md、2026-07-13-navigating-china-with-confidence-a-californians-guide-to-travel-safety.md、2026-07-14-transportation-guide-guide.md、2026-07-16-china-transportation-complete-guide-trains-subways-taxis-and-more.md、2026-07-16-food-recommendations-guide.md、2026-07-16-is-china-safe-for-tourists-2026-honest-safety-assessment.md、2026-07-20-travel-safety-guide.md、2026-07-21-cultural-etiquette-guide.md、2026-07-22-cultural-etiquette-guide.md、2026-07-23-foodies-guide-to-china-a-gastronomic-adventure.md、2026-07-31-china-remote-work-guide-a-californians-5-year-chengdu-experience.md、2026-08-01-chinabound-travel-guide-2026-08-monthly-update.md、2026-08-05-china-family-travel-tips-a-californians-guide.md、2026-08-07-china-bargaining-and-shopping-guide.md、2026-08-09-china-packing-list-2026-what-to-bring-and-what-to-leave-at-home.md、2026-08-10-chinas-food-through-the-ages-guide.md、2026-08-10-shanghai-vs-beijing-which-chinese-city-should-you-visit-first-guide.md、2026-08-11-chinese-tea-culture-where-to-experience-authentic-teahouses.md、2026-08-12-china-national-parks-zhangjiajie-jiuzhaigou-and-beyond-guide.md、best-travel-insurance-china.md、china-extends-144-hour-visa-free-transit-policy-to-more-countries.md、internet-connection-china-esim-vpn-guide.md、western-sichuan-overland-camping-route.md

## 5. 结论

- 站点级 P0 共 21 处（代码/配置/模板/About/JSON-LD/社媒模板），其中 19 处与 SOCIAL_BRAND_IDENTITY_AUDIT.md 的 P0 项对应，另含 About 页 3 项与城市页 1 项。
- 线上文章正文 P1 共 41 篇，本次不修改（遵守"只审计不修改正文"约束），建议下一阶段按批次人工改写。
- 自动生成/发布链路中，`joran_blog_generator.py` 已受 P0-1 治理保护；`social_publisher.py`、`config.py`、Medium/Quora 模板仍是旧人格，属于 P0 修复对象（本阶段只审计）。
- 所有推荐替换均不改变 SEO URL、slug、canonical、redirects 与 affiliate 参数。
