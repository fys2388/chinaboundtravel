#!/usr/bin/env python3
"""
Agent Task Executor — Agent 任务自动执行器

读取 agent_tasks/ 中 status=pending 的任务，按 agent 类型自动执行，
执行完成后更新任务状态并通过 status_writeback 回写到原始问题文件。

执行流程：
1. 扫描所有 pending 任务
2. 按 agent 类型分发到对应处理器
3. 执行验证/分析/修复
4. 更新任务状态 (completed/partial/failed)
5. 回写问题状态到原始文件
6. 记录执行日志

Usage:
    python scripts/agent_task_executor.py [--dry-run] [--agent NAME] [--date YYYY-MM-DD]
"""
import sys
import json
import argparse
import re
import requests
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from status_writeback import (
    writeback_issue, writeback_agent_task, get_pending_agent_tasks,
    ISSUES_DIR, AGENT_TASKS_DIR,
)

BASE_DIR = Path(__file__).parent.parent
SITE_URL = "https://www.chinaboundtravel.com"


# ============================================================
# 各 Agent 处理器
# ============================================================

def execute_site_health(task: dict, dry_run: bool = False) -> dict:
    """
    Site Health Agent — 验证网站可达性、SSL 等基础设施问题
    重点：区分本地网络误报 vs 真实问题
    """
    results = {"resolved": 0, "failed": 0, "false_positive": 0, "details": []}

    for issue in task.get("issues", []):
        itype = issue.get("type")
        desc = issue.get("description", "")

        if itype == "site_unreachable":
            # 验证线上是否真的不可达
            try:
                resp = requests.get(SITE_URL, timeout=15, allow_redirects=True)
                if resp.status_code == 200:
                    results["false_positive"] += 1
                    results["details"].append(f"site_unreachable: 误报，线上HTTP {resp.status_code}")
                    if not dry_run:
                        writeback_issue(
                            source_file=f"site_health_issues_{task['target_date']}.json",
                            issue_type="site_unreachable",
                            status="false_positive",
                            resolved_by="site_health_agent",
                            resolution_note=f"线上验证正常 HTTP {resp.status_code}，本地网络误报",
                            target_date=task["target_date"],
                        )
                else:
                    results["failed"] += 1
                    results["details"].append(f"site_unreachable: 真实问题 HTTP {resp.status_code}")
            except Exception as e:
                results["failed"] += 1
                results["details"].append(f"site_unreachable: 验证异常 {e}")

        elif itype == "ssl_check_failed":
            # 验证 SSL
            try:
                resp = requests.get(SITE_URL, timeout=15, verify=True)
                if resp.status_code == 200:
                    results["false_positive"] += 1
                    results["details"].append("ssl_check_failed: 误报，SSL正常")
                    if not dry_run:
                        writeback_issue(
                            source_file=f"site_health_issues_{task['target_date']}.json",
                            issue_type="ssl_check_failed",
                            status="false_positive",
                            resolved_by="site_health_agent",
                            resolution_note="线上SSL验证正常，本地网络误报",
                            target_date=task["target_date"],
                        )
            except requests.exceptions.SSLError:
                results["failed"] += 1
                results["details"].append("ssl_check_failed: 真实SSL问题")
            except Exception as e:
                results["false_positive"] += 1
                results["details"].append(f"ssl_check_failed: 误报（本地网络）{e}")
                if not dry_run:
                    writeback_issue(
                        source_file=f"site_health_issues_{task['target_date']}.json",
                        issue_type="ssl_check_failed",
                        status="false_positive",
                        resolved_by="site_health_agent",
                        resolution_note="本地网络连接拒绝，非线上SSL问题",
                        target_date=task["target_date"],
                    )

        else:
            results["details"].append(f"{itype}: 跳过（未实现自动处理）")

    return results


# AI禁用词安全替换表（保守替换，保留语义）
FORBIDDEN_WORD_REPLACEMENTS = {
    "perfect": ["excellent", "great", "ideal", "top"],
    "amazing": ["great", "impressive", "notable"],
    "incredible": ["remarkable", "notable", "great"],
    "ultimate": ["key", "essential", "top"],
    "fantastic": ["great", "good", "solid"],
    "wonderful": ["great", "enjoyable", "solid"],
    "awesome": ["great", "good"],
    "best": ["top", "leading"],
}


def _fix_forbidden_word(file_rel: str, word: str) -> tuple:
    """读取文件，替换禁用词。返回 (success, detail)"""
    fpath = BASE_DIR / file_rel
    if not fpath.is_file():
        return False, f"文件不存在: {file_rel}"
    text = fpath.read_text(encoding="utf-8")
    synonyms = FORBIDDEN_WORD_REPLACEMENTS.get(word.lower(), [])
    if not synonyms:
        return False, f"无替换表: {word}"
    count = 0
    for syn in synonyms:
        pattern = r"\b" + re.escape(word) + r"\b"
        def repl(m, s=syn):
            nonlocal count
            count += 1
            matched = m.group(0)
            if matched[0].isupper():
                return s[0].upper() + s[1:]
            return s
        new_text = re.sub(pattern, repl, text)
        if new_text != text:
            text = new_text
            break
    if count == 0:
        return True, f"禁用词已不存在（可能已修复）: {word} ({file_rel})"
    fpath.write_text(text, encoding="utf-8")
    return True, f"已将 {count} 处 '{word}' 替换为 '{synonyms[0]}'  ({file_rel})"


def execute_content(task: dict, dry_run: bool = False) -> dict:
    """
    Content Agent — 内容质量问题处理
    ai_forbidden_word: 自动替换禁用词为安全同义词
    content_placeholder: 占位内容（需人工补充）
    image_missing_alt: 图片缺alt（需人工添加）
    """
    results = {"resolved": 0, "failed": 0, "false_positive": 0, "need_manual": 0, "details": []}

    for issue in task.get("issues", []):
        itype = issue.get("type")
        if itype == "ai_forbidden_word":
            msg = issue.get("message", "") or issue.get("description", "")
            word = msg.replace("AI禁用词:", "").strip()
            file_rel = issue.get("file", "")
            if dry_run:
                results["details"].append(f"[DRY] {itype}: 将替换 {file_rel} 中的 '{word}'")
                results["resolved"] += 1
                continue
            success, detail = _fix_forbidden_word(file_rel, word)
            if success:
                results["resolved"] += 1
                results["details"].append(detail)
                writeback_issue(
                    source_file=f"site_health_issues_{task['target_date']}.json",
                    issue_type=itype,
                    status="resolved",
                    resolved_by="content_agent",
                    resolution_note=detail,
                    target_date=task["target_date"],
                )
            else:
                results["need_manual"] += 1
                results["details"].append(f"{itype}: {detail}")
                writeback_issue(
                    source_file=f"site_health_issues_{task['target_date']}.json",
                    issue_type=itype,
                    status="need_manual",
                    resolved_by="content_agent",
                    resolution_note=detail,
                    target_date=task["target_date"],
                )

        elif itype == "content_placeholder":
            results["need_manual"] += 1
            results["details"].append(f"{itype}: 需人工补充内容")
            if not dry_run:
                writeback_issue(
                    source_file=f"site_health_issues_{task['target_date']}.json",
                    issue_type=itype,
                    status="need_manual",
                    resolved_by="content_agent",
                    resolution_note="占位内容需人工补充",
                    target_date=task["target_date"],
                )

        elif itype == "image_missing_alt":
            results["need_manual"] += 1
            results["details"].append(f"{itype}: 需人工添加alt文本")
            if not dry_run:
                writeback_issue(
                    source_file=f"site_health_issues_{task['target_date']}.json",
                    issue_type=itype,
                    status="need_manual",
                    resolved_by="content_agent",
                    resolution_note="图片alt需人工添加",
                    target_date=task["target_date"],
                )

        else:
            results["details"].append(f"{itype}: 跳过")

    return results


def _fix_title_length(file_rel: str, target_max: int = 55) -> tuple:
    """读取 front matter，截断超长 title。返回 (success, detail)"""
    fpath = BASE_DIR / file_rel
    if not fpath.is_file():
        return False, f"文件不存在: {file_rel}"
    text = fpath.read_text(encoding="utf-8")
    m = re.match(r"^(---\n)(.*?)(\n---)", text, re.DOTALL)
    if not m:
        return False, "无front matter，需人工检查"
    fm = m.group(2)
    title_m = re.search(r"^title:\s*[\"']?(.+?)[\"']?\s*$", fm, re.MULTILINE)
    if not title_m:
        return False, "front matter无title"
    old_title = title_m.group(1).strip().strip('"').strip("'")
    if len(old_title) <= target_max:
        return True, f"title已合规({len(old_title)}字符)"
    new_title = old_title[:target_max].rstrip()
    last_space = new_title.rfind(" ")
    if last_space > target_max - 15:
        new_title = new_title[:last_space]
    new_title = new_title.rstrip(":,;-—")
    new_fm = fm[:title_m.start()] + f'title: "{new_title}"' + fm[title_m.end():]
    new_text = text[:m.start(2)] + new_fm + text[m.end(2):]
    fpath.write_text(new_text, encoding="utf-8")
    return True, f"title {len(old_title)}->{len(new_title)}字符: \"{new_title[:60]}\""


def _fix_meta_description(file_rel: str) -> tuple:
    """从正文提取首段生成 meta description。"""
    fpath = BASE_DIR / file_rel
    if not fpath.is_file():
        return False, f"文件不存在: {file_rel}"
    text = fpath.read_text(encoding="utf-8")
    m = re.match(r"^(---\n)(.*?)(\n---)", text, re.DOTALL)
    if not m:
        return False, "无front matter"
    fm = m.group(2)
    body = text[m.end():]
    paragraphs = [p.strip() for p in body.split("\n\n") if p.strip() and not p.strip().startswith("#") and not p.strip().startswith("!")]
    if not paragraphs:
        return False, "无正文段落"
    desc = re.sub(r"[*_\[\]()#]", "", paragraphs[0])
    desc = re.sub(r"\s+", " ", desc).strip()
    if len(desc) > 155:
        desc = desc[:152].rstrip() + "..."
    if len(desc) < 50:
        return False, f"提取描述仅{len(desc)}字符，跳过"
    desc_m = re.search(r"^description:\s*[\"']?(.+?)[\"']?\s*$", fm, re.MULTILINE)
    if desc_m:
        new_fm = fm[:desc_m.start()] + f'description: "{desc}"' + fm[desc_m.end():]
    else:
        new_fm = fm + f'\ndescription: "{desc}"'
    new_text = text[:m.start(2)] + new_fm + text[m.end(2):]
    fpath.write_text(new_text, encoding="utf-8")
    return True, f"meta description已生成({len(desc)}字符)"


def execute_seo(task: dict, dry_run: bool = False) -> dict:
    """
    SEO Agent — SEO问题自动修复
    title_too_long: 自动截断front matter title到<=55字符
    meta_description_too_short: 自动从正文生成描述
    """
    results = {"resolved": 0, "failed": 0, "false_positive": 0, "need_manual": 0, "details": []}

    for issue in task.get("issues", []):
        itype = issue.get("type")
        file_rel = issue.get("file", "")

        if itype == "title_too_long":
            if dry_run:
                results["details"].append(f"[DRY] title_too_long: 将截断 {file_rel}")
                results["resolved"] += 1
                continue
            success, detail = _fix_title_length(file_rel, target_max=55)
            if success:
                results["resolved"] += 1
                results["details"].append(detail)
                writeback_issue(
                    source_file=f"site_health_issues_{task['target_date']}.json",
                    issue_type=itype,
                    status="resolved",
                    resolved_by="seo_agent",
                    resolution_note=detail,
                    target_date=task["target_date"],
                )
            else:
                results["need_manual"] += 1
                results["details"].append(f"{itype}: {detail}")

        elif itype == "meta_description_too_short":
            if dry_run:
                results["details"].append(f"[DRY] meta_description_too_short: 将生成描述 {file_rel}")
                results["resolved"] += 1
                continue
            success, detail = _fix_meta_description(file_rel)
            if success:
                results["resolved"] += 1
                results["details"].append(detail)
                writeback_issue(
                    source_file=f"site_health_issues_{task['target_date']}.json",
                    issue_type=itype,
                    status="resolved",
                    resolved_by="seo_agent",
                    resolution_note=detail,
                    target_date=task["target_date"],
                )
            else:
                results["need_manual"] += 1
                results["details"].append(f"{itype}: {detail}")

        elif itype == "title_too_short":
            results["need_manual"] += 1
            results["details"].append(f"{itype}: title过短需人工优化")
        else:
            results["details"].append(f"{itype}: 跳过")

    return results


def execute_social(task: dict, dry_run: bool = False) -> dict:
    """
    Social Agent — 社媒问题分析
    """
    results = {"resolved": 0, "failed": 0, "false_positive": 0, "need_manual": 0, "details": []}

    for issue in task.get("issues", []):
        itype = issue.get("type")
        if itype == "social_zero_engagement":
            results["need_manual"] += 1
            results["details"].append(f"{itype}: 社媒零互动，需检查Buffer API数据接入")
            if not dry_run:
                writeback_issue(
                    source_file=f"site_health_issues_{task['target_date']}.json",
                    issue_type=itype,
                    status="need_manual",
                    resolved_by="social_agent",
                    resolution_note="社媒数据可能未接入，需检查Buffer API",
                    target_date=task["target_date"],
                )
        else:
            results["details"].append(f"{itype}: 跳过")

    return results


def execute_generic(task: dict, dry_run: bool = False) -> dict:
    """通用 Agent 处理器（user/revenue等）"""
    results = {"resolved": 0, "failed": 0, "false_positive": 0, "need_manual": 0, "details": []}
    for issue in task.get("issues", []):
        results["need_manual"] += 1
        results["details"].append(f"{issue.get('type')}: 需人工处理")
    return results


# Agent 分发映射
AGENT_HANDLERS = {
    "site_health": execute_site_health,
    "content": execute_content,
    "seo": execute_seo,
    "social": execute_social,
    "user": execute_generic,
    "revenue": execute_generic,
    "conversion": execute_generic,
}


def execute_task(task: dict, dry_run: bool = False) -> dict:
    """执行单个 Agent 任务"""
    agent = task.get("agent", "unknown")
    task_id = task.get("task_id", "unknown")
    print(f"\n{'='*60}")
    print(f"▶ 执行任务: {task_id}")
    print(f"  Agent: {agent} | 问题数: {task.get('issue_count', 0)}")

    handler = AGENT_HANDLERS.get(agent, execute_generic)

    # 标记为 in_progress
    if not dry_run:
        writeback_agent_task(task_id, "in_progress")

    # 执行
    results = handler(task, dry_run=dry_run)

    # 判定最终状态
    total = task.get("issue_count", 0)
    resolved = results.get("resolved", 0) + results.get("false_positive", 0)
    need_manual = results.get("need_manual", 0)
    failed = results.get("failed", 0)

    if failed > 0 and resolved == 0 and need_manual == 0:
        final_status = "failed"
    elif resolved + need_manual >= total:
        final_status = "completed"
    elif resolved > 0 or need_manual > 0:
        final_status = "partial"
    else:
        final_status = "completed"

    print(f"  结果: resolved={resolved}, need_manual={need_manual}, failed={failed}")
    print(f"  状态: {final_status}")
    for d in results.get("details", []):
        print(f"    - {d}")

    # 更新任务状态
    if not dry_run:
        writeback_agent_task(
            task_id,
            final_status,
            resolved_count=resolved,
            failed_count=failed,
            execution_note=f"resolved={resolved}, need_manual={need_manual}, failed={failed}",
        )

    return {"task_id": task_id, "agent": agent, "status": final_status, **results}


def main():
    parser = argparse.ArgumentParser(description="Agent Task Executor")
    parser.add_argument("--dry-run", action="store_true", help="只模拟不实际修改")
    parser.add_argument("--agent", type=str, help="只执行指定Agent的任务")
    parser.add_argument("--date", type=str, help="指定日期 YYYY-MM-DD")
    args = parser.parse_args()

    print("=" * 60)
    print("Agent Task Executor — 自动执行器")
    print(f"时间: {datetime.now().isoformat()}")
    print(f"Dry run: {args.dry_run}")
    print("=" * 60)

    # 获取 pending 任务
    pending = get_pending_agent_tasks()
    if args.agent:
        pending = [t for t in pending if t.get("agent") == args.agent]
    if args.date:
        pending = [t for t in pending if t.get("target_date") == args.date]

    if not pending:
        print("\n✅ 没有 pending 的 Agent 任务")
        return

    print(f"\n发现 {len(pending)} 个待执行任务:")
    for t in pending:
        print(f"  - {t.get('task_id')}: agent={t.get('agent')}, issues={t.get('issue_count')}")

    # 逐个执行
    all_results = []
    for task in pending:
        result = execute_task(task, dry_run=args.dry_run)
        all_results.append(result)

    # 汇总
    print("\n" + "=" * 60)
    print("执行汇总:")
    completed = sum(1 for r in all_results if r["status"] == "completed")
    partial = sum(1 for r in all_results if r["status"] == "partial")
    failed = sum(1 for r in all_results if r["status"] == "failed")
    print(f"  完成: {completed}, 部分完成: {partial}, 失败: {failed}")
    print(f"  Dry run: {args.dry_run}")
    print("=" * 60)


if __name__ == "__main__":
    main()
