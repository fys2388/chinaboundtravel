# ============================================
# Social Media Auto Poster - Using User's Chrome Profile
# ============================================

import os
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def human_delay(min_seconds=2, max_seconds=5):
    """Simulate human-like delay"""
    delay = random.uniform(min_seconds, max_seconds)
    print(f"[INFO] Waiting {delay:.2f} seconds...")
    time.sleep(delay)

def print_info(message):
    print(f"[INFO] {message}")

def print_success(message):
    print(f"[SUCCESS] {message}")

def print_fail(message):
    print(f"[FAIL] {message}")

def test_reddit(driver):
    """Test Reddit posting"""
    print("\n" + "="*60)
    print("Testing Reddit")
    print("="*60)
    
    print_info("Opening Reddit...")
    driver.get("https://www.reddit.com")
    human_delay(3, 5)
    
    try:
        user_avatar = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'img[alt="User avatar"]'))
        )
        print_success("Reddit: Already logged in!")
        return True
    except:
        print_fail("Reddit: Not logged in")
        return False

def test_facebook(driver):
    """Test Facebook posting"""
    print("\n" + "="*60)
    print("Testing Facebook")
    print("="*60)
    
    print_info("Opening Facebook...")
    driver.get("https://www.facebook.com")
    human_delay(3, 5)
    
    try:
        # Check for logged-in elements
        create_post = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//*[contains(text(), "分享你的新鲜事") or contains(text(), "Create Post")]'))
        )
        print_success("Facebook: Already logged in!")
        return True
    except:
        print_fail("Facebook: Not logged in")
        return False

def test_instagram(driver):
    """Test Instagram posting"""
    print("\n" + "="*60)
    print("Testing Instagram")
    print("="*60)
    
    print_info("Opening Instagram...")
    driver.get("https://www.instagram.com")
    human_delay(3, 5)
    
    try:
        # Check for logged-in elements
        profile_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//*[@aria-label="个人资料"]'))
        )
        print_success("Instagram: Already logged in!")
        return True
    except:
        print_fail("Instagram: Not logged in")
        return False

def main():
    print("="*60)
    print("  Social Media Auto Poster")
    print("  Using Chrome Profile with Saved Sessions")
    print("="*60)
    
    # Chrome options with user profile
    chrome_options = Options()
    
    # User's Chrome profile path
    profile_path = r"C:\Users\神魂之人\AppData\Local\Google\Chrome\User Data"
    chrome_options.add_argument(f"--user-data-dir={profile_path}")
    chrome_options.add_argument("--profile-directory=Default")
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-notifications')
    chrome_options.add_argument('--start-maximized')
    
    print_info(f"Using Chrome profile: {profile_path}")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
    except Exception as e:
        print_fail(f"Failed to start Chrome: {e}")
        print_info("Trying without profile...")
        chrome_options = Options()
        chrome_options.add_argument('--window-size=1920,1080')
        driver = webdriver.Chrome(options=chrome_options)
    
    try:
        # Test all platforms
        results = []
        
        # Reddit
        results.append(("Reddit", test_reddit(driver)))
        
        # Facebook
        results.append(("Facebook", test_facebook(driver)))
        
        # Instagram
        results.append(("Instagram", test_instagram(driver)))
        
        # Summary
        print("\n" + "="*60)
        print("TEST RESULTS SUMMARY")
        print("="*60)
        for platform, success in results:
            status = "✅ LOGGED IN" if success else "❌ NOT LOGGED IN"
            print(f"{platform}: {status}")
        
        # Keep browser open
        print("\n[INFO] Browser will remain open. You can test posting manually.")
        input("Press Enter to close...")
        
    except Exception as e:
        print_fail(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n[INFO] Closing browser...")
        driver.quit()

if __name__ == "__main__":
    main()