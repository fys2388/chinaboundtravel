# ChinaBound Travel 2.0 — Reporting Status Model

- Generated: 2026-08-17
- Source: unified reporting system (scripts/reporting_kpi_engine.py + scripts/reporting_engine.py)
- Scope: statuses and labels used by ALL management reports. One definition set — no per-report variants.

## 1. Data source labels

Every KPI in REPORTING_SNAPSHOT.json carries exactly one of these labels.

| Label | Meaning | Example |
|---|---|---|
| LIVE | Read directly from a live API at snapshot time | GA4 API pull executed during generation |
| CACHED | Persisted artifact from a previous live read; fetch date recorded | REVENUE_DASHBOARD.md (GA4_API 2026-08-17), SEO_BASELINE_2026-08.md (GSC API 2026-08-15) |
| LOCAL | Computed locally from repository files / deterministic rules | brand_identity_audit --legacy (LOCAL rule engine), content_id_audit |
| NOT_AVAILABLE | No trustworthy source exists; value MUST be NULL | revenue (no affiliate revenue API), users, engagement, backup/rollback |

Rules:
- NEVER promote a CACHED value to LIVE.
- NEVER fabricate a value to fill NOT_AVAILABLE.
- Every CACHED record must state its original fetch date in `source`.

## 2. Revenue rule

- Revenue and all revenue-derived KPIs (orders, commission, RPM, revenue per 1000 sessions) are **NULL / REVENUE_NOT_AVAILABLE** until a real revenue API provides data.
- No revenue number is ever estimated, projected, or backfilled.

## 3. Task state model

Used by REPORT_INDEX.md and action lists. Completed items MUST NOT reappear in future action lists.

| State | Meaning | Reappears in actions? |
|---|---|---|
| BACKLOG | Not started, no owner | yes |
| READY | Next in line, unblocked | yes |
| RUNNING | In progress | yes (until terminal) |
| WAITING | Blocked by external state (recrawl, API, gate) | yes (with reason) |
| PASS | Completed successfully | no |
| PARTIAL | Completed with known gaps | no (list gap as new BACKLOG item) |
| BLOCKED | Cannot proceed | yes (with blocker) |
| CANCELLED | Deliberately dropped | no |

## 4. Experiment / sample model

| Status | Condition |
|---|---|
| RUNNING | In observation window, untouched |
| PENDING | Not yet started (waits on gate) |
| WAITING_RECRAWL | Index recovery requested; waiting for Google recrawl |
| INSUFFICIENT_SAMPLE | observation < 28 days OR clicks < 20 (sample_status) |
| SUFFICIENT | observation >= 28d AND clicks >= 20 |
| POSITIVE / NEGATIVE / NEUTRAL | only after SUFFICIENT; delta >= +20% / <= -20% / else |
| LOSE / FAILED | only on sufficient evidence |

Guards:
- Minimum observation: 28 days.
- Minimum clicks: 20.
- Never declare WIN/LOSE from insufficient data.
- REV001/REV002 CTA copy, placement and partners are frozen until the 2026-09-13 review gate.

## 5. Alert model

| Level | Meaning |
|---|---|
| GREEN | no action needed |
| YELLOW | attention: low data, open queues, canonical conflicts, legacy persona, WAITING_RECRAWL |
| ORANGE | escalate within the week: experiment failure / brand regression |
| RED | act immediately: production outage / revenue anomaly / secret-security issue |

Alerts are derived deterministically from the snapshot (see scripts/reporting_engine.py derive_alerts). Nothing is invented.

## 6. Period comparison model

| Report | Comparison | Rule |
|---|---|---|
| Daily | DoD | vs closest prior dated snapshot |
| Weekly | WoW | vs closest prior dated snapshot |
| Monthly | MoM | vs closest prior dated snapshot |
| Quarterly | QoQ / YoY | vs closest prior dated snapshot |
| Yearly | YoY | vs closest prior dated snapshot |

- Snapshots are archived at reports/management/snapshots/REPORTING_SNAPSHOT_<date>.json.
- If no prior snapshot exists, every comparison row = **INSUFFICIENT_SAMPLE** (first run).
- Deltas are computed only from real snapshot values.

## 7. Consistency contract

Daily / weekly / monthly / quarterly / yearly MUST share:
- the same KPI definitions (this file + REPORTING_KPI_DEFINITIONS.md)
- the same experiment IDs
- the same content count
- the same brand status
- the same revenue definitions
- the same data source labels

Contradictions between period reports are treated as a defect in the reporting system and must be fixed in the snapshot, not in individual reports.