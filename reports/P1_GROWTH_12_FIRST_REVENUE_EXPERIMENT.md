# P1-GROWTH-12 — First Affiliate Revenue Experiment（REV001，重建版）

- 重建日期：2026-08-17（P1-REPORT-01）
- 原始生成：2026-08-16（P1-GROWTH-12）
- 状态：**RUNNING**（decision = PENDING）
- 说明：本文件为 REV001 的**最终权威定义**。早期草稿曾把 REV001 定义为「144-Hour Visa + Booking hotel CTA」，该定义已在 P1-GROWTH-12A（Candidate Lock）中被否决，并由 P1-GROWTH-12B 正式落地为下述定义；旧 `GROWTH12_BASELINE.csv` 已同步重建。旧 144h/Booking 定义**不保留**。

## 1. Experiment ID

- experiment_id: **REV001**
- type: CTA_PLACEMENT（affiliate mid-content CTA）
- status: RUNNING
- minimum_observation_days: 28（最早评估 2026-09-13）

## 2. Page（最终锁定）

- title: Chinese Food Delivery: Meituan & Ele.me Guide
- content_id: `cbt-e464169c4991`
- URL: https://www.chinaboundtravel.com/posts/chinese-food-delivery-meituan-eleme-guide/
- 选择依据：P1-GROWTH-12A Candidate Lock（GSC 28d impressions=159 全站最高之一；已有 4 个 INLINE partner；无 canonical/index blocker；与全部运行中实验零重叠）

## 3. Partner & CTA

- partner: **esim（Airalo）**
- shortcode: `affiliate-mid-cta`（复用 GA4 funnel 事件，无第二套 tracking）
- placement: **food-delivery-mid-content**
- destination: hugo.toml `[params.affiliate].esim` = `https://www.airalo.com/`（与页面既有 affiliate-esim shortcode 完全一致）
- 页面既有 4 个页尾 INLINE shortcode 保持不变：affiliate-hotel / flight / esim / tour

## 4. Baseline（2026-07-19 → 2026-08-15，固化于 REV001_BASELINE.csv / GROWTH12_BASELINE.csv）

| Metric | Value | Scope |
|---|---|---|
| sessions | 162 | sitewide 28d（页面级 GA4 不可得，DATA_SCOPE=sitewide） |
| pageviews | 365 | sitewide 28d |
| affiliate_clicks | 0 | sitewide 28d |
| affiliate_clicks_per_1000_pageviews | 0.0 | computed |
| GSC impressions | 159 | page 28d |
| GSC clicks | 0 | page 28d |
| GSC position | 19.55 | page 28d |
| revenue | NULL | REVENUE_NOT_AVAILABLE（不伪造） |

## 5. Measurement Plan

- PRIMARY: affiliate_clicks_per_1000_pageviews（实验期 vs baseline 0.0）
- SECONDARY: affiliate_click_rate、pageviews、sessions、GSC impressions/clicks、position
- 观察窗口: >= 28 天（2026-08-16 起，最早 2026-09-13 评估）
- 样本守卫: affiliate_clicks < 20 → INSUFFICIENT_SAMPLE；禁止 1/3/7 天宣布 WIN/LOSE

## 6. Confounders（已记录）

1. DRIVE-001 同时 RUNNING（全站 Drive script）——Drive 配置未改变，独立观测
2. GROWTH-05（144h CTR）不在本页面
3. Brand-03（3 篇 legacy 迁移）不涉及本页面
4. 页面 legacy persona 内容与 UTF-8 乱码：明确不在本轮修改范围
5. LOW_DATA_WARNING ACTIVE：全站 28d GSC clicks=3

## 7. SEO / Affiliate Invariants

- URL / slug / canonical / content_id / title / description 未变
- 现有 affiliate URLs / IDs / UTM / tracking_parameter 逐字节未变
- 只新增 1 个 CTA（对已有 partner esim 的引用）
- Drive script 未变（每页 exactly 1）
- PersonaGuard：新增 CTA 文案无 forbidden 短语

## 8. Deployment

- commit `feat: launch REV001 affiliate CTA experiment`（2026-08-16，P1-GROWTH-12B）→ GitHub Actions → Cloudflare Pages 自动部署
- 上线后验证：page=200、CTA exactly 1、Drive exactly 1、affiliate URL=esim config、content_id/canonical/title/meta 不变

## Final Verdict

- **REV001 = RUNNING**（frozen until 2026-09-13；不得修改 CTA copy/placement/partner）
- 本文件重建完成，与 REV001_BASELINE.csv、REV001_EXPERIMENT_LOG.md、REVENUE_EXPERIMENT_REGISTRY.csv 一致
