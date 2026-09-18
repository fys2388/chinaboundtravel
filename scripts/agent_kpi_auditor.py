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
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

# 无数据 KPI 的占位分。刻意不给 0（会让所有 Agent 塌成 D，掩盖真正的问题分布），
# 也不能给 100（等于给没数据的项发满分）。70 是中性的「未知」先验。
# 代价是它给分数加了 70 分的底，所以必须同时报出每个 Agent 的数据覆盖率和
# 由此决定的分数上限（见 calculate_agent_score），否则读者会把占位分当成绩效。
NO_DATA_BASE_SCORE = 70.0

# P2: 营收数据收集器集成（有凭证时自动使用真实数据）
# 该模块只导出函数（load_env / check_config / collect_all），没有 RevenueDataCollector 类。
# 旧代码 import 一个不存在的类 → ImportError 被下面静默吞掉 →
# REVENUE_COLLECTOR_AVAILABLE 恒为 False → load_real_revenue_data() 恒返回 {}
# → KPI 从未接入过真实营收。改为导入模块本体，走真实函数 API。
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import revenue_data_collector as _rdc
    REVENUE_COLLECTOR_AVAILABLE = True
except ImportError:
    REVENUE_COLLECTOR_AVAILABLE = False

# SEO 结构化数据审计。同样只导函数（audit / main），导入模块本体。
try:
    import seo_structured_data_audit as _sd_audit
    STRUCTURED_DATA_AUDIT_AVAILABLE = True
except ImportError:
    STRUCTURED_DATA_AUDIT_AVAILABLE = False

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
            # unit 声明值量纲，归一化按它分派。不声明就走旧启发式（向后兼容）。
            # currency = 绝对金额（美元）；目标是环比增长，两者不同口径。
            {"id": "affiliate_revenue", "name": "联盟佣金营收", "weight": 25, "target": "环比增长≥10%", "type": "revenue", "unit": "currency", "source": "Travelpayouts/Booking/Klook API"},
            {"id": "ebook_revenue", "name": "eBook 销售额", "weight": 25, "target": "环比增长≥15%", "type": "revenue", "unit": "currency", "source": "Stripe API"},
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
            # unit 必须声明：这两个 KPI 的 type 是 revenue，而 _legacy_normalize
            # 对 revenue 走 `0 <= value <= 100 → return value`。环比变化是
            # 百分比，+8% 会直接得 8 分——增长达标却拿不及格分。
            # 声明 pct 后走 _ratio_ladder(value, target_val)，语义才对。
            {"id": "organic_traffic", "name": "自然搜索流量", "weight": 20, "target": "环比增长≥8%", "type": "revenue", "unit": "pct", "source": "GA4/GSC"},
            {"id": "content_driven_revenue", "name": "内容驱动营收(联盟+eBook)", "weight": 30, "target": "环比增长≥10%", "type": "revenue", "unit": "currency", "source": "GA4归因+Stripe"},
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
            # 同 organic_traffic：必须声明 unit，否则 revenue 类型走
            # legacy 的 `0 <= value <= 100 → return value`，+10% 只得 10 分。
            {"id": "organic_traffic_seo", "name": "自然搜索流量(SEO归因)", "weight": 25, "target": "环比增长≥10%", "type": "revenue", "unit": "pct", "source": "GA4/GSC"},
            {"id": "seo_driven_revenue", "name": "SEO驱动营收", "weight": 25, "target": "环比增长≥12%", "type": "revenue", "unit": "currency", "source": "GA4归因"},
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
            {"id": "social_driven_revenue", "name": "社媒驱动营收", "weight": 30, "target": "环比增长≥20%", "type": "revenue", "unit": "currency", "source": "GA4归因+UTM"},
            # 营收驱动过程指标 (30%)
            {"id": "publish_consistency", "name": "发布一致性(每周≥5条)", "weight": 10, "target": "≥90%达标率", "type": "process", "source": "social_reports"},
            {"id": "engagement_rate", "name": "互动率(点赞+评论+转发)", "weight": 10, "target": "≥3%", "type": "process", "unit": "ratio", "source": "各平台后台"},
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
            {"id": "email_driven_revenue", "name": "邮件驱动营收(eBook+联盟)", "weight": 30, "target": "环比增长≥15%", "type": "revenue", "unit": "currency", "source": "MailerLite+Stripe+UTM"},
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
            # seconds 且越小越好：目标是「≤2.5s」，实际 3.0s 是更差而不是更好。
            {"id": "lcp_performance", "name": "LCP性能(Core Web Vitals)", "weight": 10, "target": "≤2.5s", "type": "process", "unit": "seconds", "source": "Lighthouse/CF"},
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


def _ratio_ladder(value: float, target_val: float, lower_is_better: bool = False) -> float:
    """按「实际值相对目标值」的达标程度给分。

    lower_is_better=True 用于 LCP 这类越小越好的指标：目标 ≤2.5s，
    实际 2.0s 是达标（目标的 0.8 倍），实际 5.0s 是两倍超标。
    没有目标值或目标值非正时返回 70（无从比较，给中性分）。
    """
    if not target_val or target_val <= 0:
        return 70.0
    ratio = (target_val / max(value, 1e-9)) if lower_is_better else (value / target_val)
    if ratio >= 1.2:
        return 95.0
    if ratio >= 1.0:
        return 85.0
    if ratio >= 0.8:
        return 70.0
    if ratio >= 0.5:
        return 50.0
    return 30.0


def _legacy_normalize(kpi: Dict, value: float, target_val, target_str: str) -> float:
    """未声明 unit 的 KPI 走这里，保留 2026-09-18 第一轮修复后的旧行为。

    留着这份启发式是为了避免给 48 个 KPI 一次性改口径造成大面积评分跳变：
    没有 unit 的 KPI 评分与改造前逐分一致。
    """
    if 0 <= value <= 100 and kpi.get("type") in ("revenue", "quality"):
        return value
    if 0 < value <= 1:
        return value * 100
    if target_val and target_val > 0:
        return _ratio_ladder(value, target_val)
    if value > 1000:
        return 75.0
    if value > 100:
        return 70.0
    return value


def normalize_metric_to_score(kpi: Dict, value: Any) -> float:
    """把原始指标值归一成 0-100 分。

    优先按 kpi["unit"] 声明的量纲分派；未声明 unit 的 KPI 走 _legacy_normalize
    保持旧评分不变。

    量纲为什么必须显式声明——靠「数值范围 + type」猜单位会漂移：
      affiliate_revenue 是美元金额，旧逻辑给出 $0→0、$5→5、$500→95、
      $0.50→50（被 `0 < value <= 1` 当成 0.5 的比率再 ×100）。
      结果 $0.50 营收比 0 营收还高分，且分数量级随金额漂移。
      lcp_performance 目标「≤2.5s」是越小越好，旧逻辑按 value/target 算达标度，
      实际 3.0s（更差）反而拿 95 分。

    更早一轮（零基准）修的是：target=0 且非百分比（「0 个坏链接」
    「0 例伪造数据」）原先被 `0 <= value <= 100` 吃掉，value=0 直接 return 0.0，
    「零个坏链接」拿了最低分，语义完全反了；value=1 掉进 `0 <= value <= 1`
    返回 1.0，越坏分越高。
    """
    if value is None:
        return 70.0  # 无数据基础分
    if not isinstance(value, (int, float)):
        return 70.0

    value = float(value)
    target_str = kpi.get("target", "")
    target_match = re.search(r'(\d+(?:\.\d+)?)', target_str)
    target_val = float(target_match.group(1)) if target_match else None

    # 零基准目标：value=0 是满分。必须最先判定。
    if target_val == 0 and "%" not in target_str:
        return 100.0 if value == 0 else 30.0

    # 增长型目标（target 含「环比」）下的负值 = 明确退步，给 0 分。
    # 2026-09-18 加入：接入 GSC 曝光环比后第一次出现负值（-72%）。
    # 不加这条，负值会落进 _legacy_normalize 底部的 `return value` 拿到
    # -72 分再被 max(0,...) 截成 0——结果偶然正确，靠的是截断而不是语义；
    # 而落进 _ratio_ladder 时负值最差也拿 30 分，「明显退步」被奖励非零分。
    if value < 0 and "环比" in target_str:
        return 0.0

    unit = kpi.get("unit")

    if unit == "currency":
        # 目标是环比增长（"环比增长≥10%"），实测值是绝对金额——不同口径。
        # 没有历史基数就无法评估增长，唯一可判断的事实是「是否为 0」：
        #   0   → 0 分（真实零营收，必须暴露的信号，不给默认分）
        #   > 0 → 70 分（有营收，但增长不可评估：既不奖励也不惩罚）
        # 真实金额始终通过 kpi_results 的 actual 字段暴露，不会被归一化吞掉。
        return 0.0 if value == 0 else 70.0

    if unit == "ratio":
        # 明确声明为 0-1 比率：先 ×100 换成百分比，再和目标百分比比较。
        # 不靠「0 < value <= 1」猜，因为 0.5 既可能是 50% 也可能是 $0.50。
        # 必须先换单位再比目标：旧逻辑直接 return value*100 不看目标，
        # engagement_rate=0.05 对「≥3%」是达标（5%>3%），却只得 5 分。
        return _ratio_ladder(max(0.0, min(100.0, value * 100)), target_val)

    if unit == "seconds":
        return _ratio_ladder(value, target_val, lower_is_better=True)

    if unit == "pct":
        pct = max(0.0, min(100.0, value))
        # 目标是 100%（合规率/覆盖率/结构化数据正确率）时是天花板指标，
        # 不可能超过 100，直接取原值——用达标阶梯的话 100% 只能拿 85 分。
        if target_val and target_val >= 100:
            return pct
        # 目标低于 100%（如 email_open_rate ≥25%）时按达标程度给分。
        return _ratio_ladder(pct, target_val)

    if unit in ("count", "words"):
        return _ratio_ladder(value, target_val)

    return _legacy_normalize(kpi, value, target_val, target_str)


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
            score = NO_DATA_BASE_SCORE
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

    # 数据覆盖率（按权重，不是按 KPI 个数）。
    # no_data 拿 70 分占位分，所以这个 Agent 的分数上限是硬封顶的：
    #   上限 = 100 * 已接数据权重占比 + 70 * 未接数据权重占比
    #        = 70 + 30 * 覆盖率
    # 没有接数据之前，运营做得再好分数也上不去——把这个上限打印出来，
    # 读者就能分清「分数低是因为运营差」还是「分数低是因为没数据」。
    measured_weight = sum(
        k["weight"] for k in kpis if metrics.get(k["id"], None) is not None
    )
    data_coverage_weight = round(measured_weight / total_weight, 3) if total_weight else 0.0
    score_ceiling = round(100 * data_coverage_weight + NO_DATA_BASE_SCORE * (1 - data_coverage_weight), 1)

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
        "measured_kpis": sum(1 for k in kpis if metrics.get(k["id"], None) is not None),
        "total_kpis": len(kpis),
        "data_coverage_weight": data_coverage_weight,
        "score_ceiling": score_ceiling,
        "kpi_results": kpi_results,
    }


# 与实验注册表的 INSUFFICIENT_SAMPLE 阈值一致：样本量不足时不产出比率，
# 避免用 6 次点击算出的「转化率 0%」被当成精确测量值写进考核分。
MIN_SAMPLE_FOR_RATE = 20


def _latest_daily_report() -> Dict[str, Any]:
    """读最新一份飞书日报 JSON（reports/feishu_daily/daily_*.json）。

    日报是仓库里唯一持续产出 GA4 / GSC / 联盟 / 订阅真实实测值的地方，
    而且已经在 CI 里每天跑、结果已入库。这里复用它而不是在考核脚本里
    重调一遍各 API，避免凭证缺失、限流和口径不一致三个问题。
    找不到时返回 {}，对应 KPI 仍标记 no_data（不是默认分）。
    """
    daily_dir = PROJECT_ROOT / "reports" / "feishu_daily"
    files = sorted(daily_dir.glob("daily_*.json")) if daily_dir.exists() else []
    if not files:
        return {}
    try:
        with open(files[-1], "r", encoding="utf-8") as f:
            data = json.load(f)
        data["_report_file"] = files[-1].name
        return data
    except Exception as e:
        print(f"  ⚠️  读取日报失败（营收/流量指标将标记 no_data）: {e}")
        return {}


# ── 本地可实测指标 ─────────────────────────────────────────────────
# 第 4 步接入的日报指标依赖外部 API 的每日快照：凭证缺失、限流、快照陈旧
# 都会让它变成假信号（2026-09-18 刚修过 GSC 单日窗口恒空这一例）。
# 下面这批测的是**仓库自身状态**，与站点流量无关，本地和干净 CI 沙箱里
# 都算得出来，因此更适合作为考核底座。


def _post_files(root: Path = None) -> List[Path]:
    root = root or PROJECT_ROOT
    d = root / "content" / "posts"
    return sorted(d.glob("*.md")) if d.exists() else []


def _body_without_frontmatter(text: str) -> str:
    """去掉 YAML front matter 与 HTML 标签，剩下正文用于词数统计。"""
    body = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.S)
    return re.sub(r"<[^>]+>", " ", body)


def measure_content_stats(root: Path = None) -> Dict[str, Any]:
    """从 content/posts/*.md 实测平均词数与发布率。

    为什么不用 git log 算发布率：`git log --since=7d --name-only` 返回的是
    「近 7 天被某个提交触碰过的文件」。本仓库机器人每 30 分钟批量提交一次，
    一次提交会 name-only 出全部 63 篇文章，发布率会被算成 63 篇/周——
    比硬编码的 4.0 更离谱。front-matter 的 date 才是文章真实发布日期。

    root 可注入，便于测试用临时目录验证口径。
    """
    files = _post_files(root)
    if not files:
        return {}

    word_counts: List[int] = []
    publish_dates: List[datetime] = []
    for p in files:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        word_counts.append(len(_body_without_frontmatter(text).split()))

        m = re.match(r"^---\n(.*?)\n---", text, re.S)
        if m:
            dm = re.search(r"^date:\s*[\"']?(\d{4}-\d{2}-\d{2})", m.group(1), re.M)
            if dm:
                try:
                    publish_dates.append(datetime.strptime(dm.group(1), "%Y-%m-%d"))
                except ValueError:
                    pass

    if not word_counts:
        return {}

    now = datetime.now()
    last7 = sum(1 for d in publish_dates if now - d < timedelta(days=7))
    return {
        "avg_word_count": round(sum(word_counts) / len(word_counts), 1),
        "publish_rate": last7,
        "_posts_total": len(files),
        "_posts_dated": len(publish_dates),
    }


def measure_affiliate_compliance(root: Path = None) -> Dict[str, Any]:
    """affiliate shortcode 的联盟链接合规率与坏链接数。

    Google 要求付费/联盟链接带 rel="sponsored"，缺失有人工处罚风险。
    只统计**外部**链接：`/disclosure/` 这类站内链接不是联盟链接，
    算进去会得出 11/12 = 91.7% 的假不合规。

    root 可注入，便于测试用临时目录验证口径。
    """
    root = root or PROJECT_ROOT
    sc_dir = root / "layouts" / "shortcodes"
    try:
        files = sorted(sc_dir.glob("affiliate-*.html"))
    except OSError:
        return {}

    external = compliant = broken = 0
    for p in files:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for m in re.finditer(r"<a\b([^>]*)>", text, re.I):
            attrs = m.group(1)
            if "href" not in attrs:
                continue
            hm = re.search(r'href\s*=\s*("([^"]*)"|\'([^\']*)\'|([^\s>]+))', attrs, re.I)
            href = (hm.group(2) or hm.group(3) or hm.group(4) or "") if hm else ""
            if not href or href in ("#", "./", "/"):
                broken += 1
                continue
            if href.startswith(("/", "#")):
                continue  # 站内链接，不属于联盟合规口径
            external += 1
            if "sponsored" in attrs.lower():
                compliant += 1

    if not external:
        return {}
    return {
        "affiliate_compliance": round(compliant / external * 100, 1),
        "broken_affiliate_links": broken,
        "_affiliate_external_total": external,
    }


def measure_report_timeliness(root: Path = None) -> float:
    """最新一份日报距今天数 → 时效率（%）。

    0 天 = 100%，1 天 = 50%，≥2 天 = 0%。这是「自动化是否还在按时产出」
    的直接信号。用文件名里的日期而不是 mtime：mtime 会被 git checkout、
    CI 工作流复制和机器时间改写，文件名不会。

    root 可注入，便于测试用临时目录验证口径。
    """
    root = root or PROJECT_ROOT
    daily_dir = root / "reports" / "feishu_daily"
    files = sorted(daily_dir.glob("daily_*.json")) if daily_dir.exists() else []
    if not files:
        return 0.0
    m = re.search(r"(\d{4}-\d{2}-\d{2})", files[-1].name)
    if not m:
        return 0.0
    try:
        age_days = (datetime.now() - datetime.strptime(m.group(1), "%Y-%m-%d")).days
    except ValueError:
        return 0.0
    age_days = max(age_days, 0)
    return 100.0 if age_days == 0 else (50.0 if age_days == 1 else 0.0)


def measure_structured_data(root: Path = None) -> Dict[str, Any]:
    """结构化数据覆盖率（%），来自构建产物的真实渲染结果。

    只读 public/，不自己跑 hugo build：构建有副作用且耗时，而 KPI 审计
    应该是快查。CI 的 site-health 工作流已经产出 public/，这里复用它。

    为什么不用 reports/site_health/*.json：那份审计是 2026-08-31 的，
    结论已陈旧 18 天——它报「缺 WebSite 结构化数据 / 首页缺 canonical」，
    而实测 WebSite 在 287 页、首页 canonical 存在。拿陈旧结论当考核依据，
    等于让考核系统引用一份已被事实推翻的报告。

    无 public/ 或审计报 reason 时返回 {}，对应 KPI 仍标 no_data
    （不是 70 分默认值）。root 可注入，便于测试。
    """
    if not STRUCTURED_DATA_AUDIT_AVAILABLE:
        return {}
    root = root or PROJECT_ROOT
    build_dir = root / "public"
    if not build_dir.is_dir():
        return {}
    r = _sd_audit.audit(build_dir)
    if r.get("reason"):
        return {}
    return r


GSC_MAX_AGE_DAYS = 14
"""GSC 快照超过这个年龄就不用于考核。

api_health 那次是「报告 11 天没刷新」，GSC 这处是同类缺陷的另一形态：
数据没消失、也没被标记 no_data，只是**旧**。status=OK 会让读者误以为
是当前状态。GSC 本身按 2 天判定新鲜，这里放宽到 14 天是为了让
28 天窗口的环比对比仍然成立——但超过 14 天的快照，其「环比」
已经是过去两个月的故事，不该代表本月。
"""

GSC_MIN_DAILY_ROWS = 14
"""做环比需要前后两个半程，每半程至少几天才有意义。
14 行 = 28 天窗口的一半。不足时宁可不接，也不拿 3 天数据算「环比」。"""


def _gsc_real_metrics(gsc_path: Optional[Path] = None) -> Dict[str, Any]:
    """从 reports/real_data/gsc_real_data.json 计算环比口径的 SEO 实测值。

    接 3 个 KPI：
      seo.avg_position         ← 曝光加权平均排名的**改善率**（%）
      content.organic_traffic  ← 曝光量环比变化（%）
      seo.organic_traffic_seo  ← 同上（两者都指向 GSC，定义一致）

    口径说明（这些决定了分数能不能信）：
    - 平均排名按曝光加权，不按天简单平均：曝光 381 的天和曝光 25 的天
      权重天差地别，简单平均会让低曝光日的波动主导结论。
    - 「改善」定义为正数 = 排名数字变小（1 → 2 是变差，2 → 1 是改善）：
      pct = (p1 - p2) / p1 * 100。
    - 曝光量当作「自然搜索流量」的代理指标。GSC 的点击数在这个量级
      站点上太少（28 天 5 次），算环比没有统计意义；曝光量是同一
      数据源里唯一有足够样本量的流量信号。它是**代理**不是流量本身，
      打印时必须注明。
    - top10_keywords 是**绝对计数**（当前 0），而 KPI 目标是
      「环比增长≥5%」。本文件只有单个快照、没有历史，无法算环比；
      而且本函数已明确「绝对计数对增长型目标不接」，所以不写这个 KPI。
      计数本身仍返回，供打印披露。
    """
    result: Dict[str, Any] = {
        "avg_position_pct_change": None,
        "organic_impressions_pct_change": None,
        "top10_queries": None,
        "top10_pages": None,
        "age_days": -1, "data_date": "", "pull_time": "",
        "note": "", "evidence": {},
    }

    if gsc_path is None:
        gsc_path = PROJECT_ROOT / "reports" / "real_data" / "gsc_real_data.json"
    if not gsc_path.exists():
        result["note"] = "无 gsc_real_data.json"
        return result

    try:
        with open(gsc_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception as exc:
        result["note"] = f"读取失败 {type(exc).__name__}"
        return result

    # 空壳防护：real_data_pull_engine 在鉴权失败时写过 is_real_data=False 的
    # 空壳（2026-09-18 已修：不再覆盖上一份真实数据，但历史文件可能还在）。
    # 空壳的 status 可能是 NOT_CONFIGURED，daily 是空列表——按 no_data 处理。
    if raw.get("is_real_data") is not True:
        result["note"] = f"非真实数据（status={raw.get('status', '?')}）"
        return result

    daily = [r for r in (raw.get("daily") or [])
             if isinstance(r, dict)
             and isinstance(r.get("impressions"), (int, float))
             and isinstance(r.get("position"), (int, float))]
    if len(daily) < GSC_MIN_DAILY_ROWS:
        result["note"] = f"daily 行数不足（{len(daily)} < {GSC_MIN_DAILY_ROWS}），" \
                         "无法做可靠环比"
        return result

    # 取数据日期判年龄。data_date 是数据截止日，pull_time 是拉取时刻；
    # 对考核来说「数据多旧」比「拉取多旧」更相关。
    for key in ("data_date", "pull_time"):
        v = raw.get(key)
        if isinstance(v, str):
            m = re.match(r"(20\d{2}-\d{2}-\d{2})", v)
            if m:
                result[key] = m.group(1)
                try:
                    result["age_days"] = max(
                        0, (datetime.now() - datetime.strptime(m.group(1), "%Y-%m-%d")).days)
                except ValueError:
                    pass
                break

    if result["age_days"] > GSC_MAX_AGE_DAYS:
        result["note"] = (f"数据已 {result['age_days']} 天未刷新"
                          f"（阈值 {GSC_MAX_AGE_DAYS} 天）")
        return result

    # 按日期排序后对半切，前一半 vs 后一半。
    daily.sort(key=lambda r: str(r.get("date", "")))
    half = len(daily) // 2
    first, second = daily[:half], daily[half:]

    def _weighted_position(seg: list) -> float:
        imp = sum(r["impressions"] for r in seg)
        if imp <= 0:
            return 0.0
        return sum(r["impressions"] * r["position"] for r in seg) / imp

    p1, p2 = _weighted_position(first), _weighted_position(second)
    i1 = sum(r["impressions"] for r in first)
    i2 = sum(r["impressions"] for r in second)
    c1 = sum(r.get("clicks", 0) or 0 for r in first)
    c2 = sum(r.get("clicks", 0) or 0 for r in second)

    pos_change = round((p1 - p2) / p1 * 100, 2) if p1 > 0 else None
    imp_change = round((i2 - i1) / i1 * 100, 2) if i1 > 0 else None

    result["avg_position_pct_change"] = pos_change
    result["organic_impressions_pct_change"] = imp_change
    result["top10_queries"] = len([q for q in (raw.get("top_queries") or [])
                                   if isinstance(q, dict)
                                   and isinstance(q.get("position"), (int, float))
                                   and q["position"] <= 10])
    result["top10_pages"] = len([p for p in (raw.get("top_pages") or [])
                                 if isinstance(p, dict)
                                 and isinstance(p.get("position"), (int, float))
                                 and p["position"] <= 10])
    result["evidence"] = {
        "window_days": len(daily),
        "first_half": {"days": len(first), "impressions": i1, "clicks": int(c1),
                       "weighted_position": round(p1, 2)},
        "second_half": {"days": len(second), "impressions": i2, "clicks": int(c2),
                        "weighted_position": round(p2, 2)},
        "window": f"{first[0].get('date','?')} ~ {second[-1].get('date','?')}",
    }
    return result


def _report_recency(path: Path) -> datetime:
    """报告的新旧排序键：优先文件名里的日期，退回文件 mtime。

    为什么不能按文件名排序：`site_health_audit.json` 这个名字排在所有
    `site_health_2026-09-*.json` **之后**（'a' > '2'），于是
    `sorted(glob("*.json"))[-1]` 一直拿到那份 18 天前、schema 还是旧的
    报告，把当天几小时前生成的新鲜报告完全忽略。
    这不是本次才有的问题——旧代码 `findings` 恰好存在，掩盖了它。
    """
    m = re.search(r"(20\d{2}-\d{2}-\d{2})", path.name)
    if m:
        try:
            return datetime.strptime(m.group(1), "%Y-%m-%d")
        except ValueError:
            pass
    try:
        return datetime.fromtimestamp(path.stat().st_mtime)
    except OSError:
        return datetime.min


REQUIRED_SECURITY_HEADERS = 6
"""site_health_agent.check_security_headers() 检查的必需安全头数量：
Strict-Transport-Security / X-Content-Type-Options / X-Frame-Options /
Content-Security-Policy / Referrer-Policy / Permissions-Policy。

报告只记录**缺失**的头（type=security_header_missing），
所以合规率 = (6 - 缺失数) / 6。改这个常量要同步改 site_health_agent.py
的 REQUIRED_HEADERS 字典。"""


def _security_headers(reports=None) -> Dict[str, Any]:
    """从最新 site_health 报告读安全响应头合规率。

    2026-09-18 修（静默假绿灯）：旧实现是
        findings = sh.get("findings", [])
        security_issues = [f for f in findings if f.get("module") == "security"]
        metrics["ops"]["security_headers"] = 100.0 if not security_issues else 60.0
    而 site_health_agent 的报告 schema 早已改成 `issues[].type`——
    `sh.get("findings", [])` **恒为空**，于是「0 条安全发现」永远被解读成
    100% 合规。线上真丢 HSTS 时报告里会出现 security_header_missing，
    审计器读不到；检查抛异常时（try/except 吞掉）一条都没有，同样报 100 分。
    两种情况都拿 100 分，而这个分数从没被测量过。

    现在按 schema 分派，并把「测不出来」和「测出来不合规」分开：
      issues schema:
        type=check_failed 且 check=security_headers → not_measured
        type=site_unreachable                        → not_measured
        type=security_header_missing × N             → (6-N)/6
        以上都没有                                    → compliant 100.0
      findings schema（旧报告 site_health_audit.json）:
        module=security 有无发现 → 60.0 / 100.0（保留旧口径，不重算历史）
    """
    out: Dict[str, Any] = {
        "compliance": None, "signal": "", "missing": [],
        "csp_gaps": [],
        "checked": REQUIRED_SECURITY_HEADERS,
        "note": "", "age_days": -1, "file": "",
    }
    if reports is None:
        reports = sorted(
            (PROJECT_ROOT / "reports" / "site_health").glob("*.json"),
            key=_report_recency,
        )
    if not reports:
        out["note"] = "无 site_health 报告"
        return out

    path = reports[-1]
    out["file"] = path.name
    out["age_days"] = _report_age_days(path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            sh = json.load(f)
    except Exception as exc:
        out["note"] = f"读取失败 {type(exc).__name__}"
        return out

    if not isinstance(sh, dict):
        out["note"] = "报告不是 JSON 对象"
        return out

    # 新 schema：site_health_agent.py 的 issues[]
    if "issues" in sh:
        issues = [i for i in sh.get("issues") or [] if isinstance(i, dict)]
        # CSP 放行缺口单独收集，不进 security_headers 合规率。
        # 它是 HIGH 级发现但考核的是「CSP 内容够不够」，
        # 和「6 个必需头是否齐全」不是同一件事——
        # 混进去等于用一个 KPI 测两个口径。
        out["csp_gaps"] = [str(i.get("message"))
                           for i in issues
                           if i.get("type") == "csp_allowlist_missing"]
        blocked = [i for i in issues
                   if i.get("type") == "check_failed"
                   and i.get("check") == "security_headers"]
        unreachable = [i for i in issues if i.get("type") == "site_unreachable"]
        if blocked or unreachable:
            why = "; ".join(str(i.get("message") or i.get("type"))
                            for i in (blocked or unreachable)[:2])
            out["signal"] = "not_measured"
            out["note"] = f"安全头检查未产出结论：{why}"
            # 检查本身失败时，同报告里的 CSP 缺口也不能当结论用——
            # 采集链路坏了，任何细粒度数字都不可信。
            out["csp_gaps"] = []
            return out
        missing = [i for i in issues if i.get("type") == "security_header_missing"]
        n = len(missing)
        out["missing"] = [str(i.get("message")) for i in missing]
        if n:
            out["signal"] = "missing"
            out["compliance"] = round(
                max(0.0, REQUIRED_SECURITY_HEADERS - n) / REQUIRED_SECURITY_HEADERS * 100, 1)
            return out
        out["signal"] = "compliant"
        out["compliance"] = 100.0
        return out

    # 旧 schema：site_health_audit.json 的 findings[]
    if "findings" in sh:
        findings = [f for f in sh.get("findings") or [] if isinstance(f, dict)]
        sec = [f for f in findings if f.get("module") == "security"]
        out["signal"] = "legacy"
        out["compliance"] = 100.0 if not sec else 60.0
        out["missing"] = [str(f.get("title") or f.get("message")) for f in sec]
        return out

    out["signal"] = "not_measured"
    out["note"] = "报告既无 issues 也无 findings 字段，无法判断安全头状态"
    return out


def _report_age_days(path: Path) -> int:
    """报告文件的年龄（天）。从文件名或内容里的时间戳取，取不到返回 -1。

    为什么需要：拿一份 11 天前的审计当本月考核依据，等于让考核系统引用
    过期结论。年龄打印出来至少让读者知道这个分数的时效。
    """
    m = re.search(r"(20\d{2}-\d{2}-\d{2})", path.name)
    if m:
        try:
            return max(0, (datetime.now() - datetime.strptime(m.group(1), "%Y-%m-%d")).days)
        except ValueError:
            pass
    try:
        with open(path, "r", encoding="utf-8") as f:
            head = json.load(f)
        for key in ("audit_time", "generated_at", "collected_at"):
            v = head.get(key) if isinstance(head, dict) else None
            if isinstance(v, str):
                m2 = re.match(r"(20\d{2}-\d{2}-\d{2})", v)
                if m2:
                    return max(0, (datetime.now() - datetime.strptime(m2.group(1), "%Y-%m-%d")).days)
    except Exception:
        pass
    return -1


def _publish_consistency(social_dir: Optional[Path] = None) -> Dict[str, Any]:
    """从 reports/social/social_daily_*.json 计算发布一致性达标率。

    数据源：social_daily 由 Buffer API 拉取（analytics_source="buffer_api"）。
    口径已核对：平台分项求和与 total_published 一致
    （2026-09-01: ig 9 + pinterest 13 + x 8 + fb 9 = 39 = total_published）。

    明确排除 reports/social/post_performance_data.json —— 它自报
    data_source="sample_data (replace with Buffer API)"，是样例数据，
    接进考核等于喂编造数字。

    目标「每周≥5条」→ 达标率 = 达标周 / 有数据的周。
    按周而不是按日：目标本身定义在周上，日粒度会把「某一天没发」
    这种不构成违约的噪音算成失败。
    只统计**有数据文件**的周：某周完全没有日报文件时，
    无法区分「当天没发」和「采集器没跑」，两种情况不能混为一谈。
    """
    result: Dict[str, Any] = {"rate": None, "weeks_met": 0, "weeks_measured": 0,
                              "weeks": {}, "posts_total": 0, "days": 0,
                              "age_days": -1, "note": ""}

    if social_dir is None:
        social_dir = PROJECT_ROOT / "reports" / "social"
    files = sorted(social_dir.glob("social_daily_*.json"))
    if not files:
        result["note"] = "无 social_daily 数据"
        return result

    weeks: Dict[str, int] = {}
    week_days: Dict[str, int] = {}
    posts_total = 0
    newest_name = ""

    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as fh:
                d = json.load(fh)
            date = d.get("date")
            published = d.get("total_published")
            if not isinstance(date, str) or not isinstance(published, (int, float)):
                continue
            dt = datetime.strptime(date, "%Y-%m-%d")
        except Exception:
            continue
        key = f"{dt.isocalendar().year}-W{dt.isocalendar().week:02d}"
        weeks[key] = weeks.get(key, 0) + int(published)
        week_days[key] = week_days.get(key, 0) + 1
        posts_total += int(published)
        if f.name > newest_name:
            newest_name = f.name

    if not weeks:
        result["note"] = "social_daily 里无可用数据"
        return result

    met = sum(1 for v in weeks.values() if v >= 5)
    result.update({
        "rate": round(met / len(weeks) * 100, 1),
        "weeks_met": met,
        "weeks_measured": len(weeks),
        "weeks": {k: {"published": v, "days_with_data": week_days[k]} for k, v in sorted(weeks.items())},
        "posts_total": posts_total,
        "days": len(files),
        "age_days": _report_age_days(social_dir / newest_name),
    })
    return result


def _brand_consistency(report_path: Optional[Path] = None) -> Dict[str, Any]:
    """从 brand_identity_audit 的 markdown 报告解析品牌一致性。

    数据源：reports/P1_BRAND_02_BRAND_IDENTITY_AUDIT.md，由
    brand_identity_audit.py 生成（deploy-cloudflare-pages.yml 每次部署
    都会跑一次，content-quality-audit.yml / weekly-blog-update.yml 也跑）。
    注意 --legacy 模式写的是另一份文件 P1_BRAND_02_LEGACY_PERSONA_REVIEW.md，
    那个查的是旧人设短语，不是品牌一致性，不能混用。

    口径（严格按脚本自己的定义）：
      FAIL   = 命中 forbidden_phrases 或 FICTIONAL_PATTERNS → 真违规
      WARN   = 品牌语言尚未出现，脚本注释明确写「no violations」
      PASS   = 品牌语言已出现
      MISSING = 文件不存在
    一致性 = PASS / (PASS + FAIL)。WARN 不进分母——它既不是违规也不是
    一致，脚本自己说它「不构成违约」。

    刻意同时报出 PASS 覆盖率：一致性 100% 只表示「没有互相矛盾的品牌
    表述」，不代表每个页面都写了品牌语言。2026-09-18 实测线上版本是
    16/107 PASS、0 FAIL——0 处违规但只有 15% 的页面带品牌语言。
    只打 100% 会掩盖覆盖缺口，所以打印里两个数都给。
    """
    out: Dict[str, Any] = {
        "consistency": None, "pass": 0, "total": 0, "fail": 0,
        "warn": 0, "coverage": None, "generated": "", "age_days": -1,
        "file": "", "note": "",
    }

    if report_path is None:
        report_path = PROJECT_ROOT / "reports" / "P1_BRAND_02_BRAND_IDENTITY_AUDIT.md"
    if not report_path.exists():
        out["note"] = "无 brand_identity_audit 报告"
        return out

    out["file"] = report_path.name
    try:
        text = report_path.read_text(encoding="utf-8")
    except Exception as e:
        out["note"] = f"读取失败: {e}"
        return out

    m = re.search(
        r"Summary:\s*(\d+)\s*/\s*(\d+)\s*PASS;\s*(\d+)\s*FAIL;\s*(\d+)\s*MISSING",
        text,
    )
    if not m:
        out["note"] = "报告里没有可解析的 Summary 行（脚本输出格式可能已变）"
        return out

    out["pass"] = int(m.group(1))
    out["total"] = int(m.group(2))
    out["fail"] = int(m.group(3))
    out["warn"] = out["total"] - out["pass"] - out["fail"]

    assessed = out["pass"] + out["fail"]
    if assessed <= 0:
        out["note"] = "没有任何 PASS/FAIL 记录，无法判定"
        return out
    out["consistency"] = round(out["pass"] / assessed * 100, 1)
    out["coverage"] = round(out["pass"] / out["total"] * 100, 1) if out["total"] else None

    g = re.search(r"Generated:\s*(\d{4}-\d{2}-\d{2})", text)
    if g:
        out["generated"] = g.group(1)
        try:
            out["age_days"] = (
                datetime.now().date() - datetime.strptime(g.group(1), "%Y-%m-%d").date()
            ).days
        except ValueError:
            pass

    return out


def _mojibake_free(report_path: Optional[Path] = None) -> Dict[str, Any]:
    """从 content_quality_validator 的输出算编码乱码合格率。

    数据源：reports/content_audit/validator_output.json，由
    content-quality-audit.yml 生成（
        python scripts/content_quality_validator.py --json > validator_output.json
    ）。weekly-blog-update.yml / deploy-cloudflare-pages.yml 也跑该脚本，
    但只打印到日志，不产出这份文件。

    口径：mojibake_free = 编码完全干净的文件数 / 总文件数。
    「完全干净」= mojibake_issues 为空 且 encoding_errors 为空：
      - mojibake_issues：detect_mojibake 的字节级双重编码序列
        （UTF-8 被误读为 Latin-1/CP1252 后再编码为 UTF-8）
      - encoding_errors：解码层错误
    两个都要查——KPI 名是「编码乱码合格率」，只查双重编码会漏掉
    解码层面的错误。

    2026-09-18 修掉一个口径错位：本 KPI 原先从 content_coverage 报告的
    post_fields.last_updated.passed 取值——那测的是「文章有没有填
    last_updated 字段」，和编码乱码毫无关系。后果是：一篇文章哪怕
    满篇乱码，只要 front-matter 里 last_updated 填了，就拿 100 分的
    「编码乱码合格率」。KPI 定义里声明的源一直是
    content_quality_validator(P0)，只是从来没接上——这是本轮之前
    最隐蔽的一处假绿灯，因为它打出来的分数恰好是漂亮的 100 分。
    """
    out: Dict[str, Any] = {
        "rate": None, "clean": 0, "total": 0,
        "mojibake_files": 0, "encoding_files": 0,
        "age_days": -1, "file": "", "note": "",
    }

    if report_path is None:
        report_path = PROJECT_ROOT / "reports" / "content_audit" / "validator_output.json"
    if not report_path.exists():
        out["note"] = "无 content_quality_validator 输出"
        return out

    out["file"] = report_path.name
    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
    except Exception as e:
        out["note"] = f"读取失败: {e}"
        return out

    try:
        out["age_days"] = (datetime.now()
                           - datetime.fromtimestamp(report_path.stat().st_mtime)).days
    except OSError:
        pass

    rows = data.get("results") if isinstance(data, dict) else None
    if not isinstance(rows, list) or not rows:
        out["note"] = "输出里没有 results 列表，无法判定"
        return out

    out["total"] = len(rows)
    clean = 0
    for r in rows:
        if not isinstance(r, dict):
            continue
        if r.get("mojibake_issues"):
            out["mojibake_files"] += 1
        if r.get("encoding_errors"):
            out["encoding_files"] += 1
        if not r.get("mojibake_issues") and not r.get("encoding_errors"):
            clean += 1
    out["clean"] = clean
    out["rate"] = round(clean / out["total"] * 100, 1)

    return out


def collect_metrics() -> Dict[str, Dict[str, Any]]:
    """
    收集各 Agent 的实际指标数据。
    优先从已有报告/API读取，无数据则标记为 no_data。
    """
    metrics = {aid: {} for aid in AGENTS}

    # 1. 编码乱码合格率 ← content_quality_validator 的字节级检测。
    #    2026-09-18 修掉口径错位：原先这里读 content_coverage 报告的
    #    post_fields.last_updated.passed，那测的是「文章有没有填
    #    last_updated 字段」——和编码乱码无关。61/61 篇都填了字段，
    #    于是长期稳定输出 100 分，不管正文里有没有乱码。
    #    注意：content_coverage 报告没有别的 KPI 在用，整块删掉。
    mb = _mojibake_free()
    if mb["rate"] is not None:
        metrics["content"]["mojibake_free"] = mb["rate"]
        bad = mb["mojibake_files"] + mb["encoding_files"]
        print(f"  🔤 编码乱码合格率: {mb['rate']}%"
              f"（{mb['clean']}/{mb['total']} 篇完全干净"
              f"，双重编码 {mb['mojibake_files']} 篇 / 解码错误 {mb['encoding_files']} 篇"
              f"，{mb['file']}，{mb['age_days']} 天前）")
        if bad:
            print(f"     ⚠️  {bad} 篇文件有编码问题（quality 类型，<80 分再扣 20）")
    else:
        print(f"  🔤 编码乱码合格率: 未测量（{mb['file'] or '无报告'}，{mb['note']}）")

    # 2. 从 api_health_audit 读取 API 健康指标
    api_reports = sorted((PROJECT_ROOT / "reports" / "api_health").glob("*.json"))
    if api_reports:
        try:
            with open(api_reports[-1], "r", encoding="utf-8") as f:
                api = json.load(f)
            metrics["ops"]["api_health_rate"] = float(api.get("summary", {}).get("pass_rate", 0))
            print(f"  🩺 API 健康率: {metrics['ops']['api_health_rate']}%"
                  f"（{api_reports[-1].name}，{_report_age_days(api_reports[-1])} 天前）")
        except Exception:
            pass

    # 2b. 订阅端点健康 ← subscription_health 专项审计。
    # 2026-09-18 修复：原先把 user.subscribe_api_health 接到通用 api_health 的
    # pass_rate 上。那份报告测的是全站 16 个端点，与订阅端点无关——等于用
    # 一个不相关指标给订阅 API 打分，订阅端点真实健康度反而成了盲区。
    sub_reports = sorted((PROJECT_ROOT / "reports" / "subscription_health").glob("*.json"))
    if sub_reports:
        try:
            with open(sub_reports[-1], "r", encoding="utf-8") as f:
                sub = json.load(f)
            s = sub.get("summary", {})
            total, passed = s.get("total", 0), s.get("passed", 0)
            if total:
                metrics["user"]["subscribe_api_health"] = round(passed / total * 100, 1)
                fails = [t.get("name") for t in sub.get("api_tests", []) if not t.get("passed")]
                print(f"  📧 订阅端点健康: {metrics['user']['subscribe_api_health']}%"
                      f"（{passed}/{total}，{sub_reports[-1].name}，"
                      f"{_report_age_days(sub_reports[-1])} 天前）"
                      + (f" 失败: {fails}" if fails else ""))
        except Exception:
            pass

    # 3. 从 site_health 报告读取安全/性能指标
    sh = _security_headers()
    if sh["compliance"] is not None:
        metrics.setdefault("ops", {})["security_headers"] = sh["compliance"]
        tail = f"，缺失: {'; '.join(sh['missing'])}" if sh["missing"] else ""
        print(f"  🔒 安全响应头: {sh['compliance']}%"
              f"（{sh['checked'] - len(sh['missing'])}/{sh['checked']} 个必需头齐全"
              f"，{sh['file']}，{sh['age_days']} 天前）{tail}")
        if sh["csp_gaps"]:
            print(f"     ⚠️  CSP 放行缺口 {len(sh['csp_gaps'])} 项（不影响上面的合规率，"
                  f"那是另一个口径）:")
            for g in sh["csp_gaps"]:
                print(f"       - {g}")
    else:
        print(f"  🔒 安全响应头: 未测量（{sh['file'] or '无报告'}，{sh['note']}）")

    # 3b. 发布一致性 ← Buffer API 每日发布数据。
    pc = _publish_consistency()
    if pc["rate"] is not None:
        metrics["social"]["publish_consistency"] = pc["rate"]
        print(f"  📆 发布一致性: {pc['rate']}%"
              f"（{pc['weeks_met']}/{pc['weeks_measured']} 周达标≥5条，"
              f"{pc['days']} 天 / {pc['posts_total']} 条，{pc['age_days']} 天前）")
    elif pc["note"]:
        print(f"  📆 发布一致性: 无数据（{pc['note']}）")

    # 3c. 品牌一致性 ← brand_identity_audit 的 markdown 报告。
    bc = _brand_consistency()
    if bc["consistency"] is not None:
        metrics["social"]["brand_consistency"] = bc["consistency"]
        print(f"  🏷️ 品牌一致性: {bc['consistency']}%"
              f"（{bc['fail']} 处违规 / {bc['pass']}+{bc['fail']} 个可判定面）"
              f"，品牌语言覆盖率 {bc['coverage']}%（{bc['pass']}/{bc['total']}）"
              f"，{bc['file']}，{bc['age_days']} 天前")
        if bc["consistency"] >= 95.0 and bc["coverage"] < 50.0:
            print(f"     ⚠️  零违规但覆盖不足：{bc['total'] - bc['pass']} 个页面"
                  f"还没有品牌表述（脚本记为 WARN，不算违规）")
    else:
        print(f"  🏷️ 品牌一致性: 未测量（{bc['file'] or '无报告'}，{bc['note']}）")

    # 4. 从最新日报读取真实实测值。
    #    历史问题（2026-09-18 修复）：本函数原先只填 5 个指标，其中
    #    avg_word_count=1808 与 publish_rate=4.0 是**硬编码字面量**，却被标记为
    #    status="measured" 当作真实测量值参与评分；其余 41 个 KPI 全部落到
    #    normalize_metric_to_score 的 70 分「无数据基础分」。
    #    结果是一个标榜「营收导向考核」的月度报告，实际从未测量过任何营收指标——
    #    每个 Agent 的营收项都是 70 分，谁也看不出差别。
    #
    #    接入原则（只接单位与归一化器语义对得上的）：
    #    - 货币额、百分比、有明确阈值的比率 → 接入
    #    - 绝对计数 对 增长型目标（如「环比增长≥8%」的 sessions=11 → 11 分）
    #      → 不接，那会产生看起来精确实则无意义的分数
    #    - 样本量不足的比率 → 不接（见 MIN_SAMPLE_FOR_RATE）
    daily = _latest_daily_report()
    if daily:
        print(f"  📄 营收/流量指标来源: reports/feishu_daily/{daily.get('_report_file')}")

        def _set(agent_id: str, kpi_id: str, value) -> None:
            """只有拿到非 None 的真实值才写入；None 保持 no_data 语义。"""
            if value is None:
                return
            metrics.setdefault(agent_id, {})[kpi_id] = value

        # Revenue Agent
        _set("revenue", "affiliate_revenue", daily.get("affiliate_revenue"))
        clicks = daily.get("tp_clicks") or 0
        bookings = daily.get("tp_bookings") or 0
        if clicks >= MIN_SAMPLE_FOR_RATE:
            _set("revenue", "conversion_rate", round(bookings / clicks * 100, 2))
        # Social Agent（engagement_rate 本就是百分比口径）
        _set("social", "engagement_rate", daily.get("engagement_rate"))
        # User Agent（0 个新增订阅 → 0 分，这是真实测量而非缺数据）
        _set("user", "email_list_growth", daily.get("ml_new_subscribers"))
        # SEO Agent：空链接数是 0 → 100 分；与 ops.security_headers 同一映射口径
        empty_links = daily.get("empty_links")
        if empty_links is not None:
            _set("seo", "internal_link_health",
                 100.0 if empty_links == 0 else max(0.0, 100.0 - empty_links * 10))

        # 注意：**不**接 ops.uptime ← daily.get("site_up")。
        # 2026-09-18 那次日报 site_up=False / response_time=0，实为 CI runner
        # 网络瞬时失败（当日线上站点实测 HTTP 200）。直接接入会把一次 CI 抖动
        # 变成 0 分 uptime，等于给考核注入新的假扣分——正是本函数要消除的问题。

    # 5. 专项营收收集器结果，优先级高于日报：它有 30 天窗口，日报只有单日口径。
    #    两者都有值时以收集器为准。
    for aid, vals in load_real_revenue_data().items():
        metrics.setdefault(aid, {}).update(vals)

    # 6. 本地可实测指标：仓库自身状态，不依赖外部 API 快照。
    #    这五个此前全部落在 70 分无数据基础分，是考核盲区。
    #    2026-09-18 实测：avg_word_count=1904（19/63 篇低于 1500 字目标）；
    #    publish_rate=0 篇/周——最新一篇是 2026-09-08，已停滞 10 天。
    #    后者才是本轮真正有价值的发现：内容停产不会出现在任何报表里，
    #    因为它此前根本不在 KPI 里。
    try:
        _c = measure_content_stats()
        if _c:
            metrics.setdefault("content", {})["avg_word_count"] = _c["avg_word_count"]
            metrics.setdefault("content", {})["publish_rate"] = _c["publish_rate"]
            print(f"  📝 内容实测: 平均 {_c['avg_word_count']:.0f} 词 / 近7天新发 {_c['publish_rate']} 篇"
                  f"（共 {_c['_posts_total']} 篇，{_c['_posts_dated']} 篇有日期）")
    except Exception as e:
        print(f"  ⚠️  内容指标实测失败: {e}")

    try:
        _a = measure_affiliate_compliance()
        if _a:
            metrics.setdefault("revenue", {})["affiliate_compliance"] = _a["affiliate_compliance"]
            metrics.setdefault("revenue", {})["broken_affiliate_links"] = _a["broken_affiliate_links"]
            print(f"  🔗 联盟合规: {_a['affiliate_compliance']}%"
                  f"（{_a['_affiliate_external_total']} 条外部链接）/ 坏链接 {_a['broken_affiliate_links']} 个")
    except Exception as e:
        print(f"  ⚠️  联盟合规实测失败: {e}")

    try:
        _t = measure_report_timeliness()
        metrics.setdefault("data", {})["report_timeliness"] = _t
        print(f"  ⏱️  日报时效: {_t}%")
    except Exception as e:
        print(f"  ⚠️  日报时效实测失败: {e}")

    try:
        _s = measure_structured_data()
        if _s:
            metrics.setdefault("seo", {})["structured_data"] = _s["structured_data_coverage_pct"]
            metrics.setdefault("seo", {})["canonical_consistency"] = _s["canonical_coverage_pct"]
            print(f"  🏷️  结构化数据: {_s['structured_data_coverage_pct']}%"
                  f"（{_s['pages_with_structured_data']}/{_s['pages_total']} 页，文章页 "
                  f"{_s['post_structured_data_coverage_pct']}%）"
                  f"/ canonical {_s['canonical_coverage_pct']}%"
                  f"/ 模板残留 {_s['template_residue_count']} 处")
    except Exception as e:
        print(f"  ⚠️  结构化数据实测失败: {e}")

    try:
        _t = _gsc_real_metrics()
        if _t["avg_position_pct_change"] is not None:
            metrics.setdefault("seo", {})["avg_position"] = _t["avg_position_pct_change"]
        if _t["organic_impressions_pct_change"] is not None:
            metrics.setdefault("content", {})["organic_traffic"] = _t["organic_impressions_pct_change"]
            metrics.setdefault("seo", {})["organic_traffic_seo"] = _t["organic_impressions_pct_change"]
        _ev = _t["evidence"]
        print(f"  🔎 GSC 实测（{_ev.get('window', '?') if _ev else '?'}，"
              f"{_t['age_days']} 天前，{_ev.get('window_days', 0)} 天窗口）:")
        if _ev:
            _f, _s = _ev["first_half"], _ev["second_half"]
            print(f"    排名（曝光加权）: {_f['weighted_position']} → {_s['weighted_position']}"
                  f"  改善 {_t['avg_position_pct_change']}%"
                  f"（目标环比提升≥5%）")
            print(f"    曝光量: {_f['impressions']} → {_s['impressions']}"
                  f"  变化 {_t['organic_impressions_pct_change']}%"
                  f"（作为流量代理指标；点击 {_f['clicks']} → {_s['clicks']} 样本不足）")
            print(f"    Top10 关键词: {_t['top10_queries']} 个 / Top10 页面: "
                  f"{_t['top10_pages']} 个")
        else:
            print(f"    ⚠️  未接入（{_t['note']}）")
    except Exception as e:
        print(f"  ⚠️  GSC 实测失败: {e}")

    # 7. kpi_coverage：真实覆盖率。data Agent 有这个 KPI（目标 100%），
    #    之前从未被计算。它让「多少指标是真测量的」变成可见事实，
    #    而不是所有 Agent 都拿到 70 分默认值看起来差别不大。
    #    注意顺序：必须先写入 kpi_coverage 再统计，否则 data Agent 的这个
    #    KPI 永远是 no_data，覆盖率系统性低估 1/48（自指不一致）。
    metrics.setdefault("data", {})["kpi_coverage"] = 0.0

    total = measured = 0
    for aid in AGENTS:
        for kpi in AGENTS[aid]["kpis"]:
            total += 1
            if metrics.get(aid, {}).get(kpi["id"]) is not None:
                measured += 1
    coverage_pct = round(measured / total * 100, 1) if total else 0.0
    metrics["data"]["kpi_coverage"] = coverage_pct
    metrics["data"]["_measured_count"] = measured
    metrics["data"]["_total_count"] = total

    print(f"  📊 KPI 覆盖率: {measured}/{total} = {coverage_pct}%（其余标记 no_data）")
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
        print(f"     数据覆盖: {result['measured_kpis']}/{result['total_kpis']} 个 KPI 有真实数据（权重占比 {result['data_coverage_weight']*100:.1f}%）→ 分数上限 {result['score_ceiling']}")
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
def load_real_revenue_data() -> Dict[str, Dict[str, Any]]:
    """读 revenue_data_collector 已落盘的结果，返回 {agent_id: {kpi_id: value}}。

    刻意不调用 collect_all()：它有网络调用和写文件副作用（写
    reports/revenue_data/），而且 CI 里没有 Stripe key（gh secret list 已确认
    secrets 里只有 CLOUDFLARE_* 官方名），调用只会白白失败再写一份空数据。

    历史 bug：本函数曾**完全失效**，原因是两处独立的坑叠加——
    1. import 了一个不存在的 RevenueDataCollector 类 → ImportError 被静默吞掉；
    2. 即使 import 成功，collect_all() 的返回体里**根本没有 status 键**
       （真实结构是 collected_at / period_days / total_revenue / sources），
       所以 `data.get("status") == "success"` 永远为假。
    此外本函数长期**没有被任何地方调用**——即使前两个问题都修好也白修。
    """
    if not REVENUE_COLLECTOR_AVAILABLE:
        return {}
    rd_dir = PROJECT_ROOT / "reports" / "revenue_data"
    files = sorted(rd_dir.glob("revenue_data_*.json")) if rd_dir.exists() else []
    if not files:
        return {}
    try:
        with open(files[-1], "r", encoding="utf-8") as f:
            data = json.load(f)
        total_revenue = data.get("total_revenue")
        if total_revenue is None:
            return {}
        sources = data.get("sources") or {}
        tp = sources.get("travelpayouts") or {}
        stripe = sources.get("stripe") or {}
        print(f"  📊 已接入真实营收数据: {files[-1].name} (合计 ${total_revenue:.2f})")
        out: Dict[str, Dict[str, Any]] = {}
        if tp.get("approved_commission") is not None:
            out.setdefault("revenue", {})["affiliate_revenue"] = float(tp["approved_commission"])
        if stripe.get("net_revenue") is not None:
            out.setdefault("revenue", {})["ebook_revenue"] = float(stripe["net_revenue"])
        return out
    except Exception as e:
        print(f"  ⚠️  营收数据读取失败（对应 KPI 标记 no_data）: {e}")
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
