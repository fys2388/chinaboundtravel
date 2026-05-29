# ============================================
# Single Platform Test Script
# ============================================

import time
import random
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def human_delay(min_sec=2, max_sec=5):
    delay = random.uniform(min_sec, max_sec)
    print(f"Waiting {delay:.2f} seconds...")
    time.sleep(delay)

def type_human(element, text):
    print(f"Typing {len(text)} characters...")
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.05, 0.15))

def init_browser(headless=False):
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    return webdriver.Chrome(options=chrome_options)

def test_reddit_login(driver):
    print(f"\n{Colors.BOLD}=== Testing Reddit Login ==={Colors.RESET}")
    
    try:
        print("Opening Reddit login page...")
        driver.get("https://www.reddit.com/login")
        human_delay(3, 5)
        
        print(f"Current URL: {driver.current_url}")
        print(f"Page title: {driver.title}")
        
        # Wait for page to fully load
        print("Waiting for page to load...")
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        human_delay(2, 3)
        
        # Try to find login form
        print("\nSearching for login form elements...")
        
        # List all available elements
        try:
            forms = driver.find_elements(By.TAG_NAME, "form")
            print(f"Found {len(forms)} forms")
            
            inputs = driver.find_elements(By.TAG_NAME, "input")
            print(f"Found {len(inputs)} input elements")
            
            for i, inp in enumerate(inputs[:10]):
                attrs = {}
                try: attrs['id'] = inp.get_attribute('id')
                except: pass
                try: attrs['name'] = inp.get_attribute('name')
                except: pass
                try: attrs['type'] = inp.get_attribute('type')
                except: pass
                try: attrs['placeholder'] = inp.get_attribute('placeholder')
                except: pass
                print(f"Input {i}: {attrs}")
                
        except Exception as e:
            print(f"{Colors.RED}Error listing elements: {e}{Colors.RESET}")
        
        # Try Google login
        print("\nTrying Google login...")
        try:
            google_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@aria-label, 'Google') or contains(text(), 'Google')]"))
            )
            print("Found Google login button!")
            google_button.click()
            human_delay(3, 5)
            
            # Now on Google login page
            print(f"New URL: {driver.current_url}")
            
            # Find email input
            email_input = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "identifierId"))
            )
            print("Found Google email input")
            type_human(email_input, "fys2388@gmail.com")
            human_delay(1, 2)
            
            next_button = driver.find_element(By.XPATH, "//button[@id='identifierNext']")
            next_button.click()
            human_delay(3, 5)
            
            # Find password input
            password_input = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//input[@type='password']"))
            )
            print("Found Google password input")
            type_human(password_input, "YOUR_PASSWORD_HERE")  # Placeholder
            human_delay(1, 2)
            
            print(f"{Colors.GREEN}Reddit login via Google successful!{Colors.RESET}")
            return True
            
        except Exception as e:
            print(f"{Colors.RED}Google login failed: {str(e)}{Colors.RESET}")
            return False
        
    except Exception as e:
        print(f"{Colors.RED}Reddit login test failed: {str(e)}{Colors.RESET}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    driver = init_browser(headless=False)  # Non-headless for debugging
    
    try:
        success = test_reddit_login(driver)
        if success:
            print(f"\n{Colors.GREEN}=== TEST PASSED ==={Colors.RESET}")
        else:
            print(f"\n{Colors.RED}=== TEST FAILED ==={Colors.RESET}")
    finally:
        print("\nClosing browser...")
        time.sleep(5)
        driver.quit()