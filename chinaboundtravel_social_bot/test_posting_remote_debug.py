# ============================================
# Test Posting with Remote Debugging
# Connects to an existing Chrome instance
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
    print("  Testing Reddit Posting with Remote Debugging")
    print("="*60)
    
    # First, check if Chrome is running and try to connect
    chrome_options = Options()
    chrome_options.add_argument("--remote-debugging-port=9222")
    
    try:
        # Try to connect to existing Chrome instance
        print_info("Trying to connect to existing Chrome instance on port 9222...")
        driver = webdriver.Chrome(options=chrome_options)
        
        print_success("Successfully connected to existing Chrome!")
        
    except Exception as e:
        print_info(f"Could not connect to existing Chrome: {e}")
        print_info("Starting new Chrome with remote debugging...")
        
        # Close any existing Chrome processes first
        try:
            subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe'], check=False)
            time.sleep(2)
        except:
            pass
        
        # Start Chrome with remote debugging enabled
        chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        profile_path = r"C:\Users\神魂之人\AppData\Local\Google\Chrome\User Data"
        
        command = f'"{chrome_path}" --remote-debugging-port=9222 --user-data-dir="{profile_path}" --profile-directory=Default'
        print_info(f"Starting Chrome: {command}")
        
        subprocess.Popen(command, shell=True)
        time.sleep(5)
        
        # Connect to the newly started Chrome
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
            user_avatar = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'img[alt="User avatar"]'))
            )
            print_success("Already logged in to Reddit!")
        except:
            print_info("Not logged in")
        
        # Try to post
        print_info("Attempting to create post...")
        try:
            create_button = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, '//*[contains(text(), "创建") or contains(text(), "Create")]'))
            )
            create_button.click()
            print_info("Clicked create button")
            human_delay(3, 5)
            
            post_option = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//*[contains(text(), "Post") or contains(text(), "帖子")]'))
            )
            post_option.click()
            print_info("Clicked post option")
            human_delay(3, 5)
            
            print_success("Successfully accessed post creation page!")
            
        except Exception as e:
            print_fail(f"Error creating post: {e}")
        
        print("\n[INFO] Browser will remain open...")
        while True:
            time.sleep(1)
        
    except Exception as e:
        print_fail(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n[INFO] Closing...")

if __name__ == "__main__":
    main()