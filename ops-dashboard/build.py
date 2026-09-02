#!/usr/bin/env python3
"""生成运营看板 index.html — 精致深色监控中心风格"""
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

# Agent 卡片
agents_html = ""
for a in data["agents"].get("agents", []):
    st = a["status"]
    color = "#22c55e" if "正常" in st else ("#f59e0b" if "过期" in st else "#ef4444")
    dot_class = "dot-live" if "正常" in st else "dot-warn"
    agents_html += f'''<div class="agent-card">
      <div class="agent-top">
        <span class="agent-dot {dot_class}" style="background:{color}"></span>
        <span class="agent-name">{a["name"]}</span>
      </div>
      <div class="agent-status" style="color:{color}">{st}</div>
      <div class="agent-meta">最后运行 {a["last_run"]} · 周期 {a["max_age_days"]}d</div>
    </div>'''

# Workflow 分类
wf_cats_html = ""
for cat, wfs in sorted(categories.items()):
    ok = sum(1 for w in wfs if w.get("last_status") == "success")
    fail = sum(1 for w in wfs if w.get("last_status") == "failure")
    noruns = sum(1 for w in wfs if w.get("last_status") in ("no_runs", "unknown"))
    cat_color = "#22c55e" if fail == 0 else "#ef4444"
    wf_items = ""
    for w in wfs:
        c = status_color.get(w.get("last_status", "unknown"), "#374151")
        lbl = status_label.get(w.get("last_status", "unknown"), w.get("last_status", "unknown"))
        run_time = w.get("last_run", "")[:10] if w.get("last_run") else "-"
        wf_items += f'''<div class="wf-item" title="{w["name"]} — {lbl}">
          <span class="wf-dot" style="background:{c};box-shadow:0 0 6px {c}66"></span>
          <span class="wf-name">{w["name"][:50]}</span><span class="wf-freq">{w.get("frequency","手动")}</span>
          <span class="wf-time">{run_time}</span>
        </div>'''
    wf_cats_html += f'''<div class="wf-cat">
      <div class="wf-cat-header">
        <span class="wf-cat-title">{cat}</span>
        <span class="wf-cat-count" style="color:{cat_color}">{ok}成功{f' · {fail}失败' if fail else ''}{f' · {noruns}未运行' if noruns else ''}</span>
      </div>
      <div class="wf-list">{wf_items}</div>
    </div>'''

# 实验卡片
exp_html = ""
for e in data["experiments"]:
    c = exp_color.get(e["status"], "#6b7280")
    days = f'{e["days"]}d' if e.get("days") is not None else "-"
    sample = e.get("sample", "-")
    exp_html += f'''<div class="exp-card">
      <div class="exp-top">
        <span class="exp-id">{e["id"]}</span>
        <span class="exp-badge" style="background:{c}1a;color:{c};border:1px solid {c}40">{e["status"]}</span>
      </div>
      <div class="exp-name">{e["name"][:42]}</div>
      <div class="exp-meta">观察 {days} · 样本 {sample}</div>
    </div>'''

# 数据源
ds_html = ""
for ds in data["data_sources"]:
    c = "#22c55e" if ds.get("configured") else "#ef4444"
    ds_html += f'''<div class="ds-item">
      <span class="ds-dot" style="background:{c};box-shadow:0 0 8px {c}88"></span>
      <span>{ds["name"]}</span>
    </div>'''

ga4 = data["metrics"].get("ga4_daily", data["metrics"].get("ga4", {}))
gsc = data["metrics"].get("gsc_daily", data["metrics"].get("gsc", {}))
content = data["metrics"].get("content", {})

site = data["site"]
site_color = "#22c55e" if site.get("up") else "#ef4444"
overall = data["agents"].get("overall", "未知")
overall_color = "#22c55e" if "健康" in overall else ("#f59e0b" if "注意" in overall else "#ef4444")
kill_active = data.get("kill_switch", {}).get("active", False)
kill_color = "#ef4444" if kill_active else "#22c55e"

# 统计
total_wf = len(data["workflows"])
ok_wf = sum(1 for w in data["workflows"] if w.get("last_status") == "success")
fail_wf = sum(1 for w in data["workflows"] if w.get("last_status") == "failure")
noruns_wf = sum(1 for w in data["workflows"] if w.get("last_status") in ("no_runs", "unknown"))
skipped_wf = sum(1 for w in data["workflows"] if w.get("last_status") == "skipped")
active_wf = ok_wf + fail_wf  # only count workflows that have actually run
running_exp = sum(1 for e in data["experiments"] if e["status"] == "RUNNING")
waiting_exp = sum(1 for e in data["experiments"] if e["status"] == "WAITING_RECRAWL")
pending_exp = sum(1 for e in data["experiments"] if e["status"] == "PENDING")
healthy_agents = data["agents"].get("healthy_count", 0)

# Format update time to hour precision (cron runs at exact hours)
_update_raw = data.get("generated_at", "")
try:
    from datetime import datetime as _dt
    _parsed = _dt.strptime(_update_raw, "%Y-%m-%d %H:%M:%S")
    update_hour = _parsed.strftime("%H:%M")
    update_date = _parsed.strftime("%Y-%m-%d")
except Exception:
    update_hour = _update_raw
    update_date = ""

html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ChinaBound Travel · 运营监控中心</title>
<style>
:root {{
  --bg:#070b14; --panel:#0d1320; --panel2:#111827; --border:#1e293b; --border2:#263548;
  --text:#e2e8f0; --text2:#94a3b8; --text3:#64748b; --text4:#475569;
  --accent:#00d4ff; --accent-dim:#00d4ff22;
  --green:#22c55e; --yellow:#f59e0b; --red:#ef4444; --blue:#3b82f6; --purple:#a78bfa;
}}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
  background:var(--bg);
  color:var(--text);
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif;
  font-size:13px; line-height:1.55;
  background-image:
    radial-gradient(ellipse 80% 50% at 50% -20%, rgba(0,212,255,0.06), transparent),
    linear-gradient(180deg, #070b14 0%, #0a0f1c 100%);
  min-height:100vh;
}}
.container {{ max-width:1440px; margin:0 auto; padding:20px 24px 40px; }}

/* 顶部细条 */
.top-line {{ height:2px; background:linear-gradient(90deg, transparent, var(--accent), transparent); opacity:0.6; margin-bottom:20px; }}

/* Header */
.header {{ display:flex; align-items:center; gap:20px; margin-bottom:24px; flex-wrap:wrap; }}
.brand {{ display:flex; align-items:center; gap:12px; }}
.brand-logo {{
  width:38px; height:38px; border-radius:10px;
  background:linear-gradient(135deg, var(--accent), #0099cc);
  display:flex; align-items:center; justify-content:center;
  font-weight:800; font-size:16px; color:#000; letter-spacing:-1px;
  box-shadow:0 0 20px rgba(0,212,255,0.3);
}}
.brand-text h1 {{ font-size:17px; font-weight:700; color:#f1f5f9; letter-spacing:0.3px; }}
.brand-text p {{ font-size:11px; color:var(--text3); margin-top:1px; }}

.header-pills {{ display:flex; gap:10px; flex-wrap:wrap; margin-left:auto; }}
.pill {{
  display:inline-flex; align-items:center; gap:7px;
  padding:6px 14px; border-radius:8px; font-size:12px; font-weight:600;
  background:var(--panel); border:1px solid var(--border);
}}
.pill .dot {{ width:7px; height:7px; border-radius:50%; }}
.pill .dot.live {{ animation:blink 2s infinite; }}
@keyframes blink {{ 0%,100%{{opacity:1;}} 50%{{opacity:0.35;}} }}
.pill-green {{ color:var(--green); border-color:rgba(34,197,94,0.25); background:rgba(34,197,94,0.06); }}
.pill-blue {{ color:var(--accent); border-color:rgba(0,212,255,0.25); background:rgba(0,212,255,0.06); }}
.pill-yellow {{ color:var(--yellow); border-color:rgba(245,158,11,0.25); background:rgba(245,158,11,0.06); }}
.pill-red {{ color:var(--red); border-color:rgba(239,68,68,0.25); background:rgba(239,68,68,0.06); }}

.update-time {{ font-size:11px; color:var(--text3); text-align:right; }}
.update-time strong {{ color:var(--text2); font-weight:600; }}

/* KPI 网格 */
.kpi-grid {{ display:grid; grid-template-columns:repeat(5,1fr); gap:12px; margin-bottom:24px; }}
@media(max-width:1100px) {{ .kpi-grid {{ grid-template-columns:repeat(3,1fr); }} }}
@media(max-width:700px) {{ .kpi-grid {{ grid-template-columns:repeat(2,1fr); }} }}
.kpi {{
  background:var(--panel); border:1px solid var(--border); border-radius:10px;
  padding:16px 18px; position:relative; overflow:hidden;
  transition:border-color 0.2s, transform 0.15s;
}}
.kpi:hover {{ border-color:var(--border2); transform:translateY(-1px); }}
.kpi::before {{ content:''; position:absolute; left:0; top:0; bottom:0; width:3px; }}
.kpi.k1::before {{ background:var(--accent); }}
.kpi.k2::before {{ background:var(--blue); }}
.kpi.k3::before {{ background:var(--purple); }}
.kpi.k4::before {{ background:var(--yellow); }}
.kpi.k5::before {{ background:var(--green); }}
.kpi-label {{ font-size:11px; color:var(--text3); text-transform:uppercase; letter-spacing:0.6px; font-weight:600; margin-bottom:8px; }}
.kpi-value {{ font-size:28px; font-weight:800; color:#f8fafc; line-height:1.1; font-variant-numeric:tabular-nums; }}
.kpi-sub {{ font-size:11px; color:var(--text3); margin-top:6px; }}

/* 区块 */
.section {{ margin-bottom:24px; }}
.section-head {{ display:flex; align-items:center; gap:10px; margin-bottom:14px; }}
.section-num {{
  width:22px; height:22px; border-radius:6px;
  background:var(--accent-dim); color:var(--accent);
  display:flex; align-items:center; justify-content:center;
  font-size:11px; font-weight:700;
}}
.section-title {{ font-size:14px; font-weight:700; color:#f1f5f9; letter-spacing:0.3px; }}
.section-meta {{ font-size:11px; color:var(--text3); margin-left:auto; }}

/* 两列 */
.two-col {{ display:grid; grid-template-columns:1.15fr 1fr; gap:24px; }}
@media(max-width:1000px) {{ .two-col {{ grid-template-columns:1fr; }} }}

/* Workflow 分类 */
.wf-cat {{
  background:var(--panel); border:1px solid var(--border); border-radius:10px;
  padding:14px 16px; margin-bottom:10px;
}}
.wf-cat-head {{ display:flex; align-items:center; justify-content:space-between; margin-bottom:10px; }}
.wf-cat-title {{ font-size:12px; font-weight:700; color:var(--text2); letter-spacing:0.3px; }}
.wf-cat-count {{ font-size:11px; font-weight:600; }}
.wf-list {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(260px,1fr)); gap:2px; }}
.wf-item {{
  display:flex; align-items:center; gap:8px; padding:5px 8px;
  font-size:11.5px; border-radius:5px; cursor:default;
  transition:background 0.15s;
}}
.wf-item:hover {{ background:var(--panel2); }}
.wf-dot {{ width:7px; height:7px; border-radius:50%; flex-shrink:0; }}
.wf-name {{ color:var(--text2); flex:1; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.wf-time {{ color:var(--text4); font-size:10px; font-variant-numeric:tabular-nums; }}
.wf-freq {{ font-size:9px; color:var(--accent); background:rgba(0,212,255,0.1); padding:1px 5px; border-radius:3px; margin-left:4px; flex-shrink:0; }}

/* Agent 卡片 */
.agent-grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(190px,1fr)); gap:10px; }}
.agent-card {{
  background:var(--panel); border:1px solid var(--border); border-radius:10px;
  padding:12px 14px; transition:border-color 0.2s;
}}
.agent-card:hover {{ border-color:var(--border2); }}
.agent-top {{ display:flex; align-items:center; gap:7px; margin-bottom:6px; }}
.agent-dot {{ width:7px; height:7px; border-radius:50%; }}
.agent-dot.dot-live {{ animation:blink 2.5s infinite; }}
.agent-name {{ font-size:12px; font-weight:700; color:#e2e8f0; }}
.agent-status {{ font-size:11px; font-weight:600; margin-bottom:4px; }}
.agent-meta {{ font-size:10px; color:var(--text3); }}

/* 闭环标签 */
.loop-bar {{ display:flex; gap:6px; flex-wrap:wrap; margin-top:14px; }}
.loop-tag {{
  padding:4px 10px; border-radius:6px; font-size:10.5px; font-weight:600;
  background:var(--panel2); color:var(--text2); border:1px solid var(--border);
}}
.loop-tag.active {{ color:var(--accent); border-color:rgba(0,212,255,0.3); background:rgba(0,212,255,0.06); }}

/* 实验 */
.exp-grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(230px,1fr)); gap:10px; }}
.exp-card {{
  background:var(--panel); border:1px solid var(--border); border-radius:10px;
  padding:12px 14px; transition:border-color 0.2s;
}}
.exp-card:hover {{ border-color:var(--border2); }}
.exp-top {{ display:flex; align-items:center; justify-content:space-between; margin-bottom:6px; }}
.exp-id {{ font-size:11px; font-weight:800; color:var(--accent); letter-spacing:0.5px; }}
.exp-badge {{ font-size:9.5px; font-weight:700; padding:2px 7px; border-radius:4px; text-transform:uppercase; letter-spacing:0.5px; }}
.exp-name {{ font-size:12px; color:var(--text); margin-bottom:6px; line-height:1.4; }}
.exp-meta {{ font-size:10px; color:var(--text3); }}

/* 数据源 */
.ds-grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(130px,1fr)); gap:8px; }}
.ds-item {{
  display:flex; align-items:center; gap:8px;
  background:var(--panel); border:1px solid var(--border); border-radius:8px;
  padding:9px 12px; font-size:12px; font-weight:600; color:var(--text2);
}}
.ds-dot {{ width:8px; height:8px; border-radius:50%; flex-shrink:0; }}

/* 底部 */
.footer {{
  text-align:center; font-size:11px; color:var(--text4);
  padding:24px 0 8px; border-top:1px solid var(--border); margin-top:32px;
}}
.footer span {{ color:var(--text3); }}
</style>
</head>
<body>
<div class="top-line"></div>
<div class="container">

  <!-- Header -->
  <div class="header">
    <div class="brand">
      <div class="brand-logo">CB</div>
      <div class="brand-text">
        <h1>ChinaBound Travel · 运营监控中心</h1>
        <p>chinaboundtravel.com · 自动化节点 & AI Agent 实时状态</p>
      </div>
    </div>
    <div class="header-pills">
      <div class="pill pill-green">
        <span class="dot live" style="background:{site_color}"></span>
        网站 {site.get("status","?")} · {site.get("response_ms",0)}ms
      </div>
      <div class="pill pill-blue">
        <span class="dot live" style="background:{overall_color}"></span>
        AI Agent {overall} ({healthy_agents}/7)
      </div>
      <div class="pill {'pill-red' if kill_active else 'pill-green'}">
        <span class="dot" style="background:{kill_color}"></span>
        Kill Switch {"已激活" if kill_active else "未激活"}
      </div>
      <div class="update-time">
        更新于 <strong>{update_hour}</strong><br>
        {update_date} · 每30分钟 · 每日9:00-次日2:00
      </div>
    </div>
  </div>

  <!-- KPI -->
  <div class="kpi-grid">
    <div class="kpi k1">
      <div class="kpi-label">访客 · 昨日</div>
      <div class="kpi-value">{ga4.get("visitors","-")}</div>
      <div class="kpi-sub">{ga4.get("sessions",0)} 会话 · {ga4.get("pageviews",0)} 浏览 · {ga4.get("date","")}</div>
    </div>
    <div class="kpi k2">
      <div class="kpi-label">GSC 曝光 · 昨日</div>
      <div class="kpi-value">{gsc.get("impressions","-")}</div>
      <div class="kpi-sub">{gsc.get("clicks",0)} 点击 · CTR {gsc.get("ctr",0)}% · {gsc.get("date","")}</div>
    </div>
    <div class="kpi k3">
      <div class="kpi-label">已发布文章</div>
      <div class="kpi-value">{content.get("total_articles","-")}</div>
      <div class="kpi-sub">{content.get("with_affiliate",0)} 篇含联盟链接 · 平均 {content.get("avg_word_count",0)} 字</div>
    </div>
    <div class="kpi k4">
      <div class="kpi-label">实验在跑</div>
      <div class="kpi-value">{running_exp}</div>
      <div class="kpi-sub">{waiting_exp} 待重爬 · {pending_exp} 待启动</div>
    </div>
    <div class="kpi k5">
      <div class="kpi-label">Workflow 成功率</div>
      <div class="kpi-value">{round(ok_wf/active_wf*100) if active_wf else 0}%</div>
      <div class="kpi-sub">{ok_wf}成功 · {fail_wf}失败 · {noruns_wf}未运行</div>
    </div>
  </div>

  <!-- 主体 -->
  <div class="two-col">
    <!-- 左列 -->
    <div>
      <div class="section">
        <div class="section-head">
          <span class="section-num">01</span>
          <span class="section-title">自动化节点闭环</span>
          <span class="section-meta">{total_wf} workflows · {ok_wf}成功 · {fail_wf}失败 · {noruns_wf}未运行{f' · {skipped_wf}跳过' if skipped_wf else ''}</span>
        </div>
        {wf_cats_html}
      </div>
    </div>

    <!-- 右列 -->
    <div>
      <div class="section">
        <div class="section-head">
          <span class="section-num">02</span>
          <span class="section-title">AI Agent 工作状态</span>
          <span class="section-meta">跨Agent学习: {data["agents"].get("cross_agent_learning","?")}</span>
        </div>
        <div class="agent-grid">{agents_html}</div>
        <div class="loop-bar">
          <span class="loop-tag active">SEO闭环</span>
          <span class="loop-tag active">内容闭环</span>
          <span class="loop-tag active">社媒闭环</span>
          <span class="loop-tag active">转化闭环</span>
          <span class="loop-tag">收入闭环</span>
          <span class="loop-tag active">用户闭环</span>
          <span class="loop-tag active">跨Agent学习</span>
        </div>
      </div>

      <div class="section">
        <div class="section-head">
          <span class="section-num">03</span>
          <span class="section-title">实验监控</span>
          <span class="section-meta">评审 Gate · 2026-09-13</span>
        </div>
        <div class="exp-grid">{exp_html}</div>
      </div>

      <div class="section">
        <div class="section-head">
          <span class="section-num">04</span>
          <span class="section-title">数据源健康</span>
          <span class="section-meta">{sum(1 for ds in data["data_sources"] if ds.get("configured"))}/{len(data["data_sources"])} 已配置</span>
        </div>
        <div class="ds-grid">{ds_html}</div>
      </div>
    </div>
  </div>

  <div class="footer">
    ChinaBound Travel Ops Dashboard · 数据来源 <span>GitHub Actions · GA4 · GSC · 本地报告</span> · 生成于 {data["generated_at"]} · 每小时自动刷新
  </div>
</div>
</body>
</html>'''

(ROOT / "index.html").write_text(html, encoding="utf-8")
print(f"✅ index.html generated: {len(html)} bytes")
print(f"   Workflow categories: {list(categories.keys())}")
print(f"   Agents: {healthy_agents}/7 healthy")
print(f"   Experiments: {len(data['experiments'])}")
