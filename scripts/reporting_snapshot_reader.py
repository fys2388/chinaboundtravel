"""2.0 统一 KPI 快照读取器（P1-REPORT-03R）。

供日/周/月/季/年 Feishu 报告共用：REPORTING_SNAPSHOT.json 为单一 KPI 源，
报告不再各自直连 GA4/GSC 重算。SNAPSHOT 命中则采用其口径，未命中返回 None 由
调用方回退直连（保持原行为）。
"""
import json
from pathlib import Path

BLOG_ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_FILE = BLOG_ROOT / "reports" / "management" / "REPORTING_SNAPSHOT.json"


def _load() -> dict:
    try:
        if not SNAPSHOT_FILE.exists():
            print("   \u26a0\ufe0f REPORTING_SNAPSHOT.json 不存在，回退直连")
            return None
        snap = json.loads(SNAPSHOT_FILE.read_text(encoding="utf-8"))

        def _find(domain, name):
            for k in snap.get("domains", {}).get(domain, {}).get("kpis", []):
                if k.get("name") == name:
                    return k
            return {}

        return {
            "as_of": snap.get("as_of"),
            "generated_at": snap.get("generated_at"),
            "low_data_warning": snap.get("low_data_warning"),
            "sessions_28d": _find("traffic", "sessions_28d").get("value"),
            "pageviews_28d": _find("traffic", "pageviews_28d").get("value"),
            "users_28d": _find("traffic", "users_28d").get("value"),
            "engagement_rate_28d": _find("traffic", "engagement_rate_28d").get("value"),
            "source_channel_mix": _find("traffic", "source_channel_mix").get("value"),
            "gsc_impressions_28d": _find("seo_gsc", "gsc_impressions_28d").get("value"),
            "gsc_clicks_28d": _find("seo_gsc", "gsc_clicks_28d").get("value"),
            "gsc_indexed_pages": _find("seo_gsc", "indexed_pages").get("value"),
            "gsc_ctr_28d": _find("seo_gsc", "gsc_ctr_28d").get("value"),
            "gsc_avg_position_28d": _find("seo_gsc", "gsc_avg_position_28d").get("value"),
        }
    except Exception as e:
        print(f"   \u26a0\ufe0f REPORTING_SNAPSHOT.json 读取失败: {e}")
        return None


def _channel_from_mix(c: dict) -> dict:
    """SNAPSHOT source_channel_mix → 报告渠道行契约（channel/users/bounce/duration）。

    SNAPSHOT 无停留时长维度，duration 置 None 表示"无数据"（调用方据此显示
    "数据不足"而非误判"较差"）；bounce 由 engagementRate 反推（GA4 口径
    bounce ≈ 1 - engagement）。
    """
    er = c.get("engagementRate")
    return {
        "channel": c.get("channel", "Unknown"),
        "users": c.get("activeUsers", 0),
        "bounce": round((1 - er) * 100, 1) if er is not None else 0,
        "duration": None,  # SNAPSHOT 无停留时长维度
    }


def snapshot_traffic(prefix):
    """SNAPSHOT 流量 KPI → 报告 GA4 数据契约（period 键名按 prefix 拼装）。

    prefix: week / month / quarter / year。SNAPSHOT 无流量 KPI 返回 None。
    SNAPSHOT 仅持有 28 天聚合（无月/季/年粒度、无停留时长/设备/页面维度），
    返回值携带 traffic_scope="28d_window" 供调用方明确标注"非月值"，避免
    把 28 天窗口值冒充月值。
    """
    snap = _load()
    if not snap or snap.get("sessions_28d") is None:
        return None
    # Week: snapshot only has 28-day aggregates, not weekly data.
    # Return None so report falls through to direct GA4 API call.
    if prefix == "week":
        return None
    _er = snap.get("engagement_rate_28d")
    _mix = snap.get("source_channel_mix") or []
    d = {
        f"{prefix}_users": snap.get("users_28d") or 0,
        f"{prefix}_sessions": snap.get("sessions_28d") or 0,
        f"{prefix}_pageviews": snap.get("pageviews_28d") or 0,
        f"{prefix}_bounce": round((1 - _er) * 100, 1) if _er is not None else 0,
        f"{prefix}_engagement": round(_er * 100, 1) if _er is not None else 0,
        f"{prefix}_avg_duration": 0,  # SNAPSHOT 无停留时长维度
        "channels": [_channel_from_mix(c) for c in _mix],
        "top_pages": [],  # SNAPSHOT 无页面维度
        "data_source": "SNAPSHOT",
        "traffic_scope": "28d_window",
        "snapshot_as_of": snap.get("as_of"),
        "low_data_warning": snap.get("low_data_warning"),
    }
    if prefix in ("quarter", "year"):
        d[f"{prefix}_start"] = ""
        d[f"{prefix}_end"] = ""
    else:
        d[f"{prefix}_start"] = ""
    return d


def snapshot_gsc():
    """SNAPSHOT GSC KPI → 报告 GSC 数据契约（status/indexed_pages/errors）。

    无收录数据返回 None（由调用方回退直连）。
    """
    snap = _load()
    if not snap or snap.get("gsc_indexed_pages") is None:
        return None
    return {
        "status": "authorized",
        "indexed_pages": snap.get("gsc_indexed_pages"),
        "sitemap_count": 0,
        "errors": 0,
        "impressions_28d": snap.get("gsc_impressions_28d"),
        "clicks_28d": snap.get("gsc_clicks_28d"),
        # 兼容季报/年报的 gsc_impressions / gsc_clicks 键名（快照只提供 28d 后缀）
        "gsc_impressions": snap.get("gsc_impressions_28d"),
        "gsc_clicks": snap.get("gsc_clicks_28d"),
        "gsc_ctr_28d": snap.get("gsc_ctr_28d"),
        "gsc_avg_position_28d": snap.get("gsc_avg_position_28d"),
        "data_source": "SNAPSHOT",
        "snapshot_as_of": snap.get("as_of"),
    }


def caliber_label(data) -> str:
    """报告卡片页脚的数据口径说明。"""
    if data and data.get("data_source") == "SNAPSHOT":
        if data.get("traffic_scope") == "28d_window":
            return (f"2.0 统一快照 SNAPSHOT（28 天窗口口径，非月值）"
                    f"(as_of {data.get('snapshot_as_of')})")
        return f"2.0 统一快照 SNAPSHOT (as_of {data.get('snapshot_as_of')})"
    return "直连 GA4/GSC"
