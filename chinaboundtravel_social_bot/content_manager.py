import csv
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional
from config import BLOG_URL

logger = logging.getLogger(__name__)

class ContentManager:
    def __init__(self, content_dir: str = "content"):
        self.content_dir = content_dir
        self.posts = []
        self.load_content()
    
    def load_content(self):
        self.posts = []
        self._load_from_csv()
        self._load_from_markdown()
        logger.info(f"Loaded {len(self.posts)} content items")
    
    def _load_from_csv(self):
        csv_path = os.path.join(self.content_dir, "social_media_dataset_cbt_2026.csv")
        if os.path.exists(csv_path):
            try:
                with open(csv_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        self.posts.append({
                            'id': row.get('Task_ID', row.get('id', '')),
                            'title': row.get('Post_Title', row.get('title', '')),
                            'summary': row.get('Post_Title', ''),
                            'content': row.get('Post_Content', row.get('content', '')),
                            'url': row.get('Target_URL', row.get('url', '')),
                            'tags': [],
                            'topic': row.get('Platform', ''),
                            'platforms': [row.get('Platform', '')],
                            'status': row.get('Status', 'Pending'),
                            'published_at': '',
                            'source': 'csv'
                        })
                logger.info(f"Loaded {len(self.posts)} items from CSV")
            except Exception as e:
                logger.error(f"Failed to load CSV content: {str(e)}")
    
    def _load_from_markdown(self):
        posts_dir = os.path.join(self.content_dir, "posts")
        if os.path.exists(posts_dir):
            for filename in os.listdir(posts_dir):
                if filename.endswith('.md'):
                    filepath = os.path.join(posts_dir, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        post_data = self._parse_markdown(content)
                        post_data['filename'] = filename
                        post_data['source'] = 'markdown'
                        
                        if post_data['title']:
                            self.posts.append(post_data)
                    except Exception as e:
                        logger.error(f"Failed to load {filename}: {str(e)}")
    
    def _parse_markdown(self, content: str) -> Dict:
        lines = content.split('\n')
        post_data = {
            'title': '',
            'summary': '',
            'content': '',
            'url': '',
            'tags': [],
            'topic': '',
            'published_at': '',
            'category': ''
        }
        
        in_frontmatter = False
        frontmatter_lines = []
        
        for i, line in enumerate(lines):
            if line.strip() == '---' and not in_frontmatter:
                in_frontmatter = True
                continue
            elif line.strip() == '---' and in_frontmatter:
                in_frontmatter = False
                continue
            
            if in_frontmatter:
                frontmatter_lines.append(line)
            elif not post_data['title']:
                if line.startswith('# '):
                    post_data['title'] = line[2:].strip()
            elif not post_data['summary']:
                post_data['summary'] += line + ' '
        
        if frontmatter_lines:
            for line in frontmatter_lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip().strip('"').strip("'")
                    
                    if key == 'title':
                        post_data['title'] = value
                    elif key == 'description':
                        post_data['summary'] = value
                    elif key == 'date':
                        post_data['published_at'] = value
                    elif key == 'categories':
                        post_data['category'] = value
                    elif key == 'tags':
                        post_data['tags'] = [t.strip() for t in value.split(',')]
        
        post_data['content'] = content
        post_data['url'] = self._generate_url(post_data['title'], post_data.get('filename', ''))
        
        return post_data
    
    def _generate_url(self, title: str, filename: str) -> str:
        if filename:
            slug = filename.replace('.md', '').replace('-', '/')
            return f"{BLOG_URL}/{slug}"
        elif title:
            slug = '-'.join(title.lower().split())
            return f"{BLOG_URL}/{slug}"
        return BLOG_URL
    
    def get_content(self, platform: Optional[str] = None, limit: int = 10) -> List[Dict]:
        filtered = self.posts
        
        if platform:
            filtered = [p for p in filtered if not p.get('platforms') or platform.lower() in [pl.lower() for pl in p['platforms']]]
        
        return filtered[:limit]
    
    def get_content_by_topic(self, topic: str, limit: int = 10) -> List[Dict]:
        return [p for p in self.posts if topic.lower() in p.get('topic', '').lower()][:limit]
    
    def get_random_content(self, count: int = 5, platform: Optional[str] = None) -> List[Dict]:
        import random
        filtered = self.get_content(platform)
        return random.sample(filtered, min(count, len(filtered)))
    
    def add_content(self, content: Dict):
        content['id'] = content.get('id', f"content_{int(datetime.now().timestamp())}")
        content['created_at'] = datetime.now().isoformat()
        self.posts.append(content)
        logger.info(f"Added content: {content['title']}")
    
    def update_content(self, content_id: str, updates: Dict):
        for i, post in enumerate(self.posts):
            if post.get('id') == content_id:
                self.posts[i].update(updates)
                logger.info(f"Updated content: {content_id}")
                return True
        return False
    
    def save_to_csv(self, filepath: str = None):
        if not filepath:
            filepath = os.path.join(self.content_dir, "content_backup.csv")
        
        fieldnames = ['id', 'title', 'summary', 'content', 'url', 'tags', 'topic', 'platforms', 'published_at', 'source']
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for post in self.posts:
                row = {k: post.get(k, '') for k in fieldnames}
                row['tags'] = ','.join(post.get('tags', []))
                row['platforms'] = ','.join(post.get('platforms', []))
                writer.writerow(row)
        
        logger.info(f"Saved {len(self.posts)} content items to {filepath}")
    
    def get_stats(self) -> Dict:
        total = len(self.posts)
        by_source = {}
        by_topic = {}
        
        for post in self.posts:
            source = post.get('source', 'unknown')
            by_source[source] = by_source.get(source, 0) + 1
            
            topic = post.get('topic', 'uncategorized')
            by_topic[topic] = by_topic.get(topic, 0) + 1
        
        return {
            'total': total,
            'by_source': by_source,
            'by_topic': by_topic,
            'updated_at': datetime.now().isoformat()
        }

class BufferContentSync:
    def __init__(self, buffer_client):
        self.buffer_client = buffer_client
    
    def fetch_buffer_posts(self, limit: int = 30) -> List[Dict]:
        try:
            posts = []
            channels = self.buffer_client.get_channels()
            
            for channel in channels:
                logger.info(f"Fetching posts for channel: {channel['name']}")
            
            return posts
        except Exception as e:
            logger.error(f"Failed to fetch Buffer posts: {str(e)}")
            return []
    
    def sync_to_content_manager(self, content_manager: ContentManager):
        buffer_posts = self.fetch_buffer_posts()
        
        for post in buffer_posts:
            existing = [p for p in content_manager.posts if p.get('url') == post.get('url')]
            
            if not existing:
                content_manager.add_content({
                    'title': post.get('text', '')[:100],
                    'summary': post.get('text', '')[:200],
                    'content': post.get('text', ''),
                    'url': post.get('url', ''),
                    'tags': [],
                    'topic': 'buffer_import',
                    'source': 'buffer'
                })
        
        logger.info(f"Synchronized {len(buffer_posts)} posts from Buffer")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    manager = ContentManager()
    stats = manager.get_stats()
    
    print("=== Content Manager Test ===")
    print(f"\nTotal content items: {stats['total']}")
    print("\nContent by source:")
    for source, count in stats['by_source'].items():
        print(f"  {source}: {count}")
    
    print("\nContent by topic:")
    for topic, count in stats['by_source'].items():
        print(f"  {topic}: {count}")
    
    print("\nSample content:")
    sample = manager.get_content(limit=3)
    for i, post in enumerate(sample):
        print(f"\n  {i+1}. {post['title']}")
        print(f"     URL: {post['url']}")
        print(f"     Tags: {', '.join(post.get('tags', []))}")