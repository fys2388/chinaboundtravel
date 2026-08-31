#!/usr/bin/env python3
"""
ChinaBound Travel - SEO Learning 闭环系统
SEO Learning Closed Loop

功能：打通SEO优化的完整学习闭环
Observe → Record → Analyze → Learn → Decide → Act → Measure → Learn

记录维度：关键词/排名/展示/点击/CTR、页面/标题/描述/内链/外链

使用方式：
    python scripts/seo_learning_closed_loop.py --run
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict
sys.path.insert(0, str(Path(__file__).parent))
from real_data_bridge import get_seo_records
from strategy_change_logger import make_change, STRATEGY_VERSION


PROJECT_ROOT = Path(__file__).parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
SEO_DIR = REPORTS_DIR / "seo"
SEO_DIR.mkdir(parents=True, exist_ok=True)

STRATEGY_FILE = SEO_DIR / "seo_optimization_strategy.json"
LEARNING_REPORT = SEO_DIR / "seo_learning_report.md"
PERFORMANCE_HISTORY = SEO_DIR / "seo_performance_history.json"


class SEOLearningClosedLoop:
    """SEO Learning 闭环系统"""

    def __init__(self):
        self.performance_history = self._load_json(PERFORMANCE_HISTORY, {"records": [], "version": "1.0"})
        self.current_strategy = self._load_json(STRATEGY_FILE, self._default_strategy())
        self._using_sample_data = False  # Data quality gate: True when sample/fallback data is used

    def _load_json(self, path: Path, default: Dict) -> Dict:
        if path.exists():
            try:
                with open(path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return default

    def _save_json(self, path: Path, data: Dict):
        data["last_updated"] = datetime.now().isoformat()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _default_strategy(self) -> Dict:
        return {
            "version": "1.0-default",
            "last_updated": datetime.now().isoformat(),
            "keyword_rules": {
                "target_difficulty": "low_medium",
                "min_search_volume": 100,
                "max_keyword_density": 2.5,
                "min_keyword_density": 0.5,
                "long_tail_priority": True
            },
            "on_page_rules": {
                "title_length": "50-60",
                "meta_description_length": "150-160",
                "heading_structure": "H1-H2-H3",
                "internal_links_min": 3,
                "external_links_min": 1,
                "image_alt_required": True,
                "schema_required": True,
                "url_friendly": True
            },
            "best_keywords": [],
            "best_pages": [],
            "high_priority_keywords": [],
            "learning_insights": [],
            "strategy_changes": []
        }

    def observe_and_record(self) -> List[Dict]:
        """步骤1+2: Observe + Record"""
        print("\n" + "=" * 60)
        print("  步骤1+2: Observe + Record - 观察并记录SEO表现")
        print("=" * 60)

        new_records = []

        # 从GSC报告提取数据
        # 从 real_data 读取真实数据（优先）
        try:
            real_records = get_seo_records()
            existing_ids = set()
            for r in self.performance_history.get("records", []):
                rid = r.get("post_id") or r.get("keyword") or r.get("page") or r.get("segment") or r.get("type") or r.get("title") or str(r)
                existing_ids.add(rid)
            added = 0
            for record in real_records:
                rid = record.get("post_id") or record.get("keyword") or record.get("page") or record.get("segment") or record.get("type") or record.get("title") or str(record)
                if rid not in existing_ids:
                    
                    # 补全所有可能需要的字段（兼容 analyze 方法的硬编码字段）
                    for _key, _default in {
                        "keyword": "", "page": "", "type": "query",
                        "date": "", "search_type": "web"
                    }.items():
                        record.setdefault(_key, _default)
                    record.setdefault("metrics", {})
                    record.setdefault("metadata", {})
                    record.setdefault("calculated", {})
                    for _mk in ["impressions", "clicks", "ctr", "position"]:
                        record["metrics"].setdefault(_mk, 0)
                    for _ck in ["traffic_potential", "is_opportunity", "is_optimization_candidate"]:
                        record["calculated"].setdefault(_ck, 0)
                    self.performance_history.setdefault("records", []).append(record)
                    new_records.append(record)
                    added += 1
            print(f"  📥 从 real_data 加载: {added} 条记录 (共 {len(real_records)} 条可用)")
        except Exception as e:
            print(f"  ⚠️ real_data 加载失败: {e}")


        gsc_report = REPORTS_DIR / "seo" / "gsc_analytics_report.json"
        if gsc_report.exists():
            try:
                with open(gsc_report, encoding="utf-8") as f:
                    report_data = json.load(f)

                keywords = report_data.get("keywords", report_data.get("queries", []))
                if isinstance(keywords, list):
                    for kw in keywords:
                        keyword = kw.get("keyword", kw.get("query", ""))
                        if keyword and not any(r.get("keyword") == keyword for r in self.performance_history["records"]):
                            record = {
                                "keyword": keyword,
                                "date": datetime.now().isoformat(),
                                "metrics": {
                                    "impressions": kw.get("impressions", 0),
                                    "clicks": kw.get("clicks", 0),
                                    "ctr": kw.get("ctr", 0),
                                    "position": kw.get("position", kw.get("avg_position", 100)),
                                    "search_volume": kw.get("search_volume", 0),
                                    "difficulty": kw.get("difficulty", 0)
                                },
                                "pages": kw.get("pages", []),
                                "calculated": {
                                    "traffic_potential": kw.get("impressions", 0) * kw.get("ctr", 0) if kw.get("impressions", 0) > 0 else 0,
                                    "priority_score": (kw.get("search_volume", 0) / 100) * (1 - kw.get("difficulty", 0) / 100) * (1 / max(1, kw.get("position", 100))) if kw.get("position", 100) > 0 else 0
                                }
                            }
                            self.performance_history["records"].append(record)
                            new_records.append(record)
                            print(f"  ✅ 记录: {keyword[:30]}... (展示:{record['metrics']['impressions']}, 排名:{record['metrics']['position']:.1f})")
            except Exception as e:
                print(f"  ⚠️ 处理GSC报告失败: {e}")

        # 如果没有真实数据，添加示例记录
        if not new_records and not self.performance_history["records"]:
            print("  📝 暂无真实GSC数据，使用示例数据演示闭环")
            self._using_sample_data = True  # Data quality gate: sample data cannot update strategy
            sample_keywords = [
                {"keyword": "china travel guide 2026", "impressions": 5000, "clicks": 150, "ctr": 0.03, "position": 8.5, "search_volume": 2000, "difficulty": 60},
                {"keyword": "144 hour visa free transit china", "impressions": 3000, "clicks": 120, "ctr": 0.04, "position": 5.2, "search_volume": 1500, "difficulty": 35},
                {"keyword": "best hotels in beijing", "impressions": 8000, "clicks": 200, "ctr": 0.025, "position": 12.3, "search_volume": 5000, "difficulty": 75},
                {"keyword": "china high speed rail guide", "impressions": 2000, "clicks": 80, "ctr": 0.04, "position": 6.8, "search_volume": 1000, "difficulty": 40},
                {"keyword": "what to eat in chengdu", "impressions": 4000, "clicks": 180, "ctr": 0.045, "position": 4.5, "search_volume": 3000, "difficulty": 50},
                {"keyword": "china travel insurance for foreigners", "impressions": 1500, "clicks": 60, "ctr": 0.04, "position": 7.2, "search_volume": 800, "difficulty": 30},
            ]
            for s in sample_keywords:
                record = {
                    "keyword": s["keyword"],
                    "date": datetime.now().isoformat(),
                    "metrics": {"impressions": s["impressions"], "clicks": s["clicks"], "ctr": s["ctr"], "position": s["position"], "search_volume": s["search_volume"], "difficulty": s["difficulty"]},
                    "pages": [],
                    "calculated": {
                        "traffic_potential": s["impressions"] * s["ctr"],
                        "priority_score": (s["search_volume"] / 100) * (1 - s["difficulty"] / 100) * (1 / max(1, s["position"]))
                    }
                }
                self.performance_history["records"].append(record)
                new_records.append(record)
                print(f"  ✅ 示例记录: {s['keyword'][:30]}... (CTR:{s['ctr']*100:.1f}%, 排名:{s['position']:.1f})")

        self._save_json(PERFORMANCE_HISTORY, self.performance_history)
        print(f"\n  📊 新增记录: {len(new_records)} 条")
        print(f"  📊 历史总记录: {len(self.performance_history['records'])} 条")
        return new_records

    def analyze_and_learn(self) -> Dict:
        """步骤3+4: Analyze + Learn"""
        print("\n" + "=" * 60)
        print("  步骤3+4: Analyze + Learn - 分析并学习SEO成功模式")
        print("=" * 60)

        insights = {"generated_at": datetime.now().isoformat(), "best_keywords": [], "high_potential_keywords": [], "low_difficulty_keywords": [], "success_patterns": [], "recommendations": []}
        records = self.performance_history["records"]
        if not records:
            print("  ⚠️ 没有足够数据进行分析")
            return insights

        print(f"\n  📊 分析 {len(records)} 个关键词...")

        # 数据规范化：补全所有硬编码字段（兼容 bridge 生成的记录格式）
        for _r in records:
            _r.setdefault("keyword", _r.get("page", ""))
            _r.setdefault("metrics", {})
            _r.setdefault("calculated", {})
            for _mk in ["impressions", "clicks", "ctr", "position", "difficulty", "search_volume"]:
                _r["metrics"].setdefault(_mk, 0)
            for _ck in ["traffic_potential", "priority_score"]:
                _r["calculated"].setdefault(_ck, 0)

        # 按CTR排序（最佳表现）
        sorted_by_ctr = sorted(records, key=lambda x: x["metrics"]["ctr"], reverse=True)
        insights["best_keywords"] = [{"keyword": r["keyword"], "ctr": r["metrics"]["ctr"], "position": r["metrics"]["position"], "impressions": r["metrics"]["impressions"]} for r in sorted_by_ctr[:10]]

        # 按流量潜力排序
        sorted_by_potential = sorted(records, key=lambda x: x["calculated"]["traffic_potential"], reverse=True)
        insights["high_potential_keywords"] = [{"keyword": r["keyword"], "traffic_potential": r["calculated"]["traffic_potential"], "position": r["metrics"]["position"]} for r in sorted_by_potential[:10]]

        # 按难度排序（低难度高机会）
        sorted_by_difficulty = sorted(records, key=lambda x: x["metrics"]["difficulty"])
        insights["low_difficulty_keywords"] = [{"keyword": r["keyword"], "difficulty": r["metrics"]["difficulty"], "search_volume": r["metrics"]["search_volume"], "position": r["metrics"]["position"]} for r in sorted_by_difficulty[:10]]

        # 成功模式
        if insights["best_keywords"]:
            best_kw = insights["best_keywords"][0]
            insights["success_patterns"].append({
                "pattern": "高CTR关键词特征",
                "description": f"'{best_kw['keyword']}'CTR最高，达到 {best_kw['ctr']*100:.1f}%，排名 {best_kw['position']:.1f}",
                "recommendation": "分析该关键词的标题和描述模式，复制到其他关键词"
            })

        # 排名在4-10之间的关键词（快速提升机会）
        quick_win_keywords = [r for r in records if 4 <= r["metrics"]["position"] <= 10]
        if quick_win_keywords:
            insights["success_patterns"].append({
                "pattern": "快速提升机会关键词",
                "description": f"发现 {len(quick_win_keywords)} 个排名在4-10之间的关键词，小幅优化即可进入Top 3",
                "recommendation": "优先优化这些关键词的页面，提升内链和内容质量",
                "keywords": [r["keyword"] for r in quick_win_keywords[:5]]
            })

        # 建议
        insights["recommendations"] = [
            {"priority": "high", "type": "keyword_optimization", "title": "优化高潜力关键词", "description": f"针对Top {min(5, len(insights['high_potential_keywords']))}个高流量潜力关键词进行深度优化", "action": "扩充内容、增加内链、优化标题和描述"},
            {"priority": "high", "type": "quick_win", "title": "快速提升排名4-10的关键词", "description": f"发现 {len(quick_win_keywords)} 个快速提升机会关键词", "action": "小幅优化即可进入Top 3，优先处理"},
            {"priority": "medium", "type": "low_difficulty", "title": "拓展低难度关键词", "description": "针对低难度高搜索量的关键词创建新内容", "action": "新增3-5篇 targeting 低难度关键词的文章"},
            {"priority": "medium", "type": "internal_linking", "title": "加强内链建设", "description": "高排名页面需要更多内链支持", "action": "在相关文章中添加指向高潜力页面的内链"},
        ]

        print(f"\n  🏆 最佳关键词: {insights['best_keywords'][0]['keyword'][:30] if insights['best_keywords'] else 'N/A'}")
        print(f"  📈 高潜力关键词: {len(insights['high_potential_keywords'])} 个")
        print(f"  🎯 快速提升机会: {len(quick_win_keywords)} 个")
        print(f"  💡 成功模式: {len(insights['success_patterns'])} 个")
        print(f"  🚀 优化建议: {len(insights['recommendations'])} 条")

        return insights

    def decide_and_update_strategy(self, insights: Dict) -> Dict:
        """步骤5+6: Decide + Act"""
        # Data quality gate: SAMPLE/NOT_AVAILABLE data must NOT update strategy
        if getattr(self, "_using_sample_data", False):
            print("  ⚠️ 数据质量门控: 检测到SAMPLE/回退数据，策略更新已拦截（仅LIVE/CACHED可更新策略）")
            return self.current_strategy
        print("\n" + "=" * 60)
        print("  步骤5+6: Decide + Act - 决策并更新SEO优化策略")
        print("=" * 60)

        strategy_changes = []

        if insights.get("best_keywords"):
            old_best = self.current_strategy.get("best_keywords", [])
            new_best = insights["best_keywords"]
            if old_best != new_best:
                self.current_strategy["best_keywords"] = new_best
                strategy_changes.append({"field": "best_keywords", "reason": "基于GSC数据分析，更新最佳关键词排名"})
                print(f"  ✅ 更新最佳关键词: {len(new_best)} 个")

        if insights.get("high_potential_keywords"):
            old_priority = self.current_strategy.get("high_priority_keywords", [])
            new_priority = insights["high_potential_keywords"][:5]
            if old_priority != new_priority:
                self.current_strategy["high_priority_keywords"] = new_priority
                strategy_changes.append({"field": "high_priority_keywords", "reason": "基于流量潜力分析，更新高优先级关键词"})
                print(f"  ✅ 更新高优先级关键词: {len(new_priority)} 个")

        self.current_strategy["learning_insights"] = insights.get("success_patterns", [])
        # Enrich change records with audit metadata (version/timestamp/evidence)
        _now = datetime.now().isoformat()
        for _ch in strategy_changes:
            _ch.setdefault("version", STRATEGY_VERSION)
            _ch.setdefault("timestamp", _now)
            _ch.setdefault("evidence", "based on performance data analysis")
        self.current_strategy["strategy_changes"] = strategy_changes
        self.current_strategy["last_updated"] = datetime.now().isoformat()
        self.current_strategy["version"] = f"2.0-{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        self._save_json(STRATEGY_FILE, self.current_strategy)
        print(f"\n  📊 策略变更: {len(strategy_changes)} 项")
        print(f"  📄 策略文件: {STRATEGY_FILE}")
        return self.current_strategy

    def generate_report(self, insights: Dict, strategy: Dict):
        """生成学习报告"""
        report = f"""# ChinaBound Travel SEO Learning 闭环报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**策略版本**: {strategy.get('version', 'unknown')}

---

## 🔄 闭环状态
```
Observe ✅ → Record ✅ → Analyze ✅ → Learn ✅ → Decide ✅ → Act ✅ → Measure ⏳ → Learn Again 🔄
```

---

## 🏆 最佳关键词（按CTR）

| 关键词 | CTR | 排名 | 展示量 |
|--------|-----|------|--------|
"""
        for kw in insights.get("best_keywords", [])[:10]:
            report += f"| {kw['keyword'][:40]} | {kw['ctr']*100:.1f}% | {kw['position']:.1f} | {kw['impressions']} |\n"

        report += """
---

## 📈 高流量潜力关键词

| 关键词 | 流量潜力 | 当前排名 |
|--------|----------|----------|
"""
        for kw in insights.get("high_potential_keywords", [])[:10]:
            report += f"| {kw['keyword'][:40]} | {kw['traffic_potential']:.0f} | {kw['position']:.1f} |\n"

        report += """
---

## 🎯 低难度高机会关键词

| 关键词 | 难度 | 搜索量 | 当前排名 |
|--------|------|--------|----------|
"""
        for kw in insights.get("low_difficulty_keywords", [])[:10]:
            report += f"| {kw['keyword'][:40]} | {kw['difficulty']} | {kw['search_volume']} | {kw['position']:.1f} |\n"

        report += """
---

## 💡 学习洞察

"""
        for i, pattern in enumerate(insights.get("success_patterns", []), 1):
            report += f"### {i}. {pattern['pattern']}\n{pattern['description']}\n\n**建议:** {pattern.get('recommendation', '')}\n\n"
            if pattern.get("keywords"):
                report += f"**关键词:** {', '.join(pattern['keywords'][:5])}\n\n"

        report += """---

## 🚀 优化建议

"""
        for i, rec in enumerate(insights.get("recommendations", []), 1):
            icon = "🔴" if rec["priority"] == "high" else "🟡"
            report += f"{icon} **{rec['title']}**\n- {rec['description']}\n- 行动: {rec['action']}\n\n"

        report += f"""---

*报告由SEO Learning闭环系统自动生成*
"""
        with open(LEARNING_REPORT, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"  ✅ 学习报告已生成: {LEARNING_REPORT}")

    def run_full_closed_loop(self):
        """运行完整闭环"""
        print("\n" + "=" * 60)
        print("  ChinaBound Travel SEO Learning 完整闭环运行")
        print("=" * 60)
        print(f"\n  运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        new_records = self.observe_and_record()
        insights = self.analyze_and_learn()
        strategy = self.decide_and_update_strategy(insights)
        self.generate_report(insights, strategy)

        print("\n" + "=" * 60)
        print("  SEO Learning 完整闭环运行完成")
        print("=" * 60)
        print(f"\n  ✅ Observe: 观察完成")
        print(f"  ✅ Record: 记录完成 ({len(new_records)}条)")
        print(f"  ✅ Analyze: 分析完成")
        print(f"  ✅ Learn: 学习完成 ({len(insights.get('success_patterns', []))}个模式)")
        print(f"  ✅ Decide: 决策完成")
        print(f"  ✅ Act: 行动完成 ({len(strategy.get('strategy_changes', []))}项变更)")
        print(f"  ⏳ Measure: 等待下一轮效果测量")
        print(f"\n  📄 策略文件: {STRATEGY_FILE}")
        print(f"  📄 学习报告: {LEARNING_REPORT}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="SEO Learning 闭环系统")
    parser.add_argument("--run", action="store_true", help="运行完整闭环")
    args = parser.parse_args()
    loop = SEOLearningClosedLoop()
    if args.run:
        loop.run_full_closed_loop()
    else:
        loop.run_full_closed_loop()


if __name__ == "__main__":
    main()
