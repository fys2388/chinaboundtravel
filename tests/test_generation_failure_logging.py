"""测试 generator 失败落盘与补图步骤输出校验。

背景（2026-09-18 诊断）：
  - run() 里 except Exception: break 只发飞书通知，不写磁盘。停更 10 天后
    只能靠「content/drafts 不存在」和「没有 chore: auto publish 提交」
    两个旁证反推，定位不到确切失败步骤。
  - DRAFTS_DIR 原为 content/content/drafts（content 写重），草稿落在
    content/content/drafts/，人看 content/drafts/ 是空的。
  - add_image_placeholders 硬编码 max_tokens=500 但要求输出全文（8KB≈2000
    token），模型给不出来就回 "I need the article text to proceed"，
    那段元响应被当正文落盘（971B），主编终审按词数 <700 驳回。
"""

import json
import sys
from pathlib import Path

import pytest

BLOG_ROOT = Path(__file__).parent.parent
BOT_DIR = BLOG_ROOT / "chinaboundtravel_social_bot"
sys.path.insert(0, str(BOT_DIR))

import joran_blog_generator as gen  # noqa: E402


@pytest.fixture()
def event_log(tmp_path, monkeypatch):
    """把事件日志指向临时路径，避免污染真实 reports/。"""
    log = tmp_path / "content_generation" / "generation_events.jsonl"
    monkeypatch.setattr(gen, "GENERATION_LOG", log)
    return log


def test_drafts_dir_points_to_content_drafts_not_doubled():
    """草稿必须落在 content/drafts，不能是 content/content/drafts。

    原路径写重了一次 content，导致 3 轮审核失败后稿件存进
    content/content/drafts/，人检查 content/drafts/ 是空的，
    误以为 generator 从未走到草稿分支。
    """
    assert gen.DRAFTS_DIR == BLOG_ROOT / "content" / "drafts"
    assert "content" in gen.DRAFTS_DIR.parts[-3:]
    parts = gen.DRAFTS_DIR.relative_to(BLOG_ROOT).parts
    assert parts == ("content", "drafts")


def test_generation_event_appends_jsonl(event_log):
    gen.log_generation_event(
        "unexpected_error",
        attempt=1,
        error_type="TimeoutError",
        error_message="ark endpoint timed out",
        frames=['File "a.py", line 1'],
    )
    assert event_log.exists()
    lines = event_log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["outcome"] == "unexpected_error"
    assert rec["attempt"] == 1
    assert rec["error_type"] == "TimeoutError"
    assert rec["ts"]


def test_generation_event_creates_parent_dirs(event_log):
    assert not event_log.parent.exists()
    gen.log_generation_event("limit_daily", daily_count=5, daily_limit=5)
    assert event_log.exists()
    rec = json.loads(event_log.read_text(encoding="utf-8"))
    assert rec["outcome"] == "limit_daily"
    assert rec["daily_count"] == 5


def test_generation_event_appends_multiple_lines(event_log):
    gen.log_generation_event("limit_monthly", post_count=30, max_posts=30)
    gen.log_generation_event("success", attempt=2, title="T")
    lines = event_log.read_text(encoding="utf-8").strip().splitlines()
    assert [json.loads(l)["outcome"] for l in lines] == [
        "limit_monthly",
        "success",
    ]


def _engine():
    """绕过 __init__（会建 BlogAIClient 并读环境变量），只测纯逻辑。"""
    return object.__new__(gen.AIEngine)


@pytest.mark.parametrize(
    "meta",
    [
        "I need the article text to proceed.",
        "Please provide the article content so I can add the two image placeholders.",
        "I need you to provide the full article.",
        "I cannot complete this task without the article.",
        "Could you provide the article text?",
    ],
)
def test_guard_rejects_llm_meta_response(meta):
    """元响应绝不能被当文章正文返回——那是 2026-09-04 草稿正文只有一句废话的根因。"""
    original = "# T\n\n" + ("Real article body. " * 200)
    out = _engine()._guard_image_placeholder_response(original, meta)
    assert out == original


def test_guard_rejects_truncated_output():
    original = "# T\n\n" + ("Long article body text. " * 300)
    out = _engine()._guard_image_placeholder_response(original, "Truncated.")
    assert out == original


def test_guard_rejects_output_without_placeholders():
    original = "# T\n\n" + ("No placeholders here. " * 250)
    out = _engine()._guard_image_placeholder_response(original, original)
    assert out == original


def test_guard_rejects_empty_output():
    original = "# T\n\n" + ("Body. " * 300)
    for bad in (None, "", "   "):
        assert _engine()._guard_image_placeholder_response(original, bad) == original


def test_guard_accepts_valid_output():
    original = "# T\n\n" + ("Article body sentence. " * 200)
    out = _engine()._guard_image_placeholder_response(
        original, original + "\n\n[Image:mountain landscape at dawn]"
    )
    assert out.rstrip().endswith("[Image:mountain landscape at dawn]")


def test_guard_preserves_existing_placeholder_in_original():
    """原文已有占位符时，即使输出无新增也放行（补图步骤是幂等的）。"""
    original = "# T\n\n[Image:lake]\n\n" + ("Body. " * 250)
    out = _engine()._guard_image_placeholder_response(original, original)
    assert out == original


def test_add_image_placeholders_sizes_max_tokens_to_article():
    """max_tokens 必须随文章长度扩展。硬编码 500 是元响应泄漏的根因。"""
    eng = _engine()

    captured = {}

    def fake_chat(messages, max_tokens=None):
        captured["max_tokens"] = max_tokens
        return messages[0]["content"].split("Article:\n", 1)[1]

    eng.client = type("FakeClient", (), {"chat": staticmethod(fake_chat)})()

    short = "# T\n\nShort body."
    eng.add_image_placeholders(short)
    assert captured["max_tokens"] == 1000  # 下限

    long_article = "# T\n\n" + ("Real article body. " * 400)  # ~12.4KB
    eng.add_image_placeholders(long_article)
    # est = len/3 + 512；12.4KB ≈ 4700
    assert captured["max_tokens"] > 3000, captured["max_tokens"]
