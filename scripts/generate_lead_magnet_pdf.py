#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_lead_magnet_pdf.py - 生成《China Visa-Free Entry Checklist》Lead Magnet PDF
====================================================================================

产出：static/lead-magnet/china-visa-free-entry-checklist.pdf

内容为 2.0 Editorial Voice 的实用 checklist（签证免签入境的准备清单），
基于 ChinaBound 站内 144-hour visa-free transit / visa 指南的可靠事实。
所有事实均为通用、谨慎表述，不编造政策细节（标注"以官方最新为准"）。

用法：
  python scripts/generate_lead_magnet_pdf.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (HRFlowable, ListFlowable, ListItem, Paragraph,
                                SimpleDocTemplate, Spacer)

sys.stdout.reconfigure(encoding="utf-8")

SCRIPT_DIR = Path(__file__).resolve().parent
BLOG_ROOT = SCRIPT_DIR.parent
OUT_DIR = BLOG_ROOT / "static" / "lead-magnet"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = OUT_DIR / "china-visa-free-entry-checklist.pdf"

# 尝试注册中文字体（若系统有）；缺失则用内置 Helvetica（英文为主）。
FONT_NAME = "Helvetica"
BOLD_FONT = "Helvetica-Bold"
for cand in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\msyhbd.ttc"):
    pass  # TTC 注册较复杂，本 PDF 以英文为主，使用默认字体

SECTION_TITLE = "China Visa-Free Entry — Pre-Trip Checklist"


def _styles() -> dict:
    base = getSampleStyleSheet()
    title = ParagraphStyle("CTitle", parent=base["Title"], fontSize=20,
                           leading=24, textColor=colors.HexColor("#0f2b46"),
                           spaceAfter=4, spaceBefore=0)
    sub = ParagraphStyle("CSub", parent=base["Italic"], fontSize=10.5,
                         leading=14, textColor=colors.HexColor("#5a6b7b"))
    h2 = ParagraphStyle("CH2", parent=base["Heading2"], fontSize=13,
                        leading=16, textColor=colors.HexColor("#0f2b46"),
                        spaceBefore=10, spaceAfter=4)
    body = ParagraphStyle("CBody", parent=base["BodyText"], fontSize=9.5,
                          leading=13.5, textColor=colors.HexColor("#222222"))
    note = ParagraphStyle("CNote", parent=base["BodyText"], fontSize=8,
                          leading=11, textColor=colors.HexColor("#6b7280"),
                          spaceBefore=6)
    return {"title": title, "sub": sub, "h2": h2, "body": body, "note": note}


SECTIONS = [
    ("1. Confirm Your Eligibility", [
        "Check whether your nationality is on the current visa-free transit list.",
        "Confirm your entry/exit itinerary qualifies (e.g. transit between eligible countries).",
        "Verify the time window (e.g. 144-hour transit) applies to your routing.",
        "Keep your return / onward ticket details ready — many checks ask to see them.",
    ]),
    ("2. Documents to Carry", [
        "Valid passport (6+ months validity recommended, with blank pages).",
        "Onward / return flight confirmation (print or offline copy).",
        "Hotel or accommodation booking confirmation for the transit stay.",
        "A copy of your visa-free transit policy reference in case questions arise.",
    ]),
    ("3. Before You Fly", [
        "Fill in any required pre-departure forms and save offline copies.",
        "Save emergency + embassy contact details on your phone.",
        "Arrange mobile connectivity (eSIM) and a payment method that works in China.",
        "Download offline maps and translation tools.",
    ]),
    ("4. At the Border", [
        "Join the correct lane (Transit / Visa-free) — ask if unsure.",
        "Present passport + onward ticket together when asked.",
        "Answer questions honestly and keep answers short.",
        "Keep the arrival stamp / registration card until you exit.",
    ]),
    ("5. Practical Reminders", [
        "Rules change — always confirm against the latest official notices before travel.",
        "Keep digital and paper backups of every document.",
        "If your plans change, re-check whether your visa-free window still applies.",
    ]),
]


def build_pdf() -> Path:
    st = _styles()
    doc = SimpleDocTemplate(
        str(OUT_FILE), pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
        title="China Visa-Free Entry Checklist",
        author="ChinaBound Travel",
    )
    story = [
        Paragraph(SECTION_TITLE, st["title"]),
        Paragraph("A practical pre-trip checklist for international travelers planning "
                  "a visa-free transit entry to China. Research-based, 2.0 Editorial Voice.",
                  st["sub"]),
        Spacer(1, 6),
        HRFlowable(width="100%", thickness=1.2, color=colors.HexColor("#0f2b46")),
    ]
    for title, items in SECTIONS:
        story.append(Paragraph(title, st["h2"]))
        story.append(ListFlowable(
            [ListItem(Paragraph(f"<b>{i.split('. ', 1)[0]}.</b> "
                                f"{i.split('. ', 1)[1] if '. ' in i else i}", st["body"]))
             for i in items],
            bulletType="bullet",
            start="•",
            leftIndent=10, bulletFontName="Helvetica",
        ))
        story.append(Spacer(1, 4))
    story += [
        Spacer(1, 8),
        HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#cbd5e1")),
        Paragraph("Editorial note: visa-free transit rules and eligibility are updated by "
                  "official authorities and can change without notice. Always verify against "
                  "the latest government / embassy guidance before you travel.", st["note"]),
    ]
    doc.build(story)
    return OUT_FILE


def main() -> int:
    out = build_pdf()
    print(f"Lead Magnet PDF generated: {out} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
