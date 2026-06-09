import os
import glob
import re

print("全面修复所有乱码字符...")
print("="*60)

# 扩展的乱码字符列表（基于文件中发现的）
garbled_chars = [
    # 之前的列表
    "馃", "彲", "镒", "镟", "镞", "镙", "镠", "镡", "镢", "镣",
    "镤", "镥", "镦", "镧", "镨", "镩", "镪", "镫", "镬", "镮",
    "镲", "镳", "镴", "镵", "長", "镸", "镹", "镺", "镻", "镼",
    "镽", "镾", "长", "锕", "锖", "锗", "锘", "锝", "锞", "锟",
    "锠", "锢", "锣", "锤", "锥", "锦", "锧", "锨", "锩", "锪",
    "锫", "锬", "锭", "键", "锯", "锰", "锱", "锲", "锴", "锶",
    "锼", "锽", "锾", "锿", "镃", "镄", "镅", "镆", "镈", "镋",
    "镌", "镍", "镎", "镏", "镕",
    # 新增的乱码字符
    "彊", "锔", "搷", "寙", "惣", "徍", "棑", "攋", "鈥?", "鈥",
    "€", "™", "–", "—", "鈫", "â", "œ", "Œ",
    # 更多 CJK 扩展区字符
    "𠀋", "𠀌", "𠀍", "𠀎", "𠀏", "𠀐", "𠀑", "𠀒", "𠀓", "𠀔",
    "𠀕", "𠀖", "𠀗", "𠀘", "𠀙", "𠀚", "𠀛", "𠀜", "𠀝", "𠀞",
    "𠀟", "𠀠", "𠀡", "𠀢", "𠀣", "𠀤", "𠀥", "𠀦", "𠀧", "𠀨",
]

files = glob.glob("content/**/*.md", recursive=True)

fixed_count = 0
files_fixed = 0

for filepath in files:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        
        # 移除所有乱码字符
        for char in garbled_chars:
            content = content.replace(char, "")
        
        # 额外处理：移除所有 CJK 扩展区字符（Unicode 区块）
        # 这些通常是编码错误产生的
        content = re.sub(r'[\uD800-\uDFFF]', '', content)  # 代理对
        content = re.sub(r'[\u3400-\u4DBF]', '', content)  # CJK 扩展 A
        content = re.sub(r'[\u20000-\u2A6DF]', '', content)  # CJK 扩展 B
        content = re.sub(r'[\u2A700-\u2B73F]', '', content)  # CJK 扩展 C
        content = re.sub(r'[\u2B740-\u2B81F]', '', content)  # CJK 扩展 D
        content = re.sub(r'[\u2B820-\u2CEAF]', '', content)  # CJK 扩展 E
        content = re.sub(r'[\u2CEB0-\u2EBEF]', '', content)  # CJK 扩展 F
        
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
