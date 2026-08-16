"""P1-GROWTH-08: growth validation engine tests.

Covers (pure functions, no network):
- insufficient sample guard (clicks < 20)
- CTR / impression / click / position deltas
- indexing state classification (INDEXED / WAITING_RECRAWL / NOT_INDEXED incl. noindex)
- deterministic comparison of query sets (NEW / EMERGING / LOST)
- impact score bounds and determinism
- cached-data fallback matching (absolute + relative aliases, legacy dated URL)
"""
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import growth_validation as gv


# ---------------------------------------------------------------------------
# Low sample guard
# ---------------------------------------------------------------------------
def test_low_sample_guard_insufficient():
    assert gv.low_sample_guard(0) == "INSUFFICIENT_SAMPLE"
    assert gv.low_sample_guard(19.9) == "INSUFFICIENT_SAMPLE"


def test_low_sample_guard_ok():
    assert gv.low_sample_guard(20) == "OK"
    assert gv.low_sample_guard(50) == "OK"


# ---------------------------------------------------------------------------
# Delta computation
# ---------------------------------------------------------------------------
def test_compute_deltas_ctr_positive():
    d = gv.compute_deltas(
        {"impressions": 100, "clicks": 1, "ctr": 0.01, "position": 20},
        {"impressions": 100, "clicks": 4, "ctr": 0.04, "position": 15},
    )
    assert d["ctr_delta"] == pytest.approx(0.03)
    assert d["ctr_delta_pct"] == pytest.approx(300.0)
    assert d["position_delta"] == pytest.approx(-5.0)
    assert d["clicks_delta"] == 3


def test_compute_deltas_position_improvement_is_negative_delta():
    d = gv.compute_deltas(
        {"impressions": 50, "clicks": 0, "ctr": 0, "position": 40},
        {"impressions": 60, "clicks": 0, "ctr": 0, "position": 12},
    )
    assert d["position_delta"] < 0  # rising rank -> smaller position number


def test_compute_deltas_zero_baseline_pct_none():
    d = gv.compute_deltas(
        {"impressions": 0, "clicks": 0, "ctr": 0, "position": 0},
        {"impressions": 10, "clicks": 0, "ctr": 0, "position": 5},
    )
    assert d["impressions_delta_pct"] == 100.0  # from zero -> 100 (not inf)
    assert d["clicks_delta_pct"] is None


def test_compute_deltas_deterministic():
    b = {"impressions": 100, "clicks": 2, "ctr": 0.02, "position": 30}
    c = {"impressions": 120, "clicks": 3, "ctr": 0.025, "position": 28}
    assert gv.compute_deltas(b, c) == gv.compute_deltas(b, c)


# ---------------------------------------------------------------------------
# Indexing state classification
# ---------------------------------------------------------------------------
def test_classify_indexed():
    assert gv.classify_status("Indexed", "PASS") == "INDEXED"


def test_classify_alternate_waits_recrawl():
    assert gv.classify_status("Alternate page with proper canonical tag", "NEUTRAL") == "WAITING_RECRAWL"


def test_classify_noindex_not_indexed():
    assert gv.classify_status("Excluded by \u2018noindex\u2019 tag", "NEUTRAL") == "NOT_INDEXED"


def test_classify_not_indexed():
    assert gv.classify_status("Not indexed", "NEUTRAL") == "NOT_INDEXED"


def test_classify_technical_block():
    assert gv.classify_status("Anything", "NEUTRAL", has_technical_block=True) == "TECHNICAL_BLOCK"


def test_classify_unknown():
    assert gv.classify_status("", "") == "UNKNOWN"


# ---------------------------------------------------------------------------
# Query movement
# ---------------------------------------------------------------------------
def test_compare_queries_new_emerging_lost():
    base = {
        "visa china": {"impressions": 10},
        "old query": {"impressions": 5},
        "growing": {"impressions": 2},
    }
    cur = {
        "visa china": {"impressions": 10},
        "growing": {"impressions": 8},
        "brand new": {"impressions": 3},
    }
    mov = gv.compare_queries(base, cur)
    assert mov["new_queries"] == ["brand new"]
    assert mov["lost_queries"] == ["old query"]
    assert mov["emerging_queries"] == ["growing"]


def test_compare_queries_deterministic():
    base = {"a": {"impressions": 1}, "b": {"impressions": 2}}
    cur = {"a": {"impressions": 1}, "c": {"impressions": 2}}
    assert gv.compare_queries(base, cur) == gv.compare_queries(base, cur)


# ---------------------------------------------------------------------------
# Impact score
# ---------------------------------------------------------------------------
def test_impact_score_index_gain_and_bounds():
    s = gv.impact_score("INDEXED", {"baseline_impressions": 10, "current_impressions": 30,
                                    "position_delta": -5, "current_clicks": 25, "ctr_delta": 0.01},
                        {"new_queries": ["x"], "emerging_queries": [], "lost_queries": []})
    assert 0 <= s["score"] <= 100
    assert "INDEX_GAIN" in s["reasons"]
    assert s["label"] == "INTERNAL EXPERIMENT SCORE"


def test_impact_score_not_indexed_low():
    s = gv.impact_score("NOT_INDEXED", {"baseline_impressions": 0, "current_impressions": 0,
                                        "position_delta": 0, "current_clicks": 0, "ctr_delta": 0},
                        {"new_queries": [], "emerging_queries": [], "lost_queries": []})
    assert s["score"] == 0


def test_impact_score_deterministic():
    kw = {"baseline_impressions": 10, "current_impressions": 10, "position_delta": 0,
          "current_clicks": 0, "ctr_delta": 0}
    assert gv.impact_score("INDEXED", kw, {"new_queries": [], "emerging_queries": [], "lost_queries": []}) == \
        gv.impact_score("INDEXED", kw, {"new_queries": [], "emerging_queries": [], "lost_queries": []})


# ---------------------------------------------------------------------------
# Cached fallback matching
# ---------------------------------------------------------------------------
def test_abs_url_normalizes_relative():
    assert gv._abs_url("/posts/x/") == "https://www.chinaboundtravel.com/posts/x/"
    assert gv._abs_url("https://www.chinaboundtravel.com/posts/x/") == "https://www.chinaboundtravel.com/posts/x/"


def test_match_cached_absolute_url():
    cached = {"https://www.chinaboundtravel.com/posts/x/": {"impressions": 7.0}}
    tgt = {"cache_aliases": ["https://www.chinaboundtravel.com/posts/x/"]}
    assert gv._match_cached(cached, tgt, "28d")["impressions"] == 7.0


def test_match_cached_relative_backward_compat():
    cached = {"/posts/x/": {"impressions": 7.0}}
    tgt = {"cache_aliases": ["/posts/x/"]}
    assert gv._match_cached(cached, tgt, "28d")["impressions"] == 7.0


def test_match_cached_legacy_dated_url_fallback():
    cached = {"https://www.chinaboundtravel.com/posts/2026-05-25-china-high-speed-rail-how-to-book-tickets/":
              {"impressions": 138.0}}
    tgt = {
        "cache_aliases": [
            "https://www.chinaboundtravel.com/posts/2026-05-25-china-high-speed-rail-how-to-book-tickets/",
            "https://www.chinaboundtravel.com/posts/china-high-speed-rail-how-to-book-tickets/",
        ]
    }
    assert gv._match_cached(cached, tgt, "28d")["impressions"] == 138.0


def test_match_cached_missing_returns_none():
    assert gv._match_cached({}, {"cache_aliases": ["/posts/nope/"]}, "28d") is None


# ---------------------------------------------------------------------------
# Known inspection fallback
# ---------------------------------------------------------------------------
def test_known_inspection_fallback_wechat_weak():
    fallback = gv.KNOWN_INSPECTION_FALLBACK["B"]
    assert gv.classify_status(fallback["coverageState"], fallback["verdict"]) == "WAITING_RECRAWL"


def test_known_inspection_fallback_rail():
    fallback = gv.KNOWN_INSPECTION_FALLBACK["C"]
    assert gv.classify_status(fallback["coverageState"], fallback["verdict"]) == "NOT_INDEXED"
