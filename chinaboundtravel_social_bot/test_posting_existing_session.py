# ============================================
# Test Posting with Existing Chrome Session
# Uses user's existing Chrome profile with saved logins
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
    """Print info message"""
    print(f"[INFO] {message}")

def print_success(message):
    """Print success message"""
    print(f"[SUCCESS] {message}")

def print_fail(message):
    """Print failure message"""
    print(f"[FAIL] {message}")

def main():
    print("="*60)
    print("  Testing Reddit Posting with Existing Session")
    print("="*60)
    
    # Chrome options to use existing user profile
    chrome_options = Options()
    
    # Try common Chrome profile paths
    profile_paths = [
        r"C:\Users\神魂之人\AppData\Local\Google\Chrome\User Data",
        r"C:\Users\Default\AppData\Local\Google\Chrome\User Data",
        r"C:\Users\Administrator\AppData\Local\Google\Chrome\User Data",
    ]
    
    profile_path = None
    for path in profile_paths:
        if os.path.exists(path):
            profile_path = path
            break
    
    if profile_path:
        print_info(f"Found Chrome profile: {profile_path}")
        chrome_options.add_argument(f"--user-data-dir={profile_path}")
        chrome_options.add_argument("--profile-directory=Default")
    else:
        print_info("Chrome profile not found, using fresh session")
    
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-notifications')
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        # Test Reddit posting
        print("\n" + "="*60)
        print("Testing Reddit")
        print("="*60)
        
        print_info("Opening Reddit...")
        driver.get("https://www.reddit.com")
        human_delay(3, 5)
        
        # Check if already logged in
        print_info("Checking login status...")
        try:
            # Look for user avatar in top right
            user_avatar = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'img[alt="User avatar"]'))
            )
            print_success("Already logged in to Reddit!")
        except:
            print_info("Not logged in, attempting login...")
            driver.get("https://www.reddit.com/login")
            human_delay(3, 5)
            
            # Try to find login buttons
            login_options = driver.find_elements(By.CSS_SELECTOR, 'button, [role="button"]')
            for opt in login_options[:10]:
                text = opt.text.strip()
                if text and len(text) > 0:
                    print(f"Button: '{text}'")
                    if "Google" in text or "google" in text.lower():
                        print_info(f"Found Google login button: '{text}'")
                        opt.click()
                        human_delay(5, 8)
                        break
        
        # Verify logged in
        print_info("Verifying login...")
        human_delay(5, 8)
        
        # Try to post
        print_info("Attempting to create post...")
        try:
            # Click create button
            create_button = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, '//*[contains(text(), "创建") or contains(text(), "Create")]'))
            )
            create_button.click()
            print_info("Clicked create button")
            human_delay(3, 5)
            
            # Click post option
            post_option = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//*[contains(text(), "Post") or contains(text(), "帖子")]'))
            )
            post_option.click()
            print_info("Clicked post option")
            human_delay(3, 5)
            
            print_success("Successfully accessed post creation page!")
            
        except Exception as e:
            print_fail(f"Error creating post: {e}")
        
        # Keep browser open for user verification
        print("\n[INFO] Browser will remain open for 60 seconds...")
        time.sleep(60)
        
    except Exception as e:
        print_fail(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n[INFO] Closing browser...")
        driver.quit()

if __name__ == "__main__":
    main()