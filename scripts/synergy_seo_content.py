#!/usr/bin/env python3
"""
ChinaBound Travel - SYN-002 SEO-内容协同机制
SEO-Content Synergy Mechanism

功能：实现高潜力低难度关键词自动触发内容生成
- 从SEO Learning策略读取高潜力低难度关键词
- 从Content Learning策略读取最佳内容类型和结构
- 生成内容生成计划（关键词→文章主题→内容大纲）
- 输出可供Content Agent消费的内容生成队列

协同流程：
SEO Agent识别高潜力低难度关键词 → 匹配最佳内容类型/结构 → 生成内容生成计划 → Content Agent消费生成文章 → 效果回流 → 更新双方策略

使用方式：
    python scripts/synergy_seo_content.py --run
    python scripts/synergy_seo_content.py --generate-plan
    python scripts/synergy_seo_content.py --show-queue
"""

import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
SEO_DIR = REPORTS_DIR / "seo"
CONTENT_DIR = REPORTS_DIR / "content"
SYNERGY_DIR = REPORTS_DIR / "synergy"
SYNERGY_DIR.mkdir(parents=True, exist_ok=True)

# 输出文件
CONTENT_GENERATION_QUEUE = SYNERGY_DIR / "content_generation_queue.json"
SYNERGY_REPORT_FILE = SYNERGY_DIR / "syn002_seo_content_report.md"
SYNERGY_HISTORY_FILE = SYNERGY_DIR / "syn002_history.json"


class SEOContentSynergy:
    """SEO-内容协同机制"""

    def __init__(self):
        self.seo_strategy = self._load_seo_strategy()
        self.content_strategy = self._load_content_strategy()
        self.content_queue = self._load_content_queue()
        self.history = self._load_history()

    def _load_seo_strategy(self) -> Dict:
        """加载SEO优化策略"""
        strategy_file = SEO_DIR / "seo_optimization_strategy.json"
        if strategy_file.exists():
            try:
                with open(strategy_file, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"  ⚠️ 加载SEO策略失败: {e}")
        return {"high_potential_keywords": [], "best_keywords": [], "learning_insights": []}

    def _load_content_strategy(self) -> Dict:
        """加载内容优化策略"""
        strategy_file = CONTENT_DIR / "content_optimization_strategy.json"
        if strategy_file.exists():
            try:
                with open(strategy_file, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"  ⚠️ 加载内容策略失败: {e}")
        return {"best_content_types": [], "content_templates": [], "learning_insights": []}

    def _load_content_queue(self) -> Dict:
        """加载内容生成队列"""
        if CONTENT_GENERATION_QUEUE.exists():
            try:
                with open(CONTENT_GENERATION_QUEUE, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "synergy_id": "SYN-002",
            "high_potential_keywords": [],
            "best_content_types": [],
            "content_generation_plan": [],
            "stats": {
                "total_keywords_identified": 0,
                "total_articles_planned": 0,
                "expected_traffic_boost": 0,
                "expected_keyword_coverage": 0
            }
        }

    def _save_content_queue(self):
        """保存内容生成队列"""
        self.content_queue["last_updated"] = datetime.now().isoformat()
        with open(CONTENT_GENERATION_QUEUE, "w", encoding="utf-8") as f:
            json.dump(self.content_queue, f, ensure_ascii=False, indent=2)

    def _load_history(self) -> Dict:
        """加载协同历史"""
        if SYNERGY_HISTORY_FILE.exists():
            try:
                with open(SYNERGY_HISTORY_FILE, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"runs": [], "version": "1.0"}

    def _save_history(self):
        """保存协同历史"""
        with open(SYNERGY_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)

    def identify_high_potential_keywords(self) -> List[Dict]:
        """识别高潜力低难度关键词"""
        print("\n" + "=" * 60)
        print("  步骤1: 识别高潜力低难度关键词")
        print("=" * 60)

        high_potential = []

        # 从SEO策略获取高潜力关键词
        strategy_keywords = self.seo_strategy.get("high_potential_keywords", [])
        if strategy_keywords:
            print(f"  📋 从SEO策略获取 {len(strategy_keywords)} 个高潜力关键词")
            high_potential.extend(strategy_keywords)

        # 从SEO关键词表现获取
        keyword_file = SEO_DIR / "keyword_performance_history.json"
        if keyword_file.exists():
            try:
                with open(keyword_file, encoding="utf-8") as f:
                    kw_data = json.load(f)
                records = kw_data.get("records", [])
                # 计算潜力分 = 搜索量 * (1 - 难度) * 点击率潜力
                for kw in records:
                    keyword = kw.get("keyword", "")
                    search_volume = kw["metrics"].get("search_volume", 0)
                    difficulty = kw["metrics"].get("difficulty", 0.5)
                    current_position = kw["metrics"].get("position", 50)
                    potential_score = search_volume * (1 - difficulty) * (1.0 / max(current_position, 1))
                    if keyword and potential_score > 0:
                        high_potential.append({
                            "keyword": keyword,
                            "search_volume": search_volume,
                            "difficulty": difficulty,
                            "current_position": current_position,
                            "potential_score": potential_score,
                            "source": "keyword_performance",
                            "priority": "high" if potential_score > 10 else "medium"
                        })
                # 按潜力分排序，取Top 10
                high_potential.sort(key=lambda x: x.get("potential_score", 0), reverse=True)
                high_potential = high_potential[:10]
                print(f"  📊 从关键词表现获取 Top 10 高潜力关键词")
            except Exception as e:
                print(f"  ⚠️ 读取关键词表现失败: {e}")

        # 如果没有真实数据，使用示例数据
        if not high_potential:
            print("  📝 暂无真实高潜力关键词，使用示例数据演示协同机制")
            sample_keywords = [
                {"keyword": "china visa free transit 144 hours", "search_volume": 1200, "difficulty": 0.25, "current_position": 15, "potential_score": 60.0, "source": "sample", "priority": "high"},
                {"keyword": "china high speed rail guide", "search_volume": 900, "difficulty": 0.30, "current_position": 20, "potential_score": 31.5, "source": "sample", "priority": "high"},
                {"keyword": "chengdu hotpot restaurants", "search_volume": 700, "difficulty": 0.35, "current_position": 25, "potential_score": 18.2, "source": "sample", "priority": "high"},
                {"keyword": "zhangjiajie photography spots", "search_volume": 600, "difficulty": 0.40, "current_position": 30, "potential_score": 12.0, "source": "sample", "priority": "medium"},
                {"keyword": "china payment for foreigners", "search_volume": 800, "difficulty": 0.20, "current_position": 12, "potential_score": 53.3, "source": "sample", "priority": "high"},
                {"keyword": "china travel insurance", "search_volume": 500, "difficulty": 0.45, "current_position": 35, "potential_score": 7.9, "source": "sample", "priority": "medium"},
                {"keyword": "china esim for tourists", "search_volume": 450, "difficulty": 0.30, "current_position": 18, "potential_score": 17.5, "source": "sample", "priority": "medium"},
                {"keyword": "beijing forbidden city guide", "search_volume": 1000, "difficulty": 0.50, "current_position": 40, "potential_score": 12.5, "source": "sample", "priority": "medium"},
            ]
            high_potential = sample_keywords

        print(f"\n  ✅ 识别高潜力关键词: {len(high_potential)} 个")
        for i, kw in enumerate(high_potential[:5], 1):
            print(f"    {i}. {kw['keyword'][:50]}... (搜索量:{kw.get('search_volume', 0)}, 难度:{kw.get('difficulty', 0)*100:.0f}%, 潜力分:{kw.get('potential_score', 0):.1f})")

        return high_potential

    def get_best_content_practices(self) -> Dict:
        """获取最佳内容实践"""
        print("\n" + "=" * 60)
        print("  步骤2: 获取最佳内容实践")
        print("=" * 60)

        best_practices = {
            "best_content_types": [],
            "content_templates": {},
            "recommended_length": 2000
        }

        # 从内容策略获取最佳内容类型
        best_types = self.content_strategy.get("best_content_types", [])
        if best_types:
            best_practices["best_content_types"] = best_types
            print(f"  📋 从内容策略获取 {len(best_types)} 个最佳内容类型")
            for content_type in best_types[:3]:
                print(f"    - {content_type.get('type', '')}: 平均停留 {content_type.get('avg_duration', 0)}秒, 转化率 {content_type.get('conversion_rate', 0)*100:.1f}%")

        # 如果没有真实数据，使用默认最佳实践
        if not best_practices["best_content_types"]:
            print("  📝 使用默认最佳内容实践")
            best_practices["best_content_types"] = [
                {"type": "how_to_guide", "avg_duration": 180, "conversion_rate": 0.035, "description": "操作指南，步骤清晰，实用性强"},
                {"type": "complete_guide", "avg_duration": 240, "conversion_rate": 0.030, "description": "完整指南，全面覆盖，深度内容"},
                {"type": "comparison", "avg_duration": 150, "conversion_rate": 0.040, "description": "对比分析，帮助决策，高转化"},
                {"type": "listicle", "avg_duration": 120, "conversion_rate": 0.025, "description": "清单式内容，易读，高分享"},
                {"type": "review", "avg_duration": 200, "conversion_rate": 0.045, "description": "评测内容，可信度高，高转化"}
            ]

        # 内容模板
        best_practices["content_templates"] = {
            "how_to_guide": {
                "structure": ["Introduction", "Prerequisites", "Step-by-step guide", "Tips and tricks", "Conclusion", "CTA"],
                "recommended_length": 1500,
                "keyword_density": "1-2%"
            },
            "complete_guide": {
                "structure": ["Introduction", "Overview", "Detailed sections", "FAQ", "Conclusion", "CTA"],
                "recommended_length": 2500,
                "keyword_density": "1-2%"
            },
            "comparison": {
                "structure": ["Introduction", "Comparison criteria", "Detailed comparison", "Recommendation", "Conclusion", "CTA"],
                "recommended_length": 1800,
                "keyword_density": "1-2%"
            }
        }

        return best_practices

    def generate_content_plan(self, high_potential: List[Dict], best_practices: Dict) -> List[Dict]:
        """生成内容生成计划"""
        print("\n" + "=" * 60)
        print("  步骤3: 生成内容生成计划")
        print("=" * 60)

        content_plan = []
        best_types = best_practices.get("best_content_types", [])
        templates = best_practices.get("content_templates", {})

        for i, keyword in enumerate(high_potential):
            keyword_text = keyword.get("keyword", "")
            potential_score = keyword.get("potential_score", 0)

            # 根据关键词类型选择内容类型
            if any(word in keyword_text.lower() for word in ["how", "guide", "setup", "use"]):
                content_type = "how_to_guide"
            elif any(word in keyword_text.lower() for word in ["complete", "ultimate", "everything"]):
                content_type = "complete_guide"
            elif any(word in keyword_text.lower() for word in ["vs", "comparison", "best"]):
                content_type = "comparison"
            else:
                content_type = "complete_guide"  # 默认

            # 获取内容模板
            template = templates.get(content_type, templates.get("complete_guide", {}))

            # 生成文章标题
            title = self._generate_title(keyword_text, content_type)

            # 生成内容大纲
            outline = self._generate_outline(keyword_text, content_type, template)

            plan_item = {
                "plan_id": f"SYN002_{i+1:03d}",
                "keyword": keyword_text,
                "search_volume": keyword.get("search_volume", 0),
                "difficulty": keyword.get("difficulty", 0),
                "potential_score": potential_score,
                "content_type": content_type,
                "title": title,
                "outline": outline,
                "recommended_length": template.get("recommended_length", 2000),
                "keyword_density": template.get("keyword_density", "1-2%"),
                "priority": keyword.get("priority", "medium"),
                "status": "planned",
                "created_at": datetime.now().isoformat(),
                "synergy_id": "SYN-002"
            }
            content_plan.append(plan_item)

        # 按优先级和潜力分排序
        priority_order = {"high": 0, "medium": 1, "low": 2}
        content_plan.sort(key=lambda x: (priority_order.get(x["priority"], 1), -x["potential_score"]))

        print(f"\n  ✅ 生成内容生成计划: {len(content_plan)} 篇")
        for i, item in enumerate(content_plan[:5], 1):
            print(f"    {i}. [{item['content_type']}] {item['title'][:50]}... (关键词:{item['keyword'][:30]}..., 潜力分:{item['potential_score']:.1f})")

        return content_plan

    def _generate_title(self, keyword: str, content_type: str) -> str:
        """生成文章标题"""
        # 简单的标题生成逻辑
        keyword_title = keyword.replace("-", " ").title()
        if content_type == "how_to_guide":
            return f"How to {keyword_title}: Complete Step-by-Step Guide"
        elif content_type == "complete_guide":
            return f"{keyword_title}: The Complete Guide for 2026"
        elif content_type == "comparison":
            return f"{keyword_title}: Detailed Comparison and Recommendation"
        else:
            return f"{keyword_title}: Everything You Need to Know"

    def _generate_outline(self, keyword: str, content_type: str, template: Dict) -> List[str]:
        """生成内容大纲"""
        structure = template.get("structure", ["Introduction", "Main Content", "Conclusion", "CTA"])
        keyword_title = keyword.replace("-", " ").title()

        outline = []
        for section in structure:
            if section == "Introduction":
                outline.append(f"Introduction to {keyword_title}")
            elif section == "Prerequisites":
                outline.append(f"What You Need to Know Before {keyword_title}")
            elif section == "Step-by-step guide":
                outline.append(f"Step-by-Step Guide to {keyword_title}")
            elif section == "Tips and tricks":
                outline.append(f"Expert Tips for {keyword_title}")
            elif section == "Overview":
                outline.append(f"Overview of {keyword_title}")
            elif section == "Detailed sections":
                outline.append(f"Detailed Guide to {keyword_title}")
            elif section == "FAQ":
                outline.append(f"Frequently Asked Questions About {keyword_title}")
            elif section == "Comparison criteria":
                outline.append(f"Comparison Criteria for {keyword_title}")
            elif section == "Detailed comparison":
                outline.append(f"Detailed Comparison of {keyword_title}")
            elif section == "Recommendation":
                outline.append(f"Our Recommendation for {keyword_title}")
            elif section == "Conclusion":
                outline.append(f"Conclusion: {keyword_title}")
            elif section == "CTA":
                outline.append(f"Next Steps and Recommended Resources")
            else:
                outline.append(f"{section}: {keyword_title}")

        return outline

    def update_content_queue(self, high_potential: List[Dict], best_practices: Dict, content_plan: List[Dict]):
        """更新内容生成队列"""
        print("\n" + "=" * 60)
        print("  步骤4: 更新内容生成队列")
        print("=" * 60)

        self.content_queue["high_potential_keywords"] = high_potential
        self.content_queue["best_content_types"] = best_practices.get("best_content_types", [])
        self.content_queue["content_generation_plan"] = content_plan
        self.content_queue["stats"]["total_keywords_identified"] = len(high_potential)
        self.content_queue["stats"]["total_articles_planned"] = len(content_plan)
        self.content_queue["stats"]["expected_traffic_boost"] = sum(kw.get("search_volume", 0) * 0.1 for kw in high_potential)  # 预期10%的搜索量转化
        self.content_queue["stats"]["expected_keyword_coverage"] = len(high_potential)

        self._save_content_queue()

        print(f"  ✅ 高潜力关键词: {len(high_potential)} 个")
        print(f"  ✅ 内容生成计划: {len(content_plan)} 篇")
        print(f"  📊 预期流量提升: {self.content_queue['stats']['expected_traffic_boost']:.0f} 次/月")
        print(f"  📄 队列文件: {CONTENT_GENERATION_QUEUE}")

    def generate_synergy_report(self, high_potential: List[Dict], content_plan: List[Dict]):
        """生成协同报告"""
        print("\n" + "=" * 60)
        print("  步骤5: 生成SYN-002协同报告")
        print("=" * 60)

        report = f"""# SYN-002 SEO-内容协同机制报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**协同ID**: SYN-002
**机制**: 高潜力低难度关键词自动触发内容生成

---

## 📊 协同统计

| 指标 | 数值 |
|------|------|
| 识别高潜力关键词 | {len(high_potential)} 个 |
| 生成内容计划 | {len(content_plan)} 篇 |
| 高优先级计划 | {sum(1 for p in content_plan if p['priority'] == 'high')} 篇 |
| 中优先级计划 | {sum(1 for p in content_plan if p['priority'] == 'medium')} 篇 |
| 预期流量提升 | {self.content_queue['stats']['expected_traffic_boost']:.0f} 次/月 |
| 关键词覆盖 | {self.content_queue['stats']['expected_keyword_coverage']} 个 |

---

## 🔑 高潜力关键词Top 10

| 排名 | 关键词 | 搜索量 | 难度 | 当前排名 | 潜力分 | 优先级 |
|------|--------|--------|------|----------|--------|--------|
"""

        for i, kw in enumerate(high_potential[:10], 1):
            report += f"| {i} | {kw['keyword'][:50]} | {kw.get('search_volume', 0)} | {kw.get('difficulty', 0)*100:.0f}% | {kw.get('current_position', '-')} | {kw.get('potential_score', 0):.1f} | {kw.get('priority', '')} |\n"

        report += f"""
---

## 📝 内容生成计划Top 10

| 排名 | 内容类型 | 文章标题 | 关键词 | 推荐长度 | 优先级 |
|------|---------|---------|--------|----------|--------|
"""

        for i, item in enumerate(content_plan[:10], 1):
            report += f"| {i} | {item['content_type']} | {item['title'][:40]} | {item['keyword'][:30]} | {item['recommended_length']}字 | {item['priority']} |\n"

        report += f"""
---

## 🔄 协同流程

```
SEO Agent识别高潜力低难度关键词
         ↓
匹配Content Agent学习到的最佳内容类型/结构
         ↓
生成内容生成计划（关键词→标题→大纲→长度建议）
         ↓
Content Agent消费计划，自动生成文章
         ↓
文章发布后SEO效果回流到Growth Memory
         ↓
更新SEO和Content双方策略
         ↓
持续优化协同效果
```

---

## 🎯 预期效果

- **关键词覆盖增加**: 新增{len(high_potential)}个高潜力关键词覆盖
- **自然搜索流量提升**: 预期月流量提升{self.content_queue['stats']['expected_traffic_boost']:.0f}次
- **内容质量提升**: 使用学习到的最佳内容类型和结构，提升内容质量
- **协同效应形成**: SEO和内容双向反馈，持续优化双方策略

---

## 📝 实施状态

- ✅ 高潜力关键词识别机制
- ✅ 最佳内容实践加载
- ✅ 内容生成计划生成（标题+大纲+长度建议）
- ✅ 队列文件输出（供Content Agent消费）
- ✅ 协同报告生成
- ⏳ Content Agent消费队列生成文章（待集成）
- ⏳ 效果测量和反馈（待积累数据）

---

*报告由SYN-002 SEO-内容协同机制自动生成*
*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

        with open(SYNERGY_REPORT_FILE, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"  ✅ 协同报告已生成: {SYNERGY_REPORT_FILE}")

    def run_synergy(self) -> Dict:
        """运行完整协同机制"""
        print("\n" + "=" * 60)
        print("  SYN-002 SEO-内容协同机制运行")
        print("=" * 60)
        print(f"\n  运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # 步骤1: 识别高潜力关键词
        high_potential = self.identify_high_potential_keywords()

        # 步骤2: 获取最佳内容实践
        best_practices = self.get_best_content_practices()

        # 步骤3: 生成内容计划
        content_plan = self.generate_content_plan(high_potential, best_practices)

        # 步骤4: 更新内容队列
        self.update_content_queue(high_potential, best_practices, content_plan)

        # 步骤5: 生成协同报告
        self.generate_synergy_report(high_potential, content_plan)

        # 记录历史
        run_record = {
            "run_id": f"SYN002_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.now().isoformat(),
            "high_potential_count": len(high_potential),
            "content_plan_count": len(content_plan),
            "expected_traffic_boost": self.content_queue["stats"]["expected_traffic_boost"],
            "status": "success"
        }
        self.history["runs"].append(run_record)
        self._save_history()

        # 总结
        print("\n" + "=" * 60)
        print("  SYN-002 协同机制运行完成")
        print("=" * 60)
        print(f"\n  ✅ 高潜力关键词识别: {len(high_potential)} 个")
        print(f"  ✅ 内容生成计划: {len(content_plan)} 篇")
        print(f"  ✅ 队列文件输出: {CONTENT_GENERATION_QUEUE}")
        print(f"  ✅ 协同报告生成: {SYNERGY_REPORT_FILE}")
        print(f"\n  📊 预期流量提升: {self.content_queue['stats']['expected_traffic_boost']:.0f} 次/月")
        print(f"  🔑 关键词覆盖: {self.content_queue['stats']['expected_keyword_coverage']} 个")
        print(f"\n  🎯 协同状态: SYN-002机制已建立，等待Content Agent消费队列生成文章")

        return {
            "high_potential_count": len(high_potential),
            "content_plan_count": len(content_plan),
            "queue_file": str(CONTENT_GENERATION_QUEUE),
            "report_file": str(SYNERGY_REPORT_FILE),
            "expected_traffic_boost": self.content_queue["stats"]["expected_traffic_boost"],
            "status": "success"
        }


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="SYN-002 SEO-内容协同机制")
    parser.add_argument("--run", action="store_true", help="运行完整协同机制")
    parser.add_argument("--generate-plan", action="store_true", help="仅生成内容生成计划")
    parser.add_argument("--show-queue", action="store_true", help="显示当前内容生成队列")

    args = parser.parse_args()

    synergy = SEOContentSynergy()

    if args.run:
        synergy.run_synergy()
    elif args.generate_plan:
        high_potential = synergy.identify_high_potential_keywords()
        best_practices = synergy.get_best_content_practices()
        content_plan = synergy.generate_content_plan(high_potential, best_practices)
        synergy.update_content_queue(high_potential, best_practices, content_plan)
    elif args.show_queue:
        queue = synergy.content_queue
        print(f"\n当前内容生成队列:")
        print(f"  高潜力关键词: {len(queue.get('high_potential_keywords', []))} 个")
        print(f"  内容生成计划: {len(queue.get('content_generation_plan', []))} 篇")
        for item in queue.get("content_generation_plan", [])[:5]:
            print(f"    - [{item['content_type']}] {item['title'][:40]}... (优先级:{item['priority']})")
    else:
        synergy.run_synergy()


if __name__ == "__main__":
    main()
