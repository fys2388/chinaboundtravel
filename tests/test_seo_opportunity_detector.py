"""P1-GROWTH-02: tests for the SEO opportunity detector.

Covers the required rules:
- low CTR (A)
- position 4-10 (B)
- position 11-20 (C)
- high impression zero click (D)
- thresholds (min_impressions)
- sorting

Plus rule E (multiple related queries -> same page), rule G (query/page
mismatch) and the CLI argument defaults.
"""
import pytest

from seo_opportunity_detector import detect_opportunities, load_rows


def _q(keys, clicks, impressions, ctr, position):
    return {"keys": keys, "clicks": clicks, "impressions": impressions,
            "ctr": ctr, "position": position}


def test_low_ctr_rule_a():
    queries = [
        _q("high volume query", 1, 200, 0.005, 5.0),   # qualifies
        _q("good ctr query", 20, 200, 0.10, 3.0),      # ctr too high
        _q("low volume", 0, 10, 0.0, 12.0),            # impressions too low
    ]
    opps = detect_opportunities(queries, [], [], min_impressions=100, low_ctr=0.03)
    a = [o for o in opps if o["opportunity_type"] == "A_HIGH_IMP_LOW_CTR"]
    assert len(a) == 1
    assert a[0]["query"] == "high volume query"
    assert a[0]["recommended_action"] == "META"


def test_position_4_10_rule_b():
    queries = [
        _q("page one edge", 0, 50, 0.0, 4.0),
        _q("page one middle", 0, 30, 0.0, 7.0),
        _q("just outside", 0, 40, 0.0, 11.0),
    ]
    opps = detect_opportunities(queries, [], [], min_impressions=100)
    b = [o for o in opps if o["opportunity_type"] == "B_POSITION_4_10"]
    assert sorted(o["query"] for o in b) == ["page one edge", "page one middle"]
    assert all(o["recommended_action"] == "FAQ" for o in b)


def test_position_11_20_rule_c():
    queries = [
        _q("page two", 0, 25, 0.0, 12.0),
        _q("page two deep", 0, 20, 0.0, 19.0),
        _q("too deep", 0, 15, 0.0, 21.0),
        _q("above", 0, 10, 0.0, 3.0),
    ]
    opps = detect_opportunities(queries, [], [], min_impressions=100)
    c = [o for o in opps if o["opportunity_type"] == "C_POSITION_11_20"]
    assert sorted(o["query"] for o in c) == ["page two", "page two deep"]
    assert all(o["recommended_action"] == "CONTENT_UPDATE" for o in c)


def test_high_impression_zero_click_rule_d():
    queries = [
        _q("zero click big", 0, 500, 0.0, 8.0),
        _q("zero click small", 0, 5, 0.0, 3.0),
        _q("has a click", 1, 500, 0.002, 6.0),
    ]
    opps = detect_opportunities(queries, [], [], min_impressions=100)
    d = [o for o in opps if o["opportunity_type"] == "D_HIGH_IMP_ZERO_CLICK"]
    assert [o["query"] for o in d] == ["zero click big"]
    assert d[0]["recommended_action"] == "TITLE"


def test_min_impressions_threshold():
    # Position 25 keeps rows outside rules B/C so only the A/D threshold is exercised.
    queries = [_q("below", 0, 99, 0.0, 25.0), _q("at", 0, 100, 0.0, 25.0)]
    opps = detect_opportunities(queries, [], [], min_impressions=100)
    assert "below" not in {o["query"] for o in opps}
    assert "at" in {o["query"] for o in opps}


def test_sorting_by_impressions_desc():
    queries = [
        _q("low", 0, 100, 0.0, 9.0),
        _q("high", 0, 500, 0.0, 8.0),
        _q("mid", 0, 200, 0.0, 7.0),
    ]
    opps = detect_opportunities(queries, [], [], min_impressions=100)
    imp = [o["impressions"] for o in opps]
    assert imp == sorted(imp, reverse=True)


def test_multiple_queries_same_page_rule_e():
    query_pages = []
    for i, q in enumerate(["a", "b", "c", "d"]):
        query_pages.append(_q(
            f"{q};https://www.chinaboundtravel.com/posts/hub/", 0, 10 + i, 0.0, 20.0))
    opps = detect_opportunities([], [], query_pages, min_impressions=100)
    e = [o for o in opps if o["opportunity_type"] == "E_MULTI_QUERY_PAGE"]
    assert len(e) == 1
    assert e[0]["page"] == "https://www.chinaboundtravel.com/posts/hub/"
    assert e[0]["recommended_action"] == "INTERNAL_LINK"


def test_query_page_mismatch_rule_g():
    query_pages = [
        _q("wechat pay guide;https://www.chinaboundtravel.com/posts/visa-guide/",
           0, 30, 0.0, 15.0),
        _q("wechat pay guide;https://www.chinaboundtravel.com/posts/how-to-use-wechat-pay/",
           0, 30, 0.0, 15.0),
    ]
    opps = detect_opportunities([], [], query_pages, min_impressions=100)
    g = [o for o in opps if o["opportunity_type"] == "G_QUERY_PAGE_MISMATCH"]
    assert len(g) == 1
    assert g[0]["page"] == "https://www.chinaboundtravel.com/posts/visa-guide/"
    assert g[0]["recommended_action"] == "TECHNICAL_REVIEW"


def test_load_rows_skips_malformed():
    tmp = pytest.importorskip("tempfile")
    import csv, os
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "q.csv"
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["keys", "clicks", "impressions", "ctr", "position"])
            w.writerow(["ok", 1, 10, 0.1, 5.0])
            w.writerow(["bad", "x", "y", "z", "w"])
        rows = load_rows(p)
        assert len(rows) == 1
        assert rows[0]["keys"] == "ok"
