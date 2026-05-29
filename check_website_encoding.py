import os
import glob

print("检查 Hugo 网站乱码字符...")
print("="*80)

# 常见的乱码字符
garbled_chars = ["鈥", "â", "€", "™", "oe", "–", "—"]

# 检查所有 markdown 文件
pattern = "content/**/*.md"
files = glob.glob(pattern, recursive=True)

total_issues = 0
files_with_issues = []

for filepath in files:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        for garbled in garbled_chars:
            if garbled in content:
                files_with_issues.append(filepath)
                total_issues += 1
                print(f"\n[发现问题] {filepath}")
                print(f"  包含乱码字符: '{garbled}'")
                
    except Exception as e:
        pass

print("\n" + "="*80)
print(f"检查完成！")
print(f"发现问题文件数: {len(files_with_issues)}")
print(f"乱码总数: {total_issues}")

if total_issues == 0:
    print("\n[OK] 未发现乱码字符！")
else:
    print("\n[FAIL] 发现乱码，需要修复！")
    for f in set(files_with_issues):
        print(f"  - {f}")
