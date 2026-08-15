"""P1-GROWTH-03: tests for the content opportunity engine.

Covers the required checklist:
- score bounds 0-100
- tier boundaries
- indexing score
- business intent
- low CTR
- near page 1
- not indexed
- high impression zero click
- deterministic output
- no LLM dependency
"""
import json
import subprocess
import sys
from pathlib import Path

from content_opportunity_engine import (
    BUSINESS_SCORE,
    classify_text,
    demand_score,
    gap_score,
    indexing_score,
    performance_score,
    primary_action,
    tier_of,
)

REPO = Path(__file__).resolve().parent.parent
SEO = REPO / "reports" / "seo"


def _row(**kw):
    base = {
        "indexed_status": "INDEXED",
        "impressions_28d": 0,
        "clicks_28d": 0,
        "ctr_28d": 0.0,
        "position_28d": 0.0,
        "query_count": 0,
        "business_value": "LOW",
    }
    base.update(kw)
    return base


def test_score_bounds_0_100():
    # max scenario: indexed + 500+ impressions + perfect position + high business + max gap
    for status, imp, pos, ctr, clicks, qcount in [
        ("INDEXED", 600, 2.0, 0.12, 5, 8),
        ("INDEXED", 0, 0.0, 0.0, 0, 0),
        ("NOT_INDEXED", 0, 0.0, 0.0, 0, 0),
        ("UNKNOWN", 55, 15.0, 0.02, 1, 3),
    ]:
        s = (indexing_score(status) + demand_score(imp)
             + performance_score(pos, ctr, clicks)
             + BUSINESS_SCORE["HIGH"]
             + gap_score(imp, pos, clicks, qcount))
        assert 0 <= s <= 100


def test_tier_boundaries():
    assert tier_of(100) == "A"
    assert tier_of(80) == "A"
    assert tier_of(79) == "B"
    assert tier_of(60) == "B"
    assert tier_of(59) == "C"
    assert tier_of(40) == "C"
    assert tier_of(39) == "D"
    assert tier_of(0) == "D"


def test_indexing_score():
    assert indexing_score("INDEXED") == 20
    assert indexing_score("Submitted and indexed") == 0  # normalized statuses only
    assert indexing_score("UNKNOWN") == 10
    assert indexing_score("") == 10
    assert indexing_score("NOT_INDEXED") == 0
    assert indexing_score("Page with redirect") == 0


def test_business_intent():
    assert classify_text("wechat pay for foreigners") == "PAYMENT"
    assert classify_text("144 hour visa") == "VISA"
    assert classify_text("esim china") == "INTERNET"
    assert classify_text("high speed rail tickets") == "TRANSPORT"
    assert classify_text("beijing") == "CITY"
    assert BUSINESS_SCORE["HIGH"] == 20
    assert BUSINESS_SCORE["MEDIUM"] == 12
    assert BUSINESS_SCORE["LOW"] == 6


def test_low_ctr_action():
    row = _row(impressions_28d=150, ctr_28d=0.01, position_28d=30.0, business_value="MEDIUM")
    assert primary_action(row) == "TITLE_TEST"


def test_near_page_1_action():
    row = _row(impressions_28d=80, ctr_28d=0.03, position_28d=7.0, clicks_28d=1)
    assert primary_action(row) == "CONTENT_UPDATE"


def test_not_indexed_action():
    row = _row(indexed_status="NOT_INDEXED", impressions_28d=200)
    assert primary_action(row) == "INDEX_FIX"


def test_high_impression_zero_click():
    row = _row(impressions_28d=120, clicks_28d=0, ctr_28d=0.0, position_28d=22.0)
    assert primary_action(row) == "TITLE_TEST"


def test_demand_tiers():
    assert demand_score(0) == 0
    assert demand_score(1) == 10
    assert demand_score(49) == 10
    assert demand_score(50) == 15
    assert demand_score(99) == 15
    assert demand_score(100) == 20
    assert demand_score(499) == 20
    assert demand_score(500) == 25


def test_deterministic_output():
    """Running the engine twice yields byte-identical JSON and CSV."""
    out1 = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "content_opportunity_engine.py"),
         "--out-dir", str(SEO)],
        cwd=str(REPO), capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert out1.returncode == 0, out1.stderr[-2000:]
    feed1 = (SEO / "CONTENT_OPPORTUNITY_FEED.json").read_bytes()
    csv1 = (SEO / "content_opportunity_scores.csv").read_bytes()
    out2 = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "content_opportunity_engine.py"),
         "--out-dir", str(SEO)],
        cwd=str(REPO), capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert out2.returncode == 0, out2.stderr[-2000:]
    assert (SEO / "CONTENT_OPPORTUNITY_FEED.json").read_bytes() == feed1
    assert (SEO / "content_opportunity_scores.csv").read_bytes() == csv1


def test_feed_schema_stable_and_parseable():
    feed = json.loads((SEO / "CONTENT_OPPORTUNITY_FEED.json").read_text(encoding="utf-8"))
    assert isinstance(feed, list) and feed
    for item in feed:
        for field in ("content_id", "url", "opportunity_score", "tier", "action",
                      "evidence", "business_intent", "index_status"):
            assert field in item, field
        assert 0 <= item["opportunity_score"] <= 100
        assert item["tier"] in ("A", "B", "C", "D")
        assert item["action"] in (
            "INDEX_FIX", "TITLE_TEST", "META_TEST", "CONTENT_UPDATE",
            "CONTENT_EXPANSION", "INTERNAL_LINK", "FAQ_EXPANSION",
            "COMMERCIAL_OPTIMIZATION", "MONITOR")


def test_no_llm_dependency():
    src = (REPO / "scripts" / "content_opportunity_engine.py").read_text(encoding="utf-8")
    for banned in ("openai", "anthropic", "requests", "urllib", "httpx"):
        assert banned not in src, banned


def test_tier_a_report_has_data_rows():
    """Regression: Tier A report must contain ranked data rows even when no
    article reaches the 80+ threshold (pipeline lists top 20 instead)."""
    out = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "content_opportunity_engine.py"),
         "--out-dir", str(SEO)],
        cwd=str(REPO), capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert out.returncode == 0, out.stderr[-2000:]
    text = (SEO / "TIER_A_CONTENT_OPPORTUNITIES.md").read_text(encoding="utf-8")
    data_rows = [ln for ln in text.splitlines()
                 if ln.startswith("| ") and ln.split("|")[1].strip().isdigit()]
    assert len(data_rows) >= 1, "TIER_A report contains no ranked data rows"
