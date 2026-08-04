#!/usr/bin/env python3
"""
affiliate_link_builder.py - 全站联盟链接批量布局脚本
功能：遍历所有文章，按内容主题自动匹配插入对应联盟推荐区块
版本：v1.0
"""

import os
import sys
import re
import json
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

SCRIPT_DIR = Path(__file__).parent.resolve()
BLOG_ROOT = SCRIPT_DIR.parent

CONTENT_DIR = BLOG_ROOT / "content"
POSTS_DIR = CONTENT_DIR / "posts"
REPORTS_DIR = BLOG_ROOT / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

AFFILIATE_CONFIG = {
    "hotel": {
        "keywords": ["hotel", "accommodation", "stay", "resort", "hostel", "guesthouse"],
        "template": """\n\n{{< affiliate-hotel >}}""",
        "url": "https://www.booking.com/index.html?aid=730795"
    },
    "flight": {
        "keywords": ["flight", "airline", "plane", "fly", "ticket", "airport", "transfer"],
        "template": """\n\n{{< affiliate-flight >}}""",
        "url": "https://trip.tpo.li/trains?marker=730795"
    },
    "insurance": {
        "keywords": ["insurance", "travel insurance", "safety", "medical", "health"],
        "template": """\n\n{{< affiliate-insurance >}}""",
        "url": "https://safetywing.com/ambassador/refer/26548976"
    },
    "esim": {
        "keywords": ["esim", "sim card", "internet", "data", "wifi", "mobile"],
        "template": """\n\n{{< affiliate-esim >}}""",
        "url": "https://www.airalo.com/promo/38j3e4"
    },
    "tour": {
        "keywords": ["tour", "day trip", "excursion", "activity", "attraction", "sightseeing"],
        "template": """\n\n{{< affiliate-tour >}}""",
        "url": "https://klook.tpo.li/vrPkmS2v"
    }
}

class AffiliateLinkBuilder:

    def __init__(self):
        self.stats = {
            "total_files": 0,
            "modified_files": 0,
            "no_change_files": 0,
            "error_files": [],
            "category_stats": {},
            "coverage_rate": 0
        }
        for cat in AFFILIATE_CONFIG.keys():
            self.stats["category_stats"][cat] = {"matched": 0, "updated": 0}

    def _detect_category(self, content: str) -> list:
        categories = []
        content_lower = content.lower()
        
        for cat, config in AFFILIATE_CONFIG.items():
            for keyword in config["keywords"]:
                if keyword.lower() in content_lower:
                    categories.append(cat)
                    break
        
        return categories

    def _has_affiliate_block(self, content: str) -> bool:
        for cat, config in AFFILIATE_CONFIG.items():
            if config["template"].strip() in content:
                return True
        return False

    def _process_file(self, file_path: Path) -> dict:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            categories = self._detect_category(content)
            has_block = self._has_affiliate_block(content)
            
            if not categories:
                return {"status": "no_match", "categories": [], "updated": False}
            
            if has_block:
                return {"status": "already_has_block", "categories": categories, "updated": False}
            
            for cat in categories:
                content += AFFILIATE_CONFIG[cat]["template"]
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            return {"status": "updated", "categories": categories, "updated": True}
            
        except Exception as e:
            print(f"   ⚠️ 处理失败 {file_path}: {e}")
            self.stats["error_files"].append(str(file_path))
            return {"status": "error", "categories": [], "updated": False}

    def process_all_posts(self):
        print("🔍 开始处理文章联盟链接...")
        
        md_files = list(POSTS_DIR.rglob("*.md"))
        self.stats["total_files"] = len(md_files)
        
        print(f"\n📋 发现 {len(md_files)} 篇文章")
        
        for md_file in md_files:
            print(f"   - 处理: {md_file.name}")
            
            result = self._process_file(md_file)
            
            if result["status"] == "updated":
                self.stats["modified_files"] += 1
                for cat in result["categories"]:
                    self.stats["category_stats"][cat]["updated"] += 1
                print(f"     ✅ 添加联盟区块: {', '.join(result['categories'])}")
            elif result["status"] == "already_has_block":
                self.stats["no_change_files"] += 1
                for cat in result["categories"]:
                    self.stats["category_stats"][cat]["matched"] += 1
                print(f"     - 已包含联盟区块")
            elif result["status"] == "no_match":
                self.stats["no_change_files"] += 1
                print(f"     - 无匹配主题")
            else:
                print(f"     ❌ 处理失败")

    def _calculate_coverage(self):
        if self.stats["total_files"] > 0:
            covered = self.stats["modified_files"] + (self.stats["no_change_files"] - len([f for f in self.stats["error_files"]]))
            self.stats["coverage_rate"] = round((covered / self.stats["total_files"]) * 100, 1)

    def print_report(self):
        self._calculate_coverage()
        
        print("\n" + "=" * 60)
        print("  联盟链接布局统计报告")
        print("=" * 60)
        print(f"\n📊 处理统计:")
        print(f"   - 总文章数: {self.stats['total_files']}")
        print(f"   - 新增联盟区块: {self.stats['modified_files']}")
        print(f"   - 已包含联盟区块: {self.stats['no_change_files']}")
        print(f"   - 覆盖率: {self.stats['coverage_rate']}%")
        
        print(f"\n📁 分类统计:")
        for cat, stats in self.stats["category_stats"].items():
            total = stats["matched"] + stats["updated"]
            print(f"   - {cat.capitalize()}: {total} 篇文章匹配")
        
        if self.stats["error_files"]:
            print(f"\n❌ 处理失败文件 ({len(self.stats['error_files'])} 个):")
            for ef in self.stats["error_files"]:
                print(f"   - {ef}")
        
        report_data = {
            "timestamp": str(datetime.now()),
            "stats": self.stats,
            "categories": AFFILIATE_CONFIG.keys()
        }
        
        try:
            report_file = REPORTS_DIR / "affiliate_coverage_report.json"
            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            print(f"\n📋 报告已保存: {report_file}")
        except:
            pass

def main():
    print("=" * 60)
    print("  ChinaBound Travel - 联盟链接批量布局")
    print("=" * 60)
    
    builder = AffiliateLinkBuilder()
    builder.process_all_posts()
    builder.print_report()

if __name__ == "__main__":
    from datetime import datetime
    main()
