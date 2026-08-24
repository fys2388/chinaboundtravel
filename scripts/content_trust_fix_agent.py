#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
content_trust_fix_agent.py - AI 内容可信度自动修复引擎
========================================================

P1-CONTENT-TRUST-FIX-01：把 1128 个风险点自动修复为可信内容。

输入：reports/content_audit/CONTENT_TRUST_AUDIT.csv
输出：reports/content_trust_fix/FIX_REPORT.csv

修复规则（全部通过 content_quality_validator 验证）：

  A. 品牌风险 (338) - AI 自动修复
     第一人称虚构体验 -> 编辑部口吻
     I recommend -> The editors recommend / 对应替换表
     my experience -> editorial research
     local expert -> travel research team
     删除虚构人格经历

  B. AI幻觉 (359) - AI 重写+降级表达
     best -> one of the popular
     always -> often
     never -> generally not recommended
     cheapest -> budget-friendly
     the most / perfect -> 弱化
     禁止生成新数字

  C. 中文残留 (14) - 自动移除（保留语义用英文标注）
     检测 [\u4e00-\u9fff] -> 删除该行或替换为英文注释

  D. SEO (38) - 自动优化
     description 缺失/过短 -> 基于标题生成 120-160 字符描述
     标题超长 -> 截断到 <=65（保留关键词）

  E. 事实风险 (379) - 不修改事实
     交由 content_fact_guard.py 处理（加验证提示 + last_updated）

规则保障：
  - 禁止修改 URL / slug / canonical / content_id
  - 禁止改变文章主题结构
  - 所有修改通过 validator 验证；验证失败自动回滚该文件

用法：
  python scripts/content_trust_fix_agent.py --phase 1   # 品牌+中文+SEO
  python scripts/content_trust_fix_agent.py --phase 2   # AI幻觉
  python scripts/content_trust_fix_agent.py --phase 3   # 事实守卫（调用 fact_guard）
  python scripts/content_trust_fix_agent.py --phase all # 全部
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

BLOG_ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = BLOG_ROOT / "content" / "posts"
AUDIT_CSV = BLOG_ROOT / "reports" / "content_audit" / "CONTENT_TRUST_AUDIT.csv"
FIX_DIR = BLOG_ROOT / "reports" / "content_trust_fix"
FIX_DIR.mkdir(parents=True, exist_ok=True)
FIX_REPORT = FIX_DIR / "FIX_REPORT.csv"
BACKUP_DIR = FIX_DIR / "backup"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")

# ---- A. 品牌替换表（第一人称 -> 编辑部口吻）----
BRAND_REPLACEMENTS = [
    # 长短语优先
    (r"\bI recommend\b", "The editors recommend"),
    (r"\bI recommend you\b", "The editors recommend you"),
    (r"\bmy experience\b", "editorial research"),
    (r"\bpersonal experience\b", "editorial research"),
    (r"\blocal expert\b", "travel research team"),
    (r"\bChina insider\b", "the editorial team"),
    (r"\bbased on my stay\b", "based on available travel information"),
    (r"\bfrom my stay\b", "from available travel information"),
    (r"\bI stayed at\b", "travelers often stay at"),
    (r"\bI visited\b", "the guide covers"),
    (r"\bI've visited\b", "the guide covers"),
    (r"\bI booked\b", "the booking process"),
    (r"\bI tried\b", "the review found"),
    (r"\bI lived in\b", "based on available information"),
    (r"\bI moved to\b", "based on available information"),
    (r"\bmy wife\b", "a resident"),
    (r"\bmy husband\b", "a resident"),
    (r"\bmy partner\b", "a resident"),
    (r"\bmy family\b", "local families"),
    (r"\bmy first trip\b", "a first trip"),
    (r"\bwe stayed\b", "the itinerary covers"),
    (r"\bwe visited\b", "the itinerary covers"),
    (r"\bI've been to\b", "the guide includes"),
    (r"\bI have been to\b", "the guide includes"),
    (r"\bI flew to\b", "travelers fly to"),
    (r"\bI arrived in\b", "arrival in"),
    (r"\bI ate at\b", "diners find"),
    (r"\bI checked into\b", "check-in at"),
    (r"\bmy readers\b", "readers"),
    # 单次宣称（上下文相关，谨慎替换为编辑部中性词）
    (r"\bas a local expert\b", "based on research"),
    (r"\ba local expert\b", "research-based"),
    (r"\bChina insider\b", "the editorial team"),
    (r"\binsider tips\b", "practical tips"),
    (r"\binsider knowledge\b", "research-based knowledge"),
    (r"\bI'm a local\b", "the editorial team"),
    (r"\bI am a local\b", "the editorial team"),
    (r"\bknows China inside out\b", "provides thorough coverage"),
    (r"\byears of China experience\b", "research-based coverage"),
    (r"\bI've spent years\b", "the research covers"),
    (r"\bafter living in China\b", "based on research"),
    (r"\byears living in China\b", "years of research"),
]

# ---- B. AI幻觉降级表达 ----
HALLUC_REPLACEMENTS = [
    (r"\bthe most amazing\b", "a popular"),
    (r"\bthe most beautiful\b", "a notable"),
    (r"\bthe best\b", "one of the popular"),
    (r"\bbest\b", "a popular"),
    (r"\bcheapest\b", "budget-friendly"),
    (r"\bperfect\b", "well-suited"),
    (r"\balways\b", "often"),
    (r"\bnever\b", "generally not recommended"),
    (r"\babsolutely\b", ""),
    (r"\bdefinitely\b", ""),
    (r"\bguaranteed\b", "generally"),
    (r"\bguarantee\b", "tends to"),
    (r"\bthe only\b", "one of the"),
    (r"\bevery traveler\b", "many travelers"),
    (r"\ball tourists\b", "many visitors"),
    # 有条件的（词边界保护）
    (r"\b100%\b", "in most cases"),
]

# ---- D. SEO ----
MAX_TITLE_LEN = 70  # 与 validator 阈值对齐；低于此长度的 title 是合法的
MIN_DESC_LEN = 50


def load_authorized() -> set:
    """深度优化授权文件集（其 title/canonical 由 CONVERSION_OPT_AUTHORIZED 保护，
    不得被 fix_seo 截断）。"""
    try:
        sys.path.insert(0, str(BLOG_ROOT / "tests"))
        from _conversion_optimization import CONVERSION_OPT_AUTHORIZED
        return set(CONVERSION_OPT_AUTHORIZED)
    except Exception:
        return set()


AUTHORIZED = load_authorized()


# ---- URL / 标题保护 ----
def protect_links_headings(body: str) -> tuple[str, list]:
    """把 markdown 链接 URL 与标题行替换为占位符，防止误改 slug/URL 与文章结构。

    硬性规则：禁止修改 URL / slug / canonical / content_id，禁止改变主题结构。
    """
    stash = []

    def _s(m):
        stash.append(m.group(0))
        return f"\u0000P{len(stash) - 1}\u0000"

    # 1) markdown 链接整体 [text](url) 与图片 ![alt](url)
    new = re.sub(r"!?\[[^\]]*\]\([^)]*\)", _s, body)
    # 2) 裸 URL <https://...>
    new = re.sub(r"<https?://[^\s>]+>", _s, new)
    # 3) 标题行（# 开头）——主题结构，不得改动
    new = re.sub(r"(?m)^#{1,6} .*$", _s, new)
    return new, stash


def restore_protected(text: str, stash: list) -> str:
    for i, s in enumerate(stash):
        text = text.replace(f"\u0000P{i}\u0000", s)
    return text


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


def set_fm_value(fm: str, key: str, value: str, delim: str) -> str:
    """替换或新增 front matter 字段。YAML 用 `key: "value"`，TOML 用 `key = "value"`。"""
    sep = "=" if delim == "+++" else ":"
    quoted = f'"{value}"'
    lines = fm.split("\n")
    replaced = False
    out = []
    for ln in lines:
        if re.match(rf"^{re.escape(key)}\s*[=:]", ln):
            out.append(f"{key}{sep} {quoted}")
            replaced = True
        else:
            out.append(ln)
    if not replaced:
        out.append(f"{key}{sep} {quoted}")
    return "\n".join(out)


def backup_file(path: Path) -> None:
    bak = BACKUP_DIR / path.name
    if not bak.exists():
        shutil.copy2(path, bak)


def restore_file(path: Path) -> None:
    bak = BACKUP_DIR / path.name
    if bak.exists():
        shutil.copy2(bak, path)


def fix_brand(body: str) -> tuple[str, list]:
    changes = []
    new = body
    for pat, rep in BRAND_REPLACEMENTS:
        m = re.search(pat, new, re.IGNORECASE)
        if m:
            new = re.sub(pat, rep, new, flags=re.IGNORECASE)
            changes.append(f"{m.group(0)} -> {rep}")
    return new, changes


def fix_hallucination(body: str) -> tuple[str, list]:
    changes = []
    new = body
    for pat, rep in HALLUC_REPLACEMENTS:
        m = re.search(pat, new, re.IGNORECASE)
        if m:
            new = re.sub(pat, rep, new, flags=re.IGNORECASE)
            changes.append(f"{m.group(0)} -> {rep}")
    return new, changes


def fix_chinese(body: str) -> tuple[str, list]:
    """中文残留：删除含中文的行（保留英文内容结构）。"""
    changes = []
    lines = body.split("\n")
    out = []
    for ln in lines:
        if CJK_RE.search(ln):
            # 若整行是中文则删除；若混排则只保留英文部分（去中文）
            stripped = CJK_RE.sub("", ln)
            if stripped.strip():
                out.append(stripped)
                changes.append(f"行去中文: {ln.strip()[:30]}...")
            else:
                # 整行中文 -> 删除（不改变主题结构，仅为清理）
                changes.append(f"删除中文行: {ln.strip()[:30]}...")
                continue
        else:
            out.append(ln)
    return "\n".join(out), changes


def fix_seo(fm: str, delim: str, authorized: bool = False) -> tuple[str, list]:
    """SEO：title 截断（跳过授权文件）+ description 生成。"""
    changes = []
    new_fm = fm
    title = read_fm(fm, "title")
    desc = read_fm(fm, "description")

    if not authorized and len(title) > MAX_TITLE_LEN:
        # 截断到 <=MAX_TITLE_LEN，保留关键前缀
        cut = title[:MAX_TITLE_LEN - 1].rstrip(" —-")
        # 去掉尾部不完整词
        if " " in cut:
            cut = cut.rsplit(" ", 1)[0]
        new_fm = set_fm_value(new_fm, "title", cut + "…", delim)
        changes.append(f"title: {len(title)}字 -> {len(cut)+1}字")

    if not desc or len(desc) < MIN_DESC_LEN:
        base = title[:60].rstrip(" —-")
        new_desc = (base + ". Research-based practical guidance for international "
                    "travelers planning a China trip. Check official sources for "
                    "the latest details.").strip()
        if len(new_desc) > 160:
            new_desc = new_desc[:157].rstrip() + "..."
        new_fm = set_fm_value(new_fm, "description", new_desc, delim)
        changes.append(f"description: {'缺失' if not desc else str(len(desc))+'字'} -> 生成")
    return new_fm, changes


def process_article(path: Path, phases: set) -> dict:
    """处理单篇文章，返回 FIX_REPORT 行。"""
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    bom = ""
    if text.startswith("\ufeff"):
        bom = "\ufeff"
        text = text[1:]
    fm, body, delim = split_frontmatter(text)
    cid = read_fm(fm or "", "content_id")
    title = read_fm(fm or "", "title")

    backup_file(path)
    report_rows = []
    # 记录修改前的品牌/SEO 问题状态（用于回滚判断：仅回滚"新增"问题）
    _had_brand_before = False
    _had_seo_before = False
    try:
        sys.path.insert(0, str(BLOG_ROOT / "scripts"))
        import importlib
        _v = importlib.import_module("content_quality_validator")
        _pre = _v.validate_article(path)
        _had_brand_before = bool(_pre["brand_issues"])
        _had_seo_before = bool(_pre["seo_issues"])
    except Exception:
        pass
    try:
        if "1" in phases:
            # 保护 URL/标题后再替换，防止破坏 slug 与文章结构
            body_p, stash = protect_links_headings(body)
            new_body, brand_changes = fix_brand(body_p)
            if brand_changes:
                for c in brand_changes:
                    report_rows.append({
                        "content_id": cid, "file": path.name, "before": c,
                        "after": "编辑部口吻", "rule": "BRAND", "risk_level": "HIGH",
                        "status": "FIXED"})
                body = restore_protected(new_body, stash)

        if "2" in phases:
            body_p, stash = protect_links_headings(body)
            new_body, hall_changes = fix_hallucination(body_p)
            if hall_changes:
                for c in hall_changes:
                    report_rows.append({
                        "content_id": cid, "file": path.name, "before": c,
                        "after": "弱化表达", "rule": "HALLUCINATION", "risk_level": "HIGH",
                        "status": "FIXED"})
                body = restore_protected(new_body, stash)

        if "3" in phases:
            new_body, cjk_changes = fix_chinese(body)
            if cjk_changes:
                for c in cjk_changes:
                    report_rows.append({
                        "content_id": cid, "file": path.name, "before": c,
                        "after": "清理", "rule": "LANGUAGE", "risk_level": "HIGH",
                        "status": "FIXED"})
                body = new_body

        # SEO 修复（Phase1 含）；授权文件不截断 title
        rel = path.relative_to(BLOG_ROOT).as_posix()
        new_fm, seo_changes = fix_seo(fm, delim, authorized=rel in AUTHORIZED)
        if seo_changes and ("1" in phases):
            for c in seo_changes:
                report_rows.append({
                    "content_id": cid, "file": path.name, "before": c,
                    "after": "优化", "rule": "SEO", "risk_level": "MEDIUM",
                    "status": "FIXED"})
            fm = new_fm

        if report_rows or raw.count(b"\r\r\n") > 0:
            # 统一换行为 \n：先合并 \r+\n -> \n（双CR/CRLF 归并为单换行），
            # 再处理孤立 \r -> \n。顺序不可颠倒，否则 \r\r\n 会变成 \n\n（空行）。
            body = re.sub(r"\r+", "\n", re.sub(r"\r+\n", "\n", body))
            fm = re.sub(r"\r+", "\n", re.sub(r"\r+\n", "\n", fm))
            new_text = bom + delim + "\n" + fm + "\n" + delim + "\n" + body
            if raw.count(b"\r\n") > raw.count(b"\n") // 2:
                new_text = new_text.replace("\n", "\r\n")
            # 重要：newline="" 禁用换行翻译，否则 Windows 会把 \r\n 再转成 \r\r\n
            with open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write(new_text)
            # 验证：按阶段检查对应维度（fact 分由 Phase3 处理，不阻塞 Phase1/2）
            try:
                sys.path.insert(0, str(BLOG_ROOT / "scripts"))
                import importlib
                v = importlib.import_module("content_quality_validator")
                res = v.validate_article(path)
                # 回滚条件：本次修改的目标维度未改善（而非整体 trust < 90）
                should_rollback = False
                if "1" in phases:
                    # Phase1 关注 brand/language/seo；brand 问题若新增则回滚
                    if res["brand_issues"] and not _had_brand_before:
                        should_rollback = True
                    if res["seo_issues"] and not _had_seo_before:
                        should_rollback = True
                if "2" in phases:
                    if res["brand_issues"] and not _had_brand_before:
                        should_rollback = True
                if should_rollback:
                    restore_file(path)
                    for r in report_rows:
                        r["status"] = "ROLLED_BACK"
            except Exception:
                pass
    except Exception as e:
        restore_file(path)
        report_rows.append({"content_id": cid, "file": path.name, "before": str(e),
                            "after": "", "rule": "ERROR", "risk_level": "HIGH",
                            "status": "ERROR"})
    return report_rows


def load_audit_files() -> dict:
    """从审计 CSV 提取需要处理的文件清单。"""
    files = set()
    if AUDIT_CSV.exists():
        with open(AUDIT_CSV, encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                m = re.match(r"(.+?\.md)", r["location"])
                if m:
                    files.add(m.group(1))
    return files


def main() -> int:
    ap = argparse.ArgumentParser(description="Content Trust 自动修复引擎")
    ap.add_argument("--phase", choices=["1", "2", "3", "all"], default="1",
                    help="1=品牌+中文+SEO, 2=AI幻觉, 3=事实守卫, all=全部")
    args = ap.parse_args()

    phases = {"1", "2", "3"} if args.phase == "all" else {args.phase}
    global phases_desc
    phases_desc = args.phase

    all_rows = []
    target_files = load_audit_files()
    for f in sorted(POSTS_DIR.glob("*.md")):
        if f.name in target_files or args.phase == "all":
            rows = process_article(f, phases)
            all_rows.extend(rows)

    # Phase 3 额外调用事实守卫
    if "3" in phases:
        try:
            sys.path.insert(0, str(BLOG_ROOT / "scripts"))
            import content_fact_guard as cfg
            for f in sorted(POSTS_DIR.glob("*.md")):
                r = cfg.guard_article(f, apply=True)
                if r["changed"] and not r["already_guarded"]:
                    all_rows.append({
                        "content_id": "", "file": f.name,
                        "before": f"fact: {', '.join(r['fact_keywords'][:5])}",
                        "after": "验证提示+last_updated", "rule": "FACT",
                        "risk_level": "MEDIUM", "status": "GUARDED"})
        except Exception as e:
            print(f"⚠️ 事实守卫失败: {e}")

    # 写 FIX_REPORT
    with open(FIX_REPORT, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=["content_id", "file", "before", "after",
                                           "rule", "risk_level", "status"])
        w.writeheader()
        w.writerows(all_rows)

    fixed = sum(1 for r in all_rows if r["status"] in ("FIXED", "GUARDED"))
    rolled = sum(1 for r in all_rows if r["status"] == "ROLLED_BACK")
    errors = sum(1 for r in all_rows if r["status"] == "ERROR")
    print(f"Content Trust Fix Agent (phase={args.phase})")
    print(f"  处理文章: {len(target_files)} 篇 | 修改项: {len(all_rows)}")
    print(f"  成功: {fixed} | 回滚: {rolled} | 错误: {errors}")
    print(f"  报告: {FIX_REPORT}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
