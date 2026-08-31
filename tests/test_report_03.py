"""P1-REPORT-03: unified reporting template rebuild tests.

Covers 2.0 alert model correctness:
- No FALSE RED for zero new articles, zero revenue, zero GSC yesterday
- NULL revenue never converted to $0
- INSUFFICIENT_SAMPLE on low data
- No KPI contradictions across reports
- UTF-8 output from all scripts
- Deterministic rendering from snapshot
"""
import json
import os
import sys
from datetime import date
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import report_advice
import reporting_kpi_engine as rke
import reporting_engine as reng

AS_OF = date(2026, 8, 17)

# Minimum data that represents "zero production day" with non-zero traffic
ZERO_PRODUCTION_DAILY_DATA = {
    "visitors": 12,
    "sessions": 13,
    "bounce_rate": 50.0,
    "avg_session_duration": 26,
    "engagement_rate": 0.0,
    "new_posts": 0,
    "total_posts": 60,
    "gsc_impressions": 0,
    "tp_clicks": 0,
    "tp_bookings": 0,
    "tp_revenue": 0.0,
    "ml_total_subscribers": 0,
    "placeholder_articles": 0,
    "empty_links": 0,
    "missing_alt": 0,
    "gsc_errors": 0,
    "pending_posts": 0,
    "top_channels": [],
    "visitors_trend": "📈 +100.0%",
    "week_trend": "📈 +1100.0%",
    "month_trend": "📈 +500.0%",
}


# ---------------------------------------------------------------------------
# 1. No FALSE RED for zero production metrics
# ---------------------------------------------------------------------------

def test_no_false_red_for_zero_new_articles():
    """Daily report must NOT mark 0 new articles as RED failure."""
    items = report_advice.generate_advice(ZERO_PRODUCTION_DAILY_DATA, "daily")
    red_titles = [a["title"] for a in items if a["icon"] == "🔴"]
    for t in red_titles:
        assert "新增" not in t or "篇" not in t or "0" not in t, f"false RED: {t}"


def test_zero_revenue_never_converted_to_zero_dollar():
    """Revenue 必须保持真实口径：无凭据→NULL/NOT_AVAILABLE；有凭据→LIVE 真实值（含 0）。
    绝不允许把未接入的 NULL 伪造成 $0。"""
    snap = rke.build_snapshot(AS_OF)
    rmap = {k["name"]: k for k in snap["domains"]["revenue"]["kpis"]}
    rev = rmap["revenue"]
    if os.getenv("TRAVELPAYOUTS_API_TOKEN"):
        # 有凭据：revenue 域 LIVE，0 是真实返回，不允许把 NULL 当 $0（LIVE 0 是真实值）
        assert rev["data_source_type"] == "LIVE"
        assert isinstance(rev["value"], (int, float))
    else:
        # 无凭据：必须保持 NULL / NOT_AVAILABLE，绝不显示 $0
        assert rev["value"] is None
        assert rev["data_source_type"] == "NOT_AVAILABLE"
        assert rev["status"] in ("REVENUE_NOT_AVAILABLE", "NOT_AVAILABLE")
        for k in rmap.values():
            assert k["value"] is None, f"{k['name']} should be NULL"


def test_gsc_zero_yesterday_not_red():
    """Zero GSC impressions yesterday is NOT a RED condition (new site normal)."""
    data = dict(ZERO_PRODUCTION_DAILY_DATA)
    data["gsc_impressions"] = 0
    items = report_advice.generate_advice(data, "daily")
    red_titles = [a["title"] for a in items if a["icon"] == "🔴"]
    for t in red_titles:
        assert "搜索曝光" not in t or "新站" in t, f"GSC zero should not be RED: {t}"


def test_low_data_warning_present():
    snap = rke.build_snapshot(AS_OF)
    assert snap["low_data_warning"] is True
    assert len(snap["low_data_reasons"]) > 0


def test_insufficient_sample_on_low_clicks():
    snap = rke.build_snapshot(AS_OF)
    amap = {k["name"]: k for k in snap["domains"]["affiliate_funnel"]["kpis"]}
    assert amap["affiliate_clicks_28d"]["status"] == "INSUFFICIENT_SAMPLE"
    assert amap["click_rate"]["status"] == "INSUFFICIENT_SAMPLE"


# ---------------------------------------------------------------------------
# 2. No KPI contradictions across reports
# ---------------------------------------------------------------------------

def test_no_kpi_contradictions_across_reports(tmp_path):
    """All five reports must show the same content count and revenue status."""
    snapshot = rke.build_snapshot(AS_OF)
    written = {}
    for period in ("daily", "weekly", "monthly", "quarterly", "yearly"):
        out = reng.generate_period(period, snapshot, tmp_path)
        written[period] = out.read_text(encoding="utf-8")

    # content count must be identical across all reports
    n_posts = len(list((REPO / "content" / "posts").glob("*.md")))
    count_marker = f"{n_posts} posts"
    for p1, texts1 in written.items():
        for p2, texts2 in written.items():
            if p1 >= p2:
                continue
            assert (count_marker in texts1) == (count_marker in texts2), f"{p1} vs {p2} content count mismatch"
            assert ("REVENUE_NOT_AVAILABLE" in texts1) == ("REVENUE_NOT_AVAILABLE" in texts2), \
                f"{p1} vs {p2} revenue status mismatch"


def test_all_periods_use_snapshot_as_source(tmp_path):
    snapshot, written = {}, {}
    snapshot = rke.build_snapshot(AS_OF)
    for period in ("daily", "weekly", "monthly", "quarterly", "yearly"):
        out = reng.generate_period(period, snapshot, tmp_path)
        text = out.read_text(encoding="utf-8")
        assert "REPORTING_SNAPSHOT.json" in text, f"{period} must reference snapshot source"


# ---------------------------------------------------------------------------
# 3. UTF-8 output from all scripts
# ---------------------------------------------------------------------------

def test_utf8_from_advice():
    items = report_advice.generate_advice(ZERO_PRODUCTION_DAILY_DATA, "daily")
    section = report_advice.advice_section(ZERO_PRODUCTION_DAILY_DATA, "daily")
    section.encode("utf-8")  # must not raise


def test_utf8_from_snapshot():
    snap = rke.build_snapshot(AS_OF)
    raw = json.dumps(snap, ensure_ascii=False).encode("utf-8")
    json.loads(raw.decode("utf-8"))  # roundtrip OK


# ---------------------------------------------------------------------------
# 4. Deterministic rendering
# ---------------------------------------------------------------------------

def test_deterministic_advice_output():
    data = dict(ZERO_PRODUCTION_DAILY_DATA)
    a = report_advice.generate_advice(data, "daily")
    b = report_advice.generate_advice(data, "daily")
    assert json.dumps(a, ensure_ascii=False, sort_keys=True) == json.dumps(b, ensure_ascii=False, sort_keys=True)


def test_deterministic_snapshot():
    a = rke.build_snapshot(AS_OF)
    b = rke.build_snapshot(AS_OF)
    assert json.dumps(a, ensure_ascii=False, sort_keys=True) == json.dumps(b, ensure_ascii=False, sort_keys=True)
