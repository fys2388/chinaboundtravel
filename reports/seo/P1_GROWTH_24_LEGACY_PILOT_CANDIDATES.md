# P1-GROWTH-24 — Legacy Persona Pilot Candidates

- Generated: 2026-08-17
- Data sources: reports/seo/P1_GROWTH_24_CONTENT_RECOVERY_QUEUE.csv (CACHED GSC 28d, fetch 2026-08-16) + reports/P1_BRAND_02_LEGACY_PERSONA_REVIEW.md (LOCAL, 2026-08-17)
- Rule applied: at most 3 candidates selected from the TOP5 queue; no content changed this round.

## Summary

Only 1 of the 5 TOP5 pages carries legacy-persona hits:

| content_id | URL | legacy hits | matched phrases | impressions 28d | clicks 28d | avg position | commercial intent | persona severity | verdict |
|---|---|---|---|---|---|---|---|---|---|
| cbt-d7747b73c978 | /posts/xian-terracotta-army-history-discovery-and-insider-tips/ | 2 | "American expat"; "I remember my first trip" | 1 | 0 | 5.0 | TRANSPORT (cluster) | LOW-MEDIUM | PERSONA_MIGRATION candidate (pilot, next round) |

The other 4 TOP5 pages (cbt-244822dc113b, cbt-707a8899c0a7, cbt-80ac63165adb, cbt-bfeaa5ca9007) are persona-compliant (legacy hits = 0) and do not require migration.

## Candidate evaluation

### 1. Xi'an Terracotta Army (cbt-d7747b73c978)

- Traffic: 1 impression / 0 clicks in 28d — LOW_DATA_WARNING; sample far too small to use traffic as a migration driver.
- Commercial value: MEDIUM — TRANSPORT-cluster mapping; destination guide with tickets/transport insider tips; no affiliate CTA found in the audited section.
- Persona severity: LOW-MEDIUM — both phrases are Joran-adjacent voice markers ("American expat", "I remember my first trip") rather than identity-breaking claims; page already authored as Joran with audit_status pass4.
- Recommendation: include Xi'an in the next approved legacy pilot (2-3 pages per batch, 28-day observation), but do NOT prioritize it by traffic. Its migration value is compliance-only.

## Why no other TOP5 page qualifies

Pages with higher legacy hits (e.g., travel-safety-guide = 3, food-recommendations-guide = 2, a-gastronomic-adventure... = 4) sit outside the TOP5 because they are tied to HIGH canonical conflicts, the frozen Food/Transportation experiment clusters, or duplicate-content consolidation — they must be handled by a dedicated legacy + canonical consolidation task, not this round.

## Next pilot suggestion (pending approval)

1. Xi'an Terracotta Army (cbt-d7747b73c978) — compliance migration, low risk.
2. Pick 2 additional pages from the P2 legacy segment of the recovery queue with the best traffic/severity evidence at the time of the pilot (recompute from a fresh GSC pull; do not use this 1-impression sample as justification).

No content modified this round.
