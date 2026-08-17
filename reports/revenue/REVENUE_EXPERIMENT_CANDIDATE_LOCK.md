# REVENUE EXPERIMENT CANDIDATE LOCK

- Generated: 2026-08-16
- Cycle: P1-GROWTH-12A
- Decision: single locked candidate for the first real affiliate revenue experiment (CTA placement)

## Locked Candidate

| Field | Value |
|---|---|
| selected_page | Chinese Food Delivery: Meituan & Ele.me Guide |
| content_id | `cbt-e464169c4991` |
| url | https://www.chinaboundtravel.com/posts/chinese-food-delivery-meituan-eleme-guide/ |
| partner | Airalo, Aviasales, Booking, Klook（全部 INLINE，各 1 链接） |
| commercial_intent | FOOD / APP GUIDE (HIGH) |
| sessions (28d, sitewide) | 162 |
| pageviews (28d, sitewide) | 365 |
| gsc_impressions (28d) | 159 |
| gsc_clicks (28d) | 0 |
| gsc_position (28d) | 19.55 |
| affiliate_clicks (28d) | 0 |
| current_cta | 4 个页尾 INLINE shortcode（affiliate-hotel / flight / esim / tour），无 mid-content CTA |
| drive_status | ACTIVE (DRIVE-001 RUNNING, site-wide script, exactly 1/page) |
| brand_migration_status | NOT in Brand-03 pilot（3 篇 pilot = Western Sichuan / Guilin / Hotpot） |
| conflicts | 无 canonical conflict；无 index blocker；旧日期 URL 已 301 → canonical（/posts/2026-05-28-chinese-food-delivery-meituan-eleme-guide/ 301 → /posts/chinese-food-delivery-meituan-eleme-guide/） |
| reason | TOP-20 Revenue #3（score 72.5, conf 80.7%, action CONTENT_COMMERCIALIZATION）；不在任何运行中实验；已有 4 个 affiliate partner；GSC 28d impressions=159（TOP 中最高之一）；页面稳定、indexable、canonical=self |

## Why Not the Other Candidates

| Candidate | Excluded | Reason |
|---|---|---|
| 144-Hour Visa (cbt-b4ff4381a014) | YES | GROWTH-05 CTR experiment RUNNING（REV001 已占用，勿混淆） |
| WeChat Pay strong (cbt-707a8899c0a7) | YES | Index recovery RUNNING（GROWTH-07C / observation） |
| High-Speed Rail / Transportation (cbt-52a577c1b2b8) | YES | Technical SEO / indexing observation + canonical cluster |
| 144-Hour Visa 15 Countries (cbt-244822dc113b) | YES | 与 144h 主题簇重叠（CTR experiment 隔离风险）；summary 有既有 malformed markdown；首段含严重 legacy persona 声明；VISA 内容策略建议先做内容修复而非 CTA 实验 |
| Brand-03 3 篇（Western Sichuan / Guilin / Hotpot） | YES | Legacy persona migration 观察中 |

## Known Limitations (locked with the candidate)

1. 页面仍含 legacy persona 内容（\"Hey, Joran Here\"、虚构点餐经历、Joran's Tips）— 本轮不修改；后续 CTA 必须避开 persona 段落，PersonaGuard 迁移另行排期。
2. 页面存在既有 UTF-8 乱码字符（文件内嵌损坏序列）— 不属本轮范围，仅记录。
3. 页面级 GA4 sessions/pageviews 不可得，使用全站 28d 值（DATA_SCOPE=sitewide）。
4. affiliate_clicks = 0（基线）；revenue = NULL（REVENUE_NOT_AVAILABLE）。
5. LOW_DATA_WARNING ACTIVE：全站 28d GSC clicks=3；任何短期波动不得判定成败。

## Experiment Isolation Checklist

- [x] Brand-03 = no overlap（pilot = Western Sichuan / Guilin / Hotpot）
- [x] Drive-001 = no overlap（全站 script；Drive 保持不动，不 A/B）
- [x] GROWTH-05 = no overlap（144h 页面）
- [x] GROWTH-07 = no overlap（WeChat 2 篇 + transport）
- [x] 无 canonical conflict / 无 index blocker / 无 redirect chain（旧 URL 已 301）
- [x] 不属于 legacy migration pilot

## Next

- P1-GROWTH-12B：在该页面新增 1 个明确、自然的 mid-content affiliate CTA（placement=`food_cta_mid_content`），保持 URL/canonical/content_id/affiliate/UTM 不变。

