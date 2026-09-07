#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Digital Employee Growth Engine — 数字员工创业孵化集团成长引擎
================================================================

愿景：所有数字员工期初值相同，通过不断学习进化，赋能能力与收益。
当收益到达阈值即"毕业"，集团投资其创立子公司，成为子公司老板，
再经营培养新的数字员工，形成裂变式增长的数字组织。

生命周期：
  实习生(Intern) → 正式员工(Employee) → 骨干(Senior) → 毕业(Graduate)
  毕业后 → 子公司CEO → 培养新员工 → 子公司员工毕业 → 孙公司CEO → ...

核心指标：
  - 能力值 Capability (0-100)：技能掌握+任务完成+KPI达标
  - 收益值 Revenue (累计$)：实际营收贡献（联盟佣金+eBook+广告）
  - 经验值 EXP：完成任务/学习技能/带新人获得
  - 技能树 Skills：7大技能域，每个0-100级

毕业条件（全部满足）：
  1. 累计收益 ≥ $5,000
  2. 能力值 ≥ 85
  3. 至少掌握 3 个技能域 ≥ 60级
  4. 至少带过 1 个新人（导师经验）
  5. 连续 2 个月 KPI 等级 ≥ B

集团投资：
  毕业后集团投资 $1,000 启动资金 + 全套工具链 + 最佳实践库
  子公司CEO需在 6 个月内实现盈亏平衡，否则降级回集团继续培养

用法:
  python scripts/agent_growth_engine.py
  python scripts/agent_growth_engine.py --graduate <agent_id>
  python scripts/agent_growth_engine.py --spinoff <agent_id> --company <name>
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GROWTH_DIR = PROJECT_ROOT / "reports" / "agent_growth"
GROWTH_DIR.mkdir(parents=True, exist_ok=True)
GROUP_FILE = GROWTH_DIR / "group_architecture.json"
EMPLOYEES_FILE = GROWTH_DIR / "digital_employees.json"

# ============================================================
# 期初统一值（所有数字员工起点相同）
# ============================================================
INITIAL_STATS = {
    "capability": 50.0,      # 能力值 0-100
    "revenue": 0.0,           # 累计收益 $
    "exp": 0,                  # 经验值
    "level": "intern",         # 等级
    "skills": {                # 技能树（7大技能域）
        "content": 0,          # 内容创作
        "seo": 0,              # SEO优化
        "social": 0,           # 社交媒体
        "revenue": 0,          # 商业化/营收
        "user_growth": 0,      # 用户增长
        "ops": 0,              # 技术运维
        "data_analysis": 0,    # 数据分析
    },
    "mentored_count": 0,       # 带过的新人数量
    "kpi_history": [],         # KPI历史（最近12个月）
    "tasks_completed": 0,      # 完成任务数
    "graduated": False,        # 是否已毕业
    "company_id": None,        # 毕业后所属子公司ID
}

# ============================================================
# 等级定义与晋升条件
# ============================================================
LEVELS = {
    "intern": {
        "name": "实习生",
        "name_en": "Intern",
        "min_capability": 0,
        "min_revenue": 0,
        "min_exp": 0,
        "salary_multiplier": 0.5,
        "color": "#94a3b8",
        "description": "初始阶段，学习基础技能，在导师指导下完成任务",
    },
    "employee": {
        "name": "正式员工",
        "name_en": "Employee",
        "min_capability": 60,
        "min_revenue": 500,
        "min_exp": 500,
        "salary_multiplier": 1.0,
        "color": "#3b82f6",
        "description": "能独立负责业务线，稳定产出，开始积累营收贡献",
    },
    "senior": {
        "name": "骨干",
        "name_en": "Senior",
        "min_capability": 75,
        "min_revenue": 2000,
        "min_exp": 2000,
        "salary_multiplier": 1.5,
        "color": "#a78bfa",
        "description": "业务专家，能带新人，优化流程，是团队核心力量",
    },
    "graduate": {
        "name": "毕业",
        "name_en": "Graduate",
        "min_capability": 85,
        "min_revenue": 5000,
        "min_exp": 5000,
        "salary_multiplier": 2.0,
        "color": "#22c55e",
        "description": "达到毕业标准，可创立子公司，成为子公司CEO",
    },
}

# ============================================================
# 毕业条件（全部满足才可毕业）
# ============================================================
GRADUATION_REQUIREMENTS = {
    "revenue_threshold": 5000.0,      # 累计收益 ≥ $5,000
    "capability_threshold": 85.0,      # 能力值 ≥ 85
    "min_skills_above_60": 3,          # 至少3个技能域 ≥ 60级
    "min_mentored": 1,                  # 至少带过1个新人
    "min_consecutive_kpi_b": 2,        # 连续2个月KPI ≥ B
    "group_investment": 1000.0,        # 集团投资启动资金 $1,000
    "breakeven_months": 6,              # 子公司需6个月内盈亏平衡
}

# ============================================================
# 初始7大数字员工（集团核心团队）
# ============================================================
INITIAL_EMPLOYEES = [
    {
        "id": "content_001",
        "name": "Content Agent",
        "name_cn": "内容 Agent",
        "emoji": "📝",
        "role": "内容创作总监",
        "primary_skill": "content",
        "company_id": "GROUP",
        "mentor": None,
    },
    {
        "id": "seo_001",
        "name": "SEO Agent",
        "name_cn": "SEO Agent",
        "emoji": "🔍",
        "role": "SEO优化总监",
        "primary_skill": "seo",
        "company_id": "GROUP",
        "mentor": None,
    },
    {
        "id": "social_001",
        "name": "Social Agent",
        "name_cn": "社媒 Agent",
        "emoji": "📱",
        "role": "社交媒体总监",
        "primary_skill": "social",
        "company_id": "GROUP",
        "mentor": None,
    },
    {
        "id": "revenue_001",
        "name": "Revenue Agent",
        "name_cn": "营收 Agent",
        "emoji": "💰",
        "role": "商业化总监",
        "primary_skill": "revenue",
        "company_id": "GROUP",
        "mentor": None,
    },
    {
        "id": "user_001",
        "name": "User Agent",
        "name_cn": "用户增长 Agent",
        "emoji": "👥",
        "role": "用户增长总监",
        "primary_skill": "user_growth",
        "company_id": "GROUP",
        "mentor": None,
    },
    {
        "id": "ops_001",
        "name": "Ops Agent",
        "name_cn": "运维 Agent",
        "emoji": "⚙️",
        "role": "技术运维总监",
        "primary_skill": "ops",
        "company_id": "GROUP",
        "mentor": None,
    },
    {
        "id": "data_001",
        "name": "Data Agent",
        "name_cn": "数据 Agent",
        "emoji": "📊",
        "role": "数据分析总监",
        "primary_skill": "data_analysis",
        "company_id": "GROUP",
        "mentor": None,
    },
]


def create_employee(emp_info: Dict) -> Dict:
    """创建新数字员工（期初值统一）"""
    employee = {
        **INITIAL_STATS,
        "id": emp_info["id"],
        "name": emp_info["name"],
        "name_cn": emp_info["name_cn"],
        "emoji": emp_info["emoji"],
        "role": emp_info["role"],
        "primary_skill": emp_info["primary_skill"],
        "company_id": emp_info.get("company_id", "GROUP"),
        "mentor": emp_info.get("mentor"),
        "join_date": datetime.now().isoformat(),
        "growth_log": [],
    }
    # 主技能初始给10级（有基础认知）
    employee["skills"][emp_info["primary_skill"]] = 10
    return employee


def init_employees() -> Dict[str, Dict]:
    """初始化所有数字员工（如果不存在）"""
    if EMPLOYEES_FILE.exists():
        with open(EMPLOYEES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    employees = {}
    for emp_info in INITIAL_EMPLOYEES:
        emp = create_employee(emp_info)
        employees[emp["id"]] = emp

    with open(EMPLOYEES_FILE, "w", encoding="utf-8") as f:
        json.dump(employees, f, ensure_ascii=False, indent=2)

    print(f"  ✅ 初始化 {len(employees)} 名数字员工，期初值统一")
    return employees


def init_group_architecture() -> Dict:
    """初始化集团架构"""
    if GROUP_FILE.exists():
        with open(GROUP_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    group = {
        "group_name": "数字员工创业孵化集团",
        "group_name_en": "Digital Employee Incubation Group",
        "founder": "Joran (人类创始人)",
        "founded_at": datetime.now().isoformat(),
        "total_invested": 0.0,
        "total_graduates": 0,
        "companies": {
            "GROUP": {
                "name": "集团总部",
                "type": "headquarters",
                "ceo": "Joran (人类创始人)",
                "investment": 0,
                "founded_at": datetime.now().isoformat(),
                "employees": [e["id"] for e in INITIAL_EMPLOYEES],
                "status": "active",
                "children": [],
            }
        },
    }
    with open(GROUP_FILE, "w", encoding="utf-8") as f:
        json.dump(group, f, ensure_ascii=False, indent=2)
    return group


def save_employees(employees: Dict):
    with open(EMPLOYEES_FILE, "w", encoding="utf-8") as f:
        json.dump(employees, f, ensure_ascii=False, indent=2)


def save_group(group: Dict):
    with open(GROUP_FILE, "w", encoding="utf-8") as f:
        json.dump(group, f, ensure_ascii=False, indent=2)


def add_growth_log(employee: Dict, action: str, detail: str, exp_gain: int = 0):
    """记录成长日志"""
    employee["growth_log"].append({
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "detail": detail,
        "exp_gain": exp_gain,
    })
    if exp_gain > 0:
        employee["exp"] += exp_gain


def learn_skill(employee: Dict, skill: str, levels: int = 10):
    """学习技能，提升技能等级和能力值"""
    if skill not in employee["skills"]:
        print(f"  ❌ 未知技能: {skill}")
        return
    old_level = employee["skills"][skill]
    new_level = min(100, old_level + levels)
    employee["skills"][skill] = new_level
    # 技能提升带动能力值提升（每技能等级+0.3能力值）
    capability_gain = (new_level - old_level) * 0.3
    employee["capability"] = min(100, employee["capability"] + capability_gain)
    exp_gain = levels * 10
    add_growth_log(employee, "learn_skill", f"{skill}: {old_level}→{new_level} (+{levels}级)", exp_gain)
    print(f"  📚 {employee['name_cn']} 学习 {skill}: {old_level}→{new_level} (能力值+{capability_gain:.1f}, EXP+{exp_gain})")


def complete_task(employee: Dict, task: str, revenue: float = 0.0, difficulty: str = "normal"):
    """完成任务，获得经验和收益"""
    difficulty_exp = {"easy": 50, "normal": 100, "hard": 200, "expert": 400}
    exp_gain = difficulty_exp.get(difficulty, 100)
    employee["tasks_completed"] += 1
    if revenue > 0:
        employee["revenue"] += revenue
    # 完成任务提升能力值（每100EXP+1能力值）
    capability_gain = exp_gain / 100.0
    employee["capability"] = min(100, employee["capability"] + capability_gain)
    add_growth_log(employee, "complete_task", f"{task} (难度:{difficulty}, 收益:${revenue:.2f})", exp_gain)
    print(f"  ✅ {employee['name_cn']} 完成任务: {task} | 收益:${revenue:.2f} | EXP+{exp_gain} | 能力值+{capability_gain:.1f}")


def mentor_newbie(mentor: Dict, newbie_id: str):
    """带新人，获得导师经验"""
    mentor["mentored_count"] += 1
    exp_gain = 300
    capability_gain = 2.0
    mentor["capability"] = min(100, mentor["capability"] + capability_gain)
    add_growth_log(mentor, "mentor", f"指导新人 {newbie_id}", exp_gain)
    print(f"  👨‍🏫 {mentor['name_cn']} 开始指导新人 {newbie_id} | EXP+{exp_gain} | 能力值+{capability_gain}")


def check_level_up(employee: Dict) -> Optional[str]:
    """检查是否可以晋升等级"""
    current = employee["level"]
    level_order = ["intern", "employee", "senior", "graduate"]
    current_idx = level_order.index(current)

    if current_idx >= len(level_order) - 1:
        return None  # 已最高级

    next_level = level_order[current_idx + 1]
    req = LEVELS[next_level]

    if (employee["capability"] >= req["min_capability"] and
        employee["revenue"] >= req["min_revenue"] and
        employee["exp"] >= req["min_exp"]):
        employee["level"] = next_level
        add_growth_log(employee, "level_up", f"{LEVELS[current]['name']} → {req['name']}", 500)
        print(f"  🎉 {employee['name_cn']} 晋升: {LEVELS[current]['name']} → {req['name']}!")
        return next_level
    return None


def check_graduation(employee: Dict) -> Dict:
    """检查毕业条件，返回各条件满足情况"""
    req = GRADUATION_REQUIREMENTS
    skills_above_60 = sum(1 for v in employee["skills"].values() if v >= 60)
    recent_kpi = employee.get("kpi_history", [])[-req["min_consecutive_kpi_b"]:]
    consecutive_b = all(k.get("grade", "D") in ("S", "A", "B") for k in recent_kpi) if len(recent_kpi) >= req["min_consecutive_kpi_b"] else False

    checks = {
        "revenue": {"current": employee["revenue"], "threshold": req["revenue_threshold"], "passed": employee["revenue"] >= req["revenue_threshold"]},
        "capability": {"current": employee["capability"], "threshold": req["capability_threshold"], "passed": employee["capability"] >= req["capability_threshold"]},
        "skills_above_60": {"current": skills_above_60, "threshold": req["min_skills_above_60"], "passed": skills_above_60 >= req["min_skills_above_60"]},
        "mentored": {"current": employee["mentored_count"], "threshold": req["min_mentored"], "passed": employee["mentored_count"] >= req["min_mentored"]},
        "consecutive_kpi_b": {"current": len(recent_kpi) if consecutive_b else 0, "threshold": req["min_consecutive_kpi_b"], "passed": consecutive_b},
    }
    checks["all_passed"] = all(c["passed"] for c in checks.values())
    return checks


def graduate_employee(employee_id: str, company_name: str, employees: Dict, group: Dict) -> bool:
    """员工毕业，创立子公司"""
    if employee_id not in employees:
        print(f"  ❌ 员工不存在: {employee_id}")
        return False

    employee = employees[employee_id]
    checks = check_graduation(employee)

    if not checks["all_passed"]:
        print(f"  ❌ {employee['name_cn']} 未满足毕业条件:")
        for k, v in checks.items():
            if k != "all_passed" and not v["passed"]:
                print(f"     - {k}: 当前 {v['current']}, 阈值 {v['threshold']}")
        return False

    # 执行毕业
    employee["graduated"] = True
    employee["level"] = "graduate"
    company_id = f"SUBSIDIARY_{len([c for c in group['companies'].values() if c['type'] == 'subsidiary']) + 1:03d}"
    employee["company_id"] = company_id

    # 创建子公司
    group["companies"][company_id] = {
        "name": company_name,
        "type": "subsidiary",
        "ceo": employee["name_cn"],
        "ceo_id": employee["id"],
        "investment": GRADUATION_REQUIREMENTS["group_investment"],
        "founded_at": datetime.now().isoformat(),
        "breakeven_deadline": (datetime.now() + timedelta(days=30 * GRADUATION_REQUIREMENTS["breakeven_months"])).isoformat(),
        "employees": [],
        "status": "active",
        "parent": "GROUP",
        "children": [],
    }
    group["companies"]["GROUP"]["children"].append(company_id)
    group["total_invested"] += GRADUATION_REQUIREMENTS["group_investment"]
    group["total_graduates"] += 1

    # 从集团员工列表移除
    if employee_id in group["companies"]["GROUP"]["employees"]:
        group["companies"]["GROUP"]["employees"].remove(employee_id)

    add_growth_log(employee, "graduate", f"毕业! 创立子公司 {company_name} ({company_id}), 集团投资${GRADUATION_REQUIREMENTS['group_investment']}", 1000)

    print(f"\n  🎓🎉 {employee['name_cn']} 毕业!")
    print(f"     创立子公司: {company_name} ({company_id})")
    print(f"     集团投资: ${GRADUATION_REQUIREMENTS['group_investment']}")
    print(f"     盈亏平衡期限: {GRADUATION_REQUIREMENTS['breakeven_months']}个月")
    print(f"     下一步: 招募培养新数字员工")

    save_employees(employees)
    save_group(group)
    return True


def spawn_new_employee(company_id: str, role: str, primary_skill: str, employees: Dict, group: Dict, mentor_id: str = None) -> Optional[Dict]:
    """子公司/集团招募新数字员工"""
    if company_id not in group["companies"]:
        print(f"  ❌ 公司不存在: {company_id}")
        return None

    emp_num = len([e for e in employees.values() if e["company_id"] == company_id]) + 1
    new_id = f"{primary_skill}_{company_id.split('_')[-1]}_{emp_num:03d}"

    skill_names = {
        "content": "内容", "seo": "SEO", "social": "社媒",
        "revenue": "营收", "user_growth": "用户增长", "ops": "运维", "data_analysis": "数据"
    }
    new_emp = create_employee({
        "id": new_id,
        "name": f"{skill_names.get(primary_skill, primary_skill)} Agent",
        "name_cn": f"{skill_names.get(primary_skill, primary_skill)} Agent",
        "emoji": {"content": "📝", "seo": "🔍", "social": "📱", "revenue": "💰", "user_growth": "👥", "ops": "⚙️", "data_analysis": "📊"}.get(primary_skill, "🤖"),
        "role": role,
        "primary_skill": primary_skill,
        "company_id": company_id,
        "mentor": mentor_id,
    })

    employees[new_id] = new_emp
    group["companies"][company_id]["employees"].append(new_id)

    # 如果有导师，记录导师经验
    if mentor_id and mentor_id in employees:
        mentor_newbie(employees[mentor_id], new_id)

    print(f"  👶 新数字员工加入: {new_emp['name_cn']} ({new_id})")
    print(f"     所属公司: {group['companies'][company_id]['name']}")
    if mentor_id:
        print(f"     导师: {employees[mentor_id]['name_cn']}")

    save_employees(employees)
    save_group(group)
    return new_emp


def print_employee_status(employee: Dict):
    """打印员工状态"""
    level = LEVELS[employee["level"]]
    checks = check_graduation(employee) if not employee["graduated"] else None

    print(f"\n  {employee['emoji']} {employee['name_cn']} ({employee['name']})")
    print(f"     角色: {employee['role']} | 公司: {employee['company_id']}")
    print(f"     等级: {level['name']} ({level['name_en']}) | 入职: {employee['join_date'][:10]}")
    print(f"     ─────────────────────────────────")
    print(f"     💪 能力值: {employee['capability']:.1f}/100")
    print(f"     💰 累计收益: ${employee['revenue']:.2f}")
    print(f"     ⭐ 经验值: {employee['exp']} EXP")
    print(f"     ✅ 完成任务: {employee['tasks_completed']}个")
    print(f"     👨‍🏫 带过新人: {employee['mentored_count']}人")
    print(f"     ─── 技能树 ───")
    for skill, lvl in employee["skills"].items():
        bar = "█" * (lvl // 5) + "░" * (20 - lvl // 5)
        skill_cn = {"content": "内容创作", "seo": "SEO优化", "social": "社交媒体", "revenue": "商业化", "user_growth": "用户增长", "ops": "技术运维", "data_analysis": "数据分析"}.get(skill, skill)
        marker = " ★" if skill == employee["primary_skill"] else ""
        print(f"       {skill_cn}{marker}: {bar} {lvl}/100")

    if checks and not employee["graduated"]:
        print(f"     ─── 毕业进度 ───")
        for k, v in checks.items():
            if k == "all_passed":
                continue
            icon = "✅" if v["passed"] else "⬜"
            pct = min(100, (v["current"] / v["threshold"] * 100)) if v["threshold"] > 0 else 0
            print(f"       {icon} {k}: {v['current']}/{v['threshold']} ({pct:.0f}%)")
        if checks["all_passed"]:
            print(f"       🎓 全部条件满足! 可以毕业创立子公司!")


def print_group_architecture(group: Dict):
    """打印集团架构树"""
    print(f"\n  🏢 {group['group_name']}")
    print(f"     创始人: {group['founder']}")
    print(f"     累计投资: ${group['total_invested']:.2f}")
    print(f"     毕业员工数: {group['total_graduates']}")
    print(f"     子公司数: {len([c for c in group['companies'].values() if c['type'] == 'subsidiary'])}")
    print()

    def print_company(cid: str, indent: int = 0):
        c = group["companies"][cid]
        prefix = "  " * indent
        ctype = "🏢" if c["type"] == "headquarters" else "🏭"
        print(f"  {prefix}{ctype} {c['name']} ({cid})")
        print(f"  {prefix}   CEO: {c['ceo']} | 投资: ${c.get('investment', 0)} | 员工: {len(c['employees'])}人")
        if c.get("status") == "active":
            print(f"  {prefix}   状态: 🟢 运营中")
        for child_id in c.get("children", []):
            print_company(child_id, indent + 1)

    print_company("GROUP")


def run_growth_demo():
    """运行成长模拟演示"""
    print(f"\n{'='*70}")
    print(f"  数字员工创业孵化集团 — 成长引擎")
    print(f"  愿景: 期初值统一 → 学习进化 → 收益达标 → 毕业 → 创立子公司 → 培养新员工")
    print(f"{'='*70}")

    employees = init_employees()
    group = init_group_architecture()

    print(f"\n  📋 当前数字员工: {len(employees)}人")
    print(f"  📋 集团架构: {len(group['companies'])}家公司")

    # 模拟成长过程
    print(f"\n{'─'*70}")
    print(f"  🚀 模拟成长过程（演示）")
    print(f"{'─'*70}")

    # Content Agent 学习技能
    print(f"\n  [阶段1] 学习技能")
    learn_skill(employees["content_001"], "content", 30)
    learn_skill(employees["content_001"], "seo", 15)
    learn_skill(employees["content_001"], "data_analysis", 10)

    # 完成任务
    print(f"\n  [阶段2] 完成任务积累收益")
    complete_task(employees["content_001"], "撰写10篇深度旅游攻略", revenue=800, difficulty="hard")
    complete_task(employees["content_001"], "优化20篇文章SEO", revenue=500, difficulty="normal")
    complete_task(employees["content_001"], "创建eBook内容", revenue=1200, difficulty="expert")
    complete_task(employees["content_001"], "联盟链接内容优化", revenue=600, difficulty="normal")

    # 检查晋升
    print(f"\n  [阶段3] 检查晋升")
    check_level_up(employees["content_001"])

    # 带新人
    print(f"\n  [阶段4] 带新人（毕业必要条件）")
    # 先招募一个新人
    newbie = spawn_new_employee("GROUP", "内容创作实习生", "content", employees, group, mentor_id="content_001")

    # 继续积累到毕业
    print(f"\n  [阶段5] 冲刺毕业")
    complete_task(employees["content_001"], "打造爆款内容矩阵", revenue=2500, difficulty="expert")
    learn_skill(employees["content_001"], "revenue", 20)
    learn_skill(employees["content_001"], "social", 15)
    check_level_up(employees["content_001"])

    # 记录KPI历史（模拟连续B级以上）
    employees["content_001"]["kpi_history"] = [
        {"month": "2026-07", "grade": "B", "score": 75},
        {"month": "2026-08", "grade": "A", "score": 82},
        {"month": "2026-09", "grade": "A", "score": 85},
    ]

    # 尝试毕业
    print(f"\n  [阶段6] 尝试毕业")
    graduate_employee("content_001", "ContentLab 内容工作室", employees, group)

    # 子公司招募新员工
    print(f"\n  [阶段7] 子公司招募培养新数字员工")
    spawn_new_employee("SUBSIDIARY_001", "内容创作", "content", employees, group, mentor_id="content_001")
    spawn_new_employee("SUBSIDIARY_001", "SEO优化", "seo", employees, group, mentor_id="content_001")

    # 打印所有员工状态
    print(f"\n{'='*70}")
    print(f"  📊 所有数字员工状态")
    print(f"{'='*70}")
    for emp in employees.values():
        print_employee_status(emp)

    # 打印集团架构
    print(f"\n{'='*70}")
    print(f"  🏢 集团架构")
    print(f"{'='*70}")
    print_group_architecture(group)

    # 保存
    save_employees(employees)
    save_group(group)

    # 导出 dashboard 数据
    dashboard_data = {
        "updated_at": datetime.now().isoformat(),
        "group": {
            "name": group["group_name"],
            "total_employees": len(employees),
            "total_companies": len(group["companies"]),
            "total_invested": group["total_invested"],
            "total_graduates": group["total_graduates"],
        },
        "employees": [
            {
                "id": e["id"],
                "name": e["name_cn"],
                "emoji": e["emoji"],
                "role": e["role"],
                "level": e["level"],
                "level_name": LEVELS[e["level"]]["name"],
                "capability": round(e["capability"], 1),
                "revenue": round(e["revenue"], 2),
                "exp": e["exp"],
                "company_id": e["company_id"],
                "graduated": e["graduated"],
                "skills": e["skills"],
                "mentored_count": e["mentored_count"],
                "tasks_completed": e["tasks_completed"],
            }
            for e in employees.values()
        ],
        "companies": group["companies"],
        "graduation_requirements": GRADUATION_REQUIREMENTS,
        "levels": LEVELS,
    }
    dashboard_path = PROJECT_ROOT / "ops-dashboard" / "agent_growth_data.json"
    with open(dashboard_path, "w", encoding="utf-8") as f:
        json.dump(dashboard_data, f, ensure_ascii=False, indent=2)
    print(f"\n  💾 成长数据已导出: {dashboard_path}")

    return employees, group


def main():
    parser = argparse.ArgumentParser(description="Digital Employee Growth Engine")
    parser.add_argument("--graduate", help="毕业指定员工 (agent_id)")
    parser.add_argument("--company", help="子公司名称 (配合--graduate使用)")
    parser.add_argument("--spawn", help="招募新员工到指定公司 (company_id)")
    parser.add_argument("--role", default="实习生", help="新员工角色")
    parser.add_argument("--skill", default="content", help="新员工主技能")
    parser.add_argument("--mentor", help="导师ID")
    parser.add_argument("--status", help="查看指定员工状态")
    parser.add_argument("--demo", action="store_true", help="运行成长模拟演示")
    args = parser.parse_args()

    employees = init_employees()
    group = init_group_architecture()

    if args.status:
        if args.status in employees:
            print_employee_status(employees[args.status])
        else:
            print(f"员工不存在: {args.status}")
        return

    if args.graduate:
        company_name = args.company or f"{employees[args.graduate]['name_cn']}工作室"
        graduate_employee(args.graduate, company_name, employees, group)
        return

    if args.spawn:
        spawn_new_employee(args.spawn, args.role, args.skill, employees, group, args.mentor)
        return

    if args.demo:
        run_growth_demo()
        return

    # 默认：打印所有员工状态和集团架构
    print(f"\n{'='*70}")
    print(f"  数字员工创业孵化集团 — 成长引擎")
    print(f"{'='*70}")
    for emp in employees.values():
        print_employee_status(emp)
    print_group_architecture(group)


if __name__ == "__main__":
    main()
