#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P1-CONTENT-TRUST-AUDIT-01: ChinaBound Travel 内容真实性与品牌一致性审计
========================================================================

对 content/posts/*.md 的 60 篇文章执行只读审计（禁止修改任何 content 文件）。

检查维度：
  A. 中文残留     - 中文字符、中国内部表达（对国际读者不透明）
  B. AI幻觉风险   - 虚构个人经历、无来源数据、绝对化描述
  C. 品牌风险     - 第一人称体验、年限宣称、expert/local 等（复用 governance 规则）
  D. 事实风险     - 交通规则/签证政策/价格/时间/营业信息（快速变化的动态事实）
  E. SEO 问题     - title/description/heading/内部链接质量

输出：
  reports/content_audit/CONTENT_TRUST_AUDIT.csv
  reports/content_audit/CONTENT_TRUST_SUMMARY.md

用法：
  python scripts/content_trust_audit.py
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

BLOG_ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = BLOG_ROOT / "content" / "posts"
OUT_DIR = BLOG_ROOT / "reports" / "content_audit"
OUT_DIR.mkdir(parents=True, exist_ok=True)
CSV_OUT = OUT_DIR / "CONTENT_TRUST_AUDIT.csv"
MD_OUT = OUT_DIR / "CONTENT_TRUST_SUMMARY.md"

GOVERNANCE = BLOG_ROOT / "config" / "content_governance.json"

# 单文章各维度最大 issue 记录数（避免单个文件刷屏）
MAX_PER_ISSUE = 8


def load_forbidden() -> list:
    if GOVERNANCE.exists():
        try:
            data = json.loads(GOVERNANCE.read_text(encoding="utf-8-sig"))
            return data.get("persona", {}).get("forbidden_phrases", [])
        except Exception:
            pass
    return []


FORBIDDEN_PHRASES = load_forbidden()

# ---- A. 中文残留 ----
CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")

# ---- B. AI幻觉风险 ----
# 虚构个人经历（与 persona_guard / brand_identity_audit 一致）
FICTIONAL_RE = re.compile(
    r"personally (tested|used|use|recommend)|"
    r"\bmy wife\b|\bmy husband\b|\bmy partner\b|\bmy family\b|"
    r"\bI (stayed|visited|booked|tried|ate at|flew to|arrived in)\b|"
    r"\bwe (stayed|visited)\b|\bmy first trip\b|"
    r"\bI (lived|moved) (in|to)\b|\bI've (been|lived) in\b|\bI have (been|lived) in\b",
    re.IGNORECASE,
)
# 无来源的绝对化/夸大
ABSOLUTE_RE = re.compile(
    r"\b(100%|guarantee|guaranteed|best|cheapest|most amazing|absolutely|definitely|"
    r"always|never|every traveler|all tourists|the only)\b",
    re.IGNORECASE,
)
# 无来源数字/统计（疑似编造）
UNSOURCED_NUM_RE = re.compile(
    r"\b\d{2,3}[,%]\b|\b\$\d[\d,.]*|\b\d+\s*(?:million|billion|km|miles|yuan|rmb|CNY)\b",
    re.IGNORECASE,
)

# ---- C. 品牌风险 ----
BRAND_RE = re.compile(
    r"\bI\b|\bmy experience\b|\bmy\b|\bI'm\b|\bI've\b|\bI'll\b|"
    r"\b\d+\s*years? living in China\b|\b\d+\s*-year expat\b|"
    r"\bexpert\b|\blocal\b|\binsider\b|\bsecret\b",
    re.IGNORECASE,
)

# ---- D. 事实风险（快速变化的动态事实关键词） ----
FACT_KEYWORDS = [
    "visa", "visa-free", "144-hour", "240-hour", "transit", "immigration",
    "price", "prices", "cost", "costs", "fee", "fees", "charge", "charges",
    "open", "opens", "closes", "hours", "营业", "operating hours",
    "high-speed rail", "train schedule", "ticket price", "fare",
    "law", "legal", "regulation", "policy", "rules", "restriction",
    "passport", "entry requirement",
]
FACT_RE = re.compile(r"\b(" + "|".join(FACT_KEYWORDS) + r")\b", re.IGNORECASE)

# 营业时间/价格模式
TIME_PRICE_RE = re.compile(
    r"\b\d{1,2}:\d{2}\s*(?:am|pm|AM|PM)?\b|\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*\b|"
    r"\b\$\d[\d,.]*|\b\d+\s*(?:yuan|rmb|CNY)\b|\b\d{4}-\d{2}-\d{2}\b",
)

# ---- E. SEO 问题 ----
HEADING_RE = re.compile(r"^#{1,3}\s+(.+)$", re.MULTILINE)
INTERNAL_LINK_RE = re.compile(r"\[[^\]]*\]\((/[^)#]+)\)")
EXTERNAL_LINK_RE = re.compile(r"\[[^\]]*\]\((https?://[^)#]+)\)")


def split_frontmatter(text: str):
    for delim in ("---", "+++"):
        ed = re.escape(delim)
        m = re.match(r"^%s\s*\n(.*?)\n%s\s*\n" % (ed, ed), text, re.DOTALL)
        if m:
            return m.group(1), text[m.end():], delim
    return None, text, ""


def read_fm(fm: str, key: str) -> str:
    m = re.search(rf'^{key}\s*[=:]\s*["\']?([^"\'\n#]+)', fm, re.MULTILINE)
    return m.group(1).strip().strip('"').strip("'") if m else ""


def line_of(text: str, pattern: re.Pattern, start: int = 0) -> str:
    """返回匹配出现的行号（约）。"""
    m = pattern.search(text, start)
    if not m:
        return "body"
    line = text.count("\n", 0, m.start()) + 1
    return f"L{line}"


def audit_article(path: Path) -> tuple:
    """返回 (rows, extra_stats)。rows 为 CSV 行 dict 列表。"""
    text = path.read_text(encoding="utf-8", errors="replace")
    fm_text, body, delim = split_frontmatter(text)
    fm = fm_text or ""
    content_id = read_fm(fm, "content_id")
    title = read_fm(fm, "title")
    desc = read_fm(fm, "description")
    slug = read_fm(fm, "slug") or path.stem

    rows = []
    seen = Counter()

    def add(issue_type, location, suggestion, fixable):
        key = issue_type
        if seen[key] >= MAX_PER_ISSUE:
            return
        seen[key] += 1
        rows.append({
            "content_id": content_id,
            "title": title,
            "risk_level": "HIGH" if issue_type in ("AI幻觉", "品牌风险", "中文残留") else "MEDIUM",
            "issue_type": issue_type,
            "location": f"{path.name}:{location}",
            "suggestion": suggestion,
            "auto_fix_possible": "yes" if fixable else "no",
        })

    # ---- A. 中文残留 ----
    cjk = CJK_RE.findall(body)
    if cjk:
        add("中文残留", line_of(text, CJK_RE), "正文含中文字符，国际读者无法理解；翻译为英文或移除", True)

    # ---- B. AI幻觉风险 ----
    for m in FICTIONAL_RE.finditer(body):
        loc = f"L{text.count(chr(10), 0, m.start()) + 1}"
        add("AI幻觉", loc, f"虚构个人经历: '{m.group(0)[:40]}'；改为编辑部研究性表述", True)
    for m in ABSOLUTE_RE.finditer(body):
        loc = f"L{text.count(chr(10), 0, m.start()) + 1}"
        add("AI幻觉", loc, f"绝对化/无依据描述: '{m.group(0)}'；补充来源或弱化语气", True)
    # 无来源数字（排除 front matter date/weight）
    body_wo_fm = body
    for m in UNSOURCED_NUM_RE.finditer(body_wo_fm):
        loc = f"L{text.count(chr(10), 0, m.start()) + 1}"
        add("AI幻觉", loc, f"无来源数据: '{m.group(0)}'；标注来源或移除", False)
        if seen["AI幻觉"] >= MAX_PER_ISSUE:
            break

    # ---- C. 品牌风险 ----
    for m in BRAND_RE.finditer(body):
        loc = f"L{text.count(chr(10), 0, m.start()) + 1}"
        add("品牌风险", loc, f"第一人称/本地宣称: '{m.group(0)}'；改用编辑部口吻", True)
        if seen["品牌风险"] >= MAX_PER_ISSUE:
            break

    # 显式年限宣称
    for pat in (r"\d+\s*years? (?:living|in) China", r"\d+\s*-year expat", r"decade(s)? (?:in|of) China"):
        for m in re.finditer(pat, body, re.IGNORECASE):
            loc = f"L{text.count(chr(10), 0, m.start()) + 1}"
            add("品牌风险", loc, f"年限/身份宣称: '{m.group(0)}'；移除虚构身份", True)

    # ---- D. 事实风险 ----
    fact_hits = set(FACT_RE.findall(body.lower()))
    for kw in list(fact_hits)[:MAX_PER_ISSUE]:
        add("事实风险", "body", f"动态事实关键词 '{kw}'：需核对最新官方信息并注明日期", False)
    for m in TIME_PRICE_RE.finditer(body):
        loc = f"L{text.count(chr(10), 0, m.start()) + 1}"
        add("事实风险", loc, f"价格/时间/营业信息: '{m.group(0)}'；需注明更新日期", False)
        if seen["事实风险"] >= MAX_PER_ISSUE:
            break

    # ---- E. SEO 问题 ----
    if len(title) > 65:
        add("SEO问题", "frontmatter:title", f"标题过长({len(title)}字>65)；建议精简含核心关键词", True)
    if len(title) < 20:
        add("SEO问题", "frontmatter:title", f"标题过短({len(title)}字<20)；补充长尾关键词", True)
    if not desc:
        add("SEO问题", "frontmatter:description", "缺少 meta description；补充 120-160 字符描述", True)
    elif len(desc) > 160:
        add("SEO问题", "frontmatter:description", f"description 过长({len(desc)}字>160)；精简", True)
    elif len(desc) < 50:
        add("SEO问题", "frontmatter:description", f"description 过短({len(desc)}字<50)；补充关键词", True)
    # heading 质量
    h2_count = len(re.findall(r"^##\s+", body, re.MULTILINE))
    if h2_count < 2:
        add("SEO问题", "body", f"正文仅 {h2_count} 个 H2 标题；建议增加小节以利 SEO", True)
    # 内部链接
    internal = INTERNAL_LINK_RE.findall(body)
    if len(internal) < 2:
        add("SEO问题", "body", f"内部链接仅 {len(internal)} 条；建议补充 3-5 条相关内链", True)

    # 统计
    stats = {
        "cjk_count": len(cjk),
        "fictional_hits": len(FICTIONAL_RE.findall(body)),
        "absolute_hits": len(ABSOLUTE_RE.findall(body)),
        "brand_hits": len(BRAND_RE.findall(body)),
        "fact_kws": len(fact_hits),
        "h2_count": h2_count,
        "internal_links": len(internal),
        "external_links": len(EXTERNAL_LINK_RE.findall(body)),
        "word_count": len(re.findall(r"[A-Za-z]+", body)),
    }
    return rows, stats


def main() -> int:
    all_rows = []
    per_article = {}
    for f in sorted(POSTS_DIR.glob("*.md")):
        rows, stats = audit_article(f)
        all_rows.extend(rows)
        per_article[f.stem] = {"rows": rows, "stats": stats}

    # ---- CSV ----
    with open(CSV_OUT, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=["content_id", "title", "risk_level",
                                           "issue_type", "location", "suggestion",
                                           "auto_fix_possible"])
        w.writeheader()
        w.writerows(all_rows)

    # ---- Summary MD ----
    total_articles = len(per_article)
    articles_with_issues = sum(1 for a in per_article.values() if a["rows"])
    issue_types = Counter(r["issue_type"] for r in all_rows)
    risk_levels = Counter(r["risk_level"] for r in all_rows)
    total_issues = len(all_rows)

    lines = [
        "# P1-CONTENT-TRUST-AUDIT-01 内容信任审计报告",
        "",
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 概述",
        "",
        f"- 审计文章数: **{total_articles}**",
        f"- 存在问题文章: **{articles_with_issues}**（{round(articles_with_issues/max(total_articles,1)*100,1)}%）",
        f"- 问题总数: **{total_issues}**",
        "",
        "> 本审计为**只读**：未修改任何 content 文件。",
        "",
        "## 问题类型分布",
        "",
        "| 问题类型 | 数量 | 严重度 |",
        "| :--- | :--- | :--- |",
    ]
    type_sev = {"中文残留": "HIGH", "AI幻觉": "HIGH", "品牌风险": "HIGH",
                "事实风险": "MEDIUM", "SEO问题": "MEDIUM"}
    for t, n in issue_types.most_common():
        lines.append(f"| {t} | {n} | {type_sev.get(t, 'MEDIUM')} |")
    lines += ["", "## 风险等级分布", "", "| 等级 | 数量 |", "| :--- | :--- |"]
    for lv in ("HIGH", "MEDIUM", "LOW"):
        if risk_levels.get(lv):
            lines.append(f"| {lv} | {risk_levels[lv]} |")
    lines += ["", "## 各文章问题清单", ""]
    for stem in sorted(per_article):
        info = per_article[stem]
        if not info["rows"]:
            continue
        lines.append(f"### {info['rows'][0]['title']} (`{stem}`)")
        lines.append("")
        lines.append("| 类型 | 位置 | 建议 | 可自动修复 |")
        lines.append("| :--- | :--- | :--- | :--- |")
        for r in info["rows"]:
            lines.append(f"| {r['issue_type']} | {r['location']} | {r['suggestion']} | {r['auto_fix_possible']} |")
        lines.append("")
    MD_OUT.write_text("\n".join(lines), encoding="utf-8")

    print(f"审计完成: {total_articles} 篇文章, {total_issues} 个问题")
    print(f"  CSV: {CSV_OUT}")
    print(f"  MD:  {MD_OUT}")
    print(f"  问题类型: {dict(issue_types)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
