import re

with open('scripts/social_analytics_pull.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 替换 get_organization_id 函数，使用 account.organizations 查询
old_func = '''def get_organization_id(token: str) -> str:
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

new_func = '''def get_organization_id(token: str) -> str:
    """Get organization ID for the current user via account query."""
    # Try account.organizations (plural)
    query = """
    query GetAccount {
      account {
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
    if data and "account" in data:
        account = data["account"]
        # Try to get organizations from account
        if "organizations" in account and account["organizations"]:
            orgs = account["organizations"]
            if orgs:
                org_id = orgs[0].get("id")
                if org_id:
                    print(f"  Got organization ID from account.organizations: {org_id}")
                    return org_id
        # If no organizations, try account ID itself
        account_id = account.get("id")
        if account_id:
            print(f"  Using account ID as org ID: {account_id}")
            return account_id
    
    # Print data for debugging
    if data:
        print(f"  Data keys: {list(data.keys())}")
        if "account" in data:
            print(f"  Account fields: {list(data['account'].keys())}")
            if "organizations" in data["account"]:
                print(f"  Organizations: {data['account']['organizations']}")
    
    return None'''

content = content.replace(old_func, new_func)
print('get_organization_id 函数已更新，使用account.organizations')

with open('scripts/social_analytics_pull.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('文件已保存')
