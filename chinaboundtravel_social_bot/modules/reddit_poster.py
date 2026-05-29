import praw
import random
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from config import REDDIT_CONFIG, CONTENT_TEMPLATES

logger = logging.getLogger(__name__)

class RedditPoster:
    def __init__(self):
        self.config = REDDIT_CONFIG
        self.reddit = None
        self.last_post_time = {}
        self.today_post_count = {}
        self.approval_queue = []
        self.test_mode = self._is_test_mode()
        
    def _is_test_mode(self) -> bool:
        return self.config['client_id'] == 'test_client_id' or \
               self.config['client_secret'] == 'test_client_secret'
        
    def connect(self) -> bool:
        if self.test_mode:
            logger.info("Running in TEST MODE - Skipping real Reddit connection")
            return True
            
        try:
            self.reddit = praw.Reddit(
                client_id=self.config['client_id'],
                client_secret=self.config['client_secret'],
                user_agent=self.config['user_agent'],
                username=self.config['username'],
                password=self.config['password']
            )
            
            self.reddit.user.me()
            logger.info("Successfully connected to Reddit")
            return True
        except Exception as e:
            logger.error(f"Reddit connection failed: {str(e)}")
            return False
    
    def is_connected(self) -> bool:
        if self.test_mode:
            return True
            
        try:
            if self.reddit:
                self.reddit.user.me()
                return True
            return False
        except:
            return False
    
    def can_post(self, subreddit: str) -> bool:
        now = datetime.now()
        today = now.date()
        
        if subreddit not in self.today_post_count:
            self.today_post_count[subreddit] = {'date': today, 'count': 0}
        
        if self.today_post_count[subreddit]['date'] != today:
            self.today_post_count[subreddit] = {'date': today, 'count': 0}
        
        if self.today_post_count[subreddit]['count'] >= self.config['max_posts_per_day']:
            logger.warning(f"Max posts per day reached for {subreddit}")
            return False
        
        if subreddit in self.last_post_time:
            elapsed = (now - self.last_post_time[subreddit]).total_seconds() / 60
            min_interval = self.config['min_post_interval_minutes']
            if elapsed < min_interval:
                logger.warning(f"Post interval too short for {subreddit}. Elapsed: {elapsed:.1f} min")
                return False
        
        return True
    
    def generate_random_delay(self) -> int:
        min_delay = self.config['min_post_interval_minutes'] * 60
        max_delay = self.config['max_post_interval_minutes'] * 60
        return random.randint(min_delay, max_delay)
    
    def format_post(self, content: Dict) -> Dict:
        template = CONTENT_TEMPLATES['reddit']
        tags = content.get('tags', [])
        tags_str = ' '.join([f'#{t}' for t in tags[:5]])
        
        return {
            'title': template['title_template'].format(
                title=content.get('title', '')
            ),
            'body': template['body_template'].format(
                summary=content.get('summary', ''),
                content=content.get('content', ''),
                url=content.get('url', ''),
                tags=tags_str
            )
        }
    
    def submit_for_approval(self, content: Dict, subreddit: str) -> Dict:
        post_data = self.format_post(content)
        approval_item = {
            'id': f"req_{int(time.time())}",
            'timestamp': datetime.now().isoformat(),
            'subreddit': subreddit,
            'title': post_data['title'],
            'body': post_data['body'][:200] + '...' if len(post_data['body']) > 200 else post_data['body'],
            'full_body': post_data['body'],
            'status': 'pending',
            'content_source': content.get('url', 'unknown')
        }
        
        self.approval_queue.append(approval_item)
        logger.info(f"Post submitted for approval: {approval_item['id']} to r/{subreddit}")
        
        return approval_item
    
    def approve_post(self, request_id: str) -> Optional[Dict]:
        for item in self.approval_queue:
            if item['id'] == request_id and item['status'] == 'pending':
                item['status'] = 'approved'
                result = self._post(item['subreddit'], item['title'], item['full_body'])
                item['posted'] = result['success']
                if result['success']:
                    item['post_id'] = result.get('id')
                    item['post_url'] = result.get('url')
                return item
        return None
    
    def reject_post(self, request_id: str) -> bool:
        for item in self.approval_queue:
            if item['id'] == request_id and item['status'] == 'pending':
                item['status'] = 'rejected'
                logger.info(f"Post rejected: {request_id}")
                return True
        return False
    
    def get_approval_queue(self) -> List[Dict]:
        return [item for item in self.approval_queue if item['status'] == 'pending']
    
    def _post(self, subreddit_name: str, title: str, body: str) -> Dict:
        try:
            if not self.is_connected():
                if not self.connect():
                    return {"success": False, "error": "Not connected"}
            
            if not self.can_post(subreddit_name):
                return {"success": False, "error": "Cannot post at this time"}
            
            self.last_post_time[subreddit_name] = datetime.now()
            if subreddit_name in self.today_post_count:
                self.today_post_count[subreddit_name]['count'] += 1
            else:
                self.today_post_count[subreddit_name] = {'date': datetime.now().date(), 'count': 1}
            
            delay = self.generate_random_delay()
            
            if self.test_mode:
                logger.info(f"[TEST MODE] Would post to r/{subreddit_name}: {title[:50]}...")
                logger.info(f"[TEST MODE] Next post available in {delay/60:.1f} minutes")
                
                return {
                    "success": True,
                    "id": f"test_post_{int(time.time())}",
                    "url": f"https://reddit.com/r/{subreddit_name}/comments/test_post_{int(time.time())}/",
                    "subreddit": subreddit_name,
                    "next_available_in_minutes": delay / 60,
                    "test_mode": True
                }
            
            subreddit = self.reddit.subreddit(subreddit_name)
            submission = subreddit.submit(title, selftext=body)
            
            logger.info(f"Post successful: https://reddit.com{submission.permalink}")
            logger.info(f"Next post available in {delay/60:.1f} minutes")
            
            return {
                "success": True,
                "id": submission.id,
                "url": f"https://reddit.com{submission.permalink}",
                "subreddit": subreddit_name,
                "next_available_in_minutes": delay / 60
            }
        
        except Exception as e:
            logger.error(f"Reddit post failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def post(self, content: Dict, subreddit: Optional[str] = None) -> Dict:
        if self.config['require_approval'] and not self.config['auto_publish']:
            target_subreddit = subreddit or random.choice(self.config['target_subreddits'])
            return self.submit_for_approval(content, target_subreddit)
        
        target_subreddit = subreddit or random.choice(self.config['target_subreddits'])
        post_data = self.format_post(content)
        return self._post(target_subreddit, post_data['title'], post_data['body'])
    
    def auto_post_random(self, content_list: List[Dict]) -> List[Dict]:
        results = []
        
        for content in content_list:
            if not self.can_post(random.choice(self.config['target_subreddits'])):
                break
            
            subreddit = random.choice(self.config['target_subreddits'])
            result = self.post(content, subreddit)
            
            if result.get('success'):
                delay = self.generate_random_delay()
                logger.info(f"Waiting {delay/60:.1f} minutes before next post...")
                time.sleep(delay)
            
            results.append(result)
        
        return results
    
    def get_subreddit_stats(self, subreddit_name: str) -> Dict:
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            return {
                'name': subreddit.display_name,
                'subscribers': subreddit.subscribers,
                'active_users': subreddit.active_user_count,
                'over18': subreddit.over18,
                'description': subreddit.public_description[:200]
            }
        except Exception as e:
            logger.error(f"Failed to get subreddit stats: {str(e)}")
            return {}
    
    def close(self):
        if self.reddit:
            pass
    
    def test_connection(self) -> bool:
        if self.connect():
            logger.info("Reddit connection test passed")
            return True
        return False

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    poster = RedditPoster()
    
    print("=== Reddit Poster Test ===")
    print("\n1. Testing connection...")
    
    if poster.test_connection():
        print("✅ Connected to Reddit successfully")
        
        print("\n2. Testing subreddit stats...")
        for sub in REDDIT_CONFIG['target_subreddits'][:3]:
            stats = poster.get_subreddit_stats(sub)
            if stats:
                print(f"   r/{sub}: {stats['subscribers']:,} subscribers, {stats['active_users']} active")
        
        print("\n3. Testing post formatting...")
        test_content = {
            'title': "10 Amazing Places to Visit in China",
            'summary': "Discover the most beautiful destinations in China",
            'content': "From the Great Wall to the Terracotta Army, China has amazing sights...",
            'url': "https://chinaboundtravel.com/10-amazing-places",
            'tags': ["ChinaTravel", "Travel", "China"]
        }
        
        formatted = poster.format_post(test_content)
        print(f"   Title: {formatted['title']}")
        print(f"   Body preview: {formatted['body'][:100]}...")
        
        print("\n4. Testing approval workflow...")
        approval = poster.submit_for_approval(test_content, "ChinaTravel")
        print(f"   Approval request created: {approval['id']}")
        print(f"   Queue has {len(poster.get_approval_queue())} pending requests")
        
    else:
        print("❌ Failed to connect to Reddit")