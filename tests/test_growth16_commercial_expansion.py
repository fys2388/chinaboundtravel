"""P1-GROWTH-16: commercial content expansion tests.

Covers (deterministic, no network, analysis only):
- cluster scoring model (demand 30 / intent 30 / authority 20 / fit 15 / gap 5)
- cluster priority + status (Transportation READY, Payment/Connectivity HOLD)
- expansion decision (12306 KEEP, card/airport CREATE)
- legacy persona commercial risk report
- REV002 protection + SEO invariants
"""
import csv
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from commercial_cluster_expansion import (  # noqa: E402
    authority20, affiliate15, build_cluster_rows, build_expansion_decision,
    build_legacy_risk, demand30, gap5, write_cluster_priority, write_roadmap,
)

MAX = 100
WEIGHTS = {"demand": 30, "intent": 30, "authority": 20, "affiliate": 15, "gap": 5}


# ---------------------------------------------------------------------------
# scoring model
# ---------------------------------------------------------------------------
def test_cluster_weights_sum_100():
    assert sum(WEIGHTS.values()) == MAX


def test_demand30_boundaries():
    assert demand30(0) == 0
    assert demand30(80) == 10
    assert demand30(150) == 15
    assert demand30(250) == 20
    assert demand30(500) == 25
    assert demand30(900) == 30


def test_authority20_boundaries():
    assert authority20(0) == 0
    assert authority20(3) == 20
    assert authority20(8) == 17
    assert authority20(15) == 13
    assert authority20(25) == 9
    assert authority20(40) == 5
    assert authority20(80) == 2


def test_affiliate15_and_gap5():
    assert affiliate15(3, 3) == 15
    assert affiliate15(1, 3) == 10
    assert affiliate15(0, 3) == 0
    assert affiliate15(2, 0) == 0
    assert gap5(0, 3) == 5
    assert gap5(2, 3) == 3
    assert gap5(3, 3) == 0


# ---------------------------------------------------------------------------
# cluster priority
# ---------------------------------------------------------------------------
def test_cluster_priority_schema():
    rows = build_cluster_rows()
    assert len(rows) == 3
    for r in rows:
        for f in ("cluster", "intent", "score", "priority", "status"):
            assert f in r
        assert 0 <= r["score"] <= 100


def test_transportation_top_and_ready():
    rows = build_cluster_rows()
    assert rows[0]["cluster"] == "China Transportation"
    assert rows[0]["priority"] == "A"
    assert rows[0]["status"] == "READY"


def test_payment_hold():
    rows = {r["cluster"]: r for r in build_cluster_rows()}
    assert rows["China Payment"]["status"] == "HOLD"


def test_connectivity_hold():
    rows = {r["cluster"]: r for r in build_cluster_rows()}
    assert rows["China Connectivity"]["status"] == "HOLD"


def test_cluster_csv_reproducible(tmp_path):
    rows = build_cluster_rows()
    out = tmp_path / "c.csv"
    write_cluster_priority(rows, out)
    with out.open(encoding="utf-8") as f:
        written = list(csv.DictReader(f))
    assert len(written) == len(rows)
    assert [r["cluster"] for r in written] == [r["cluster"] for r in rows]


def test_roadmap_artifact(tmp_path):
    rows = build_cluster_rows()
    out = tmp_path / "roadmap.md"
    write_roadmap(rows, out)
    text = out.read_text(encoding="utf-8")
    assert "China Transportation" in text
    assert "P1-GROWTH-17" in text


# ---------------------------------------------------------------------------
# expansion decision
# ---------------------------------------------------------------------------
def test_expansion_decision_12306_keep():
    rows = {r["topic"]: r for r in build_expansion_decision()}
    assert rows["China Railway 12306 App Guide"]["action"] == "KEEP"


def test_expansion_decision_card_now_keep():
    # P1-GROWTH-18 created the card page; decision engine now detects coverage -> KEEP
    rows = {r["topic"]: r for r in build_expansion_decision()}
    assert rows["China Transportation Card"]["action"] == "KEEP"


def test_expansion_decision_airport_now_keep():
    # P1-GROWTH-19 created the airport page; decision engine now detects coverage -> KEEP
    rows = {r["topic"]: r for r in build_expansion_decision()}
    assert rows["China Airport Transfer"]["action"] == "KEEP"


def test_expansion_decision_schema():
    rows = build_expansion_decision()
    assert len(rows) == 3
    for r in rows:
        for f in ("topic", "search_intent", "existing_url", "action", "reason"):
            assert f in r
        assert r["action"] in ("KEEP", "UPDATE", "CREATE", "IGNORE")


# ---------------------------------------------------------------------------
# legacy persona risk
# ---------------------------------------------------------------------------
def test_legacy_risk_schema():
    rows = build_legacy_risk()
    assert rows
    for r in rows:
        assert r["content_id"]
        assert r["url"].startswith("https://www.chinaboundtravel.com")
        assert r["risk"] in ("HIGH", "MED", "LOW")


def test_transportation_high_risk_detected():
    """transportation 文章已通过 2.0 内容优化合规（PersonaGuard 无违规）。

    原为 HIGH（含 legacy 第一人称内容）；经 content_deep_optimizer 等
    优化后违规已清除，应为 LOW。检测逻辑本身仍需覆盖该文章。
    """
    rows = build_legacy_risk()
    trans = [r for r in rows if "china-transportation-complete-guide" in r["url"]]
    assert trans and trans[0]["risk"] == "LOW"
    assert trans[0]["violations"] == 0


def test_risk_report_artifact():
    text = (REPO / "reports/revenue/LEGACY_COMMERCIAL_RISK_REPORT.md").read_text(encoding="utf-8")
    assert "ANALYSIS ONLY" in text
    assert "HIGH" in text


# ---------------------------------------------------------------------------
# REV002 protection + invariants
# ---------------------------------------------------------------------------
def test_rev002_still_running():
    with (REPO / "reports/revenue/REV002_EXPERIMENT_REGISTRY.csv").open(encoding="utf-8") as f:
        row = next(csv.DictReader(f))
    assert row["status"] == "RUNNING"
    assert row["minimum_observation_days"] == "28"


def test_rev002_cta_not_modified():
    post = (REPO / "content/posts/2026-07-16-china-transportation-complete-guide-trains-subways-taxis-and-more.md")
    text = post.read_text(encoding="utf-8")
    assert text.count("transportation-train-tickets-mid") == 1


def test_drive_and_ga4_unchanged():
    head = (REPO / "layouts/partials/head.html").read_bytes().decode("utf-8", errors="replace")
    single = (REPO / "layouts/_default/single.html").read_bytes().decode("gbk", errors="replace")
    assert head.count("emrldtp.com/NTMxNDY5.js?t=531469") == 1
    for ev in ("affiliate_impression", "affiliate_click", "affiliate_outbound"):
        assert ev in single


def test_affiliate_urls_unchanged():
    toml = (REPO / "hugo.toml").read_text(encoding="utf-8")
    for marker in ("aid=730795", "aff_id=150687", "klook.tpo.li", "safetywing.com/nomad-insurance?referenceID=26548976",
                   'trip = "https://www.trip.com/"'):
        assert marker in toml
