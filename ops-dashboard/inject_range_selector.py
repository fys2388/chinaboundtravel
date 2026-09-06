#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
后处理脚本：在生成的 index.html 中注入时间范围选择器
在 build.py 之后运行
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
INDEX_HTML = ROOT / "index.html"
DASHBOARD_DATA = ROOT / "dashboard_data.json"


def inject_range_selector():
    """在 index.html 中注入时间范围选择器和 JS 代码"""
    if not INDEX_HTML.exists():
        print("❌ index.html 不存在")
        return False

    html = INDEX_HTML.read_text(encoding="utf-8")

    # 读取多时间范围数据
    ranges_data = {}
    if DASHBOARD_DATA.exists():
        data = json.loads(DASHBOARD_DATA.read_text(encoding="utf-8"))
        ga4 = data.get("metrics", {}).get("ga4_daily", {})
        gsc = data.get("metrics", {}).get("gsc_daily", {})
        ranges_data = {
            "ga4": ga4.get("ranges", {}),
            "gsc": gsc.get("ranges", {}),
            "ga4_daily": ga4.get("daily", []),
            "gsc_daily": gsc.get("daily", []),
        }

    # 1. 在 KPI 趋势图之前注入时间范围选择器
    selector_html = '''
  <!-- 时间范围选择器 -->
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;flex-wrap:wrap;">
    <span style="font-size:11px;color:var(--text3);text-transform:uppercase;letter-spacing:0.6px;font-weight:600;">时间范围</span>
    <div id="range-selector" style="display:flex;gap:4px;flex-wrap:wrap;">
      <button class="range-btn" data-range="today" style="padding:4px 10px;font-size:11px;border:1px solid var(--border2);background:transparent;color:var(--text3);border-radius:6px;cursor:pointer;">今天</button>
      <button class="range-btn" data-range="yesterday" style="padding:4px 10px;font-size:11px;border:1px solid var(--border2);background:transparent;color:var(--text3);border-radius:6px;cursor:pointer;">昨日</button>
      <button class="range-btn active" data-range="7d" style="padding:4px 10px;font-size:11px;border:1px solid var(--accent);background:var(--accent);color:#fff;border-radius:6px;cursor:pointer;">过去7天</button>
      <button class="range-btn" data-range="30d" style="padding:4px 10px;font-size:11px;border:1px solid var(--border2);background:transparent;color:var(--text3);border-radius:6px;cursor:pointer;">过去30天</button>
      <button class="range-btn" data-range="last_month" style="padding:4px 10px;font-size:11px;border:1px solid var(--border2);background:transparent;color:var(--text3);border-radius:6px;cursor:pointer;">上个月</button>
      <button class="range-btn" data-range="90d" style="padding:4px 10px;font-size:11px;border:1px solid var(--border2);background:transparent;color:var(--text3);border-radius:6px;cursor:pointer;">过去90天</button>
    </div>
  </div>
'''

    # 在 "<!-- KPI 趋势图 -->" 之前插入
    if "<!-- KPI 趋势图 -->" in html:
        html = html.replace("<!-- KPI 趋势图 -->", selector_html + "\n  <!-- KPI 趋势图 -->")
    else:
        # 尝试在 kpi-trend-grid 之前插入
        html = html.replace('<div class="kpi-trend-grid">', selector_html + '\n  <div class="kpi-trend-grid">')

    # 2. 给 KPI 标签和值添加 id
    html = html.replace(
        '<span class="kpi-trend-label">访客 · 近7天</span>',
        '<span class="kpi-trend-label" id="ga4-label">访客 · 过去7天</span>'
    )
    html = html.replace(
        '<span class="kpi-trend-label">GSC 曝光 · 近7天</span>',
        '<span class="kpi-trend-label" id="gsc-label">GSC 曝光 · 过去7天</span>'
    )

    # 给值和子标题添加 id（需要用正则匹配，因为值是动态的）
    # GA4 value: <span class="kpi-trend-value">数字</span> (第一个)
    # GSC value: 第二个
    ga4_value_match = re.search(r'(<div class="kpi-trend t1">.*?<span class="kpi-trend-value">)([^<]+)(</span>)', html, re.DOTALL)
    if ga4_value_match:
        html = html[:ga4_value_match.start(2)] + 'id="ga4-value">' + ga4_value_match.group(2) + html[ga4_value_match.end(2):]
    gsc_value_match = re.search(r'(<div class="kpi-trend t2">.*?<span class="kpi-trend-value">)([^<]+)(</span>)', html, re.DOTALL)
    if gsc_value_match:
        html = html[:gsc_value_match.start(2)] + 'id="gsc-value">' + gsc_value_match.group(2) + html[gsc_value_match.end(2):]

    # 给 sub 添加 id
    ga4_sub_match = re.search(r'(<div class="kpi-trend t1">.*?<span class="kpi-trend-sub">)([^<]+)(</span>)', html, re.DOTALL)
    if ga4_sub_match:
        html = html[:ga4_sub_match.start(2)] + 'id="ga4-sub">' + ga4_sub_match.group(2) + html[ga4_sub_match.end(2):]
    gsc_sub_match = re.search(r'(<div class="kpi-trend t2">.*?<span class="kpi-trend-sub">)([^<]+)(</span>)', html, re.DOTALL)
    if gsc_sub_match:
        html = html[:gsc_sub_match.start(2)] + 'id="gsc-sub">' + gsc_sub_match.group(2) + html[gsc_sub_match.end(2):]

    # 3. 注入 JS 代码（在 </body> 之前）
    ranges_json = json.dumps(ranges_data, ensure_ascii=False)
    js_code = f'''
<script>
(function() {{
  var rangesData = {ranges_json};
  var ga4Ranges = rangesData.ga4 || {{}};
  var gscRanges = rangesData.gsc || {{}};
  var ga4Daily = rangesData.ga4_daily || [];
  var gscDaily = rangesData.gsc_daily || [];

  var rangeLabels = {{
    today: "今天", yesterday: "昨日", "7d": "过去7天",
    "30d": "过去30天", last_month: "上个月", "90d": "过去90天"
  }};
  var rangeDays = {{ today: 1, yesterday: 1, "7d": 7, "30d": 30, last_month: 30, "90d": 90 }};

  function switchRange(range) {{
    // 更新按钮状态
    document.querySelectorAll('.range-btn').forEach(function(btn) {{
      if (btn.dataset.range === range) {{
        btn.style.borderColor = 'var(--accent)';
        btn.style.background = 'var(--accent)';
        btn.style.color = '#fff';
      }} else {{
        btn.style.borderColor = 'var(--border2)';
        btn.style.background = 'transparent';
        btn.style.color = 'var(--text3)';
      }}
    }});

    // 更新 GA4 指标
    var g = ga4Ranges[range] || {{}};
    var ga4Label = document.getElementById('ga4-label');
    var ga4Value = document.getElementById('ga4-value');
    var ga4Sub = document.getElementById('ga4-sub');
    if (ga4Label) ga4Label.textContent = '访客 · ' + (rangeLabels[range] || range);
    if (ga4Value) ga4Value.textContent = g.visitors || 0;
    if (ga4Sub) ga4Sub.textContent = (g.sessions || 0) + ' 会话 · ' + (g.pageviews || 0) + ' 浏览 · ' + (g.date_range || '');

    // 更新 GSC 指标
    var s = gscRanges[range] || {{}};
    var gscLabel = document.getElementById('gsc-label');
    var gscValue = document.getElementById('gsc-value');
    var gscSub = document.getElementById('gsc-sub');
    if (gscLabel) gscLabel.textContent = 'GSC 曝光 · ' + (rangeLabels[range] || range);
    if (gscValue) gscValue.textContent = s.impressions || 0;
    var ctr = s.clicks && s.impressions ? (s.clicks / s.impressions * 100).toFixed(1) : 0;
    if (gscSub) gscSub.textContent = (s.clicks || 0) + ' 点击 · CTR ' + ctr + '% · ' + (s.date_range || '');

    // 更新趋势图（如果 echarts 实例存在）
    if (window.ga4Chart && ga4Daily.length) {{
      var days = rangeDays[range] || 7;
      var slice = ga4Daily.slice(-days);
      if (range === 'yesterday') slice = ga4Daily.slice(-2, -1);
      window.ga4Chart.setOption({{
        xAxis: {{ data: slice.map(function(d) {{ return d.date; }}) }},
        series: [{{ data: slice.map(function(d) {{ return d.activeUsers || 0; }}) }}]
      }});
    }}
    if (window.gscChart && gscDaily.length) {{
      var days = rangeDays[range] || 7;
      var slice = gscDaily.slice(-days);
      if (range === 'yesterday') slice = gscDaily.slice(-2, -1);
      window.gscChart.setOption({{
        xAxis: {{ data: slice.map(function(d) {{ return d.date; }}) }},
        series: [{{ data: slice.map(function(d) {{ return d.impressions || 0; }}) }}]
      }});
    }}
  }}

  // 绑定按钮事件
  document.querySelectorAll('.range-btn').forEach(function(btn) {{
    btn.addEventListener('click', function() {{
      switchRange(this.dataset.range);
    }});
  }});
}})();
</script>
'''

    # 在 </body> 之前插入
    if "</body>" in html:
        html = html.replace("</body>", js_code + "\n</body>")
    else:
        html += js_code

    # 保存
    INDEX_HTML.write_text(html, encoding="utf-8")
    print("✅ 时间范围选择器已注入 index.html")
    print(f"   GA4 ranges: {list(ga4Ranges.keys()) if 'ga4Ranges' in dir() else 'N/A'}")
    print(f"   GSC ranges: {list(gscRanges.keys()) if 'gscRanges' in dir() else 'N/A'}")
    return True


if __name__ == "__main__":
    inject_range_selector()
