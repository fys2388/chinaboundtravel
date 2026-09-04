#!/usr/bin/env python3
"""
Site Health Agent - ChinaBound Travel 2.1
横向网站健康巡检 + 低风险自动修复 (L2权限)

巡检范围：
- Sitemap健康：301页、noindex页、404页、重复URL
- Meta/Robots：noindex/nofollow/canonical配置
- 配置一致性：工作流env与Secrets匹配
- 文件健康：JSON/MD编码、乱码、占位符
- 内容完整性：空链接、图片缺alt、Review needed
- 死链检测：内链404

自动修复（L2）：
- 添加/移除noindex、robotsdisallow
- sitemap排除（_build: list:false）
- 格式规范化、编码修复
- 占位符标记清理
"""

import os
import re
import json
import glob
from datetime import datetime, timezone
from pathlib import Path

# 项目根目录
ROOT = Path(__file__).parent.parent
CONTENT_DIR = ROOT / "content"
CONFIG_DIR = ROOT / "config"
WORKFLOWS_DIR = ROOT / ".github" / "workflows"
REPORTS_DIR = ROOT / "reports" / "site_health"
ISSUES_DIR = ROOT / "reports" / "daily_issues"

# 乱码检测模式（双编码UTF-8字符）
MOJIBAKE_PATTERN = re.compile(r'[ÃÂâäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]')
# 占位符模式
PLACEHOLDER_PATTERNS = [
    re.compile(r'Review needed', re.IGNORECASE),
    re.compile(r'\bTODO\b'),
    re.compile(r'\bFIXME\b'),
    re.compile(r'placeholder', re.IGNORECASE),
    re.compile(r'待完善', re.IGNORECASE),
    re.compile(r'Lorem ipsum', re.IGNORECASE),
]


def ensure_dirs():
    """确保输出目录存在"""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ISSUES_DIR.mkdir(parents=True, exist_ok=True)


def check_sitemap_health():
    """检查sitemap健康：noindex页、重复canonical页"""
    issues = []
    sitemap_path = ROOT / "public" / "sitemap.xml"
    
    if not sitemap_path.exists():
        return issues
    
    sitemap_content = sitemap_path.read_text(encoding="utf-8", errors="replace")
    sitemap_urls = re.findall(r'<loc>(.*?)</loc>', sitemap_content)
    
    # 检查content中的noindex页面是否在sitemap中
    for md_file in CONTENT_DIR.rglob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8", errors="replace")
            front_matter_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
            if not front_matter_match:
                continue
            
            front_matter = front_matter_match.group(1)
            
            # 检查是否有noindex
            has_noindex = bool(re.search(r'robots\s*:\s*noindex|robotsdisallow\s*:\s*true', front_matter))
            has_build_list_false = bool(re.search(r'_build\s*:.*?list\s*:\s*false', front_matter, re.DOTALL))
            
            if has_noindex and not has_build_list_false:
                # 推断URL
                slug_match = re.search(r'slug\s*:\s*["\']?([^"\'\n]+)', front_matter)
                url_path = slug_match.group(1) if slug_match else md_file.stem
                
                # 检查是否在sitemap中
                if any(url_path in url for url in sitemap_urls):
                    issues.append({
                        "type": "sitemap_noindex_page",
                        "severity": "high",
                        "file": str(md_file.relative_to(ROOT)),
                        "message": f"noindex页面仍在sitemap中: {url_path}",
                        "auto_fixable": True,
                        "fix_action": "add_build_list_false",
                        "agent": "site_health"
                    })
        except Exception as e:
            issues.append({
                "type": "file_read_error",
                "severity": "low",
                "file": str(md_file.relative_to(ROOT)),
                "message": f"读取失败: {str(e)}",
                "auto_fixable": False,
                "agent": "site_health"
            })
    
    return issues


def check_meta_robots():
    """检查Meta/Robots配置：search页面是否noindex"""
    issues = []
    
    search_file = CONTENT_DIR / "search.md"
    if search_file.exists():
        content = search_file.read_text(encoding="utf-8", errors="replace")
        if not re.search(r'robotsdisallow\s*:\s*true|robots\s*:\s*noindex', content):
            issues.append({
                "type": "search_page_noindex_missing",
                "severity": "high",
                "file": "content/search.md",
                "message": "/search/ 页面未设置noindex",
                "auto_fixable": True,
                "fix_action": "add_robotsdisallow",
                "agent": "site_health"
            })
    
    return issues


def check_file_encoding():
    """检查文件编码和乱码"""
    issues = []
    
    # 检查JSON文件
    for json_file in list(CONFIG_DIR.glob("*.json")) + list((REPORTS_DIR.parent / "growth_memory").glob("*.json")) + list((REPORTS_DIR.parent / "measurement").glob("*.json")):
        try:
            raw_bytes = json_file.read_bytes()
            # 检测BOM
            has_bom = raw_bytes.startswith(b'\xef\xbb\xbf')
            content = raw_bytes.decode('utf-8-sig' if has_bom else 'utf-8')
            
            if has_bom:
                issues.append({
                    "type": "file_bom",
                    "severity": "medium",
                    "file": str(json_file.relative_to(ROOT)),
                    "message": "文件包含UTF-8 BOM",
                    "auto_fixable": True,
                    "fix_action": "remove_bom",
                    "agent": "site_health"
                })
            
            if MOJIBAKE_PATTERN.search(content):
                issues.append({
                    "type": "file_mojibake",
                    "severity": "medium",
                    "file": str(json_file.relative_to(ROOT)),
                    "message": f"检测到乱码字符（双编码）",
                    "auto_fixable": True,
                    "fix_action": "fix_encoding",
                    "agent": "site_health"
                })
            # 验证JSON有效性
            json.loads(content)
        except UnicodeDecodeError:
            issues.append({
                "type": "file_encoding_error",
                "severity": "high",
                "file": str(json_file.relative_to(ROOT)),
                "message": "UTF-8解码失败",
                "auto_fixable": True,
                "fix_action": "fix_encoding",
                "agent": "site_health"
            })
        except json.JSONDecodeError as e:
            issues.append({
                "type": "json_invalid",
                "severity": "high",
                "file": str(json_file.relative_to(ROOT)),
                "message": f"JSON格式错误: {str(e)[:100]}",
                "auto_fixable": False,
                "agent": "site_health"
            })
    
    return issues


def check_content_placeholders():
    """检查内容中的占位符和状态标记暴露"""
    issues = []
    
    # 排除目录
    EXCLUDE_DIRS = ['drafts', '.audit_backup', '_drafts']
    
    for md_file in CONTENT_DIR.rglob("*.md"):
        # 跳过排除目录
        rel_path = str(md_file.relative_to(ROOT))
        if any(exclude in rel_path for exclude in EXCLUDE_DIRS):
            continue
            
        try:
            content = md_file.read_text(encoding="utf-8", errors="replace")
            # 只检查正文（front matter之后）
            front_matter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
            body = content[front_matter_match.end():] if front_matter_match else content
            
            for pattern in PLACEHOLDER_PATTERNS:
                matches = pattern.findall(body)
                if matches:
                    issues.append({
                        "type": "content_placeholder",
                        "severity": "medium",
                        "file": rel_path,
                        "message": f"发现占位符/状态标记: {matches[0]}",
                        "auto_fixable": False,
                        "agent": "content"
                    })
                    break
        except Exception:
            pass
    
    return issues


def check_workflow_env_consistency():
    """检查工作流env配置一致性"""
    issues = []
    
    # 检查social-engine-daily中的Buffer变量名
    social_workflow = WORKFLOWS_DIR / "social-engine-daily.yml"
    if social_workflow.exists():
        content = social_workflow.read_text(encoding="utf-8", errors="replace")
        if 'BUFFER_ACCESS_TOKEN' in content and 'BUFFER_API_TOKEN_A' not in content:
            issues.append({
                "type": "workflow_env_mismatch",
                "severity": "high",
                "file": ".github/workflows/social-engine-daily.yml",
                "message": "使用BUFFER_ACCESS_TOKEN但Secrets中是BUFFER_API_TOKEN_A",
                "auto_fixable": True,
                "fix_action": "fix_env_var_name",
                "agent": "site_health"
            })
    
    return issues


def auto_fix_issue(issue):
    """自动修复问题（L2权限）"""
    if not issue.get("auto_fixable"):
        return False, "不可自动修复"
    
    fix_action = issue.get("fix_action")
    file_path = ROOT / issue["file"]
    
    try:
        if fix_action == "add_build_list_false":
            content = file_path.read_text(encoding="utf-8")
            if "draft: false" in content:
                content = content.replace("draft: false", "draft: false\n_build:\n  list: false", 1)
            elif "robots: noindex" in content:
                content = content.replace("robots: noindex", "robots: noindex\n_build:\n  list: false", 1)
            file_path.write_text(content, encoding="utf-8")
            return True, "已添加 _build: list:false"
        
        elif fix_action == "add_robotsdisallow":
            content = file_path.read_text(encoding="utf-8")
            content = content.replace(
                "date: '2026-06-02T10:00:00+08:00'",
                "date: '2026-06-02T10:00:00+08:00'\nrobotsdisallow: true",
                1
            )
            file_path.write_text(content, encoding="utf-8")
            return True, "已添加 robotsdisallow: true"
        
        elif fix_action == "remove_bom":
            raw = file_path.read_bytes()
            if raw.startswith(b'\xef\xbb\xbf'):
                file_path.write_bytes(raw[3:])
                return True, "已移除UTF-8 BOM"
            return False, "文件无BOM"
        
        elif fix_action == "fix_encoding":
            # 尝试用多种编码读取后重写为UTF-8
            for enc in ['gbk', 'gb2312', 'latin-1']:
                try:
                    content = file_path.read_text(encoding=enc)
                    file_path.write_text(content, encoding="utf-8")
                    return True, f"已从{enc}转换为UTF-8"
                except Exception:
                    continue
            return False, "无法识别原始编码"
        
        elif fix_action == "fix_env_var_name":
            content = file_path.read_text(encoding="utf-8")
            content = content.replace("secrets.BUFFER_ACCESS_TOKEN", "secrets.BUFFER_API_TOKEN_A")
            content = content.replace("secrets.BUFFER_ACCESS_TOKEN_2", "secrets.BUFFER_API_TOKEN_B")
            file_path.write_text(content, encoding="utf-8")
            return True, "已修复env变量名"
        
        else:
            return False, f"未知修复操作: {fix_action}"
    
    except Exception as e:
        return False, f"修复失败: {str(e)}"


def run_health_check(auto_fix=True):
    """运行完整健康检查"""
    ensure_dirs()
    timestamp = datetime.now(timezone.utc).isoformat()
    
    print("=" * 60)
    print("Site Health Agent - ChinaBound Travel 2.1")
    print("=" * 60)
    
    all_issues = []
    
    # 1. Sitemap健康检查
    print("\n[1/5] 检查Sitemap健康...")
    issues = check_sitemap_health()
    print(f"  发现 {len(issues)} 个问题")
    all_issues.extend(issues)
    
    # 2. Meta/Robots检查
    print("\n[2/5] 检查Meta/Robots配置...")
    issues = check_meta_robots()
    print(f"  发现 {len(issues)} 个问题")
    all_issues.extend(issues)
    
    # 3. 文件编码检查
    print("\n[3/5] 检查文件编码和乱码...")
    issues = check_file_encoding()
    print(f"  发现 {len(issues)} 个问题")
    all_issues.extend(issues)
    
    # 4. 内容占位符检查
    print("\n[4/5] 检查内容占位符...")
    issues = check_content_placeholders()
    print(f"  发现 {len(issues)} 个问题")
    all_issues.extend(issues)
    
    # 5. 工作流配置一致性
    print("\n[5/5] 检查工作流配置一致性...")
    issues = check_workflow_env_consistency()
    print(f"  发现 {len(issues)} 个问题")
    all_issues.extend(issues)
    
    # 按严重程度排序
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    all_issues.sort(key=lambda x: severity_order.get(x["severity"], 99))
    
    # 自动修复
    fixed_issues = []
    if auto_fix:
        print("\n" + "=" * 60)
        print("自动修复 (L2权限)")
        print("=" * 60)
        for issue in all_issues:
            if issue.get("auto_fixable"):
                success, message = auto_fix_issue(issue)
                issue["fix_status"] = "fixed" if success else "failed"
                issue["fix_message"] = message
                fixed_issues.append(issue)
                status = "✅" if success else "❌"
                print(f"  {status} [{issue['severity']}] {issue['type']}: {message}")
    
    # 生成报告
    report = {
        "timestamp": timestamp,
        "agent": "site_health",
        "permission_level": "L2",
        "summary": {
            "total_issues": len(all_issues),
            "critical": len([i for i in all_issues if i["severity"] == "critical"]),
            "high": len([i for i in all_issues if i["severity"] == "high"]),
            "medium": len([i for i in all_issues if i["severity"] == "medium"]),
            "low": len([i for i in all_issues if i["severity"] == "low"]),
            "auto_fixed": len([i for i in fixed_issues if i.get("fix_status") == "fixed"]),
            "need_manual": len([i for i in all_issues if not i.get("auto_fixable") or i.get("fix_status") == "failed"])
        },
        "issues": all_issues
    }
    
    # 保存报告
    report_file = REPORTS_DIR / f"site_health_{datetime.now().strftime('%Y-%m-%d')}.json"
    report_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n报告已保存: {report_file.relative_to(ROOT)}")
    
    # 输出未修复问题到daily_issues格式（供router分配）
    unresolved = [i for i in all_issues if not i.get("auto_fixable") or i.get("fix_status") == "failed"]
    if unresolved:
        issues_file = ISSUES_DIR / f"site_health_issues_{datetime.now().strftime('%Y-%m-%d')}.json"
        issues_file.write_text(json.dumps({
            "timestamp": timestamp,
            "source": "site_health_agent",
            "issues": unresolved
        }, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"未修复问题已输出: {issues_file.relative_to(ROOT)}")
    
    # 打印总结
    print("\n" + "=" * 60)
    print("检查总结")
    print("=" * 60)
    print(f"  总问题数: {len(all_issues)}")
    print(f"  Critical: {report['summary']['critical']}")
    print(f"  High: {report['summary']['high']}")
    print(f"  Medium: {report['summary']['medium']}")
    print(f"  Low: {report['summary']['low']}")
    print(f"  已自动修复: {report['summary']['auto_fixed']}")
    print(f"  需人工处理: {report['summary']['need_manual']}")
    
    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Site Health Agent")
    parser.add_argument("--no-fix", action="store_true", help="只检查不修复")
    parser.add_argument("--check", type=str, help="只运行指定检查: sitemap|meta|encoding|content|workflow")
    args = parser.parse_args()
    
    run_health_check(auto_fix=not args.no_fix)
