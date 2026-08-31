# -*- coding: utf-8 -*-
"""FeishuDailyReporter._scan_content_quality 内容巡检回归测试。

覆盖 2026-08-30 数据准确性修复：
- 占位符检测纳入 Joran 图片占位符 [Image: ...] 格式（此前漏检）；
- 真实 markdown 图片不误报占位符；空 Alt / 空链接正确计数。
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import feishu_daily_report as fdr  # noqa: E402


def _post(tmp_path: Path, name: str, body: str) -> Path:
    p = tmp_path / name
    p.write_text(body, encoding="utf-8")
    return p


def _scan(tmp_path, monkeypatch):
    monkeypatch.setattr(fdr, "POSTS_DIR", tmp_path)
    reporter = object.__new__(fdr.FeishuDailyReporter)
    return reporter._scan_content_quality(report_date="2026-08-28")


def test_scan_flags_joran_image_placeholders(tmp_path, monkeypatch):
    _post(tmp_path, "a.md", "---\ndate: \"2026-08-28T10:00:00+08:00\"\n---\n\n"
                            "[Image: Golden hour airport terminal, cinematic]\n")
    res = _scan(tmp_path, monkeypatch)
    assert res["total_posts"] == 1
    assert res["placeholder_articles"] == 1


def test_scan_ignores_real_markdown_images(tmp_path, monkeypatch):
    _post(tmp_path, "b.md", "---\ndate: \"2026-08-28T10:00:00+08:00\"\n---\n\n"
                            "![Tea ceremony](/img/china-dest/culture/teahouse-tea-chat-chengdu.jpg)\n")
    res = _scan(tmp_path, monkeypatch)
    assert res["placeholder_articles"] == 0
    assert res["missing_alt"] == 0


def test_scan_counts_missing_alt_and_empty_links(tmp_path, monkeypatch):
    _post(tmp_path, "c.md", "---\n---\n\n![](/img/china-dest/x.jpg)\n\n[text]()\n")
    res = _scan(tmp_path, monkeypatch)
    assert res["missing_alt"] == 1
    assert res["empty_links"] == 1


def test_scan_counts_new_posts_by_frontmatter_date(tmp_path, monkeypatch):
    _post(tmp_path, "d.md", "---\ndate: \"2026-08-29T10:00:00+08:00\"\n---\n\nbody\n")
    _post(tmp_path, "e.md", "---\ndate: \"2026-08-28T10:00:00+08:00\"\n---\n\nbody\n")
    res = _scan(tmp_path, monkeypatch)
    assert res["new_posts"] == 1
