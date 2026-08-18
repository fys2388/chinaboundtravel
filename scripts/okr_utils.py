# -*- coding: utf-8 -*-
"""
okr_utils.py - 统一 OKR 目标与进度复盘工具
供 日报/周报/月报/季报/年报 调用，实现"计划-执行-复盘"闭环：
  1. build_okr_section: 当期 OKR 关键结果进度看板
  2. review_previous_plan: 读取上期计划快照，用本期真实数据判定完成度
  3. save_snapshot: 保存本期计划+KR 快照（CI 中由 workflow 提交回 git，支持跨期复盘）
"""
import json
from datetime import datetime, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
BLOG_ROOT = SCRIPT_DIR.parent
OKR_FILE = BLOG_ROOT / "config" / "okr.json"
PROGRESS_DIR = BLOG_ROOT / "reports" / "okr_progress"

# 各报表 data 字段别名 → 统一 KR 数据源
KR_ALIASES = {
    "ga4_users": ["visitors", "week_users", "month_users", "quarter_users", "year_users", "active_users"],
    "content_new": ["new_posts", "weekly_new_posts", "monthly_new_posts", "quarter_new_posts", "year_new_posts"],
    "content_total": ["total_posts"],
    "gsc_impressions": ["gsc_impressions"],
    "tp_revenue": ["tp_revenue", "week_revenue", "month_revenue", "quarter_revenue", "year_revenue"],
    "ml_total": ["ml_total_subscribers", "total_subscribers"],
}


def load_okr() -> dict:
    """读取 config/okr.json"""
    if not OKR_FILE.exists():
        print("   ⚠️ OKR 配置文件不存在: " + str(OKR_FILE))
        return None
    try:
        return json.loads(OKR_FILE.read_text(encoding="utf-8-sig"))
    except Exception as e:
        print(f"   ⚠️ OKR 配置解析失败: {e}")
        return None


def current_quarter(date=None) -> int:
    """返回当前季度 1-4"""
    d = date or datetime.now()
    return (d.month - 1) // 3 + 1


def quarter_range(year: int, quarter: int):
    """返回季度起止日期 (start, end)"""
    start_month = (quarter - 1) * 3 + 1
    start = datetime(year, start_month, 1)
    end = datetime(year + 1, 1, 1) if quarter == 4 else datetime(year, start_month + 3, 1)
    return start.strftime("%Y-%m-%d"), (end - timedelta(days=1)).strftime("%Y-%m-%d")


def pick_quarter_krs(okr: dict, quarter: int) -> list:
    """取指定季度 KR 集合，缺省回退年度 KR"""
    for item in okr.get("quarters", []):
        if item.get("q") == quarter:
            return item.get("krs", []) or okr.get("annual", {}).get("krs", [])
    return okr.get("annual", {}).get("krs", [])


def extract_kr(data: dict, source: str) -> float:
    """从报表数据中提取 KR 实际值（兼容各报表字段别名）"""
    for key in KR_ALIASES.get(source, []):
        v = data.get(key)
        if v not in (None, "", "N/A"):
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
    return 0.0


def _target_for(kr: dict, scope: str) -> float:
    """按报表周期取 KR 目标：显式 targets 优先，缺省按月度目标推导（daily=月/30, weekly=月/4.3）"""
    base = float(kr.get("target", 0) or 0)
    targets = kr.get("targets") or {}
    monthly = float(targets.get("monthly", base))
    if scope == "monthly":
        return monthly
    if scope == "quarterly":
        return float(targets.get("quarterly", monthly * 3))
    if scope == "yearly":
        return float(targets.get("yearly", monthly * 12))
    if scope == "weekly":
        return float(targets.get("weekly", max(1, round(monthly / 4.3))))
    if scope == "daily":
        return float(targets.get("daily", max(1, round(monthly / 30))))
    return base


def build_okr_progress(data: dict, scope: str, report_date=None) -> list:
    """生成当期 OKR 关键结果进度列表（供待办生成与复盘使用）。

    返回 [{"name", "current", "target", "progress", "icon", "unit"}]；
    数值口径与 build_okr_section 完全一致。
    """
    okr = load_okr()
    if not okr:
        return []
    now = datetime.now()
    d = report_date or now

    if scope == "yearly":
        krs = okr.get("annual", {}).get("krs", [])
    elif scope == "quarterly":
        krs = pick_quarter_krs(okr, current_quarter(d))
    else:
        krs = pick_quarter_krs(okr, current_quarter(now))

    # 按周期统一 KR 口径名称（日/周/月/季/年对应各自数值口径，避免"月xxx"名称配其它周期数值）
    period_names = {
        "daily": "日", "weekly": "周", "monthly": "月", "quarterly": "季度", "yearly": "年度",
    }
    pname = period_names.get(scope, "月")
    scope_name_map = {
        "月访问用户": f"{pname}访问用户",
        "季度新增文章": f"{pname}新增文章",
        "年度新增文章": f"{pname}新增文章",
        "月搜索曝光": f"{pname}搜索曝光",
        "月联盟佣金": f"{pname}联盟佣金",
    }
    rows = []
    for kr in krs:
        current = extract_kr(data, kr.get("source", ""))
        target = _target_for(kr, scope)
        progress = min(round(current / target * 100), 100) if target > 0 else 0
        icon = "✅" if progress >= 100 else "🟡" if progress >= 50 else "🔴" if progress == 0 else "🟠"
        unit = kr.get("unit", "")
        name = scope_name_map.get(kr.get("name", ""), kr.get("name", kr.get("id", "")))
        rows.append({
            "name": name,
            "current": current,
            "target": target,
            "progress": progress,
            "icon": icon,
            "unit": unit,
        })
    return rows


def build_okr_section(data: dict, scope: str, report_date=None) -> str:
    """生成 OKR 进度看板 markdown；scope: daily/weekly/monthly/quarterly/yearly
    report_date: 季报/年报传入报告期最后一天，用于展示"上季度/上年度"达成情况；
                 日报/周报/月报省略则展示当前季度 OKR 进度。
    """
    okr = load_okr()
    if not okr:
        return ""
    now = datetime.now()
    year = okr.get("year", now.year)
    d = report_date or now

    if scope == "yearly":
        title = f"🎯 {d.year} 年度 OKR 达成复盘"
        period_desc = f"{d.year}全年"
    elif scope == "quarterly":
        q = current_quarter(d)
        start, end = quarter_range(year, q)
        title = f"🎯 {year}年Q{q} OKR 达成复盘（{start} ~ {end}）"
        period_desc = f"{year}年Q{q}"
    elif scope == "weekly":
        q = current_quarter(now)
        start, end = quarter_range(year, q)
        title = f"🎯 本周 OKR 进度（Q{q} 目标折算）"
        period_desc = f"{year}年Q{q}"
    elif scope == "monthly":
        q = current_quarter(now)
        start, end = quarter_range(year, q)
        title = f"🎯 本月 OKR 进度（Q{q} 目标）"
        period_desc = f"{year}年Q{q}"
    else:
        q = current_quarter(now)
        start, end = quarter_range(year, q)
        title = f"🎯 今日 OKR 速览（Q{q} 目标折算）"
        period_desc = f"{year}年Q{q}"

    rows = build_okr_progress(data, scope, report_date)
    if not rows:
        return ""
    header = f"""---
## {title}
| 关键结果 | 当前 | 目标 | 进度 | 状态 |
| :--- | :--- | :--- | :--- | :--- |
"""
    return header + "\n".join(
        f"| {r['name']} | {r['current']:g}{r['unit']} | {r['target']:g}{r['unit']} | {r['progress']}% | {r['icon']} |"
        for r in rows
    )


def _plan_judge(item: dict, data: dict) -> str:
    """按计划项判定完成状态：
    1) 含 kr_id：用本期真实数据 vs 计划目标判定
    2) 含关键词规则：按数据启发式判定
    3) 兜底：待确认
    """
    kr_id = item.get("kr_id")
    if kr_id:
        source_map = {kr["id"]: kr for kr in _all_krs()}
        kr = source_map.get(kr_id)
        if kr:
            current = extract_kr(data, kr.get("source", ""))
            target = float(item.get("target", kr.get("target", 0)) or 0)
            if target > 0:
                ratio = current / target
                if ratio >= 1:
                    return "✅ 已完成"
                if ratio >= 0.5:
                    return "🟡 进行中"
                if current > 0:
                    return "🟠 起步中"
                return "❌ 未启动"
    # 关键词启发式（与既有周报复盘规则对齐）
    task = item.get("task", "")
    weekly_new = data.get("weekly_new_posts") or data.get("new_posts", 0)
    month_new = data.get("monthly_new_posts", 0)
    if "发布" in task and "文章" in task:
        got = month_new if "月" in item.get("period", "") else weekly_new
        if got >= 3:
            return "✅ 已完成"
        return "🟡 进行中" if got > 0 else "❌ 未启动"
    if "索引" in task or "GSC" in task:
        gsc = data.get("gsc_impressions", 0)
        if gsc > 0:
            return "✅ 已完成"
        return "🟡 进行中" if data.get("gsc_data", {}).get("status") == "authorized" else "❌ 未启动"
    return "🟡 待确认"


def _all_krs() -> list:
    """汇总所有 KR 定义（年度+季度）"""
    okr = load_okr()
    if not okr:
        return []
    krs = list(okr.get("annual", {}).get("krs", []))
    for item in okr.get("quarters", []):
        for kr in item.get("krs", []):
            if kr.get("id") not in [k.get("id") for k in krs]:
                krs.append(kr)
    return krs


def review_previous_plan(prev_snapshot: dict, data: dict) -> list:
    """复盘上期计划：读取快照 plan，用本期数据判定完成度"""
    plan = (prev_snapshot or {}).get("plan", [])
    review = []
    for item in plan:
        task = item.get("task", "")
        status = _plan_judge(item, data)
        priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(item.get("priority", "medium"), "⚪")
        review.append({"task": task, "priority": item.get("priority", "medium"),
                       "icon": priority_icon, "status": status, "period": item.get("period", "-")})
    return review


def save_snapshot(report_type: str, period_key: str, plan: list, data: dict) -> str:
    """保存本期快照（计划 + 关键KR值），返回文件路径"""
    try:
        PROGRESS_DIR.mkdir(parents=True, exist_ok=True)
        okr = load_okr()
        krs = _all_krs() if okr else []
        snap = {
            "report_type": report_type,
            "period": period_key,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "plan": plan,
            "krs": {kr["id"]: extract_kr(data, kr.get("source", "")) for kr in krs},
        }
        path = PROGRESS_DIR / f"{report_type}_{period_key}.json"
        path.write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"   ✅ OKR 快照已保存: {path}")
        return str(path)
    except Exception as e:
        print(f"   ⚠️ OKR 快照保存失败: {e}")
        return ""


def load_snapshot(report_type: str, period_key: str) -> dict:
    """读取指定周期快照（用于复盘）"""
    path = PROGRESS_DIR / f"{report_type}_{period_key}.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"   ⚠️ OKR 快照加载失败: {e}")
    return {}


def period_key(scope: str, date=None) -> str:
    """生成周期标识：daily=YYYY-MM-DD / weekly=YYYY-Www / monthly=YYYY-MM / quarterly=YYYY-Qq / yearly=YYYY"""
    d = date or datetime.now()
    if scope == "daily":
        return d.strftime("%Y-%m-%d")
    if scope == "weekly":
        iso = d.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"
    if scope == "monthly":
        return d.strftime("%Y-%m")
    if scope == "quarterly":
        return f"{d.year}-Q{current_quarter(d)}"
    return str(d.year)