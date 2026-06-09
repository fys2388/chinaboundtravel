# ============================================
# chinaboundtravel.com Social Media Bot
# Test Posting Script - 6 Platforms
# ============================================
# Simulates human-like behavior for testing
# ============================================

import sys
import os
import time
import random
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    print("Error: Selenium not installed!")
    sys.exit(1)

# ------------------------
# Colors for output
# ------------------------
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_success(msg):
    print(f"{Colors.GREEN}[OK]{Colors.RESET} {msg}")

def print_error(msg):
    print(f"{Colors.RED}[FAIL]{Colors.RESET} {msg}")

def print_info(msg):
    print(f"{Colors.BLUE}[INFO]{Colors.RESET} {msg}")

def print_header(msg):
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{msg}{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}")

# ------------------------
# Human-like delays
# ------------------------
def human_delay(min_sec=2, max_sec=5):
    """Simulate human thinking/typing delay"""
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)

def type_human(element, text):
    """Type text like a human (with pauses between characters)"""
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.05, 0.15))  # Human typing speed

# ------------------------
# Initialize browser
# ------------------------
def init_browser():
    try:
        from undetected_chromedriver import Chrome, ChromeOptions
        chrome_options = ChromeOptions()
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        return Chrome(options=chrome_options)
    except ImportError:
        print_info("undetected-chromedriver not installed, using regular chrome")
        chrome_options = Options()
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        return webdriver.Chrome(options=chrome_options)

# ------------------------
# Platform Posting Functions
# ------------------------
def post_reddit(driver):
    """Post to Reddit using Google login"""
    print_header("Posting to Reddit")
    
    try:
        # Login using Google
        print_info("Logging in to Reddit via Google...")
        driver.get("https://www.reddit.com/login")
        human_delay(3, 5)
        
        # Find Google login button (Chinese interface)
        print_info("Finding Google login button...")
        
        try:
            google_button = None
            
            # Step 1: Check iframes for Google login button
            print_info("Step 1: Checking iframes for Google login...")
            iframes = driver.find_elements(By.TAG_NAME, 'iframe')
            print_info(f"Found {len(iframes)} iframes")
            
            for i, iframe in enumerate(iframes):
                try:
                    driver.switch_to.frame(iframe)
                    print_info(f"Switched to iframe {i}")
                    
                    # Try to find Google button in this iframe
                    selectors = [
                        "//button[contains(text(), '通过 Google 继续操作')]",
                        "//button[contains(text(), '通过 Google')]",
                        "//button[contains(text(), 'Google')]",
                        "//*[contains(text(), 'Google')]",
                    ]
                    
                    for selector in selectors:
                        try:
                            google_button = WebDriverWait(driver, 5).until(
                                EC.element_to_be_clickable((By.XPATH, selector))
                            )
                            print_info(f"Found Google button in iframe {i} using selector: {selector}")
                            break
                        except:
                            continue
                    
                    if google_button:
                        break
                except Exception as e:
                    print_info(f"Error checking iframe {i}: {e}")
                finally:
                    if not google_button:
                        driver.switch_to.default_content()
            
            # Step 2: If not found in iframes, check main document
            if not google_button:
                print_info("Step 2: Checking main document for Google login button...")
                driver.switch_to.default_content()
                
                selectors = [
                    "//button[contains(text(), '通过 Google 继续操作')]",
                    "//button[contains(text(), '通过 Google')]",
                    "//*[contains(text(), '通过 Google 继续操作')]/ancestor::button",
                    "//*[contains(text(), '通过 Google')]/ancestor::button",
                    "//span[contains(text(), 'Google')]/ancestor::button",
                    "//*[contains(@class, 'google')]/ancestor::button",
                ]
                
                for selector in selectors:
                    try:
                        google_button = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                        print_info(f"Found Google login button using selector: {selector}")
                        break
                    except:
                        continue
            
            if not google_button:
                raise Exception("Google login button not found in iframes or main document")
            
            # Click the Google button
            google_button.click()
            print_info("Clicked '通过 Google 继续操作' button")
            human_delay(3, 5)
            
            # Switch back to main content after clicking
            driver.switch_to.default_content()
            
            # Step 2: On Google account selection page - click Joran Fan account
            print_info("Step 2: Looking for Joran Fan account...")
            if "google" in driver.current_url.lower():
                print_info("On Google account selection page...")
                
                # Find the account by email
                account_selectors = [
                    f"//*[contains(text(), '{config.REDDIT_CONFIG['email']}')]",
                    "//*[contains(text(), 'Joran Fan')]",
                    "//*[contains(text(), 'fys2388')]",
                ]
                
                account_button = None
                for selector in account_selectors:
                    try:
                        account_button = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                        print_info(f"Found Joran Fan account using selector: {selector}")
                        break
                    except:
                        continue
                
                if account_button:
                    account_button.click()
                    print_info("Clicked Joran Fan account")
                    human_delay(5, 8)
                else:
                    print_info("Joran Fan account not found, continuing with manual login...")
                    # Fallback: try email input
                    try:
                        email_input = WebDriverWait(driver, 15).until(
                            EC.presence_of_element_located((By.ID, "identifierId"))
                        )
                        type_human(email_input, config.REDDIT_CONFIG['email'])
                        human_delay(1, 2)
                        
                        next_button = driver.find_element(By.ID, "identifierNext")
                        next_button.click()
                        human_delay(3, 5)
                        
                        # Enter password
                        password_input = WebDriverWait(driver, 15).until(
                            EC.presence_of_element_located((By.XPATH, "//input[@type='password']"))
                        )
                        type_human(password_input, config.REDDIT_CONFIG['password'])
                        human_delay(1, 2)
                        
                        next_button = driver.find_element(By.ID, "passwordNext")
                        next_button.click()
                        human_delay(5, 8)
                    except Exception as e:
                        raise Exception(f"Google login failed: {e}")
            
        except Exception as e:
            print_info(f"Error during login: {e}")
            raise
        
        # Check if logged in
        if "login" in driver.current_url.lower():
            raise Exception("Login failed - still on login page")
        print_success("Reddit login successful")
        
        # Go to subreddit
        print_info("Navigating to r/ChinaTravel...")
        driver.get("https://www.reddit.com/r/ChinaTravel/submit")
        human_delay(2, 3)
        
        # Fill title
        title_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "title"))
        )
        title = "7 Mistakes First-Time Travelers Make in China (And How to Avoid Them)"
        type_human(title_input, title)
        human_delay(1, 2)
        
        # Fill content
        content = """Traveling to China for the first time? I've seen hundreds of travelers make these 7 avoidable mistakes that ruin their trip:

1. Not setting up Alipay/WeChat Pay before arrival (cash is almost useless now)

2. Booking a hotel in the wrong neighborhood (too far from attractions)

3. Not getting a local SIM card (roaming charges are insane)

4. Trying to visit 10 cities in 7 days (way too rushed)

5. Ignoring visa rules (many travelers get denied entry for missing documents)

6. Only eating at tourist restaurants (missing out on the best local food)

7. Not learning basic Chinese phrases (it makes a huge difference with locals)


I wrote a fully detailed guide on my blog. Comment "GUIDE" below, and I'll DM you the link."""
        
        content_input = driver.find_element(By.ID, "post-content")
        type_human(content_input, content)
        human_delay(2, 3)
        
        # Submit
        submit_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Post')]")
        submit_button.click()
        human_delay(3, 5)
        
        print_success("Reddit post successful")
        return {"platform": "Reddit", "status": "success", "url": driver.current_url, "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        
    except Exception as e:
        print_error(f"Reddit post failed: {str(e)}")
        return {"platform": "Reddit", "status": "failed", "error": str(e), "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

def post_pinterest(driver):
    """Post to Pinterest"""
    print_header("Posting to Pinterest")
    
    try:
        # Login
        print_info("Logging in to Pinterest...")
        driver.get("https://www.pinterest.com/login/")
        human_delay()
        
        email_input = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "email"))
        )
        type_human(email_input, config.PINTEREST_CONFIG['email'])
        human_delay(1, 2)
        
        password_input = driver.find_element(By.ID, "password")
        type_human(password_input, config.PINTEREST_CONFIG['password'])
        human_delay(1, 2)
        
        login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        login_button.click()
        human_delay(3, 5)
        
        if "login" in driver.current_url.lower():
            raise Exception("Login failed")
        print_success("Pinterest login successful")
        
        # Go to create pin
        print_info("Creating new pin...")
        driver.get("https://www.pinterest.com/pin-builder/")
        human_delay(2, 3)
        
        # Upload image (using placeholder)
        print_info("Uploading image...")
        human_delay(2, 3)
        
        # Fill title
        title = "The Ultimate Guide to Avoiding Common Travel Mistakes in China 2026"
        title_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//textarea[@placeholder='Add your title']"))
        )
        type_human(title_input, title)
        human_delay(1, 2)
        
        # Fill description
        description = """Traveling to China for the first time? After 10 years of exploring China and helping thousands of travelers, I've put together this guide to the 7 most common mistakes first-time visitors make — and exactly how to avoid them.


From setting up mobile payments to visa rules, local food to itinerary planning, this guide covers everything you need to know to have a smooth, amazing trip to China.

👉 https://chinaboundtravel.com


#ChinaTravel #TravelChina #ChinaGuide #FirstTimeTravel #TravelTips"""
        
        desc_input = driver.find_element(By.XPATH, "//textarea[@placeholder='Write a description']")
        type_human(desc_input, description)
        human_delay(2, 3)
        
        # Select board
        board_select = driver.find_element(By.XPATH, "//div[contains(text(), 'Choose board')]")
        board_select.click()
        human_delay(1, 2)
        
        board_option = driver.find_element(By.XPATH, "//div[contains(text(), 'China Travel Guides')]")
        board_option.click()
        human_delay(1, 2)
        
        # Save
        save_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Save')]")
        save_button.click()
        human_delay(3, 5)
        
        print_success("Pinterest post successful")
        return {"platform": "Pinterest", "status": "success", "url": driver.current_url, "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        
    except Exception as e:
        print_error(f"Pinterest post failed: {str(e)}")
        return {"platform": "Pinterest", "status": "failed", "error": str(e), "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

def post_quora(driver):
    """Post to Quora"""
    print_header("Posting to Quora")
    
    try:
        # Login
        print_info("Logging in to Quora...")
        driver.get("https://www.quora.com/login")
        human_delay()
        
        email_input = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='email']"))
        )
        type_human(email_input, config.QUORA_CONFIG['email'])
        human_delay(1, 2)
        
        continue_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        continue_button.click()
        human_delay(2, 3)
        
        password_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='password']"))
        )
        type_human(password_input, config.QUORA_CONFIG['password'])
        human_delay(1, 2)
        
        login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        login_button.click()
        human_delay(3, 5)
        
        if "login" in driver.current_url.lower():
            raise Exception("Login failed")
        print_success("Quora login successful")
        
        # Search question
        print_info("Searching for question...")
        search_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='text' and @placeholder='Search Quora']"))
        )
        type_human(search_input, "What are common mistakes tourists make when traveling to China?")
        human_delay(1, 2)
        search_input.submit()
        human_delay(2, 3)
        
        # Find question and answer
        question_link = driver.find_element(By.XPATH, "//a[contains(text(), 'common mistakes tourists make')]")
        question_link.click()
        human_delay(2, 3)
        
        answer_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'Answer')]"))
        )
        answer_button.click()
        human_delay(2, 3)
        
        # Write answer
        answer = """Many first-time travelers run into unnecessary troubles when visiting China. Based on my years of experience helping overseas visitors, I summarize the most frequent mistakes and practical solutions.


A lot of tourists rely purely on cash, but mobile payments like Alipay and WeChat Pay are widely used across the country. You will meet inconvenience if you do not prepare in advance. Besides, many travelers arrange an over-packed itinerary and rush between different cities, which makes the journey tiring.


It is also important to follow visa regulations and prepare complete documents. Staying in the wrong district or eating only at tourist-oriented restaurants will also lower your travel experience. Learning several simple daily Chinese phrases can help you communicate better with local people.


For a complete guide, check out my full article: https://chinaboundtravel.com"""
        
        content_input = driver.find_element(By.XPATH, "//textarea[contains(@class, 'q-box')]")
        type_human(content_input, answer)
        human_delay(2, 3)
        
        submit_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Submit')]")
        submit_button.click()
        human_delay(3, 5)
        
        print_success("Quora answer successful")
        return {"platform": "Quora", "status": "success", "url": driver.current_url, "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        
    except Exception as e:
        print_error(f"Quora post failed: {str(e)}")
        return {"platform": "Quora", "status": "failed", "error": str(e), "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

def post_medium(driver):
    """Post to Medium"""
    print_header("Posting to Medium")
    
    try:
        # Login
        print_info("Logging in to Medium...")
        driver.get("https://medium.com/m/signin")
        human_delay()
        
        email_input = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='email']"))
        )
        type_human(email_input, config.MEDIUM_CONFIG['email'])
        human_delay(1, 2)
        
        continue_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        continue_button.click()
        human_delay(2, 3)
        
        password_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='password']"))
        )
        type_human(password_input, config.MEDIUM_CONFIG['password'])
        human_delay(1, 2)
        
        login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        login_button.click()
        human_delay(3, 5)
        
        if "signin" in driver.current_url.lower():
            raise Exception("Login failed")
        print_success("Medium login successful")
        
        # New story
        print_info("Creating new story...")
        write_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Write')]")
        write_button.click()
        human_delay(2, 3)
        
        # Fill title
        title = "The Ultimate Guide to Avoiding Common Travel Mistakes in China 2026"
        title_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Title']"))
        )
        type_human(title_input, title)
        human_delay(1, 2)
        
        # Fill content
        content = """Traveling to China for the first time? After 10 years of exploring China and helping thousands of travelers, I've put together this guide to the 7 most common mistakes first-time visitors make — and exactly how to avoid them.


From setting up mobile payments to visa rules, local food to itinerary planning, this guide covers everything you need to know to have a smooth, amazing trip to China.

👉 https://chinaboundtravel.com


#ChinaTravel #TravelTips #ChineseCulture"""
        
        content_input = driver.find_element(By.XPATH, "//div[@role='textbox']")
        type_human(content_input, content)
        human_delay(2, 3)
        
        # Publish
        publish_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Publish')]")
        publish_button.click()
        human_delay(2, 3)
        
        confirm_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Publish now')]")
        confirm_button.click()
        human_delay(3, 5)
        
        print_success("Medium post successful")
        return {"platform": "Medium", "status": "success", "url": driver.current_url, "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        
    except Exception as e:
        print_error(f"Medium post failed: {str(e)}")
        return {"platform": "Medium", "status": "failed", "error": str(e), "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

def post_instagram(driver):
    """Post to Instagram"""
    print_header("Posting to Instagram")
    
    try:
        # Login
        print_info("Logging in to Instagram...")
        driver.get("https://www.instagram.com/accounts/login/")
        human_delay()
        
        email_input = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.NAME, "username"))
        )
        type_human(email_input, config.INSTAGRAM_CONFIG['email'])
        human_delay(1, 2)
        
        password_input = driver.find_element(By.NAME, "password")
        type_human(password_input, config.INSTAGRAM_CONFIG['password'])
        human_delay(1, 2)
        
        login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        login_button.click()
        human_delay(3, 5)
        
        if "login" in driver.current_url.lower():
            raise Exception("Login failed")
        print_success("Instagram login successful")
        
        # Create post
        print_info("Creating new post...")
        driver.get("https://www.instagram.com/create/post/")
        human_delay(2, 3)
        
        # Upload image (placeholder)
        print_info("Uploading image...")
        human_delay(2, 3)
        
        # Next buttons
        next_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Next')]")
        next_button.click()
        human_delay(2, 3)
        next_button.click()
        human_delay(2, 3)
        
        # Caption
        caption = """The biggest mistakes new travelers make in China — save this post for your trip!

Full guide: https://chinaboundtravel.com


#ChinaTravel #VisitChina #TravelTips"""
        
        caption_input = driver.find_element(By.XPATH, "//textarea[@placeholder='Write a caption...']")
        type_human(caption_input, caption)
        human_delay(2, 3)
        
        # Share
        share_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Share')]")
        share_button.click()
        human_delay(3, 5)
        
        print_success("Instagram post successful")
        return {"platform": "Instagram", "status": "success", "url": driver.current_url, "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        
    except Exception as e:
        print_error(f"Instagram post failed: {str(e)}")
        return {"platform": "Instagram", "status": "failed", "error": str(e), "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

def post_facebook(driver):
    """Post to Facebook"""
    print_header("Posting to Facebook")
    
    try:
        # Login
        print_info("Logging in to Facebook...")
        driver.get("https://www.facebook.com/login/")
        human_delay()
        
        email_input = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "email"))
        )
        type_human(email_input, config.FACEBOOK_CONFIG['email'])
        human_delay(1, 2)
        
        password_input = driver.find_element(By.ID, "pass")
        type_human(password_input, config.FACEBOOK_CONFIG['password'])
        human_delay(1, 2)
        
        login_button = driver.find_element(By.NAME, "login")
        login_button.click()
        human_delay(3, 5)
        
        if "login" in driver.current_url.lower():
            raise Exception("Login failed")
        print_success("Facebook login successful")
        
        # Go to page
        print_info("Navigating to page...")
        driver.get(f"https://www.facebook.com/profile.php?id={config.FACEBOOK_CONFIG['page_id']}")
        human_delay(2, 3)
        
        # Create post
        post_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true']"))
        )
        post_box.click()
        human_delay(1, 2)
        
        content = """The Ultimate Guide to Avoiding Common Travel Mistakes in China 2026

Traveling to China for the first time? After 10 years of exploring China and helping thousands of travelers, I've put together this guide to the 7 most common mistakes first-time visitors make — and exactly how to avoid them.

From setting up mobile payments to visa rules, local food to itinerary planning, this guide covers everything you need to know to have a smooth, amazing trip to China.

👉 https://chinaboundtravel.com"""
        
        type_human(post_box, content)
        human_delay(2, 3)
        
        # Post
        post_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        post_button.click()
        human_delay(3, 5)
        
        print_success("Facebook post successful")
        return {"platform": "Facebook", "status": "success", "url": driver.current_url, "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        
    except Exception as e:
        print_error(f"Facebook post failed: {str(e)}")
        return {"platform": "Facebook", "status": "failed", "error": str(e), "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

# ------------------------
# Main Execution
# ------------------------
def main():
    print("\n" + "="*60)
    print("  6 Platform Test Posting - chinaboundtravel.com")
    print("="*60)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    results = []
    driver = None
    
    platforms = [
        ("Reddit", post_reddit),
        ("Pinterest", post_pinterest),
        ("Quora", post_quora),
        ("Medium", post_medium),
        ("Instagram", post_instagram),
        ("Facebook", post_facebook),
    ]
    
    for platform_name, post_func in platforms:
        try:
            driver = init_browser()
            result = post_func(driver)
            results.append(result)
            
            if result['status'] == 'failed':
                print_error(f"Stopping due to failure on {platform_name}")
                break
                
            driver.quit()
            driver = None
            
            if platform_name != "Facebook":  # Last platform, no delay needed
                print_info(f"Waiting 60 seconds before next platform...")
                time.sleep(60)
                
        except Exception as e:
            results.append({"platform": platform_name, "status": "failed", "error": str(e), "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
            print_error(f"Error on {platform_name}: {str(e)}")
            break
        finally:
            if driver:
                driver.quit()
    
    # Summary
    print_header("Posting Results Summary")
    
    success_count = sum(1 for r in results if r['status'] == 'success')
    failed_count = len(results) - success_count
    
    for result in results:
        if result['status'] == 'success':
            print_success(f"{result['platform']}: ✓ Posted at {result['time']}")
        else:
            print_error(f"{result['platform']}: ✗ Failed - {result.get('error', 'Unknown error')}")
    
    print("\n" + "="*60)
    print(f"Results: {success_count}/{len(results)} successful")
    print(f"Failed: {failed_count}")
    print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

if __name__ == "__main__":
    main()