import re

with open('scripts/social_analytics_pull.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 替换 get_organization_id 函数，使用 account 查询
old_func = '''def get_organization_id(token: str) -> str:
    """Get organization ID for the current user via introspection."""
    # First try organizations query
    query = """
    query GetOrganizations {
      organizations {
        id
        name
      }
    }
    """
    data = buffer_api_request(token, query)
    if data and "organizations" in data:
        orgs = data["organizations"]
        if orgs:
            return orgs[0].get("id")
    
    # Try introspection to find available queries
    intro_query = """
    query IntrospectQuery {
      __schema {
        queryType {
          fields {
            name
            type {
              name
              kind
            }
          }
        }
      }
    }
    """
    data = buffer_api_request(token, intro_query)
    if data and "__schema" in data:
        fields = data["__schema"]["queryType"]["fields"]
        field_names = [f["name"] for f in fields]
        print(f"  Available query fields: {field_names[:20]}")
        
        # Try to find organization-related field
        for field in fields:
            if "org" in field["name"].lower():
                print(f"  Found org field: {field['name']}")
    
    return None'''

new_func = '''def get_organization_id(token: str) -> str:
    """Get organization ID for the current user via account query."""
    query = """
    query GetAccount {
      account {
        id
        name
        organization {
          id
          name
        }
      }
    }
    """
    data = buffer_api_request(token, query)
    if data and "account" in data:
        account = data["account"]
        # Try to get organization from account
        if "organization" in account and account["organization"]:
            org_id = account["organization"].get("id")
            if org_id:
                print(f"  Got organization ID from account: {org_id}")
                return org_id
        # If no organization field, try account ID itself
        account_id = account.get("id")
        if account_id:
            print(f"  Using account ID as org ID: {account_id}")
            return account_id
    
    # Print account data for debugging
    if data:
        print(f"  Account data keys: {list(data.keys())}")
        if "account" in data:
            print(f"  Account fields: {list(data['account'].keys())}")
    
    return None'''

content = content.replace(old_func, new_func)
print('get_organization_id 函数已更新，使用account查询')

with open('scripts/social_analytics_pull.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('文件已保存')
