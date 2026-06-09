# ============================================
# chinaboundtravel.com Social Media Bot
# Connection Test Script (Browser Automation)
# ============================================
# Tests connectivity to all platforms using selenium
# ============================================

import sys
import os
import time
import feedparser
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

try:
    from colorlog import ColoredFormatter
    COLORLOG_AVAILABLE = True
except ImportError:
    COLORLOG_AVAILABLE = False

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

def print_warning(msg):
    print(f"{Colors.YELLOW}[WARN]{Colors.RESET} {msg}")

def print_info(msg):
    print(f"{Colors.BLUE}[INFO]{Colors.RESET} {msg}")

def print_header(msg):
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{msg}{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}")

# ------------------------
# Helper Functions
# ------------------------
def init_chrome():
    """Initialize Chrome browser in headless mode"""
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except Exception as e:
        print_error(f"Failed to initialize Chrome: {str(e)}")
        return None

# ------------------------
# Test Functions
# ------------------------
def test_blog_rss():
    """Test blog RSS feed connectivity"""
    print_header("Testing Blog RSS Feed")

    try:
        print_info(f"Fetching: {config.BLOG_RSS}")
        response = requests.get(config.BLOG_RSS, timeout=10)

        if response.status_code == 200:
            feed = feedparser.parse(response.content)
            if feed.bozo == 0:
                print_success(f"RSS Feed accessible - {len(feed.entries)} articles found")
                print_info(f"Blog Title: {feed.feed.get('title', 'N/A')}")
                print_info(f"Last Updated: {feed.feed.get('updated', 'N/A')}")
                return True
            else:
                print_error("RSS Feed is malformed")
                return False
        else:
            print_error(f"HTTP Status: {response.status_code}")
            return False

    except requests.exceptions.Timeout:
        print_error("Connection timeout")
        return False
    except requests.exceptions.ConnectionError:
        print_error("Connection error - check URL")
        return False
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return False

def test_reddit():
    """Test Reddit browser automation"""
    print_header("Testing Reddit (Browser Automation)")

    if not SELENIUM_AVAILABLE:
        print_warning("Selenium not installed - skipping Reddit test")
        print_info("Install with: pip install selenium")
        return None

    username = config.REDDIT_CONFIG['username']
    password = config.REDDIT_CONFIG['password']
    
    if password == "YOUR_REDDIT_PASSWORD":
        print_warning("Password not configured - skipping Reddit test")
        print_info("Set REDDIT_CONFIG['password'] in config.py")
        return None

    driver = init_chrome()
    if not driver:
        return False

    try:
        print_info(f"Attempting to login as: {username}")
        driver.get("https://www.reddit.com/login")
        time.sleep(2)

        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        email_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "login-username"))
        )
        email_input.send_keys(username)

        password_input = driver.find_element(By.ID, "login-password")
        password_input.send_keys(password)

        login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        login_button.click()
        time.sleep(3)

        if "login" not in driver.current_url.lower():
            print_success("Reddit login successful")
            return True
        else:
            print_error("Reddit login failed - check credentials")
            return False

    except Exception as e:
        print_error(f"Error: {str(e)}")
        return False
    finally:
        if driver:
            driver.quit()

def test_pinterest():
    """Test Pinterest browser automation"""
    print_header("Testing Pinterest (Browser Automation)")

    if not SELENIUM_AVAILABLE:
        print_warning("Selenium not installed - skipping Pinterest test")
        print_info("Install with: pip install selenium")
        return None

    email = config.PINTEREST_CONFIG['email']
    password = config.PINTEREST_CONFIG['password']
    
    if password == "YOUR_PINTEREST_PASSWORD":
        print_warning("Password not configured - skipping Pinterest test")
        print_info("Set PINTEREST_CONFIG['password'] in config.py")
        return None

    driver = init_chrome()
    if not driver:
        return False

    try:
        print_info(f"Attempting to login as: {email}")
        driver.get("https://www.pinterest.com/login/")
        time.sleep(2)

        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        email_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "email"))
        )
        email_input.send_keys(email)

        password_input = driver.find_element(By.ID, "password")
        password_input.send_keys(password)

        login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        login_button.click()
        time.sleep(3)

        if "login" not in driver.current_url.lower():
            print_success("Pinterest login successful")
            return True
        else:
            print_error("Pinterest login failed - check credentials")
            return False

    except Exception as e:
        print_error(f"Error: {str(e)}")
        return False
    finally:
        if driver:
            driver.quit()

def test_quora():
    """Test Quora browser automation"""
    print_header("Testing Quora (Browser Automation)")

    if not SELENIUM_AVAILABLE:
        print_warning("Selenium not installed - skipping Quora test")
        print_info("Install with: pip install selenium")
        return None

    email = config.QUORA_CONFIG['email']
    password = config.QUORA_CONFIG['password']
    
    if password == "YOUR_QUORA_PASSWORD":
        print_warning("Password not configured - skipping Quora test")
        print_info("Set QUORA_CONFIG['password'] in config.py")
        return None

    driver = init_chrome()
    if not driver:
        return False

    try:
        print_info(f"Attempting to login as: {email}")
        driver.get("https://www.quora.com/login")
        time.sleep(2)

        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        email_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='email']"))
        )
        email_input.send_keys(email)

        continue_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        continue_button.click()
        time.sleep(2)

        password_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='password']"))
        )
        password_input.send_keys(password)

        login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        login_button.click()
        time.sleep(3)

        if "login" not in driver.current_url.lower():
            print_success("Quora login successful")
            return True
        else:
            print_error("Quora login failed - check credentials")
            return False

    except Exception as e:
        print_error(f"Error: {str(e)}")
        return False
    finally:
        if driver:
            driver.quit()

def test_medium():
    """Test Medium browser automation"""
    print_header("Testing Medium (Browser Automation)")

    if not SELENIUM_AVAILABLE:
        print_warning("Selenium not installed - skipping Medium test")
        print_info("Install with: pip install selenium")
        return None

    email = config.MEDIUM_CONFIG['email']
    password = config.MEDIUM_CONFIG['password']
    
    if password == "YOUR_MEDIUM_PASSWORD":
        print_warning("Password not configured - skipping Medium test")
        print_info("Set MEDIUM_CONFIG['password'] in config.py")
        return None

    driver = init_chrome()
    if not driver:
        return False

    try:
        print_info(f"Attempting to login as: {email}")
        driver.get("https://medium.com/m/signin")
        time.sleep(2)

        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        email_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='email']"))
        )
        email_input.send_keys(email)

        continue_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        continue_button.click()
        time.sleep(2)

        password_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='password']"))
        )
        password_input.send_keys(password)

        login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        login_button.click()
        time.sleep(3)

        if "signin" not in driver.current_url.lower() and "login" not in driver.current_url.lower():
            print_success("Medium login successful")
            return True
        else:
            print_error("Medium login failed - check credentials")
            return False

    except Exception as e:
        print_error(f"Error: {str(e)}")
        return False
    finally:
        if driver:
            driver.quit()

def test_instagram():
    """Test Instagram browser automation"""
    print_header("Testing Instagram (Browser Automation)")

    if not SELENIUM_AVAILABLE:
        print_warning("Selenium not installed - skipping Instagram test")
        print_info("Install with: pip install selenium")
        return None

    email = config.INSTAGRAM_CONFIG['email']
    password = config.INSTAGRAM_CONFIG['password']
    
    if password == "YOUR_INSTAGRAM_PASSWORD":
        print_warning("Password not configured - skipping Instagram test")
        print_info("Set INSTAGRAM_CONFIG['password'] in config.py")
        return None

    driver = init_chrome()
    if not driver:
        return False

    try:
        print_info(f"Attempting to login as: {email}")
        driver.get("https://www.instagram.com/accounts/login/")
        time.sleep(3)

        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        email_input = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.NAME, "username"))
        )
        email_input.send_keys(email)

        password_input = driver.find_element(By.NAME, "password")
        password_input.send_keys(password)

        login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        login_button.click()
        time.sleep(5)

        if "login" not in driver.current_url.lower():
            print_success("Instagram login successful")
            return True
        else:
            print_error("Instagram login failed - check credentials")
            return False

    except Exception as e:
        print_error(f"Error: {str(e)}")
        return False
    finally:
        if driver:
            driver.quit()

def test_facebook():
    """Test Facebook browser automation"""
    print_header("Testing Facebook (Browser Automation)")

    if not SELENIUM_AVAILABLE:
        print_warning("Selenium not installed - skipping Facebook test")
        print_info("Install with: pip install selenium")
        return None

    email = config.FACEBOOK_CONFIG['email']
    password = config.FACEBOOK_CONFIG['password']
    
    if email == "YOUR_FACEBOOK_EMAIL" or password == "YOUR_FACEBOOK_PASSWORD":
        print_warning("Credentials not configured - skipping Facebook test")
        print_info("Set FACEBOOK_CONFIG['email'] and 'password' in config.py")
        return None

    driver = init_chrome()
    if not driver:
        return False

    try:
        print_info(f"Attempting to login as: {email}")
        driver.get("https://www.facebook.com/login/")
        time.sleep(3)

        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        email_input = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "email"))
        )
        email_input.send_keys(email)

        password_input = driver.find_element(By.ID, "pass")
        password_input.send_keys(password)

        login_button = driver.find_element(By.NAME, "login")
        login_button.click()
        time.sleep(5)

        if "login" not in driver.current_url.lower():
            print_success("Facebook login successful")
            return True
        else:
            print_error("Facebook login failed - check credentials")
            return False

    except Exception as e:
        print_error(f"Error: {str(e)}")
        return False
    finally:
        if driver:
            driver.quit()

def test_dependencies():
    """Test if all required packages are installed"""
    print_header("Testing Dependencies")

    packages = {
        'requests': 'requests',
        'feedparser': 'feedparser',
        'schedule': 'schedule',
        'PIL': 'Pillow',
        'selenium': 'selenium',
        'webdriver_manager': 'webdriver-manager',
    }

    all_ok = True
    for import_name, package_name in packages.items():
        try:
            __import__(import_name)
            print_success(f"{package_name} installed")
        except ImportError:
            print_error(f"{package_name} NOT installed - run: pip install {package_name}")
            all_ok = False

    return all_ok

# ------------------------
# Main Test Runner
# ------------------------
def run_all_tests():
    print("\n")
    print("="*60)
    print("  chinaboundtravel.com Social Bot - Connection Test")
    print("="*60)
    print(f"\nTesting: {config.BLOG_URL}")
    print(f"Author: {config.AUTHOR_NAME}")

    results = {}

    results['Dependencies'] = test_dependencies()
    results['Blog RSS'] = test_blog_rss()
    results['Reddit'] = test_reddit()
    results['Pinterest'] = test_pinterest()
    results['Quora'] = test_quora()
    results['Medium'] = test_medium()
    results['Instagram'] = test_instagram()
    results['Facebook'] = test_facebook()

    # Summary
    print_header("Test Summary")

    total = 0
    passed = 0
    skipped = 0

    for platform, result in results.items():
        total += 1
        if result is True:
            print_success(f"{platform}: Connected")
            passed += 1
        elif result is False:
            print_error(f"{platform}: Failed")
        else:
            print_warning(f"{platform}: Skipped (not configured)")
            skipped += 1

    print("\n" + "="*60)
    print(f"Results: {passed}/{total} passed, {skipped} skipped")
    print("="*60)

    if skipped > 0:
        print(f"\n{Colors.YELLOW}Configure passwords in config.py to enable full functionality{Colors.RESET}")

    return passed >= 2

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)