#!/usr/bin/env python3
"""P1-GROWTH-02: query intent classifier (transparent rule-based).

Classifies GSC query CSV rows into BRAND / VISA / PAYMENT / INTERNET /
CITY / TRANSPORT / TRAVEL_GUIDE / OTHER.  Pure rules, no external LLM API.

Outputs:
  reports/seo/query_intent_distribution.csv   - per-query intent
  reports/seo/QUERY_INTENT_DISTRIBUTION.md    - summary + full table
"""

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SEO_DIR = REPO / "reports" / "seo"

RULES = [
    ("BRAND", ["chinabound", "china bound", "cbt"]),
    ("VISA", ["visa", "transit", "144", "240", "immigration", "entry", "border", "evisa", "l visa", "z visa", "x visa", "q visa", "s visa", "f visa", "m visa", "30 day", "60 day", "15 day"]),
    ("PAYMENT", ["wechat pay", "alipay", "mobile pay", "payment", "pay", "card", "cash", "money", "unionpay", "apple pay"]),
    ("INTERNET", ["wifi", "sim card", "sim", "internet", "vpn", "esim", "data", "hotspot", "phone plan", "5g", "4g", "telecom", "china mobile", "china unicom"]),
    ("CITY", ["beijing", "shanghai", "shenzhen", "chengdu", "guangzhou", "hangzhou", "xi'an", "xian", "chongqing", "hong kong", "macau", "suzhou", "tianjin", "sichuan", "guilin", "kunming", "qianmen", "hutongs", "forbidden city", "great wall", "panda", "disney"]),
    ("TRANSPORT", ["train", "high speed rail", "hsr", "subway", "metro", "flight", "airport", "taxi", "bus", "ticket", "rail", "bullet train", "grab", "didi", "12306", "ctrip", "trip.com"]),
    ("TRAVEL_GUIDE", ["itinerary", "travel guide", "travel", "guide", "tour", "trip", "attraction", "tips", "packing", "food", "restaurant", "hotel", "accommodation", "language", "etiquette", "culture", "weather"]),
]


def classify(query):
    q = (query or "").lower()
    for intent, words in RULES:
        for w in words:
            if w in q:
                return intent
    return "OTHER"


def load_rows(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append({"query": r["keys"], "clicks": int(float(r["clicks"])),
                         "impressions": int(float(r["impressions"])),
                         "ctr": float(r["ctr"]), "position": float(r["position"])})
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", default=str(SEO_DIR / "raw_queries_28d.csv"))
    ap.add_argument("--output-dir", default=str(SEO_DIR))
    args = ap.parse_args(argv)
    rows = load_rows(args.input)
    out_dir = Path(args.output_dir)

    for r in rows:
        r["intent"] = classify(r["query"])

    with open(out_dir / "query_intent_distribution.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["query", "intent", "clicks", "impressions", "ctr", "position"])
        w.writeheader()
        for r in sorted(rows, key=lambda x: (-x["impressions"], x["query"])):
            w.writerow(r)

    agg = defaultdict(lambda: {"queries": 0, "clicks": 0, "impressions": 0})
    for r in rows:
        a = agg[r["intent"]]
        a["queries"] += 1
        a["clicks"] += r["clicks"]
        a["impressions"] += r["impressions"]
    total_imp = sum(a["impressions"] for a in agg.values())

    lines = ["# Query Intent Distribution (28-day baseline)", "",
             "Rule-based classification. No external LLM API was used.",
             "",
             "| intent | queries | impressions | % impressions | clicks |",
             "|---|---|---|---|---|"]
    for intent in ["BRAND", "VISA", "PAYMENT", "INTERNET", "CITY", "TRANSPORT", "TRAVEL_GUIDE", "OTHER"]:
        a = agg.get(intent, {"queries": 0, "clicks": 0, "impressions": 0})
        pct = (a["impressions"] / total_imp * 100) if total_imp else 0
        lines.append(f"| {intent} | {a['queries']} | {a['impressions']} | {pct:.1f}% | {a['clicks']} |")
    lines += ["", "## Per-Query Classification", "",
              "| query | intent | impressions | clicks | position |",
              "|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda x: (-x["impressions"], x["query"])):
        lines.append(f"| {r['query']} | {r['intent']} | {r['impressions']} | {r['clicks']} | {r['position']:.1f} |")
    lines.append("")
    (out_dir / "QUERY_INTENT_DISTRIBUTION.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out_dir / 'QUERY_INTENT_DISTRIBUTION.md'} ({len(rows)} queries)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
