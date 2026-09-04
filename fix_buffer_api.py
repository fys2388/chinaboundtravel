import re

with open('scripts/social_analytics_pull.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 用正则替换 get_channels 函数
pattern = r'def get_channels\(token: str\) -> list:.*?return \[\]'
replacement = '''def get_channels(token: str) -> list:
    """Get connected social media channels."""
    query = """
    query GetChannels($input: ChannelsInput!) {
      channels(input: $input) {
        id
        service
        serviceId
        name
      }
    }
    """
    variables = {
        "input": {
            "limit": 100
        }
    }
    data = buffer_api_request(token, query, variables)
    if data and "channels" in data:
        return data["channels"]
    return []'''

content = re.sub(pattern, replacement, content, flags=re.DOTALL)
print('get_channels 函数已替换')

# 修复 validate_buffer_token 中的 stats 引用
old_stats = "print(f'    - {ch.get(\\'service\\', \\'?\\')}: {ch.get(\\'name\\', \\'?\\')} ({ch.get(\\'stats\\', {}).get(\\'followers\\', 0)} followers)')"
new_stats = "print(f'    - {ch.get(\\'service\\', \\'?\\')}: {ch.get(\\'name\\', \\'?\\')}')"
content = content.replace(old_stats, new_stats)
print('validate_buffer_token stats引用已修复')

with open('scripts/social_analytics_pull.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('文件已保存')
