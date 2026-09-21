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

try:
    from buffer_credentials import configured_buffer_accounts
except ImportError:
    configured_buffer_accounts = lambda: []


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


# ============================================================
# 2026-09-21 数据新鲜度可见性（假绿灯治理）
#
# 根因：collect_data.py 此前对 metrics.gsc_daily / ga4_daily 无条件写
#     "status": "OK"，data_sources 也一律标 "ok"，
# 只要 API 返回任意一份数据（哪怕 30 天前的旧值）就会被看板当成当前状态。
# 症状：dashboard_data.json 里 metrics.gsc_daily.daily 末端停在 2026-08-17，
#       ranges.today/7d/30d/90d 全部基于 35 天前的序列计算，但看板显示 "OK"。
# 修复：
#   1. 每个数据源都携带 updated_at / age_days / threshold_days / status
#   2. metrics.gsc_daily / ga4_daily 的 status 从 freshness 推导，不再写死 "OK"
#   3. 顶层新增 data_freshness 块，看板 UI 一眼可见哪个源陈旧、陈旧多少天
#   4. data_sources 的 status 也走 freshness，不再只看 is_real_data
# ============================================================
FRESHNESS_THRESHOLDS = {
    # GA4 单日数据本身约 T+1，留 2 天缓冲
    "ga4_daily": 2,
    # GSC 有 ~3 天固有延迟，allow 5
    "gsc_daily": 5,
    # 28 天累计缓存文件
    "ga4_28d": 4,
    "gsc_28d": 4,
    # 内容扫描
    "content": 3,
    # Agent KPI / Growth 是月度产物，阈值对齐月度节奏
    "agent_kpi": 35,
    "agent_growth": 35,
    # Site health / Quality / Agent execution 都应有日级刷新
    "site_health": 2,
    "quality": 2,
    "agent_execution": 2,
}


def _parse_ts(s):
    """尽力解析常见时间戳字符串为 naive datetime；失败返回 None。

    兼容 dashboard_data.json / gsc_real_data.json 里所有实际出现过的格式：
    - "2026-09-21 02:00:56"（collect_data.py 生成）
    - "2026-09-17T14:04:45.153291"（GitHub runner UTC 无时区）
    - "2026-09-17"（date only）
    """
    if not s:
        return None
    s = str(s).strip()
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(s[:19], fmt)
        except ValueError:
            continue
    return None


def _metric_updated_at(metric):
    """从 metric 字典里取"最后一天的数据日期"。

    优先级：daily[-1].date（真实序列末端） > metric.date > metric.data_date
    > metric.updated_at。这样 GSC 序列即使被 rowLimit 截断也能被识别到
    "最后一条真实数据是哪一天"，而不是被顶层 date 字段掩盖。
    """
    if not isinstance(metric, dict):
        return ""
    daily = metric.get("daily", [])
    if isinstance(daily, list) and daily:
        dates = sorted(
            d.get("date", "")
            for d in daily
            if isinstance(d, dict) and d.get("date")
        )
        if dates:
            return dates[-1]
    return metric.get("date") or metric.get("data_date") or metric.get("updated_at") or ""


def _metric_freshness(metric, name):
    """为某个 metric 或文件计算新鲜度元数据。

    返回结构：
      {name, updated_at, age_days, threshold_days, status, label}
    status ∈ {"fresh", "stale", "missing"}

    - fresh：age_days <= threshold
    - stale：age_days > threshold（数据在磁盘，但已陈旧）
    - missing：updated_at 无法解析或不存在
    """
    threshold = FRESHNESS_THRESHOLDS.get(name, 3)
    upd = _metric_updated_at(metric) if isinstance(metric, dict) else (metric or "")
    dt = _parse_ts(upd) if upd else None
    now = datetime.now()
    if dt is None:
        return {
            "name": name,
            "updated_at": str(upd) if upd else "",
            "age_days": None,
            "threshold_days": threshold,
            "status": "missing",
            "label": f"{name}: 数据缺失（未取到时间戳）",
        }
    age = (now.date() - dt.date()).days
    if age <= 0:
        status = "fresh"
        label = "实时" if age == 0 else f"{abs(age)}h 内"
    elif age <= threshold:
        status = "fresh"
        label = f"{age} 天前"
    else:
        status = "stale"
        label = f"陈旧 {age} 天（阈值 {threshold} 天）"
    return {
        "name": name,
        "updated_at": str(upd),
        "age_days": age,
        "threshold_days": threshold,
        "status": status,
        "label": label,
    }


def _file_freshness(file_path, name):
    """读取 ops-dashboard/*.json 文件的 updated_at，产出同一形状的 freshness 元数据。

    优雅降级：文件不存在 / JSON 损坏 / 无 updated_at 字段时返回 missing 状态，
    不抛异常、不写 stub 数据覆盖上一份真实结果。
    """
    threshold = FRESHNESS_THRESHOLDS.get(name, 3)
    if not file_path or not file_path.exists():
        return {
            "name": name,
            "updated_at": "",
            "age_days": None,
            "threshold_days": threshold,
            "status": "missing",
            "label": f"{name}: 文件不存在（{file_path.name if file_path else '?'}）",
        }
    try:
        body = json.loads(file_path.read_text(encoding="utf-8-sig"))
    except Exception as e:
        return {
            "name": name,
            "updated_at": "",
            "age_days": None,
            "threshold_days": threshold,
            "status": "missing",
            "label": f"{name}: JSON 解析失败（{str(e)[:40]}）",
        }
    # agent_kpi_data.json / agent_growth_data.json 用 updated_at；
    # 兼容 month / data_date 字段（agent_growth 有的版本只写 month）
    upd = body.get("updated_at") or body.get("data_date") or body.get("month") or ""
    if not upd:
        return {
            "name": name,
            "updated_at": "",
            "age_days": None,
            "threshold_days": threshold,
            "status": "missing",
            "label": f"{name}: 文件里无 updated_at 字段",
        }
    return _metric_freshness({"date": upd}, name)


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
        content = f.read_text(encoding="utf-8-sig")  # 自动去除BOM
        for line in content.splitlines():
            if line.lstrip("\ufeff").startswith("name:"):
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

# 用 gh CLI 查每个 workflow 最近运行（limit 500，多维度匹配）
def _norm(s):
    """规范化字符串用于模糊匹配：去空格/括号/连字符/标点，转小写"""
    import re
    return re.sub(r'[\s_\-()（）【】\[\].,，。:：+]', '', s).lower()

try:
    import subprocess
    result = subprocess.run(
        [
            "gh",
            "run",
            "list",
            "--limit",
            "500",
            "--json",
            "name,status,conclusion,createdAt,event,databaseId,workflowName",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(ROOT),
        timeout=60,
    )
    if result.returncode == 0:
        runs = json.loads(result.stdout)
        latest_by_name = {}
        latest_by_wfname = {}
        latest_by_norm = {}
        for run in runs:
            wf_name = run.get("name", "")
            wf_full = run.get("workflowName", "")
            if wf_name and wf_name not in latest_by_name:
                latest_by_name[wf_name] = run
            if wf_full and wf_full not in latest_by_wfname:
                latest_by_wfname[wf_full] = run
            for key in [wf_name, wf_full]:
                if key:
                    n = _norm(key)
                    if n and n not in latest_by_norm:
                        latest_by_norm[n] = run
        for wf in workflows:
            # 精确匹配：name 或 workflowName
            run = latest_by_name.get(wf["name"]) or latest_by_wfname.get(wf["name"])
            # 模糊匹配：规范化后的 display name 或 文件名
            if not run:
                run = latest_by_norm.get(_norm(wf["name"])) or latest_by_norm.get(_norm(wf["id"]))
            if run:
                wf["last_status"] = run.get("conclusion", run.get("status", "unknown"))
                wf["last_run"] = run.get("createdAt", "")
                wf["last_event"] = run.get("event", "")
            else:
                # 手动触发型显示"手动"
                if wf.get("frequency") == "手动":
                    wf["last_status"] = "manual"
                    wf["last_run"] = ""
                    wf["last_event"] = "manual"
                # 按周/月/季/年调度的，运行记录可能超出查询范围，显示"按周期调度"
                elif wf.get("frequency") in ["每周", "每月", "每季", "每年"]:
                    wf["last_status"] = "scheduled"
                    wf["last_run"] = ""
                    wf["last_event"] = "scheduled"
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

# Unified quality gate data (content + predeploy + online semantic + visual + SEO + site health)
try:
    quality_file = ROOT / "reports" / "quality" / "quality_issues.json"
    if quality_file.exists():
        quality = json.loads(quality_file.read_text(encoding="utf-8"))
        summary = quality.get("summary", {})
        data["quality"] = {
            "available": True,
            "generated_at": quality.get("generated_at", ""),
            "total": summary.get("total", 0),
            "P0": summary.get("P0", 0),
            "P1": summary.get("P1", 0),
            "P2": summary.get("P2", 0),
            "by_source": summary.get("by_source", {}),
            "by_owner": summary.get("by_owner", {}),
            "sources": quality.get("sources", {}),
            "issues": quality.get("issues", [])[:50],
        }
        print(
            "  quality: total={total}, P0={P0}, P1={P1}, P2={P2}".format(
                total=data["quality"]["total"],
                P0=data["quality"]["P0"],
                P1=data["quality"]["P1"],
                P2=data["quality"]["P2"],
            )
        )
    else:
        data["quality"] = {
            "available": False,
            "generated_at": "",
            "total": 0,
            "P0": 0,
            "P1": 0,
            "P2": 0,
            "by_source": {},
            "by_owner": {},
            "sources": {},
            "issues": [],
        }
        print("  quality: unified report missing")
except Exception as e:
    print("  quality load failed: " + str(e))
    data["quality"] = {
        "available": False,
        "generated_at": "",
        "total": 0,
        "P0": 0,
        "P1": 0,
        "P2": 0,
        "by_source": {},
        "by_owner": {},
        "sources": {},
        "issues": [],
        "error": str(e)[:160],
    }

# Agent执行日志（今日修复数量）
try:
    exec_log_file = ROOT / "reports" / "daily_issues" / "execution_log.json"
    if exec_log_file.exists():
        exec_log = json.loads(exec_log_file.read_text(encoding="utf-8"))
        agents = exec_log.get("agents", {})
        exec_date = exec_log.get("target_date", "")
        today = datetime.now().strftime("%Y-%m-%d")
        is_today = exec_date == today
        from status_writeback import reconcile_agents_with_tasks

        reconcile_agents_with_tasks(
            agents,
            exec_date,
            ROOT / "reports" / "daily_issues" / "agent_tasks",
        )
        summary = {
            "total": sum(int(v.get("total", 0) or 0) for v in agents.values()),
            "fixed": sum(int(v.get("fixed", 0) or 0) for v in agents.values()),
            "failed": sum(int(v.get("failed", 0) or 0) for v in agents.values()),
            "manual_review": sum(
                int(v.get("manual_review", 0) or 0) for v in agents.values()
            ),
            "in_progress": sum(
                int(v.get("in_progress", 0) or 0) for v in agents.values()
            ),
        }
        data["agent_execution"] = {
            "date": exec_date,
            "is_today": is_today,
            "total_fixed": summary.get("fixed", 0) if is_today else 0,
            "total_issues": summary.get("total", 0) if is_today else 0,
            "manual_review": summary.get("manual_review", 0) if is_today else 0,
            "failed": summary.get("failed", 0) if is_today else 0,
            "in_progress": summary.get("in_progress", 0) if is_today else 0,
            "agents": agents if is_today else {},
        }
        print(
            "  agent_execution: "
            + str(summary.get("fixed", 0))
            + " fixes, "
            + str(summary.get("manual_review", 0))
            + " manual, "
            + str(summary.get("failed", 0))
            + " failed"
        )
    else:
        data["agent_execution"] = {
            "date": "",
            "total_fixed": 0,
            "total_issues": 0,
            "manual_review": 0,
            "failed": 0,
            "in_progress": 0,
            "agents": {},
        }
except Exception as e:
    print("  agent_execution load failed: " + str(e))
    data["agent_execution"] = {
        "date": "",
        "total_fixed": 0,
        "total_issues": 0,
        "manual_review": 0,
        "failed": 0,
        "in_progress": 0,
        "agents": {},
    }



# 多时间范围汇总计算
def _calc_ranges(daily, metrics_map):
    """从 daily 数组计算多个时间范围的汇总
    metrics_map: {"visitors": "activeUsers", "sessions": "sessions", "pageviews": "pageviews"}
    """
    from datetime import datetime, timedelta
    if not daily:
        return {}
    today = datetime.now().date()
    ranges = {}
    range_defs = {
        "today": 1,
        "yesterday": 2,
        "7d": 7,
        "30d": 30,
        "90d": 90,
    }
    # 按日期排序
    sorted_daily = sorted(daily, key=lambda x: x.get("date", ""))
    for name, days in range_defs.items():
        subset = sorted_daily[-days:] if name != "yesterday" else sorted_daily[-2:-1]
        summary = {}
        for key, field in metrics_map.items():
            summary[key] = sum(int(d.get(field, 0) or 0) for d in subset)
        summary["date_range"] = f"{subset[0].get('date','')} ~ {subset[-1].get('date','')}" if subset else ""
        summary["days"] = len(subset)
        ranges[name] = summary
    # 上个月（自然月）
    try:
        first_of_this_month = today.replace(day=1)
        last_month_end = first_of_this_month - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        lm_subset = [d for d in sorted_daily if last_month_start.strftime("%Y-%m-%d") <= d.get("date","") <= last_month_end.strftime("%Y-%m-%d")]
        lm_summary = {}
        for key, field in metrics_map.items():
            lm_summary[key] = sum(int(d.get(field, 0) or 0) for d in lm_subset)
        lm_summary["date_range"] = f"{last_month_start.strftime('%Y-%m-%d')} ~ {last_month_end.strftime('%Y-%m-%d')}"
        lm_summary["days"] = len(lm_subset)
        ranges["last_month"] = lm_summary
    except:
        pass
    return ranges

# 5b. GA4/GSC 单日数据（拉取90天，计算多时间范围）（日报口径，save=False 不覆盖28天文件）
#
# 2026-09-21 修复：status 从 freshness 推导，不再写死 "OK"。
# 之前 API 只要返回任意数据就写 status="OK"，即使 daily 序列末端停在 35 天前，
# 看板的 data_sources 与 UI 都读成 "ok" —— 这是 GSC 日期错位事件的直接根因。
try:
    from real_data_pull_engine import pull_ga4_data, pull_gsc_data
    ga4_daily = pull_ga4_data(days=90, save=False)
    if ga4_daily.get("is_real_data") and ga4_daily.get("metrics"):
        m = ga4_daily["metrics"]
        # 最近一天数据（用于KPI显示）
        latest = ga4_daily.get("daily", [])[-1] if ga4_daily.get("daily") else {}
        # 多时间范围汇总
        ga4_ranges = _calc_ranges(ga4_daily.get("daily", []), {
            "visitors": "activeUsers",
            "sessions": "sessions",
            "pageviews": "pageviews",
        })
        _ga4_payload = {
            "visitors": latest.get("activeUsers", m.get("activeUsers", 0)),
            "sessions": latest.get("sessions", m.get("sessions", 0)),
            "pageviews": latest.get("pageviews", m.get("screenPageViews", 0)),
            "new_users": m.get("newUsers", 0),
            "bounce_rate": round(m.get("bounceRate", 0) * 100, 1),
            "date": latest.get("date", ga4_daily.get("data_date", "")),
            "status": "OK",
            "daily": ga4_daily.get("daily", []),
            "ranges": ga4_ranges,
            "is_real_data": True,
        }
        _ga4_payload["freshness"] = _metric_freshness(_ga4_payload, "ga4_daily")
        if _ga4_payload["freshness"]["status"] == "stale":
            _ga4_payload["status"] = "STALE"
            _ga4_payload["stale_reason"] = _ga4_payload["freshness"]["label"]
        elif _ga4_payload["freshness"]["status"] == "missing":
            _ga4_payload["status"] = "MISSING"
        data["metrics"]["ga4_daily"] = _ga4_payload
    else:
        data["metrics"]["ga4_daily"] = {
            "visitors": 0, "sessions": 0, "pageviews": 0,
            "status": ga4_daily.get("status", "failed"),
            "date": "", "daily": [], "is_real_data": False,
            "freshness": _metric_freshness(
                {"date": ga4_daily.get("data_date", "")}, "ga4_daily"
            ) | {"status": "missing",
                 "label": f"数据缺失（API status={ga4_daily.get('status', 'failed')}）"},
        }
except Exception as e:
    data["metrics"]["ga4_daily"] = {
        "visitors": 0, "sessions": 0, "pageviews": 0,
        "status": "error:" + str(e)[:50], "date": "", "daily": [],
        "is_real_data": False,
        "freshness": _metric_freshness({}, "ga4_daily") | {
            "status": "missing",
            "label": "采集异常: " + str(e)[:60],
        },
    }

try:
    gsc_daily = pull_gsc_data(days=90, save=False)
    if gsc_daily.get("is_real_data") and gsc_daily.get("metrics"):
        m = gsc_daily["metrics"]
        latest = gsc_daily.get("daily", [])[-1] if gsc_daily.get("daily") else {}
        # 多时间范围汇总
        gsc_ranges = _calc_ranges(gsc_daily.get("daily", []), {
            "impressions": "impressions",
            "clicks": "clicks",
        })
        _gsc_payload = {
            "impressions": latest.get("impressions", m.get("impressions", 0)),
            "clicks": latest.get("clicks", m.get("clicks", 0)),
            "ctr": latest.get("ctr", round(m.get("ctr", 0), 2)),
            "avg_position": latest.get("position", m.get("average_position", 0)),
            "date": latest.get("date", gsc_daily.get("data_date", "")),
            "status": "OK",
            "daily": gsc_daily.get("daily", []),
            "ranges": gsc_ranges,
            "is_real_data": True,
        }
        _gsc_payload["freshness"] = _metric_freshness(_gsc_payload, "gsc_daily")
        if _gsc_payload["freshness"]["status"] == "stale":
            _gsc_payload["status"] = "STALE"
            _gsc_payload["stale_reason"] = _gsc_payload["freshness"]["label"]
        elif _gsc_payload["freshness"]["status"] == "missing":
            _gsc_payload["status"] = "MISSING"
        data["metrics"]["gsc_daily"] = _gsc_payload
    else:
        data["metrics"]["gsc_daily"] = {
            "impressions": 0, "clicks": 0, "ctr": 0,
            "status": gsc_daily.get("status", "failed"),
            "date": "", "daily": [], "is_real_data": False,
            "freshness": _metric_freshness(
                {"date": gsc_daily.get("data_date", "")}, "gsc_daily"
            ) | {"status": "missing",
                 "label": f"数据缺失（API status={gsc_daily.get('status', 'failed')}）"},
        }
except Exception as e:
    data["metrics"]["gsc_daily"] = {
        "impressions": 0, "clicks": 0, "ctr": 0,
        "status": "error:" + str(e)[:50], "date": "", "daily": [],
        "is_real_data": False,
        "freshness": _metric_freshness({}, "gsc_daily") | {
            "status": "missing",
            "label": "采集异常: " + str(e)[:60],
        },
    }

# 6. 数据源状态
def _has(*keys):
    return any(os.environ.get(k) for k in keys)

# 数据源状态：先看 freshness，再看 is_real_data/api_status。
# 2026-09-21 修复：不再让 is_real_data 单独决定状态；
# 数据在磁盘但已陈旧时，明确返回 "stale" 而不是 "ok(缓存)"。
def _ds_status(metric_key):
    m = data["metrics"].get(metric_key, {})
    daily = m.get("daily", [])
    is_real = m.get("is_real_data", False)
    api_status = m.get("status", "unknown")
    fresh = m.get("freshness", {})
    fresh_status = fresh.get("status", "")
    # 优先级：freshness > is_real_data 判据
    if fresh_status == "stale":
        return "stale"
    if fresh_status == "missing" and not daily and not is_real:
        # 既没有真实数据，也没有 fallback —— 尊重 API 层的错误状态
        return api_status if api_status else "missing"
    if daily and is_real:
        return "ok" if api_status in ("OK", "STALE") else "ok(缓存)"
    return api_status

def _ds_entry(name, metric_key, configured):
    """构造 data_sources 里一条 entry，把 freshness 也塞进来。"""
    m = data["metrics"].get(metric_key, {})
    fresh = m.get("freshness", {}) or _metric_freshness(m, metric_key)
    return {
        "name": name,
        "configured": bool(configured),
        "status": _ds_status(metric_key),
        "updated_at": fresh.get("updated_at", ""),
        "age_days": fresh.get("age_days"),
        "threshold_days": fresh.get("threshold_days"),
        "freshness_status": fresh.get("status", "missing"),
        "freshness_label": fresh.get("label", ""),
    }

data["data_sources"] = [
    _ds_entry("GA4", "ga4_daily", _has("GA4_API_KEY", "GA4_SERVICE_ACCOUNT_JSON", "GA4_PROPERTY_ID")),
    _ds_entry("GSC", "gsc_daily", _has("GSC_SERVICE_ACCOUNT_JSON")),
    {"name": "Travelpayouts", "configured": _has("TRAVELPAYOUTS_API_TOKEN"), "status": "ok",
     "updated_at": "", "age_days": None, "threshold_days": 0,
     "freshness_status": "unknown", "freshness_label": "无时间戳字段（凭据存在即视为可用）"},
    {"name": "NordVPN", "configured": _has("NORDVPN_API_KEY", "NORDVPN_AFFILIATE_ID"), "status": "ok",
     "updated_at": "", "age_days": None, "threshold_days": 0,
     "freshness_status": "unknown", "freshness_label": "无时间戳字段（凭据存在即视为可用）"},
    {"name": "MailerLite", "configured": _has("MAILERLITE_API_TOKEN"), "status": "ok",
     "updated_at": "", "age_days": None, "threshold_days": 0,
     "freshness_status": "unknown", "freshness_label": "无时间戳字段（凭据存在即视为可用）"},
    {"name": "Buffer", "configured": bool(configured_buffer_accounts()), "status": "ok",
     "updated_at": "", "age_days": None, "threshold_days": 0,
     "freshness_status": "unknown", "freshness_label": "无时间戳字段（凭据存在即视为可用）"},
    {"name": "Cloudflare", "configured": _has("CLOUDFLARE_API_TOKEN"), "status": "ok",
     "updated_at": "", "age_days": None, "threshold_days": 0,
     "freshness_status": "unknown", "freshness_label": "无时间戳字段（凭据存在即视为可用）"},
]

# 7. Kill switch
try:
    from ai_governance import check_kill_switch
    safe, reason = check_kill_switch()
    data["kill_switch"] = {"active": not safe, "reason": reason}
except:
    data["kill_switch"] = {"active": False, "reason": "unknown"}

# 8. 顶层 data_freshness 块 —— 看板陈旧度可见性
#    这是「程序成功结束但结果不是最新结果」的假绿灯治理入口：
#    每个数据源都暴露 updated_at / age_days / threshold_days / status，
#    超过阈值时 warnings 会列出人类可读的告警，overall 会标 "stale" 或 "missing"。
def _source_freshness(metric_key):
    """从 metrics 里取某个源的 freshness 元数据；缺失时现场计算。"""
    m = data["metrics"].get(metric_key, {})
    return m.get("freshness") or _metric_freshness(m, metric_key)

# Agent KPI / Growth：读 ops-dashboard/ 源文件的 updated_at
_kpi_path = ROOT / "ops-dashboard" / "agent_kpi_data.json"
_growth_path = ROOT / "ops-dashboard" / "agent_growth_data.json"
_kpi_freshness = _file_freshness(_kpi_path, "agent_kpi")
_growth_freshness = _file_freshness(_growth_path, "agent_growth")

# site_health / quality / agent_execution 的 freshness
_sh = data.get("site_health", {}) or {}
_quality = data.get("quality", {}) or {}
_exec = data.get("agent_execution", {}) or {}
_sh_ts = _sh.get("timestamp", "") or _sh.get("date", "")
_quality_ts = _quality.get("generated_at", "")
_exec_ts = _exec.get("date", "")
_sh_freshness = _metric_freshness({"date": _sh_ts}, "site_health") if _sh_ts else _metric_freshness({}, "site_health")
_quality_freshness = _metric_freshness({"date": _quality_ts}, "quality") if _quality_ts else _metric_freshness({}, "quality")
_exec_freshness = _metric_freshness({"date": _exec_ts}, "agent_execution") if _exec_ts else _metric_freshness({}, "agent_execution")

_sources = {
    "ga4_daily": _source_freshness("ga4_daily"),
    "gsc_daily": _source_freshness("gsc_daily"),
    "ga4_28d": _metric_freshness(data["metrics"].get("ga4_28d", {}), "ga4_28d"),
    "gsc_28d": _metric_freshness(data["metrics"].get("gsc_28d", {}), "gsc_28d"),
    "content": _metric_freshness(data["metrics"].get("content", {}), "content"),
    "agent_kpi": _kpi_freshness,
    "agent_growth": _growth_freshness,
    "site_health": _sh_freshness,
    "quality": _quality_freshness,
    "agent_execution": _exec_freshness,
}

_warnings = []
_stale = False
_missing = False
for _name, _meta in _sources.items():
    _s = _meta.get("status", "missing")
    if _s == "stale":
        _stale = True
        _warnings.append(f"[STALE] {_meta.get('label', _name)}")
    elif _s == "missing":
        _missing = True
        _warnings.append(f"[MISSING] {_meta.get('label', _name)}")

# overall: 任何 missing 优先于 stale；否则 stale 优先于 fresh
if _missing:
    _overall = "missing"
elif _stale:
    _overall = "stale"
else:
    _overall = "fresh"

data["data_freshness"] = {
    "generated_at": data["generated_at"],
    "thresholds": FRESHNESS_THRESHOLDS,
    "overall": _overall,
    "overall_label": {
        "fresh": "全部数据源均在阈值内",
        "stale": "存在陈旧数据源（详见 warnings）",
        "missing": "存在数据缺失的源（详见 warnings）",
    }[_overall],
    "warnings": _warnings,
    "sources": _sources,
    # 便捷字段：agent_kpi / agent_growth 是月度产物，这里显式对比它们与主看板的间隔
    "publish_path_gap": {
        "dashboard_generated_at": data["generated_at"],
        "agent_kpi_updated_at": _kpi_freshness.get("updated_at", ""),
        "agent_kpi_age_days": _kpi_freshness.get("age_days"),
        "agent_kpi_threshold_days": _kpi_freshness.get("threshold_days"),
        "agent_kpi_status": _kpi_freshness.get("status", "missing"),
        "agent_growth_updated_at": _growth_freshness.get("updated_at", ""),
        "agent_growth_age_days": _growth_freshness.get("age_days"),
        "agent_growth_threshold_days": _growth_freshness.get("threshold_days"),
        "agent_growth_status": _growth_freshness.get("status", "missing"),
        "note": "agent_kpi_data.json 与 agent_growth_data.json 由 agent-kpi-monthly.yml 每月 1 日 10:00 北京时间生成；"
                "dashboard_data.json 由 ops-dashboard-hourly.yml 每 30 分钟刷新。"
                "月度产物天然与小时级看板存在时间差，本字段用于让看板自身承认这个差值，"
                "而不是让读者误以为看板刷新了考核数据也刷新了。",
    },
}

# 输出
out = ROOT / "ops-dashboard" / "dashboard_data.json"
out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
overall_status = str(data["agents"].get("overall", "?")).encode(
    "ascii", "backslashreplace"
).decode("ascii")
print(
    "[OK] Data collected:",
    len(workflows),
    "workflows,",
    len(data["experiments"]),
    "experiments, agents=",
    overall_status,
)
print("   Site:", data["site"].get("status"), str(data["site"].get("response_ms")) + "ms")
print("   GA4 daily:", data["metrics"]["ga4_daily"].get("visitors"), "visitors, status=", data["metrics"]["ga4_daily"].get("status"))
print("   GSC daily:", data["metrics"]["gsc_daily"].get("impressions"), "impressions, status=", data["metrics"]["gsc_daily"].get("status"))
