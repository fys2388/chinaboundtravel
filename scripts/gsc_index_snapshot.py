"""GSC 页面级快照采集器 —— 为 pages_newly_indexed / pages_losing_visibility 提供原始数据。

为什么单独做一个采集器而不是在 reporting_kpi_engine 里拉 API：

reporting_kpi_engine 是**只读汇总器**，它的工作是把 reports/ 下的产物聚合成
REPORTING_SNAPSHOT.json。让它在运行期打外部 API 会引入三类问题：
  1. 失败模式混淆 —— 引擎本来报「数据不存在」，现在可能报「API 超时」，
     两种失败在日报里长一个样，值班的人分不清是数据缺了还是网络抽风
  2. 非幂等 —— 同一天跑两次会得到两个不同的快照，REPORTING_SNAPSHOT.json
     的内容取决于谁先跑、API 当时返回什么
  3. 慢 —— 引擎要读 20+ 个本地文件，不该再加一个 60s 的外部调用

所以采集和汇总分成两个进程，中间用一份不可变文件隔开。

产物布局（每天一份，文件名带日期，永不覆盖）：

    reports/seo/gsc_page_snapshots/INDEX_PAGE_SNAPSHOT_2026-09-17.json

engine 侧 glob 这个目录、按日期排序、取最近两份做差。第一天只有 1 份时
两个 KPI 保持 NOT_AVAILABLE（没有对照基线，报 0 是假的），第二天起自动
转正 —— 这就是「自举」：不需要人工干预，机制自己长出来。

指标定义（写死在这里，不要改，否则历史快照失去可比性）：

  pages_newly_indexed
    本次快照里 impressions > 0、且上次快照里没有（或 impressions == 0）的页面数。
    「新进入 GSC 可见集合」是索引状态的代理指标 —— GSC 的 searchAnalytics
    不会告诉你 Google 索引了没有，只告诉你这个页面在自然结果里被看到了没有。
    这是能拿到的最接近「新索引」的信号。

  pages_losing_visibility
    上次快照里 impressions > 0、本次快照里消失或 impressions 归零的页面数。

为什么不用 GSC Index Coverage API：webmasters.readonly 作用域下
Index Coverage 的分面统计不可用，URL Inspection 又是单 URL 一次，
一个站点几百个页面跑一遍会打爆配额且要 3 天以上。页面级 searchAnalytics
一次调用覆盖全部，且已经有服务账号权限（verify_gsc_access.py 通过）。

用法：
    python scripts/gsc_index_snapshot.py            # 拉 28 天窗口
    python scripts/gsc_index_snapshot.py --days 28  # 显式窗口
    python scripts/gsc_index_snapshot.py --stdout    # 打印而不落盘（调试）
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
BASE = SCRIPTS.parent
SNAPSHOT_DIR = BASE / "reports" / "seo" / "gsc_page_snapshots"

DEFAULT_DAYS = 28
# GSC searchAnalytics 有约 3 天延迟，最后一天拿不到数。窗口右端要往前退 3 天。
DATA_LAG_DAYS = 3
ROW_LIMIT = 25000


def _import_gsc_utils():
    sys.path.insert(0, str(SCRIPTS))
    import gsc_utils  # noqa: E402
    return gsc_utils


def _load_env() -> None:
    """加载 .env（若存在）。gsc_utils 从环境变量读服务账号。"""
    env_file = BASE / ".env"
    if not env_file.is_file():
        return
    for line in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def collect(days: int = DEFAULT_DAYS, dry_run: bool = False) -> dict:
    """拉 page 维度 searchAnalytics，返回快照 dict。不落盘。"""
    _load_env()
    gsc = _import_gsc_utils()

    info = gsc.load_service_account_info()
    if not info:
        return {"status": "NO_CREDENTIALS",
                "error": "GSC_SERVICE_ACCOUNT_JSON 未配置（环境变量或 key 文件）"}

    creds = gsc.build_credentials(info, scopes=[
        "https://www.googleapis.com/auth/webmasters.readonly"])
    if creds is None:
        return {"status": "NO_CREDENTIALS",
                "error": "build_credentials 返回 None（缺少 google-auth 库或密钥无效）"}

    site = gsc.get_site_url()
    site_enc = urllib.parse.quote(site, safe="")

    end = date.today() - timedelta(days=DATA_LAG_DAYS)
    start = end - timedelta(days=days - 1)

    api_url = ("https://searchconsole.googleapis.com/webmasters/v3/sites/"
               f"{site_enc}/searchAnalytics/query")
    body = {
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "searchType": "web",
        "dimensions": ["page"],
        "rowLimit": ROW_LIMIT,
        "orderBy": [{"field": "impressions", "desc": True}],
    }

    import requests
    resp = requests.post(api_url, headers={
        "Authorization": f"Bearer {creds.token}",
        "Content-Type": "application/json",
    }, json=body, timeout=90)

    if resp.status_code != 200:
        return {"status": "API_ERROR", "http_status": resp.status_code,
                "error": resp.text[:500]}

    pages = {}
    for row in resp.json().get("rows", []):
        try:
            url = row["keys"][0]
        except (KeyError, IndexError):
            continue
        pages[url] = {
            "impressions": int(row.get("impressions") or 0),
            "clicks": int(row.get("clicks") or 0),
            "position": round(float(row.get("position") or 0), 2),
        }

    total_imp = sum(p["impressions"] for p in pages.values())
    total_clk = sum(p["clicks"] for p in pages.values())

    return {
        "status": "OK",
        "site": site,
        "window": {"start": start.isoformat(), "end": end.isoformat(),
                   "days": days},
        "generated_at": datetime_now(),
        "totals": {"impressions": total_imp, "clicks": total_clk,
                   "pages_with_data": len(pages)},
        "pages": pages,
    }


def datetime_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_snapshot(snapshot: dict) -> Path | None:
    """把快照落盘成不可变的日期文件。同一天重跑会覆盖同一天的文件。"""
    if snapshot.get("status") != "OK":
        return None
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    day = snapshot["window"]["end"]  # 用数据窗口右端命名，不用拉取时间
    out = SNAPSHOT_DIR / f"INDEX_PAGE_SNAPSHOT_{day}.json"
    out.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False,
                              sort_keys=True), encoding="utf-8")
    return out


def list_snapshots() -> list[Path]:
    """按日期升序列出所有快照文件。"""
    if not SNAPSHOT_DIR.is_dir():
        return []
    return sorted(SNAPSHOT_DIR.glob("INDEX_PAGE_SNAPSHOT_*.json"))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="GSC 页面级快照采集")
    ap.add_argument("--days", type=int, default=DEFAULT_DAYS,
                    help=f"窗口天数（默认 {DEFAULT_DAYS}）")
    ap.add_argument("--stdout", action="store_true",
                    help="只打印 JSON 不落盘（调试用）")
    ap.add_argument("--list", action="store_true",
                    help="列出现有快照文件")
    args = ap.parse_args(argv)

    if args.list:
        for p in list_snapshots():
            print(p.name)
        return 0

    snap = collect(days=args.days)
    if snap.get("status") != "OK":
        print(json.dumps(snap, indent=2, ensure_ascii=False))
        return 1

    if args.stdout:
        print(json.dumps(snap, indent=2, ensure_ascii=False))
        return 0

    out = write_snapshot(snap)
    t = snap["totals"]
    print(f"window:      {snap['window']['start']} .. {snap['window']['end']}")
    print(f"pages:       {t['pages_with_data']}")
    print(f"impressions: {t['impressions']}")
    print(f"clicks:      {t['clicks']}")
    print(f"WROTE {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
