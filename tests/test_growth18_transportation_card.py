"""P1-GROWTH-18: China Transportation Card commercial content creation tests.

Deterministic, no network. Covers:
- Content: file / title / description / content_id / slug
- SEO: canonical self / no noindex / required H2 structure / internal links >= 5
- Commercial: affiliate disclosure / partner URLs unchanged / no new partner
- Persona: forbidden phrase scan + persona_guard
- Regression: REV002 CTA unchanged / Drive exactly 1 / GA4 schema unchanged
- Front matter parseable
"""
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

POST = REPO / "content/posts/china-transportation-card-guide.md"
POST_TEXT = POST.read_text(encoding="utf-8")
TOML = (REPO / "hugo.toml").read_text(encoding="utf-8")
SINGLE = (REPO / "layouts/_default/single.html").read_bytes().decode("gbk", errors="replace")
HEAD = (REPO / "layouts/partials/head.html").read_bytes().decode("utf-8", errors="replace")
TRANSPORT = (REPO / "content/posts/2026-07-16-china-transportation-complete-guide-trains-subways-taxis-and-more.md").read_text(encoding="utf-8")
HSR = (REPO / "content/posts/2026-05-25-china-high-speed-rail-how-to-book-tickets.md").read_text(encoding="utf-8")
RESOURCES = (REPO / "content/resources/_index.md").read_text(encoding="utf-8")

CARD_URL = "https://www.chinaboundtravel.com/posts/china-transportation-card-guide/"


# ---------------------------------------------------------------------------
# 18A/18G content & front matter
# ---------------------------------------------------------------------------
def test_page_file_exists():
    assert POST.exists()


def test_front_matter_title():
    assert 'title: "China Transportation Card Guide (2026)' in POST_TEXT


def test_front_matter_description():
    assert "description:" in POST_TEXT
    m = re.search(r'description:\s*"([^"]+)"', POST_TEXT)
    assert m and len(m.group(1)) >= 50


def test_content_id_exists():
    m = re.search(r'content_id:\s*"(cbt-[0-9a-f]{12})"', POST_TEXT)
    assert m, "content_id missing"


def test_slug_exists():
    assert 'slug: "china-transportation-card-guide"' in POST_TEXT
    assert 'canonicalURL: "' + CARD_URL + '"' in POST_TEXT


def test_front_matter_parseable():
    try:
        import yaml
    except ImportError:
        return  # pragma: no cover
    body = POST_TEXT.split("---", 2)[1]
    data = yaml.safe_load(body)
    assert data["content_id"].startswith("cbt-")
    assert data["slug"] == "china-transportation-card-guide"
    assert data["draft"] is False
    assert data["canonicalURL"] == CARD_URL


# ---------------------------------------------------------------------------
# 18B/18C/18F SEO
# ---------------------------------------------------------------------------
def test_canonical_self():
    assert 'canonicalURL: "' + CARD_URL + '"' in POST_TEXT


def test_no_noindex():
    low = POST_TEXT.lower()
    assert "noindex" not in low
    assert "draft: true" not in low


def test_required_h2_structure():
    for h2 in (
        "## Do Foreign Travelers Need a Transportation Card in China?",
        "## China Transportation Card Options Compared",
        "### 1. Metro IC Cards (Physical Transit Cards)",
        "### 2. Transit Apps and Digital Payments",
        "### 3. Mobile Payment Options (Alipay / WeChat Pay)",
        "## City Examples",
        "### Beijing Transportation Card",
        "### Shanghai Transportation Card",
        "### Guangzhou / Shenzhen Transportation Card",
        "## How to Buy a Transportation Card",
        "## Which Option Is Best for Tourists?",
        "## Recommended Travel Tools",
    ):
        assert h2 in POST_TEXT, h2


def test_internal_links_ge_5():
    # inbound links from existing pages to the new page
    total = (
        HSR.count("/posts/china-transportation-card-guide/")
        + TRANSPORT.count("/posts/china-transportation-card-guide/")
        + RESOURCES.count("/posts/china-transportation-card-guide/")
    )
    assert total >= 5, total


def test_transport_payment_section_linked():
    assert "### How to Pay for the Subway" in TRANSPORT
    assert "/posts/china-transportation-card-guide/" in TRANSPORT


def test_hsr_linked():
    assert "/posts/china-transportation-card-guide/" in HSR
    assert "Before taking trains, travelers may also need a local" in HSR


# ---------------------------------------------------------------------------
# 18D commercial layer
# ---------------------------------------------------------------------------
def test_affiliate_disclosure_exists():
    assert "affiliate" in POST_TEXT.lower()
    assert "disclosure" in POST_TEXT.lower() or "/disclosure/" in POST_TEXT


def test_recommended_tools_table():
    assert "| Train tickets |" in POST_TEXT
    assert "| Attraction tickets |" in POST_TEXT
    assert "| Mobile data |" in POST_TEXT
    assert "| Hotels |" in POST_TEXT


def test_partner_urls_unchanged():
    for marker in ("aid=730795", "aff_id=150687", "klook.tpo.li",
                   "safetywing.com/nomad-insurance?referenceID=26548976",
                   'trip = "https://www.trip.com/"',
                   'hotel = "https://www.booking.com/index.html?aid=730795"',
                   'esim = "https://www.airalo.com/"'):
        assert marker in TOML, marker


def test_no_new_partner_key():
    # only existing affiliate keys may be referenced
    used = set(re.findall(r'key="([a-z0-9]+)"', POST_TEXT))
    allowed = {"trip", "klook", "esim", "hotel", "flight", "vpn", "safetywing"}
    assert used <= allowed, used


# ---------------------------------------------------------------------------
# 18H persona
# ---------------------------------------------------------------------------
def test_forbidden_persona_phrases_absent():
    low = POST_TEXT.lower()
    for phrase in ("i used this card", "my experience", "when i arrived in china",
                   "my wife told me", "living in china", "i used", "i tried",
                   "5 years", "american expat", "personally tested"):
        assert phrase not in low, phrase


def test_editorial_voice_present():
    assert "This guide explains" in POST_TEXT
    assert "ChinaBound Travel" in POST_TEXT
    assert "Based on official transport information" in POST_TEXT or "Based on" in POST_TEXT


def test_persona_guard_passes():
    proc = subprocess.run(["python", "scripts/persona_guard.py", str(POST)],
                          cwd=str(REPO), capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, proc.stdout + proc.stderr


# ---------------------------------------------------------------------------
# regression invariants
# ---------------------------------------------------------------------------
def test_rev002_cta_unchanged():
    assert TRANSPORT.count("transportation-train-tickets-mid") == 1
    assert "Compare Train Tickets on Trip.com" in TRANSPORT


def test_drive_exactly_once():
    assert HEAD.count("emrldtp.com/NTMxNDY5.js?t=531469") == 1


def test_ga4_schema_unchanged():
    for ev in ("affiliate_impression", "affiliate_click", "affiliate_outbound"):
        assert ev in SINGLE
    assert "gtag('event', 'affiliate_click', eventParams)" in SINGLE


def test_existing_seo_unchanged():
    # existing transportation pages keep their canonical / slug / content_id
    assert 'canonicalURL: "https://www.chinaboundtravel.com/posts/china-high-speed-rail-how-to-book-tickets/"' in HSR
    assert 'content_id: "cbt-cc4549872c92"' in HSR
    assert 'slug = "china-transportation-complete-guide-trains-subways-taxis-and-more"' in TRANSPORT
    assert 'content_id = "cbt-17c6738ffb32"' in TRANSPORT
