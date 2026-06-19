# China Bound Travel Guide 2026 - Pure Vector Collage Cover
# Zero external images. 100% vector-drawn collage to avoid any wrong landmark photos.

import json, os
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    HRFlowable, Table, TableStyle
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from pypdf import PdfReader, PdfWriter

BASE = "E:/AI/dulizhan/travel-blog"
OUTPUT = BASE + "/static/ebook/china-bound-travel-guide.pdf"
os.makedirs(BASE + "/static/ebook", exist_ok=True)

# ---- COLORS ----
ORANGE = HexColor("#FF6B35")
DARK = HexColor("#1a1a2e")
GRAY = HexColor("#666666")
LIGHT = HexColor("#f5f5f5")
WHITE = HexColor("#ffffff")
CREAM = HexColor("#FDF6E3")

# Block colours for collage blocks
GREATWALL = HexColor("#C4956A")   # warm sandstone
TEMPLE = HexColor("#7A8B82")      # temple grey-green
SHANGHAI = HexColor("#4A6572")    # steel blue
XIAN = HexColor("#B8956A")        # terracotta
PANDA = HexColor("#6B8E6B")       # bamboo green
CITY = HexColor("#8B7355")        # earthy brown

with open(BASE + "/ebook_data.json", "r", encoding="utf-8") as f:
    raw = json.load(f)

meta = raw["meta"]
chapters = raw["chapters"]
appendices = raw.get("appendices", [])

# ---- PAGE SETUP ----
PAGE_W, PAGE_H = A4
MARGIN = 2 * cm

# ---- STYLES ----
styles = {}
styles["title"] = ParagraphStyle("T", fontName="Helvetica-Bold", fontSize=28, textColor=ORANGE, spaceAfter=8, alignment=TA_CENTER)
styles["subtitle"] = ParagraphStyle("S", fontName="Helvetica", fontSize=13, textColor=GRAY, spaceAfter=4, alignment=TA_CENTER)
styles["meta"] = ParagraphStyle("M", fontName="Helvetica", fontSize=9, textColor=GRAY, spaceAfter=20, alignment=TA_CENTER)
styles["cn"] = ParagraphStyle("CN", fontName="Helvetica-Bold", fontSize=9, textColor=ORANGE, spaceBefore=15, spaceAfter=3)
styles["ct"] = ParagraphStyle("CT", fontName="Helvetica-Bold", fontSize=17, textColor=DARK, spaceAfter=10)
styles["sh"] = ParagraphStyle("SH", fontName="Helvetica-Bold", fontSize=11, textColor=DARK, spaceBefore=8, spaceAfter=4)
styles["body"] = ParagraphStyle("BD", fontName="Helvetica", fontSize=10, textColor=DARK, leading=14, spaceAfter=7, alignment=TA_JUSTIFY)
styles["bullet"] = ParagraphStyle("BL", fontName="Helvetica", fontSize=10, textColor=DARK, leading=14, spaceAfter=3, leftIndent=14)
styles["callout"] = ParagraphStyle("CO", fontName="Helvetica-Oblique", fontSize=10, textColor=HexColor("#8B4513"), leading=14, spaceAfter=8, leftIndent=10)
styles["apptitle"] = ParagraphStyle("AT", fontName="Helvetica-Bold", fontSize=14, textColor=ORANGE, spaceAfter=8, spaceBefore=10)


# ============================================================================
# VECTOR DRAWING HELPERS
# ============================================================================

def draw_rounded_rect(c, x, y, w, h, r, fill, stroke=0, strokeColor=None, strokeWidth=1):
    """Draw a rectangle with rounded corners."""
    c.setFillColor(fill)
    if stroke:
        c.setStrokeColor(strokeColor or fill)
        c.setLineWidth(strokeWidth)
    c.roundRect(x, y, w, h, r, fill=1, stroke=stroke)


def draw_great_wall(c, bx, by, bw, bh):
    """Abstract Great Wall: zigzag line across hills."""
    c.setFillColor(GREATWALL)
    c.rect(bx, by, bw, bh, fill=1, stroke=0)
    # Hill shapes
    c.setFillColor(HexColor("#A87B4F"))
    c.setStrokeColor(HexColor("#A87B4F"))
    # Left hill
    path = c.beginPath()
    path.moveTo(bx, by + bh * 0.25)
    path.curveTo(bx + bw * 0.2, by + bh * 0.55, bx + bw * 0.35, by + bh * 0.45, bx + bw * 0.5, by + bh * 0.35)
    path.lineTo(bx + bw * 0.5, by)
    path.lineTo(bx, by)
    c.drawPath(path, fill=1, stroke=0)
    # Right hill
    path2 = c.beginPath()
    path2.moveTo(bx + bw * 0.5, by + bh * 0.35)
    path2.curveTo(bx + bw * 0.65, by + bh * 0.5, bx + bw * 0.8, by + bh * 0.6, bx + bw, by + bh * 0.3)
    path2.lineTo(bx + bw, by)
    path2.lineTo(bx + bw * 0.5, by)
    c.drawPath(path2, fill=1, stroke=0)
    # Wall zigzag
    c.setStrokeColor(HexColor("#E8D5C0"))
    c.setLineWidth(2.5)
    c.setLineCap(1)
    wy = by + bh * 0.42
    seg = bw / 8.0
    for i in range(8):
        x1 = bx + i * seg
        x2 = bx + (i + 1) * seg
        y1 = wy + (3 if i % 2 == 0 else -3)
        y2 = wy + (3 if (i + 1) % 2 == 0 else -3)
        c.line(x1, y1, x2, y2)
        # tower
        if i % 3 == 0:
            c.setFillColor(HexColor("#D4B896"))
            c.rect(x1 - 4, y1 - 4, 8, 12, fill=1, stroke=0)
    # Label
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(bx + bw / 2, by + bh * 0.12, "GREAT WALL")


def draw_temple(c, bx, by, bw, bh):
    """Abstract Temple of Heaven: tiered circles."""
    c.setFillColor(TEMPLE)
    c.rect(bx, by, bw, bh, fill=1, stroke=0)
    cx, cy = bx + bw / 2, by + bh * 0.45
    # Three tiers
    tiers = [
        (bw * 0.28, bh * 0.12, HexColor("#5C4A3A")),
        (bw * 0.22, bh * 0.10, HexColor("#7A6350")),
        (bw * 0.16, bh * 0.08, HexColor("#9A8268")),
    ]
    for tw, th, col in tiers:
        c.setFillColor(col)
        c.ellipse(cx - tw / 2, cy - th / 2, cx + tw / 2, cy + th / 2, fill=1, stroke=0)
        cy += th * 0.7
    # Pillar
    c.setFillColor(HexColor("#4A3A2A"))
    c.rect(cx - 3, by + bh * 0.25, 6, bh * 0.20, fill=1, stroke=0)
    # Base platform
    c.setFillColor(HexColor("#8A7560"))
    c.rect(cx - bw * 0.22, by + bh * 0.18, bw * 0.44, bh * 0.06, fill=1, stroke=0)
    # Label
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(bx + bw / 2, by + bh * 0.07, "TEMPLE OF HEAVEN")


def draw_shanghai(c, bx, by, bw, bh):
    """Abstract Shanghai skyline: vertical bars."""
    c.setFillColor(SHANGHAI)
    c.rect(bx, by, bw, bh, fill=1, stroke=0)
    # Skyline bars
    bars = [
        (0.10, 0.35, HexColor("#6B8FA3")),
        (0.18, 0.55, HexColor("#5A7D90")),
        (0.28, 0.25, HexColor("#7A9EAF")),
        (0.38, 0.60, HexColor("#4A6B7D")),
        (0.50, 0.45, HexColor("#6B8FA3")),
        (0.60, 0.70, HexColor("#3D5A6A")),
        (0.72, 0.40, HexColor("#5A7D90")),
        (0.82, 0.50, HexColor("#7A9EAF")),
        (0.92, 0.30, HexColor("#6B8FA3")),
    ]
    for x_pct, h_pct, col in bars:
        c.setFillColor(col)
        bar_w = bw * 0.06
        bar_h = bh * h_pct
        c.rect(bx + bw * x_pct - bar_w / 2, by + bh * 0.18, bar_w, bar_h, fill=1, stroke=0)
    # River
    c.setFillColor(HexColor("#3A5566"))
    c.rect(bx, by, bw, bh * 0.15, fill=1, stroke=0)
    # Label
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(bx + bw / 2, by + bh * 0.07, "SHANGHAI")


def draw_xian(c, bx, by, bw, bh):
    """Abstract Terracotta Warrior: simple human silhouette."""
    c.setFillColor(XIAN)
    c.rect(bx, by, bw, bh, fill=1, stroke=0)
    # Background subtle pattern
    c.setFillColor(HexColor("#A08055"))
    for i in range(5):
        c.rect(bx + bw * (0.1 + i * 0.18), by + bh * 0.55, bw * 0.08, bh * 0.25, fill=1, stroke=0)
    # Warrior silhouette (abstract)
    cx = bx + bw / 2
    cy = by + bh * 0.45
    # Head
    c.setFillColor(HexColor("#D4B896"))
    c.ellipse(cx - 12, cy + 25, cx + 12, cy + 50, fill=1, stroke=0)
    # Body / armour
    c.setFillColor(HexColor("#C4A87A"))
    path = c.beginPath()
    path.moveTo(cx - 20, cy + 25)
    path.lineTo(cx + 20, cy + 25)
    path.lineTo(cx + 28, cy - 30)
    path.lineTo(cx - 28, cy - 30)
    c.drawPath(path, fill=1, stroke=0)
    # Belt
    c.setFillColor(HexColor("#A08050"))
    c.rect(cx - 22, cy - 5, 44, 6, fill=1, stroke=0)
    # Base
    c.setFillColor(HexColor("#9A7A50"))
    c.rect(cx - 35, cy - 38, 70, 10, fill=1, stroke=0)
    # Label
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(bx + bw / 2, by + bh * 0.07, "XI'AN WARRIORS")


def draw_panda(c, bx, by, bw, bh):
    """Abstract Panda: circles."""
    c.setFillColor(PANDA)
    c.rect(bx, by, bw, bh, fill=1, stroke=0)
    cx, cy = bx + bw / 2, by + bh * 0.50
    # Body (white)
    c.setFillColor(WHITE)
    c.ellipse(cx - 35, cy - 40, cx + 35, cy + 35, fill=1, stroke=0)
    # Ears (black)
    c.setFillColor(DARK)
    c.circle(cx - 22, cy + 32, 10, fill=1, stroke=0)
    c.circle(cx + 22, cy + 32, 10, fill=1, stroke=0)
    # Eye patches (black ovals)
    c.ellipse(cx - 16, cy + 10, cx - 4, cy + 20, fill=1, stroke=0)
    c.ellipse(cx + 4, cy + 10, cx + 16, cy + 20, fill=1, stroke=0)
    # Eyes (white dots)
    c.setFillColor(WHITE)
    c.circle(cx - 10, cy + 15, 3, fill=1, stroke=0)
    c.circle(cx + 10, cy + 15, 3, fill=1, stroke=0)
    # Nose
    c.setFillColor(HexColor("#4A4A4A"))
    c.ellipse(cx - 5, cy + 2, cx + 5, cy + 8, fill=1, stroke=0)
    # Bamboo
    c.setFillColor(HexColor("#4A7A3A"))
    c.setLineWidth(3)
    c.setStrokeColor(HexColor("#4A7A3A"))
    c.line(cx + 30, cy - 20, cx + 45, cy + 10)
    c.setFillColor(HexColor("#5A9A4A"))
    c.ellipse(cx + 42, cy + 8, cx + 50, cy + 14, fill=1, stroke=0)
    c.ellipse(cx + 38, cy - 2, cx + 46, cy + 4, fill=1, stroke=0)
    # Label
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(bx + bw / 2, by + bh * 0.07, "CHENGDU PANDAS")


def draw_city(c, bx, by, bw, bh):
    """Abstract traditional Chinese architecture: roof curves."""
    c.setFillColor(CITY)
    c.rect(bx, by, bw, bh, fill=1, stroke=0)
    cx = bx + bw / 2
    # Roof 1
    c.setFillColor(HexColor("#7A5A3A"))
    path = c.beginPath()
    path.moveTo(cx - bw * 0.30, by + bh * 0.55)
    path.curveTo(cx - bw * 0.15, by + bh * 0.75, cx + bw * 0.15, by + bh * 0.75, cx + bw * 0.30, by + bh * 0.55)
    path.lineTo(cx + bw * 0.25, by + bh * 0.50)
    path.curveTo(cx + bw * 0.10, by + bh * 0.65, cx - bw * 0.10, by + bh * 0.65, cx - bw * 0.25, by + bh * 0.50)
    c.drawPath(path, fill=1, stroke=0)
    # Roof 2 (smaller, behind)
    c.setFillColor(HexColor("#6B4A2A"))
    path2 = c.beginPath()
    path2.moveTo(cx - bw * 0.20, by + bh * 0.45)
    path2.curveTo(cx - bw * 0.10, by + bh * 0.60, cx + bw * 0.10, by + bh * 0.60, cx + bw * 0.20, by + bh * 0.45)
    path2.lineTo(cx + bw * 0.16, by + bh * 0.41)
    path2.curveTo(cx + bw * 0.06, by + bh * 0.53, cx - bw * 0.06, by + bh * 0.53, cx - bw * 0.16, by + bh * 0.41)
    c.drawPath(path2, fill=1, stroke=0)
    # Pillars
    c.setFillColor(HexColor("#5A3A1A"))
    for px in [cx - bw * 0.18, cx - bw * 0.06, cx + bw * 0.06, cx + bw * 0.18]:
        c.rect(px - 3, by + bh * 0.18, 6, bh * 0.35, fill=1, stroke=0)
    # Label
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(bx + bw / 2, by + bh * 0.07, "ANCIENT CHINA")


# ============================================================================
# COVER & BACK COVER DRAWING
# ============================================================================

def draw_cover_page(c: canvas.Canvas, width, height):
    """Draw the vector collage cover."""
    # Background
    c.setFillColor(CREAM)
    c.rect(0, 0, width, height, fill=1, stroke=0)

    # ---- COLLAGE BLOCKS (3 cols x 2 rows) ----
    col_w = width / 3.0
    top_h = height * 0.40
    bot_h = height * 0.28
    gap = 2

    # Top row
    draw_great_wall(c, 0, height - top_h, col_w - gap, top_h)
    draw_temple(c, col_w, height - top_h, col_w - gap, top_h)
    draw_shanghai(c, col_w * 2, height - top_h, col_w, top_h)
    # Bottom row
    draw_xian(c, 0, height - top_h - bot_h, col_w - gap, bot_h - gap)
    draw_panda(c, col_w, height - top_h - bot_h, col_w - gap, bot_h - gap)
    draw_city(c, col_w * 2, height - top_h - bot_h, col_w, bot_h - gap)

    # White borders between blocks
    c.setStrokeColor(WHITE)
    c.setLineWidth(2)
    # vertical dividers
    c.line(col_w - 1, height - top_h - bot_h, col_w - 1, height)
    c.line(col_w * 2 - 1, height - top_h - bot_h, col_w * 2 - 1, height)
    # horizontal divider
    c.line(0, height - top_h, width, height - top_h)

    # ---- TITLE BAND ----
    band_y = height * 0.22
    band_h = height * 0.16
    c.setFillColor(DARK)
    c.setFillAlpha(0.88)
    c.rect(0, band_y, width, band_h, fill=1, stroke=0)
    c.setFillAlpha(1.0)

    # Title text
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 36)
    c.drawCentredString(width / 2, band_y + band_h * 0.52, "China Bound")
    c.drawCentredString(width / 2, band_y + band_h * 0.28, "Travel Guide")

    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(width / 2, band_y + band_h * 0.10, "2026.05  |  Monthly Updates")

    # ---- BOTTOM INFO ----
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(width / 2, height * 0.11, meta.get("author", "Joran"))
    c.setFont("Helvetica", 9)
    c.drawCentredString(width / 2, height * 0.08, meta.get("version", ""))
    c.drawCentredString(width / 2, height * 0.05, "Published monthly on the 1st of every month.")

    # Decorative orange line
    c.setStrokeColor(ORANGE)
    c.setLineWidth(3)
    line_y = height * 0.14
    c.line(width * 0.30, line_y, width * 0.70, line_y)


def draw_back_cover(c: canvas.Canvas, width, height):
    """Back cover with branding."""
    c.setFillColor(CREAM)
    c.rect(0, 0, width, height, fill=1, stroke=0)

    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(width / 2, height * 0.65, "CHINA BOUND")
    c.drawCentredString(width / 2, height * 0.58, "TRAVEL GUIDE 2026")

    c.setStrokeColor(ORANGE)
    c.setLineWidth(2)
    c.line(width * 0.30, height * 0.52, width * 0.70, height * 0.52)

    c.setFont("Helvetica", 10)
    c.drawCentredString(width / 2, height * 0.45, f"Author: {meta.get('author', 'Joran')}")
    c.drawCentredString(width / 2, height * 0.41, "chinaboundtravel.com")
    c.drawCentredString(width / 2, height * 0.37, "joran@chinaboundtravel.com")

    c.drawCentredString(width / 2, height * 0.28, "Published monthly on the 1st of every month.")
    c.drawCentredString(width / 2, height * 0.24, "Next update: June 1, 2026 — Guilin and Yangshuo Guide")

    c.setFillColor(ORANGE)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(width / 2, height * 0.15, "Your Honest Field-Tested Playbook")


# ============================================================================
# CONTENT BUILDING
# ============================================================================

# Build story (TOC + chapters + appendices)
story = []

# ---- TABLE OF CONTENTS ----
story.append(Paragraph("TABLE OF CONTENTS", styles["ct"]))
story.append(HRFlowable(width="100%", thickness=1, color=ORANGE, spaceAfter=10))

toc_items = []
for i, ch in enumerate(chapters):
    pg = str(i + 2)
    label = ch.get("num", "") + "  " + ch.get("title", "")
    toc_items.append([label, pg])

toc_items.append(["", ""])
toc_items.append(["APPENDICES", ""])
for app in appendices:
    toc_items.append(["  " + app.get("num", "") + "  " + app.get("title", ""), ""])

toc_tbl = Table(toc_items, colWidths=[13 * cm, 2 * cm])
toc_tbl.setStyle(TableStyle([
    ("FONTSIZE", (0, 0), (-1, -1), 10),
    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ("TOPPADDING", (0, 0), (-1, -1), 4),
    ("TEXTCOLOR", (0, -4), (-1, -1), ORANGE),
    ("FONTNAME", (0, -4), (-1, -1), "Helvetica-Bold"),
]))
story.append(toc_tbl)
story.append(PageBreak())

# ---- MONTHLY UPDATE SCHEDULE ----
story.append(Paragraph("MONTHLY UPDATE SCHEDULE", styles["ct"]))
story.append(HRFlowable(width="100%", thickness=1, color=ORANGE, spaceAfter=10))
story.append(Paragraph("This guide is updated on the 1st of every month with new city guides, visa changes, and travel tips.", styles["body"]))
story.append(Spacer(1, 0.5 * cm))

sched = [
    ["MONTH", "NEW CONTENT"],
    ["June 2026", "Guilin and Yangshuo Guide"],
    ["July 2026", "Zhangjiajie Guide"],
    ["August 2026", "Yunnan Guide (Dali, Lijiang, Shangri-La)"],
    ["September 2026", "Street Food Deep Dive"],
    ["October 2026", "Great Wall Complete Guide"],
    ["November 2026", "Ancient Towns of Jiangnan"],
    ["December 2026", "Southern China Winter Guide"],
]
tbl = Table(sched, colWidths=[4 * cm, 11 * cm])
tbl.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), ORANGE),
    ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 9),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BACKGROUND", (0, 1), (-1, -1), LIGHT),
    ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#dddddd")),
]))
story.append(tbl)
story.append(PageBreak())

# ---- CHAPTERS ----
for ch in chapters:
    num = ch.get("num", "")
    title = ch.get("title", "")
    sections = ch.get("sections", [])
    is_intro = ch.get("is_intro", False)
    is_conclusion = ch.get("is_conclusion", False)

    story.append(Paragraph(num, styles["cn"]))
    story.append(Paragraph(title, styles["ct"]))

    for sec in sections:
        h = sec.get("h", "")
        body = sec.get("body", "")
        bullets = sec.get("bullets", [])
        callout = sec.get("callout", "")

        if h:
            story.append(Paragraph(h, styles["sh"]))
        if body:
            story.append(Paragraph(body, styles["body"]))
        for b in bullets:
            story.append(Paragraph(b, styles["bullet"]))
        if callout:
            story.append(Paragraph(callout, styles["callout"]))

    if not is_intro and not is_conclusion:
        story.append(PageBreak())

# ---- APPENDICES ----
story.append(PageBreak())
story.append(Paragraph("APPENDICES", styles["ct"]))
story.append(HRFlowable(width="100%", thickness=1, color=ORANGE, spaceAfter=10))

for app in appendices:
    num = app.get("num", "")
    title = app.get("title", "")
    sections = app.get("sections", [])

    story.append(Paragraph(num + ": " + title, styles["apptitle"]))

    for sec in sections:
        h = sec.get("h", "")
        bullets = sec.get("bullets", [])
        if h:
            story.append(Paragraph(h, styles["sh"]))
        for b in bullets:
            story.append(Paragraph(b, styles["bullet"]))

# ---- MERGE COVER + CONTENT + BACK ----

# 1. Build content PDF
content_buf = BytesIO()
content_doc = SimpleDocTemplate(
    content_buf, pagesize=A4,
    rightMargin=MARGIN, leftMargin=MARGIN,
    topMargin=2.5 * cm, bottomMargin=2.5 * cm
)
content_doc.build(story)

# 2. Cover page
cover_buf = BytesIO()
c = canvas.Canvas(cover_buf, pagesize=A4)
draw_cover_page(c, PAGE_W, PAGE_H)
c.showPage()
c.save()

# 3. Back cover page
back_buf = BytesIO()
c2 = canvas.Canvas(back_buf, pagesize=A4)
draw_back_cover(c2, PAGE_W, PAGE_H)
c2.showPage()
c2.save()

# 4. Merge
cover_pdf = PdfReader(cover_buf)
content_pdf = PdfReader(content_buf)
back_pdf = PdfReader(back_buf)

writer = PdfWriter()
writer.add_page(cover_pdf.pages[0])
for page in content_pdf.pages:
    writer.add_page(page)
writer.add_page(back_pdf.pages[0])

with open(OUTPUT, "wb") as f:
    writer.write(f)

# Also copy dated version
dated_output = BASE + "/static/ebook/china-bound-travel-guide-2026-05.pdf"
with open(dated_output, "wb") as f:
    writer.write(f)

size = os.path.getsize(OUTPUT)
print(f"PDF generated: {OUTPUT}")
print(f"Size: {size} bytes ({size/1024:.1f} KB)")
print(f"Pages: {len(writer.pages)}")
