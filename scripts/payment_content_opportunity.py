"""P1-GROWTH-21C: Alipay for Foreigners content opportunity analysis.

Deterministic, no network. Scores whether a dedicated Alipay content asset is
worth creating now, using cached SEO inventory data.
"""
import csv
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "reports/revenue/ALIPAY_CONTENT_DECISION.md"
SEO_INVENTORY = REPO / "reports/seo/CONTENT_SEO_INVENTORY.csv"


def seo_rows():
    if not SEO_INVENTORY.exists():
        return []
    with SEO_INVENTORY.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def num(value, default=0):
    try:
        return float(value) if value not in (None, "", "NULL", "NOT_AVAILABLE") else default
    except (TypeError, ValueError):
        return default


def score():
    rows = seo_rows()
    alipay_pages = [r for r in rows if "alipay" in r.get("title", "").lower()
                    or "alipay" in r.get("url", "").lower()]
    existing_impressions = sum(num(r.get("impressions_28d")) for r in alipay_pages)
    indexed = sum(1 for r in alipay_pages if r.get("indexed_status") == "INDEXED")

    # Search Demand: high for "alipay for foreigners" but cached demand is low
    search = 24 if existing_impressions else 20
    # Commercial Intent: payment + foreign card setup = high intent
    commercial = 22
    # Existing Authority: alipay pages exist and some indexed
    authority = min(10 + indexed * 3, 18)
    # Content Gap: dedicated up-to-date Alipay guide exists -> smaller gap
    gap = 8 if alipay_pages else 15
    # Risk: payment = high-trust topic; WeChat recovery pending; sample low
    risk = 5
    total = search + commercial + authority + gap + risk

    if total >= 75 and indexed >= 1:
        verdict = "CREATE_READY"
    elif total >= 60:
        verdict = "HOLD"
    else:
        verdict = "REJECT"

    lines = [
        "# Alipay Content Decision (P1-GROWTH-21C)",
        "",
        f"Generated: {date.today().isoformat()}  |  ANALYSIS ONLY — no page created",
        "",
        "## Score (100)",
        "| Dimension | Weight | Score |",
        "|---|---|---|",
        f"| Search Demand | 30 | {search} |",
        f"| Commercial Intent | 25 | {commercial} |",
        f"| Existing Authority | 20 | {authority} |",
        f"| Content Gap | 15 | {gap} |",
        f"| Risk | 10 | {risk} |",
        f"| **Total** | 100 | **{total}** |",
        "",
        f"## Verdict: {verdict}",
        "",
        f"## Evidence (cached)",
        f"- alipay-related pages found: {len(alipay_pages)}",
        f"- indexed among them: {indexed}",
        f"- combined cached impressions: {existing_impressions}",
        "",
        "## Notes",
        "- Payment cluster is in Authority Build; commercial push waits for index stability.",
        "- If CREATE_READY in a future round, a dedicated Alipay guide would slot under the Payment Hub.",
        "- No content created this round; no CTA; no partner changes.",
    ]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"verdict": verdict, "total": total, "pages": len(alipay_pages)}


if __name__ == "__main__":
    if "--check" in sys.argv:
        result = score()
        assert result["verdict"] in ("CREATE_READY", "HOLD", "REJECT")
        assert OUT.exists()
        print(f"OK verdict={result['verdict']} total={result['total']} pages={result['pages']}")
    else:
        result = score()
        print(f"written {OUT} verdict={result['verdict']}")
