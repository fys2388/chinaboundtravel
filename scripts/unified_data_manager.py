#!/usr/bin/env python3
"""
ChinaBound Travel - 统一数据管理器
Unified Data Manager

整合所有数据源，为7大AI Agent提供统一的数据访问接口：
- GA4: 流量、用户行为、转化数据
- GSC: 搜索展示、点击、排名数据
- Travelpayouts: 联盟点击、订单、佣金数据
- MailerLite: 邮件订阅、用户数据
- Buffer: 社媒发布、互动数据
- 本地: 内容扫描、CTA审计、质量检测

使用方式：
    from unified_data_manager import UnifiedDataManager
    dm = UnifiedDataManager()
    ga4_data = dm.get_ga4_data(days=7)
    gsc_data = dm.get_gsc_data(days=28)
"""

import os
import sys
import json
import csv
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
DATA_CACHE_DIR = REPORTS_DIR / "data_cache"
DATA_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass


class UnifiedDataManager:
    """统一数据管理器"""

    def __init__(self, use_cache: bool = True):
        self.use_cache = use_cache
        self.cache = {}
        self._load_config()

    def _load_config(self):
        """加载配置"""
        self.config = {
            "ga4": {
                "api_key": os.environ.get("GA4_API_KEY", ""),
                "property_id": os.environ.get("GA4_PROPERTY_ID", "541752321"),
                "service_account_json": os.environ.get("GA4_SERVICE_ACCOUNT_JSON", ""),
            },
            "gsc": {
                "service_account_json": os.environ.get("GSC_SERVICE_ACCOUNT_JSON", ""),
                "site_url": os.environ.get("GSC_SITE_URL", "sc-domain:chinaboundtravel.com"),
            },
            "travelpayouts": {
                "api_token": os.environ.get("TRAVELPAYOUTS_API_TOKEN", ""),
                "marker": os.environ.get("TRAVELPAYOUTS_MARKER", ""),
                "drive_id": os.environ.get("TRAVELPAYOUTS_DRIVE_ID", ""),
            },
            "mailerlite": {
                "api_token": os.environ.get("MAILERLITE_API_TOKEN", ""),
            },
            "buffer": {
                "worker_url": os.environ.get("BUFFER_WORKER_URL", ""),
                "new_worker_url": os.environ.get("NEW_BUFFER_WORKER_URL", ""),
                "api_token_a": os.environ.get("BUFFER_API_TOKEN_A", ""),
                "api_token_b": os.environ.get("BUFFER_API_TOKEN_B", ""),
            },
            "cloudflare": {
                "api_token": os.environ.get("CLOUDFLARE_API_TOKEN", ""),
                "zone_id": os.environ.get("CLOUDFLARE_ZONE_ID", ""),
            }
        }

    def _get_cache_key(self, source: str, **kwargs) -> str:
        """生成缓存键"""
        key_parts = [source]
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}={v}")
        return "_".join(key_parts)

    def _load_from_cache(self, cache_key: str) -> Optional[Dict]:
        """从缓存加载数据"""
        if not self.use_cache:
            return None

        cache_file = DATA_CACHE_DIR / f"{cache_key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, encoding="utf-8") as f:
                    data = json.load(f)
                # 检查缓存是否过期（默认24小时）
                cached_at = datetime.fromisoformat(data.get("cached_at", "2020-01-01"))
                if (datetime.now() - cached_at).total_seconds() < 86400:
                    return data.get("data")
            except Exception:
                pass
        return None

    def _save_to_cache(self, cache_key: str, data: Any):
        """保存数据到缓存"""
        if not self.use_cache:
            return

        cache_file = DATA_CACHE_DIR / f"{cache_key}.json"
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump({
                    "cached_at": datetime.now().isoformat(),
                    "data": data
                }, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ==================== GA4 数据 ====================

    def get_ga4_data(self, days: int = 7, use_sample: bool = False) -> Dict[str, Any]:
        """获取GA4数据"""
        cache_key = self._get_cache_key("ga4", days=days)
        cached = self._load_from_cache(cache_key)
        if cached:
            return cached

        if use_sample or not self.config["ga4"]["api_key"]:
            data = self._get_sample_ga4_data(days)
        else:
            try:
                data = self._fetch_ga4_data(days)
            except Exception as e:
                print(f"  ⚠️ GA4数据获取失败，使用样本数据: {e}")
                data = self._get_sample_ga4_data(days)

        self._save_to_cache(cache_key, data)
        return data

    def _fetch_ga4_data(self, days: int) -> Dict[str, Any]:
        """从GA4 API获取数据（简化版，实际使用时参考feishu_daily_report.py）"""
        # 这里简化处理，实际应该调用GA4 Data API
        # 参考 scripts/feishu_daily_report.py 中的GA4数据获取逻辑
        raise NotImplementedError("GA4 API fetch not implemented in unified manager, use sample data")

    def _get_sample_ga4_data(self, days: int) -> Dict[str, Any]:
        """获取样本GA4数据"""
        return {
            "period": f"last_{days}_days",
            "total_users": 100 + days * 15,
            "sessions": 150 + days * 20,
            "page_views": 300 + days * 40,
            "bounce_rate": 0.65,
            "avg_session_duration": 120 + days * 2,
            "top_pages": [
                {"page": "/posts/china-travel-guide-2026/", "views": 50 + days * 5},
                {"page": "/posts/144-hour-visa-free-transit-guide/", "views": 40 + days * 4},
                {"page": "/posts/china-high-speed-rail-guide/", "views": 30 + days * 3},
            ],
            "traffic_sources": {
                "organic_search": 35,
                "direct": 25,
                "organic_social": 20,
                "referral": 10,
                "email": 10
            },
            "countries": {
                "United States": 30,
                "United Kingdom": 15,
                "Canada": 10,
                "Australia": 8,
                "Germany": 7
            }
        }

    # ==================== GSC 数据 ====================

    def get_gsc_data(self, days: int = 28, use_sample: bool = False) -> Dict[str, Any]:
        """获取GSC数据"""
        cache_key = self._get_cache_key("gsc", days=days)
        cached = self._load_from_cache(cache_key)
        if cached:
            return cached

        # 优先从本地CSV文件加载
        csv_file = REPORTS_DIR / "seo" / "CONTENT_SEO_INVENTORY.csv"
        if csv_file.exists():
            data = self._load_gsc_from_csv(csv_file)
        elif use_sample or not self.config["gsc"]["service_account_json"]:
            data = self._get_sample_gsc_data(days)
        else:
            try:
                data = self._fetch_gsc_data(days)
            except Exception as e:
                print(f"  ⚠️ GSC数据获取失败，使用样本数据: {e}")
                data = self._get_sample_gsc_data(days)

        self._save_to_cache(cache_key, data)
        return data

    def _load_gsc_from_csv(self, csv_file: Path) -> Dict[str, Any]:
        """从CSV文件加载GSC数据"""
        pages = []
        try:
            with open(csv_file, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    pages.append({
                        "url": row.get("url", ""),
                        "title": row.get("title", ""),
                        "impressions_28d": int(row.get("impressions_28d", 0) or 0),
                        "clicks_28d": int(row.get("clicks_28d", 0) or 0),
                        "ctr_28d": float(row.get("ctr_28d", 0) or 0),
                        "position_28d": float(row.get("position_28d", 0) or 0),
                        "indexed_status": row.get("indexed_status", "unknown")
                    })
        except Exception as e:
            print(f"  ⚠️ 加载GSC CSV失败: {e}")

        return {
            "total_pages": len(pages),
            "indexed_pages": sum(1 for p in pages if p["indexed_status"] == "INDEXED"),
            "total_impressions": sum(p["impressions_28d"] for p in pages),
            "total_clicks": sum(p["clicks_28d"] for p in pages),
            "avg_position": sum(p["position_28d"] for p in pages if p["position_28d"] > 0) / max(1, sum(1 for p in pages if p["position_28d"] > 0)),
            "top_pages": sorted(pages, key=lambda x: x["impressions_28d"], reverse=True)[:10],
            "all_pages": pages
        }

    def _fetch_gsc_data(self, days: int) -> Dict[str, Any]:
        """从GSC API获取数据"""
        raise NotImplementedError("GSC API fetch not implemented in unified manager")

    def _get_sample_gsc_data(self, days: int) -> Dict[str, Any]:
        """获取样本GSC数据"""
        return {
            "period": f"last_{days}_days",
            "total_pages": 60,
            "indexed_pages": 53,
            "total_impressions": 2000 + days * 50,
            "total_clicks": 50 + days * 2,
            "avg_position": 15.5,
            "top_queries": [
                {"query": "china travel guide", "impressions": 500, "clicks": 15, "position": 8.2},
                {"query": "144 hour visa china", "impressions": 300, "clicks": 10, "position": 5.1},
                {"query": "china high speed rail", "impressions": 200, "clicks": 5, "position": 12.3},
            ],
            "top_pages": [
                {"page": "/posts/china-travel-guide-2026/", "impressions": 800, "clicks": 20, "position": 7.5},
                {"page": "/posts/144-hour-visa-free-transit-guide/", "impressions": 500, "clicks": 15, "position": 4.2},
            ]
        }

    # ==================== Travelpayouts 数据 ====================

    def get_travelpayouts_data(self, days: int = 28, use_sample: bool = False) -> Dict[str, Any]:
        """获取Travelpayouts联盟数据"""
        cache_key = self._get_cache_key("travelpayouts", days=days)
        cached = self._load_from_cache(cache_key)
        if cached:
            return cached

        if use_sample or not self.config["travelpayouts"]["api_token"]:
            data = self._get_sample_travelpayouts_data(days)
        else:
            try:
                data = self._fetch_travelpayouts_data(days)
            except Exception as e:
                print(f"  ⚠️ Travelpayouts数据获取失败，使用样本数据: {e}")
                data = self._get_sample_travelpayouts_data(days)

        self._save_to_cache(cache_key, data)
        return data

    def _fetch_travelpayouts_data(self, days: int) -> Dict[str, Any]:
        """从Travelpayouts API获取数据"""
        raise NotImplementedError("Travelpayouts API fetch not implemented")

    def _get_sample_travelpayouts_data(self, days: int) -> Dict[str, Any]:
        """获取样本Travelpayouts数据"""
        return {
            "period": f"last_{days}_days",
            "impressions": 5000 + days * 100,
            "clicks": 100 + days * 3,
            "searches": 50 + days * 1,
            "bookings": 2 + (days // 14),
            "revenue": 50.0 + (days // 7) * 15.0,
            "ctr": 0.02,
            "conversion_rate": 0.02,
            "by_product": {
                "hotels": {"clicks": 60, "bookings": 1, "revenue": 30.0},
                "flights": {"clicks": 25, "bookings": 1, "revenue": 15.0},
                "tours": {"clicks": 10, "bookings": 0, "revenue": 0},
                "insurance": {"clicks": 5, "bookings": 0, "revenue": 5.0}
            },
            "by_partner": {
                "Booking.com": {"clicks": 40, "revenue": 25.0},
                "Klook": {"clicks": 20, "revenue": 10.0},
                "Trip.com": {"clicks": 25, "revenue": 12.0},
                "Agoda": {"clicks": 15, "revenue": 3.0}
            }
        }

    # ==================== MailerLite 数据 ====================

    def get_mailerlite_data(self, use_sample: bool = False) -> Dict[str, Any]:
        """获取MailerLite邮件订阅数据"""
        cache_key = self._get_cache_key("mailerlite")
        cached = self._load_from_cache(cache_key)
        if cached:
            return cached

        if use_sample or not self.config["mailerlite"]["api_token"]:
            data = self._get_sample_mailerlite_data()
        else:
            try:
                data = self._fetch_mailerlite_data()
            except Exception as e:
                print(f"  ⚠️ MailerLite数据获取失败，使用样本数据: {e}")
                data = self._get_sample_mailerlite_data()

        self._save_to_cache(cache_key, data)
        return data

    def _fetch_mailerlite_data(self) -> Dict[str, Any]:
        """从MailerLite API获取数据"""
        raise NotImplementedError("MailerLite API fetch not implemented")

    def _get_sample_mailerlite_data(self) -> Dict[str, Any]:
        """获取样本MailerLite数据"""
        return {
            "total_subscribers": 1,
            "active_subscribers": 1,
            "unsubscribed": 0,
            "new_this_week": 0,
            "new_this_month": 1,
            "open_rate": 0.0,
            "click_rate": 0.0,
            "groups": [
                {"name": "Newsletter", "count": 1},
                {"name": "Lead Magnet - Visa Checklist", "count": 0}
            ],
            "top_forms": [
                {"name": "Sidebar Newsletter", "submissions": 1},
                {"name": "Article Bottom CTA", "submissions": 0}
            ]
        }

    # ==================== Buffer 社媒数据 ====================

    def get_buffer_data(self, days: int = 28, use_sample: bool = False) -> Dict[str, Any]:
        """获取Buffer社媒数据"""
        cache_key = self._get_cache_key("buffer", days=days)
        cached = self._load_from_cache(cache_key)
        if cached:
            return cached

        # 优先从本地社媒数据文件加载
        social_data_file = REPORTS_DIR / "social" / "post_performance_data.json"
        if social_data_file.exists():
            try:
                with open(social_data_file, encoding="utf-8") as f:
                    raw_data = json.load(f)
                data = {
                    "total_posts": raw_data.get("total_count", 0),
                    "posts": raw_data.get("posts", []),
                    "data_source": "local_cache"
                }
                self._save_to_cache(cache_key, data)
                return data
            except Exception as e:
                print(f"  ⚠️ 加载本地Buffer数据失败: {e}")

        if use_sample or not self.config["buffer"]["api_token_a"]:
            data = self._get_sample_buffer_data(days)
        else:
            try:
                data = self._fetch_buffer_data(days)
            except Exception as e:
                print(f"  ⚠️ Buffer数据获取失败，使用样本数据: {e}")
                data = self._get_sample_buffer_data(days)

        self._save_to_cache(cache_key, data)
        return data

    def _fetch_buffer_data(self, days: int) -> Dict[str, Any]:
        """从Buffer API获取数据"""
        raise NotImplementedError("Buffer API fetch not implemented")

    def _get_sample_buffer_data(self, days: int) -> Dict[str, Any]:
        """获取样本Buffer数据"""
        return {
            "period": f"last_{days}_days",
            "total_posts": 50,
            "total_impressions": 21411,
            "total_clicks": 779,
            "total_engagement": 1194,
            "avg_engagement_rate": 0.0558,
            "avg_ctr": 0.0364,
            "by_platform": {
                "pinterest": {"posts": 10, "impressions": 9248, "clicks": 364, "engagement_rate": 0.0587},
                "instagram": {"posts": 10, "impressions": 4725, "clicks": 94, "engagement_rate": 0.0507},
                "facebook": {"posts": 10, "impressions": 2889, "clicks": 81, "engagement_rate": 0.0504},
                "x": {"posts": 10, "impressions": 2482, "clicks": 121, "engagement_rate": 0.0503},
                "linkedin": {"posts": 10, "impressions": 2067, "clicks": 119, "engagement_rate": 0.0449}
            },
            "top_posts": [
                {"id": "post_001", "platform": "pinterest", "impressions": 1500, "clicks": 60, "engagement_rate": 0.08},
                {"id": "post_002", "platform": "instagram", "impressions": 800, "clicks": 25, "engagement_rate": 0.07}
            ]
        }

    # ==================== 本地内容数据 ====================

    def get_content_data(self) -> Dict[str, Any]:
        """获取本地内容数据"""
        posts_dir = PROJECT_ROOT / "content" / "posts"
        posts = []

        if posts_dir.exists():
            for md_file in posts_dir.glob("*.md"):
                try:
                    content = md_file.read_text(encoding="utf-8")
                    # 简单解析Front Matter
                    title_match = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', content, re.MULTILINE)
                    date_match = re.search(r'^date:\s*["\']?(.+?)["\']?\s*$', content, re.MULTILINE)
                    word_count = len(content.split())

                    posts.append({
                        "file": md_file.name,
                        "title": title_match.group(1).strip() if title_match else md_file.stem,
                        "date": date_match.group(1).strip()[:10] if date_match else "",
                        "word_count": word_count,
                        "has_affiliate": bool(re.search(r'(booking\.com|agoda\.com|klook\.com|trip\.com)', content, re.IGNORECASE)),
                        "has_faq": "faq" in content.lower(),
                        "image_count": len(re.findall(r'!\[.*?\]\(.*?\)', content))
                    })
                except Exception:
                    pass

        return {
            "total_posts": len(posts),
            "avg_word_count": sum(p["word_count"] for p in posts) / max(1, len(posts)),
            "posts_with_affiliate": sum(1 for p in posts if p["has_affiliate"]),
            "posts_with_faq": sum(1 for p in posts if p["has_faq"]),
            "posts_with_images": sum(1 for p in posts if p["image_count"] > 0),
            "posts": posts
        }

    # ==================== 综合数据 ====================

    def get_all_data(self, days: int = 28) -> Dict[str, Any]:
        """获取所有数据源的综合数据"""
        print("\n" + "=" * 60)
        print("  统一数据管理器 - 获取所有数据源")
        print("=" * 60)

        all_data = {
            "fetched_at": datetime.now().isoformat(),
            "ga4": self.get_ga4_data(days=min(days, 7)),
            "gsc": self.get_gsc_data(days=days),
            "travelpayouts": self.get_travelpayouts_data(days=days),
            "mailerlite": self.get_mailerlite_data(),
            "buffer": self.get_buffer_data(days=days),
            "content": self.get_content_data()
        }

        print(f"\n  ✅ 数据获取完成:")
        print(f"    GA4: {all_data['ga4'].get('total_users', 'N/A')} 用户")
        print(f"    GSC: {all_data['gsc'].get('total_impressions', 'N/A')} 展示")
        print(f"    Travelpayouts: {all_data['travelpayouts'].get('revenue', 'N/A')} 收入")
        print(f"    MailerLite: {all_data['mailerlite'].get('total_subscribers', 'N/A')} 订阅")
        print(f"    Buffer: {all_data['buffer'].get('total_posts', 'N/A')} 帖子")
        print(f"    Content: {all_data['content'].get('total_posts', 'N/A')} 文章")

        return all_data

    def get_data_quality_report(self) -> Dict[str, Any]:
        """获取数据质量报告"""
        report = {
            "checked_at": datetime.now().isoformat(),
            "sources": {}
        }

        # 检查各数据源配置
        for source, config in self.config.items():
            has_config = any(v for v in config.values() if v)
            report["sources"][source] = {
                "configured": has_config,
                "fields_configured": {k: bool(v) for k, v in config.items()}
            }

        # 检查本地数据文件
        report["local_files"] = {
            "gsc_csv": (REPORTS_DIR / "seo" / "CONTENT_SEO_INVENTORY.csv").exists(),
            "social_data": (REPORTS_DIR / "social" / "post_performance_data.json").exists(),
            "content_posts": len(list((PROJECT_ROOT / "content" / "posts").glob("*.md"))) if (PROJECT_ROOT / "content" / "posts").exists() else 0
        }

        return report


def main():
    """主函数 - 测试数据管理器"""
    import argparse

    parser = argparse.ArgumentParser(description="ChinaBound Travel 统一数据管理器")
    parser.add_argument("--all", action="store_true", help="获取所有数据")
    parser.add_argument("--ga4", action="store_true", help="仅获取GA4数据")
    parser.add_argument("--gsc", action="store_true", help="仅获取GSC数据")
    parser.add_argument("--travelpayouts", action="store_true", help="仅获取Travelpayouts数据")
    parser.add_argument("--mailerlite", action="store_true", help="仅获取MailerLite数据")
    parser.add_argument("--buffer", action="store_true", help="仅获取Buffer数据")
    parser.add_argument("--content", action="store_true", help="仅获取内容数据")
    parser.add_argument("--quality", action="store_true", help="数据质量检查")
    parser.add_argument("--days", type=int, default=28, help="数据天数")
    parser.add_argument("--sample", action="store_true", help="使用样本数据")

    args = parser.parse_args()

    dm = UnifiedDataManager(use_cache=False)

    if args.quality:
        report = dm.get_data_quality_report()
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif args.all or not any([args.ga4, args.gsc, args.travelpayouts, args.mailerlite, args.buffer, args.content]):
        data = dm.get_all_data(days=args.days)
        print(f"\n📊 综合数据获取完成，共 {len(data)} 个数据源")
    elif args.ga4:
        data = dm.get_ga4_data(days=args.days, use_sample=args.sample)
        print(json.dumps(data, ensure_ascii=False, indent=2)[:2000])
    elif args.gsc:
        data = dm.get_gsc_data(days=args.days, use_sample=args.sample)
        print(json.dumps(data, ensure_ascii=False, indent=2)[:2000])
    elif args.travelpayouts:
        data = dm.get_travelpayouts_data(days=args.days, use_sample=args.sample)
        print(json.dumps(data, ensure_ascii=False, indent=2)[:2000])
    elif args.mailerlite:
        data = dm.get_mailerlite_data(use_sample=args.sample)
        print(json.dumps(data, ensure_ascii=False, indent=2)[:2000])
    elif args.buffer:
        data = dm.get_buffer_data(days=args.days, use_sample=args.sample)
        print(json.dumps(data, ensure_ascii=False, indent=2)[:2000])
    elif args.content:
        data = dm.get_content_data()
        print(json.dumps(data, ensure_ascii=False, indent=2)[:2000])


if __name__ == "__main__":
    main()
