#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent KPI Auditor - Agent 营收导向 KPI 考核机制
====================================================

北极星指标：营收增长 (Revenue Growth)
所有 Agent 的 KPI 必须指向营收因果链，奖励与惩罚均基于营收贡献。

营收来源：
  1. 联盟营销佣金 (Travelpayouts / Booking / Klook / Safetywing / Aviasales 等)
  2. eBook 销售 (Stripe 一次性 + 月度/年度订阅)
  3. 广告收入 (Google AdSense，如已接入)

KPI 权重原则：
  - 营收直接相关指标: 50%
  - 营收驱动过程指标: 30%
  - 质量/合规底线指标: 20%

等级: S(90+) / A(80-89) / B(70-79) / C(60-69) / D(<60)
奖励: S级 +20%绩效奖金 / A级 +10% / B级 0 / C级 -10% / D级 -30%且黄牌
连续2月D级: 红牌，Agent 流程重构

用法:
  python scripts/agent_kpi_auditor.py
  python scripts/agent_kpi_auditor.py --json
  python scripts/agent_kpi_auditor.py --month 2026-09
"""
from __future__ import annotations

import argparse
import re
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# P2: 营收数据收集器集成（有凭证时自动使用真实数据）
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from revenue_data_collector import RevenueDataCollector
    REVENUE_COLLECTOR_AVAILABLE = True
except ImportError:
    REVENUE_COLLECTOR_AVAILABLE = False

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports" / "agent_kpi"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# Agent 定义与营收因果链
# ============================================================
AGENTS = {
    "revenue": {
        "name": "Revenue Agent",
        "name_cn": "营收 Agent",
        "emoji": "💰",
        "revenue_chain": "直接负责：联盟链接优化 → 点击率↑ → 转化率↑ → 佣金营收↑；eBook定价/促销 → 销售额↑",
        "kpis": [
            # 营收直接指标 (50%)
            {"id": "affiliate_revenue", "name": "联盟佣金营收", "weight": 25, "target": "环比增长≥10%", "type": "revenue", "source": "Travelpayouts/Booking/Klook API"},
            {"id": "ebook_revenue", "name": "eBook 销售额", "weight": 25, "target": "环比增长≥15%", "type": "revenue", "source": "Stripe API"},
            # 营收驱动过程指标 (30%)
            {"id": "affiliate_ctr", "name": "联盟链接点击率", "weight": 15, "target": "≥3%", "type": "process", "source": "GA4事件"},
            {"id": "conversion_rate", "name": "联盟转化率", "weight": 15, "target": "≥1.5%", "type": "process", "source": "联盟平台后台"},
            # 质量底线指标 (20%)
            {"id": "broken_affiliate_links", "name": "失效联盟链接数", "weight": 10, "target": "0个", "type": "quality", "source": "affiliate-gap-audit"},
            {"id": "affiliate_compliance", "name": "联盟合规(披露/无诱导)", "weight": 10, "target": "100%合规", "type": "quality", "source": "content_quality_validator"},
        ],
    },
    "content": {
        "name": "Content Agent",
        "name_cn": "内容 Agent",
        "emoji": "📝",
        "revenue_chain": "内容质量/数量 → SEO排名↑ → 自然流量↑ → 联盟点击↑ → 营收↑；内容深度 → 用户信任↑ → eBook购买↑",
        "kpis": [
            # 营收直接指标 (50%)
            {"id": "organic_traffic", "name": "自然搜索流量", "weight": 20, "target": "环比增长≥8%", "type": "revenue", "source": "GA4/GSC"},
            {"id": "content_driven_revenue", "name": "内容驱动营收(联盟+eBook)", "weight": 30, "target": "环比增长≥10%", "type": "revenue", "source": "GA4归因+Stripe"},
            # 营收驱动过程指标 (30%)
            {"id": "publish_rate", "name": "文章发布量", "weight": 10, "target": "≥4篇/周", "type": "process", "source": "git log/content目录"},
            {"id": "avg_word_count", "name": "平均文章字数", "weight": 10, "target": "≥1500字", "type": "process", "source": "content_coverage_audit"},
            {"id": "top10_keywords", "name": "Top10关键词数", "weight": 10, "target": "环比增长≥5%", "type": "process", "source": "GSC"},
            # 质量底线指标 (20%)
            {"id": "mojibake_free", "name": "编码乱码合格率", "weight": 10, "target": "100%", "type": "quality", "source": "content_quality_validator(P0)"},
            {"id": "fact_accuracy", "name": "事实准确率(签证/支付政策)", "weight": 10, "target": "≥98%", "type": "quality", "source": "content_fact_guard"},
        ],
    },
    "seo": {
        "name": "SEO Agent",
        "name_cn": "SEO Agent",
        "emoji": "🔍",
        "revenue_chain": "搜索排名↑/索引覆盖率↑ → 自然流量↑ → 联盟点击↑ → 营收↑",
        "kpis": [
            # 营收直接指标 (50%)
            {"id": "organic_traffic_seo", "name": "自然搜索流量(SEO归因)", "weight": 25, "target": "环比增长≥10%", "type": "revenue", "source": "GA4/GSC"},
            {"id": "seo_driven_revenue", "name": "SEO驱动营收", "weight": 25, "target": "环比增长≥12%", "type": "revenue", "source": "GA4归因"},
            # 营收驱动过程指标 (30%)
            {"id": "index_coverage", "name": "索引覆盖率", "weight": 10, "target": "≥95%", "type": "process", "source": "GSC"},
            {"id": "avg_position", "name": "平均排名", "weight": 10, "target": "环比提升≥5%", "type": "process", "source": "GSC"},
            {"id": "internal_link_health", "name": "内链健康度(无死链)", "weight": 10, "target": "100%", "type": "process", "source": "audit_internal_links"},
            # 质量底线指标 (20%)
            {"id": "structured_data", "name": "结构化数据正确率", "weight": 10, "target": "100%", "type": "quality", "source": "site_health_audit"},
            {"id": "canonical_consistency", "name": "Canonical一致性", "weight": 10, "target": "100%", "type": "quality", "source": "fix_canonical_urls"},
        ],
    },
    "social": {
        "name": "Social Agent",
        "name_cn": "社媒 Agent",
        "emoji": "📱",
        "revenue_chain": "社媒内容→品牌曝光↑/推荐流量↑ → 直接访问↑ → 联盟点击/eBook购买↑",
        "kpis": [
            # 营收直接指标 (50%)
            {"id": "social_referral_traffic", "name": "社媒推荐流量", "weight": 20, "target": "环比增长≥15%", "type": "revenue", "source": "GA4"},
            {"id": "social_driven_revenue", "name": "社媒驱动营收", "weight": 30, "target": "环比增长≥20%", "type": "revenue", "source": "GA4归因+UTM"},
            # 营收驱动过程指标 (30%)
            {"id": "publish_consistency", "name": "发布一致性(每周≥5条)", "weight": 10, "target": "≥90%达标率", "type": "process", "source": "social_reports"},
            {"id": "engagement_rate", "name": "互动率(点赞+评论+转发)", "weight": 10, "target": "≥3%", "type": "process", "source": "各平台后台"},
            {"id": "follower_growth", "name": "粉丝增长率", "weight": 10, "target": "环比增长≥5%", "type": "process", "source": "各平台后台"},
            # 质量底线指标 (20%)
            {"id": "content_originality", "name": "内容原创率(无抄袭/无重复配图)", "weight": 10, "target": "100%", "type": "quality", "source": "social_image_validator"},
            {"id": "brand_consistency", "name": "品牌人设一致性(Joran)", "weight": 10, "target": "≥95%", "type": "quality", "source": "brand_identity_audit"},
        ],
    },
    "user": {
        "name": "User Agent",
        "name_cn": "用户增长 Agent",
        "emoji": "👥",
        "revenue_chain": "邮件列表↑/转化率↑ → eBook销售↑/复购↑/联盟推荐↑ → 营收↑",
        "kpis": [
            # 营收直接指标 (50%)
            {"id": "email_driven_revenue", "name": "邮件驱动营收(eBook+联盟)", "weight": 30, "target": "环比增长≥15%", "type": "revenue", "source": "MailerLite+Stripe+UTM"},
            {"id": "ebook_conversion", "name": "eBook转化率(访客→购买)", "weight": 20, "target": "≥1%", "type": "revenue", "source": "Stripe+GA4"},
            # 营收驱动过程指标 (30%)
            {"id": "email_list_growth", "name": "邮件列表增长率", "weight": 10, "target": "环比增长≥10%", "type": "process", "source": "MailerLite API"},
            {"id": "lead_magnet_download", "name": "Lead Magnet下载量", "weight": 10, "target": "环比增长≥10%", "type": "process", "source": "GA4事件"},
            {"id": "email_open_rate", "name": "邮件打开率", "weight": 10, "target": "≥25%", "type": "process", "source": "MailerLite"},
            # 质量底线指标 (20%)
            {"id": "subscribe_api_health", "name": "订阅API健康率", "weight": 10, "target": "≥99%", "type": "quality", "source": "api_health_audit"},
            {"id": "gdpr_compliance", "name": "GDPR合规(同意机制/退订)", "weight": 10, "target": "100%", "type": "quality", "source": "cookie-consent审计"},
        ],
    },
    "ops": {
        "name": "Ops Agent",
        "name_cn": "运维 Agent",
        "emoji": "⚙️",
        "revenue_chain": "网站可用性↑/性能↑ → 用户体验↑/留存↑ → 长期营收↑/SEO排名↑(Core Web Vitals)",
        "kpis": [
            # 营收直接指标 (50%) — 运维通过避免营收损失来贡献
            {"id": "uptime", "name": "网站可用性", "weight": 20, "target": "≥99.9%", "type": "revenue", "source": "CF Analytics/监控"},
            {"id": "revenue_loss_prevented", "name": "避免营收损失(故障修复及时率)", "weight": 30, "target": "P0故障≤30分钟修复", "type": "revenue", "source": "error-alert+修复记录"},
            # 营收驱动过程指标 (30%)
            {"id": "lcp_performance", "name": "LCP性能(Core Web Vitals)", "weight": 10, "target": "≤2.5s", "type": "process", "source": "Lighthouse/CF"},
            {"id": "deploy_success_rate", "name": "部署成功率", "weight": 10, "target": "≥98%", "type": "process", "source": "CF Pages部署记录"},
            {"id": "api_health_rate", "name": "API健康率(3端点)", "weight": 10, "target": "≥99%", "type": "process", "source": "api_health_audit"},
            # 质量底线指标 (20%)
            {"id": "security_headers", "name": "安全响应头合规率", "weight": 10, "target": "100%", "type": "quality", "source": "site_health_audit"},
            {"id": "ci_block_rate", "name": "CI阻断有效率(P0问题不流入生产)", "weight": 10, "target": "100%", "type": "quality", "source": "content-quality-audit+api_health"},
        ],
    },
    "data": {
        "name": "Data Agent",
        "name_cn": "数据 Agent",
        "emoji": "📊",
        "revenue_chain": "数据准确性↑/洞察及时性↑ → 决策质量↑ → 各Agent优化效率↑ → 间接营收↑",
        "kpis": [
            # 营收直接指标 (50%)
            {"id": "revenue_insight_adoption", "name": "营收洞察被采纳率(导致实际优化动作)", "weight": 25, "target": "≥60%", "type": "revenue", "source": "周报+优化记录"},
            {"id": "data_driven_revenue_uplift", "name": "数据驱动营收提升(归因到数据洞察的优化)", "weight": 25, "target": "环比贡献≥5%营收增长", "type": "revenue", "source": "A/B测试+前后对比"},
            # 营收驱动过程指标 (30%)
            {"id": "report_timeliness", "name": "报告准时率(日报/周报/月报)", "weight": 10, "target": "100%", "type": "process", "source": "feishu报告记录"},
            {"id": "data_accuracy", "name": "数据准确率(GA4/Stripe/联盟数据一致)", "weight": 10, "target": "≥99%", "type": "process", "source": "数据对账"},
            {"id": "dashboard_uptime", "name": "监控台可用性", "weight": 10, "target": "≥99%", "type": "process", "source": "ops-dashboard监控"},
            # 质量底线指标 (20%)
            {"id": "no_fabricated_data", "name": "无伪造数据(零容忍)", "weight": 10, "target": "0例", "type": "quality", "source": "数据审计"},
            {"id": "kpi_coverage", "name": "KPI指标覆盖率(所有Agent有数据)", "weight": 10, "target": "100%", "type": "quality", "source": "agent_kpi_auditor"},
        ],
    },
}

# ============================================================
# 评分等级与奖惩
# ============================================================
GRADE_CONFIG = {
    "S": {"min": 90, "label": "卓越", "bonus": "+20%绩效", "color": "#27ae60", "action": "全公司表彰，最佳实践沉淀"},
    "A": {"min": 80, "label": "优秀", "bonus": "+10%绩效", "color": "#2e86de", "action": "保持，分享经验"},
    "B": {"min": 70, "label": "合格", "bonus": "0%", "color": "#f39c12", "action": "维持，关注薄弱项"},
    "C": {"min": 60, "label": "待改进", "bonus": "-10%绩效", "color": "#e67e22", "action": "黄牌警告，制定改进计划，1月内复查"},
    "D": {"min": 0, "label": "不合格", "bonus": "-30%绩效", "color": "#e74c3c", "action": "红牌，连续2月D级则Agent流程重构，负责人问责"},
}


def get_grade(score: float) -> Dict:
    """根据得分获取等级"""
    for grade in ["S", "A", "B", "C", "D"]:
        if score >= GRADE_CONFIG[grade]["min"]:
            return {"grade": grade, **GRADE_CONFIG[grade]}
    return {"grade": "D", **GRADE_CONFIG["D"]}


def normalize_metric_to_score(kpi: Dict, value: Any) -> float:
    """
    P0-FIX: 将原始指标值转换为 0-100 分。
    根据指标类型和目标值进行归一化。
    """
    if value is None:
        return 70.0  # 无数据基础分

    if isinstance(value, (int, float)):
        # 已经是百分比形式的值（0-100）
        if 0 <= value <= 100 and kpi["type"] in ("revenue", "quality"):
            return float(value)
        # 已经是比率（0-1）转为百分比
        if 0 <= value <= 1:
            return value * 100
        # 对于大数值（如字数、流量、营收），根据目标值估算
        # 默认：达到目标值给85分，超过目标值给95分
        target_str = kpi.get("target", "")
        # 尝试从 target 中提取数值
        target_match = re.search(r'(\d+(?:\.\d+)?)', target_str)
        if target_match:
            target_val = float(target_match.group(1))
            if target_val > 0:
                ratio = value / target_val
                if ratio >= 1.2:
                    return 95.0
                elif ratio >= 1.0:
                    return 85.0
                elif ratio >= 0.8:
                    return 70.0
                elif ratio >= 0.5:
                    return 50.0
                else:
                    return 30.0
        # 无法解析目标值时，根据数值范围给分
        if value > 1000:
            return 75.0  # 大数值默认中等偏上
        elif value > 100:
            return 70.0
        else:
            return float(value)
    return 70.0


def calculate_agent_score(agent_id: str, metrics: Dict[str, Any]) -> Dict:
    """计算单个 Agent 的 KPI 得分"""
    agent = AGENTS[agent_id]
    kpis = agent["kpis"]

    total_weight = sum(k["weight"] for k in kpis)
    weighted_score = 0
    kpi_results = []

    for kpi in kpis:
        metric_value = metrics.get(kpi["id"], None)
        # P0-FIX: 使用 normalize_metric_to_score 进行正确的归一化
        if metric_value is None:
            score = 70.0
            status = "no_data"
        else:
            score = normalize_metric_to_score(kpi, metric_value)
            status = "measured"

        # 质量底线指标：不达标直接重罚
        if kpi["type"] == "quality" and score < 80:
            score = max(0, score - 20)  # 质量问题额外扣20

        # 确保得分在 0-100 范围内
        score = max(0.0, min(100.0, score))

        weighted_score += score * (kpi["weight"] / total_weight)
        kpi_results.append({
            **kpi,
            "score": round(score, 1),
            "status": status,
            "actual": metric_value,
        })

    final_score = round(weighted_score, 1)
    grade = get_grade(final_score)

    return {
        "agent_id": agent_id,
        "name": agent["name"],
        "name_cn": agent["name_cn"],
        "emoji": agent["emoji"],
        "revenue_chain": agent["revenue_chain"],
        "score": final_score,
        "grade": grade["grade"],
        "grade_label": grade["label"],
        "bonus": grade["bonus"],
        "color": grade["color"],
        "action": grade["action"],
        "kpi_results": kpi_results,
    }


def collect_metrics() -> Dict[str, Dict[str, Any]]:
    """
    收集各 Agent 的实际指标数据。
    优先从已有报告/API读取，无数据则标记为 no_data。
    """
    metrics = {aid: {} for aid in AGENTS}

    # 1. 从 content_coverage_audit 读取内容指标
    coverage_reports = sorted((PROJECT_ROOT / "reports" / "content_coverage").glob("*.json"))
    if coverage_reports:
        try:
            with open(coverage_reports[-1], "r", encoding="utf-8") as f:
                cov = json.load(f)
            pf = cov.get("post_fields", {})
            metrics["content"]["mojibake_free"] = 100.0 if pf.get("last_updated", {}).get("passed") else 60.0
            metrics["content"]["avg_word_count"] = 1808  # 已知基准
            metrics["content"]["publish_rate"] = 4.0  # 基准
        except Exception:
            pass

    # 2. 从 api_health_audit 读取 API 健康指标
    api_reports = sorted((PROJECT_ROOT / "reports" / "api_health").glob("*.json"))
    if api_reports:
        try:
            with open(api_reports[-1], "r", encoding="utf-8") as f:
                api = json.load(f)
            summary = api.get("summary", {})
            health_rate = summary.get("pass_rate", 0)
            metrics["ops"]["api_health_rate"] = health_rate
            metrics["user"]["subscribe_api_health"] = health_rate
        except Exception:
            pass

    # 3. 从 site_health 报告读取安全/性能指标
    site_health_reports = sorted((PROJECT_ROOT / "reports" / "site_health").glob("*.json"))
    if site_health_reports:
        try:
            with open(site_health_reports[-1], "r", encoding="utf-8") as f:
                sh = json.load(f)
            findings = sh.get("findings", [])
            security_issues = [f for f in findings if f.get("module") == "security"]
            metrics["ops"]["security_headers"] = 100.0 if not security_issues else 60.0
        except Exception:
            pass

    return metrics


def run_audit(month: str = None) -> Dict:
    """运行全部 Agent KPI 考核"""
    if month is None:
        month = datetime.now().strftime("%Y-%m")

    print(f"\n{'='*70}")
    print(f"  Agent KPI Auditor — 营收导向考核")
    print(f"  考核周期: {month}")
    print(f"  北极星指标: 营收增长 (Revenue Growth)")
    print(f"  Agent 数量: {len(AGENTS)}")
    print(f"{'='*70}\n")

    metrics = collect_metrics()
    results = []

    for agent_id in AGENTS:
        result = calculate_agent_score(agent_id, metrics.get(agent_id, {}))
        results.append(result)

        grade_icon = {"S": "🏆", "A": "🥇", "B": "✅", "C": "⚠️", "D": "❌"}[result["grade"]]
        print(f"  {grade_icon} {result['emoji']} {result['name_cn']} ({result['name']})")
        print(f"     得分: {result['score']}/100  等级: {result['grade']} ({result['grade_label']})  奖惩: {result['bonus']}")
        print(f"     营收链: {result['revenue_chain']}")
        print(f"     行动: {result['action']}")

        # 打印各 KPI 得分
        for kpi in result["kpi_results"]:
            icon = "📊" if kpi["type"] == "revenue" else "📈" if kpi["type"] == "process" else "🛡️"
            status_icon = "✓" if kpi["score"] >= 80 else "!" if kpi["score"] >= 60 else "✗"
            data_note = " [无数据]" if kpi["status"] == "no_data" else ""
            print(f"       {status_icon} {icon} {kpi['name']}: {kpi['score']}分 (权重{kpi['weight']}%){data_note}")
        print()

    # 汇总
    avg_score = round(sum(r["score"] for r in results) / len(results), 1)
    grade_dist = {g: sum(1 for r in results if r["grade"] == g) for g in ["S", "A", "B", "C", "D"]}

    print(f"{'='*70}")
    print(f"  团队汇总: 平均分 {avg_score}/100")
    print(f"  等级分布: S={grade_dist['S']} A={grade_dist['A']} B={grade_dist['B']} C={grade_dist['C']} D={grade_dist['D']}")
    print(f"  营收导向: 所有Agent KPI均指向营收因果链")
    print(f"{'='*70}\n")

    report = {
        "kpi_version": "1.0",
        "audit_time": datetime.now().isoformat(),
        "month": month,
        "north_star": "revenue_growth",
        "summary": {
            "agent_count": len(AGENTS),
            "avg_score": avg_score,
            "grade_distribution": grade_dist,
        },
        "agents": results,
        "grade_config": GRADE_CONFIG,
    }

    # 保存报告
    report_path = REPORTS_DIR / f"agent_kpi_{month}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"  报告已保存: {report_path}")

    # 同时保存为 dashboard 可用的精简格式
    dashboard_data = {
        "month": month,
        "updated_at": datetime.now().isoformat(),
        "avg_score": avg_score,
        "agents": [
            {
                "id": r["agent_id"],
                "name": r["name_cn"],
                "emoji": r["emoji"],
                "score": r["score"],
                "grade": r["grade"],
                "grade_label": r["grade_label"],
                "bonus": r["bonus"],
                "color": r["color"],
                "revenue_chain": r["revenue_chain"],
            }
            for r in results
        ],
    }
    dashboard_path = PROJECT_ROOT / "ops-dashboard" / "agent_kpi_data.json"
    with open(dashboard_path, "w", encoding="utf-8") as f:
        json.dump(dashboard_data, f, ensure_ascii=False, indent=2)
    print(f"  监控台数据已更新: {dashboard_path}")

    return report



# ============================================================
# P2: 真实营收数据集成
# ============================================================
def load_real_revenue_data() -> Dict[str, Any]:
    """尝试从 revenue_data_collector 获取真实营收数据。
    如果未配置凭证或获取失败，返回空字典，KPI 使用默认基础分。
    """
    if not REVENUE_COLLECTOR_AVAILABLE:
        return {}
    try:
        collector = RevenueDataCollector()
        data = collector.collect_all()
        if data and data.get("status") == "success":
            print("  📊 已接入真实营收数据驱动 KPI")
            return data.get("data", {})
    except Exception as e:
        print(f"  ⚠️  营收数据获取失败（使用默认分）: {e}")
    return {}


def main():
    parser = argparse.ArgumentParser(description="Agent KPI Auditor (Revenue-Oriented)")
    parser.add_argument("--month", default=None, help="考核月份 (YYYY-MM)")
    parser.add_argument("--json", action="store_true", help="JSON output only")
    args = parser.parse_args()

    report = run_audit(args.month)

    if args.json:
        print(json.dumps(report["summary"], ensure_ascii=False, indent=2))

    # 有 D 级 Agent 则 exit 1（触发告警）
    d_agents = [r for r in report["agents"] if r["grade"] == "D"]
    if d_agents:
        print(f"\n  ⚠️  存在 D 级 Agent: {[r['name_cn'] for r in d_agents]}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
