# P1-BRAND-03 — Legacy Persona Migration Pilot（实验记录）

- 周期：P1-BRAND-03
- 迁移日期：2026-08-16
- 基线：GitHub main `9feab69`
- 范围：3 篇高价值 legacy 文章，Persona 2.0（Editorial Persona）迁移
- 原则：只改“身份来源”，不改事实/数据/政策/交通信息/旅游建议；URL / canonical / content_id / affiliate / UTM 全部保持不变

---

## 1. Pilot A — Western Sichuan Overland Camping Route

| 字段 | 值 |
|---|---|
| content_id | `cbt-80f6c218ad94` |
| title | Western Sichuan Overland Camping Route: 7 Days |
| URL | https://www.chinaboundtravel.com/posts/western-sichuan-overland-camping-route/ |
| GSC 28d baseline | impressions=26, clicks=1, CTR=3.85%, position=19.31, INDEXED |
| Affiliate baseline | klook-link（Klook Car Rentals）、booking-link（Kangding hotels）、affiliate-hotel / flight / insurance / esim / tour shortcodes |

### Before（虚构个人经历）→ After（编辑口吻）

| Before | After |
|---|---|
| H1 “My 7-Day Adventure Through China's Most Epic Wilderness” | “7 Days Through China's Most Epic Wilderness” |
| “Let me set the scene … My wife, Xiao Li … Five years living in China … my friend Lao Wang” | “Western Sichuan (Chuan Xi) is a demanding overland route that rewards careful planning. The 7-day loop below starts in Chengdu …” |
| “But trust me - it's worth every single minute.” | “It's demanding, but travelers consistently say the payoff is worth it.” |
| “Let me save you some pain. I made every mistake in the book on my first trip” | “This checklist condenses the most common first-trip mistakes so you don't have to learn them the hard way.” |
| “I forgot lip balm once - never again. My lips cracked so bad I couldn't smile for a week.” | “Sunburn and cracked lips are the most common complaints from first-time high-altitude campers.” |
| “I drove my Honda CR-V first time - big mistake.” | “A standard SUV is not enough for many of these roads.” |
| “We left at 6 AM to beat the traffic” | “Leave at 6 AM to beat the traffic” |
| “Trust me, it's better than any restaurant in Chengdu.” | “A bowl at one of the small stalls here rivals anything you'll find in Chengdu.” |
| “This is where we set up camp for the first time” | “This is the first recommended campsite on the route” |
| “We forgot - our tent almost blew away!” | “gusts have been known to flatten poorly staked tents” |
| “Final Thoughts: Why This Trip Changed My Life” / “When I first came to China, I thought I knew what 'adventure' meant.” | “Final Thoughts: Why This Route Stands Out” / “Few routes in China combine such extreme scenery with such real logistical challenges.” |
| Disclaimer “All recommendations are based on my personal experience.” | “Recommendations are based on current research and traveler reports.” |

保留：全部事实（altitude、里程、每日路线、露营准备清单）、内部链接、klook/booking shortcode、价格/开放信息。

---

## 2. Pilot B — Guilin & Yangshuo

| 字段 | 值 |
|---|---|
| content_id | `cbt-bf4ec5e57a07` |
| title | Guilin & Yangshuo: Complete 2026 Travel Guide |
| URL | https://www.chinaboundtravel.com/posts/guilin-and-yangshuo-the-ultimate-karst-landscape-guide-for-2026/ |
| GSC 28d baseline | impressions=24, clicks=0, CTR=0.0%, position=18.88, INDEXED |
| Affiliate baseline | affiliate-hotel / flight / esim / tour shortcodes |

### Before → After

| Before | After |
|---|---|
| summary “…insider tips from a 5-year China expat.” | summary “…practical insider tips.” |
| Intro “I'd read about the karst landscape … I looked down at those limestone peaks” | “The karst landscape is famous from the 20 RMB banknote image and countless photographs …” |
| “**My honest take:**” | “**Editor's take:**” |
| “I've been to Guilin in three different seasons, and the difference is staggering.” | “Visitors who return in different seasons report a staggering difference.” |
| “This is the route I'd recommend to a friend.” | “This route covers the essential Guilin and Yangshuo highlights without overpacking.” |
| “if you love Chinese regional cuisine as much as I do” | “if you're exploring Chinese regional cuisine” |
| “Quiet, scenic, my top recommendation.” | “Quiet, scenic, and a top pick among returning visitors.” |
| “Based on what I'd actually spend” | “Based on typical mid-range spending” |
| “I made this mistake once — never again.” | “Noise complaints are common, so ask your hotel specifically about this before booking.” |

保留：全部价格（¥）、时间、班次、行程、内部链接、图片、FAQ。

---

## 3. Pilot C — Sichuan Hotpot

| 字段 | 值 |
|---|---|
| content_id | `cbt-550a6e3e929c` |
| title | Sichuan Hotpot Guide: History & Best Restaurants |
| URL | https://www.chinaboundtravel.com/posts/sichuan-hotpot-guide-history-best-restaurants-and-cultural-significance/ |
| GSC 28d baseline | impressions=11, clicks=0, CTR=0.0%, position=37.18, INDEXED |
| Affiliate baseline | affiliate-flight / tour / hotel / insurance / esim shortcodes + NordVPN 直链 |

### Before → After

| Before | After |
|---|---|
| description “…authentic picks from a US expat in Chengdu.” | description “…current picks for first-time visitors.” |
| “As an American who has spent over 5 years living in Chengdu, I've become somewhat of an expert … I'll be sharing with you …” | “Sichuan hotpot is one of China's most iconic dishes … This guide covers the history, best restaurants, and cultural significance of the dish, based on current food guides and traveler reports.” |
| “I remember one time when I was invited to a local family's home …” | “A hotpot dinner at a local home is a common way the culture is experienced in Chengdu …” |
| “One of my personal favorites is 'Hai Di Lao.'” | “A consistently popular chain is 'Hai Di Lao.'” |
| “I would recommend checking out some of the smaller, hole-in-the-wall restaurants … trust me, it's worth it for the taste.” | “check out some of the smaller, hole-in-the-wall restaurants … regulars say it's worth it for the taste.” |
| “there are a few tips that I would like to share” | “A few practical tips will help you get the most out of a hotpot meal.” |
| “I highly recommend giving Sichuan hotpot a try … Trust me, your taste buds will thank you!” | “Sichuan hotpot is well worth trying … keep a cold drink nearby.” |

保留：全部历史事实（明代起源、重庆码头、花椒/辣椒史）、餐厅介绍、价格、内部链接、FAQ。

---

## 4. 迁移保护清单（逐字节验证）

- [x] URL / slug 未变（3/3）
- [x] canonicalURL 未变（3/3）
- [x] content_id 未变（3/3）
- [x] title front matter 未变（3/3）
- [x] affiliate shortcode / 直链未变（3/3，token 级比对）
- [x] UTM 未变（3/3）
- [x] PersonaGuard PASS（3/3）
- [x] 旧虚构经历语句已全部移除（per-article 声明列表比对）
- [x] H1 + 主要 H2 结构保留（per-article section 检查）

## 5. 预期影响（观察目标，非保证）

| Pilot | 预期指标 | 观察窗口 |
|---|---|---|
| A Western Sichuan | 保持/提升 CTR（当前 3.85%），position 19.31 → 前 15 | 28 天 |
| B Guilin | 保持/提升 CTR（当前 0.0%），position 18.88 → 前 15 | 28 天 |
| C Hotpot | 保持/提升 CTR（当前 0.0%），position 37.18 → 前 30 | 28 天 |

- LOW_DATA_WARNING：28d clicks 整体仅 3 次；单页 clicks 0–1，任何短期波动不得判定成败。
- 若 28 天后无负向变化且 PersonaGuard 持续 PASS，再推进剩余 25 篇。
