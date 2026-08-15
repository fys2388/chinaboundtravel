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
    # Hermetic run: mock CSVs in a temp dir, --no-reports so committed
    # report files are never regenerated/overwritten by the test.
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        q = Path(d) / "q.csv"
        p = Path(d) / "p.csv"
        qp = Path(d) / "qp.csv"
        with open(q, "w", newline="", encoding="utf-8") as f:
            f.write("keys,clicks,impressions,ctr,position\n"
                    "china visa,0,120,0.0,7.0\n")
        with open(p, "w", newline="", encoding="utf-8") as f:
            f.write("keys,clicks,impressions,ctr,position\n"
                    "https://www.chinaboundtravel.com/posts/visa/,0,150,0.0,9.0\n")
        with open(qp, "w", newline="", encoding="utf-8") as f:
            f.write("keys,clicks,impressions,ctr,position\n"
                    "china visa;https://www.chinaboundtravel.com/posts/visa/,0,10,0.0,12.0\n")
        out = Path(d) / "opps.csv"
        proc = subprocess.run(
            [sys.executable, str(REPO / "scripts" / "seo_opportunity_detector.py"),
             "--queries", str(q), "--pages", str(p), "--query-pages", str(qp),
             "--output", str(out), "--min-impressions", "100", "--no-reports"],
            cwd=str(REPO), capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        assert proc.returncode == 0, proc.stderr[-2000:]
        assert out.exists()
        with open(out, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert rows, "csv empty"
        types = {r["opportunity_type"] for r in rows}
        assert "A_HIGH_IMP_LOW_CTR" in types
        assert "D_HIGH_IMP_ZERO_CLICK" in types


def test_committed_opportunity_reports_present():
    for name, section in [
        ("SEO_OPPORTUNITIES.md", "## Top 20 Query Opportunities"),
        ("LOW_CTR_OPPORTUNITIES.md", "Position bands"),
        ("PAGE_1_OPPORTUNITIES.md", "Position 4-20"),
    ]:
        fp = SEO_DIR / name
        assert fp.exists(), name
        text = fp.read_text(encoding="utf-8")
        assert section in text, (name, section)


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
