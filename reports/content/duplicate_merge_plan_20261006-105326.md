# Duplicate Draft Merge Plan

Generated 2026-10-06 02:53 UTC by `scripts/content_dedup_merge.py` (deterministic, no LLM).

**Dry run — no files modified.** Re-run with `--apply` to merge.

- Drafts scanned: **3**
- `slug_conflict` (never merge): **2**
- `topic_duplicate`: **1**
- `publishable` (no conflict): **0**
- Mergeable paragraphs total: **0**

## `2026-05-20-china-just-made-it-way-easier-to-visit-my-mother-i.md`
- kind: `topic_duplicate`  sim=0.555
- target: `content\posts\2026-09-08-china-visa-free-entry-2026-complete-guide-countries-rules-tips.md`
- ⚠️ policy-gated topic(s): target article is immigration — never merged
- paragraphs: 14 total, 0 mergeable
- action: skip: target is a policy-gated article; not merged

## `2026-08-26-china-business-travel-guide-meetings-dining-and-networking-attempt2.md`
- kind: `slug_conflict`  sim=1.0
- target: `content\posts\2026-08-30-china-business-travel-guide-meetings-dining-and-networking.md`
- paragraphs: 18 total, 0 mergeable
- action: flag: slug collides with a published post; publishing would duplicate a URL. Merge manually or retire.

## `2026-08-26-china-travel-etiquette-tipping-photos-and-unwritten-rules-guide-attempt1.md`
- kind: `slug_conflict`  sim=1.0
- target: `content\posts\2026-08-31-china-travel-etiquette-tipping-photos-and-unwritten-rules-guide.md`
- paragraphs: 4 total, 0 mergeable
- action: flag: slug collides with a published post; publishing would duplicate a URL. Merge manually or retire.
