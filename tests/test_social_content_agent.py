# -*- coding: utf-8 -*-
"""tests for scripts/social_content_agent.py and scripts/social_reports.py.

Covers the full social growth engine:
  - inventory structure (content/social/inventory.json)
  - generation (5 types x 4 platforms, brand-compliance rewrite)
  - scheduling (3/day, 80% value / 20% conversion, 7-day de-dup)
  - distribution to the two Buffer Workers (requests mocked)
  - metrics backfill (data feedback loop)
  - daily / weekly report summaries

No network calls: requests.post is monkeypatched where needed.
"""
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import social_content_agent as sga  # noqa: E402
import social_reports as sr  # noqa: E402

INVENTORY_FILE = REPO_ROOT / "content" / "social" / "inventory.json"


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture(scope="module")
def inventory() -> dict:
    data = sga.load_inventory(INVENTORY_FILE)
    if not data["items"]:
        data = sga.build_inventory(top_n=20)
    return data


@pytest.fixture
def article() -> dict:
    return {
        "title": "China High-Speed Rail Booking Guide",
        "description": "How to book high-speed rail tickets in China as an international traveler.",
        "slug": "china-high-speed-rail-how-to-book-tickets",
        "url": "https://www.chinaboundtravel.com/posts/china-high-speed-rail-how-to-book-tickets/",
        "content_id": "cbt-test123456",
        "cover": "https://www.chinaboundtravel.com/img/cover.jpg",
        "headings": ["Booking on 12306", "High-Speed vs Sleeper", "Station Logistics"],
        "date": date.today(),
    }


# ============================================================
# 1. Inventory structure
# ============================================================


def test_inventory_file_exists():
    assert INVENTORY_FILE.exists()


def test_inventory_has_100_items_and_20_sources(inventory):
    assert len(inventory["items"]) == 100
    sources = {i["source_article"] for i in inventory["items"]}
    assert len(sources) == 20


def test_inventory_required_fields(inventory):
    required = {"id", "source_article", "platform", "type", "caption",
                "image_prompt", "utm_params", "status", "publish_date", "metrics"}
    for item in inventory["items"]:
        assert required.issubset(set(item)), item["id"]


def test_inventory_platform_balance(inventory):
    by_platform = {}
    for i in inventory["items"]:
        by_platform[i["platform"]] = by_platform.get(i["platform"], 0) + 1
    assert set(by_platform) == {"ig", "pinterest", "x", "fb"}
    for p, n in by_platform.items():
        assert n == 25, f"{p}: {n}"


def test_inventory_covers_all_types(inventory):
    types = {i["type"] for i in inventory["items"]}
    assert types == set(sga.TYPES)


def test_inventory_default_status_is_pending(inventory):
    assert all(i["status"] == "待审核" for i in inventory["items"])


# ============================================================
# 2. Generation & brand compliance
# ============================================================


def test_generate_one_returns_compliant(article):
    for ctype in sga.TYPES:
        for platform in sga.PLATFORMS:
            res = sga.generate_one(article, ctype, platform, "test_campaign")
            ok, audit = sga.validate_copy(res["text"])
            assert ok, f"{ctype}/{platform} not compliant: {audit}"


def test_generate_one_platform_length(article):
    # X must be <= 280 chars
    x = sga.generate_one(article, "tip", "x", "c")["text"]
    assert len(x) <= 280
    # Pinterest should be longer & keyword-dense (攻略实用型)
    pin = sga.generate_one(article, "knowledge", "pinterest", "c")["text"]
    assert len(pin) > len(x)


def test_generate_one_has_utm(article):
    res = sga.generate_one(article, "knowledge", "ig", "cbt_social_test")["text"]
    assert "utm_source=ig" in res
    assert "utm_campaign=cbt_social_test" in res


def test_validate_copy_rejects_first_person():
    ok, res = sga.validate_copy("I stayed at a hotel in Chengdu last month.")
    assert not ok
    assert res.get("forbidden")


def test_image_prompt_present(article):
    p = sga.build_image_prompt(article, "visual", "ig")
    assert "visual" in p and "ig" in p


# ============================================================
# 3. Scheduling
# ============================================================


def test_build_schedule_three_per_day(inventory):
    sched = sga.build_schedule(inventory, start_date=date(2026, 8, 21))
    for day in sched[:3]:
        assert len(day["slots"]) <= 3


def test_schedule_has_three_slots_per_day(inventory):
    sched = sga.build_schedule(inventory, start_date=date(2026, 8, 21))
    assert len(sched[0]["slots"]) == 3


def test_schedule_ratio_80_20(inventory):
    sched = sga.build_schedule(inventory, start_date=date(2026, 8, 21))
    types = [sl["type"] for d in sched for sl in d["slots"]]
    value = sum(1 for t in types if t in sga.VALUE_TYPES)
    conv = sum(1 for t in types if t in sga.CONVERSION_TYPES)
    total = value + conv
    assert total > 0
    # 80% value, 20% conversion within tolerance
    assert abs(value / total - 0.8) < 0.15
    assert abs(conv / total - 0.2) < 0.15


def test_schedule_utc_slots():
    slots = sga.schedule_slots_for_day(date(2026, 8, 21))
    assert len(slots) == 3
    for s in slots:
        assert s.endswith("+00:00")
        assert "T" in s


# ============================================================
# 4. Distribution (requests mocked)
# ============================================================


def test_account_url_routing():
    assert sga.account_url("pinterest") == sga.ACCOUNT_B_URL
    assert sga.account_url("ig") == sga.ACCOUNT_A_URL
    assert sga.account_url("x") == sga.ACCOUNT_A_URL
    assert sga.account_url("fb") == sga.ACCOUNT_A_URL


def test_publish_item_dry_run():
    item = {"id": "soc-x", "source_article": "slug", "platform": "ig",
            "type": "knowledge", "caption": "caption", "image_url": ""}
    res = sga.publish_item(item, "https://worker.example/publish", dry_run=True)
    assert res["success"] and res["dry_run"]


def test_publish_item_posts_to_worker(monkeypatch):
    captured = {}

    class FakeResp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"success": True, "platforms": {"success": ["x"]}}

    def fake_post(url, json=None, timeout=None):
        captured["url"] = url
        captured["payload"] = json
        return FakeResp()

    monkeypatch.setattr(sga.requests, "post", fake_post)
    item = {"id": "soc-x", "source_article": "slug", "platform": "x",
            "type": "tip", "caption": "caption", "image_url": ""}
    res = sga.publish_item(item, "https://worker.example/publish", dry_run=False)
    assert res["success"]
    assert captured["payload"]["source_workflow"] == "social_content_agent"
    assert captured["payload"]["content_variant"] == "x_tip"


def test_publish_item_worker_queued_is_success(monkeypatch):
    """worker 单日限流（202 + queued:true）应视为成功交接，而非失败。"""
    class FakeResp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"success": False, "queued": True,
                    "message": "今日已发布 3 篇，单日上限 3 篇。稿件已存入队列，明日自动发布。"}

    def fake_post(url, json=None, timeout=None):
        return FakeResp()

    monkeypatch.setattr(sga.requests, "post", fake_post)
    item = {"id": "soc-x", "source_article": "slug", "platform": "ig",
            "type": "knowledge", "caption": "caption", "image_url": ""}
    res = sga.publish_item(item, "https://worker.example/publish", dry_run=False)
    assert res["success"] is True
    assert res["queued"] is True


# ============================================================
# 5. Metrics backfill (data feedback)
# ============================================================


def test_backfill_metrics(tmp_path, monkeypatch):
    data = sga.load_inventory(INVENTORY_FILE)
    target = data["items"][0]["id"]
    mfile = tmp_path / "metrics.json"
    mfile.write_text(json.dumps({"items": [
        {"item_id": target, "impressions": 500, "clicks": 20, "uv": 10},
    ]}), encoding="utf-8")

    inv_path = tmp_path / "inventory.json"
    inv_path.write_text(json.dumps(data), encoding="utf-8")
    updated = sga.backfill_metrics(mfile, inventory_path=inv_path)
    assert updated == 1

    reloaded = sga.load_inventory(inv_path)
    rec = next(i for i in reloaded["items"] if i["id"] == target)
    assert rec["metrics"]["impressions"] == 500
    assert rec["metrics"]["clicks"] == 20


def test_backfill_metrics_missing_file(tmp_path):
    assert sga.backfill_metrics(tmp_path / "nope.json") == 0


# ============================================================
# 6. Reports
# ============================================================


def test_daily_summary_shape(inventory):
    s = sr.summarize_daily(inventory, date.today() - timedelta(days=1))
    assert "total_published" in s and "by_platform" in s
    assert set(s["by_platform"]) == set(sga.PLATFORMS)


def test_weekly_summary_shape(inventory):
    s = sr.summarize_weekly(inventory)
    assert "top5" in s and "bottom5" in s and "by_type" in s
    assert "next_week_suggestion" in s


def test_daily_block_is_lark_md(inventory):
    s = sr.summarize_daily(inventory, date.today() - timedelta(days=1))
    blocks = sr.social_daily_block(s)
    assert blocks and blocks[0]["tag"] == "div"
    assert blocks[0]["text"]["tag"] == "lark_md"


def test_weekly_block_content(inventory):
    s = sr.summarize_weekly(inventory)
    blocks = sr.social_weekly_block(s)
    joined = "\n".join(b["text"]["content"] for b in blocks)
    assert "社媒增长复盘" in joined


# ============================================================
# 7. filter_items
# ============================================================


def test_filter_items_by_platform(inventory):
    ig = sga.filter_items(inventory, platform="ig")
    assert ig and all(i["platform"] == "ig" for i in ig)


def test_filter_items_by_status(inventory):
    pending = sga.filter_items(inventory, status="待审核")
    assert pending and all(i["status"] == "待审核" for i in pending)
