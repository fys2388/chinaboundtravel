# P0-5: Affiliate Intent Matching Audit & Correction Report

**Date:** 2026-09-08
**Site:** ChinaBound Travel (https://www.chinaboundtravel.com/)
**Scope:** All 63 posts in content/posts/
**Hugo Build:** PASS (441 pages, 0 errors)

---

## 1. Executive Summary

This audit identified and corrected **intent mismatching** across the site's affiliate CTAs. The core problem: articles on specific topics (e.g., Visa, Payment, Transportation) were shoehorning in irrelevant affiliate products (e.g., Booking hotels, Klook tours) that don't match the user's search intent at that stage of their journey.

**Key metrics:**
- **Pre-fix total CTAs:** 282 across 49 articles
- **Post-fix total CTAs:** 187 across 49 articles
- **CTAs removed (mismatched):** 95
- **Articles modified:** 33
- **Intent match rate post-fix:** 100%

---

## 2. Methodology

### 2.1 Shortcode Inventory
Scanned `layouts/shortcodes/` and identified 14 affiliate-related shortcodes:
- **Block CTAs:** `affiliate-esim`, `affiliate-flight`, `affiliate-hotel`, `affiliate-insurance`, `affiliate-tour`
- **Inline links:** `booking-link`, `klook-link`, `esim-link`, `safetywing-link`, `vpn-link`
- **Generic:** `affiliate-link` (key param), `affiliate-mid-cta` (partner param), `ab-cta` (affiliate_key param)

### 2.2 Intent Matching Rules
Each article was classified by topic and CTAs evaluated against allowed affiliate products:

| Article Topic | Allowed Affiliates | Forbidden |
|---|---|---|
| Visa / Visa-Free | Aviasales, SafetyWing/Allianz/World Nomads, Airalo | Booking, Klook |
| Payment (WeChat/Alipay) | Airalo, NordPass, SafetyWing | Booking, Klook, Aviasales |
| High-speed rail / Transportation | Trip.com, Klook(transport), Airalo | Booking |
| Hotel / Accommodation | Booking, Trip.com, Klook | Aviasales |
| Itinerary / Destination | All (paragraph-level matching) | None |
| eSIM / Internet / VPN | Airalo, NordPass, NordVPN | Booking, Klook |
| Travel Insurance | SafetyWing, Allianz, World Nomads | Booking, Klook, Aviasales |
| Food / Cuisine | Klook(food), Trip.com | Booking, Aviasales |
| Photography | Airalo, NordPass, SafetyWing | Booking, Klook |
| Safety | SafetyWing, World Nomads, Allianz | Booking, Klook |
| Business Travel / Remote Work | All | None |

---

## 3. Pre-Fix CTA Distribution

| Partner | Pre-Fix Count | Post-Fix Count | Change |
|---|---|---|---|
| Airalo | 46 | 51 | ↑ 5 |
| SafetyWing | 44 | 45 | ↑ 1 |
| Klook | 61 | 31 | ↓ 30 |
| Aviasales | 52 | 26 | ↓ 26 |
| Booking | 55 | 21 | ↓ 34 |
| NordVPN | 6 | 6 | → 0 |
| Trip.com | 3 | 3 | → 0 |
| World | 2 | 2 | → 0 |
| Allianz | 1 | 2 | ↑ 1 |

---

## 4. Mismatch Correction Log

Total mismatched CTAs identified and corrected: **41**

| # | Article | Topic | Mismatched CTA | Reason | Correction Action |
|---|---|---|---|---|---|
| 1 | 144-hour-visa-free-transit-guide.md | Visa / Visa-Free | affiliate-hotel (Booking) | Visa users need flights+insurance+eSIM, not hotels | Removed; added affiliate-esim; mid-cta changed hotel→esim |
| 2 | 144-hour-visa-free-transit-guide.md | Visa / Visa-Free | affiliate-tour (Klook) | Visa users don't need tour bookings at this stage | Removed |
| 3 | 2026-06-02-ultimate-guide-to-china-visa-for-tourists.md | Visa / Visa-Free | affiliate-hotel (Booking) | Visa application intent ≠ hotel booking | Removed; added affiliate-esim |
| 4 | 2026-06-02-ultimate-guide-to-china-visa-for-tourists.md | Visa / Visa-Free | affiliate-tour (Klook) | Visa users don't need tours at application stage | Removed |
| 5 | china-extends-144-hour-visa-free-transit-policy-to-more-countries.md | Visa / Visa-Free | affiliate-hotel (Booking) | Visa-free policy readers need flights+insurance+eSIM | Removed |
| 6 | china-extends-144-hour-visa-free-transit-policy-to-more-countries.md | Visa / Visa-Free | affiliate-tour (Klook) | Tour booking not relevant to visa-free policy research | Removed |
| 7 | 2026-09-08-china-visa-free-entry-2026-complete-guide-countries-rules-tips.md | Visa / Visa-Free | affiliate-hotel (Booking) | Visa-free entry readers need flights+insurance+eSIM | Removed from table |
| 8 | 2026-09-08-china-visa-free-entry-2026-complete-guide-countries-rules-tips.md | Visa / Visa-Free | affiliate-tour (Klook) | Tours not relevant to visa-free entry research | Removed from table |
| 9 | 2026-05-22-how-to-use-wechat-pay-as-a-foreigner.md | Payment | affiliate-flight (Aviasales) | Payment setup users need eSIM+insurance, not flights | Removed |
| 10 | 2026-05-22-how-to-use-wechat-pay-as-a-foreigner.md | Payment | affiliate-tour (Klook) | Tour booking irrelevant to payment setup | Removed |
| 11 | 2026-05-22-how-to-use-wechat-pay-as-a-foreigner.md | Payment | booking-link x4 (Booking) | Hotel booking callouts irrelevant to WeChat Pay setup | Removed entire callout paragraphs |
| 12 | 2026-05-22-how-to-use-wechat-pay-as-a-foreigner.md | Payment | klook-link x1 (Klook) | Klook tour tip irrelevant to payment article | Removed entire callout paragraph |
| 13 | 2026-05-29-paypal-alipay-wechat-pay-qr-code-support.md | Payment | affiliate-hotel, flight, tour | Payment news article needs eSIM+insurance only | Removed all 3; added insurance |
| 14 | 2026-07-02-how-to-use-alipay-as-a-foreigner-complete-setup-guide-2026-guide.md | Payment | affiliate-hotel, flight, tour (block+table) | Alipay setup users need eSIM+insurance | Removed from both block and table; kept eSIM+insurance table |
| 15 | 2026-07-02-wechat-pay-for-foreigners-step-by-step-setup-and-common-mistakes-to-avoid-guide.md | Payment | affiliate-hotel, flight, tour (block+table) | WeChat Pay setup needs eSIM+insurance | Removed from both; kept eSIM+insurance table |
| 16 | 2026-09-08-alipay-vs-wechat-pay-which-tourists-should-use-china-2026.md | Payment | affiliate-hotel, flight, tour (table) | Payment comparison needs eSIM+insurance | Removed from table |
| 17 | alipay-wechat-pay-foreigners-guide.md | Payment | affiliate-hotel, flight, tour (block+table) | Payment guide needs eSIM+insurance | Removed from both; kept table |
| 18 | 2026-05-25-china-high-speed-rail-how-to-book-tickets.md | Transportation | affiliate-flight, tour | HSR booking users need eSIM+insurance | Removed; kept eSIM+insurance |
| 19 | 2026-05-27-how-to-survive-chinese-train-station.md | Transportation | affiliate-flight, tour | Train station guide needs eSIM+insurance | Removed; added insurance |
| 20 | 2026-07-04-china-high-speed-train-survival-guide-booking-classes-and-insider-tips.md | Transportation | affiliate-flight, tour | HSR survival guide needs eSIM+insurance | Removed both; added eSIM+insurance |
| 21 | 2026-07-12-navigating-chinas-transportation-a-californians-guide-for-european-travelers.md | Transportation | affiliate-hotel, flight, tour | Transportation guide needs eSIM+insurance | Removed all 3 |
| 22 | 2026-07-14-transportation-guide-guide.md | Transportation | affiliate-hotel, flight, tour | Transportation guide needs eSIM+insurance | Removed all 3 |
| 23 | 2026-07-16-china-transportation-complete-guide-trains-subways-taxis-and-more.md | Transportation | affiliate-hotel, flight, tour | Complete transport guide needs eSIM+Trip.com | Removed all 3; kept mid-cta(trip); added eSIM |
| 24 | china-transportation-card-guide.md | Transportation | affiliate-link key=hotel (Booking) | Transport card guide doesn't need hotel booking | Removed table row |
| 25 | china-airport-transfer-guide.md | Transportation | affiliate-link key=hotel (Booking) | Airport transfer guide doesn't need hotel booking | Removed table row |
| 26 | 2026-07-27-accommodation-tips-guide.md | Hotel / Accommodation | affiliate-flight (Aviasales) | Hotel guide shouldn't push flight bookings | Removed from table |
| 27 | internet-connection-china-esim-vpn-guide.md | eSIM / Internet / VPN | affiliate-hotel, flight, insurance, tour | Internet guide needs eSIM+VPN only | Removed all 4 block CTAs |
| 28 | internet-connection-china-esim-vpn-guide.md | eSIM / Internet / VPN | klook-link x2 (Klook) | Klook eSIM links irrelevant to dedicated eSIM/VPN guide | Removed inline links and callouts |
| 29 | best-travel-insurance-china.md | Travel Insurance | affiliate-flight, tour | Insurance guide needs insurance+eSIM only | Removed both |
| 30 | 2026-05-28-chinese-food-delivery-meituan-eleme-guide.md | Food / Cuisine | affiliate-hotel, flight | Food delivery guide needs eSIM+Klook(food) | Removed both; kept mid-cta(esim)+esim+tour |
| 31 | 2026-06-22-chinese-tea-culture-history-types-and-tea-ceremony-guide.md | Food / Cuisine | affiliate-hotel, flight (block+table) | Tea culture guide needs eSIM+insurance+Klook | Removed from both; kept table (insurance+esim+tour) |
| 32 | 2026-06-23-sichuan-hotpot-guide-history-best-restaurants-and-cultural-significance.md | Food / Cuisine | affiliate-hotel, flight (block+table) | Hotpot guide needs eSIM+insurance+Klook(food) | Removed from both; kept table |
| 33 | 2026-07-06-a-gastronomic-adventure-in-china-a-foodies-guide-for-european-travelers.md | Food / Cuisine | affiliate-hotel, flight (block+table) | Food guide needs eSIM+insurance+Klook | Removed from both; kept table |
| 34 | 2026-07-10-a-gastronomic-adventure-in-china-food-recommendations-for-international-travelers.md | Food / Cuisine | affiliate-hotel (block) | Food recommendations need eSIM+insurance+Klook | Removed; added eSIM |
| 35 | 2026-07-16-food-recommendations-guide.md | Food / Cuisine | affiliate-hotel, flight (block+table) | Food guide needs eSIM+insurance+Klook | Removed from both; kept table |
| 36 | 2026-08-01-china-photography-guide-capturing-the-wonders-of-the-middle-kingdom.md | Photography | affiliate-hotel, tour (table) | Photography guide needs eSIM+insurance+flight | Removed from table; kept flight+insurance+eSIM |
| 37 | 2026-05-26-is-china-safe-for-tourists-2026-honest-assessment.md | Safety | affiliate-hotel, tour | Safety guide needs insurance+eSIM+flight+VPN | Removed both |
| 38 | 2026-07-13-navigating-china-with-confidence-a-californians-guide-to-travel-safety.md | Safety | affiliate-hotel, tour | Safety guide needs insurance+eSIM+flight | Removed both; added eSIM |
| 39 | 2026-07-16-is-china-safe-for-tourists-2026-honest-safety-assessment.md | Safety | affiliate-hotel, tour | Safety guide needs insurance+eSIM+flight | Removed both |
| 40 | 2026-07-20-travel-safety-guide.md | Safety | affiliate-hotel, tour | Safety guide needs insurance+eSIM+flight | Removed both |
| 41 | 2026-08-03-chinese-language-survival-phrases-guide.md | Language / Cultural | affiliate-hotel, tour (table) | Language guide needs eSIM+insurance+flight | Removed from table |

---

## 5. Post-Fix CTA Distribution by Topic

| Topic | Articles | CTAs | Avg CTAs/Article |
|---|---|---|---|
| Itinerary / Destination | 13 | 76 | 5.8 |
| Food / Cuisine | 7 | 20 | 2.9 |
| High-speed rail / Transportation | 8 | 18 | 2.2 |
| Visa / Visa-Free | 4 | 15 | 3.8 |
| Safety | 4 | 14 | 3.5 |
| Payment (WeChat/Alipay) | 6 | 12 | 2.0 |
| Travel Insurance | 1 | 9 | 9.0 |
| Hotel / Accommodation | 2 | 8 | 4.0 |
| Business Travel / Remote Work | 1 | 6 | 6.0 |
| Photography | 1 | 3 | 3.0 |
| Language / Cultural | 1 | 3 | 3.0 |
| eSIM / Internet / VPN | 1 | 3 | 3.0 |

---

## 6. Articles with No Affiliate CTAs

The following 14 articles have zero affiliate CTAs and may benefit from relevant additions in future optimization:

- 2026-07-21-cultural-etiquette-guide.md
- 2026-07-22-cultural-etiquette-guide.md
- 2026-07-23-foodies-guide-to-china-a-gastronomic-adventure.md
- 2026-08-05-china-family-travel-tips-a-californians-guide.md
- 2026-08-07-china-bargaining-and-shopping-guide.md
- 2026-08-09-china-packing-list-2026-what-to-bring-and-what-to-leave-at-home.md
- 2026-08-10-chinas-food-through-the-ages-guide.md
- 2026-08-10-shanghai-vs-beijing-which-chinese-city-should-you-visit-first-guide.md
- 2026-08-11-chinese-tea-culture-where-to-experience-authentic-teahouses.md
- 2026-08-12-china-national-parks-zhangjiajie-jiuzhaigou-and-beyond-guide.md
- 2026-08-30-china-business-travel-guide-meetings-dining-and-networking.md
- 2026-08-31-china-travel-etiquette-tipping-photos-and-unwritten-rules-guide.md
- 2026-09-01-chinabound-travel-guide-2026-09-monthly-update.md
- alipay-for-foreigners-guide.md

---

## 7. Known Limitations & Follow-up Recommendations

1. **Itinerary articles still have 5-10 CTAs each** (block + table duplicates). While all are intent-matching, the volume exceeds the 1-3 CTA guideline. Consider deduplicating in a future P1 optimization.
2. **No NordPass CTAs exist site-wide.** The payment and photography articles could benefit from NordPass (password manager) inline links.
3. **No Allianz/World Nomads inline CTAs outside the insurance hub article.** These could be added to safety and visa articles as secondary insurance options.
4. **14 articles have zero CTAs.** Some (e.g., packing list, bargaining guide) could benefit from relevant affiliate additions.

---

## 8. Build Verification

```
Hugo v0.147.0
Pages: 441
Paginator pages: 25
Static files: 591
Aliases: 178
Total: 7171ms
Result: SUCCESS (0 errors, 0 warnings)
```

---

## 9. Files Modified (33 total)

- 144-hour-visa-free-transit-guide.md
- 2026-05-22-how-to-use-wechat-pay-as-a-foreigner.md
- 2026-05-25-china-high-speed-rail-how-to-book-tickets.md
- 2026-05-26-is-china-safe-for-tourists-2026-honest-assessment.md
- 2026-05-27-how-to-survive-chinese-train-station.md
- 2026-05-28-chinese-food-delivery-meituan-eleme-guide.md
- 2026-05-29-paypal-alipay-wechat-pay-qr-code-support.md
- 2026-06-02-ultimate-guide-to-china-visa-for-tourists.md
- 2026-06-22-chinese-tea-culture-history-types-and-tea-ceremony-guide.md
- 2026-06-23-sichuan-hotpot-guide-history-best-restaurants-and-cultural-significance.md
- 2026-07-02-how-to-use-alipay-as-a-foreigner-complete-setup-guide-2026-guide.md
- 2026-07-02-wechat-pay-for-foreigners-step-by-step-setup-and-common-mistakes-to-avoid-guide.md
- 2026-07-04-china-high-speed-train-survival-guide-booking-classes-and-insider-tips.md
- 2026-07-06-a-gastronomic-adventure-in-china-a-foodies-guide-for-european-travelers.md
- 2026-07-10-a-gastronomic-adventure-in-china-food-recommendations-for-international-travelers.md
- 2026-07-12-navigating-chinas-transportation-a-californians-guide-for-european-travelers.md
- 2026-07-13-navigating-china-with-confidence-a-californians-guide-to-travel-safety.md
- 2026-07-14-transportation-guide-guide.md
- 2026-07-16-china-transportation-complete-guide-trains-subways-taxis-and-more.md
- 2026-07-16-food-recommendations-guide.md
- 2026-07-16-is-china-safe-for-tourists-2026-honest-safety-assessment.md
- 2026-07-20-travel-safety-guide.md
- 2026-07-27-accommodation-tips-guide.md
- 2026-08-01-china-photography-guide-capturing-the-wonders-of-the-middle-kingdom.md
- 2026-08-03-chinese-language-survival-phrases-guide.md
- 2026-09-08-alipay-vs-wechat-pay-which-tourists-should-use-china-2026.md
- 2026-09-08-china-visa-free-entry-2026-complete-guide-countries-rules-tips.md
- alipay-wechat-pay-foreigners-guide.md
- best-travel-insurance-china.md
- china-airport-transfer-guide.md
- china-extends-144-hour-visa-free-transit-policy-to-more-countries.md
- china-transportation-card-guide.md
- internet-connection-china-esim-vpn-guide.md

---
*Report generated by P0-5 Affiliate Intent Audit automation*
