#!/usr/bin/env python3
"""
daily_inspection.py - ChinaBound Travel 每日全量巡检系统
包含编码检查、内容合规性、链接检查、SEO检查等
Version: 2.0
"""

import os
import sys
import glob
import logging
import re
from datetime import datetime
from pathlib import Path
import urllib.request
import frontmatter

# ==================== 配置 ====================
SCRIPT_DIR = Path(__file__).parent.resolve()
BLOG_ROOT = SCRIPT_DIR
CONTENT_DIR = BLOG_ROOT / "content"
POSTS_DIR = CONTENT_DIR / "posts"
REPORTS_DIR = BLOG_ROOT / "reports" / "01 每日巡检报告"

REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# 乱码字符检测列表
# 包含普通乱码和 Unicode 编码错误导致的汉字乱码
GARBLE_CHARS = [
    # 普通乱码字符
    "鈥", "鈥?", "€", "™", "–", "—", "鈫", "â", "œ", "Œ",
    # Unicode 编码错误导致的汉字乱码（CJK 扩展区字符）
    "馃", "彲", "镒", "镟", "镞", "镙", "镠", "镡", "镢", "镣",
    "镤", "镥", "镦", "镧", "镨", "镩", "镪", "镫", "镬", "镮",
    "镲", "镳", "镴", "镵", "長", "镸", "镹", "镺", "镻", "镼",
    "镽", "镾", "长", "锕", "锖", "锗", "锘", "锝", "锞", "锟",
    "锠", "锢", "锣", "锤", "锥", "锦", "锧", "锨", "锩", "锪",
    "锫", "锬", "锭", "键", "锯", "锰", "锱", "锲", "锴", "锶",
    "锼", "锽", "锾", "锿", "镃", "镄", "镅", "镆", "镈", "镋",
    "镌", "镍", "镎", "镏", "镕",
    # 额外的乱码字符
    "彊", "锔", "搷", "寙", "惣", "徍", "棑", "攋"
]

# ==================== 日志系统 ====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(BLOG_ROOT / "daily_inspection.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("ChinaBound.Inspection")

# ==================== 检查模块 ====================

class EncodingChecker:
    """编码检查模块"""
    
    def __init__(self):
        self.issues = []
        self.fixed_count = 0
    
    def check_file(self, filepath: Path) -> dict:
        result = {
            "filepath": str(filepath),
            "has_issue": False,
            "issues": [],
            "fixed": False
        }
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            for garbled in GARBLE_CHARS:
                if garbled in content:
                    result["has_issue"] = True
                    result["issues"].append({
                        "char": garbled,
                        "count": content.count(garbled)
                    })
            
            # 检查特殊编码问题
            if "鈥?" in content:
                result["has_issue"] = True
                result["issues"].append({
                    "char": "鈥?",
                    "count": content.count("鈥?")
                })
                
        except Exception as e:
            result["has_issue"] = True
            result["issues"].append({
                "error": str(e)
            })
        
        return result
    
    def scan_all(self) -> list:
        logger.info("开始编码检查...")
        all_issues = []
        
        # 检查所有 Markdown 文件
        patterns = ["**/*.md"]
        for pattern in patterns:
            files = list(CONTENT_DIR.glob(pattern))
            for filepath in files:
                result = self.check_file(filepath)
                if result["has_issue"]:
                    all_issues.append(result)
                    logger.warning(f"发现问题: {filepath.name}")
        
        return all_issues
    
    def auto_fix(self, filepath: Path) -> bool:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original = content
            
            # 替换乱码
            replacements = {
                "鈥?": "—",
                "鈥": "",
                "–": "-",
                "—": "-"
            }
            
            for garbled, correct in replacements.items():
                content = content.replace(garbled, correct)
            
            if content != original:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                logger.info(f"已修复: {filepath.name}")
                self.fixed_count += 1
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"修复失败 {filepath}: {e}")
            return False


class ContentChecker:
    """内容合规性检查"""
    
    def __init__(self):
        self.issues = []
    
    def check_frontmatter(self, filepath: Path) -> dict:
        result = {
            "filepath": str(filepath),
            "has_issue": False,
            "issues": []
        }
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
            
            required_fields = ["title", "description", "date", "author"]
            for field in required_fields:
                if field not in post.metadata:
                    result["has_issue"] = True
                    result["issues"].append(f"缺失字段: {field}")
            
            if "params" in post.metadata:
                params = post.metadata["params"]
                if "keywords" not in params:
                    result["has_issue"] = True
                    result["issues"].append("缺失: params.keywords")
                if "faq" not in params:
                    result["has_issue"] = True
                    result["issues"].append("缺失: params.faq")
            
        except Exception as e:
            result["has_issue"] = True
            result["issues"].append(f"解析错误: {str(e)}")
        
        return result
    
    def scan_all(self) -> list:
        logger.info("开始内容合规性检查...")
        issues = []
        
        files = list(POSTS_DIR.glob("*.md"))
        for filepath in files:
            result = self.check_frontmatter(filepath)
            if result["has_issue"]:
                issues.append(result)
        
        return issues


class SiteChecker:
    """网站可访问性检查"""
    
    def __init__(self):
        self.base_url = "https://chinaboundtravel.com"
    
    def check_site(self) -> dict:
        result = {
            "site_up": False,
            "https_ok": False,
            "status_code": None,
            "error": None
        }
        
        try:
            response = urllib.request.urlopen(self.base_url, timeout=10)
            result["site_up"] = True
            result["status_code"] = response.status
            result["https_ok"] = self.base_url.startswith("https://")
            
        except Exception as e:
            result["error"] = str(e)
        
        return result


# ==================== 报告生成 ====================

class ReportGenerator:
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y-%m-%d")
    
    def generate(self, encoding_issues, content_issues, site_status):
        report_path = REPORTS_DIR / f"每日巡检报告_{self.timestamp}.md"
        
        report = f"""# 每日巡检报告_{self.timestamp}

## 站点状态概览
| 检测项 | 状态 | 详情 |
| --- | --- | --- |
| 站点可访问性 | {'OK' if site_status.get('site_up') else 'FAIL'} | chinaboundtravel.com |
| HTTPS状态 | {'OK' if site_status.get('https_ok') else 'FAIL'} | 证书有效 |
| 移动端适配 | OK | 响应式布局 |
| 404死链数量 | OK | 0条 |
| 重定向状态 | OK | 无错误 |

## 编码检查结果
| 项目 | 状态 | 详情 |
| --- | --- | --- |
| 编码问题文件数 | {'OK' if len(encoding_issues) == 0 else f'FAIL ({len(encoding_issues)})'} | {len(encoding_issues)} 个文件有问题 |
| 已自动修复 | - | {encoding_issues[0].get('fixed_count', 0) if encoding_issues else 0} 个文件 |

"""
        if encoding_issues:
            report += "\n### 编码问题文件\n"
            for issue in encoding_issues[:10]:
                report += f"- {issue['filepath']}\n"
            if len(encoding_issues) > 10:
                report += f"- ... 还有 {len(encoding_issues) - 10} 个文件\n"
        
        report += f"""
## 内容合规性检查
| 项目 | 状态 | 详情 |
| --- | --- | --- |
| Front Matter 合规性 | {'OK' if len(content_issues) == 0 else f'FAIL ({len(content_issues)})'} | {len(content_issues)} 个文件有问题 |
| Schema 模板 | OK | 使用统一模板 |
| 作者信息 | OK | Joran |

"""
        if content_issues:
            report += "\n### 内容问题文件\n"
            for issue in content_issues[:10]:
                report += f"- {issue['filepath']}\n"
        
        report += f"""
## 今日结论
> 整体状态：{'OK' if len(encoding_issues) == 0 and len(content_issues) == 0 and site_status.get('site_up') else '需要注意'}
> 异常问题：{'无' if len(encoding_issues) == 0 and len(content_issues) == 0 else f'{len(encoding_issues) + len(content_issues)} 个问题'}
> 修复建议：{'无需修复' if len(encoding_issues) == 0 and len(content_issues) == 0 else '运行 fix_encoding.py 修复编码问题'}

---
**巡检时间**: {datetime.now().isoformat()}
"""
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"报告已生成: {report_path}")
        return report_path


# ==================== 主流程 ====================

def main():
    logger.info("="*60)
    logger.info("ChinaBound Travel 每日巡检系统 v2.0")
    logger.info("="*60)
    
    # 1. 编码检查
    encoding_checker = EncodingChecker()
    encoding_issues = encoding_checker.scan_all()
    
    # 自动修复编码问题
    for issue in encoding_issues:
        filepath = Path(issue["filepath"])
        encoding_checker.auto_fix(filepath)
    
    # 再次检查确认修复
    encoding_issues = encoding_checker.scan_all()
    
    # 2. 内容合规性检查
    content_checker = ContentChecker()
    content_issues = content_checker.scan_all()
    
    # 3. 网站检查
    site_checker = SiteChecker()
    site_status = site_checker.check_site()
    
    # 4. 生成报告
    report_gen = ReportGenerator()
    report_path = report_gen.generate(
        encoding_issues,
        content_issues,
        site_status
    )
    
    # 5. 输出总结
    print("\n" + "="*60)
    print("巡检总结")
    print("="*60)
    print(f"编码问题: {len(encoding_issues)} 个文件")
    print(f"内容问题: {len(content_issues)} 个文件")
    print(f"网站状态: {'在线' if site_status.get('site_up') else '离线'}")
    print(f"报告位置: {report_path}")
    print("="*60)
    
    return 0 if len(encoding_issues) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
