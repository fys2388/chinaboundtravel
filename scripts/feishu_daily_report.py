#!/usr/bin/env python3
"""
feishu_daily_report.py - ChinaBound Travel 飞书每日日报推送
功能：流量、内容、联盟、运维四大核心板块数据推送
"""

import os
import sys

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

# API配置
TRAVELPAYOUTS_API_TOKEN = os.environ.get("TRAVELPAYOUTS_API_TOKEN", "")
CLOUDFLARE_API_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN", "")
CLOUDFLARE_ZONE_ID = os.environ.get("CLOUDFLARE_ZONE_ID", "")


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
        """构建飞书日报卡片"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 状态图标
        traffic_status = "🟢" if data.get("site_up") else "🔴"
        content_status = "🟢" if data.get("content_issues", 0) == 0 else "🟡"
        affiliate_status = "🟢" if data.get("affiliate_revenue", 0) > 0 else "⚪"
        ops_status = "🟢" if data.get("ops_issues", 0) == 0 else "🔴"
        
        card = {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"📊 ChinaBound Travel 每日日报 ({today})"
                },
                "template": "blue"
            },
            "elements": [
                # === 1. 流量数据总览 ===
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"""**🚀 流量数据总览** {traffic_status}

| 指标 | 今日数据 |
| --- | --- |
| 访客数 | {data.get('visitors', 0):,} |
| 页面浏览 | {data.get('page_views', 0):,} |
| Top1文章 | {data.get('top_article', 'N/A')} |
| 新增关键词 | {data.get('new_keywords', 0)} 个"""
                    }
                },
                {"tag": "hr"},
                
                # === 2. 内容生产与优化 ===
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"""**📝 内容生产与优化** {content_status}

| 指标 | 数量 |
| --- | --- |
| 今日新发 | {data.get('new_posts', 0)} 篇 |
| 待发布 | {data.get('pending_posts', 0)} 篇 |
| 占位符未替换 | {data.get('placeholder_articles', 0)} 篇 |
| 配图缺失 | {data.get('missing_images', 0)} 篇 |
| Alt文本缺失 | {data.get('missing_alt', 0)} 篇"""
                    }
                },
                {"tag": "hr"},
                
                # === 3. 联盟变现数据 ===
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"""**💰 联盟变现数据** {affiliate_status}

| 平台 | 点击 | 转化 | 收入 |
| --- | --- | --- | --- |
| Travelpayouts | {data.get('tp_clicks', 0)} | {data.get('tp_bookings', 0)} | $ {data.get('tp_revenue', 0):.2f} |
| NordVPN | {data.get('nord_clicks', 0)} | {data.get('nord_conversions', 0)} | $ {data.get('nord_revenue', 0):.2f} |

**Top3转化文章**: {data.get('top_converting_articles', 'N/A')}"""
                    }
                },
                {"tag": "hr"},
                
                # === 4. 运维与合规 ===
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"""**🔧 运维与合规** {ops_status}

| 指标 | 数量 |
| --- | --- |
| 404页面 | {data.get('404_count', 0)} 个 |
| GSC索引错误 | {data.get('gsc_errors', 0)} 个 |
| 结构化数据缺失 | {data.get('schema_issues', 0)} 个 |
| 响应时长 | {data.get('response_time', 0)} ms |

**待处理SEO项**: {data.get('pending_seo', '无')}"""
                    }
                },
                {"tag": "hr"},
                
                # === AI成本 ===
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"""**🤖 AI成本监控**

今日消耗: ¥ {data.get('ai_cost', 0):.2f} / ¥ 30.00
API调用: {data.get('api_calls', 0)} 次
使用率: {data.get('ai_usage_percent', 0):.1f}%"""
                    }
                },
                {"tag": "hr"},
                
                # === 待处理问题汇总 ===
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": f"⚠️ 待处理问题: {data.get('total_issues', 0)} 个 | 详情请查看 reports 目录"
                        }
                    ]
                }
            ]
        }
        
        return card
    
    def collect_data(self) -> dict:
        """收集日报数据"""
        data = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "site_up": True,
            "visitors": 0,
            "page_views": 0,
            "top_article": "N/A",
            "new_keywords": 0,
            "new_posts": 0,
            "pending_posts": 0,
            "placeholder_articles": 0,
            "missing_images": 0,
            "missing_alt": 0,
            "tp_clicks": 0,
            "tp_bookings": 0,
            "tp_revenue": 0.0,
            "nord_clicks": 0,
            "nord_conversions": 0,
            "nord_revenue": 0.0,
            "top_converting_articles": "N/A",
            "404_count": 0,
            "gsc_errors": 0,
            "schema_issues": 0,
            "response_time": 0,
            "pending_seo": "无",
            "ai_cost": 0.0,
            "api_calls": 0,
            "ai_usage_percent": 0.0,
            "total_issues": 0,
            "content_issues": 0,
            "affiliate_revenue": 0.0,
            "ops_issues": 0
        }
        
        # 1. 检查网站状态
        try:
            response = requests.get("https://chinaboundtravel.com", timeout=10)
            data["site_up"] = response.status_code == 200
        except:
            data["site_up"] = False
        
        # 2. 统计文章数量
        posts = list(POSTS_DIR.glob("*.md"))
        today_posts = [p for p in posts if self._is_today_post(p)]
        data["new_posts"] = len(today_posts)
        data["pending_posts"] = len([p for p in posts if "_draft" in str(p) or "draft" in str(p)])
        
        # 3. 检查占位符和配图问题
        placeholder_count = 0
        missing_image_count = 0
        
        for post in posts:
            try:
                content = post.read_text(encoding='utf-8')
                # 检查占位符
                if "#TP_" in content or "#VPN_" in content or "PLACEHOLDER" in content:
                    placeholder_count += 1
                # 检查配图
                if "[Image:" in content and "](http" not in content:
                    missing_image_count += 1
            except:
                pass
        
        data["placeholder_articles"] = placeholder_count
        data["missing_images"] = missing_image_count
        
        # 4. Travelpayouts数据
        tp_data = self._fetch_travelpayouts()
        if tp_data:
            data["tp_clicks"] = tp_data.get("clicks", 0)
            data["tp_bookings"] = tp_data.get("bookings", 0)
            data["tp_revenue"] = tp_data.get("revenue_usd", 0.0)
            data["affiliate_revenue"] = data["tp_revenue"]
        
        # 5. AI成本数据
        ai_data = self._fetch_ai_cost()
        if ai_data:
            data["ai_cost"] = ai_data.get("used_yuan", 0.0)
            data["api_calls"] = ai_data.get("api_calls", 0)
            data["ai_usage_percent"] = ai_data.get("used_percent", 0.0)
        
        # 6. 统计总问题数
        data["content_issues"] = placeholder_count + missing_image_count
        data["total_issues"] = data["content_issues"] + data["404_count"] + data["gsc_errors"]
        
        return data
    
    def _is_today_post(self, filepath: Path) -> bool:
        """检查是否是今天发布的文章"""
        try:
            filename = filepath.name
            if filename.startswith(datetime.now().strftime("%Y-%m-%d")):
                return True
            # 检查文件修改时间
            mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
            if mtime.date() == datetime.now().date():
                return True
        except:
            pass
        return False
    
    def _fetch_travelpayouts(self) -> dict:
        """获取Travelpayouts数据"""
        if not TRAVELPAYOUTS_API_TOKEN:
            return None
        
        try:
            url = "https://api.travelpayouts.com/statistics/v1/execute_query"
            headers = {
                "X-Access-Token": TRAVELPAYOUTS_API_TOKEN,
                "Content-Type": "application/json"
            }
            
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            
            payload = {
                "fields": ["action_id", "sub_id", "price_usd", "paid_profit_usd", "state", "date", "type"],
                "filters": [
                    {"field": "date", "op": "ge", "value": start_date},
                    {"field": "date", "op": "le", "value": end_date}
                ],
                "sort": [{"field": "date", "order": "desc"}],
                "offset": 0,
                "limit": 50
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                results = result.get("results", [])
                
                clicks = 0
                bookings = 0
                revenue = 0.0
                
                for item in results:
                    if item.get("type") in ["redirect", "init"]:
                        clicks += 1
                    if item.get("state") == "paid":
                        bookings += 1
                        revenue += float(item.get("paid_profit_usd", 0) or 0)
                
                return {
                    "clicks": clicks,
                    "bookings": bookings,
                    "revenue_usd": round(revenue, 2)
                }
        except Exception as e:
            print(f"⚠️ Travelpayouts API 获取失败: {e}")
        
        return None
    
    def _fetch_ai_cost(self) -> dict:
        """获取AI成本数据"""
        try:
            manifest_path = BLOG_ROOT / "manifest.json"
            if manifest_path.exists():
                with open(manifest_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                cost_tracking = data.get("cost_tracking", {})
                today = datetime.now().strftime("%Y-%m-%d")
                today_data = cost_tracking.get(today, {})
                
                budget = 30.0
                used = today_data.get("total_cost_yuan", 0.0)
                
                return {
                    "used_yuan": used,
                    "budget_yuan": budget,
                    "api_calls": today_data.get("api_calls", 0),
                    "used_percent": round((used / budget * 100), 1) if budget > 0 else 0
                }
        except:
            pass
        
        return {"used_yuan": 0, "budget_yuan": 30, "api_calls": 0, "used_percent": 0}
    
    def run(self) -> bool:
        """执行日报推送"""
        print("=" * 60)
        print("📊 ChinaBound Travel 飞书每日日报")
        print("=" * 60)
        
        # 1. 收集数据
        print("📥 收集数据...")
        data = self.collect_data()
        
        # 2. 构建卡片
        print("📝 构建飞书卡片...")
        card = self.build_daily_card(data)
        
        # 3. 发送消息
        print("📤 发送飞书消息...")
        success = self.send_card_message(card)
        
        # 4. 保存日报记录
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
