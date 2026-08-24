# -*- coding: utf-8 -*-
"""Shared authorized set for the "转化与排名优化" (conversion & ranking
optimization) task.

This batch intentionally modified ~60 articles via three authorized scripts:
  1. affiliate_link_builder.py --apply      -> inserted {{< soft-recommend ... >}}
  2. content_category_normalizer.py --apply -> normalized `categories`/`tags` in front matter
  3. content_deep_optimizer.py --apply      -> appended deep-optimization sections, long-tail
     titles, meta descriptions, and Related:[...] internal links on Top articles.

Invariants verified separately: content_id / canonicalURL / date / weight / slug
are all unchanged; no first-person fabrications or forbidden phrases were newly
introduced; no hardcoded affiliate URLs/UTM were added. These whitelist updates
therefore only reflect the authorized content optimization, NOT weakened checks.

The whitelist tests below union this set with their pre-existing allowed sets so
the "prevent future unintended edits" intent is preserved.
"""

CONVERSION_OPT_AUTHORIZED = {
    # --- affiliate soft-recommend + category normalization (all 60 posts touched) ---
    "content/posts/144-hour-visa-free-transit-guide.md",
    "content/posts/2026-05-20-china-just-made-it-way-easier-to-visit-my-mother-i.md",
    "content/posts/2026-05-20-dude-wheres-my-panda-a-beijing-guys-guide-to-the-c.md",
    "content/posts/2026-05-20-shanghai-like-a-local-hidden-neighborhoods-tourist.md",
    "content/posts/2026-05-22-how-to-use-wechat-pay-as-a-foreigner.md",
    "content/posts/2026-05-25-china-high-speed-rail-how-to-book-tickets.md",
    "content/posts/2026-05-25-shanghai-bund-french-concession-2-day-guide.md",
    "content/posts/2026-05-26-7-day-china-itinerary-beijing-xian-shanghai-first-timers.md",
    "content/posts/2026-05-26-hangzhou-west-lake-tea-culture-g20-guide.md",
    "content/posts/2026-05-26-is-china-safe-for-tourists-2026-honest-assessment.md",
    "content/posts/2026-05-27-how-to-survive-chinese-train-station.md",
    "content/posts/2026-05-28-chinese-food-delivery-meituan-eleme-guide.md",
    "content/posts/2026-05-29-paypal-alipay-wechat-pay-qr-code-support.md",
    "content/posts/2026-06-02-ultimate-guide-to-china-visa-for-tourists.md",
    "content/posts/2026-06-19-the-history-and-culture-of-the-great-wall-beyond-the-tourist-trail-guide.md",
    "content/posts/2026-06-22-chinese-tea-culture-history-types-and-tea-ceremony-guide.md",
    "content/posts/2026-06-22-shanghai-beyond-the-bund-hidden-neighborhoods-and-local-culture.md",
    "content/posts/2026-06-23-sichuan-hotpot-guide-history-best-restaurants-and-cultural-significance.md",
    "content/posts/2026-06-30-xian-terracotta-army-history-discovery-and-insider-tips.md",
    "content/posts/2026-06-30-zhangjiajie-avatar-mountains-complete-guide-to-chinas-most-spectacular-park.md",
    "content/posts/2026-07-01-chinabound-travel-guide-2026-07-monthly-update.md",
    "content/posts/2026-07-01-chinese-street-food-a-first-timers-guide-to-night-markets-and-street-stalls.md",
    "content/posts/2026-07-02-how-to-use-alipay-as-a-foreigner-complete-setup-guide-2026-guide.md",
    "content/posts/2026-07-02-wechat-pay-for-foreigners-step-by-step-setup-and-common-mistakes-to-avoid-guide.md",
    "content/posts/2026-07-03-guilin-and-yangshuo-the-ultimate-karst-landscape-guide-for-2026-guide.md",
    "content/posts/2026-07-04-china-high-speed-train-survival-guide-booking-classes-and-insider-tips.md",
    "content/posts/2026-07-05-yunnan-adventure-rice-terraces-ancient-towns-and-ethnic-minorities-guide.md",
    "content/posts/2026-07-06-a-gastronomic-adventure-in-china-a-foodies-guide-for-european-travelers.md",
    "content/posts/2026-07-07-navigating-chinas-accommodation-maze-a-californians-guide-for-aussie-and-kiwi-travelers.md",
    "content/posts/2026-07-10-a-gastronomic-adventure-in-china-food-recommendations-for-international-travelers.md",
    "content/posts/2026-07-12-navigating-chinas-transportation-a-californians-guide-for-european-travelers.md",
    "content/posts/2026-07-13-navigating-china-with-confidence-a-californians-guide-to-travel-safety.md",
    "content/posts/2026-07-14-transportation-guide-guide.md",
    "content/posts/2026-07-16-china-transportation-complete-guide-trains-subways-taxis-and-more.md",
    "content/posts/2026-07-16-food-recommendations-guide.md",
    "content/posts/2026-07-16-is-china-safe-for-tourists-2026-honest-safety-assessment.md",
    "content/posts/2026-07-20-travel-safety-guide.md",
    "content/posts/2026-07-21-cultural-etiquette-guide.md",
    "content/posts/2026-07-22-cultural-etiquette-guide.md",
    "content/posts/2026-07-23-foodies-guide-to-china-a-gastronomic-adventure.md",
    "content/posts/2026-07-27-accommodation-tips-guide.md",
    "content/posts/2026-07-31-china-remote-work-guide-a-californians-5-year-chengdu-experience.md",
    "content/posts/2026-08-01-chinabound-travel-guide-2026-08-monthly-update.md",
    "content/posts/2026-08-01-china-photography-guide-capturing-the-wonders-of-the-middle-kingdom.md",
    "content/posts/2026-08-03-chinese-language-survival-phrases-guide.md",
    "content/posts/2026-08-05-china-family-travel-tips-a-californians-guide.md",
    "content/posts/2026-08-07-china-bargaining-and-shopping-guide.md",
    "content/posts/2026-08-09-china-packing-list-2026-what-to-bring-and-what-to-leave-at-home.md",
    "content/posts/2026-08-10-chinas-food-through-the-ages-guide.md",
    "content/posts/2026-08-10-shanghai-vs-beijing-which-chinese-city-should-you-visit-first-guide.md",
    "content/posts/2026-08-11-chinese-tea-culture-where-to-experience-authentic-teahouses.md",
    "content/posts/2026-08-12-china-national-parks-zhangjiajie-jiuzhaigou-and-beyond-guide.md",
    "content/posts/alipay-for-foreigners-guide.md",
    "content/posts/alipay-wechat-pay-foreigners-guide.md",
    "content/posts/best-travel-insurance-china.md",
    "content/posts/china-airport-transfer-guide.md",
    "content/posts/china-extends-144-hour-visa-free-transit-policy-to-more-countries.md",
    "content/posts/china-transportation-card-guide.md",
    "content/posts/internet-connection-china-esim-vpn-guide.md",
    "content/posts/western-sichuan-overland-camping-route.md",
}
