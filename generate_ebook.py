# China Bound Travel Guide 2026 - V1.0
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

N=HexColor("#1a3a5c");B=HexColor("#2d5a8a");A=HexColor("#FF6B35")
G=HexColor("#6b7280");D=HexColor("#1f2937");R=HexColor("#e2e8f0")

def mk():
 d={}
 d["ct"]=ParagraphStyle("ct",fontName="Helvetica-Bold",fontSize=30,textColor=HexColor("#ffffff"),alignment=TA_CENTER,leading=38,spaceAfter=5)
 d["cs"]=ParagraphStyle("cs",fontName="Helvetica",fontSize=12,textColor=HexColor("#a0c4e8"),alignment=TA_CENTER,leading=16)
 d["cm"]=ParagraphStyle("cm",fontName="Helvetica",fontSize=9,textColor=HexColor("#c8dff5"),alignment=TA_CENTER,leading=12)
 d["pt"]=ParagraphStyle("pt",fontName="Helvetica-Bold",fontSize=18,textColor=N,alignment=TA_CENTER,spaceAfter=4)
 d["ps"]=ParagraphStyle("ps",fontName="Helvetica",fontSize=10,textColor=G,alignment=TA_CENTER,spaceAfter=10)
 d["cn"]=ParagraphStyle("cn",fontName="Helvetica-Bold",fontSize=9,textColor=A,spaceBefore=10,spaceAfter=2)
 d["c2"]=ParagraphStyle("c2",fontName="Helvetica-Bold",fontSize=15,textColor=N,spaceAfter=4)
 d["h2"]=ParagraphStyle("h2",fontName="Helvetica-Bold",fontSize=11,textColor=B,spaceBefore=8,spaceAfter=3)
 d["b"]=ParagraphStyle("b",fontName="Helvetica",fontSize=10,textColor=D,leading=15,spaceAfter=5,alignment=TA_JUSTIFY)
 d["bb"]=ParagraphStyle("bb",fontName="Helvetica-Bold",fontSize=10,textColor=D,leading=15,spaceAfter=3)
 d["bl"]=ParagraphStyle("bl",fontName="Helvetica",fontSize=10,textColor=D,leading=14,spaceAfter=3,leftIndent=12,firstLineIndent=-10)
 d["co"]=ParagraphStyle("co",fontName="Helvetica-BoldOblique",fontSize=10,textColor=A,leading=14,spaceAfter=5,leftIndent=10)
 d["tp"]=ParagraphStyle("tp",fontName="Helvetica-Bold",fontSize=11,textColor=N,leading=18,spaceAfter=3,spaceBefore=7)
 d["te"]=ParagraphStyle("te",fontName="Helvetica",fontSize=10,textColor=D,leading=15,spaceAfter=2)
 return d

ST=mk();story=[]

def P(t,s="b"): return Paragraph(t,ST[s])
def SP(h=5): return Spacer(1,h*mm)
def HR(): return HRFlowable(width="100%",thickness=1,color=R,spaceAfter=4,spaceBefore=4)
def PB(): return PageBreak()

def build():
 global story; story=[]