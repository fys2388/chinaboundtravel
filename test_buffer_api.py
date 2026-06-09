#!/usr/bin/env python3
import json
import requests

with open('chinaboundtravel_social_bot/buffer_config.json', 'r') as f:
    config = json.load(f)

headers = {
    'Authorization': f"Bearer {config['api']['access_token']}",
    'Content-Type': 'application/json'
}

query = '''
query {
  account {
    id
    name
    channels {
      id
      name
      service
    }
  }
}
'''

response = requests.post(config['api']['base_url'], json={'query': query}, headers=headers)
print(f'HTTP Status: {response.status_code}')
if response.status_code == 200:
    data = response.json()
    if 'errors' in data:
        print(f'GraphQL Errors: {json.dumps(data["errors"], indent=2)}')
    else:
        print('API连接成功!')
        print(f"账户名: {data['data']['account']['name']}")
        print(f"频道数量: {len(data['data']['account']['channels'])}")
        for ch in data['data']['account']['channels']:
            print(f"  - {ch['name']} ({ch['service']})")
else:
    print(f'失败: {response.text}')
