# P1-REPORT-03 — Unified ChinaBound 2.0 Reporting Template Rebuild

- Status: **PASS**
- Date: 2026-08-19
- Workdir: `E:\AI\dulizhan\travel-blog`
- Scope: reports / scripts / tests / docs only (no content, URL, affiliate, UTM, GA4 schema, Drive, or GSC config changes)

## 1. Overview

P1-REPORT-03 aligns the Daily / Weekly / Monthly / Quarterly / Yearly reporting stack with the ChinaBound Travel 2.0 operating model. The five management reports already render from the single KPI snapshot (`reports/management/REPORTING_SNAPSHOT.json`) via `scripts/reporting_engine.py`; this task removes the remaining 1.0 alert/KPI behavior that produced false RED conditions on zero-value days and aligns the shared advice engine and Feishu risk logic with the 2.0 status model.

No second KPI system was created. KPI values are only ever formatted from the snapshot; report scripts never re-derive them.

## 2. Five report changes

All five reports (`daily`, `weekly`, `monthly`, `quarterly`, `yearly`) render from `REPORTING_SNAPSHOT.json` and use the nine standard business domains:

- Traffic
- SEO / GSC
- Content Assets
- Brand 2.0
- Affiliate Funnel
- Revenue
- Experiments
- Commercial Clusters
- Operations

Per-period behavior verified in the unified engine:

| Report | Purpose | Key focus |
|---|---|---|
| Daily | Operations + anomaly detection | DoD changes, technical health, indexing changes, experiment events, affiliate events, alerts, active tasks |
| Weekly | Growth + experiment management | WoW traffic, GSC visibility, content asset health, legacy persona migration, affiliate funnel, revenue, experiments, commercial clusters, blockers, next-week actions |
| Monthly | Business review | MoM trends, indexed content growth, ranking movement, high-value content, brand migration, affiliate funnel, revenue, experiment outcomes, cluster ROI/readiness, resource allocation |
| Quarterly | Strategic review | What worked / failed, cluster resourcing, experiment scale/stop decisions, content create/update/merge, automation simplification |
| Yearly | Annual business / asset review | Traffic and search visibility growth, content asset value, brand maturity, commercial funnel maturity, revenue, experiment portfolio, operational maturity, strategic moat, next-year strategy |

Report-wide 2.0 guarantees (enforced by tests):

- Zero new articles is NOT scored as failure.
- GSC with no yesterday data renders as `NOT_AVAILABLE` and uses the latest valid cached window (`INSUFFICIENT_SAMPLE` until a prior snapshot exists).
- Revenue without a real source renders as `NULL / REVENUE_NOT_AVAILABLE`, never `$0`.
- Experiments use the real registry and are `INSUFFICIENT_SAMPLE` when observation `< 28d` or clicks `< 20`; no WIN/LOSE is declared.
- Affiliate funnel separates website-side (`affiliate_impression`, `affiliate_click`, `affiliate_outbound`) from partner-side (clicks, orders, commission) and never combines them.
- Content KPI uses total/updated/indexed/high-value assets, recovery, migration, technical fixes, and opportunity queue instead of "new articles per day".
- Brand 2.0 tracks core compliance, legacy persona count, migrations, logo/favicon status, and editorial identity.

## 3. Feishu changes

- `scripts/feishu_weekly_report.py`
  - Zero revenue + low coverage: moved from 🔴 RED to 🟡 YELLOW, labeled "Revenue NOT_AVAILABLE，非故障".
  - Persona year-conflict count: moved from 🔴 RED to 🟡 YELLOW ("按优先级迁移 legacy 文案").
  - Auto-diagnosis section header changed from "🔴 核心问题：供给侧缺失" to "⚠️ 供给侧提示：变现链路待验证（Revenue NOT_AVAILABLE，非故障）".
  - Comparison-table conflict status emoji corrected from 🔴 to 🟡.
  - "启用 Travelpayouts Drive 自动推荐组件" plan task replaced with "评估 Travelpayouts Drive 对核心页面的覆盖价值（人工决策）".
- `scripts/feishu_monthly_report.py`
  - Zero revenue + low coverage: moved from 🔴 RED to 🟡 YELLOW ("Revenue NOT_AVAILABLE，非故障").
  - Persona year-conflict: moved from 🔴 RED to 🟡 YELLOW.
  - Affiliate coverage status emoji: 🔴 → 🟡 (coverage below 30 is a funnel-readiness note, not an outage).
- `scripts/report_advice.py` (shared advice engine consumed by daily / weekly / monthly Feishu pushes)
  - Removed automatic "把有曝光无点击的页面标题改到 60 字符内" → replaced with keyword-first title guidance (城市/主题+年份).
  - Removed automatic "在热门文章首屏下方加入 Travelpayouts Drive / 对比表" → replaced with manual CTA-visibility evaluation on high-traffic pages.

Feishu pushes keep pulling live operational numbers (GA4/GSC/affiliate APIs) because the snapshot is a 28d cached artifact, but they share the same status model and advice rules via `report_advice.py` + `okr_utils.py`; no Feishu script re-derives snapshot KPIs.

## 4. KPI rules changed

- Alert engine now only emits meaningful conditions:
  - RED: production outage, security issue, known broken affiliate/revenue path, critical indexing regression, workflow failure loop.
  - ORANGE: significant traffic decline, canonical conflict, measurement failure, experiment blocked.
  - YELLOW: low sample, waiting recrawl, data unavailable, legacy content remaining.
- Revenue rule: no real revenue source → `value = NULL`, `status = REVENUE_NOT_AVAILABLE`; NULL is never converted to `$0`.
- Data source labels standardized: `LIVE | CACHED | LOCAL | NOT_AVAILABLE`.
- Statuses standardized: `GREEN | YELLOW | ORANGE | RED | INSUFFICIENT_SAMPLE | WAITING | NOT_STARTED`.
- Experiment status: `INSUFFICIENT_SAMPLE` when observation `< 28d` OR `affiliate_clicks < 20`; no WIN/LOSE.

## 5. Old 1.0 rules removed / downgraded

| 1.0 rule | Before | After |
|---|---|---|
| Fixed daily article quota | RED when `new_articles = 0` | No failure; content KPI uses asset quality |
| Fixed daily search impressions target | RED when GSC yesterday = 0 | `NOT_AVAILABLE` / latest cached window |
| Fixed daily affiliate commission target | RED when revenue = 0 | YELLOW "Revenue NOT_AVAILABLE，非故障" |
| Fixed daily email signup target | RED when signups = 0 | YELLOW (only when MailerLite connected) |
| "Enable Travelpayouts Drive" | automatic plan task | manual evaluation task (human decision) |
| "GSC not authorized" legacy task | repeated RED task | YELLOW with service-account check action |
| Completed infrastructure tasks | reappeared in action lists | removed; task states PASS/PARTIAL |
| Automatic "change title to 60 characters" | automatic advice | keyword-first title guidance |
| Automatic "move affiliate CTA above the fold" | automatic advice | manual CTA visibility evaluation |

These items remain valid as business reference targets but no longer auto-alert purely because today's value is zero.

## 6. Validation results

| Check | Command | Result |
|---|---|---|
| Full test suite | `python -m pytest tests/ -q` | 626 passed |
| P1-REPORT-03 tests | `tests/test_report_03.py` | 11 passed |
| GROWTH-05 scope guard | `tests/test_growth05_first_content_action.py` | 10 passed |
| Content ID audit | `python scripts/content_id_audit.py audit --strict` | PASS (60/60) |
| Hugo build | `hugo --gc --minify` | PASS (377 pages) |
| Brand identity audit | `python scripts/brand_identity_audit.py` | PASS (12/15, 3 pre-existing WARN) |
| Feishu weekly risk model | `_detect_risk_level` unit check | zero revenue/conflict → YELLOW, no RED |
| Feishu monthly risk model | `_detect_risk_level` unit check | zero revenue/conflict → YELLOW, no RED |
| Daily priority-task linkage | `generate_priority_tasks` unit check | OKR <50% → 🔴 task; 100% → excluded |

New tests cover: NULL revenue, NOT_AVAILABLE GSC, LOW_DATA_WARNING, INSUFFICIENT_SAMPLE, no false RED for zero content production, no KPI contradictions across the five reports, snapshot-as-source for all periods, UTF-8 output, and deterministic rendering.

## 7. Files changed

- `scripts/report_advice.py`
- `scripts/feishu_weekly_report.py`
- `scripts/feishu_monthly_report.py`
- `tests/test_report_03.py` (new)
- `tests/test_growth05_first_content_action.py` (allowed-scope whitelist updated for P1-REPORT-03 and P1-GROWTH-24/25)
- `reports/P1_BRAND_02_BRAND_IDENTITY_AUDIT.md` (regenerated audit layers)

## 8. Follow-up notes

- Feishu scripts keep live data collection by design; if a single-source-of-truth push is required later, the next step is a snapshot-reading path for the daily card (beyond this task's scope).
- Quarterly / yearly Feishu messages should be wired to the management report output in CI (engine already renders them).
- Do NOT commit or push automatically (per task instructions).
