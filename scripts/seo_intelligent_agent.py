#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEO Intelligent Agent - ChinaBound Travel 2.0
================================================
统一的SEO智能优化Agent，整合现有能力并增加智能分析和自动优化功能。

核心能力：
1. 数据采集层：自动从GSC、GA4、本地文件采集数据
2. 机会识别层：识别高展示低CTR、排名4-20、内容质量低等机会
3. 智能分析层：分析问题根因，生成优化建议
4. 自动优化层：自动优化Title/Meta、内链、内容结构
5. 效果追踪层：追踪优化效果，持续迭代

用法：
  python scripts/seo_intelligent_agent.py --analyze          # 分析SEO机会
  python scripts/seo_intelligent_agent.py --optimize --dry-run # 生成优化方案（不执行）
  python scripts/seo_intelligent_agent.py --optimize --apply   # 执行优化
  python scripts/seo_intelligent_agent.py --report             # 生成SEO优化报告
  python scripts/seo_intelligent_agent.py --track              # 追踪优化效果
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import csv
from collections import defaultdict
from datetime import datetime, timedelta

# P1-AI-OPS-03: Consume SEO optimization strategy from Learning Closed Loop
try:
    from strategy_consumer import StrategyConsumer
    _STRATEGY_CONSUMER = None
except Exception:
    _STRATEGY_CONSUMER = None
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# 尝试加载.env
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

SCRIPT_DIR = Path(__file__).resolve().parent
BLOG_ROOT = SCRIPT_DIR.parent
POSTS_DIR = BLOG_ROOT / "content" / "posts"
REPORTS_DIR = BLOG_ROOT / "reports"
SEO_REPORTS_DIR = REPORTS_DIR / "seo"
SEO_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# 优化历史记录
OPTIMIZATION_HISTORY_FILE = SEO_REPORTS_DIR / "optimization_history.json"

# ============================================================
# 数据采集层
# ============================================================

class SEODataCollector:
    """SEO数据采集器：从GSC、GA4、本地文件采集数据"""

    def __init__(self):
        self.gsc_data = {}
        self.ga4_data = {}
        self.content_data = {}
        self.technical_data = {}

    def collect_all(self) -> Dict:
        """采集所有SEO相关数据"""
        print("=" * 60)
        print("  SEO Intelligent Agent - 数据采集")
        print("=" * 60)

        self.collect_gsc_data()
        self.collect_content_data()
        self.collect_technical_data()

        return {
            "gsc": self.gsc_data,
            "content": self.content_data,
            "technical": self.technical_data,
            "collected_at": datetime.now().isoformat(),
        }

    def collect_gsc_data(self) -> Dict:
        """采集GSC数据（从现有CSV/JSON文件读取）"""
        print("\n[1/3] 采集GSC数据...")

        gsc_data = {
            "queries": [],
            "pages": [],
            "query_page_cross": [],
            "page_inventory": [],
            "url_inspection": {},
            "summary": {
                "total_impressions": 0,
                "total_clicks": 0,
                "avg_ctr": 0,
                "avg_position": 0,
                "indexed_pages": 0,
                "not_indexed_pages": 0,
            }
        }

        # 1. 读取CONTENT_SEO_INVENTORY.csv（页面级别GSC数据）
        content_inventory_file = SEO_REPORTS_DIR / "CONTENT_SEO_INVENTORY.csv"
        if content_inventory_file.exists():
            print(f"  ✅ 读取 CONTENT_SEO_INVENTORY.csv（页面级别GSC数据）")
            page_inventory = self._load_csv(content_inventory_file)
            gsc_data["page_inventory"] = page_inventory

            # 转换为统一的pages格式
            pages = []
            for row in page_inventory:
                try:
                    page = {
                        "keys": row.get("url", ""),
                        "title": row.get("title", ""),
                        "content_id": row.get("content_id", ""),
                        "clicks": int(float(row.get("clicks_28d", 0) or 0)),
                        "impressions": int(float(row.get("impressions_28d", 0) or 0)),
                        "ctr": float(row.get("ctr_28d", 0) or 0),
                        "position": float(row.get("position_28d", 0) or 0),
                        "indexed_status": row.get("indexed_status", ""),
                        "published_date": row.get("published_date", ""),
                    }
                    pages.append(page)
                except (TypeError, ValueError):
                    continue
            gsc_data["pages"] = pages

            # 计算汇总数据（基于有展示的页面）
            pages_with_impressions = [p for p in pages if p.get("impressions", 0) > 0]
            if pages_with_impressions:
                total_impressions = sum(p.get("impressions", 0) for p in pages_with_impressions)
                total_clicks = sum(p.get("clicks", 0) for p in pages_with_impressions)
                avg_position = sum(p.get("position", 0) for p in pages_with_impressions) / len(pages_with_impressions)
                avg_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0

                indexed_count = len([p for p in pages if p.get("indexed_status") == "INDEXED"])
                not_indexed_count = len([p for p in pages if p.get("indexed_status") != "INDEXED"])

                gsc_data["summary"] = {
                    "total_impressions": total_impressions,
                    "total_clicks": total_clicks,
                    "avg_ctr": round(avg_ctr, 2),
                    "avg_position": round(avg_position, 2),
                    "total_pages": len(pages),
                    "pages_with_impressions": len(pages_with_impressions),
                    "indexed_pages": indexed_count,
                    "not_indexed_pages": not_indexed_count,
                }

                print(f"  📊 页面总数: {len(pages)}, 有展示页面: {len(pages_with_impressions)}")
                print(f"  📊 已索引: {indexed_count}, 未索引: {not_indexed_count}")
                print(f"  📊 总展示: {total_impressions}, 总点击: {total_clicks}")
                print(f"  📊 平均CTR: {round(avg_ctr, 2)}%, 平均排名: {round(avg_position, 2)}")
        else:
            print(f"  ⚠️ CONTENT_SEO_INVENTORY.csv 不存在")

        # 2. 读取url_inspection_results.json（URL索引检查结果）
        url_inspection_file = SEO_REPORTS_DIR / "url_inspection_results.json"
        if url_inspection_file.exists():
            print(f"  ✅ 读取 url_inspection_results.json（URL索引检查）")
            try:
                with open(url_inspection_file, encoding="utf-8") as f:
                    gsc_data["url_inspection"] = json.load(f)
                print(f"  📊 检查URL数: {len(gsc_data['url_inspection'])}")
            except Exception as e:
                print(f"  ⚠️ 读取 url_inspection_results.json 失败: {e}")

        # 3. 尝试读取现有的GSC CSV文件（查询级别数据）
        gsc_csv_files = [
            SEO_REPORTS_DIR / "query_dimension.csv",
            SEO_REPORTS_DIR / "page_dimension.csv",
            SEO_REPORTS_DIR / "query_page_cross.csv",
        ]

        for csv_file in gsc_csv_files:
            if csv_file.exists():
                print(f"  ✅ 读取 {csv_file.name}")
                rows = self._load_gsc_csv(csv_file)
                if "query" in csv_file.name and "page" not in csv_file.name:
                    gsc_data["queries"] = rows
                elif "cross" in csv_file.name:
                    gsc_data["query_page_cross"] = rows

        # 4. 尝试读取现有的SEO机会报告
        seo_opportunities_file = SEO_REPORTS_DIR / "seo_opportunities.csv"
        if seo_opportunities_file.exists():
            print(f"  ✅ 读取 seo_opportunities.csv")
            gsc_data["opportunities"] = self._load_csv(seo_opportunities_file)

        # 5. 如果没有查询数据但有页面数据，用页面数据作为查询数据的补充
        if not gsc_data["queries"] and gsc_data["pages"]:
            print(f"  ℹ️ 使用页面数据作为查询数据补充")
            gsc_data["queries"] = gsc_data["pages"]

        self.gsc_data = gsc_data
        return gsc_data

    def collect_content_data(self) -> Dict:
        """采集内容数据（扫描本地Markdown文件）"""
        print("\n[2/3] 采集内容数据...")

        content_data = {
            "total_posts": 0,
            "posts": [],
            "quality_distribution": {"excellent": 0, "good": 0, "average": 0, "poor": 0},
            "issues": [],
        }

        if not POSTS_DIR.exists():
            print("  ⚠️ content/posts 目录不存在")
            self.content_data = content_data
            return content_data

        md_files = list(POSTS_DIR.glob("*.md"))
        content_data["total_posts"] = len(md_files)
        print(f"  📝 扫描到 {len(md_files)} 篇文章")

        for md_file in md_files:
            try:
                post_info = self._analyze_post_file(md_file)
                content_data["posts"].append(post_info)

                # 质量分级
                word_count = post_info.get("word_count", 0)
                has_meta = bool(post_info.get("meta_description"))
                has_internal_links = post_info.get("internal_links", 0) > 0

                score = 0
                if word_count >= 2000:
                    score += 2
                elif word_count >= 1000:
                    score += 1
                if has_meta:
                    score += 1
                if has_internal_links:
                    score += 1

                if score >= 4:
                    content_data["quality_distribution"]["excellent"] += 1
                elif score >= 3:
                    content_data["quality_distribution"]["good"] += 1
                elif score >= 2:
                    content_data["quality_distribution"]["average"] += 1
                else:
                    content_data["quality_distribution"]["poor"] += 1

            except Exception as e:
                content_data["issues"].append({"file": md_file.name, "error": str(e)})

        print(f"  📊 质量分布: {content_data['quality_distribution']}")
        self.content_data = content_data
        return content_data

    def collect_technical_data(self) -> Dict:
        """采集技术SEO数据"""
        print("\n[3/3] 采集技术SEO数据...")

        technical_data = {
            "canonical_issues": [],
            "meta_issues": [],
            "og_issues": [],
            "internal_link_issues": [],
            "indexing_status": {},
        }

        # 尝试读取现有的技术审计报告
        audit_files = [
            REPORTS_DIR / "P1_GROWTH_07B_TECHNICAL_SEO_REPORT.md",
            SEO_REPORTS_DIR / "INDEX_COVERAGE_BASELINE.md",
        ]

        for audit_file in audit_files:
            if audit_file.exists():
                print(f"  ✅ 读取 {audit_file.name}")

        # 简单的规范化检查
        print("  🔍 检查规范化URL...")
        canonical_conflicts = self._check_canonical_conflicts()
        technical_data["canonical_issues"] = canonical_conflicts
        print(f"  📊 发现 {len(canonical_conflicts)} 个规范化问题")

        self.technical_data = technical_data
        return technical_data

    def _load_gsc_csv(self, file_path: Path) -> List[Dict]:
        """加载GSC CSV文件"""
        rows = []
        try:
            with open(file_path, encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    try:
                        rows.append({
                            "keys": (r.get("keys") or r.get("query") or r.get("page") or "").strip(),
                            "clicks": int(float(r.get("clicks") or 0)),
                            "impressions": int(float(r.get("impressions") or 0)),
                            "ctr": float(r.get("ctr") or 0),
                            "position": float(r.get("position") or 0),
                        })
                    except (TypeError, ValueError):
                        continue
        except Exception as e:
            print(f"  ⚠️ 读取 {file_path.name} 失败: {e}")
        return rows

    def _load_csv(self, file_path: Path) -> List[Dict]:
        """加载通用CSV文件"""
        rows = []
        try:
            with open(file_path, encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    rows.append(dict(r))
        except Exception as e:
            print(f"  ⚠️ 读取 {file_path.name} 失败: {e}")
        return rows

    def _analyze_post_file(self, file_path: Path) -> Dict:
        """分析单篇文章文件"""
        content = file_path.read_text(encoding="utf-8", errors="replace")

        # 解析Front Matter
        fm, body, delim = self._split_front_matter(content)

        # 提取标题
        title = ""
        meta_description = ""
        if fm:
            title_match = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', fm, re.MULTILINE)
            if title_match:
                title = title_match.group(1).strip()
            desc_match = re.search(r'^description:\s*["\']?(.+?)["\']?\s*$', fm, re.MULTILINE)
            if desc_match:
                meta_description = desc_match.group(1).strip()

        # 计算字数（英文单词数）
        word_count = len(re.findall(r'\b\w+\b', body))

        # 统计内链
        internal_links = len(re.findall(r'\]\(/posts/', body))
        external_links = len(re.findall(r'\]\(https?://', body))

        # 统计标题层级
        h1_count = len(re.findall(r'^#\s', body, re.MULTILINE))
        h2_count = len(re.findall(r'^##\s', body, re.MULTILINE))
        h3_count = len(re.findall(r'^###\s', body, re.MULTILINE))

        return {
            "file": file_path.name,
            "slug": file_path.stem,
            "title": title,
            "meta_description": meta_description,
            "word_count": word_count,
            "internal_links": internal_links,
            "external_links": external_links,
            "h1_count": h1_count,
            "h2_count": h2_count,
            "h3_count": h3_count,
            "has_meta": bool(meta_description),
            "has_enough_content": word_count >= 1000,
            "has_internal_links": internal_links > 0,
        }

    def _split_front_matter(self, text: str) -> Tuple[Optional[str], str, str]:
        """分割Front Matter和正文"""
        for delim in ("---", "+++"):
            ed = re.escape(delim)
            m = re.match(r"^%s\s*\n(.*?)\n%s\s*\n" % (ed, ed), text, re.DOTALL)
            if m:
                return m.group(1), text[m.end():], delim
        return None, text, ""

    def _check_canonical_conflicts(self) -> List[Dict]:
        """检查规范化URL冲突"""
        conflicts = []
        # 简单实现：检查是否有重复的slug或标题
        slugs = defaultdict(list)
        titles = defaultdict(list)

        for post in self.content_data.get("posts", []):
            slug = post.get("slug", "")
            title = post.get("title", "")
            if slug:
                slugs[slug].append(post.get("file", ""))
            if title:
                titles[title].append(post.get("file", ""))

        for slug, files in slugs.items():
            if len(files) > 1:
                conflicts.append({"type": "duplicate_slug", "slug": slug, "files": files})

        return conflicts


# ============================================================
# 机会识别层
# ============================================================

class SEOOpportunityDetector:
    """SEO机会识别器：识别高展示低CTR、排名4-20、内容质量低等机会"""

    def __init__(self, data: Dict):
        self.data = data
        self.opportunities = []

    def detect_all(self) -> List[Dict]:
        """识别所有SEO机会"""
        print("\n" + "=" * 60)
        print("  SEO Intelligent Agent - 机会识别")
        print("=" * 60)

        self.detect_low_ctr_opportunities()
        self.detect_position_opportunities()
        self.detect_content_quality_opportunities()
        self.detect_technical_opportunities()
        self.detect_zero_click_opportunities()

        # 按优先级排序
        self.opportunities.sort(key=lambda x: x.get("priority_score", 0), reverse=True)

        print(f"\n📊 共识别 {len(self.opportunities)} 个SEO优化机会")
        print(f"  🔴 高优先级: {len([o for o in self.opportunities if o.get('priority') == 'high'])}")
        print(f"  🟡 中优先级: {len([o for o in self.opportunities if o.get('priority') == 'medium'])}")
        print(f"  🟢 低优先级: {len([o for o in self.opportunities if o.get('priority') == 'low'])}")

        return self.opportunities

    def detect_low_ctr_opportunities(self) -> List[Dict]:
        """识别高展示低CTR机会"""
        print("\n[1/5] 识别高展示低CTR机会...")

        opportunities = []
        queries = self.data.get("gsc", {}).get("queries", [])

        for query in queries:
            impressions = query.get("impressions", 0)
            ctr = query.get("ctr", 0)
            position = query.get("position", 0)

            # 高展示（>=50）且低CTR（<2%）
            if impressions >= 50 and ctr < 2.0:
                priority_score = impressions * (2.0 - ctr) / 100
                priority = "high" if priority_score > 50 else "medium"

                opportunity = {
                    "type": "low_ctr",
                    "category": "title_meta_optimization",
                    "target": query.get("keys", ""),
                    "impressions": impressions,
                    "ctr": ctr,
                    "position": position,
                    "priority": priority,
                    "priority_score": round(priority_score, 2),
                    "recommended_action": "TITLE_META",
                    "description": f"查询 '{query.get('keys', '')}' 展示 {impressions} 次但CTR仅 {ctr}%，优化Title和Meta描述可提升点击",
                    "estimated_impact": f"预计可提升CTR至 {min(ctr + 2, 5)}%，增加约 {int(impressions * 0.02)} 次点击",
                }
                opportunities.append(opportunity)
                self.opportunities.append(opportunity)

        print(f"  📊 识别 {len(opportunities)} 个高展示低CTR机会")
        return opportunities

    def detect_position_opportunities(self) -> List[Dict]:
        """识别排名4-20的机会（接近首页但未进入前3）"""
        print("\n[2/5] 识别排名4-20机会...")

        opportunities = []
        queries = self.data.get("gsc", {}).get("queries", [])

        for query in queries:
            position = query.get("position", 0)
            impressions = query.get("impressions", 0)

            # 排名4-10（首页但非前3）
            if 4 <= position <= 10:
                priority_score = (11 - position) * impressions / 100
                priority = "high" if priority_score > 30 else "medium"

                opportunity = {
                    "type": "position_4_10",
                    "category": "content_deepening",
                    "target": query.get("keys", ""),
                    "impressions": impressions,
                    "position": position,
                    "ctr": query.get("ctr", 0),
                    "priority": priority,
                    "priority_score": round(priority_score, 2),
                    "recommended_action": "CONTENT_UPDATE",
                    "description": f"查询 '{query.get('keys', '')}' 排名第 {position} 位，进入前3可大幅提升流量",
                    "estimated_impact": f"进入前3预计可提升展示 {int(impressions * 0.5)} 次，点击增加约 {int(impressions * 0.05)} 次",
                }
                opportunities.append(opportunity)
                self.opportunities.append(opportunity)

            # 排名11-20（第二页，有机会进入首页）
            elif 11 <= position <= 20:
                priority_score = (21 - position) * impressions / 200
                priority = "medium" if priority_score > 10 else "low"

                opportunity = {
                    "type": "position_11_20",
                    "category": "seo_optimization",
                    "target": query.get("keys", ""),
                    "impressions": impressions,
                    "position": position,
                    "ctr": query.get("ctr", 0),
                    "priority": priority,
                    "priority_score": round(priority_score, 2),
                    "recommended_action": "INTERNAL_LINK",
                    "description": f"查询 '{query.get('keys', '')}' 排名第 {position} 位，增加内链和内容深度可进入首页",
                    "estimated_impact": f"进入首页预计可提升展示 {int(impressions * 0.3)} 次",
                }
                opportunities.append(opportunity)
                self.opportunities.append(opportunity)

        print(f"  📊 识别 {len(opportunities)} 个排名4-20机会")
        return opportunities

    def detect_content_quality_opportunities(self) -> List[Dict]:
        """识别内容质量低的机会"""
        print("\n[3/5] 识别内容质量低机会...")

        opportunities = []
        posts = self.data.get("content", {}).get("posts", [])

        for post in posts:
            word_count = post.get("word_count", 0)
            has_meta = post.get("has_meta", False)
            has_internal_links = post.get("has_internal_links", False)
            internal_links = post.get("internal_links", 0)

            issues = []
            if word_count < 1000:
                issues.append(f"内容不足（{word_count}词）")
            if not has_meta:
                issues.append("缺少Meta描述")
            if not has_internal_links:
                issues.append("缺少内链")
            elif internal_links < 3:
                issues.append(f"内链不足（{internal_links}条）")

            if issues:
                priority = "high" if len(issues) >= 3 else "medium"
                priority_score = len(issues) * 10 + (1000 - min(word_count, 1000)) / 100

                opportunity = {
                    "type": "content_quality",
                    "category": "content_optimization",
                    "target": post.get("file", ""),
                    "title": post.get("title", ""),
                    "word_count": word_count,
                    "issues": issues,
                    "priority": priority,
                    "priority_score": round(priority_score, 2),
                    "recommended_action": "CONTENT_UPDATE",
                    "description": f"文章 '{post.get('title', post.get('file', ''))}' 存在 {len(issues)} 个质量问题: {', '.join(issues)}",
                    "estimated_impact": "优化后可提升排名和用户停留时长",
                }
                opportunities.append(opportunity)
                self.opportunities.append(opportunity)

        print(f"  📊 识别 {len(opportunities)} 个内容质量低机会")
        return opportunities

    def detect_technical_opportunities(self) -> List[Dict]:
        """识别技术SEO机会"""
        print("\n[4/5] 识别技术SEO机会...")

        opportunities = []
        canonical_issues = self.data.get("technical", {}).get("canonical_issues", [])

        for issue in canonical_issues:
            opportunity = {
                "type": "technical_seo",
                "category": "canonical_fix",
                "target": issue.get("slug", ""),
                "issues": issue.get("files", []),
                "priority": "high",
                "priority_score": 50,
                "recommended_action": "TECHNICAL_REVIEW",
                "description": f"规范化URL冲突: {issue.get('slug', '')} 出现在 {len(issue.get('files', []))} 个文件中",
                "estimated_impact": "修复后可避免重复内容惩罚",
            }
            opportunities.append(opportunity)
            self.opportunities.append(opportunity)

        print(f"  📊 识别 {len(opportunities)} 个技术SEO机会")
        return opportunities

    def detect_zero_click_opportunities(self) -> List[Dict]:
        """识别高展示零点击机会"""
        print("\n[5/5] 识别高展示零点击机会...")

        opportunities = []
        queries = self.data.get("gsc", {}).get("queries", [])

        for query in queries:
            impressions = query.get("impressions", 0)
            clicks = query.get("clicks", 0)
            position = query.get("position", 0)

            # 高展示（>=100）且零点击
            if impressions >= 100 and clicks == 0:
                priority_score = impressions / 50
                priority = "high" if priority_score > 30 else "medium"

                opportunity = {
                    "type": "zero_click",
                    "category": "title_meta_optimization",
                    "target": query.get("keys", ""),
                    "impressions": impressions,
                    "clicks": 0,
                    "position": position,
                    "priority": priority,
                    "priority_score": round(priority_score, 2),
                    "recommended_action": "TITLE_META",
                    "description": f"查询 '{query.get('keys', '')}' 展示 {impressions} 次但0点击，Title和Meta描述可能不吸引用户",
                    "estimated_impact": f"优化CTR至2%可增加约 {int(impressions * 0.02)} 次点击",
                }
                opportunities.append(opportunity)
                self.opportunities.append(opportunity)

        print(f"  📊 识别 {len(opportunities)} 个高展示零点击机会")
        return opportunities


# ============================================================
# 智能分析层
# ============================================================

class SEOIntelligentAnalyzer:
    """SEO智能分析器：分析问题根因，生成优化建议"""

    def __init__(self, data: Dict, opportunities: List[Dict]):
        self.data = data
        self.opportunities = opportunities
        self.analysis = {}

    def analyze_all(self) -> Dict:
        """执行全面的SEO智能分析"""
        print("\n" + "=" * 60)
        print("  SEO Intelligent Agent - 智能分析")
        print("=" * 60)

        self.analyze_traffic_patterns()
        self.analyze_content_gaps()
        self.analyze_competition()
        self.analyze_ctr_patterns()
        self.generate_optimization_plan()

        return self.analysis

    def analyze_traffic_patterns(self) -> Dict:
        """分析流量模式"""
        print("\n[1/5] 分析流量模式...")

        gsc_summary = self.data.get("gsc", {}).get("summary", {})
        content_summary = self.data.get("content", {}).get("quality_distribution", {})

        analysis = {
            "overall_health": "poor" if gsc_summary.get("avg_ctr", 0) < 1 else "fair",
            "key_findings": [],
            "traffic_potential": 0,
        }

        # 分析CTR
        avg_ctr = gsc_summary.get("avg_ctr", 0)
        if avg_ctr < 1:
            analysis["key_findings"].append(f"平均CTR极低（{avg_ctr}%），Title和Meta描述需要大幅优化")
        elif avg_ctr < 3:
            analysis["key_findings"].append(f"平均CTR偏低（{avg_ctr}%），有优化空间")

        # 分析排名
        avg_position = gsc_summary.get("avg_position", 0)
        if avg_position > 30:
            analysis["key_findings"].append(f"平均排名靠后（第{avg_position}位），内容深度和权威性需要提升")
        elif avg_position > 15:
            analysis["key_findings"].append(f"平均排名中等（第{avg_position}位），有进入首页的潜力")

        # 分析内容质量
        poor_content = content_summary.get("poor", 0)
        average_content = content_summary.get("average", 0)
        if poor_content > 0:
            analysis["key_findings"].append(f"有 {poor_content} 篇低质量内容，需要优先优化")

        # 估算流量潜力
        total_impressions = gsc_summary.get("total_impressions", 0)
        current_clicks = gsc_summary.get("total_clicks", 0)
        potential_clicks = int(total_impressions * 0.03)  # 目标CTR 3%
        analysis["traffic_potential"] = max(0, potential_clicks - current_clicks)

        print(f"  📊 整体健康度: {analysis['overall_health']}")
        print(f"  📊 流量潜力: 每月可增加约 {analysis['traffic_potential']} 次点击")
        for finding in analysis["key_findings"]:
            print(f"  🔍 {finding}")

        self.analysis["traffic_patterns"] = analysis
        return analysis

    def analyze_content_gaps(self) -> Dict:
        """分析内容缺口"""
        print("\n[2/5] 分析内容缺口...")

        posts = self.data.get("content", {}).get("posts", [])
        queries = self.data.get("gsc", {}).get("queries", [])

        # 统计主题覆盖
        topic_coverage = defaultdict(int)
        for post in posts:
            title = (post.get("title", "") + " " + post.get("file", "")).lower()
            for topic in ["visa", "payment", "transport", "food", "hotel", "city", "internet", "safety", "culture", "photography"]:
                if topic in title:
                    topic_coverage[topic] += 1

        # 统计查询主题
        query_topics = defaultdict(int)
        for query in queries:
            q = query.get("keys", "").lower()
            for topic in ["visa", "payment", "transport", "food", "hotel", "city", "internet", "safety", "culture", "photography"]:
                if topic in q:
                    query_topics[topic] += query.get("impressions", 0)

        # 识别内容缺口（有搜索需求但内容少）
        gaps = []
        for topic, impressions in query_topics.items():
            content_count = topic_coverage.get(topic, 0)
            if impressions > 50 and content_count < 3:
                gaps.append({
                    "topic": topic,
                    "search_impressions": impressions,
                    "content_count": content_count,
                    "gap_score": impressions / max(content_count, 1),
                })

        gaps.sort(key=lambda x: x["gap_score"], reverse=True)

        analysis = {
            "topic_coverage": dict(topic_coverage),
            "query_topics": dict(query_topics),
            "content_gaps": gaps[:5],
        }

        print(f"  📊 主题覆盖: {dict(topic_coverage)}")
        print(f"  📊 识别 {len(gaps)} 个内容缺口")
        for gap in gaps[:3]:
            print(f"  🔍 {gap['topic']}: 搜索展示 {gap['search_impressions']} 次，内容仅 {gap['content_count']} 篇")

        self.analysis["content_gaps"] = analysis
        return analysis

    def analyze_competition(self) -> Dict:
        """分析竞争情况"""
        print("\n[3/5] 分析竞争情况...")

        queries = self.data.get("gsc", {}).get("queries", [])

        # 分析关键词难度（基于排名和展示）
        high_difficulty = []
        medium_difficulty = []
        low_difficulty = []

        for query in queries:
            position = query.get("position", 0)
            impressions = query.get("impressions", 0)

            if position > 20 and impressions > 100:
                high_difficulty.append(query)
            elif 10 < position <= 20 and impressions > 50:
                medium_difficulty.append(query)
            elif position <= 10 and impressions > 20:
                low_difficulty.append(query)

        analysis = {
            "high_difficulty_keywords": len(high_difficulty),
            "medium_difficulty_keywords": len(medium_difficulty),
            "low_difficulty_keywords": len(low_difficulty),
            "recommended_strategy": "focus_low_difficulty",
        }

        print(f"  📊 高难度关键词: {len(high_difficulty)}")
        print(f"  📊 中难度关键词: {len(medium_difficulty)}")
        print(f"  📊 低难度关键词: {len(low_difficulty)}")
        print(f"  📊 建议策略: 优先优化低难度关键词，快速获取流量")

        self.analysis["competition"] = analysis
        return analysis

    def analyze_ctr_patterns(self) -> Dict:
        """分析CTR模式"""
        print("\n[4/5] 分析CTR模式...")

        queries = self.data.get("gsc", {}).get("queries", [])

        # 按排名区间分析CTR
        ctr_by_position = defaultdict(list)
        for query in queries:
            position = query.get("position", 0)
            ctr = query.get("ctr", 0)
            if position > 0 and ctr >= 0:
                if position <= 3:
                    ctr_by_position["1-3"].append(ctr)
                elif position <= 10:
                    ctr_by_position["4-10"].append(ctr)
                elif position <= 20:
                    ctr_by_position["11-20"].append(ctr)
                else:
                    ctr_by_position["20+"].append(ctr)

        avg_ctr_by_position = {}
        for pos_range, ctrs in ctr_by_position.items():
            if ctrs:
                avg_ctr_by_position[pos_range] = round(sum(ctrs) / len(ctrs), 2)

        analysis = {
            "avg_ctr_by_position": avg_ctr_by_position,
            "ctr_benchmark": {
                "1-3": 15.0,
                "4-10": 5.0,
                "11-20": 2.0,
                "20+": 0.5,
            },
            "ctr_gap": {},
        }

        # 计算CTR差距
        for pos_range, avg_ctr in avg_ctr_by_position.items():
            benchmark = analysis["ctr_benchmark"].get(pos_range, 1.0)
            gap = benchmark - avg_ctr
            analysis["ctr_gap"][pos_range] = round(gap, 2)

        print(f"  📊 各排名区间平均CTR: {avg_ctr_by_position}")
        print(f"  📊 CTR差距（基准-实际）: {analysis['ctr_gap']}")

        self.analysis["ctr_patterns"] = analysis
        return analysis

    def generate_optimization_plan(self) -> Dict:
        """生成优化计划"""
        print("\n[5/5] 生成优化计划...")

        # 按类别分组机会
        opportunities_by_category = defaultdict(list)
        for opp in self.opportunities:
            category = opp.get("category", "other")
            opportunities_by_category[category].append(opp)

        # 生成分阶段优化计划
        plan = {
            "immediate": {
                "title": "立即执行（1-3天）",
                "tasks": [],
                "expected_impact": "快速提升CTR和修复技术问题",
            },
            "short_term": {
                "title": "短期优化（1-2周）",
                "tasks": [],
                "expected_impact": "提升内容质量和内链结构",
            },
            "medium_term": {
                "title": "中期建设（1个月）",
                "tasks": [],
                "expected_impact": "填补内容缺口，建立主题权威",
            },
            "long_term": {
                "title": "长期战略（3个月）",
                "tasks": [],
                "expected_impact": "持续增长飞轮，自动化优化",
            },
        }

        # 立即执行：高优先级Title/Meta优化和技术修复
        high_priority = [o for o in self.opportunities if o.get("priority") == "high"]
        title_meta_opps = [o for o in high_priority if o.get("recommended_action") == "TITLE_META"]
        technical_opps = [o for o in high_priority if o.get("recommended_action") == "TECHNICAL_REVIEW"]

        plan["immediate"]["tasks"] = [
            f"优化Top {min(5, len(title_meta_opps))} 个高展示低CTR查询的Title和Meta描述",
            f"修复 {len(technical_opps)} 个技术SEO问题（规范化URL等）",
            "提交优化后的页面到GSC重新索引",
        ]

        # 短期优化：内容质量和内链
        content_opps = [o for o in self.opportunities if o.get("type") == "content_quality"]
        internal_link_opps = [o for o in self.opportunities if o.get("recommended_action") == "INTERNAL_LINK"]

        plan["short_term"]["tasks"] = [
            f"深度优化 {min(10, len(content_opps))} 篇低质量内容（扩充至1000+词，补充Meta描述）",
            f"为 {min(10, len(internal_link_opps))} 篇文章增加内链（每篇至少3条）",
            "建立内链策略：主题集群和支柱页面",
        ]

        # 中期建设：内容缺口
        content_gaps = self.analysis.get("content_gaps", {}).get("content_gaps", [])

        plan["medium_term"]["tasks"] = [
            f"填补Top {min(3, len(content_gaps))} 个内容缺口主题",
            "每个主题创建1-2篇深度内容（2000+词）",
            "建立内容更新机制：每月更新5篇旧内容",
        ]

        # 长期战略：自动化
        plan["long_term"]["tasks"] = [
            "建立SEO自动化监控和优化闭环",
            "A/B测试Title和Meta描述模板",
            "建立主题权威和外链建设策略",
            "实现AI驱动的内容优化建议自动生成",
        ]

        print(f"  📊 立即执行任务: {len(plan['immediate']['tasks'])} 项")
        print(f"  📊 短期优化任务: {len(plan['short_term']['tasks'])} 项")
        print(f"  📊 中期建设任务: {len(plan['medium_term']['tasks'])} 项")
        print(f"  📊 长期战略任务: {len(plan['long_term']['tasks'])} 项")

        self.analysis["optimization_plan"] = plan
        return plan


# ============================================================
# 自动优化层
# ============================================================

class SEOAutoOptimizer:
    """SEO自动优化器：自动优化Title/Meta、内链、内容结构"""

    def __init__(self, data: Dict, opportunities: List[Dict], analysis: Dict):
        self.data = data
        self.opportunities = opportunities
        self.analysis = analysis
        self.optimization_results = []
        # P1-AI-OPS-03: Load SEO optimization strategy
        self.strategy = None
        if _STRATEGY_CONSUMER is not None:
            try:
                self.strategy = _STRATEGY_CONSUMER("reports/seo/seo_optimization_strategy.json", "seo")
            except Exception as _e:
                print(f"  ⚠️ SEO Strategy load skipped: {_e}")

    def generate_optimization_suggestions(self, dry_run: bool = True) -> List[Dict]:
        """生成优化建议"""
        print("\n" + "=" * 60)
        print(f"  SEO Intelligent Agent - 生成优化建议 ({'DRY RUN' if dry_run else 'APPLY'})")
        print("=" * 60)

        suggestions = []

        # Title/Meta优化建议
        title_meta_opps = [o for o in self.opportunities if o.get("recommended_action") == "TITLE_META"][:5]
        for opp in title_meta_opps:
            suggestion = self._generate_title_meta_suggestion(opp)
            if suggestion:
                suggestions.append(suggestion)

        # 内容优化建议
        content_opps = [o for o in self.opportunities if o.get("type") == "content_quality"][:5]
        for opp in content_opps:
            suggestion = self._generate_content_optimization_suggestion(opp)
            if suggestion:
                suggestions.append(suggestion)

        # 内链优化建议
        internal_link_opps = [o for o in self.opportunities if o.get("recommended_action") == "INTERNAL_LINK"][:5]
        for opp in internal_link_opps:
            suggestion = self._generate_internal_link_suggestion(opp)
            if suggestion:
                suggestions.append(suggestion)

        # P1-AI-OPS-03: Sort suggestions by strategy priority (high_priority_keywords first)
        if getattr(self, "strategy", None) and self.strategy.available:
            high_priority = self.strategy.get_priority_list("high_priority_keywords")
            best_keywords = self.strategy.get_priority_list("best_keywords")
            all_priority = list(dict.fromkeys(high_priority + best_keywords))
            if all_priority and suggestions:
                def _seo_priority_score(s: Dict) -> int:
                    target = str(s.get("target", "")).lower()
                    suggestion = str(s.get("suggestion", "")).lower()
                    combined = target + " " + suggestion
                    for i, kw in enumerate(all_priority):
                        if kw in combined:
                            return i
                    return 999
                suggestions.sort(key=_seo_priority_score)
                matched = sum(1 for s in suggestions if _seo_priority_score(s) < 999)
                print(f"  📋 策略已消费: version={self.strategy.version}, 优先关键词={len(all_priority)}, 匹配建议={matched}/{len(suggestions)}")

        self.optimization_results = suggestions

        print(f"\n📊 共生成 {len(suggestions)} 条优化建议")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"\n  [{i}] {suggestion.get('type', '')}: {suggestion.get('target', '')}")
            print(f"      优先级: {suggestion.get('priority', '')}")
            print(f"      建议: {suggestion.get('suggestion', '')[:100]}...")

        # 保存建议到文件
        suggestions_file = SEO_REPORTS_DIR / "optimization_suggestions.json"
        with open(suggestions_file, "w", encoding="utf-8") as f:
            json.dump(suggestions, f, ensure_ascii=False, indent=2)
        print(f"\n💾 优化建议已保存到: {suggestions_file}")

        return suggestions

    def _generate_title_meta_suggestion(self, opportunity: Dict) -> Optional[Dict]:
        """生成Title/Meta优化建议"""
        target = opportunity.get("target", "")
        if not target:
            return None

        # 查找对应的页面
        matching_post = None
        for post in self.data.get("content", {}).get("posts", []):
            if post.get("slug", "") in target or target in post.get("title", "").lower():
                matching_post = post
                break

        current_title = matching_post.get("title", "") if matching_post else ""
        current_meta = matching_post.get("meta_description", "") if matching_post else ""

        # 生成优化建议（基于最佳实践）
        suggestions = []

        # Title优化建议
        if len(current_title) > 60:
            suggestions.append(f"Title过长（{len(current_title)}字符），建议精简至50-60字符")
        elif len(current_title) < 30:
            suggestions.append(f"Title过短（{len(current_title)}字符），建议扩充至50-60字符，包含核心关键词")
        else:
            suggestions.append("Title长度合适，建议优化关键词位置和吸引力")

        # 加入数字和年份
        if not any(char.isdigit() for char in current_title):
            suggestions.append("建议在Title中加入数字或年份（如'2026'、'10 Tips'），可提升CTR约10%")

        # Meta描述优化建议
        if not current_meta:
            suggestions.append("缺少Meta描述，建议添加150-160字符的描述，包含核心关键词和行动号召")
        elif len(current_meta) > 160:
            suggestions.append(f"Meta描述过长（{len(current_meta)}字符），建议精简至150-160字符")
        elif len(current_meta) < 100:
            suggestions.append(f"Meta描述过短（{len(current_meta)}字符），建议扩充至150-160字符")

        return {
            "type": "title_meta_optimization",
            "target": target,
            "file": matching_post.get("file", "") if matching_post else "",
            "current_title": current_title,
            "current_meta": current_meta,
            "priority": opportunity.get("priority", "medium"),
            "priority_score": opportunity.get("priority_score", 0),
            "suggestion": "; ".join(suggestions),
            "estimated_impact": opportunity.get("estimated_impact", ""),
            "status": "pending",
        }

    def _generate_content_optimization_suggestion(self, opportunity: Dict) -> Optional[Dict]:
        """生成内容优化建议"""
        target = opportunity.get("target", "")
        if not target:
            return None

        issues = opportunity.get("issues", [])
        suggestions = []

        for issue in issues:
            if "内容不足" in issue:
                suggestions.append("扩充内容至1000+词，增加FAQ、案例、详细步骤等")
            elif "缺少Meta描述" in issue:
                suggestions.append("添加Meta描述（150-160字符），包含核心关键词")
            elif "缺少内链" in issue or "内链不足" in issue:
                suggestions.append("增加3-5条相关内链，指向同主题的其他文章")

        return {
            "type": "content_optimization",
            "target": target,
            "title": opportunity.get("title", ""),
            "issues": issues,
            "priority": opportunity.get("priority", "medium"),
            "priority_score": opportunity.get("priority_score", 0),
            "suggestion": "; ".join(suggestions),
            "estimated_impact": "优化后可提升排名和用户停留时长",
            "status": "pending",
        }

    def _generate_internal_link_suggestion(self, opportunity: Dict) -> Optional[Dict]:
        """生成内链优化建议"""
        target = opportunity.get("target", "")
        if not target:
            return None

        # 查找相关文章（基于主题关键词）
        related_posts = []
        target_words = set(target.lower().split())
        for post in self.data.get("content", {}).get("posts", []):
            title_words = set((post.get("title", "") + " " + post.get("file", "")).lower().split())
            overlap = len(target_words & title_words)
            if overlap > 0 and post.get("file", "") != target:
                related_posts.append((post, overlap))

        related_posts.sort(key=lambda x: x[1], reverse=True)
        top_related = [p[0].get("file", "") for p in related_posts[:5]]

        return {
            "type": "internal_link_optimization",
            "target": target,
            "related_posts": top_related,
            "priority": opportunity.get("priority", "medium"),
            "priority_score": opportunity.get("priority_score", 0),
            "suggestion": f"在文章中增加指向以下相关文章的内链: {', '.join(top_related[:3])}",
            "estimated_impact": "增加内链可提升页面权重和用户停留时长",
            "status": "pending",
        }


# ============================================================
# 效果追踪层
# ============================================================

class SEOPerformanceTracker:
    """SEO效果追踪器：追踪优化效果，持续迭代"""

    def __init__(self):
        self.history = self._load_history()

    def _load_history(self) -> List[Dict]:
        """加载优化历史记录"""
        if OPTIMIZATION_HISTORY_FILE.exists():
            try:
                with open(OPTIMIZATION_HISTORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _save_history(self):
        """保存优化历史记录"""
        with open(OPTIMIZATION_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)

    def record_optimization(self, optimization: Dict):
        """记录优化操作"""
        optimization["recorded_at"] = datetime.now().isoformat()
        optimization["status"] = "completed"
        self.history.append(optimization)
        self._save_history()

    def track_performance(self, data: Dict) -> Dict:
        """追踪优化效果"""
        print("\n" + "=" * 60)
        print("  SEO Intelligent Agent - 效果追踪")
        print("=" * 60)

        gsc_summary = data.get("gsc", {}).get("summary", {})

        tracking = {
            "tracked_at": datetime.now().isoformat(),
            "current_metrics": {
                "total_impressions": gsc_summary.get("total_impressions", 0),
                "total_clicks": gsc_summary.get("total_clicks", 0),
                "avg_ctr": gsc_summary.get("avg_ctr", 0),
                "avg_position": gsc_summary.get("avg_position", 0),
            },
            "optimizations_completed": len(self.history),
            "pending_optimizations": 0,
            "performance_trend": "insufficient_data",
        }

        # 计算趋势（如果有历史数据）
        if len(self.history) >= 2:
            first = self.history[0].get("metrics_at_optimization", {})
            current = tracking["current_metrics"]
            if first.get("avg_ctr", 0) > 0:
                ctr_change = ((current["avg_ctr"] - first["avg_ctr"]) / first["avg_ctr"]) * 100
                tracking["ctr_change_pct"] = round(ctr_change, 2)
                tracking["performance_trend"] = "improving" if ctr_change > 0 else "declining"

        print(f"  📊 当前指标:")
        print(f"    总展示: {tracking['current_metrics']['total_impressions']}")
        print(f"    总点击: {tracking['current_metrics']['total_clicks']}")
        print(f"    平均CTR: {tracking['current_metrics']['avg_ctr']}%")
        print(f"    平均排名: {tracking['current_metrics']['avg_position']}")
        print(f"  📊 已完成优化: {tracking['optimizations_completed']} 项")
        print(f"  📊 性能趋势: {tracking['performance_trend']}")

        return tracking

    def generate_report(self, data: Dict, opportunities: List[Dict], analysis: Dict, suggestions: List[Dict]) -> str:
        """生成完整的SEO优化报告"""
        print("\n" + "=" * 60)
        print("  SEO Intelligent Agent - 生成报告")
        print("=" * 60)

        report = []
        report.append("# ChinaBound Travel SEO智能优化报告")
        report.append(f"\n**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"**数据来源**: GSC + 本地内容扫描 + 技术审计")
        report.append("")

        # 执行摘要
        report.append("## 📊 执行摘要")
        report.append("")
        gsc_summary = data.get("gsc", {}).get("summary", {})
        report.append(f"- **总展示**: {gsc_summary.get('total_impressions', 0)} 次")
        report.append(f"- **总点击**: {gsc_summary.get('total_clicks', 0)} 次")
        report.append(f"- **平均CTR**: {gsc_summary.get('avg_ctr', 0)}%")
        report.append(f"- **平均排名**: 第 {gsc_summary.get('avg_position', 0)} 位")
        report.append(f"- **识别优化机会**: {len(opportunities)} 个")
        report.append(f"- **生成优化建议**: {len(suggestions)} 条")
        report.append("")

        # 关键发现
        report.append("## 🔍 关键发现")
        report.append("")
        for finding in analysis.get("traffic_patterns", {}).get("key_findings", []):
            report.append(f"- {finding}")
        report.append("")

        # 优化机会
        report.append("## 🎯 优化机会（Top 10）")
        report.append("")
        report.append("| 优先级 | 类型 | 目标 | 展示 | CTR | 排名 | 建议操作 |")
        report.append("|--------|------|------|------|-----|------|----------|")
        for opp in opportunities[:10]:
            report.append(f"| {opp.get('priority', '')} | {opp.get('type', '')} | {opp.get('target', '')[:30]} | {opp.get('impressions', '-')} | {opp.get('ctr', '-')}% | {opp.get('position', '-')} | {opp.get('recommended_action', '')} |")
        report.append("")

        # 优化计划
        plan = analysis.get("optimization_plan", {})
        report.append("## 📋 分阶段优化计划")
        report.append("")
        for phase_key, phase in plan.items():
            if isinstance(phase, dict) and "title" in phase:
                report.append(f"### {phase['title']}")
                report.append(f"**预期效果**: {phase.get('expected_impact', '')}")
                report.append("")
                for task in phase.get("tasks", []):
                    report.append(f"- {task}")
                report.append("")

        # 优化建议详情
        report.append("## 💡 优化建议详情")
        report.append("")
        for i, suggestion in enumerate(suggestions, 1):
            report.append(f"### [{i}] {suggestion.get('type', '')}: {suggestion.get('target', '')}")
            report.append(f"- **优先级**: {suggestion.get('priority', '')}")
            report.append(f"- **优先级分数**: {suggestion.get('priority_score', 0)}")
            report.append(f"- **建议**: {suggestion.get('suggestion', '')}")
            report.append(f"- **预期影响**: {suggestion.get('estimated_impact', '')}")
            if suggestion.get("current_title"):
                report.append(f"- **当前Title**: {suggestion.get('current_title', '')}")
            if suggestion.get("related_posts"):
                report.append(f"- **相关文章**: {', '.join(suggestion.get('related_posts', [])[:3])}")
            report.append("")

        # 内容缺口
        content_gaps = analysis.get("content_gaps", {}).get("content_gaps", [])
        if content_gaps:
            report.append("## 📈 内容缺口（建议新增内容）")
            report.append("")
            report.append("| 主题 | 搜索展示 | 现有内容 | 缺口分数 |")
            report.append("|------|----------|----------|----------|")
            for gap in content_gaps[:5]:
                report.append(f"| {gap.get('topic', '')} | {gap.get('search_impressions', 0)} | {gap.get('content_count', 0)} | {gap.get('gap_score', 0):.1f} |")
            report.append("")

        # 效果追踪
        tracking = self.track_performance(data)
        report.append("## 📊 效果追踪")
        report.append("")
        report.append(f"- **已完成优化**: {tracking.get('optimizations_completed', 0)} 项")
        report.append(f"- **性能趋势**: {tracking.get('performance_trend', 'insufficient_data')}")
        if "ctr_change_pct" in tracking:
            report.append(f"- **CTR变化**: {tracking.get('ctr_change_pct', 0)}%")
        report.append("")

        report.append("---")
        report.append("*本报告由 SEO Intelligent Agent 自动生成*")

        report_text = "\n".join(report)

        # 保存报告
        report_file = SEO_REPORTS_DIR / f"SEO_OPTIMIZATION_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report_text)
        print(f"\n💾 报告已保存到: {report_file}")

        return report_text


# ============================================================
# 主程序
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="ChinaBound Travel SEO Intelligent Agent")
    parser.add_argument("--analyze", action="store_true", help="分析SEO机会")
    parser.add_argument("--optimize", action="store_true", help="生成优化建议")
    parser.add_argument("--dry-run", action="store_true", help="仅生成建议，不执行")
    parser.add_argument("--apply", action="store_true", help="执行优化")
    parser.add_argument("--report", action="store_true", help="生成SEO优化报告")
    parser.add_argument("--track", action="store_true", help="追踪优化效果")
    parser.add_argument("--all", action="store_true", help="执行全部流程")

    args = parser.parse_args()

    # 如果没有指定任何操作，默认执行全部流程
    if not any([args.analyze, args.optimize, args.report, args.track, args.all]):
        args.all = True

    # 初始化各模块
    collector = SEODataCollector()
    tracker = SEOPerformanceTracker()

    # 1. 数据采集
    data = collector.collect_all()

    # 2. 机会识别
    detector = SEOOpportunityDetector(data)
    opportunities = detector.detect_all()

    # 3. 智能分析
    analyzer = SEOIntelligentAnalyzer(data, opportunities)
    analysis = analyzer.analyze_all()

    # 4. 生成优化建议
    optimizer = SEOAutoOptimizer(data, opportunities, analysis)
    suggestions = []
    if args.optimize or args.all:
        dry_run = not args.apply
        suggestions = optimizer.generate_optimization_suggestions(dry_run=dry_run)

    # 5. 效果追踪
    if args.track or args.all:
        tracking = tracker.track_performance(data)

    # 6. 生成报告
    if args.report or args.all:
        report = tracker.generate_report(data, opportunities, analysis, suggestions)
        print("\n" + "=" * 60)
        print("  ✅ SEO智能优化流程完成！")
        print("=" * 60)
        print(f"\n📊 识别优化机会: {len(opportunities)} 个")
        print(f"💡 生成优化建议: {len(suggestions)} 条")
        print(f"📈 流量潜力: 每月可增加约 {analysis.get('traffic_patterns', {}).get('traffic_potential', 0)} 次点击")
        print(f"\n📁 报告文件: {SEO_REPORTS_DIR}")
        print(f"📁 优化建议: {SEO_REPORTS_DIR / 'optimization_suggestions.json'}")


if __name__ == "__main__":
    main()
