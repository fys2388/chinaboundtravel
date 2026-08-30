# P1-GROWTH-30 — Unified Growth Priority Model

- Date: 2026-08-29
- Output: `reports/management/GROWTH_PRIORITY_QUEUE.csv`
- 设计约束：不是合并旧排名，而是从原始字段重新计算确定性统一队列。

## 输入数据

- `CONTENT_SEO_INVENTORY.csv`：impressions/clicks/position/indexed
- `content_opportunity_scores.csv`：query_count、duplicate_count
- `REVENUE_OPPORTUNITY_SCORES.csv`：commercial_intent、partner_count、has_affiliate
- `AFFILIATE_FUNNEL_INVENTORY.csv`：CTA 数量
- `CONTENT_TRUST_AUDIT.csv`：事实/AI/品牌/SEO issue 数
- `content/social/inventory.json`：社交发布与 metrics
- 实验注册表 + `CANONICAL_CONFLICT_QUEUE.md`：冻结与技术阻断

## 子分公式（0-100）

| 分项 | 公式 |
|---|---|
| traffic | 15 + 85 * log1p(impressions)/log1p(max_imp)，点击加成，封顶 100 |
| seo | indexed 30 + position 0-50 + CTR 0-20 + query_count 0-20，封顶 100 |
| engagement | 社交曝光/点击归一化；有发布无数据给 10 |
| commercial | commercial_intent 映射 25-90 + query_count 加成，封顶 100 |
| affiliate | CTA 数量 *12 + partner_count *4 + has_affiliate 10，封顶 100 |
| revenue | 当前全站无收入证据，统一 0 |
| trust | 100 - fact*3 - AI*2 - brand*1 - SEO*1，最低 0 |
| risk | FROZEN +50，canonical conflict +30，WAIT_RECRAWL +20，fact>10 +10，duplicate +10 |

统一优先级分 =
0.25*traffic + 0.20*seo + 0.15*engagement + 0.15*commercial +
0.10*affiliate + 0.05*revenue + 0.10*trust - 0.15*risk（0-100 封顶）。

## 状态与动作

- `FROZEN`：活动实验页面，禁止自动执行。
- `WAIT`：等待 recrawl / 样本不足 / 数据缺失。
- `TECHNICAL_FIX`：canonical 冲突、索引或重定向问题。
- `READY`：可进入治理流程。

动作优先级：FROZEN -> WAIT -> TECHNICAL_FIX -> FACT_CHECK -> OPTIMIZE ->
SCALE -> MONITOR。事实核查是内容改写的守门动作。

## TOP 10

| # | content_id | URL | priority | action | status | traffic | seo | engagement | commercial | affiliate | revenue | trust | risk |
|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | cbt-b4ff4381a014 | /posts/144-hour-visa-free-transit-guide/ | P0 | FROZEN | FROZEN | 93.4 | 60 | 100 | 91.5 | 86 | 0 | 71 | 50 |
| 2 | cbt-244822dc113b | /posts/china-extends-144-hour-visa-free-transit-policy-to-more-countries/ | P0 | FACT_CHECK | READY | 90 | 70 | 0 | 89.7 | 90 | 0 | 63 | 0 |
| 3 | cbt-52a577c1b2b8 | /posts/china-transportation-complete-guide-trains-subways-taxis-and-more/ | P1 | FACT_CHECK | READY | 93.4 | 64 | 0 | 70.4 | 90 | 0 | 77 | 10 |
| 4 | cbt-707a8899c0a7 | /posts/how-to-use-wechat-pay-as-a-foreigner/ | P1 | FACT_CHECK | READY | 89.2 | 60 | 0 | 87.2 | 70 | 0 | 71 | 0 |
| 5 | cbt-e464169c4991 | /posts/chinese-food-delivery-meituan-eleme-guide/ | P1 | FROZEN | FROZEN | 100 | 78 | 0 | 55.8 | 86 | 0 | 62 | 50 |
| 6 | cbt-80f6c218ad94 | /posts/western-sichuan-overland-camping-route/ | P1 | FACT_CHECK | READY | 72.2 | 74 | 0 | 40.6 | 90 | 0 | 54 | 0 |
| 7 | cbt-de065751769e | /posts/china-transportation-complete-guide-trains-subways-taxis-and-more/ | P1 | FACT_CHECK | READY | 93.4 | 64 | 0 | 23.6 | 60 | 0 | 86 | 10 |
| 8 | cbt-34777b6c17c1 | /posts/zhangjiajie-avatar-mountains-complete-guide-to-chinas-most-spectacular-park/ | P1 | FACT_CHECK | READY | 66 | 62 | 0 | 48 | 100 | 0 | 52 | 0 |
| 9 | cbt-9e2f5ffa1b6d | /posts/accommodation-tips-guide/ | P1 | FACT_CHECK | READY | 63.4 | 66 | 0 | 73.3 | 58 | 0 | 67 | 10 |
| 10 | cbt-bf4ec5e57a07 | /posts/guilin-and-yangshuo-the-ultimate-karst-landscape-guide-for-2026/ | P1 | FACT_CHECK | READY | 68.9 | 70 | 0 | 38.2 | 74 | 0 | 59 | 0 |

## 约束

- 冻结实验与未解决技术阻断不会自动变成可执行动作：状态字段强制 FROZEN/WAIT/
  TECHNICAL_FIX。
- 无收入证据，revenue_score 一律为 0，不虚构转化数据。
- 队列由 `python scripts/growth_control_plane.py` 幂等生成。
