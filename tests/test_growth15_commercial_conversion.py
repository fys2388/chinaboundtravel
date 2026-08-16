"""P1-GROWTH-15: commercial conversion optimization tests.

Covers (deterministic, no network):
- conversion scoring model (traffic 25 / intent 30 / cta match 25 / gap 15 / risk 5)
- top-3 eligibility (impressions > 50, indexed, commercial query)
- URL dedupe + ground-truth content_id
- REV002 CTA (exactly once, correct placement, Trip.com partner)
- SEO invariants (URL/canonical/content_id/affiliate unchanged)
- persona guard on new CTA copy
- experiment artifacts (registry / baseline / log)
"""
import csv
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from commercial_conversion_engine import (  # noqa: E402
    EXPERIMENT_PAGES, INTENT_WEIGHT, cta_gap_score, cta_match_score,
    eligible_top3, risk_score, traffic_score, build_targets,
    load_true_content_ids, write_targets,
)

POST = (REPO / "content/posts/2026-07-16-china-transportation-complete-guide-trains-subways-taxis-and-more.md")
POST_TEXT = POST.read_text(encoding="utf-8")
TOML = (REPO / "hugo.toml").read_text(encoding="utf-8")

REV002_URL = "https://www.chinaboundtravel.com/posts/china-transportation-complete-guide-trains-subways-taxis-and-more/"
REV002_CID = "cbt-17c6738ffb32"


# ---------------------------------------------------------------------------
# conversion scoring model
# ---------------------------------------------------------------------------
def test_traffic_score_boundaries():
    assert traffic_score(0) == 0
    assert traffic_score(30) == 6
    assert traffic_score(80) == 10
    assert traffic_score(150) == 15
    assert traffic_score(300) == 20
    assert traffic_score(600) == 25


def test_cta_match_and_gap():
    assert cta_match_score({"Trip.com", "Klook"}, "TRAIN") == 25
    assert cta_match_score({"Airalo"}, "TRAIN") == 8
    assert cta_match_score(set(), "TRAIN") == 8
    assert cta_gap_score(set(), "TRAIN") == 15
    assert cta_gap_score({"Airalo"}, "TRAIN") == 8
    assert cta_gap_score({"Trip.com", "Booking", "Klook"}, "TRAIN") == 2


def test_risk_adjustment():
    assert risk_score("cbt-e464169c4991") == 0  # REV001 frozen
    assert risk_score("cbt-17c6738ffb32") == 5  # free page


def test_score_weights():
    assert max(INTENT_WEIGHT.values()) <= 30


# ---------------------------------------------------------------------------
# engine output
# ---------------------------------------------------------------------------
def test_targets_dedupe_urls():
    rows = build_targets()
    urls = [r["url"] for r in rows]
    assert len(urls) == len(set(urls)), "URLs must be deduped"


def test_targets_ground_truth_content_id():
    rows = build_targets()
    rev = next(r for r in rows if r["url"] == REV002_URL)
    assert rev["content_id"] == REV002_CID


def test_eligible_top3_conditions():
    rows = build_targets()
    top3 = eligible_top3(rows)
    assert len(top3) <= 3
    for r in top3:
        assert r["impressions_28d"] > 50
        assert r["indexed_status"] == "INDEXED"
        assert r["commercial_query"] is True
        assert r["content_id"] not in EXPERIMENT_PAGES


def test_transportation_guide_in_top3():
    rows = build_targets()
    top3 = eligible_top3(rows)
    assert any(r["url"] == REV002_URL for r in top3)


def test_targets_csv_schema(tmp_path):
    rows = build_targets()
    out = tmp_path / "targets.csv"
    write_targets(rows, out)
    with out.open(encoding="utf-8") as f:
        written = list(csv.DictReader(f))
    assert len(written) == len(rows)
    fields = ["content_id", "url", "intent", "conversion_score", "commercial_query"]
    for r in written:
        for f in fields:
            assert f in r


def test_true_content_id_map_consistent():
    mapping = load_true_content_ids()
    assert mapping[REV002_URL] == REV002_CID


# ---------------------------------------------------------------------------
# REV002 CTA
# ---------------------------------------------------------------------------
def test_rev002_cta_exists_once():
    assert POST_TEXT.count("affiliate-mid-cta") == 2  # open + close
    assert POST_TEXT.count("transportation-train-tickets-mid") == 1


def test_rev002_partner_trip():
    assert 'partner="trip"' in POST_TEXT
    assert "Trip.com" in POST_TEXT


def test_rev002_placement_after_booking_section():
    buy = POST_TEXT.find("### How to Buy Tickets")
    cta = POST_TEXT.find("transportation-train-tickets-mid")
    station = POST_TEXT.find("### Station Survival Guide")
    assert buy < cta < station


def test_rev002_affiliate_url_unchanged():
    assert 'trip = "https://www.trip.com/"' in TOML


def test_rev002_content_id_and_url_unchanged():
    assert 'content_id = "cbt-17c6738ffb32"' in POST_TEXT
    assert 'slug = "china-transportation-complete-guide-trains-subways-taxis-and-more"' in POST_TEXT


def test_rev002_no_forbidden_persona_phrases():
    low = POST_TEXT.lower()
    for phrase in ("i lived in china", "i remember", "my wife", "american expat",
                   "personally tested", "5 years living in china", "10 years living in china"):
        # the CTA block itself must be clean (existing body phrases are out of scope)
        assert phrase not in POST_TEXT[POST_TEXT.find("affiliate-mid-cta"):]


def test_rev002_artifacts_exist():
    for name in ("REV002_EXPERIMENT_REGISTRY.csv", "REV002_BASELINE.csv", "REV002_EXPERIMENT_LOG.md"):
        assert (REPO / "reports/revenue" / name).exists()


def test_rev002_registry_schema():
    with (REPO / "reports/revenue/REV002_EXPERIMENT_REGISTRY.csv").open(encoding="utf-8") as f:
        row = next(csv.DictReader(f))
    assert row["experiment_id"] == "REV002"
    assert row["content_id"] == REV002_CID
    assert row["status"] == "RUNNING"
    assert row["decision"] == "PENDING"
    assert row["minimum_observation_days"] == "28"


def test_rev002_baseline_schema():
    with (REPO / "reports/revenue/REV002_BASELINE.csv").open(encoding="utf-8") as f:
        row = next(csv.DictReader(f))
    assert row["content_id"] == REV002_CID
    assert row["gsc_clicks"] == "0"
    assert row["revenue"] == "NULL"


def test_rev002_no_drive_change():
    head = (REPO / "layouts/partials/head.html").read_bytes().decode("utf-8", errors="replace")
    assert head.count("emrldtp.com/NTMxNDY5.js?t=531469") == 1
