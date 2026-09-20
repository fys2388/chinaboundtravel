"""P0-FIX (2026-09-20): /search/ 空状态与无结果提示契约测试。

实测（2026-09-20 线上）：
  - 首页主 CTA「🗺️ Plan Your China Trip」指向 /search/
  - 客户点进来：list "search results" 为空，无引导语
  - 输入 zzzqqqxxxnonexistent123：列表依然空白，无「无结果」提示

主题版 fastsearch.js 的 renderResults([]) 只做 resList.innerHTML = ''，
initSearch 的 catch 只 console.error —— 客户分不清「没结果」和「坏了」，
3 秒内看不到任何东西就关掉标签页。首页 CTA 的转化率死在这里。

本测试锁定项目级覆盖版 assets/js/fastsearch.js 的关键实现点。
"""
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OVERRIDE = REPO / "assets" / "js" / "fastsearch.js"
THEME = REPO / "themes" / "PaperMod" / "assets" / "js" / "fastsearch.js"
CSS = REPO / "assets" / "css" / "extended" / "custom-search.css"
THEME_HEAD = REPO / "themes" / "PaperMod" / "layouts" / "_partials" / "head.html"


def _read(p):
    return p.read_text(encoding="utf-8")


class TestFastsearchOverride:
    def test_override_exists(self):
        assert OVERRIDE.exists(), "缺少项目级 assets/js/fastsearch.js"

    def test_theme_version_is_still_blind(self):
        """锁定根因：主题版确实没有空状态文案。
        主题一旦补上，这条会失败，提示可以移除项目级覆盖。"""
        src = _read(THEME)
        for marker in ("No guides found", "search-empty", "temporarily unavailable"):
            assert marker not in src

    def test_hugo_prefers_project_assets(self):
        """head.html 用 resources.Get 加载，项目 assets/ 优先于主题。"""
        src = _read(THEME_HEAD)
        assert 'resources.Get "js/fastsearch.js"' in src

    def test_empty_state_hint_present(self):
        src = _read(OVERRIDE)
        assert "EMPTY_HINT" in src
        assert "search-empty" in src

    def test_no_results_shows_suggestions(self):
        """无结果时必须给真实存在的高频主题，不能让客户死路一条。"""
        src = _read(OVERRIDE)
        assert "showNoResults" in src
        assert "SUGGESTED" in src
        assert "search-suggest" in src

    def test_no_results_suggestions_are_real_topics(self):
        """建议词必须真实存在于站点里，否则点下去还是空白。"""
        src = _read(OVERRIDE)
        for topic in ("visa", "Alipay", "eSIM"):
            assert topic in src

    def test_load_error_is_visible(self):
        """index.json 拉不到时不能静默 —— 主题版只 console.error。"""
        src = _read(OVERRIDE)
        assert "showLoadError" in src
        assert "temporarily unavailable" in src
        assert 'console.error' in src  # 保留原有的控制台诊断

    def test_empty_list_no_longer_blank(self):
        """renderResults([]) 必须落到一个提示分支，不能清空后什么都不渲染。"""
        src = _read(OVERRIDE)
        assert "clearResults()" in src
        # renderResults 的空分支里必须有渲染动作
        body = src[src.index("const renderResults"):]
        body = body[:body.index("const performSearch")]
        assert "showNoResults" in body and "showHint" in body

    def test_xss_escaped(self):
        """把用户输入回显到 innerHTML 时必须转义。"""
        src = _read(OVERRIDE)
        assert "escapeHtml" in src
        assert "showNoResults(sInput.value.trim())" in src
        assert "escapeHtml(query)" in src

    def test_theme_behavior_preserved(self):
        """覆盖版不能把主题原有的键盘导航、防抖、Fuse 选项弄丢。"""
        src = _read(OVERRIDE)
        for token in ("ArrowDown", "ArrowUp", "ArrowRight", "Escape",
                      "debounce", "buildFuseOptions", "defaultFuseOptions"):
            assert token in src, f"覆盖了主题逻辑，缺 {token}"


class TestSearchEmptyStyles:
    """没有样式的话，提示语会以裸文本挤在结果列表里。"""

    def test_css_exists(self):
        assert CSS.exists(), "缺少 assets/css/extended/custom-search.css"

    def test_hugo_wires_extended_css(self):
        src = _read(THEME_HEAD)
        assert 'resources.Match "css/extended/*.css"' in src

    def test_css_covers_all_new_classes(self):
        src = _read(CSS)
        for cls in (".search-empty", ".search-error", ".search-suggest"):
            assert cls in src
