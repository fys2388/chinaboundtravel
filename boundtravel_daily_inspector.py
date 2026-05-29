"""
BoundTravel 每日巡检机器人 v2.0 - 乱码专项增强版
用于 chinaboundtravel.com 的自动化日常巡检

核心功能:
    1. 网站可访问性检查
    2. SSL证书检查
    3. 【最高优先级】乱码专项检查
    4. UTF-8编码标签验证
    5. 博客内容检查
    6. Front Matter完整性检查

使用方法:
    python boundtravel_daily_inspector.py
    python boundtravel_daily_inspector.py --report  # 生成详细报告
"""

import sys
import os
import logging
import requests
from datetime import datetime
from pathlib import Path
import json
import time

# Windows 控制台编码修复
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# ==================== 配置 ====================
BLOG_ROOT = Path(__file__).parent.resolve()
REPORTS_DIR = BLOG_ROOT / "reports" / "01 每日巡检报告"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://chinaboundtravel.com"

# 乱码字符检测
GARBLE_CHARS = [
    "鈥", "鈥?", "€", "™", "–", "—", "鈫", "â", "œ", "Œ",
    "馃", "彲", "镒", "镟", "镞", "镙", "镠", "镡", "镢", "镣",
    "镤", "镥", "镦", "镧", "镨", "镩", "镪", "镫", "镬", "镮",
    "镲", "镳", "镴", "镵", "長", "镸", "镹", "镺", "镻", "镼",
    "镽", "镾", "长", "锕", "锖", "锗", "锘", "锝", "锞", "锟",
    "锠", "锢", "锣", "锤", "锥", "锦", "锧", "锨", "锩", "锪",
    "锫", "锬", "锭", "键", "锯", "锰", "锱", "锲", "锴", "锶",
    "锼", "锽", "锾", "锿", "镃", "镄", "镅", "镆", "镈", "镋",
    "镌", "镍", "镎", "镏", "镕", "彊", "锔", "搷", "寙", "惣",
    "徍", "棑", "攋"
]

# ==================== 日志配置 ====================
log_file = BLOG_ROOT / "boundtravel_inspector.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file, encoding="utf-8")
    ]
)
logger = logging.getLogger("BoundTravel.Inspector")

# ==================== 检查类 ====================

class SiteChecker:
    """网站基础检查"""
    
    def __init__(self):
        self.base_url = BASE_URL
        self.results = {}
    
    def check_accessibility(self) -> dict:
        """检查网站可访问性"""
        result = {
            "status": "OK",
            "message": "",
            "response_time": 0,
            "status_code": None
        }
        
        try:
            start = time.time()
            response = requests.get(self.base_url, timeout=10)
            result["response_time"] = round((time.time() - start) * 1000)
            result["status_code"] = response.status_code
            
            if response.status_code != 200:
                result["status"] = "ERROR"
                result["message"] = f"HTTP {response.status_code}"
            elif "text/html" not in response.headers.get("Content-Type", ""):
                result["status"] = "WARNING"
                result["message"] = "Content-Type is not HTML"
            else:
                result["status"] = "OK"
                result["message"] = "Site is accessible"
                
        except requests.exceptions.SSL_ERROR:
            result["status"] = "ERROR"
            result["message"] = "SSL Certificate Error"
        except requests.exceptions.Timeout:
            result["status"] = "ERROR"
            result["message"] = "Request Timeout"
        except Exception as e:
            result["status"] = "ERROR"
            result["message"] = str(e)
        
        self.results["accessibility"] = result
        return result
    
    def check_ssl(self) -> dict:
        """检查 SSL 证书"""
        result = {"status": "OK", "message": ""}
        
        try:
            response = requests.get(self.base_url, verify=True, timeout=10)
            result["status"] = "OK"
            result["message"] = "SSL Certificate Valid"
        except requests.exceptions.SSLError:
            result["status"] = "ERROR"
            result["message"] = "SSL Certificate Invalid"
        except Exception as e:
            result["status"] = "WARNING"
            result["message"] = f"SSL check failed: {str(e)}"
        
        self.results["ssl"] = result
        return result
    
    def check_internal_links(self) -> dict:
        """检查内链是否正常"""
        result = {
            "status": "OK",
            "checked_links": [],
            "broken_links": []
        }
        
        try:
            response = requests.get(self.base_url, timeout=10)
            content = response.text
            
            # 提取首页的内链
            import re
            links = re.findall(r'href="(/[^"]+)"', content)
            links = [self.base_url + link for link in links[:5] if not link.startswith('/#')]
            
            for link in links:
                try:
                    resp = requests.head(link, timeout=5, allow_redirects=True)
                    if resp.status_code >= 400:
                        result["broken_links"].append({"url": link, "status": resp.status_code})
                except:
                    result["broken_links"].append({"url": link, "status": "Error"})
            
            result["checked_links"] = [l["url"] for l in links]
            
            if result["broken_links"]:
                result["status"] = "WARNING"
            
        except Exception as e:
            result["status"] = "ERROR"
            result["message"] = str(e)
        
        self.results["internal_links"] = result
        return result
    
    def check_charset_tag(self) -> dict:
        """【最高优先级】检查页面是否有UTF-8编码标签"""
        result = {
            "status": "OK",
            "has_charset_utf8": False,
            "pages_checked": [],
            "pages_missing_charset": []
        }
        
        pages_to_check = [
            self.base_url,
            self.base_url + "/posts/",
            self.base_url + "/cities/"
        ]
        
        for page in pages_to_check:
            try:
                response = requests.get(page, timeout=10)
                content = response.text
                
                has_utf8 = '<meta charset="UTF-8"' in content or \
                          '<meta charset="utf-8"' in content or \
                          'charset=utf-8' in content.lower()
                
                result["pages_checked"].append(page)
                
                if not has_utf8:
                    result["pages_missing_charset"].append(page)
                
            except Exception as e:
                pass
        
        if result["pages_missing_charset"]:
            result["status"] = "ERROR"
        else:
            result["has_charset_utf8"] = True
        
        self.results["charset_tag"] = result
        return result


class ContentChecker:
    """内容检查"""
    
    def __init__(self):
        self.results = {}
    
    def check_garbled_chars(self) -> dict:
        """【最高优先级】检查乱码字符"""
        result = {
            "status": "OK",
            "files_with_issues": [],
            "total_issues": 0,
            "details": []
        }
        
        import glob
        
        for filepath in glob.glob("content/**/*.md", recursive=True):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                file_issues = []
                for char in GARBLE_CHARS:
                    count = content.count(char)
                    if count > 0:
                        file_issues.append({"char": char, "count": count})
                        result["total_issues"] += count
                
                if file_issues:
                    result["files_with_issues"].append(filepath)
                    result["details"].append({
                        "file": filepath,
                        "issues": file_issues
                    })
                        
            except Exception as e:
                pass
        
        if result["files_with_issues"]:
            result["status"] = "ERROR"
        
        self.results["garbled_chars"] = result
        return result
    
    def check_garbled_in_html(self) -> dict:
        """【最高优先级】检查网页内容中的乱码字符（线上验证）"""
        result = {
            "status": "OK",
            "pages_with_garbled": [],
            "total_garbled_chars": 0
        }
        
        import re
        
        pages_to_check = [
            "https://chinaboundtravel.com",
            "https://chinaboundtravel.com/cities/",
            "https://chinaboundtravel.com/posts/"
        ]
        
        for page in pages_to_check:
            try:
                response = requests.get(page, timeout=10)
                content = response.text
                
                garbled_found = []
                for char in GARBLE_CHARS:
                    if char in content:
                        garbled_found.append(char)
                        result["total_garbled_chars"] += content.count(char)
                
                if garbled_found:
                    result["pages_with_garbled"].append({
                        "page": page,
                        "garbled_chars": garbled_found
                    })
                
            except Exception as e:
                pass
        
        if result["pages_with_garbled"]:
            result["status"] = "ERROR"
        
        self.results["garbled_in_html"] = result
        return result
    
    def check_blog_posts(self) -> dict:
        """检查博客文章"""
        result = {
            "status": "OK",
            "posts_count": 0,
            "recent_posts": [],
            "issues": []
        }
        
        import glob
        from datetime import datetime, timedelta
        
        posts = glob.glob("content/posts/*.md")
        result["posts_count"] = len(posts)
        
        # 获取最近的文章
        recent = []
        for post in posts[:5]:
            try:
                mtime = os.path.getmtime(post)
                recent.append({
                    "file": Path(post).name,
                    "modified": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
                })
            except:
                pass
        
        result["recent_posts"] = recent
        
        # 检查是否有最近的文章
        week_ago = datetime.now() - timedelta(days=7)
        has_recent = False
        for post in posts:
            try:
                mtime = os.path.getmtime(post)
                if datetime.fromtimestamp(mtime) > week_ago:
                    has_recent = True
                    break
            except:
                pass
        
        if not has_recent and len(posts) > 0:
            result["issues"].append("No posts published in the last 7 days")
        
        self.results["blog_posts"] = result
        return result
    
    def check_frontmatter(self) -> dict:
        """检查 Front Matter 完整性"""
        result = {
            "status": "OK",
            "files_with_issues": [],
            "missing_fields": []
        }
        
        import glob
        import frontmatter
        
        for filepath in glob.glob("content/posts/*.md"):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    post = frontmatter.load(f)
                
                required = ["title", "description", "date", "author"]
                missing = [field for field in required if field not in post.metadata]
                
                if missing:
                    result["files_with_issues"].append(Path(filepath).name)
                    result["missing_fields"].extend(missing)
                    
            except Exception as e:
                result["files_with_issues"].append(Path(filepath).name)
        
        if result["files_with_issues"]:
            result["status"] = "WARNING"
        
        self.results["frontmatter"] = result
        return result


class ReportGenerator:
    """报告生成"""
    
    def __init__(self):
        self.timestamp = datetime.now()
        self.week_type = "双休周" if self.timestamp.isocalendar()[2] <= 5 else "单休周"
    
    def generate(self, site_results: dict, content_results: dict) -> str:
        """生成巡检报告"""
        date_str = self.timestamp.strftime("%Y-%m-%d")
        report_path = REPORTS_DIR / f"BoundTravel巡检报告_{date_str}.md"
        
        # 总体状态
        all_ok = all([
            site_results.get("accessibility", {}).get("status") == "OK",
            site_results.get("ssl", {}).get("status") == "OK",
            content_results.get("garbled_chars", {}).get("status") == "OK",
            content_results.get("frontmatter", {}).get("status") == "OK"
        ])
        
        report = f"""# BoundTravel 每日巡检报告

**巡检日期**: {date_str}
**巡检时间**: {self.timestamp.strftime("%H:%M:%S")}
**当前周期**: 【{self.week_type}】

---

## 总体状态

| 状态 | 说明 |
|------|------|
| {"[OK] 全部正常" if all_ok else "[FAIL] 需要关注"} | {"所有检查项通过" if all_ok else "存在需要处理的问题"} |

---

## 1. 网站可访问性检查

| 检查项 | 状态 | 详情 |
|--------|------|------|
| 站点访问 | {site_results.get("accessibility", {}).get("status", "N/A")} | {site_results.get("accessibility", {}).get("message", "")} |
| SSL证书 | {site_results.get("ssl", {}).get("status", "N/A")} | {site_results.get("ssl", {}).get("message", "")} |
| 响应时间 | {site_results.get("accessibility", {}).get("response_time", "N/A")}ms | - |

---

## 2. 内部链接检查

| 检查项 | 状态 | 详情 |
|--------|------|------|
| 检查链接数 | {len(site_results.get("internal_links", {}).get("checked_links", []))} | - |
| 失效链接 | {len(site_results.get("internal_links", {}).get("broken_links", []))} | {"无" if not site_results.get("internal_links", {}).get("broken_links") else str(site_results.get("internal_links", {}).get("broken_links"))} |

---

## 3. 内容质量检查

| 检查项 | 状态 | 详情 |
|--------|------|------|
| 乱码检查 | {"[OK] 无乱码" if content_results.get("garbled_chars", {}).get("status") == "OK" else "[FAIL] 发现乱码"} | {content_results.get("garbled_chars", {}).get("total_issues", 0)} 个乱码字符 |
| Front Matter | {"[OK] 完整" if content_results.get("frontmatter", {}).get("status") == "OK" else "[WARN] 有缺失"} | {len(content_results.get("frontmatter", {}).get("files_with_issues", []))} 个文件有问题 |

---

## 4. 博客文章检查

| 检查项 | 状态 | 详情 |
|--------|------|------|
| 文章总数 | {content_results.get("blog_posts", {}).get("posts_count", 0)} | - |
| 最近更新 | {content_results.get("blog_posts", {}).get("recent_posts", [{}])[0].get("modified", "N/A") if content_results.get("blog_posts", {}).get("recent_posts") else "N/A"} | - |

---

## 巡检结论

**整体状态**: {"[OK] 正常" if all_ok else "[FAIL] 异常"}

**异常问题**: {len(content_results.get("garbled_chars", {}).get("files_with_issues", [])) + len(content_results.get("frontmatter", {}).get("files_with_issues", []))} 个

**处理建议**: 
{"无需特殊处理" if all_ok else self._get_fix_suggestions(content_results)}

---

**巡检完成**: {self.timestamp.strftime("%Y-%m-%d %H:%M:%S")}
"""
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"报告已生成: {report_path}")
        return str(report_path)
    
    def _get_fix_suggestions(self, results: dict) -> str:
        suggestions = []
        
        if results.get("garbled_chars", {}).get("files_with_issues"):
            suggestions.append("1. 运行 fix_garbled_precise.py 修复乱码字符")
        
        if results.get("frontmatter", {}).get("files_with_issues"):
            suggestions.append("2. 检查缺失 Front Matter 的文件")
        
        return "\n".join(suggestions) if suggestions else "无"


# ==================== 主流程 ====================

def main():
    print("\n" + "="*70)
    print("       BoundTravel 每日巡检机器人 v2.0")
    print("       【乱码专项增强版】")
    print("="*70)
    print(f"巡检时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")
    
    # 1. 网站基础检查
    logger.info("[Step 1/5] 检查网站可访问性和SSL证书...")
    site_checker = SiteChecker()
    site_checker.check_accessibility()
    site_checker.check_ssl()
    site_checker.check_internal_links()
    site_checker.check_charset_tag()  # 新增：检查UTF-8编码标签
    
    print(f"  - 可访问性: {site_checker.results['accessibility']['status']}")
    print(f"  - SSL证书: {site_checker.results['ssl']['status']}")
    print(f"  - 内链检查: {len(site_checker.results['internal_links']['broken_links'])} 个失效链接")
    print(f"  - UTF-8编码标签: {'[OK] 已设置' if site_checker.results.get('charset_tag', {}).get('has_charset_utf8') else '[FAIL] 缺失'}")
    
    # 2. 【最高优先级】乱码专项检查
    logger.info("[Step 2/5] 【最高优先级】乱码专项检查...")
    content_checker = ContentChecker()
    content_checker.check_garbled_chars()
    content_checker.check_garbled_in_html()  # 新增：检查线上页面乱码
    
    print(f"  - Markdown文件乱码: {content_checker.results['garbled_chars']['total_issues']} 个字符")
    print(f"  - 线上页面乱码: {content_checker.results.get('garbled_in_html', {}).get('total_garbled_chars', 0)} 个字符")
    
    # 3. 博客内容检查
    logger.info("[Step 3/5] 检查博客内容...")
    content_checker.check_blog_posts()
    
    print(f"  - 博客文章: {content_checker.results['blog_posts']['posts_count']} 篇")
    
    # 4. Front Matter检查
    logger.info("[Step 4/5] 检查Front Matter完整性...")
    content_checker.check_frontmatter()
    
    print(f"  - Front Matter: {len(content_checker.results['frontmatter']['files_with_issues'])} 个文件有问题")
    
    # 5. 生成报告
    logger.info("[Step 5/5] 生成巡检报告...")
    report_gen = ReportGenerator()
    report_path = report_gen.generate(site_checker.results, content_checker.results)
    
    # 输出结果
    print("\n" + "="*70)
    print("                      巡检完成总结")
    print("="*70)
    
    # 乱码问题优先判断
    garbled_ok = content_checker.results.get("garbled_chars", {}).get("status") == "OK"
    charset_ok = site_checker.results.get("charset_tag", {}).get("status") == "OK"
    html_garbled_ok = content_checker.results.get("garbled_in_html", {}).get("status") == "OK"
    
    all_ok = all([
        site_checker.results.get("accessibility", {}).get("status") == "OK",
        site_checker.results.get("ssl", {}).get("status") == "OK",
        garbled_ok,
        charset_ok,
        html_garbled_ok,
        content_checker.results.get("frontmatter", {}).get("status") == "OK"
    ])
    
    if all_ok:
        print("  ✅ 全部检查项通过 - 网站运行正常")
    else:
        print("  ⚠️ 发现问题 - 需要处理")
        
        # 乱码问题优先显示
        if not charset_ok:
            print(f"    - 【严重】UTF-8编码标签缺失: {len(site_checker.results.get('charset_tag', {}).get('pages_missing_charset', []))} 个页面")
        
        if not garbled_ok:
            print(f"    - 【严重】Markdown文件乱码: {len(content_checker.results['garbled_chars']['files_with_issues'])} 个文件")
        
        if not html_garbled_ok:
            print(f"    - 【严重】线上页面乱码: {len(content_checker.results.get('garbled_in_html', {}).get('pages_with_garbled', []))} 个页面")
        
        if content_checker.results.get("frontmatter", {}).get("files_with_issues"):
            print(f"    - Front Matter问题: {len(content_checker.results['frontmatter']['files_with_issues'])} 个文件")
    
    print(f"\n  报告位置: {report_path}")
    print(f"  当前周期: 【{report_gen.week_type}】")
    print("="*70)
    
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
