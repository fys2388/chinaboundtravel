import json
import logging
from typing import Dict, List, Optional
from config import BUFFER_CONFIG
from buffer_graphql import BufferGraphQLClient

logger = logging.getLogger(__name__)


class BufferPoster:
    def __init__(self):
        self.config = BUFFER_CONFIG
        self.client = None
        self.channels = []
        self._initialize()
        
    def _initialize(self):
        try:
            self.client = BufferGraphQLClient()
            self.channels = self.client.get_channels()
            logger.info(f"Buffer connected with {len(self.channels)} channels")
        except Exception as e:
            logger.error(f"Failed to initialize Buffer client: {str(e)}")
    
    def is_connected(self) -> bool:
        return self.client is not None and len(self.channels) > 0
    
    def get_channels(self) -> List[Dict]:
        return self.channels
    
    def format_post(self, content: Dict) -> str:
        tags = ' '.join([f'#{tag}' for tag in content.get('tags', ['ChinaTravel', 'Travel'])[:3]])
        text_parts = []
        
        if content.get('title'):
            text_parts.append(content['title'])
        
        if content.get('summary'):
            text_parts.append(content['summary'])
        
        if content.get('url'):
            text_parts.append(content['url'])
        
        text_parts.append(tags)
        
        return '\n'.join(text_parts)
    
    def post(self, content: Dict, channel_id: Optional[str] = None) -> Dict:
        try:
            if not self.is_connected():
                logger.error("Buffer not connected")
                return {"success": False, "error": "Buffer not connected"}
            
            post_text = self.format_post(content)
            
            if channel_id:
                logger.info(f"Posting to channel {channel_id}")
                result = self.client.create_post(channel_id, post_text)
            else:
                if not self.channels:
                    return {"success": False, "error": "No channels available"}
                
                first_channel = self.channels[0]
                logger.info(f"Posting to {first_channel['name']} ({first_channel['service']})")
                result = self.client.create_post(first_channel['id'], post_text)
            
            if result and 'createPost' in result:
                post_data = result['createPost']
                
                if 'message' in post_data:
                    error_msg = post_data['message']
                    logger.error(f"Buffer post error: {error_msg}")
                    return {"success": False, "error": error_msg}
                else:
                    post_info = post_data.get('post', {})
                    logger.info(f"Buffer post successful: {post_info.get('id')}")
                    return {
                        "success": True,
                        "id": post_info.get('id'),
                        "text": post_info.get('text'),
                        "url": f"https://buffer.com"
                    }
            else:
                logger.error("Unexpected response from Buffer")
                return {"success": False, "error": "Unexpected response"}
                
        except Exception as e:
            logger.error(f"Buffer post exception: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def post_to_all(self, content: Dict) -> List[Dict]:
        results = []
        
        for channel in self.channels:
            logger.info(f"Posting to {channel['name']} ({channel['service']})")
            result = self.post(content, channel['id'])
            result['channel'] = channel
            results.append(result)
        
        return results
    
    def schedule_post(self, content: Dict, scheduled_at: str, channel_id: Optional[str] = None) -> Dict:
        try:
            if not self.is_connected():
                return {"success": False, "error": "Buffer not connected"}
            
            post_text = self.format_post(content)
            target_channel_id = channel_id or self.channels[0]['id'] if self.channels else None
            
            if not target_channel_id:
                return {"success": False, "error": "No channel available"}
            
            result = self.client.create_post(target_channel_id, post_text, scheduled_at)
            
            if result and 'createPost' in result:
                post_data = result['createPost']
                if 'message' in post_data:
                    return {"success": False, "error": post_data['message']}
                else:
                    post_info = post_data.get('post', {})
                    return {
                        "success": True,
                        "id": post_info.get('id'),
                        "scheduled_at": scheduled_at,
                        "text": post_info.get('text')
                    }
            
            return {"success": False, "error": "Failed to schedule post"}
            
        except Exception as e:
            logger.error(f"Buffer schedule error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def test_connection(self) -> bool:
        if self.is_connected():
            logger.info("Buffer connection test passed")
            return True
        else:
            logger.error("Buffer connection test failed")
            return False


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    print("=== Buffer Poster Test ===")
    
    poster = BufferPoster()
    
    if poster.test_connection():
        print("\nConnected! Channels:")
        for i, channel in enumerate(poster.channels):
            print(f"  {i+1}. {channel['name']} ({channel['service']}) - ID: {channel['id']}")
        
        print("\nTesting post format...")
        test_content = {
            'title': '10 Amazing Places to Visit in China',
            'summary': 'Discover the most beautiful destinations in China',
            'url': 'https://chinaboundtravel.com/10-amazing-places',
            'tags': ['ChinaTravel', 'Travel', 'China']
        }
        
        formatted = poster.format_post(test_content)
        print(f"Formatted text:\n{formatted}")
        
        print("\nBuffer poster test completed!")
    else:
        print("Buffer connection failed!")
