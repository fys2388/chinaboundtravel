# P1-BRAND-02 — JORAN PERSONA MIGRATION (FINAL)

- Generated: 2026-08-16
- WORKDIR: `E:\AI\dulizhan\travel-blog`

## 结论

**P1-BRAND-02 = PASS_WITH_LEGACY_CONTENT**

核心品牌层（Homepage / Resources / Author Block / About / Schema）已全部统一到 Editorial Persona；legacy 文章未批量修改（28 篇含旧 persona 短语，标记 LEGACY_PERSONA_CONTENT 后续处理）；测试、构建、审计全绿。

## 1. Brand Positioning（已固化）

- BRAND: ChinaBound Travel
- AUDIENCE: International travelers planning or taking trips to China
- POSITIONING: Research-based, practical, current China travel guidance for international travelers.
- Joran: Virtual editorial voice behind ChinaBound Travel（不是现实旅行博主）
- AUTHORITY 来源：editorial research / official & current sources / cross-checking / structured comparisons / traveler-focused explanations / current policy verification / practical guidance
- 禁止以个人虚构经历作为 authority

## 2. Homepage

- `layouts/partials/home-banner.html`：`Written by Joran · American Living in Chengdu` → `Edited by Joran · Editorial Voice of ChinaBound Travel`
- `hugo.toml` site description：移除 `Written by an American married into a Chengdu family` → 编辑团队署名
- `hugo.toml [params.profileMode]` subtitle：移除 `A California native married into a Chengdu family. I've spent 5 years...` → Research-based 定位

## 3. Resources Page

`content/resources/_index.md`：
- front matter description：`10+ years of experience` → `Editorially reviewed ... compared for international travelers`
- 移除：`After 10+ years of living in China ... I personally use and trust`、`personally used`、`After 2+ years of using SafetyWing personally`、`After testing dozens ... I trust`、`Tested daily`、`I personally respond`
- 保留：affiliate 链接/ID/UTM 原样（SafetyWing / Airalo / NordVPN / Booking / Aviasales / Klook / Wise / Hostelworld）与 affiliate disclosure

## 4. Author Block

- `layouts/partials/sidebar-author.html`：`American in Chengdu 🇺🇸→🇨🇳` → `Editorial Voice · China Travel Guide`；bio `5 years navigating...` → research-based 定位
- `layouts/_default/single.html`（GBK）与 `layouts/cities/single.html`：`Joran's personally tested recommendations` → `our editorially reviewed recommendations`；`I only recommend products I personally use` → 编辑团队审查
- `layouts/partials/affiliate-disclosure.html` + `layouts/shortcodes/affiliate-disclosure.html`：`Joran has personally used and trusts` → `our editorial team has reviewed for international travelers`
- `layouts/partials/travel-promo.html`：移除 `after 5 years of living in China`、`personally used`、`tested daily` → editorial 表述

## 5. About Page

`content/about/_index.md` 重写为 editorial：
- title/description：`The story of an American who fell in love with China` → 品牌与编辑方法
- 移除：American Expat · Chengdu Husband · my wife · 加州定居经历 · VPN/支付个人故事 · `my wife's mood` 等
- 新增：`How We Research`（官方/现行来源、交叉核验、日期标注）、`How Recommendations Are Evaluated`（availability / coverage / cost transparency）、保留 contact email 与 affiliate disclosure 链接

## 6. Schema / SEO Author

- `layouts/partials/templates/schema_json.html` author：`jobTitle: China Travel Blogger` → `Editorial Voice, ChinaBound Travel`；`description: A California native married into a Chengdu family with 5 years...` → editorial voice 描述
- Person schema 结构（Person/Organization）继续使用；canonical / article URL / sitemap / affiliate 未变

## 7. Governance

`config/content_governance.json` forbidden_phrases 50 → 60（新增 10 条最小必要）：`American living in Chengdu`、`American in Chengdu`、`Chengdu husband`、`personally tested`、`personally used`、`6 years living in China`、`10+ years of living in China`、`I personally use`、`I personally recommend`、`tested daily`。已有 PersonaGuard / Risk Gate 未破坏（pytest 全绿）。

## 8. Legacy Content

详细：`reports/P1_BRAND_02_LEGACY_PERSONA_REVIEW.md`

- content/posts 共 57 篇，28 篇命中旧 persona 短语（如 `American expat`、`my wife`、`first trip`、`I lived in`）
- 状态：LEGACY_PERSONA_CONTENT — 本轮不处理、不批量改写
- 建议：按 opportunity engine 排序优先修订有流量的 legacy 页；每批 ≤2-3 篇；保留 URL/canonical/content_id/affiliate/UTM；改后 28 天观察

## 9. Brand Identity Audit

新增 `scripts/brand_identity_audit.py`（确定性规则，无 LLM），输出 `reports/P1_BRAND_02_BRAND_IDENTITY_AUDIT.md`：

- 13 个品牌层文件扫描：11 PASS、2 WARN（`layouts/index.html`、`layouts/partials/author.html` 为纯结构模板，无违规也无 editorial 文案，无需改动）
- `--legacy` 模式扫描 posts 生成 legacy review

## 10. Tests

新增 `tests/test_brand_identity_p2.py`（13 项）：homepage/resources/about 无虚构经历、author block editorial 身份、schema author 干净、forbidden phrases governed、affiliate section 未变（git diff HEAD vs 工作区）、content/posts 未动、非品牌 content 仅 about/resources、canonical 未变。

| 检查 | 结果 |
|---|---|
| `python -m pytest tests/ -q` | 311 passed, 0 failed, 0 skipped |
| `hugo --gc --minify` | PASS |
| `python scripts/content_id_audit.py audit --strict` | PASS（57/57, 0 missing, 0 duplicate） |
| secret scan / workflow YAML / internal link / affiliate regression | PASS（含于 pytest） |

## 11. SEO Regression

- URL / slug / canonical / content_id：未变（content/posts 零改动）
- sitemap / robots：未变
- 文章 schema（FAQPage 等）与 publisher 结构：保留，仅 author description 更新

## 12. Affiliate Regression

- `hugo.toml [params.affiliate]` 段与 HEAD 逐字节一致（测试断言）
- 品牌层未改任何 affiliate URL / ID / UTM；Resources 页 affiliate 链接原样保留
- Travelpayouts Drive 未动（每页渲染 1 次，由既有测试保障）

## 13. Production Deployment

commit → push → GitHub Actions Post-deploy Tasks（content/layouts/config 变化触发）→ Cloudflare Pages 自动部署。部署后验证 `/`、`/resources/`、`/about/`：200、品牌文案正确、无虚构经历声明、Drive exactly 1。

## 14. Remaining Issues

1. **Legacy articles（28/57）**：仍含旧 persona 短语（含首页文章卡片 summary 的展示），按 LEGACY_PERSONA_CONTENT 后续分批处理。
2. `content/affiliate-disclosure.md`、`content/7-day-china-itinerary.md` 等非品牌层页面仍有个别 `I personally use` 表述（严格范围外，未改；建议下一轮品牌轮处理）。
3. 首页文章卡片的 summary 会显示 legacy 文章摘要中的旧 persona 短语（来源为文章正文，不在本轮范围）。
4. `layouts/index.html` / `layouts/partials/author.html` 无 editorial 文案（WARN，非违规）。

---
**P1-BRAND-02 = PASS_WITH_LEGACY_CONTENT**