# ============================================
# Connect to Existing Chrome Instance
# Requires Chrome to be running with remote debugging enabled
# ============================================

import subprocess
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
    print("  Connect to Existing Chrome Browser")
    print("="*60)
    print("[INFO] Please ensure Chrome is running with all social media accounts logged in")
    print("[INFO] This script will try to connect to your existing Chrome session")
    print("="*60)
    
    chrome_options = Options()
    chrome_options.add_argument("--remote-debugging-port=9222")
    
    try:
        # Try to connect to existing Chrome
        print_info("Trying to connect to Chrome on port 9222...")
        driver = webdriver.Chrome(options=chrome_options)
        print_success("Connected to existing Chrome instance!")
        
    except Exception as e:
        print_info(f"Could not connect directly: {e}")
        print_info("Trying to start Chrome with remote debugging...")
        
        # Start Chrome with remote debugging
        chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        command = f'"{chrome_path}" --remote-debugging-port=9222'
        print_info(f"Starting Chrome: {command}")
        subprocess.Popen(command, shell=True)
        time.sleep(5)
        
        driver = webdriver.Chrome(options=chrome_options)
    
    try:
        # Test Reddit
        print("\n" + "="*60)
        print("Testing Reddit")
        print("="*60)
        driver.get("https://www.reddit.com")
        human_delay(3, 5)
        try:
            driver.find_element(By.CSS_SELECTOR, 'img[alt="User avatar"]')
            print_success("✅ Reddit: Already logged in!")
        except:
            print_fail("❌ Reddit: Not logged in - please login manually")
        
        # Test Facebook
        print("\n" + "="*60)
        print("Testing Facebook")
        print("="*60)
        driver.get("https://www.facebook.com/profile.php?id=61589236162181")
        human_delay(3, 5)
        try:
            driver.find_element(By.XPATH, '//*[contains(text(), "分享你的新鲜事") or contains(text(), "Create Post")]')
            print_success("✅ Facebook: Already logged in!")
        except:
            print_fail("❌ Facebook: Not logged in - please login manually")
        
        # Test Instagram
        print("\n" + "="*60)
        print("Testing Instagram")
        print("="*60)
        driver.get("https://www.instagram.com/joranchinatravel/")
        human_delay(3, 5)
        try:
            driver.find_element(By.XPATH, '//*[@aria-label="个人资料"]')
            print_success("✅ Instagram: Already logged in!")
        except:
            print_fail("❌ Instagram: Not logged in - please login manually")
        
        print("\n" + "="*60)
        print("All platforms tested!")
        print("[INFO] Browser will remain open for manual testing...")
        input("Press Enter to close browser")
        
    except Exception as e:
        print_fail(f"Error: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()