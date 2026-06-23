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

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ==================== 配置 ====================
SCRIPT_DIR = Path(__file__).parent.resolve()
BLOG_ROOT = SCRIPT_DIR.parent
CONTENT_DIR = BLOG_ROOT / "content"
POSTS_DIR = CONTENT_DIR / "posts"
CONFIG_DIR = BLOG_ROOT / "config"

# 飞书配置
FEISHU_WEBHOOK_URL = os.environ.get("FEISHU_WEBHOOK_URL", "")
FEISHU_SECRET = os.environ.get("FEISHU_SECRET", "")

# 如果环境变量未设置，尝试从 .env 文件读取
if not FEISHU_WEBHOOK_URL:
    try:
        from dotenv import load_dotenv
        load_dotenv()
        FEISHU_WEBHOOK_URL = os.environ.get("FEISHU_WEBHOOK_URL", "")
        FEISHU_SECRET = os.environ.get("FEISHU_SECRET", "")
    except:
        pass

# API配置
TRAVELPAYOUTS_API_TOKEN = os.environ.get("TRAVELPAYOUTS_API_TOKEN", "")
TRAVELPAYOUTS_MARKER = os.environ.get("TRAVELPAYOUTS_MARKER", "730795")
CLOUDFLARE_API_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN", "")
CLOUDFLARE_ZONE_ID = os.environ.get("CLOUDFLARE_ZONE_ID", "")
# GA4配置
GA4_API_KEY = os.environ.get("GA4_API_KEY", "")
GA4_PROPERTY_ID = os.environ.get("GA4_PROPERTY_ID", "538482322")


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
        """构建飞书日报卡片 - 完整版"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 状态图标
        traffic_status = "🟢" if data.get("site_up") else "🔴"
        content_status = "🟢" if data.get("total_content_issues", 0) == 0 else "🟡"
        affiliate_status = "🟢" if data.get("affiliate_revenue", 0) > 0 else "⚪"
        search_status = "🟢" if data.get("gsc_errors", 0) == 0 else "🟡"
        
        # Top3 流量页面
        top_pages = data.get("top_pages", [])
        top_pages_str = "暂无数据"
        if top_pages:
            top_pages_lines = []
            for i, page in enumerate(top_pages[:3], 1):
                path = page.get("path", "N/A")
                views = page.get("views", 0)
                top_pages_lines.append(f"{i}. {path} ({views} 次)")
            top_pages_str = "\n".join(top_pages_lines)
        
        # 高优先级待办
        todos = data.get("high_priority_todos", [])
        todos_str = "✅ 所有正常，无待处理问题"
        if todos:
            todos_lines = []
            for i, todo in enumerate(todos[:5], 1):
                todos_lines.append(f"{i}. {todo}")
            todos_str = "\n".join(todos_lines)
        
        # 获取报告数据日期（昨日）
        report_date = data.get("report_date", (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"))
        
        card = {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"🌍 ChinaBound Travel 每日运营日报 | {report_date}（昨日数据）"
                },
                "template": "blue"
            },
            "elements": [
                # === 1. 流量总览 ===
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"""**📊 1. 流量总览（GA4 | {report_date}）** {traffic_status}

| 指标 | 数据 |
| --- | --- |
| 昨日访客数 | {data.get('visitors', 0):,} 人 |
| 昨日请求数 | {data.get('requests', 0):,} 次 |
| 同比前日 | {data.get('visitors_trend', 'N/A')} |

**🔥 Top3 流量页面**
{top_pages_str}"""
                    }
                },
                {"tag": "hr"},
                
                # === 2. 搜索表现 ===
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"""**🔍 2. 搜索表现（Google Search Console）**

| 指标 | 数据 |
| --- | --- |
| 已收录页面 | {data.get('indexed_pages', 'N/A')} 页 |
| 今日搜索曝光 | {data.get('gsc_impressions', 0):,} 次 |
| 今日搜索点击 | {data.get('gsc_clicks', 0):,} 次 |
| 索引错误 | {data.get('gsc_errors', 0)} 个 {search_status if data.get('gsc_errors', 0) == 0 else '⚠️'}"""
                    }
                },
                {"tag": "hr"},
                
                # === 3. 内容质量巡检 ===
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"""**⚠️ 3. 内容质量巡检（本地文件扫描）**

| 指标 | 数量 |
| --- | --- |
| 站点总文章数 | {data.get('total_posts', 0)} 篇 |
| 今日新发 | {data.get('new_posts', 0)} 篇 |
| 未替换占位符 | {data.get('placeholder_articles', 0)} 篇 {data.get('placeholder_articles', 0) > 0 and '❌' or '✅'} |
| 空链接残留 | {data.get('empty_links', 0)} 处 |
| 图片缺失Alt文本 | {data.get('missing_alt', 0)} 处"""
                    }
                },
                {"tag": "hr"},
                
                # === 4. 联盟变现数据 ===
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"""**💰 4. 联盟变现数据（{report_date} 昨日）**

🏨 **Travelpayouts（酒店/活动）**
| 指标 | 数据 |
| --- | --- |
| 昨日点击 | {data.get('tp_clicks', 0)} 次 |
| 昨日订单 | {data.get('tp_bookings', 0)} 单 |
| 昨日佣金 | ${data.get('tp_revenue', 0):.2f} |

🌐 **NordVPN / NordPass**
| 指标 | 数据 |
| --- | --- |
| 昨日点击 | {data.get('nord_clicks', 0)} 次 |
| 昨日转化 | {data.get('nord_conversions', 0)} 单 |
| 昨日佣金 | ${data.get('nord_revenue', 0):.2f} |

**Top 转化页面**: {data.get('top_converting_article', 'N/A')}"""
                    }
                },
                {"tag": "hr"},
                
                # === 5. 高优先级待办 ===
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"""**📌 今日高优先级待办**

{todos_str}"""
                    }
                },
                
                # === 运维状态 ===
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": f"🟢 网站状态: {'正常' if data.get('site_up') else '异常'} | ⏱️ 响应: {data.get('response_time', 0):.0f}ms | 📁 详情: reports/feishu_daily/"
                        }
                    ]
                }
            ]
        }
        
        return card
    
    def collect_data(self) -> dict:
        """收集日报数据 - 完整版"""
        data = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "site_up": True,
            "response_time": 0,
            # 流量数据
            "visitors": 0,
            "requests": 0,
            "visitors_trend": "N/A",
            "top_pages": [],
            # 搜索数据
            "indexed_pages": "N/A",
            "gsc_impressions": 0,
            "gsc_clicks": 0,
            "gsc_errors": 0,
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
            # 高优先级待办
            "high_priority_todos": []
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
        
        # 2. GA4 流量数据（优先）
        ga4_data = self._fetch_ga4()
        if ga4_data:
            data.update(ga4_data)
            print(f"   ✅ GA4流量数据: {data['visitors']:,} 访客, {data['requests']:,} 请求")
            print(f"   ✅ Top页面: {len(data['top_pages'])} 个")
        else:
            # 降级到 Cloudflare
            cf_data = self._fetch_cloudflare()
            if cf_data:
                data.update(cf_data)
                print(f"   ✅ Cloudflare流量数据: {data['visitors']:,} 访客, {data['requests']:,} 请求")
        
        # 3. 本地内容质量巡检
        content_issues = self._scan_content_quality()
        data.update(content_issues)
        print(f"   ✅ 内容巡检: {data['total_posts']} 篇, 占位符 {data['placeholder_articles']}, 空链接 {data['empty_links']}, Alt缺失 {data['missing_alt']}")
        
        # 4. Travelpayouts 数据
        tp_data = self._fetch_travelpayouts()
        if tp_data:
            data.update(tp_data)
            print(f"   ✅ Travelpayouts: {data['tp_clicks']} 点击, {data['tp_bookings']} 订单, ${data['tp_revenue']:.2f}")
        
        # 5. 生成高优先级待办
        data["high_priority_todos"] = self._generate_todos(data)
        
        # 6. 统计总问题数
        data["total_content_issues"] = data["placeholder_articles"] + data["empty_links"] + data["missing_alt"]
        
        return data
    
    def _fetch_cloudflare(self) -> dict:
        """获取 Cloudflare 流量数据"""
        if not CLOUDFLARE_API_TOKEN or not CLOUDFLARE_ZONE_ID:
            print("   ⚠️ Cloudflare API Token 未配置")
            return None
        
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(days=1)
            
            url = f"https://api.cloudflare.com/client/v4/zones/{CLOUDFLARE_ZONE_ID}/analytics/dashboard"
            headers = {
                "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
                "Content-Type": "application/json"
            }
            
            params = {
                "since": int((end_time - timedelta(hours=24)).timestamp()),
                "until": int(end_time.timestamp()),
                "continuous": "true"
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    result_info = result.get("result", {})
                    timeseries = result_info.get("timeseriesGroup", [])
                    
                    # 计算今日请求数
                    today_requests = 0
                    yesterday_requests = 0
                    
                    for group in timeseries:
                        if group.get("维度") == "requests":
                            for ts in group.get("timeseries", []):
                                ts_date = datetime.fromtimestamp(ts.get("since", 0))
                                ts_requests = ts.get("requests", 0)
                                if ts_date.date() == datetime.now().date():
                                    today_requests += ts_requests
                                elif ts_date.date() == (datetime.now() - timedelta(days=1)).date():
                                    yesterday_requests += ts_requests
                    
                    # 获取 Top 页面
                    top_pages = []
                    for group in timeseries:
                        if group.get("维度") == "statusCode":
                            for page_data in group.get("timeseries", []):
                                if page_data.get("since"):
                                    continue
                                # 简化处理，实际应该用 GraphQL API 获取页面维度
                            
                    # 获取 Top 页面（从 timeseries 获取）
                    for group in timeseries:
                        if "page" in str(group.get("维度", "")).lower():
                            for item in group.get("timeseries", []):
                                if item.get("page"):
                                    path = item["page"]
                                    views = item.get("requests", 0)
                                    if views > 0:
                                        top_pages.append({"path": path, "views": views})
                    
                    # 按访问量排序
                    top_pages = sorted(top_pages, key=lambda x: x.get("views", 0), reverse=True)[:10]
                    
                    # 计算同比
                    trend = "N/A"
                    if yesterday_requests > 0:
                        change = ((today_requests - yesterday_requests) / yesterday_requests) * 100
                        trend = f"+{change:.1f}%" if change >= 0 else f"{change:.1f}%"
                    
                    return {
                        "visitors": today_requests,
                        "requests": today_requests,
                        "visitors_trend": trend,
                        "top_pages": top_pages
                    }
                        
        except Exception as e:
            print(f"   ⚠️ Cloudflare API 获取失败: {e}")
        
        return None
    
    def _fetch_ga4(self) -> dict:
        """获取 GA4 数据（昨日自然日）"""
        if not GA4_API_KEY or not GA4_PROPERTY_ID:
            print("   ⚠️ GA4 API Key 或 Property ID 未配置")
            return None
        
        try:
            # 昨日自然日数据
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            two_days_ago = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
            
            # 获取昨日访客和页面浏览
            url = f"https://analyticsdata.googleapis.com/v1beta/properties/{GA4_PROPERTY_ID}:runReport"
            headers = {
                "Authorization": f"Bearer {GA4_API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "dateRanges": [
                    {
                        "startDate": yesterday,
                        "endDate": yesterday
                    },
                    {
                        "startDate": two_days_ago,
                        "endDate": two_days_ago
                    }
                ],
                "metrics": [
                    {"name": "activeUsers"},
                    {"name": "sessions"},
                    {"name": "screenPageViews"}
                ],
                "dimensions": []
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                rows = result.get("rows", [])
                
                if rows:
                    yesterday_users = int(rows[0].get("metricValues", [{}])[0].get("value", "0"))
                    yesterday_sessions = int(rows[0].get("metricValues", [{}])[1].get("value", "0"))
                    yesterday_pageviews = int(rows[0].get("metricValues", [{}])[2].get("value", "0"))
                    
                    two_days_ago_users = int(rows[1].get("metricValues", [{}])[0].get("value", "0"))
                    
                    trend = "N/A"
                    if two_days_ago_users > 0:
                        change = ((yesterday_users - two_days_ago_users) / two_days_ago_users) * 100
                        trend = f"+{change:.1f}%" if change >= 0 else f"{change:.1f}%"
                    
                    # 获取昨日 Top 页面
                    top_pages_url = f"https://analyticsdata.googleapis.com/v1beta/properties/{GA4_PROPERTY_ID}:runReport"
                    top_pages_payload = {
                        "dateRanges": [
                            {
                                "startDate": yesterday,
                                "endDate": yesterday
                            }
                        ],
                        "metrics": [
                            {"name": "screenPageViews"}
                        ],
                        "dimensions": [
                            {"name": "pagePath"}
                        ],
                        "orderBys": [
                            {
                                "metric": {
                                    "metricName": "screenPageViews"
                                },
                                "desc": True
                            }
                        ],
                        "limit": 10
                    }
                    
                    tp_response = requests.post(top_pages_url, headers=headers, json=top_pages_payload, timeout=30)
                    top_pages = []
                    
                    if tp_response.status_code == 200:
                        tp_result = tp_response.json()
                        tp_rows = tp_result.get("rows", [])
                        for row in tp_rows:
                            path = row.get("dimensionValues", [{}])[0].get("value", "")
                            views = int(row.get("metricValues", [{}])[0].get("value", "0"))
                            if path and views > 0:
                                top_pages.append({"path": path, "views": views})
                    
                    return {
                        "report_date": yesterday,
                        "visitors": yesterday_users,
                        "requests": yesterday_pageviews,
                        "visitors_trend": trend,
                        "top_pages": top_pages
                    }
                    
        except Exception as e:
            print(f"   ⚠️ GA4 API 获取失败: {e}")
        
        return None
    
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
        
        for post in posts:
            try:
                content = post.read_text(encoding='utf-8')
                
                # 检查是否今日新发
                try:
                    mtime = datetime.fromtimestamp(post.stat().st_mtime).date()
                    if mtime == today:
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
                
                # 检查图片 Alt 缺失
                if re.search(r'!\[([^\]]*)\]\((?!http)', content):
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
