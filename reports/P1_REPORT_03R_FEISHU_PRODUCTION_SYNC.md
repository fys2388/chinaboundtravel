# P1-REPORT-03R — Feishu 2.0 Production Sync Verification

- Status: **PASS**
- Date: 2026-08-19
- Workdir: `E:\AI\dulizhan\travel-blog`
- Scope: reporting path only (`scripts/feishu_daily_report.py`, `scripts/okr_utils.py`, `scripts/report_advice.py`). No website, layout, affiliate URL, UTM, experiment, GA4 schema, or GSC config changes.

## 1. Local vs GitHub

| Check | Value |
|---|---|
| `LOCAL_HEAD` | `02de656ca9b81369e7a40a3f36c7cd1eb7b75cd5` |
| `ORIGIN_MAIN` | `02de656ca9b81369e7a40a3f36c7cd1eb7b75cd5` |
| `LOCAL_HAS_UNPUSHED_REPORTING_CHANGES` | **YES** |

Root cause of "production Feishu still shows 1.0 logic": `LOCAL_HEAD == ORIGIN_MAIN`, but the P1-REPORT-03 / 2.0 changes live only in the working tree:

- `scripts/feishu_daily_report.py` (M)
- `scripts/okr_utils.py` (M)
- `scripts/report_advice.py` (M)
- `tests/test_report_03.py` (untracked)
- `reports/P1_REPORT_03_UNIFIED_REPORTING_TEMPLATE_REBUILD.md` (untracked)

The GitHub Actions scheduled run (`cron 0 1 * * *` = 09:00 Asia/Shanghai) checks out `origin/main`, which still contains the 1.0 alert/OKR logic. Fix is local-only per instructions; no push performed.

## 2. Feishu execution path

- `.github/workflows/feishu-daily-report.yml` → `python scripts/feishu_daily_report.py`
- `feishu_daily_report.py` imports `okr_utils` + `report_advice` (shared helpers), and previously did **not** read `reports/management/REPORTING_SNAPSHOT.json`.
- Before this fix: `FEISHU_NOT_USING_UNIFIED_SNAPSHOT` = **TRUE**.
- After this fix: `feishu_daily_report.py` loads `REPORTING_SNAPSHOT.json` via `load_reporting_snapshot()` and uses it as the cached fallback window for GSC and as the revenue status reference. KPI values are never recomputed in Feishu; the snapshot remains the single KPI source for status labels (`CACHED / NOT_AVAILABLE / REVENUE_NOT_AVAILABLE`).

## 3. 2.0 rule checks (dry-run, real 2026-08-18 data)

| Rule | Expected | Observed | Result |
|---|---|---|---|
| A. Revenue | `NULL / REVENUE_NOT_AVAILABLE`, not `$0.00` | `收入状态: REVENUE_NOT_AVAILABLE`；`合计昨日佣金: REVENUE_NOT_AVAILABLE（无结算佣金，不折算 $0）` | PASS |
| B. GSC | `NOT_AVAILABLE` + cached window, no auto "authorize" unless auth fails | `搜索曝光 NOT_AVAILABLE（缓存 234）` / `搜索点击 NOT_AVAILABLE（缓存 0）`；auth-failure note kept because the service account is genuinely not an owner | PASS |
| C. Daily article count | 0 articles NOT RED | `日新增文章 0篇/1篇 0% 🟢` | PASS |
| D. Affiliate advice | no auto "move CTA above the fold" while REV001/REV002 frozen | `CTA 位置变更属 REV001/REV002 冻结范围，需人工复核后评估` | PASS |
| E. SEO advice | no auto title-change on zero GSC | `（不自动改标题）` on both organic/impression advice | PASS |
| F. MailerLite | `NOT_AVAILABLE / INTEGRATION_ERROR`, not subscriber=0 | `总订阅人数 未连接（API 认证失败）` | PASS |
| G. Automation status | actual workflow state | `CI 状态未获取（本地预览）` when `GITHUB_TOKEN` absent; real state shown when token present (CI path) | PASS |

## 4. Data source consistency

Feishu daily is a live yesterday window (`LIVE`), the snapshot is a 28d cached window (`CACHED`, `as_of 2026-08-17`). Consistency handling:

| KPI | Feishu (LIVE) | Snapshot (CACHED 28d) | Status |
|---|---|---|---|
| Revenue | `REVENUE_NOT_AVAILABLE` (no settlement commission) | `revenue = NULL / NOT_AVAILABLE` | consistent status |
| GSC impressions | `NOT_AVAILABLE（缓存 234）` fallback | `gsc_impressions_28d = 234 / CACHED / OK` | same cached window, labelled |
| GSC clicks | `NOT_AVAILABLE（缓存 0）` fallback | `gsc_clicks_28d = 0 / CACHED / OK` | same cached window, labelled |
| 0 new articles | `🟢 INFO` | content KPI does not use daily quota | no contradiction |

No KPI contradiction: both systems now label revenue as NOT_AVAILABLE and use the same cached GSC window; every fallback value is explicitly tagged with its source label.

## 5. Changes made (reporting path only)

- `scripts/feishu_daily_report.py`
  - Added `load_reporting_snapshot()` reading `reports/management/REPORTING_SNAPSHOT.json`.
  - `collect_data()` attaches the snapshot; fixed missing `gsc_data_available` initial flag so unavailable GSC is `NOT_AVAILABLE` instead of a fake `0`.
  - GSC block renders `NOT_AVAILABLE` + cached window when yesterday has no data.
  - Revenue block adds `收入状态: REVENUE_NOT_AVAILABLE`; total commission renders `REVENUE_NOT_AVAILABLE` instead of `$0.00` when no settlement commission exists.
  - Automation status shows `CI 状态未获取（本地预览）` locally instead of misleading `未运行/未配置`.
  - `generate_priority_tasks` skips unavailable / zero-value fixed quotas (no false RED for article/GSC/commission/email).
- `scripts/okr_utils.py`
  - `_source_available()` distinguishes real 0 from disconnected sources (GSC/Travelpayouts/MailerLite flags).
  - `build_okr_progress()` 2.0 status: unavailable → `⚪ NOT_AVAILABLE`; 0 new articles → `🟢 INFO`; other 0 values → `🟡` (not RED).
  - `build_okr_section()` renders unavailable rows as `未连接 | - | ⚪`.
- `scripts/report_advice.py`
  - Removed auto "move CTA above the fold" advice (REV001/REV002 frozen) → manual review note.
  - Removed auto title-change advice on zero organic/impressions → "补内链/内容密度/持续提交 sitemap（不自动改标题）".

## 6. Validation

| Check | Command | Result |
|---|---|---|
| Full test suite | `python -m pytest tests/ -q` | 626 passed |
| Feishu dry-run | `python scripts/feishu_daily_report.py --dry-run` | PASS (real 2026-08-18 data) |
| Revenue rule | dry-run contains `REVENUE_NOT_AVAILABLE`, no auto `$0.00` total | PASS |
| GSC rule | dry-run contains `NOT_AVAILABLE（缓存 234）` | PASS |
| 0 articles | dry-run OKR shows `🟢` not RED | PASS |
| CTA advice | dry-run shows frozen-scope manual review | PASS |
| SEO advice | dry-run shows `不自动改标题` | PASS |
| MailerLite | dry-run shows `未连接（API 认证失败）` | PASS |
| Automation | dry-run shows `CI 状态未获取（本地预览）` | PASS |

## 7. Required next step for production

Commit and push the working-tree changes (P1-REPORT-03 + P1-REPORT-03R) so the scheduled GitHub Actions run executes the 2.0 code. Per instructions, no push was performed automatically.

Suggested commit:
```
feat(report): P1-REPORT-03R 飞书消费统一快照 + 2.0 告警模型上线

- 飞书日报读取 REPORTING_SNAPSHOT.json 作为 GSC/收入缓存回退
- 移除 0 值固定配额红灯（文章/曝光/佣金/订阅）
- REV001/REV002 冻结期不再自动建议 CTA 位置变更
- GSC 无昨日数据 → NOT_AVAILABLE + 缓存窗口
- 收入无结算佣金 → REVENUE_NOT_AVAILABLE，不折算 $0
- MailerLite 未连接 → NOT_AVAILABLE/INTEGRATION_ERROR
```

Final: **P1-REPORT-03R = PASS** (local reporting path fixed; production activation requires push of the working tree).

## 8. Production deployment verification (2026-08-19)

Deployment executed in this session via `gh` CLI (logged in as `fys2388`); browser graphical control was unavailable in this session, so GitHub was verified with the authenticated CLI instead of the browser UI.

| Step | Detail | Result |
|---|---|---|
| Pre-deploy local head | `02de656` (reporting changes uncommitted) | confirmed |
| Pre-deploy origin/main | `387ed9e` (bot commits only, no 2.0 code) | confirmed via `gh run list` + fetch |
| Commit | `9a4ca09 feat(report): P1-REPORT-03/03R 2.0 报表体系线上部署` (9 files, +560/-47) | pushed |
| Rebase | local commit rebased onto `387ed9e` (non-fast-forward) | done |
| Manual workflow run | `32254050848` (`workflow_dispatch`, ref main) | success |
| Artifact | `report_2026-08-19.json` (4,644 B) | contains `reporting_snapshot` |
| Revenue | `revenue_value: null`, `revenue_status: NOT_AVAILABLE` | PASS |
| GSC | `gsc_label: CACHED`, 28d cache window 234 impressions / 0 clicks | PASS |
| OKR: 0 new articles | `日新增文章 0篇/1篇 0% 🟢` (INFO, not RED) | PASS |
| OKR: 0 commission | `日联盟佣金 0$ 🟡` (reference target, not RED) | PASS |
| Advice | REV001/REV002 frozen-scope note + `不自动改标题` present | PASS |
| data_status | `GSC已连接但昨日无搜索数据（新站正常现象）`; no false auth alert | PASS |
| MailerLite | API reachable (`ml_available: true`), real 0 subscribers | PASS |
| Actions post-step | OKR snapshot auto-committed as `7d2bc38 [skip ci]` | PASS |

Full test suite: `626 passed in 33.22s` (local). Production artifact now renders from `REPORTING_SNAPSHOT.json` with the unified status model.

Final: **P1-REPORT-03R = PASS** (reporting path fixed, deployed to `origin/main`, verified on a live workflow run).
