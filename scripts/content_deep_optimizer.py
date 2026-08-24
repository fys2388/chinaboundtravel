#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
content_deep_optimizer.py - Top 核心文章深度优化引擎
======================================================

任务3b：对 Top10 核心文章做深度优化：
  1. 扩充内容至 2000 字以上（确定性规则补充，不编造事实）。
  2. 补充长尾关键词（title 与 description）。
  3. 增加 3-5 条相关内链（基于全站文章库，按主题相关度匹配）。
  4. 优化标题与 meta 描述。

设计原则：
  - 确定性、可测试：不调用 LLM，内容补充基于文章已有结构（headings）、
    可靠的通用旅行信息模板（谨慎表述），避免编造具体政策/价格/开放时间。
  - 内链从全站 posts 构建候选池，按主题关键词重叠匹配相关文章。
  - --dry-run 默认，--apply 写文件。
  - 保留 front matter 与原始换行（统一 LF）。

用法：
  python scripts/content_deep_optimizer.py --dry-run
  python scripts/content_deep_optimizer.py --apply [--files a.md b.md]
  python scripts/content_deep_optimizer.py --apply --all
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

SCRIPT_DIR = Path(__file__).resolve().parent
BLOG_ROOT = SCRIPT_DIR.parent
POSTS_DIR = BLOG_ROOT / "content" / "posts"
REPORTS_DIR = BLOG_ROOT / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

MIN_WORDS = 2000
MIN_INTERNAL_LINKS = 3

# 默认优化清单（Top10 核心文章，按 slug 或文件名）
DEFAULT_FILES = [
    "144-hour-visa-free-transit-guide.md",
    "2026-06-02-ultimate-guide-to-china-visa-for-tourists.md",
    "2026-05-22-how-to-use-wechat-pay-as-a-foreigner.md",
    "alipay-for-foreigners-guide.md",
    "2026-05-25-china-high-speed-rail-how-to-book-tickets.md",
    "2026-07-16-china-transportation-complete-guide-trains-subways-taxis-and-more.md",
    "2026-07-13-navigating-china-with-confidence-a-californians-guide-to-travel-safety.md",
    "2026-08-09-china-packing-list-2026-what-to-bring-and-what-to-leave-at-home.md",
    "2026-08-01-china-photography-guide-capturing-the-wonders-of-the-middle-kingdom.md",
    "internet-connection-china-esim-vpn-guide.md",
]

# 长尾关键词补强（每类主题给 title 追加的长尾）
LONGTAIL_TITLE = {
    "visa": "2026 China Visa & 144-Hour Visa-Free Transit Explained",
    "payment": "Foreigners Payment Setup",
    "transport": "Booking & Logistics",
    "safety": "2026 Safety Guide for International Travelers",
    "packing": "2026 Packing Essentials for International Travelers",
}


# ------------------------------------------------------------
# 文章解析
# ------------------------------------------------------------

def split_fm(text: str):
    for delim in ("---", "+++"):
        ed = re.escape(delim)
        m = re.match(r"^%s\s*\n(.*?)\n%s\s*\n" % (ed, ed), text, re.DOTALL)
        if m:
            return m.group(1), text[m.end():], delim
    return None, text, ""


def read_fm_scalar(fm: str, key: str) -> str:
    m = re.search(rf'^{key}\s*[=:]\s*["\']?([^"\'\n#]+)', fm, re.MULTILINE)
    return m.group(1).strip().strip('"').strip("'") if m else ""


def read_fm_array(fm: str, key: str) -> list:
    m = re.search(rf'^{key}\s*[=:]\s*\[(.*?)\]', fm, re.MULTILINE | re.DOTALL)
    if m:
        return [x.strip().strip('"').strip("'") for x in m.group(1).split(",") if x.strip()]
    return []


def word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z]+", text))


def count_internal_links(body: str) -> int:
    return len(re.findall(r"\[[^\]]+\]\((/posts/[^)#]+)", body))


# ------------------------------------------------------------
# 内链候选池
# ------------------------------------------------------------

class LinkPool:
    def __init__(self):
        self.posts = []  # {file, slug, title, keywords}

    def build(self):
        for p in POSTS_DIR.glob("*.md"):
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            fm, body, _ = split_fm(text)
            title = read_fm_scalar(fm or "", "title")
            # 跳过 redirect 文章：canonicalURL 指向与自身 slug 不同的路径
            # （这类文章是别名页，不应作为内链目标）
            canon = read_fm_scalar(fm or "", "canonicalURL")
            slug = p.stem
            m = re.match(r"^\d{4}-\d{2}-\d{2}-(.*)$", slug)
            clean = m.group(1) if m else slug
            if canon and f"/posts/{clean}/" not in canon:
                continue
            keywords = " ".join(re.findall(r"[A-Za-z]+", (title + " " + body[:1500]).lower()))
            self.posts.append({
                "file": p.name, "slug": slug, "title": title, "keywords": keywords,
            })

    def suggest(self, target_text: str, exclude_files: set, limit: int = 5) -> list:
        """按主题关键词重叠为文章推荐内链。"""
        tkw = set(re.findall(r"[A-Za-z]{4,}", target_text.lower()))
        scored = []
        for post in self.posts:
            if post["file"] in exclude_files:
                continue
            pkw = set(re.findall(r"[A-Za-z]{4,}", post["keywords"]))
            overlap = len(tkw & pkw)
            if overlap >= 2:
                scored.append((post, overlap))
        scored.sort(key=lambda x: -x[1])
        return [s[0] for s in scored[:limit]]


def post_url(slug: str) -> str:
    # slug 可能是带日期前缀的文件名，去掉日期前缀
    m = re.match(r"^\d{4}-\d{2}-\d{2}-(.*)$", slug)
    clean = m.group(1) if m else slug
    return f"/posts/{clean}/"


# ------------------------------------------------------------
# 内容补充（确定性，不编造事实）
# ------------------------------------------------------------

# 可靠通用补充内容（谨慎表述，2.0 Editorial Voice；每节含实用要点，可追加多节）
GENERIC_SECTIONS = {
    "visa": [
        ("### Understanding Your Entry Options\n\n"
         "International visitors have a few ways to enter China, and the right choice "
         "depends on your nationality, itinerary, and trip length. Visa-free transit "
         "windows let eligible travelers pass through for a limited period, while a "
         "standard tourist visa suits longer stays. Before booking, confirm the latest "
         "rules against official government sources — windows, eligible ports, and "
         "documentation can change without notice.\n\n"
         "Key documents to keep accessible: a valid passport, an onward or return "
         "ticket, and accommodation confirmation. Store digital backups and a printed "
         "copy in case your phone battery runs out."),
        ("### What to Expect at the Border\n\n"
         "Entry procedures are generally straightforward, but small preparation helps. "
         "Join the correct lane, present your passport and onward ticket together when "
         "asked, and keep answers brief and accurate. Travelers who transit between "
         "eligible countries typically follow a defined corridor; if your plans shift, "
         "re-check whether your visa-free window still applies.\n\n"
         "Keep the arrival stamp or registration card until you leave. If you have any "
         "doubts about your documents, ask a border officer before proceeding."),
        ("### Practical Preparation Checklist\n\n"
         "- Confirm eligibility and time window against official sources.\n"
         "- Carry passport, onward ticket, and accommodation booking.\n"
         "- Save offline copies of all documents.\n"
         "- Arrange mobile connectivity and a working payment method.\n"
         "- Re-verify any fast-changing rules shortly before departure."),
        ("### Common Questions for First-Time Visitors\n\n"
         "First-time visitors often ask how far in advance to apply, whether transit "
         "counts as an entry, and what happens if their plans change. The practical "
         "answer depends on your route and nationality. Where possible, apply or "
         "confirm your eligibility before booking flights, and keep a copy of the "
         "relevant policy reference on hand.\n\n"
         "If your itinerary is flexible, weighing a visa-free transit against a "
         "standard visa based on trip length can save both time and cost."),
        ("### Planning Around Your Documents\n\n"
         "Your passport should be valid well beyond your intended stay, with blank "
         "pages for stamps. Keep the documents you'll need at the border together — "
         "passport, onward ticket, accommodation — and consider a travel document "
         "wallet to keep them organized and protected."),
    ],
    "payment": [
        ("### Setting Up Mobile Payment\n\n"
         "Mobile payment is central to daily life in China, and setting it up before you "
         "arrive saves time on the ground. The main practical steps involve a verified "
         "account and a linked payment method — commonly a foreign card via a tourist "
         "wallet or a local bank card. Each option has different limits and steps, so "
         "choosing one that matches your trip length is worthwhile.\n\n"
         "Test the app while you still have home connectivity, and keep a backup "
         "payment method in case of card or network issues."),
        ("### Common Issues and Fixes\n\n"
         "- Linking a foreign card may require identity verification — allow time.\n"
         "- Some merchants prefer one app over another; having both major apps helps.\n"
         "- Connectivity hiccups can block payments; keep a little cash as a fallback.\n"
         "- Set limits and monitor transactions for peace of mind.\n"
         "- Update the app before travel to avoid forced updates on arrival."),
        ("### Using Payments Safely\n\n"
         "Mobile payment is convenient, but a few habits reduce risk. Use the official "
         "app, keep your device locked, and avoid sharing verification codes. If a "
         "transaction fails, verify your network and card before retrying. For "
         "higher-value purchases, confirm the amount before confirming payment."),
        ("### Preparing Before You Land\n\n"
         "The smoother your payment setup before arrival, the less friction you'll "
         "face. Set up the app, link a card, and test a small transaction while you "
         "still have home connectivity. Note your linked card's limits and any "
         "verification requirements so they don't surprise you mid-trip.\n\n"
         "Keep a physical card and some cash as backups in case the app or network "
         "is unavailable."),
        ("### Where Mobile Payment Works Best\n\n"
         "Mobile payment is widely accepted across restaurants, shops, and transport "
         "in China's cities. Smaller vendors and street markets may rely on QR-based "
         "payment, so having a working app covers most daily needs. For services that "
         "require in-person verification or special setup, a local contact or your "
         "accommodation can often help."),
        ("### Keeping Transactions Traceable\n\n"
         "Using the official app gives you a clear transaction history, which helps "
         "with budgeting and any disputes. Check statements periodically, set "
         "transaction alerts if available, and keep receipts for larger purchases. "
         "If something looks unfamiliar, contact the service's support promptly."),
    ],
    "transport": [
        ("### Booking Trains in Advance\n\n"
         "China's high-speed rail network is extensive, and booking ahead is wise for "
         "popular routes and peak holiday periods. Tickets can be booked through "
         "official platforms or travel agencies, and seat classes range from second "
         "class to business. Keep your booking reference and passport ready — you'll "
         "need them at the station.\n\n"
         "Arrive early, as stations are large and boarding gates can be far from the "
         "entrance."),
        ("### Navigating Metro and Stations\n\n"
         "Subway systems in major cities are clean, frequent, and signposted in both "
         "Chinese and English at major stops. Buy a single-journey ticket or use a "
         "transport card. At stations, follow the platform signs, and allow extra time "
         "for security checks and transfers.\n\n"
         "Downloading an offline map and checking the last-train time for your route is "
         "a sensible precaution."),
        ("### Planning Your Route\n\n"
         "- Choose transport based on distance: high-speed rail for mid-range, metro "
         "for within-city, and flights for long-distance routes.\n"
         "- Book long-distance rail and flights in advance during holidays.\n"
         "- Allow buffer time at airports and stations.\n"
         "- Have your booking reference and ID ready for checks."),
        ("### Understanding Seat Classes\n\n"
         "High-speed trains typically offer a range of seat classes that differ in "
         "legroom, recline, and price. Second class is the most economical and common, "
         "while first class and business offer more comfort on longer journeys. "
         "Choosing based on trip length helps balance cost and comfort.\n\n"
         "On overnight sleeper trains, berth classes vary; booking early is "
         "recommended for popular routes."),
        ("### Getting to and From Stations\n\n"
         "Major stations are well connected by metro, buses, and taxis. Allow extra "
         "time to navigate large stations, find your platform, and pass security. "
         "Checking your departure gate and any last-minute platform changes on the "
         "station screens is a sensible habit.\n\n"
         "For airport transfers, pre-booking a registered ride or using the metro "
         "often saves both time and money."),
        ("### Practical Tips for Smooth Travel\n\n"
         "- Confirm train times the day before, as schedules can shift.\n"
         "- Keep your booking reference and passport easily accessible.\n"
         "- Board early on busy routes to settle in comfortably.\n"
         "- Download offline maps for station navigation.\n"
         "- Carry a small amount of cash for smaller vendors."),
    ],
    "safety": [
        ("### Staying Aware on the Ground\n\n"
         "As in any destination, awareness of your surroundings goes a long way. Keep "
         "valuables secure, avoid displaying large amounts of cash, and be cautious "
         "with strangers who approach with unsolicited offers. Official advice and "
         "local signage are the most reliable references for current guidance.\n\n"
         "Save emergency numbers and your embassy's contact details in your phone."),
        ("### Protecting Your Documents\n\n"
         "Carry a copy of your passport and visa rather than the originals when "
         "possible. Store the originals in a safe place, and keep digital backups in "
         "your email or cloud. If documents are lost, contact your embassy and the "
         "local authorities promptly.\n\n"
         "Avoid sharing passport details or verification codes with third parties."),
        ("### Practical Safety Habits\n\n"
         "- Stay in well-reviewed accommodation and note emergency exits.\n"
         "- Use registered taxis or ride-hailing apps for late travel.\n"
         "- Keep a portable charger and offline maps.\n"
         "- Trust official guidance over unsolicited advice."),
    ],
    "packing": [
        ("### Building a Practical Packing List\n\n"
         "A good China packing list balances practicality with season and itinerary. "
         "Universal essentials include a universal adapter, a power bank, comfortable "
         "walking shoes, and weather-appropriate layers. Carry only what you can "
         "manage easily, since you'll move between cities and use public transport.\n\n"
         "If your trip involves multiple climate zones, check the forecast for each "
         "destination."),
        ("### What to Bring and What to Leave\n\n"
         "- Bring: adapter, power bank, comfortable shoes, essential medications.\n"
         "- Bring: a VPN and eSIM setup if you need familiar web services.\n"
         "- Leave: bulky electronics and items easily bought on arrival.\n"
         "- Consider: a reusable water bottle and a small daypack.\n"
         "- Check: airline baggage limits before you fly."),
        ("### Final Pre-Departure Checks\n\n"
         "Confirm your documents, confirm your payment setup works, and check whether "
         "your hotel can assist with common needs. Share your itinerary with someone "
         "you trust, and note your embassy's contact details. A little preparation "
         "before departure makes the first days in China much smoother."),
    ],
}

# ------------------------------------------------------------
# 处理单篇
# ------------------------------------------------------------

def append_content(body: str, section_key: str, target_min: int = MIN_WORDS,
                   max_sections: int = 12) -> tuple:
    """若字数不足，追加可靠补充章节直到接近目标。返回 (new_body, added_count)."""
    if word_count(body) >= target_min:
        return body, 0
    sections = GENERIC_SECTIONS.get(section_key, GENERIC_SECTIONS["visa"])
    added = 0
    for section in sections:
        if word_count(body) >= target_min or added >= max_sections:
            break
        h3 = section.split("\n", 1)[0].strip()
        if h3 in body:
            continue
        body = body.rstrip() + "\n\n---\n\n" + section + "\n"
        added += 1
    return body, added

def process_one(path: Path, pool: LinkPool, apply: bool = False) -> dict:
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="ignore")
    bom = ""
    if text.startswith("\ufeff"):
        bom = "\ufeff"
        text = text[1:]
    fm, body, delim = split_fm(text)
    if fm is None:
        return {"file": path.name, "status": "no_fm", "changes": 0}

    title = read_fm_scalar(fm, "title")
    desc = read_fm_scalar(fm, "description")
    changes = 0
    report = {"file": path.name, "words_before": word_count(text),
              "links_before": count_internal_links(body)}

    new_fm = fm
    # 主题判定：优先用标题，再辅以正文开头（精确关键词）
    tl = (title + " " + body[:800]).lower()
    if any(k in tl for k in ["alipay", "wechat", "mobile payment", "payment", "qr code", "paypal"]):
        section_key = "payment"
    elif any(k in tl for k in ["train", "high-speed", "subway", "metro", "transport", "taxi", "airport"]):
        section_key = "transport"
    elif any(k in tl for k in ["visa", "visa-free", "transit", "144-hour", "entry", "immigration"]):
        section_key = "visa"
    elif any(k in tl for k in ["safe", "safety", "scam", "crime"]):
        section_key = "safety"
    elif any(k in tl for k in ["packing", "what to bring", "pack"]):
        section_key = "packing"
    else:
        section_key = "visa"
    # 1) 标题长尾词（仅当字数不足 2000 时追加，避免对长文加无谓后缀）
    if word_count(text) < MIN_WORDS and section_key in LONGTAIL_TITLE \
            and LONGTAIL_TITLE[section_key] not in title:
        new_title = title.rstrip().rstrip(".") + " — " + LONGTAIL_TITLE[section_key]
        new_fm = re.sub(rf'^title\s*[=:]\s*.*$', f'title = "{new_title}"' if delim == "+++" else f'title: "{new_title}"',
                        new_fm, count=1, flags=re.MULTILINE)
        changes += 1

    # 2) description 补长尾（若过短 <50 字）
    if len(desc) < 50:
        new_desc = (title + ". " + "Practical, research-based guidance for international travelers planning a China trip in 2026.").strip()
        new_fm = re.sub(rf'^description\s*[=:]\s*.*$',
                        f'description = "{new_desc}"' if delim == "+++" else f'description: "{new_desc}"',
                        new_fm, count=1, flags=re.MULTILINE)
        changes += 1

    # 3) 内链补充
    current_links = count_internal_links(body)
    if current_links < MIN_INTERNAL_LINKS:
        suggestions = pool.suggest(title + " " + body[:1500],
                                   exclude_files={path.name}, limit=MIN_INTERNAL_LINKS + 2)
        need = MIN_INTERNAL_LINKS - current_links
        added_links = []
        for s in suggestions[:need]:
            link_text = s["title"].split("(")[0].strip()[:60] or "related guide"
            body = body + f"\n\nRelated: [{link_text}]({post_url(s['slug'])})"
            added_links.append(s["slug"])
        if added_links:
            changes += 1

    # 4) 内容扩充
    body, appended = append_content(body, section_key)
    if appended:
        changes += 1

    if changes and apply:
        new_text = bom + delim + "\n" + new_fm + "\n" + delim + "\n" + body
        path.write_text(new_text, encoding="utf-8")

    final_words = word_count(bom + delim + "\n" + new_fm + "\n" + delim + "\n" + body)
    report.update({
        "status": "updated" if changes else "ok",
        "changes": changes,
        "words_after": final_words,
        "reached_2000": final_words >= MIN_WORDS,
        "links_after": count_internal_links(body),
        "new_title": read_fm_scalar(new_fm, "title"),
        "section_key": section_key,
    })
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Top 核心文章深度优化")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--files", nargs="*", default=None)
    ap.add_argument("--all", action="store_true", help="优化全部 60 篇")
    args = ap.parse_args(argv)

    pool = LinkPool()
    pool.build()

    if args.files:
        targets = [POSTS_DIR / f for f in args.files]
    elif args.all:
        targets = sorted(POSTS_DIR.glob("*.md"))
    else:
        targets = [POSTS_DIR / f for f in DEFAULT_FILES if (POSTS_DIR / f).exists()]

    results = []
    for t in targets:
        if t.exists():
            results.append(process_one(t, pool, apply=args.apply))

    print(f"深度优化（{'APPLY' if args.apply else 'DRY-RUN'}）:")
    for r in results:
        mark = "✅" if r.get("changes") else "➡️"
        reached = "✓2000+" if r.get("reached_2000") else "!!<2000"
        print(f"  {mark} {r['file'][:45]:47s} words {r['words_before']}→{r['words_after']} "
              f"{reached:8s} links {r['links_before']}→{r['links_after']} "
              f"section={r.get('section_key','?')}")

    # 报告
    out = REPORTS_DIR / "content_deep_optimize_report.json"
    out.write_text(json.dumps({"mode": "apply" if args.apply else "dry_run",
                               "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  报告: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
