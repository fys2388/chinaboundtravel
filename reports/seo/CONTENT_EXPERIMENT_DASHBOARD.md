# Content Experiment Dashboard

- Generated: 2026-08-16
- Source: `reports/seo/EXPERIMENT_REGISTRY.csv` + `reports/seo/EXPERIMENT_RESULTS.md`
- LOW_SAMPLE_WARNING active (28d clicks = 3 site-wide); no success/failure claims on tiny samples.

## By Status

### RUNNING

| experiment | content | start | days | baseline CTR | current CTR | delta | status |
|---|---|---|---|---|---|---|---|
| GROWTH05-CTR-001 | cbt-b4ff4381a014 (144-Hour Visa) | 2026-08-16 | 0 | 0.00% | 0.00% | n/a | RUNNING / INSUFFICIENT_SAMPLE |

### POSITIVE

None yet (no experiment has 28 days of post-change data).

### NEUTRAL

None yet.

### NEGATIVE

None yet.

### INSUFFICIENT_SAMPLE

| experiment | content | start | days | baseline CTR | current CTR | delta | status |
|---|---|---|---|---|---|---|---|
| GROWTH05-CTR-001 | cbt-b4ff4381a014 | 2026-08-16 | 0 | 0.00% | 0.00% | n/a | INSUFFICIENT_SAMPLE |

## Rules

- POSITIVE: CTR delta >= +20% with impressions delta >= -10%.
- NEUTRAL: CTR delta within +/-20%.
- NEGATIVE: CTR delta <= -20%.
- INSUFFICIENT_SAMPLE: clicks < 20 or observation < 28 days.

## How to refresh

```
python scripts/seo_experiment_measurement.py --all
python scripts/seo_experiment_measurement.py --experiment-id GROWTH05-CTR-001 --fetch-live
```

No cron is required this round; refresh manually each week.
