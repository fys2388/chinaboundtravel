# ChinaBound Travel — Buffer Brand Identity Audit — P0.6

> 日期：2026-08-13
> 范围：Buffer 品牌身份 / 发布人格 / 代码与配置
> 约束：只处理 Buffer 相关代码、配置与模板；不改 TikTok / YouTube / 41 篇历史文章 / Medium / Quora / Reddit / social_distributor.py / modules/distributors.py / worker.js 平台适配与调度核心；不 commit、不 push、不调用真实 Buffer API、不真实发布。

## 1. 原问题

| 类别 | 问题 |
|---|---|
| Persona | Buffer 社媒文案虚构 Joran 真实经历：5 年居住 / 5-year expat / 10 年 resident / 成都妻子 / 个人旅行回忆 |
| Persona | config.py 与 config/global_rules.py 的 AUTHOR_BIO 是虚构真人传记（California native + Chengdu wife + 30 城市） |
| Persona | joran_blog_generator.py 的 AUTHORITY prompt 要求 “Reference my 5 years experience FREQUENTLY”，强制模型编造经历 |
| Persona | config/content_knowledge_base.json 内嵌一条 “my Chengdu wife” 虚构故事，会污染后续生成文案 |
| Persona | pinterest_templates.md 模板含 “written by a 10-year resident” |
| Content ID | 文章 frontmatter 有 content_id，但 Buffer payload 不带 content_id，发布任务无法内部追溯 |
| Dedup | 存在 social_publisher manifest / content_rotator manifest / Worker KV dedup 三套，互不知道；KV dedup 不基于 content_id |
| Secret | buffer-worker 查询/测试脚本、buffer_config.json、config.py fallback、video-pipeline 测试脚本中明文写死真实 Buffer token |
| Governance | config/content_governance.json 缺 “5-year expat / American expat / Chengdu wife” 等禁止短语 |

## 2. 修改位置

### 2.1 Persona — 社媒文案（chinaboundtravel_social_bot/social_publisher.py）
- IG 文案 “Expert tips from 5 years living in China” → “Research-based China travel tips from our editorial team”
- Pinterest 文案 “Local secrets from a 5-year expat” → “Practical tips for international travelers”
- X/Twitter 文案 “I've lived in China for 5 years & here's what I WISH I knew...” → “Planning your first trip to China? Here are the practical things international travelers should know before they arrive.”
- IG Story hooks：from a 10-year resident / After 10 years here, here's what I'd tell my younger self / I wish someone told me → 编辑型表达（our editorial team / essentials every first-time traveler should plan for / first-time applicants should know）

### 2.2 Persona — AUTHOR_BIO（chinaboundtravel_social_bot/config.py、config/global_rules.py）
- 统一改为：Joran is the editorial voice behind ChinaBound Travel — providing research-based, practical China travel information for international travelers.

### 2.3 Persona — 生成器规则（chinaboundtravel_social_bot/joran_blog_generator.py）
- 删除 “15. AUTHORITY: Reference my 5 years experience FREQUENTLY but naturally”
- 改为：Base practical advice on research, official sources, and editorial expertise; NEVER claim personal travel experience, residence, marriage, or family in China
- highlights 示例：200+ rides experience / someone who lives here / 10 years of experience → research-based guidance on common traveler questions / verified safety information from official sources / research-based essential guide for travelers

### 2.4 Persona — 知识库（config/content_knowledge_base.json）
- 删除一条含 “When I told my Chengdu wife...” 的虚构故事，改为编辑型摘要（杭州西湖南山指南内容）。

### 2.5 Persona — 模板（chinaboundtravel_social_bot/content/templates/pinterest_templates.md）
- “written by a 10-year resident” → “research-based practical travel information from the ChinaBound Travel editorial team”
- 注：medium_templates.md / reddit_templates.md 仍含旧人格（本阶段明确不改 Medium / Reddit，列入剩余 P1）。

### 2.6 Governance（config/content_governance.json）
- forbidden_phrases 新增 10 条：5 years living in China、5-year expat、I've lived in China、10-year resident、After 10 years here、my wife、Chengdu wife、American expat、my first trip to China、my experience living in China
- 保留原有 PersonaGuard 规则与 risk gate；未做任何绕过。

### 2.7 Content ID 进入 Buffer
- social_publisher.py：get_article_info() 从 frontmatter 读取 content_id；publish_to_worker() payload 增加 content_id / content_variant / source_workflow
- scripts/content_rotator.py：parse_article() 读取 content_id；publish_to_buffer() payload 增加同上三字段
- buffer-worker/worker.js：/publish 接收 content_id / content_variant / source_workflow，用于内部 dedup / tracking；不插入用户可见社媒文案
- buffer-worker/dedup.mjs：新增纯函数 buildDedupKey / buildTrackRecord / isDuplicate

### 2.8 Dedup 增强
- 稳定 dedup identity：content_id + account + platform + content_variant
- KV key：dedup:{content_id}:{account}:{platform}:{variant}，TTL 仍为 30 天
- tracking 记录：track:{...}，TTL 90 天，保存 content_id / platform / account / scheduled_at / source_workflow / post_url
- 无 content_id 时回退到原 dedup 逻辑，不影响旧任务
- 不改变全局限流、retry queue、customScheduled、workflow concurrency

### 2.9 Secret Governance
- buffer-worker/ 22 个查询/测试脚本：真实 token → process.env.BUFFER_TOKEN || 'BUFFER_TEST_TOKEN'（Pinterest 类脚本 process.env.BUFFER_TOKEN_PINTEREST || process.env.BUFFER_TOKEN_PIN）
- chinaboundtravel_social_bot/buffer_config.json：access_token 置空，token 只从环境变量读取
- chinaboundtravel_social_bot/config.py：os.getenv("BUFFER_ACCESS_TOKEN", "")，删除明文 fallback
- video-pipeline/test_buffer_*.py：5 个脚本改用 os.environ.get("BUFFER_ACCESS_TOKEN", "BUFFER_TEST_TOKEN")
- tests/test_no_hardcoded_secrets.py：新增 Buffer bearer / token literal / token assignment 三种模式扫描
- 全仓库扫描确认：3 个历史真实 token 已无任何残留（NO REAL TOKEN FOUND）

## 3. 新 Persona

```
Brand:       ChinaBound Travel
Slogan:      China Travel Made Simple.
Positioning: Practical China travel information for international travelers.
Joran:       Joran is the editorial voice behind ChinaBound Travel.
```

- 80% 内容直接解决旅行者问题（支付、签证、交通、预算、安全等），20% 品牌/目的地灵感
- CTA：Read the full guide: {url} 或 More China travel guides: https://www.chinaboundtravel.com/
- 禁止任何虚构第一人称经历（居住、婚姻、家庭、旅行）

## 4. Buffer 架构

```
social_publisher.py ─┐
                     ├─> Cloudflare Worker (/publish) ─> Buffer GraphQL API
content_rotator.py ──┘          │
                                ├─ Buffer-A（tokenKey=BUFFER_WORKER_URL）→ FB + IG + X
                                └─ Buffer-B（tokenKey=NEW_BUFFER_WORKER_URL）→ Pinterest
```

- 保留：自动调度（automatic / customScheduled）、retry queue、全局限流（每日 3 条/文章）、账户配额（15 分钟 70 条）
- 保留：KV dedup 30 天 TTL、distributor 入口
- 新增：content_id dedup 与 tracking metadata（KV）

## 5. Content ID 追踪

每次 Buffer 发布任务内部可追溯：

```
content_id + platform + account + scheduled_at + source_workflow + post_url
```

- 来源：文章 frontmatter content_id: cbt-xxxxxxxxxxxx
- 存放：Worker KV track:{content_id}:{account}:{platform}:{variant}（90 天 TTL）
- content_id 仅作为内部 metadata / dedup，不写入用户可见文案

## 6. Dedup 机制

| 场景 | 行为 |
|---|---|
| 同 content_id + platform + account + variant | 跳过（SKIPPED，返回原因） |
| 同文章不同平台 | 正常发布 |
| 同文章同平台不同 variant | 正常发布 |
| 不同文章同平台 | 正常发布 |
| 无 content_id | 回退旧 dedup 逻辑 |

## 7. Affiliate / URL 安全

- 未修改：文章 URL、canonical、affiliate URL、UTM 参数、GA4 attribution
- content_id 只增加内部追踪字段，不进入 Buffer API 的可见文本字段（text/link）
- 未使用 Buffer link shortener，未替换原 URL
- test_no_affiliate_url_changed PASS

## 8. 测试结果（2026-08-13 复跑）

| 项目 | 结果 |
|---|---|
| pytest（tests/ 全量） | PASS — 51 passed / 0 failed / 0 skipped |
| Hugo build（v0.147.0） | PASS — 365 pages，exit 0 |
| PersonaGuard（governance 配置 + 生成器规则） | PASS |
| Risk Gate | PASS |
| Content ID audit --strict | PASS — 57/57 有 content_id，0 missing / malformed / duplicate |
| Affiliate regression | PASS |
| Workflow YAML / name validation | PASS |
| Hardcoded secret scan（含 Buffer 专项） | PASS — 真实 token 无残留 |
| Buffer dedup 单元测试 | PASS — 6 项 |
| Buffer content_id propagation 测试 | PASS — 6 项 |

## 9. 结论

Brand Identity: PASS
Persona Governance: PASS
Content ID: PASS
Dedup: PASS
Secret Security: PASS
Affiliate Safety: PASS
SEO: PASS
Tests: PASS
Hugo Build: PASS

## 10. 剩余风险

- P1：medium_templates.md（3 处）与 reddit_templates.md（2 处）仍含旧人格文案（本阶段明确不改 Medium / Reddit）
- P1：41 篇历史文章与 about 页含旧第一人称内容（用户已决定暂不批量修改，后续单独阶段处理）
- P2：social_publisher.py.bak 等本地备份文件保留旧文案，建议清理或归档
- P2：video-pipeline/.env（gitignored、未跟踪）含第三方 API key（DeepSeek / Doubao 等），不属于 Buffer 范围，建议定期轮换
- P2：worker.js 中 BUFFER_WORKER_URL / NEW_BUFFER_WORKER_URL 命名实际承载 token，属历史命名，本阶段按“不改变 token 机制”保留，建议后续更名并同步 Cloudflare 环境变量