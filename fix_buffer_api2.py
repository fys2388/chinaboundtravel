import re

with open('scripts/social_analytics_pull.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 替换 get_channels 函数，添加 get_organization_id 函数
old_func = '''def get_channels(token: str) -> list:
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

new_func = '''def get_organization_id(token: str) -> str:
    """Get organization ID for the current user."""
    query = """
    query GetMe {
      me {
        id
        name
        organizations {
          id
          name
        }
      }
    }
    """
    data = buffer_api_request(token, query)
    if data and "me" in data:
        orgs = data["me"].get("organizations", [])
        if orgs:
            return orgs[0].get("id")
    return None


def get_channels(token: str) -> list:
    """Get connected social media channels."""
    org_id = get_organization_id(token)
    if not org_id:
        print("  Warning: Could not get organization ID")
        return []
    
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
            "organizationId": org_id
        }
    }
    data = buffer_api_request(token, query, variables)
    if data and "channels" in data:
        return data["channels"]
    return []'''

content = content.replace(old_func, new_func)
print('get_channels 函数已更新，添加了 get_organization_id')

with open('scripts/social_analytics_pull.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('文件已保存')
