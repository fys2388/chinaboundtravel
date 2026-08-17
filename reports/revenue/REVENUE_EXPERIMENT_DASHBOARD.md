# REVENUE EXPERIMENT DASHBOARD

- Generated: 2026-08-17
- Data source: CACHED (registry + baseline artifacts) + GA4_API (live read via revenue_measurement 2026-08-17) + GSC cached snapshots (2026-08-16)
- Revenue API: REVENUE_NOT_AVAILABLE (no affiliate revenue API; nothing fabricated)

## Status groups

### RUNNING (in observation window)
| Experiment | Page / scope | content_id | Start | Days | Status |
|---|---|---|---|---|---|
| REV001 | Food Delivery (Meituan & Ele.me) | cbt-e464169c4991 | 2026-08-16 | 1 | RUNNING / INSUFFICIENT_SAMPLE |
| REV002 | Transportation Guide (Trip.com mid-CTA) | cbt-17c6738ffb32 | 2026-08-16 | 1 | RUNNING / INSUFFICIENT_SAMPLE (frozen) |
| DRIVE-001 | Site-wide Travelpayouts Drive | - | 2026-08-16 | 1 | RUNNING / INSUFFICIENT_SAMPLE |

### PENDING
| Experiment | Type | Note |
|---|---|---|
| REV003 | CTA_COPY variant (Transportation Guide) | Waits for REV002 review gate >= 2026-09-13 |

### OBSERVATION (SEO / index)
| Experiment | Page | Status |
|---|---|---|
| GROWTH05-CTR-001 | 144-Hour Visa (cbt-b4ff4381a014) | RUNNING / INSUFFICIENT_SAMPLE |
| GROWTH07C-INDEX-001 | WeChat Pay weak (cbt-255af4ed003a) | WAITING_RECRAWL (requested 2026-08-16) |
| GROWTH07B-TECH-001 | High-Speed Rail (cbt-cc4549872c92) | WAITING_RECRAWL (fix live; old noindex snapshot) |

### NOT_STARTED
| Experiment | Candidate |
|---|---|
| REV004 | Transportation Card CTA (cbt-55aef784e6aa) - WAIT |
| Payment -> eSIM | C1 Alipay / C2 WeChat weak / C3 Card - all WAIT |

## Metrics (current known)

| Experiment | affiliate_clicks | clicks_per_1000 | sessions | pageviews | revenue |
|---|---|---|---|---|---|
| REV001 | 0 | 0.0 | 166* | 374* | NULL |
| REV002 | 0 | 0.0 | 166* | 374* | NULL |
| DRIVE-001 | 0 | 0.0 | 166* | 374* | NULL |

* 28d sitewide (GA4 API, fetched 2026-08-17); page-level GA4 not available - DATA_SCOPE=sitewide.

## Sample warnings

- All experiments: observation < 28 days and affiliate_clicks < 20 -> INSUFFICIENT_SAMPLE; no WIN/LOSE declarations.
- Sitewide 28d GSC clicks very low (~3); any short-term movement is not actionable.
- Do not modify REV001 / REV002 CTA copy, placement or partner before 2026-09-13.
