# -*- coding: utf-8 -*-
"""
feishu_yearly_report.py - ChinaBound Travel 飞书年报推送
功能：年度运营数据 + 年度 OKR 完成度 + 去年计划复盘 + 下一年计划
版本：v1.0
"""
import os
import sys
import re

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

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

# OKR 公共工具
sys.path.insert(0, str(SCRIPT_DIR))
import okr_utils
import report_advice

try:
    from dotenv import load_dotenv
    load_dotenv(BLOG_ROOT / ".env")
except ImportError:
    pass

CONTENT_DIR = BLOG_ROOT / "content"
POSTS_DIR = CONTENT_DIR / "posts"
REPORTS_DIR = BLOG_ROOT / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

FEISHU_WEBHOOK_URL = os.environ.get("FEISHU_WEBHOOK_URL", "")
FEISHU_SECRET = os.environ.get("FEISHU_SECRET", "")
TRAVELPAYOUTS_API_TOKEN = os.environ.get("TRAVELPAYOUTS_API_TOKEN", "")
TRAVELPAYOUTS_MARKER = os.environ.get("TRAVELPAYOUTS_MARKER", "730795")
GA4_PROPERTY_ID = os.environ.get("GA4_PROPERTY_ID", "541752321")
GA4_SERVICE_ACCOUNT_JSON = os.environ.get("GA4_SERVICE_ACCOUNT_JSON", "")
MAILERLITE_API_TOKEN = os.environ.get("MAILERLITE_API_TOKEN", "")
GSC_SERVICE_ACCOUNT_JSON = os.environ.get("GSC_SERVICE_ACCOUNT_JSON", "")
GSC_SITE_URL = os.environ.get("GSC_SITE_URL", "sc-domain:chinaboundtravel.com")


class FeishuYearlyReporter:
    def _get_period(self):
        """报告上一年度，对比前一年度"""
        now = datetime.now()
        rep_year = now.year - 1
        return {
            "rep_start": f"{rep_year}-01-01", "rep_end": f"{rep_year}-12-31",
            "cmp_start": f"{rep_year - 1}-01-01", "cmp_end": f"{rep_year - 1}-12-31",
            "rep_label": f"{rep_year}年", "cmp_label": f"{rep_year - 1}年",
        }

    # ---------- 飞书 ----------
    def _generate_signature(self, timestamp: str) -> str:
        string_to_sign = f"{timestamp}\n{FEISHU_SECRET}"
        hmac_code = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
        return base64.b64encode(hmac_code).decode("utf-8")

    def send_card_message(self, card_content: dict) -> bool:
        if not FEISHU_WEBHOOK_URL:
            print("   ⚠️ FEISHU_WEBHOOK_URL 未配置")
            return False
        try:
            payload = {"msg_type": "interactive", "card": card_content}
            timestamp = str(round(datetime.now().timestamp()))
            if FEISHU_SECRET:
                payload["timestamp"] = timestamp
                payload["sign"] = self._generate_signature(timestamp)
            resp = requests.post(FEISHU_WEBHOOK_URL, json=payload, timeout=15)
            print(f"📤 飞书响应状态码: {resp.status_code}")
            print(f"📤 飞书响应内容: {resp.text[:200]}")
            return resp.status_code == 200 and '"StatusCode":0' in resp.text
        except Exception as e:
            print(f"   ⚠️ 飞书发送失败: {e}")
            return False

    # ---------- 服务账号 / GA4 ----------
    def _load_service_account(self, sa_json_str: str):
        if not sa_json_str:
            return None
        try:
            return json.loads(sa_json_str)
        except Exception:
            pass
        try:
            if "\\n" in sa_json_str and "BEGIN PRIVATE KEY" in sa_json_str:
                return json.loads(sa_json_str.replace("\\n", "\n"))
        except Exception:
            pass
        try:
            sa_path = Path(sa_json_str)
            if not sa_path.is_absolute():
                sa_path = BLOG_ROOT / sa_path
            if sa_path.exists() and sa_path.is_file():
                return json.loads(sa_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"   ⚠️ 服务账号加载失败: {e}")
        return None

    def _get_ga4_headers(self):
        if not GA4_SERVICE_ACCOUNT_JSON or not HAS_GOOGLE_AUTH:
            print("   ⚠️ GA4: 服务账号未配置")
            return None
        try:
            info = self._load_service_account(GA4_SERVICE_ACCOUNT_JSON)
            if not info:
                return None
            creds = service_account.Credentials.from_service_account_info(
                info, scopes=["https://www.googleapis.com/auth/analytics.readonly"])
            creds.refresh(Request())
            return {"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json"}
        except Exception as e:
            print(f"   ⚠️ GA4 认证失败: {e}")
        return None

    def _ga4_run_report(self, headers: dict, payload: dict):
        url = f"https://analyticsdata.googleapis.com/v1beta/properties/{GA4_PROPERTY_ID}:runReport"
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                return resp.json()
            print(f"   ⚠️ GA4 API 响应 {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            print(f"   ⚠️ GA4 API 调用失败: {e}")
        return None

    def _fetch_yearly_ga4(self) -> dict:
        headers = self._get_ga4_headers()
        if not headers:
            return None
        p = self._get_period()
        print(f"   🔍 GA4 年度数据（{p['rep_label']}: {p['rep_start']} ~ {p['rep_end']}）...")

        def fetch_range(start, end):
            res = self._ga4_run_report(headers, {
                "dateRanges": [{"startDate": start, "endDate": end}],
                "metrics": [
                    {"name": "activeUsers"}, {"name": "sessions"}, {"name": "screenPageViews"},
                    {"name": "averageSessionDuration"}, {"name": "bounceRate"}]})
            if res and "rows" in res:
                r = res["rows"][0]
                return {"users": int(r["metricValues"][0].get("value", "0")),
                        "sessions": int(r["metricValues"][1].get("value", "0")),
                        "pageviews": int(r["metricValues"][2].get("value", "0")),
                        "avg_duration": int(float(r["metricValues"][3].get("value", "0"))),
                        "bounce": round(float(r["metricValues"][4].get("value", "0")) * 100, 1)}
            return {"users": 0, "sessions": 0, "pageviews": 0, "avg_duration": 0, "bounce": 0.0}

        cur = fetch_range(p["rep_start"], p["rep_end"])
        prev = fetch_range(p["cmp_start"], p["cmp_end"])

        def change(c, v):
            if v == 0:
                return "-"
            chg = round((c - v) / v * 100, 1)
            icon = "📈" if chg > 0 else "📉" if chg < 0 else "➡️"
            return f"{icon} {abs(chg)}%"

        return {
            "year_label": p["rep_label"], "prev_year_label": p["cmp_label"],
            "year_start": p["rep_start"], "year_end": p["rep_end"],
            "year_users": cur["users"], "year_sessions": cur["sessions"],
            "year_pageviews": cur["pageviews"], "year_bounce": cur["bounce"],
            "year_avg_duration": cur["avg_duration"],
            "prev_users": prev["users"], "prev_pageviews": prev["pageviews"],
            "users_change": change(cur["users"], prev["users"]),
            "pageviews_change": change(cur["pageviews"], prev["pageviews"]),
        }

    # ---------- GSC ----------
    def _fetch_gsc_data(self) -> dict:
        if not GSC_SERVICE_ACCOUNT_JSON or not HAS_GOOGLE_AUTH:
            return {"status": "unauthorized"}
        try:
            info = self._load_service_account(GSC_SERVICE_ACCOUNT_JSON)
            if not info:
                return {"status": "unauthorized"}
            creds = service_account.Credentials.from_service_account_info(
                info, scopes=["https://www.googleapis.com/auth/webmasters.readonly"])
            creds.refresh(Request())
            from googleapiclient.discovery import build
            service = build("searchconsole", "v1", credentials=creds)
            candidates = [s.strip() for s in str(GSC_SITE_URL or "").split(",") if s.strip()]
            if "sc-domain:chinaboundtravel.com" not in candidates:
                candidates.append("sc-domain:chinaboundtravel.com")
            site_url = None
            for cand in candidates:
                try:
                    service.sites().get(siteUrl=cand).execute()
                    site_url = cand
                    break
                except Exception:
                    continue
            if not site_url:
                return {"status": "unauthorized"}
            p = self._get_period()
            resp = service.searchanalytics().query(
                siteUrl=site_url,
                body={"startDate": p["rep_start"], "endDate": p["rep_end"],
                      "rowLimit": 1000, "dataState": "final"}).execute()
            impressions = int(resp["rows"][0].get("impressions", 0)) if "rows" in resp else 0
            return {"status": "authorized", "gsc_impressions": impressions}
        except Exception as e:
            print(f"   ⚠️ GSC API 获取失败: {e}")
            return {"status": "error"}

    # ---------- Travelpayouts ----------
    def _fetch_yearly_travelpayouts(self) -> dict:
        if not TRAVELPAYOUTS_API_TOKEN:
            return {"tp_available": False}
        try:
            p = self._get_period()
            resp = requests.post(
                "https://api.travelpayouts.com/statistics/v1/execute_query",
                headers={"X-Access-Token": TRAVELPAYOUTS_API_TOKEN, "Content-Type": "application/json"},
                json={"fields": ["redirects_count", "inits_count", "searches_count",
                                 "paid_actions_count", "paid_profit_usd_sum"],
                      "filters": [
                          {"field": "date", "op": "ge", "value": p["rep_start"]},
                          {"field": "date", "op": "le", "value": p["rep_end"]}],
                      "offset": 0, "limit": 1},
                timeout=30)
            if resp.status_code != 200:
                return {"tp_available": False}
            rows = resp.json().get("results", []) or resp.json().get("data", [])
            row = rows[0] if rows else {}
            return {"tp_available": True,
                    "year_revenue": float(row.get("paid_profit_usd_sum", 0) or 0)}
        except Exception as e:
            print(f"   ⚠️ Travelpayouts API 获取失败: {e}")
            return {"tp_available": False}

    # ---------- MailerLite ----------
    def _fetch_yearly_mailerlite(self) -> dict:
        if not MAILERLITE_API_TOKEN:
            return {"ml_available": False}
        # 清洗 token：去除 BOM（\ufeff）和空白，避免 latin-1 编码错误
        clean_token = MAILERLITE_API_TOKEN.lstrip("\ufeff").strip()
        clean_token = "".join(c for c in clean_token if ord(c) < 128)
        try:
            headers = {"Authorization": f"Bearer {clean_token}", "Content-Type": "application/json"}
            resp = requests.get("https://connect.mailerlite.com/api/subscribers", headers=headers,
                                params={"limit": 1}, timeout=15)
            if resp.status_code != 200:
                return {"ml_available": False}
            return {"ml_available": True,
                    "ml_total_subscribers": int(resp.headers.get("x-total-count", "0"))}
        except Exception as e:
            return {"ml_available": False}

    # ---------- 内容 ----------
    def _scan_content_quality(self) -> dict:
        if not POSTS_DIR.exists():
            return {"total_posts": 0, "year_new_posts": 0}
        p = self._get_period()
        new_count = 0
        for post in POSTS_DIR.glob("*.md"):
            try:
                content = post.read_text(encoding="utf-8")
                fm = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
                if fm:
                    dm = re.search(r"^date:\s*[\"']?([\d-]+)", fm.group(1), re.MULTILINE)
                    if dm and p["rep_start"] <= dm.group(1) <= p["rep_end"]:
                        new_count += 1
            except Exception:
                continue
        return {"total_posts": len(list(POSTS_DIR.glob("*.md"))), "year_new_posts": new_count}

    # ---------- 汇总 ----------
    def collect_data(self) -> dict:
        print("📊 收集年报数据...")
        data = {}
        # 2.0 统一口径（P1-REPORT-03R）：SNAPSHOT 优先，命中则 GA4/GSC 采用统一快照，不再直连
        _snap_ga4 = reporting_snapshot_reader.snapshot_traffic("year")
        if _snap_ga4 is not None:
            print("   📦 2.0 统一快照命中：GA4/GSC 采用 SNAPSHOT 口径（as_of=%s）" % _snap_ga4.get("snapshot_as_of"))
            data.update(_snap_ga4)
            _snap_gsc = reporting_snapshot_reader.snapshot_gsc()
            if _snap_gsc is not None:
                data.update(_snap_gsc)
            else:
                data.update(self._fetch_gsc_data())
        else:
            ga4 = self._fetch_yearly_ga4()
            if ga4:
                data.update(ga4)
            data.update(self._fetch_gsc_data())
        tp = self._fetch_yearly_travelpayouts()
        if tp:
            data.update(tp)
        ml = self._fetch_yearly_mailerlite()
        if ml:
            data.update(ml)
        content = self._scan_content_quality()
        data["content_data"] = content
        data.update({"total_posts": content["total_posts"], "year_new_posts": content["year_new_posts"]})

        p = self._get_period()
        rep_end_dt = datetime.strptime(p["rep_end"], "%Y-%m-%d")
        data["okr_section"] = okr_utils.build_okr_section(data, "yearly", report_date=rep_end_dt)
        prev_key = okr_utils.period_key("yearly", rep_end_dt - timedelta(days=1))
        prev_snap = okr_utils.load_snapshot("yearly", prev_key)
        data["okr_review"] = okr_utils.review_previous_plan(prev_snap, data)

        # 下一年计划（按年度 OKR 差距）
        plan = []
        okr = okr_utils.load_okr()
        if okr:
            annual_name_map = {"月访问用户": "年度访问用户", "月搜索曝光": "年度搜索曝光", "月联盟佣金": "年度联盟佣金"}
            for kr in okr.get("annual", {}).get("krs", []):
                cur = okr_utils.extract_kr(data, kr.get("source", ""))
                target = okr_utils._target_for(kr, "yearly")
                name = annual_name_map.get(kr.get("name", ""), kr.get("name", kr.get("id", "")))
                if target > 0 and cur < target:
                    plan.append({"task": f"达成「{name}」年度目标（当前{cur:g}/{target:g}{kr.get('unit','')}）",
                                 "priority": "high", "period": "下一年", "kr_id": kr.get("id"), "target": target})
        if not plan:
            plan = [{"task": "持续内容与 SEO 增长，保持年度 OKR 滚动迭代", "priority": "medium", "period": "下一年"}]
        data["next_year_plan"] = plan

        # 自动运营建议（基于真实数据精准生成）
        data["advice_section"] = report_advice.advice_section(data, "yearly")
        return data

    # ---------- 卡片 ----------
    def build_yearly_card(self, data: dict) -> dict:
        p = self._get_period()
        label = data.get("year_label", p["rep_label"])
        users = data.get("year_users", 0)
        sessions = data.get("year_sessions", 0)
        pageviews = data.get("year_pageviews", 0)
        dur = data.get("year_avg_duration", 0)
        dur_str = f"{dur // 60}分{dur % 60}秒" if dur >= 60 else f"{dur}秒"
        gsc_imp = data.get("gsc_impressions", 0)
        tp_rev = data.get("year_revenue", 0)
        ml_total = data.get("ml_total_subscribers", 0)
        total_posts = data.get("total_posts", 0)
        new_posts = data.get("year_new_posts", 0)

        okr_review_rows = "\n".join([f"| {r['task']} | {r['icon']} | {r['status']} | {r['period']} |"
                                     for r in data.get("okr_review", [])]) or "| - | - | - | - |"
        plan_rows = "\n".join([f"| {it['task']} | {'🔴' if it['priority']=='high' else '🟡'} | {it['period']} |"
                               for it in data.get("next_year_plan", [])]) or "| - | - | - |"

        main = f"""**📊 ChinaBound Travel 年度运营报告 | {label}**

| 指标 | {label} | {data.get('prev_year_label', '')} | 同比 |
| :--- | :--- | :--- | :--- |
| 访客数 | {users} 人 | {data.get('prev_users', 0)} | {data.get('users_change', '-')} |
| 页面浏览 | {pageviews} 次 | {data.get('prev_pageviews', 0)} | {data.get('pageviews_change', '-')} |
| 会话数 | {sessions} 次 | - | - |
| 平均时长 | {dur_str} | - | - |

**🌱 年度盘点**
- 全年 GSC 搜索曝光：**{gsc_imp} 次**
- 内容：总文章 {total_posts} 篇｜{label}新增 {new_posts} 篇
- 联盟佣金：**${tp_rev:.2f}**
- 邮件订阅：**{ml_total} 人**"""

        review = f"""---
## ✅ 去年计划复盘（OKR 对齐）
| 计划项 | 优先级 | 状态 | 周期 |
| :--- | :--- | :--- | :--- |
{okr_review_rows}"""

        plan = f"""---
## 📋 下一年执行计划
| 任务项 | 优先级 | 周期 |
| :--- | :--- | :--- |
{plan_rows}"""

        card = {
            "config": {"wide_screen_mode": True},
            "header": {"template": "gold", "title": {"tag": "plain_text",
                       "content": f"📊 ChinaBound Travel 年度运营报告 | {label}"}},
            "elements": [
                {"tag": "div", "text": {"tag": "lark_md", "content": main}},
                ({"tag": "div", "text": {"tag": "lark_md", "content": data.get("okr_section", "")}}
                 if data.get("okr_section") else None),
                ({"tag": "div", "text": {"tag": "lark_md", "content": data.get("advice_section", "")}} if data.get("advice_section") else None),
                {"tag": "div", "text": {"tag": "lark_md", "content": review}},
                {"tag": "div", "text": {"tag": "lark_md", "content": plan}},
            ],
        }
        card["elements"] = [el for el in card["elements"] if el]
        return card

    # ---------- 执行 ----------
    def run(self) -> bool:
        print("=" * 60)
        print("🌍 ChinaBound Travel 年度运营报告")
        print("=" * 60)
        data = self.collect_data()
        p = self._get_period()
        rep_end_dt = datetime.strptime(p["rep_end"], "%Y-%m-%d")
        okr_utils.save_snapshot("yearly", okr_utils.period_key("yearly", rep_end_dt),
                                data.get("next_year_plan", []), data)
        print("📝 构建飞书年报卡片...")
        card = self.build_yearly_card(data)
        print("📤 发送飞书消息...")
        success = self.send_card_message(card)
        report_path = REPORTS_DIR / f"yearly_report_{datetime.now().strftime('%Y%m%d')}.json"
        with open(report_path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        print(f"📁 年报已保存: {report_path}")
        print("=" * 60)
        print(f"{'✅ 年报推送完成' if success else '❌ 年报推送失败'}")
        print("=" * 60)
        return success


def main():
    reporter = FeishuYearlyReporter()
    return 0 if reporter.run() else 1


if __name__ == "__main__":
    sys.exit(main())
