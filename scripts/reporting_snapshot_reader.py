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
            "gsc_impressions_28d": _find("seo_gsc", "gsc_impressions_28d").get("value"),
            "gsc_clicks_28d": _find("seo_gsc", "gsc_clicks_28d").get("value"),
            "gsc_indexed_pages": _find("seo_gsc", "indexed_pages").get("value"),
        }
    except Exception as e:
        print(f"   \u26a0\ufe0f REPORTING_SNAPSHOT.json 读取失败: {e}")
        return None


def snapshot_traffic(prefix):
    """SNAPSHOT 流量 KPI → 报告 GA4 数据契约（period 键名按 prefix 拼装）。

    prefix: week / month / quarter / year。SNAPSHOT 无流量 KPI 返回 None。
    """
    snap = _load()
    if not snap or snap.get("sessions_28d") is None:
        return None
    d = {
        f"{prefix}_users": snap.get("users_28d") or 0,
        f"{prefix}_sessions": snap.get("sessions_28d") or 0,
        f"{prefix}_pageviews": snap.get("pageviews_28d") or 0,
        f"{prefix}_bounce": 0,
        f"{prefix}_engagement": 0,
        f"{prefix}_avg_duration": 0,
        "channels": [],
        "top_pages": [],
        "data_source": "SNAPSHOT",
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
        "data_source": "SNAPSHOT",
        "snapshot_as_of": snap.get("as_of"),
    }


def caliber_label(data) -> str:
    """报告卡片页脚的数据口径说明。"""
    if data and data.get("data_source") == "SNAPSHOT":
        return f"2.0 统一快照 SNAPSHOT (as_of {data.get('snapshot_as_of')})"
    return "直连 GA4/GSC"
