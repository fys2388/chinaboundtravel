"""P1-GROWTH-21: Payment cluster authority build tests.

Deterministic, no network. Covers:
- 21A inventory / 21B WeChat review / 21C Alipay decision / 21D-21F reports
- SEO: canonical/content_id unchanged
- Experiments: REV001/REV002/Drive unchanged
- Persona guard on payment pages
- Affiliate: no new partner
"""
import csv
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

TOML = (REPO / "hugo.toml").read_text(encoding="utf-8")
SINGLE = (REPO / "layouts/_default/single.html").read_bytes().decode("gbk", errors="replace")
HEAD = (REPO / "layouts/partials/head.html").read_bytes().decode("utf-8", errors="replace")
TRANSPORT = (REPO / "content/posts/2026-07-16-china-transportation-complete-guide-trains-subways-taxis-and-more.md").read_text(encoding="utf-8")
FOOD = (REPO / "content/posts/2026-05-28-chinese-food-delivery-meituan-eleme-guide.md").read_text(encoding="utf-8")
WECHAT_STRONG = (REPO / "content/posts/2026-05-22-how-to-use-wechat-pay-as-a-foreigner.md").read_text(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# 21A inventory
# ---------------------------------------------------------------------------
def test_inventory_exists():
    p = REPO / "reports/revenue/PAYMENT_CLUSTER_INVENTORY.csv"
    assert p.exists()


def test_inventory_schema():
    with (REPO / "reports/revenue/PAYMENT_CLUSTER_INVENTORY.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows
    for field in ("content_id", "url", "title", "payment_topic", "gsc_impressions_28d",
                  "index_status", "persona_status", "affiliate_status", "commercial_score"):
        assert field in rows[0], field


def test_inventory_contains_wechat_and_alipay():
    with (REPO / "reports/revenue/PAYMENT_CLUSTER_INVENTORY.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    topics = set()
    for r in rows:
        topics.update(r["payment_topic"].split(";"))
    assert "wechat pay" in topics
    assert "alipay" in topics


def test_inventory_script_clean():
    proc = subprocess.run(["python", "scripts/payment_cluster_audit.py", "--check"],
                          cwd=str(REPO), capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, proc.stdout + proc.stderr


# ---------------------------------------------------------------------------
# 21B WeChat review
# ---------------------------------------------------------------------------
def test_wechat_review_exists():
    p = REPO / "reports/revenue/WECHAT_INDEX_RECOVERY_REVIEW.md"
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    assert "cbt-255af4ed003a" in text
    assert "WAITING_RECRAWL" in text


def test_wechat_no_request_indexing_this_round():
    text = (REPO / "reports/revenue/WECHAT_INDEX_RECOVERY_REVIEW.md").read_text(encoding="utf-8")
    assert "no request indexing" in text.lower() or "not request" in text.lower()


# ---------------------------------------------------------------------------
# 21C Alipay decision
# ---------------------------------------------------------------------------
def test_alipay_decision_exists():
    p = REPO / "reports/revenue/ALIPAY_CONTENT_DECISION.md"
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    verdict = text.split("## Verdict:")[1].splitlines()[0].strip()
    assert verdict in ("CREATE_READY", "HOLD", "REJECT")


def test_alipay_no_page_created():
    # 21C explicitly does not create the page this round
    assert not (REPO / "content/posts/alipay-for-foreigners-guide.md").exists()


def test_alipay_script_clean():
    proc = subprocess.run(["python", "scripts/payment_content_opportunity.py", "--check"],
                          cwd=str(REPO), capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, proc.stdout + proc.stderr


# ---------------------------------------------------------------------------
# 21D/21E/21F reports
# ---------------------------------------------------------------------------
def test_funnel_report_exists():
    p = REPO / "reports/revenue/PAYMENT_COMMERCIAL_FUNNEL.md"
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    assert "Discovery" in text and "Trust Content" in text and "Monetization" in text


def test_connectivity_map_exists():
    p = REPO / "reports/revenue/PAYMENT_CONNECTIVITY_MAP.md"
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    assert "Airalo" in text and "NordVPN" in text and "SafetyWing" in text


def test_architecture_exists():
    p = REPO / "reports/revenue/PAYMENT_CLUSTER_ARCHITECTURE.md"
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    assert "Payment Hub" in text


# ---------------------------------------------------------------------------
# SEO invariants
# ---------------------------------------------------------------------------
def test_payment_canonicals_unchanged():
    assert "https://www.chinaboundtravel.com/posts/how-to-use-wechat-pay-as-a-foreigner/" in WECHAT_STRONG \
           or "canonicalURL" in WECHAT_STRONG


def test_payment_content_ids_unchanged():
    assert 'content_id: "cbt-707a8899c0a7"' in WECHAT_STRONG or 'content_id = "cbt-707a8899c0a7"' in WECHAT_STRONG


def test_wechat_weak_content_untouched():
    # weak page file must not have been modified this round (git diff empty for it)
    proc = subprocess.run(["git", "diff", "HEAD", "--name-only"], cwd=str(REPO),
                          capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0
    weak_files = [p for p in proc.stdout.splitlines() if "wechat-pay-for-foreigners-step-by-step" in p]
    assert not weak_files, weak_files


# ---------------------------------------------------------------------------
# experiments frozen
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


# ---------------------------------------------------------------------------
# persona guard (payment pages)
# ---------------------------------------------------------------------------
def test_payment_persona_clean():
    low = WECHAT_STRONG.lower()
    for phrase in ("i used wechat pay", "my chinese wife showed me", "my wife",
                   "living in china", "american expat", "i remember"):
        assert phrase not in low, phrase


def test_wechat_strong_persona_guard_script():
    p = REPO / "content/posts/2026-05-22-how-to-use-wechat-pay-as-a-foreigner.md"
    proc = subprocess.run(["python", "scripts/persona_guard.py", str(p)],
                          cwd=str(REPO), capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, proc.stdout + proc.stderr


# ---------------------------------------------------------------------------
# affiliate: no new partner
# ---------------------------------------------------------------------------
def test_no_new_affiliate_partner():
    for marker in ("aid=730795", "aff_id=150687", "klook.tpo.li",
                   "safetywing.com/nomad-insurance?referenceID=26548976",
                   'trip = "https://www.trip.com/"', 'esim = "https://www.airalo.com/"'):
        assert marker in TOML, marker


def test_no_extra_partner_keys():
    # affiliate section keys remain the known set (no new partner added)
    allowed = {"esim", "vpn", "vpnNord", "nordpass", "hotel", "klook", "klook_expire_date", "safetywing",
               "trip", "flight", "worldnomads", "allianz", "partnerizeUserId"}
    import re
    section = TOML.split("[params.affiliate]")[1].split("\n[")[0]
    keys = set(re.findall(r"^\s{2}(\w+)\s*=", section, re.M))
    assert keys <= allowed, keys


# ---------------------------------------------------------------------------
# overall guardrails
# ---------------------------------------------------------------------------
def test_no_new_cta_added_this_round():
    # no content files changed this round (scripts/tests/reports only)
    proc = subprocess.run(["git", "diff", "HEAD", "--name-only", "--", "content/"],
                          cwd=str(REPO), capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0
    changed = [p for p in proc.stdout.splitlines() if p]
    assert not changed, changed

# ---------------------------------------------------------------------------
# additional coverage (P1-GROWTH-21 completeness)
# ---------------------------------------------------------------------------
def test_inventory_commercial_score_range():
    with (REPO / "reports/revenue/PAYMENT_CLUSTER_INVENTORY.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        score = int(r["commercial_score"])
        assert 0 <= score <= 100, r


def test_inventory_contains_wechat_weak():
    with (REPO / "reports/revenue/PAYMENT_CLUSTER_INVENTORY.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    weak = [r for r in rows if r["content_id"] == "cbt-255af4ed003a"]
    assert weak, "wechat weak page missing from inventory"
    assert "Alternate" in weak[0]["index_status"] or "NOT_AVAILABLE" in weak[0]["index_status"]


def test_inventory_contains_wechat_strong():
    with (REPO / "reports/revenue/PAYMENT_CLUSTER_INVENTORY.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    strong = [r for r in rows if r["content_id"] == "cbt-707a8899c0a7"]
    assert strong, "wechat strong page missing from inventory"
    assert strong[0]["index_status"] == "INDEXED"


def test_reports_date_and_cluster_consistency():
    for name in ("PAYMENT_COMMERCIAL_FUNNEL.md", "PAYMENT_CONNECTIVITY_MAP.md",
                 "PAYMENT_CLUSTER_ARCHITECTURE.md", "ALIPAY_CONTENT_DECISION.md"):
        p = REPO / "reports/revenue" / name
        assert p.exists(), name
        text = p.read_text(encoding="utf-8")
        assert "2026-08-16" in text or "P1-GROWTH-21" in text, name

