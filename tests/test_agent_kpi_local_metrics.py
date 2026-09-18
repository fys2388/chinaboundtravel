"""本地可实测 KPI 与归一化器的回归测试。

守护 2026-09-18 的三处修复：
  1. 零基准目标语义反转：broken_affiliate_links 目标「0个」，value=0（零个坏链接
     = 满分）原先被 `0 <= value <= 100` 的百分比分支吃掉，直接返回 0.0 分。
  2. 整数 0 被当比率：publish_rate=0 篇/周 原先落进 `0 <= value <= 1 → value*100`，
     返回 0.0 分。收紧为 `0 < value <= 1` 后，任何 0 值统一走目标比较分支。
  3. 五个此前恒为 70 分默认值的 KPI 接入仓库内可实测数据。
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import agent_kpi_auditor as A  # noqa: E402


def kpi(kpi_id: str, target: str, ktype: str = "quality") -> dict:
    return {"id": kpi_id, "target": target, "type": ktype}


# ── 归一化器：零基准目标 ────────────────────────────────────────

@pytest.mark.parametrize("value,expected", [
    (0, 100.0),   # 零个坏链接 = 满分
    (0.0, 100.0),
    (1, 30.0),    # 出现坏链接 = 不合格
    (5, 30.0),
])
def test_zero_baseline_target_scores_zero_as_perfect(value, expected):
    """回归：零基准 KPI 的 value=0 必须是满分，不能落进百分比/比率分支。

    原先 type="quality" 且 value=0 会被 `0 <= value <= 100` 分支直接 return 0.0，
    「零个坏链接」拿了最低分，语义完全反转。
    """
    got = A.normalize_metric_to_score(kpi("broken_affiliate_links", "0个"), value)
    assert got == expected, f"value={value!r} 期望 {expected}，实际 {got}"


def test_zero_baseline_not_swallowed_by_percentage_branch():
    """type=quality + value=0 必须走零基准分支，不是百分比分支。"""
    assert A.normalize_metric_to_score(kpi("x", "0个", "quality"), 0) == 100.0
    # 对照：真百分比口径的 quality 指标 value=0 仍是 0（目标非 0）
    assert A.normalize_metric_to_score(kpi("y", "100%", "quality"), 0) == 0.0


def test_zero_baseline_ignores_percent_sign_in_target():
    """target 含 % 时不适用零基准逻辑（那是真正的百分比口径）。"""
    assert A.normalize_metric_to_score(kpi("y", "0%", "quality"), 0) == 0.0


# ── 归一化器：整数 0 不再是 0 分 ─────────────────────────────────

def test_count_metric_zero_is_far_below_target_not_zero():
    """回归：publish_rate=0 篇/周 应得 30（远低于目标），不是 0。

    原先 `0 <= 0 <= 1` 命中「0-1 比率」分支，返回 0*100=0.0。
    """
    got = A.normalize_metric_to_score(kpi("publish_rate", "≥4篇/周", "process"), 0)
    assert got == 30.0, f"0 篇/周 应得 30（远低于目标），实际 {got}"


def test_count_metric_positive_still_compares_to_target():
    assert A.normalize_metric_to_score(kpi("publish_rate", "≥4篇/周", "process"), 5) == 95.0
    assert A.normalize_metric_to_score(kpi("publish_rate", "≥4篇/周", "process"), 2) == 50.0


def test_true_ratio_still_converted():
    """收紧为 0 < value <= 1 后，真比率（如 engagement_rate=0.05）不受影响。"""
    assert A.normalize_metric_to_score(kpi("engagement_rate", "≥3%", "process"), 0.05) == 5.0


def test_percent_passthrough_unchanged():
    assert A.normalize_metric_to_score(kpi("affiliate_compliance", "100%合规", "quality"), 100.0) == 100.0
    assert A.normalize_metric_to_score(kpi("mojibake_free", "100%", "quality"), 60.0) == 60.0


def test_large_value_scaled_by_target():
    assert A.normalize_metric_to_score(kpi("avg_word_count", "≥1500字", "process"), 1904) == 95.0
    assert A.normalize_metric_to_score(kpi("avg_word_count", "≥1500字", "process"), 800) == 50.0


def test_none_is_baseline_score():
    assert A.normalize_metric_to_score(kpi("ebook_revenue", "环比增长≥15%", "revenue"), None) == 70.0


# ── 内容指标实测 ────────────────────────────────────────────────

def _write_post(root: Path, name: str, date_offset_days, words: int) -> Path:
    d = root / "content" / "posts"
    d.mkdir(parents=True, exist_ok=True)
    date = (datetime.now() - timedelta(days=date_offset_days)).strftime("%Y-%m-%d")
    body = ("word " * words).strip()
    p = d / name
    p.write_text(
        f"---\ntitle: \"T {words}\"\ndate: {date}\ntags: [test]\n---\n\n{body}\n",
        encoding="utf-8",
    )
    return p


def test_publish_rate_uses_frontmatter_date_not_git_log(tmp_path):
    """回归：发布率必须按 front-matter 的 date 算。

    git log --since=7d --name-only 会返回所有被提交触碰过的文件；
    本仓库机器人每 30 分钟批量提交，一次就 name-only 出全部文章，
    发布率会被算成「全部文章数/周」，比硬编码 4.0 更离谱。
    """
    _write_post(tmp_path, "a.md", 0, 2000)
    _write_post(tmp_path, "b.md", 6, 2000)
    _write_post(tmp_path, "c.md", 30, 2000)   # 30 天前，不该计入
    _write_post(tmp_path, "d.md", 90, 2000)   # 90 天前，不该计入

    m = A.measure_content_stats(tmp_path)
    assert m["publish_rate"] == 2, f"近 7 天应只有 2 篇，实际 {m['publish_rate']}"
    assert m["_posts_total"] == 4


def test_publish_rate_is_never_the_total_post_count(tmp_path):
    """口径防回归：发布率绝不可能等于文章总数（git-log 误用的特征症状）。"""
    for i in range(20):
        _write_post(tmp_path, f"p{i}.md", 200, 1000)
    m = A.measure_content_stats(tmp_path)
    assert m["publish_rate"] < m["_posts_total"], "发布率等于文章总数 = 用了 git log 口径"


def test_avg_word_count_excludes_frontmatter_and_tags(tmp_path):
    _write_post(tmp_path, "only.md", 0, 300)
    m = A.measure_content_stats(tmp_path)
    # 正文 300 词；front matter 里有 title/date/tags 等额外词，若未剥离会虚高
    assert m["avg_word_count"] == pytest.approx(300, abs=2), m["avg_word_count"]


def test_content_stats_empty_dir_returns_empty(tmp_path):
    assert A.measure_content_stats(tmp_path) == {}


# ── 联盟合规实测 ────────────────────────────────────────────────

def _write_shortcode(root: Path, name: str, body: str) -> Path:
    d = root / "layouts" / "shortcodes"
    d.mkdir(parents=True, exist_ok=True)
    p = d / name
    p.write_text(body, encoding="utf-8")
    return p


def test_internal_link_is_not_counted_as_affiliate(tmp_path):
    """回归：/disclosure/ 这类站内链接不是联盟链接，不该拉低合规率。

    原先统计所有 <a>，affiliate-disclosure.html 的 href="/disclosure/" 被算进去，
    得出 11/12 = 91.7% 的假不合规。
    """
    _write_shortcode(
        tmp_path, "affiliate-esim.html",
        '<a href="https://www.airalo.com/" rel="sponsored noopener">eSIM</a>',
    )
    _write_shortcode(
        tmp_path, "affiliate-disclosure.html",
        '联盟披露：<a href="/disclosure/">查看详情</a>',
    )
    m = A.measure_affiliate_compliance(tmp_path)
    assert m["_affiliate_external_total"] == 1, m
    assert m["affiliate_compliance"] == 100.0


def test_unsponsored_external_link_lowers_compliance(tmp_path):
    _write_shortcode(
        tmp_path, "affiliate-esim.html",
        '<a href="https://www.airalo.com/" rel="noopener">eSIM</a>',
    )
    _write_shortcode(
        tmp_path, "affiliate-klook.html",
        '<a href="https://klook.cn/" rel="sponsored noopener">Klook</a>',
    )
    m = A.measure_affiliate_compliance(tmp_path)
    assert m["_affiliate_external_total"] == 2
    assert m["affiliate_compliance"] == 50.0, m["affiliate_compliance"]


def test_broken_link_detected_and_excluded_from_compliance(tmp_path):
    """href="#" 应计为坏链接，且不参与合规率分母。"""
    _write_shortcode(
        tmp_path, "affiliate-cta.html",
        '<a href="#" rel="sponsored">CTA</a>'
        '<a href="https://www.booking.com/?aid=730795" rel="sponsored">Booking</a>',
    )
    m = A.measure_affiliate_compliance(tmp_path)
    assert m["broken_affiliate_links"] == 1
    assert m["_affiliate_external_total"] == 1
    assert m["affiliate_compliance"] == 100.0


@pytest.mark.parametrize("href", ['https://a.com/', 'https://a.com', "https://a.com/"])
def test_unquoted_and_single_quoted_href_are_parsed(tmp_path, href):
    """Hugo 输出无引号属性；漏解析会静默漏掉合规检查。"""
    _write_shortcode(
        tmp_path, "affiliate-x.html",
        f'<a href={href} rel="sponsored">x</a>',
    )
    m = A.measure_affiliate_compliance(tmp_path)
    assert m["_affiliate_external_total"] == 1, m


def test_no_affiliate_shortcodes_returns_empty(tmp_path):
    assert A.measure_affiliate_compliance(tmp_path) == {}


# ── 日报时效 ────────────────────────────────────────────────────

def _daily_file(root: Path, name: str) -> Path:
    d = root / "reports" / "feishu_daily"
    d.mkdir(parents=True, exist_ok=True)
    p = d / name
    p.write_text("{}", encoding="utf-8")
    return p


@pytest.mark.parametrize("offset,expected", [(0, 100.0), (1, 50.0), (2, 0.0), (9, 0.0)])
def test_report_timeliness_buckets(offset, expected, tmp_path):
    name = f"daily_{(datetime.now() - timedelta(days=offset)).strftime('%Y-%m-%d')}.json"
    _daily_file(tmp_path, name)
    assert A.measure_report_timeliness(tmp_path) == expected


def test_report_timeliness_uses_filename_not_mtime(tmp_path):
    """mtime 会被 git checkout / CI 复制改写，必须读文件名日期。"""
    _daily_file(tmp_path, "daily_2026-01-01.json")
    assert A.measure_report_timeliness(tmp_path) == 0.0


def test_report_timeliness_no_files_is_zero(tmp_path):
    assert A.measure_report_timeliness(tmp_path) == 0.0


# ── collect_metrics 集成 ────────────────────────────────────────

def test_collect_metrics_wires_local_metrics():
    m = A.collect_metrics()
    assert m["content"]["avg_word_count"] is not None
    assert m["content"]["publish_rate"] is not None
    assert m["revenue"]["affiliate_compliance"] is not None
    assert m["revenue"]["broken_affiliate_links"] is not None
    assert m["data"]["report_timeliness"] is not None


def test_collect_metrics_coverage_at_least_fourteen_of_48():
    """接入 5 个新指标后覆盖率应到 14/48（此前 9/48）。"""
    m = A.collect_metrics()
    total = m["data"]["_total_count"]
    measured = m["data"]["_measured_count"]
    assert total == 48
    assert measured >= 14, f"覆盖率不足：{measured}/{total}"


def test_broken_affiliate_links_zero_scores_perfect_in_live_data():
    """端到端：当前仓库坏链接为 0，归一化后必须是 100 分（不是 0 分）。"""
    m = A.collect_metrics()
    val = m["revenue"]["broken_affiliate_links"]
    kpi_def = next(k for k in A.AGENTS["revenue"]["kpis"] if k["id"] == "broken_affiliate_links")
    score = A.normalize_metric_to_score(kpi_def, val)
    assert score == 100.0, f"坏链接 {val} 个应得 100 分，实际 {score}"
