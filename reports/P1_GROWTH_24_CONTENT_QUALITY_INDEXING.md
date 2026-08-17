# P1-GROWTH-24 — Content Quality & Indexing Recovery

- Generated: 2026-08-17 | Repo: E:\AI\dulizhan\travel-blog | HEAD: a60a3ba (P1-REPORT-02)
- Data labels: GSC 28d = CACHED (raw_pages_28d.csv, fetch 2026-08-16); URL inspection = CACHED (url_inspection_results.json, 2026-08-16 snapshot); brand = LOCAL
- Final status: **PASS**

## 1. Content Recovery Queue

Created: reports/seo/P1_GROWTH_24_CONTENT_RECOVERY_QUEUE.csv (60 rows = 60 published posts)

- Priority distribution: P0 = 2 (technical indexing/canonical), P1 = 18 (high-value content), P2 = 24 (legacy persona), P3 = 16 (low-value)
- Ranking inputs: 28d impressions; average position (30-distance weighting); commercial intent (VISA / TRANSPORT / PAYMENT / FOOD / INTERNET +15); legacy persona hits (+4 each); duplicate count (-8 each); HIGH canonical conflict (+12); frozen experiment pages (-25 execution risk, HIGH)
- Frozen pages excluded from TOP5: REV001 Food Delivery, REV002 Transportation cluster, GROWTH-05 144h guide, GROWTH07C WeChat weak, GROWTH07B High-Speed Rail
- No data invented: all numbers copied from existing GSC/inspection artifacts.

## 2. TOP 5 Queue (highest-value existing pages)

| # | content_id | URL | title | index status | canonical status | impressions 28d | clicks 28d | avg position | persona risk | commercial intent | recommended action |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | cbt-244822dc113b | /posts/china-extends-144-hour-visa-free-transit-policy-to-more-countries/ | China's 144-Hour Visa-Free Transit: 15 New Countries | INDEXED | OK (self) | 87 | 0 | 41.87 | none (0 hits) | VISA | CONTENT_UPDATE (front-matter repair executed; full update deferred) |
| 2 | cbt-707a8899c0a7 | /posts/how-to-use-wechat-pay-as-a-foreigner/ | Can Foreigners Use WeChat Pay in China? (2026 Guide) | INDEXED | OK (self) | 83 | 0 | 62.45 | none (0 hits) | PAYMENT | CONTENT_UPDATE (deferred - WeChat cluster under observation) |
| 3 | cbt-80ac63165adb | /posts/chinabound-travel-guide-2026-08-monthly-update/ | China Travel Guide: August 2026 Update | INDEXED | OK (self) | 52 | 0 | 11.40 | none (0 hits) | TRAVEL_GUIDE | CONTENT_UPDATE (deferred - title/H1 CTR alignment) |
| 4 | cbt-bfeaa5ca9007 | /posts/china-photography-guide-capturing-the-wonders-of-the-middle-kingdom/ | China Photography Guide: Best Spots & Tips | INDEXED | OK (self) | 51 | 0 | 20.88 | none (0 hits) | TRAVEL_GUIDE | CONTENT_UPDATE (deferred - CTR/affiliate) |
| 5 | cbt-d7747b73c978 | /posts/xian-terracotta-army-history-discovery-and-insider-tips/ | Xi'an Terracotta Army: Tickets, Tips & History | INDEXED | OK (self) | 1 | 0 | 5.00 | 2 legacy hits | TRANSPORT (cluster) | PERSONA_MIGRATION (pilot candidate - not executed) |

Note: Xi'an ranks by recovery score but carries a 1-impression sample (LOW_DATA_WARNING); Yunnan (cbt-23c31fe5b281, 40 impressions, score 54.0) is the alternate if Xi'an is deprioritized by sample size.

## 3. Six HIGH Canonical Conflicts - Root Cause Analysis

No automatic fix was executed. Root causes and safe-to-fix verdicts:

| URL | user canonical (declared) | Google canonical | index state | last crawl | root cause | safe to fix now? |
|---|---|---|---|---|---|---|
| /posts/a-gastronomic-adventure-in-china-food-recommendations-for-international-travelers/ | /posts/food-recommendations-guide/ | itself (www) | INDEXED | 2026-08-13 | food-cluster duplicate; Google keeps the non-declared URL as canonical | NO - requires content-layer consolidation (food cluster) - DEFERRED |
| /posts/chinabound-travel-guide-2026-07-monthly-update/ | bare domain (no www) | itself (www) | INDEXED | 2026-07-23 | canonicalURL uses bare domain while site serves www; Google resolves the redirect chain to www | NO - fix_canonical_urls.py exists but is a bulk content rewrite outside allowed scope - DEFERRED |
| /posts/navigating-china-with-confidence-a-californians-guide-to-travel-safety/ | bare domain self | /posts/is-china-safe-for-tourists-2026-honest-safety-assessment/ | NOT_INDEXED (Alternate) | 2026-07-10 | duplicate of is-china-safe with self-canonical; Google dedupes to is-china-safe (acceptable outcome) | NO - content change required - DEFERRED |
| /posts/transportation-guide-guide/ | www complete-guide | bare domain self | NOT_INDEXED (redirect), NOT_IN_SITEMAP | 2026-08-14 | redirect/alias URL, not a real page; _redirects 301 -> /posts/transportation-guide/ | NO ACTION - benign; URL unchanged |
| /posts/transportation-guide/ | www complete-guide | itself (www) | INDEXED | 2026-08-14 | near-duplicate post canonicalizing to the complete guide; Google keeps the short URL; competes with REV002 page | NO - REV002 FROZEN + consolidation needed - DEFERRED |
| /posts/travel-safety-guide/ | www is-china-safe | itself (www) | INDEXED | 2026-08-10 | duplicate of is-china-safe; Google keeps the short URL | NO - consolidation needed - DEFERRED |

Verdicts: all URLs must remain unchanged; the deterministic tool (scripts/fix_canonical_urls.py) rewrites every content file's canonicalURL and therefore exceeds this task's scope (TOP5 only, preserve canonical, frozen experiments). Canonical cleanup belongs in a dedicated, approved task.

## 4. WAITING_RECRAWL Status

| page | content_id | inspection snapshot | classification | action |
|---|---|---|---|---|
| WeChat Pay (weak) - /posts/wechat-pay-for-foreigners-step-by-step-setup-and-common-mistakes-to-avoid-guide/ | cbt-255af4ed003a | "Alternate page with proper canonical tag"; last crawl 2026-07-28 (pre-differentiation); indexing requested 2026-08-16 | **WAITING_RECRAWL** | No re-request; no content change; observe 14-28 days |
| High-Speed Rail - /posts/china-high-speed-rail-how-to-book-tickets/ | cbt-cc4549872c92 | "Excluded by noindex" from crawl 2026-08-06 (pre-fix); GROWTH07B fix live 2026-08-16 | **WAITING_RECRAWL** (stale crawl; fix confirmed in current build) | No content change; no re-request |

High-Speed Rail verification this round (hugo --gc --minify): slug URL builds a real ~67KB article, `noindex` absent, canonical = self. The noindex inspection result is simply stale Google crawl data.

## 5. Legacy Persona Pilot Candidates

Only 1 of the TOP5 qualifies: Xi'an Terracotta Army (cbt-d7747b73c978, 2 hits: "American expat", "I remember my first trip"). Details: reports/seo/P1_GROWTH_24_LEGACY_PILOT_CANDIDATES.md. No persona migration executed; needs explicit pilot approval.

## 6. Content Quality Audit - TOP 5

| page | title | meta description | H1/H2 | freshness | duplicates | internal links | affiliate | persona |
|---|---|---|---|---|---|---|---|---|
| 144-Hour 15 countries (cbt-244822dc113b) | OK (title clear, keyword-rich) | OK, 127 chars, unique | H1 consistent; body H1 embeds a markdown link (site pattern) | partial - body opens "announced today" (dated 2026-06-02) | 1 (with complete 144h guide; different intent, reciprocal link present) | valid links to /posts/144-hour-visa-free-transit-guide/ | esim + tour CTAs present | Joran, clean |
| WeChat Pay foreigner (cbt-707a8899c0a7) | OK | OK, unique | H1 = title | strong (2026 markers) | 1 (cluster pages, reciprocal links) | valid (weak guide + Alipay guide) | booking CTA present | Joran, clean |
| August 2026 update (cbt-80ac63165adb) | OK | OK, unique | H1 wording differs from title (ChinaBound 2026.08 vs China Travel Guide: August) | strong (2026.08, current month) | 1 | valid (144h guide etc.) | PDF product promo | Joran, clean |
| Photography (cbt-bfeaa5ca9007) | OK | OK, unique | H1 = title | strong (lastmod 2026-08-01) | 1 | valid | none found in audited section (gear guide - opportunity) | Joran, clean |
| Xi'an (cbt-d7747b73c978) | OK | OK, unique | H1 omits "Tickets" from title (history-focused) | ok (2026 ticket prices claimed) | 1 | valid (Sichuan hotpot link) | none found (tickets/transport - opportunity) | 2 legacy phrases |

No word-count optimization performed. All audit findings below are actionable only with approval.

## 7. Fixes Executed

1. content/posts/china-extends-144-hour-visa-free-transit-policy-to-more-countries.md - repaired corrupted front matter: the `categories` entry contained an injected markdown link plus a broken summary fragment (`China Essent[144-hour visa](/posts/144-hour-visa-free-transit-guide/) 'Breaking news: ...'`). Restored to `- China Essentials` (matching the 144-hour guide cluster). Deterministic, low-risk, fully evidenced, within TOP5. URL / slug / canonicalURL / content_id / affiliate shortcodes untouched (verified by git diff).
2. tests/ x5 - extended the authorized-file whitelists of the scope-guard tests to record the P1-GROWTH-24 authorized content change (repo convention: tests/test_brand_identity_p2.py, test_brand_legacy_pilot.py, test_growth07_content_differentiation.py, test_growth21_payment_cluster.py, test_travelpayouts_drive.py). No test logic weakened.

## 8. Fixes Deferred (Report Only)

- All 6 HIGH canonical conflicts - require approved canonical consolidation task (bulk tool exists but is out of scope; REV002 frozen).
- WeChat Pay foreigner page (position 62.45) - cluster under GROWTH07C observation; do not edit before review gate.
- August update title/H1 alignment + CTR improvement (0 clicks / 52 impressions) - needs approved copy change.
- Photography guide CTR + affiliate gap (no CTA in audited section) - needs approved copy change.
- 144-Hour 15 countries body freshness wording ("announced today") - editorial change, needs approval.
- Xi'an legacy persona migration - pilot approval required.
- Pre-existing non-TOP5 meta descriptions too long: china-airport-transfer-guide.md (178 chars), china-transportation-card-guide.md (169 chars) - outside TOP5 scope this round.

## 9. Regression Results

| check | result |
|---|---|
| python -m pytest tests/ -q | 615 passed, 0 failed, 0 skipped |
| python scripts/content_id_audit.py audit --strict | PASS - 60 posts / 60 content_id / 0 missing / 0 duplicates |
| hugo --gc --minify | SUCCESS (no errors; verified built 144-15 page + High-Speed Rail page) |
| meta audit (scripts/audit_meta_descriptions.py --audit) | PASS - duplicates 0; 2 pre-existing too_long (non-TOP5) |
| internal link audit (scripts/audit_internal_links.py --audit) | PASS - 589 links, 404 = 0, 301 = 0, malformed = 0 (docs/internal_link_audit.json) |
| redirect chains (scripts/check_redirect_chains.py) | PASS - chains 0 / loops 0 / final-not-200 0 |
| affiliate regression | PASS - Klook expiry OK (341 days); funnel inventory regenerated (278 -> 279 CTA rows, +1 new row detected); pytest affiliate tests green |
| secret scan | PASS (covered by pytest test_no_hardcoded_secrets.py + test_secret_name_contract.py) |
| workflow validation | PASS (pytest test_workflow_names.py + test_workflow_yaml.py) |

## 10. Next Recommended Actions

1. Dedicated canonical consolidation task: run scripts/fix_canonical_urls.py under explicit approval (or per-file fixes), then re-inspect the 6 HIGH conflicts and request recrawl.
2. Re-pull GSC data (label fetch date) and re-run the recovery queue after 28 days; do not act on 1-impression samples.
3. WeChat Pay / High-Speed Rail: wait for recrawl (no re-request); verify coverage at the end of the observation window.
4. Approve a 2-3 page legacy pilot (Xi'an + 2 highest-evidence P2 pages from the queue).
5. Approve CTR copy changes for August update and Photography guide (title/H1/meta) in a later content round.

Artifacts created this round:
- reports/seo/P1_GROWTH_24_CONTENT_RECOVERY_QUEUE.csv
- reports/seo/P1_GROWTH_24_LEGACY_PILOT_CANDIDATES.md
- reports/P1_GROWTH_24_CONTENT_QUALITY_INDEXING.md
- docs/internal_link_audit.json (internal link audit evidence)
