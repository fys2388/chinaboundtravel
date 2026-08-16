# P1-GROWTH-18 China Transportation Card Commercial Content Creation — Final Report

Date: 2026-08-16
Previous: P1-GROWTH-17 = PASS (commit 5e2a6a7)
Instruction source: ChatGPT「ChinaBound Travel评测」(reports/CHATGPT_INSTRUCTION_P1_GROWTH_18.md)

## 1. New Page (18A)
- content/posts/china-transportation-card-guide.md
- content_id: cbt-55aef784e6aa
- URL: https://www.chinaboundtravel.com/posts/china-transportation-card-guide/
- canonical: self | draft: false | sitemap: included
- Position: editorial travel guide (no "Best Card" / no affiliate landing page)

## 2. Search Intent (18B)
- Primary: china transportation card
- Secondary: china metro card for foreigners / china subway card tourist / how to pay subway in china / china public transportation app / beijing subway card tourist / shanghai metro card foreigner

## 3. Structure (18C)
- All required H2 sections present (Do Foreign Travelers Need a Card / Options Compared 1-3 / City Examples Beijing-Shanghai-Guangzhou-Shenzhen / How to Buy / Which Option Is Best / Recommended Travel Tools) + FAQ
- Editorial voice; no first-person claims

## 4. Commercial Layer (18D)
- Recommended Travel Tools: Trip.com (train) / Klook (attractions) / Airalo (mobile data) / Booking (hotels)
- Existing shortcodes only (affiliate-section + affiliate-link); no new partner / no new tracking / no new UTM

## 5. CTA Strategy (18E)
- No CTA experiment; REV002 remains the only active transportation CTA experiment (frozen)
- comparison layer only; affiliate_click experiment disabled on this page

## 6. Internal Linking (18F)
- Inbound links >= 5: Transportation Guide (2: subway payment + subway tips) / High-Speed Rail (2: Quick Answer + Further Reading) / Resources (1: Transportation section)

## 7. SEO Constraints (18G)
- Existing pages untouched structurally: URL / canonical / aliases / content_id unchanged
- REV002 CTA byte-identical; Drive script exactly 1; GA4 schema unchanged

## 8. Persona (18H)
- PersonaGuard PASS; forbidden phrase scan clean

## 9. Tests (18I + regression)
- New tests/test_growth18_transportation_card.py: 23 checks
- Full suite: 474 passed, 0 failed, 0 skipped
- Updated historical baseline assertions: 57 -> 58 posts; brand/drive white-lists extended for 18-authorized files; 16-round decision now KEEP (page exists)
- hugo --gc --minify: PASS | content_id_audit --strict: PASS (58/58) | secret scan: 0 | workflow YAML: 18/18

## 10. Reports (18J)
- reports/revenue/TRANSPORTATION_CARD_CONTENT_RELEASE.md
- reports/revenue/TRANSPORTATION_CLUSTER_MAP.md
- reports/revenue/COMMERCIAL_CLUSTER_PROGRESS.md

## 11. Deployment (18K)
- Git commit + push (fast-forward); GitHub Actions -> Cloudflare Pages auto-deploy (content changed)
- Post-deploy verify: page 200 / canonical self / no noindex / affiliate links present / Drive=1 / REV002 CTA=1

## 12. Final Status
P1-GROWTH-18 = PASS
NEXT = P1-GROWTH-19 Transportation Cluster Authority Expansion (Airport Transfer CREATE / Card CTA candidate / REV002 evaluation prep)
