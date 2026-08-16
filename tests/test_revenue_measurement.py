"""P1-GROWTH-10B: revenue measurement engine tests.

Covers (pure/deterministic, no network):
- pre/post drive period classification
- null revenue (never fabricated)
- affiliate click normalization per 1000 sessions
- insufficient sample guard
- deterministic commercial ranking
- baseline rows per page/content_id/partner
"""
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import revenue_measurement as rm


def sample_article(content_id="cbt-x", url=None, intent_override=None, text="{{< affiliate-hotel >}}"):
    fm_url = url or "https://www.chinaboundtravel.com/posts/test-article/"
    return {
        "content_id": content_id,
        "title": "Test",
        "url": fm_url,
        "date": "2026-01-01",
        "scans": __import__("affiliate_gap_detector").scan_article(text),
        "intent": intent_override or __import__("affiliate_gap_detector").infer_business_intent(fm_url, "Test"),
        "gsc": {"clicks": 0, "impressions": 100, "ctr": 0, "position": 10},
    }


# ---------------------------------------------------------------------------
# Drive period classification
# ---------------------------------------------------------------------------
def test_classify_drive_state_pre():
    assert rm.classify_drive_state(date(2026, 8, 15)) == "PRE_DRIVE"


def test_classify_drive_state_insufficient():
    assert rm.classify_drive_state(date(2026, 8, 16)) == "INSUFFICIENT_SAMPLE"
    assert rm.classify_drive_state(date(2026, 9, 10)) == "INSUFFICIENT_SAMPLE"


def test_classify_drive_state_post_after_28d():
    assert rm.classify_drive_state(date(2026, 9, 13)) == "POST_DRIVE"


def test_days_since_drive_active():
    assert rm.days_since_drive_active(date(2026, 8, 16)) == 0
    assert rm.days_since_drive_active(date(2026, 8, 20)) == 4


# ---------------------------------------------------------------------------
# Null revenue / normalization
# ---------------------------------------------------------------------------
def test_baseline_revenue_null():
    arts = [sample_article()]
    rows = rm.build_pre_drive_rows(arts, {}, 100, {}, rm.PARTNER_DEFS)
    assert rows[0]["revenue_28d"] == "NULL"
    assert rows[0]["affiliate_sessions_28d"] == "NULL"


def test_per1000_normalization():
    assert rm.per1000(0, 162) == 0.0
    assert rm.per1000(16.2, 162) == 100.0
    assert rm.per1000(5, 0) == 0.0


def test_per1000_attribution_per_page():
    arts = [sample_article(content_id="cbt-1", url="https://www.chinaboundtravel.com/posts/visa/"),
            sample_article(content_id="cbt-2", url="https://www.chinaboundtravel.com/posts/other/")]
    rows = rm.build_pre_drive_rows(arts, {"/posts/visa/": 4}, 200, {}, rm.PARTNER_DEFS)
    visa = [r for r in rows if r["content_id"] == "cbt-1"]
    other = [r for r in rows if r["content_id"] == "cbt-2"]
    assert visa[0]["affiliate_clicks_28d"] == 4
    assert other[0]["affiliate_clicks_28d"] == 0
    assert visa[0]["affiliate_clicks_per_1000_sessions"] == 20.0


# ---------------------------------------------------------------------------
# Sample guard
# ---------------------------------------------------------------------------
def test_sample_guard():
    assert rm.sample_guard(0) == "INSUFFICIENT_SAMPLE"
    assert rm.sample_guard(19) == "INSUFFICIENT_SAMPLE"
    assert rm.sample_guard(20) == "OK"


# ---------------------------------------------------------------------------
# Deterministic ranking
# ---------------------------------------------------------------------------
def test_rank_commercial_deterministic_and_intent_weight():
    arts = [
        sample_article(content_id="cbt-v", url="https://www.chinaboundtravel.com/posts/china-visa/",
                       intent_override="VISA"),
        sample_article(content_id="cbt-f", url="https://www.chinaboundtravel.com/posts/food/",
                       intent_override="FOOD"),
    ]
    r1 = rm.rank_commercial_drive(arts, rm.PARTNER_DEFS, {})
    r2 = rm.rank_commercial_drive(arts, rm.PARTNER_DEFS, {})
    assert r1 == r2
    assert r1[0]["content_id"] == "cbt-v"
    assert r1[0]["drive_status"] == "ACTIVE"


def test_rank_commercial_no_affiliate_partner_none():
    arts = [sample_article(text="", content_id="cbt-n")]
    rows = rm.rank_commercial_drive(arts, rm.PARTNER_DEFS, {})
    assert rows[0]["partner"] == "NONE"


# ---------------------------------------------------------------------------
# Baseline determinism
# ---------------------------------------------------------------------------
def test_build_pre_drive_rows_deterministic():
    arts = [sample_article(), sample_article(content_id="cbt-2")]
    a = rm.build_pre_drive_rows(arts, {}, 10, {}, rm.PARTNER_DEFS)
    b = rm.build_pre_drive_rows(arts, {}, 10, {}, rm.PARTNER_DEFS)
    assert a == b
