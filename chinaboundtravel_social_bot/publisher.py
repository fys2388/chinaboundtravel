import logging
import schedule
import time
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from config import SCHEDULE_CONFIG, LOGGING_CONFIG
from content_manager import ContentManager

logger = logging.getLogger(__name__)

class PublicationScheduler:
    def __init__(self):
        self.content_manager = ContentManager()
        self.publishers = {}
        self.publish_log = []
        self.approval_queue = []
        self._setup_logging()
    
    def _setup_logging(self):
        log_file = LOGGING_CONFIG['log_file']
        logging.basicConfig(
            level=LOGGING_CONFIG['level'],
            format=LOGGING_CONFIG['format'],
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
    
    def register_publisher(self, platform: str, publisher):
        self.publishers[platform] = publisher
        logger.info(f"Registered publisher for: {platform}")
    
    def submit_for_approval(self, content: Dict, platform: str) -> Dict:
        approval_item = {
            'id': f"approval_{int(datetime.now(timezone.utc).timestamp())}",
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'platform': platform,
            'content': content,
            'status': 'pending',
            'reviewed_by': None,
            'reviewed_at': None
        }
        
        self.approval_queue.append(approval_item)
        logger.info(f"Content submitted for approval: {approval_item['id']} ({platform})")
        
        return approval_item
    
    def approve_content(self, approval_id: str) -> Optional[Dict]:
        for item in self.approval_queue:
            if item['id'] == approval_id and item['status'] == 'pending':
                item['status'] = 'approved'
                item['reviewed_by'] = 'system'
                item['reviewed_at'] = datetime.now(timezone.utc).isoformat()
                
                platform = item['platform']
                if platform in self.publishers:
                    result = self._publish(platform, item['content'])
                    item['publish_result'] = result
                    return item
        
        logger.warning(f"Approval request not found or already processed: {approval_id}")
        return None
    
    def reject_content(self, approval_id: str, reason: str = "") -> bool:
        for item in self.approval_queue:
            if item['id'] == approval_id and item['status'] == 'pending':
                item['status'] = 'rejected'
                item['reviewed_by'] = 'system'
                item['reviewed_at'] = datetime.now(timezone.utc).isoformat()
                item['rejection_reason'] = reason
                logger.info(f"Content rejected: {approval_id} - {reason}")
                return True
        
        return False
    
    def get_pending_approvals(self) -> List[Dict]:
        return [item for item in self.approval_queue if item['status'] == 'pending']
    
    def _publish(self, platform: str, content: Dict) -> Dict:
        if platform not in self.publishers:
            return {"success": False, "error": f"No publisher registered for {platform}"}
        
        try:
            publisher = self.publishers[platform]
            result = publisher.post(content)
            
            log_entry = {
                'id': f"log_{int(datetime.now(timezone.utc).timestamp())}",
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'platform': platform,
                'content_title': content.get('title', ''),
                'content_url': content.get('url', ''),
                'success': result.get('success', False),
                'error': result.get('error', ''),
                'post_url': result.get('url', '')
            }
            
            self.publish_log.append(log_entry)
            
            if result.get('success'):
                logger.info(f"Successfully published to {platform}: {content.get('title')}")
            else:
                logger.error(f"Failed to publish to {platform}: {result.get('error')}")
            
            return result
        
        except Exception as e:
            logger.error(f"Exception publishing to {platform}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def publish_now(self, platform: str, content: Dict) -> Dict:
        if platform not in self.publishers:
            return {"success": False, "error": f"No publisher registered for {platform}"}
        
        return self._publish(platform, content)
    
    def schedule_posts(self):
        """
        调度器已禁用自动预缓存功能。
        帖子将不再提前缓存到Buffer草稿箱，只有在触发时才会发布。
        """
        logger.warning("Auto-scheduling is DISABLED - posts will only be published when explicitly triggered")
    
    def _scheduled_publish_task(self, platform: str):
        logger.info(f"Running scheduled publish task for {platform}")
        
        pending_approvals = self.get_pending_approvals()
        platform_pending = [a for a in pending_approvals if a['platform'] == platform]
        
        if platform_pending:
            for approval in platform_pending[:3]:
                self.approve_content(approval['id'])
        else:
            contents = self.content_manager.get_random_content(count=1, platform=platform)
            if contents:
                self.submit_for_approval(contents[0], platform)
                logger.info(f"Auto-submitted content for {platform} approval")
    
    def run(self):
        logger.info("Starting publication scheduler...")
        self.schedule_posts()
        
        while True:
            schedule.run_pending()
            time.sleep(60)
    
    def get_publish_log(self, limit: int = 50) -> List[Dict]:
        return self.publish_log[-limit:]
    
    def get_stats(self) -> Dict:
        stats = {
            'total_published': sum(1 for log in self.publish_log if log['success']),
            'total_failed': sum(1 for log in self.publish_log if not log['success']),
            'by_platform': {},
            'pending_approvals': len(self.get_pending_approvals()),
            'total_content': len(self.content_manager.posts),
            'last_run': datetime.now(timezone.utc).isoformat()
        }
        
        for log in self.publish_log:
            platform = log['platform']
            if platform not in stats['by_platform']:
                stats['by_platform'][platform] = {'success': 0, 'failed': 0}
            
            if log['success']:
                stats['by_platform'][platform]['success'] += 1
            else:
                stats['by_platform'][platform]['failed'] += 1
        
        return stats
    
    def save_log(self, filepath: str = None):
        if not filepath:
            filepath = f"publish_log_{datetime.now(timezone.utc).strftime('%Y%m%d')}.json"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.publish_log, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved publish log to {filepath}")

class ApprovalCLI:
    def __init__(self, scheduler: PublicationScheduler):
        self.scheduler = scheduler
    
    def run(self):
        while True:
            print("\n=== Approval Dashboard ===")
            print("1. View pending approvals")
            print("2. Approve content")
            print("3. Reject content")
            print("4. View publish stats")
            print("5. Exit")
            
            choice = input("\nEnter your choice: ")
            
            if choice == '1':
                self._view_pending()
            elif choice == '2':
                self._approve_content()
            elif choice == '3':
                self._reject_content()
            elif choice == '4':
                self._view_stats()
            elif choice == '5':
                break
            else:
                print("Invalid choice")
    
    def _view_pending(self):
        pending = self.scheduler.get_pending_approvals()
        
        if not pending:
            print("\nNo pending approvals")
            return
        
        print(f"\nPending approvals ({len(pending)}):")
        for i, item in enumerate(pending):
            print(f"\n{i+1}. ID: {item['id']}")
            print(f"   Platform: {item['platform']}")
            print(f"   Title: {item['content'].get('title', 'No title')}")
            print(f"   URL: {item['content'].get('url', 'No URL')}")
            print(f"   Submitted: {item['timestamp']}")
    
    def _approve_content(self):
        pending = self.scheduler.get_pending_approvals()
        
        if not pending:
            print("\nNo pending approvals")
            return
        
        self._view_pending()
        
        try:
            index = int(input("\nEnter the number of the item to approve: ")) - 1
            if 0 <= index < len(pending):
                result = self.scheduler.approve_content(pending[index]['id'])
                if result:
                    print(f"\n✅ Approved and published: {result['content'].get('title')}")
                else:
                    print("\n❌ Failed to approve")
            else:
                print("\nInvalid selection")
        except ValueError:
            print("\nInvalid input")
    
    def _reject_content(self):
        pending = self.scheduler.get_pending_approvals()
        
        if not pending:
            print("\nNo pending approvals")
            return
        
        self._view_pending()
        
        try:
            index = int(input("\nEnter the number of the item to reject: ")) - 1
            if 0 <= index < len(pending):
                reason = input("Enter rejection reason: ")
                success = self.scheduler.reject_content(pending[index]['id'], reason)
                if success:
                    print(f"\n✅ Rejected: {pending[index]['content'].get('title')}")
                else:
                    print("\n❌ Failed to reject")
            else:
                print("\nInvalid selection")
        except ValueError:
            print("\nInvalid input")
    
    def _view_stats(self):
        stats = self.scheduler.get_stats()
        
        print("\n=== Publish Statistics ===")
        print(f"Total published: {stats['total_published']}")
        print(f"Total failed: {stats['total_failed']}")
        print(f"Pending approvals: {stats['pending_approvals']}")
        print(f"Total content in library: {stats['total_content']}")
        
        print("\nBy platform:")
        for platform, data in stats['by_platform'].items():
            print(f"  {platform}: {data['success']} success, {data['failed']} failed")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    scheduler = PublicationScheduler()
    
    print("=== Publication Scheduler ===")
    print(f"Loaded {len(scheduler.content_manager.posts)} content items")
    print(f"Registered platforms: {list(scheduler.publishers.keys())}")
    
    cli = ApprovalCLI(scheduler)
    cli.run()