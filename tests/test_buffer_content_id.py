"""P0-6: Buffer content_id propagation tests.

Verifies that every Buffer publish path carries the article content_id
(and variant + source_workflow) so each publish task is internally traceable:

    content_id + platform + account + variant + scheduled_at + source_workflow + post_url

No real Buffer API is called: requests.post is monkeypatched.
"""
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SOCIAL_PUBLISHER = REPO_ROOT / "chinaboundtravel_social_bot" / "social_publisher.py"
CONTENT_ROTATOR = REPO_ROOT / "scripts" / "content_rotator.py"
WORKER = REPO_ROOT / "buffer-worker" / "worker.js"
DEDUP = REPO_ROOT / "buffer-worker" / "dedup.mjs"


# ---------- source-level assertions ----------

def test_social_publisher_reads_and_sends_content_id():
    src = SOCIAL_PUBLISHER.read_text(encoding="utf-8")
    assert '"content_id": frontmatter.get("content_id", "")' in src
    assert '"content_id": article.get("content_id", "")' in src
    assert '"content_variant": variant' in src
    assert '"source_workflow": "social_publisher"' in src


def test_content_rotator_reads_and_sends_content_id():
    src = CONTENT_ROTATOR.read_text(encoding="utf-8")
    assert '"content_id": fm.get("content_id", "")' in src
    assert '"content_id": article.get("content_id", "")' in src
    assert '"content_variant": variant' in src
    assert '"source_workflow": "content_rotation"' in src


def test_worker_accepts_content_id_and_builds_dedup_key():
    src = WORKER.read_text(encoding="utf-8")
    assert "content_id: contentId" in src
    assert "buildDedupKey" in src
    assert "buildTrackRecord" in src
    assert "contentVariant" in src
    assert "sourceWorkflow" in src
    assert "trackKey" in src
    dedup_src = DEDUP.read_text(encoding="utf-8")
    assert "content_id" in dedup_src
    assert "scheduled_at" in dedup_src
    assert "source_workflow" in dedup_src


# ---------- behavioral assertions (requests mocked) ----------

def test_social_publisher_payload_contains_traceability(monkeypatch):
    import sys
    sys.path.insert(0, str(SOCIAL_PUBLISHER.parent))
    import social_publisher as sp

    captured = {}

    class FakeResp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"success": True, "platforms": {"success": ["x"], "failed": []}}

    def fake_post(url, json=None, timeout=None):
        captured["url"] = url
        captured["payload"] = json
        return FakeResp()

    monkeypatch.setattr(sp.requests, "post", fake_post)

    article = {
        "title": "Test Guide",
        "description": "A test description",
        "url": "https://www.chinaboundtravel.com/posts/test-guide/",
        "content_id": "cbt-57d0b0208d3b",
    }
    sp.publish_to_worker(article, "https://chinaboundtravel.com/img/china-dest/test.jpg", "Some text", "x_promo")

    payload = captured["payload"]
    assert payload["content_id"] == "cbt-57d0b0208d3b"
    assert payload["content_variant"] == "x_promo"
    assert payload["source_workflow"] == "social_publisher"
    assert payload["url"] == article["url"]
    # canonical URL and original params must be untouched
    assert payload["url"] == "https://www.chinaboundtravel.com/posts/test-guide/"


def test_content_rotator_payload_contains_traceability(monkeypatch):
    import sys
    sys.path.insert(0, str(CONTENT_ROTATOR.parent))
    import content_rotator as cr

    captured = {}

    class FakeResp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"success": True, "platforms": {"success": ["instagram"], "failed": []}}

    def fake_post(url, json=None, timeout=None):
        captured["url"] = url
        captured["payload"] = json
        return FakeResp()

    monkeypatch.setattr(cr.requests, "post", fake_post)

    article = {
        "title": "Rotation Guide",
        "url": "https://www.chinaboundtravel.com/posts/rotation/",
        "content_id": "cbt-1234567890ab",
    }
    cr.publish_to_buffer(article, "Some copy", "https://chinaboundtravel.com/img/cover.jpg", "informative")

    payload = captured["payload"]
    assert payload["content_id"] == "cbt-1234567890ab"
    assert payload["content_variant"] == "informative"
    assert payload["source_workflow"] == "content_rotation"


def test_real_article_frontmatter_content_id_is_parsed():
    """A real article with a content_id must surface it through get_article_info."""
    import sys
    sys.path.insert(0, str(SOCIAL_PUBLISHER.parent))
    import social_publisher as sp

    sample = REPO_ROOT / "content" / "posts" / "2026-07-13-navigating-china-with-confidence-a-californians-guide-to-travel-safety.md"
    assert sample.exists()
    info = sp.get_article_info(sample)
    assert re.fullmatch(r"cbt-[0-9a-f]{12}", info["content_id"]), info["content_id"]
    # canonical URL preserved
    assert info["url"].startswith("https://")
