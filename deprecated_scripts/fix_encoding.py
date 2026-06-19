import os
import glob

print("修复网站编码问题...")
print("="*80)

# 乱码字符及其正确的替换
replacements = {
    "鈥": "",
    "鈥?": "—",
    "â": "",
    "€": "",
    "™": "",
    "œ": "",
    "–": "-",
    "—": "-",
    "鈫": "-",
    "鈥?" : "—"
}

# 需要检查的文件
pattern = "content/**/*.md"
files = glob.glob(pattern, recursive=True)

total_fixed = 0
files_fixed = 0

for filepath in files:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        fixed_content = content
        
        # 替换乱码字符
        for garbled, correct in replacements.items():
            fixed_content = fixed_content.replace(garbled, correct)
        
        # 如果有变化，保存文件
        if fixed_content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            
            files_fixed += 1
            total_fixed += original_content.count("鈥") + original_content.count("–") + original_content.count("—")
            print(f"[FIXED] {filepath}")
            
    except Exception as e:
        print(f"[ERROR] {filepath}: {str(e)}")

print("\n" + "="*80)
print(f"修复完成！")
print(f"修复文件数: {files_fixed}")
print(f"修复乱码数: {total_fixed}")
print("="*80)
