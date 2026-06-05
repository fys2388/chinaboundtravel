from pathlib import Path
import os
import sys

sys.path.insert(0, str(Path(__file__).parent))
os.chdir(Path(__file__).parent)

from joran_blog_generator import generate_cover_for_post

url1 = generate_cover_for_post('Chengdu Panda Adventure: A Traveler Guide', 'chengdu-panda-adventure-guide')
print(f'封面1 URL: {url1}')

url2 = generate_cover_for_post('Beijing Great Wall: Complete Hiking Guide', 'beijing-great-wall-hiking-guide')
print(f'封面2 URL: {url2}')

url3 = generate_cover_for_post('Shanghai Bund Night Walk: A Local Guide', 'shanghai-bund-night-walk')
print(f'封面3 URL: {url3}')

# 检查文件
base = Path('../static/img/china-dest')
for category in ['chengdu', 'beijing', 'shanghai']:
    cat_dir = base / category
    if cat_dir.exists():
        files = list(cat_dir.glob('*.jpg'))
        print(f'{category}: {len(files)} files')
        for f in files:
            print(f'  {f.name}: {f.stat().st_size} bytes')
    else:
        print(f'{category}: 目录不存在')

# 测试 Worker 接口
print('\n=== 测试 Worker 发布接口 ===')
import requests

body = {
    "title": "Chengdu Panda Adventure: A Traveler Guide",
    "desc": "Experience pandas in Chengdu, China. Tips, timing, and local food recommendations for travelers visiting the famous Sichuan capital.",
    "cover": url1,
    "url": "https://chinaboundtravel.com/posts/chengdu-panda-adventure-guide/"
}

resp = requests.post('https://buffer-auto-poster.fys2388.workers.dev/publish', json=body, timeout=90)
print(f'Status: {resp.status_code}')
import json
print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
