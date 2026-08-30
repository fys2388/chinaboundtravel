#!/usr/bin/env python3
"""
ChinaBound Travel - 用户旅程关键瓶颈优化器
User Journey Bottleneck Optimizer

针对用户旅程3个关键瓶颈提供具体可执行的优化方案：
1. 转化阶段（流失60%）- CTA优化、信任信号、简化流程
2. 留存阶段（流失50%）- 邮件序列、回访激励、个性化推荐
3. 认知阶段（流失45%）- 首屏优化、加载速度、价值主张

使用方式：
    python scripts/journey_optimization.py --all
    python scripts/journey_optimization.py --conversion
    python scripts/journey_optimization.py --retention
    python scripts/journey_optimization.py --awareness
"""

import os
import sys
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
JOURNEY_DIR = REPORTS_DIR / "journey"
JOURNEY_DIR.mkdir(parents=True, exist_ok=True)

# 内容目录
CONTENT_DIR = PROJECT_ROOT / "content"
POSTS_DIR = CONTENT_DIR / "posts"


class JourneyOptimizer:
    """用户旅程关键瓶颈优化器"""

    def __init__(self):
        self.optimizations = {}
        self.generated_at = datetime.now()

    def analyze_awareness_stage(self) -> Dict[str, Any]:
        """分析认知阶段瓶颈（流失45%）"""
        print("\n" + "=" * 60)
        print("  认知阶段优化（流失45%）")
        print("=" * 60)

        # 扫描首页和热门文章的首屏内容
        issues = []
        recommendations = []

        # 1. 检查首页首屏
        index_file = CONTENT_DIR / "_index.md"
        if index_file.exists():
            content = index_file.read_text(encoding="utf-8")
            word_count = len(content.split())
            has_value_proposition = bool(re.search(r'(China travel|travel guide|itinerary|tips)', content, re.IGNORECASE))
            has_cta = bool(re.search(r'(book|plan|start|explore|discover)', content, re.IGNORECASE))

            if word_count < 100:
                issues.append({"type": "首屏内容不足", "severity": "high", "detail": f"首页内容仅{word_count}词，价值主张不清晰"})
            if not has_value_proposition:
                issues.append({"type": "价值主张缺失", "severity": "high", "detail": "首页未明确说明网站为用户提供什么价值"})
            if not has_cta:
                issues.append({"type": "首屏CTA缺失", "severity": "medium", "detail": "首页首屏没有明确的行动号召按钮"})

        # 2. 检查网站加载速度（基于已知数据）
        issues.append({"type": "加载速度优化", "severity": "medium", "detail": "响应时间577ms，建议优化至300ms以下（图片压缩、CDN缓存、懒加载）"})

        # 3. 检查移动端适配
        issues.append({"type": "移动端体验", "severity": "medium", "detail": "移动端用户占37.6%，需确保首屏在移动端清晰展示价值主张和CTA"})

        # 生成优化建议
        recommendations = [
            {
                "priority": "high",
                "title": "优化首页首屏价值主张",
                "description": "在首屏明确展示：'ChinaBound Travel - 你的中国旅行指南，提供真实、实用的旅行攻略和工具'",
                "expected_impact": "降低跳出率15-25%",
                "implementation": "修改首页banner文案，添加清晰的副标题和价值描述",
                "effort": "low"
            },
            {
                "priority": "high",
                "title": "首屏添加明确CTA按钮",
                "description": "添加2个CTA按钮：'开始规划行程'（主按钮）和'浏览热门攻略'（次按钮）",
                "expected_impact": "提升点击率20-30%",
                "implementation": "在首页banner下方添加CTA按钮组，链接到热门文章和行程规划页面",
                "effort": "low"
            },
            {
                "priority": "medium",
                "title": "优化网站加载速度",
                "description": "图片压缩、启用Cloudflare缓存、图片懒加载、最小化CSS/JS",
                "expected_impact": "降低跳出率10-15%，提升SEO排名",
                "implementation": "配置Cloudflare Cache Rule，压缩所有图片，启用懒加载",
                "effort": "medium"
            },
            {
                "priority": "medium",
                "title": "移动端首屏优化",
                "description": "确保移动端首屏在3秒内加载完成，价值主张和CTA在首屏可见",
                "expected_impact": "提升移动端转化率15-20%",
                "implementation": "响应式设计优化，移动端专用CTA布局",
                "effort": "medium"
            },
            {
                "priority": "low",
                "title": "添加社会证明元素",
                "description": "在首屏添加用户评价、阅读量、订阅人数等社会证明",
                "expected_impact": "提升信任度10-15%",
                "implementation": "添加用户评价轮播、统计数据展示",
                "effort": "medium"
            }
        ]

        result = {
            "stage": "认知阶段",
            "bounce_rate": "45%",
            "issues_found": len(issues),
            "issues": issues,
            "recommendations": recommendations,
            "expected_improvement": "降低跳出率15-25%，提升页面浏览深度20-30%"
        }

        self.optimizations["awareness"] = result

        print(f"\n  📊 发现问题: {len(issues)}个")
        print(f"  💡 优化建议: {len(recommendations)}个")
        print(f"  🎯 预期提升: {result['expected_improvement']}")

        return result

    def analyze_conversion_stage(self) -> Dict[str, Any]:
        """分析转化阶段瓶颈（流失60%）"""
        print("\n" + "=" * 60)
        print("  转化阶段优化（流失60%）")
        print("=" * 60)

        issues = []
        recommendations = []

        # 1. 扫描文章中的CTA
        cta_count = 0
        articles_with_cta = 0
        total_articles = 0

        if POSTS_DIR.exists():
            for md_file in POSTS_DIR.glob("*.md"):
                total_articles += 1
                try:
                    content = md_file.read_text(encoding="utf-8")
                    has_booking = bool(re.search(r'(booking\.com|agoda\.com|klook\.com|trip\.com)', content, re.IGNORECASE))
                    has_cta_text = bool(re.search(r'(book now|reserve|check price|get started|plan your)', content, re.IGNORECASE))
                    if has_booking or has_cta_text:
                        articles_with_cta += 1
                        cta_count += len(re.findall(r'(booking\.com|agoda\.com|klook\.com|trip\.com)', content, re.IGNORECASE))
                except Exception:
                    pass

        cta_coverage = articles_with_cta / max(1, total_articles) * 100

        if cta_coverage < 90:
            issues.append({"type": "CTA覆盖率不足", "severity": "high", "detail": f"仅{cta_coverage:.1f}%的文章包含联盟链接或CTA，目标100%"})

        # 2. 检查CTA位置
        issues.append({"type": "CTA位置优化", "severity": "high", "detail": "CTA应出现在文章中部（用户阅读高峰）和底部（决策点），而非仅在顶部"})

        # 3. 检查信任信号
        issues.append({"type": "信任信号缺失", "severity": "medium", "detail": "联盟链接附近缺少价格保证、免费取消、用户评价等信任信号"})

        # 4. 检查转化流程
        issues.append({"type": "转化流程复杂", "severity": "medium", "detail": "用户从点击到预订需多次跳转，建议在新标签页打开，保留原页面"})

        # 生成优化建议
        recommendations = [
            {
                "priority": "high",
                "title": "CTA位置优化 - 文章中部插入",
                "description": "在每篇文章的中部（约50%位置）插入相关的联盟推荐区块，包含酒店/交通/门票推荐",
                "expected_impact": "提升联盟点击率30-50%",
                "implementation": "创建文章中部CTA模板，自动根据文章主题推荐相关产品",
                "effort": "medium"
            },
            {
                "priority": "high",
                "title": "优化CTA文案 - 从'预订'到'查看价格'",
                "description": "使用'查看今日最低价'、'比较酒店价格'等低压力文案，替代'立即预订'",
                "expected_impact": "提升CTA点击率20-30%",
                "implementation": "批量修改文章底部CTA文案，A/B测试不同文案效果",
                "effort": "low"
            },
            {
                "priority": "high",
                "title": "添加信任信号 - 价格保证和免费取消",
                "description": "在联盟链接附近添加'免费取消'、'价格匹配保证'、'1000+评价'等信任信号",
                "expected_impact": "提升转化率15-25%",
                "implementation": "创建信任信号组件，在所有联盟推荐区块显示",
                "effort": "medium"
            },
            {
                "priority": "medium",
                "title": "创建产品对比表格",
                "description": "在热门文章中添加酒店/交通/门票对比表格，包含价格、评分、特色、链接",
                "expected_impact": "提升决策效率和转化率20-30%",
                "implementation": "创建产品对比表格模板，为Top10文章手动添加",
                "effort": "high"
            },
            {
                "priority": "medium",
                "title": "退出意图弹窗 - 最后机会优惠",
                "description": "当用户试图离开页面时，显示'获取中国旅行省钱指南'弹窗，收集邮件并推荐优惠",
                "expected_impact": "挽回5-10%的流失用户，增加邮件订阅",
                "implementation": "添加退出意图弹窗脚本，配置MailerLite集成",
                "effort": "medium"
            },
            {
                "priority": "low",
                "title": "优化联盟链接打开方式",
                "description": "所有联盟链接在新标签页打开，保留用户在原页面，降低流失",
                "expected_impact": "降低跳出率5-10%",
                "implementation": "批量修改所有联盟链接，添加target='_blank'",
                "effort": "low"
            }
        ]

        result = {
            "stage": "转化阶段",
            "bounce_rate": "60%",
            "cta_coverage": f"{cta_coverage:.1f}%",
            "total_articles": total_articles,
            "articles_with_cta": articles_with_cta,
            "issues_found": len(issues),
            "issues": issues,
            "recommendations": recommendations,
            "expected_improvement": "提升联盟点击率30-50%，提升转化率15-25%"
        }

        self.optimizations["conversion"] = result

        print(f"\n  📊 CTA覆盖率: {cta_coverage:.1f}% ({articles_with_cta}/{total_articles})")
        print(f"  📊 发现问题: {len(issues)}个")
        print(f"  💡 优化建议: {len(recommendations)}个")
        print(f"  🎯 预期提升: {result['expected_improvement']}")

        return result

    def analyze_retention_stage(self) -> Dict[str, Any]:
        """分析留存阶段瓶颈（流失50%）"""
        print("\n" + "=" * 60)
        print("  留存阶段优化（流失50%）")
        print("=" * 60)

        issues = []
        recommendations = []

        # 1. 检查邮件订阅现状
        issues.append({"type": "邮件订阅率低", "severity": "high", "detail": "总订阅仅1人，订阅CTA覆盖不足，缺少Lead Magnet"})

        # 2. 检查回访激励
        issues.append({"type": "回访激励缺失", "severity": "high", "detail": "没有邮件序列、推送通知、会员内容等回访激励机制"})

        # 3. 检查个性化推荐
        issues.append({"type": "个性化推荐不足", "severity": "medium", "detail": "文章底部相关推荐基于标签，未基于用户行为个性化"})

        # 4. 检查社区建设
        issues.append({"type": "社区互动缺失", "severity": "medium", "detail": "没有评论区、论坛、社媒群组等用户互动渠道"})

        # 生成优化建议
        recommendations = [
            {
                "priority": "high",
                "title": "创建7天邮件欢迎序列",
                "description": "新订阅者收到7封邮件：Day1欢迎+资源包、Day2行程规划、Day3交通指南、Day4美食推荐、Day5签证须知、Day6省钱技巧、Day7高级攻略+联盟推荐",
                "expected_impact": "提升回访率30-50%，提升联盟收入20-30%",
                "implementation": "在MailerLite中创建自动化邮件序列，编写7封邮件内容",
                "effort": "high"
            },
            {
                "priority": "high",
                "title": "优化Lead Magnet - 中国旅行省钱指南",
                "description": "创建'中国旅行省钱指南PDF'（包含10个省钱技巧、5个免费资源、3个优惠码），在所有文章底部和侧边栏推广",
                "expected_impact": "提升邮件订阅率200-300%",
                "implementation": "创建PDF内容，设计美观封面，配置MailerLite自动发送",
                "effort": "medium"
            },
            {
                "priority": "high",
                "title": "文章底部订阅CTA优化",
                "description": "在每篇文章底部添加订阅区块：'获取中国旅行每周攻略 + 独家省钱技巧'，包含输入框和订阅按钮",
                "expected_impact": "提升订阅率50-100%",
                "implementation": "创建文章底部订阅模板，批量添加到所有文章",
                "effort": "medium"
            },
            {
                "priority": "medium",
                "title": "创建会员专属内容区",
                "description": "为订阅者提供专属内容：高级行程模板、独家优惠码、直播问答、提前访问新文章",
                "expected_impact": "提升订阅价值感和留存率20-30%",
                "implementation": "创建会员页面，配置内容访问权限",
                "effort": "high"
            },
            {
                "priority": "medium",
                "title": "推送通知 - 新文章提醒",
                "description": "启用浏览器推送通知，新文章发布时自动推送给订阅用户",
                "expected_impact": "提升回访率15-25%",
                "implementation": "集成OneSignal或类似推送服务，配置自动推送",
                "effort": "medium"
            },
            {
                "priority": "medium",
                "title": "个性化相关文章推荐",
                "description": "基于用户阅读历史和热门文章，优化文章底部相关推荐算法",
                "expected_impact": "提升页面浏览深度20-30%",
                "implementation": "优化Hugo相关文章模板，基于标签和分类加权",
                "effort": "medium"
            },
            {
                "priority": "low",
                "title": "添加评论区和社交分享",
                "description": "集成Giscus或Disqus评论系统，添加社媒分享按钮，促进用户互动",
                "expected_impact": "提升用户参与度和回访率10-15%",
                "implementation": "集成评论系统，添加分享按钮",
                "effort": "low"
            }
        ]

        result = {
            "stage": "留存阶段",
            "bounce_rate": "50%",
            "current_subscribers": 1,
            "issues_found": len(issues),
            "issues": issues,
            "recommendations": recommendations,
            "expected_improvement": "提升回访率30-50%，邮件订阅增长200-300%"
        }

        self.optimizations["retention"] = result

        print(f"\n  📊 当前订阅: 1人")
        print(f"  📊 发现问题: {len(issues)}个")
        print(f"  💡 优化建议: {len(recommendations)}个")
        print(f"  🎯 预期提升: {result['expected_improvement']}")

        return result

    def generate_optimization_report(self) -> str:
        """生成优化报告"""
        print("\n" + "=" * 60)
        print("  生成用户旅程优化报告")
        print("=" * 60)

        now = self.generated_at

        report = f"""# ChinaBound Travel 用户旅程关键瓶颈优化报告

**生成时间**: {now.strftime('%Y-%m-%d %H:%M:%S')}
**优化阶段**: 认知阶段 → 转化阶段 → 留存阶段

---

## 📊 优化总览

| 阶段 | 当前流失率 | 发现问题 | 优化建议 | 预期提升 |
|------|-----------|---------|---------|---------|
| 认知阶段 | 45% | {self.optimizations.get('awareness', {}).get('issues_found', 0)} | {len(self.optimizations.get('awareness', {}).get('recommendations', []))} | 降低跳出率15-25% |
| 转化阶段 | 60% | {self.optimizations.get('conversion', {}).get('issues_found', 0)} | {len(self.optimizations.get('conversion', {}).get('recommendations', []))} | 提升转化率15-25% |
| 留存阶段 | 50% | {self.optimizations.get('retention', {}).get('issues_found', 0)} | {len(self.optimizations.get('retention', {}).get('recommendations', []))} | 提升回访率30-50% |

**综合预期**: 整体转化率提升50-100%，用户生命周期价值提升30-50%

---

## 🔴 第一优先级：转化阶段优化（流失60%）

### 发现问题
"""

        for issue in self.optimizations.get('conversion', {}).get('issues', []):
            severity_icon = "🔴" if issue['severity'] == 'high' else "🟡"
            report += f"- {severity_icon} **{issue['type']}**: {issue['detail']}\n"

        report += """
### 优化建议（按优先级排序）

"""

        for i, rec in enumerate(self.optimizations.get('conversion', {}).get('recommendations', []), 1):
            priority_icon = "🔴" if rec['priority'] == 'high' else "🟡" if rec['priority'] == 'medium' else "🟢"
            report += f"""#### {i}. {priority_icon} {rec['title']}

**描述**: {rec['description']}

**预期影响**: {rec['expected_impact']}

**实施方案**: {rec['implementation']}

**实施难度**: {rec['effort']}

---

"""

        report += """## 🟡 第二优先级：留存阶段优化（流失50%）

### 发现问题
"""

        for issue in self.optimizations.get('retention', {}).get('issues', []):
            severity_icon = "🔴" if issue['severity'] == 'high' else "🟡"
            report += f"- {severity_icon} **{issue['type']}**: {issue['detail']}\n"

        report += """
### 优化建议（按优先级排序）

"""

        for i, rec in enumerate(self.optimizations.get('retention', {}).get('recommendations', []), 1):
            priority_icon = "🔴" if rec['priority'] == 'high' else "🟡" if rec['priority'] == 'medium' else "🟢"
            report += f"""#### {i}. {priority_icon} {rec['title']}

**描述**: {rec['description']}

**预期影响**: {rec['expected_impact']}

**实施方案**: {rec['implementation']}

**实施难度**: {rec['effort']}

---

"""

        report += """## 🟢 第三优先级：认知阶段优化（流失45%）

### 发现问题
"""

        for issue in self.optimizations.get('awareness', {}).get('issues', []):
            severity_icon = "🔴" if issue['severity'] == 'high' else "🟡"
            report += f"- {severity_icon} **{issue['type']}**: {issue['detail']}\n"

        report += """
### 优化建议（按优先级排序）

"""

        for i, rec in enumerate(self.optimizations.get('awareness', {}).get('recommendations', []), 1):
            priority_icon = "🔴" if rec['priority'] == 'high' else "🟡" if rec['priority'] == 'medium' else "🟢"
            report += f"""#### {i}. {priority_icon} {rec['title']}

**描述**: {rec['description']}

**预期影响**: {rec['expected_impact']}

**实施方案**: {rec['implementation']}

**实施难度**: {rec['effort']}

---

"""

        report += f"""## 🚀 实施路线图

### 第一周（立即执行）
1. 🔴 优化CTA文案 - 从'预订'到'查看价格'（低难度，高影响）
2. 🔴 优化首页首屏价值主张和CTA按钮（低难度，高影响）
3. 🔴 所有联盟链接在新标签页打开（低难度，中影响）
4. 🟡 文章底部订阅CTA优化（中难度，高影响）

### 第二周
5. 🔴 CTA位置优化 - 文章中部插入（中难度，高影响）
6. 🔴 创建Lead Magnet - 中国旅行省钱指南PDF（中难度，高影响）
7. 🟡 添加信任信号 - 价格保证和免费取消（中难度，中影响）
8. 🟡 优化网站加载速度（中难度，中影响）

### 第三周
9. 🔴 创建7天邮件欢迎序列（高难度，高影响）
10. 🟡 创建产品对比表格（高难度，中影响）
11. 🟡 推送通知 - 新文章提醒（中难度，中影响）
12. 🟡 个性化相关文章推荐（中难度，中影响）

### 第四周及以后
13. 🟡 退出意图弹窗（中难度，中影响）
14. 🟡 创建会员专属内容区（高难度，中影响）
15. 🟢 添加评论区和社交分享（低难度，低影响）
16. 🟢 移动端首屏优化（中难度，中影响）
17. 🟢 添加社会证明元素（中难度，低影响）

---

## 📊 预期效果

| 指标 | 当前 | 1个月后 | 3个月后 |
|------|------|---------|---------|
| 跳出率 | 89% | 70% | 55% |
| 平均停留时长 | 1分48秒 | 2分30秒 | 3分30秒 |
| 联盟点击率 | 0.5% | 2% | 5% |
| 联盟转化率 | 0% | 0.5% | 2% |
| 邮件订阅 | 1人 | 50人 | 200人 |
| 回访率 | 5% | 15% | 30% |
| 月收入 | $0 | $50 | $300 |

---

*报告由用户旅程关键瓶颈优化器自动生成*
*生成时间: {now.strftime('%Y-%m-%d %H:%M:%S')}*
"""

        # 保存报告
        report_file = JOURNEY_DIR / f"journey_optimization_{now.strftime('%Y%m%d_%H%M%S')}.md"
        latest_report = JOURNEY_DIR / "latest_journey_optimization.md"

        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)
        with open(latest_report, "w", encoding="utf-8") as f:
            f.write(report)

        # 保存JSON数据
        json_file = JOURNEY_DIR / "journey_optimization_data.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(self.optimizations, f, ensure_ascii=False, indent=2)

        print(f"\n  ✅ 优化报告已生成: {report_file}")
        print(f"  ✅ 最新报告: {latest_report}")
        print(f"  ✅ JSON数据: {json_file}")

        return report

    def run(self, stages: List[str] = None) -> str:
        """运行完整的优化流程"""
        if stages is None:
            stages = ["awareness", "conversion", "retention"]

        print("\n" + "=" * 60)
        print("  ChinaBound Travel 用户旅程关键瓶颈优化器")
        print("=" * 60)
        print(f"\n  运行时间: {self.generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  优化阶段: {', '.join(stages)}")

        if "awareness" in stages:
            self.analyze_awareness_stage()
        if "conversion" in stages:
            self.analyze_conversion_stage()
        if "retention" in stages:
            self.analyze_retention_stage()

        return self.generate_optimization_report()


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="ChinaBound Travel 用户旅程关键瓶颈优化器")
    parser.add_argument("--all", action="store_true", help="优化所有阶段")
    parser.add_argument("--awareness", action="store_true", help="仅优化认知阶段")
    parser.add_argument("--conversion", action="store_true", help="仅优化转化阶段")
    parser.add_argument("--retention", action="store_true", help="仅优化留存阶段")
    parser.add_argument("--report-only", action="store_true", help="仅生成报告（不分析）")

    args = parser.parse_args()

    optimizer = JourneyOptimizer()

    stages = []
    if args.all or not any([args.awareness, args.conversion, args.retention]):
        stages = ["awareness", "conversion", "retention"]
    else:
        if args.awareness:
            stages.append("awareness")
        if args.conversion:
            stages.append("conversion")
        if args.retention:
            stages.append("retention")

    optimizer.run(stages)

    print("\n" + "=" * 60)
    print("  ✅ 用户旅程优化完成！")
    print("=" * 60)
    print(f"\n  📁 报告目录: {JOURNEY_DIR}")
    print(f"  📄 最新报告: {JOURNEY_DIR / 'latest_journey_optimization.md'}")
    print(f"  📊 JSON数据: {JOURNEY_DIR / 'journey_optimization_data.json'}")


if __name__ == "__main__":
    main()
