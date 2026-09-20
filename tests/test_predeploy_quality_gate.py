"""闸门必须能看见 GA4 双计 —— 这是它上一次漏掉的真实缺陷。

真实事故链（2026-09-20 复盘）：
  线上首页每次 page_view 同时 POST
      /vo5w/ga/g/c?tid=G-P6BH500VBK   和   /vo5w/ga/g/c?tid=G-GECBME3YVJ
  仓库里只有 G-GECBME3YVJ，另一个来自部署层（Cloudflare Worker / Transform Rule）。

  旧闸门实现只匹配 googletagmanager.com/gtag/js?id= —— 那是**加载脚本**。
  双计场景里第二个 ID 出现在 **collect 路径 tid=** 里，正则完全看不见。
  结果：reports/quality/predeploy_quality.json（2026-09-14）显示
  issues=0 / P0=0 / P1=0，闸门"通过"，双计在 main 分支上跑了 6 天无人拦截。
  而那时 users_28d / sessions_28d / engagement_rate_28d 正被当 LIVE KPI 上报。

  这些测试用合成 HTML 复现，锁定检测范围与严重度，防止回退。
"""
from pathlib import Path

from scripts.predeploy_quality_gate import audit_static_site


SITE_HOSTS = {"www.chinaboundtravel.com", "chinaboundtravel.com"}

# 真实线上 ID（hugo.toml 里的那个）
REAL = "G-GECBME3YVJ"
# 部署层注入的那个（仓库里不存在）
PHANTOM = "G-P6BH500VBK"


def _page(body: str) -> str:
    """包一个最小合法页面：H1 一个、canonical 指向自己、有 alt 的图片。
    只让「分析标记」这一个检查说话，其余检查不产生噪声。"""
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<title>China Travel Guide</title>
<link rel="canonical" href="https://www.chinaboundtravel.com/">
{body}
</head><body><h1>China Travel Guide</h1></body></html>
"""


def _write(tmp, rel, html):
    p = tmp / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html, encoding="utf-8")
    return p


def _types(report):
    return [i["type"] for i in report["issues"]]


def _by_type(report, t):
    return [i for i in report["issues"] if i["type"] == t]


class TestMultipleAnalyticsTagsDetection:
    def test_single_id_passes(self, tmp_path):
        _write(tmp_path, "index.html", _page(
            f'<script async src="https://www.googletagmanager.com/gtag/js?id={REAL}"></script>'))
        report = audit_static_site(tmp_path, SITE_HOSTS)
        assert _types(report) == []
        assert report["summary"]["P0"] == 0

    def test_two_ids_in_loader_scripts(self, tmp_path):
        """经典形态：两个 gtag.js 加载脚本。旧正则本来能抓到。"""
        _write(tmp_path, "index.html", _page(
            f'<script async src="https://www.googletagmanager.com/gtag/js?id={REAL}"></script>'
            f'<script async src="https://www.googletagmanager.com/gtag/js?id={PHANTOM}"></script>'))
        report = audit_static_site(tmp_path, SITE_HOSTS)
        hits = _by_type(report, "multiple_analytics_tags")
        assert len(hits) == 1
        assert hits[0]["severity"] == "P0"
        assert REAL in hits[0]["evidence"]
        assert PHANTOM in hits[0]["evidence"]

    def test_id_hidden_in_collect_path_tid(self, tmp_path):
        """真实事故形态：只有一个加载脚本，第二个 ID 藏在 collect 路径 tid= 里。
        旧正则（只匹配 gtag/js?id=）对这个形态完全失明。"""
        body = (
            f'<script async src="https://www.googletagmanager.com/gtag/js?id={REAL}"></script>'
            '<script>window.gtag=function(){};'
            f"var u='/vo5w/ga/g/c?v=2&tid={PHANTOM}&en=page_view';"
            "fetch(u,{method:'POST'});</script>"
        )
        _write(tmp_path, "index.html", _page(body))
        report = audit_static_site(tmp_path, SITE_HOSTS)
        hits = _by_type(report, "multiple_analytics_tags")
        assert len(hits) == 1, report["issues"]
        assert hits[0]["severity"] == "P0"
        assert PHANTOM in hits[0]["evidence"]

    def test_id_in_gtag_config_call(self, tmp_path):
        """inline gtag('config', 'G-XXX') 形态也必须被抓。"""
        body = (
            f'<script async src="https://www.googletagmanager.com/gtag/js?id={REAL}"></script>'
            f"<script>window.gtag=function(){{}};gtag('config','{PHANTOM}');</script>"
        )
        _write(tmp_path, "index.html", _page(body))
        report = audit_static_site(tmp_path, SITE_HOSTS)
        assert len(_by_type(report, "multiple_analytics_tags")) == 1

    def test_severity_is_p0(self, tmp_path):
        """双计会让所有流量/营收 KPI 失真 —— 一个"看起来干净"的错误数字
        比显示 0 更危险，所以是 P0 而不是 P1。"""
        _write(tmp_path, "index.html", _page(
            f'<script async src="https://www.googletagmanager.com/gtag/js?id={REAL}"></script>'
            f'<script>window.gtag=function(){{}};gtag("config","{PHANTOM}");</script>'))
        report = audit_static_site(tmp_path, SITE_HOSTS)
        assert report["summary"]["P0"] >= 1
        assert report["summary"]["P1"] == 0

    def test_body_prose_is_not_scanned(self, tmp_path):
        """只扫 <script> 与 HTML 属性，不扫正文散文 ——
        文章里正常提到 "G-XXXXXXXX" 字样不该误拦部署。"""
        body = (
            f'<script async src="https://www.googletagmanager.com/gtag/js?id={REAL}"></script>'
        )
        html = _page(body).replace(
            "<h1>China Travel Guide</h1>",
            f"<h1>China Travel Guide</h1><p>Analytics code {PHANTOM} is optional. "
            f"Compare {REAL} and {PHANTOM} in the wild.</p>")
        _write(tmp_path, "index.html", html)
        report = audit_static_site(tmp_path, SITE_HOSTS)
        assert _by_type(report, "multiple_analytics_tags") == []

    def test_multi_page_dedupe_per_page(self, tmp_path):
        """两个页面各自双计 -> 两条 issue；两页共用同一个第二 ID 不去重掉。"""
        body = (
            f'<script async src="https://www.googletagmanager.com/gtag/js?id={REAL}"></script>'
            f'<script>gtag("config","{PHANTOM}");</script>'
        )
        _write(tmp_path, "index.html", _page(body))
        _write(tmp_path, "pricing/index.html", _page(body))
        report = audit_static_site(tmp_path, SITE_HOSTS)
        hits = _by_type(report, "multiple_analytics_tags")
        assert len(hits) == 2
        assert {h["page"] for h in hits} == {"/", "/pricing/"}
