# P1-GROWTH-12B — First Affiliate Revenue Experiment Report

- 日期：2026-08-16
- 基线：GitHub main `0d05a31`
- 状态：**PASS**
- REV001：CTA_PLACEMENT 实验已启动（RUNNING）

## 1. Experiment ID
- REV001（registry: reports/revenue/REVENUE_EXPERIMENT_REGISTRY.csv）
- minimum_observation_days = 28，status = RUNNING，decision = PENDING

## 2. Page
- Chinese Food Delivery: Meituan & Ele.me Guide
- content_id: `cbt-e464169c4991`
- URL: https://www.chinaboundtravel.com/posts/chinese-food-delivery-meituan-eleme-guide/

## 3. Partner
- **esim（Airalo）**：与页面 Step 1（需要中国手机号/eSIM 接收验证码）用户意图最直接相关
- destination = hugo.toml `[params.affiliate].esim` = `https://www.airalo.com/`（与页面现有 affiliate-esim shortcode 完全一致）
- 未新增 partner、未修改 ID/UTM/tracking_parameter

## 4. Baseline（2026-07-19 → 2026-08-15）
| Metric | Value |
|---|---|
| sessions（sitewide 28d） | 162 |
| pageviews（sitewide 28d） | 365 |
| affiliate_clicks（28d） | 0 |
| affiliate_clicks_per_1000_pageviews | 0.0 |
| GSC impressions / clicks / position | 159 / 0 / 19.55 |
| revenue | NULL（不伪造） |

## 5. CTA Copy
\"**Setting up before you land saves time.** Both apps need a Chinese phone number for the verification code. Compare eSIM options with a Chinese number ahead of your trip so you can register as soon as you arrive.\"
- 自然、透明、面向外国游客；无虚构经历/折扣/稀缺性；shortcode 自带 affiliate disclosure + rel=\"nofollow sponsored\"

## 6. Placement
- `food-delivery-mid-content`（1 个 mid-content CTA）
- 位置：`## How to Set Up` → `### Step 1: Phone Number` 段落后
- 无 hero/sidebar/footer/popup/multiple CTA

## 7. Tracking
- 复用现有 `affiliate_click` event（single.html delegate，payload 含 content_id/partner/placement/channel/destination/timestamp/tracking_parameter）
- 未建立第二套 event；CTA 链接由 shortcode 渲染（destination 来自 hugo.toml）

## 8. Invariants（全部 PASS）
- [x] URL / slug / canonical / content_id / title / description 未变（与 HEAD 逐字段比对）
- [x] 现有 affiliate URLs / UTM 逐字节未变（hugo.toml affiliate section 与 HEAD 一致）
- [x] Drive script 未变（head.html 与渲染页 exactly 1）
- [x] 只新增 1 个 CTA（content/post changes = 1）
- [x] PersonaGuard：CTA 文案无 forbidden 短语

## 9. Tests
- 新增 `tests/test_growth12b_revenue_experiment.py`（15 项，覆盖任务要求的 12 点 + tracking/rendered 验证）
- 更新 5 个 scope-guard 白名单（brand_identity_p2 / brand_legacy_pilot / travelpayouts_drive / growth05 / growth07）
- `python -m pytest tests/ -q` → **340 passed, 0 failed, 0 skipped**
- `hugo --gc --minify` → PASS
- `content_id_audit --strict` → PASS（57/57）
- internal link audit / affiliate regression / meta audit / secret scan / workflow YAML → 全部 PASS（测试覆盖）

## 10. Production Deployment
- commit `feat: launch REV001 affiliate CTA experiment` → push → GitHub Actions → Cloudflare Pages 自动部署（不手动部署）
- 上线后验证：page=200、CTA exactly 1、Drive exactly 1、affiliate URL=esim config、content_id/canonical/title/meta 不变

## 11. Observation Window
- >= 28 天（2026-08-16 起，最早 2026-09-13 评估）
- 禁止 1/3/7 天调整或宣布结果

## 12. Success Criteria
- PRIMARY：affiliate_clicks_per_1000_pageviews（实验期 vs baseline 0.0）
- SECONDARY：affiliate_click_rate、pageviews、sessions、GSC impressions/clicks、position
- POSITIVE = 有意义提升 + 足够样本；NEUTRAL = 无明显变化；NEGATIVE = 明显下降
- 样本守卫：affiliate_clicks < 20 → INSUFFICIENT_SAMPLE；不宣布 WIN/LOSE

## 13. Confounders
1. DRIVE-001 同时 RUNNING——Drive 配置本轮未改变，独立观测
2. GROWTH-05（144h）不在本页面
3. Brand-03 不涉及本页面
4. 页面 legacy persona 不在本轮修改范围
5. 页面 UTF-8 乱码不在本轮修改范围
6. LOW_DATA_WARNING ACTIVE（全站 28d GSC clicks=3）

## 14. Current Status
- CTA launched：PASS
- tracking PASS / SEO invariants PASS / tests PASS / production PENDING（部署后验证）

## Final Verdict
- **P1-GROWTH-12B = PASS**
- NEXT = P1-GROWTH-13 REVENUE MEASUREMENT REVIEW
