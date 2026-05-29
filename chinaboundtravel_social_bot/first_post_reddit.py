# ============================================
# First Social Media Post - Reddit
# ============================================

import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def human_delay(min_seconds=2, max_seconds=5):
    delay = random.uniform(min_seconds, max_seconds)
    print(f"[INFO] Waiting {delay:.2f} seconds...")
    time.sleep(delay)

def print_info(message):
    print(f"[INFO] {message}")

def print_success(message):
    print(f"[SUCCESS] {message}")

def print_fail(message):
    print(f"[FAIL] {message}")

def main():
    print("="*60)
    print("  First Social Media Post - Reddit")
    print("="*60)
    
    # Post content
    title = "Western Sichuan Overland Camping: A 7-Day Adventure Guide"
    content = """Just completed an epic 7-day overland camping trip through Western Sichuan! 🏔️

From Chengdu to Kangding, Tagong Grassland to Yajiang, and beyond - this route offers some of the most breathtaking landscapes in China.

Highlights:
✅ Camping under the stars at Tagong Grassland
✅ Driving through stunning mountain passes
✅ Experiencing authentic Tibetan culture
✅ Spotting yaks and wildlife along the way

Practical tips for international travelers:
• Best time: May-October
• 4WD vehicle recommended
• Prepare for high altitude (3000m+)
• Alipay works in most places, but carry 500 RMB cash

I wrote a fully detailed guide on my blog. Comment "GUIDE" below, and I'll DM you the link.

#ChinaTravel #Sichuan #Overland #Camping #AdventureTravel"""
    
    print_info(f"Title: {title}")
    print_info(f"Content length: {len(content)} characters")
    
    # Start Chrome
    chrome_options = Options()
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-notifications')
    
    try:
        print_info("Starting Chrome...")
        driver = webdriver.Chrome(options=chrome_options)
    except Exception as e:
        print_fail(f"Failed to start Chrome: {e}")
        return
    
    try:
        # Open Reddit
        print_info("Opening Reddit...")
        driver.get("https://www.reddit.com")
        human_delay(3, 5)
        
        # Check if logged in
        try:
            user_avatar = driver.find_element(By.CSS_SELECTOR, 'img[alt="User avatar"]')
            print_success("Already logged in to Reddit!")
        except:
            print_fail("Not logged in. Please login first.")
            input("Press Enter after you login...")
        
        # Go to submit page
        print_info("Going to submit page...")
        driver.get("https://www.reddit.com/submit")
        human_delay(3, 5)
        
        # Find and fill title
        print_info("Finding title field...")
        try:
            # Try different selectors for title field
            title_selectors = [
                (By.ID, 'title'),
                (By.NAME, 'title'),
                (By.XPATH, '//textarea[@placeholder="标题"]'),
                (By.XPATH, '//textarea[contains(@class, "title")]'),
            ]
            
            title_field = None
            for selector_type, selector in title_selectors:
                try:
                    title_field = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((selector_type, selector))
                    )
                    print_info(f"Found title field using: {selector}")
                    break
                except:
                    continue
            
            if title_field:
                title_field.send_keys(title)
                print_success("Entered title")
            else:
                print_fail("Could not find title field")
                
        except Exception as e:
            print_fail(f"Error finding title field: {e}")
        
        human_delay(1, 2)
        
        # Find and fill content
        print_info("Finding content field...")
        try:
            content_selectors = [
                (By.ID, 'text-body'),
                (By.NAME, 'text'),
                (By.XPATH, '//textarea[@placeholder="正文"]'),
                (By.XPATH, '//div[contains(@class, "text")]//textarea'),
            ]
            
            content_field = None
            for selector_type, selector in content_selectors:
                try:
                    content_field = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((selector_type, selector))
                    )
                    print_info(f"Found content field using: {selector}")
                    break
                except:
                    continue
            
            if content_field:
                content_field.send_keys(content)
                print_success("Entered content")
            else:
                print_fail("Could not find content field")
                
        except Exception as e:
            print_fail(f"Error finding content field: {e}")
        
        print("\n" + "="*60)
        print("Post content has been filled!")
        print("Please review and click 'Post' button manually.")
        print("="*60)
        
        input("\nPress Enter to close browser...")
        
    except Exception as e:
        print_fail(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print_info("Closing browser...")
        driver.quit()

if __name__ == "__main__":
    main()