"""P1-GROWTH-13: unified revenue + SEO experiment review tests.

Covers (pure, deterministic, no network):
- sample guard (days < 28 or clicks < 20 -> INSUFFICIENT_SAMPLE)
- per-1000 metric
- delta / percentage delta
- revenue NULL handling
- experiment status classification
- cached data source flag
- deterministic output (stable order + reproducible CSV)
"""
import csv
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from revenue_experiment_review import (  # noqa: E402
    BASE,
    build_comparison,
    calc_delta,
    calc_per1000,
    classify_experiment,
    load_rev001_baseline,
    sample_status,
    write_comparison,
)


# ---------------------------------------------------------------------------
# sample guard
# ---------------------------------------------------------------------------
def test_sample_guard_insufficient_when_days_short():
    assert sample_status(10, 100) == "INSUFFICIENT_SAMPLE"
    assert sample_status(0, 0) == "INSUFFICIENT_SAMPLE"


def test_sample_guard_insufficient_when_clicks_low():
    assert sample_status(28, 19) == "INSUFFICIENT_SAMPLE"


def test_sample_guard_sufficient():
    assert sample_status(28, 20) == "SUFFICIENT"
    assert sample_status(40, 50) == "SUFFICIENT"


# ---------------------------------------------------------------------------
# metrics
# ---------------------------------------------------------------------------
def test_per1000():
    assert calc_per1000(5, 500) == 10.0
    assert calc_per1000(0, 365) == 0.0
    assert calc_per1000(0, 0) == 0.0
    assert calc_per1000(None, 365) == 0.0


def test_delta_and_percent():
    d, pct = calc_delta(10.0, 15.0)
    assert d == 5.0 and pct == 50.0
    d, pct = calc_delta(10.0, 10.0)
    assert d == 0.0 and pct == 0.0
    d, pct = calc_delta(0.0, 5.0)
    assert d == 5.0 and pct is None  # zero baseline: percent undefined
    d, pct = calc_delta(None, 5.0)
    assert d is None and pct is None


# ---------------------------------------------------------------------------
# revenue NULL (never fabricated)
# ---------------------------------------------------------------------------
def test_rev001_baseline_revenue_not_required():
    row = load_rev001_baseline()
    assert row["content_id"] == "cbt-e464169c4991"
    assert row["affiliate_clicks"] == "0"


def test_revenue_null_in_dashboard_context():
    # revenue availability is recorded as NULL / REVENUE_NOT_AVAILABLE, never guessed
    log = (BASE / "reports/revenue/REV001_EXPERIMENT_LOG.md").read_text(encoding="utf-8")
    assert "NULL" in log
    assert "REVENUE_NOT_AVAILABLE" in log


# ---------------------------------------------------------------------------
# classification
# ---------------------------------------------------------------------------
def test_classify_status():
    assert classify_experiment("SUFFICIENT", 25.0) == "POSITIVE"
    assert classify_experiment("SUFFICIENT", -25.0) == "NEGATIVE"
    assert classify_experiment("SUFFICIENT", 5.0) == "NEUTRAL"
    assert classify_experiment("INSUFFICIENT_SAMPLE", 50.0) == "INSUFFICIENT_SAMPLE"
    assert classify_experiment("SUFFICIENT", None) == "NEUTRAL"


# ---------------------------------------------------------------------------
# cached fallback + deterministic output
# ---------------------------------------------------------------------------
def test_comparison_uses_cached_when_no_live():
    rows = build_comparison()
    by_id = {r["experiment_id"]: r for r in rows}
    assert by_id["REV001"]["data_source"] == "CACHED"
    assert by_id["DRIVE-001"]["data_source"] == "CACHED"


def test_comparison_deterministic_order():
    rows = build_comparison()
    ids = [r["experiment_id"] for r in rows]
    assert ids == sorted(ids)
    assert len(rows) == 5
    for r in rows:
        assert r["status"] == "INSUFFICIENT_SAMPLE"
        assert r["sample_size"] == 0


def test_comparison_csv_reproducible():
    rows = build_comparison()
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "comparison.csv"
        write_comparison(rows, out)
        with out.open(encoding="utf-8") as f:
            written = list(csv.DictReader(f))
    assert len(written) == len(rows)
    assert [r["experiment_id"] for r in written] == [r["experiment_id"] for r in rows]
