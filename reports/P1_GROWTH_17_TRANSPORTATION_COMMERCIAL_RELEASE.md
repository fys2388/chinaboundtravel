# P1-GROWTH-17 Transportation Commercial Content Release — Final Report

Date: 2026-08-16
Previous: P1-GROWTH-16 = PASS (commit 8234954)
Current main: 8234954 → (this round)

## 1. Objective
Close the first commercial cluster loop (Transportation) via a low-risk content release:
- 17A: Authority-page persona migration + commercial trust layer
- 17B: REV003 CTA copy variant registration (PENDING, REV002 freeze respected)
- 17C: Deterministic release decision (CREATE_ONE / HOLD) — no new page this round

## 2. Scope Guard
- Modified exactly 1 published post: China Transportation Guide
  (content_id cbt-17c6738ffb32, URL unchanged)
- No changes to REV001 / REV002 / DRIVE-001 (all remain RUNNING)
- No canonical / URL / content_id / affiliate URL / UTM changes
- No bulk content edits, no new affiliate partner

## 3. 17A — Transportation Guide Upgrade
- Removed 9 legacy persona claims (e.g. "I remember my first attempt", "I have ridden all three classes", "I used Trip.com exclusively", "Five years later, I book") → editorial / research-based wording
- Added "Recommended Booking Options for Foreign Travelers" comparison layer:
  - A. Trip.com (English UI / international payment)
  - B. 12306 (official app)
  - C. Klook (packages)
- SEO invariants verified: content_id / slug / date / aliases / title unchanged
- REV002 mid-cta (placement=transportation-train-tickets-mid) untouched byte-for-byte

## 4. 17B — REV003 Registration
- reports/revenue/REV003_EXPERIMENT_REGISTRY.csv
- experiment_id=REV003, type=CTA_COPY, status=PENDING, decision=PENDING
- primary=affiliate_click_rate; secondary=affiliate_outbound_rate;affiliate_clicks_per_1000_sessions
- Variant A "Book China Train Tickets Online" / Variant B "Compare China Train Tickets & Routes" defined, NOT deployed
- REV003 waits for REV002 review gate (>= 2026-09-13) — no copy change before that

## 5. 17C — Release Decision
- China Transportation Card (Klook, 2 existing pages, 11 impressions, score 55) → CREATE_ONE (executes P1-GROWTH-18)
- China Airport Transfer (Booking/Klook, 0 impressions, score 40) → HOLD
- Deterministic scoring only; no LLM judgment

## 6. Tests & Regressions
- python -m pytest tests/ -q → 451 passed, 0 failed, 0 skipped
- hugo --gc --minify → PASS (Total 14.1s)
- python scripts/content_id_audit.py audit --strict → PASS (57/57, 0 missing, 0 duplicate)
- secret scan (all staged files) → CLEAN
- workflow YAML validation → 18/18 OK
- internal link / affiliate regression covered by test suite

## 7. Git
- commit: feat: release transportation commercial content
- push origin main (fast-forward; no force)

## 8. Production & Observation
- Await GitHub Actions → Cloudflare Pages auto-deploy (no manual deploy)
- Post-deploy verify: page 200, REV002 CTA=1, Drive script=1, persona phrases removed
- Observation: REV002 review gate 2026-09-13; REV003 PENDING; CREATE_ONE content in P1-GROWTH-18

## 9. Final Status
P1-GROWTH-17 = PASS
NEXT = P1-GROWTH-18 (per ChatGPT instruction round)
