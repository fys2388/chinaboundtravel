import os
import glob

print("搜索中文乱码字符...")
print("="*60)

# 要搜索的乱码字符
garbled_chars = ["馃", "彲", "镒", "镟", "镞", "镙", "镠", "镡", "镢", "镣", "镤", "镥", "镦", "镧", "镨", "镩", "镪", "镫", "镬", "镮", "镲", "镳", "镴", "镵", "長", "镸", "镹", "镺", "镻", "镼", "镽", "镾", "长", "锕", "锖", "锗", "锘", "锝", "锞", "锟", "锠", "锢", "锣", "锤", "锥", "锦", "锧", "锨", "锩", "锪", "锫", "锬", "锭", "键", "锯", "锰", "锱", "锲", "锴", "锶", "锼", "锽", "锾", "锿", "镃", "镄", "镅", "镆", "镈", "镋", "镌", "镍", "镎", "镏", "镋", "镕", "镋", "镋", "镋", "镋"]

# 搜索所有 markdown 文件
files = glob.glob("content/**/*.md", recursive=True)

files_with_issues = []
total_chars_found = 0

for filepath in files:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        found_chars = []
        for char in garbled_chars:
            if char in content:
                count = content.count(char)
                found_chars.append((char, count))
                total_chars_found += count
        
        if found_chars:
            files_with_issues.append((filepath, found_chars))
            print(f"\n[发现问题] {filepath}")
            for char, count in found_chars:
                print(f"  - '{char}': {count} 次")
    
    except Exception as e:
        pass

print("\n" + "="*60)
print(f"搜索完成！")
print(f"发现问题文件数: {len(files_with_issues)}")
print(f"乱码字符总数: {total_chars_found}")
print("="*60)

if files_with_issues:
    print("\n问题文件清单:")
    for filepath, _ in files_with_issues:
        print(f"  - {filepath}")
