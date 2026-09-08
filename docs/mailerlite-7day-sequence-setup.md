# MailerLite 7-Day China Onboarding Sequence 配置指南

> Automation ID: 198035712694552205
> 配置时间: 2026-09-08

## 一、触发器配置

1. 进入 Automation 编辑页面
2. 选择触发器：**Joins group(s)**
3. 选择组：**chinaboundtravel** (ID: 188150880190596249)
4. 点击 **Save**

## 二、工作流步骤配置

按以下顺序添加节点（共 13 个节点）：

```
Trigger: Joins group(s) → chinaboundtravel
    ↓
Step 1: Email — Day 1: Welcome to ChinaBound Travel
    ↓ Wait 1 day
Step 2: Email — Day 2: China Visa Guide
    ↓ Wait 1 day
Step 3: Email — Day 3: Payments in China
    ↓ Wait 1 day
Step 4: Email — Day 4: eSIM & Internet in China
    ↓ Wait 1 day
Step 5: Email — Day 5: Where to Stay in China
    ↓ Wait 1 day
Step 6: Email — Day 6: Getting Around China
    ↓ Wait 1 day
Step 7: Email — Day 7: Your 10-Day China Itinerary
```

## 三、邮件内容模板

### Day 1: Welcome to ChinaBound Travel

**Subject:** Welcome! Your China travel journey starts here 🇨🇳

**From:** Joran at ChinaBound Travel

**Body:**

```
Hi there,

Thanks for subscribing to ChinaBound Travel! You're now part of a community of travelers who want to experience China the right way.

Over the next 7 days, I'll send you practical guides covering everything you need for a smooth trip:

📅 Day 1: Today — Welcome & basics
📅 Day 2: Visa requirements (critical!)
📅 Day 3: Mobile payments (Alipay & WeChat Pay)
📅 Day 4: eSIM & internet access
📅 Day 5: Hotel recommendations
📅 Day 6: Transportation (high-speed rail & flights)
📅 Day 7: Your complete 10-day itinerary

First, the most important tip for first-time visitors:

👉 Download Alipay and WeChat Pay BEFORE you arrive. Most places in China don't accept cash or foreign credit cards anymore. Set up your account with your passport and international card while you're still home — it'll save you hours of frustration.

Need an eSIM for data? I recommend Airalo — they have affordable China data plans that work the moment you land:
https://buffer-worker.chinaboundtravel.com/s/airalo-email-day1

(utm_source=email&utm_medium=sequence&utm_campaign=7day_china&utm_content=day1)

More tomorrow — your visa guide is coming next!

Safe travels,
Joran
ChinaBound Travel
https://www.chinaboundtravel.com
```

---

### Day 2: China Visa Guide

**Subject:** Day 2: Do you need a visa for China? (2026 update)

**Body:**

```
Hi there,

Let's tackle the biggest question most travelers have: Do you need a visa for China?

The answer depends on your passport. Here's the 2026 update:

✅ Visa-Free Entry (up to 30 days):
- France, Germany, Italy, Spain, Netherlands, Belgium, Luxembourg, Switzerland, Ireland, Hungary, Austria, Greece, and more EU countries
- Malaysia, Singapore, Brunei, Thailand, Japan, South Korea (for certain stays)

✅ 144-Hour Transit Visa-Free:
- Most nationalities can stay up to 6 days in specific regions if transiting through
- Perfect for a quick stopover in Beijing, Shanghai, or Guangzhou

⚠️ Need a Full Visa:
- US, UK, Canadian, Australian, and many other passports still require a pre-arranged visa
- Process takes 3-7 business days through a visa agency

👉 Read our complete visa guide with country-by-country requirements:
https://www.chinaboundtravel.com/posts/china-visa-free-entry-2026-complete-guide-countries-rules-tips/

If you need travel insurance for your trip (many embassies require it for visa applications), I recommend SafetyWing — affordable coverage designed for travelers:
https://buffer-worker.chinaboundtravel.com/s/safetywing-email-day2

(utm_source=email&utm_medium=sequence&utm_campaign=7day_china&utm_content=day2)

Tomorrow: How to pay for everything in China (cash is dead!)

— Joran
```

---

### Day 3: Payments in China

**Subject:** Day 3: Cash is dead in China — here's how to pay

**Body:**

```
Hi there,

If you take one thing away from this email series, let it be this:

CASH IS LARGELY USELESS IN MODERN CHINA.

I've seen travelers arrive with $500 in cash and struggle to buy a bottle of water because the vendor only accepts mobile payment. Here's what you need to know:

📱 The Two Apps You Need:
1. Alipay (支付宝) — owned by Alibaba, accepted everywhere
2. WeChat Pay (微信支付) — owned by Tencent, also accepted everywhere

✅ Setup Before You Arrive:
- Download Alipay and WeChat on your phone
- Sign up with your passport number
- Link your international credit card (Visa/Mastercard work now!)
- Verify your identity — this can take 1-2 days

💡 Pro Tip:
- Alipay has a "Tour Card" feature specifically for foreign visitors
- You can top it up with your foreign card and use it like a local
- No Chinese bank account needed!

👉 Complete guide to Alipay vs WeChat Pay for foreigners:
https://www.chinaboundtravel.com/posts/alipay-vs-wechat-pay-which-is-better-for-tourists/

Need to book flights within China? Trip.com has the best inventory for domestic flights and trains:
https://buffer-worker.chinaboundtravel.com/s/tripcom-email-day3

(utm_source=email&utm_medium=sequence&utm_campaign=7day_china&utm_content=day3)

Tomorrow: Staying connected — eSIM, VPN, and internet in China

— Joran
```

---

### Day 4: eSIM & Internet in China

**Subject:** Day 4: How to stay online in China (and access Google!)

**Body:**

```
Hi there,

Let's talk about something that causes more stress than it should: internet access in China.

The reality:
❌ Google, Gmail, YouTube, Instagram, Facebook, WhatsApp — all blocked
❌ Your hotel WiFi might be slow or restricted
✅ But with the right setup, you can stay connected just like home

📶 Step 1: Get an eSIM for data
- Airalo has China data plans starting at ~$15 for 10GB
- Activate before you land, and you'll have data the moment you turn on your phone
- No physical SIM card needed — install the eSIM profile in 2 minutes

👉 Get your China eSIM:
https://buffer-worker.chinaboundtravel.com/s/airalo-email-day4

🔓 Step 2: Use a VPN for blocked sites
- You'll need a VPN to access Google, Gmail, social media, etc.
- NordVPN works reliably in China (they have obfuscated servers specifically for this)
- Install and test BEFORE you arrive — VPN websites are also blocked in China

👉 Get NordVPN (works in China):
https://buffer-worker.chinaboundtravel.com/s/nordvpn-email-day4

💡 Pro Tips:
- Download all your maps (Google Maps offline) before arrival
- Save important documents to your phone (you might not be able to access Gmail)
- WeChat works without VPN — use it for messaging, payments, and translations

👉 Complete guide to internet & eSIM in China:
https://www.chinaboundtravel.com/posts/best-esim-for-china-travel-comparison/

Tomorrow: Where to stay — from budget hostels to luxury hotels

— Joran
```

---

### Day 5: Where to Stay in China

**Subject:** Day 5: Where to stay in China (my top recommendations)

**Body:**

```
Hi there,

Accommodation in China is generally excellent value — you can get a 4-star hotel for $50-80/night in most cities. Here's what I recommend:

🏙️ By City:

Beijing:
- Budget: Downtown Beijing Youth Hostel (clean, central, ~$15/night)
- Mid-range: Holiday Inn Express Beijing (4-star, ~$60/night)
- Luxury: The Peninsula Beijing (5-star, ~$200/night)

Shanghai:
- Budget: The People Square hostel area (great location)
- Mid-range: Radisson Blu Hotel Shanghai (4-star, ~$70/night)
- Luxury: The Bund waterfront hotels (iconic views, ~$250/night)

Chengdu:
- Budget: Sim's Cozy Garden Hostel (famous backpacker spot)
- Mid-range: Citadines Chengdu (apartment hotel, ~$50/night)
- Luxury: The Ritz-Carlton Chengdu (~$150/night)

Xi'an:
- Budget: Han Tang House Hostel (near the Muslim Quarter)
- Mid-range: Grand Mercure Xi'an (~$55/night)
- Luxury: Sofitel Legend People's Grand Hotel (~$180/night)

👉 Book on Booking.com — they have the best cancellation policies and most inventory:
https://buffer-worker.chinaboundtravel.com/s/booking-email-day5

(utm_source=email&utm_medium=sequence&utm_campaign=7day_china&utm_content=day5)

💡 Pro Tips:
- Book hotels near subway stations — Beijing and Shanghai have excellent metro systems
- Chinese hotels require passport check-in at the front desk
- Some budget hostels don't accept foreigners — check before booking
- Breakfast is usually included in mid-range and luxury hotels

👉 Read our complete city guides with hotel recommendations:
https://www.chinaboundtravel.com/posts/

Tomorrow: Getting around — high-speed trains, domestic flights, and more

— Joran
```

---

### Day 6: Getting Around China

**Subject:** Day 6: How to get around China (high-speed rail is amazing!)

**Body:**

```
Hi there,

China has the best transportation infrastructure I've ever experienced — and it's incredibly affordable. Here's your guide:

🚄 High-Speed Rail (My #1 Recommendation):
- China has 40,000+ km of high-speed rail (more than the rest of the world combined)
- Trains reach 350 km/h (217 mph) — Beijing to Shanghai in 4.5 hours!
- Prices: ~$50-80 for second class, ~$100-150 for first class
- Book in advance — popular routes sell out
- Use Trip.com to book train tickets with your passport

👉 Book high-speed train tickets:
https://buffer-worker.chinaboundtravel.com/s/tripcom-train-email-day6

✈️ Domestic Flights:
- For long distances (e.g., Beijing to Chengdu = 3 hours by plane vs 10 hours by train)
- Airlines: Air China, China Eastern, China Southern, Hainan Airlines
- Prices: $50-150 for most domestic routes
- Book on Trip.com or Aviasales for best prices

👉 Compare flight prices:
https://buffer-worker.chinaboundtravel.com/s/aviasales-email-day6

🚇 City Transportation:
- Metro: Beijing (27 lines!), Shanghai (20 lines), Guangzhou, Chengdu, Xi'an — all have excellent subway systems
- Taxi/Didi: Didi is the Chinese Uber — download the app, pay with Alipay
- Bus: Cheap but confusing for non-Chinese speakers
- Bike sharing: Mobike/Ofo — scan and ride everywhere

💡 Pro Tips:
- Always carry your passport — needed for train tickets and hotel check-in
- Buy train tickets 7-14 days in advance for popular routes
- High-speed trains have power outlets and free WiFi (sometimes)
- Avoid traveling during Chinese holidays (Spring Festival, National Day) — everything is packed

👉 Complete guide to China high-speed rail:
https://www.chinaboundtravel.com/posts/china-high-speed-rail-guide-booking-tips-routes/

Tomorrow (final day): Your complete 10-day China itinerary — the big payoff!

— Joran
```

---

### Day 7: Your 10-Day China Itinerary

**Subject:** 🎉 Day 7: Your complete 10-day China itinerary (the big payoff!)

**Body:**

```
Hi there,

Congratulations — you've made it through the 7-day preparation series! Now for the big payoff: your complete 10-day China itinerary.

This itinerary covers the classics: Beijing, Xi'an, Chengdu, and Shanghai. It's designed for first-time visitors who want to see the highlights without rushing.

📅 Day 1-3: Beijing (3 days)
- Day 1: Tiananmen Square → Forbidden City → Jingshan Park (sunset views)
- Day 2: Great Wall (Mutianyu section — less crowded) → Summer Palace
- Day 3: Temple of Heaven → Hutong walking tour → Peking duck dinner

📅 Day 4: Beijing → Xi'an (high-speed train, 4.5 hours)
- Afternoon: Xi'an City Wall (rent a bike!) → Muslim Quarter (street food dinner)

📅 Day 5: Xi'an
- Morning: Terracotta Warriors (half day, go early!)
- Afternoon: Big Wild Goose Pagoda → Tang Dynasty show

📅 Day 6: Xi'an → Chengdu (flight, 1.5 hours OR train, 3.5 hours)
- Afternoon: People's Park → tea house → Sichuan hotpot dinner

📅 Day 7: Chengdu
- Morning: Chengdu Panda Base (GO BEFORE 8 AM — pandas sleep after that!)
- Afternoon: Jinli Ancient Street → Wuhou Shrine

📅 Day 8: Chengdu → Shanghai (flight, 3 hours)
- Afternoon: The Bund (waterfront walk) → Yu Garden → Nanjing Road

📅 Day 9: Shanghai
- Morning: Shanghai Museum → Former French Concession (walking tour)
- Afternoon: Shanghai Tower observation deck → Tianzifang (art district)
- Evening: Huangpu River cruise

📅 Day 10: Departure
- Last-minute shopping → airport

💰 Estimated Budget (per person, mid-range):
- Flights (international): $500-1000
- Internal transport: $200-300
- Accommodation: $500-700 (10 nights)
- Food: $200-300
- Attractions: $150-200
- Total: $1550-2500

👉 All the detailed guides for each city:
https://www.chinaboundtravel.com/posts/

🎁 Bonus: Save this email — it's your complete travel checklist!

Need anything else? Just reply to this email — I read every message.

Safe travels and enjoy China!

— Joran
ChinaBound Travel
https://www.chinaboundtravel.com

P.S. If you found this series helpful, tell a friend who's planning a China trip!
```

## 四、UTM 参数说明

所有 Affiliate 链接使用统一 UTM 格式：
```
utm_source=email&utm_medium=sequence&utm_campaign=7day_china&utm_content=day{N}
```

短链接已通过 Worker 短链接服务生成，保留完整 UTM 参数。

## 五、激活 Automation

1. 确认所有 13 个节点配置完成
2. 点击右上角 **Activate** 按钮
3. 确认激活（Automation 状态变为 "On"）
4. 测试：用真实邮箱订阅 Lead Magnet，验证是否收到 Day 1 邮件

## 六、监控指标

- 订阅→打开率：目标 > 40%
- 打开→点击率：目标 > 10%
- 点击→Affiliate 转化：目标 > 2%
- 退订率：< 2%

每周四 email-growth-loop.yml workflow 会自动生成 Email 营销效果报告。
