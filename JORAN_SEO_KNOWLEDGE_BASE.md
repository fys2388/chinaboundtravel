# Joran SEO Knowledge Base

> Based on the expert audit of chinaboundtravel.com (2026-07-08).  
> Initial score: 63/100. Target after P0 fixes: 75+/100.

---

## 1. Site Architecture & Domain

### DONE - What We Got Right
- Hugo static site on Cloudflare Pages: fast, secure, free hosting
- HTTPS enforced, HSTS header active
- Sitemap exists and auto-updates
- robots.txt allows crawling
- Content structure: posts + cities + resources + pricing makes logical sense
- Stripe payment integration functional

### FIXED - What Was Wrong
- **www vs non-www duplicate**: Both returned 200, splitting link equity. `_redirects` file had rules but Cloudflare Pages `_redirects` does NOT handle cross-domain redirects. Must configure at Cloudflare DNS/Bulk Redirects level.
- **H1 missing on all article pages**: `single.html` used `<div role="heading" aria-level="1">` instead of `<h1>`. Search engines do NOT treat ARIA `role="heading"` as equivalent to real `<h1>` tags. Fixed by replacing `<div>` with `<h1>`.
- **Favicon 404 errors**: head.html referenced `/favicon.ico`, `apple-touch-icon.png`, and `safari-pinned-tab.svg` that didn't exist. Fixed by removing non-existent references.
- **Internal link 404s**: 6 broken links found across templates and content:
  - `/disclosure/` should be `/affiliate-disclosure/` (4 template files)
  - `/posts/how-to-use-wechat-pay-foreigner/` should be `/posts/how-to-use-wechat-pay-as-a-foreigner/`
  - `/posts/china-high-speed-rail-booking/` should be `/posts/china-high-speed-rail-how-to-book-tickets/`
  - `/tags/china-vpn/` tag page didn't exist (no posts used that tag)

### KEY LESSON - Cloudflare Pages `_redirects` Only Handles Path Redirects
> Cloudflare Pages `_redirects` only handles path-level redirects within the same domain. For www/non-www unification, you MUST use:
> 1. Cloudflare DNS: Delete the root domain CNAME, keep only `www` CNAME pointing to Pages
> 2. Or a Cloudflare Worker to intercept non-www requests and 301 to www
> Page Rules CANNOT do hostname-level redirects — they only match URL paths.

### KEY LESSON - H1 is Not Negotiable
> Every page MUST have exactly one `<h1>`. ARIA attributes do NOT compensate for missing semantic HTML. Hugo templates must be audited after theme updates.

### KEY LESSON - Internal Links Must Be Validated
> After bulk content creation or theme changes, always grep for all `href="/"` patterns and verify each target exists. Broken internal links are worse than no links at all - they signal poor site quality to both users and crawlers.

---

## 2. Title & Meta Description Optimization

### DONE - What We Got Right
- Site-level title and description now concise in hugo.toml
- Title template `{{ .Title }} | {{ site.Title }}` is correct

### FIXED - What Was Wrong
- **16 articles had titles > 65 chars** - truncated in SERPs, diluting keyword impact
- **12 articles had descriptions > 160 chars** - truncated in SERPs
- Some descriptions had typos ("China China 2026")

### Title Best Practices (memorize this)
| Element | Target Length | Hard Max |
|---------|--------------|----------|
| Page title | 50-60 chars | 65 chars |
| Meta description | 120-150 chars | 160 chars |
| H1 heading | Matches title | N/A |

### Title Formula
```
[Primary Keyword]: [Value Proposition] ([Year])
```
Examples:
- "China High-Speed Rail: How to Book Tickets Like a Local" (52 chars)
- "WeChat Pay for Foreigners: Setup Guide & Common Mistakes" (55 chars)
- "Chengdu Panda Base: The Honest Visitor Guide (2026)" (51 chars)

### What NOT to Do
- Don't add "China Travel Guide 2026 — Visa, Payment & Internet for Foreigners" to every title
- Don't front-load the brand name - keywords first, brand at end
- Don't exceed 65 chars - Google will truncate around 60 anyway
- Don't use vague titles like "Travel Safety Guide" (19 chars) - too short, no keywords

### KEY LESSON - Title Length Discipline
> Every article title should be checked for character count BEFORE publishing. Create a pre-publish checklist that includes: title <= 65 chars, description <= 160 chars, H1 matches title, canonical URL correct.

---

## 3. E-E-A-T & Trust Signals

### DONE - What We Got Right
- About page with personal narrative (American in Chengdu)
- Affiliate Disclosure page
- Privacy Policy
- Refund Policy
- Author photo and bio

### FIXED - What Was Wrong
- **No Contact page**: Users had no way to reach us. Created `contact.md` with email, social links, response time info.
- **No Terms of Service**: Critical for Stripe payments. Already existed as `terms-of-service.md`.
- **Personal brand underutilized**: "American living in Chengdu" is a strong E-E-A-T asset but wasn't prominent in articles.

### Trust Page Checklist (every site needs these)
- [x] About page with real photos and bio
- [x] Contact page with email and response time
- [x] Privacy Policy
- [x] Terms of Service
- [x] Affiliate Disclosure
- [x] Refund Policy
- [ ] Social proof (reviews, testimonials)
- [ ] Real contact method (not just email - consider contact form)

### KEY LESSON - Trust Pages Before Monetization
> If you have Stripe checkout, you NEED Terms of Service and Contact page. Without them, conversion drops significantly. Payment processors may also require them for compliance.

---

## 4. Content Quality

### What We Got Right
- Topic selection is excellent: visa, payment (Alipay/WeChat Pay), internet (eSIM/VPN), city guides
- 153 URLs in ~57 days shows strong execution
- Monthly update posts demonstrate freshness

### What Needs Improvement
- **AI content feel**: Articles have similar structure and phrasing patterns. Mix formats - add personal anecdotes, city-specific tips, failure stories.
- **Template repetition**: "I remember..." used 6 times in one article. Each article should have a unique voice.
- **Missing verification signals**: No "last verified" dates, no source links to official pages.
- **No FAQ sections**: Most articles lack structured FAQs - these are free featured snippets.

### Content Template (use for every article)
```markdown
---
title: "..." (50-65 chars)
description: "..." (120-155 chars)
date: YYYY-MM-DD
tags: [...]
slug: "clean-url-slug"
canonicalURL: "https://www.chinaboundtravel.com/posts/slug/"
---

## Quick Answer (2-3 sentences for featured snippet)

## [Main Content]
- Real screenshots/photos where possible
- City/venue-specific details
- Official source links

## What Changed in [Year]
- Recent policy updates

## Common Mistakes to Avoid
- Real failure cases

## FAQ
- 4-6 questions with concise answers

## Related Guides
- 3-6 internal links to relevant articles
```

### KEY LESSON - AI Content Risk
> Google's helpful content system penalizes sites that publish large volumes of template-similar content. For a 57-day-old site with 153 URLs, this is a real risk. Quality > Quantity. Each article should have at least one element that can ONLY come from personal experience.

---

## 5. Technical SEO Checklist

### Before Publishing Any Article
1. Title <= 65 chars, description <= 160 chars
2. Exactly one `<h1>` matching the title
3. canonicalURL set and correct (with www)
4. All internal links verified (no 404s)
5. At least 3 internal links to other articles
6. FAQ section with 4-6 questions
7. Meta description unique (not duplicated from other pages)
8. Cover image set with alt text
9. Tags use existing taxonomy (verify tag page exists)

### Monthly Maintenance
1. Check Google Search Console for coverage errors
2. Verify all internal links still valid
3. Update "What Changed in [Year]" sections
4. Check for new 404s in server logs
5. Review and update meta descriptions for CTR

### KEY LESSON - Static Sites Need CI Too
> Even Hugo static sites benefit from automated checks. Consider adding a pre-build script that: validates all internal links, checks title/description lengths, verifies images exist, and checks canonical URLs.

---

## 6. Security Headers

### DONE
- `Strict-Transport-Security`: max-age=31536000; includeSubDomains; preload
- `X-Content-Type-Options`: nosniff
- `X-Frame-Options`: SAMEORIGIN
- `Referrer-Policy`: strict-origin-when-cross-origin
- `Permissions-Policy`: camera=(), microphone=(), geolocation=()
- `Content-Security-Policy`: Added with allowed sources for GA, Stripe, Pollinations
- Cache-Control: Improved from `max-age=0` to `max-age=3600, stale-while-revalidate=86400` for HTML

### Cache Strategy
| Content Type | max-age | Strategy |
|---------------|---------|----------|
| Static assets (CSS/JS/images) | 31536000 (1 year) | immutable |
| HTML pages | 3600 (1 hour) | must-revalidate, stale-while-revalidate=86400 |
| Sitemap/RSS | 3600 (1 hour) | standard |

### KEY LESSON - Cache Headers Matter
> `cache-control: public, max-age=0, must-revalidate` forces revalidation on EVERY page load. For a static Hugo site, this wastes server resources and slows down the user experience. Cache HTML for 1 hour with stale-while-revalidate for the best balance.

---

## 7. Cloudflare-Specific Notes

### `_redirects` File Limitations
- Only handles path-level redirects within the SAME domain
- Cannot redirect non-www to www (cross-domain)
- Use Cloudflare Dashboard -> Rules -> Bulk Redirects for domain-level redirects
- 301 redirects use `!` suffix: `/old-path /new-path 301!`

### `_headers` File
- Comment lines use `/* ... */` syntax (C-style)
- CSP should be one continuous line
- Headers apply top-down; more specific paths override general ones

### KEY LESSON
> Don't assume `_redirects` handles everything. For www canonicalization, Cloudflare Bulk Redirects or DNS configuration is required. Test with `curl -I` from the actual internet, not just locally.

---

## 8. Action Items Still Pending

### P1 (Two Weeks)
- [ ] Shorten title template to avoid adding site title to very long titles
- [ ] Add FAQ schema, Article schema, Breadcrumb schema to core pages
- [ ] Build topic cluster pages: Alipay hub, Visa hub, Internet hub
- [ ] Add official source links (visa.gov.cn, Alipay official, etc.)
- [ ] Configure www/non-www redirect in Cloudflare Dashboard

### P2 (One Month)
- [ ] Write 5-8 pillar articles with original reporting
- [ ] Create city pages: Beijing, Shanghai, Chengdu, Xi'an, Guilin, Zhangjiajie
- [ ] Build internal link network (3-6 links per article)
- [ ] Create PDF/Checklist lead magnet
- [ ] Source real questions from Reddit, TripAdvisor, Quora
- [ ] Add structured data (FAQ, Article, Breadcrumb) to all posts

---

*Last updated: 2026-07-09*

## 9. P1 Optimizations Completed (2026-07-09)

### FAQ Schema Auto-Detection
- Created `schema_faq.html` partial that automatically detects `## FAQ` sections in article content
- Extracts H3 questions and paragraph answers, outputs `FAQPage` JSON-LD
- Integrated into `schema_json.html` so ALL articles with FAQ sections get schema automatically
- Free featured snippets from Google for FAQ-optimized content

### Topic Cluster Hub Pages
- Created 3 pillar pages: `/payments/`, `/internet/`, `/visa/`
- Each has comparison tables, FAQ sections, and links to all related articles
- Added to navigation menu for easy discovery
- Hub pages cross-link to each other for internal link equity

### Related Posts Improvement
- Changed from random 3 posts to tag-based matching
- Articles now show related content from the same topic, improving engagement and SEO

### Travel Safety Guide Title Fix
- Title was only 19 chars ("Travel Safety Guide") — no keywords
- Changed to "Is China Safe for Travelers? Honest Safety Guide 2026" (55 chars)
