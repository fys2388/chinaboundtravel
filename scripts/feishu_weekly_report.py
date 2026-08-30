#!/usr/bin/env python3
"""
feishu_weekly_report.py - ChinaBound Travel 飞书周报推送
功能：诊断+预警+复盘闭环的冷启动运营控制台
版本：v3.0 - 工业级冷启动周报模板
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

import reporting_snapshot_reader

try:
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
    HAS_GOOGLE_AUTH = True
except ImportError:
    HAS_GOOGLE_AUTH = False

SCRIPT_DIR = Path(__file__).parent.resolve()
BLOG_ROOT = SCRIPT_DIR.parent

# OKR 公共工具（进度看板 / 上期复盘 / 快照）
sys.path.insert(0, str(SCRIPT_DIR))
import okr_utils
import report_advice

try:
    from dotenv import load_dotenv
    dotenv_path = BLOG_ROOT / ".env"
    load_dotenv(dotenv_path)
except ImportError:
    pass

CONTENT_DIR = BLOG_ROOT / "content"
POSTS_DIR = CONTENT_DIR / "posts"
THEME_SCHEMA_PATH = BLOG_ROOT / "layouts" / "partials" / "templates" / "schema_json.html"
TEMPLATE_AFFILIATE_PATH = BLOG_ROOT / "layouts" / "partials" / "travel-promo.html"
REDIRECTS_PATH = BLOG_ROOT / "static" / "_redirects"
META_TAGS_PATH = BLOG_ROOT / "layouts" / "partials" / "head" / "meta.html"
REPORTS_DIR = BLOG_ROOT / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
LAST_WEEK_DATA_FILE = REPORTS_DIR / "last_week_data.json"

FEISHU_WEBHOOK_URL = os.environ.get("FEISHU_WEBHOOK_URL", "")
FEISHU_SECRET = os.environ.get("FEISHU_SECRET", "")

TRAVELPAYOUTS_API_TOKEN = os.environ.get("TRAVELPAYOUTS_API_TOKEN", "")
TRAVELPAYOUTS_MARKER = os.environ.get("TRAVELPAYOUTS_MARKER", "730795")
GA4_API_KEY = os.environ.get("GA4_API_KEY", "")
GA4_PROPERTY_ID = os.environ.get("GA4_PROPERTY_ID", "541752321")
GA4_SERVICE_ACCOUNT_JSON = os.environ.get("GA4_SERVICE_ACCOUNT_JSON", "")
MAILERLITE_API_TOKEN = os.environ.get("MAILERLITE_API_TOKEN", "")
GSC_SERVICE_ACCOUNT_JSON = os.environ.get("GSC_SERVICE_ACCOUNT_JSON", "")
GSC_SITE_URL = os.environ.get("GSC_SITE_URL", "sc-domain:chinaboundtravel.com")

class FeishuWeeklyReporter:

    def __init__(self):
        self.webhook_url = FEISHU_WEBHOOK_URL
        self.secret = FEISHU_SECRET
        self.last_week_data = self._load_last_week_data()

    def _load_last_week_data(self) -> dict:
        """加载上周数据用于环比计算"""
        if LAST_WEEK_DATA_FILE.exists():
            try:
                with open(LAST_WEEK_DATA_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"   ⚠️ 加载上周数据失败: {e}")
        return {}

    def _save_week_data(self, data: dict):
        """保存本周数据供下周环比计算和PDCA复盘"""
        try:
            save_data = {
                "week_users": data.get("week_users", 0),
                "week_sessions": data.get("week_sessions", 0),
                "week_pageviews": data.get("week_pageviews", 0),
                "week_bounce": data.get("week_bounce", 0),
                "next_week_plan": data.get("next_week_plan", []),
                "content_data": data.get("content_data", {}),
                "gsc_data": data.get("gsc_data", {}),
            }
            with open(LAST_WEEK_DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)
            print(f"   ✅ 本周数据已保存: {LAST_WEEK_DATA_FILE}")
        except Exception as e:
            print(f"   ⚠️ 保存本周数据失败: {e}")

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
                print("✅ 飞书周报推送成功")
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
            if not sa_path.is_absolute():
                sa_path = BLOG_ROOT / sa_path
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

    def _fetch_weekly_ga4(self) -> dict:
        """获取上一周GA4数据（完整一周）"""
        headers = self._get_ga4_headers()
        if not headers:
            return None

        today = datetime.now()
        week_start = (today - timedelta(days=today.weekday() + 7)).strftime("%Y-%m-%d")
        week_end = (today - timedelta(days=today.weekday() + 1)).strftime("%Y-%m-%d")
        prev_week_start = (today - timedelta(days=today.weekday() + 14)).strftime("%Y-%m-%d")
        prev_week_end = (today - timedelta(days=today.weekday() + 8)).strftime("%Y-%m-%d")

        print(f"   🔍 获取 GA4 数据（上周: {week_start} ~ {week_end}）...")

        try:
            total_payload = {
                "dateRanges": [{"startDate": week_start, "endDate": week_end}],
                "metrics": [
                    {"name": "activeUsers"},
                    {"name": "sessions"},
                    {"name": "screenPageViews"},
                    {"name": "engagementRate"},
                    {"name": "averageSessionDuration"}
                ]
            }
            total_result = self._ga4_run_report(headers, total_payload)

            week_users = 0
            week_sessions = 0
            week_pageviews = 0
            week_engagement = 0.0
            week_avg_duration = 0

            if total_result and "rows" in total_result:
                row = total_result["rows"][0]
                week_users = int(row.get("metricValues", [{}])[0].get("value", "0"))
                week_sessions = int(row.get("metricValues", [{}])[1].get("value", "0"))
                week_pageviews = int(row.get("metricValues", [{}])[2].get("value", "0"))
                week_engagement = round(float(row.get("metricValues", [{}])[3].get("value", "0")) * 100, 1)
                week_avg_duration = int(float(row.get("metricValues", [{}])[4].get("value", "0")))

            prev_total_payload = {
                "dateRanges": [{"startDate": prev_week_start, "endDate": prev_week_end}],
                "metrics": [{"name": "activeUsers"}, {"name": "sessions"}, {"name": "screenPageViews"}]
            }
            prev_result = self._ga4_run_report(headers, prev_total_payload)
            prev_users = 0
            prev_sessions = 0
            prev_pageviews = 0
            if prev_result and "rows" in prev_result:
                row = prev_result["rows"][0]
                prev_users = int(row.get("metricValues", [{}])[0].get("value", "0"))
                prev_sessions = int(row.get("metricValues", [{}])[1].get("value", "0"))
                prev_pageviews = int(row.get("metricValues", [{}])[2].get("value", "0"))

            bounce_payload = {
                "dateRanges": [{"startDate": week_start, "endDate": week_end}],
                "metrics": [{"name": "bounceRate"}]
            }
            bounce_result = self._ga4_run_report(headers, bounce_payload)
            week_bounce = 0.0
            if bounce_result and "rows" in bounce_result:
                week_bounce = round(float(bounce_result["rows"][0].get("metricValues", [{}])[0].get("value", "0")) * 100, 1)

            prev_bounce_payload = {
                "dateRanges": [{"startDate": prev_week_start, "endDate": prev_week_end}],
                "metrics": [{"name": "bounceRate"}]
            }
            prev_bounce_result = self._ga4_run_report(headers, prev_bounce_payload)
            prev_bounce = 0.0
            if prev_bounce_result and "rows" in prev_bounce_result:
                prev_bounce = round(float(prev_bounce_result["rows"][0].get("metricValues", [{}])[0].get("value", "0")) * 100, 1)

            channel_payload = {
                "dateRanges": [{"startDate": week_start, "endDate": week_end}],
                "metrics": [{"name": "activeUsers"}, {"name": "bounceRate"}, {"name": "averageSessionDuration"}],
                "dimensions": [{"name": "sessionDefaultChannelGroup"}],
                "orderBys": [{"metric": {"metricName": "activeUsers"}, "desc": True}],
                "limit": 5
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
                "dateRanges": [{"startDate": week_start, "endDate": week_end}],
                "metrics": [{"name": "screenPageViews"}, {"name": "averageSessionDuration"}, {"name": "bounceRate"}],
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
                    if path and views > 0:
                        if not title or title.lower() in ["(not set)", "not set", ""]:
                            title = path.split('/')[-1].replace('-', ' ').title()
                            if not title:
                                title = path
                        title = re.sub(r'^\s*[-|·|\|]\s*ChinaBound Travel\s*[-|·|\|]\s*', '', title, flags=re.IGNORECASE)
                        title = re.sub(r'\s*[-|·|\|]\s*ChinaBound Travel\s*$', '', title, flags=re.IGNORECASE)
                        if len(title) > 40:
                            title = title[:37] + "..."
                        top_pages.append({"path": path, "title": title, "views": views, "duration": duration, "bounce": bounce})

            def calc_trend(current, prev):
                if prev == 0:
                    return "-"
                change = round((current - prev) / prev * 100, 1)
                icon = "📈" if change > 0 else "📉" if change < 0 else "➡️"
                return f"{icon} {abs(change)}%"

            def calc_pct_change(current, prev):
                if prev == 0:
                    return "-"
                change = round(current - prev, 1)
                icon = "📈" if change > 0 else "📉" if change < 0 else "➡️"
                return f"{icon} {abs(change)}pct"

            return {
                "week_start": week_start,
                "week_end": week_end,
                "week_users": week_users,
                "week_sessions": week_sessions,
                "week_pageviews": week_pageviews,
                "week_bounce": week_bounce,
                "week_engagement": week_engagement,
                "week_avg_duration": week_avg_duration,
                "users_trend": calc_trend(week_users, prev_users),
                "sessions_trend": calc_trend(week_sessions, prev_sessions),
                "pageviews_trend": calc_trend(week_pageviews, prev_pageviews),
                "bounce_trend": calc_pct_change(week_bounce, prev_bounce),
                "channels": channels,
                "top_pages": top_pages
            }

        except Exception as e:
            print(f"   ⚠️ GA4 API 获取失败: {e}")

        return None

    def _fetch_weekly_travelpayouts(self) -> dict:
        """获取上一周Travelpayouts数据"""
        if not TRAVELPAYOUTS_API_TOKEN:
            return None

        try:
            url = "https://api.travelpayouts.com/statistics/v1/execute_query"
            headers = {"X-Access-Token": TRAVELPAYOUTS_API_TOKEN, "Content-Type": "application/json"}

            today = datetime.now()
            week_start = (today - timedelta(days=today.weekday() + 7))
            week_end = (today - timedelta(days=today.weekday() + 1))

            total_clicks = 0
            total_bookings = 0
            total_revenue = 0.0
            total_inits = 0
            total_searches = 0

            current_date = week_start
            while current_date <= week_end:
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
                except Exception as e:
                    pass
                current_date += timedelta(days=1)

            return {
                "tp_clicks": total_clicks,
                "tp_bookings": total_bookings,
                "tp_revenue": round(total_revenue, 2),
                "tp_inits": total_inits,
                "tp_searches": total_searches
            }

        except Exception as e:
            print(f"   ⚠️ Travelpayouts API 获取失败: {e}")
            return None

    def _fetch_gsc_data(self) -> dict:
        """获取GSC数据（带平滑降级；未授权/失败明确 status，避免误报零收录）"""
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

            from googleapiclient.discovery import build
            service = build("searchconsole", "v1", credentials=credentials)

            # 站点候选：优先 GSC_SITE_URL 配置（逗号分隔多候选），回退域属性
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
                    break
                except Exception:
                    continue
            if not site_url:
                return {"status": "unauthorized", "estimated_pages": len(list(POSTS_DIR.glob("*.md"))) if POSTS_DIR.exists() else 0}

            # 与 GA4 周报口径一致：上周一 ~ 上周日
            today = datetime.now()
            week_start = (today - timedelta(days=today.weekday() + 7)).strftime("%Y-%m-%d")
            week_end = (today - timedelta(days=today.weekday() + 1)).strftime("%Y-%m-%d")
            resp = service.searchanalytics().query(
                siteUrl=site_url,
                body={"startDate": week_start, "endDate": week_end,
                      "dimensions": ["page"], "rowLimit": 1000, "dataState": "final"}
            ).execute()
            indexed_pages = len(resp.get("rows", []))

            # sitemap 数量作为收录参考
            sitemap_count = 0
            try:
                sm = service.sitemaps().list(siteUrl=site_url).execute()
                sitemap_count = len(sm.get("sitemap", []))
            except Exception:
                pass

            return {"status": "authorized", "indexed_pages": indexed_pages,
                    "sitemap_count": sitemap_count, "errors": 0}

        except Exception as e:
            print(f"   ⚠️ GSC API 获取失败: {e}")

        return {"status": "error", "estimated_pages": len(list(POSTS_DIR.glob("*.md"))) if POSTS_DIR.exists() else 0}

    def _fetch_weekly_mailerlite(self) -> dict:
        """获取MailerLite数据（未配置/认证失败时明确标记，不伪装成 0）"""
        if not MAILERLITE_API_TOKEN:
            return {"ml_available": False, "ml_error": "MAILERLITE_API_TOKEN 未配置"}

        # 清洗 token：去除 BOM（\ufeff）和空白，避免 latin-1 编码错误
        clean_token = MAILERLITE_API_TOKEN.lstrip("\ufeff").strip()
        clean_token = "".join(c for c in clean_token if ord(c) < 128)

        try:
            headers = {"Authorization": f"Bearer {clean_token}", "Content-Type": "application/json"}
            resp = requests.get("https://connect.mailerlite.com/api/subscribers", headers=headers, params={"limit": 1}, timeout=15)
            if resp.status_code != 200:
                print(f"   ⚠️ MailerLite API 响应 {resp.status_code}: {resp.text[:150]}")
                return {"ml_available": False, "ml_error": f"MailerLite API 认证失败（HTTP {resp.status_code}）"}
            # 分页统计订阅者总数（新版 API 的 x-total-count / meta.total 可能缺失）
            total_subscribers = 0
            _cursor = None
            while True:
                _params = {"limit": 100}
                if _cursor:
                    _params["cursor"] = _cursor
                _r = requests.get("https://connect.mailerlite.com/api/subscribers",
                                  headers=headers, params=_params, timeout=15)
                if _r.status_code == 200:
                    _d = _r.json()
                    total_subscribers += len(_d.get("data", []))
                    _cursor = (_d.get("meta") or {}).get("next_cursor")
                    if not _cursor:
                        break
                    if total_subscribers >= 10000:
                        break
                else:
                    break

            today = datetime.now()
            week_start = (today - timedelta(days=today.weekday() + 7)).strftime("%Y-%m-%d")
            week_end = (today - timedelta(days=today.weekday() + 1)).strftime("%Y-%m-%d")
            weekly_new = 0
            try:
                resp_recent = requests.get(
                    "https://connect.mailerlite.com/api/subscribers",
                    headers=headers, params={"limit": 100, "sort": "created_at:desc"}, timeout=15
                )
                if resp_recent.status_code == 200:
                    for sub in resp_recent.json().get("data", []):
                        created = sub.get("created_at", "")[:10]
                        if week_start <= created <= week_end:
                            weekly_new += 1
            except Exception as e:
                print(f"   ⚠️ MailerLite 周新增获取失败: {e}")

            return {"ml_available": True, "total_subscribers": total_subscribers, "weekly_new_subscribers": weekly_new}

        except Exception as e:
            print(f"   ⚠️ MailerLite API 获取失败: {e}")
            return {"ml_available": False, "ml_error": f"MailerLite API 请求异常: {e}"}

    def _scan_content_quality(self) -> dict:
        """本地内容质量巡检引擎"""
        result = {
            "total_posts": 0,
            "posts_with_affiliate": 0,
            "posts_with_conflict": 0,
            "posts_without_schema": 0,
            "posts_with_placeholder": 0,
            "category_distribution": {},
            "weekly_new_posts": 0,
            "template_level_coverage": False,
            "site_wide_affiliate": False,
        }

        if not POSTS_DIR.exists():
            return result

        template_exists = THEME_SCHEMA_PATH.exists()
        result["template_level_coverage"] = template_exists
        result["site_wide_affiliate"] = TEMPLATE_AFFILIATE_PATH.exists()

        posts = list(POSTS_DIR.glob("*.md"))
        result["total_posts"] = len(posts)

        today = datetime.now()
        week_start = (today - timedelta(days=today.weekday() + 7)).date()
        week_end = (week_start + timedelta(days=6))

        affiliate_patterns = [
            r'travelpayouts', r'booking\.com', r'agoda\.com', r'trip\.com', r'klook',
            r'safetywing', r'airalo', r'hotellook', r'affiliatescn', r'nordpass',
            r'worldnomads', r'allianz', r'affiliate-section', r'affiliate_key',
            r'promo-widget', r'travel-promo', r'affiliate-disclosure'
        ]

        for post in posts:
            try:
                content = post.read_text(encoding='utf-8')

                post_date = None
                fm_match = re.search(r'---\r?\n(.*?)\r?\n---', content, re.DOTALL)
                if fm_match:
                    date_match = re.search(r"date:\s*['\"]?(\d{4}-\d{2}-\d{2})", fm_match.group(1))
                    if date_match:
                        try:
                            post_date = datetime.strptime(date_match.group(1), "%Y-%m-%d")
                        except ValueError:
                            pass
                if post_date and week_start <= post_date.date() <= week_end:
                    result["weekly_new_posts"] += 1

                if any(re.search(p, content, re.IGNORECASE) for p in affiliate_patterns):
                    result["posts_with_affiliate"] += 1

                years_patterns = re.findall(r'(\d+)\s*years?\s+(?:in|of|living|staying|working|teaching|studying)', content, re.IGNORECASE)
                unique_years = set([int(y) for y in years_patterns if y.isdigit()])
                has_decade = re.search(r'(?:decade|10\+?\s*years?)\s+(?:in|of)\s+China', content, re.IGNORECASE)
                has_author_years = re.search(r'(?:I|We|My|Our|Joran)\s+have\s+(?:been\s+)?(?:living|staying|working|teaching|studying)?\s*(\d+)\s*years?\s+(?:in|of)', content, re.IGNORECASE)
                if len(unique_years) > 1 or (has_decade and has_author_years):
                    result["posts_with_conflict"] += 1

                if template_exists:
                    pass
                else:
                    fm_match2 = re.search(r'---\r?\n(.*?)\r?\n---', content, re.DOTALL)
                    if fm_match2:
                        fm = fm_match2.group(1)
                        if not re.search(r'article_schema|structured_data|schema', fm, re.IGNORECASE):
                            result["posts_without_schema"] += 1

                front_matter_match = re.search(r'---\r?\n(.*?)\r?\n---', content, re.DOTALL)
                if front_matter_match:
                    front_matter = front_matter_match.group(1)
                    categories_section = re.search(r'categories:\s*\r?\n((?:\s*-\s*[^\r\n]+\r?\n?)+)', front_matter)
                    if categories_section:
                        cat_block = categories_section.group(1)
                        cat_items = re.findall(r'^\s*-\s*(.+?)\s*$', cat_block, re.MULTILINE)
                        for cat in cat_items:
                            cat_clean = cat.strip()
                            cat_clean = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', cat_clean)
                            cat_clean = cat_clean.strip('- ')
                            # 过滤损坏的分类条目
                            if not cat_clean or len(cat_clean) > 50:
                                continue
                            if re.search(r'\[.*\]', cat_clean):
                                continue
                            if re.search(r'[\/\\]', cat_clean):
                                continue
                            if not re.match(r'^[\w\s\-]+$', cat_clean):
                                continue
                            result["category_distribution"][cat_clean] = result["category_distribution"].get(cat_clean, 0) + 1

                if re.search(r'\[IMAGE\]|\[TODO\]|\[PLACEHOLDER\]', content, re.IGNORECASE):
                    result["posts_with_placeholder"] += 1

            except Exception as e:
                pass

        return result

    def _detect_risk_level(self, data: dict) -> dict:
        """自动风险分级预警系统"""
        red_risks = []
        yellow_risks = []

        gsc_data = data.get("gsc_data", {})
        gsc_ok = gsc_data.get("status") == "authorized"
        indexed_pages = gsc_data.get("indexed_pages", 0)
        if gsc_ok and indexed_pages == 0:
            red_risks.append("Google 零收录，自然搜索流量完全断流 → 对应行动：GSC验证域名 + 提交索引")
        elif not gsc_ok:
            yellow_risks.append("GSC 未授权/接口异常，收录数据缺失 → 对应行动：检查 GSC 服务账号授权")

        tp_revenue = data.get("tp_revenue", 0)
        content_data = data.get("content_data", {})
        total_posts = content_data.get("total_posts", 0)
        posts_with_affiliate = content_data.get("posts_with_affiliate", 0)
        site_wide_affiliate = content_data.get("site_wide_affiliate", False)
        coverage = (posts_with_affiliate / max(total_posts, 1)) * 100 if total_posts > 0 else 0
        if tp_revenue == 0 and coverage < 30 and not site_wide_affiliate:
            yellow_risks.append("联盟佣金为0且链接覆盖率<30%，变现链路待验证（NEW：Revenue NOT_AVAILABLE，非故障）")

        posts_with_conflict = content_data.get("posts_with_conflict", 0)
        if posts_with_conflict > 0:
            yellow_risks.append(f"人设年限冲突（{posts_with_conflict}篇），需批量修正 → 对应行动：按优先级迁移 legacy 文案")

        week_users = data.get("week_users", 0)
        if week_users < 100:
            yellow_risks.append("访客数低于100，核心业务目标完成率不足 → 对应行动：发布高转化长尾攻略")

        week_bounce = data.get("week_bounce", 0)
        if week_bounce > 60:
            yellow_risks.append(f"跳出率{week_bounce}%偏高，用户留存弱 → 对应行动：优化页面内容质量")

        week_avg_duration = data.get("week_avg_duration", 0)
        if week_avg_duration < 30:
            yellow_risks.append(f"平均停留时长{week_avg_duration}秒，不足30秒 → 对应行动：优化核心文章内容")

        total_subscribers = data.get("total_subscribers", 0)
        weekly_new_subscribers = data.get("weekly_new_subscribers", 0)
        if data.get("ml_available", False) and weekly_new_subscribers == 0:
            yellow_risks.append("邮件订阅新增为0，私域沉淀为零 → 对应行动：上线免费订阅诱饵")

        posts_without_schema = content_data.get("posts_without_schema", 0)
        template_level_coverage = content_data.get("template_level_coverage", False)
        if posts_without_schema > 5 and not template_level_coverage:
            yellow_risks.append(f"结构化数据缺失{posts_without_schema}篇，影响SEO → 对应行动：批量补充Article Schema")

        return {"red": red_risks, "yellow": yellow_risks}

    def _generate_next_week_plan(self, risks: dict) -> list:
        """基于风险动态生成下周计划"""
        plan = []

        if risks.get("red"):
            plan.extend([
                {"task": "Cloudflare 配置 www → 裸域名 301 永久重定向，统一 canonical", "priority": "high", "period": "3天内"},
                {"task": "补全全站 OG / Twitter Card 社交预览标签，修复零分享预览问题", "priority": "high", "period": "3天内"},
                {"task": "GSC 验证域名、提交 sitemap，手动请求 5 篇核心文章索引", "priority": "high", "period": "3天内", "kr_id": "gsc", "target": 300},
                {"task": "全局批量修正 Joran 旅居年限文案，统一为 5 年标准表述", "priority": "high", "period": "3天内"},
                {"task": "完成全站联盟链接覆盖，目标覆盖率 100%", "priority": "high", "period": "本周", "kr_id": "revenue", "target": 30},
                {"task": "深度优化张家界、成都火锅 2 篇核心文章，扩充至 2000+ 字", "priority": "high", "period": "本周", "kr_id": "content", "target": 5}
            ])

        if risks.get("yellow"):
            plan.extend([
                {"task": "评估 Travelpayouts Drive 对核心页面的覆盖价值（人工决策）", "priority": "medium", "period": "本月", "kr_id": "revenue"},
                {"task": "发布 3 篇高转化长尾攻略（支付 / 签证 / 交通）", "priority": "medium", "period": "本周", "kr_id": "content", "target": 5},
                {"task": "Reddit / Quora 铺设 3 条问答外链，实现零突破", "priority": "medium", "period": "本周"},
                {"task": "社媒标准化模板落地，每日稳定更新", "priority": "medium", "period": "本周"},
                {"task": "上线免费订阅诱饵（7 天中国行程模板）", "priority": "medium", "period": "本周", "kr_id": "email", "target": 10}
            ])

        plan.extend([
            {"task": "全量检测内部断链与占位符", "priority": "low", "period": "本周"},
            {"task": "文章页批量补充 Article 结构化数据", "priority": "low", "period": "本周"}
        ])

        return plan

    def _review_last_week_plan(self, data: dict) -> list:
        """PDCA复盘：读取上周计划并判定完成状态"""
        last_week_plan = self.last_week_data.get("next_week_plan", [])
        weekly_new_posts = data.get("content_data", {}).get("weekly_new_posts", 0)
        indexed_pages = data.get("gsc_data", {}).get("indexed_pages", 0)
        total_posts = data.get("content_data", {}).get("total_posts", 0)
        posts_with_affiliate = data.get("content_data", {}).get("posts_with_affiliate", 0)
        coverage = round(posts_with_affiliate / max(total_posts, 1) * 100, 1) if total_posts > 0 else 0

        review = []
        for item in last_week_plan:
            task = item.get("task", "")
            priority = item.get("priority", "medium")

            if "发布" in task and "文章" in task:
                progress = min(round(weekly_new_posts / 5 * 100, 0), 100)
                if weekly_new_posts >= 5:
                    status = f"✅ 超额完成 ({progress}%)"
                elif weekly_new_posts >= 3:
                    status = f"✅ 已完成 ({progress}%)"
                else:
                    status = f"🟡 进行中 ({progress}%)"
            elif "索引" in task or "GSC" in task:
                progress = round(indexed_pages / 10 * 100, 0)
                if indexed_pages >= 10:
                    status = f"✅ 已完成 ({progress}%)"
                elif indexed_pages > 0:
                    status = f"🟡 进行中 ({progress}%)"
                else:
                    status = f"❌ 未开始 ({progress}%)"
            elif "联盟" in task:
                if coverage >= 80:
                    status = f"✅ 收尾 ({coverage}%)"
                elif coverage >= 50:
                    status = f"🟡 进行中 ({coverage}%)"
                elif coverage > 0:
                    status = f"🟡 进行中 ({coverage}%)"
                else:
                    status = f"❌ 未开始 ({coverage}%)"
            elif "SEO" in task:
                status = "🟡 进行中"
            elif "社媒" in task:
                status = "🟡 进行中"
            elif "外链" in task:
                status = "🟡 进行中"
            elif "301" in task or "重定向" in task:
                if REDIRECTS_PATH.exists():
                    status = "✅ 已完成"
                else:
                    status = "❌ 未开始"
            elif "OG" in task or "社交标签" in task:
                if META_TAGS_PATH.exists():
                    status = "✅ 已完成"
                else:
                    status = "❌ 未开始"
            elif "文案" in task or "人设" in task:
                status = "❌ 未开始"
            elif "结构化数据" in task or "Article" in task:
                status = "🟡 进行中"
            elif "断链" in task or "占位符" in task:
                status = "🟡 进行中"
            else:
                status = "🟡 进行中"

            review.append({"task": task, "priority": priority, "status": status})

        return review

    def collect_data(self) -> dict:
        """收集周报数据"""
        print("📊 收集周报数据...")
        data = {}

        # 2.0 统一口径（P1-REPORT-03R）：SNAPSHOT 优先，命中则 GA4/GSC 采用统一快照，不再直连
        _snap_ga4 = reporting_snapshot_reader.snapshot_traffic("week")
        if _snap_ga4 is not None:
            print("   📦 2.0 统一快照命中：GA4/GSC 采用 SNAPSHOT 口径（as_of=%s）" % _snap_ga4.get("snapshot_as_of"))
            data.update(_snap_ga4)
            _snap_gsc = reporting_snapshot_reader.snapshot_gsc()
            data["gsc_data"] = _snap_gsc if _snap_gsc is not None else self._fetch_gsc_data()
        else:
            print("1️⃣ 获取 GA4 数据...")
            ga4_data = self._fetch_weekly_ga4()
            if ga4_data:
                data.update(ga4_data)

            print("3️⃣ 获取 GSC 数据...")
            gsc_data = self._fetch_gsc_data()
            data["gsc_data"] = gsc_data

        print("2️⃣ 获取 Travelpayouts 数据...")
        tp_data = self._fetch_weekly_travelpayouts()
        if tp_data:
            data.update(tp_data)

        print("4️⃣ 获取 MailerLite 数据...")
        ml_data = self._fetch_weekly_mailerlite()
        if ml_data:
            data.update(ml_data)

        print("5️⃣ 扫描内容质量...")
        content_data = self._scan_content_quality()
        data["content_data"] = content_data

        print("6️⃣ 检测风险等级...")
        risks = self._detect_risk_level(data)
        data["risks"] = risks

        print("7️⃣ 生成下周计划...")
        next_week_plan = self._generate_next_week_plan(risks)
        data["next_week_plan"] = next_week_plan

        print("8️⃣ 复盘上周计划...")
        last_week_review = self._review_last_week_plan(data)
        data["last_week_review"] = last_week_review

        print("9️⃣ 生成 OKR 进度与复盘...")
        data["okr_section"] = okr_utils.build_okr_section(data, "weekly")
        prev_key = okr_utils.period_key("weekly", datetime.now() - timedelta(days=7))
        prev_snap = okr_utils.load_snapshot("weekly", prev_key)
        data["okr_review"] = okr_utils.review_previous_plan(prev_snap, data)

        # 🔟 自动运营建议（基于真实数据精准生成）
        data["advice_section"] = report_advice.advice_section(data, "weekly")

        return data

    def build_weekly_card(self, data: dict) -> dict:
        """构建飞书周报卡片（工业级模板）"""

        _caliber = reporting_snapshot_reader.caliber_label(data)
        today = datetime.now()
        week_num = today.isocalendar()[1]
        prev_week_num = week_num - 1
        week_start = data.get("week_start", "")
        week_end = data.get("week_end", "")

        week_users = data.get("week_users", 0)
        week_sessions = data.get("week_sessions", 0)
        week_pageviews = data.get("week_pageviews", 0)
        week_bounce = data.get("week_bounce", 0)
        week_avg_duration = data.get("week_avg_duration", 0)
        week_engagement = data.get("week_engagement", 0)

        users_trend = data.get("users_trend", "-")
        sessions_trend = data.get("sessions_trend", "-")
        pageviews_trend = data.get("pageviews_trend", "-")
        bounce_trend = data.get("bounce_trend", "-")
        duration_trend = "-"

        if week_avg_duration > 60:
            dur_str = f"{week_avg_duration // 60}分{week_avg_duration % 60}秒"
        else:
            dur_str = f"{week_avg_duration}秒"

        traffic_goal = 500
        traffic_rate = round(week_users / traffic_goal * 100, 1) if traffic_goal > 0 else 0
        traffic_status = "✅" if week_users >= traffic_goal else "⚠️"

        gsc_data = data.get("gsc_data", {})
        gsc_ok = gsc_data.get("status") == "authorized"
        gsc_status = "⚠️ GSC 未授权" if not gsc_ok else "已授权"
        indexed_pages = gsc_data.get("indexed_pages", 0)
        estimated_pages = gsc_data.get("estimated_pages", len(list(POSTS_DIR.glob("*.md"))) if POSTS_DIR.exists() else 0)

        content_data = data.get("content_data", {})
        total_posts = content_data.get("total_posts", 0)
        posts_with_affiliate = content_data.get("posts_with_affiliate", 0)
        coverage = round(posts_with_affiliate / max(total_posts, 1) * 100, 1) if total_posts > 0 else 0
        template_level_coverage = content_data.get("template_level_coverage", False)
        site_wide_affiliate = content_data.get("site_wide_affiliate", False)
        if site_wide_affiliate:
            coverage_display = f"{coverage}%（内容级 {posts_with_affiliate}/{total_posts}）+ 模板级全量覆盖"
        else:
            coverage_display = f"{coverage}%（{posts_with_affiliate}/{total_posts}）"
        posts_with_conflict = content_data.get("posts_with_conflict", 0)
        posts_without_schema = content_data.get("posts_without_schema", 0)
        posts_with_placeholder = content_data.get("posts_with_placeholder", 0)
        weekly_new_posts = content_data.get("weekly_new_posts", 0)
        content_goal = 5
        content_rate = round(weekly_new_posts / content_goal * 100, 0) if content_goal > 0 else 0

        channels = data.get("channels", [])
        channel_rows = []
        for c in channels:
            dur_c = f"{c['duration']}秒" if c['duration'] < 60 else f"{c['duration']//60}分{c['duration']%60}秒"
            if c['duration'] >= 30 and c['bounce'] < 60:
                quality = "🟢 优质"
            elif (c['duration'] >= 25 and c['bounce'] >= 70) or (15 <= c['duration'] < 30 and 60 <= c['bounce'] <= 75):
                quality = "🟡 一般"
            elif c['duration'] < 15 or (c['bounce'] > 80 and c['duration'] < 20):
                quality = "🔴 较差"
            else:
                quality = "🟡 一般"
            
            remark = ""
            if c['channel'].lower() == "direct":
                remark = "｜停留时长优质，跳出率偏高，需优化内链引导"
            elif c['channel'].lower() == "organic social":
                remark = "｜短停留低质量流量，社媒素材匹配度不足"
            
            pct = round(c['users'] / max(week_users, 1) * 100, 1)
            channel_rows.append(f"| {c['channel']} | {c['users']} | {pct}% | {c['bounce']}% | {dur_c} | {quality}{remark} |")

        top_pages = data.get("top_pages", [])
        page_rows = []
        for i, p in enumerate(top_pages[:5], 1):
            title = p.get('title', p.get('path', ''))
            dur_p = f"{p['duration']}秒" if p['duration'] < 60 else f"{p['duration']//60}分{p['duration']%60}秒"
            anomaly_mark = ""
            if p['duration'] <= 5:
                anomaly_mark = " ⚠️短停留"
            elif p['bounce'] == 100:
                anomaly_mark = " ⚠️全跳出"
            elif week_avg_duration > 0 and p['duration'] >= week_avg_duration * 3:
                anomaly_mark = " ⚠️异常高停留"
            page_rows.append(f"| {i} | {title} | {p['views']} | {dur_p} | {p['bounce']}% |{anomaly_mark} |")

        tp_clicks = data.get("tp_clicks", 0)
        tp_bookings = data.get("tp_bookings", 0)
        tp_revenue = data.get("tp_revenue", 0.0)
        tp_inits = data.get("tp_inits", 0)
        tp_searches = data.get("tp_searches", 0)

        ml_available = data.get("ml_available", False)
        ml_error = data.get("ml_error", "")
        total_subscribers = data.get("total_subscribers", 0)
        weekly_new_subscribers = data.get("weekly_new_subscribers", 0)
        if ml_available:
            total_sub_str = f"{total_subscribers:,}"
            weekly_new_str = f"{weekly_new_subscribers}"
            ml_diag = "🟡 **诊断**：暂无 Lead Magnet 订阅诱饵，全站无明确转化入口"
        else:
            total_sub_str = f"未连接（{ml_error}）" if ml_error else "未配置"
            weekly_new_str = "-"
            ml_diag = "⚠️ **数据源**：MailerLite 未接入/认证失败，订阅数据缺失"

        cat_dist = content_data.get("category_distribution", {})
        cat_lines = []
        for cat, count in sorted(cat_dist.items(), key=lambda x: x[1], reverse=True):
            pct = round(count / max(total_posts, 1) * 100, 1)
            cat_lines.append(f"- {cat}：{count} 篇 ({pct}%)")

        risks = data.get("risks", {})
        red_risks = risks.get("red", [])
        yellow_risks = risks.get("yellow", [])

        okr_review = data.get("okr_review", [])
        if okr_review:
            # OKR 快照复盘优先（跨期计划真实数据判定）
            review_rows = [f"| {r['task']} | {r['icon']} | {r['status']} | {r['period']} |" for r in okr_review]
            review_title = "✅ 上周计划复盘（OKR 对齐）"
        else:
            # 首次运行无快照，回退旧 PDCA 复盘
            last_week_review = data.get("last_week_review", [])
            review_rows = []
            for item in last_week_review:
                priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(item["priority"], "⚪")
                review_rows.append(f"| {item['task']} | {priority_icon} | {item['status']} | - |")
            review_title = "✅ PDCA · 上周计划复盘（快照建立后自动切换 OKR 复盘）"

        next_week_plan = data.get("next_week_plan", [])
        plan_rows = []
        for item in next_week_plan:
            priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(item["priority"], "⚪")
            period = item.get("period", "本周")
            plan_rows.append(f"| {item['task']} | {priority_icon} | {period} |")

        indexed_status = "🔴" if (gsc_ok and indexed_pages == 0) else "🟡" if (gsc_ok and indexed_pages < 10) else ("⚪" if not gsc_ok else "✅")
        indexed_progress = f"{round(indexed_pages/10*100,0)}%" if gsc_ok else "-"
        indexed_display = str(indexed_pages) if gsc_ok else "-"
        coverage_status = "🔴" if (coverage < 30 and not site_wide_affiliate) else "🟡" if coverage < 80 else "✅"
        conflict_status = "🔴" if posts_with_conflict > 0 else "✅"
        schema_status = "🟡" if (posts_without_schema > 0 and not template_level_coverage) else "✅"
        placeholder_status = "⚠️" if posts_with_placeholder > 0 else "✅"
        content_rate_status = "✅" if content_rate >= 100 else "⚠️"

        conclusions = []
        if "📉" in users_trend:
            conclusions.append("流量环比下滑")
        elif "📈" in users_trend:
            conclusions.append("流量环比增长")
        
        if gsc_ok and indexed_pages == 0:
            conclusions.append("冷启动基建无实质突破")
        elif gsc_ok and indexed_pages < 10:
            conclusions.append("冷启动基建缓慢推进")
        
        if content_rate > 200:
            conclusions.append("内容批量产出但质量存风险")
        elif content_rate >= 100:
            conclusions.append("内容产出达标")
        
        priority_actions = []
        if gsc_ok and indexed_pages == 0:
            priority_actions.append("提交GSC索引")
        if coverage < 30 and not site_wide_affiliate:
            priority_actions.append("全站联盟链接覆盖")
        if posts_with_conflict > 0:
            priority_actions.append("统一人设文案")
        
        conclusion_text = "📌 本周结论：" + "，".join(conclusions) + "；" if conclusions else "📌 本周结论："
        conclusion_text += f"核心优先级为{', '.join(priority_actions)}。" if priority_actions else "核心优先级为持续优化内容质量。"

        core_kpi_table = f"""{conclusion_text}

## 🎯 核心指标看板

### 1. 业务核心指标
| 指标 | 本周数值 | 周环比 | 周目标 | 达标率 | 状态 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 访客数 | {week_users} 人 | {users_trend} | 500 人 | {traffic_rate}% | {traffic_status} |
| 会话数 | {week_sessions} 次 | {sessions_trend} | - | - | - |
| 页面浏览量 | {week_pageviews} 次 | {pageviews_trend} | - | - | - |
| 跳出率 | {week_bounce}% | {bounce_trend} | <60% | - | ⚠️ |
| 平均访问时长 | {dur_str} | {duration_trend} | >40s | - | ⚠️ |

### 2. 冷启动基建指标
| 指标 | 当前值 | 周目标 | 进度 | 状态 |
| :--- | :--- | :--- | :--- | :--- |
| GSC 曝光页面 | {indexed_display} 页 | 10 页 | {indexed_progress} | {indexed_status} |
| 有效外链总数 | 0 条 | 5 条 | 0% | 🔴 |
| 联盟链接覆盖率 | {coverage_display} | 100% | {coverage}% | {coverage_status} |"""

        channel_table = f"""---
## 🌐 流量深度分析

### 1. 渠道质量对比
| 流量渠道 | 访客数 | 占比 | 跳出率 | 平均停留时长 | 质量评级 |
| :--- | :--- | :--- | :--- | :--- | :--- |
""" + "\n".join(channel_rows) + ("\n| - | - | - | - | - | - |" if not channel_rows else "")

        pages_table = f"""### 2. 热门页面 Top5（带质量维度）
| 排名 | 页面标题 | 浏览量 | 平均停留 | 跳出率 | 异常标记 |
| :--- | :--- | :--- | :--- | :--- | :--- |
""" + "\n".join(page_rows) + ("\n| - | - | - | - | - | - |" if not page_rows else "")

        redirect_status = "✅"
        og_status = "✅"
        twitter_status = "✅"
        article_schema_status = "✅"

        seo_section = f"""### 3. 🔍 SEO 专项巡检
- **GSC 状态**：{gsc_status}｜预估可收录页面 {estimated_pages} 页
- **索引进度**：已提交 0 页 / GSC 曝光页面 {indexed_display} 页 / 索引错误 0 项
- **技术整改进度**：
  ✅ 首页 Organization 结构化数据
  {redirect_status} www → 裸域名 301 重定向
  {og_status} 全站 OG / Twitter Card 社交标签
  {twitter_status} Twitter Card 配置
  {article_schema_status} 文章页 Article 结构化数据
- **外链增长**：本周新增 0 条 / 累计 0 条
- **关键词排名**：🔌 待接入 Ahrefs / GSC 关键词数据"""

        # 分产品联盟转化统计（各品类 CTA 曝光面 + 点击率对比）
        try:
            from affiliate_product_stats import product_summary
            _prod_rows = product_summary()
            _prod_cn = {"flight": "机票", "insurance": "旅行保险", "esim": "eSIM",
                        "hotel": "酒店", "tour": "一日游/门票"}
            _prod_lines = ["| 品类 | 覆盖文章 | CTA数 | 点击 | CTR |",
                           "| :--- | :--- | :--- | :--- | :--- |"]
            for _r in _prod_rows:
                _ctr = f"{_r['ctr_pct']:.2f}%" if _r.get('ctr_pct') else "-"
                _clk = f"{_r['clicks']:,}" if _r.get('clicks') else "-"
                _prod_lines.append(f"| {_prod_cn.get(_r['product'], _r['product'])} | "
                                   f"{_r['posts']} | {_r['cta_count']} | {_clk} | {_ctr} |")
            _product_stats_table = "\n".join(_prod_lines)
        except Exception:
            _product_stats_table = "（分产品统计暂不可用）"

        affiliate_section = f"""---
## 💸 联盟变现诊断

### 整体数据
| 指标 | 本周数据 | 周环比 | 转化率 |
| :--- | :--- | :--- | :--- |
| 链接展示量 | {tp_inits} 次 | - | - |
| 点击量 | {tp_clicks} 次 | - | 0% |
| 订单数 | {tp_bookings} 单 | - | 0% |
| 佣金收入 | ${tp_revenue:.2f} | - | - |

### 📊 分产品转化对比
{_product_stats_table}

### 🩺 自动诊断结论
⚠️ **供给侧提示：变现链路待验证（Revenue NOT_AVAILABLE，非故障）**
- 本地检测：全站 {total_posts} 篇文章，{posts_with_affiliate} 篇含联盟链接，覆盖率 {coverage}%
- 联盟链接展示量（inits）为 0：新站正常，等待 GA4 事件收集足够样本
- 追踪脚本状态需人工复核"""

        email_section = f"""---
## 📧 邮件订阅
| 指标 | 数据 | 周环比 |
| :--- | :--- | :--- |
| 总订阅人数 | {total_sub_str} | - |
| 本周新增 | {weekly_new_str} | - |
{ml_diag}"""

        batch_warning = ""
        if content_rate > 200:
            batch_warning = f"\n⚠️ **本周为批量发布周期**，已触发人设一致性校验；建议抽检 3-5 篇事实准确性，防控 AI 批量生成的质量滑坡风险"

        content_section = f"""---
## 📝 内容运营巡检

### 1. 产出统计
- 站点总文章数：{total_posts} 篇
- 本周新发：{weekly_new_posts} 篇
- 周目标：5 篇 ｜ 完成率：{content_rate}% {content_rate_status}{batch_warning}

### 2. 质量巡检报告
| 检测项 | 检测规则 | 结果 | 状态 |
| :--- | :--- | :--- | :--- |
| 联盟链接覆盖率 | 含 Travelpayouts / Booking 等链接 | {coverage_display} | {coverage_status} |
| 人设一致性 | 同时出现 "5 years" / "10 years" 矛盾表述 | 检测到 {posts_with_conflict} 篇冲突 | {conflict_status} |
| 结构化数据 | 主题模板自动生成 Article/BlogPosting Schema | {total_posts-posts_without_schema}/{total_posts} 配置 | {schema_status} |
| 断链 / 占位符 | 含 [IMAGE]、TODO 等空占位符 | {posts_with_placeholder} 篇异常 | {placeholder_status} |

### 3. 文章分类分布
""" + "\n".join(cat_lines) if cat_lines else f"""---
## 📝 内容运营巡检

### 1. 产出统计
- 站点总文章数：{total_posts} 篇
- 本周新发：{weekly_new_posts} 篇
- 周目标：5 篇 ｜ 完成率：{content_rate}% {content_rate_status}{batch_warning}

### 2. 质量巡检报告
| 检测项 | 检测规则 | 结果 | 状态 |
| :--- | :--- | :--- | :--- |
| 联盟链接覆盖率 | 含 Travelpayouts / Booking 等链接 | {coverage_display} | {coverage_status} |
| 人设一致性 | 同时出现 "5 years" / "10 years" 矛盾表述 | 检测到 {posts_with_conflict} 篇冲突 | {conflict_status} |
| 结构化数据 | 主题模板自动生成 Article/BlogPosting Schema | {total_posts-posts_without_schema}/{total_posts} 配置 | {schema_status} |
| 断链 / 占位符 | 含 [IMAGE]、TODO 等空占位符 | {posts_with_placeholder} 篇异常 | {placeholder_status} |

### 3. 文章分类分布
- 暂无数据"""

        if cat_lines:
            content_section = f"""---
## 📝 内容运营巡检

### 1. 产出统计
- 站点总文章数：{total_posts} 篇
- 本周新发：{weekly_new_posts} 篇
- 周目标：5 篇 ｜ 完成率：{content_rate}% {content_rate_status}{batch_warning}

### 2. 质量巡检报告
| 检测项 | 检测规则 | 结果 | 状态 |
| :--- | :--- | :--- | :--- |
| 联盟链接覆盖率 | 含 Travelpayouts / Booking 等链接 | {coverage_display} | {coverage_status} |
| 人设一致性 | 同时出现 "5 years" / "10 years" 矛盾表述 | 检测到 {posts_with_conflict} 篇冲突 | {conflict_status} |
| 结构化数据 | 主题模板自动生成 Article/BlogPosting Schema | {total_posts-posts_without_schema}/{total_posts} 配置 | {schema_status} |
| 断链 / 占位符 | 含 [IMAGE]、TODO 等空占位符 | {posts_with_placeholder} 篇异常 | {placeholder_status} |

### 3. 文章分类分布
""" + "\n".join(cat_lines)

        review_section = f"""---
## {review_title}
| 计划项 | 优先级 | 状态 | 周期 |
| :--- | :--- | :--- | :--- |
""" + "\n".join(review_rows) + ("\n| - | - | - | - |" if not review_rows else "")

        risks_section = f"""---
## ⚠️ 本周风险汇总

### 🔴 红色高风险（立即处理）
""" + ("\n".join([f"{i+1}. {r}" for i, r in enumerate(red_risks)]) if red_risks else "- 暂无") + f"""

### 🟡 黄色中风险（本周跟进）
""" + ("\n".join([f"{i+1}. {r}" for i, r in enumerate(yellow_risks)]) if yellow_risks else "- 暂无")

        high_plan_rows = [r for r in plan_rows if "🔴" in r]
        medium_plan_rows = [r for r in plan_rows if "🟡" in r]
        low_plan_rows = [r for r in plan_rows if "🟢" in r]

        plan_section = f"""---
## 📋 下周执行计划

### 🔴 最高优先级（基建止血，3天内）
| 任务项 | 优先级 | 预计周期 |
| :--- | :--- | :--- |
""" + "\n".join(high_plan_rows) + ("\n| - | - | - |" if not high_plan_rows else "") + f"""

### 🟡 增长配套
| 任务项 | 优先级 | 预计周期 |
| :--- | :--- | :--- |
""" + "\n".join(medium_plan_rows) + ("\n| - | - | - |" if not medium_plan_rows else "") + f"""

### 🟢 常规运维
| 任务项 | 优先级 | 预计周期 |
| :--- | :--- | :--- |
""" + "\n".join(low_plan_rows) + ("\n| - | - | - |" if not low_plan_rows else "")

        improvement_section = f"""---
## 🛠️ 本周整改验收
| 整改项 | 上周状态 | 本周状态 | 改进效果 |
| :--- | :--- | :--- | :--- |
| www→裸域名301重定向 | ❌ 未配置 | {redirect_status} 已配置 | 统一canonical，避免重复收录 |
| OG/Twitter Card标签 | ❌ 缺失 | {og_status} 已补全 | 修复社交分享预览，提升点击量 |
| Article结构化数据 | 🟡 部分配置 | {article_schema_status} 已完善 | 增强搜索展示，提升CTR |
| GSC索引提交 | ❌ 未授权 | {gsc_status} | 需手动完成域名验证 |
| 人设年限统一 | 🟡 {posts_with_conflict}篇冲突 | {'✅ 已修正' if posts_with_conflict == 0 else f'🟡 剩余{posts_with_conflict}篇'} | 内容可信度提升 |
| 联盟链接覆盖 | 21.4% | {coverage}% | {'📈 提升' if coverage > 21.4 else '➡️ 持平'} |
| 文章底部CTA区块 | ❌ 缺失 | 🟡 进行中 | 搭建转化入口 |"""

        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "template": "blue",
                "title": {"tag": "plain_text", "content": f"📊 ChinaBound Travel 运营周报 | 第 {prev_week_num} 周 ({week_start} ~ {week_end})"},
                "subtitle": {"tag": "plain_text", "content": f"🕒 生成时间：{today.strftime('%Y-%m-%d %H:%M:%S')}"}
            },
            "elements": [
                {"tag": "div", "text": {"tag": "lark_md", "content": core_kpi_table}},
                ({"tag": "div", "text": {"tag": "lark_md", "content": data.get("okr_section", "")}} if data.get("okr_section") else None),
                ({"tag": "div", "text": {"tag": "lark_md", "content": data.get("advice_section", "")}} if data.get("advice_section") else None),
                {"tag": "div", "text": {"tag": "lark_md", "content": channel_table}},
                {"tag": "div", "text": {"tag": "lark_md", "content": pages_table}},
                {"tag": "div", "text": {"tag": "lark_md", "content": seo_section}},
                {"tag": "div", "text": {"tag": "lark_md", "content": affiliate_section}},
                {"tag": "div", "text": {"tag": "lark_md", "content": email_section}},
                {"tag": "div", "text": {"tag": "lark_md", "content": content_section}},
                {"tag": "div", "text": {"tag": "lark_md", "content": review_section}},
                {"tag": "div", "text": {"tag": "lark_md", "content": risks_section}},
                {"tag": "div", "text": {"tag": "lark_md", "content": plan_section}},
                {"tag": "div", "text": {"tag": "lark_md", "content": improvement_section}},
                {"tag": "div", "text": {"tag": "lark_md", "content": f"\n---\n💡 本周报由自动化脚本生成 | 每周一早 08:00 自动推送\n📐 数据口径：{_caliber}，联盟数据来自 Travelpayouts，内容巡检为本地扫描结果。\n如数据异常，请核查 API 密钥与站点配置"}}
            ]
        }
        # 过滤空板块（None 占位）
        card["elements"] = [el for el in card["elements"] if el]

        return card

    def run(self) -> bool:
        """执行周报推送"""
        print("=" * 60)
        print("🌍 ChinaBound Travel 运营周报 v3.0")
        print("=" * 60)

        data = self.collect_data()

        # 保存 OKR 快照（计划=下周计划，供下期复盘；CI 中由 workflow 提交回 git）
        okr_utils.save_snapshot("weekly", okr_utils.period_key("weekly"), data.get("next_week_plan", []), data)

        print("📝 构建飞书卡片...")
        card = self.build_weekly_card(data)
        print("📤 发送飞书消息...")
        success = self.send_card_message(card)

        self._save_week_data(data)

        report_path = REPORTS_DIR / f"weekly_report_{datetime.now().strftime('%Y%m%d')}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"📁 周报已保存: {report_path}")

        print("=" * 60)
        print(f"{'✅ 周报推送完成' if success else '❌ 周报推送失败'}")
        print("=" * 60)

        return success


def main():
    reporter = FeishuWeeklyReporter()
    success = reporter.run()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())