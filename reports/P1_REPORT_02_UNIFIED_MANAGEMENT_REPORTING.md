# P1-REPORT-02 — ChinaBound Travel 2.0 Unified Management Reporting

- Generated: 2026-08-17
- Status: **PASS**

## 1. Unified architecture

ONE source of truth feeds ALL reports — no five independent KPI systems.

```
repo artifacts (GSC/GA4/funnel/revenue/registry/inventory/brand/cluster/ops)
        |
        v
scripts/reporting_kpi_engine.py  -->  reports/management/REPORTING_SNAPSHOT.json
        |
        v
scripts/reporting_engine.py  -->  daily / weekly / monthly / quarterly / yearly
        |                        + master dashboard + ALERTS.md
        v
reports/REPORT_INDEX.md (CURRENT / HISTORICAL / STALE / SUPERSEDED)
```

## 2. Deliverables created

| Artifact | Path |
|---|---|
| KPI snapshot (single source) | reports/management/REPORTING_SNAPSHOT.json + snapshots/REPORTING_SNAPSHOT_2026-08-17.json |
| Data dictionary | reports/management/REPORTING_DATA_DICTIONARY.md |
| KPI definitions | reports/management/REPORTING_KPI_DEFINITIONS.md |
| Status model | reports/management/REPORTING_STATUS_MODEL.md |
| Daily report | reports/management/daily/CHINABOUND_TRAVEL_2_0_DAILY.md |
| Weekly report | reports/management/weekly/CHINABOUND_TRAVEL_2_0_WEEKLY.md |
| Monthly report | reports/management/monthly/CHINABOUND_TRAVEL_2_0_MONTHLY.md |
| Quarterly report | reports/management/quarterly/CHINABOUND_TRAVEL_2_0_QUARTERLY.md |
| Yearly report | reports/management/yearly/CHINABOUND_TRAVEL_2_0_YEARLY.md |
| Master dashboard | reports/CHINABOUND_TRAVEL_2_0_MASTER_DASHBOARD.md |
| Management alerts | reports/management/ALERTS.md |
| Report index | reports/REPORT_INDEX.md |
| KPI engine | scripts/reporting_kpi_engine.py |
| Reporting engine | scripts/reporting_engine.py |
| Tests | tests/test_reporting_kpi_engine.py + tests/test_reporting_engine.py |

## 3. One unified KPI source

- All KPI values exist only in REPORTING_SNAPSHOT.json.
- The five period reports format snapshot values; they never re-derive KPIs (no duplicated calculation).
- KPI fields: name, meaning, value, unit, data_source_type, source, calculation, update_frequency, baseline, valid_period, status.
- Data source labels: LIVE / CACHED / LOCAL / NOT_AVAILABLE — every value carries exactly one.
- Revenue: NULL (REVENUE_NOT_AVAILABLE) everywhere; nothing fabricated.

## 4. Period comparison

- DoD / WoW / MoM / QoQ / YoY implemented against the closest prior dated snapshot
  (archived in reports/management/snapshots/).
- First run has no prior snapshot → all rows **INSUFFICIENT_SAMPLE** (by design, not fabricated).
- Once a second snapshot exists, deltas are computed automatically.

## 5. Low-data protection

- Guards preserved: GSC low sample, affiliate clicks < 20, revenue unavailable.
- NEW: LOW_DATA_WARNING banner + 9 deterministic low-data reasons in the snapshot and ALERTS.md.
- No WIN/LOSE / success/failure declarations below 28d observation or 20 clicks.
- Alert levels GREEN / YELLOW / ORANGE / RED derived from snapshot evidence only.
- Current level: **YELLOW** (low sample, 6 canonical conflicts, 25 legacy-persona posts, 2 WAITING_RECRAWL).

## 6. Current 2.0 baseline (from real artifacts)

| KPI | Value | Source type |
|---|---|---|
| Published posts | 60 | CACHED |
| content_id | 60/60 (audit PASS) | CACHED |
| Sessions 28d | 166 | CACHED (GA4_API 2026-08-17) |
| Pageviews 28d | 374 | CACHED |
| GSC page impressions 28d | 1168 | CACHED |
| GSC page clicks 28d | 3 (LOW_DATA) | CACHED |
| Indexed / not indexed (GSC UI) | 69 / 89 | CACHED (2026-08-16) |
| Affiliate clicks 28d | 0 (LOW_DATA) | CACHED |
| CTA inventory | 277 rows / 45 pages | CACHED |
| Drive | ACTIVE (DRIVE-001) | CACHED |
| Revenue | NULL / REVENUE_NOT_AVAILABLE | NOT_AVAILABLE |
| Legacy persona posts | 25 | LOCAL |
| Logo/favicon | LOGO_REPLACEMENT_READY | LOCAL |

Experiments: REV001 RUNNING · REV002 RUNNING (frozen) · REV003 PENDING · DRIVE-001 RUNNING ·
GROWTH-05 RUNNING · WeChat Pay recovery WAITING_RECRAWL · High-Speed Rail recovery WAITING_RECRAWL.

Commercial clusters: Transportation READY (score 77, impressions 321) · Payment HOLD (64, 85) ·
Connectivity HOLD (39, 0).

## 7. Report consistency

- All five periods share the same KPI definitions, experiment IDs, content count (60), brand status,
  revenue definitions (NULL) and data source labels — enforced by construction (one snapshot) and
  verified by tests (test_consistent_content_count, test_revenue_null_everywhere).

## 8. Outdated report cleanup

- Historical reports preserved (no deletion).
- reports/REPORT_INDEX.md classifies each important report: CURRENT / HISTORICAL / STALE / SUPERSEDED,
  with purpose, source of truth, and superseded-by mapping.
- content_inventory.csv marked SUPERSEDED; daily_search_performance* and 08-16 GSC snapshots marked STALE.

## 9. Validation results

| Check | Result |
|---|---|
| `python -m pytest tests/ -q` | **615 passed, 0 failed, 0 skipped** |
| `python scripts/content_id_audit.py audit --strict` | **PASS** (60 posts / 60 content_id / 0 missing / 0 malformed / 0 duplicates) |
| `hugo --gc --minify` | **SUCCESS** |
| Secret scan | PASS (test_no_hardcoded_secrets + test_secret_name_contract) |
| Workflow validation | PASS (test_workflow_yaml + test_workflow_names) |
| New reporting tests | 20/20 PASS (kpi engine + engine, deterministic, UTF-8, guards) |

## 10. Git scope

- Committed: scripts/ (2 engines), tests/ (2 files), reports/ (management system + master + index + this report), docs/ (AI_CONTEXT).
- Not modified: content/posts/, layouts/, affiliate URLs, UTM, Drive, GA4 schema, GSC configuration.
- Commit: `feat: unify ChinaBound 2.0 management reporting` — pushed to origin/main, no force push.

## 11. Remaining / future work (BACKLOG, not blockers)

- Fresh GSC pull to refresh daily_search_performance and the 08-16 SEO snapshot derivatives (STALE).
- Rebuild headline reports P1_GROWTH_03/04/09/11/22 from the 60-post baseline (STALE/PARTIAL).
- GROWTH-22 live verification (deployment section incomplete).
- Backup/rollback KPI remains NOT_AVAILABLE until a source artifact exists.

---

**P1-REPORT-02 = PASS**