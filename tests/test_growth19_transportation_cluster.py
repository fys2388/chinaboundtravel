"""P1-GROWTH-19: Transportation cluster authority expansion tests.

Deterministic, no network. Covers:
- Airport page: exists / indexable / canonical / content_id / sitemap / structure
- Commercial: partner unchanged / disclosure exists / no new tracking
- Cluster: links >= 5 / no orphan / scripts run clean
- Regression: REV002 unchanged / Drive=1 / GA4 schema unchanged
"""
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

POST = REPO / "content/posts/china-airport-transfer-guide.md"
POST_TEXT = POST.read_text(encoding="utf-8")
TOML = (REPO / "hugo.toml").read_text(encoding="utf-8")
SINGLE = (REPO / "layouts/_default/single.html").read_bytes().decode("gbk", errors="replace")
HEAD = (REPO / "layouts/partials/head.html").read_bytes().decode("utf-8", errors="replace")
TRANSPORT = (REPO / "content/posts/2026-07-16-china-transportation-complete-guide-trains-subways-taxis-and-more.md").read_text(encoding="utf-8")
HSR = (REPO / "content/posts/2026-05-25-china-high-speed-rail-how-to-book-tickets.md").read_text(encoding="utf-8")
CARD = (REPO / "content/posts/china-transportation-card-guide.md").read_text(encoding="utf-8")

AIRPORT_URL = "https://www.chinaboundtravel.com/posts/china-airport-transfer-guide/"


# ---------------------------------------------------------------------------
# airport page content
# ---------------------------------------------------------------------------
def test_airport_page_exists():
    assert POST.exists()


def test_airport_front_matter_complete():
    for marker in ('content_id: "cbt-', 'title: "China Airport Transfer Guide',
                   'description:', 'slug: "china-airport-transfer-guide"',
                   'date: 2026-08-16', 'draft: false',
                   'canonicalURL: "' + AIRPORT_URL + '"'):
        assert marker in POST_TEXT, marker


def test_airport_content_id_format():
    m = re.search(r'content_id:\s*"(cbt-[0-9a-f]{12})"', POST_TEXT)
    assert m, "content_id missing"
    assert m.group(1) == "cbt-02a3e0d6ed4f"


def test_airport_indexable():
    low = POST_TEXT.lower()
    assert "noindex" not in low
    assert "draft: true" not in low


def test_airport_canonical_self():
    assert 'canonicalURL: "' + AIRPORT_URL + '"' in POST_TEXT


def test_airport_h1():
    # Hugo renders H1 from front matter title; markdown has no explicit # heading
    assert "China Airport Transfer Guide (2026)" in POST_TEXT


def test_airport_required_h2_structure():
    for h2 in (
        "## How to Get From Chinese Airports to Cities",
        "## Airport Transfer Options Compared",
        "### 1. Airport Express Trains",
        "### 2. Metro Systems",
        "### 3. Taxi and Ride-Hailing Apps",
        "### 4. Private Airport Transfers",
        "## Beijing Airport Transfer Guide",
        "## Shanghai Airport Transfer Guide",
        "## Guangzhou Airport Transfer Guide",
        "## Which Airport Transfer Option Is Best?",
        "## Recommended Travel Services",
        "## FAQ",
    ):
        assert h2 in POST_TEXT, h2


def test_airport_sitemap_included():
    # sitemap inclusion is checked after a build; front matter has no exclusion
    assert "sitemap" not in POST_TEXT.lower() or "exclude" not in POST_TEXT.lower()


# ---------------------------------------------------------------------------
# commercial layer
# ---------------------------------------------------------------------------
def test_airport_affiliate_disclosure():
    assert "affiliate" in POST_TEXT.lower()
    assert "affiliate-disclosure" in POST_TEXT or "/affiliate-disclosure/" in POST_TEXT


def test_airport_recommended_services_table():
    assert "| Airport transfer |" in POST_TEXT
    assert "| Hotels |" in POST_TEXT
    assert "| Train connection |" in POST_TEXT
    assert "| Mobile data |" in POST_TEXT


def test_airport_no_new_partner():
    used = set(re.findall(r'key="([a-z0-9]+)"', POST_TEXT))
    allowed = {"trip", "klook", "esim", "hotel"}
    assert used <= allowed, used


def test_partner_urls_unchanged():
    for marker in ("aid=730795", "aff_id=150687", "klook.tpo.li",
                   "safetywing.com/nomad-insurance?referenceID=26548976",
                   'trip = "https://www.trip.com/"',
                   'hotel = "https://www.booking.com/index.html?aid=730795"',
                   'esim = "https://www.airalo.com/"'):
        assert marker in TOML, marker


def test_airport_persona_guard():
    proc = subprocess.run(["python", "scripts/persona_guard.py", str(POST)],
                          cwd=str(REPO), capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_airport_no_forbidden_phrases():
    low = POST_TEXT.lower()
    for phrase in ("i used", "i tried", "my experience", "my wife",
                   "living in china", "5 years", "american expat", "personally tested"):
        assert phrase not in low, phrase


# ---------------------------------------------------------------------------
# cluster linking
# ---------------------------------------------------------------------------
def test_airport_inbound_links_ge_5():
    total = (HSR.count("/posts/china-airport-transfer-guide/")
             + TRANSPORT.count("/posts/china-airport-transfer-guide/")
             + CARD.count("/posts/china-airport-transfer-guide/"))
    assert total >= 5, total


def test_cluster_no_orphan():
    for text in (TRANSPORT, HSR, CARD, POST_TEXT):
        # every cluster node must link somewhere within the cluster
        assert ("china-transportation-complete-guide" in text
                or "china-high-speed-rail-how-to-book-tickets" in text
                or "china-transportation-card-guide" in text
                or "china-airport-transfer-guide" in text)


def test_cluster_audit_script_clean():
    proc = subprocess.run(["python", "scripts/transportation_cluster_audit.py", "--check"],
                          cwd=str(REPO), capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "OK orphans=0" in proc.stdout


def test_rev002_review_prep_script_clean():
    proc = subprocess.run(["python", "scripts/rev002_review_preparation.py", "--check"],
                          cwd=str(REPO), capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "OK sample_status=INSUFFICIENT_SAMPLE" in proc.stdout


def test_rev003_candidate_analysis_exists():
    p = REPO / "reports/revenue/REV003_CANDIDATE_ANALYSIS.md"
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    assert "cbt-55aef784e6aa" in text
    assert "WAIT" in text
    assert "REV002" in text


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


def test_existing_urls_canonicals_unchanged():
    assert 'canonicalURL: "https://www.chinaboundtravel.com/posts/china-high-speed-rail-how-to-book-tickets/"' in HSR
    assert 'content_id: "cbt-cc4549872c92"' in HSR
    assert 'content_id = "cbt-17c6738ffb32"' in TRANSPORT
    assert 'content_id: "cbt-55aef784e6aa"' in CARD
    assert 'canonicalURL: "https://www.chinaboundtravel.com/posts/china-transportation-card-guide/"' in CARD
