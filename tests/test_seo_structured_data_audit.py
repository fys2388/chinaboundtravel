"""SEO 结构化数据审计的回归测试。

守护 2026-09-18 的两处缺陷：
1. **Hugo 无引号属性漏检**：Hugo/PaperMod 把无特殊字符的属性渲染成无引号形式
   （<meta charset=utf-8>、<link rel=canonical href=...>、
   <script type=application/ld+json>）。要求 type="..." / rel="..." 的审计
   会静默漏掉全部命中，报告「结构化数据覆盖率 0%」。本轮先用这种正则得出
   「472 页 0 个 JSON-LD、canonical 仅 3/472」的结论，修正后实测是
   287 页有 JSON-LD、canonical 466/472——两个结论都是假的。
2. **分页页被当成文章**：posts/page/1/index.html 不是文章，
   计入会让文章覆盖率变成 69/74 这种被分页污染的数字。

另有内容层缺陷（不在此修复，仅验证能被检出）：
   content/posts 有 2 篇文章把 {{< soft-recommend >}} shortcode 写进了
   front-matter 的 description 字段，Hugo 只在正文渲染 shortcode，
   于是原始语法泄漏进 meta description / og:description / twitter:description。
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import seo_structured_data_audit as S  # noqa: E402


# ── 夹具：手写最小构建产物 ───────────────────────────────────

LD_VALID = '{"@context":"https://schema.org","@type":"Article","headline":"x"}'
LD_ARRAY = '{"@context":"https://schema.org","@type":["WebPage","BlogPosting"]}'


def _write(root: Path, rel: str, body: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    return p


def _post(root: Path, name: str, ld: str = "") -> Path:
    return _write(
        root, f"posts/{name}/index.html",
        f"<html><head>{ld}</head><body><h1>{name}</h1></body></html>",
    )


# ── 无引号属性：本轮的核心回归 ────────────────────────────────

@pytest.mark.parametrize("tag", [
    '<script type=application/ld+json>' + LD_VALID + '</script>',
    '<script type="application/ld+json">' + LD_VALID + '</script>',
    '<script type=\'application/ld+json\'>' + LD_VALID + '</script>',
    '<script type="application/ld+json" class="x">' + LD_VALID + '</script>',
])
def test_ld_detected_regardless_of_quoting(tag, tmp_path):
    """双引号 / 单引号 / 无引号三种形式都必须检出。

    Hugo 实际输出的是无引号形式；漏掉它会得到 0% 覆盖率的假结论。
    """
    _write(tmp_path, "index.html", f"<html>{tag}</html>")
    r = S.audit(tmp_path)
    assert r["pages_with_structured_data"] == 1, tag


@pytest.mark.parametrize("tag", [
    '<link rel=canonical href=/x>',
    '<link rel="canonical" href="/x">',
    '<link rel=\'canonical\' href=\'/x\'>',
    '<link rel=canonical href=https://a.com/x>',
])
def test_canonical_detected_regardless_of_quoting(tag, tmp_path):
    _write(tmp_path, "index.html", f"<html><head>{tag}</head></html>")
    r = S.audit(tmp_path)
    assert r["canonical_pages"] == 1, tag


def test_unquoted_meta_is_ignored_not_miscounted(tmp_path):
    """无引号 meta 不应被当成 canonical。"""
    _write(tmp_path, "index.html",
           '<html><head><meta charset=utf-8><meta name=description content="x"></head></html>')
    r = S.audit(tmp_path)
    assert r["canonical_pages"] == 0
    assert r["structured_data_coverage_pct"] == 0.0


# ── JSON 有效性与 @type ──────────────────────────────────────

def test_valid_and_invalid_json_counted_separately(tmp_path):
    _post(tmp_path, "ok", f'<script type="application/ld+json">{LD_VALID}</script>')
    _post(tmp_path, "bad", '<script type="application/ld+json">{"@type": "Article",</script>')
    r = S.audit(tmp_path)
    assert r["json_blocks_valid"] == 1
    assert r["json_blocks_invalid"] == 1
    assert r["invalid_samples"] and "bad" in r["invalid_samples"][0]["page"]


def test_array_type_form_extracted(tmp_path):
    _post(tmp_path, "a", f'<script type="application/ld+json">{LD_ARRAY}</script>')
    r = S.audit(tmp_path)
    assert r["type_counts"].get("WebPage") == 1
    assert r["type_counts"].get("BlogPosting") == 1


def test_multiple_blocks_on_one_page(tmp_path):
    body = (f'<script type="application/ld+json">{LD_VALID}</script>'
            f'<script type="application/ld+json">{LD_ARRAY}</script>')
    _post(tmp_path, "multi", body)
    r = S.audit(tmp_path)
    assert r["json_blocks_valid"] == 2
    assert r["pages_with_structured_data"] == 1  # 按页计，不按块计


# ── 分页页排除 ───────────────────────────────────────────────

def test_pagination_pages_excluded_from_post_count(tmp_path):
    """回归：posts/page/N/ 不是文章，不能拉低文章覆盖率。"""
    _post(tmp_path, "real-article")
    _write(tmp_path, "posts/page/1/index.html", "<html><body>page</body></html>")
    _write(tmp_path, "posts/page/2/index.html", "<html><body>page</body></html>")
    r = S.audit(tmp_path)
    assert r["post_pages"] == 1, r["post_pages"]
    assert r["post_structured_data_coverage_pct"] == 0.0
    assert not any("/page/" in p for p in r["posts_missing_structured_data"])


# ── 模板残留 ─────────────────────────────────────────────────

@pytest.mark.parametrize("snippet,expected", [
    ('{{< soft-recommend partner="esim" >}}', "soft-recommend"),
    ("{{% affiliate-coupon %}}", "affiliate-coupon"),
])
def test_unexecuted_shortcode_residue_detected(snippet, expected, tmp_path):
    """front-matter 里嵌 shortcode 会原样泄漏进 meta description。"""
    _write(tmp_path, "index.html",
           f'<html><head><meta name=description content=\'{snippet} tail\'></head></html>')
    r = S.audit(tmp_path)
    assert r["template_residue_count"] == 1
    assert r["template_residue"][0]["shortcode"] == expected
    assert r["blocking"] is True


def test_normal_shortcode_execution_is_not_residue(tmp_path):
    """已经渲染成 HTML 的联盟链接不是残留。"""
    _post(tmp_path, "a", f'<script type="application/ld+json">{LD_VALID}</script>')
    r = S.audit(tmp_path)
    assert r["template_residue_count"] == 0
    assert r["blocking"] is False


# ── 覆盖率与 blocking ────────────────────────────────────────

def test_coverage_percentages_are_computed(tmp_path):
    _post(tmp_path, "a", f'<script type="application/ld+json">{LD_VALID}</script>')
    _post(tmp_path, "b")  # 无结构化数据
    r = S.audit(tmp_path)
    assert r["structured_data_coverage_pct"] == 50.0
    assert r["post_structured_data_coverage_pct"] == 50.0


def test_missing_build_dir_reports_reason_and_blocks(tmp_path):
    r = S.audit(tmp_path / "no-such-dir")
    assert r["blocking"] is True
    assert r["reason"]
    assert r["pages_total"] == 0


def test_empty_build_dir_reports_reason(tmp_path):
    r = S.audit(tmp_path)
    assert r["blocking"] is True
    assert r["reason"]


# ── CLI ──────────────────────────────────────────────────────

def _cli(tmp_path, *extra):
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "seo_structured_data_audit.py"),
         "--build", str(tmp_path), *extra],
        capture_output=True, text=True, encoding="utf-8",
    )


def test_cli_json_is_valid_and_complete(tmp_path):
    _post(tmp_path, "a", f'<script type="application/ld+json">{LD_VALID}</script>')
    p = _cli(tmp_path, "--json")
    assert p.returncode == 0, p.stderr
    data = json.loads(p.stdout)
    for key in ("pages_total", "structured_data_coverage_pct",
                "canonical_coverage_pct", "json_blocks_valid", "blocking"):
        assert key in data


def test_cli_plain_output_names_coverage(tmp_path):
    _post(tmp_path, "a", f'<script type="application/ld+json">{LD_VALID}</script>')
    p = _cli(tmp_path)
    assert p.returncode == 0
    assert "结构化数据覆盖" in p.stdout


def test_cli_fail_exits_nonzero_on_residue(tmp_path):
    """残留属于阻塞问题，--fail 必须 exit 1 才能当 CI 闸门。"""
    _write(tmp_path, "index.html", '<html><meta name=description content="{{< soft-recommend >}}"></html>')
    p = _cli(tmp_path, "--fail")
    assert p.returncode == 1, p.stdout


def test_cli_fail_exits_zero_when_clean(tmp_path):
    _post(tmp_path, "a", f'<script type="application/ld+json">{LD_VALID}</script>')
    p = _cli(tmp_path, "--fail")
    assert p.returncode == 0, p.stdout


# ── KPI 接入 ─────────────────────────────────────────────────

def test_measure_structured_data_returns_empty_without_public(tmp_path):
    """没有 public/ 时返回 {}，对应 KPI 标 no_data 而不是 70 分默认值。"""
    import agent_kpi_auditor as A
    assert A.measure_structured_data(tmp_path) == {}


def test_measure_structured_data_reads_public(tmp_path):
    import agent_kpi_auditor as A
    pub = tmp_path / "public"
    _post(pub, "a", f'<script type="application/ld+json">{LD_VALID}</script>')
    _post(pub, "b")
    r = A.measure_structured_data(tmp_path)
    assert r["structured_data_coverage_pct"] == 50.0


def test_collect_metrics_wires_seo_structured_data_when_public_exists(tmp_path, monkeypatch):
    import agent_kpi_auditor as A
    pub = tmp_path / "public"
    _post(pub, "a", f'<script type="application/ld+json">{LD_VALID}</script>')
    monkeypatch.setattr(A, "PROJECT_ROOT", tmp_path)
    m = A.collect_metrics()
    assert m["seo"]["structured_data"] == 100.0
    assert m["seo"]["canonical_consistency"] == 0.0
