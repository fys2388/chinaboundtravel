# P1-GROWTH-03 Content Opportunity Engine — Report

- Date: 2026-08-16
- Workdir: `E:\AI\dulizhan\travel-blog`
- GitHub main baseline: `2e167b3`
- GSC property: https://www.chinaboundtravel.com/

## 1. Scoring model

Transparent, explainable rules (no LLM, no network calls).

| component | max | rule |
|---|---|---|
| INDEXING SCORE | /20 | 20 = INDEXED, 10 = unknown, 0 = not indexed |
| SEARCH DEMAND SCORE | /25 | impressions tiers: 0 / 1-49 / 50-99 / 100-499 / 500+ |
| PERFORMANCE SCORE | /20 | position + CTR + clicks; rewards position 4-20 |
| BUSINESS INTENT SCORE | /20 | VISA/PAYMENT/INTERNET/CITY/TRANSPORT/TRAVEL_GUIDE x HIGH/MEDIUM/LOW |
| CONTENT GAP SCORE | /15 | multi-query -> same page; high demand but weak page |
| **total** | **/100** | Tier A 80-100 / B 60-79 / C 40-59 / D <40 |

Implementation: `scripts/content_opportunity_engine.py` (deterministic; two runs produce byte-identical CSV/JSON).

## 2. Tier A

- No article reached the 80+ threshold in this data window (top score = 77).
- `reports/seo/TIER_A_CONTENT_OPPORTUNITIES.md` lists the top 20 pipeline articles (highest opportunity_score first).
- Top candidates: 144-hour visa-free guide (77), transportation guide (75), food delivery guide (67), 144-hour policy update (67), WeChat Pay (65).

## 3. Tier B

- Tier B (60-79): **8 rows** in `content_opportunity_scores.csv`, **6 primary articles** listed in `reports/seo/TIER_B_CONTENT_OPPORTUNITIES.md`.
- Top B articles: 144-hour visa-free transit guide (77), transportation guide (75), food delivery (67), 144-hour 15-country update (67), WeChat Pay (65), Xi'an Terracotta Army (60).

## 4. Index Recovery

- `reports/seo/INDEX_RECOVERY_QUEUE.md` lists **10 not-indexed articles**.
- Inspection status comes from GSC URL Inspection API coverage state; non-API reasons are marked INFERENCE (none masked as official GSC reasons).
- Real coverage states observed: noindex, redirect, alternate canonical, URL unknown to Google.

## 5. Canonical Conflict

- `reports/seo/CANONICAL_CONFLICT_QUEUE.md`: **6 candidates**, all severity HIGH -> TECHNICAL_REVIEW.
- Detected via `google_canonical != user_canonical`. No changes made.

## 6. Topic Clusters

- `reports/seo/TOPIC_CLUSTER_GAPS.md` covers VISA / PAYMENT / INTERNET / TRANSPORT / CITY / TRAVEL_GUIDE / OTHER.
- Strong: TRAVEL_GUIDE (377 article impressions), TRANSPORT (322), VISA (194).
- Weak with demand: VISA (22 queries, avg position far from page 1), TRANSPORT (26 queries, high-speed-rail ranks 26-35).
- INTERNET: 9 queries / 14 impressions but only 1 article with 0 article impressions -> cluster gap.

## 7. New Content

- `reports/seo/NEW_CONTENT_IDEAS.md`: **14 evidence-backed ideas** (GSC query evidence / multi-query / high-impression gap).
- All entries include topic, target_query, evidence, recommended_format, priority, business_intent. No article created.

## 8. Commercial Opportunities

- `reports/seo/COMMERCIAL_CONTENT_OPPORTUNITIES.md`: **16 entries** sorted by business_intent + impressions + position.
- Focus: visa, transport, payment (WeChat Pay), hotels/flights-adjacent demand. No affiliate inserted.

## 9. Content Update Roadmap

- `reports/seo/CONTENT_UPDATE_ROADMAP.md`: **NOW 10 / NEXT 15 / LATER 23** (48 primary rows; duplicates grouped per canonical URL).
- Each row includes why / what / expected_goal / risk.

## 10. LOW_DATA_WARNING

- 28d: impressions = 1168, clicks = **3**, CTR = 0.26%, avg position = 34.6.
- CTR and position results are unstable at this sample size; decisions prioritize impressions + position + multi-query signals; no extreme single-query decisions.
- All reports carry the LOW_DATA_WARNING banner.

## 11. Feed JSON

- `reports/seo/CONTENT_OPPORTUNITY_FEED.json`: **48 items**, stable parseable schema:
  `content_id, url, opportunity_score, tier, action, evidence, queries, business_intent, index_status`.
- Validated by `test_feed_schema_stable_and_parseable`.

## 12. Tests

- `tests/test_content_opportunity_engine.py`: 13 tests (score bounds, tier boundaries, indexing score, business intent, low CTR, near page 1, not indexed, high impression zero click, demand tiers, deterministic output, feed schema, no-LLM dependency, Tier A report non-empty regression).
- Full suite: **142 passed, 0 failed, 0 skipped** (`python -m pytest tests/ -q`).
- `hugo --gc --minify`: exit 0; `public/robots.txt` + `public/sitemap.xml` present.
- `content_id_audit --strict`: PASS (57 posts, 0 missing, 0 malformed).
- Workflow YAML validation: 18/18 valid.
- Secret scan: HEAD tracked blobs + this round's files = **0 hits**.

## 13. Git commit

- commit message: `feat: add content opportunity engine`
- Scope: engine + tests + reports only (no article/front-matter/URL/canonical/affiliate changes).
- Pushed as a normal fast-forward (no force).

## 14. Production status

- No Cloudflare deploy, no Buffer deploy, no Stripe/Resend change, no GSC indexing request, no sitemap/robots modification.
- Production code unchanged; this round is analysis + tooling only.

---

## Final status

**P1-GROWTH-03 = PASS**

Next: **P1-GROWTH-04 CONTENT PRIORITIZATION**
