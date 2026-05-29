import logging
import argparse
from config import REDDIT_CONFIG
from modules.reddit_poster import RedditPoster
from modules.medium_poster import MediumPoster
from modules.buffer_poster import BufferPoster
from content_manager import ContentManager
from publisher import PublicationScheduler, ApprovalCLI
from reporting import AnalyticsDashboard

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('social_bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description='ChinaBound Travel Social Media Bot')
    parser.add_argument('--mode', choices=['dashboard', 'approve', 'schedule', 'test'], 
                        default='dashboard', help='Operating mode')
    parser.add_argument('--platform', choices=['reddit', 'medium', 'buffer', 'all'], 
                        default='all', help='Platform to operate')
    
    args = parser.parse_args()
    
    scheduler = PublicationScheduler()
    
    if args.platform in ['reddit', 'all'] and REDDIT_CONFIG['client_id'] != 'YOUR_REDDIT_CLIENT_ID':
        reddit_poster = RedditPoster()
        scheduler.register_publisher('reddit', reddit_poster)
        logger.info("Reddit publisher registered")
    
    if args.platform in ['medium', 'all']:
        medium_poster = MediumPoster()
        scheduler.register_publisher('medium', medium_poster)
        logger.info("Medium publisher registered")
    
    if args.platform in ['buffer', 'all']:
        buffer_poster = BufferPoster()
        if buffer_poster.is_connected():
            scheduler.register_publisher('buffer', buffer_poster)
            logger.info("Buffer publisher registered")
            for channel in buffer_poster.get_channels():
                logger.info(f"  - {channel['name']} ({channel['service']})")
        else:
            logger.warning("Buffer publisher not registered (connection failed)")
    
    if args.mode == 'dashboard':
        dashboard = AnalyticsDashboard(scheduler)
        dashboard.print_dashboard()
        
    elif args.mode == 'approve':
        cli = ApprovalCLI(scheduler)
        cli.run()
        
    elif args.mode == 'schedule':
        logger.info("Starting scheduled publication service...")
        scheduler.run()
        
    elif args.mode == 'test':
        run_tests(scheduler)

def run_tests(scheduler):
    print("\n=== Running System Tests ===")
    
    print("\n1. Testing Content Manager...")
    cm = ContentManager()
    stats = cm.get_stats()
    print(f"   [OK] Loaded {stats['total']} content items")
    
    print("\n2. Testing Reddit Publisher...")
    try:
        from modules.reddit_poster import RedditPoster
        reddit = RedditPoster()
        if reddit.connect():
            print("   [OK] Reddit connected successfully")
            reddit.close()
        else:
            print("   [WARN] Reddit connection failed (check credentials)")
    except Exception as e:
        print(f"   [WARN] Reddit test failed: {str(e)}")
    
    print("\n3. Testing Buffer Publisher...")
    try:
        from modules.buffer_poster import BufferPoster
        buffer = BufferPoster()
        if buffer.test_connection():
            print("   [OK] Buffer connected successfully")
            for i, channel in enumerate(buffer.get_channels()):
                print(f"      {i+1}. {channel['name']} ({channel['service']})")
        else:
            print("   [WARN] Buffer connection failed (check credentials)")
    except Exception as e:
        print(f"   [WARN] Buffer test failed: {str(e)}")
    
    print("\n4. Testing Publication Scheduler...")
    try:
        scheduler.schedule_posts()
        print("   [OK] Scheduler configured successfully")
    except Exception as e:
        print(f"   [WARN] Scheduler test failed: {str(e)}")
    
    print("\n5. Testing Analytics Dashboard...")
    dashboard = AnalyticsDashboard(scheduler)
    data = dashboard.get_dashboard_data()
    print(f"   [OK] Dashboard data retrieved: {len(data)} sections")
    
    print("\n=== All tests completed ===")

if __name__ == '__main__':
    main()