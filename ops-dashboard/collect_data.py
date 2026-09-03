#!/usr/bin/env python3
"""收集运营看板所需的全部真实数据，输出 dashboard_data.json"""
import json, sys, os, time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

# 加载 .env 环境变量
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass


def parse_cron_freq(cron_expr):
    """解析 cron 表达式，返回中文频率描述"""
    if not cron_expr:
        return "手动"
    parts = cron_expr.strip().split()
    if len(parts) != 5:
        return "手动"
    minute, hour, day, month, weekday = parts
    if month != '*' and day != '*' and hour != '*' and minute != '*':
        if ',' in month:
            return "每季"
        return "每年"
    if day != '*' and hour != '*' and minute != '*' and month == '*':
        return "每月"
    if weekday != '*' and hour != '*' and minute != '*' and day == '*' and month == '*':
        return "每周"
    if hour != '*' and minute != '*' and day == '*' and month == '*' and weekday == '*':
        return "每日"
    if hour == '*' and minute != '*' and day == '*':
        if minute.startswith('*/'):
            return "每" + minute[2:] + "分钟"
        return "每时"
    if minute.startswith('*/') and hour == '*':
        return "每" + minute[2:] + "分钟"
    return "定时"


data = {"generated_at": (datetime.now(timezone.utc) + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S"), "site": {}, "workflows": [], "agents": {}, "experiments": [], "metrics": {}, "data_sources": []}

# 1. 网站状态
try:
    import requests
    r = requests.get("https://chinaboundtravel.com", timeout=10)
    data["site"] = {"url": "chinaboundtravel.com", "status": r.status_code, "up": r.status_code == 200, "response_ms": round(r.elapsed.total_seconds() * 1000), "server": r.headers.get("Server", "unknown")}
except Exception as e:
    data["site"] = {"url": "chinaboundtravel.com", "status": 0, "up": False, "response_ms": 0, "server": "unreachable", "error": str(e)}

# 2. Workflow 列表 + 最近运行状态
wf_dir = ROOT / ".github" / "workflows"
workflows = []
for f in sorted(wf_dir.glob("*.yml")) + sorted(wf_dir.glob("*.yaml")):
    name = f.stem
    try:
        content = f.read_text(encoding="utf-8")
        for line in content.splitlines():
            if line.startswith("name:"):
                display = line.split("name:", 1)[1].strip().strip("'\"")
                break
        else:
            display = name
    except:
        display = name
    # 提取 cron 频率
    freq = "手动"
    try:
        for line in content.splitlines():
            if "cron:" in line:
                cron_expr = line.split("cron:")[1].strip()
                # 去掉引号和注释
                cron_expr = cron_expr.strip("'\"").split("#")[0].strip()
                freq = parse_cron_freq(cron_expr)
                break
    except:
        pass
    workflows.append({"file": f.name, "name": display, "id": name, "frequency": freq})

# 用 gh CLI 查每个 workflow 最近运行
try:
    import subprocess
    result = subprocess.run(["gh", "run", "list", "--limit", "50", "--json", "name,status,conclusion,createdAt,event,databaseId"], capture_output=True, text=True, cwd=str(ROOT), timeout=30)
    if result.returncode == 0:
        runs = json.loads(result.stdout)
        latest = {}
        for run in runs:
            wf_name = run.get("name", "")
            if wf_name not in latest:
                latest[wf_name] = run
        for wf in workflows:
            run = latest.get(wf["name"])
            if run:
                wf["last_status"] = run.get("conclusion", run.get("status", "unknown"))
                wf["last_run"] = run.get("createdAt", "")
                wf["last_event"] = run.get("event", "")
            else:
                wf["last_status"] = "no_runs"
                wf["last_run"] = ""
                wf["last_event"] = ""
except Exception as e:
    for wf in workflows:
        wf["last_status"] = "unknown"
        wf["last_run"] = ""
        wf["last_event"] = ""

data["workflows"] = workflows

# 3. Agent 健康
try:
    from agent_health_monitor import check_health
    data["agents"] = check_health()
except Exception as e:
    data["agents"] = {"error": str(e), "overall": "unknown", "agents": []}

# 4. 实验状态
try:
    snap = json.loads((ROOT / "reports/management/REPORTING_SNAPSHOT.json").read_text(encoding="utf-8"))
    exps = snap.get("domains", {}).get("experiments", {}).get("experiments", [])
    data["experiments"] = [{"id": e.get("experiment_id"), "name": e.get("display_name"), "status": e.get("status"), "days": e.get("observation_days"), "sample": e.get("sample_status"), "page": e.get("page", "")[:40], "start": e.get("start_date")} for e in exps]
except Exception as e:
    data["experiments"] = []

# 5. 关键指标 — 28天累计（用于数据源状态参考）
try:
    ga4 = json.loads((ROOT / "reports/real_data/ga4_real_data.json").read_text(encoding="utf-8"))
    m = ga4.get("metrics", {})
    data["metrics"]["ga4_28d"] = {"visitors": m.get("activeUsers", 0), "sessions": m.get("sessions", 0), "pageviews": m.get("screenPageViews", 0), "date": ga4.get("data_date", "")}
except:
    data["metrics"]["ga4_28d"] = {"visitors": 0, "sessions": 0, "pageviews": 0}

try:
    gsc = json.loads((ROOT / "reports/real_data/gsc_real_data.json").read_text(encoding="utf-8"))
    m = gsc.get("metrics", {})
    data["metrics"]["gsc_28d"] = {"impressions": m.get("impressions", 0), "clicks": m.get("clicks", 0), "date": gsc.get("data_date", "")}
except:
    data["metrics"]["gsc_28d"] = {"impressions": 0, "clicks": 0}

# 内容资产
try:
    content = json.loads((ROOT / "reports/real_data/content_real_data.json").read_text(encoding="utf-8"))
    m = content.get("metrics", {})
    data["metrics"]["content"] = {"total_articles": m.get("total_articles", 0), "with_affiliate": m.get("articles_with_affiliate_links", 0), "avg_word_count": m.get("avg_word_count", 0), "date": content.get("data_date", "")}
except:
    data["metrics"]["content"] = {"total_articles": 0, "with_affiliate": 0}

# 5b. GA4/GSC 单日数据（日报口径，save=False 不覆盖28天文件）
try:
    from real_data_pull_engine import pull_ga4_data, pull_gsc_data
    ga4_daily = pull_ga4_data(days=7, save=False)
    if ga4_daily.get("is_real_data") and ga4_daily.get("metrics"):
        m = ga4_daily["metrics"]
        # 最近一天数据（用于KPI显示）
        latest = ga4_daily.get("daily", [])[-1] if ga4_daily.get("daily") else {}
        data["metrics"]["ga4_daily"] = {
            "visitors": latest.get("activeUsers", m.get("activeUsers", 0)),
            "sessions": latest.get("sessions", m.get("sessions", 0)),
            "pageviews": latest.get("pageviews", m.get("screenPageViews", 0)),
            "new_users": m.get("newUsers", 0),
            "bounce_rate": round(m.get("bounceRate", 0) * 100, 1),
            "date": latest.get("date", ga4_daily.get("data_date", "")),
            "status": "OK",
            "daily": ga4_daily.get("daily", []),
        }
    else:
        data["metrics"]["ga4_daily"] = {"visitors": 0, "sessions": 0, "pageviews": 0, "status": ga4_daily.get("status", "failed"), "date": "", "daily": []}
except Exception as e:
    data["metrics"]["ga4_daily"] = {"visitors": 0, "sessions": 0, "pageviews": 0, "status": "error:" + str(e)[:50], "date": "", "daily": []}

try:
    gsc_daily = pull_gsc_data(days=7, save=False)
    if gsc_daily.get("is_real_data") and gsc_daily.get("metrics"):
        m = gsc_daily["metrics"]
        latest = gsc_daily.get("daily", [])[-1] if gsc_daily.get("daily") else {}
        data["metrics"]["gsc_daily"] = {
            "impressions": latest.get("impressions", m.get("impressions", 0)),
            "clicks": latest.get("clicks", m.get("clicks", 0)),
            "ctr": latest.get("ctr", round(m.get("ctr", 0), 2)),
            "avg_position": latest.get("position", m.get("average_position", 0)),
            "date": latest.get("date", gsc_daily.get("data_date", "")),
            "status": "OK",
            "daily": gsc_daily.get("daily", []),
        }
    else:
        data["metrics"]["gsc_daily"] = {"impressions": 0, "clicks": 0, "ctr": 0, "status": gsc_daily.get("status", "failed"), "date": "", "daily": []}
except Exception as e:
    data["metrics"]["gsc_daily"] = {"impressions": 0, "clicks": 0, "ctr": 0, "status": "error:" + str(e)[:50], "date": "", "daily": []}

# 6. 数据源状态
def _has(*keys):
    return any(os.environ.get(k) for k in keys)

data["data_sources"] = [
    {"name": "GA4", "configured": _has("GA4_API_KEY", "GA4_SERVICE_ACCOUNT_JSON", "GA4_PROPERTY_ID"), "status": data["metrics"]["ga4_daily"].get("status", "unknown")},
    {"name": "GSC", "configured": _has("GSC_SERVICE_ACCOUNT_JSON"), "status": data["metrics"]["gsc_daily"].get("status", "unknown")},
    {"name": "Travelpayouts", "configured": _has("TRAVELPAYOUTS_API_TOKEN"), "status": "ok"},
    {"name": "NordVPN", "configured": _has("NORDVPN_API_KEY", "NORDVPN_AFFILIATE_ID"), "status": "ok"},
    {"name": "MailerLite", "configured": _has("MAILERLITE_API_TOKEN"), "status": "configured"},
    {"name": "Buffer", "configured": _has("BUFFER_API_TOKEN_A", "BUFFER_API_TOKEN_B"), "status": "ok"},
    {"name": "Cloudflare", "configured": _has("CLOUDFLARE_API_TOKEN"), "status": "ok"},
]

# 7. Kill switch
try:
    from ai_governance import check_kill_switch
    safe, reason = check_kill_switch()
    data["kill_switch"] = {"active": not safe, "reason": reason}
except:
    data["kill_switch"] = {"active": False, "reason": "unknown"}

# 输出
out = ROOT / "ops-dashboard" / "dashboard_data.json"
out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print("✅ Data collected:", len(workflows), "workflows,", len(data["experiments"]), "experiments, agents=", data["agents"].get("overall", "?"))
print("   Site:", data["site"].get("status"), str(data["site"].get("response_ms")) + "ms")
print("   GA4 daily:", data["metrics"]["ga4_daily"].get("visitors"), "visitors, status=", data["metrics"]["ga4_daily"].get("status"))
print("   GSC daily:", data["metrics"]["gsc_daily"].get("impressions"), "impressions, status=", data["metrics"]["gsc_daily"].get("status"))
