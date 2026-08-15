"""P1-GROWTH-01: SEO baseline artifacts regression.

Ensures the SEO opportunity detector and generated CSVs stay parseable and
consistent (mock/local only, no real API calls).
"""

import csv
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SEO_DIR = REPO / "reports" / "seo"


def test_opportunity_detector_runs_and_writes():
    proc = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "seo_opportunity_detector.py")],
        cwd=str(REPO), capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    out = SEO_DIR / "seo_opportunities.md"
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    for section in ("A. High Impression + Low CTR", "B. Position 4-10", "C. Position 11-20", "D. High Impression + Zero Click", "E. Pages with Multiple Related Queries"):
        assert section in text, section


def test_page_performance_csv_parseable():
    fp = SEO_DIR / "page_performance.csv"
    assert fp.exists()
    with open(fp, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows, "csv empty"
    assert rows[0].keys() >= {"page", "clicks", "impressions", "ctr", "position"}


def test_query_performance_csv_parseable():
    fp = SEO_DIR / "query_performance.csv"
    assert fp.exists()
    with open(fp, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows, "csv empty"
    assert rows[0].keys() >= {"query", "clicks", "impressions", "ctr", "position"}


def test_content_inventory_57_with_content_id():
    fp = SEO_DIR / "content_inventory.csv"
    assert fp.exists()
    with open(fp, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 57, len(rows)
    assert all(r["content_id"] for r in rows)
