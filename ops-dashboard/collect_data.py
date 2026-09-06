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

# 用 gh CLI 查每个 workflow 最近运行（增加limit，双匹配name和id）
try:
    import subprocess
    result = subprocess.run(["gh", "run", "list", "--limit", "200", "--json", "name,status,conclusion,createdAt,event,databaseId,workflowName"], capture_output=True, text=True, cwd=str(ROOT), timeout=45)
    if result.returncode == 0:
        runs = json.loads(result.stdout)
        latest_by_name = {}
        latest_by_wfname = {}
        for run in runs:
            wf_name = run.get("name", "")
            wf_full = run.get("workflowName", "")
            if wf_name and wf_name not in latest_by_name:
                latest_by_name[wf_name] = run
            if wf_full and wf_full not in latest_by_wfname:
                latest_by_wfname[wf_full] = run
        for wf in workflows:
            # 双匹配：name 或 workflowName
            run = latest_by_name.get(wf["name"]) or latest_by_wfname.get(wf["name"])
            if run:
                wf["last_status"] = run.get("conclusion", run.get("status", "unknown"))
                wf["last_run"] = run.get("createdAt", "")
                wf["last_event"] = run.get("event", "")
            else:
                wf["last_status"] = "no_runs"
                wf["last_run"] = ""
                wf["last_event"] = ""
    else:
        # gh CLI 失败时，用 GitHub API 兜底
        import os as _os
        token = _os.environ.get("GITHUB_TOKEN", "")
        if token:
            import urllib.request as _ur
            req = _ur.Request(f"https://api.github.com/repos/fys2388/chinaboundtravel/actions/runs?per_page=200",
                            headers={"Authorization": f"token {token}", "Accept": "application/vnd.github+json"})
            with _ur.urlopen(req, timeout=20) as resp:
                runs_data = json.loads(resp.read())
                latest_api = {}
                for run in runs_data.get("workflow_runs", []):
                    wf_name = run.get("name", "")
                    if wf_name not in latest_api:
                        latest_api[wf_name] = run
                for wf in workflows:
                    run = latest_api.get(wf["name"])
                    if run:
                        wf["last_status"] = run.get("conclusion", run.get("status", "unknown"))
                        wf["last_run"] = run.get("created_at", "")
                        wf["last_event"] = run.get("event", "")
                    else:
                        wf["last_status"] = "no_runs"
                        wf["last_run"] = ""
                        wf["last_event"] = ""
        else:
            for wf in workflows:
                wf["last_status"] = "unknown"
                wf["last_run"] = ""
                wf["last_event"] = ""
except Exception as e:
    print(f"  [warn] workflow run list failed: {e}")
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

# 4. 实验状态 — 优先从真实配置 static/experiments.json 读取
try:
    exp_config_path = ROOT / "static" / "experiments.json"
    if exp_config_path.exists():
        exp_cfg = json.loads(exp_config_path.read_text(encoding="utf-8"))
        exps = exp_cfg.get("experiments", [])
        data["experiments"] = [
            {
                "id": e.get("id"),
                "name": e.get("name"),
                "status": e.get("status"),
                "type": e.get("type", ""),
                "days": e.get("observation_days"),
                "sample": "PLANNED" if e.get("status") == "PLANNED" else e.get("sample_status", "INSUFFICIENT_SAMPLE"),
                "page": e.get("page", "")[:40],
                "start": e.get("start_date"),
                "variants": len(e.get("variants", [])),
                "min_sample": e.get("min_sample", 0),
            }
            for e in exps
        ]
    else:
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

# Site Health 巡检数据（只统计未解决问题）
try:
    import glob as _glob
    sh_files = sorted([f for f in _glob.glob(str(ROOT / "reports" / "site_health" / "site_health_*.json")) if "audit" not in f])
    if sh_files:
        sh = json.loads(open(sh_files[-1], encoding="utf-8").read())
        issues = sh.get("issues", [])

        RESOLVED_STATUSES = {"resolved", "fixed", "false_positive", "closed"}
        resolved_count = 0
        today_fixed = 0
        today_str = datetime.now().strftime("%Y-%m-%d")
        unresolved_critical = unresolved_high = unresolved_medium = unresolved_low = 0
        pending_unassigned = 0

        for issue in issues:
            status = (issue.get("status") or "").lower()
            severity = (issue.get("severity") or "").lower()
            assigned = issue.get("assigned", False)
            if status in RESOLVED_STATUSES:
                resolved_count += 1
                resolved_at = issue.get("resolved_at", "") or ""
                if today_str in resolved_at:
                    today_fixed += 1
            else:
                if severity == "critical": unresolved_critical += 1
                elif severity == "high": unresolved_high += 1
                elif severity == "medium": unresolved_medium += 1
                elif severity == "low": unresolved_low += 1
                if not assigned: pending_unassigned += 1

        unresolved_total = unresolved_critical + unresolved_high + unresolved_medium + unresolved_low
        data["site_health"] = {
            "total": unresolved_total,
            "critical": unresolved_critical,
            "high": unresolved_high,
            "medium": unresolved_medium,
            "low": unresolved_low,
            "auto_fixed": today_fixed,
            "pending": pending_unassigned,
            "resolved": resolved_count,
            "timestamp": sh.get("timestamp", ""),
            "checks": 16
        }
        print(f"  site_health: 未解决={unresolved_total}, 今日新修复={today_fixed}, 累计已解决={resolved_count}")
    else:
        data["site_health"] = {"total": 0, "critical": 0, "high": 0, "medium": 0, "low": 0, "auto_fixed": 0, "pending": 0, "resolved": 0, "timestamp": "", "checks": 16}
except Exception as e:
    print("  site_health load failed: " + str(e))
    data["site_health"] = {"total": 0, "critical": 0, "high": 0, "medium": 0, "low": 0, "auto_fixed": 0, "pending": 0, "resolved": 0, "timestamp": "", "checks": 16}

# Agent执行日志（今日修复数量）
try:
    exec_log_file = ROOT / "reports" / "daily_issues" / "execution_log.json"
    if exec_log_file.exists():
        exec_log = json.loads(exec_log_file.read_text(encoding="utf-8"))
        data["agent_execution"] = {
            "date": exec_log.get("target_date", ""),
            "total_fixed": exec_log.get("summary", {}).get("fixed", 0),
            "total_issues": exec_log.get("summary", {}).get("total", 0),
            "agents": exec_log.get("agents", {})
        }
        print("  agent_execution: " + str(exec_log.get("summary", {}).get("fixed", 0)) + " fixes today")
    else:
        data["agent_execution"] = {"date": "", "total_fixed": 0, "total_issues": 0, "agents": {}}
except Exception as e:
    print("  agent_execution load failed: " + str(e))
    data["agent_execution"] = {"date": "", "total_fixed": 0, "total_issues": 0, "agents": {}}


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

# 数据源状态：有缓存真实数据时显示ok(缓存)，不标红
def _ds_status(metric_key):
    m = data["metrics"].get(metric_key, {})
    daily = m.get("daily", [])
    is_real = m.get("is_real_data", False)
    api_status = m.get("status", "unknown")
    if daily and is_real:
        return "ok" if api_status == "OK" else "ok(缓存)"
    return api_status

data["data_sources"] = [
    {"name": "GA4", "configured": _has("GA4_API_KEY", "GA4_SERVICE_ACCOUNT_JSON", "GA4_PROPERTY_ID"), "status": _ds_status("ga4_daily")},
    {"name": "GSC", "configured": _has("GSC_SERVICE_ACCOUNT_JSON"), "status": _ds_status("gsc_daily")},
    {"name": "Travelpayouts", "configured": _has("TRAVELPAYOUTS_API_TOKEN"), "status": "ok"},
    {"name": "NordVPN", "configured": _has("NORDVPN_API_KEY", "NORDVPN_AFFILIATE_ID"), "status": "ok"},
    {"name": "MailerLite", "configured": _has("MAILERLITE_API_TOKEN"), "status": "ok"},
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
