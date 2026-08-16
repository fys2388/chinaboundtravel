# P1-GROWTH-10B DRIVE REVENUE BASELINE REPORT

WORKDIR: `E:\AI\dulizhan\travel-blog`
GitHub main: `7b39f11`（本轮新增 commit）
Generated: 2026-08-16

---

## 1. Drive Status

- **DRIVE STATUS = ACTIVE**（Travelpayouts 面板检测成功，FULL CAPACITY）
- Script: 全站 exactly 1 次（本轮线上复检 9 页全部 = 1）
- 本轮未重新安装、未修改 Drive script

## 2. Activation Date

- `DRIVE_ACTIVE_DATE = 2026-08-16`
- 记录于 `reports/revenue/TRAVELPAYOUTS_DRIVE_BASELINE.md`（activation_date / site / drive_status / script_status / baseline_period）

## 3. Pre-Drive Baseline（28d，2026-07-19 .. 2026-08-15）

`reports/revenue/PRE_DRIVE_BASELINE.csv`（190 行，按 page/content_id/partner）：

- GA4（真实只读）：28d sessions = **162**，pageviews = **365**
- GA4 affiliate_click 事件 = **0**
- affiliate clicks / 1000 sessions = **0.0**
- GSC：全站 clicks 极低（≈3/28d），impressions 按页记录
- **Revenue = NULL**（无 affiliate 营收 API，明确 REVENUE_NOT_AVAILABLE，未伪造）

## 4. Post-Drive Status

- `days_since_active = 0` → **INSUFFICIENT_SAMPLE**
- 不因 1–7 天数据宣布 WIN/LOSE；观察期 >= 28 天

## 5. Affiliate Tracking Health

`reports/revenue/AFFILIATE_TRACKING_HEALTH.md` → **PASS**

- 事件 `affiliate_click`：content_id / partner / placement / channel / timestamp / destination 全部存在
- gtag event + dataLayer push 均正常；未新增第二套 tracking

## 6. Top Commercial Pages

`reports/revenue/TOP_COMMERCIAL_PAGES_DRIVE.md`（GSC demand × intent × affiliate presence）：

1. 144-hour-visa-free-transit-guide（VISA, imp=107）
2. china-transportation-complete-guide（TRAIN, imp=107）
3. china-extends-144-hour-visa-free-transit-policy（VISA, imp=87）
4. how-to-use-wechat-pay-as-a-foreigner（PAYMENT, imp=83）
5. chinese-food-delivery-meituan-eleme-guide（FOOD, imp=159，无商业加权但流量最高）

## 7. Revenue Availability

- **REVENUE_NOT_AVAILABLE**：无 affiliate 转化/营收 API 接入
- 当前以 `affiliate_clicks_per_1000_sessions` 作为 DRIVE-001 主指标（可观测）
- 未来接入营收 API 后切换 `affiliate_revenue_per_1000_sessions`

## 8. Measurement Model

新增 `scripts/revenue_measurement.py`：

- CLI：`--days` / `--partner` / `--content-id` / `--drive-state` / `--output`
- GA4 只读：sessions、pageviews、affiliate_click（按 pagePath）
- GSC：page_performance / raw_pages 关联
- 纯函数：`classify_drive_state`、`per1000`、`sample_guard`、`build_pre_drive_rows`、`rank_commercial_drive`
- 输出 `reports/revenue/REVENUE_DASHBOARD.md`（PRE_DRIVE / POST_DRIVE / INSUFFICIENT_SAMPLE）

## 9. Experiment Registry

`reports/revenue/DRIVE_EXPERIMENT_REGISTRY.csv`：

- DRIVE-001 | start 2026-08-16 | baseline pre-drive 28d | post >= 28d | status **RUNNING**
- PRIMARY: `affiliate_clicks_per_1000_sessions`（营收 API 可用后切换 revenue 指标）
- SECONDARY: affiliate CTR / sessions / pageviews / GSC clicks / impressions

## 10. Tests

- 新增 `tests/test_revenue_measurement.py`（11 项）：pre/post periods、null revenue、per-1000 归一化、insufficient sample、deterministic ranking、per-page attribution
- `python -m pytest tests/ -q` → **262 passed, 0 failed, 0 skipped**
- `hugo --gc --minify` → exit 0
- `content_id_audit --strict` → PASS
- secret scan（含于 pytest）→ PASS
- affiliate regression（含于 pytest）→ PASS
- 说明：`test_growth05_first_content_action.py` 的范围测试按历史 diff 演进，已将 GROWTH-10A 授权的 `layouts/partials/head.html` 加入允许列表（与 GROWTH-07 测试一致）；content/ 保护不变

## 11. Observation Plan

- 保持 Drive 当前版本稳定：不做 A/B、不删除、不重装、不同时改大量 CTA
- 每 7 天运行 `python scripts/revenue_measurement.py` 快照
- 满 28 天（2026-09-13 起）首次判定 POST_DRIVE
- clicks >= 20 且观察 >= 28 天才允许初步结论

## 判定

**P1-GROWTH-10B = PASS**

- Drive = ACTIVE ✓
- Tracking = PASS ✓
- Measurement system = PASS ✓（DRIVE-001 RUNNING，INSUFFICIENT_SAMPLE 保护生效）
- NEXT = P1-GROWTH-11 REVENUE OPTIMIZATION
