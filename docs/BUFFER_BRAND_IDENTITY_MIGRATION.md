# ChinaBound Travel — Buffer Brand Identity Migration — P0.6

> 日期：2026-08-13
> 迁移类型：品牌身份 / Persona 治理 / Content ID 追踪 / Dedup 增强 / Secret 治理
> 原则：最小修改；不改变发布 API、token 机制、文章 URL、affiliate URL、UTM、content_id、发布时间策略、Buffer queue 基本逻辑。

## 1. 修改前 → 修改后

### 1.1 Persona（Buffer 社媒文案）

| 位置 | 修改前 | 修改后 |
|---|---|---|
| social_publisher.py（IG） | Expert tips from 5 years living in China | Research-based China travel tips from our editorial team |
| social_publisher.py（Pinterest） | Local secrets from a 5-year expat | Practical tips for international travelers |
| social_publisher.py（X） | I've lived in China for 5 years & here's what I WISH I knew... | Planning your first trip to China? Here are the practical things international travelers should know before they arrive. |
| social_publisher.py（Story hooks） | from a 10-year resident / After 10 years here... / I wish someone told me | 编辑型表达（our editorial team / essentials every first-time traveler should plan for / first-time applicants should know） |
| pinterest_templates.md | written by a 10-year resident | research-based practical travel information from the ChinaBound Travel editorial team |

### 1.2 Persona（AUTHOR_BIO）

| 位置 | 修改前 | 修改后 |
|---|---|---|
| config.py / config/global_rules.py | California native married to a Chengdu local... traveled to over 30 cities | Joran is the editorial voice behind ChinaBound Travel — providing research-based, practical China travel information for international travelers. |

### 1.3 Persona（生成器与知识库）

| 位置 | 修改前 | 修改后 |
|---|---|---|
| joran_blog_generator.py | AUTHORITY 规则 Reference my 5 years experience FREQUENTLY but naturally；highlights 含 200+ rides experience / someone who lives here / 10 years of experience | Base practical advice on research, official sources, and editorial expertise; NEVER claim personal travel experience...；highlights 改 research-based / verified / editorial |
| content_knowledge_base.json | 一条含 When I told my Chengdu wife... 的虚构故事 | 编辑型摘要（杭州指南内容） |

### 1.4 Governance

| 位置 | 修改前 | 修改后 |
|---|---|---|
| config/content_governance.json | 无 5-year expat / American expat / Chengdu wife 等 | forbidden_phrases 新增 10 条，覆盖居住/婚姻/家庭/旅行虚构表述；保留原 PersonaGuard 规则 |

### 1.5 Content ID

| 位置 | 修改前 | 修改后 |
|---|---|---|
| social_publisher.py | payload 无 content_id | payload 增加 content_id / content_variant / source_workflow |
| scripts/content_rotator.py | payload 无 content_id | payload 增加同上三字段 |
| buffer-worker/worker.js | /publish 忽略 content_id | 接收三字段，写入 KV dedup / track metadata |

### 1.6 Dedup

| 位置 | 修改前 | 修改后 |
|---|---|---|
| buffer-worker/worker.js | KV dedup 仅基于标题/URL/文本 | 新增 content_id + account + platform + variant 稳定 dedup；无 content_id 回退旧逻辑 |
| buffer-worker/dedup.mjs | 不存在 | 新增 buildDedupKey / buildTrackRecord / isDuplicate 纯函数 |

### 1.7 Secret

| 位置 | 修改前 | 修改后 |
|---|---|---|
| buffer-worker/*.js（22 个） | 明文真实 token | process.env.BUFFER_TOKEN || 'BUFFER_TEST_TOKEN'；Pinterest 类 process.env.BUFFER_TOKEN_PINTEREST || process.env.BUFFER_TOKEN_PIN |
| buffer_config.json | access_token 明文 | 置空 ""，token 走环境变量 |
| config.py | os.getenv("BUFFER_ACCESS_TOKEN", "<真实token>") | os.getenv("BUFFER_ACCESS_TOKEN", "") |
| video-pipeline/test_buffer_*.py（5 个） | 明文 API_TOKEN | os.environ.get("BUFFER_ACCESS_TOKEN", "BUFFER_TEST_TOKEN") |
| tests/test_no_hardcoded_secrets.py | 无 Buffer 专项 | 新增 bearer / literal / assignment 三种模式 |

## 2. 配置要求

- chinaboundtravel_social_bot/buffer_config.json：access_token 保持为空，勿回填 token
- config/content_governance.json：PersonaGuard 使用该文件，禁止删除新增的 10 条 forbidden phrases
- 社媒文案原则：80% 解决问题 / 20% 品牌灵感；CTA 统一为 Read the full guide: {url} 或 More China travel guides: https://www.chinaboundtravel.com/

## 3. 环境变量要求（部署侧，不入库）

Cloudflare Worker（buffer-auto-poster）需配置：

| 变量 | 用途 |
|---|---|
| BUFFER_WORKER_URL | Buffer-A token（FB + IG + X） |
| NEW_BUFFER_WORKER_URL | Buffer-B token（Pinterest） |
| PINTEREST_BOARD_SERVICE_ID | Pinterest board service id（可选，有默认值） |
| FEISHU_WEBHOOK_URL | 发布/配额预警通知（可选） |
| GA4_PROPERTY_ID / GA4_SERVICE_ACCOUNT_KEY | GA4 attribution（可选） |
| KV namespace KV_STORE | dedup / track / retry / quota 存储 |

本机/CI 运行侧：

| 变量 | 用途 |
|---|---|
| BUFFER_ACCESS_TOKEN | Python 侧（config.py / video-pipeline 测试）读取 |
| BUFFER_TOKEN | buffer-worker 查询/测试脚本读取 |
| BUFFER_TOKEN_PINTEREST / BUFFER_TOKEN_PIN | Pinterest 类脚本读取 |

注意：GitHub Actions / Cloudflare 中 BUFFER_WORKER_URL、NEW_BUFFER_WORKER_URL 的键名是历史命名，实际存 token（本次不改机制、不改名）。

## 4. 后续人工操作

- 在 Cloudflare Worker 与 GitHub Secrets 中确认上述环境变量已配置（不在此次自动修改范围内）
- 若历史明文 token 曾泄露到第三方渠道，建议在 Buffer 后台轮换 token 并同步更新环境变量
- 重新部署 buffer-auto-poster Worker（wrangler deploy）以启用 content_id dedup / tracking 逻辑
- 人工审核 docs/BUFFER_BRAND_IDENTITY_AUDIT.md 剩余风险清单（Medium / Reddit 模板、历史文章、.bak 备份）

## 5. 不需要人工操作的部分

- 文章 URL、canonical、affiliate URL、UTM、content_id、slug 均未改动
- Buffer 账号、channel、board、发布时间策略未改动
- Buffer queue 基本逻辑、retry、限流、customScheduled 未改动
- TikTok / YouTube / 41 篇历史文章 / Medium / Quora / Reddit 未改动
- 本阶段未 commit、未 push、未调用真实 Buffer API、未真实发布

## 6. 验证清单（2026-08-13 复跑）

- pytest：51 passed / 0 failed / 0 skipped
- Hugo build：PASS（365 pages）
- PersonaGuard / Risk Gate：PASS
- Content ID audit --strict：PASS（57/57）
- Affiliate regression：PASS（含 test_no_affiliate_url_changed）
- Workflow YAML / name validation：PASS
- Hardcoded secret scan + Buffer 专项：PASS（真实 token 无残留）
- Buffer dedup 测试 6 项、content_id propagation 测试 6 项：PASS

## 7. 结论

PASS（Brand Identity / Persona Governance / Content ID / Dedup / Secret Security / Affiliate Safety / SEO / Tests / Hugo Build 全部通过）。