# P1-GROWTH-07B — Index Recovery Readiness

- Date: 2026-08-16
- Page: `/posts/china-high-speed-rail-how-to-book-tickets/`
- content_id: `cbt-cc4549872c92`

## Current state (before this round)

- URL was folded by the transportation guide's Hugo `aliases` entry
  (`/posts/china-high-speed-rail-how-to-book-tickets/` inside the guide's aliases list)
- The page also lacked a `slug`, so Hugo rendered it at the dated URL
  `/posts/2026-05-25-china-high-speed-rail-how-to-book-tickets/`, while
  `static/_redirects` 301'd the dated URL to the slug URL
- The slug URL therefore served the guide's alias refresh stub:
  `noindex` + meta refresh -> transportation guide (508-byte page)
- GSC status for the dated URL: "Excluded by 'noindex' tag"

## New state (after this round)

- Rail page now renders real content at the canonical slug URL:
  `https://www.chinaboundtravel.com/posts/china-high-speed-rail-how-to-book-tickets/`
- `slug: "china-high-speed-rail-how-to-book-tickets"` added to front matter
- Guide's aliases no longer contain the rail URL; guide unchanged otherwise
  (still 200, self-canonical, indexable)
- Dated URL `/posts/2026-05-25-china-high-speed-rail-how-to-book-tickets/`
  continues to 301 -> final rail page (kept in `static/_redirects`)
- Built output: ~63KB real article, `noindex` absent, canonical = self,
  FAQPage JSON-LD present (4 Q&A)

## Recommended GSC inspection (manual, no Indexing API)

1. URL Inspection for `https://www.chinaboundtravel.com/posts/china-high-speed-rail-how-to-book-tickets/`
   after this deployment is live: expect "URL is on Google" / "URL can be indexed"
2. If it shows "Page is not indexed (Discovered - currently not indexed)" or
   "Crawled - currently not indexed", click **Request indexing** once
   (manual action only; no automated Indexing API call in this round)
3. Also re-inspect the dated URL after a recrawl: it should resolve via the
   301 to the final slug URL (redirect target indexable)

## Do not

- Do not send automated indexing requests
- Do not change robots / sitemap
- Do not revert the alias removal
