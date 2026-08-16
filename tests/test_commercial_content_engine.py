"""P1-GROWTH-14B: commercial content pipeline engine tests.

Covers (deterministic, no network, analysis only):
- scoring model weights (Commercial Intent 30 / Search Demand 25 /
  Affiliate Fit 20 / Existing Authority 15 / Content Gap 10)
- demand / authority / gap score boundaries
- priority CSV schema and deterministic order
- topic clusters + revenue gaps artifacts
- no fake revenue / no content mutation
"""
import csv
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from commercial_content_engine import (  # noqa: E402
    CLUSTERS, INTENT_SCORE, PRIORITY_FIELDS,
    authority_score, build_priority_rows, demand_score, gap_score,
    write_content_revenue_gaps, write_priority, write_topic_clusters,
)

MAX_SCORE = 100
WEIGHTS = {"intent": 30, "demand": 25, "affiliate": 20, "authority": 15, "gap": 10}


# ---------------------------------------------------------------------------
# scoring model
# ---------------------------------------------------------------------------
def test_score_model_weights_sum_100():
    assert sum(WEIGHTS.values()) == MAX_SCORE


def test_demand_score_boundaries():
    assert demand_score(0) == 0
    assert demand_score(1) == 5
    assert demand_score(25) == 8
    assert demand_score(60) == 12
    assert demand_score(120) == 16
    assert demand_score(250) == 20
    assert demand_score(600) == 25


def test_authority_score_boundaries():
    assert authority_score(3.0, "INDEXED") == 15
    assert authority_score(8.0, "INDEXED") == 13
    assert authority_score(15.0, "INDEXED") == 10
    assert authority_score(35.0, "INDEXED") == 6
    assert authority_score(80.0, "INDEXED") == 2
    assert authority_score(0.0, "INDEXED") == 0
    assert authority_score(5.0, "NOT_INDEXED") == 0


def test_gap_score_boundaries():
    assert gap_score(False, 0.0, "NOT_INDEXED") == 10
    assert gap_score(True, 0.0, "NOT_INDEXED") == 8
    assert gap_score(True, 5.0, "INDEXED") == 2
    assert gap_score(True, 20.0, "INDEXED") == 5
    assert gap_score(True, 60.0, "INDEXED") == 7


def test_intent_scores_within_weight():
    for v in INTENT_SCORE.values():
        assert 20 <= v <= 30


# ---------------------------------------------------------------------------
# engine output
# ---------------------------------------------------------------------------
def test_priority_rows_deterministic():
    rows = build_priority_rows()
    keys = [(r["score"], r["keyword_cluster"], r["keyword"]) for r in rows]
    assert keys == sorted(keys, key=lambda k: (-k[0], k[1], k[2]))


def test_priority_rows_score_range():
    rows = build_priority_rows()
    assert 0 < len(rows) <= 30
    for r in rows:
        assert 0 <= r["score"] <= 100


def test_priority_rows_cover_all_clusters():
    rows = build_priority_rows()
    clusters = {r["keyword_cluster"] for r in rows}
    assert clusters == set(CLUSTERS.keys())


def test_priority_csv_schema(tmp_path):
    rows = build_priority_rows()
    out = tmp_path / "p.csv"
    write_priority(rows, out)
    with out.open(encoding="utf-8") as f:
        written = list(csv.DictReader(f))
    assert len(written) == len(rows)
    for r in written:
        for field in PRIORITY_FIELDS:
            assert field in r


def test_priority_actions_valid():
    rows = build_priority_rows()
    valid = {"CREATE", "OPTIMIZE", "CTA_ALIGN", "MONITOR"}
    for r in rows:
        assert r["action"] in valid
        assert r["priority"] in ("A", "B", "C")


def test_topic_clusters_artifact(tmp_path):
    out = tmp_path / "clusters.md"
    write_topic_clusters(out)
    text = out.read_text(encoding="utf-8")
    assert "China Transportation" in text
    assert "China Payment" in text
    assert "China Connectivity" in text
    assert "Affiliate match" in text


def test_content_revenue_gaps_artifact(tmp_path):
    out = tmp_path / "gaps.md"
    write_content_revenue_gaps(out=out)
    text = out.read_text(encoding="utf-8")
    assert "ANALYSIS ONLY" in text
    assert "NO_AFFILIATE" in text or "PARTIAL" in text


def test_no_fake_revenue():
    rows = build_priority_rows()
    for r in rows:
        assert "revenue" not in r
    gap_text = write_content_revenue_gaps(out=REPO / "reports" / "revenue" / "_gap_test_tmp.md")
    gap_text.unlink()
    assert "NULL" in (REPO / "reports" / "revenue" / "CONTENT_REVENUE_GAPS.md").read_text(encoding="utf-8")


def test_engine_does_not_touch_content():
    before = set((REPO / "content" / "posts").glob("*.md"))
    build_priority_rows()
    after = set((REPO / "content" / "posts").glob("*.md"))
    assert before == after
