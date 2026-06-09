import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import logging
from datetime import datetime
from modules.buffer_poster import BufferPoster
from content_manager import ContentManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_buffer_post():
    print("=" * 70)
    print("           Buffer 发布测试")
    print("=" * 70)
    
    # 初始化 Buffer 发布器
    print("\n[1] 初始化 Buffer 发布器...")
    poster = BufferPoster()
    
    if not poster.is_connected():
        print("❌ Buffer 连接失败！")
        return False
    
    print("✅ Buffer 连接成功！")
    
    # 显示可用频道
    print("\n[2] 可用频道列表:")
    for i, channel in enumerate(poster.get_channels()):
        print(f"   {i+1}. {channel['name']} ({channel['service']}) - ID: {channel['id']}")
    
    # 加载内容
    print("\n[3] 加载内容库...")
    cm = ContentManager()
    print(f"✅ 共加载 {len(cm.posts)} 条内容")
    
    # 获取一条测试内容
    test_content = cm.posts[0] if cm.posts else {
        'title': 'ChinaBound Travel - 中国旅行指南',
        'summary': '探索中国最美的风景和文化',
        'url': 'https://chinaboundtravel.com',
        'tags': ['ChinaTravel', 'Travel', 'China']
    }
    
    print(f"\n[4] 测试内容:")
    print(f"   标题: {test_content.get('title', 'N/A')}")
    print(f"   URL: {test_content.get('url', 'N/A')}")
    print(f"   标签: {', '.join(test_content.get('tags', []))}")
    
    # 格式化内容
    print(f"\n[5] 格式化内容...")
    formatted_text = poster.format_post(test_content)
    print("   格式化后的文本:")
    print("   " + "-" * 60)
    for line in formatted_text.split('\n'):
        print(f"   {line}")
    print("   " + "-" * 60)
    
    # 提示用户确认
    print("\n" + "=" * 70)
    print("⚠️  警告: 继续将实际发布到 Buffer 连接的社交平台！")
    print("=" * 70)
    
    choice = input("\n是否继续发布？(yes/no): ").strip().lower()
    
    if choice != 'yes':
        print("\n❌ 已取消发布")
        return False
    
    # 发布到所有频道
    print(f"\n[6] 开始发布到 {len(poster.get_channels())} 个频道...")
    results = poster.post_to_all(test_content)
    
    # 显示结果
    print(f"\n[7] 发布结果:")
    success_count = 0
    fail_count = 0
    
    for result in results:
        channel = result.get('channel', {})
        channel_name = channel.get('name', 'Unknown')
        channel_service = channel.get('service', 'Unknown')
        
        if result.get('success'):
            print(f"   ✅ {channel_name} ({channel_service}): 发布成功")
            print(f"      Post ID: {result.get('id')}")
            success_count += 1
        else:
            print(f"   ❌ {channel_name} ({channel_service}): 发布失败")
            print(f"      错误: {result.get('error')}")
            fail_count += 1
    
    # 总结
    print(f"\n" + "=" * 70)
    print(f"测试完成！")
    print(f"成功: {success_count}")
    print(f"失败: {fail_count}")
    print(f"=" * 70)
    
    return success_count > 0


if __name__ == '__main__':
    try:
        success = test_buffer_post()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
