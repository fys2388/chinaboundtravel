#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cloudflare Pages Secrets Verification Script
Validates API Token and Account ID configuration
"""

import requests
import sys

def verify_cloudflare_credentials(api_token, account_id):
    """验证Cloudflare API Token和Account ID"""
    print("Verifying Cloudflare API Token and Account ID...\n")
    
    # 1. 验证Token是否有效
    print("1. Testing API Token validity...")
    headers = {
        'Authorization': f'Bearer {api_token}',
        'Content-Type': 'application/json'
    }
    
    try:
        # 调用用户信息API验证Token
        response = requests.get(
            'https://api.cloudflare.com/client/v4/user',
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                email = data['result'].get('email', 'N/A')
                print(f"   SUCCESS: Token is valid for user: {email}")
            else:
                print(f"   ERROR: Token validation failed: {data.get('errors', 'Unknown error')}")
                return False
        elif response.status_code == 401:
            print("   ERROR: Unauthorized - Invalid API Token")
            return False
        else:
            print(f"   ERROR: API request failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"   ERROR: {str(e)}")
        return False
    
    # 2. 验证Account ID是否存在
    print("\n2. Testing Account ID...")
    try:
        response = requests.get(
            f'https://api.cloudflare.com/client/v4/accounts/{account_id}',
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                account_name = data['result'].get('name', 'N/A')
                print(f"   SUCCESS: Account found: {account_name}")
            else:
                print(f"   ERROR: Account not found: {data.get('errors', 'Unknown error')}")
                return False
        elif response.status_code == 404:
            print("   ERROR: Account ID not found")
            return False
        elif response.status_code == 403:
            print("   ERROR: Forbidden - Token does not have access to this account")
            return False
        else:
            print(f"   ERROR: API request failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"   ERROR: {str(e)}")
        return False
    
    # 3. 验证Pages项目权限
    print("\n3. Testing Pages project access...")
    try:
        response = requests.get(
            f'https://api.cloudflare.com/client/v4/accounts/{account_id}/pages/projects',
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                projects = data['result']
                project_names = [p['name'] for p in projects]
                print(f"   SUCCESS: Found {len(projects)} Pages projects")
                print(f"   Projects: {', '.join(project_names)}")
                
                # 检查chinaboundtravel项目是否存在
                if 'chinaboundtravel' in project_names:
                    print("   CONFIRMED: 'chinaboundtravel' project exists")
                else:
                    print("   WARNING: 'chinaboundtravel' project not found in this account")
                    print("   Please verify the project name in Cloudflare Pages")
            else:
                print(f"   ERROR: Failed to list projects: {data.get('errors', 'Unknown error')}")
                return False
        elif response.status_code == 403:
            print("   ERROR: Forbidden - Token does not have Pages access")
            return False
        else:
            print(f"   ERROR: API request failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"   ERROR: {str(e)}")
        return False
    
    # 4. 检查Token权限范围
    print("\n4. Checking Token permissions...")
    try:
        response = requests.get(
            'https://api.cloudflare.com/client/v4/user/tokens/verify',
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                policies = data['result'].get('policies', [])
                print(f"   Token has {len(policies)} permission policy(ies)")
                
                has_pages_write = False
                for policy in policies:
                    resources = policy.get('resources', [])
                    permission_groups = policy.get('permission_groups', [])
                    
                    for perm in permission_groups:
                        perm_name = perm.get('name', '')
                        if 'Pages' in perm_name and 'Write' in perm_name:
                            has_pages_write = True
                            print(f"   FOUND: {perm_name}")
                
                if has_pages_write:
                    print("   SUCCESS: Token has Pages Write permission")
                else:
                    print("   WARNING: Token may not have Pages Write permission")
                    print("   Required: Cloudflare Pages > Edit permission")
            else:
                print(f"   ERROR: Failed to verify token permissions")
    except Exception as e:
        print(f"   ERROR: {str(e)}")
    
    return True

def test_deployment(api_token, account_id, project_name):
    """测试部署API"""
    print("\n5. Testing Pages deployment API...")
    
    headers = {
        'Authorization': f'Bearer {api_token}',
        'Content-Type': 'application/json'
    }
    
    try:
        # 尝试列出部署历史
        response = requests.get(
            f'https://api.cloudflare.com/client/v4/accounts/{account_id}/pages/projects/{project_name}/deployments',
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                deployments = data['result']
                if deployments:
                    latest = deployments[0]
                    status = latest.get('environment', {}).get('status', 'N/A')
                    print(f"   SUCCESS: Found {len(deployments)} deployments")
                    print(f"   Latest deployment status: {status}")
                else:
                    print("   INFO: No deployments found yet")
            else:
                print(f"   ERROR: {data.get('errors', 'Unknown error')}")
        elif response.status_code == 403:
            print("   ERROR: Forbidden - Check Pages permissions")
        else:
            print(f"   ERROR: API request failed with status {response.status_code}")
            
    except Exception as e:
        print(f"   ERROR: {str(e)}")

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    
    print("=" * 70)
    print("Cloudflare Pages Secrets Verification Tool")
    print("=" * 70)
    print("This tool verifies if your Cloudflare API Token and Account ID")
    print("are correctly configured for GitHub Actions deployment.\n")
    
    # 从环境变量获取或提示用户输入
    import os
    
    api_token = os.environ.get('CLOUDFLARE_API_TOKEN')
    account_id = os.environ.get('CLOUDFLARE_ACCOUNT_ID')
    
    if not api_token or not account_id:
        print("Please enter your Cloudflare credentials:")
        api_token = input("API Token: ").strip()
        account_id = input("Account ID: ").strip()
    
    print("\n" + "-" * 70)
    
    if verify_cloudflare_credentials(api_token, account_id):
        print("\n" + "=" * 70)
        print("All checks passed! Your credentials are valid.")
        print("=" * 70)
        
        # 额外测试部署API
        test_deployment(api_token, account_id, 'chinaboundtravel')
        
        print("\n" + "=" * 70)
        print("Next steps:")
        print("1. Ensure these values are set in GitHub Secrets")
        print("2. Trigger GitHub Actions workflow")
        print("3. Verify deployment in Cloudflare Pages dashboard")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("Some checks failed! Please verify your credentials.")
        print("=" * 70)