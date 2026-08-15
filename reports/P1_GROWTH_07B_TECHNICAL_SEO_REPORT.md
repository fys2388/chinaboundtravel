# P1-GROWTH-07B — Technical SEO Finalization Report

- Date: 2026-08-16
- GitHub main baseline: `7390326`
- Final verdict: **P1-GROWTH-07B = PASS**

## 1. Rail root cause

Two compounding causes folded `/posts/china-high-speed-rail-how-to-book-tickets/`:

1. The transportation guide (`content/posts/2026-07-16-china-transportation-complete-guide-trains-subways-taxis-and-more.md`)
   declared `/posts/china-high-speed-rail-how-to-book-tickets/` in its Hugo `aliases`,
   generating a noindex + meta-refresh stub at that URL pointing to the guide.
2. The rail page itself had **no `slug`** in front matter, so Hugo rendered it at the
   dated URL `/posts/2026-05-25-china-high-speed-rail-how-to-book-tickets/`
   while `static/_redirects` 301'd the dated URL to the slug URL (which was occupied
   by the stub). Result: the canonical slug URL served a 508-byte noindex stub.

## 2. Rail fix (minimal)

- Added `slug: "china-high-speed-rail-how-to-book-tickets"` to the rail page front matter
  (renders real content at the canonical slug URL).
- Removed `/posts/china-high-speed-rail-how-to-book-tickets/` from the guide's `aliases`
  (frees the URL for the rail page; the guide still keeps its other aliases).
- Kept `static/_redirects` dated-URL rule unchanged:
  `/posts/2026-05-25-china-high-speed-rail-how-to-book-tickets/` -> final slug URL `301`.
- URL / content_id / canonical / affiliate / UTM: unchanged.

## 3. Transportation guide regression

- Guide URL still renders real content (~70KB), no `noindex`, canonical = self
  (`https://www.chinaboundtravel.com/posts/china-transportation-complete-guide-trains-subways-taxis-and-more/`).
- All other guide aliases intact (`transportation-guide-guide`, navigating-chinas-..., survival-guide, train-station).
- Locked by tests: `test_guide_renders_and_indexable`, `test_guide_canonical_unchanged`,
  `test_guide_no_longer_claims_rail_alias`.

## 4. FAQ root cause

`layouts/partials/schema_faq.html` detected FAQs with `in $content "## FAQ"`, but
`.Content` is rendered HTML — the markdown heading `## FAQ` becomes `<h2>FAQ</h2>`,
so the literal string never matched. FAQPage JSON-LD was therefore never emitted
(also true for the pre-existing zhangjiajie FAQ page).

## 5. FAQ fix

Rewrote `layouts/partials/schema_faq.html`:

- Detection: an `<h2>` heading whose text starts with `FAQ` (case-insensitive), which
  matches both `## FAQ` and `## FAQ: <subtitle>` variants.
- Extraction: consecutive `<h3>Question</h3><p>Answer</p>` pairs after that heading,
  stopping at the next `<h2>`.
- Output: single valid `FAQPage` JSON-LD with `mainEntity` (Question / acceptedAnswer / Answer);
  question text cleaned of heading anchors (`<a ...>#</a>`), entities unescaped,
  whitespace collapsed.
- No FAQ data on the page -> no FAQPage emitted. No duplicate FAQPage (partial is
  included exactly once per page).
- Product / other schema untouched.

## 6. Tests

- New `tests/test_growth07b_technical_seo.py` (13 checks):
  rail renders at slug (real content), rail indexable, rail canonical = self,
  rail slug declared, guide renders + indexable, guide canonical unchanged,
  guide no longer aliases rail URL, dated URL still 301s, FAQPage valid when FAQ exists
  (4 FAQ pages), no FAQPage when FAQ absent, no duplicate FAQPage site-wide,
  content_id unchanged, affiliate/UTM unchanged.
- Updated `tests/test_growth05_first_content_action.py` (guide alias assertion reflects
  new intended state) and `tests/test_growth07_content_differentiation.py` (scope allow-list
  + sanctioned `layouts/partials/schema_faq.html`).
- Full suite: **199 passed / 0 failed / 0 skipped**.
- `hugo --gc --minify`: exit 0.
- `content_id_audit audit --strict`: PASS (0 missing / 0 malformed / 0 duplicate).
- Internal link audit: 556 links, 0 broken / 0 redirect / 0 malformed.
- Meta audit: too_long 0, P0 duplicate 0.
- Secret scan + workflow YAML validation: PASS (20/20 in dedicated tests).

## 7. Production deployment

- Deployment: normal `git push origin main` (fast-forward) -> GitHub Actions
  `Post-deploy Tasks` auto-deploy (`layouts/**` + `content/**` trigger).
- No manual `wrangler pages deploy`; no DNS change; no secrets touched.
- Post-deploy verification will confirm the live URLs (see section 8).

## 8. GSC readiness

See `reports/seo/GROWTH07B_INDEX_RECOVERY_READINESS.md`.

- Rail page: now indexable, self-canonical, real content at the canonical slug URL.
- Recommended: manual URL Inspection + one-time "Request indexing" after deploy.
- No automated Indexing API call in this round.

## 9. Remaining issues

1. `how-to-survive-chinese-train-station` and `china-high-speed-train-survival-guide-...`
   URLs are still consumed by the guide's aliases (same folding pattern as the rail page
   had). Out of this round's scope; candidates for a follow-up technical batch.
2. FAQ content stored only in front matter `params.faq` (not rendered in body) is not
   picked up by the FAQPage extractor — by design, so we never emit schema for
   invisible content.
3. GSC re-crawl of the rail page is a manual action (no automated Indexing API).

## Files in this commit

- `content/posts/2026-05-25-china-high-speed-rail-how-to-book-tickets.md`
- `content/posts/2026-07-16-china-transportation-complete-guide-trains-subways-taxis-and-more.md`
- `layouts/partials/schema_faq.html`
- `tests/test_growth07b_technical_seo.py` (new)
- `tests/test_growth05_first_content_action.py`
- `tests/test_growth07_content_differentiation.py`
- `reports/seo/GROWTH07B_INDEX_RECOVERY_READINESS.md` (new)
- `reports/P1_GROWTH_07B_TECHNICAL_SEO_REPORT.md` (new)
