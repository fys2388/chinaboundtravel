#!/usr/bin/env python3
"""生成运营看板 index.html，嵌入真实数据"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
data = json.loads((ROOT / "dashboard_data.json").read_text(encoding="utf-8"))

# Workflow 分类
def classify(wf_name):
    n = wf_name.lower()
    if "daily" in n or "report" in n or "feishu" in n: return "日报与通知"
    if "social" in n or "buffer" in n or "content" in n: return "内容与社媒"
    if "seo" in n or "gsc" in n or "index" in n or "audit" in n: return "SEO与索引"
    if "agent" in n or "learning" in n or "growth" in n or "orchestrat" in n: return "AI Agent"
    if "deploy" in n or "build" in n or "hugo" in n or "environment" in n: return "构建与部署"
    if "backup" in n or "security" in n or "monitor" in n: return "运维与安全"
    return "其他"

categories = {}
for wf in data["workflows"]:
    cat = classify(wf["name"])
    categories.setdefault(cat, []).append(wf)

status_color = {"success": "#22c55e", "failure": "#ef4444", "cancelled": "#f59e0b", "skipped": "#6b7280", "no_runs": "#374151", "unknown": "#374151"}
status_label = {"success": "成功", "failure": "失败", "cancelled": "取消", "skipped": "跳过", "no_runs": "未运行", "unknown": "未知"}

exp_color = {"RUNNING": "#3b82f6", "WAITING_RECRAWL": "#f59e0b", "PENDING": "#6b7280", "WIN": "#22c55e", "LOSE": "#ef4444"}

agents_html = ""
for a in data["agents"].get("agents", []):
    st = a["status"]
    color = "#22c55e" if "正常" in st else ("#f59e0b" if "过期" in st else "#ef4444")
    agents_html += f'''<div class="agent-card" style="border-left:3px solid {color}">
      <div class="agent-name">{a["name"]}</div>
      <div class="agent-status" style="color:{color}">{st}</div>
      <div class="agent-meta">最后运行: {a["last_run"]} | 周期: {a["max_age_days"]}d</div>
    </div>'''

wf_cats_html = ""
for cat, wfs in sorted(categories.items()):
    ok = sum(1 for w in wfs if w["last_status"] == "success")
    fail = sum(1 for w in wfs if w["last_status"] == "failure")
    wf_items = ""
    for w in wfs:
        c = status_color.get(w["last_status"], "#374151")
        lbl = status_label.get(w["last_status"], w["last_status"])
        run_time = w.get("last_run", "")[:10] if w.get("last_run") else "-"
        wf_items += f'''<div class="wf-item">
          <span class="wf-dot" style="background:{c}"></span>
          <span class="wf-name">{w["name"][:36]}</span>
          <span class="wf-time">{run_time}</span>
        </div>'''
    wf_cats_html += f'''<div class="wf-cat">
      <div class="wf-cat-header"><span>{cat}</span><span class="wf-cat-count">{ok}/{len(wfs)} 正常{f' · {fail}失败' if fail else ''}</span></div>
      <div class="wf-list">{wf_items}</div>
    </div>'''

exp_html = ""
for e in data["experiments"]:
    c = exp_color.get(e["status"], "#6b7280")
    days = f'{e["days"]}d' if e.get("days") is not None else "-"
    exp_html += f'''<div class="exp-card" style="border-left:3px solid {c}">
      <div class="exp-id">{e["id"]}</div>
      <div class="exp-name">{e["name"][:40]}</div>
      <div class="exp-meta"><span style="color:{c}">{e["status"]}</span> · 观察{days} · {e.get("sample","-")}</div>
    </div>'''

ds_html = ""
for ds in data["data_sources"]:
    c = "#22c55e" if ds.get("configured") else "#ef4444"
    ds_html += f'''<div class="ds-item"><span class="ds-dot" style="background:{c}"></span>{ds["name"]}</div>'''

ga4 = data["metrics"].get("ga4", {})
gsc = data["metrics"].get("gsc", {})
ml = data["metrics"].get("mailerlite", {})

site = data["site"]
site_color = "#22c55e" if site.get("up") else "#ef4444"
overall = data["agents"].get("overall", "未知")
overall_color = "#22c55e" if "健康" in overall else ("#f59e0b" if "注意" in overall else "#ef4444")

html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ChinaBound Travel 运营监控中心</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#0a0e17; color:#e2e8f0; font-family:'SF Mono','Cascadia Code','Consolas',monospace; font-size:13px; line-height:1.5; }}
.container {{ max-width:1400px; margin:0 auto; padding:20px; }}

/* 顶部状态栏 */
.topbar {{ display:flex; align-items:center; gap:24px; padding:16px 20px; background:#111827; border:1px solid #1f2937; border-radius:8px; margin-bottom:20px; flex-wrap:wrap; }}
.topbar-title {{ font-size:18px; font-weight:700; color:#f1f5f9; letter-spacing:1px; }}
.topbar-title span {{ color:#00d4ff; }}
.status-pill {{ display:inline-flex; align-items:center; gap:6px; padding:4px 12px; border-radius:20px; font-size:12px; font-weight:600; }}
.pulse {{ width:8px; height:8px; border-radius:50%; animation:pulse 2s infinite; }}
@keyframes pulse {{ 0%,100%{{opacity:1;}} 50%{{opacity:0.4;}} }}
.topbar-meta {{ margin-left:auto; font-size:11px; color:#6b7280; }}

/* KPI 条 */
.kpi-row {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:12px; margin-bottom:20px; }}
.kpi {{ background:#111827; border:1px solid #1f2937; border-radius:8px; padding:14px 16px; }}
.kpi-label {{ font-size:11px; color:#6b7280; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:6px; }}
.kpi-value {{ font-size:24px; font-weight:700; color:#f1f5f9; }}
.kpi-sub {{ font-size:11px; color:#6b7280; margin-top:4px; }}

/* 区块 */
.section {{ margin-bottom:24px; }}
.section-header {{ display:flex; align-items:center; gap:10px; margin-bottom:12px; padding-bottom:8px; border-bottom:1px solid #1f2937; }}
.section-title {{ font-size:14px; font-weight:700; color:#00d4ff; text-transform:uppercase; letter-spacing:1px; }}
.section-count {{ font-size:11px; color:#6b7280; }}

/* 两列布局 */
.two-col {{ display:grid; grid-template-columns:1fr 1fr; gap:20px; }}
@media(max-width:900px) {{ .two-col {{ grid-template-columns:1fr; }} }}

/* Workflow */
.wf-cat {{ background:#111827; border:1px solid #1f2937; border-radius:8px; padding:12px; margin-bottom:10px; }}
.wf-cat-header {{ display:flex; justify-content:space-between; font-size:12px; font-weight:600; color:#94a3b8; margin-bottom:8px; }}
.wf-cat-count {{ color:#6b7280; font-weight:400; }}
.wf-list {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:4px; }}
.wf-item {{ display:flex; align-items:center; gap:8px; padding:4px 6px; font-size:11px; border-radius:4px; }}
.wf-item:hover {{ background:#1f2937; }}
.wf-dot {{ width:8px; height:8px; border-radius:50%; flex-shrink:0; }}
.wf-name {{ color:#cbd5e1; flex:1; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.wf-time {{ color:#4b5563; font-size:10px; }}

/* Agent */
.agent-grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(200px,1fr)); gap:10px; }}
.agent-card {{ background:#111827; border:1px solid #1f2937; border-radius:6px; padding:10px 12px; }}
.agent-name {{ font-size:12px; font-weight:600; color:#e2e8f0; margin-bottom:4px; }}
.agent-status {{ font-size:11px; font-weight:600; margin-bottom:4px; }}
.agent-meta {{ font-size:10px; color:#6b7280; }}

/* Experiment */
.exp-grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(240px,1fr)); gap:10px; }}
.exp-card {{ background:#111827; border:1px solid #1f2937; border-radius:6px; padding:10px 12px; }}
.exp-id {{ font-size:11px; font-weight:700; color:#00d4ff; margin-bottom:4px; }}
.exp-name {{ font-size:12px; color:#e2e8f0; margin-bottom:6px; }}
.exp-meta {{ font-size:10px; color:#6b7280; }}

/* Data sources */
.ds-grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(120px,1fr)); gap:8px; }}
.ds-item {{ display:flex; align-items:center; gap:6px; background:#111827; border:1px solid #1f2937; border-radius:6px; padding:8px 10px; font-size:12px; }}
.ds-dot {{ width:8px; height:8px; border-radius:50%; }}

/* 闭环状态 */
.loop-bar {{ display:flex; gap:6px; flex-wrap:wrap; margin-top:10px; }}
.loop-tag {{ padding:3px 8px; border-radius:4px; font-size:10px; background:#1f2937; color:#94a3b8; border:1px solid #374151; }}

.footer {{ text-align:center; font-size:10px; color:#4b5563; padding:20px 0; border-top:1px solid #1f2937; margin-top:20px; }}
</style>
</head>
<body>
<div class="container">

  <!-- 顶部状态栏 -->
  <div class="topbar">
    <div class="topbar-title">ChinaBound <span>运营监控中心</span></div>
    <div class="status-pill" style="background:rgba(34,197,94,0.1);color:#22c55e">
      <span class="pulse" style="background:{site_color}"></span>
      网站 {site.get("status","?")} · {site.get("response_ms",0)}ms
    </div>
    <div class="status-pill" style="background:rgba(0,212,255,0.1);color:{overall_color}">
      <span class="pulse" style="background:{overall_color}"></span>
      AI Agent {overall}
    </div>
    <div class="status-pill" style="background:rgba(245,158,11,0.1);color:#f59e0b">
      Kill Switch: {"已激活" if data.get("kill_switch",{}).get("active") else "未激活"}
    </div>
    <div class="topbar-meta">数据更新: {data["generated_at"]} · 30 Workflows · 7 Agents · 7 Experiments</div>
  </div>

  <!-- KPI 条 -->
  <div class="kpi-row">
    <div class="kpi"><div class="kpi-label">访客 (昨日)</div><div class="kpi-value">{ga4.get("visitors","-")}</div><div class="kpi-sub">{ga4.get("sessions",0)} 会话 · {ga4.get("pageviews",0)} 浏览</div></div>
    <div class="kpi"><div class="kpi-label">GSC 曝光 (28d)</div><div class="kpi-value">{gsc.get("impressions","-")}</div><div class="kpi-sub">{gsc.get("clicks",0)} 点击 · CTR {gsc.get("ctr",0)}%</div></div>
    <div class="kpi"><div class="kpi-label">订阅用户</div><div class="kpi-value">{ml.get("total","-")}</div><div class="kpi-sub">昨日新增 {ml.get("new",0)}</div></div>
    <div class="kpi"><div class="kpi-label">实验在跑</div><div class="kpi-value">{sum(1 for e in data["experiments"] if e["status"]=="RUNNING")}</div><div class="kpi-sub">{sum(1 for e in data["experiments"] if e["status"]=="WAITING_RECRAWL")} 待重爬 · {sum(1 for e in data["experiments"] if e["status"]=="PENDING")} 待启动</div></div>
    <div class="kpi"><div class="kpi-label">Workflow 正常率</div><div class="kpi-value">{round(sum(1 for w in data["workflows"] if w["last_status"]=="success")/len(data["workflows"])*100)}%</div><div class="kpi-sub">{sum(1 for w in data["workflows"] if w["last_status"]=="success")}/{len(data["workflows"])} 成功</div></div>
  </div>

  <!-- 主体两列 -->
  <div class="two-col">
    <!-- 左列：自动化节点 -->
    <div>
      <div class="section">
        <div class="section-header"><span class="section-title">自动化节点闭环</span><span class="section-count">{len(data["workflows"])} workflows</span></div>
        {wf_cats_html}
      </div>
    </div>

    <!-- 右列：AI Agent + 实验 -->
    <div>
      <div class="section">
        <div class="section-header"><span class="section-title">AI Agent 工作状态</span><span class="section-count">{data["agents"].get("healthy_count",0)}/7 正常 · 跨Agent {data["agents"].get("cross_agent_learning","?")}</span></div>
        <div class="agent-grid">{agents_html}</div>
        <div class="loop-bar">
          <span class="loop-tag">SEO闭环</span><span class="loop-tag">内容闭环</span><span class="loop-tag">社媒闭环</span>
          <span class="loop-tag">转化闭环</span><span class="loop-tag">收入闭环</span><span class="loop-tag">用户闭环</span>
          <span class="loop-tag" style="border-color:#00d4ff;color:#00d4ff">跨Agent学习(日度)</span>
        </div>
      </div>

      <div class="section">
        <div class="section-header"><span class="section-title">实验监控</span><span class="section-count">评审gate 2026-09-13</span></div>
        <div class="exp-grid">{exp_html}</div>
      </div>

      <div class="section">
        <div class="section-header"><span class="section-title">数据源健康</span></div>
        <div class="ds-grid">{ds_html}</div>
      </div>
    </div>
  </div>

  <div class="footer">
    ChinaBound Travel Ops Dashboard · 数据来源: GitHub Actions + GA4 + GSC + 本地报告 · 生成于 {data["generated_at"]}
  </div>
</div>
</body>
</html>'''

(ROOT / "index.html").write_text(html, encoding="utf-8")
print(f"✅ index.html generated: {len(html)} bytes")
print(f"   Workflow categories: {list(categories.keys())}")
print(f"   Agents: {data['agents'].get('healthy_count',0)}/7 healthy")
print(f"   Experiments: {len(data['experiments'])}")
