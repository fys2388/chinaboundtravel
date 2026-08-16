"""P1-GROWTH-12A: revenue experiment candidate lock regression tests.

Verifies deterministically:
1. lock report + baseline CSV exist and are complete
2. candidate is not any running experiment object
3. candidate page: draft=false, canonical=self, content_id matches
4. candidate already has affiliate partners (shortcode set)
5. legacy date URL is 301-redirected to the canonical
6. baseline values are stable and non-negative
"""
import csv
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

CANDIDATE = "content/posts/2026-05-28-chinese-food-delivery-meituan-eleme-guide.md"
CONTENT_ID = "cbt-e464169c4991"
CANONICAL = "https://www.chinaboundtravel.com/posts/chinese-food-delivery-meituan-eleme-guide/"
LEGACY_URL = "/posts/2026-05-28-chinese-food-delivery-meituan-eleme-guide/"

BRAND03_PILOTS = {
    "content/posts/western-sichuan-overland-camping-route.md",
    "content/posts/2026-07-03-guilin-and-yangshuo-the-ultimate-karst-landscape-guide-for-2026-guide.md",
    "content/posts/2026-06-23-sichuan-hotpot-guide-history-best-restaurants-and-cultural-significance.md",
}
RUNNING_EXPERIMENTS = {
    "content/posts/144-hour-visa-free-transit-guide.md",           # GROWTH-05 CTR
    "content/posts/2026-05-22-how-to-use-wechat-pay-as-a-foreigner.md",  # GROWTH-07 strong
    "content/posts/2026-07-02-wechat-pay-for-foreigners-step-by-step-setup-and-common-mistakes-to-avoid-guide.md",  # weak
    "content/posts/2026-05-25-china-high-speed-rail-how-to-book-tickets.md",  # technical SEO
    "content/posts/2026-07-16-china-transportation-complete-guide-trains-subways-taxis-and-more.md",
}


def _fm(text, key):
    m = re.search(r"^\s*" + re.escape(key) + r"\s*[:=]\s*(.+)$", text.split("---", 2)[1], re.M)
    if not m:
        return None
    val = m.group(1).strip()
    if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
        val = val[1:-1]
    return val


def test_lock_artifacts_exist():
    assert (REPO / "reports/revenue/REVENUE_EXPERIMENT_CANDIDATE_LOCK.md").exists()
    assert (REPO / "reports/revenue/REV001_BASELINE.csv").exists()
    assert (REPO / "reports/P1_GROWTH_12A_REVENUE_CANDIDATE_LOCK.md").exists()


def test_candidate_not_in_running_experiments_or_brand03():
    assert CANDIDATE not in BRAND03_PILOTS
    assert CANDIDATE not in RUNNING_EXPERIMENTS


def test_candidate_page_identity_locked():
    text = (REPO / CANDIDATE).read_text(encoding="utf-8")
    assert _fm(text, "content_id") == CONTENT_ID
    assert _fm(text, "canonicalURL") == CANONICAL
    assert _fm(text, "draft") != "true"
    slug = _fm(text, "slug")
    assert slug and slug in CANONICAL


def test_candidate_has_affiliate_partners():
    text = (REPO / CANDIDATE).read_text(encoding="utf-8")
    for sc in ("affiliate-hotel", "affiliate-flight", "affiliate-esim", "affiliate-tour"):
        assert sc in text, sc
    assert "{{< affiliate-" in text


def test_legacy_date_url_redirected():
    redirects = (REPO / "static/_redirects").read_text(encoding="utf-8")
    assert LEGACY_URL + " /posts/chinese-food-delivery-meituan-eleme-guide/ 301" in redirects


def test_baseline_csv_values_stable():
    p = REPO / "reports/revenue/REV001_BASELINE.csv"
    rows = list(csv.DictReader(p.open(encoding="utf-8")))
    assert len(rows) == 1
    row = rows[0]
    assert row["content_id"] == CONTENT_ID
    assert row["url"] == CANONICAL
    assert row["baseline_start"] == "2026-07-19"
    assert row["baseline_end"] == "2026-08-15"
    for k in ("sessions", "pageviews", "affiliate_clicks", "affiliate_clicks_per_1000",
              "gsc_impressions", "gsc_clicks"):
        assert float(row[k]) >= 0, k
    assert float(row["gsc_position"]) > 0
    assert row["affiliate_clicks"] == "0"
