"""P1-GROWTH-11: Revenue Opportunity Engine tests.

Covers (pure/deterministic, no network, no LLM):
- score bounds 0-100
- commercial intent tiers and scoring
- data confidence factor (small-sample guard)
- conversion gap rules
- primary action rules (MEASURE_MORE / MONITOR on low confidence)
- deterministic sorting / tie-breaker
- revenue stays NULL (REVENUE_NOT_AVAILABLE)
- drive active flag flows through scored rows
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import revenue_opportunity_engine as roe


def sample_row(**overrides):
    row = {
        "content_id": "cbt-test0001",
        "url": "https://www.chinaboundtravel.com/posts/test/",
        "title": "Test",
        "section": "posts",
        "impressions_28d": 100.0,
        "clicks_28d": 0.0,
        "gsc_clicks_28d": 0.0,
        "position_28d": 10.0,
        "affiliate_clicks_28d": 0.0,
        "partner_count": 1,
        "has_affiliate": True,
        "commercial_intent": "VISA",
        "business_intent": "VISA",
        "indexed_status": "INDEXED",
        "seo_opportunity_score": 60.0,
    }
    row.update(overrides)
    return row


# ---------------------------------------------------------------------------
# Score bounds
# ---------------------------------------------------------------------------
def test_score_bounds_0_100():
    for intent in ("VISA", "GENERAL", "FOOD", "HOTEL"):
        comp = roe.compute_score(sample_row(commercial_intent=intent))
        assert 0.0 <= comp["score"] <= 100.0
        assert comp["tier"] in ("A", "B", "C", "D")


def test_score_never_exceeds_100():
    comp = roe.compute_score(sample_row(impressions_28d=99999, gsc_clicks_28d=500))
    assert comp["score"] <= 100.0


# ---------------------------------------------------------------------------
# Commercial intent
# ---------------------------------------------------------------------------
def test_intent_tiers():
    assert roe.intent_tier("VISA") == "HIGH"
    assert roe.intent_tier("train") == "HIGH"
    assert roe.intent_tier("FOOD") == "MEDIUM"
    assert roe.intent_tier("CITY") == "MEDIUM"
    assert roe.intent_tier("GENERAL") == "LOW"
    assert roe.intent_tier("") == "LOW"


def test_commercial_intent_score_values():
    assert roe.commercial_intent_score("VISA") == 20.0
    assert roe.commercial_intent_score("FOOD") == 12.0
    assert roe.commercial_intent_score("GENERAL") == 5.0


def test_high_intent_scores_above_low():
    high = roe.compute_score(sample_row(commercial_intent="VISA"))
    low = roe.compute_score(sample_row(commercial_intent="GENERAL"))
    assert high["score"] > low["score"]


# ---------------------------------------------------------------------------
# Data confidence / small-sample guard
# ---------------------------------------------------------------------------
def test_confidence_factor_small_sample():
    assert roe.confidence_factor(100, 0, 0) < 1.0
    assert roe.confidence_factor(100, 0, 0) <= 0.85 * 0.95


def test_confidence_factor_high_sample():
    # site-wide dampener (sessions<500) caps even high-sample pages at 0.95
    assert roe.confidence_factor(1000, 30, 0) == 0.95
    assert roe.confidence_factor(1000, 30, 0) == roe.confidence_factor(2000, 30, 20)


def test_low_confidence_forces_measure_more():
    # imp<20 + zero clicks => small-sample guard, even though confidence >= 50%
    comp = roe.compute_score(sample_row(impressions_28d=5, gsc_clicks_28d=0))
    assert roe.primary_action(sample_row(impressions_28d=5), comp) == "MEASURE_MORE"
    # sub-50% confidence path (imp=0 after dampener) => MONITOR
    comp0 = roe.compute_score(sample_row(impressions_28d=0))
    assert comp0["confidence"] < 50.0


def test_zero_impressions_forces_monitor():
    comp = roe.compute_score(sample_row(impressions_28d=0))
    assert roe.primary_action(sample_row(impressions_28d=0), comp) == "MONITOR"


# ---------------------------------------------------------------------------
# Conversion gap
# ---------------------------------------------------------------------------
def test_conversion_gap_high_impressions_zero_affiliate_clicks():
    s = roe.conversion_gap_score(100, 0, 0, True, "VISA")
    assert s >= 5.0


def test_conversion_gap_high_intent_missing_affiliate():
    s = roe.conversion_gap_score(100, 1, 0, False, "HOTEL")
    assert s >= 5.0


def test_conversion_gap_zero_for_low_intent_no_data():
    assert roe.conversion_gap_score(0, 0, 0, False, "GENERAL") == 0.0


# ---------------------------------------------------------------------------
# Primary actions
# ---------------------------------------------------------------------------
def test_primary_action_affiliate_placement_high_intent():
    row = sample_row(commercial_intent="VPN", has_affiliate=False, partner_count=0,
                     impressions_28d=120, gsc_clicks_28d=1)
    comp = roe.compute_score(row)
    assert comp["confidence"] >= 50.0
    assert roe.primary_action(row, comp) == "AFFILIATE_PLACEMENT"


def test_primary_action_cta_optimization():
    row = sample_row(commercial_intent="VISA", impressions_28d=150, gsc_clicks_28d=0)
    comp = roe.compute_score(row)
    assert roe.primary_action(row, comp) == "CTA_OPTIMIZATION"


def test_primary_action_commercialization():
    row = sample_row(commercial_intent="TRAIN", impressions_28d=150, gsc_clicks_28d=2)
    comp = roe.compute_score(row)
    assert roe.primary_action(row, comp) == "CONTENT_COMMERCIALIZATION"


def test_primary_action_internal_link_when_not_indexed():
    row = sample_row(indexed_status="NOT_INDEXED", impressions_28d=60, gsc_clicks_28d=1)
    comp = roe.compute_score(row)
    assert roe.primary_action(row, comp) == "INTERNAL_LINK"


# ---------------------------------------------------------------------------
# Revenue NULL / Drive
# ---------------------------------------------------------------------------
def test_revenue_never_fabricated():
    rows = roe.build_rows([sample_row()], [], [], [])
    assert rows[0]["revenue"] == "NULL"
    assert rows[0]["revenue_status"] == "REVENUE_NOT_AVAILABLE"


def test_drive_active_flag_present():
    rows = roe.build_rows([sample_row()], [], [], [])
    assert rows[0]["drive_active"] is True


def test_build_scored_adds_score_fields():
    rows = roe.build_rows([sample_row()], [], [], [])
    scored = roe.build_scored(rows)
    r = scored[0]
    assert "revenue_opportunity_score" in r
    assert "data_confidence_pct" in r
    assert "tier" in r
    assert "primary_action" in r


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------
def test_deterministic_sorting_and_tie_breaker():
    a = sample_row(content_id="cbt-aaa", url="https://www.chinaboundtravel.com/posts/aaa/",
                   impressions_28d=100, commercial_intent="VISA")
    b = sample_row(content_id="cbt-bbb", url="https://www.chinaboundtravel.com/posts/bbb/",
                   impressions_28d=100, commercial_intent="VISA")
    rows = roe.build_rows([b, a], [], [], [])
    s1 = roe.build_scored(rows)
    s2 = roe.build_scored(rows)
    assert [r["content_id"] for r in s1] == [r["content_id"] for r in s2]
    assert [r["content_id"] for r in s1] == ["cbt-aaa", "cbt-bbb"]  # url tie-breaker


def test_deterministic_high_intent_first():
    # intent is read from PRE_DRIVE_BASELINE (pre), not from seo_inv rows
    pre = [
        {"content_id": "cbt-high", "commercial_intent": "VISA", "affiliate_clicks_28d": 0,
         "gsc_clicks_28d": 0, "gsc_impressions_28d": 120},
        {"content_id": "cbt-low", "commercial_intent": "GENERAL", "affiliate_clicks_28d": 0,
         "gsc_clicks_28d": 0, "gsc_impressions_28d": 120},
    ]
    high = sample_row(content_id="cbt-high", impressions_28d=120)
    low = sample_row(content_id="cbt-low", impressions_28d=120)
    s = roe.build_scored(roe.build_rows([low, high], [], [], pre))
    assert s[0]["content_id"] == "cbt-high"
