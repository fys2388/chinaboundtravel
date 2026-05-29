import os
import glob

print("修复中文乱码字符...")
print("="*60)

# 这些是 Unicode 编码错误导致的乱码字符
# 它们通常是某些特殊符号（如引号、破折号等）被错误解码产生的
garbled_chars = [
    "馃", "彲", "镒", "镟", "镞", "镙", "镠", "镡", "镢", "镣", 
    "镤", "镥", "镦", "镧", "镨", "镩", "镪", "镫", "镬", "镮", 
    "镲", "镳", "镴", "镵", "長", "镸", "镹", "镺", "镻", "镼", 
    "镽", "镾", "长", "锕", "锖", "锗", "锘", "锝", "锞", "锟", 
    "锠", "锢", "锣", "锤", "锥", "锦", "锧", "锨", "锩", "锪", 
    "锫", "锬", "锭", "键", "锯", "锰", "锱", "锲", "锴", "锶", 
    "锼", "锽", "锾", "锿", "镃", "镄", "镅", "镆", "镈", "镋", 
    "镌", "镍", "镎", "镏", "镕"
]

files = glob.glob("content/**/*.md", recursive=True)

fixed_count = 0
files_fixed = 0

for filepath in files:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        
        # 移除所有这些乱码字符
        for char in garbled_chars:
            content = content.replace(char, "")
        
        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            files_fixed += 1
            fixed_count += len(original) - len(content)
            print(f"[FIXED] {filepath}")
    
    except Exception as e:
        print(f"[ERROR] {filepath}: {str(e)}")

print("\n" + "="*60)
print(f"修复完成！")
print(f"修复文件数: {files_fixed}")
print(f"移除乱码字符数: {fixed_count}")
print("="*60)
