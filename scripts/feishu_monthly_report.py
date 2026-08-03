#!/usr/bin/env python3
"""
feishu_monthly_report.py - ChinaBound Travel 飞书月度运营报告
功能：月度业务全景复盘，数据汇总与趋势分析
版本：v1.0
"""

import os
import sys
import re

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
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
    HAS_GOOGLE_AUTH = True
except ImportError:
    HAS_GOOGLE_AUTH = False

SCRIPT_DIR = Path(__file__).parent.resolve()
BLOG_ROOT = SCRIPT_DIR.parent

try:
    from dotenv import load_dotenv
    dotenv_path = BLOG_ROOT / ".env"
    load_dotenv(dotenv_path)
except ImportError:
    pass

CONTENT_DIR = BLOG_ROOT / "content"
POSTS_DIR = CONTENT_DIR / "posts"
REPORTS_DIR = BLOG_ROOT / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
LAST_MONTH_DATA_FILE = REPORTS_DIR / "last_month_data.json"

FEISHU_WEBHOOK_URL = os.environ.get("FEISHU_WEBHOOK_URL", "")
FEISHU_SECRET = os.environ.get("FEISHU_SECRET", "")

TRAVELPAYOUTS_API_TOKEN = os.environ.get("TRAVELPAYOUTS_API_TOKEN", "")
TRAVELPAYOUTS_MARKER = os.environ.get("TRAVELPAYOUTS_MARKER", "730795")
GA4_API_KEY = os.environ.get("GA4_API_KEY", "")
GA4_PROPERTY_ID = os.environ.get("GA4_PROPERTY_ID", "541752321")
GA4_SERVICE_ACCOUNT_JSON = os.environ.get("GA4_SERVICE_ACCOUNT_JSON", "")
MAILERLITE_API_TOKEN = os.environ.get("MAILERLITE_API_TOKEN", "")
GSC_SERVICE_ACCOUNT_JSON = os.environ.get("GSC_SERVICE_ACCOUNT_JSON", "")


class FeishuMonthlyReporter:

    def __init__(self):
        self.webhook_url = FEISHU_WEBHOOK_URL
        self.secret = FEISHU_SECRET
        self.last_month_data = self._load_last_month_data()

    def _load_last_month_data(self) -> dict:
        if LAST_MONTH_DATA_FILE.exists():
            try:
                with open(LAST_MONTH_DATA_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"   ⚠️ 加载上月数据失败: {e}")
        return {}

    def _save_month_data(self, data: dict):
        try:
            save_data = {
                "month_users": data.get("month_users", 0),
                "month_sessions": data.get("month_sessions", 0),
                "month_pageviews": data.get("month_pageviews", 0),
                "month_bounce": data.get("month_bounce", 0),
                "month_revenue": data.get("month_revenue", 0),
                "next_month_plan": data.get("next_month_plan", []),
                "content_data": data.get("content_data", {}),
                "gsc_data": data.get("gsc_data", {}),
                "month_label": data.get("month_label", ""),
            }
            with open(LAST_MONTH_DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)
            print(f"   ✅ 本月数据已保存: {LAST_MONTH_DATA_FILE}")
        except Exception as e:
            print(f"   ⚠️ 保存本月数据失败: {e}")

    def _generate_signature(self, timestamp: str) -> str:
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
                print("✅ 飞书月报推送成功")
                return True
            else:
                print(f"❌ 飞书推送失败: {result.get('msg', 'Unknown error')}")
                return False

        except Exception as e:
            print(f"❌ 飞书推送异常: {e}")
            return False

    def _load_service_account(self, sa_json_str: str):
        if not sa_json_str:
            return None
        try:
            return json.loads(sa_json_str)
        except:
            pass
        try:
            if "\\n" in sa_json_str and "BEGIN PRIVATE KEY" in sa_json_str:
                fixed_json = sa_json_str.replace("\\n", "\n")
                return json.loads(fixed_json)
        except:
            pass
        try:
            sa_path = Path(sa_json_str)
            if sa_path.exists() and sa_path.is_file():
                with open(sa_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"   ⚠️ 服务账号加载失败: {e}")
            return None
        return None

    def _get_ga4_headers(self):
        if not GA4_SERVICE_ACCOUNT_JSON or not HAS_GOOGLE_AUTH:
            print("   ⚠️ GA4: 服务账号未配置")
            return None
        try:
            service_account_info = self._load_service_account(GA4_SERVICE_ACCOUNT_JSON)
            if not service_account_info:
                return None
            credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=["https://www.googleapis.com/auth/analytics.readonly"]
            )
            credentials.refresh(Request())
            return {"Authorization": f"Bearer {credentials.token}", "Content-Type": "application/json"}
        except Exception as e:
            print(f"   ⚠️ GA4 认证失败: {e}")
        return None

    def _ga4_run_report(self, headers: dict, payload: dict):
        url = f"https://analyticsdata.googleapis.com/v1beta/properties/{GA4_PROPERTY_ID}:runReport"
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"   ⚠️ GA4 API 响应 {response.status_code}: {response.text[:200]}")
        except Exception as e:
            print(f"   ⚠️ GA4 API 调用失败: {e}")
        return None

    def _fetch_monthly_ga4(self) -> dict:
        """获取当月GA4数据并与上月对比"""
        headers = self._get_ga4_headers()
        if not headers:
            return None

        today = datetime.now()
        first_of_month = today.replace(day=1)
        last_month_end = first_of_month - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)

        cur_month_start = first_of_month.strftime("%Y-%m-%d")
        cur_month_end = today.strftime("%Y-%m-%d")
        prev_month_start = last_month_start.strftime("%Y-%m-%d")
        prev_month_end = last_month_end.strftime("%Y-%m-%d")

        month_label = today.strftime("%Y年%m月")
        prev_month_label = last_month_start.strftime("%Y年%m月")

        print(f"   🔍 获取 GA4 数据（本月: {cur_month_start} ~ {cur_month_end}）...")
        print(f"   📊 对比月份: {prev_month_start} ~ {prev_month_end}")

        def fetch_range(start, end, extra_metrics=None):
            metrics = [
                {"name": "activeUsers"},
                {"name": "sessions"},
                {"name": "screenPageViews"},
                {"name": "engagementRate"},
                {"name": "averageSessionDuration"},
                {"name": "bounceRate"},
            ]
            if extra_metrics:
                metrics.extend(extra_metrics)
            payload = {
                "dateRanges": [{"startDate": start, "endDate": end}],
                "metrics": metrics
            }
            result = self._ga4_run_report(headers, payload)
            if result and "rows" in result:
                row = result["rows"][0]
                return {
                    "users": int(row.get("metricValues", [{}])[0].get("value", "0")),
                    "sessions": int(row.get("metricValues", [{}])[1].get("value", "0")),
                    "pageviews": int(row.get("metricValues", [{}])[2].get("value", "0")),
                    "engagement": round(float(row.get("metricValues", [{}])[3].get("value", "0")) * 100, 1),
                    "avg_duration": int(float(row.get("metricValues", [{}])[4].get("value", "0"))),
                    "bounce": round(float(row.get("metricValues", [{}])[5].get("value", "0")) * 100, 1),
                }
            return {"users": 0, "sessions": 0, "pageviews": 0, "engagement": 0.0, "avg_duration": 0, "bounce": 0.0}

        cur = fetch_range(cur_month_start, cur_month_end)
        prev = fetch_range(prev_month_start, prev_month_end)

        def calc_change(cur_val, prev_val):
            if prev_val == 0:
                return "-"
            change = round((cur_val - prev_val) / prev_val * 100, 1)
            icon = "📈" if change > 0 else "📉" if change < 0 else "➡️"
            return f"{icon} {abs(change)}%"

        channel_payload = {
            "dateRanges": [{"startDate": cur_month_start, "endDate": cur_month_end}],
            "metrics": [{"name": "activeUsers"}, {"name": "bounceRate"}, {"name": "averageSessionDuration"}],
            "dimensions": [{"name": "sessionDefaultChannelGroup"}],
            "orderBys": [{"metric": {"metricName": "activeUsers"}, "desc": True}],
            "limit": 10
        }
        channel_result = self._ga4_run_report(headers, channel_payload)
        channels = []
        if channel_result and "rows" in channel_result:
            for row in channel_result["rows"]:
                ch_name = row.get("dimensionValues", [{}])[0].get("value", "N/A")
                ch_users = int(row.get("metricValues", [{}])[0].get("value", "0"))
                ch_bounce = round(float(row.get("metricValues", [{}])[1].get("value", "0")) * 100, 1)
                ch_duration = int(float(row.get("metricValues", [{}])[2].get("value", "0")))
                if ch_users > 0:
                    channels.append({"channel": ch_name, "users": ch_users, "bounce": ch_bounce, "duration": ch_duration})

        pages_payload = {
            "dateRanges": [{"startDate": cur_month_start, "endDate": cur_month_end}],
            "metrics": [{"name": "screenPageViews"}, {"name": "averageSessionDuration"}, {"name": "bounceRate"}, {"name": "activeUsers"}],
            "dimensions": [{"name": "pagePath"}, {"name": "pageTitle"}],
            "orderBys": [{"metric": {"metricName": "screenPageViews"}, "desc": True}],
            "limit": 10
        }
        pages_result = self._ga4_run_report(headers, pages_payload)
        top_pages = []
        if pages_result and "rows" in pages_result:
            for row in pages_result["rows"]:
                path = row.get("dimensionValues", [{}])[0].get("value", "")
                title = row.get("dimensionValues", [{}, {}])[1].get("value", "")
                views = int(row.get("metricValues", [{}])[0].get("value", "0"))
                duration = int(float(row.get("metricValues", [{}])[1].get("value", "0")))
                bounce = round(float(row.get("metricValues", [{}])[2].get("value", "0")) * 100, 1)
                users = int(row.get("metricValues", [{}])[3].get("value", "0"))
                if path and views > 0:
                    if not title or title.lower() in ["(not set)", "not set", ""]:
                        title = path.split('/')[-1].replace('-', ' ').title()
                        if not title:
                            title = path
                    title = re.sub(r'^\s*[-|·|\|]\s*ChinaBound Travel\s*[-|·|\|]\s*', '', title, flags=re.IGNORECASE)
                    title = re.sub(r'\s*[-|·|\|]\s*ChinaBound Travel\s*$', '', title, flags=re.IGNORECASE)
                    if len(title) > 40:
                        title = title[:37] + "..."
                    top_pages.append({"path": path, "title": title, "views": views, "duration": duration, "bounce": bounce, "users": users})

        device_payload = {
            "dateRanges": [{"startDate": cur_month_start, "endDate": cur_month_end}],
            "metrics": [{"name": "activeUsers"}, {"name": "sessions"}],
            "dimensions": [{"name": "deviceCategory"}],
            "orderBys": [{"metric": {"metricName": "activeUsers"}, "desc": True}],
            "limit": 5
        }
        device_result = self._ga4_run_report(headers, device_payload)
        devices = []
        if device_result and "rows" in device_result:
            for row in device_result["rows"]:
                dev = row.get("dimensionValues", [{}])[0].get("value", "N/A")
                dev_users = int(row.get("metricValues", [{}])[0].get("value", "0"))
                if dev_users > 0:
                    devices.append({"device": dev, "users": dev_users})

        return {
            "month_label": month_label,
            "prev_month_label": prev_month_label,
            "month_start": cur_month_start,
            "month_end": cur_month_end,
            "month_users": cur["users"],
            "month_sessions": cur["sessions"],
            "month_pageviews": cur["pageviews"],
            "month_bounce": cur["bounce"],
            "month_engagement": cur["engagement"],
            "month_avg_duration": cur["avg_duration"],
            "prev_users": prev["users"],
            "prev_sessions": prev["sessions"],
            "prev_pageviews": prev["pageviews"],
            "prev_bounce": prev["bounce"],
            "prev_avg_duration": prev["avg_duration"],
            "prev_engagement": prev["engagement"],
            "users_change": calc_change(cur["users"], prev["users"]),
            "sessions_change": calc_change(cur["sessions"], prev["sessions"]),
            "pageviews_change": calc_change(cur["pageviews"], prev["pageviews"]),
            "bounce_change": calc_change(cur["bounce"], prev["bounce"]),
            "channels": channels,
            "top_pages": top_pages,
            "devices": devices,
        }

    def _fetch_monthly_travelpayouts(self) -> dict:
        """获取整月Travelpayouts数据"""
        if not TRAVELPAYOUTS_API_TOKEN:
            return None

        try:
            url = "https://api.travelpayouts.com/statistics/v1/execute_query"
            headers = {"X-Access-Token": TRAVELPAYOUTS_API_TOKEN, "Content-Type": "application/json"}

            today = datetime.now()
            first_of_month = today.replace(day=1)
            month_start = first_of_month
            month_end = today

            total_clicks = 0
            total_bookings = 0
            total_revenue = 0.0
            total_inits = 0
            total_searches = 0

            current_date = month_start
            while current_date <= month_end:
                date_str = current_date.strftime("%Y-%m-%d")
                payload = {
                    "fields": ["redirects_count", "inits_count", "searches_count", "paid_actions_count", "paid_profit_usd_sum"],
                    "filters": [{"field": "date", "op": "eq", "value": date_str}],
                    "offset": 0,
                    "limit": 1
                }
                try:
                    response = requests.post(url, headers=headers, json=payload, timeout=30)
                    if response.status_code == 200:
                        result = response.json()
                        rows = result.get("results", [])
                        if rows:
                            row = rows[0]
                            total_clicks += int(row.get("redirects_count", 0) or 0)
                            total_bookings += int(row.get("paid_actions_count", 0) or 0)
                            total_revenue += float(row.get("paid_profit_usd_sum", 0) or 0)
                            total_inits += int(row.get("inits_count", 0) or 0)
                            total_searches += int(row.get("searches_count", 0) or 0)
                except Exception:
                    pass
                current_date += timedelta(days=1)

            return {
                "tp_clicks": total_clicks,
                "tp_bookings": total_bookings,
                "tp_revenue": round(total_revenue, 2),
                "tp_inits": total_inits,
                "tp_searches": total_searches,
            }

        except Exception as e:
            print(f"   ⚠️ Travelpayouts API 获取失败: {e}")
            return None

    def _fetch_gsc_data(self) -> dict:
        if not GSC_SERVICE_ACCOUNT_JSON or not HAS_GOOGLE_AUTH:
            return {"status": "unauthorized", "estimated_pages": len(list(POSTS_DIR.glob("*.md"))) if POSTS_DIR.exists() else 0}

        try:
            service_account_info = self._load_service_account(GSC_SERVICE_ACCOUNT_JSON)
            if not service_account_info:
                return {"status": "unauthorized", "estimated_pages": len(list(POSTS_DIR.glob("*.md"))) if POSTS_DIR.exists() else 0}

            credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=["https://www.googleapis.com/auth/webmasters.readonly"]
            )
            credentials.refresh(Request())

            url = "https://www.googleapis.com/webmasters/v3/sites/sc-domain:chinaboundtravel.com/searchAnalytics/query"
            headers = {"Authorization": f"Bearer {credentials.token}", "Content-Type": "application/json"}
            payload = {
                "startDate": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
                "endDate": datetime.now().strftime("%Y-%m-%d"),
                "dimensions": ["page"],
                "rowLimit": 1000
            }

            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                result = response.json()
                indexed_pages = len(result.get("rows", []))
                return {"status": "authorized", "indexed_pages": indexed_pages, "errors": 0}
            else:
                print(f"   ⚠️ GSC API 响应 {response.status_code}: {response.text[:200]}")

        except Exception as e:
            print(f"   ⚠️ GSC API 获取失败: {e}")

        return {"status": "error", "estimated_pages": len(list(POSTS_DIR.glob("*.md"))) if POSTS_DIR.exists() else 0}

    def _fetch_monthly_mailerlite(self) -> dict:
        if not MAILERLITE_API_TOKEN:
            return {"total_subscribers": 0, "monthly_new_subscribers": 0}

        try:
            headers = {"Authorization": f"Bearer {MAILERLITE_API_TOKEN}", "Content-Type": "application/json"}
            resp = requests.get("https://connect.mailerlite.com/api/subscribers", headers=headers, params={"limit": 1}, timeout=15)
            total_subscribers = int(resp.headers.get("x-total-count", "0")) if resp.status_code == 200 else 0

            today = datetime.now()
            month_start = today.replace(day=1).strftime("%Y-%m-%d")
            month_end = today.strftime("%Y-%m-%d")
            resp_recent = requests.get(
                f"https://connect.mailerlite.com/api/subscribers?filter[date_from]={month_start}&filter[date_to]={month_end}",
                headers=headers, timeout=15
            )
            monthly_new = len(resp_recent.json()) if resp_recent.status_code == 200 else 0

            return {"total_subscribers": total_subscribers, "monthly_new_subscribers": monthly_new}

        except Exception as e:
            print(f"   ⚠️ MailerLite API 获取失败: {e}")
            return {"total_subscribers": 0, "monthly_new_subscribers": 0}

    def _scan_content_quality(self) -> dict:
        result = {
            "total_posts": 0,
            "posts_with_affiliate": 0,
            "posts_with_conflict": 0,
            "posts_without_schema": 0,
            "posts_with_placeholder": 0,
            "category_distribution": {},
            "monthly_new_posts": 0,
        }

        if not POSTS_DIR.exists():
            return result

        posts = list(POSTS_DIR.glob("*.md"))
        result["total_posts"] = len(posts)

        today = datetime.now()
        month_start = today.replace(day=1)

        for post in posts:
            try:
                content = post.read_text(encoding='utf-8')
                mtime = datetime.fromtimestamp(post.stat().st_mtime)
                if mtime >= month_start:
                    result["monthly_new_posts"] += 1

                affiliate_patterns = [r'travelpayouts', r'booking\.com', r'agoda\.com', r'trip\.com', r'klook\.com']
                if any(re.search(p, content, re.IGNORECASE) for p in affiliate_patterns):
                    result["posts_with_affiliate"] += 1

                years_patterns = re.findall(r'(\d+)\s*years?', content, re.IGNORECASE)
                unique_years = set([int(y) for y in years_patterns if y.isdigit()])
                if len(unique_years) > 1:
                    result["posts_with_conflict"] += 1

                front_matter_match = re.search(r'---\n(.*?)\n---', content, re.DOTALL)
                has_schema = False
                if front_matter_match:
                    front_matter = front_matter_match.group(1)
                    if re.search(r'article_schema|structured_data|schema', front_matter, re.IGNORECASE):
                        has_schema = True
                    categories_section = re.search(r'categories:\s*\n((?:\s*-\s*[^\n]+\n?)+)', front_matter)
                    if categories_section:
                        cat_block = categories_section.group(1)
                        cat_items = re.findall(r'-\s*([^\n-]+)', cat_block)
                        for cat in cat_items:
                            cat_clean = cat.strip()
                            cat_clean = re.sub(r'\[.*?\]\(.*?\)', '', cat_clean)
                            if len(cat_clean) > 40:
                                cat_clean = cat_clean[:40]
                            if cat_clean and not re.search(r'[\/\\]', cat_clean):
                                result["category_distribution"][cat_clean] = result["category_distribution"].get(cat_clean, 0) + 1
                if not has_schema:
                    result["posts_without_schema"] += 1

                if re.search(r'\[IMAGE\]|\[TODO\]|\[PLACEHOLDER\]', content, re.IGNORECASE):
                    result["posts_with_placeholder"] += 1

            except Exception:
                pass

        return result

    def _detect_risk_level(self, data: dict) -> dict:
        red_risks = []
        yellow_risks = []

        gsc_data = data.get("gsc_data", {})
        indexed_pages = gsc_data.get("indexed_pages", 0)
        if indexed_pages == 0:
            red_risks.append("Google 零收录，自然搜索流量完全断流")

        tp_revenue = data.get("month_revenue", 0)
        content_data = data.get("content_data", {})
        total_posts = content_data.get("total_posts", 0)
        posts_with_affiliate = content_data.get("posts_with_affiliate", 0)
        coverage = (posts_with_affiliate / max(total_posts, 1)) * 100 if total_posts > 0 else 0
        if tp_revenue == 0 and coverage < 30:
            red_risks.append("联盟佣金为0且链接覆盖率<30%，变现链路缺失")

        posts_with_conflict = content_data.get("posts_with_conflict", 0)
        if posts_with_conflict > 0:
            red_risks.append(f"检测到人设年限冲突（{posts_with_conflict}篇文章）")

        month_users = data.get("month_users", 0)
        prev_users = data.get("prev_users", 0)
        if prev_users > 0 and month_users < prev_users * 0.7:
            yellow_risks.append(f"访客数环比下滑超30%（{month_users} vs {prev_users}）")

        month_bounce = data.get("month_bounce", 0)
        if month_bounce > 60:
            yellow_risks.append(f"跳出率{month_bounce}%偏高")

        total_subscribers = data.get("total_subscribers", 0)
        monthly_new = data.get("monthly_new_subscribers", 0)
        if monthly_new == 0 and total_subscribers > 0:
            yellow_risks.append("邮件订阅新增为零")

        posts_without_schema = content_data.get("posts_without_schema", 0)
        if posts_without_schema > 5:
            yellow_risks.append(f"结构化数据缺失{posts_without_schema}篇")

        return {"red": red_risks, "yellow": yellow_risks}

    def _generate_next_month_plan(self, risks: dict) -> list:
        plan = []
        if risks.get("red"):
            plan.extend([
                {"task": "提交GSC索引，确保新页面收录", "priority": "high", "period": "3天内"},
                {"task": "完成全站联盟链接覆盖", "priority": "high", "period": "本周"},
                {"task": "批量修正人设年限文案", "priority": "high", "period": "3天内"},
            ])
        if risks.get("yellow"):
            plan.extend([
                {"task": "优化跳出率偏高的核心页面", "priority": "medium", "period": "本周"},
                {"task": "上线邮件订阅诱饵", "priority": "medium", "period": "本周"},
                {"task": "补充文章结构化数据", "priority": "medium", "period": "本周"},
            ])
        plan.extend([
            {"task": "发布5篇高转化长尾攻略", "priority": "medium", "period": "本月"},
            {"task": "全量检测内部断链", "priority": "low", "period": "本周"},
        ])
        return plan

    def collect_data(self) -> dict:
        print("📊 收集月报数据...")
        data = {}

        print("1️⃣ 获取 GA4 月度数据...")
        ga4_data = self._fetch_monthly_ga4()
        if ga4_data:
            data.update(ga4_data)

        print("2️⃣ 获取 Travelpayouts 月度数据...")
        tp_data = self._fetch_monthly_travelpayouts()
        if tp_data:
            data.update(tp_data)

        print("3️⃣ 获取 GSC 数据...")
        gsc_data = self._fetch_gsc_data()
        data["gsc_data"] = gsc_data

        print("4️⃣ 获取 MailerLite 月度数据...")
        ml_data = self._fetch_monthly_mailerlite()
        if ml_data:
            data.update(ml_data)

        print("5️⃣ 扫描内容质量...")
        content_data = self._scan_content_quality()
        data["content_data"] = content_data

        print("6️⃣ 检测风险等级...")
        risks = self._detect_risk_level(data)
        data["risks"] = risks

        print("7️⃣ 生成下月计划...")
        next_month_plan = self._generate_next_month_plan(risks)
        data["next_month_plan"] = next_month_plan

        return data

    def build_monthly_card(self, data: dict) -> dict:
        today = datetime.now()
        month_label = data.get("month_label", today.strftime("%Y年%m月"))
        prev_month_label = data.get("prev_month_label", "")
        month_start = data.get("month_start", "")
        month_end = data.get("month_end", "")

        month_users = data.get("month_users", 0)
        month_sessions = data.get("month_sessions", 0)
        month_pageviews = data.get("month_pageviews", 0)
        month_bounce = data.get("month_bounce", 0)
        month_engagement = data.get("month_engagement", 0)
        month_avg_duration = data.get("month_avg_duration", 0)

        prev_users = data.get("prev_users", 0)
        prev_sessions = data.get("prev_sessions", 0)
        prev_pageviews = data.get("prev_pageviews", 0)
        prev_bounce = data.get("prev_bounce", 0)

        users_change = data.get("users_change", "-")
        sessions_change = data.get("sessions_change", "-")
        pageviews_change = data.get("pageviews_change", "-")
        bounce_change = data.get("bounce_change", "-")

        if month_avg_duration > 60:
            dur_str = f"{month_avg_duration // 60}分{month_avg_duration % 60}秒"
        else:
            dur_str = f"{month_avg_duration}秒"

        prev_avg_duration = data.get("prev_avg_duration", 0)
        if prev_avg_duration > 60:
            prev_dur_str = f"{prev_avg_duration // 60}分{prev_avg_duration % 60}秒"
        else:
            prev_dur_str = f"{prev_avg_duration}秒"

        traffic_goal = 2000
        traffic_rate = round(month_users / traffic_goal * 100, 1) if traffic_goal > 0 else 0
        traffic_status = "✅" if month_users >= traffic_goal else "⚠️"

        gsc_data = data.get("gsc_data", {})
        gsc_status = "⚠️ GSC 未授权" if gsc_data.get("status") != "authorized" else "已授权"
        indexed_pages = gsc_data.get("indexed_pages", 0)

        content_data = data.get("content_data", {})
        total_posts = content_data.get("total_posts", 0)
        posts_with_affiliate = content_data.get("posts_with_affiliate", 0)
        coverage = round(posts_with_affiliate / max(total_posts, 1) * 100, 1) if total_posts > 0 else 0
        posts_with_conflict = content_data.get("posts_with_conflict", 0)
        posts_without_schema = content_data.get("posts_without_schema", 0)
        posts_with_placeholder = content_data.get("posts_with_placeholder", 0)
        monthly_new_posts = content_data.get("monthly_new_posts", 0)
        content_goal = 20
        content_rate = round(monthly_new_posts / content_goal * 100, 0) if content_goal > 0 else 0

        channels = data.get("channels", [])
        channel_rows = []
        for c in channels:
            dur_c = f"{c['duration']}秒" if c['duration'] < 60 else f"{c['duration']//60}分{c['duration']%60}秒"
            if c['duration'] >= 30 and c['bounce'] < 60:
                quality = "🟢 优质"
            elif c['duration'] < 15 or c['bounce'] > 80:
                quality = "🔴 较差"
            else:
                quality = "🟡 一般"
            pct = round(c['users'] / max(month_users, 1) * 100, 1)
            channel_rows.append(f"| {c['channel']} | {c['users']} | {pct}% | {c['bounce']}% | {dur_c} | {quality} |")

        top_pages = data.get("top_pages", [])
        page_rows = []
        for i, p in enumerate(top_pages[:10], 1):
            title = p.get('title', p.get('path', ''))
            dur_p = f"{p['duration']}秒" if p['duration'] < 60 else f"{p['duration']//60}分{p['duration']%60}秒"
            anomaly_mark = ""
            if p['duration'] <= 5:
                anomaly_mark = " ⚠️短停留"
            elif p['bounce'] == 100:
                anomaly_mark = " ⚠️全跳出"
            page_rows.append(f"| {i} | {title} | {p['views']} | {dur_p} | {p['bounce']}% |{anomaly_mark} |")

        devices = data.get("devices", [])
        device_total = sum(d["users"] for d in devices)
        device_rows = []
        for d in devices:
            pct = round(d['users'] / max(device_total, 1) * 100, 1)
            icon = "📱" if d['device'].lower() == 'mobile' else "💻" if d['device'].lower() == 'desktop' else "📟"
            device_rows.append(f"| {icon} {d['device']} | {d['users']} | {pct}% |")

        tp_clicks = data.get("tp_clicks", 0)
        tp_bookings = data.get("tp_bookings", 0)
        tp_revenue = data.get("tp_revenue", 0.0)
        tp_inits = data.get("tp_inits", 0)
        tp_searches = data.get("tp_searches", 0)

        total_subscribers = data.get("total_subscribers", 0)
        monthly_new_subscribers = data.get("monthly_new_subscribers", 0)

        cat_dist = content_data.get("category_distribution", {})
        cat_lines = []
        for cat, count in sorted(cat_dist.items(), key=lambda x: x[1], reverse=True):
            pct = round(count / max(total_posts, 1) * 100, 1)
            cat_lines.append(f"- {cat}：{count} 篇 ({pct}%)")

        risks = data.get("risks", {})
        red_risks = risks.get("red", [])
        yellow_risks = risks.get("yellow", [])

        next_month_plan = data.get("next_month_plan", [])
        plan_rows = []
        for item in next_month_plan:
            priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(item["priority"], "⚪")
            period = item.get("period", "本月")
            plan_rows.append(f"| {item['task']} | {priority_icon} | {period} |")

        indexed_status = "🔴" if indexed_pages == 0 else "🟡" if indexed_pages < 10 else "✅"
        coverage_status = "🔴" if coverage < 30 else "🟡" if coverage < 80 else "✅"
        conflict_status = "🔴" if posts_with_conflict > 0 else "✅"
        schema_status = "🟡" if posts_without_schema > 0 else "✅"

        conclusions = []
        if "📉" in users_change:
            conclusions.append("流量环比下滑")
        elif "📈" in users_change:
            conclusions.append("流量环比增长")
        if tp_revenue > 0:
            conclusions.append(f"佣金收入 ${tp_revenue:.2f}")
        if monthly_new_posts >= content_goal:
            conclusions.append("内容产出达标")
        elif monthly_new_posts > 0:
            conclusions.append(f"内容产出{monthly_new_posts}篇")

        conclusion_text = f"📌 {month_label}运营总结：" + "，".join(conclusions) + "。"

        core_table = f"""{conclusion_text}

## 🎯 {month_label} 核心指标看板

### 1. 流量核心指标
| 指标 | {month_label} | {prev_month_label} | 环比 | 月目标 | 达标率 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 访客数 | {month_users} 人 | {prev_users} | {users_change} | {traffic_goal} 人 | {traffic_rate}% {traffic_status} |
| 会话数 | {month_sessions} 次 | {prev_sessions} | {sessions_change} | - | - |
| 页面浏览量 | {month_pageviews} 次 | {prev_pageviews} | {pageviews_change} | - | - |
| 平均停留 | {dur_str} | {prev_dur_str} | - | >40s | - |
| 跳出率 | {month_bounce}% | {prev_bounce}% | {bounce_change} | <60% | - |
| 参与度 | {month_engagement}% | - | - | - | - |

### 2. 设备分布
| 设备 | 用户数 | 占比 |
| :--- | :--- | :--- |
""" + "\n".join(device_rows) + ("\n| - | - | - |" if not device_rows else "")

        channel_table = f"""---
## 🌐 流量渠道分析

### 1. 渠道质量对比
| 流量渠道 | 访客数 | 占比 | 跳出率 | 平均停留 | 质量评级 |
| :--- | :--- | :--- | :--- | :--- | :--- |
""" + "\n".join(channel_rows) + ("\n| - | - | - | - | - | - |" if not channel_rows else "")

        pages_table = f"""### 2. 热门页面 Top10
| 排名 | 页面标题 | 浏览量 | 平均停留 | 跳出率 | 异常标记 |
| :--- | :--- | :--- | :--- | :--- | :--- |
""" + "\n".join(page_rows) + ("\n| - | - | - | - | - | - |" if not page_rows else "")

        seo_section = f"""---
## 🔍 SEO 与基建

- **GSC 状态**：{gsc_status}｜预估可收录 {len(list(POSTS_DIR.glob("*.md"))) if POSTS_DIR.exists() else 0} 页
- **已索引页面**：{indexed_pages} 页
- **联盟链接覆盖率**：{coverage}%（{posts_with_affiliate}/{total_posts}）{coverage_status}
- **人设冲突**：{posts_with_conflict} 篇 {conflict_status}
- **结构化数据**：缺失 {posts_without_schema} 篇 {schema_status}
- **占位符**：{posts_with_placeholder} 篇 ⚠️"""

        affiliate_section = f"""---
## 💸 联盟变现数据

| 指标 | {month_label} | 转化率 |
| :--- | :--- | :--- |
| 链接展示量 | {tp_inits} 次 | - |
| 点击量 | {tp_clicks} 次 | 点击率 {round(tp_clicks / max(tp_inits, 1) * 100, 1)}% |
| 搜索量 | {tp_searches} 次 | - |
| 订单数 | {tp_bookings} 单 | 转化率 {round(tp_bookings / max(tp_clicks, 1) * 100, 1)}% |
| **佣金收入** | **${tp_revenue:.2f}** | - |

> 建议：优化高转化页面的联盟链接布局，增加机票/保险/eSIM 产品覆盖"""

        email_section = f"""---
## 📧 邮件订阅
| 指标 | 数据 |
| :--- | :--- |
| 总订阅人数 | {total_subscribers} |
| {month_label}新增 | {monthly_new_subscribers} |
| 转化率 | {round(monthly_new_subscribers / max(month_users, 1) * 100, 2)}% |"""

        content_section = f"""---
## 📝 内容运营巡检

### 1. 产出统计
- 站点总文章数：{total_posts} 篇
- {month_label}新发：{monthly_new_posts} 篇
- 月目标：{content_goal} 篇｜完成率：{content_rate}%

### 2. 质量报告
| 检测项 | 结果 | 状态 |
| :--- | :--- | :--- |
| 联盟链接覆盖率 | {posts_with_affiliate}/{total_posts} = {coverage}% | {coverage_status} |
| 人设一致性 | 检测到 {posts_with_conflict} 篇冲突 | {conflict_status} |
| 结构化数据 | {total_posts-posts_without_schema}/{total_posts} 配置 | {schema_status} |
| 断链/占位符 | {posts_with_placeholder} 篇异常 | {'⚠️' if posts_with_placeholder > 0 else '✅'} |

### 3. 文章分类分布
""" + ("\n".join(cat_lines) if cat_lines else "- 暂无数据")

        risks_section = f"""---
## ⚠️ 风险汇总

### 🔴 红色高风险
""" + ("\n".join([f"{i+1}. {r}" for i, r in enumerate(red_risks)]) if red_risks else "- 暂无") + f"""

### 🟡 黄色中风险
""" + ("\n".join([f"{i+1}. {r}" for i, r in enumerate(yellow_risks)]) if yellow_risks else "- 暂无")

        plan_section = f"""---
## 📋 下月执行计划
| 任务项 | 优先级 | 预计周期 |
| :--- | :--- | :--- |
""" + "\n".join(plan_rows) + ("\n| - | - | - |" if not plan_rows else "")

        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "template": "indigo",
                "title": {"tag": "plain_text", "content": f"📊 ChinaBound Travel {month_label} 月度运营报告"},
                "subtitle": {"tag": "plain_text", "content": f"📅 统计周期：{month_start} ~ {month_end}｜🕒 生成时间：{today.strftime('%Y-%m-%d %H:%M')}"}
            },
            "elements": [
                {"tag": "div", "text": {"tag": "lark_md", "content": core_table}},
                {"tag": "div", "text": {"tag": "lark_md", "content": channel_table}},
                {"tag": "div", "text": {"tag": "lark_md", "content": pages_table}},
                {"tag": "div", "text": {"tag": "lark_md", "content": seo_section}},
                {"tag": "div", "text": {"tag": "lark_md", "content": affiliate_section}},
                {"tag": "div", "text": {"tag": "lark_md", "content": email_section}},
                {"tag": "div", "text": {"tag": "lark_md", "content": content_section}},
                {"tag": "div", "text": {"tag": "lark_md", "content": risks_section}},
                {"tag": "div", "text": {"tag": "lark_md", "content": plan_section}},
                {"tag": "div", "text": {"tag": "lark_md", "content": "\n---\n💡 本月报由自动化脚本生成 | 每月1日 08:00 自动推送\n📐 数据口径：GA4 + Travelpayouts + MailerLite + 本地扫描"}}
            ]
        }

        return card

    def run(self) -> bool:
        print("=" * 60)
        print("🌍 ChinaBound Travel 月度运营报告 v1.0")
        print("=" * 60)

        data = self.collect_data()
        print("📝 构建飞书月报卡片...")
        card = self.build_monthly_card(data)
        print("📤 发送飞书消息...")
        success = self.send_card_message(card)

        self._save_month_data(data)

        report_path = REPORTS_DIR / f"monthly_report_{datetime.now().strftime('%Y%m')}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"📁 月报已保存: {report_path}")

        print("=" * 60)
        print(f"{'✅ 月报推送完成' if success else '❌ 月报推送失败'}")
        print("=" * 60)

        return success


def main():
    reporter = FeishuMonthlyReporter()
    success = reporter.run()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())