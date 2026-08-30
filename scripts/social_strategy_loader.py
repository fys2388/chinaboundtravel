#!/usr/bin/env python3
"""
ChinaBound Travel - Social Strategy Loader
社媒发布策略加载器

功能：加载social_publish_strategy.json，为社媒内容生成提供策略指导
- 最佳发布时间
- 最佳Hook关键词
- 最佳CTA类型
- 平台特定规则
- 学习洞察

使用方式：
    from social_strategy_loader import SocialStrategyLoader
    loader = SocialStrategyLoader()
    strategy = loader.get_strategy()
    best_times = loader.get_best_times('pinterest')
    best_hooks = loader.get_best_hooks('pinterest')
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
SOCIAL_DIR = REPORTS_DIR / "social"
STRATEGY_FILE = SOCIAL_DIR / "social_publish_strategy.json"


class SocialStrategyLoader:
    """社媒发布策略加载器"""

    def __init__(self, strategy_file: Optional[Path] = None):
        self.strategy_file = strategy_file or STRATEGY_FILE
        self.strategy = self._load_strategy()

    def _load_strategy(self) -> Dict[str, Any]:
        """加载策略文件"""
        if self.strategy_file.exists():
            try:
                with open(self.strategy_file, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"  ⚠️ 加载策略文件失败: {e}，使用默认策略")
        else:
            print(f"  ⚠️ 策略文件不存在: {self.strategy_file}，使用默认策略")

        # 默认策略
        return {
            "version": "default",
            "last_updated": datetime.now().isoformat(),
            "platforms": {
                "pinterest": {
                    "best_times": ["09:00", "14:00", "20:00"],
                    "best_hooks": ["travel tips", "itinerary", "guide"],
                    "best_ctas": ["save for later", "click to read"],
                    "content_types": ["guide", "tips", "itinerary"],
                    "max_posts_per_day": 3
                },
                "instagram": {
                    "best_times": ["10:00", "18:00", "21:00"],
                    "best_hooks": ["beautiful places", "travel inspiration"],
                    "best_ctas": ["link in bio", "swipe up"],
                    "content_types": ["visual", "lifestyle", "tips"],
                    "max_posts_per_day": 2
                },
                "facebook": {
                    "best_times": ["09:00", "13:00", "19:00"],
                    "best_hooks": ["travel tips", "guide", "checklist"],
                    "best_ctas": ["read more", "click here"],
                    "content_types": ["guide", "tips", "news"],
                    "max_posts_per_day": 2
                },
                "x": {
                    "best_times": ["08:00", "12:00", "17:00"],
                    "best_hooks": ["quick tips", "thread", "facts"],
                    "best_ctas": ["read thread", "click link"],
                    "content_types": ["tips", "facts", "thread"],
                    "max_posts_per_day": 3
                }
            },
            "global_rules": {
                "max_posts_per_day_per_platform": 3,
                "min_interval_minutes": 120,
                "use_utm_tracking": True,
                "brand_voice": "editorial",
                "avoid_legacy_persona": True
            },
            "learning_insights": [],
            "strategy_changes": []
        }

    def get_strategy(self) -> Dict[str, Any]:
        """获取完整策略"""
        return self.strategy

    def get_platform_strategy(self, platform: str) -> Optional[Dict[str, Any]]:
        """获取特定平台的策略"""
        return self.strategy.get("platforms", {}).get(platform.lower())

    def get_best_times(self, platform: str) -> List[str]:
        """获取特定平台的最佳发布时间"""
        platform_strategy = self.get_platform_strategy(platform)
        if platform_strategy:
            return platform_strategy.get("best_times", [])
        return []

    def get_best_hooks(self, platform: str) -> List[str]:
        """获取特定平台的最佳Hook关键词"""
        platform_strategy = self.get_platform_strategy(platform)
        if platform_strategy:
            return platform_strategy.get("best_hooks", [])
        return []

    def get_best_ctas(self, platform: str) -> List[str]:
        """获取特定平台的最佳CTA类型"""
        platform_strategy = self.get_platform_strategy(platform)
        if platform_strategy:
            return platform_strategy.get("best_ctas", [])
        return []

    def get_content_types(self, platform: str) -> List[str]:
        """获取特定平台的最佳内容类型"""
        platform_strategy = self.get_platform_strategy(platform)
        if platform_strategy:
            return platform_strategy.get("content_types", [])
        return []

    def get_max_posts_per_day(self, platform: str) -> int:
        """获取特定平台的每日最大发布数"""
        platform_strategy = self.get_platform_strategy(platform)
        if platform_strategy:
            return platform_strategy.get("max_posts_per_day", 3)
        return 3

    def get_global_rules(self) -> Dict[str, Any]:
        """获取全局规则"""
        return self.strategy.get("global_rules", {})

    def get_learning_insights(self) -> List[Dict[str, Any]]:
        """获取学习洞察"""
        return self.strategy.get("learning_insights", [])

    def get_strategy_changes(self) -> List[Dict[str, Any]]:
        """获取策略变更历史"""
        return self.strategy.get("strategy_changes", [])

    def get_strategy_version(self) -> str:
        """获取策略版本"""
        return self.strategy.get("version", "unknown")

    def get_last_updated(self) -> str:
        """获取策略最后更新时间"""
        return self.strategy.get("last_updated", "unknown")

    def generate_content_guidance(self, platform: str, content_type: str = "guide") -> Dict[str, Any]:
        """生成内容创作指导"""
        platform = platform.lower()
        guidance = {
            "platform": platform,
            "content_type": content_type,
            "recommended_times": self.get_best_times(platform),
            "recommended_hooks": self.get_best_hooks(platform),
            "recommended_ctas": self.get_best_ctas(platform),
            "recommended_content_types": self.get_content_types(platform),
            "max_posts_today": self.get_max_posts_per_day(platform),
            "global_rules": self.get_global_rules(),
            "learning_insights": self.get_learning_insights()[:3],
            "strategy_version": self.get_strategy_version(),
            "generated_at": datetime.now().isoformat()
        }
        return guidance

    def print_strategy_summary(self):
        """打印策略摘要"""
        print("\n" + "=" * 60)
        print("  Social Publish Strategy Summary")
        print("=" * 60)
        print(f"\n  版本: {self.get_strategy_version()}")
        print(f"  最后更新: {self.get_last_updated()}")
        print(f"  策略变更数: {len(self.get_strategy_changes())}")
        print(f"  学习洞察数: {len(self.get_learning_insights())}")

        print("\n  平台策略:")
        for platform, strategy in self.strategy.get("platforms", {}).items():
            print(f"\n    📱 {platform}:")
            print(f"       最佳时间: {', '.join(strategy.get('best_times', []))}")
            print(f"       最佳Hook: {', '.join(strategy.get('best_hooks', [])[:3])}")
            print(f"       最佳CTA: {', '.join(strategy.get('best_ctas', [])[:3])}")
            print(f"       内容类型: {', '.join(strategy.get('content_types', [])[:3])}")
            print(f"       每日上限: {strategy.get('max_posts_per_day', 3)}条")

        print("\n" + "=" * 60)


def main():
    """主函数 - 测试策略加载器"""
    import argparse

    parser = argparse.ArgumentParser(description="Social Strategy Loader")
    parser.add_argument("--summary", action="store_true", help="打印策略摘要")
    parser.add_argument("--platform", type=str, default="", help="获取特定平台策略")
    parser.add_argument("--guidance", type=str, default="", help="生成内容创作指导")

    args = parser.parse_args()

    loader = SocialStrategyLoader()

    if args.summary:
        loader.print_strategy_summary()
    elif args.platform:
        platform_strategy = loader.get_platform_strategy(args.platform)
        if platform_strategy:
            print(json.dumps(platform_strategy, ensure_ascii=False, indent=2))
        else:
            print(f"未找到平台 {args.platform} 的策略")
    elif args.guidance:
        guidance = loader.generate_content_guidance(args.guidance)
        print(json.dumps(guidance, ensure_ascii=False, indent=2))
    else:
        # 默认打印摘要
        loader.print_strategy_summary()


if __name__ == "__main__":
    main()
