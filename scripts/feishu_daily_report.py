#!/usr/bin/env python3
"""
feishu_daily_report.py - ChinaBound Travel 飞书每日日报推送
功能：流量、内容、联盟、运维四大核心板块数据推送
版本：v2.0 - 完整版日报模板
"""

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
CLOUDFLARE_API_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN", "")
CLOUDFLARE_ZONE_ID = os.environ.get("CLOUDFLARE_ZONE_ID", "")
# GA4配置
GA4_API_KEY = os.environ.get("GA4_API_KEY", "")
GA4_PROPERTY_ID = os.environ.get("GA4_PROPERTY_ID", "541752321")
GA4_SERVICE_ACCOUNT_JSON = os.environ.get("GA4_SERVICE_ACCOUNT_JSON", "")

# MailerLite 订阅配置
MAILERLITE_API_TOKEN = os.environ.get("MAILERLITE_API_TOKEN", "")

# GitHub 配置
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = "fys2388/chinaboundtravel"

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
        traffic_status = "🟢" if data.get("visitors", 0) > 0 else "⚪"
        content_status = "🟢" if data.get("total_content_issues", 0) == 0 else "🟡"
        affiliate_status = "🟢" if data.get("affiliate_revenue", 0) > 0 else "⚪"
        search_status = "🟢" if data.get("gsc_errors", 0) == 0 else "🟡"
        
        # ===== 1. 流量总览 =====
        # 格式化会话时长
        avg_dur = data.get("avg_session_duration", 0)
        if avg_dur > 60:
            dur_str = f"{avg_dur // 60}分{avg_dur % 60}秒"
        else:
            dur_str = f"{avg_dur}秒"
        
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
        
        # ===== 2. 搜索表现 =====
        # Top 搜索关键词
        top_keywords = data.get("top_keywords", [])
        kw_lines = ["暂无数据"]
        if top_keywords:
            kw_lines = [f"{i}. {kw['keyword']} (曝光 {kw['impressions']}, 点击 {kw['clicks']}, CTR {kw['ctr']}%, 排名 {kw['position']})" for i, kw in enumerate(top_keywords[:5], 1)]
        kw_str = "\n".join(kw_lines)
        
        # ===== 3. 内容质量巡检 =====
        
        # ===== 4. 联盟变现 =====
        
        # ===== 5. 订阅数据 =====
        
        # ===== 6. 自动化运维状态 =====
        gh_blog = data.get("gh_blog_success")
        gh_report = data.get("gh_report_success")
        blog_icon = "✅" if gh_blog == True else ("❌" if gh_blog == False else "⚪")
        report_icon = "✅" if gh_report == True else ("❌" if gh_report == False else "⚪")
        
        # 高优先级待办
        todos = data.get("high_priority_todos", [])
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
- 日环比: {data.get('visitors_trend', 'N/A')} ｜ 周同比: {data.get('week_trend', 'N/A')} ｜ 月同比: {data.get('month_trend', 'N/A')}"""
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
                        "content": f"""**🔍 2. 搜索表现（Google Search Console | {report_date}）** {search_status}

| 指标 | 数据 | 指标 | 数据 |
| --- | --- | --- | --- |
| 已收录页面 | {data.get('indexed_pages', 'N/A')} 页 | 索引错误 | {data.get('gsc_errors', 0)} 个 |
| 搜索曝光 | {data.get('gsc_impressions', 0):,} 次 | 搜索点击 | {data.get('gsc_clicks', 0):,} 次 |
| 点击率 CTR | {data.get('gsc_ctr', 0):.2f}% | | |

**📈 GSC 同比趋势**: 周同比 {data.get('gsc_week_trend', 'N/A')} ｜ 月同比 {data.get('gsc_month_trend', 'N/A')}"""
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
                
                # === 4. 联盟变现数据 ===
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"""**💰 4. 联盟变现数据（{report_date}）** {affiliate_status}

🏨 **Travelpayouts（酒店/航班）**
| 指标 | 数据 |
| --- | --- |
| 昨日点击 | {data.get('tp_clicks', 0)} 次 |
| 昨日订单 | {data.get('tp_bookings', 0)} 单 |
| 昨日佣金 | ${data.get('tp_revenue', 0):.2f} |

🛡️ **NordVPN / NordPass**
| 指标 | 数据 |
| --- | --- |
| 昨日点击 | {data.get('nord_clicks', 0)} 次 |
| 昨日转化 | {data.get('nord_conversions', 0)} 单 |
| 昨日佣金 | ${data.get('nord_revenue', 0):.2f} |

🏨 **Klook（玩乐）** — 需手动查看 Klook Partner 后台
🌐 **Booking.com（酒店）** — 需手动查看 Booking Affiliate 后台
🛡️ **WorldNomads（保险）** — 需手动查看 Partner 后台

**合计昨日佣金**: ${data.get('affiliate_revenue', 0):.2f} ｜ **Top转化页面**: {data.get('top_converting_article', 'N/A')}"""
                    }
                },
                {"tag": "hr"},
                
                # === 5. 邮件订阅 ===
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"""**📧 5. 邮件订阅（MailerLite）**

| 指标 | 数据 |
| --- | --- |
| 总订阅人数 | {data.get('ml_total_subscribers', 'N/A')} 人 |
| 昨日新增 | {data.get('ml_new_subscribers', 0)} 人 |"""
                    }
                },
                {"tag": "hr"},
                
                # === 6. 自动化运维状态 ===
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"""**⚙️ 6. 自动化运维状态**

| 工作流 | 状态 |
| --- | --- |
| 博客自动生成（Hugo） | {blog_icon} {'成功' if gh_blog == True else ('失败' if gh_blog == False else '未运行/未配置')} |
| 日报自动推送（Feishu） | {report_icon} {'成功' if gh_report == True else ('失败' if gh_report == False else '未运行/未配置')} |

🟢 网站状态: {'正常' if data.get('site_up') else '异常'} | ⏱️ 响应: {data.get('response_time', 0):.0f}ms"""
                    }
                },
                {"tag": "hr"},
                
                # === 7. 高优先级待办 ===
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"""**📌 今日高优先级待办**

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
        
        return card
    
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
            "nord_clicks": 0,
            "nord_conversions": 0,
            "nord_revenue": 0.0,
            "top_converting_article": "N/A",
            "affiliate_revenue": 0.0,
            # 订阅数据
            "ml_total_subscribers": 0,
            "ml_new_subscribers": 0,
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
        if gsc_data:
            data.update(gsc_data)
            print(f"   ✅ GSC数据: 曝光 {data['gsc_impressions']:,} 次, 点击 {data['gsc_clicks']:,} 次")
        else:
            data["data_status"].append("GSC数据获取失败")

        # 4. 本地内容质量巡检
        content_issues = self._scan_content_quality()
        data.update(content_issues)
        print(f"   ✅ 内容巡检: {data['total_posts']} 篇, 占位符 {data['placeholder_articles']}, 空链接 {data['empty_links']}, Alt缺失 {data['missing_alt']}")
        
        # 4. Travelpayouts 数据
        tp_data = self._fetch_travelpayouts()
        if tp_data:
            data.update(tp_data)
            print(f"   ✅ Travelpayouts: {data['tp_clicks']} 点击, {data['tp_bookings']} 订单, ${data['tp_revenue']:.2f}")
        else:
            data["data_status"].append("Travelpayouts联盟数据未配置")
        
        # 5. MailerLite 订阅数据
        ml_data = self._fetch_mailerlite()
        if ml_data:
            data.update(ml_data)
            print(f"   ✅ MailerLite: 总订阅 {data.get('ml_total_subscribers', 'N/A')} 人, 昨日新增 {data.get('ml_new_subscribers', 0)} 人")
        else:
            data["data_status"].append("MailerLite订阅数据未配置（需设置 MAILERLITE_API_TOKEN）")
        
        # 6. GitHub Actions 工作流状态
        gh_data = self._fetch_github_actions()
        if gh_data:
            data.update(gh_data)
            print(f"   ✅ GitHub Actions: 博客生成 {'成功' if data.get('gh_blog_success') else '失败'}, 日报 {'成功' if data.get('gh_report_success') else '失败'}")
        
        # 7. 生成高优先级待办
        data["high_priority_todos"] = self._generate_todos(data)
        
        # 6. 统计总问题数
        data["total_content_issues"] = data["placeholder_articles"] + data["empty_links"] + data["missing_alt"]
        
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
        if not GA4_SERVICE_ACCOUNT_JSON or not HAS_GOOGLE_AUTH:
            print("   ⚠️ GSC: 服务账号未配置")
            return None
        
        try:
            from googleapiclient.discovery import build
            
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            two_days_ago = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
            three_days_ago = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
            # 周同比：上周同天
            last_week_start = (datetime.now() - timedelta(days=8)).strftime("%Y-%m-%d")
            last_week_end = (datetime.now() - timedelta(days=8)).strftime("%Y-%m-%d")
            # 月同比：上月同天
            last_month_start = (datetime.now() - timedelta(days=32)).strftime("%Y-%m-%d")
            last_month_end = (datetime.now() - timedelta(days=32)).strftime("%Y-%m-%d")
            
            print(f"   🔍 正在调用 GSC API ({yesterday})...")
            
            service_account_info = json.loads(GA4_SERVICE_ACCOUNT_JSON)
            credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=["https://www.googleapis.com/auth/webmasters.readonly"]
            )
            credentials.refresh(Request())
            
            service = build("searchconsole", "v1", credentials=credentials)
            site_url = "https://chinaboundtravel.com"
            
            def gsc_query(start, end, dimensions=None, row_limit=10):
                """封装 GSC 查询"""
                body = {
                    "siteUrl": site_url,
                    "startDate": start,
                    "endDate": end,
                    "type": "web",
                    "rowLimit": row_limit,
                    "dataState": "final"
                }
                if dimensions:
                    body["dimensions"] = dimensions
                return service.searchanalytics().query(body=body).execute()
            
            # === 昨日总览 ===
            response = gsc_query(three_days_ago, yesterday)
            print(f"   ✅ GSC API 调用成功")
            
            yesterday_impressions = 0
            yesterday_clicks = 0
            yesterday_ctr = 0.0
            
            if "rows" in response:
                # 分离昨日数据（按日期拆分会太复杂，用3天总量/3近似）
                # 改用精确的2天范围获取昨日
                yesterday_response = gsc_query(yesterday, yesterday)
                if "rows" in yesterday_response:
                    yesterday_impressions = int(yesterday_response["rows"][0].get("impressions", 0)) if yesterday_response["rows"] else 0
                    yesterday_clicks = int(yesterday_response["rows"][0].get("clicks", 0)) if yesterday_response["rows"] else 0
                    yesterday_ctr = round(float(yesterday_response["rows"][0].get("ctr", 0)) * 100, 2) if yesterday_response["rows"] else 0.0
                else:
                    # 回退到3天总量
                    for row in response["rows"]:
                        yesterday_impressions += int(row.get("impressions", 0))
                        yesterday_clicks += int(row.get("clicks", 0))
            
            # === 周同比 ===
            week_impressions = 0
            try:
                week_resp = gsc_query(last_week_start, last_week_end)
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
                month_resp = gsc_query(last_month_start, last_month_end)
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
            
            # === 获取 sitemap 信息 ===
            indexed_pages = "N/A"
            try:
                sitemaps = service.sitemaps().list(siteUrl=site_url).execute()
                if sitemaps.get("sitemap"):
                    indexed_pages = len(sitemaps["sitemap"])
            except Exception:
                pass
            
            # GSC 错误数（简化为0，详细错误需 urlInspection API）
            gsc_errors = 0
            
            print(f"   📊 GSC数据: 曝光 {yesterday_impressions:,}, 点击 {yesterday_clicks:,}, CTR {yesterday_ctr}%, 关键词 {len(top_keywords)} 个")
            
            return {
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
            print(f"   ⚠️ GSC API 获取失败: {e}")
        
        return None
    
    def _get_ga4_auth_headers(self) -> dict:
        """获取 GA4 API 认证 headers（复用认证逻辑）"""
        if not GA4_SERVICE_ACCOUNT_JSON or not HAS_GOOGLE_AUTH:
            print("   ⚠️ GA4: 服务账号未配置")
            return None
        
        try:
            service_account_info = json.loads(GA4_SERVICE_ACCOUNT_JSON)
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
            seven_days_ago = (datetime.now() - timedelta(days=8)).strftime("%Y-%m-%d")
            last_week_range = (datetime.now() - timedelta(days=8)).strftime("%Y-%m-%d")
            last_week_end = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
            last_month_range = (datetime.now() - timedelta(days=32)).strftime("%Y-%m-%d")
            last_month_end = (datetime.now() - timedelta(days=1) - timedelta(days=30)).strftime("%Y-%m-%d")
            
            print(f"   🔍 正在调用 GA4 API ({yesterday})...")
            
            headers = self._get_ga4_auth_headers()
            if not headers:
                return None
            
            print("   ✅ GA4 服务账号认证成功")
            
            # === 核心指标：昨日 vs 前日 ===
            core_payload = {
                "dateRanges": [
                    {"startDate": yesterday, "endDate": yesterday},
                    {"startDate": two_days_ago, "endDate": two_days_ago}
                ],
                "metrics": [
                    {"name": "activeUsers"},
                    {"name": "sessions"},
                    {"name": "screenPageViews"},
                    {"name": "engagementRate"},
                    {"name": "averageSessionDuration"},
                    {"name": "bounceRate"}
                ],
                "dimensions": []
            }
            
            result = self._ga4_run_report(headers, core_payload)
            if not result or "rows" not in result:
                print("   ⚠️ GA4 核心指标返回空数据")
                return None
            
            rows = result.get("rows", [])
            yesterday_users = int(rows[0].get("metricValues", [{}])[0].get("value", "0"))
            yesterday_sessions = int(rows[0].get("metricValues", [{}])[1].get("value", "0"))
            yesterday_pageviews = int(rows[0].get("metricValues", [{}])[2].get("value", "0"))
            yesterday_engagement = self._parse_ga4_rate(rows[0].get("metricValues", [{}])[3].get("value", "0"))
            yesterday_avg_duration = int(float(rows[0].get("metricValues", [{}])[4].get("value", "0")))
            yesterday_bounce = self._parse_ga4_rate(rows[0].get("metricValues", [{}])[5].get("value", "0"))
            
            two_days_ago_users = int(rows[1].get("metricValues", [{}])[0].get("value", "0"))
            
            day_trend = "N/A"
            if two_days_ago_users > 0:
                change = ((yesterday_users - two_days_ago_users) / two_days_ago_users) * 100
                day_trend = f"+{change:.1f}%" if change >= 0 else f"{change:.1f}%"
            
            print(f"   📊 GA4 核心数据: {yesterday_users} 访客, {yesterday_sessions} 会话, 跳出率 {yesterday_bounce}%")
            
            # === 周同比（昨日 vs 上周同日） ===
            week_payload = {
                "dateRanges": [
                    {"startDate": last_week_range, "endDate": last_week_end}
                ],
                "metrics": [{"name": "activeUsers"}],
                "dimensions": []
            }
            week_result = self._ga4_run_report(headers, week_payload)
            week_users = 0
            if week_result and "rows" in week_result:
                week_users = int(week_result["rows"][0].get("metricValues", [{}])[0].get("value", "0"))
            # 周同比只需7天中对应日数据，简化为7天均值对比
            week_avg = week_users // 7 if week_users > 0 else 0
            week_trend = "N/A"
            if week_avg > 0:
                w_change = ((yesterday_users - week_avg) / week_avg) * 100
                week_trend = f"+{w_change:.1f}%" if w_change >= 0 else f"{w_change:.1f}%"
            
            # === 月同比（昨日 vs 30天前） ===
            month_payload = {
                "dateRanges": [
                    {"startDate": last_month_range, "endDate": last_month_end}
                ],
                "metrics": [{"name": "activeUsers"}],
                "dimensions": []
            }
            month_result = self._ga4_run_report(headers, month_payload)
            month_total = 0
            if month_result and "rows" in month_result:
                month_total = int(month_result["rows"][0].get("metricValues", [{}])[0].get("value", "0"))
            month_avg = month_total // 30 if month_total > 0 else 0
            month_trend = "N/A"
            if month_avg > 0:
                m_change = ((yesterday_users - month_avg) / month_avg) * 100
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
            print(f"   ⚠️ GA4 API 获取失败: {e}")
        
        return None
    
    def _parse_ga4_rate(self, value: str) -> float:
        """解析 GA4 返回的比率值（如 0.6543 → 65.4%）"""
        try:
            return round(float(value) * 100, 1)
        except:
            return 0.0
    
    def _scan_content_quality(self) -> dict:
        """扫描本地内容质量"""
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
        
        today = datetime.now().date()
        today_str = today.strftime("%Y-%m-%d")
        
        for post in posts:
            try:
                content = post.read_text(encoding='utf-8')
                
                # 检查是否今日新发（根据文件名日期前缀判断）
                try:
                    if post.name.startswith(today_str):
                        result["new_posts"] += 1
                except:
                    pass
                
                # 检查是否草稿
                if "_draft" in post.name.lower() or post.name.startswith("draft"):
                    result["pending_posts"] += 1
                
                # 检查占位符
                if re.search(r'#TP_[A-Z_]+#|#VPN_[A-Z_]+#|PLACEHOLDER', content, re.IGNORECASE):
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
        """获取 Travelpayouts 数据（昨日）"""
        if not TRAVELPAYOUTS_API_TOKEN:
            print("   ⚠️ Travelpayouts API Token 未配置")
            return None
        
        try:
            url = "https://api.travelpayouts.com/statistics/v1/execute_query"
            headers = {
                "X-Access-Token": TRAVELPAYOUTS_API_TOKEN,
                "Content-Type": "application/json"
            }
            
            # 只获取昨日数据
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            
            payload = {
                "fields": ["action_id", "sub_id", "price_usd", "paid_profit_usd", "state", "date", "type", "host"],
                "filters": [
                    {"field": "date", "op": "eq", "value": yesterday}
                ],
                "sort": [{"field": "paid_profit_usd", "order": "desc"}],
                "offset": 0,
                "limit": 100
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                results = result.get("results", [])
                
                clicks = 0
                bookings = 0
                revenue = 0.0
                top_article = "N/A"
                max_revenue = 0
                
                for item in results:
                    # 计算点击
                    if item.get("type") in ["redirect", "init"]:
                        clicks += 1
                    
                    # 计算已支付订单
                    if item.get("state") == "paid":
                        bookings += 1
                        profit = float(item.get("paid_profit_usd", 0) or 0)
                        revenue += profit
                        
                        if profit > max_revenue:
                            max_revenue = profit
                            sub_id = item.get("sub_id", "")
                            if sub_id:
                                top_article = f"/posts/{sub_id}/"
                
                return {
                    "tp_clicks": clicks,
                    "tp_bookings": bookings,
                    "tp_revenue": round(revenue, 2),
                    "top_converting_article": top_article,
                    "affiliate_revenue": round(revenue, 2)
                }
                
        except Exception as e:
            print(f"   ⚠️ Travelpayouts API 获取失败: {e}")
        
        return None
    
    def _fetch_mailerlite(self) -> dict:
        """获取 MailerLite 订阅数据（总订阅数 + 昨日新增）"""
        if not MAILERLITE_API_TOKEN:
            print("   ⚠️ MailerLite API Token 未配置")
            return None
        
        try:
            headers = {
                "Authorization": f"Bearer {MAILERLITE_API_TOKEN}",
                "Content-Type": "application/json"
            }
            
            # 获取总订阅者数
            total_subscribers = 0
            try:
                resp = requests.get(
                    "https://connect.mailerlite.com/api/subscribers",
                    headers=headers,
                    params={"limit": 1},
                    timeout=15
                )
                if resp.status_code == 200:
                    data = resp.json()
                    total_subscribers = data.get("meta", {}).get("total", 0)
            except Exception as e:
                print(f"   ⚠️ MailerLite 总订阅获取失败: {e}")
            
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
                "ml_total_subscribers": total_subscribers,
                "ml_new_subscribers": new_subscribers
            }
            
        except Exception as e:
            print(f"   ⚠️ MailerLite API 获取失败: {e}")
        
        return None
    
    def _fetch_github_actions(self) -> dict:
        """获取 GitHub Actions 工作流运行状态（博客生成 + 日报推送）"""
        if not GITHUB_TOKEN:
            print("   ⚠️ GitHub Token 未配置")
            return None
        
        try:
            headers = {
                "Authorization": f"Bearer {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            base_url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/runs"
            yesterday = (datetime.now() - timedelta(days=1)).isoformat()
            
            result = {}
            
            # 检查博客生成工作流
            try:
                resp = requests.get(
                    base_url,
                    headers=headers,
                    params={"per_page": 10},
                    timeout=15
                )
                if resp.status_code == 200:
                    runs = resp.json().get("workflow_runs", [])
                    blog_runs = [r for r in runs if "hugo" in r.get("name", "").lower() or "blog" in r.get("name", "").lower()]
                    if blog_runs:
                        latest_blog = blog_runs[0]
                        result["gh_blog_success"] = latest_blog.get("conclusion") == "success"
                        result["gh_blog_run_time"] = latest_blog.get("created_at", "")
                    else:
                        result["gh_blog_success"] = None  # 无工作流运行
            except Exception as e:
                print(f"   ⚠️ GitHub 博客工作流查询失败: {e}")
                result["gh_blog_success"] = None
            
            # 检查日报工作流
            try:
                report_runs = [r for r in runs if "daily" in r.get("name", "").lower() or "feishu" in r.get("name", "").lower()]
                if report_runs:
                    latest_report = report_runs[0]
                    result["gh_report_success"] = latest_report.get("conclusion") == "success"
                else:
                    result["gh_report_success"] = None
            except:
                result["gh_report_success"] = None
            
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
            todos.append(f"补充 {data['missing_alt']} 篇图片 Alt 文本")
        
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
    reporter = FeishuDailyReporter()
    success = reporter.run()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
