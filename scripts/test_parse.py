import re
from pathlib import Path

post = Path('content/posts/2026-07-22-cultural-etiquette-guide.md')
text = post.read_text(encoding='utf-8')

# 模拟审计脚本的解析
match = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.DOTALL)
if match:
    fm_text = match.group(1)
    print('front matter 提取成功，长度:', len(fm_text))
    print('前300字符:')
    print(fm_text[:300])
    print()
    
    fm = {}
    for line in fm_text.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        m = re.match(r'^(\w+)\s*[:=]\s*(.+)$', line)
        if m:
            key = m.group(1).lower()
            value = m.group(2).strip().strip('"').strip("'")
            fm[key] = value
    
    print('解析到的字段:', list(fm.keys()))
    print('last_updated:', fm.get('last_updated', 'MISSING'))
    print('description:', fm.get('description', 'MISSING'))
    print('canonicalurl:', fm.get('canonicalurl', 'MISSING'))
    print('content_id:', fm.get('content_id', 'MISSING'))
else:
    print('front matter 提取失败')
    print('前100字符:', repr(text[:100]))
