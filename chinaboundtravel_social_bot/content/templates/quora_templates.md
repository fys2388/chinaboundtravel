# ============================================
# Quora Answer Templates
# ============================================
# Style: Authoritative, helpful, drives to blog
# ============================================

TEMPLATES = {
    "visa_question": {
        "question_patterns": [
            "How can I visit China without a visa?",
            "What is China's transit visa?",
            "Is 144-hour visa enough for China?"
        ],
        "answer": """
Based on my 10 years of traveling in China as a foreign resident, here's what actually works:

**China's Visa-Free Options (2026):**

1. **144-Hour Transit Visa-Free**
   - Available at major airports and some train stations
   - Must have confirmed onward ticket
   - Limited to designated cities only

2. **Who qualifies:**
   - US, UK, Canada, Australia, EU citizens + 50+ other countries
   - Must be in transit to a third country

3. **My experience:**
   I've used this multiple times at Shanghai Pudong and Beijing. The process is straightforward:
   - Fill out arrival card
   - Show passport + onward ticket
   - Get stamped for 144 hours

**Key tips:**
- The 144 hours start from your arrival time, not midnight
- You MUST leave China within 144 hours (not 6 days)
- Some cities have 72-hour options too

I wrote a comprehensive guide covering all the cities and current requirements. Feel free to follow me for more China travel tips!
"""
    },

    "payment_question": {
        "question_patterns": [
            "How do foreigners pay in China?",
            "Can I use credit cards in China?",
            "How to use Alipay as a tourist?"
        ],
        "answer": """
After 10 years navigating China's payment systems, here's the real answer:

**Short version: Use mobile payment, not cash.**

China is essentially cashless for most transactions. Here's what works:

**1. Alipay (支付宝)**
- Now accepts foreign credit cards (Visa, Mastercard)
- Setup takes about 10 minutes
- Works at 95% of places

**2. WeChat Pay**
- Also accepts foreign cards now
- Great for splitting bills with Chinese friends

**What doesn't work:**
- Your regular credit cards (unless linked to Alipay/WeChat)
- Most ATMs charge high fees

**Pro tip:** Download the apps BEFORE arriving in China. Getting them set up with a Chinese friend's help is much easier.

I cover the complete setup process in my detailed guide. Follow me for more China travel advice!
"""
    },

    "internet_question": {
        "question_patterns": [
            "How to access internet in China?",
            "Do I need a VPN in China?",
            "Best SIM card for tourists in China?"
        ],
        "answer": """
Let me save you from my first-week-in-China internet nightmare.

**Your internet options in China (2026):**

**1. eSIM (My Recommendation)**
- Get one before you arrive (Airalo works great)
- Immediate activation
- No Chinese phone number needed
- Around $20-30 for 30 days

**2. Local SIM Card**
- Requires Chinese phone number
- Cheaper but more hassle
- Get one at the airport

**3. VPN (Essential for some)**
- Required for Google, Facebook, WhatsApp, etc.
- ExpressVPN, NordVPN work well
- Sometimes slow during peak hours

**What I do:**
eSIM for data + VPN for work = smooth China experience

I wrote a complete guide comparing all options. Follow me for more practical China tips!
"""
    },

    "transport_question": {
        "question_patterns": [
            "How to travel by train in China?",
            "Is China high-speed rail worth it?",
            "How to buy train tickets in China?"
        ],
        "answer": """
Having taken over 200 high-speed rail trips in China, here's the truth:

**China's High-Speed Rail is incredible.**

Why:
- Faster than flying for routes under 800km
- Trains leave/arrive in city centers
- Comfortable seats, clean bathrooms
- WiFi on most trains now

**How to book (English-friendly):**

1. **Trip.com** - Best English interface
2. **12306** - Official Chinese app (has English option)
3. **At the station** - Works but long queues

**Pro tips:**
- Book 3-5 days ahead for popular routes
- F seats = first class, C/D = second class windows
- Bring snacks - train food is... experimental

I cover the complete booking system in my guide. Follow me for more China travel tips!
"""
    },

    "food_question": {
        "question_patterns": [
            "What food to try in China?",
            "How to order food in China without Chinese?",
            "Is street food safe in China?"
        ],
        "answer": """
10 years in China, and the food is still the best part.

**Must-try dishes by region:**

**Sichuan (where I live):**
- Mapo Tofu (麻婆豆腐)
- Spicy Hot Pot (火锅)
- Dan Dan Noodles (担担面)

**Universal favorites:**
- Peking Duck (Beijing)
- Xiao Long Bao (Shanghai)
- Dim Sum (Cantonese)

**How to order without Chinese:**

1. **Use Meituan/Ele.me apps** - They have English now
2. **Point and smile** - Works surprisingly well
3. **Take photos** - Food photos are universal

**Street food safety:**
Stick to busy stalls with fresh turnover. If locals are eating there, you're fine.

I cover regional cuisines and ordering tips in my guide. Follow me for more!
"""
    }
}

# Generic answer template
GENERIC_ANSWER = """
Based on my 10 years of living and traveling in China, here's what works in 2026:

**Key points:**
- {key_point_1}
- {key_point_2}
- {key_point_3}

**My recommendation:**
{recommendation}

I wrote a comprehensive guide on my blog that covers all the details with current 2026 information.

Feel free to follow me for more China travel tips!
"""

# Topic to keywords mapping for Quora
TOPIC_KEYWORDS = {
    "visa": ["visa china", "transit visa", "china travel requirements"],
    "payment": ["alipay foreigners", "wechat pay", "china payment apps"],
    "internet": ["vpn china", "esim china", "internet access china"],
    "transportation": ["china trains", "high speed rail china", "china transportation"],
    "food": ["chinese food", "china cuisine", "food travel china"],
    "city_guide": ["travel china", "china cities", "backpacking china"]
}