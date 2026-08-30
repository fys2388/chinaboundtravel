# -*- coding: utf-8 -*-
"""Joran 风控治理回归测试。

覆盖 2026-08-29 排查出的两个故障：
1. 敏感词表把 "government" 一刀切误杀引用官方政府信源的文章
   （与 config/content_governance.json "优先引用官方政府信源" 矛盾）；
2. move_to_posts 内局部 import re 导致 UnboundLocalError。
"""
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _article(*extra_sentences: str) -> str:
    """构造通过主旨/深度校验的 700+ 词中国旅行文章底稿。"""
    base = ("This guide covers travel to China, including Beijing, Shanghai and Chengdu. "
            "Travelers planning a trip to China should review practical tips before departure. "
            "ChinaBound Travel editors verify facts against official sources before publishing. ") * 20
    return base + " ".join(extra_sentences)


def _chief_editor():
    # 绕过 __init__（其会初始化需要 API Key 的 AI 客户端）；full_check 不依赖 self.client。
    import sys
    from pathlib import Path as _P
    sys.path.insert(0, str(_P(__file__).resolve().parent.parent))
    sys.path.insert(0, str(_P(__file__).resolve().parent.parent / "chinaboundtravel_social_bot"))
    from joran_blog_generator import ChiefEditor
    return object.__new__(ChiefEditor)


def test_full_check_allows_official_government_citations():
    """引用官方政府信源（签证/官方政策）不应被风控拦截。"""
    ce = _chief_editor()
    text = _article(
        "Visitors should check the official government visa website before departure.",
        "The Chinese government publishes entry requirements through the National Immigration Administration.",
        "Travelers can also verify policies on the Ministry of Culture and Tourism website.",
    )
    ok, errors, error_types, _ = ce.full_check(text)
    assert "sensitive" not in error_types, errors


def test_full_check_blocks_political_terms():
    """明确政治敏感词（communist / tiananmen 等）仍必须拦截。"""
    ce = _chief_editor()
    text = _article("This article discusses the communist party's role in modern China.")
    ok, errors, error_types, _ = ce.full_check(text)
    assert "sensitive" in error_types


def test_full_check_blocks_political_government_usage():
    """政府一词的负面政治语境（criticism of the government）必须拦截。"""
    ce = _chief_editor()
    text = _article("Criticism of the government is growing among young travelers.")
    ok, errors, error_types, _ = ce.full_check(text)
    assert "sensitive" in error_types


def test_no_function_level_import_re():
    """move_to_posts 内禁止局部 import re（会触发 UnboundLocalError），必须使用模块级 import。"""
    src = (REPO_ROOT / "chinaboundtravel_social_bot" / "joran_blog_generator.py").read_text(encoding="utf-8")
    for lineno, line in enumerate(src.splitlines(), 1):
        assert not re.match(r"^\s+import re\s*$", line), f"line {lineno}: 发现函数级 import re"
    assert "import re" in src.splitlines()[:30], "模块顶部必须保留全局 import re"
