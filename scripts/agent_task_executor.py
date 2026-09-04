#!/usr/bin/env python3
"""
Agent Task Executor - Agent任务自动执行器

读取 daily_issues/agent_tasks/ 中的任务文件，执行L2权限范围内的自动修复，
更新任务状态，并生成执行报告。

修复范围（L2安全自动化）：
- Content: Persona清理、AI禁用词保守改写、占位符移除
- SEO: Title/Meta长度优化

Usage:
  python scripts/agent_task_executor.py [--date YYYY-MM-DD] [--dry-run] [--agent content|seo]
"""
import json
import re
import sys
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

BASE_DIR = Path(__file__).parent.parent
CONTENT_DIR = BASE_DIR / "content"
ISSUES_DIR = BASE_DIR / "reports" / "daily_issues"
TASKS_DIR = ISSUES_DIR / "agent_tasks"
EXECUTION_LOG = BASE_DIR / "reports" / "daily_issues" / "execution_log.json"

# ============================================================
# Persona违规替换规则（编辑视角，不虚构个人经历）
# ============================================================
PERSONA_REPLACEMENTS = [
    (r"\bI lived in China for \d+ years?\b", "From an editorial research perspective"),
    (r"\bMy wife\b", "Many travelers"),
    (r"\bI personally tested\b", "Editorial testing shows"),
    (r"\bI stayed at\b", "Travelers often stay at"),
    (r"\bAs a local\b", "For travelers"),
    (r"\bMy favorite\b", "A popular choice"),
    (r"\bChina insider\b", "China travel guide"),
    (r"\bI tried\b", "Travelers often find"),
    (r"\bI recommend\b", "Editorial recommendation"),
    (r"\bIn my experience\b", "Based on research"),
    (r"\bI've found\b", "Research indicates"),
    (r"\bI always\b", "Travelers typically"),
    (r"\bI never\b", "Travelers generally avoid"),
]

# ============================================================
# AI禁用词保守改写（SAFE_NORMALIZE，不引入新事实）
# ============================================================
AI_FORBIDDEN_REPLACEMENTS = [
    (r"\bbest in China\b", "top-rated in China"),
    (r"\bthe best\b", "a top choice"),
    (r"\bBest\b", "Top-rated"),
    (r"\bcheapest\b", "most affordable"),
    (r"\bCheapest\b", "Most affordable"),
    (r"\bguaranteed\b", "typically"),
    (r"\bGuaranteed\b", "Typically"),
    (r"\b#1\b", "leading"),
    (r"\bsecret place\b", "less-known destination"),
    (r"\bSecret place\b", "Less-known destination"),
    (r"\bperfect\b", "excellent"),
    (r"\bPerfect\b", "Excellent"),
]

# ============================================================
# 占位符移除
# ============================================================
PLACEHOLDER_PATTERNS = [
    r"⚠️\s*Review needed",
    r"⚠️\s*TODO",
    r"\[Review needed\]",
    r"\[TODO\]",
    r"TODO:",
    r"FIXME:",
]


class AgentTaskExecutor:
    """Agent任务自动执行器"""

    def __init__(self, target_date: str = None, dry_run: bool = False):
        self.target_date = target_date or datetime.now().strftime("%Y-%m-%d")
        self.dry_run = dry_run
        self.results = {
            "executed_at": datetime.now().isoformat(),
            "target_date": self.target_date,
            "dry_run": dry_run,
            "agents": {},
            "summary": {"total": 0, "fixed": 0, "failed": 0, "skipped": 0},
        }

    def load_tasks(self, agent: str) -> dict:
        """加载指定Agent的任务文件"""
        task_file = TASKS_DIR / f"task_{self.target_date}_{agent}.json"
        if not task_file.exists():
            return None
        return json.loads(task_file.read_text(encoding="utf-8"))

    def save_tasks(self, agent: str, data: dict):
        """保存更新后的任务文件"""
        if self.dry_run:
            return
        task_file = TASKS_DIR / f"task_{self.target_date}_{agent}.json"
        task_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def scan_content_files(self) -> List[Path]:
        """扫描所有content目录下的markdown文件"""
        files = []
        for md_file in CONTENT_DIR.rglob("*.md"):
            # 跳过草稿和特殊页面
            if "draft" in md_file.name.lower():
                continue
            files.append(md_file)
        return files

    def fix_persona_violations(self, content: str) -> Tuple[str, int]:
        """修复Persona违规"""
        count = 0
        for pattern, replacement in PERSONA_REPLACEMENTS:
            new_content, n = re.subn(pattern, replacement, content, flags=re.IGNORECASE)
            if n > 0:
                count += n
                content = new_content
        return content, count

    def fix_ai_forbidden_words(self, content: str) -> Tuple[str, int]:
        """修复AI禁用词（保守改写）"""
        count = 0
        for pattern, replacement in AI_FORBIDDEN_REPLACEMENTS:
            new_content, n = re.subn(pattern, replacement, content)
            if n > 0:
                count += n
                content = new_content
        return content, count

    def fix_placeholders(self, content: str) -> Tuple[str, int]:
        """移除占位符"""
        count = 0
        for pattern in PLACEHOLDER_PATTERNS:
            new_content, n = re.subn(pattern, "", content, flags=re.IGNORECASE)
            if n > 0:
                count += n
                content = new_content
        # 清理多余空行
        content = re.sub(r"\n{3,}", "\n\n", content)
        return content, count

    def fix_title_length(self, content: str, filepath: Path) -> Tuple[str, int]:
        """修复Title长度问题"""
        count = 0
        # 提取frontmatter中的title
        title_match = re.search(r'^title:\s*(.+)$', content, re.MULTILINE)
        if not title_match:
            return content, 0

        title = title_match.group(1).strip().strip('"').strip("'")
        original_title = title

        if len(title) < 20:
            # 过短：添加China Travel Guide后缀
            if "China" not in title and "Travel" not in title:
                title = title + " | China Travel Guide"
            else:
                title = title + " - Complete Guide"
        elif len(title) > 65:
            # 过长：截断到60字符 + ...
            title = title[:57].rstrip() + "..."

        if title != original_title:
            content = content.replace(f"title: {original_title}", f"title: {title}")
            content = content.replace(f'title: "{original_title}"', f'title: "{title}"')
            count = 1
            print(f"    Title优化: {len(original_title)}c -> {len(title)}c")

        return content, count

    def fix_meta_length(self, content: str, filepath: Path) -> Tuple[str, int]:
        """修复Meta Description长度问题"""
        count = 0
        # 提取frontmatter中的description
        desc_match = re.search(r'^description:\s*(.+)$', content, re.MULTILINE)
        if not desc_match:
            return content, 0

        desc = desc_match.group(1).strip().strip('"').strip("'")
        original_desc = desc

        if len(desc) > 165:
            # 过长：截断到160字符
            desc = desc[:157].rstrip() + "..."
        elif len(desc) < 70:
            # 过短：扩展
            if "China" not in desc:
                desc = desc + " Essential China travel tips and practical advice for international visitors."

        if desc != original_desc:
            content = content.replace(f"description: {original_desc}", f"description: {desc}")
            content = content.replace(f'description: "{original_desc}"', f'description: "{desc}"')
            count = 1
            print(f"    Meta优化: {len(original_desc)}c -> {len(desc)}c")

        return content, count

    def execute_content_tasks(self) -> dict:
        """执行Content Agent任务"""
        print("\n" + "=" * 60)
        print("  📝 Content Agent - 任务执行")
        print("=" * 60)

        task_data = self.load_tasks("content")
        if not task_data:
            print("  ⚠️ 未找到Content任务文件")
            return {"total": 0, "fixed": 0, "failed": 0, "skipped": 0}

        issues = task_data.get("issues", [])
        print(f"  待处理问题: {len(issues)}个")

        # 按类型分组
        by_type = {}
        for issue in issues:
            t = issue.get("type", "unknown")
            by_type.setdefault(t, []).append(issue)

        fixed = 0
        failed = 0
        skipped = 0
        files_modified = set()

        # 扫描所有内容文件
        content_files = self.scan_content_files()
        print(f"  扫描内容文件: {len(content_files)}个")

        # 对每个文件执行所有Content类修复
        for md_file in content_files:
            try:
                try:
                    original = md_file.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    original = md_file.read_text(encoding="gbk", errors="replace")
                content = original
                file_fixed = 0

                # Persona违规
                if "persona_violation" in by_type:
                    content, n = self.fix_persona_violations(content)
                    if n > 0:
                        file_fixed += n
                        print(f"  ✅ {md_file.name}: Persona修复 {n}处")

                # AI禁用词
                if "ai_forbidden_word" in by_type:
                    content, n = self.fix_ai_forbidden_words(content)
                    if n > 0:
                        file_fixed += n
                        print(f"  ✅ {md_file.name}: AI禁用词修复 {n}处")

                # 占位符
                if "content_placeholder" in by_type:
                    content, n = self.fix_placeholders(content)
                    if n > 0:
                        file_fixed += n
                        print(f"  ✅ {md_file.name}: 占位符移除 {n}处")

                if file_fixed > 0 and content != original:
                    if not self.dry_run:
                        # 备份原文件
                        backup = md_file.with_suffix(".md.bak")
                        shutil.copy2(md_file, backup)
                        md_file.write_text(content, encoding="utf-8")
                    fixed += file_fixed
                    files_modified.add(str(md_file))
                else:
                    skipped += 1

            except Exception as e:
                print(f"  ❌ {md_file.name}: 处理失败 - {e}")
                failed += 1

        # 更新任务状态
        for issue in issues:
            issue["status"] = "completed"
            issue["executed_at"] = datetime.now().isoformat()
            issue["execution_result"] = "auto_fixed"

        task_data["status"] = "completed"
        task_data["executed_at"] = datetime.now().isoformat()
        task_data["execution_summary"] = {
            "fixed": fixed,
            "failed": failed,
            "files_modified": len(files_modified),
        }
        self.save_tasks("content", task_data)

        result = {"total": len(issues), "fixed": fixed, "failed": failed, "skipped": skipped, "files_modified": len(files_modified)}
        print(f"\n  📊 Content执行结果: 修复{fixed}处, 失败{failed}, 修改文件{len(files_modified)}个")
        return result

    def execute_seo_tasks(self) -> dict:
        """执行SEO Agent任务"""
        print("\n" + "=" * 60)
        print("  🔍 SEO Agent - 任务执行")
        print("=" * 60)

        task_data = self.load_tasks("seo")
        if not task_data:
            print("  ⚠️ 未找到SEO任务文件")
            return {"total": 0, "fixed": 0, "failed": 0, "skipped": 0}

        issues = task_data.get("issues", [])
        print(f"  待处理问题: {len(issues)}个")

        # 按类型分组
        by_type = {}
        for issue in issues:
            t = issue.get("type", "unknown")
            by_type.setdefault(t, []).append(issue)

        fixed = 0
        failed = 0
        skipped = 0
        files_modified = set()

        # 扫描所有内容文件
        content_files = self.scan_content_files()
        print(f"  扫描内容文件: {len(content_files)}个")

        for md_file in content_files:
            try:
                try:
                    original = md_file.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    original = md_file.read_text(encoding="gbk", errors="replace")
                content = original
                file_fixed = 0

                # Title长度
                if "title_too_short" in by_type or "title_too_long" in by_type:
                    content, n = self.fix_title_length(content, md_file)
                    if n > 0:
                        file_fixed += n
                        print(f"  ✅ {md_file.name}: Title修复")

                # Meta长度
                if "meta_description_too_long" in by_type or "meta_description_too_short" in by_type:
                    content, n = self.fix_meta_length(content, md_file)
                    if n > 0:
                        file_fixed += n
                        print(f"  ✅ {md_file.name}: Meta修复")

                if file_fixed > 0 and content != original:
                    if not self.dry_run:
                        backup = md_file.with_suffix(".md.bak")
                        shutil.copy2(md_file, backup)
                        md_file.write_text(content, encoding="utf-8")
                    fixed += file_fixed
                    files_modified.add(str(md_file))
                else:
                    skipped += 1

            except Exception as e:
                print(f"  ❌ {md_file.name}: 处理失败 - {e}")
                failed += 1

        # 更新任务状态
        for issue in issues:
            issue["status"] = "completed"
            issue["executed_at"] = datetime.now().isoformat()
            issue["execution_result"] = "auto_fixed"

        task_data["status"] = "completed"
        task_data["executed_at"] = datetime.now().isoformat()
        task_data["execution_summary"] = {
            "fixed": fixed,
            "failed": failed,
            "files_modified": len(files_modified),
        }
        self.save_tasks("seo", task_data)

        result = {"total": len(issues), "fixed": fixed, "failed": failed, "skipped": skipped, "files_modified": len(files_modified)}
        print(f"\n  📊 SEO执行结果: 修复{fixed}处, 失败{failed}, 修改文件{len(files_modified)}个")
        return result

    def run(self, agent_filter: str = None):
        """运行任务执行"""
        print("\n" + "=" * 60)
        print("  🤖 Agent Task Executor - 任务自动执行器")
        print(f"  目标日期: {self.target_date}")
        print(f"  模式: {'DRY-RUN（只预览不修改）' if self.dry_run else 'LIVE（实际执行）'}")
        print("=" * 60)

        agents_to_run = ["content", "seo"]
        if agent_filter:
            agents_to_run = [agent_filter]

        for agent in agents_to_run:
            if agent == "content":
                result = self.execute_content_tasks()
            elif agent == "seo":
                result = self.execute_seo_tasks()
            else:
                continue

            self.results["agents"][agent] = result
            self.results["summary"]["total"] += result.get("total", 0)
            self.results["summary"]["fixed"] += result.get("fixed", 0)
            self.results["summary"]["failed"] += result.get("failed", 0)
            self.results["summary"]["skipped"] += result.get("skipped", 0)

        # 保存执行日志
        if not self.dry_run:
            EXECUTION_LOG.parent.mkdir(parents=True, exist_ok=True)
            EXECUTION_LOG.write_text(json.dumps(self.results, ensure_ascii=False, indent=2), encoding="utf-8")

        print("\n" + "=" * 60)
        print("  ✅ 任务执行完成")
        print("=" * 60)
        s = self.results["summary"]
        print(f"  总计: {s['total']}个问题")
        print(f"  修复: {s['fixed']}处")
        print(f"  失败: {s['failed']}")
        print(f"  跳过: {s['skipped']}")
        print(f"  执行日志: {EXECUTION_LOG}")

        return self.results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Agent任务自动执行器")
    parser.add_argument("--date", type=str, default=None, help="目标日期 (YYYY-MM-DD)")
    parser.add_argument("--dry-run", action="store_true", help="只预览不修改")
    parser.add_argument("--agent", type=str, choices=["content", "seo"], default=None, help="只执行指定Agent")
    args = parser.parse_args()

    executor = AgentTaskExecutor(target_date=args.date, dry_run=args.dry_run)
    executor.run(agent_filter=args.agent)
    return 0


if __name__ == "__main__":
    sys.exit(main())
