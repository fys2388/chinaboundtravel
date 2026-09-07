import re
import os
from pathlib import Path

posts_dir = Path('content/posts')

# 需要修复的文章
fix_bom = ['2026-07-22-cultural-etiquette-guide.md']
fix_canonical = [
    '2026-05-26-7-day-china-itinerary-beijing-xian-shanghai-first-timers.md',
    '2026-05-26-is-china-safe-for-tourists-2026-honest-assessment.md',
    '2026-07-16-china-transportation-complete-guide-trains-subways-taxis-and-more.md',
    '2026-07-16-is-china-safe-for-tourists-2026-honest-safety-assessment.md',
    '2026-09-01-chinabound-travel-guide-2026-09-monthly-update.md',
    'best-travel-insurance-china.md',
]

def read_frontmatter(text):
    """读取 front matter，返回 (fm_text, body, delimiter)"""
    # 处理 BOM
    if text.startswith('\ufeff'):
        text = text[1:]
    
    if text.startswith('+++'):
        match = re.match(r'^\+\+\+\s*\n(.*?)\n\+\+\+\s*\n', text, re.DOTALL)
        if match:
            return match.group(1), text[match.end():], '+++'
    else:
        match = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.DOTALL)
        if match:
            return match.group(1), text[match.end():], '---'
    return None, text, None

def get_slug_from_filename(filename):
    """从文件名生成 slug"""
    # 移除日期前缀和 .md 后缀
    name = filename.replace('.md', '')
    # 移除日期前缀 (YYYY-MM-DD-)
    name = re.sub(r'^\d{4}-\d{2}-\d{2}-', '', name)
    return name

def get_slug_from_fm(fm_text, filename):
    """从 front matter 获取 slug，如果没有则从文件名生成"""
    m = re.search(r'^slug\s*[:=]\s*["\']?([^"\'\n]+)', fm_text, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return get_slug_from_filename(filename)

# 修复 BOM
for filename in fix_bom:
    filepath = posts_dir / filename
    text = filepath.read_text(encoding='utf-8')
    if text.startswith('\ufeff'):
        text = text[1:]
        filepath.write_text(text, encoding='utf-8')
        print(f'✅ 移除 BOM: {filename}')
    else:
        print(f'⏭️  无 BOM: {filename}')

# 修复 canonical_url
for filename in fix_canonical:
    filepath = posts_dir / filename
    text = filepath.read_text(encoding='utf-8')
    
    # 处理 BOM
    if text.startswith('\ufeff'):
        text = text[1:]
    
    fm_text, body, delimiter = read_frontmatter(text)
    if fm_text is None:
        print(f'❌ 无法解析 front matter: {filename}')
        continue
    
    # 检查是否已有 canonicalURL
    if re.search(r'^canonicalURL\s*[:=]', fm_text, re.MULTILINE | re.IGNORECASE):
        print(f'⏭️  已有 canonicalURL: {filename}')
        continue
    
    # 获取 slug
    slug = get_slug_from_fm(fm_text, filename)
    canonical_url = f'https://www.chinaboundtravel.com/posts/{slug}/'
    
    # 在 front matter 末尾添加 canonicalURL
    # 找到合适的插入位置（在最后一个简单 key:value 之后）
    lines = fm_text.split('\n')
    insert_idx = len(lines)
    
    # 从后往前找，跳过空行和嵌套结构
    for i in range(len(lines) - 1, -1, -1):
        line = lines[i].strip()
        if line and not line.startswith('-') and not line.startswith(' ') and not line.startswith('\t'):
            # 检查是否是简单 key:value
            if re.match(r'^\w+\s*[:=]', line):
                insert_idx = i + 1
                break
    
    new_fm_lines = lines[:insert_idx] + [f'canonicalURL: "{canonical_url}"'] + lines[insert_idx:]
    new_fm = '\n'.join(new_fm_lines)
    
    # 重新组装文件
    new_text = f'{delimiter}\n{new_fm}\n{delimiter}\n{body}'
    filepath.write_text(new_text, encoding='utf-8')
    print(f'✅ 添加 canonicalURL: {filename} -> {canonical_url}')

print('\n=== 修复完成 ===')
