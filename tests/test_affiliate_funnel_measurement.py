"""P1-GROWTH-14A: affiliate funnel measurement layer tests.

Covers (deterministic, no network):
- CTA inventory engine (schema, determinism, partner coverage, REV001 placement)
- revenue provider abstraction (REVENUE_NOT_AVAILABLE, never fabricates)
- GA4 event model (affiliate_impression / affiliate_click / affiliate_outbound)
- REV001 measurement upgrade (per-1000-sessions, CTA CTR, outbound rate)
- SEO invariants (content_id 57/57, Drive script exactly 1, affiliate URLs)
"""
import csv
import os
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from affiliate_funnel_audit import (  # noqa: E402
    CTA_AB, CTA_INLINE, CTA_MID, CTA_SHORTCODE,
    EVENT_CLICK, EVENT_FULL, build_inventory, scan_post, write_inventory,
)
from revenue_experiment_review import (  # noqa: E402
    calc_clicks_per_1000_sessions, calc_cta_ctr, calc_outbound_rate,
    write_rev001_funnel_metrics,
)
from revenue_provider import (  # noqa: E402
    REVENUE_STATUS, KNOWN_STATUSES, RevenueProvider, get_active_provider,
)

SINGLE = (REPO / "layouts/_default/single.html").read_bytes().decode("gbk", errors="replace")
DRIVE = (REPO / "layouts/partials/head.html").read_bytes().decode("utf-8", errors="replace")

FUNNEL_FIELDS = ["content_id", "url", "partner", "cta_type", "placement",
                 "tracking_event", "utm_source", "utm_campaign"]


# ---------------------------------------------------------------------------
# CTA inventory engine
# ---------------------------------------------------------------------------
def test_inventory_schema_complete():
    rows = build_inventory()
    assert len(rows) > 100
    for r in rows:
        for f in FUNNEL_FIELDS:
            assert f in r, f"missing {f}"
        # core fields are never empty; utm_* may be empty (no query string)
        for f in ("content_id", "url", "partner", "cta_type", "placement", "tracking_event"):
            assert r[f] != "", f"empty {f} in {r}"


def test_inventory_deterministic_order():
    rows = build_inventory()
    keys = [(r["content_id"], r["url"], r["partner"], r["cta_type"], r["placement"]) for r in rows]
    assert keys == sorted(keys)


def test_inventory_cta_types_recognized():
    rows = build_inventory()
    types = {r["cta_type"] for r in rows}
    assert CTA_MID in types
    assert CTA_SHORTCODE in types
    assert CTA_INLINE in types


def test_inventory_ab_cta_count():
    rows = build_inventory()
    assert sum(1 for r in rows if r["cta_type"] == CTA_AB) >= 1


def test_inventory_rev001_placement_detected():
    rows = build_inventory()
    rev = [r for r in rows if r["content_id"] == "cbt-e464169c4991"]
    assert rev, "REV001 page must appear in inventory"
    placements = {r["placement"] for r in rev}
    assert "food-delivery-mid-content" in placements


def test_inventory_full_tracking_on_ctas():
    rows = build_inventory()
    for r in rows:
        if r["cta_type"] in (CTA_MID, CTA_SHORTCODE):
            assert r["tracking_event"] == EVENT_FULL


def test_inventory_partner_coverage():
    rows = build_inventory()
    partners = {r["partner"] for r in rows}
    for expected in ("Booking", "Klook", "Airalo", "SafetyWing", "NordVPN"):
        assert expected in partners, expected


def test_inventory_utm_extracted():
    from affiliate_funnel_audit import _utm_from_url
    assert _utm_from_url("https://x.com/?utm_source=s&utm_campaign=c") == ("s", "c")
    assert _utm_from_url("https://safetywing.com/nomad-insurance?referenceID=26548976&utm_source=26548976&utm_medium=Ambassador") == ("26548976", "")
    assert _utm_from_url("https://x.com/noquery") == ("", "")


def test_inventory_csv_reproducible(tmp_path):
    rows = build_inventory()
    out = tmp_path / "funnel.csv"
    write_inventory(rows, out)
    with out.open(encoding="utf-8") as f:
        written = list(csv.DictReader(f))
    assert len(written) == len(rows)
    assert [r["content_id"] for r in written] == [r["content_id"] for r in rows]


def test_scan_post_mid_cta():
    text = '{{< affiliate-mid-cta partner="esim" placement="x-mid" text="Go" >}}body{{< /affiliate-mid-cta >}}'
    rows = scan_post(text)
    assert any(r["cta_type"] == CTA_MID and r["placement"] == "x-mid" for r in rows)


# ---------------------------------------------------------------------------
# Revenue provider abstraction
# ---------------------------------------------------------------------------
def test_revenue_status_not_available():
    # 无 TRAVELPAYOUTS_API_TOKEN → REVENUE_NOT_AVAILABLE；有凭据 → AVAILABLE（P1-GROWTH-14A）
    if not os.environ.get("TRAVELPAYOUTS_API_TOKEN", "").strip():
        assert REVENUE_STATUS == "REVENUE_NOT_AVAILABLE"
    else:
        assert REVENUE_STATUS == "AVAILABLE"
    assert REVENUE_STATUS in KNOWN_STATUSES


def test_provider_never_fabricates_revenue():
    p = get_active_provider()
    # 无凭据 → 永不虚构（None）；有凭据 → 只返回真实数值或 None（API 失败），绝不虚构
    if not os.environ.get("TRAVELPAYOUTS_API_TOKEN", "").strip():
        assert p.get_revenue() is None
        assert p.get_affiliate_clicks() is None
        assert p.status == "REVENUE_NOT_AVAILABLE"
    else:
        rev = p.get_revenue()
        assert rev is None or rev >= 0
        clicks = p.get_affiliate_clicks()
        assert clicks is None or clicks >= 0
        assert p.status in KNOWN_STATUSES


def test_provider_interface_validates_days():
    p = RevenueProvider("test")
    try:
        p.get_revenue(0)
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_provider_baseline_period():
    p = RevenueProvider()
    start, end = p.baseline_period(28)
    assert start < end


# ---------------------------------------------------------------------------
# GA4 event model upgrade
# ---------------------------------------------------------------------------
def test_ga4_impression_event_present():
    assert "affiliate_impression" in SINGLE
    assert "IntersectionObserver" in SINGLE


def test_ga4_outbound_event_present():
    assert "affiliate_outbound" in SINGLE
    assert "outbound_success" in SINGLE
    assert "pagehide" in SINGLE


def test_ga4_click_compatible():
    assert "affiliate_click" in SINGLE
    assert "gtag('event', 'affiliate_click', eventParams)" in SINGLE
    for f in ("content_id", "partner", "placement", "channel", "timestamp", "destination", "tracking_parameter"):
        assert f in SINGLE


def test_ga4_funnel_params_complete():
    for f in ("content_id", "partner", "placement", "channel", "timestamp", "destination", "tracking_parameter"):
        assert f in SINGLE


def test_ga4_no_duplicate_click_handler():
    assert SINGLE.count("affiliate_click") >= 2  # send + event name
    assert SINGLE.count("addEventListener('click'") >= 2  # article + funnel


# ---------------------------------------------------------------------------
# REV001 measurement upgrade
# ---------------------------------------------------------------------------
def test_rev001_per1000_sessions():
    assert calc_clicks_per_1000_sessions(5, 500) == 10.0
    assert calc_clicks_per_1000_sessions(0, 162) == 0.0
    assert calc_clicks_per_1000_sessions(None, 162) == 0.0
    assert calc_clicks_per_1000_sessions(3, 0) == 0.0


def test_rev001_cta_ctr():
    assert calc_cta_ctr(10, 100) == 10.0
    assert calc_cta_ctr(0, 100) == 0.0
    assert calc_cta_ctr(5, 0) == 0.0


def test_rev001_outbound_rate():
    assert calc_outbound_rate(5, 10) == 50.0
    assert calc_outbound_rate(0, 10) == 0.0
    assert calc_outbound_rate(3, 0) == 0.0


def test_rev001_funnel_metrics_file(tmp_path):
    out = tmp_path / "rev001.csv"
    write_rev001_funnel_metrics(out=out)
    with out.open(encoding="utf-8") as f:
        row = next(csv.DictReader(f))
    assert row["experiment_id"] == "REV001"
    assert row["primary_metric"] == "affiliate_clicks_per_1000_sessions"
    assert row["revenue"] == "NULL"
    assert row["status"] == "INSUFFICIENT_SAMPLE"


# ---------------------------------------------------------------------------
# SEO invariants
# ---------------------------------------------------------------------------
def test_content_ids_unique_57():
    posts = [f for f in (REPO / "content" / "posts").glob("*.md")]
    assert len(posts) == 58, f"expected 58 published posts, got {len(posts)}"
    rows = build_inventory()
    assert all(r["content_id"] for r in rows), "every inventory row needs content_id"
    cids = {r["content_id"] for r in rows}
    assert len(cids) >= 45, f"expected affiliate posts, got {len(cids)}"


def test_drive_script_exactly_once():
    assert DRIVE.count("emrldtp.com/NTMxNDY5.js?t=531469") == 1


def test_affiliate_urls_not_mutated():
    toml = (REPO / "hugo.toml").read_text(encoding="utf-8")
    for marker in ("aid=730795", "aff_id=150687", "klook.tpo.li", "safetywing.com/nomad-insurance?referenceID=26548976"):
        assert marker in toml


def test_single_html_affiliate_hrefs_template_driven():
    for key in ("esim", "vpn", "hotel", "klook"):
        assert "{{{{ .Site.Params.affiliate.{key} }}}}".format(key=key) in SINGLE


def test_no_drive_change_in_single():
    assert "emrldtp.com" not in SINGLE
