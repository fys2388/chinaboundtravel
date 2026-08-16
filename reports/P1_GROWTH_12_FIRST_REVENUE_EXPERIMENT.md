# P1-GROWTH-12 — FIRST REVENUE EXPERIMENT

- Generated: 2026-08-16
- GitHub main 前: `274305a`
- GSC Property: `https://www.chinaboundtravel.com/`

## 结论

**P1-GROWTH-12 = PASS**

REV-001 CTA PLACEMENT EXPERIMENT 已上线（144-Hour Visa 页面中部 1 个 affiliate CTA），tracking/SEO 不变量/Drive 隔离全部通过，测试与构建全绿。

**NEXT = P1-GROWTH-13 REVENUE MEASUREMENT REVIEW**

## 1. Experiment ID
- `REV-001`
- type: `CTA_PLACEMENT`
- status: `RUNNING`（decision=PENDING）
- 最小观察: 28 天（至 2026-09-13 评估）
- 注册表: `reports/revenue/REVENUE_EXPERIMENT_REGISTRY.csv`

## 2. Page
- title: China 144-Hour Visa-Free Transit (2026 Guide)
- content_id: `cbt-b4ff4381a014`
- URL: `https://www.chinaboundtravel.com/posts/144-hour-visa-free-transit-guide/`
- 来源确认: `reports/revenue/TOP_5_REVENUE_ACTIONS.md` #1（score 82.5 / Tier A / CTA_OPTIMIZATION）；`reports/seo/NEXT_EXPERIMENT_CANDIDATES.md` 不含该页（无冲突）

## 3. Partner
- partner: `hotel`（Booking, `aid=730795`）— 页面既有已验证 partner，非新增合作
- 不涉及 Booking/Klook/Aviasales/NordVPN/SafetyWing 新合作
- 未改变 affiliate destination / UTM

## 4. Baseline（28d，固定保存）

| 指标 | 值 |
|---|---|
| sessions | 162 |
| pageviews | 365 |
| affiliate_clicks | 0 |
| affiliate_clicks / 1000 pageviews | 0.0 |
| gsc_impressions（本页） | 107 |
| gsc_clicks（本页） | 0 |

保存于 `reports/revenue/GROWTH12_BASELINE.csv`。

## 5. CTA Change

仅 1 个新增 mid-content CTA，位于文章 Step 3 之后、Step 4 之前（`visa_cta_mid_content`）：

> **Planning your transit stopover?** Your 144-hour window is short. Compare well-located hotel options ahead of time so you can start exploring the moment you clear immigration.
> Compare Hotel Options →（Booking, aid=730795, `rel=nofollow sponsored`）
> 附透明披露：*Affiliate link - we may earn a small commission at no extra cost to you.*

- 无弹窗 / 无 sticky / 无自动跳转 / 无强制点击 / 仅 1 个 CTA
- 未创建第二个页面版本，无 client-side A/B

## 6. Tracking

复用现有 `affiliate_click` 事件，未创建第二套 tracking：
- 新 shortcode `layouts/shortcodes/affiliate-mid-cta.html` 输出 `a.affiliate-link` + `data-affiliate-partner=hotel` + `data-affiliate-placement=visa_cta_mid_content`
- `layouts/_default/single.html` 事件委托扩展：正文中带 `data-affiliate-placement` 的链接由同一 `send()` 上报（字段不变：content_id/partner/placement/channel/timestamp/destination/tracking_parameter；容器内点击不重复计数）
- 无页面修改时行为不变（向后兼容）

## 7. SEO Invariants（未变）
- URL / canonical / content_id / title / meta description / sitemap 均未修改
- affiliate destination（`booking.com/index.html?aid=730795`）与 UTM 未修改

## 8. Compliance / PersonaGuard

- CTA 文案无价格、折扣、稀缺性、排名、个人体验、Joran 第一人称
- 未含禁止短语（5 years living in China / my wife / first trip 等）
- PersonaGuard 对新增 CTA 文案检查通过

## 9. Deployment

本 commit 修改了 1 篇文章 + 2 个模板文件（shortcode + tracking JS），由 GitHub Actions → Cloudflare Pages 自动部署；不手动重复 deploy。

## 10. Observation Window
- start: 2026-08-16
- 最小观察: 28 天
- 首次评估: 2026-09-13 之后

## 11. Success Criteria
- PRIMARY: `affiliate_clicks / 1000 pageviews`（baseline = 0.0）
- SECONDARY: affiliate_click_rate、sessions、pageviews、GSC impressions、GSC clicks
- 判定: POSITIVE = meaningful increase + sufficient sample；NEUTRAL = no meaningful change；NEGATIVE = meaningful decrease
- 不设定虚假绝对 revenue target；revenue 继续 NULL

## 12. Sample-Size Guard

**LOW_SAMPLE_WARNING / LOW_DATA_WARNING**：
- 当前全站 28d affiliate_clicks = 0、GSC clicks = 3，样本极小
- `affiliate_clicks < 20` → 状态一律 `INSUFFICIENT_SAMPLE`，不宣布成败
- 1/3/7 天数据不构成结论

## 13. Drive Isolation

- DRIVE-001 继续 RUNNING，未修改 Drive code / settings / placement
- 渲染页面 Drive script 恰好 1 次（回归测试验证）

## 14. Tests

新增 `tests/test_growth12_revenue_experiment.py`（15 项）：CTA exactly once（source + rendered）、placement ID、affiliate destination unchanged、tracking intact（source + rendered）、content_id / title / canonical / URL unchanged、PersonaGuard、no duplicate CTA、Drive unchanged。

| 检查 | 结果 |
|---|---|
| `python -m pytest tests/ -q` | 全量通过（见最终输出） |
| `hugo --gc --minify` | PASS |
| `content_id audit --strict` | PASS |
| internal link audit / affiliate regression / secret scan / workflow YAML | PASS（含于 pytest） |

## 15. Git

- 修改对象：`content/posts/144-hour-visa-free-transit-guide.md`（1 篇）、`layouts/shortcodes/affiliate-mid-cta.html`、`layouts/_default/single.html`（tracking 委托）
- 新增：tests、GROWTH12_BASELINE.csv、REVENUE_EXPERIMENT_REGISTRY.csv、本报告
- commit: `feat: start first affiliate revenue experiment` → 正常 fast-forward push

---
**P1-GROWTH-12 = PASS** ｜ NEXT = **P1-GROWTH-13 REVENUE MEASUREMENT REVIEW**