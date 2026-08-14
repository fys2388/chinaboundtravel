# V6-3 Broken Link Review

Scope: real internal 404s and malformed markdown links in **published** content
(`content/**/*.md` + `layouts/` + `assets/`), normalized per the V6-3 batch.

Tooling: `scripts/audit_internal_links.py --audit`
(report: `docs/internal_link_audit.json`).

## Summary

| Metric | Before | After |
| --- | --- | --- |
| Internal links audited (published) | 558 | 558 |
| Explicit broken targets (404) | 14 | 0 |
| Relative links missing leading `/` (404 on rendered site) | 115 | 0 |
| Links pointing to 301 sources | 23 | 0 |
| Malformed link instances | 11 | 0 |

## Fixed (high confidence, direct replacement)

- 62 relative `posts/...` / `img/...` links -> root-relative `/posts/...`, `/img/...`.
- 5 merged/nested-bracket links (Zhangjiajie 197/266, Yunnan 228, Alipay 150,
  China-extends 152) -> single canonical link.
- 7 double-bracket nested links (`[[text](url)...](url)`) -> single link.
- 6 `[Internal Link N: ...]` placeholder lines (bargaining guide) -> bullet list.
- 1 space-in-URL link (accommodation guide -> visa guide) -> clean URL.
- 2 wrong-slug links on `/resources/`:
  - `/posts/how-to-use-wechat-pay-foreigner/` -> `/posts/how-to-use-wechat-pay-as-a-foreigner/`
  - `/posts/china-high-speed-rail-booking/` -> `/posts/china-high-speed-rail-how-to-book-tickets/`
- 2 `hero-chengdu.jpg` references (homepage hero CSS + insurance post cover)
  -> existing `/img/china-dest/chengdu/chengdu-hotpot-street.jpg`.

## Redirected / normalized (301 source -> final 200 URL)

- 51 relative date-prefixed links + 23 absolute date-prefixed links
  (74 total) rewritten to canonical final URLs using the existing
  `static/_redirects` mapping. The redirects themselves are preserved.
- 1 new redirect added:
  `/images/hero-chengdu.jpg /img/china-dest/chengdu/chengdu-hotpot-street.jpg 301`.
- `/cities/sichuan/` had 0 references in the repo (no action needed).

## Manual review

- `content/posts/china-extends-144-hour-visa-free-transit-policy-to-more-countries.md:143`
  - mangled prose with a triple-nested link ("can co[144-hour transit](...)out the
    hassle...t](/posts/...)"); rewriting requires inventing copy, so it was left
    untouched for human review.
- `content/_draft/*` (3 links) - unpublished drafts; not part of the live site.
- Legacy date-prefixed pages emit theme-generated `og:url`/`alternate`
  self-links; `rel=canonical` already points to the canonical URL (unchanged).
- No article URLs, slugs, canonical URLs, affiliate URLs, or UTM parameters
  were modified.
