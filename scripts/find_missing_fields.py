import json
import os
import re
from pathlib import Path

# 读取报告
with open('reports/content_coverage/coverage_audit_20260907_151716.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

pf = data['post_fields']
print(f'总文章数: {pf["total_posts"]}')

all_missing = {}
for field in ['last_updated', 'description', 'canonical_url', 'content_id']:
    missing = pf[field]['missing']
    count = pf[field]['count']
    print(f'\n{field}: {count}/{pf["total_posts"]} 缺失{len(missing)}篇:')
    for m in missing:
        print(f'  {m}')
        all_missing.setdefault(m, []).append(field)

print('\n\n=== 按文章汇总缺失字段 ===')
for post, fields in sorted(all_missing.items()):
    print(f'{post}: {fields}')
