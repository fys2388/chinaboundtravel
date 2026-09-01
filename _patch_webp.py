import sys
path = r'E:\AI\dulizhan\travel-blog\chinaboundtravel_social_bot\social_publisher.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old = '''    """调用 Cloudflare Worker 发布到多平台"""
    # P1-GROWTH-28A: 双账户路由 - Pinterest 长尾账户走 NEW_BUFFER_WORKER_URL，其余走主账户'''

new = '''    """调用 Cloudflare Worker 发布到多平台"""
    # Buffer API 不支持 .webp 格式，自动转换为 .jpg（网站同时保留两种格式）
    if cover_url and cover_url.lower().endswith(".webp"):
        original_cover = cover_url
        cover_url = cover_url[:-5] + ".jpg"
        print(f"[CoverFix] .webp -> .jpg: {original_cover[-40:]} -> {cover_url[-40:]}")
    # P1-GROWTH-28A: 双账户路由 - Pinterest 长尾账户走 NEW_BUFFER_WORKER_URL，其余走主账户'''

if old in content:
    content = content.replace(old, new, 1)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: Added .webp -> .jpg conversion in publish_to_worker')
else:
    print('FAILED: Could not find target string')
    idx = content.find('def publish_to_worker')
    if idx >= 0:
        print('Context:', repr(content[idx:idx+300]))
