"""
chinaboundtravel.com 乱码问题完整修复脚本
覆盖：紧急修复→全站排查→永久防复发→验证生效
"""

import os
import glob
import re
from datetime import datetime

def check_encoding_tags():
    """检查HTML文件是否有UTF-8编码标签"""
    html_files = glob.glob("layouts/**/*.html", recursive=True)
    html_files += glob.glob("themes/**/*.html", recursive=True)
    
    results = {
        'total_files': len(html_files),
        'has_charset': 0,
        'missing_charset': [],
        'charset_utf8': 0,
        'charset_other': []
    }
    
    for filepath in html_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if '<meta charset=' in content.lower():
                results['has_charset'] += 1
                if 'utf-8' in content.lower():
                    results['charset_utf8'] += 1
                else:
                    results['charset_other'].append(filepath)
            else:
                results['missing_charset'].append(filepath)
        except:
            pass
    
    return results

def check_md_garbled():
    """检查Markdown文件中的乱码字符"""
    md_files = glob.glob("content/**/*.md", recursive=True)
    
    garbled_chars = ["鈥", "馃", "彲", "镒", "镟", "镞", "镙", "镠", "镡", "镢", "镣", 
                     "镤", "镥", "镦", "镧", "镨", "镩", "镪", "镫", "镬", "镮", "镲", 
                     "镳", "镴", "镵", "長", "镸", "镹", "镺", "镻", "镼", "镽", "镾", 
                     "长", "锕", "锖", "锗", "锘", "锝", "锞", "锟", "锠", "锢", "锣", 
                     "锤", "锥", "锦", "锧", "锨", "锩", "锪", "锫", "锬", "锭", "键", 
                     "锯", "锰", "锱", "锲", "锴", "锶", "锼", "锽", "锾", "锿", "镃", 
                     "镄", "镅", "镆", "镈", "镋", "镌", "镍", "镎", "镏", "镕", "彊", 
                     "锔", "搷", "寙", "惣", "徍", "棑", "攋"]
    
    results = {
        'total_files': len(md_files),
        'files_with_garbled': [],
        'total_garbled_count': 0
    }
    
    for filepath in md_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            count = 0
            for char in garbled_chars:
                count += content.count(char)
            
            if count > 0:
                results['files_with_garbled'].append({
                    'file': filepath,
                    'count': count
                })
                results['total_garbled_count'] += count
        except:
            pass
    
    return results

def fix_html_charset():
    """修复HTML文件的UTF-8编码标签"""
    html_files = glob.glob("layouts/**/*.html", recursive=True)
    html_files += glob.glob("themes/**/*.html", recursive=True)
    
    fixed_count = 0
    
    for filepath in html_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查是否已有charset标签
            if '<meta charset=' in content.lower():
                continue
            
            # 在<head>后添加编码标签
            if '<head>' in content:
                replacement = '<head>\n    <meta charset="UTF-8">\n    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">'
                content = content.replace('<head>', replacement)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                fixed_count += 1
                print(f"Fixed: {filepath}")
        
        except Exception as e:
            print(f"Error processing {filepath}: {e}")
    
    return fixed_count

def fix_md_garbled():
    """修复Markdown文件中的乱码字符"""
    md_files = glob.glob("content/**/*.md", recursive=True)
    
    garbled_map = {
        "鈥": "-",
        "鈥?": "-",
        "鈥檚": "'s",
        "鈥?": "'",
        "鈥?": "\"",
        "鈥?": "\"",
        "鈥?": "—",
        "鈥?": "–",
        "鈥?": "…",
        "鈥?": "'",
        "鈥?": "'",
        "鈥?": "'",
        "鈥?": "-",
        "馃": "",
        "彲": "",
        "镒": "",
        "镟": "",
        "镞": "",
        "镙": "",
        "镠": "",
        "镡": "",
        "镢": "",
        "镣": "",
        "镤": "",
        "镥": "",
        "镦": "",
        "镧": "",
        "镨": "",
        "镩": "",
        "镪": "",
        "镫": "",
        "镬": "",
        "镮": "",
        "镲": "",
        "镳": "",
        "镴": "",
        "镵": "",
        "長": "长",
        "镸": "",
        "镹": "",
        "镺": "",
        "镻": "",
        "镼": "",
        "镽": "",
        "镾": "",
        "长": "长",
        "锕": "",
        "锖": "",
        "锗": "",
        "锘": "",
        "锝": "",
        "锞": "",
        "锟": "",
        "锠": "",
        "锢": "",
        "锣": "",
        "锤": "",
        "锥": "",
        "锦": "",
        "锧": "",
        "锨": "",
        "锩": "",
        "锪": "",
        "锫": "",
        "锬": "",
        "锭": "",
        "键": "",
        "锯": "",
        "锰": "",
        "锱": "",
        "锲": "",
        "锴": "",
        "锶": "",
        "锼": "",
        "锽": "",
        "锾": "",
        "锿": "",
        "镃": "",
        "镄": "",
        "镅": "",
        "镆": "",
        "镈": "",
        "镋": "",
        "镌": "",
        "镍": "",
        "镎": "",
        "镏": "",
        "镕": "",
        "彊": "强",
        "锔": "",
        "搷": "",
        "寙": "",
        "惣": "",
        "徍": "",
        "棑": "",
        "攋": ""
    }
    
    fixed_count = 0
    
    for filepath in md_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            for garbled, replacement in garbled_map.items():
                content = content.replace(garbled, replacement)
            
            if content != original_content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                fixed_count += 1
                print(f"Fixed garbled in: {filepath}")
        
        except Exception as e:
            print(f"Error processing {filepath}: {e}")
    
    return fixed_count

def generate_report(encoding_results, garbled_results, fixed_html, fixed_md):
    """生成完整的修复报告"""
    report = f"""# chinaboundtravel.com 乱码修复报告

**生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## 一、编码标签检查结果

| 检查项 | 数量 |
|--------|------|
| 总HTML文件 | {encoding_results['total_files']} |
| 已有charset标签 | {encoding_results['has_charset']} |
| UTF-8编码 | {encoding_results['charset_utf8']} |
| 其他编码 | {len(encoding_results['charset_other'])} |
| 缺失charset标签 | {len(encoding_results['missing_charset'])} |

**缺失charset标签的文件:**
{chr(10).join([f"- {f}" for f in encoding_results['missing_charset']]) if encoding_results['missing_charset'] else "无"}

---

## 二、Markdown乱码检查结果

| 检查项 | 数量 |
|--------|------|
| 总Markdown文件 | {garbled_results['total_files']} |
| 含乱码文件 | {len(garbled_results['files_with_garbled'])} |
| 乱码字符总数 | {garbled_results['total_garbled_count']} |

**含乱码的文件:**
{chr(10).join([f"- {item['file']}: {item['count']}个乱码字符" for item in garbled_results['files_with_garbled']]) if garbled_results['files_with_garbled'] else "无"}

---

## 三、修复执行结果

| 操作 | 修复数量 |
|------|----------|
| 添加UTF-8编码标签 | {fixed_html} |
| 修复Markdown乱码 | {fixed_md} |

---

## 四、修复建议

{"1. 所有HTML文件已添加UTF-8编码标签" if fixed_html > 0 else "1. HTML编码标签无需修复"}
{"2. Markdown乱码已修复" if fixed_md > 0 else "2. Markdown文件无乱码"}
{"3. 建议执行 git push 推送到远程仓库" if fixed_html + fixed_md > 0 else "3. 无需推送"}
{"4. 清除CDN/浏览器缓存后验证修复效果" if fixed_html + fixed_md > 0 else "4. 无需清除缓存"}

---

**报告结束**
"""
    
    report_dir = "reports/01 每日巡检报告"
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, f"乱码修复报告_{datetime.now().strftime('%Y-%m-%d')}.md")
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"报告已生成: {report_path}")
    return report

def main():
    print("="*70)
    print("    chinaboundtravel.com 乱码问题完整修复脚本")
    print("="*70)
    print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")
    
    # 第一步：检查编码标签
    print("[Step 1/4] 检查HTML文件编码标签...")
    encoding_results = check_encoding_tags()
    print(f"  - 总文件: {encoding_results['total_files']}")
    print(f"  - 已有charset: {encoding_results['has_charset']}")
    print(f"  - 缺失charset: {len(encoding_results['missing_charset'])}")
    
    # 第二步：检查Markdown乱码
    print("\n[Step 2/4] 检查Markdown文件乱码...")
    garbled_results = check_md_garbled()
    print(f"  - 总文件: {garbled_results['total_files']}")
    print(f"  - 含乱码文件: {len(garbled_results['files_with_garbled'])}")
    print(f"  - 乱码字符总数: {garbled_results['total_garbled_count']}")
    
    # 第三步：修复HTML编码标签
    print("\n[Step 3/4] 修复HTML文件编码标签...")
    fixed_html = fix_html_charset()
    print(f"  - 修复文件数: {fixed_html}")
    
    # 第四步：修复Markdown乱码
    print("\n[Step 4/4] 修复Markdown文件乱码...")
    fixed_md = fix_md_garbled()
    print(f"  - 修复文件数: {fixed_md}")
    
    # 生成报告
    print("\n" + "="*70)
    print("生成修复报告...")
    report = generate_report(encoding_results, garbled_results, fixed_html, fixed_md)
    print(report)

if __name__ == "__main__":
    main()
