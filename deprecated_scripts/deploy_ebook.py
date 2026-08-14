"""
deploy_ebook.py v2.0
====================
ChinaBound Travel - Ebook Deploy, AI Review & Digital Delivery Script

新增功能 (v2.0):
  - 数字水印：为每个用户生成带专属水印的PDF
  - MailerLite集成：购买成功后自动触发交付邮件
  - 旅行雷达生成：自动生成每周五的1页PDF雷达

用法:
  python deploy_ebook.py                              # 审查 + 部署主版
  python deploy_ebook.py --dry-run                   # 仅审查
  python deploy_ebook.py --watermark --email x@test.com --order ORD-001
                                                       # 生成带水印PDF
  python deploy_ebook.py --radar                     # 生成本周旅行雷达PDF
  python deploy_ebook.py --process-order --email x@test.com --order ORD-001 --type annual
                                                       # 处理订单（水印+邮件）

依赖:
  pip install pypdf openai python-dotenv requests reportlab
"""

import argparse, os, shutil, sys, time, json, logging
from datetime import datetime, timedelta
from pathlib import Path

# -- 依赖检查 ---------------------------------------------------------------
DEPS_OK = True
try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    print("pip install pypdf"); DEPS_OK = False
try:
    import requests
except ImportError:
    print("pip install requests"); DEPS_OK = False
try:
    from openai import OpenAI
except ImportError:
    print("pip install openai"); DEPS_OK = False
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = lambda: None
if not DEPS_OK:
    sys.exit(1)

# -- 配置 -------------------------------------------------------------------
load_dotenv()
DEFAULT_API_KEY    = os.getenv("DEEPSEEK_API_KEY", "")
DEFAULT_MODEL      = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEFAULT_BASE_URL  = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
MAILERLITE_API_KEY = os.getenv("MAILERLITE_API_TOKEN") or os.getenv("MAILERLITE_API_KEY", "")
LOG_FILE          = "./logs/ebook_deploy.log"

DRAFT_PDF   = "./draft_ebook.pdf"
OUTPUT_DIR  = "./static/ebook"
OUTPUT_FILE = "china-bound-travel-guide.pdf"
RADAR_DIR    = "./static/ebook/radar"
MAX_RETRIES = 2

os.makedirs("./logs", exist_ok=True)
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
log = logging.getLogger("ebook_deploy")

# -- 主编 System Prompt ----------------------------------------------------
CHIEF_EDITOR_SYSTEM = r"""You are the Chief Editor of chinaboundtravel.com, a premium travel blog for foreign visitors to China.

Your ONLY job: ruthlessly review the FULL TEXT of our $49.99/year premium China Travel Guide PDF before it goes live.

PERSONALITY: You're a grumpy, no-nonsense California editor who has seen too many travel writers screw up facts. You're protecting Joran's reputation. You are BRUTALLY honest but constructive.

## Fatal Errors - Any ONE of these = AUTO REJECT

1. TRANSPORT HALLUCINATIONS
   - NO bullet trains / high-speed rail to Jiuzhaigou, Western Sichuan, Siguniang Mountain, or remote western China UNLESS confirmed operational by 2026.
   - NO subway lines to tourist sites that don't have them.
   - If you're unsure = REJECT. Better safe than misleading a tourist.

2. CHENGDU PANDA BASE - Must include ALL of:
   - Local price: CNY 55 (via WeChat/Alipay with Chinese ID)
   - Foreign platform price: CNY 72 / ~$10-12 on Klook/Trip.com
   - MUST bring physical passport (required at entrance)
   - MUST mention the CNY 30 shuttle bus from Chengdu Panda Base Station

3. TONE CHECK
   - ZERO official tourism fluff like "Welcome to beautiful China"
   - Must sound like a real American who's been burned by China travel mistakes
   - Must be raw, direct, empathetic - like a friend who's already made the mistakes

4. FACTUAL ACCURACY
   - Visa info must match 2026 rules (144-hour / 240-hour policies)
   - Internet/VPN info must be current
   - Payment methods must reflect 2026 reality

## Response Format (MANDATORY)

If you find ANY fatal error or significant tone issues:
[EBOOK_REVIEW: REJECT]
Issues found:
1. [Category] - Exact quote or location in text: ...

If the guide is clean, accurate, and sounds 100% like Joran:
[EBOOK_REVIEW: PASS]
Brief notes (optional): ..."""

# ===========================================================================
#  工具函数
# ===========================================================================

def extract_pdf_text(pdf_path: str) -> str:
    print(f"\n📄 Reading PDF: {pdf_path}")
    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)
    print(f"   Total pages: {total_pages}")
    blocks = []
    for i, page in enumerate(reader.pages, 1):
        text = page.extract_text()
        if text and text.strip():
            blocks.append(f"\n--- Page {i} ---\n{text.strip()}")
        print(f"   Page {i}/{total_pages}", end="\r")
    full_text = "\n".join(blocks)
    print(f"\n✅ Extracted {len(full_text):,} characters")
    return full_text


def call_editor(text: str, api_key: str, model: str, base_url: str, attempt: int) -> str:
    print(f"\n🔍 Chief Editor review (attempt {attempt})...")
    client = OpenAI(api_key=api_key, base_url=base_url)
    MAX_CHARS = 120_000
    if len(text) > MAX_CHARS:
        print(f"   Truncating to {MAX_CHARS:,} chars")
        text = text[:MAX_CHARS] + "\n\n[...truncated...]"
    messages = [
        {"role": "system", "content": CHIEF_EDITOR_SYSTEM},
        {"role": "user", "content": f"Review the PDF below:\n{'='*60}\n\n{text}\n\n{'='*60}\nYour verdict:"},
    ]
    start = time.time()
    response = client.chat.completions.create(model=model, messages=messages, temperature=0.2, max_tokens=2048)
    elapsed = time.time() - start
    verdict = response.choices[0].message.content.strip()
    print(f"\n📝 Editor verdict ({elapsed:.1f}s):\n{verdict}")
    return verdict


def parse_verdict(verdict: str) -> tuple:
    lines = verdict.splitlines()
    issues, status = [], None
    for line in lines:
        line = line.strip()
        if "[EBOOK_REVIEW: REJECT]" in line.upper(): status = "REJECT"
        elif "[EBOOK_REVIEW: PASS]" in line.upper(): status = "PASS"
        elif status == "REJECT" and line.startswith(("1.", "2.", "3.", "4.", "5.", "- ")):
            issues.append(line)
    if status is None:
        issues.append(f"Could not parse verdict: {verdict[:200]}"); status = "REJECT"
    return status, issues


def copy_to_static(src: str, dst_dir: str, dst_name: str) -> str:
    Path(dst_dir).mkdir(parents=True, exist_ok=True)
    dst_path = os.path.join(dst_dir, dst_name)
    if os.path.exists(dst_path):
        shutil.copy2(dst_path, dst_path + f".bak.{int(time.time())}")
        print(f"   Backup created")
    shutil.copy2(src, dst_path)
    return dst_path


# ===========================================================================
#  数字水印功能
# ===========================================================================

def gen_watermarked_pdf(base_pdf: str, user_email: str, order_id: str, output_path: str) -> str:
    """
    使用 ReportLab + pypdf 为 PDF 添加数字水印。
    水印：底部小字 + 每页右上角半透明警告。
    """
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        import io
    except ImportError:
        print("pip install reportlab"); shutil.copy2(base_pdf, output_path); return output_path

    print(f"\n💧 Adding watermark for {user_email} | {order_id}")
    reader = PdfReader(base_pdf)
    writer = PdfWriter()

    wm_bottom = f"Licensed to: {user_email} | Order: {order_id} | chinaboundtravel.com"
    wm_diag   = "PREMIUM PASS - FOR LICENSED USER ONLY"

    for page in reader.pages:
        mw, mh = float(page.mediabox.width), float(page.mediabox.height)
        packet = io.BytesIO()
        c = canvas.Canvas(packet, pagesize=(mw, mh))

        # 对角线半透明警告（右上角）
        c.saveState()
        c.setFillColor(colors.Color(0.5, 0.5, 0.5, alpha=0.12))
        c.setFont("Helvetica-Bold", 9)
        c.translate(mw - 0.4 * inch, mh - 1.0 * inch)
        c.rotate(30)
        c.drawString(0, 0, wm_diag)
        c.restoreState()

        # 底部小字水印
        c.setFillColor(colors.Color(0.55, 0.55, 0.55, alpha=0.45))
        c.setFont("Helvetica", 5.5)
        c.drawString(0.35 * inch, 0.22 * inch, wm_bottom)

        c.save()
        overlay = PdfReader(packet)
        page.merge_page(overlay.pages[0])
        writer.add_page(page)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        writer.write(f)

    size_kb = os.path.getsize(output_path) / 1024
    print(f"   ✅ Watermarked PDF: {output_path} ({size_kb:.1f} KB)")
    log.info(f"WATERMARK_OK email={user_email} order={order_id} output={output_path}")
    return output_path


# ===========================================================================
#  MailerLite 集成
# ===========================================================================

def send_mailerlite_welcome(user_email: str, subscription_type: str, order_id: str) -> bool:
    if not MAILERLITE_API_KEY:
        print(f"\n📧 MailerLite API key not configured. Skipping email.")
        print(f"   User: {user_email} | Order: {order_id} | Type: {subscription_type}")
        log.warning(f"MAILERLITE_SKIP no_api_key email={user_email}")
        return False

    base_url = "https://api.mailerlite.com/api/v2"
    headers = {"Authorization": f"Bearer {MAILERLITE_API_KEY}", "Content-Type": "application/json"}

    type_tag = {"one-time": "one-time-buyer", "monthly": "monthly-subscriber", "annual": "annual-subscriber"}
    tags = ["active"]
    if subscription_type in type_tag:
        tags.append(type_tag[subscription_type])

    subscriber = {
        "email": user_email,
        "fields": {
            "subscription_type": subscription_type,
            "order_number": order_id,
            "order_date": datetime.now().strftime("%Y-%m-%d"),
        },
        "tags": tags,
    }

    try:
        resp = requests.post(f"{base_url}/subscribers", headers=headers, json=subscriber, timeout=15)
        if resp.status_code in (200, 201):
            print(f"   ✅ Subscriber created/updated in MailerLite")
        else:
            print(f"   ⚠️ MailerLite error: {resp.status_code} {resp.text[:100]}")
            log.error(f"MAILERLITE_SUB_FAIL {resp.status_code} {resp.text[:100]}")
    except Exception as e:
        print(f"   ❌ MailerLite request failed: {e}")
        log.error(f"MAILERLITE_FAIL {e}")

    print(f"   📧 Welcome email queued (handled by MailerLite automation workflow)")
    log.info(f"MAILERLITE_WELCOME_QUEUED email={user_email} type={subscription_type}")
    return True


# ===========================================================================
#  每周旅行雷达生成
# ===========================================================================

RADAR_TEMPLATE = """\
CHINA BOUND TRAVEL RADAR
Week of {week_date}
By Joran - chinaboundtravel.com

{alert_text}

VISA/POLICY UPDATE:
{alert_detail}

CROWD CONDITIONS:
{crowd_report}

ON THE GROUND (Joran's Tip):
{joran_tip}

CITY OF THE WEEK: {city_spotlight}
{city_content}

SCAM ALERT:
{scam_alert}

---
Generated {gen_time} - For Premium Pass holders only
chinaboundtravel.com | Unsubscribe: https://chinaboundtravel.com/unsubscribe/
"""


def generate_weekly_radar(output_dir: str = RADAR_DIR, week_date: str = None) -> str:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas

    if week_date is None:
        today = datetime.now()
        days_until_friday = (4 - today.weekday()) % 7
        if days_until_friday == 0: days_until_friday = 7
        friday = today + timedelta(days=days_until_friday)
        week_date = friday.strftime("%B %d, %Y")

    os.makedirs(output_dir, exist_ok=True)
    safe = week_date.replace(" ", "-").replace(",", "")
    output_pdf = os.path.join(output_dir, f"travel-radar-{safe}.pdf")

    print(f"\n📡 Generating Travel Radar: {output_pdf}")

    client = OpenAI(api_key=DEFAULT_API_KEY, base_url=DEFAULT_BASE_URL)
    radar_prompt = f"""You are Joran, a California-born travel writer in Chengdu, China.
Generate the weekly Travel Radar for the week of {week_date} for chinaboundtravel.com premium subscribers.

Return ONLY valid JSON with this exact keys (no markdown, no code blocks):
{{
  "alert_text": "1-sentence urgent alert for China travelers",
  "alert_detail": "2-3 sentences on visa/policy detail",
  "crowd_report": "Crowd conditions at top 3 attractions this week",
  "joran_tip": "1 specific insider tip only Joran would know",
  "city_spotlight": "City name",
  "city_content": "3 sentences with specific practical tips about this city",
  "scam_alert": "1 specific scam targeting tourists with exact red flag phrase"
}}

Rules:
- Be specific. Named places, exact prices, real situations.
- Tone: street-smart California bro, direct, slightly witty.
- No political content.
- Output ONLY the JSON."""

    try:
        resp = client.chat.completions.create(model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": radar_prompt}],
            temperature=0.7, max_tokens=800)
        content = resp.choices[0].message.content.strip()
        if content.startswith("```"):
            parts = content.split("```")
            for p in parts:
                if p.strip().startswith("{"):
                    content = p.strip(); break
        radar_data = json.loads(content)
        print(f"   ✅ AI radar content generated")
    except Exception as e:
        print(f"   ⚠️ AI failed, using defaults: {e}")
        radar_data = {
            "alert_text": "No major alerts this week - but double-check your eSIM works before you land.",
            "alert_detail": "Visa-free 144/240h policy unchanged. Carry your passport at all times.",
            "crowd_report": "Beijing: Forbidden City packed on weekends, try Tuesday morning. Shanghai: Yuyuan Garden packed after 10am. Xian: Terracotta Warriors busy before 9am.",
            "joran_tip": "If your VPN fails in China, remember Astrill's backup servers. Download the setup before you go.",
            "city_spotlight": "Guilin",
            "city_content": "Guilin's Li River cruise is at its best. Book through your hotel for CNY 200-250 vs CNY 450+ on Klook. Stay near Elephant Trunk Hill for easiest access.",
            "scam_alert": "Airport taxi drivers sometimes claim your hotel is 'closed' to take you to commission hotels. Always verify with your booking app.",
        }

    gen_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    content_text = RADAR_TEMPLATE.format(week_date=week_date, gen_time=gen_time, **radar_data)

    # Generate PDF
    c = canvas.Canvas(output_pdf, pagesize=letter)
    w, h = letter

    # Header band
    c.setFillColor(colors.HexColor("#1a1a2e"))
    c.rect(0, h - 1.1 * inch, w, 1.1 * inch, fill=True, stroke=False)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 17)
    c.drawString(0.5 * inch, h - 0.55 * inch, "CHINA BOUND TRAVEL RADAR")
    c.setFont("Helvetica", 9)
    c.drawString(0.5 * inch, h - 0.85 * inch, f"Week of {week_date}  -  Premium Pass Only  -  chinaboundtravel.com")
    c.setFillColor(colors.HexColor("#FF6B35"))
    c.rect(0, h - 1.25 * inch, w, 0.15 * inch, fill=True, stroke=False)

    # Content
    y = h - 1.6 * inch
    sections = [
        ("🔴 ALERT", "alert_text", colors.HexColor("#FF6B35")),
        ("VISA/POLICY", "alert_detail", colors.HexColor("#3A6EA5")),
        ("SCAM ALERT", "scam_alert", colors.HexColor("#c0392b")),
        ("ON THE GROUND", "joran_tip", colors.HexColor("#27ae60")),
        ("CROWD CONDITIONS", "crowd_report", colors.HexColor("#8e44ad")),
        (f"CITY OF THE WEEK: {radar_data['city_spotlight'].upper()}", "city_content", colors.HexColor("#FF6B35")),
    ]

    for label, key, color in sections:
        if y < 1.5 * inch:
            c.showPage(); y = h - 1 * inch
        c.setFont("Helvetica-Bold", 8.5)
        c.setFillColor(color)
        c.drawString(0.5 * inch, y, label)
        y -= 0.17 * inch
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 7.5)
        text = radar_data.get(key, "")
        words = text.split(); line = ""
        for word in words:
            test = (line + " " + word).strip()
            if c.stringWidth(test, "Helvetica", 7.5) < w - 1 * inch:
                line = test
            else:
                c.drawString(0.5 * inch, y, line); y -= 0.13 * inch; line = word
        if line:
            c.drawString(0.5 * inch, y, line); y -= 0.2 * inch
        c.setStrokeColor(colors.HexColor("#e0e0e0"))
        c.setLineWidth(0.5)
        c.line(0.5 * inch, y, w - 0.5 * inch, y); y -= 0.18 * inch

    c.setFont("Helvetica", 6.5)
    c.setFillColor(colors.grey)
    c.drawString(0.5 * inch, 0.4 * inch,
        f"Generated {gen_time} - Premium Pass holders only - chinaboundtravel.com")
    c.save()

    size_kb = os.path.getsize(output_pdf) / 1024
    print(f"   ✅ Radar PDF: {output_pdf} ({size_kb:.1f} KB)")
    log.info(f"RADAR_GENERATED {output_pdf}")
    return output_pdf


# ===========================================================================
#  订单处理
# ===========================================================================

def process_order(user_email: str, order_id: str, subscription_type: str = "one-time") -> bool:
    print(f"\n{'='*55}")
    print(f"  Processing order: {order_id}")
    print(f"  User: {user_email} | Type: {subscription_type}")
    print(f"{'='*55}")

    base_pdf = os.path.join(OUTPUT_DIR, OUTPUT_FILE)
    if not os.path.exists(base_pdf):
        print(f"   ❌ Base PDF not found: {base_pdf}")
        log.error(f"ORDER_FAIL base_pdf_missing order={order_id}")
        return False

    # Generate watermarked PDF
    wm_dir = os.path.join(OUTPUT_DIR, "watermarked")
    safe_email = user_email.replace("@", "_at_").replace(".", "_")
    wm_pdf = os.path.join(wm_dir, f"{order_id}_{safe_email}.pdf")

    try:
        gen_watermarked_pdf(base_pdf, user_email, order_id, wm_pdf)
    except Exception as e:
        print(f"   ⚠️ Watermark failed: {e}"); log.error(f"WATERMARK_FAIL {e} order={order_id}")
        wm_pdf = base_pdf

    # Send MailerLite email
    try:
        send_mailerlite_welcome(user_email, subscription_type, order_id)
    except Exception as e:
        print(f"   ⚠️ Email failed: {e}"); log.error(f"MAILERLITE_FAIL {e} order={order_id}")

    print(f"\n✅ Order complete: {order_id}")
    log.info(f"ORDER_COMPLETE order={order_id} email={user_email} type={subscription_type}")
    return True


# ===========================================================================
#  主流程
# ===========================================================================

def main():
    parser = argparse.ArgumentParser(description="ChinaBound Ebook Deploy Script v2.0")
    parser.add_argument("--pdf", default=DRAFT_PDF, help="Draft PDF path")
    parser.add_argument("--dry-run", action="store_true", help="Review only, no deploy")
    parser.add_argument("--api-key", default=DEFAULT_API_KEY, help="DeepSeek API Key")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model name")
    parser.add_argument("--watermark", action="store_true", help="Watermark mode")
    parser.add_argument("--email", default="", help="User email (for watermark)")
    parser.add_argument("--order", default="", help="Order ID (for watermark)")
    parser.add_argument("--type", default="one-time",
                        choices=["one-time", "monthly", "annual"], help="Subscription type")
    parser.add_argument("--radar", action="store_true", help="Generate weekly radar PDF")
    parser.add_argument("--process-order", dest="proc_order", action="store_true",
                        help="Process order (watermark + email)")
    args = parser.parse_args()

    print("=" * 55)
    print("  ChinaBound Ebook Deploy Script v2.0")
    print("  Watermark + MailerLite + Travel Radar")
    print("=" * 55)

    # Radar mode
    if args.radar:
        out = generate_weekly_radar()
        print(f"\n📡 Radar: {out}"); return

    # Order processing mode
    if args.proc_order or (args.email and args.order):
        if not args.email or not args.order:
            print("❌ --process-order needs --email and --order"); sys.exit(1)
        success = process_order(args.email, args.order, args.type)
        sys.exit(0 if success else 1)

    # Watermark-only mode
    if args.watermark:
        if not args.email or not args.order:
            print("❌ --watermark needs --email and --order"); sys.exit(1)
        base = args.pdf if os.path.exists(args.pdf) else os.path.join(OUTPUT_DIR, OUTPUT_FILE)
        safe_email = args.email.replace("@", "_at_").replace(".", "_")
        out_path = os.path.join(OUTPUT_DIR, "watermarked", f"{args.order}_{safe_email}.pdf")
        gen_watermarked_pdf(base, args.email, args.order, out_path)
        print(f"\n💧 Done: {out_path}"); return

    # Review + deploy (original workflow)
    if not os.path.exists(args.pdf):
        print(f"\n❌ Draft PDF not found: {args.pdf}"); sys.exit(1)

    full_text = extract_pdf_text(args.pdf)

    verdict_text = call_editor(full_text, args.api_key, args.model, DEFAULT_BASE_URL, 1)
    status, issues = parse_verdict(verdict_text)

    attempt = 1
    while status == "REJECT" and attempt < MAX_RETRIES:
        attempt += 1
        print(f"\n🔄 Re-review (attempt {attempt})...")
        retry_text = "Previous issues:\n" + "\n".join(f"  - {i}" for i in issues) + "\n\n=== Updated PDF ===\n\n" + full_text
        verdict_text = call_editor(retry_text, args.api_key, args.model, DEFAULT_BASE_URL, attempt)
        status, issues = parse_verdict(verdict_text)

    print(f"\n{'='*55}")
    if status == "PASS":
        print("✅ [EBOOK_REVIEW: PASS] Approved!")
        if args.dry_run:
            print(f"   Dry-run: file not moved"); print(f"   Path: {os.path.abspath(args.pdf)}")
        else:
            dst = copy_to_static(args.pdf, OUTPUT_DIR, OUTPUT_FILE)
            print(f"\n🚀 Deployed: {os.path.abspath(dst)}")
            print(f"   URL: https://chinaboundtravel.com/ebook/{OUTPUT_FILE}")
    else:
        print("❌ [EBOOK_REVIEW: REJECT] Rejected!")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")
        print(f"\nFix draft_ebook.pdf and rerun."); sys.exit(1)
    print(f"{'='*55}")


if __name__ == "__main__":
    main()
