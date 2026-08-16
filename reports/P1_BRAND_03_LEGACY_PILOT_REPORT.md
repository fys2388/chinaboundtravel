# P1-BRAND-03 — Legacy Persona Migration Pilot Report

- 日期：2026-08-16
- 基线：GitHub main `9feab69` → 本轮提交
- 状态：**PASS**
- 范围：3 篇 legacy 文章 Persona 2.0 迁移（Editorial Persona）
- 禁止项遵守：未批量修改、未改 URL/slug/canonical/content_id/affiliate/UTM/sitemap、未改 Drive/Stripe/Buffer/GSC/GA4、未改 Resources 与首页品牌层、未调用 LLM 重写

---

## 1. Pilot Articles（数据驱动选择）

选择依据：`reports/P1_BRAND_02_LEGACY_PERSONA_REVIEW.md` + `reports/seo/TOP_10_CONTENT_PRIORITIES.md` + `reports/revenue/TOP_20_REVENUE_OPPORTUNITIES.md` + `reports/seo/CONTENT_SEO_INVENTORY.csv`；排除 canonical 冲突簇与实验页后按 impressions 排序。

| Pilot | content_id | Title | URL | GSC impressions | position | business intent |
|---|---|---|---|---|---|---|
| A | `cbt-80f6c218ad94` | Western Sichuan Overland Camping Route: 7 Days | /posts/western-sichuan-overland-camping-route/ | 26 | 19.31 | 中高（露营/租车/保险 affiliate） |
| B | `cbt-bf4ec5e57a07` | Guilin & Yangshuo: Complete 2026 Travel Guide | /posts/guilin-and-yangshuo-the-ultimate-karst-landscape-guide-for-2026/ | 24 | 18.88 | 高（酒店/交通 affiliate） |
| C | `cbt-550a6e3e929c` | Sichuan Hotpot Guide: History & Best Restaurants | /posts/sichuan-hotpot-guide-history-best-restaurants-and-cultural-significance/ | 11 | 37.18 | 中（美食/酒店 affiliate） |

## 2. Before / After Persona Claims

详见 `reports/P1_BRAND_03_LEGACY_PILOT.md` 逐条对照表。摘要：

- **Pilot A（13 处）**：移除 “My wife, Xiao Li”“Five years living in China”“my friend Lao Wang”“I made every mistake in the book”“my Honda CR-V”“we set up camp”“our tent almost blew away”“This Trip Changed My Life” 及个人化 Disclaimer。
- **Pilot B（9 处）**：移除 summary 中 “5-year China expat”、intro 第一人称、 “My honest take”→“Editor's take”、 “I've been to Guilin in three different seasons”、 “my top recommendation”、 “Based on what I'd actually spend” 等。
- **Pilot C（7 处）**：移除 description 中 “US expat in Chengdu”、intro “American who has spent over 5 years living in Chengdu”、家庭聚餐第一人称故事、 “One of my personal favorites”、 “I would recommend…trust me” 等。

替换为编辑口吻： “Based on current food guides and traveler reports”“Travelers commonly encounter…”“ChinaBound Travel recommends…”“Visitors who return in different seasons report…”“A consistently popular chain is…”。

未制造任何不存在的数据、体验、采访、价格、排名。

## 3. SEO Impact（保护性）

| 检查项 | 结果 |
|---|---|
| title front matter | 未变（3/3） |
| canonicalURL | 未变（3/3） |
| URL / slug | 未变（3/3） |
| H1 + 主要 H2 | 保留（3/3，仅移除 H2 内虚构经历字样） |
| description / summary | 仅移除 persona 声明，长度 ≤160、无重复 |
| PersonaGuard | PASS（3/3） |
| 内部链接 | markdown audit 0 broken / 0 malformed |

## 4. Affiliate Impact（零变化）

| 检查项 | 结果 |
|---|---|
| affiliate shortcode 集合 | token 级比对 HEAD 完全一致 |
| 裸 affiliate URL / UTM | 完全一致 |
| klook-link / booking-link | 逐字节一致 |
| Drive script | 未触碰 |

## 5. Tests

- 新增 `tests/test_brand_legacy_pilot.py`（8 项）覆盖任务要求的 10 点：URL/canonical/content_id/title 不变、affiliate/UTM 不变、PersonaGuard、旧虚构声明移除、结构保留、meta 有效唯一、内部链接有效、scope 控制。
- 更新既有 scope-guard 白名单：`test_brand_identity_p2.py`、`test_travelpayouts_drive.py`、`test_growth05_first_content_action.py`、`test_growth07_content_differentiation.py`，纳入 3 篇授权 pilot 文件。
- 结果：`python -m pytest tests/ -q` → **319 passed, 0 failed, 0 skipped**。
- `hugo --gc --minify` → PASS（12.3s）。
- `python scripts/content_id_audit.py audit --strict` → PASS（57/57, 0 missing, 0 duplicate）。
- Secret scan（`tests/test_no_hardcoded_secrets.py`）→ PASS。
- Workflow YAML validation（`tests/test_workflow_yaml.py`）→ PASS。
- Internal link audit（`tests/test_internal_links.py`）→ PASS。
- Meta audit（`tests/test_meta_description.py`）→ PASS。

## 6. Production Deployment

- 本轮修改 `content/posts/*`，由现有 GitHub Actions → Cloudflare Pages 自动部署；不手动部署。
- GitHub Actions `deploy-cloudflare-pages.yml`：push 后自动触发并 **success**（run `31932112875`，含 Purge CDN Cache 与 Post-deploy Tasks）。
- 部署后验证（线上 2026-08-16）：

| Page | HTTP | canonical | Drive script | noindex |
|---|---|---|---|---|
| Western Sichuan | 200 | self ✓ | exactly 1 | false |
| Guilin & Yangshuo | 200 | self ✓ | exactly 1 | false |
| Sichuan Hotpot | 200 | self ✓ | exactly 1 | false |

- 线上 title 确认：三页均正常渲染新 front matter（如 “Western Sichuan Overland Camping Route: 7 Days | ChinaBound Travel”）。

## 7. Observation Plan

| Pilot | 基线 | 观察指标 | 窗口 |
|---|---|---|---|
| A Western Sichuan | 1 click / 26 impr / 19.31 | CTR、position、impressions | 28 天 |
| B Guilin | 0 click / 24 impr / 18.88 | CTR、position、impressions | 28 天 |
| C Hotpot | 0 click / 11 impr / 37.18 | CTR、position、impressions | 28 天 |

- `LOW_DATA_WARNING`：整体 28d clicks = 3，单页 clicks 0–1；任何短期波动不得判定成败。
- 28 天后无负向变化 → 推进下一批（剩余 25 篇）。

## 8. Recommendation for Remaining 25 Articles

1. 保持同一套替换规则（只改身份来源、不改事实；persona_guard.py + governance forbidden list 为准）。
2. 按 SEO impressions / position 排序分批，每轮最多 3 篇，逐批上线观察。
3. 优先处理有自然流量但 position 4–20 的文章（CTR 提升空间最大）。
4. 每批跑同一回归套件（pytest 全套 + hugo build + content_id audit + secret scan）。
5. 若 28 天观察显示无排名/CTR 负向变化，可加速至每轮 5 篇；出现负向则暂停复盘。

## 9. Final Verdict

- 3 articles migrated：**PASS**
- all regression PASS（319 passed / 0 failed / 0 skipped）：**PASS**
- **P1-BRAND-03 = PASS**
- NEXT = P1-GROWTH-12 / REVENUE EXPERIMENT REVIEW
