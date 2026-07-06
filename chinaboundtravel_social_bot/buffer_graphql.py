import json
import requests
import schedule
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import sys
import io
import zoneinfo

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

class BufferGraphQLClient:
    def __init__(self, config_path: str = 'buffer_config.json'):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        self.base_url = self.config['api']['base_url']
        self.access_token = self.config['api']['access_token']
        self.timezone = self.config['default_schedule']['timezone']
        self.best_times = self.config['default_schedule']['best_times']
        
    def _graphql_request(self, query: str, variables: Dict = None) -> Dict:
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
            print(f"Buffer GraphQL API error: {str(e)}")
            return {}
    
    def get_channels(self) -> List[Dict]:
        query = """
        query GetChannels($input: ChannelsInput!) {
          channels(input: $input) {
            id
            service
            name
          }
        }
        """
        org_id = self.config.get('organization_id', '6a20329943b37a7289e25b6d')
        result = self._graphql_request(query, {'input': {'organizationId': org_id}})
        return result.get('channels', [])
    
    def create_post(self, channel_id: str, text: str, scheduled_at: Optional[str] = None) -> Dict:
        query = """
        mutation CreatePost($input: CreatePostInput!) {
          createPost(input: $input) {
            ... on PostActionSuccess {
              post {
                id
                text
              }
            }
            ... on MutationError {
              message
            }
          }
        }
        """
        
        if scheduled_at:
            variables = {
                'input': {
                    'channelId': channel_id,
                    'text': text,
                    'schedulingType': 'automatic',
                    'mode': 'customScheduled',
                    'dueAt': scheduled_at
                }
            }
        else:
            variables = {
                'input': {
                    'channelId': channel_id,
                    'text': text,
                    'schedulingType': 'automatic',
                    'mode': 'shareNow'
                }
            }
        
        return self._graphql_request(query, variables)
    
    def schedule_daily_posts(self, content_list: List[Dict]) -> None:
        enabled_channels = [ch for ch in self.config['channels'].values() if ch['enabled'] and ch['channel_id']]
        
        if not enabled_channels:
            print("ERROR: No enabled channels with channel_id found.")
            return
        
        print(f"Found {len(enabled_channels)} enabled channels: {[ch['name'] for ch in enabled_channels]}")
        
        for idx, post_time in enumerate(self.best_times):
            if idx >= len(content_list):
                break
            
            content = content_list[idx]
            scheduled_time = self._get_scheduled_time(post_time)
            
            for channel in enabled_channels:
                print(f"Trying to schedule to {channel['name']} at {post_time}")
                result = self.create_post(
                    channel_id=channel['channel_id'],
                    text=content['text'],
                    scheduled_at=scheduled_time
                )
                
                if result and result.get('createPost'):
                    post_data = result['createPost']
                    if 'message' in post_data:
                        print(f"ERROR: {channel['name']} - {post_data['message']}")
                    else:
                        print(f"SUCCESS: {channel['name']} - Post scheduled successfully!")
                elif result:
                    print(f"SUCCESS: {channel['name']} - Post scheduled successfully!")
                else:
                    print(f"FAILED: {channel['name']} - Unknown error")
    
    def _get_scheduled_time(self, time_str: str) -> str:
        tz = zoneinfo.ZoneInfo(self.timezone)
        now = datetime.now(tz)
        hour, minute = map(int, time_str.split(':'))
        scheduled = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        if scheduled < now:
            scheduled += timedelta(days=1)
        
        return scheduled.isoformat()
    
    def run_scheduler(self, content_provider) -> None:
        """
        调度器已禁用自动预缓存功能。
        帖子将不再提前缓存到Buffer草稿箱，只有在触发时才会发布。
        """
        print("Buffer GraphQL Scheduler is DISABLED")
        print("WARNING: Auto-scheduling and pre-caching is disabled.")
        print("Posts will only be created when explicitly triggered.")
        
        # 保持空循环但不做任何调度
        while True:
            time.sleep(3600)  # 每小时检查一次，但不执行任何操作

def example_content_provider():
    return [
        {
            'text': "ChinaBound Travel - Your Ultimate Guide to China! https://chinaboundtravel.com #ChinaTravel"
        },
        {
            'text': "Travel Tip: Always carry cash in China! #ChinaTravel #TravelTips"
        },
        {
            'text': "New Article: 7-Day China Itinerary https://chinaboundtravel.com/7-day-itinerary #ChinaTravel"
        },
        {
            'text': "Planning a trip to China? Check our visa guide! https://chinaboundtravel.com/visa-guide"
        }
    ]

if __name__ == '__main__':
    client = BufferGraphQLClient()
    
    print("=== Buffer GraphQL Client ===")
    print("\n1. Testing API connection...")
    
    channels = client.get_channels()
    
    if channels:
        print("\nConnected! Your Buffer channels:")
        for i, channel in enumerate(channels):
            print(f"  {i+1}. {channel['name']} ({channel['service']}) - ID: {channel['id']}")
    else:
        print("\nERROR: Failed to fetch channels. Check your API token.")
    
    print("\n2. Testing immediate post creation...")
    print("Creating post to Twitter channel...")
    test_result = client.create_post(
        channel_id="6a17e044c687a22dd4346bf4",
        text="Test post from Buffer GraphQL API! https://chinaboundtravel.com #ChinaTravel"
    )
    
    if test_result:
        if test_result.get('createPost'):
            post_data = test_result['createPost']
            if 'message' in post_data:
                print(f"ERROR: {post_data['message']}")
            else:
                print("SUCCESS: Post created successfully!")
        else:
            print("SUCCESS: Post created successfully!")
    else:
        print("FAILED: Unknown error")
    
    print("\nBuffer GraphQL Client setup complete!")
    print("Use client.run_scheduler(provider) to start the scheduler")
