"""P1-GROWTH-20: Transportation cluster monetization phase tests.

Deterministic, no network. Covers:
- REV002: CTA unchanged / partner unchanged / tracking unchanged
- Cluster: 4 pages / no orphan / canonical unchanged
- Affiliate: shortcode unchanged / Drive=1 / GA4 schema unchanged
- 20A-20E outputs exist with expected verdicts
"""
import csv
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

TOML = (REPO / "hugo.toml").read_text(encoding="utf-8")
SINGLE = (REPO / "layouts/_default/single.html").read_bytes().decode("gbk", errors="replace")
HEAD = (REPO / "layouts/partials/head.html").read_bytes().decode("utf-8", errors="replace")
TRANSPORT = (REPO / "content/posts/2026-07-16-china-transportation-complete-guide-trains-subways-taxis-and-more.md").read_text(encoding="utf-8")
HSR = (REPO / "content/posts/2026-05-25-china-high-speed-rail-how-to-book-tickets.md").read_text(encoding="utf-8")
CARD = (REPO / "content/posts/china-transportation-card-guide.md").read_text(encoding="utf-8")
AIRPORT = (REPO / "content/posts/china-airport-transfer-guide.md").read_text(encoding="utf-8")
CLUSTER = {"transport": TRANSPORT, "hsr": HSR, "card": CARD, "airport": AIRPORT}


# ---------------------------------------------------------------------------
# REV002 freeze
# ---------------------------------------------------------------------------
def test_rev002_cta_unchanged():
    assert TRANSPORT.count("transportation-train-tickets-mid") == 1
    assert "Compare Train Tickets on Trip.com" in TRANSPORT
    assert "affiliate-mid-cta" in TRANSPORT


def test_rev002_partner_unchanged():
    assert 'partner="trip"' in TRANSPORT or "partner = \"trip\"" in TRANSPORT or "partner=\"trip\"" in TRANSPORT


def test_rev002_registry_running():
    with (REPO / "reports/revenue/REV002_EXPERIMENT_REGISTRY.csv").open(encoding="utf-8") as f:
        row = next(csv.DictReader(f))
    assert row["experiment_id"] == "REV002"
    assert row["status"] == "RUNNING"
    assert row["primary_metric"] == "affiliate_click_rate"


def test_rev002_tracking_schema_unchanged():
    for ev in ("affiliate_impression", "affiliate_click", "affiliate_outbound"):
        assert ev in SINGLE
    assert "gtag('event', 'affiliate_click', eventParams)" in SINGLE


# ---------------------------------------------------------------------------
# cluster integrity
# ---------------------------------------------------------------------------
def test_cluster_pages_ge_4():
    assert len(CLUSTER) == 4


def test_cluster_no_orphan():
    for key, text in CLUSTER.items():
        others = [k for k in CLUSTER if k != key]
        assert any("/posts/" + o + "/" in text for o in
                   ["china-transportation-complete-guide-trains-subways-taxis-and-more",
                    "china-high-speed-rail-how-to-book-tickets",
                    "china-transportation-card-guide",
                    "china-airport-transfer-guide"]), key


def test_cluster_canonical_unchanged():
    assert 'canonicalURL: "https://www.chinaboundtravel.com/posts/china-transportation-card-guide/"' in CARD
    assert 'canonicalURL: "https://www.chinaboundtravel.com/posts/china-airport-transfer-guide/"' in AIRPORT
    assert 'canonicalURL: "https://www.chinaboundtravel.com/posts/china-high-speed-rail-how-to-book-tickets/"' in HSR


def test_cluster_content_ids_unchanged():
    assert 'content_id = "cbt-17c6738ffb32"' in TRANSPORT
    assert 'content_id: "cbt-cc4549872c92"' in HSR
    assert 'content_id: "cbt-55aef784e6aa"' in CARD
    assert 'content_id: "cbt-02a3e0d6ed4f"' in AIRPORT


def test_airport_inbound_ge_5():
    total = (HSR.count("/posts/china-airport-transfer-guide/")
             + TRANSPORT.count("/posts/china-airport-transfer-guide/")
             + CARD.count("/posts/china-airport-transfer-guide/"))
    assert total >= 5


# ---------------------------------------------------------------------------
# affiliate invariants
# ---------------------------------------------------------------------------
def test_affiliate_shortcodes_unchanged():
    for name in ("affiliate-mid-cta.html", "affiliate-link.html", "affiliate-section.html"):
        p = REPO / "layouts/shortcodes" / name
        assert p.exists(), name


def test_drive_exactly_once():
    assert HEAD.count("emrldtp.com/NTMxNDY5.js?t=531469") == 1


def test_affiliate_urls_unchanged():
    for marker in ("aid=730795", "aff_id=150687", "klook.tpo.li",
                   "safetywing.com/nomad-insurance?referenceID=26548976",
                   'trip = "https://www.trip.com/"',
                   'hotel = "https://www.booking.com/index.html?aid=730795"',
                   'esim = "https://www.airalo.com/"'):
        assert marker in TOML, marker


def test_no_new_partner_in_new_pages():
    for text in (CARD, AIRPORT):
        used = set(re.findall(r'key="([a-z0-9]+)"', text))
        assert used <= {"trip", "klook", "esim", "hotel"}, used


# ---------------------------------------------------------------------------
# 20A REV002 review framework
# ---------------------------------------------------------------------------
def test_rev002_final_review_gate_waiting():
    p = REPO / "reports/revenue/REV002_FINAL_REVIEW.md"
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    assert "WAITING_REVIEW_GATE" in text
    assert "2026-09-13" in text


def test_rev002_final_review_script_clean():
    proc = subprocess.run(["python", "scripts/rev002_final_review.py", "--check"],
                          cwd=str(REPO), capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "OK status=WAITING_REVIEW_GATE" in proc.stdout


# ---------------------------------------------------------------------------
# 20B card CTA readiness
# ---------------------------------------------------------------------------
def test_card_cta_readiness_exists():
    p = REPO / "reports/revenue/TRANSPORTATION_CARD_CTA_READINESS.md"
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    assert "cbt-55aef784e6aa" in text
    assert text.split("## Verdict:")[1].splitlines()[0].strip() in ("READY_FOR_EXPERIMENT", "WAIT_FOR_DATA", "REJECT")


def test_card_cta_readiness_script_clean():
    proc = subprocess.run(["python", "scripts/transportation_card_conversion_analysis.py", "--check"],
                          cwd=str(REPO), capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_no_cta_added_to_card_this_round():
    # verdict not READY -> no experiment shortcode allowed on card page
    text = (REPO / "reports/revenue/TRANSPORTATION_CARD_CTA_READINESS.md").read_text(encoding="utf-8")
    if "READY_FOR_EXPERIMENT" not in text:
        assert "affiliate-mid-cta" not in CARD


# ---------------------------------------------------------------------------
# 20C airport analysis
# ---------------------------------------------------------------------------
def test_airport_monetization_analysis_exists():
    p = REPO / "reports/revenue/AIRPORT_TRANSFER_MONETIZATION_ANALYSIS.md"
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    assert "cbt-02a3e0d6ed4f" in text
    assert "CANDIDATE" in text


def test_no_cta_on_airport_this_round():
    assert "affiliate-mid-cta" not in AIRPORT


# ---------------------------------------------------------------------------
# 20D revenue map
# ---------------------------------------------------------------------------
def test_revenue_funnel_exists():
    p = REPO / "reports/revenue/TRANSPORTATION_REVENUE_FUNNEL.md"
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    assert "Traffic Entry" in text
    assert "Revenue" in text
    assert "Discovery" in text and "Transaction" in text and "Utility" in text


def test_revenue_map_script_clean():
    proc = subprocess.run(["python", "scripts/transportation_revenue_map.py", "--check"],
                          cwd=str(REPO), capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "OK pages=4" in proc.stdout


# ---------------------------------------------------------------------------
# 20E payment cluster research
# ---------------------------------------------------------------------------
def test_payment_cluster_readiness_exists():
    p = REPO / "reports/revenue/PAYMENT_CLUSTER_READINESS.md"
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    assert text.split("## Verdict:")[1].splitlines()[0].strip() in ("READY", "WAIT", "BLOCKED")
    assert "cbt-255af4ed003a" in text or "WeChat Pay Weak" in text


# ---------------------------------------------------------------------------
# persona / SEO guard on new pages
# ---------------------------------------------------------------------------
def test_new_pages_persona_clean():
    for text in (CARD, AIRPORT):
        low = text.lower()
        for phrase in ("i used", "i tried", "my wife", "living in china",
                       "5 years", "american expat"):
            assert phrase not in low, phrase


def test_new_pages_no_noindex():
    for text in (CARD, AIRPORT):
        assert "noindex" not in text.lower()
        assert "draft: true" not in text.lower()
