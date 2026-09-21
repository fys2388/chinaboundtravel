"""tests/test_internal_traffic_filter.py

锁定报表层内部流量剔除行为。

背景：GA4 流量榜前 3 名里有两个是内部运营页（/ops-dashboard/ 173 pv、
/ops/ops-center 70 pv，首页仅 98 pv），占全站 33.4% pageview。这些访问来自
bot 与 agent 会话轮询，不是真实访客。不剔除的话 agent 会把运营看板读成
「表现最好的内容」，进而论证出「应该多做内部工具」这类荒谬结论。

方案 2（报表层黑名单）的三条不可退让的性质，本文件逐条锁定：
  1. 过滤只做减法，不改入参、不改原始数据文件；
  2. 判定要能抗 query/hash/尾斜杠变体，不能靠字符串前缀裸奔；
  3. 公开流量占比必须是**下限**而不是精确值——分子只能从 top_pages 覆盖范围
     里精确算，分母是全站汇总，内部页若未上榜就漏掉了。报成精确值就是造假。
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import internal_traffic_filter as ITF  # noqa: E402


# ── 判定 ────────────────────────────────────────────────────

def test_ops_variants_all_detected():
    """/ops-dashboard/ 与 /ops/ops-center 必须同时命中。"""
    for path in ("/ops", "/ops/", "/ops-dashboard/", "/ops-dashboard/?tab=kpi",
                 "/ops/ops-center", "/ops/ops-center.html", "/ops/agent-kpi"):
        assert ITF.is_internal_path(path), path


def test_public_pages_not_excluded():
    """绝不能误伤公共页——包括名字里带 ops 的合法内容页。"""
    for path in ("/", "/pricing/", "/posts/", "/about/", "/products/",
                 "/ops-guide-for-travelers/", "/post-operator-tips/",
                 "/blog/operations-in-china/"):
        assert not ITF.is_internal_path(path), path


def test_empty_and_none_safe():
    assert ITF.is_internal_path(None) is False
    assert ITF.is_internal_path("") is False
    assert ITF.is_internal_path("   ") is False


# ── 过滤：只做减法 ──────────────────────────────────────────

def _sample_pages():
    return [
        {"path": "/ops-dashboard/", "views": 173, "pageviews": 173},
        {"path": "/", "views": 98, "pageviews": 98},
        {"path": "/ops/ops-center", "views": 45, "pageviews": 45},
        {"path": "/pricing/", "views": 15, "pageviews": 15},
    ]


def test_filter_splits_without_mutating_input():
    pages = _sample_pages()
    snapshot = [dict(p) for p in pages]
    kept, excluded = ITF.filter_pages(pages)
    assert len(kept) + len(excluded) == len(pages)
    assert [p["path"] for p in excluded] == ["/ops-dashboard/", "/ops/ops-center"]
    assert [p["path"] for p in kept] == ["/", "/pricing/"]
    # 入参不受影响：过滤不能就地修改调用方的数据
    assert pages == snapshot


def test_filter_is_idempotent():
    pages = _sample_pages()
    _, first = ITF.filter_pages(pages)
    _, second = ITF.filter_pages(pages)
    assert first == second


def test_filter_survives_missing_keys():
    """缺 path 的条目应保留（不做臆断），缺 views 的不应抛异常。"""
    pages = [{"path": "/ops/"}, {"path": "/x/", "views": 3}, {"views": 1}]
    kept, excluded = ITF.filter_pages(pages)
    assert len(kept) == 2 and len(excluded) == 1


def test_filter_returns_copies():
    """返回副本，下游改动不能反向污染调用方。"""
    pages = _sample_pages()
    kept, excluded = ITF.filter_pages(pages)
    kept[0]["views"] = 999
    excluded[0]["views"] = 1
    assert pages[1]["views"] == 98 and pages[0]["views"] == 173


# ── 剔除体量 ────────────────────────────────────────────────

def test_excluded_volume_sums_both_field_names():
    """GA4 有的地方叫 pageviews，飞书日报那边叫 views，两种都要能加。"""
    kept, excluded = ITF.filter_pages(_sample_pages())
    vol = ITF.excluded_volume(excluded)
    assert vol == {"pages": 2, "pageviews": 218, "sessions": 0, "users": 0}


def test_excluded_volume_tolerates_string_numbers():
    vol = ITF.excluded_volume([{"path": "/ops/", "pageviews": "173", "sessions": "45"}])
    assert vol["pageviews"] == 173 and vol["sessions"] == 45


# ── 公开流量占比：必须是下限 ────────────────────────────────

def test_share_is_a_lower_bound_not_an_estimate():
    metrics = {"screenPageViews": 727, "sessions": 359}
    kept, excluded = ITF.filter_pages(_sample_pages())
    share = ITF.public_share_estimate(metrics, excluded)
    assert share["public_pageviews_lower_bound"] == 727 - 218
    assert share["public_share_lower_bound"] == round((727 - 218) / 727, 4)
    # 口径必须写清楚，否则消费方会当精确值用
    assert "下限" in share["basis"]


def test_share_degrades_safely_on_empty_metrics():
    share = ITF.public_share_estimate({}, [])
    assert share["public_share_lower_bound"] is None
    assert share["total_pageviews"] == 0


def test_share_never_exceeds_one():
    metrics = {"screenPageViews": 100, "sessions": 50}
    kept, excluded = ITF.filter_pages(_sample_pages())
    share = ITF.public_share_estimate(metrics, excluded)
    assert share["public_share_lower_bound"] == 0.0
    assert share["public_pageviews_lower_bound"] == 0


# ── 与桥接层的接线 ──────────────────────────────────────────

def test_bridge_excludes_internal_pages_from_records():
    """real_data_bridge 是喂给各 learning loop 的入口，必须已接上过滤。"""
    import real_data_bridge as BR
    src = (REPO_ROOT / "scripts" / "real_data_bridge.py").read_text(encoding="utf-8")
    assert "ITF.filter_pages" in src, "桥接层未接入内部流量过滤"
    # get_user_records 的 top_pages 循环必须走过滤后的 public_pages，
    # 不能直接遍历 data.get("top_pages")——否则过滤等于没做。
    body = src[src.find("def get_user_records("):]
    assert "for page in public_pages:" in body
    assert "for page in data.get(\"top_pages\"" not in body


def test_prefix_list_is_defined_in_exactly_one_place():
    """首段名单只能有一处事实来源，否则各消费者会漂移出不同名单。"""
    src = (REPO_ROOT / "scripts" / "internal_traffic_filter.py").read_text(encoding="utf-8")
    assert src.count("INTERNAL_PATH_PREFIXES: Tuple") == 1
    daily = (REPO_ROOT / "scripts" / "feishu_daily_report.py").read_text(encoding="utf-8")
    assert "ITF.filter_pages" in daily
    # 飞书日报的兜底分支里有一份 _segments，它必须与共用模块一致——
    # 这是唯一允许存在的第二份，因为它在模块缺失时是灾备，漂移会导致
    # 两个分支给出不同的名单。
    assert '_segments = frozenset({"ops", "ops-dashboard"})' in daily
