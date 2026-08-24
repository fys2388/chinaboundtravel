"""P1-GROWTH-22: Payment content release (Alipay authority page) tests.

Deterministic, no network. Covers:
- 22A/22B Alipay page: exists / title / description / content_id / slug /
  canonical self / no noindex / FAQ >= 5 / H2 structure / sitemap inclusion
- 22E cluster: inbound >= 5 / outbound topic path / no orphan / link graph report
- 22F candidate report exists with READY/WAIT/REJECT verdict
- Persona: forbidden phrases absent, editorial voice present, persona_guard PASS
- Regression: REV001 unchanged / REV002 unchanged / Drive exactly 1 /
  GA4 schema unchanged / affiliate config unchanged
- Reports exist: WECHAT_PAYMENT_STATUS.md / PAYMENT_CLUSTER_LINK_GRAPH.md /
  PAYMENT_ESIM_EXPERIMENT_CANDIDATE.md
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

ALIPAY = REPO / "content/posts/alipay-for-foreigners-guide.md"
ALIPAY_TEXT = ALIPAY.read_text(encoding="utf-8")
ALIPAY_URL = "https://www.chinaboundtravel.com/posts/alipay-for-foreigners-guide/"
ALIPAY_CONTENT_ID = "cbt-0adceab18b53"

TOML = (REPO / "hugo.toml").read_text(encoding="utf-8")
SINGLE = (REPO / "layouts/_default/single.html").read_bytes().decode("gbk", errors="replace")
HEAD = (REPO / "layouts/partials/head.html").read_bytes().decode("utf-8", errors="replace")
TRANSPORT = (REPO / "content/posts/2026-07-16-china-transportation-complete-guide-trains-subways-taxis-and-more.md").read_text(encoding="utf-8")
CARD = (REPO / "content/posts/china-transportation-card-guide.md").read_text(encoding="utf-8")
FOOD = (REPO / "content/posts/2026-05-28-chinese-food-delivery-meituan-eleme-guide.md").read_text(encoding="utf-8")
PACKING = (REPO / "content/posts/2026-08-09-china-packing-list-2026-what-to-bring-and-what-to-leave-at-home.md").read_text(encoding="utf-8")
ESIM = (REPO / "content/posts/internet-connection-china-esim-vpn-guide.md").read_text(encoding="utf-8")
RESOURCES = (REPO / "content/resources/_index.md").read_text(encoding="utf-8")
WECHAT_WEAK = (REPO / "content/posts/2026-07-02-wechat-pay-for-foreigners-step-by-step-setup-and-common-mistakes-to-avoid-guide.md").read_text(encoding="utf-8", errors="replace")

REQUIRED_H2 = [
    "## Can Foreigners Use Alipay in China?",
    "## What You Need Before Setting Up Alipay",
    "## How to Set Up Alipay Step by Step",
    "## Common Alipay Problems",
    "## Alipay vs WeChat Pay for Foreign Travelers",
    "## Recommended Travel Preparation Tools",
]


def _fm(text, key):
    fm = text.split("---", 2)[1]
    m = re.search(r"^\s*" + re.escape(key) + r"\s*[:=]\s*(.+)$", fm, re.M)
    if not m:
        return None
    val = m.group(1).strip()
    if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
        val = val[1:-1]
    return val


@pytest.fixture(scope="module")
def built_site():
    out = Path(tempfile.mkdtemp(prefix="hugo_g22_"))
    proc = subprocess.run(
        ["hugo", "--gc", "--minify", "--destination", str(out)],
        cwd=str(REPO), capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=300,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    return out


def _page_html(built_site, rel):
    p = built_site / rel
    assert p.exists(), f"missing rendered page: {rel}"
    return p.read_text(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# 22A/22B content & front matter
# ---------------------------------------------------------------------------
def test_alipay_page_exists():
    assert ALIPAY.exists()


def test_front_matter_title():
    # Base Alipay title is preserved; the "转化与排名优化" task appends a long-tail
    # variant (authorized deep optimizer), e.g. "...(2026) — Foreigners Payment Setup".
    assert "Alipay for Foreigners in China: Setup Guide and Payment Tips (2026)" in ALIPAY_TEXT
    m = re.search(r'^title:\s*"([^"]+)"', ALIPAY_TEXT, re.M)
    assert m and "Alipay" in m.group(1)


def test_front_matter_description():
    m = re.search(r'description:\s*"([^"]+)"', ALIPAY_TEXT)
    assert m and len(m.group(1)) >= 50
    assert len(m.group(1)) <= 160


def test_content_id():
    assert _fm(ALIPAY_TEXT, "content_id") == ALIPAY_CONTENT_ID


def test_slug():
    assert _fm(ALIPAY_TEXT, "slug") == "alipay-for-foreigners-guide"


def test_not_draft():
    assert _fm(ALIPAY_TEXT, "draft") == "false"


def test_no_noindex():
    assert "noindex" not in ALIPAY_TEXT.lower()


def test_no_cover_image_breakage():
    # cover removed because no matching local image exists (no broken /img ref)
    assert "cover" not in ALIPAY_TEXT.split("---", 2)[1].lower() or "image" not in ALIPAY_TEXT.split("---", 2)[1].lower()


# ---------------------------------------------------------------------------
# SEO: canonical / sitemap / rendering
# ---------------------------------------------------------------------------
def test_canonical_self():
    assert _fm(ALIPAY_TEXT, "canonicalURL") == ALIPAY_URL


def test_rendered_page_200(built_site):
    html = _page_html(built_site, "posts/alipay-for-foreigners-guide/index.html")
    assert "<html" in html


def test_rendered_canonical_self(built_site):
    html = _page_html(built_site, "posts/alipay-for-foreigners-guide/index.html")
    assert ("rel=canonical href=" + ALIPAY_URL) in html


def test_rendered_no_noindex(built_site):
    html = _page_html(built_site, "posts/alipay-for-foreigners-guide/index.html")
    assert 'name="robots" content="noindex' not in html


def test_rendered_h1(built_site):
    html = _page_html(built_site, "posts/alipay-for-foreigners-guide/index.html")
    assert "Alipay for Foreigners in China" in html


def test_sitemap_includes_alipay(built_site):
    sitemap = built_site / "sitemap.xml"
    assert sitemap.exists()
    text = sitemap.read_text(encoding="utf-8", errors="replace")
    assert ALIPAY_URL in text


def test_faq_ge_5():
    import yaml
    body = ALIPAY_TEXT.split("---", 2)[1]
    data = yaml.safe_load(body)
    faq = data.get("params", {}).get("faq") or []
    assert len(faq) >= 5, len(faq)


def test_faq_has_answers():
    import yaml
    body = ALIPAY_TEXT.split("---", 2)[1]
    data = yaml.safe_load(body)
    for item in (data.get("params", {}).get("faq") or []):
        assert item.get("question") and item.get("answer") and len(item["answer"]) >= 30


def test_h2_structure():
    for h2 in REQUIRED_H2:
        assert h2 in ALIPAY_TEXT, h2


def test_keyword_presence():
    low = ALIPAY_TEXT.lower()
    for kw in ("alipay", "foreigners", "passport", "visa or mastercard", "qr"):
        assert kw in low, kw


# ---------------------------------------------------------------------------
# 22E cluster linking
# ---------------------------------------------------------------------------
def test_inbound_links_ge_5():
    total = (
        TRANSPORT.count("/posts/alipay-for-foreigners-guide/")
        + CARD.count("/posts/alipay-for-foreigners-guide/")
        + PACKING.count("/posts/alipay-for-foreigners-guide/")
        + ESIM.count("/posts/alipay-for-foreigners-guide/")
        + RESOURCES.count("/posts/alipay-for-foreigners-guide/")
    )
    assert total >= 5, total


def test_outbound_topic_path():
    assert "/posts/wechat-pay-for-foreigners-step-by-step-setup-and-common-mistakes-to-avoid-guide/" in ALIPAY_TEXT
    assert "/posts/internet-connection-china-esim-vpn-guide/" in ALIPAY_TEXT
    assert "/posts/china-transportation-complete-guide-trains-subways-taxis-and-more/" in ALIPAY_TEXT


def test_transport_guide_links_alipay():
    assert "/posts/alipay-for-foreigners-guide/" in TRANSPORT


def test_card_links_alipay():
    assert CARD.count("/posts/alipay-for-foreigners-guide/") >= 2


def test_packing_list_links_alipay():
    assert "/posts/alipay-for-foreigners-guide/" in PACKING


def test_esim_guide_links_alipay():
    assert "/posts/alipay-for-foreigners-guide/" in ESIM


def test_resources_links_alipay():
    assert "/posts/alipay-for-foreigners-guide/" in RESOURCES


def test_no_orphan_self_link():
    # page must not link to itself
    assert "/posts/alipay-for-foreigners-guide/" not in ALIPAY_TEXT.split("---", 2)[-1] or "canonical" not in ALIPAY_TEXT


def test_link_graph_report_exists():
    p = REPO / "reports/revenue/PAYMENT_CLUSTER_LINK_GRAPH.md"
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    assert "Inbound count" in text and "Outbound count" in text


# ---------------------------------------------------------------------------
# 22F experiment candidate (analysis only)
# ---------------------------------------------------------------------------
def test_esim_candidate_report_exists():
    p = REPO / "reports/revenue/PAYMENT_ESIM_EXPERIMENT_CANDIDATE.md"
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    assert "READY" in text and "WAIT" in text


def test_esim_candidate_not_started():
    # analysis only: no CTA added, no affiliate destination changed
    assert "payment-esim-connectivity-mid" not in ALIPAY_TEXT


# ---------------------------------------------------------------------------
# 22D WeChat review status
# ---------------------------------------------------------------------------
def test_wechat_status_report_exists():
    p = REPO / "reports/revenue/WECHAT_PAYMENT_STATUS.md"
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    assert "WAITING_RECRAWL" in text or "WECHAT_RECOVERED" in text


def test_wechat_weak_frozen():
    # no canonical / title change on weak page this round
    assert 'canonicalURL: "https://www.chinaboundtravel.com/posts/wechat-pay-for-foreigners-step-by-step-setup-and-common-mistakes-to-avoid-guide/"' in WECHAT_WEAK
    assert 'content_id: "cbt-255af4ed003a"' in WECHAT_WEAK


# ---------------------------------------------------------------------------
# persona & compliance
# ---------------------------------------------------------------------------
def test_forbidden_persona_phrases_absent():
    low = ALIPAY_TEXT.lower()
    for phrase in ("i used alipay", "my chinese friends showed me", "living in china",
                   "my wife", "american expat", "i remember", "personally tested",
                   "5 years", "i lived in", "i moved to"):
        assert phrase not in low, phrase


def test_editorial_voice_present():
    assert "ChinaBound Travel" in ALIPAY_TEXT
    assert "Based on current official information" in ALIPAY_TEXT or "editorial" in ALIPAY_TEXT.lower()


def test_persona_guard_passes():
    proc = subprocess.run(["python", "scripts/persona_guard.py", str(ALIPAY)],
                          cwd=str(REPO), capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_no_affiliate_cta_in_alipay():
    # commercial layer is soft only: no affiliate-mid-cta / popup / strong purchase language
    assert "affiliate-mid-cta" not in ALIPAY_TEXT
    assert "popup" not in ALIPAY_TEXT.lower()


# ---------------------------------------------------------------------------
# regression: experiments frozen
# ---------------------------------------------------------------------------
def test_rev001_unchanged():
    assert "food-delivery-mid-content" in FOOD or "affiliate-mid-cta" in FOOD


def test_rev002_unchanged():
    assert TRANSPORT.count("transportation-train-tickets-mid") == 1
    assert "Compare Train Tickets on Trip.com" in TRANSPORT


def test_drive_exactly_once():
    assert HEAD.count("emrldtp.com/NTMxNDY5.js?t=531469") == 1


def test_ga4_schema_unchanged():
    for ev in ("affiliate_impression", "affiliate_click", "affiliate_outbound"):
        assert ev in SINGLE
    assert "gtag('event', 'affiliate_click', eventParams)" in SINGLE


def test_affiliate_config_unchanged():
    for marker in ("aid=730795", "aff_id=150687", "klook.tpo.li",
                   "safetywing.com/nomad-insurance?referenceID=26548976",
                   'trip = "https://www.trip.com/"', 'esim = "https://www.airalo.com/"'):
        assert marker in TOML, marker


def test_no_utm_in_alipay_body():
    assert "utm_" not in ALIPAY_TEXT.split("---", 2)[2]
