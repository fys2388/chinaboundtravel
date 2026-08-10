# -*- coding: utf-8 -*-
"""
audit_okr_achievement.py - 建站以来 OKR 达成审计（实事求是）
数据源：GA4 / GSC / Travelpayouts / MailerLite 真实 API + 本地内容扫描
口径：站点 2026-05-12 上线，OKR 自该日起算
用法：python scripts/audit_okr_achievement.py
"""
import os, sys, re, json
sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path
from datetime import datetime, timedelta

SCRIPT_DIR = Path(__file__).parent.resolve()
BLOG_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

import feishu_quarterly_report as qm
import okr_utils

LAUNCH = "2026-05-12"
TODAY = datetime.now().strftime("%Y-%m-%d")

rep = qm.FeishuQuarterlyReporter()

def ga4_sum(start, end):
    headers = rep._get_ga4_headers()
    if not headers:
        return None
    payload = {"dateRanges": [{"startDate": start, "endDate": end}],
               "metrics": [{"name": "activeUsers"}, {"name": "sessions"}, {"name": "screenPageViews"},
                           {"name": "bounceRate"}, {"name": "averageSessionDuration"}]}
    res = rep._ga4_run_report(headers, payload)
    if res and "rows" in res:
        r = res["rows"][0]
        return {"users": int(r["metricValues"][0].get("value", "0")),
                "sessions": int(r["metricValues"][1].get("value", "0")),
                "pageviews": int(r["metricValues"][2].get("value", "0")),
                "bounce": round(float(r["metricValues"][3].get("value", "0")) * 100, 1),
                "avg_duration": int(float(r["metricValues"][4].get("value", "0")))}
    return {"users": 0, "sessions": 0, "pageviews": 0, "bounce": 0.0, "avg_duration": 0}

def gsc_sum(start, end):
    info = rep._load_service_account(qm.GSC_SERVICE_ACCOUNT_JSON)
    if not info:
        return {"status": "unauthorized", "impressions": 0, "clicks": 0, "days": 0}
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/webmasters.readonly"])
    creds.refresh(Request())
    svc = build("searchconsole", "v1", credentials=creds)
    resp = svc.searchanalytics().query(siteUrl="sc-domain:chinaboundtravel.com",
        body={"startDate": start, "endDate": end, "dimensions": ["date"], "rowLimit": 10000}).execute()
    rows = resp.get("rows", [])
    return {"status": "authorized",
            "impressions": sum(int(r.get("impressions", 0)) for r in rows),
            "clicks": sum(int(r.get("clicks", 0)) for r in rows),
            "days": len(rows)}

def tp_sum(start, end):
    if not qm.TRAVELPAYOUTS_API_TOKEN:
        return {"tp_available": False, "profit": 0}
    try:
        headers = {"X-Access-Token": qm.TRAVELPAYOUTS_API_TOKEN, "Content-Type": "application/json"}
        payload = {"query_id": "commission_report",
                   "fields": ["redirects_count", "paid_actions_count", "paid_profit_usd_sum"],
                   "filters": {"date": {"from": start, "to": end}, "marker": [qm.TRAVELPAYOUTS_MARKER]},
                   "limit": 1}
        import requests
        resp = requests.post("https://api.tp.st/statistics/v1/execute_query", headers=headers, json=payload, timeout=30)
        if resp.status_code != 200:
            return {"tp_available": False, "profit": 0}
        rows = resp.json().get("results", []) or resp.json().get("data", [])
        row = rows[0] if rows else {}
        return {"tp_available": True,
                "redirects": int(row.get("redirects_count", 0) or 0),
                "actions": int(row.get("paid_actions_count", 0) or 0),
                "profit": float(row.get("paid_profit_usd_sum", 0) or 0)}
    except Exception as e:
        return {"tp_available": False, "profit": 0, "err": str(e)}

def ml_total():
    if not qm.MAILERLITE_API_TOKEN:
        return {"ml_available": False, "total": 0}
    try:
        import requests
        headers = {"Authorization": f"Bearer {qm.MAILERLITE_API_TOKEN}", "Content-Type": "application/json"}
        resp = requests.get("https://connect.mailerlite.com/api/subscribers", headers=headers, params={"limit": 1}, timeout=15)
        if resp.status_code != 200:
            return {"ml_available": False, "total": 0}
        return {"ml_available": True, "total": int(resp.headers.get("x-total-count", "0"))}
    except Exception:
        return {"ml_available": False, "total": 0}

def scan_content():
    posts_dir = BLOG_ROOT / "content" / "posts"
    total = 0
    by_date = []
    for post in posts_dir.glob("*.md"):
        total += 1
        try:
            c = post.read_text(encoding="utf-8")
            fm = re.match(r"^---\s*\n(.*?)\n---", c, re.DOTALL)
            dm = re.search(r"^date:\s*[\"']?([\d-]+)", fm.group(1), re.MULTILINE) if fm else None
            if dm:
                by_date.append(dm.group(1)[:10])
            else:
                # 文件名含日期兜底
                fm2 = re.search(r"(\d{4}-\d{2}-\d{2})", post.name)
                if fm2:
                    by_date.append(fm2.group(1))
                else:
                    by_date.append("9999-99-99")  # 日期不明
        except Exception:
            by_date.append("9999-99-99")
    q2 = len([d for d in by_date if LAUNCH <= d <= "2026-06-30"])
    q3 = len([d for d in by_date if "2026-07-01" <= d <= "2026-09-30"])
    unknown = len([d for d in by_date if d == "9999-99-99"])
    return {"total": total, "q2": q2, "q3": q3, "since_launch": total - 0, "unknown": unknown}

def fmt_progress(cur, target):
    if not target:
        return "-"
    return f"{min(round(cur/target*100), 999)}%"

def main():
    print("=" * 66)
    print(f"ChinaBound Travel OKR 达成审计 | 建站 {LAUNCH} | 截止 {TODAY}")
    print("=" * 66)

    content = scan_content()
    print(f"① 内容: 总 {content['total']} 篇 | Q2 新增 {content['q2']} | Q3 新增 {content['q3']} | 日期不明 {content['unknown']} 篇")

    print("\n② GA4 / GSC / 变现 / 订阅（5/12 边界）...")
    g_q2 = ga4_sum(LAUNCH, "2026-06-30")
    g_q3 = ga4_sum("2026-07-01", TODAY)
    g_all = ga4_sum(LAUNCH, TODAY)
    s_q2 = gsc_sum(LAUNCH, "2026-06-30")
    s_q3 = gsc_sum("2026-07-01", TODAY)
    s_all = gsc_sum(LAUNCH, TODAY)
    tp = tp_sum(LAUNCH, TODAY)
    ml = ml_total()

    okr = okr_utils.load_okr()
    if not okr:
        print("okr.json 缺失")
        return

    # 真实数据 → 各周期实际值
    real = {
        "q2":  {"traffic": g_q2["users"], "content": content["q2"], "gsc": s_q2["impressions"],
                "revenue": tp["profit"], "email": ml["total"]},
        "q3":  {"traffic": g_q3["users"], "content": content["q3"], "gsc": s_q3["impressions"],
                "revenue": 0.0, "email": ml["total"]},
        "year": {"traffic": g_all["users"], "content": content["total"], "gsc": s_all["impressions"],
                 "revenue": tp["profit"], "email": ml["total"]},
    }
    real["q3"]["revenue"] = 0.0  # TP 无分季数据，统一按累计口径（Q3 至今 0）

    def row(name, cur, target, unit=""):
        pct = fmt_progress(cur, target)
        icon = "✅" if target and cur >= target else ("🟡" if target and cur >= target*0.5 else "🔴")
        return f"| {name} | {cur:g}{unit} | {target:g}{unit} | {pct} | {icon} |"

    periods = [
        ("Q2 启动期（5/12-6/30）", "q2", "quarterly"),
        ("Q3 进行中（7/1-今）", "q3", "quarterly"),
        ("年度（5/12 至今 vs 全年目标）", "year", "yearly"),
    ]
    for label, key, scope in periods:
        print()
        print(f"--- {label} ---")
        print("| KR | 实际 | 目标 | 达成率 | 状态 |")
        print("| :--- | :--- | :--- | :--- | :--- |")
        krs = okr_utils.pick_quarter_krs(okr, 3) if key in ("q2", "q3") else okr["annual"]["krs"]
        # q2 用 q2 的 KR（quarters 里第一个是 q2）
        if key == "q2":
            for item in okr["quarters"]:
                if item.get("q") == 2:
                    krs = item["krs"]
                    break
        for kr in krs:
            cur = real[key][kr["id"]]
            target = okr_utils._target_for(kr, scope)
            name = kr.get("name", kr["id"])
            if scope == "quarterly" and key == "q3":
                name = {"月访问用户": "季度访问用户(累计)", "月搜索曝光": "季度曝光", "月联盟佣金": "季度佣金"}.get(name, name)
            print(row(name, cur, target, kr.get("unit", "")))

    print()
    print(f"③ 其它关键事实：TP 佣金累计 ${tp.get('profit', 0):.2f}（本地token{'有效' if tp.get('tp_available') else '过期，以线上日报口径 $0 为准'}）| 订阅 {ml.get('total', 0)} 人（{'已连接' if ml.get('ml_available') else '本地未连接，线上口径 0'}）")
    print(f"   建站以来：访客 {g_all['users']} | 曝光 {s_all['impressions']} | 点击 {s_all['clicks']} | 有数据天数 {s_all['days']}")

if __name__ == "__main__":
    main()