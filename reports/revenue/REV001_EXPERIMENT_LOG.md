# REV001 — EXPERIMENT LOG（Affiliate CTA Placement）

- experiment_id: REV001
- 类型：CTA_PLACEMENT
- 页面：Chinese Food Delivery: Meituan & Ele.me Guide
- content_id: `cbt-e464169c4991`
- URL: https://www.chinaboundtravel.com/posts/chinese-food-delivery-meituan-eleme-guide/
- start_date: 2026-08-16
- 状态：RUNNING（decision PENDING）

## Baseline（2026-07-19 → 2026-08-15）

| Metric | Value | Scope |
|---|---|---|
| sessions | 162 | sitewide 28d |
| pageviews | 365 | sitewide 28d |
| affiliate_clicks | 0 | sitewide 28d |
| affiliate_clicks_per_1000_pageviews | 0.0 | computed |
| GSC impressions | 159 | page 28d |
| GSC clicks | 0 | page 28d |
| GSC position | 19.55 | page 28d |
| revenue | NULL | REVENUE_NOT_AVAILABLE（不伪造） |

## Old State（修改前）

- 无 mid-content CTA（affiliate-mid-cta 计数 = 0）
- 页面已有 4 个页尾 INLINE shortcode：affiliate-hotel（Booking）/ flight（Aviasales）/ esim（Airalo）/ tour（Klook）
- 无新增 partner

## New CTA（本轮唯一改动，4 行插入）

- shortcode: `{{< affiliate-mid-cta >}}`（复用 GROWTH-12 已建机制，非第二套 tracking）
- partner: `esim` → destination = hugo.toml `[params.affiliate].esim` = `https://www.airalo.com/`（与页面现有 affiliate-esim shortcode 完全一致）
- placement: `food-delivery-mid-content`
- 位置：`## How to Set Up (English Guide)` → `### Step 1: Phone Number` 段落之后（用户刚读到需要中国手机号/eSIM 验证码，上下文最相关）
- 文案：\"Setting up before you land saves time. Both apps need a Chinese phone number for the verification code. Compare eSIM options with a Chinese number ahead of your trip so you can register as soon as you arrive.\"
- 透明性：shortcode 自带 disclosure（Affiliate link - we may earn a small commission at no extra cost to you.）+ link rel=\"nofollow sponsored\"

## Measurement Plan

- PRIMARY：affiliate_clicks_per_1000_pageviews（实验期 vs baseline）
- SECONDARY：affiliate_click_rate、pageviews、sessions、GSC impressions、GSC clicks、position
- 观察窗口：>= 28 天（至 2026-09-13 起可评估）
- 样本守卫：affiliate_clicks < 20 → INSUFFICIENT_SAMPLE；禁止 1/3/7 天宣布 WIN/LOSE
- 决策规则：正向 = 相对 baseline 有意义提升 + 足够样本；中性 = 无明显变化；负向 = 明显下降

## Confounders（已记录）

1. DRIVE-001 同时 RUNNING（全站 Drive script）——本轮未改变 Drive 配置，Drive 效果与本 CTA 独立观测。
2. GROWTH-05（144h Visa CTR）运行中——不在本页面，不构成干扰。
3. Brand-03（3 篇 legacy 迁移）观察中——不涉及本页面。
4. GROWTH-07（WeChat / transport）历史观察——不涉及本页面。
5. 页面 legacy persona 内容（\"Hey, Joran Here\" 等）——明确不在本轮修改范围。
6. 页面 UTF-8 乱码字符——明确不在本轮修改范围。
7. LOW_DATA_WARNING ACTIVE：全站 28d GSC clicks=3；页面 clicks=0。任何短期波动不得判定成败。

## SEO / Affiliate Invariants（本轮验证）

- [x] URL / slug / canonical / content_id / title / description 未变
- [x] 现有 affiliate URLs / IDs / UTM / tracking_parameter 逐字节未变（token 级比对）
- [x] 只新增 1 个 CTA（对已有 partner esim 的引用）
- [x] Drive script 未变（仍 exactly 1/page）
- [x] PersonaGuard：新增文案无 forbidden 短语
