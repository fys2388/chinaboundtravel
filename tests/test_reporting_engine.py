"""P1-REPORT-02: unified reporting engine tests.

Covers (deterministic, no network):
- all five period reports generated from one snapshot
- DoD / WoW / MoM / QoQ / YoY markers (INSUFFICIENT_SAMPLE on first run)
- consistent 60-content baseline across every report
- NULL revenue everywhere
- low-data warning present
- UTF-8 output
- deterministic regeneration
- master dashboard + alerts generation
"""
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import reporting_kpi_engine as rke
import reporting_engine as reng

AS_OF = date(2026, 8, 17)
PERIOD_FILES = {
    "daily": "CHINABOUND_TRAVEL_2_0_DAILY.md",
    "weekly": "CHINABOUND_TRAVEL_2_0_WEEKLY.md",
    "monthly": "CHINABOUND_TRAVEL_2_0_MONTHLY.md",
    "quarterly": "CHINABOUND_TRAVEL_2_0_QUARTERLY.md",
    "yearly": "CHINABOUND_TRAVEL_2_0_YEARLY.md",
}
COMPARE_LABELS = {
    "daily": "DoD", "weekly": "WoW", "monthly": "MoM",
    "quarterly": "QoQ / YoY", "yearly": "YoY",
}


def _generate_all(tmp_path):
    snapshot = rke.build_snapshot(AS_OF)
    written = {}
    for period, fname in PERIOD_FILES.items():
        out = reng.generate_period(period, snapshot, tmp_path)
        assert out.name == fname
        written[period] = out
    return snapshot, written


def test_all_periods_generated(tmp_path):
    _, written = _generate_all(tmp_path)
    assert set(written) == set(PERIOD_FILES)
    for period, p in written.items():
        assert p.exists()
        text = p.read_text(encoding="utf-8")
        assert COMPARE_LABELS[period] in text


def test_consistent_content_count(tmp_path):
    snapshot, written = _generate_all(tmp_path)
    for p in written.values():
        text = p.read_text(encoding="utf-8")
        assert "- Published posts: 60 posts" in text


def test_revenue_null_everywhere(tmp_path):
    _, written = _generate_all(tmp_path)
    for p in written.values():
        text = p.read_text(encoding="utf-8")
        assert "REVENUE_NOT_AVAILABLE" in text
        assert "never fabricated" in text


def test_low_data_warning_everywhere(tmp_path):
    _, written = _generate_all(tmp_path)
    for p in written.values():
        text = p.read_text(encoding="utf-8")
        assert "LOW_DATA" in text or "Low data:" in text


def test_period_comparison_insufficient_first_run():
    snapshot = rke.build_snapshot(AS_OF)
    for label in ("DoD", "WoW", "MoM", "QoQ / YoY", "YoY"):
        rows = reng.period_comparison(snapshot, AS_OF, label)
        assert len(rows) == len(reng.COMPARE_METRICS)
        assert all(r["status"] == "INSUFFICIENT_SAMPLE" for r in rows)


def test_utf8_roundtrip(tmp_path):
    _, written = _generate_all(tmp_path)
    for p in written.values():
        raw = p.read_bytes()
        raw.decode("utf-8")  # must not raise


def test_deterministic_output(tmp_path):
    snapshot = rke.build_snapshot(AS_OF)
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    for period in PERIOD_FILES:
        pa = reng.generate_period(period, snapshot, out_a)
        pb = reng.generate_period(period, snapshot, out_b)
        assert pa.read_bytes() == pb.read_bytes()


def test_master_dashboard_and_alerts(tmp_path):
    snapshot = rke.build_snapshot(AS_OF)
    master = tmp_path / "MASTER.md"
    alerts = tmp_path / "ALERTS.md"
    master.write_text(reng.render_master(snapshot) + "\n", encoding="utf-8")
    alerts.write_text(reng.render_alerts(snapshot) + "\n", encoding="utf-8")
    m = master.read_text(encoding="utf-8")
    a = alerts.read_text(encoding="utf-8")
    assert "Master Dashboard" in m
    assert "YELLOW" in a
    assert "REV001" in m and "REV003" in m


def test_derive_alerts_no_fabrication():
    snapshot = rke.build_snapshot(AS_OF)
    alerts = reng.derive_alerts(snapshot)
    assert alerts["level"] in ("GREEN", "YELLOW", "ORANGE", "RED")
    assert "revenue" not in " ".join(alerts["red"]).lower()


def test_required_daily_sections(tmp_path):
    snapshot, written = _generate_all(tmp_path)
    text = written["daily"].read_text(encoding="utf-8")
    for section in ("1. Traffic today", "2. SEO changes", "3. Indexing changes",
                    "4. Revenue / affiliate events", "5. Experiment events",
                    "6. Production health", "7. Brand compliance changes",
                    "8. Alerts / anomalies", "9. Today's actions"):
        assert section in text