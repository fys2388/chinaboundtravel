import sys
sys.stdout.reconfigure(encoding='utf-8')

import logging
from modules.buffer_poster import BufferPoster

logging.basicConfig(level=logging.INFO)

print("=" * 60)
print("社媒分发测试")
print("=" * 60)

poster = BufferPoster()

print(f"\n连接状态: {'已连接' if poster.is_connected() else '未连接'}")
print(f"可用频道: {len(poster.get_channels())}")

for i, channel in enumerate(poster.get_channels()):
    print(f"  {i+1}. {channel['name']} ({channel['service']})")

test_content = {
    'title': 'ChinaBound Travel - China Visa Guide',
    'summary': 'Everything you need to know about Chinese visa for foreigners',
    'url': 'https://chinaboundtravel.com/visa-guide',
    'tags': ['ChinaTravel', 'ChinaVisa', 'Travel']
}

print(f"\n测试内容:")
print(f"  标题: {test_content['title']}")
print(f"  URL: {test_content['url']}")

formatted = poster.format_post(test_content)
print(f"\n格式化后内容:")
print(formatted)

print("\n测试完成！")
print("=" * 60)