#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_7day_itinerary_pdf.py - 生成《7-Day China Itinerary Template》Lead Magnet PDF
=====================================================================================

产出：static/ebook/7-day-china-itinerary.pdf

内容为 Beijing → Xi'an → Shanghai 经典 7 天行程模板，含每日安排、
预算表、行前清单和实用贴士。基于站内可靠事实，通用谨慎表述。

用法：
  python scripts/generate_7day_itinerary_pdf.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (HRFlowable, ListFlowable, ListItem, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

sys.stdout.reconfigure(encoding="utf-8")

SCRIPT_DIR = Path(__file__).resolve().parent
BLOG_ROOT = SCRIPT_DIR.parent
OUT_DIR = BLOG_ROOT / "static" / "ebook"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = OUT_DIR / "7-day-china-itinerary.pdf"

BRAND = colors.HexColor("#0f2b46")
ACCENT = colors.HexColor("#3A6EA5")
LIGHT_BG = colors.HexColor("#f0f4f8")
BORDER = colors.HexColor("#cbd5e1")


def _styles() -> dict:
    base = getSampleStyleSheet()
    title = ParagraphStyle("CTitle", parent=base["Title"], fontSize=22,
                           leading=26, textColor=BRAND, spaceAfter=4, spaceBefore=0)
    sub = ParagraphStyle("CSub", parent=base["Italic"], fontSize=10.5,
                         leading=14, textColor=colors.HexColor("#5a6b7b"))
    h2 = ParagraphStyle("CH2", parent=base["Heading2"], fontSize=14,
                        leading=18, textColor=BRAND, spaceBefore=12, spaceAfter=6)
    h3 = ParagraphStyle("CH3", parent=base["Heading3"], fontSize=11.5,
                        leading=15, textColor=ACCENT, spaceBefore=8, spaceAfter=3)
    body = ParagraphStyle("CBody", parent=base["BodyText"], fontSize=9.5,
                          leading=13.5, textColor=colors.HexColor("#222222"))
    note = ParagraphStyle("CNote", parent=base["BodyText"], fontSize=8,
                          leading=11, textColor=colors.HexColor("#6b7280"), spaceBefore=6)
    cell = ParagraphStyle("CCell", parent=base["BodyText"], fontSize=8.5,
                          leading=11.5, textColor=colors.HexColor("#222222"))
    cell_head = ParagraphStyle("CCellHead", parent=base["BodyText"], fontSize=9,
                               leading=12, textColor=colors.white, fontName="Helvetica-Bold")
    return {"title": title, "sub": sub, "h2": h2, "h3": h3,
            "body": body, "note": note, "cell": cell, "cell_head": cell_head}


DAYS = [
    ("Day 1 — Beijing: Temple of Heaven + Wangfujing",
     "Arrive at PEK or PKX. Take subway or Didi to hotel. Morning: Temple of Heaven before 8 AM (watch locals do tai chi). Evening: Wangfujing Street — try candied hawthorn berries."),
    ("Day 2 — Beijing: Forbidden City + Jingshan + Houhai",
     "Enter Forbidden City via Tiananmen Gate (bring passport, allow 3-4 hours). Climb Jingshan Park for the iconic overhead view. Evening: Houhai lakeside — Yanjing beer and local karaoke."),
    ("Day 3 — Beijing: Great Wall (Mutianyu)",
     "Skip Badaling. Mutianyu: 70 km from city, cable car available, less crowded. Book via official site or reputable operator. Avoid 'free ride' solicitors at subway stations."),
    ("Day 4 — Xi'an: Terracotta Army",
     "Take Fuxing Hao high-speed train from Beijing (4.5 hrs, ~$85). Arrive, drop bags near South Gate. Visit Terracotta Army before 9 AM or after 3 PM. Don't miss the bronze chariots."),
    ("Day 5 — Xi'an: City Wall + Big Wild Goose Pagoda + Muslim Quarter",
     "Rent a bike on the ancient City Wall (14 km loop, ~2 hrs, start at South Gate). Afternoon: Big Wild Goose Pagoda. Evening: Muslim Quarter — lamb biangbiang noodles, roujiamo, osmanthus cake."),
    ("Day 6 — Shanghai: The Bund + Nanjing Road + Yu Garden",
     "Fly Xi'an → Shanghai (~2 hrs, $80-120) or take high-speed rail (6 hrs). Morning: The Bund at sunrise. Midday: Nanjing Road pedestrian street. Afternoon: Yu Garden and old streets. Evening: Bund night lights."),
    ("Day 7 — Shanghai: French Concession + Jade Buddha Temple + Departure",
     "Morning walk in the French Concession — tree-lined streets, lane houses, cafes. Jade Buddha Temple (45 min). Depart from PVG (international, allow 3 hrs) or SHA (domestic)."),
]


PRE_TRIP_CHECKLIST = [
    "Valid passport (6+ months validity, blank pages)",
    "China tourist visa (L-visa) OR confirm 144-hour visa-free transit eligibility",
    "Onward / return flight confirmation (print + offline copy)",
    "Hotel booking confirmations for every city",
    "Alipay & WeChat Pay activated before arrival (no Chinese bank needed)",
    "VPN installed and active before arrival (Gmail, Google, WhatsApp blocked)",
    "eSIM or international roaming plan for data",
    "500-1,000 RMB cash for small vendors and temples",
    "Travel insurance covering China",
    "Offline maps (Google Maps won't work; download Maps.me or Baidu)",
]


BUDGET_ROWS = [
    ["Item", "Budget", "Mid-Range", "Comfort"],
    ["Hotel / night (dbl)", "$25-40", "$60-120", "$200+"],
    ["Meals / day", "$10-20", "$25-50", "$80+"],
    ["Transport (7 days)", "$50-80", "$100-150", "$200+"],
    ["Attractions (all)", "$40-60", "$80-120", "$120+"],
    ["Total (7 days)", "$560-840", "$1,050-1,750", "$2,500+"],
]


INSIDER_TIPS = [
    "High-speed rail: Book via 12306 app (English version) or at station counter. Beijing→Xi'an 4.5 hrs.",
    "Payment: Alipay Tour Card and WeChat Pay support foreign cards now. Activate before you land.",
    "Internet: NordVPN or Astrill consistently work. Install and test before arrival — you can't download VPN apps inside China.",
    "Taxis: Use Didi (Chinese Uber) with English interface. Don't flag regular taxis as a first-timer.",
    "Great Wall: Mutianyu for convenience, Jinshanling for wild wall with zero crowds (2.5 hrs each way).",
    "Xi'an food: Eat in the Muslim Quarter, not near the Terracotta Army museum (overpriced and mediocre).",
    "Shanghai: The Bund at sunrise is empty and magical; night lights turn on around 7 PM.",
]


def build_pdf() -> Path:
    st = _styles()
    doc = SimpleDocTemplate(
        str(OUT_FILE), pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
        title="7-Day China Itinerary Template",
        author="ChinaBound Travel",
    )
    story = [
        Paragraph("7-Day China Itinerary Template", st["title"]),
        Paragraph("Beijing → Xi'an → Shanghai — A tested, efficient route for first-time visitors. "
                  "Routes, budget breakdown, pre-trip checklist, and insider tips.", st["sub"]),
        Spacer(1, 6),
        HRFlowable(width="100%", thickness=1.2, color=BRAND),
        Spacer(1, 4),
        Paragraph("The core logic: Fly into Beijing → Train to Xi'an → Fly to Shanghai. "
                  "Three cities, seven days, zero regrets.", st["body"]),
    ]

    # Day-by-day
    story.append(Paragraph("Day-by-Day Breakdown", st["h2"]))
    for day_title, day_desc in DAYS:
        story.append(Paragraph(day_title, st["h3"]))
        story.append(Paragraph(day_desc, st["body"]))

    # Budget table
    story.append(Paragraph("Quick-Reference Budget (per person, 7 days)", st["h2"]))
    table_data = []
    for i, row in enumerate(BUDGET_ROWS):
        style = st["cell_head"] if i == 0 else st["cell"]
        table_data.append([Paragraph(c, style) for c in row])
    tbl = Table(table_data, colWidths=[45 * mm, 35 * mm, 35 * mm, 35 * mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(tbl)
    story.append(Paragraph("Note: Excludes international flights. Prices are 2026 estimates in USD.",
                           st["note"]))

    # Pre-trip checklist
    story.append(Paragraph("Pre-Trip Checklist", st["h2"]))
    story.append(ListFlowable(
        [ListItem(Paragraph(f"☐ {item}", st["body"])) for item in PRE_TRIP_CHECKLIST],
        bulletType="bullet", start="•", leftIndent=10,
        bulletFontName="Helvetica",
    ))

    # Insider tips
    story.append(Paragraph("Insider Tips from Joran", st["h2"]))
    story.append(ListFlowable(
        [ListItem(Paragraph(item, st["body"])) for item in INSIDER_TIPS],
        bulletType="bullet", start="•", leftIndent=10,
        bulletFontName="Helvetica",
    ))

    story += [
        Spacer(1, 10),
        HRFlowable(width="100%", thickness=0.6, color=BORDER),
        Paragraph("Editorial note: This itinerary is a planning template based on research and "
                  "on-the-ground experience. Prices, opening hours, and policies can change. "
                  "Always verify against official sources before travel. "
                  "More guides at chinaboundtravel.com", st["note"]),
        Paragraph("— ChinaBound Travel editorial team", st["note"]),
    ]

    doc.build(story)
    return OUT_FILE


def main() -> int:
    out = build_pdf()
    print(f"7-Day Itinerary PDF generated: {out} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
