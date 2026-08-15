"""P1-GROWTH-04: tests for the content prioritization engine.

Covers:
- technical > content (canonical / index recovery outranks title tweaks)
- indexed vs not indexed
- commercial weighting
- low data guard (Rule F)
- deterministic sorting
- tie breaker
- score bounds 0-100
- forced rules A/B
"""
import csv
import json
import subprocess
import sys
from pathlib import Path

from content_priority_engine import (
    business_intent_score,
    effort_of,
    execution_ease_score,
    expected_impact_score,
    primary_action,
    risk_score,
    score_item,
    search_demand_score,
    seo_opportunity_score,
    technical_urgency_score,
    tier_of_score,
)

REPO = Path(__file__).resolve().parent.parent
SEO = REPO / "reports" / "seo"


def _row(**kw):
    base = {
        "content_id": "cbt-test0001",
        "url": "https://www.chinaboundtravel.com/posts/test-page/",
        "opportunity_score": 50.0,
        "tier": "C",
        "action": "MONITOR",
        "business_intent": "TRAVEL_GUIDE",
        "index_status": "INDEXED",
        "queries": [],
        "query_count": 0,
        "impressions_28d": 10,
        "clicks_28d": 0,
        "ctr_28d": 0.0,
        "avg_position": 30.0,
        "indexed_status": "INDEXED",
    }
    base.update(kw)
    return base


def test_score_bounds_0_100():
    r = score_item(_row(), {}, {})
    assert 0 <= r["priority_score"] <= 100


def test_technical_beats_content():
    """Rule A: canonical HIGH must outrank a pure title/meta optimization."""
    tech = score_item(
        _row(content_id="cbt-can001", impressions_28d=5),
        {"/posts/test-page": "HIGH"}, {})
    content = score_item(
        _row(content_id="cbt-title001", impressions_28d=200, avg_position=8.0),
        {}, {})
    assert tech["priority_score"] >= 85            # Rule A floor
    assert tech["primary_action"] == "TECHNICAL_FIX"
    assert tech["priority_score"] > content["priority_score"]


def test_indexed_vs_not_indexed():
    """Not indexed + commercial intent must floor at 80 (Rule B)."""
    ni = score_item(
        _row(content_id="cbt-ni001", index_status="NOT_INDEXED",
             indexed_status="NOT_INDEXED", business_intent="PAYMENT"),
        {}, {"cbt-ni001": "Excluded by noindex tag"})
    idx = score_item(
        _row(content_id="cbt-ix001", index_status="INDEXED"),
        {}, {})
    assert ni["priority_score"] >= 80
    assert ni["primary_action"] == "INDEX_RECOVERY"
    assert ni["priority_score"] > idx["priority_score"]
    assert technical_urgency_score("NOT_INDEXED", "", "noindex") >            technical_urgency_score("INDEXED", "", "")


def test_commercial_weighting():
    """Commercial intent boosts priority and action classification."""
    visa = score_item(
        _row(content_id="cbt-v001", business_intent="VISA", impressions_28d=120,
             avg_position=12.0),
        {}, {})
    other = score_item(
        _row(content_id="cbt-o001", business_intent="TRAVEL_GUIDE", impressions_28d=120,
             avg_position=12.0),
        {}, {})
    assert business_intent_score("VISA", "HIGH") > business_intent_score("TRAVEL_GUIDE", "MEDIUM")
    assert visa["priority_score"] >= other["priority_score"]
    assert visa["primary_action"] in ("COMMERCIAL_OPTIMIZATION", "CONTENT_REFRESH", "TITLE_META_UPDATE")


def test_low_data_guard():
    """Rule F: tiny impression samples must not inflate priority."""
    low = score_item(
        _row(content_id="cbt-low001", impressions_28d=3, avg_position=6.0),
        {}, {})
    assert low["priority_score"] <= 60
    assert "RULE_F_LOW_DATA_CAP" in low["rule_flags"]
    assert expected_impact_score(6.0, 3, 0) <= 4.0


def test_deterministic_output():
    """Running the engine twice yields identical bytes for all outputs."""
    out1 = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "content_priority_engine.py"),
         "--out-dir", str(SEO)],
        cwd=str(REPO), capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert out1.returncode == 0, out1.stderr[-2000:]
    bytes1 = {
        name: (SEO / name).read_bytes()
        for name in ("TOP_10_CONTENT_PRIORITIES.md", "CONTENT_EXECUTION_BATCHES.md",
                     "FIRST_CONTENT_REVIEW_QUEUE.csv", "TOP_5_COMMERCIAL_PAGES.md",
                     "TOP_5_NEW_CONTENT_IDEAS.md", "CONTENT_DO_NOT_DO_YET.md")
    }
    out2 = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "content_priority_engine.py"),
         "--out-dir", str(SEO)],
        cwd=str(REPO), capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert out2.returncode == 0, out2.stderr[-2000:]
    for name, data in bytes1.items():
        assert (SEO / name).read_bytes() == data, name


def test_tie_breaker_deterministic():
    """Equal scores sort by impressions desc, then opportunity desc, then content_id."""
    a = score_item(_row(content_id="cbt-aaa", impressions_28d=50, business_intent="VISA"), {}, {})
    b = score_item(_row(content_id="cbt-bbb", impressions_28d=50, business_intent="VISA"), {}, {})
    # after manual sort with same comparator as engine
    rows = sorted([a, b], key=lambda r: (-r["priority_score"], -r["impressions_28d"],
                                         -r["opportunity_score"], r["content_id"]))
    assert [r["content_id"] for r in rows] == ["cbt-aaa", "cbt-bbb"]


def test_artifacts_exist_and_parseable():
    top10 = (SEO / "TOP_10_CONTENT_PRIORITIES.md").read_text(encoding="utf-8")
    rows = [ln for ln in top10.splitlines() if ln.startswith("| ") and
            ln.split("|")[1].strip().isdigit()]
    assert len(rows) == 10
    queue = list(csv.DictReader(open(SEO / "FIRST_CONTENT_REVIEW_QUEUE.csv", encoding="utf-8")))
    assert len(queue) == 10
    for row in queue:
        assert row["review_status"] == "PENDING"
        assert row["content_id"]
    dnd = (SEO / "CONTENT_DO_NOT_DO_YET.md").read_text(encoding="utf-8")
    for guard in ("bulk-edit", "3 clicks", "affiliate", "legacy persona"):
        assert guard in dnd


def test_rule_a_canonical_floor():
    r = score_item(_row(content_id="cbt-c001"), {"/posts/test-page": "HIGH"}, {})
    assert r["priority_score"] >= 85
    assert "RULE_A_CANONICAL_HIGH" in r["rule_flags"]


def test_rule_f_low_data_not_indexed_exemption():
    """Rule F cap does not apply when a technical rule already raised priority."""
    r = score_item(
        _row(content_id="cbt-c002", impressions_28d=2, index_status="NOT_INDEXED",
             indexed_status="NOT_INDEXED", business_intent="PAYMENT"),
        {}, {"cbt-c002": "URL unknown to Google"})
    assert r["priority_score"] >= 80  # Rule B wins, not capped by Rule F


def test_helpers():
    assert 0 <= seo_opportunity_score(100) <= 25
    assert search_demand_score(600, 10) == 20
    assert search_demand_score(0, 0) == 2
    assert execution_ease_score("TITLE_META_UPDATE") > execution_ease_score("NEW_CONTENT")
    assert effort_of("NEW_CONTENT") == "L"
    assert effort_of("TITLE_META_UPDATE") == "S"
    assert risk_score("INTERNAL_LINK", 100) > risk_score("NEW_CONTENT", 100)
    assert tier_of_score(88) == "P0"
    assert tier_of_score(30) == "P4"
    assert primary_action(_row(impressions_28d=200, ctr_28d=0.01, avg_position=10.0), "", "") in (
        "TITLE_META_UPDATE", "CONTENT_REFRESH")


def test_no_llm_dependency():
    src = (REPO / "scripts" / "content_priority_engine.py").read_text(encoding="utf-8")
    for banned in ("openai", "anthropic", "import requests", "requests.post",
                      "requests.get", "urllib", "httpx"):
        assert banned not in src, banned
