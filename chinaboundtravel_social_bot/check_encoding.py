import os
import glob

print("检查乱码字符...")
print("="*80)

# 常见的乱码字符
garbled_chars = ["鈥", "�", "â", "€", "™"]

# 检查的文件扩展名
extensions = ["*.md", "*.txt", "*.html"]

total_issues = 0
files_with_issues = []

for ext in extensions:
    pattern = f"content/**/{ext}"
    files = glob.glob(pattern, recursive=True)
    
    for filepath in files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
            for garbled in garbled_chars:
                if garbled in content:
                    line_num = content[:content.index(garbled)].count('\n') + 1
                    files_with_issues.append(filepath)
                    total_issues += 1
                    print(f"\n[发现问题] {filepath}")
                    print(f"  行 {line_num}: 包含乱码字符 '{garbled}'")
                    
                    # 显示周围的内容
                    start = max(0, content.index(garbled) - 30)
                    end = min(len(content), content.index(garbled) + 30)
                    context = content[start:end].replace('\n', ' ')
                    print(f"  上下文: ...{context}...")
                    
        except Exception as e:
            print(f"[错误] {filepath}: {str(e)}")

print("\n" + "="*80)
print(f"检查完成！")
print(f"发现问题文件数: {len(set(files_with_issues))}")
print(f"乱码总数: {total_issues}")

if total_issues == 0:
    print("\n[OK] 未发现乱码字符！")
else:
    print("\n[FAIL] 发现乱码，需要修复！")
