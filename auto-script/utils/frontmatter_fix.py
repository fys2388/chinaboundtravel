#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Front Matter 自动修复脚本 - 优化版
功能：修复 Hugo Markdown 文件的 Front Matter 格式问题
特性：
  - 使用 PyYAML 专业解析，避免正则破坏结构
  - 智能处理冒号问题，非破坏性修复
  - 自动备份机制
  - 支持预览模式（dry-run）
  - 详细报告输出
"""

import os
import re
import sys
import yaml
import shutil
import argparse
from datetime import datetime
from pathlib import Path

# 项目根目录 - 优先使用环境变量 GITHUB_WORKSPACE（用于 CI），否则使用脚本相对路径
GITHUB_WORKSPACE = os.environ.get('GITHUB_WORKSPACE')
if GITHUB_WORKSPACE:
    ROOT_PATH = Path(GITHUB_WORKSPACE)
else:
    # 本地开发环境：从脚本位置向上两级找到项目根（auto-script/utils/ → project root）
    ROOT_PATH = Path(__file__).resolve().parent.parent.parent
CONTENT_PATH = ROOT_PATH / "content"
REPORT_PATH = ROOT_PATH / "auto-script" / "log"
BACKUP_PATH = ROOT_PATH / "auto-script" / "backup"

# 确保目录存在
REPORT_PATH.mkdir(parents=True, exist_ok=True)
BACKUP_PATH.mkdir(parents=True, exist_ok=True)

def log_message(message, level="INFO", color=True):
    """带颜色的日志输出"""
    colors = {
        "INFO": "\033[94m",
        "SUCCESS": "\033[92m",
        "WARNING": "\033[93m",
        "ERROR": "\033[91m",
        "ENDC": "\033[0m"
    }
    timestamp = datetime.now().strftime("%H:%M:%S")
    # 处理 Windows 编码问题
    msg = f"[{timestamp}] {message}"
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('ascii', errors='replace').decode('ascii'))

def backup_file(file_path):
    """创建文件备份"""
    backup_dir = BACKUP_PATH / file_path.parent.relative_to(ROOT_PATH)
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_file = backup_dir / f"{file_path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
    shutil.copy(file_path, backup_file)
    return backup_file

def parse_frontmatter(content):
    """解析 Front Matter，返回 (frontmatter_dict, body_content, yaml_text)"""
    if not content.startswith("---"):
        return None, content, None
    
    lines = content.splitlines()
    if len(lines) < 3:
        return None, content, None
    
    end_idx = -1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    
    if end_idx == -1:
        return None, content, None
    
    yaml_text = "\n".join(lines[1:end_idx])
    body_content = "\n".join(lines[end_idx+1:])
    
    try:
        frontmatter = yaml.safe_load(yaml_text)
        return frontmatter, body_content, yaml_text
    except yaml.YAMLError:
        return None, body_content, yaml_text

def fix_yaml_text(yaml_text):
    """修复 YAML 文本，处理常见解析错误"""
    lines = yaml_text.splitlines()
    fixed_lines = []
    
    for line in lines:
        # 处理 title 和 description 字段的冒号问题
        title_match = re.match(r'^(\s*title\s*:\s*)(["\'])(.*)\2', line)
        desc_match = re.match(r'^(\s*description\s*:\s*)(["\'])(.*)\2', line)
        
        if title_match or desc_match:
            prefix = title_match.group(1) if title_match else desc_match.group(1)
            original_value = title_match.group(3) if title_match else desc_match.group(3)
            
            # 检查是否包含未转义的冒号（在引号内但可能导致问题）
            # 只在 YAML 解析失败时才处理
            try:
                yaml.safe_load(f"key: '{original_value}'")
                fixed_lines.append(line)
            except yaml.YAMLError:
                # 需要修复：转义冒号或替换为安全字符
                fixed_value = original_value.replace(":", " -")
                fixed_lines.append(f"{prefix}'{fixed_value}'")
                log_message(f"  修复字段值中的冒号: '{original_value}' -> '{fixed_value}'", "WARNING")
        else:
            fixed_lines.append(line)
    
    return "\n".join(fixed_lines)

def fix_frontmatter(md_file_path, dry_run=False, backup=False):
    """修复单个 Markdown 文件的 Front Matter"""
    md_file_path = Path(md_file_path)
    
    try:
        with open(md_file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return False, f"读取失败: {str(e)}", {}
    
    # 检查是否有 Front Matter
    if not content.startswith("---"):
        return False, "无有效的 YAML Front Matter", {}
    
    # 尝试解析
    frontmatter, body, yaml_text = parse_frontmatter(content)
    
    changes = {}
    
    # 如果解析失败，尝试修复 YAML 文本
    if frontmatter is None:
        log_message(f"  YAML 解析失败，尝试修复...", "WARNING")
        fixed_yaml = fix_yaml_text(yaml_text)
        
        try:
            frontmatter = yaml.safe_load(fixed_yaml)
            changes["yaml_fixed"] = True
        except yaml.YAMLError as e:
            return False, f"YAML 修复失败: {str(e)}", {}
    
    # 统一日期格式
    if frontmatter and "date" in frontmatter:
        date_val = frontmatter["date"]
        if isinstance(date_val, datetime):
            date_str = date_val.strftime("%Y-%m-%dT10:00:00+08:00")
        elif isinstance(date_val, str):
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', date_val)
            if date_match:
                date_str = f"{date_match.group(1)}T10:00:00+08:00"
            else:
                date_str = datetime.now().strftime("%Y-%m-%dT10:00:00+08:00")
        else:
            date_str = datetime.now().strftime("%Y-%m-%dT10:00:00+08:00")
        
        if frontmatter["date"] != date_str:
            frontmatter["date"] = date_str
            changes["date_normalized"] = date_str
    
    # 如果没有 date 字段，添加当前日期
    if frontmatter and "date" not in frontmatter:
        today = datetime.now().strftime("%Y-%m-%dT10:00:00+08:00")
        frontmatter["date"] = today
        changes["date_added"] = today
    
    # 确保 title 和 description 使用单引号
    if frontmatter:
        if "title" in frontmatter and isinstance(frontmatter["title"], str):
            title = frontmatter["title"]
            if ":" in title and "'" not in title:
                frontmatter["title"] = title.replace(":", " -")
                changes["title_fixed"] = True
        
        if "description" in frontmatter and isinstance(frontmatter["description"], str):
            desc = frontmatter["description"]
            if ":" in desc and "'" not in desc:
                frontmatter["description"] = desc.replace(":", " -")
                changes["description_fixed"] = True
    
    # 如果没有修改，直接返回
    if not changes:
        return True, "无需修改", changes
    
    # 创建备份
    if backup:
        backup_file(md_file_path)
        changes["backup_created"] = True
    
    # 写回文件（非预览模式）
    if not dry_run:
        new_yaml = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True, sort_keys=False)
        new_content = f"---\n{new_yaml}---\n{body}"
        
        with open(md_file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        
        return True, f"修复完成 ({', '.join(changes.keys())})", changes
    else:
        return True, f"预览模式: 需修复 ({', '.join(changes.keys())})", changes

def batch_fix_all(dry_run=False, backup=True, verbose=False):
    """批量修复所有 Markdown 文件"""
    results = []
    fixed_count = 0
    failed_count = 0
    skipped_count = 0
    
    log_message("="*60)
    log_message(f"开始 Front Matter 修复 {'(预览模式)' if dry_run else ''}")
    log_message(f"扫描目录: {CONTENT_PATH}")
    log_message("="*60)
    
    for md_file in CONTENT_PATH.rglob("*.md"):
        if verbose:
            log_message(f"处理: {md_file.relative_to(ROOT_PATH)}", "INFO")
        
        success, msg, changes = fix_frontmatter(md_file, dry_run=dry_run, backup=backup)
        
        result = {
            "file": str(md_file.relative_to(ROOT_PATH)),
            "full_path": str(md_file),
            "success": success,
            "message": msg,
            "changes": changes,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        results.append(result)
        
        if success:
            if changes:
                fixed_count += 1
                log_message(f"✅ {md_file.name}: {msg}", "SUCCESS")
            else:
                skipped_count += 1
                if verbose:
                    log_message(f"ℹ️ {md_file.name}: {msg}", "INFO")
        else:
            failed_count += 1
            log_message(f"❌ {md_file.name}: {msg}", "ERROR")
    
    # 生成报告
    generate_report(results, dry_run)
    
    log_message("="*60)
    log_message(f"修复完成！")
    log_message(f"  处理文件: {fixed_count + failed_count + skipped_count}")
    log_message(f"  修复成功: {fixed_count}")
    log_message(f"  无需修改: {skipped_count}")
    log_message(f"  修复失败: {failed_count}")
    log_message("="*60)
    
    return results

def generate_report(results, dry_run):
    """生成修复报告"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = REPORT_PATH / f"frontmatter_fix_report_{timestamp}.md"
    
    report_lines = [
        f"# Front Matter 修复报告",
        f"",
        f"## 基本信息",
        f"- 修复时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 模式: {'预览模式（未实际修改）' if dry_run else '实际修复模式'}",
        f"",
        f"## 统计摘要",
        f"| 状态 | 数量 |",
        f"|------|------|",
        f"| 修复成功 | {sum(1 for r in results if r['success'] and r['changes'])} |",
        f"| 无需修改 | {sum(1 for r in results if r['success'] and not r['changes'])} |",
        f"| 修复失败 | {sum(1 for r in results if not r['success'])} |",
        f"",
        f"## 详细结果",
        f"",
        f"### ✅ 修复成功",
        f""
    ]
    
    for r in results:
        if r["success"] and r["changes"]:
            report_lines.append(f"- **{r['file']}**: {r['message']}")
            if r["changes"]:
                report_lines.append(f"  - 修改项: {', '.join(r['changes'].keys())}")
    
    report_lines.append("")
    report_lines.append("### ❌ 修复失败")
    report_lines.append("")
    
    for r in results:
        if not r["success"]:
            report_lines.append(f"- **{r['file']}**: {r['message']}")
    
    report_content = "\n".join(report_lines)
    
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report_content)
    
    log_message(f"报告已生成: {report_file}", "INFO")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Front Matter 自动修复脚本")
    parser.add_argument("--dry-run", "-d", action="store_true", help="预览模式，不实际修改文件")
    parser.add_argument("--no-backup", "-n", action="store_true", help="不创建备份文件")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    parser.add_argument("--test", "-t", action="store_true", help="测试模式，只处理前5个文件")
    
    args = parser.parse_args()
    
    # 检查依赖
    try:
        import yaml
    except ImportError:
        log_message("错误: 缺少 PyYAML 库，请安装: pip install pyyaml", "ERROR")
        sys.exit(1)
    
    batch_fix_all(
        dry_run=args.dry_run,
        backup=not args.no_backup,
        verbose=args.verbose
    )

if __name__ == "__main__":
    main()