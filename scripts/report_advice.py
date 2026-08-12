# -*- coding: utf-8 -*-
"""
report_advice.py - 报表自动运营建议生成器
基于各报表真实数据 + 精准规则，自动产出可执行运营建议（无需人工配置）
规则口径：实事求是，问题→动作，每条一行
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")

# 各报表周期 → 数据字段别名（data.get 多别名兜底）
SCOPE_FIELDS = {
    "daily": {
        "users": ["visitors"], "bounce": ["bounce_rate"], "duration": ["avg_duration"],
        "gsc": ["gsc_impressions"], "tp_clicks": ["tp_clicks"], "tp_orders": ["tp_bookings"],
        "revenue": ["tp_revenue"], "email": ["ml_total_subscribers", "total_subscribers"],
        "new_content": ["new_posts"], "total_content": ["total_posts"],
        "channels": ["top_channels"], "trend": ["users_trend"],
    },
    "weekly": {
        "users": ["week_users"], "bounce": ["week_bounce"], "duration": ["week_avg_duration"],
        "gsc": ["gsc_impressions"], "tp_clicks": ["tp_clicks"], "tp_orders": ["tp_bookings"],
        "revenue": ["week_revenue", "tp_revenue"], "email": ["total_subscribers", "ml_total_subscribers"],
        "new_content": ["weekly_new_posts", "new_posts"], "total_content": ["total_posts"],
        "channels": ["top_channels"], "trend": ["users_trend"],
    },
    "monthly": {
        "users": ["month_users"], "bounce": ["month_bounce"], "duration": ["month_avg_duration"],
        "gsc": ["gsc_impressions"], "tp_clicks": ["tp_clicks"], "tp_orders": ["tp_bookings"],
        "revenue": ["month_revenue", "tp_revenue"], "email": ["total_subscribers", "ml_total_subscribers"],
        "new_content": ["monthly_new_posts", "new_posts"], "total_content": ["total_posts"],
        "channels": ["top_channels"], "trend": ["users_trend"],
    },
    "quarterly": {
        "users": ["quarter_users"], "bounce": ["quarter_bounce"], "duration": ["quarter_avg_duration"],
        "gsc": ["gsc_impressions"], "tp_clicks": ["tp_clicks"], "tp_orders": ["tp_bookings"],
        "revenue": ["quarter_revenue", "tp_revenue"], "email": ["ml_total_subscribers", "total_subscribers"],
        "new_content": ["quarter_new_posts", "new_posts"], "total_content": ["total_posts"],
        "channels": ["top_channels"], "trend": ["users_change"],
    },
    "yearly": {
        "users": ["year_users"], "bounce": ["year_bounce"], "duration": ["year_avg_duration"],
        "gsc": ["gsc_impressions"], "tp_clicks": ["tp_clicks"], "tp_orders": ["tp_bookings"],
        "revenue": ["year_revenue", "tp_revenue"], "email": ["ml_total_subscribers", "total_subscribers"],
        "new_content": ["year_new_posts", "new_posts"], "total_content": ["total_posts"],
        "channels": ["top_channels"], "trend": ["users_change"],
    },
}


def _get(data: dict, keys) -> float:
    """取第一个非 None 数值"""
    for k in keys:
        v = data.get(k)
        if v not in (None, "", "N/A", "未接入"):
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
    return 0.0


# 渠道精确匹配（避免 Organic Social 被误判为自然搜索）
_CHANNEL_MATCH = {
    "organic": lambda n: n.lower().startswith("organic search"),
    "social": lambda n: n.lower().startswith("organic social") or n.lower() in ("social",),
}


def _channel_users(data: dict, kind: str) -> tuple:
    """返回指定渠道的用户数与渠道合计（kind: organic/social）"""
    chans = data.get("top_channels", []) or data.get("channels", []) or []
    total = 0
    hit = 0
    matcher = _CHANNEL_MATCH.get(kind)
    for c in chans:
        name = str(c.get("channel", ""))
        u = float(c.get("users", 0) or 0)
        total += u
        if matcher and matcher(name):
            hit += u
    return hit, total


def generate_advice(data: dict, scope: str) -> list:
    """生成精准运营建议列表：[{icon, title, detail}]"""
    f = SCOPE_FIELDS.get(scope, SCOPE_FIELDS["daily"])
    users = _get(data, f["users"])
    bounce = _get(data, f["bounce"])
    duration = _get(data, f["duration"])
    gsc = _get(data, f["gsc"])
    tp_clicks = _get(data, f["tp_clicks"])
    tp_orders = _get(data, f["tp_orders"])
    revenue = _get(data, f["revenue"])
    email = _get(data, f["email"])
    new_content = _get(data, f["new_content"])
    total_content = _get(data, f["total_content"])
    period = {"daily": "今日", "weekly": "本周", "monthly": "本月",
              "quarterly": "本季", "yearly": "本年"}[scope]

    advice = []

    # 1) 自然搜索占比（核心瓶颈）
    organic, total = _channel_users(data, "organic")
    if users > 0:
        ratio = organic / users * 100
        if ratio < 10:
            advice.append({"icon": "🔴", "title": f"自然搜索仅 {organic:g}/{users:g} 人（{ratio:.0f}%）",
                           "detail": "搜索基本盘未起量：已收录页排名靠后，优化核心页标题/内容密度并加强内链，持续观察曝光"})
        elif ratio < 30:
            advice.append({"icon": "🟡", "title": f"自然搜索占比 {ratio:.0f}%",
                           "detail": "搜索开始起量，继续补收录与内链，把有曝光无点击的页面标题改到 60 字符内"})
    elif users == 0:
        advice.append({"icon": "🔴", "title": "本期无流量",
                       "detail": "检查社媒自动发布是否正常（Buffer/Feishu），并确认站点 200"})

    # 2) 社媒流量质量
    social, _ = _channel_users(data, "social")
    if users > 0 and social / max(users, 1) > 0.5 and bounce > 70:
        advice.append({"icon": "🟡", "title": f"社媒引流 {social:g}/{users:g} 人但跳出 {bounce:.0f}%",
                       "detail": "落地页承接差：帖子标题/首图需与页面首屏对齐，文首加目录+核心结论，文末加订阅CTA"})

    # 3) 跳出率/时长
    if users >= 5 and bounce > 80:
        advice.append({"icon": "🟡", "title": f"跳出率 {bounce:.0f}% 偏高",
                       "detail": "首屏未抓住用户：检查页面加载速度、首屏内容与访客预期匹配度"})
    if users >= 5 and duration > 0 and duration < 30:
        advice.append({"icon": "🟡", "title": f"平均时长 {duration:.0f} 秒",
                       "detail": "内容未形成阅读：强化文章开头钩子与图文节奏，优先优化高流量页"})

    # 4) 变现
    if tp_clicks > 0 and tp_orders == 0:
        advice.append({"icon": "🟡", "title": f"联盟 {tp_clicks:.0f} 次点击 / 0 转化",
                       "detail": "链路已被触达：确认点击来自哪个联盟位，把高流量页联盟入口提到首屏下方，补充信任元素"})
    elif tp_clicks == 0 and users >= 10:
        advice.append({"icon": "🟠", "title": "高流量但联盟零点击",
                       "detail": "联盟入口不可见：在热门文章首屏下方加入 Travelpayouts Drive / 对比表"})

    # 5) 订阅
    if email == 0:
        advice.append({"icon": "🟠", "title": "邮件订阅为 0",
                       "detail": "上线 Lead Magnet（7天中国行程模板）并在文章中部/底部放订阅框"})

    # 6) 内容
    if new_content > 0:
        advice.append({"icon": "🟢", "title": f"{period}新增 {new_content:g} 篇",
                       "detail": "内容产出正常，保持节奏；优先放大已验证流量题材（144小时过境免签等）"})
    if total_content > 0 and total_content < 50:
        advice.append({"icon": "🟡", "title": f"站点文章 {total_content:g} 篇",
                       "detail": "内容基数偏低：核实去重/归档流程是否误删，目标季度新增 ≥20 篇"})

    # 7) GSC 曝光为 0（新站单日波动正常，核心页通常已收录）
    if gsc == 0:
        advice.append({"icon": "🟠", "title": "今日无搜索曝光（新站正常波动）",
                       "detail": "核心页已收录但排名未起量：优先优化核心页标题/首段/内链，持续提交新页 sitemap"})

    # 8) 趋势回落
    trend = str(data.get(f["trend"][0], "")) if f["trend"] else ""
    if "📉" in trend:
        advice.append({"icon": "🟠", "title": f"{period}流量环比回落（{trend}）",
                       "detail": "排查渠道衰减：社媒发布频次、Direct 是否含自测水分"})

    # 去重 + 限制 6 条，优先级 icon 排序
    seen, out = set(), []
    order = {"🔴": 0, "🟡": 1, "🟠": 2, "🟢": 3}
    for a in advice:
        key = a["title"]
        if key not in seen:
            seen.add(key)
            out.append(a)
    out.sort(key=lambda x: order.get(x["icon"], 9))
    return out[:6]


def advice_section(data: dict, scope: str) -> str:
    """生成 markdown 板块（无建议时返回空）"""
    items = generate_advice(data, scope)
    if not items:
        return ""
    lines = "\n".join([f"- {a['icon']} **{a['title']}**：{a['detail']}" for a in items])
    return f"---\n## 📌 运营建议（自动生成）\n{lines}"