"""P1-GROWTH-17: transportation commercial content release tests.

Covers (deterministic, no network):
- 17A persona migration on transportation guide (no forbidden first-person,
  trust layer present, SEO invariants intact, REV002 CTA untouched)
- 17B REV003 registration (PENDING, variants defined, REV002 freeze)
- 17C release decision (CREATE_ONE + HOLD)
- global invariants (affiliate URLs, Drive exactly 1, GA4 schema, content_id)
"""
import csv
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from commercial_content_release import build_release_decision  # noqa: E402

POST = (REPO / "content/posts/2026-07-16-china-transportation-complete-guide-trains-subways-taxis-and-more.md")
POST_TEXT = POST.read_text(encoding="utf-8")
TOML = (REPO / "hugo.toml").read_text(encoding="utf-8")
SINGLE = (REPO / "layouts/_default/single.html").read_bytes().decode("gbk", errors="replace")
HEAD = (REPO / "layouts/partials/head.html").read_bytes().decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# 17A persona migration
# ---------------------------------------------------------------------------
def test_no_forbidden_first_person_phrases():
    low = POST_TEXT.lower()
    for phrase in ("i remember my first", "i have ridden all three classes",
                   "common mistakes i have made", "i used trip.com exclusively",
                   "my wife", "american expat", "personally tested",
                   "i lived in china", "five years later, i book"):
        assert phrase not in low, phrase


def test_editorial_replacement_present():
    assert "Here is a practical comparison" in POST_TEXT
    assert "ChinaBound Travel's recommendation" in POST_TEXT
    assert "Common Mistakes First-Time Travelers Make" in POST_TEXT


def test_trust_layer_present():
    assert "Recommended Booking Options for Foreign Travelers" in POST_TEXT
    assert "**A. Trip.com**" in POST_TEXT
    assert "**B. 12306 (official app)**" in POST_TEXT
    assert "**C. Klook**" in POST_TEXT
    assert "comparison layer" in POST_TEXT


def test_front_matter_unchanged():
    assert 'content_id = "cbt-17c6738ffb32"' in POST_TEXT
    assert 'slug = "china-transportation-complete-guide-trains-subways-taxis-and-more"' in POST_TEXT
    assert 'date = 2026-07-16' in POST_TEXT
    assert "china-transportation-complete-guide-trains-subways-taxis-and-more" in POST_TEXT


def test_rev002_cta_untouched():
    assert POST_TEXT.count("transportation-train-tickets-mid") == 1
    assert POST_TEXT.count("affiliate-mid-cta") == 2


def test_persona_guard_passes():
    import subprocess
    proc = subprocess.run(["python", "scripts/persona_guard.py", str(POST)],
                          cwd=str(REPO), capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, proc.stdout + proc.stderr


# ---------------------------------------------------------------------------
# 17B REV003
# ---------------------------------------------------------------------------
def test_rev003_registry_pending():
    with (REPO / "reports/revenue/REV003_EXPERIMENT_REGISTRY.csv").open(encoding="utf-8") as f:
        row = next(csv.DictReader(f))
    assert row["experiment_id"] == "REV003"
    assert row["status"] == "PENDING"
    assert row["experiment_type"] == "CTA_COPY"
    assert row["content_id"] == "cbt-17c6738ffb32"


def test_rev003_log_defines_variants():
    log = (REPO / "reports/revenue/REV003_EXPERIMENT_LOG.md").read_text(encoding="utf-8")
    assert "Book China Train Tickets Online" in log
    assert "Compare China Train Tickets & Routes" in log
    assert "PENDING" in log
    assert "2026-09-13" in log


def test_rev003_no_cta_change():
    # copy variant must not have touched the REV002 CTA copy
    assert "Compare Train Tickets on Trip.com" in POST_TEXT


# ---------------------------------------------------------------------------
# 17C release decision
# ---------------------------------------------------------------------------
def test_release_decision_one_create_one_hold():
    rows = build_release_decision()
    actions = {r["action"] for r in rows}
    assert actions == {"CREATE_ONE", "HOLD"}


def test_release_card_first():
    rows = build_release_decision()
    assert rows[0]["topic"] == "China Transportation Card"
    assert rows[0]["action"] == "CREATE_ONE"
    assert rows[1]["topic"] == "China Airport Transfer"
    assert rows[1]["action"] == "HOLD"


def test_release_decision_schema():
    rows = build_release_decision()
    for r in rows:
        for f in ("topic", "partner", "existing_pages", "impressions_28d", "score", "action"):
            assert f in r


# ---------------------------------------------------------------------------
# invariants
# ---------------------------------------------------------------------------
def test_affiliate_urls_unchanged():
    for marker in ("aid=730795", "aff_id=150687", "klook.tpo.li",
                   "safetywing.com/nomad-insurance?referenceID=26548976",
                   'trip = "https://www.trip.com/"'):
        assert marker in TOML


def test_drive_exactly_once():
    assert HEAD.count("emrldtp.com/NTMxNDY5.js?t=531469") == 1


def test_ga4_schema_unchanged():
    for ev in ("affiliate_impression", "affiliate_click", "affiliate_outbound"):
        assert ev in SINGLE
    assert "gtag('event', 'affiliate_click', eventParams)" in SINGLE


def test_content_ids_57():
    import subprocess
    proc = subprocess.run(["python", "scripts/content_id_audit.py", "audit", "--strict"],
                          cwd=str(REPO), capture_output=True, text=True, encoding="utf-8")
    assert "RESULT: PASS" in proc.stdout
    assert "With content_id: 58" in proc.stdout


def test_no_utms_added_in_post():
    assert "utm_" not in POST_TEXT.split("+++")[2]  # body has no utm params
