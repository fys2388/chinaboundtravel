#!/usr/bin/env python3
"""收集运营看板所需的全部真实数据，输出 dashboard_data.json"""
import json, sys, os, time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

# 加载 .env 环境变量
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

data = {"generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "site": {}, "workflows": [], "agents": {}, "experiments": [], "metrics": {}, "data_sources": []}

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
    # 从文件中提取 name 字段
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
    workflows.append({"file": f.name, "name": display, "id": name})

# 用 gh CLI 查每个 workflow 最近运行
try:
    import subprocess
    result = subprocess.run(["gh", "run", "list", "--limit", "50", "--json", "name,status,conclusion,createdAt,event,databaseId"], capture_output=True, text=True, cwd=str(ROOT), timeout=30)
    if result.returncode == 0:
        runs = json.loads(result.stdout)
        # 按 workflow name 分组取最新
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

# 5. 关键指标
# GA4
try:
    ga4 = json.loads((ROOT / "reports/real_data/ga4_real_data.json").read_text(encoding="utf-8"))
    data["metrics"]["ga4"] = {"status": ga4.get("status", "unknown"), "visitors": ga4.get("visitors", 0), "sessions": ga4.get("sessions", 0), "pageviews": ga4.get("pageviews", 0), "date": ga4.get("date", "")}
except:
    data["metrics"]["ga4"] = {"status": "not_found"}

# GSC
try:
    gsc = json.loads((ROOT / "reports/real_data/gsc_real_data.json").read_text(encoding="utf-8"))
    data["metrics"]["gsc"] = {"status": gsc.get("status", "unknown"), "impressions": gsc.get("impressions", 0), "clicks": gsc.get("clicks", 0), "ctr": gsc.get("ctr", 0)}
except:
    data["metrics"]["gsc"] = {"status": "not_found"}

# 订阅
try:
    ml = json.loads((ROOT / "reports/real_data/mailerlite_data.json").read_text(encoding="utf-8"))
    data["metrics"]["mailerlite"] = {"total": ml.get("total_subscribers", 0), "new": ml.get("new_subscribers", 0)}
except:
    data["metrics"]["mailerlite"] = {"total": 0, "new": 0}

# 6. 数据源状态（基于 .env 中实际变量名）
def _has(*keys):
    return any(os.environ.get(k) for k in keys)

data["data_sources"] = [
    {"name": "GA4", "configured": _has("GA4_API_KEY", "GA4_SERVICE_ACCOUNT_JSON", "GA4_PROPERTY_ID"), "status": data["metrics"]["ga4"].get("status", "unknown")},
    {"name": "GSC", "configured": _has("GSC_SERVICE_ACCOUNT_JSON"), "status": data["metrics"]["gsc"].get("status", "unknown")},
    {"name": "Travelpayouts", "configured": _has("TRAVELPAYOUTS_API_TOKEN"), "status": "ok"},
    {"name": "NordVPN", "configured": _has("NORDVPN_API_KEY", "NORDVPN_AFFILIATE_ID"), "status": "ok"},
    {"name": "MailerLite", "configured": _has("MAILERLITE_API_TOKEN"), "status": "ok" if data["metrics"]["mailerlite"].get("total", 0) > 0 else "configured"},
    {"name": "Buffer", "configured": _has("BUFFER_API_TOKEN_A", "BUFFER_API_TOKEN_B", "BUFFER_ACCESS_TOKEN"), "status": "ok"},
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
print(f"✅ Data collected: {len(workflows)} workflows, {len(data['experiments'])} experiments, agents={data['agents'].get('overall','?')}")
print(f"   Site: {data['site'].get('status')} {data['site'].get('response_ms')}ms")
