# P1-GROWTH-09 AFFILIATE REVENUE BASELINE REPORT

WORKDIR: `E:\AI\dulizhan\travel-blog`
GitHub HEAD == origin/main: `2a91494`（本轮将新增 commit）
Generated: 2026-08-16

---

## 1. Partner Inventory

`reports/revenue/AFFILIATE_PARTNER_INVENTORY.csv` — 9 个 ACTIVE partner（hugo.toml `[params.affiliate]` 配置 + 内容扫描）：

| partner | affiliate_key | pages | links | tracking |
|---|---|---|---|---|
| Klook | klook | 43 | 54 | yes |
| Booking | hotel | 39 | 51 | yes |
| Aviasales | flight | 39 | 50 | yes |
| SafetyWing | safetywing | 32 | 47 | yes (utm) |
| Airalo | esim | 34 | 45 | yes |
| Trip.com | trip | 4 | 5 | yes |
| Allianz | allianz | 1 | 3 | yes |
| World Nomads | worldnomads | 1 | 3 | yes |
| NordPass | nordpass | 0 | 0 | configured, unused |

- NordVPN（affiliatescn, offer 153）存在于 single.html article_cta 与 ab-cta 中，未计入 pages（自动区），按配置 ACTIVE
- 未修改任何 affiliate URL / ID / UTM

## 2. Content Map

`reports/revenue/AFFILIATE_CONTENT_MAP.csv` — 182 行（46 篇去重后文章 × partner），placement 分类为 INLINE（正文 shortcode/内联链接）与 CTA（ab-cta）；每篇文章另有 single.html 自动 article_cta 区（esim/vpn/hotel/klook，4 链接/页）。

## 3. Affiliate Click Tracking

- 事件模型已存在（P0-7 已实现）：`layouts/_default/single.html` 监听 `.article-affiliate` 容器点击，字段 = `content_id / partner / placement / channel / timestamp / destination`
- `tracking_schema_check` = **OK**，missing fields = none
- 同时推送 gtag 事件与 dataLayer

## 4. GA4 Readiness

- GA4 Property `541752321`，事件名 `affiliate_click`
- GA4 Data API 只读验证：HTTP 200，28d 查询可用（含 pagePath 维度）
- 当前 28d `affiliate_click` 事件数 = **0**（真实读取，无伪造）

## 5. 28d Clicks

- GSC 全站 28d clicks = 3（既有基线）
- GA4 affiliate_click 28d = 0

## 6. Revenue Availability

- `reports/revenue/AFFILIATE_REVENUE_BASELINE.csv`：`affiliate_clicks_28d` 按 GA4 per-page 归因（当前全 0）；`affiliate_sessions_28d` / `revenue_28d` = **NULL**；status = `ZERO` / `NOT_AVAILABLE`
- 无 affiliate 转化/营收 API → 明确 **REVENUE_NOT_AVAILABLE**，未猜测、未伪造

## 7. Top Commercial Pages

`reports/revenue/TOP_COMMERCIAL_PAGES.md`（按 search demand × business intent × affiliate presence）：

1. 144-hour-visa-free-transit-guide（VISA, imp=107）
2. china-transportation-complete-guide（TRAIN, imp=107）
3. china-extends-144-hour-visa-free-transit-policy（VISA, imp=87）
4. how-to-use-wechat-pay-as-a-foreigner（PAYMENT, imp=83）
5. chinese-food-delivery-meituan-eleme-guide（FOOD, imp=159，无商业加权但搜索量最高）

## 8. Affiliate Gaps

`reports/revenue/AFFILIATE_GAPS.md` + `AFFILIATE_GAPS_DETAIL.csv`（57 条）：

- A_HIGH_INTENT_NO_AFFILIATE: 0（所有高商业意图页已有联盟）
- B_AFFILIATE_LOW_VISIBILITY: 16（有联盟但 28d 0 impressions）
- C_HIGH_IMPRESSION_ZERO_CLICK: 3（imp>=100 且 clicks=0）
- D_MULTI_PARTNER_PAGE: 23（同页 >=5 个 partner）
- E_OVER_MONETIZATION: 15（同页 >=6 个 partner，人工 review 候选）

## 9. Revenue Experiment Readiness

`reports/revenue/REVENUE_EXPERIMENT_READINESS.md`：

- A. CTA placement test → READY
- B. Affiliate partner comparison → READY（partner 字段已跟踪）
- C. Content-to-affiliate conversion → PARTIAL（缺 affiliate sessions/revenue API）
- D. Travelpayouts Drive experiment → NOT_READY（本轮不启用）

## 10. Travelpayouts Drive

**DRIVE_STATUS = NOT_ENABLED**（本轮未启用、未修改任何 Drive 配置；下一轮 P1-GROWTH-10 单独处理）

## 11. Tests

- `python -m pytest tests/ -q` → **241 passed, 0 failed, 0 skipped**（新增 18 项 `test_affiliate_revenue_baseline.py`）
- `hugo --gc --minify` → exit 0
- `content_id_audit --strict` → PASS
- secret scan（含于 pytest）→ PASS
- affiliate regression（`test_affiliate_attribution.py` + `test_affiliate_revenue_baseline.py` no-mutation + `check_affiliate_rendered.cjs`）→ URL 无变更

## 12. Known Issues（本轮不修改）

- 仓库存在 9 个 duplicate-URL 文章文件（多文件同 canonicalURL，已按 URL 去重分析并在报告记录，人工 review 已存在）
- 外部 affiliate 链接健康：Airalo emrldtp timeout、Klook tpo.li 403（既有线上现象，非本轮回归；禁止本轮修改 affiliate URL，留待人工/供应商确认）
- GA4 affiliate_click 数据接近 0（流量极低，LOW_DATA_WARNING 生效）

## 判定

**P1-GROWTH-09 = PASS**

- attribution 模型 = OK（affiliate_click 事件 schema 完整）
- baseline 系统 = PASS（partner/content/revenue baseline 全部生成，revenue=NULL 未伪造）
- NEXT = P1-GROWTH-10 TRAVELPAYOUTS DRIVE EXPERIMENT
