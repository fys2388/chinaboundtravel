"""P1-GROWTH-20D: Transportation cluster revenue funnel map.

Deterministic, no network. Classifies cluster pages by funnel stage and
documents the Traffic Entry -> Revenue path.
"""
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "reports/revenue/TRANSPORTATION_REVENUE_FUNNEL.md"

NODES = [
    ("transportation_guide", "cbt-17c6738ffb32",
     "content/posts/2026-07-16-china-transportation-complete-guide-trains-subways-taxis-and-more.md",
     "Discovery", "REV002 Trip.com mid-cta"),
    ("high_speed_rail", "cbt-cc4549872c92",
     "content/posts/2026-05-25-china-high-speed-rail-how-to-book-tickets.md",
     "Transaction", "Trip.com/booking links"),
    ("transportation_card", "cbt-55aef784e6aa",
     "content/posts/china-transportation-card-guide.md",
     "Utility", "comparison layer (Trip/Klook/Airalo/Booking)"),
    ("airport_transfer", "cbt-02a3e0d6ed4f",
     "content/posts/china-airport-transfer-guide.md",
     "Transaction", "comparison layer (Klook/Booking/Trip/Airalo)"),
]


def build_map():
    lines = [
        "# Transportation Revenue Funnel (P1-GROWTH-20D)",
        "",
        f"Generated: {date.today().isoformat()}  |  Deterministic map, no network",
        "",
        "## Funnel",
        "Traffic Entry -> Informational Page -> Commercial Intent -> Affiliate CTA -> Outbound -> Revenue",
        "",
        "## Page classification",
        "| Page | content_id | Stage | Commercial element |",
        "|---|---|---|---|",
    ]
    for key, cid, rel, stage, commercial in NODES:
        p = REPO / rel
        cta_links = 0
        if p.exists():
            text = p.read_text(encoding="utf-8")
            cta_links = (text.count("affiliate-link") + text.count("affiliate-mid-cta")
                         + text.count("affiliate-section"))
        lines.append(f"| {key} | {cid} | {stage} | {commercial} (shortcode uses: {cta_links}) |")
    lines += [
        "",
        "## Stage inventory",
        "- Discovery: Transportation Guide (authority hub, REV002 active)",
        "- Transaction: High-Speed Rail (booking intent), Airport Transfer (transfer intent)",
        "- Utility: Transportation Card (comparison layer, no experiment)",
        "",
        "## Measurement readiness",
        "- affiliate_click / affiliate_impression / affiliate_outbound events exist (GA4 schema unchanged)",
        "- Revenue: NULL allowed; never fabricated",
        "- Sample guard: affiliate_clicks < 20 -> INSUFFICIENT_SAMPLE",
        "",
        "## Rules",
        "- REV002 frozen; no new CTA this round; no new partner/tracking/UTM.",
    ]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"pages": len(NODES), "output": str(OUT)}


if __name__ == "__main__":
    if "--check" in sys.argv:
        result = build_map()
        assert result["pages"] == 4
        assert OUT.exists()
        print(f"OK pages={result['pages']}")
    else:
        result = build_map()
        print(f"written {result['output']}")
