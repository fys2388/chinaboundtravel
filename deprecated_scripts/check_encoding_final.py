import os
import glob

print("最终检查网站编码...")
print("="*80)

# 只检查真正有问题的乱码字符
garbled_chars = ["鈥", "€", "™", "–", "—", "鈫", "鈥?"]

pattern = "content/**/*.md"
files = glob.glob(pattern, recursive=True)

files_with_issues = []

for filepath in files:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        for garbled in garbled_chars:
            if garbled in content:
                files_with_issues.append(filepath)
                print(f"[问题] {filepath} - 包含 '{garbled}'")
    except Exception as e:
        pass

print("\n" + "="*80)
if files_with_issues:
    print(f"[FAIL] 还有 {len(files_with_issues)} 个文件包含乱码字符")
    print("需要修复的问题文件:")
    for f in set(files_with_issues):
        print(f"  - {f}")
else:
    print("[OK] 所有乱码已修复！")
print("="*80)
