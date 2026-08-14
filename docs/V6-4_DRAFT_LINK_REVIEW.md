# V6-4 Draft Link Review

Scope: `content/_draft/` (unpublished drafts only). Drafts are excluded from
the published build (`buildDrafts = false`), so none of these affect the
production site score. Only high-confidence links were fixed; uncertain
targets are recorded below for manual review.

## Summary

- Total internal links in drafts: 13
- 200 OK: 10
- 404 (unpublished, uncertain target): 3
- Fixed: 0 (no high-confidence target available)
- Manual review: 3

## Manual Review

| # | File | Line | Broken target | Candidate | Confidence |
|---|------|------|---------------|-----------|------------|
| 1 | `content/_draft/2026-06-10-family-travel-tips-guide-attempt2.md` | 95 | `https://www.chinaboundtravel.com/posts/china - travel - resources/` (spaces in slug) | None exists; slug likely `china-travel-resources` but no such post | Low |
| 2 | `content/_draft/2026-06-10-navigating-chinas-accommodation-maze-a-californians-guide-attempt1.md` | 35 | `https://www.chinaboundtravel.com/posts/china-visa-requirements/` | `/posts/ultimate-guide-to-china-visa-for-tourists/` (site-wide canonical visa guide) | Medium |
| 3 | `content/_draft/2026-06-12-a-gastronomic-adventure-in-chengdu-a-foodies-guide-for-european-travelers-attempt1.md` | 33 | `https://www.chinaboundtravel.com/posts/china-visa-requirements/` | `/posts/ultimate-guide-to-china-visa-for-tourists/` (site-wide canonical visa guide) | Medium |

## Notes

- No draft link was auto-fixed because none of the three 404 targets has an
  unambiguous published successor. Per V6-4 rules, uncertain targets are
  recorded, not guessed.
- When the drafts are ever published, the medium-confidence candidates above
  should be re-verified against the live sitemap before replacement.
- Draft files were not modified.
