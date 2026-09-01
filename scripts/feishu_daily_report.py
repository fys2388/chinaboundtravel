#!/usr/bin/env python3
"""
feishu_daily_report.py - ChinaBound Travel 飞书每日日报推送
功能：流量、内容、联盟、运维四大核心板块数据推送
版本：v2.0 - 完整版日报模板
"""

import argparse
import os
import sys
import re

# Windows终端编码设置
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

import json
import requests
import hashlib
import hmac
import base64
from datetime import datetime, timedelta
from pathlib import Path

# GA4服务账号认证依赖
try:
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
    HAS_GOOGLE_AUTH = True
except ImportError:
    HAS_GOOGLE_AUTH = False
    print("⚠️ google-auth 未安装，将使用 API Key 方式（可能不可用）")

# ==================== 配置 ====================
SCRIPT_DIR = Path(__file__).parent.resolve()
BLOG_ROOT = SCRIPT_DIR.parent

# OKR 公共工具（进度看板 / 快照）
sys.path.insert(0, str(SCRIPT_DIR))
import okr_utils
import report_advice

# 加载 .env 文件
try:
    from dotenv import load_dotenv
    dotenv_path = BLOG_ROOT / ".env"
    print(f"DEBUG: Loading .env from {dotenv_path}")
    print(f"DEBUG: .env exists: {dotenv_path.exists()}")
    load_dotenv(dotenv_path)
    # 验证加载
    test_key = os.environ.get("GA4_API_KEY", "")
    print(f"DEBUG: GA4_API_KEY after load_dotenv: {'已配置' if test_key else '未配置'}")
    if test_key:
        print(f"DEBUG: GA4_API_KEY length: {len(test_key)}")
except ImportError:
    print("DEBUG: dotenv not installed")

CONTENT_DIR = BLOG_ROOT / "content"
POSTS_DIR = CONTENT_DIR / "posts"
CONFIG_DIR = BLOG_ROOT / "config"

# 飞书配置
FEISHU_WEBHOOK_URL = os.environ.get("FEISHU_WEBHOOK_URL", "")
FEISHU_SECRET = os.environ.get("FEISHU_SECRET", "")

# API配置
TRAVELPAYOUTS_API_TOKEN = os.environ.get("TRAVELPAYOUTS_API_TOKEN", "")
TRAVELPAYOUTS_MARKER = os.environ.get("TRAVELPAYOUTS_MARKER", "730795")
NORDVPN_API_KEY = os.environ.get("NORDVPN_API_KEY", "")
NORDVPN_AFFILIATE_ID = os.environ.get("NORDVPN_AFFILIATE_ID", "")
CLOUDFLARE_API_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN", "")
CLOUDFLARE_ZONE_ID = os.environ.get("CLOUDFLARE_ZONE_ID", "")
# GA4配置
GA4_API_KEY = os.environ.get("GA4_API_KEY", "")
GA4_PROPERTY_ID = os.environ.get("GA4_PROPERTY_ID", "541752321")
GA4_SERVICE_ACCOUNT_JSON = os.environ.get("GA4_SERVICE_ACCOUNT_JSON", "")
GSC_SERVICE_ACCOUNT_JSON = os.environ.get("GSC_SERVICE_ACCOUNT_JSON", "")
# GSC 站点配置：支持 sc-domain: 域属性或 https:// URL 前缀属性，逗号分隔多个候选
GSC_SITE_URL = os.environ.get("GSC_SITE_URL", "sc-domain:chinaboundtravel.com")

# MailerLite 订阅配置
MAILERLITE_API_TOKEN = os.environ.get("MAILERLITE_API_TOKEN", "")

# GitHub 配置
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = "fys2388/chinaboundtravel"


SNAPSHOT_FILE = BLOG_ROOT / "reports" / "management" / "REPORTING_SNAPSHOT.json"


def load_reporting_snapshot() -> dict:
    """读取统一 2.0 KPI 快照（P1-REPORT-03R：飞书消费快照，不重复计算 KPI）。

    返回快照中的缓存回退数据与状态标签；快照缺失/损坏返回 None。
    """
    try:
        if not SNAPSHOT_FILE.exists():
            print("   \u26a0\ufe0f REPORTING_SNAPSHOT.json 不存在，无法回退缓存窗口")
            return None
        snap = json.loads(SNAPSHOT_FILE.read_text(encoding="utf-8"))

        def _find(domain, name):
            for k in snap.get("domains", {}).get(domain, {}).get("kpis", []):
                if k.get("name") == name:
                    return k
            return {}

        gsc_imp = _find("seo_gsc", "gsc_impressions_28d")
        gsc_clk = _find("seo_gsc", "gsc_clicks_28d")
        rev = _find("revenue", "revenue")
        traf_s = _find("traffic", "sessions_28d")
        traf_p = _find("traffic", "pageviews_28d")
        return {
            "as_of": snap.get("as_of"),
            "generated_at": snap.get("generated_at"),
            "low_data_warning": snap.get("low_data_warning"),
            "gsc_impressions_28d": gsc_imp.get("value"),
            "gsc_clicks_28d": gsc_clk.get("value"),
            "gsc_label": gsc_imp.get("data_source_type"),
            "sessions_28d": traf_s.get("value"),
            "pageviews_28d": traf_p.get("value"),
            "revenue_value": rev.get("value"),
            "revenue_status": rev.get("status") or "NOT_AVAILABLE",
            "revenue_source": rev.get("data_source_type"),
        }
    except Exception as e:
        print(f"   \u26a0\ufe0f REPORTING_SNAPSHOT.json 读取失败: {e}")
        return None




def get_drive_status() -> str:
    """P1-GROWTH-28A: Drive 状态字段（日报联盟板块）。
    从 2.0 KPI 快照的 DRIVE-001 实验记录读取；RUNNING/ACTIVE -> 🟢，
    其余状态/缺失/解析失败 -> 🔴（进入当日待办）。"""
    try:
        if not SNAPSHOT_FILE.exists():
            return "🔴 UNKNOWN（REPORTING_SNAPSHOT.json 缺失）"
        snap = json.loads(SNAPSHOT_FILE.read_text(encoding="utf-8"))
        exps = snap.get("domains", {}).get("experiments", {}).get("experiments", [])
        for e in exps:
            if e.get("experiment_id") == "DRIVE-001":
                st = (e.get("status") or "").upper()
                if st in ("RUNNING", "ACTIVE"):
                    return f"🟢 ACTIVE（DRIVE-001 {st}，start {e.get('start_date') or '-'}）"
                return f"🔴 {st}（DRIVE-001 非 RUNNING，进入待办）"
        return "🔴 DRIVE-001 未在快照实验注册表"
    except Exception as exc:
        return f"🔴 快照解析失败：{exc}"


def generate_priority_tasks(okr_data, suggestions):
    """根据 OKR 完成率和自动运营建议生成高优先级待办列表（P0: 告警-待办打通）。

    okr_data: okr_utils.build_okr_progress 输出的关键结果列表
        [{"name", "current", "target", "progress", "icon", "unit"}]
    suggestions: report_advice.generate_advice 输出的建议列表
        [{"icon", "title", "detail"}]

    规则：
      - OKR 完成率 < 50%   -> 自动进入待办，标注 🟠（业务差距；🔴 只留给生产故障/收入断链等）
      - OKR 完成率 50%-80% -> 自动进入待办，标注 🟡
      - 自动运营建议逐条映射为待办项（优先级图标 + 具体动作 + 对应指标）
    返回去重后的待办列表；无异常时返回空列表（由调用方显示"所有正常"）。
    """
    tasks = []

    # 1) OKR 完成率分级（2.0：数据不可用/进度为 0 的固定配额不进入失败待办）
    for kr in okr_data or []:
        if not kr.get("available", True):
            continue
        progress = kr.get("progress")
        if progress is None or int(progress or 0) == 0:
            continue
        progress = int(progress)
        name = kr.get("name", "")
        current = kr.get("current", 0)
        target = kr.get("target", 0)
        unit = kr.get("unit", "")
        if progress < 50:
            tasks.append(f"🟠 {name}：当前 {current:g}{unit} / 目标 {target:g}{unit}（{progress}%），需重点推进")
        elif progress < 80:
            tasks.append(f"🟡 {name}：当前 {current:g}{unit} / 目标 {target:g}{unit}（{progress}%），保持推进")

    # 2) 自动运营建议 -> 待办
    for s in suggestions or []:
        icon = s.get("icon", "🟠")
        title = s.get("title", "")
        detail = s.get("detail", "")
        tasks.append(f"{icon} {title}：{detail}")

    # 3) 去重保序
    seen, out = set(), []
    for t in tasks:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


class FeishuDailyReporter:
    """飞书每日日报推送器"""
    
    def __init__(self):
        self.webhook_url = FEISHU_WEBHOOK_URL
        self.secret = FEISHU_SECRET
        
    def _generate_signature(self, timestamp: str) -> str:
        """生成飞书签名"""
        if not self.secret:
            return ""
        string_to_sign = f"{timestamp}\n{self.secret}"
        hmac_code = hmac.new(
            self.secret.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            hashlib.sha256
        ).digest()
        return base64.b64encode(hmac_code).decode('utf-8')
    
    def send_card_message(self, card_content: dict) -> bool:
        """发送飞书卡片消息"""
        if not self.webhook_url:
            print("⚠️ 飞书 Webhook URL 未配置")
            return False
        
        try:
            timestamp = str(int(datetime.now().timestamp()))
            
            payload = {
                "msg_type": "interactive",
                "card": card_content
            }
            
            if self.secret:
                payload["timestamp"] = timestamp
                payload["sign"] = self._generate_signature(timestamp)
            
            headers = {"Content-Type": "application/json"}
            response = requests.post(
                self.webhook_url,
                headers=headers,
                json=payload,
                timeout=15
            )
            
            print(f"📤 飞书响应状态码: {response.status_code}")
            print(f"📤 飞书响应内容: {response.text[:500]}")
            
            result = response.json()
            if result.get("code") == 0:
                print("✅ 飞书日报推送成功")
                return True
            else:
                print(f"❌ 飞书推送失败: {result.get('msg', 'Unknown error')}")
                return False
                
        except Exception as e:
            print(f"❌ 飞书推送异常: {e}")
            return False
    
    def build_daily_card(self, data: dict) -> dict:
        """构建飞书日报卡片 - 完整增强版"""
        today = datetime.now().strftime("%Y-%m-%d")
        report_date = data.get("report_date", (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"))
        
        # 状态图标
        # 状态图标
        traffic_status = "🟢" if data.get("visitors", 0) > 0 else "⚪"
        content_status = "🟢" if data.get("total_content_issues", 0) == 0 else "🟡"
        tp_available = data.get("tp_available", False)
        nord_available = data.get("nord_available", False)
        # 合计佣金只统计有真实数据的渠道，避免把"未接入"当 0 计入
        total_aff_revenue = 0.0
        total_aff_parts = []
        if tp_available:
            total_aff_revenue += float(data.get("tp_revenue", 0) or 0)
            total_aff_parts.append("Travelpayouts")
        if nord_available:
            total_aff_revenue += float(data.get("nord_revenue", 0) or 0)
            total_aff_parts.append("NordVPN")
        affiliate_status = "🟢" if total_aff_revenue > 0 else ("🟡" if (tp_available or nord_available) else "⚪")
        tp_quality_note = ""
        if tp_available:
            _tp_inits = float(data.get('tp_inits', 0) or 0)
            _tp_clicks = float(data.get('tp_clicks', 0) or 0)
            # 口径标注：TP inits=initiations（触达），非"展示"；触达未全量上报时避免被误读为 0 展示
            inits_display = (f"{_tp_inits:,.0f}" if (_tp_inits > 0 or _tp_clicks == 0)
                             else "未上报（点击>0，勿读作0展示）")
            if _tp_inits == 0 and _tp_clicks > 0:
                tp_quality_note = ("\n> 口径说明：TP 触达(initiations)维度未全量上报，点击为同源有效数据；"
                                   "「未上报」≠ 0 展示")
            tp_display = {"inits": inits_display, "searches": f"{data.get('tp_searches', 0):,}",
                          "clicks": f"{data.get('tp_clicks', 0)}", "bookings": f"{data.get('tp_bookings', 0)}",
                          "revenue": f"${data.get('tp_revenue', 0):.2f}"}
            # P1-GROWTH-28A: 同源口径校准 - 点击率只使用 TP 同源数据 (clicks/inits)
            tp_ctr = f"{_tp_clicks / _tp_inits * 100:.2f}%" if _tp_inits > 0 else "INSUFFICIENT_SAMPLE"
            tp_ctr_note = "同源 clicks/inits"
        else:
            tp_display = {"inits": "未配置", "searches": "未配置", "clicks": "未配置",
                          "bookings": "未配置", "revenue": "未配置"}
            tp_ctr = "未配置"
            tp_ctr_note = ""
        drive_status_line = get_drive_status()
        if nord_available:
            nord_display = {"clicks": f"{data.get('nord_clicks', 0)}", "conversions": f"{data.get('nord_conversions', 0)}",
                            "revenue": f"${data.get('nord_revenue', 0):.2f}"}
        else:
            nord_display = {"clicks": "未接入", "conversions": "未接入", "revenue": "未接入"}
        if total_aff_revenue > 0:
            total_rev_str = f"${total_aff_revenue:.2f}（{' + '.join(total_aff_parts)}）"
        elif tp_available or nord_available:
            # TP/Nord 已接入但昨日无结算订单：显示真实 0，不再用 REVENUE_NOT_AVAILABLE 掩盖
            total_rev_str = f"$0.00（{' + '.join(total_aff_parts) or '已接入渠道'}，已接入无结算订单）"
        else:
            total_rev_str = "REVENUE_NOT_AVAILABLE（无接入渠道）"
        if total_aff_revenue > 0:
            rev_status_line = "✅ 有真实结算佣金"
        elif tp_available or nord_available:
            rev_status_line = "🟡 渠道已接入（LIVE），昨日无结算订单（非故障）"
        else:
            rev_status_line = "REVENUE_NOT_AVAILABLE（无接入渠道，与快照口径一致，非故障）"

        gsc_available = data.get("gsc_data_available", False)
        gsc_has_data = gsc_available and data.get("gsc_impressions", 0) > 0
        # 索引错误为真实 int 且 ==0 才算 🟢；未检测(None)不算；GSC 未授权用 🔴
        search_status = ("🟢" if (gsc_has_data and isinstance(data.get("gsc_errors"), int)
                          and data["gsc_errors"] == 0) else ("🟡" if gsc_available else "🔴"))
        
        # MailerLite 显示：认证失败/未配置时提示，避免把 API 错误当真实 0
        if data.get("ml_available"):
            ml_total_str = f"{data.get('ml_total_subscribers', 0):,} 人"
            ml_new_str = f"{data.get('ml_new_subscribers', 0)} 人"
        else:
            ml_total_str = "未连接（API 认证失败）" if data.get("ml_error") else "未配置"
            ml_new_str = "-"
        
        # ===== 1. 流量总览 =====
        # 格式化会话时长
        avg_dur = data.get("avg_session_duration", 0)
        if avg_dur > 60:
            dur_str = f"{avg_dur // 60}分{avg_dur % 60}秒"
        else:
            dur_str = f"{avg_dur}秒"

        # 低样本：访客 < 10 时环比百分比无统计意义，标注 INSUFFICIENT_SAMPLE
        trend_note = ""
        if (data.get("visitors") or 0) < 10:
            trend_note = "\n（INSUFFICIENT_SAMPLE：访客 < 10，低样本，百分比仅参考）"
        
        # Top 流量页面
        top_pages = data.get("top_pages", [])
        top_pages_lines = ["暂无数据"]
        if top_pages:
            top_pages_lines = [f"{i}. {p['path']} ({p['views']} 次)" for i, p in enumerate(top_pages[:5], 1)]
        top_pages_str = "\n".join(top_pages_lines)
        
        # Top 流量来源渠道
        top_channels = data.get("top_channels", [])
        channel_lines = ["暂无数据"]
        if top_channels:
            channel_lines = [f"{c['channel']}: {c['users']} 人 / {c['sessions']} 会话" for c in top_channels[:5]]
        channel_str = "\n".join(channel_lines)
        
        # Top 国家/地区
        top_countries = data.get("top_countries", [])
        country_lines = ["暂无数据"]
        if top_countries:
            country_lines = [f"{c['country']}: {c['users']} 人" for c in top_countries[:5]]
        country_str = "\n".join(country_lines)
        # GA4 小流量隐私阈值提示：明细合计可能与总数不一致
        consistency_notes = []
        if top_channels and data.get("sessions"):
            ch_s = sum(c.get("sessions", 0) for c in top_channels)
            if ch_s != data.get("sessions"):
                consistency_notes.append(f"渠道会话合计 {ch_s} ≠ 总会话 {data.get('sessions')}")
        if top_channels and data.get("visitors"):
            ch_u = sum(c.get("users", 0) for c in top_channels)
            if ch_u != data.get("visitors"):
                consistency_notes.append(f"渠道用户合计 {ch_u} ≠ 总访客 {data.get('visitors')}")
        if top_pages and data.get("requests"):
            pv = sum(p.get("views", 0) for p in top_pages)
            if pv != data.get("requests"):
                consistency_notes.append(f"Top页面浏览合计 {pv} ≠ 总浏览 {data.get('requests')}")
        consistency_str = ""
        if consistency_notes:
            consistency_str = "\n\n⚠️ 一致性提示：" + "；".join(consistency_notes) + "\n（GA4 小流量隐私阈值/other 分组可能导致明细与总数不一致）"
        # 2.0: GA4 平均时长异常提示（DATA_QUALITY_WARNING），不当作转化故障
        if avg_dur > 600:
            consistency_str += "\n\n⚠️ 数据质量提示：平均时长 " + dur_str + " 异常，可能由 GA4 小流量/单会话长停留导致，建议以 28 天滚动口径为准"
        elif avg_dur == 0 and (data.get("sessions") or 0) > 0:
            consistency_str += ("\n\n⚠️ 数据质量提示：平均时长 0 秒（" + str(data.get("sessions")) +
                                " 会话），疑似即时跳出或事件未上报，建议核对 GA4 埋点/consent 配置，以 28 天滚动口径为准")
        
        # ===== 2. 搜索表现 =====
        gsc_available = data.get("gsc_data_available", False)
        gsc_has_data = gsc_available and data.get("gsc_impressions", 0) > 0
        # 缓存口径：28 天快照窗口独立成行，绝不冒充"昨日"（真实性修复）
        _snap = data.get("reporting_snapshot") or {}
        _cached_imp = _snap.get("gsc_impressions_28d")
        gsc_cache_imp_str = f"{_cached_imp:,.0f} 次" if _cached_imp is not None else "—"
        gsc_cache_clk_str = f"{(_snap.get('gsc_clicks_28d') or 0):,.0f} 次" if _cached_imp is not None else "—"
        if gsc_has_data:
            gsc_auth_str = "✅ 已连接"
            gsc_impressions_str = f"{data.get('gsc_impressions', 0):,} 次"
            gsc_clicks_str = f"{data.get('gsc_clicks', 0):,} 次"
            gsc_ctr_str = f"{data.get('gsc_ctr', 0):.2f}%"
            gsc_indexed_str = f"{data.get('indexed_pages', 'N/A')} 个"
            gsc_errors_str = ("未检测" if data.get('gsc_errors') is None else f"{data['gsc_errors']} 个")
            gsc_week_trend = data.get('gsc_week_trend', 'N/A')
            gsc_month_trend = data.get('gsc_month_trend', 'N/A')
        elif gsc_available:
            # 已连接但昨日无数据：昨日列显示 NOT_AVAILABLE，缓存独立成行
            gsc_auth_str = "✅ 已连接"
            gsc_impressions_str = "NOT_AVAILABLE"
            gsc_clicks_str = "NOT_AVAILABLE"
            gsc_ctr_str = "NOT_AVAILABLE"
            gsc_indexed_str = f"{data.get('indexed_pages', 'N/A')} 个"
            gsc_errors_str = ("未检测" if data.get('gsc_errors') is None else f"{data['gsc_errors']} 个")
            gsc_week_trend = "NOT_AVAILABLE（无昨日数据）"
            gsc_month_trend = "NOT_AVAILABLE（无昨日数据）"
        else:
            # GSC 未授权/取数失败：明确标注，不回退为缓存冒充昨日
            gsc_auth_str = "⚠️ 未授权（服务账号无站点访问权）"
            gsc_impressions_str = "未授权"
            gsc_clicks_str = "未授权"
            gsc_ctr_str = "未授权"
            gsc_indexed_str = "未授权"
            gsc_errors_str = "未授权"
            gsc_week_trend = "NOT_AVAILABLE"
            gsc_month_trend = "NOT_AVAILABLE"
        
        # Top 搜索关键词
        top_keywords = data.get("top_keywords", [])
        kw_lines = ["暂无数据"]
        if gsc_has_data and top_keywords:
            kw_lines = [f"{i}. {kw['keyword']} (曝光 {kw['impressions']}, 点击 {kw['clicks']}, CTR {kw['ctr']}%, 排名 {kw['position']})" for i, kw in enumerate(top_keywords[:5], 1)]
        elif gsc_has_data and not top_keywords:
            kw_lines = ["昨日无搜索关键词数据"]
        elif gsc_available and not gsc_has_data:
            kw_lines = ["GSC 已连接，昨日暂无搜索数据"]
        elif not gsc_available:
            kw_lines = ["GSC 未授权：服务账号无站点访问权，无法取数。请到 Search Console 将服务账号添加为站点所有者"]
        kw_str = "\n".join(kw_lines)
        
        # ===== 3. 内容质量巡检 =====
        
        # ===== 4. 联盟变现 =====
        
        # ===== 5. 订阅数据 =====
        
        # ===== 6. 自动化运维状态 =====
        gh_blog = data.get("gh_blog_success")
        gh_report = data.get("gh_report_success")
        blog_icon = "✅" if gh_blog == True else ("❌" if gh_blog == False else "⚪")
        report_icon = "✅" if gh_report == True else ("❌" if gh_report == False else "⚪")
        ci_token_missing = not os.environ.get("GITHUB_TOKEN")
        blog_state = "成功" if gh_blog == True else ("失败" if gh_blog == False else ("CI 状态未获取（本地预览）" if ci_token_missing else "未运行"))
        report_state = "成功" if gh_report == True else ("失败" if gh_report == False else ("CI 状态未获取（本地预览）" if ci_token_missing else "未运行"))
        
        # 高优先级待办
        todos = data.get("high_priority_todos", [])
        # P1-GROWTH-28A: Drive 状态异常自动进入当日待办（标红）
        if "🔴" in drive_status_line:
            todos = [f"🔴 Drive 状态异常：{drive_status_line}"] + todos
        todos_str = "✅ 所有正常，无待处理问题"
        if todos:
            todos_str = "\n".join([f"{i}. {t}" for i, t in enumerate(todos[:8], 1)])
        
        card = {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"📊 ChinaBound Travel 每日运营日报 | {report_date}（昨日数据）"
                },
                "template": "blue"
            },
            "elements": [
                # === 0. OKR 进度速览 ===
                ({"tag": "div", "text": {"tag": "lark_md", "content": data.get("okr_section", "")}} if data.get("okr_section") else None),
                ({"tag": "div", "text": {"tag": "lark_md", "content": data.get("advice_section", "")}} if data.get("advice_section") else None),
                # === 1. 流量总览（GA4） ===
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"""**📊 1. 流量总览（GA4 | {report_date}）** {traffic_status}

| 指标 | 数据 | 指标 | 数据 |
| --- | --- | --- | --- |
| 访客数 | {data.get('visitors', 0):,} 人 | 页面浏览 | {data.get('requests', 0):,} 次 |
| 会话数 | {data.get('sessions', 0):,} 次 | 跳出率 | {data.get('bounce_rate', 0):.1f}% |
| 互动率 | {data.get('engagement_rate', 0):.1f}% | 平均时长 | {dur_str} |

**📈 同比趋势**
- 日环比: {data.get('visitors_trend', 'N/A')} ｜ 周同比: {data.get('week_trend', 'N/A')} ｜ 月同比: {data.get('month_trend', 'N/A')}{trend_note}{consistency_str}"""
                    }
                },
                # Top 流量来源
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"""**🔗 流量来源 Top5**
{channel_str}

**🌍 访客地区 Top5**
{country_str}

**🔥 热门页面 Top5**
{top_pages_str}"""
                    }
                },
                {"tag": "hr"},
                
                # === 2. 搜索表现（GSC） ===
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"""**🔍 2. 搜索表现（Google Search Console | {report_date}）** {search_status} {gsc_auth_str}

| 指标 | 数据 | 指标 | 数据 |
| --- | --- | --- | --- |
| 授权状态 | {gsc_auth_str} | Sitemap 数量 | {gsc_indexed_str} |
| 昨日搜索曝光 | {gsc_impressions_str} | 昨日搜索点击 | {gsc_clicks_str} |
| 28天缓存窗口 | {gsc_cache_imp_str} | 缓存点击 | {gsc_cache_clk_str} |
| 索引错误 | {gsc_errors_str} | 点击率 CTR | {gsc_ctr_str} |

**📈 GSC 同比趋势**: 周同比 {gsc_week_trend} ｜ 月同比 {gsc_month_trend}"""
                    }
                },
                # Top 关键词
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"""**🔑 搜索关键词 Top5**
{kw_str}"""
                    }
                },
                {"tag": "hr"},
                
                # === 3. 内容质量巡检 ===
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"""**📝 3. 内容质量巡检（本地文件扫描）** {content_status}

| 指标 | 数量 | 状态 |
| --- | --- | --- |
| 站点总文章数 | {data.get('total_posts', 0)} 篇 | - |
| 今日新发 | {data.get('new_posts', 0)} 篇 | {data.get('new_posts', 0) > 0 and '🆕' or '-'} |
| 草稿待审 | {data.get('pending_posts', 0)} 篇 | {data.get('pending_posts', 0) > 0 and '⏳' or '✅'} |
| 占位符残留 | {data.get('placeholder_articles', 0)} 篇 | {data.get('placeholder_articles', 0) > 0 and '❌' or '✅'} |
| 空链接残留 | {data.get('empty_links', 0)} 处 | {data.get('empty_links', 0) > 0 and '❌' or '✅'} |
| 图片缺Alt | {data.get('missing_alt', 0)} 处 | {data.get('missing_alt', 0) > 0 and '⚠️' or '✅'} |"""
                    }
                },
                {"tag": "hr"},
                
                # === 4. 实验与阻塞 ===
                ({"tag": "div", "text": {"tag": "lark_md", "content": self._build_experiments_block(data)}} if data.get("reporting_snapshot") else None),
                {"tag": "hr"},

                # === 5. 联盟变现数据 ===
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"""**💰 5. 联盟变现数据（{report_date}）** {affiliate_status}

💰 **收入状态**: {rev_status_line}

🏨 **Travelpayouts（酒店/机票/门票/租车/玩乐 — 统一渠道）**
| 指标 | 数据 |
| --- | --- |
| 昨日触达(TP inits) | {tp_display['inits']} 次 |
| 昨日搜索 | {tp_display['searches']} 次 |
| 昨日点击 | {tp_display['clicks']} 次 |
| 昨日订单 | {tp_display['bookings']} 单 |
| 昨日佣金 | {tp_display['revenue']} |
| 点击率（同源 clicks/inits） | {tp_ctr} |
{tp_quality_note}

🛡️ **NordVPN / NordPass（通过 AffiliatesCN）**
| 指标 | 数据 |
| --- | --- |
| 昨日点击 | {nord_display['clicks']} 次 |
| 昨日转化 | {nord_display['conversions']} 单 |
| 昨日佣金 | {nord_display['revenue']} |

> Klook、Booking.com 链接均通过 Travelpayouts 追踪，佣金统一统计

**合计昨日佣金**: {total_rev_str}

**Drive 状态**: {drive_status_line}"""
                    }
                },
                {"tag": "hr"},
                
                # === 5. 邮件订阅 ===
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"""**📧 6. 邮件订阅（MailerLite）**

| 指标 | 数据 |
| --- | --- |
| 总订阅人数 | {ml_total_str} |
| 昨日新增 | {ml_new_str} |

{('⚠️ **零增长告警**：昨日新增订阅为 0，建议排查 Lead Magnet / 订阅 CTA 覆盖' if data.get('ml_zero_growth_alert') else '✅ 订阅数据正常')}"""
                    }
                },
                {"tag": "hr"},
                
                # === 6. 自动化运维状态 ===
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"""**⚙️ 7. 自动化运维状态**

| 工作流 | 状态 |
| --- | --- |
| 博客自动生成（Hugo） | {blog_icon} {blog_state} |
| 日报自动推送（Feishu） | {report_icon} {report_state} |

🟢 网站状态: {'正常' if data.get('site_up') else '异常'} | ⏱️ 响应: {data.get('response_time', 0):.0f}ms"""
                    }
                },
                {"tag": "hr"},
                
                # === 7. 高优先级待办 ===
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"""**📌 8. 今日高优先级待办**

{todos_str}"""
                    }
                },
                
                # === 数据状态提醒 ===
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"""**📋 数据源状态提醒**

{self._build_status_message(data)}"""
                    }
                }
            ]
        }
        # 过滤空板块（None 占位）
        card["elements"] = [el for el in card["elements"] if el]
        
        return card
    
    def _build_experiments_block(self, data: dict) -> str:
        """构建实验与阻塞板块（2.0 G域 + 关键blocker）"""
        # 直接读原始快照（load_reporting_snapshot 返回扁平化结构，不含experiments列表）
        try:
            raw = json.loads(SNAPSHOT_FILE.read_text(encoding="utf-8"))
        except Exception:
            return ""
        domains = raw.get("domains", {})
        exp_domain = domains.get("experiments", {})
        experiments = exp_domain.get("experiments", []) if isinstance(exp_domain, dict) else []
        if not experiments:
            return ""
        running = [e for e in experiments if e.get("status") == "RUNNING"]
        waiting = [e for e in experiments if e.get("status") == "WAITING_RECRAWL"]
        pending = [e for e in experiments if e.get("status") == "PENDING"]
        lines = [f"**🧪 4. 实验与阻塞** | 在跑 {len(running)} | 待重爬 {len(waiting)} | 待启动 {len(pending)}", ""]
        lines.append("| ID | 实验名称 | 状态 | 观察 | 样本 |")
        lines.append("| --- | --- | --- | --- | --- |")
        icon_map = {"RUNNING": "🔄", "WAITING_RECRAWL": "⏳", "PENDING": "📋", "WIN": "✅", "LOSE": "❌"}
        for e in experiments[:6]:
            eid = e.get("experiment_id", "?")
            name = (e.get("display_name") or eid)[:28]
            st = e.get("status", "?")
            icon = icon_map.get(st, "❓")
            days = e.get("observation_days")
            days_str = f"{days}d" if days is not None else "-"
            samp = e.get("sample_status", "-")
            samp_short = "不足" if samp == "INSUFFICIENT_SAMPLE" else (samp or "-")[:8]
            lines.append(f"| {eid} | {name} | {icon} {st} | {days_str} | {samp_short} |")
        blockers = []
        if waiting:
            blockers.append(f"⏳ 等待重爬: {', '.join(e.get('experiment_id','') for e in waiting)}")
        ca_kpis = (domains.get("content_assets", {}) or {}).get("kpis", [])
        for k in ca_kpis:
            if k.get("name") == "canonical_conflicts":
                val = k.get("value")
                if isinstance(val, (int, float)) and val > 0:
                    blockers.append(f"⚠️ canonical冲突: {int(val)} 处 HIGH")
                elif isinstance(val, str) and val not in ("0", "NULL", "None", ""):
                    blockers.append(f"⚠️ canonical冲突: {val}")
        ops_kpis = (domains.get("operations", {}) or {}).get("kpis", [])
        for k in ops_kpis:
            if k.get("name") == "backup_rollback" and (k.get("value") is None or k.get("status") == "NOT_AVAILABLE"):
                blockers.append("🗄️ 备份回滚: 未配置")
        if blockers:
            lines.append("")
            lines.append("**🚧 关键阻塞**")
            for b in blockers:
                lines.append(f"- {b}")
        lines.append("")
        lines.append("> 评审gate: REV001/REV002/DRIVE-001 观察期至 2026-09-13，样本不足前不做判定")
        return "\n".join(lines)

    def _build_status_message(self, data: dict) -> str:
        """构建数据状态提示信息"""
        status_list = data.get("data_status", [])
        
        if not status_list:
            return "✅ 所有数据来源正常"
        
        message = ""
        for status in status_list:
            message += f"⚠️ {status}\n"
        
        return message
    
    def collect_data(self) -> dict:
        """收集日报数据 - 完整版"""
        data = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "site_up": True,
            "response_time": 0,
            # 流量数据
            "visitors": 0,
            "sessions": 0,
            "requests": 0,
            "visitors_trend": "N/A",
            "week_trend": "N/A",
            "month_trend": "N/A",
            "bounce_rate": 0.0,
            "avg_session_duration": 0,
            "engagement_rate": 0.0,
            "top_pages": [],
            "top_channels": [],
            "top_countries": [],
            # 搜索数据
            "indexed_pages": "N/A",
            "gsc_data_available": False,
            "gsc_impressions": 0,
            "gsc_clicks": 0,
            "gsc_ctr": 0.0,
            "gsc_errors": 0,
            "gsc_week_trend": "N/A",
            "gsc_month_trend": "N/A",
            "top_keywords": [],
            # 内容数据
            "total_posts": 0,
            "new_posts": 0,
            "pending_posts": 0,
            "placeholder_articles": 0,
            "empty_links": 0,
            "missing_alt": 0,
            "total_content_issues": 0,
            # 联盟数据
            "tp_clicks": 0,
            "tp_bookings": 0,
            "tp_revenue": 0.0,
            "tp_available": False,
            "tp_inits": 0,
            "tp_searches": 0,
            "nord_available": False,
            "nord_clicks": 0,
            "nord_conversions": 0,
            "nord_revenue": 0.0,
            "top_converting_article": "N/A",
            "affiliate_revenue": 0.0,
            # 订阅数据
            "ml_total_subscribers": 0,
            "ml_new_subscribers": 0,
            "ml_available": False,
            # GitHub Actions 状态
            "gh_blog_success": None,
            "gh_report_success": None,
            # 高优先级待办
            "high_priority_todos": [],
            # 数据获取状态
            "data_status": []
        }
        
        print("📥 收集数据...")
        
        # 1. 检查网站状态
        try:
            response = requests.get("https://chinaboundtravel.com", timeout=10)
            data["site_up"] = response.status_code == 200
            data["response_time"] = response.elapsed.total_seconds() * 1000
            print(f"   ✅ 网站状态: {'正常' if data['site_up'] else '异常'}")
        except Exception as e:
            print(f"   ⚠️ 网站检查失败: {e}")
            data["site_up"] = False
            data["data_status"].append("网站状态检查失败")
        
        # 2. GA4 流量数据（优先）
        ga4_data = self._fetch_ga4()
        if ga4_data:
            data.update(ga4_data)
            print(f"   ✅ GA4流量数据: {data['visitors']:,} 访客, {data.get('sessions', 0):,} 会话, 跳出率 {data.get('bounce_rate', 0):.1f}%")
            if data.get('top_channels'):
                print(f"   ✅ 流量来源: {data['top_channels'][0].get('channel', 'N/A')} ({data['top_channels'][0].get('users', 0)} 人)")
            if data.get('top_keywords'):
                print(f"   ✅ GSC数据: 曝光 {data['gsc_impressions']:,}, 点击 {data['gsc_clicks']:,}")
        else:
            data["data_status"].append("GA4流量数据获取失败（请配置GA4_SERVICE_ACCOUNT_JSON）")
            # 降级到 Cloudflare
            cf_data = self._fetch_cloudflare()
            if cf_data:
                data.update(cf_data)
                print(f"   ✅ Cloudflare流量数据: {data['visitors']:,} 访客, {data['requests']:,} 请求")
            else:
                data["data_status"].append("Cloudflare流量数据未配置")
        
        # 3. GSC 搜索数据
        gsc_data = self._fetch_gsc()
        if gsc_data and gsc_data.get("gsc_data_available"):
            data.update(gsc_data)
            if data.get("gsc_impressions", 0) > 0:
                print(f"   ✅ GSC数据: 曝光 {data['gsc_impressions']:,} 次, 点击 {data['gsc_clicks']:,} 次")
            else:
                print(f"   ✅ GSC已连接，昨日暂无搜索数据")
                data["data_status"].append("GSC已连接，昨日搜索曝光 0（新站可能未起量，持续观察；非授权问题）")
        else:
            data["data_status"].append("GSC数据获取失败 - 请在 Google Search Console 中授权服务账号")

        # 4. 本地内容质量巡检
        content_issues = self._scan_content_quality(data.get("report_date"))
        data.update(content_issues)
        print(f"   ✅ 内容巡检: {data['total_posts']} 篇, 占位符 {data['placeholder_articles']}, 空链接 {data['empty_links']}, Alt缺失 {data['missing_alt']}")
        
        # 4. Travelpayouts 数据
        tp_data = self._fetch_travelpayouts()
        if tp_data:
            data.update(tp_data)
            data["tp_available"] = True
            print(f"   ✅ Travelpayouts: 点击 {data['tp_clicks']}, 订单 {data['tp_bookings']}, ${data['tp_revenue']:.2f}")
        else:
            data["tp_available"] = False
            data["data_status"].append("Travelpayouts联盟数据未配置（需设置 TRAVELPAYOUTS_API_TOKEN）")
        
        # 5. NordVPN 数据
        nord_data = self._fetch_nordvpn()
        if nord_data:
            data.update(nord_data)
            data["nord_available"] = nord_data.get("nord_available", False)
            if not data["nord_available"]:
                data["data_status"].append("NordVPN: 需手动查看 Impact.com 后台")
        else:
            data["nord_available"] = False
            data["data_status"].append("NordVPN: 需手动查看 Impact.com 后台")
        
        # 6. MailerLite 订阅数据
        ml_data = self._fetch_mailerlite()
        if ml_data:
            data.update(ml_data)
            if data.get("ml_available"):
                print(f"   ✅ MailerLite: 总订阅 {data.get('ml_total_subscribers', 'N/A')} 人, 昨日新增 {data.get('ml_new_subscribers', 0)} 人")
                # 零增长自动告警（订阅渠道已接入但昨日无新增 → 提示行动）
                if data.get("ml_new_subscribers", 0) == 0:
                    _zero_alert = "📧 订阅零增长：昨日新增订阅为 0（渠道已接入），需排查 Lead Magnet / 订阅 CTA 覆盖与投放"
                    data.setdefault("data_status", []).append(_zero_alert)
                    data["ml_zero_growth_alert"] = True
                    print(f"   ⚠️ {_zero_alert}")
                else:
                    data["ml_zero_growth_alert"] = False
            else:
                print(f"   ⚠️ MailerLite: {data.get('ml_error', 'API 不可用')}")
                data["data_status"].append(data.get("ml_error", "MailerLite API 不可用"))
        else:
            data["data_status"].append("MailerLite订阅数据未配置（需设置 MAILERLITE_API_TOKEN）")
        
        # 6. GitHub Actions 工作流状态
        gh_data = self._fetch_github_actions()
        if gh_data:
            data.update(gh_data)
            blog_status = '成功' if data.get('gh_blog_success') == True else ('失败' if data.get('gh_blog_success') == False else '未运行')
            report_status = '成功' if data.get('gh_report_success') == True else ('失败' if data.get('gh_report_success') == False else '未运行')
            print(f"   ✅ GitHub Actions: 博客生成 {blog_status}, 日报 {report_status}")
            # 社媒分发失败 → 真实告警（不被日报状态吞掉）
            if data.get("gh_social_success") is False:
                _social_alert = "社媒分发工作流（Social Engine Daily）昨日失败，请检查 Buffer 排期与 Worker 日志"
                data.setdefault("data_status", []).append(_social_alert)
                print(f"   ⚠️ {_social_alert}")
        

        # 8. 统计总问题数和总佣金
        data["total_content_issues"] = data["placeholder_articles"] + data["empty_links"] + data["missing_alt"]
        data["affiliate_revenue"] = data.get("tp_revenue", 0) + data.get("nord_revenue", 0)

        # 9. 当期 OKR 进度速览（季度目标）
        data["okr_section"] = okr_utils.build_okr_section(data, "daily")

        # 10. 自动运营建议（基于真实数据精准生成）
        advice_items = report_advice.generate_advice(data, "daily")
        data["advice_section"] = report_advice.advice_section(data, "daily")

        # 7. 高优先级待办 = 内容巡检 + OKR 完成率 + 运营建议 三源打通（告警-待办闭环）
        base_todos = self._generate_todos(data)
        okr_progress = okr_utils.build_okr_progress(data, "daily")
        merged_todos = base_todos + generate_priority_tasks(okr_progress, advice_items)
        seen, todos = set(), []
        for t in merged_todos:
            if t not in seen:
                seen.add(t)
                todos.append(t)
        data["high_priority_todos"] = todos[:8]

        # 2.0: 附加统一 KPI 快照（GSC/收入缓存回退与状态标签）
        data["reporting_snapshot"] = load_reporting_snapshot()

        return data
    
    def _fetch_cloudflare(self) -> dict:
        """获取 Cloudflare 流量数据（使用 GraphQL API）"""
        if not CLOUDFLARE_API_TOKEN or not CLOUDFLARE_ZONE_ID:
            print("   ⚠️ Cloudflare API Token 未配置")
            return None
        
        try:
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            two_days_ago = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
            
            # 使用 Cloudflare GraphQL API
            url = "https://api.cloudflare.com/client/v4/graphql"
            headers = {
                "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
                "Content-Type": "application/json"
            }
            
            query = f"""{{
                viewer {{
                    zones(filter: {{zoneTag: "{CLOUDFLARE_ZONE_ID}"}}) {{
                        httpRequests1dGroups(
                            limit: 2,
                            filter: {{date_geq: "{two_days_ago}", date_leq: "{yesterday}"}},
                            orderBy: [date_ASC]
                        ) {{
                            dimensions {{ date }}
                            sum {{ requests pageViews }}
                            uniq {{ uniques }}
                        }}
                    }}
                }}
            }}"""
            
            print(f"   🔍 正在调用 Cloudflare GraphQL API ({yesterday})...")
            response = requests.post(url, headers=headers, json={"query": query}, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                data = result.get("data", {}).get("viewer", {}).get("zones", [])
                
                if not data:
                    print("   ⚠️ Cloudflare GraphQL 返回空数据")
                    return None
                
                groups = data[0].get("httpRequests1dGroups", [])
                
                yesterday_requests = 0
                yesterday_pageviews = 0
                yesterday_uniques = 0
                two_days_ago_requests = 0
                
                for group in groups:
                    date = group.get("dimensions", {}).get("date", "")
                    req = int(group.get("sum", {}).get("requests", 0))
                    pv = int(group.get("sum", {}).get("pageViews", 0))
                    uv = int(group.get("uniq", {}).get("uniques", 0))
                    
                    if date == yesterday:
                        yesterday_requests = req
                        yesterday_pageviews = pv
                        yesterday_uniques = uv
                    elif date == two_days_ago:
                        two_days_ago_requests = req
                
                # 计算同比
                trend = "N/A"
                if two_days_ago_requests > 0:
                    change = ((yesterday_requests - two_days_ago_requests) / two_days_ago_requests) * 100
                    trend = f"+{change:.1f}%" if change >= 0 else f"{change:.1f}%"
                
                print(f"   ✅ Cloudflare 数据: {yesterday_uniques} 访客, {yesterday_requests} 请求, {yesterday_pageviews} 浏览量")
                
                return {
                    "visitors": yesterday_uniques,
                    "requests": yesterday_requests,
                    "pageviews": yesterday_pageviews,
                    "visitors_trend": trend,
                    "top_pages": []
                }
            else:
                print(f"   ⚠️ Cloudflare GraphQL API 响应: {response.status_code}")
                        
        except Exception as e:
            print(f"   ⚠️ Cloudflare API 获取失败: {e}")
        
        return None
    
    def _fetch_gsc(self) -> dict:
        """获取 Google Search Console 数据（昨日 + Top关键词 + CTR + 周同比 + 月同比）"""
        if not GSC_SERVICE_ACCOUNT_JSON or not HAS_GOOGLE_AUTH:
            print("   ⚠️ GSC: 服务账号未配置")
            return None
        
        try:
            from googleapiclient.discovery import build
            
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            # 周同比：上周同日（D-7）；月同比：上月同日（D-30）
            last_week_day = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            last_month_day = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            
            print(f"   🔍 正在调用 GSC API ({yesterday})...")
            
            service_account_info = self._load_gsc_service_account()
            if not service_account_info:
                return None
            
            credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=["https://www.googleapis.com/auth/webmasters.readonly"]
            )
            credentials.refresh(Request())
            
            service = build("searchconsole", "v1", credentials=credentials)
            # 站点候选：优先使用配置的 GSC_SITE_URL（.env/CI 环境变量），回退域属性；支持逗号分隔多候选
            site_candidates = []
            for s in str(GSC_SITE_URL or "").split(","):
                s = s.strip()
                if s and s not in site_candidates:
                    site_candidates.append(s)
            default_domain = "sc-domain:chinaboundtravel.com"
            if default_domain not in site_candidates:
                site_candidates.append(default_domain)
            site_url = None
            for candidate in site_candidates:
                try:
                    service.sites().get(siteUrl=candidate).execute()
                    site_url = candidate
                    print(f"   ✅ GSC 站点验证通过: {candidate}")
                    break
                except Exception:
                    print(f"   ⚠️ GSC 站点不可用: {candidate}")
            if not site_url:
                print(f"   ❌ 所有 GSC 站点候选均不可用: {site_candidates}")
                print(f"   ❌ 请确认服务账号 {service_account_info.get('client_email', '')} 已被添加为站点所有者")
                return None
            def gsc_query(start, end, dimensions=None, row_limit=10):
                """封装 GSC 查询"""
                request_body = {
                    "startDate": start,
                    "endDate": end,
                    "type": "web",
                    "rowLimit": row_limit,
                    "dataState": "final"
                }
                if dimensions:
                    request_body["dimensions"] = dimensions
                return service.searchanalytics().query(
                    siteUrl=site_url, body=request_body
                ).execute()
            
            # === 昨日总览（单日精确查询） ===
            yesterday_response = gsc_query(yesterday, yesterday)
            print(f"   ✅ GSC API 调用成功")

            yesterday_impressions = 0
            yesterday_clicks = 0
            yesterday_ctr = 0.0

            if "rows" in yesterday_response and yesterday_response["rows"]:
                yesterday_impressions = int(yesterday_response["rows"][0].get("impressions", 0))
                yesterday_clicks = int(yesterday_response["rows"][0].get("clicks", 0))
                yesterday_ctr = round(float(yesterday_response["rows"][0].get("ctr", 0)) * 100, 2)
            
            # === 周同比 ===
            week_impressions = 0
            try:
                week_resp = gsc_query(last_week_day, last_week_day)
                if "rows" in week_resp:
                    week_impressions = int(week_resp["rows"][0].get("impressions", 0)) if week_resp["rows"] else 0
            except:
                pass
            week_trend = "N/A"
            if week_impressions > 0:
                w_change = ((yesterday_impressions - week_impressions) / week_impressions) * 100
                week_trend = f"+{w_change:.1f}%" if w_change >= 0 else f"{w_change:.1f}%"
            
            # === 月同比 ===
            month_impressions = 0
            try:
                month_resp = gsc_query(last_month_day, last_month_day)
                if "rows" in month_resp:
                    month_impressions = int(month_resp["rows"][0].get("impressions", 0)) if month_resp["rows"] else 0
            except:
                pass
            month_trend = "N/A"
            if month_impressions > 0:
                m_change = ((yesterday_impressions - month_impressions) / month_impressions) * 100
                month_trend = f"+{m_change:.1f}%" if m_change >= 0 else f"{m_change:.1f}%"
            
            # === Top 搜索关键词 Top10 ===
            top_keywords = []
            try:
                kw_response = gsc_query(yesterday, yesterday, dimensions=["query"], row_limit=10)
                if "rows" in kw_response:
                    for row in kw_response["rows"]:
                        keyword = row.get("keys", [""])[0] if row.get("keys") else "N/A"
                        clicks = int(row.get("clicks", 0))
                        impressions = int(row.get("impressions", 0))
                        ctr = round(float(row.get("ctr", 0)) * 100, 2)
                        position = round(float(row.get("position", 0)), 1)
                        if impressions > 0:
                            top_keywords.append({
                                "keyword": keyword,
                                "clicks": clicks,
                                "impressions": impressions,
                                "ctr": ctr,
                                "position": position
                            })
            except Exception as e:
                print(f"   ⚠️ GSC 关键词查询失败: {e}")
            
            # === 获取 sitemap 信息 + 真实索引错误数（sitemaps API 提供 errors 字段）===
            indexed_pages = "N/A"
            gsc_errors = None  # None=未检测；真实错误数来自 sitemaps API
            try:
                sitemaps = service.sitemaps().list(siteUrl=site_url).execute()
                if sitemaps.get("sitemap"):
                    indexed_pages = len(sitemaps["sitemap"])
                    _err_sum = 0
                    for _s in sitemaps["sitemap"]:
                        try:
                            _err_sum += int(_s.get("errors") or 0)
                        except (TypeError, ValueError):
                            pass
                    gsc_errors = _err_sum
            except Exception:
                pass
            
            print(f"   📊 GSC数据: 曝光 {yesterday_impressions:,}, 点击 {yesterday_clicks:,}, CTR {yesterday_ctr}%, 关键词 {len(top_keywords)} 个")
            
            return {
                "gsc_data_available": True,
                "indexed_pages": indexed_pages,
                "gsc_impressions": yesterday_impressions,
                "gsc_clicks": yesterday_clicks,
                "gsc_ctr": yesterday_ctr,
                "gsc_errors": gsc_errors,
                "gsc_week_trend": week_trend,
                "gsc_month_trend": month_trend,
                "top_keywords": top_keywords
            }
                
        except Exception as e:
            import traceback
            print(f"   ⚠️ GSC API 获取失败: {e}")
            print(f"   ⚠️ GSC traceback: {traceback.format_exc()[-500:]}")
        
        return None
    
    def _load_service_account(self) -> dict:
        """加载服务账号信息（支持文件路径或直接JSON字符串）"""
        if not GA4_SERVICE_ACCOUNT_JSON:
            return None
        
        sa_json = GA4_SERVICE_ACCOUNT_JSON
        
        try:
            # 优先尝试直接解析为 JSON
            return json.loads(sa_json)
        except (json.JSONDecodeError, TypeError):
            pass
        
        # GitHub Secrets 存储时可能将 \n 转义为字面 \\n，尝试修复
        try:
            if "\\n" in sa_json and "BEGIN PRIVATE KEY" in sa_json:
                fixed_json = sa_json.replace("\\n", "\n")
                return json.loads(fixed_json)
        except (json.JSONDecodeError, TypeError):
            pass
        
        try:
            # 如果不是有效 JSON，尝试作为文件路径读取
            sa_path = Path(sa_json)
            if not sa_path.is_absolute():
                # 相对路径基于 BLOG_ROOT 解析
                sa_path = BLOG_ROOT / sa_path
            if sa_path.exists() and sa_path.is_file():
                with open(sa_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"   ⚠️ 服务账号加载失败: {e}")
            return None

        print(f"   ⚠️ 服务账号加载失败: 无法解析 JSON 或读取文件 (路径: {sa_json})")
        return None
    
    def _load_gsc_service_account(self) -> dict:
        """加载 GSC 服务账号信息（独立于 GA4）
        如果 GSC_SERVICE_ACCOUNT_JSON 加载失败，回退到 GA4 服务账号（两者通常使用同一账号）
        """
        # 优先尝试 GSC 专用配置
        if GSC_SERVICE_ACCOUNT_JSON:
            sa_json = GSC_SERVICE_ACCOUNT_JSON

            try:
                return json.loads(sa_json)
            except (json.JSONDecodeError, TypeError):
                pass

            try:
                if "\\n" in sa_json and "BEGIN PRIVATE KEY" in sa_json:
                    fixed_json = sa_json.replace("\\n", "\n")
                    return json.loads(fixed_json)
            except (json.JSONDecodeError, TypeError):
                pass

            try:
                sa_path = Path(sa_json)
                if not sa_path.is_absolute():
                    sa_path = BLOG_ROOT / sa_path
                if sa_path.exists() and sa_path.is_file():
                    with open(sa_path, "r", encoding="utf-8") as f:
                        return json.load(f)
            except Exception as e:
                print(f"   ⚠️ GSC 服务账号文件读取失败: {e}")

            print(f"   ⚠️ GSC 服务账号加载失败，尝试回退到 GA4 服务账号...")

        # Fallback: 使用 GA4 服务账号（本地两者用同一文件，GitHub Actions 中 GA4 可能已配置）
        if GA4_SERVICE_ACCOUNT_JSON:
            ga4_info = self._load_service_account()
            if ga4_info:
                print(f"   ✅ GSC 回退到 GA4 服务账号成功")
                return ga4_info

        print(f"   ⚠️ GSC: 服务账号未配置且 GA4 回退也失败")
        return None
    
    def _get_ga4_auth_headers(self) -> dict:
        """获取 GA4 API 认证 headers（复用认证逻辑）"""
        if not GA4_SERVICE_ACCOUNT_JSON or not HAS_GOOGLE_AUTH:
            print("   ⚠️ GA4: 服务账号未配置")
            return None
        
        try:
            service_account_info = self._load_service_account()
            if not service_account_info:
                return None
            
            credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=["https://www.googleapis.com/auth/analytics.readonly"]
            )
            credentials.refresh(Request())
            return {
                "Authorization": f"Bearer {credentials.token}",
                "Content-Type": "application/json"
            }
        except Exception as e:
            print(f"   ⚠️ GA4 认证失败: {e}")
            return None
    
    def _ga4_run_report(self, headers: dict, payload: dict) -> dict:
        """执行 GA4 runReport 请求"""
        url = f"https://analyticsdata.googleapis.com/v1beta/properties/{GA4_PROPERTY_ID}:runReport"
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            return resp.json()
        print(f"   ⚠️ GA4 API 响应 {resp.status_code}: {resp.text[:200]}")
        return None
    
    def _fetch_ga4(self) -> dict:
        """获取 GA4 数据（昨日 + 周同比 + 月同比 + 流量来源 + 互动指标）"""
        if not GA4_PROPERTY_ID:
            print("   ⚠️ GA4 Property ID 未配置")
            return None
        
        try:
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            two_days_ago = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
            # 周同比：上周同日（D-7）；月同比：上月同日（D-30）
            last_week_day = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            last_month_day = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            
            print(f"   🔍 正在调用 GA4 API ({yesterday})...")
            
            headers = self._get_ga4_auth_headers()
            if not headers:
                return None
            
            print("   ✅ GA4 服务账号认证成功")
            
            # === 核心指标：昨日 vs 前日 ===
            # 注意：GA4 Data API 多 dateRange 查询返回的行序不保证与请求顺序一致（实测为逆序），
            # 若直接取 rows[0] 会把前日数据当成昨日。改为两次独立单日期查询，确保不错位。
            core_metrics = [
                {"name": "activeUsers"},
                {"name": "sessions"},
                {"name": "screenPageViews"},
                {"name": "engagementRate"},
                {"name": "averageSessionDuration"},
                {"name": "bounceRate"}
            ]

            def query_day(day: str):
                """单日期查询核心指标，返回 metricValues 列表或 None"""
                payload = {
                    "dateRanges": [{"startDate": day, "endDate": day}],
                    "metrics": core_metrics,
                    "dimensions": []
                }
                res = self._ga4_run_report(headers, payload)
                if not res or "rows" not in res or not res["rows"]:
                    return None
                return res["rows"][0].get("metricValues", [])

            yesterday_vals = query_day(yesterday)
            if yesterday_vals is None:
                print(f"   ⚠️ GA4 核心指标返回空数据（{yesterday}）")
                return None

            print(f"   📤 GA4 昨日({yesterday})指标: {[v.get('value') for v in yesterday_vals]}")
            yesterday_users = int(yesterday_vals[0].get("value", "0"))
            yesterday_sessions = int(yesterday_vals[1].get("value", "0"))
            yesterday_pageviews = int(yesterday_vals[2].get("value", "0"))
            yesterday_engagement = self._parse_ga4_rate(yesterday_vals[3].get("value", "0"))
            yesterday_avg_duration = int(float(yesterday_vals[4].get("value", "0")))
            yesterday_bounce = self._parse_ga4_rate(yesterday_vals[5].get("value", "0"))

            two_days_ago_vals = query_day(two_days_ago)
            two_days_ago_users = 0
            if two_days_ago_vals:
                two_days_ago_users = int(two_days_ago_vals[0].get("value", "0"))

            day_trend = "N/A"
            if two_days_ago_users > 0:
                change = ((yesterday_users - two_days_ago_users) / two_days_ago_users) * 100
                day_trend = f"+{change:.1f}%" if change >= 0 else f"{change:.1f}%"

            print(f"   📊 GA4 核心数据: {yesterday_users} 访客, {yesterday_sessions} 会话, 跳出率 {yesterday_bounce}%")
            
            # === 周同比（昨日 vs 上周同日 D-7） ===
            week_payload = {
                "dateRanges": [
                    {"startDate": last_week_day, "endDate": last_week_day}
                ],
                "metrics": [{"name": "activeUsers"}],
                "dimensions": []
            }
            week_result = self._ga4_run_report(headers, week_payload)
            week_users = 0
            if week_result and "rows" in week_result:
                week_users = int(week_result["rows"][0].get("metricValues", [{}])[0].get("value", "0"))
            week_trend = "N/A"
            if week_users > 0:
                w_change = ((yesterday_users - week_users) / week_users) * 100
                week_trend = f"+{w_change:.1f}%" if w_change >= 0 else f"{w_change:.1f}%"
            
            # === 月同比（昨日 vs 上月同日 D-30） ===
            month_payload = {
                "dateRanges": [
                    {"startDate": last_month_day, "endDate": last_month_day}
                ],
                "metrics": [{"name": "activeUsers"}],
                "dimensions": []
            }
            month_result = self._ga4_run_report(headers, month_payload)
            month_total = 0
            if month_result and "rows" in month_result:
                month_total = int(month_result["rows"][0].get("metricValues", [{}])[0].get("value", "0"))
            month_trend = "N/A"
            if month_total > 0:
                m_change = ((yesterday_users - month_total) / month_total) * 100
                month_trend = f"+{m_change:.1f}%" if m_change >= 0 else f"{m_change:.1f}%"
            
            # === 流量来源渠道 Top5 ===
            channel_payload = {
                "dateRanges": [{"startDate": yesterday, "endDate": yesterday}],
                "metrics": [{"name": "activeUsers"}, {"name": "sessions"}],
                "dimensions": [{"name": "sessionDefaultChannelGroup"}],
                "orderBys": [{"metric": {"metricName": "activeUsers"}, "desc": True}],
                "limit": 5
            }
            channel_result = self._ga4_run_report(headers, channel_payload)
            top_channels = []
            if channel_result and "rows" in channel_result:
                for row in channel_result["rows"]:
                    ch_name = row.get("dimensionValues", [{}])[0].get("value", "N/A")
                    ch_users = int(row.get("metricValues", [{}])[0].get("value", "0"))
                    ch_sessions = int(row.get("metricValues", [{}])[1].get("value", "0"))
                    top_channels.append({"channel": ch_name, "users": ch_users, "sessions": ch_sessions})
            
            # === Top 国家/地区 Top5 ===
            country_payload = {
                "dateRanges": [{"startDate": yesterday, "endDate": yesterday}],
                "metrics": [{"name": "activeUsers"}],
                "dimensions": [{"name": "country"}],
                "orderBys": [{"metric": {"metricName": "activeUsers"}, "desc": True}],
                "limit": 5
            }
            country_result = self._ga4_run_report(headers, country_payload)
            top_countries = []
            if country_result and "rows" in country_result:
                for row in country_result["rows"]:
                    country = row.get("dimensionValues", [{}])[0].get("value", "N/A")
                    users = int(row.get("metricValues", [{}])[0].get("value", "0"))
                    top_countries.append({"country": country, "users": users})
            
            # === Top 页面 Top10 ===
            pages_payload = {
                "dateRanges": [{"startDate": yesterday, "endDate": yesterday}],
                "metrics": [{"name": "screenPageViews"}],
                "dimensions": [{"name": "pagePath"}],
                "orderBys": [{"metric": {"metricName": "screenPageViews"}, "desc": True}],
                "limit": 10
            }
            pages_result = self._ga4_run_report(headers, pages_payload)
            top_pages = []
            if pages_result and "rows" in pages_result:
                for row in pages_result["rows"]:
                    path = row.get("dimensionValues", [{}])[0].get("value", "")
                    views = int(row.get("metricValues", [{}])[0].get("value", "0"))
                    if path and views > 0:
                        top_pages.append({"path": path, "views": views})
            
            return {
                "report_date": yesterday,
                "visitors": yesterday_users,
                "sessions": yesterday_sessions,
                "requests": yesterday_pageviews,
                "visitors_trend": day_trend,
                "week_trend": week_trend,
                "month_trend": month_trend,
                "bounce_rate": yesterday_bounce,
                "avg_session_duration": yesterday_avg_duration,
                "engagement_rate": yesterday_engagement,
                "top_channels": top_channels,
                "top_countries": top_countries,
                "top_pages": top_pages
            }
                
        except Exception as e:
            import traceback
            print(f"   ⚠️ GA4 API 获取失败: {e}")
            print(f"   ⚠️ GA4 traceback: {traceback.format_exc()[-500:]}")
        
        return None
    
    def _parse_ga4_rate(self, value: str) -> float:
        """解析 GA4 返回的比率值（如 0.6543 → 65.4%）"""
        try:
            return round(float(value) * 100, 1)
        except:
            return 0.0
    
    def _scan_content_quality(self, report_date: str = None) -> dict:
        """扫描本地内容质量
        report_date: 日报报告日期（昨日），用于统计"昨日新增"文章
        """
        result = {
            "total_posts": 0,
            "new_posts": 0,
            "pending_posts": 0,
            "placeholder_articles": 0,
            "empty_links": 0,
            "missing_alt": 0
        }
        
        if not POSTS_DIR.exists():
            print(f"   ⚠️ 文章目录不存在: {POSTS_DIR}")
            return result
        
        posts = list(POSTS_DIR.glob("*.md"))
        result["total_posts"] = len(posts)
        
        # 默认统计昨日新增；优先取 frontmatter date，其次文件名日期前缀
        report_date = report_date or (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        for post in posts:
            try:
                content = post.read_text(encoding='utf-8')

                # 统计 report_date 当天新增的文章（frontmatter date 优先，文件名前缀兜底）
                post_date = None
                fm = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
                if fm:
                    dm = re.search(r'^date:\s*["\']?([\d-]+)', fm.group(1), re.MULTILINE)
                    if dm:
                        post_date = dm.group(1)
                if post_date == report_date or (not post_date and post.name.startswith(report_date)):
                    result["new_posts"] += 1
                
                # 检查是否草稿
                if "_draft" in post.name.lower() or post.name.startswith("draft"):
                    result["pending_posts"] += 1
                
                # 检查占位符（含 Joran 图片占位符 [Image: ...] 格式）
                if re.search(r'#TP_[A-Z_]+#|#VPN_[A-Z_]+#|PLACEHOLDER|\[\s*Image\s*:', content, re.IGNORECASE):
                    result["placeholder_articles"] += 1
                
                # 检查空链接
                if re.search(r'\[([^\]]+)\]\(\s*\)', content):
                    result["empty_links"] += 1
                
                # 检查图片 Alt 缺失（排除相对路径但无alt文本的情况）
                for img_match in re.finditer(r'!\[([^\]]*)\]\([^)]+\)', content):
                    alt_text = img_match.group(1).strip()
                    if not alt_text:
                        result["missing_alt"] += 1
                    
            except Exception as e:
                print(f"   ⚠️ 扫描文件失败: {post.name}")
        
        return result
    
    def _fetch_travelpayouts(self) -> dict:
        """获取 Travelpayouts 数据（昨日汇总：点击、订单、佣金）"""
        if not TRAVELPAYOUTS_API_TOKEN:
            print("   ⚠️ Travelpayouts API Token 未配置")
            return None
        
        try:
            url = "https://api.travelpayouts.com/statistics/v1/execute_query"
            headers = {
                "X-Access-Token": TRAVELPAYOUTS_API_TOKEN,
                "Content-Type": "application/json"
            }
            
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            
            # 使用聚合查询获取昨日汇总数据
            payload = {
                "fields": [
                    "redirects_count",
                    "inits_count",
                    "searches_count",
                    "paid_actions_count",
                    "paid_profit_usd_sum"
                ],
                "filters": [
                    {"field": "date", "op": "eq", "value": yesterday}
                ],
                "offset": 0,
                "limit": 1
            }
            
            print(f"   🔍 正在调用 Travelpayouts API ({yesterday})...")
            response = requests.post(url, headers=headers, json=payload, timeout=30)

            if response.status_code == 200:
                result = response.json()
                # Travelpayouts 可能返回 "results" 或 "data" 字段
                rows = result.get("results", []) or result.get("data", [])
                if not rows:
                    print(f"   ℹ️ Travelpayouts API 返回空数据（昨日无活动），原始响应: {str(result)[:300]}")
                
                clicks = 0
                bookings = 0
                revenue = 0.0
                
                if rows:
                    row = rows[0]
                    clicks = int(row.get("redirects_count", 0) or 0)
                    bookings = int(row.get("paid_actions_count", 0) or 0)
                    revenue = float(row.get("paid_profit_usd_sum", 0) or 0)
                    inits = int(row.get("inits_count", 0) or 0)
                    searches = int(row.get("searches_count", 0) or 0)
                    print(f"   📊 Travelpayouts: 展示 {inits}, 搜索 {searches}, 点击 {clicks}, 订单 {bookings}, 佣金 ${revenue:.2f}")
                else:
                    print(f"   📊 Travelpayouts: 昨日暂无数据（正常）")
                    inits = 0
                    searches = 0
                
                return {
                    "tp_clicks": clicks,
                    "tp_bookings": bookings,
                    "tp_revenue": round(revenue, 2),
                    "tp_inits": inits,
                    "tp_searches": searches,
                    "top_converting_article": "N/A",
                    "affiliate_revenue": round(revenue, 2)
                }
            else:
                print(f"   ⚠️ Travelpayouts API 响应 {response.status_code}: {response.text[:200]}")
                
        except Exception as e:
            print(f"   ⚠️ Travelpayouts API 获取失败: {e}")
        
        return None
    
    def _fetch_nordvpn(self) -> dict:
        """获取 NordVPN 联盟数据
        Impact.com 使用异步导出机制，无法在日报中实时获取数据。
        返回带可用性标记的数据，让日报显示"未接入"而非误导性的 0。
        """
        print("   ℹ️ NordVPN/Impact.com: 需手动查看 Impact.com 后台获取数据")
        return {"nord_available": False}
    
    def _fetch_mailerlite(self) -> dict:
        """获取 MailerLite 订阅数据（总订阅数 + 昨日新增）"""
        if not MAILERLITE_API_TOKEN:
            print("   ⚠️ MailerLite API Token 未配置")
            return None

        # 清洗 token：去除 BOM（\ufeff）和空白，避免 latin-1 编码错误
        clean_token = MAILERLITE_API_TOKEN.lstrip("\ufeff").strip()
        clean_token = "".join(c for c in clean_token if ord(c) < 128)

        try:
            headers = {
                "Authorization": f"Bearer {clean_token}",
                "Content-Type": "application/json"
            }
            
            # 获取总订阅者数
            total_subscribers = 0
            try:
                # 遍历分页统计订阅者总数（新版 API 的 meta 无 total，需分页累计）
                page_cursor = None
                _seen = 0
                while True:
                    params = {"limit": 100}
                    if page_cursor:
                        params["cursor"] = page_cursor
                    resp = requests.get(
                        "https://connect.mailerlite.com/api/subscribers",
                        headers=headers,
                        params=params,
                        timeout=15
                    )
                    if resp.status_code != 200:
                        err = resp.text[:150]
                        print(f"   ⚠️ MailerLite API 响应 {resp.status_code}: {err}")
                        return {"ml_available": False,
                                "ml_error": f"MailerLite API 认证失败（HTTP {resp.status_code}），请检查 MAILERLITE_API_TOKEN"}
                    data = resp.json()
                    _seen += len(data.get("data", []))
                    page_cursor = (data.get("meta") or {}).get("next_cursor")
                    if not page_cursor:
                        break
                    if _seen >= 10000:  # 安全上限
                        break
                total_subscribers = _seen
            except Exception as e:
                print(f"   ⚠️ MailerLite 总订阅获取失败: {e}")
                return {"ml_available": False, "ml_error": f"MailerLite API 请求异常: {e}"}
            
            # 获取昨日新增订阅者（通过 group activity 或 subscribers 列表筛选）
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            new_subscribers = 0
            try:
                resp = requests.get(
                    "https://connect.mailerlite.com/api/subscribers",
                    headers=headers,
                    params={"limit": 100, "sort": "created_at:desc"},
                    timeout=15
                )
                if resp.status_code == 200:
                    data = resp.json()
                    subscribers = data.get("data", [])
                    for sub in subscribers:
                        created = sub.get("created_at", "")[:10]
                        if created == yesterday:
                            new_subscribers += 1
            except Exception as e:
                print(f"   ⚠️ MailerLite 昨日新增获取失败: {e}")
            
            return {
                "ml_available": True,
                "ml_total_subscribers": total_subscribers,
                "ml_new_subscribers": new_subscribers
            }
            
        except Exception as e:
            print(f"   ⚠️ MailerLite API 获取失败: {e}")
        
        return None
    
    def _fetch_github_actions(self) -> dict:
        """获取 GitHub Actions 工作流运行状态（博客生成 + 日报推送 + 社媒分发）"""
        if not GITHUB_TOKEN:
            print("   ⚠️ GitHub Token 未配置")
            return None
        
        try:
            headers = {
                "Authorization": f"Bearer {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            base_url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/runs"
            # 只统计报告日（UTC 昨日）完成的工作流，避免把历史成功当成当日状态
            report_day = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            # 当前正在运行的 run（GitHub Actions 自动注入），排除自身避免误判
            current_run_id = str(os.environ.get("GITHUB_RUN_ID", ""))
            
            # 按工作流文件路径精确匹配，避免 "Social Engine Daily" 等名称干扰日报状态
            REPORT_WORKFLOW_PATHS = {".github/workflows/feishu-daily-report.yml"}
            BLOG_WORKFLOW_PATHS = {".github/workflows/weekly-blog-update.yml"}
            SOCIAL_WORKFLOW_PATHS = {
                ".github/workflows/social-engine-daily.yml",
                ".github/workflows/social_distributor.yml",
            }
            
            result = {}
            runs = []  # 预定义避免作用域问题
            try:
                resp = requests.get(
                    base_url,
                    headers=headers,
                    params={"per_page": 100},
                    timeout=15
                )
                if resp.status_code == 200:
                    runs = resp.json().get("workflow_runs", [])
                else:
                    print(f"   ⚠️ GitHub API 响应 {resp.status_code}: {resp.text[:200]}")
            except Exception as e:
                print(f"   ⚠️ GitHub API 查询失败: {e}")

            def _completed_runs(paths):
                """报告日内、已完成、排除当前 run、按创建时间倒序"""
                return sorted(
                    [r for r in runs
                     if r.get("path") in paths
                     and r.get("status") == "completed"
                     and str(r.get("id")) != current_run_id
                     and (r.get("created_at") or "").startswith(report_day)],
                    key=lambda r: r.get("created_at") or "",
                    reverse=True,
                )
            
            # 检查博客生成工作流
            try:
                blog_runs = _completed_runs(BLOG_WORKFLOW_PATHS)
                if blog_runs:
                    latest_blog = blog_runs[0]
                    result["gh_blog_success"] = latest_blog.get("conclusion") == "success"
                    result["gh_blog_run_time"] = latest_blog.get("created_at", "")
                else:
                    result["gh_blog_success"] = None  # 无已完成的工作流
            except Exception as e:
                print(f"   ⚠️ GitHub 博客工作流查询失败: {e}")
                result["gh_blog_success"] = None

            # 检查日报工作流（精确路径，排除正在运行的当前实例）
            try:
                report_runs = _completed_runs(REPORT_WORKFLOW_PATHS)
                if report_runs:
                    latest_report = report_runs[0]
                    result["gh_report_success"] = latest_report.get("conclusion") == "success"
                    print(f"   📋 日报工作流最新完成: {latest_report.get('display_title', 'N/A')} -> {latest_report.get('conclusion', 'N/A')}")
                else:
                    result["gh_report_success"] = None
                    print(f"   ⚠️ 未找到已完成的日报工作流（可能正在运行中）")
            except Exception as e:
                print(f"   ⚠️ GitHub 日报工作流查询失败: {e}")
                result["gh_report_success"] = None

            # 社媒分发工作流：失败是真实事件，转为告警而非被日报状态吞掉
            try:
                social_runs = _completed_runs(SOCIAL_WORKFLOW_PATHS)
                if social_runs:
                    latest_social = social_runs[0]
                    result["gh_social_success"] = latest_social.get("conclusion") == "success"
                    if not result["gh_social_success"]:
                        print(f"   ⚠️ 社媒分发工作流最近失败: {latest_social.get('display_title', 'N/A')} -> {latest_social.get('conclusion', 'N/A')}")
            except Exception as e:
                print(f"   ⚠️ GitHub 社媒工作流查询失败: {e}")
            
            return result if result else None
            
        except Exception as e:
            print(f"   ⚠️ GitHub Actions API 获取失败: {e}")
        
        return None
    
    def _generate_todos(self, data: dict) -> list:
        """生成高优先级待办列表"""
        todos = []
        
        if data.get("placeholder_articles", 0) > 0:
            todos.append(f"修复 {data['placeholder_articles']} 篇占位符残留文章")
        
        if data.get("empty_links", 0) > 0:
            todos.append(f"处理 {data['empty_links']} 处空链接残留")
        
        if data.get("missing_alt", 0) > 0:
            todos.append(f"补充 {data['missing_alt']} 处图片 Alt 文本")
        
        if data.get("gsc_errors", 0) > 0:
            todos.append(f"修复 GSC 索引错误 {data['gsc_errors']} 个")
        
        if data.get("pending_posts", 0) > 0:
            todos.append(f"审核并发布 {data['pending_posts']} 篇草稿文章")
        
        return todos
    
    def run(self) -> bool:
        """执行日报推送"""
        print("=" * 60)
        print("🌍 ChinaBound Travel 飞书每日日报")
        print("=" * 60)
        
        # 收集数据
        data = self.collect_data()

        # 保存 OKR 快照（计划=今日待办，供日报复盘）
        daily_plan = [{"task": t, "priority": "high", "period": "今日"} for t in data.get("high_priority_todos", [])]
        okr_utils.save_snapshot("daily", okr_utils.period_key("daily"), daily_plan, data)
        
        # 构建卡片
        print("📝 构建飞书卡片...")
        card = self.build_daily_card(data)
        
        # 发送消息
        print("📤 发送飞书消息...")
        success = self.send_card_message(card)
        
        # 保存日报记录
        self._save_report(data)
        
        print("=" * 60)
        print(f"{'✅ 日报推送完成' if success else '❌ 日报推送失败'}")
        print("=" * 60)
        
        return success
    
    def _save_report(self, data: dict):
        """保存日报记录"""
        reports_dir = BLOG_ROOT / "reports" / "feishu_daily"
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        report_path = reports_dir / f"report_{datetime.now().strftime('%Y-%m-%d')}.json"
        
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"📁 日报已保存: {report_path}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="ChinaBound Travel 飞书每日日报推送")
    parser.add_argument("--dry-run", action="store_true",
                        help="仅采集数据并打印日报卡片与待办，不发送飞书")
    args = parser.parse_args()

    reporter = FeishuDailyReporter()

    if args.dry_run:
        print("=" * 60)
        print("🧪 DRY RUN - 仅预览日报内容，不发送飞书")
        print("=" * 60)
        data = reporter.collect_data()
        card = reporter.build_daily_card(data)
        print(json.dumps(card, ensure_ascii=False, indent=2))
        print("\n📌 高优先级待办：")
        todos = data.get("high_priority_todos", [])
        if todos:
            for i, t in enumerate(todos, 1):
                print(f"  {i}. {t}")
        else:
            print("  ✅ 所有正常，无待处理问题")
        return 0

    success = reporter.run()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
