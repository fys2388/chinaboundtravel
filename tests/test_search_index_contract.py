"""P0-FIX (2026-09-20): 站内搜索索引污染契约测试。

实测（2026-09-20 线上 /index.json，83 条）：
    /success/  Payment Successful!
    /cancel/   Payment Cancelled
    /ebook/    ChinaBound Travel Guide 2026.08   （标题重复 2 次）
    /contact/  Contact ChinaBound Travel
    /terms-of-service/ /privacy-policy/ /affiliate-disclosure/ /disclaimer/

根因：themes/PaperMod/layouts/index.json 只过滤 searchHidden / archives /
search 三种情况，完全不读 site.Params.sitemapExclude。于是所有被
sitemapExclude 排掉的交易页/表单页仍进搜索索引。客户搜「visa」看到 30 条
结果，约 1/3 是无关内容。

修复：项目级 layouts/index.json 覆盖主题模板（83 -> 62 条，残留 0）。
本测试是静态契约检查（不联网、不跑 hugo），锁定关键实现点。
"""
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
INDEX = REPO / "layouts" / "index.json"
HUGO_TOML = REPO / "hugo.toml"
THEME_INDEX = REPO / "themes" / "PaperMod" / "layouts" / "index.json"

LEGAL_PAGES = [
    "content/contact.md", "content/terms-of-service.md",
    "content/privacy-policy.md", "content/affiliate-disclosure.md",
    "content/disclaimer.md",
]


def _read(p):
    return p.read_text(encoding="utf-8")


class TestSearchIndexTemplateOverride:
    def test_project_override_exists(self):
        assert INDEX.exists(), "缺少项目级 layouts/index.json 覆盖"

    def test_theme_template_is_still_polluted(self):
        """锁定根因：主题内建版确实不读 sitemapExclude。
        如果哪天主题升级补上了，这条会失败——那时应删除项目级覆盖。"""
        src = _read(THEME_INDEX)
        assert "sitemapExclude" not in src, (
            "PaperMod 主题已自行过滤 sitemapExclude —— 项目级覆盖可以移除了")

    def test_override_reads_sitemap_exclude(self):
        src = _read(INDEX)
        assert "site.Params.sitemapExclude" in src, "覆盖版未读 sitemapExclude"

    def test_override_strips_leading_slash(self):
        """RelPermalink 是 /success/，而 sitemapExclude 里是 "success"。
        不 TrimPrefix 的话 hasPrefix 永远不命中 —— 这是修复时的真实踩坑。"""
        src = _read(INDEX)
        assert 'strings.TrimPrefix "/"' in src

    def test_override_preserves_page_variable_in_nested_range(self):
        """内层 range $e := $excl 会把 . 换成字符串。
        不先 $page := . 保存会报
        "can't evaluate field RelPermalink in type interface {}"。"""
        src = _read(INDEX)
        assert "$page := ." in src
        assert "$page.RelPermalink" in src

    def test_override_keeps_theme_filters(self):
        """不能把主题原有的三个过滤条件弄丢。"""
        src = _read(INDEX)
        assert "searchHidden" in src
        assert 'archives' in src
        assert 'search' in src

    def test_hugo_toml_still_has_exclude_list(self):
        """单点来源：排除清单仍在 hugo.toml，模板不硬编码副本。"""
        src = _read(HUGO_TOML)
        assert "sitemapExclude" in src
        for key in ("success", "cancel", "ebook", "member-month", "static-package"):
            assert f'"{key}"' in src or f"'{key}'" in src


class TestLegalPagesHiddenFromSearch:
    """交易/表单/法务页应当存在于站点（能被 Google 索引、能被直接访问），
    但不应出现在站内搜索里。手段是 front-matter 的 searchHidden。"""

    def test_all_legal_pages_exist(self):
        for rel in LEGAL_PAGES:
            assert (REPO / rel).exists(), f"缺少 {rel}"

    def test_all_legal_pages_have_search_hidden(self):
        for rel in LEGAL_PAGES:
            src = _read(REPO / rel)
            head = src.split("---", 2)[1] if src.lstrip().startswith("---") \
                else src.split("+++", 2)[1]
            assert "searchHidden" in head, (
                f"{rel} front-matter 缺 searchHidden —— 会重新出现在搜索索引里")
            assert 'searchHidden: true' in head or 'searchHidden = true' in head

    def test_transaction_pages_excluded_via_sitemap(self):
        """success / cancel 走 sitemapExclude 路线（它们本就不该被 Google 索引）。"""
        src = _read(HUGO_TOML)
        assert '"success"' in src and '"cancel"' in src

    def test_search_hidden_does_not_break_sitemap_for_legal_pages(self):
        """法务页必须在 sitemap 里（Google 要能索引它们），
        所以只能用 searchHidden，不能把它们加进 sitemapExclude。"""
        src = _read(HUGO_TOML)
        for name in ("contact", "terms-of-service", "privacy-policy",
                     "affiliate-disclosure", "disclaimer"):
            assert f'"{name}"' not in src.split("sitemapExclude")[-1].split("]")[0], (
                f'{name} 被加进 sitemapExclude 了 —— 那会让 Google 也索引不到它')
