#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MailerLite 7-Day Email Sequence Setup — Closed Loop 4 (P2)
============================================================
Creates a 7-day onboarding email sequence for ChinaBound Travel subscribers.

Pipeline:
  1. Verify MailerLite API connectivity (new API: connect.mailerlite.com)
  2. Create/update 7 email campaign templates via API
  3. Attempt to create automation workflow (if API supports it)
  4. If automation creation is not supported via API, generate detailed
     manual setup guide: docs/mailerlite-7day-sequence-setup.md
  5. Record all results to reports/mailerlite-sequence-setup.json

Each email:
  - English content, Joran persona (Californian in Chengdu, film lover, witty)
  - Affiliate recommendations with UTM params
  - Brand color #FF6B35, inline CSS (email-client safe)
  - From: Joran @ ChinaBound <joran@chinaboundtravel.com>

UTM convention: utm_source=email&utm_medium=sequence&utm_campaign=7day_china&utm_content=dayN

Usage:
  python scripts/mailerlite_sequence_setup.py
  python scripts/mailerlite_sequence_setup.py --dry-run
  python scripts/mailerlite_sequence_setup.py --skip-api  # only generate guide
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
DOCS_DIR = PROJECT_ROOT / "docs"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)

SETUP_RESULT_JSON = REPORTS_DIR / "mailerlite-sequence-setup.json"
MANUAL_SETUP_GUIDE = DOCS_DIR / "mailerlite-7day-sequence-setup.md"

MAILERLITE_API_BASE = "https://connect.mailerlite.com/api"
FROM_NAME = "Joran @ ChinaBound"
FROM_EMAIL = "joran@chinaboundtravel.com"
REPLY_TO = "joran@chinaboundtravel.com"
BRAND_COLOR = "#FF6B35"
BRAND_COLOR_DARK = "#e85a2a"

# Affiliate links with UTM (dayN placeholder replaced per email)
AFFILIATE_LINKS = {
    "airalo": "https://www.airalo.com/?utm_source=email&utm_medium=sequence&utm_campaign=7day_china&utm_content=day{day}",
    "safetywing": "https://safetywing.com/nomad-insurance?referenceID=26548976&utm_source=email&utm_medium=sequence&utm_campaign=7day_china&utm_content=day{day}",
    "booking": "https://www.booking.com/index.html?aid=730795&utm_source=email&utm_medium=sequence&utm_campaign=7day_china&utm_content=day{day}",
    "aviasales": "https://www.aviasales.com/?marker=730795&utm_source=email&utm_medium=sequence&utm_campaign=7day_china&utm_content=day{day}",
    "klook": "https://klook.tpo.li/vrPkmS2v?utm_source=email&utm_medium=sequence&utm_campaign=7day_china&utm_content=day{day}",
    "trip": "https://www.trip.com/?utm_source=email&utm_medium=sequence&utm_campaign=7day_china&utm_content=day{day}",
    "vpn": "https://get.affiliatescn.net/aff_c?offer_id=153&aff_id=150687&url_id=613&utm_source=email&utm_medium=sequence&utm_campaign=7day_china&utm_content=day{day}",
}


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
def load_env() -> None:
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
    except Exception:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def get_token() -> str:
    return os.environ.get("MAILERLITE_API_TOKEN", "").strip()


# ---------------------------------------------------------------------------
# Email HTML template builder
# ---------------------------------------------------------------------------
def _email_shell(title: str, body_html: str, day: int) -> str:
    """Wrap email body in brand-consistent HTML shell with inline CSS."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
</head>
<body style="margin:0;padding:0;background-color:#f4f4f5;font-family:Inter,-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:#1f2937;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f4f5;">
<tr><td align="center" style="padding:20px 10px;">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background-color:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">

<!-- Header -->
<tr><td style="background:linear-gradient(135deg,{BRAND_COLOR} 0%,{BRAND_COLOR_DARK} 100%);padding:28px 32px;text-align:center;">
<h1 style="margin:0;color:#ffffff;font-size:24px;font-weight:800;letter-spacing:-0.3px;">ChinaBound Travel</h1>
<p style="margin:6px 0 0;color:rgba(255,255,255,0.85);font-size:13px;">Your 7-Day China Prep Series · Day {day}</p>
</td></tr>

<!-- Body -->
<tr><td style="padding:28px 32px;">
{body_html}
</td></tr>

<!-- Footer -->
<tr><td style="padding:20px 32px;background-color:#f9fafb;border-top:1px solid #e5e7eb;">
<p style="margin:0 0 8px;font-size:12px;color:#6b7280;line-height:1.6;">
<strong style="color:#374151;">— Joran</strong><br>
California-born, Chengdu-based. I watch too many movies and eat too much mapo tofu.<br>
ChinaBound Travel · <a href="https://www.chinaboundtravel.com" style="color:{BRAND_COLOR};text-decoration:underline;">chinaboundtravel.com</a>
</p>
<p style="margin:8px 0 0;font-size:11px;color:#9ca3af;line-height:1.5;">
You're receiving this because you subscribed to ChinaBound Travel.<br>
<a href="{{{{ unsubscribe_url }}}}" style="color:#9ca3af;text-decoration:underline;">Unsubscribe</a> ·
<a href="{{{{ manage_preferences_url }}}}" style="color:#9ca3af;text-decoration:underline;">Manage preferences</a>
</p>
</td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""


def _affiliate_button(url: str, text: str) -> str:
    """Render a brand-colored CTA button for email."""
    return f"""<table role="presentation" cellpadding="0" cellspacing="0" style="margin:16px 0;">
<tr><td align="center" style="border-radius:8px;background-color:{BRAND_COLOR};">
<a href="{url}" style="display:inline-block;padding:12px 28px;color:#ffffff;font-size:15px;font-weight:700;text-decoration:none;border-radius:8px;">{text} →</a>
</td></tr>
</table>"""


def _affiliate_link(url: str, text: str) -> str:
    return f'<a href="{url}" style="color:{BRAND_COLOR};font-weight:600;text-decoration:underline;">{text}</a>'


# ---------------------------------------------------------------------------
# 7 Email definitions
# ---------------------------------------------------------------------------
def build_email_day1() -> Dict[str, str]:
    """Day 1: Welcome + China travel basics + eSIM (Airalo)."""
    day = 1
    airalo = AFFILIATE_LINKS["airalo"].format(day=day)
    body = f"""
<p style="margin:0 0 16px;font-size:16px;line-height:1.7;">Hey {{% if subscriber.fields.name %}}{{{{ subscriber.fields.name }}}}{{% else %}}Traveler{{% endif %}},</p>

<p style="margin:0 0 16px;font-size:15px;line-height:1.7;">
Welcome to the crew. You just took the first step toward a China trip that doesn't involve
panicking at a Beijing airport at 2 AM. I've been there. It's not cinematic.
</p>

<p style="margin:0 0 16px;font-size:15px;line-height:1.7;">
Over the next 7 days I'll send you one focused email per day — the stuff that actually
matters: visa, payment, internet, hotels, transport, and a real itinerary template.
No fluff, no "10,000 years of history" lectures.
</p>

<div style="background-color:#fff7ed;border-left:4px solid {BRAND_COLOR};padding:14px 18px;margin:20px 0;border-radius:0 8px 8px 0;">
<p style="margin:0;font-size:14px;line-height:1.6;color:#9a3412;">
<strong>Today's essential:</strong> Get your phone working in China before you land.
A physical SIM at the airport means paperwork, queues, and a clerk who's seen
"confused foreigner" too many times. An eSIM takes 2 minutes and activates the second
you touch down.
</p>
</div>

<p style="margin:0 0 12px;font-size:15px;line-height:1.7;">
I use <strong>Airalo</strong> for every trip — their China eSIM plans are cheap,
reliable, and you don't need a local address. Grab one before your flight and
you'll be texting your mom from the Great Wall before the tour bus arrives.
</p>

{_affiliate_button(airalo, "Get Your China eSIM on Airalo")}

<p style="margin:20px 0 0;font-size:14px;line-height:1.6;color:#6b7280;">
<strong>Tomorrow:</strong> Visa rules — who needs one, who doesn't, and the
144-hour transit hack that saves you a $150 visa fee.
</p>
"""
    return {
        "day": day,
        "subject": "Welcome to ChinaBound — let's get your phone working first 📱",
        "preview_text": "Your 7-day China prep starts now. First up: eSIM before you land.",
        "name": "7Day-China-Day1-Welcome-eSIM",
        "html": _email_shell("Welcome to ChinaBound", body, day),
    }


def build_email_day2() -> Dict[str, str]:
    """Day 2: Visa guide + Travel Insurance (SafetyWing)."""
    day = 2
    safetywing = AFFILIATE_LINKS["safetywing"].format(day=day)
    body = f"""
<p style="margin:0 0 16px;font-size:16px;line-height:1.7;">Hey Traveler,</p>

<p style="margin:0 0 16px;font-size:15px;line-height:1.7;">
Day 2. Let's talk visas — the thing that can either be a non-issue or a full-on
bureaucracy nightmare, depending on your passport.
</p>

<h3 style="margin:20px 0 10px;font-size:17px;color:#111827;">The Short Version</h3>
<ul style="margin:0 0 16px;padding-left:20px;font-size:14px;line-height:1.8;">
<li><strong>144-hour visa-free transit:</strong> If you're passing through to a third country, you get 6 days visa-free in certain cities. Game changer for stopovers.</li>
<li><strong>15-day visa-free:</strong> Citizens of many countries (France, Germany, Italy, Spain, Malaysia, Thailand, and more) can visit for 15 days without a visa. Check the latest list — it changes often.</li>
<li><strong>Everyone else:</strong> Standard L (tourist) visa. Apply at your nearest Chinese consulate or via an agency. Budget $150–$200.</li>
</ul>

<div style="background-color:#fef2f2;border-left:4px solid #ef4444;padding:14px 18px;margin:20px 0;border-radius:0 8px 8px 0;">
<p style="margin:0;font-size:14px;line-height:1.6;color:#991b1b;">
<strong>Don't skip travel insurance.</strong> China's medical system is excellent
but expensive for foreigners without coverage. A broken ankle in a Beijing
hospital can cost more than your entire flight.
</p>
</div>

<p style="margin:0 0 12px;font-size:15px;line-height:1.7;">
I recommend <strong>SafetyWing Nomad Insurance</strong> — it's built for travelers,
covers China, and costs less than a fancy dinner. You can even buy it after you've
already left home (ask me how I know).
</p>

{_affiliate_button(safetywing, "Get SafetyWing Travel Insurance")}

<p style="margin:20px 0 0;font-size:14px;line-height:1.6;color:#6b7280;">
<strong>Tomorrow:</strong> Paying for stuff — Alipay, WeChat Pay, and why your
credit card will feel useless.
</p>
"""
    return {
        "day": day,
        "subject": "China visa rules 2026 — who's exempt, who's not 🛂",
        "preview_text": "144-hour transit, 15-day visa-free, or full visa? Plus why travel insurance is non-negotiable.",
        "name": "7Day-China-Day2-Visa-Insurance",
        "html": _email_shell("China Visa Guide", body, day),
    }


def build_email_day3() -> Dict[str, str]:
    """Day 3: Payment guide (Alipay/WeChat Pay) + related recs."""
    day = 3
    airalo = AFFILIATE_LINKS["airalo"].format(day=day)
    safetywing = AFFILIATE_LINKS["safetywing"].format(day=day)
    body = f"""
<p style="margin:0 0 16px;font-size:16px;line-height:1.7;">Hey Traveler,</p>

<p style="margin:0 0 16px;font-size:15px;line-height:1.7;">
Day 3. Let's talk money — specifically, how to pay for things in a country
where even the beggars have QR codes.
</p>

<h3 style="margin:20px 0 10px;font-size:17px;color:#111827;">The Two Apps You Need</h3>
<ul style="margin:0 0 16px;padding-left:20px;font-size:14px;line-height:1.8;">
<li><strong>Alipay:</strong> The default. Link your foreign credit card (Visa/Mastercard) and you can scan to pay almost everywhere. Tour Pass feature works for short visits.</li>
<li><strong>WeChat Pay:</strong> Ubiquitous for smaller shops, street food, and tipping your guide. Also links foreign cards now.</li>
</ul>

<div style="background-color:#eff6ff;border-left:4px solid #3b82f6;padding:14px 18px;margin:20px 0;border-radius:0 8px 8px 0;">
<p style="margin:0;font-size:14px;line-height:1.6;color:#1e40af;">
<strong>Pro tip:</strong> Set up both apps <em>before</em> you arrive. You'll need
your passport for verification, and doing it from your hotel WiFi at 3 AM is
a special kind of frustration. Also: cash is still useful for tiny villages
and emergency taxi rides — carry ¥500 in small bills.
</p>
</div>

<h3 style="margin:20px 0 10px;font-size:17px;color:#111827;">What About Cards?</h3>
<p style="margin:0 0 16px;font-size:15px;line-height:1.7;">
Major hotels and some chain restaurants take foreign cards, but assume your
Visa won't work at the noodle shop down the alley. Mobile payment is king.
Set it up, test it with a ¥5 bottle of water at the airport, and you're golden.
</p>

<p style="margin:0 0 12px;font-size:15px;line-height:1.7;">
While you're setting up your phone for China, make sure you've got your eSIM
and insurance sorted — both are easier to buy from home than from a Shanghai
street corner.
</p>

{_affiliate_button(airalo, "Grab eSIM Before You Go")}

<p style="margin:8px 0 0;font-size:14px;line-height:1.6;">
Or {_affiliate_link(safetywing, "check SafetyWing insurance")} if you haven't yet.
</p>

<p style="margin:20px 0 0;font-size:14px;line-height:1.6;color:#6b7280;">
<strong>Tomorrow:</strong> Internet in China — why Google is dead to you, and
the eSIM/VPN combo that actually works.
</p>
"""
    return {
        "day": day,
        "subject": "Paying in China: Alipay, WeChat Pay, and why cash still matters 💳",
        "preview_text": "Set up mobile payment before you land. Here's exactly how.",
        "name": "7Day-China-Day3-Payment",
        "html": _email_shell("Payment in China", body, day),
    }


def build_email_day4() -> Dict[str, str]:
    """Day 4: eSIM/VPN deep dive + Airalo."""
    day = 4
    airalo = AFFILIATE_LINKS["airalo"].format(day=day)
    vpn = AFFILIATE_LINKS["vpn"].format(day=day)
    body = f"""
<p style="margin:0 0 16px;font-size:16px;line-height:1.7;">Hey Traveler,</p>

<p style="margin:0 0 16px;font-size:15px;line-height:1.7;">
Day 4. Let's talk about the Great Firewall — not the tourist one, the digital
one. In China, Google, Instagram, WhatsApp, Gmail, and Netflix are all blocked.
Your phone will feel like it's been sent back to 2005.
</p>

<h3 style="margin:20px 0 10px;font-size:17px;color:#111827;">The Two-Part Fix</h3>

<p style="margin:0 0 12px;font-size:15px;line-height:1.7;">
<strong>1. eSIM for data.</strong> You need a local data connection. Airport
WiFi is unreliable and hotel WiFi often can't handle video calls. An eSIM
gives you 4G/5G everywhere.
</p>
{_affiliate_button(airalo, "Get Airalo China eSIM")}

<p style="margin:16px 0 12px;font-size:15px;line-height:1.7;">
<strong>2. VPN for access.</strong> Even with local data, Google and friends
are blocked. You need a VPN that works in China. Not all do — many get blocked
the moment you cross the border. I use NordVPN; it has obfuscated servers
specifically designed for China.
</p>
{_affiliate_button(vpn, "Get NordVPN for China")}

<div style="background-color:#fff7ed;border-left:4px solid {BRAND_COLOR};padding:14px 18px;margin:20px 0;border-radius:0 8px 8px 0;">
<p style="margin:0;font-size:14px;line-height:1.6;color:#9a3412;">
<strong>Critical:</strong> Install and TEST your VPN before you arrive in China.
Once you're behind the firewall, you can't download a VPN app — the App Store
won't even show it. Set it up at home, connect to a Hong Kong or Japan server,
confirm Google works, then you're ready.
</p>
</div>

<h3 style="margin:20px 0 10px;font-size:17px;color:#111827;">What Actually Works Inside China</h3>
<ul style="margin:0 0 16px;padding-left:20px;font-size:14px;line-height:1.8;">
<li><strong>WeChat:</strong> Your everything app — messaging, payments, maps, mini-programs for subway tickets</li>
<li><strong>Dianping (大众点评):</strong> Like Yelp but actually useful, with restaurant menus and queue systems</li>
<li><strong>Amap (高德地图):</strong> The best navigation app in China, way more accurate than Google Maps here</li>
<li><strong>Apple Music / Spotify (with VPN):</strong> Works fine through VPN</li>
</ul>

<p style="margin:20px 0 0;font-size:14px;line-height:1.6;color:#6b7280;">
<strong>Tomorrow:</strong> Where to stay — from budget capsules to the
"why is this so cheap?" hotel finds.
</p>
"""
    return {
        "day": day,
        "subject": "Internet in China: eSIM + VPN setup that actually works 🌐",
        "preview_text": "Google is blocked. Here's the eSIM+VPN combo I use on every trip.",
        "name": "7Day-China-Day4-eSIM-VPN",
        "html": _email_shell("Internet in China", body, day),
    }


def build_email_day5() -> Dict[str, str]:
    """Day 5: Hotels + Booking."""
    day = 5
    booking = AFFILIATE_LINKS["booking"].format(day=day)
    klook = AFFILIATE_LINKS["klook"].format(day=day)
    body = f"""
<p style="margin:0 0 16px;font-size:16px;line-height:1.7;">Hey Traveler,</p>

<p style="margin:0 0 16px;font-size:15px;line-height:1.7;">
Day 5. Let's find you a bed. China's hotel scene is wild — you can get a
decent private room for $25/night or a 5-star suite for $80. The trick is
knowing where to look and what to avoid.
</p>

<h3 style="margin:20px 0 10px;font-size:17px;color:#111827;">My Booking Strategy</h3>
<ul style="margin:0 0 16px;padding-left:20px;font-size:14px;line-height:1.8;">
<li><strong>Book through Booking.com:</strong> Free cancellation on most rooms, English reviews, and you can filter by "foreigners accepted" (some Chinese hotels only take local ID)</li>
<li><strong>Location > luxury:</strong> Stay near a subway station. A 10-minute walk to the metro beats a fancy hotel that's 45 minutes from everything</li>
<li><strong>Check recent reviews (last 3 months):</strong> Hotels in China change management fast — a 2023 glowing review might describe a completely different place now</li>
<li><strong>Avoid "airport hotels" unless you have a 6 AM flight:</strong> They're usually isolated and overpriced</li>
</ul>

{_affiliate_button(booking, "Search Hotels on Booking.com")}

<div style="background-color:#f0fdf4;border-left:4px solid #22c55e;padding:14px 18px;margin:20px 0;border-radius:0 8px 8px 0;">
<p style="margin:0;font-size:14px;line-height:1.6;color:#166534;">
<strong>Budget hack:</strong> In tier-2 cities (Chengdu, Xi'an, Hangzhou),
4-star hotels regularly go for $35–$50/night. In Beijing and Shanghai, budget
$60–$100 for something decent near the center. Hostels are $10–$15/night
and great for meeting other travelers.
</p>
</div>

<h3 style="margin:20px 0 10px;font-size:17px;color:#111827;">Tours & Activities</h3>
<p style="margin:0 0 16px;font-size:15px;line-height:1.7;">
For guided tours, skip the hotel desk (they mark up 30–50%) and book through
<strong>Klook</strong>. They have English-speaking guides, skip-the-line tickets
for the Forbidden City and Terracotta Warriors, and prices are transparent.
</p>

{_affiliate_button(klook, "Book Tours on Klook")}

<p style="margin:20px 0 0;font-size:14px;line-height:1.6;color:#6b7280;">
<strong>Tomorrow:</strong> Getting around — high-speed rail, domestic flights,
and why the subway is your best friend.
</p>
"""
    return {
        "day": day,
        "subject": "Where to stay in China: hotels that don't suck 🏨",
        "preview_text": "Booking strategy, budget hacks, and the tours platform I actually use.",
        "name": "7Day-China-Day5-Hotels",
        "html": _email_shell("Hotels in China", body, day),
    }


def build_email_day6() -> Dict[str, str]:
    """Day 6: Transportation (high-speed rail/flights) + Aviasales/Trip."""
    day = 6
    aviasales = AFFILIATE_LINKS["aviasales"].format(day=day)
    trip = AFFILIATE_LINKS["trip"].format(day=day)
    body = f"""
<p style="margin:0 0 16px;font-size:16px;line-height:1.7;">Hey Traveler,</p>

<p style="margin:0 0 16px;font-size:15px;line-height:1.7;">
Day 6. Getting around China is either the best part of your trip or the most
stressful, depending on how you plan it. The high-speed rail network is
genuinely incredible — 350 km/h, on time, comfortable, and cheaper than you think.
</p>

<h3 style="margin:20px 0 10px;font-size:17px;color:#111827;">High-Speed Rail (The Star of the Show)</h3>
<ul style="margin:0 0 16px;padding-left:20px;font-size:14px;line-height:1.8;">
<li><strong>Beijing → Shanghai:</strong> 4.5 hours, ~$80 second class. Flights take 2.5 hours but add 3 hours of airport hassle</li>
<li><strong>Beijing → Xi'an:</strong> 4.5 hours, ~$70. Perfect for the Terracotta Warriors day trip</li>
<li><strong>Shanghai → Hangzhou:</strong> 45 minutes, ~$15. Day trip, no brainer</li>
<li>Book through Trip.com app or at the station with your passport. Buy 3–7 days ahead for popular routes</li>
</ul>

<h3 style="margin:20px 0 10px;font-size:17px;color:#111827;">Domestic Flights</h3>
<p style="margin:0 0 16px;font-size:15px;line-height:1.7;">
For long distances (Chengdu → Beijing, Shanghai → Guilin), flights make sense.
Use <strong>Aviasales</strong> to compare prices across Chinese airlines —
they aggregate domestic carriers and often find deals 20–30% cheaper than
booking direct.
</p>

{_affiliate_button(aviasales, "Search Flights on Aviasales")}

<div style="background-color:#eff6ff;border-left:4px solid #3b82f6;padding:14px 18px;margin:20px 0;border-radius:0 8px 8px 0;">
<p style="margin:0;font-size:14px;line-height:1.6;color:#1e40af;">
<strong>Booking everything in one place:</strong> Trip.com (the international
version of Ctrip) handles flights, trains, hotels, and airport transfers in
English. It's the app I open most when I'm on the move in China.
</p>
</div>

{_affiliate_button(trip, "Book Transport on Trip.com")}

<h3 style="margin:20px 0 10px;font-size:17px;color:#111827;">City Transport</h3>
<ul style="margin:0 0 16px;padding-left:20px;font-size:14px;line-height:1.8;">
<li><strong>Subway:</strong> Clean, fast, cheap ($0.50–$1 per ride). Use WeChat or Alipay to scan through gates</li>
<li><strong>Didi (滴滴):</strong> China's Uber. Cheaper and more available. English interface available</li>
<li><strong>Avoid taxis from the airport queue:</strong> They'll try to charge flat rates. Use Didi instead</li>
</ul>

<p style="margin:20px 0 0;font-size:14px;line-height:1.6;color:#6b7280;">
<strong>Tomorrow (final day):</strong> Your 10-day itinerary template —
Beijing, Xi'an, Chengdu, Shanghai — with exact times, costs, and what to skip.
</p>
"""
    return {
        "day": day,
        "subject": "Getting around China: 350km/h trains and cheap flights 🚄",
        "preview_text": "High-speed rail guide, flight comparison, and the apps that make it painless.",
        "name": "7Day-China-Day6-Transport",
        "html": _email_shell("Transportation in China", body, day),
    }


def build_email_day7() -> Dict[str, str]:
    """Day 7: 10-day itinerary + all affiliate summary."""
    day = 7
    airalo = AFFILIATE_LINKS["airalo"].format(day=day)
    safetywing = AFFILIATE_LINKS["safetywing"].format(day=day)
    booking = AFFILIATE_LINKS["booking"].format(day=day)
    aviasales = AFFILIATE_LINKS["aviasales"].format(day=day)
    klook = AFFILIATE_LINKS["klook"].format(day=day)
    vpn = AFFILIATE_LINKS["vpn"].format(day=day)
    body = f"""
<p style="margin:0 0 16px;font-size:16px;line-height:1.7;">Hey Traveler,</p>

<p style="margin:0 0 16px;font-size:15px;line-height:1.7;">
Day 7. The final email. You've got eSIM, visa, payment, internet, hotels,
and transport figured out. Now let me hand you the actual itinerary —
the one I recommend to friends visiting China for the first time.
</p>

<h3 style="margin:20px 0 10px;font-size:17px;color:#111827;">The Classic 10-Day Route</h3>

<div style="background-color:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;padding:16px 20px;margin:16px 0;">
<p style="margin:0 0 8px;font-size:14px;line-height:1.7;"><strong>Days 1–3: Beijing</strong><br>
Forbidden City (book ahead!), Great Wall at Mutianyu (not Badaling),
Summer Palace, Wangfujing food street. Stay near Wangfujing or Qianmen.</p>

<p style="margin:0 0 8px;font-size:14px;line-height:1.7;"><strong>Days 4–5: Xi'an</strong><br>
High-speed train from Beijing (4.5h). Terracotta Warriors (go at opening!),
Muslim Quarter food, City Wall bike ride. One full day is enough.</p>

<p style="margin:0 0 8px;font-size:14px;line-height:1.7;"><strong>Days 6–7: Chengdu</strong><br>
Fly or train from Xi'an. Giant Panda Breeding Center (arrive before 8 AM!),
Jinli Ancient Street, hot pot (obviously), People's Park tea house.</p>

<p style="margin:0;font-size:14px;line-height:1.7;"><strong>Days 8–10: Shanghai</strong><br>
Fly from Chengdu (2.5h). The Bund, Yu Garden, French Concession cafes,
day trip to Hangzhou or Suzhou. End with a Huangpu River cruise.</p>
</div>

<div style="background-color:#fff7ed;border-left:4px solid {BRAND_COLOR};padding:14px 18px;margin:20px 0;border-radius:0 8px 8px 0;">
<p style="margin:0;font-size:14px;line-height:1.6;color:#9a3412;">
<strong>Budget estimate (per person, mid-range):</strong> Flights $800–$1200,
hotels $50–$80/night × 10 = $500–$800, food $20–$40/day = $200–$400,
transport & attractions $300–$500. <strong>Total: ~$2,000–$3,000</strong> for 10 days.
</p>
</div>

<h3 style="margin:20px 0 10px;font-size:17px;color:#111827;">Your Pre-Departure Checklist</h3>
<table role="presentation" cellpadding="4" cellspacing="0" style="width:100%;font-size:13px;">
<tr><td style="padding:4px 0;">☐ eSIM purchased & installed</td><td style="padding:4px 0;">{_affiliate_link(airalo, "Airalo")}</td></tr>
<tr><td style="padding:4px 0;">☐ VPN installed & tested</td><td style="padding:4px 0;">{_affiliate_link(vpn, "NordVPN")}</td></tr>
<tr><td style="padding:4px 0;">☐ Travel insurance active</td><td style="padding:4px 0;">{_affiliate_link(safetywing, "SafetyWing")}</td></tr>
<tr><td style="padding:4px 0;">☐ Hotels booked (free cancel)</td><td style="padding:4px 0;">{_affiliate_link(booking, "Booking.com")}</td></tr>
<tr><td style="padding:4px 0;">☐ Flights & trains booked</td><td style="padding:4px 0;">{_affiliate_link(aviasales, "Aviasales")} / {_affiliate_link(AFFILIATE_LINKS['trip'].format(day=day), "Trip.com")}</td></tr>
<tr><td style="padding:4px 0;">☐ Tours & skip-the-line tickets</td><td style="padding:4px 0;">{_affiliate_link(klook, "Klook")}</td></tr>
<tr><td style="padding:4px 0;">☐ Alipay & WeChat Pay set up</td><td style="padding:4px 0;">(at home, before flight)</td></tr>
<tr><td style="padding:4px 0;">☐ ¥500 cash in small bills</td><td style="padding:4px 0;">(exchange at home bank)</td></tr>
</table>

<p style="margin:24px 0 0;font-size:15px;line-height:1.7;">
That's it. You're ready. If you have questions at any point — before or during
your trip — just reply to this email. I read every one.
</p>

<p style="margin:16px 0 0;font-size:15px;line-height:1.7;">
Now go plan something amazing. China isn't a country you visit — it's a
country that rearranges how you see the world.
</p>

<p style="margin:24px 0 0;font-size:14px;line-height:1.6;color:#6b7280;">
P.S. — Bookmark <a href="https://www.chinaboundtravel.com" style="color:{BRAND_COLOR};text-decoration:underline;">chinaboundtravel.com</a>
for city guides, scam alerts, and updates. And tell your friends — we're growing
the community of travelers who do China right.
</p>
"""
    return {
        "day": day,
        "subject": "Your 10-day China itinerary + final checklist 🗺️",
        "preview_text": "Beijing → Xi'an → Chengdu → Shanghai. Exact days, costs, and what to skip.",
        "name": "7Day-China-Day7-Itinerary-Summary",
        "html": _email_shell("Your China Itinerary", body, day),
    }


def get_all_emails() -> List[Dict[str, str]]:
    return [
        build_email_day1(),
        build_email_day2(),
        build_email_day3(),
        build_email_day4(),
        build_email_day5(),
        build_email_day6(),
        build_email_day7(),
    ]


# ---------------------------------------------------------------------------
# MailerLite API interaction
# ---------------------------------------------------------------------------
def api_request(method: str, endpoint: str, token: str, json_body: Optional[Dict] = None) -> Tuple[int, Any]:
    """Make a MailerLite API request. Returns (status_code, parsed_response)."""
    import requests
    url = f"{MAILERLITE_API_BASE}/{endpoint.lstrip('/')}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    try:
        if method.upper() == "GET":
            r = requests.get(url, headers=headers, timeout=30)
        elif method.upper() == "POST":
            r = requests.post(url, headers=headers, json=json_body, timeout=30)
        elif method.upper() == "PUT":
            r = requests.put(url, headers=headers, json=json_body, timeout=30)
        else:
            return 0, {"error": f"Unsupported method: {method}"}
        try:
            return r.status_code, r.json()
        except Exception:
            return r.status_code, {"raw": r.text[:500]}
    except Exception as e:
        return 0, {"error": str(e)}


def verify_api(token: str) -> Dict[str, Any]:
    """Verify API connectivity by fetching account info / subscriber count."""
    print("   [API] Verifying connectivity...")
    # Try fetching subscribers (lightweight endpoint)
    code, data = api_request("GET", "subscribers?limit=1", token)
    if code == 200:
        total = data.get("meta", {}).get("total", "unknown")
        print(f"   [API] Connected. Total subscribers: {total}")
        return {"connected": True, "subscribers_total": total, "endpoint": "subscribers"}
    # Try account info
    code2, data2 = api_request("GET", "account", token)
    if code2 == 200:
        print(f"   [API] Connected via account endpoint")
        return {"connected": True, "account": data2, "endpoint": "account"}
    print(f"   [API] Connection failed: HTTP {code} — {str(data)[:200]}")
    return {"connected": False, "status_code": code, "error": str(data)[:300]}


def save_email_html(email: Dict[str, str]) -> Path:
    """Save email HTML to a local file for manual import / reference."""
    email_dir = REPORTS_DIR / "email-templates"
    email_dir.mkdir(parents=True, exist_ok=True)
    filepath = email_dir / f"{email['name']}.html"
    filepath.write_text(email["html"], encoding="utf-8")
    return filepath


def create_campaign(token: str, email: Dict[str, str]) -> Dict[str, Any]:
    """Create a campaign (email template) in MailerLite.

    Correct MailerLite API format:
      - top-level from = sender name, from_email = sender email
      - emails[0].from = sender email address, emails[0].from_name = sender name
    """
    payload = {
        "name": email["name"],
        "subject": email["subject"],
        "from": FROM_NAME,
        "from_email": FROM_EMAIL,
        "type": "regular",
        "emails": [
            {
                "subject": email["subject"],
                "from": FROM_EMAIL,        # must be email address
                "from_name": FROM_NAME,    # display name
                "content": email["html"],
            }
        ],
    }
    code, data = api_request("POST", "campaigns", token, payload)
    if code in (200, 201):
        campaign_id = data.get("data", {}).get("id") or data.get("id")
        print(f"   [Campaign] Created: {email['name']} (id={campaign_id})")
        return {"status": "created", "campaign_id": campaign_id, "response": data}
    elif code == 422:
        err_msg = str(data)[:300]
        # Detect specific error types
        is_sender_unverified = "verified" in err_msg.lower() or "sender" in err_msg.lower()
        if is_sender_unverified:
            print(f"   [Campaign] Sender not verified: {FROM_EMAIL} — saving HTML for manual import")
        else:
            print(f"   [Campaign] Create returned 422: {err_msg[:150]}")
        # Try listing campaigns to find existing one
        code2, data2 = api_request("GET", f"campaigns?filter[name]={email['name']}", token)
        existing_id = None
        if code2 == 200:
            for c in data2.get("data", []):
                if c.get("name") == email["name"]:
                    existing_id = c.get("id")
                    break
        if existing_id:
            print(f"   [Campaign] Found existing: {email['name']} (id={existing_id})")
            return {"status": "already_exists", "campaign_id": existing_id, "error": err_msg}
        status = "sender_unverified" if is_sender_unverified else "create_failed"
        return {"status": status, "status_code": code, "error": err_msg, "email": email["name"]}
    else:
        print(f"   [Campaign] Create failed HTTP {code}: {str(data)[:200]}")
        return {"status": "failed", "status_code": code, "error": str(data)[:300], "email": email["name"]}


def try_create_automation(token: str) -> Dict[str, Any]:
    """Attempt to create an automation workflow via API.

    MailerLite's automation API support is limited. We try the endpoint
    and gracefully fall back to manual guide generation.
    """
    print("   [Automation] Attempting API automation creation...")
    # Try listing automations first to see if endpoint exists
    code, data = api_request("GET", "automations", token)
    if code == 200:
        print(f"   [Automation] Endpoint accessible. Existing automations: {len(data.get('data', []))}")
        # Try creating a simple automation
        payload = {
            "name": "7-Day China Onboarding Sequence",
            "enabled": False,
            "trigger": {"type": "subscriber_added", "group": "newsletter"},
        }
        code2, data2 = api_request("POST", "automations", token, payload)
        if code2 in (200, 201):
            auto_id = data2.get("data", {}).get("id") or data2.get("id")
            print(f"   [Automation] Created workflow id={auto_id}")
            return {"status": "created", "automation_id": auto_id, "response": data2}
        else:
            print(f"   [Automation] Create not supported via API (HTTP {code2})")
            return {"status": "api_not_supported", "status_code": code2, "detail": str(data2)[:200]}
    else:
        print(f"   [Automation] Endpoint returned HTTP {code} — automation API likely not available")
        return {"status": "endpoint_unavailable", "status_code": code, "detail": str(data)[:200]}


# ---------------------------------------------------------------------------
# Manual setup guide generation
# ---------------------------------------------------------------------------
def generate_manual_setup_guide(emails: List[Dict[str, str]], automation_result: Dict[str, Any]) -> str:
    """Generate detailed MailerLite dashboard setup guide."""
    lines = [
        "# MailerLite 7-Day Sequence — Manual Setup Guide",
        "",
        "> Generated by `scripts/mailerlite_sequence_setup.py`",
        f"> Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Why Manual Setup?",
        "",
        f"MailerLite's API returned: **{automation_result.get('status', 'unknown')}** "
        f"(HTTP {automation_result.get('status_code', 'N/A')}).",
        "Automation workflows cannot be fully created through the API. The 7 email",
        "templates have been pre-created (or are ready to create), but the workflow",
        "trigger and delays must be configured in the MailerLite dashboard.",
        "",
        "---",
        "",
        "## Step 1: Verify Email Templates Exist",
        "",
        "1. Log in to [MailerLite](https://www.mailerlite.com/login)",
        "2. Go to **Campaigns** → **Drafts** (or **Sent** → **Templates**)",
        "3. You should see these 7 templates:",
        "",
        "| # | Template Name | Subject | Delay |",
        "|---|--------------|---------|-------|",
    ]
    for e in emails:
        delay = "Immediately" if e["day"] == 1 else f"Day {e['day']} (after {e['day']-1} day(s))"
        lines.append(f"| {e['day']} | {e['name']} | {e['subject'][:50]} | {delay} |")

    lines.extend([
        "",
        "If a template is missing, create it manually:",
        "1. **Campaigns** → **Create campaign** → **Regular campaign**",
        "2. Name it exactly as shown above",
        "3. Set From: **Joran @ ChinaBound** <joran@chinaboundtravel.com>",
        "4. Subject: use the subject line from the table",
        "5. Content: use the HTML from the script output (or paste the email body)",
        "",
        "---",
        "",
        "## Step 2: Create the Automation Workflow",
        "",
        "1. Go to **Automations** → **Create workflow** → **Start from scratch**",
        "2. Name: `7-Day China Onboarding Sequence`",
        "",
        "### Trigger",
        "- **When subscriber joins a group**",
        "- Group: `Lead Magnet` (or your main newsletter group)",
        "- This triggers when someone downloads the 7-day itinerary lead magnet",
        "",
        "### Workflow Steps",
        "",
    ])

    for e in emails:
        if e["day"] == 1:
            lines.append(f"**Step {e['day']}: Send email (immediately)**")
        else:
            lines.append(f"**Step {e['day']*2-1}: Wait**")
            lines.append(f"- Delay: {e['day']-1} day(s)")
            lines.append("")
            lines.append(f"**Step {e['day']*2}: Send email**")
        lines.append(f"- Email: `{e['name']}`")
        lines.append(f"- Subject: {e['subject']}")
        lines.append("")

    lines.extend([
        "### Workflow Settings",
        "- **Re-entry**: Allow subscribers to re-enter the workflow (off)",
        "- **Send schedule**: Any time (or 9 AM – 9 PM in subscriber timezone)",
        "- **Goal**: None (this is an onboarding sequence)",
        "",
        "---",
        "",
        "## Step 3: Set Up UTM Tracking Verification",
        "",
        "All affiliate links in the emails already include UTM parameters:",
        "- `utm_source=email`",
        "- `utm_medium=sequence`",
        "- `utm_campaign=7day_china`",
        "- `utm_content=day1` through `day7`",
        "",
        "To verify tracking in GA4:",
        "1. GA4 → **Reports** → **Acquisition** → **Traffic acquisition**",
        "2. Filter by `Session source / medium` = `email / sequence`",
        "3. Check `Session campaign` = `7day_china`",
        "",
        "---",
        "",
        "## Step 4: Test the Sequence",
        "",
        "1. Add a test subscriber to the trigger group (use a secondary email)",
        "2. Verify Day 1 email arrives immediately",
        "3. Check that all affiliate links work and contain UTM params",
        "4. (Optional) Use MailerLite's **Test workflow** feature to skip delays",
        "",
        "---",
        "",
        "## Email Content Reference",
        "",
        "The full HTML for each email is generated by `scripts/mailerlite_sequence_setup.py`.",
        "Run `python scripts/mailerlite_sequence_setup.py --dry-run` to preview all 7 emails.",
        "",
        "### Affiliate Links Used",
        "",
        "| Partner | Product | Day(s) Featured |",
        "|---------|---------|-----------------|",
        "| Airalo | eSIM | 1, 3, 4, 7 |",
        "| SafetyWing | Travel Insurance | 2, 3, 7 |",
        "| Booking.com | Hotels | 5, 7 |",
        "| Klook | Tours & Activities | 5, 7 |",
        "| Aviasales | Flights | 6, 7 |",
        "| Trip.com | Transport/Hotels | 6, 7 |",
        "| NordVPN | VPN | 4, 7 |",
        "",
        "---",
        "",
        f"_Generated: {datetime.now().isoformat()}_",
    ])
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="MailerLite 7-Day Sequence Setup (Closed Loop 4)")
    parser.add_argument("--dry-run", action="store_true", help="Preview emails without API calls")
    parser.add_argument("--skip-api", action="store_true", help="Skip API calls, only generate guide")
    args = parser.parse_args()

    load_env()
    token = get_token()

    print("=" * 70)
    print("  MailerLite 7-Day Sequence Setup — Closed Loop 4")
    print(f"  Mode: {'DRY-RUN' if args.dry_run else 'LIVE'} | Skip API: {args.skip_api}")
    print("=" * 70)

    # Build all 7 emails
    print("\n[1/4] Building 7 email templates...")
    emails = get_all_emails()
    for e in emails:
        print(f"   Day {e['day']}: {e['subject'][:60]}")

    results: Dict[str, Any] = {
        "timestamp": datetime.now().isoformat(),
        "mode": "dry_run" if args.dry_run else "live",
        "emails": [],
        "api_verification": None,
        "automation": None,
        "guide_generated": False,
    }

    # Always save email HTML files locally (for manual import / reference)
    print("\n   Saving email HTML templates locally...")
    html_paths = []
    for e in emails:
        p = save_email_html(e)
        html_paths.append(str(p))
    print(f"   Saved {len(html_paths)} HTML files to reports/email-templates/")

    if args.dry_run or args.skip_api or not token:
        if not token:
            print("\n   ⚠️  MAILERLITE_API_TOKEN not found — running in guide-only mode")
        print("\n[2/4] Skipping API calls (dry-run or no token)")

        # Generate guide regardless
        print("\n[3/4] Generating manual setup guide...")
        automation_result = {"status": "skipped", "status_code": 0, "detail": "Dry-run or no token"}
        guide = generate_manual_setup_guide(emails, automation_result)
        MANUAL_SETUP_GUIDE.write_text(guide, encoding="utf-8")
        results["guide_generated"] = True
        results["automation"] = automation_result
        results["html_files"] = html_paths
        print(f"   Guide written: {MANUAL_SETUP_GUIDE}")

        # Save email previews
        for e in emails:
            results["emails"].append({
                "day": e["day"],
                "name": e["name"],
                "subject": e["subject"],
                "status": "preview_only",
                "html_length": len(e["html"]),
            })

    else:
        # Verify API
        print("\n[2/4] Verifying MailerLite API...")
        api_result = verify_api(token)
        results["api_verification"] = api_result

        if not api_result.get("connected"):
            print("\n   ⚠️  API connection failed — generating guide only")
            automation_result = {"status": "api_connection_failed", "status_code": api_result.get("status_code"),
                                 "detail": api_result.get("error", "")}
            guide = generate_manual_setup_guide(emails, automation_result)
            MANUAL_SETUP_GUIDE.write_text(guide, encoding="utf-8")
            results["guide_generated"] = True
            results["automation"] = automation_result
            results["html_files"] = html_paths
        else:
            # Create campaigns
            print("\n[3/4] Creating email campaigns...")
            sender_unverified = False
            for e in emails:
                result = create_campaign(token, e)
                if result.get("status") == "sender_unverified":
                    sender_unverified = True
                results["emails"].append({
                    "day": e["day"],
                    "name": e["name"],
                    "subject": e["subject"],
                    **result,
                })

            # Try automation
            print("\n[4/4] Attempting automation workflow creation...")
            auto_result = try_create_automation(token)
            results["automation"] = auto_result
            results["html_files"] = html_paths

            # Generate guide if automation not fully created OR sender unverified
            need_guide = auto_result.get("status") not in ("created",) or sender_unverified
            if need_guide:
                reason = []
                if auto_result.get("status") not in ("created",):
                    reason.append(f"automation={auto_result.get('status')}")
                if sender_unverified:
                    reason.append(f"sender {FROM_EMAIL} not verified in MailerLite")
                print(f"\n   Generating manual setup guide ({', '.join(reason)})...")
                guide = generate_manual_setup_guide(emails, auto_result)
                # Append sender verification note
                if sender_unverified:
                    guide += f"""

---

## ⚠️ Action Required: Verify Sender Email

The API could not create campaigns because **{FROM_EMAIL}** is not verified in your MailerLite account.

**To verify:**
1. Log in to [MailerLite](https://www.mailerlite.com/login)
2. Go to **Settings** → **Sending domains** (or **Sender addresses**)
3. Add **{FROM_EMAIL}** and click verify
4. Check the inbox for {FROM_EMAIL} and click the verification link
5. Re-run: `python scripts/mailerlite_sequence_setup.py`

After verification, the 7 campaign templates will be created automatically.
The email HTML files are already saved in `reports/email-templates/` for manual import if needed.
"""
                MANUAL_SETUP_GUIDE.write_text(guide, encoding="utf-8")
                results["guide_generated"] = True
                results["sender_unverified"] = sender_unverified
                print(f"   Guide written: {MANUAL_SETUP_GUIDE}")

    # Save results JSON
    SETUP_RESULT_JSON.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n📋 Setup results: {SETUP_RESULT_JSON}")

    # Summary
    created = sum(1 for e in results["emails"] if e.get("status") == "created")
    failed = sum(1 for e in results["emails"] if e.get("status") in ("failed", "create_failed"))
    sender_unverified = sum(1 for e in results["emails"] if e.get("status") == "sender_unverified")
    preview = sum(1 for e in results["emails"] if e.get("status") == "preview_only")

    print("\n" + "=" * 70)
    print(f"  DONE. Emails: {created} created, {sender_unverified} blocked (sender unverified), {failed} failed, {preview} preview-only")
    print(f"  Automation: {results['automation']['status']}")
    print(f"  Guide: {'generated' if results['guide_generated'] else 'not needed'}")
    print(f"  HTML templates: {len(html_paths)} saved to reports/email-templates/")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
