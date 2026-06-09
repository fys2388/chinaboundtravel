#!/usr/bin/env python3
"""
delete_buffer_drafts.py - 删除Buffer草稿箱中的所有帖子

功能：
1. 获取Buffer账户中所有的草稿帖子
2. 删除所有草稿帖子
3. 禁止提前缓存，只有触发时才缓存

注意：此脚本需要Buffer API权限
"""

import json
import os
import requests
import sys
from typing import List, Dict

sys.stdout.reconfigure(encoding='utf-8')


class BufferDraftDeleter:
    def __init__(self):
        self.config = self._load_config()
        self.base_url = self.config['api']['base_url']
        self.access_token = self.config['api']['access_token']
    
    def _load_config(self) -> Dict:
        """加载Buffer配置"""
        # 尝试从多个位置加载配置
        config_paths = [
            'buffer_config.json',
            'chinaboundtravel_social_bot/buffer_config.json',
            '../buffer_config.json'
        ]
        
        for path in config_paths:
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except Exception as e:
                    print(f"ERROR: Failed to load {path}: {str(e)}")
                    sys.exit(1)
        
        print(f"ERROR: buffer_config.json not found in any of: {config_paths}")
        sys.exit(1)
    
    def _graphql_request(self, query: str, variables: Dict = None) -> Dict:
        """执行GraphQL请求"""
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'query': query,
            'variables': variables or {}
        }
        
        try:
            response = requests.post(self.base_url, json=data, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            if 'errors' in result:
                print(f"GraphQL errors: {json.dumps(result['errors'], indent=2, ensure_ascii=False)}")
                return {}
            
            return result.get('data', {})
        except requests.exceptions.HTTPError as e:
            try:
                error_details = response.json()
                print(f"HTTP Error {response.status_code}: {json.dumps(error_details, indent=2, ensure_ascii=False)}")
            except:
                print(f"HTTP Error {response.status_code}: {response.text}")
            return {}
        except Exception as e:
            print(f"Buffer API error: {str(e)}")
            return {}
    
    def get_drafts(self) -> List[Dict]:
        """获取所有草稿帖子"""
        query = """
        query {
          account {
            drafts {
              edges {
                node {
                  id
                  text
                  createdAt
                  channel {
                    id
                    name
                    service
                  }
                }
              }
            }
          }
        }
        """
        
        result = self._graphql_request(query)
        edges = result.get('account', {}).get('drafts', {}).get('edges', [])
        return [edge['node'] for edge in edges]
    
    def delete_post(self, post_id: str) -> bool:
        """删除指定的帖子"""
        query = """
        mutation DeletePost($input: DeletePostInput!) {
          deletePost(input: $input) {
            ... on PostActionSuccess {
              success
            }
            ... on MutationError {
              message
            }
          }
        }
        """
        
        variables = {
            'input': {
                'id': post_id
            }
        }
        
        result = self._graphql_request(query, variables)
        
        if result and result.get('deletePost'):
            delete_data = result['deletePost']
            if 'message' in delete_data:
                print(f"  ERROR deleting {post_id}: {delete_data['message']}")
                return False
            else:
                print(f"  SUCCESS deleted {post_id}")
                return True
        
        print(f"  FAILED to delete {post_id}")
        return False
    
    def delete_all_drafts(self) -> Dict:
        """删除所有草稿"""
        print("=== 正在获取草稿列表 ===")
        drafts = self.get_drafts()
        
        if not drafts:
            print("✓ 草稿箱为空，无需删除")
            return {"deleted": 0, "failed": 0}
        
        print(f"找到 {len(drafts)} 篇草稿:")
        for i, draft in enumerate(drafts, 1):
            channel_info = f"{draft['channel']['name']} ({draft['channel']['service']})"
            text_preview = draft['text'][:50] + "..." if len(draft['text']) > 50 else draft['text']
            print(f"  {i}. [{channel_info}] {text_preview}")
        
        print("\n=== 开始删除草稿 ===")
        deleted = 0
        failed = 0
        
        for draft in drafts:
            if self.delete_post(draft['id']):
                deleted += 1
            else:
                failed += 1
        
        print(f"\n=== 删除完成 ===")
        print(f"已删除: {deleted} 篇")
        print(f"删除失败: {failed} 篇")
        
        return {"deleted": deleted, "failed": failed}


def main():
    """主函数"""
    print("=" * 60)
    print("Buffer 草稿删除工具")
    print("=" * 60)
    
    deleter = BufferDraftDeleter()
    result = deleter.delete_all_drafts()
    
    # 输出最终结果
    print("\n" + "=" * 60)
    if result['failed'] == 0:
        print("✓ 所有草稿已成功删除")
        sys.exit(0)
    else:
        print(f"⚠️ 部分草稿删除失败 ({result['failed']} 篇)")
        sys.exit(1)


if __name__ == "__main__":
    main()
