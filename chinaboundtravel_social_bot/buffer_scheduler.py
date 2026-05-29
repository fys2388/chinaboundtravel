import json
import requests
import schedule
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import sys

class BufferScheduler:
    def __init__(self, config_path: str = 'buffer_config.json'):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        self.base_url = self.config['api']['base_url']
        self.access_token = self.config['api']['access_token']
        self.timezone = self.config['default_schedule']['timezone']
        self.optimal_times = self.config['default_schedule']['best_times']
        
    def _make_request(self, endpoint: str, method: str = 'GET', data: Dict = None) -> Dict:
        url = f"{self.base_url}{endpoint}?access_token={self.access_token}"
        
        try:
            if method == 'POST':
                response = requests.post(url, json=data)
            else:
                response = requests.get(url)
            
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Buffer API error: {str(e)}")
            return {}
    
    def schedule_post(self, channel_id: str, text: str, scheduled_at: Optional[str] = None, media_url: Optional[str] = None) -> Dict:
        from buffer_graphql import BufferGraphQLClient
        client = BufferGraphQLClient()
        return client.create_post(channel_id, text, scheduled_at)
    
    def schedule_daily_posts(self, content_list: List[Dict]) -> None:
        enabled_accounts = [acc for acc in self.config['channels'].values() if acc['enabled'] and acc['channel_id']]
        
        if not enabled_accounts:
            print("ERROR: No enabled accounts with profile_id found.")
            return
        
        for idx, post_time in enumerate(self.optimal_times):
            if idx >= len(content_list):
                break
            
            content = content_list[idx]
            scheduled_time = self._get_scheduled_time(post_time)
            
            for account in enabled_accounts:
                result = self.schedule_post(
                    channel_id=account['channel_id'],
                    text=content['text'],
                    scheduled_at=scheduled_time,
                    media_url=content.get('image_url')
                )
                
                if 'id' in result or (result.get('data') and result.get('data', {}).get('createPost')):
                    print(f"SUCCESS: {account['name']} - Scheduled at {post_time}: {content['text'][:30]}...")
                else:
                    print(f"FAILED: {account['name']} - Schedule failed: {result.get('error', 'Unknown error')}")
    
    def _get_scheduled_time(self, time_str: str) -> str:
        today = datetime.now()
        hour, minute = map(int, time_str.split(':'))
        scheduled = today.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        if scheduled < datetime.now():
            scheduled += timedelta(days=1)
        
        return scheduled.isoformat() + 'Z'
    
    def run_scheduler(self, content_provider) -> None:
        print("Buffer Scheduler started")
        print(f"Timezone: {self.timezone}")
        print(f"Daily post times: {', '.join(self.optimal_times)}")
        
        def daily_job():
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Scheduling today's posts...")
            content_list = content_provider.get_content()
            self.schedule_daily_posts(content_list)
        
        schedule.every().day.at("08:00").do(daily_job)
        
        while True:
            schedule.run_pending()
            time.sleep(60)
    
    def get_enabled_accounts(self):
        return [acc for acc in self.config['channels'].values() if acc['enabled']]

def example_content_provider():
    return [
        {
            'text': "ChinaBound Travel - Your Ultimate Guide to China!\n\nDiscover travel tips, visa info, and hidden gems.\n\nhttps://chinaboundtravel.com\n\n#ChinaTravel #TravelGuide",
            'image_url': None
        },
        {
            'text': "Travel Tip: Always carry cash in China, even in big cities!\n\nMany small shops don't accept cards.\n\n#ChinaTravel #TravelTips",
            'image_url': None
        },
        {
            'text': "New Article: 7-Day China Itinerary for First Timers\n\nBeijing -> Xi'an -> Shanghai\n\nhttps://chinaboundtravel.com/7-day-itinerary\n\n#ChinaTravel #Beijing #Shanghai",
            'image_url': None
        }
    ]

if __name__ == '__main__':
    scheduler = BufferScheduler()
    
    print("=== Buffer Scheduler ===")
    print("\n1. Configured channels:")
    for key, account in scheduler.config['channels'].items():
        status = "ENABLED" if account['enabled'] else "DISABLED"
        print(f"  {key}: {account['name']} ({account['channel_id'] or 'No ID'}) - {status}")
    
    print("\n2. Testing post scheduling...")
    test_content = example_content_provider()
    scheduler.schedule_daily_posts(test_content)
    
    print("\nBuffer Scheduler setup complete!")
    print("Use scheduler.run_scheduler(provider) to start the scheduler")
