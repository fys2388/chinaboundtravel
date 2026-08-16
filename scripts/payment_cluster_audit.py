"""P1-GROWTH-21A: Payment cluster existing asset audit.

Deterministic, no network. Scans content/posts for payment-related keywords,
joins per-page GSC data from CONTENT_SEO_INVENTORY.csv (cached) and writes
reports/revenue/PAYMENT_CLUSTER_INVENTORY.csv.
"""
import csv
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "reports/revenue/PAYMENT_CLUSTER_INVENTORY.csv"
POSTS_DIR = REPO / "content/posts"
SEO_INVENTORY = REPO / "reports/seo/CONTENT_SEO_INVENTORY.csv"

KEYWORDS = {
    "wechat pay": r"wechat\s*pay|wechat\s*wallet|微信",
    "alipay": r"alipay|支付宝",
    "mobile payment": r"mobile\s*payment|qr\s*payment|cashless",
    "foreign card": r"foreign\s*card|international\s*card|visa|mastercard",
    "payment problem": r"payment\s*problem|payment\s*issue|pay\s*fail|troubleshoot",
}
FORBIDDEN_PERSONA = ("i used wechat", "my chinese wife", "my wife", "living in china",
                     "american expat", "5 years", "i remember")


def read_seo_index():
    if not SEO_INVENTORY.exists():
        return {}
    index = {}
    with SEO_INVENTORY.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            index[row.get("content_id", "")] = row
    return index


def front_matter(text):
    """Extract YAML/TOML front matter pairs (simple)."""
    fm = {}
    for m in re.finditer(r'^(?:content_id|title|slug)\s*[:=]\s*"([^"]+)"', text, re.M):
        key = m.group(0).split(":")[0].split("=")[0].strip()
        fm[key] = m.group(1)
    return fm


def payment_topics(text):
    low = text.lower()
    return [k for k, pat in KEYWORDS.items() if re.search(pat, low)]


def persona_status(text):
    low = text.lower()
    return "CLEAN" if not any(p in low for p in FORBIDDEN_PERSONA) else "LEGACY_RISK"


def affiliate_status(text):
    if "affiliate" in text.lower() and ("affiliate-mid-cta" in text or "affiliate-link" in text
                                        or "affiliate-section" in text or "affiliate-" in text.lower()):
        return "PRESENT"
    return "NONE"


def commercial_score(text, impressions):
    score = 0
    topics = payment_topics(text)
    if any("card" in t or "foreign" in t or "problem" in t for t in topics):
        score += 30  # high commercial intent
    elif topics:
        score += 20
    score += min(int(impressions) // 20, 30) if impressions else 0
    if affiliate_status(text) == "PRESENT":
        score += 20
    if "faq" in text.lower():
        score += 5
    return min(score, 100)


def build_inventory():
    seo = read_seo_index()
    rows = []
    for p in sorted(POSTS_DIR.glob("*.md")):
        text = p.read_text(encoding="utf-8", errors="replace")
        topics = payment_topics(text)
        if not topics:
            continue
        fm = front_matter(text)
        cid = fm.get("content_id", "")
        seo_row = seo.get(cid, {})
        impressions = seo_row.get("impressions_28d", "NOT_AVAILABLE")
        index_status = seo_row.get("indexed_status", "NOT_AVAILABLE")
        if impressions in (None, "", "NULL"):
            impressions = "NOT_AVAILABLE"
        slug = fm.get("slug", p.stem)
        url = f"https://www.chinaboundtravel.com/posts/{slug}/"
        rows.append({
            "content_id": cid or "MISSING",
            "url": url,
            "title": fm.get("title", p.stem),
            "payment_topic": ";".join(topics),
            "gsc_impressions_28d": impressions,
            "index_status": index_status,
            "persona_status": persona_status(text),
            "affiliate_status": affiliate_status(text),
            "commercial_score": commercial_score(text, impressions if impressions != "NOT_AVAILABLE" else 0),
        })
    with OUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else
                                ["content_id", "url", "title", "payment_topic", "gsc_impressions_28d",
                                 "index_status", "persona_status", "affiliate_status", "commercial_score"])
        writer.writeheader()
        writer.writerows(rows)
    return rows


if __name__ == "__main__":
    if "--check" in sys.argv:
        rows = build_inventory()
        assert len(rows) >= 4, f"expected >=4 payment pages, got {len(rows)}"
        assert OUT.exists()
        assert any("alipay" in r["payment_topic"] for r in rows)
        assert any("wechat" in r["payment_topic"] for r in rows)
        print(f"OK payment_pages={len(rows)}")
    else:
        rows = build_inventory()
        print(f"written {OUT} pages={len(rows)}")
