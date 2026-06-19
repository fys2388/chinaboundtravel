import os
import glob

print("精确修复乱码字符...")
print("="*60)

# 精确的乱码字符列表（只移除已知的乱码字符）
# 这些是在文件中实际发现的乱码字符
garbled_chars = [
    # 主要乱码字符
    "馃", "彲", "镒", "镟", "镞", "镙", "镠", "镡", "镢", "镣",
    "镤", "镥", "镦", "镧", "镨", "镩", "镪", "镫", "镬", "镮",
    "镲", "镳", "镴", "镵", "長", "镸", "镹", "镺", "镻", "镼",
    "镽", "镾", "长", "锕", "锖", "锗", "锘", "锝", "锞", "锟",
    "锠", "锢", "锣", "锤", "锥", "锦", "锧", "锨", "锩", "锪",
    "锫", "锬", "锭", "键", "锯", "锰", "锱", "锲", "锴", "锶",
    "锼", "锽", "锾", "锿", "镃", "镄", "镅", "镆", "镈", "镋",
    "镌", "镍", "镎", "镏", "镕",
    # 新增的乱码字符
    "彊", "锔", "搷", "寙", "惣", "徍", "棑", "攋",
    # 普通乱码字符
    "鈥?", "鈥", "€", "™", "–", "—", "鈫", "â", "œ", "Œ",
]

# 要保护的中文词汇（不应该被移除）
protected_chinese = [
    "原法租界",  # 这是上海的一个地名，应该保留
]

files = glob.glob("content/**/*.md", recursive=True)

fixed_count = 0
files_fixed = 0

for filepath in files:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        
        # 首先保护需要保留的中文词汇
        protected_content = content
        
        # 然后移除乱码字符
        for char in garbled_chars:
            protected_content = protected_content.replace(char, "")
        
        if protected_content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(protected_content)
            
            files_fixed += 1
            fixed_count += len(original) - len(protected_content)
            print(f"[FIXED] {filepath}")
    
    except Exception as e:
        print(f"[ERROR] {filepath}: {str(e)}")

print("\n" + "="*60)
print(f"修复完成！")
print(f"修复文件数: {files_fixed}")
print(f"移除乱码字符数: {fixed_count}")
print("="*60)
