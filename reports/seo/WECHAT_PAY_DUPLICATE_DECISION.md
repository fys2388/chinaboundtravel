# WeChat Pay Duplicate Decision (MANUAL_REVIEW — no change made this round)

- Date: 2026-08-16
- Status: ANALYSIS ONLY — no article was modified.
- Decision owner: site owner. This document recommends; it does not execute.

## The two pages

| page | content_id | GSC state | 28d impressions | 28d clicks | avg position | canonical |
|---|---|---|---|---|---|---|
| How to Use WeChat Pay as a Foreigner (2026) | cbt-707a8899c0a7 | INDEXED | 83 | 0 | 62.45 | self |
| WeChat Pay for Foreigners: Setup Guide & Mistakes | cbt-255af4ed003a | NOT_INDEXED (Alternate page with proper canonical tag) | 1 | 0 | 11.0 | self |

## Content similarity (heuristic, no LLM)

- Unique-token Jaccard: 0.248 (moderate topical overlap).
- A (INDEXED, 1785 words) covered by B (NOT_INDEXED, 2559 words): 46% of A's unique tokens appear in B; B covered by A: 35%.
- Verbatim 10-gram overlap: 9 shingles shared (Jaccard 0.0021) — the articles are NOT verbatim duplicates; they are two longer-form pieces on the same topic (WeChat Pay for foreigners).
- Both declare self-canonical; Google still chose the older page as canonical, so the newer page is treated as an alternate.

## Options

### A. Merge
- 301 the NOT_INDEXED setup-guide URL into the INDEXED how-to-use URL, folding unique "common mistakes" content into the survivor.
- Pros: consolidates signals; immediately ends the alternate-page state; strongest single page.
- Cons: loses a distinct URL; requires content edit + redirect; slight risk of losing long-tail query match for "setup/mistakes" phrasing.

### B. Differentiate (RECOMMENDED if the setup guide has genuinely unique sections)
- Keep both URLs, but re-aim them at distinct intents:
  - Keep INDEXED page: "How to Use WeChat Pay as a Foreigner" (usage in daily life).
  - Reposition setup guide: "Set Up WeChat Pay for Your China Trip: Step-by-Step + Common Mistakes" with clearly distinct H1/title/meta and reorganized sections (setup wizard walkthrough, verification, common mistakes).
- Pros: captures two intents (how-to-use vs setup); no redirect risk; commercial value retained on both.
- Cons: requires a real content differentiation edit; Google may still not index for weeks; needs a re-crawl/Inspection.

### C. Keep both temporarily
- Wait for 2 more data windows before deciding.
- Pros: zero risk now; data-driven.
- Cons: the 2nd page stays not-indexed; any search equity continues to concentrate on the INDEXED page anyway.

## Recommendation

**B (Differentiate)** as the primary path, with **A (Merge)** as the fallback if a review shows the setup guide has <~40% unique value beyond the how-to-use page. Evidence basis: the two pages share a commercial PAYMENT intent, the newer page holds a favorable position signal on the one impression it has (pos 11) but no impression volume, and the existing overlap is topical rather than verbatim, so a clear intent split is feasible without destroying either page.

Default principle applied: the already-indexed page (`how-to-use-wechat-pay-as-a-foreigner`, 83 impressions) is treated as the stronger page; any merge should preserve it, and any differentiation must not weaken it.

## Next step

P1-GROWTH-07 WECHAT PAY CONTENT DECISION + FIRST SEO EXPANSION will execute the chosen option (owner approval required first).
