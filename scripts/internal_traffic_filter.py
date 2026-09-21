"""内部流量路径黑名单 —— 单一事实来源。

为什么需要它
------------
GA4 流量榜前 3 名里有两个是内部运营页：
  /ops-dashboard/ 173 pv、/ops/ops-center 70 pv，而首页只有 98 pv。
  内部运营页合计 243 / 727 = 33.4% 的 pageview。

这些访问来自 bot 与 agent 会话（ops-dashboard-hourly.yml 每 ~30 分钟轮询一次
运营看板），不是真实访客。它们混进 top_pages 后会污染所有派生指标：
  - 转化率漏斗：内部页的跳出率与参与度远低于真实用户
  - 页面优先级：agent 会把 /ops-dashboard/ 读成「表现最好的内容」
  - SEO 机会判断：拿内部页的高参与度去论证「应该多做内部工具」

为什么在报表层做，而不是 GA4 IP 排除
--------------------------------------
IP 排除是正解，但需要精确的 IP 段；配错范围会把真实访客一起排除，那是破坏性
分析操作，不会在没有确切 IP 的情况下盲配。报表层黑名单立即生效、可回滚、
不影响 GA4 后台原始数据（后台原始数字保持不动，只改派生指标）。

现状
----
feishu_daily_report.py 早就检测得出这个问题（打 ⚠️ 警告），但只报不滤——
典型的「产出 artifact 不闭环」。本模块把检测与过滤合一，供所有消费方共用，
避免每个消费者各自维护一份前缀列表。

用法::

    from internal_traffic_filter import filter_pages, public_share_estimate

    pages, excluded = filter_pages(ga4_data.get("top_pages", []))
    share = public_share_estimate(ga4_data.get("metrics", {}), excluded)

约束
----
本模块只读不改：不修改 ga4_real_data.json，也不触碰任何 _redirects / ops 页面。
"""
from __future__ import annotations

import copy
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

#: 内部运营路径的**首段**名单。
#: 必须按首段（path segment）匹配，不能用字符串前缀——`/ops` 用裸 startswith
#: 会误杀 `/ops-guide-for-travelers`（真实公共内容页），等于把公共内容从指标里
#: 偷偷删掉；而单靠 `/ops` 又漏掉 `/ops-dashboard/`，因为那是它的**兄弟路径**
#: 不是子路径（/ops-dashboard 不以 /ops/ 开头）。
#: 已核实仓库内没有以这两段开头的公共页面。
INTERNAL_PATH_PREFIXES: Tuple[str, ...] = ("ops", "ops-dashboard")

#: 完整路径形式，供报告/日志引用，避免各消费者措辞不一致。
INTERNAL_PATHS_DOCUMENTED: Tuple[str, ...] = (
    "/ops/", "/ops-dashboard/", "/ops/ops-center"
)

#: 供报告/日志引用的固定说明，避免各消费者措辞不一致。
EXCLUSION_NOTE = (
    "内部运营页（/ops*）已从指标中剔除：这些访问来自 bot 与 agent 会话轮询，"
    "不是真实访客。GA4 后台原始数据未改动。"
)


def is_internal_path(path: Optional[str]) -> bool:
    """判断路径是否属于内部运营流量。

    按**路径首段**匹配：`/ops/ops-center` 首段是 `ops`，`/ops-dashboard/`
    首段是 `ops-dashboard`，都命中；`/ops-guide-for-travelers/` 首段是
    `ops-guide-for-travelers`，不命中。
    """
    if not path:
        return False
    p = str(path).strip()
    # 归一化：去掉 query / hash / 尾部斜杠，避免 /ops-dashboard/?x=1 漏网
    p = p.split("?", 1)[0].split("#", 1)[0]
    if len(p) > 1:
        p = p.rstrip("/")
    first = p.lstrip("/").split("/", 1)[0]
    return first in INTERNAL_PATH_PREFIXES


def filter_pages(
    pages: Iterable[Dict],
) -> Tuple[List[Dict], List[Dict]]:
    """把 top_pages 拆成 (公共页, 内部页)。

    返回**深拷贝**的新列表与新字典，不改入参。这样下游把条目塞进 record
    后再怎么改，都不会反向污染调用方手里的原始数据（原始数据还来自磁盘上的
    ga4_real_data.json，被内存里的改动悄悄改脏是最难查的那类问题）。
    缺 path 字段的条目视为公共页保留（不做臆断）。
    """
    kept: List[Dict] = []
    excluded: List[Dict] = []
    for page in pages:
        target = excluded if is_internal_path(page.get("path")) else kept
        target.append(copy.deepcopy(page))
    return kept, excluded


def _num(value, default: int = 0) -> int:
    """GA4 数字偶尔是字符串或缺失，统一成 int。"""
    try:
        if value is None:
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def excluded_volume(excluded: Sequence[Dict]) -> Dict[str, int]:
    """被剔除的流量体量（仅覆盖传入的 top_pages 范围内）。"""
    return {
        "pages": len(excluded),
        "pageviews": sum(_num(p.get("pageviews", p.get("views"))) for p in excluded),
        "sessions": sum(_num(p.get("sessions")) for p in excluded),
        "users": sum(_num(p.get("activeUsers", p.get("users"))) for p in excluded),
    }


def public_share_estimate(
    metrics: Optional[Dict],
    excluded: Sequence[Dict],
) -> Dict[str, object]:
    """估算剔除内部流量后的公开流量占比。

    明确标注这是估算：分子只能从 top_pages 覆盖范围内精确计算，
    分母是全站汇总。内部页若不在 top 榜里就不会被计入分子，
    所以这个比例是**下限**，不是精确值。
    """
    total_pv = _num((metrics or {}).get("screenPageViews", (metrics or {}).get("pageviews")))
    total_sessions = _num((metrics or {}).get("sessions"))
    vol = excluded_volume(excluded)

    def _share(removed: int, total: int) -> Optional[float]:
        if total <= 0:
            return None
        return round(max(0.0, (total - removed)) / total, 4)

    return {
        "total_pageviews": total_pv,
        "excluded_pageviews": vol["pageviews"],
        "public_pageviews_lower_bound": max(0, total_pv - vol["pageviews"]),
        "public_share_lower_bound": _share(vol["pageviews"], total_pv),
        "total_sessions": total_sessions,
        "excluded_sessions": vol["sessions"],
        "public_sessions_lower_bound": max(0, total_sessions - vol["sessions"]),
        "public_session_share_lower_bound": _share(vol["sessions"], total_sessions),
        "basis": "仅覆盖 top_pages 范围内；未上榜的内部访问未被计入，故为下限",
        "note": EXCLUSION_NOTE,
    }


def apply_to_metrics(metrics: Optional[Dict], excluded: Sequence[Dict]) -> Dict[str, object]:
    """把剔除结果挂到 metrics 旁，供报表消费。"""
    return {
        "excluded_internal": excluded_volume(excluded),
        "public_share": public_share_estimate(metrics, excluded),
    }
