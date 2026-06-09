# ============================================
# Test All Platforms - Social Media Auto Poster
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

def test_reddit(driver):
    print("\n" + "="*60)
    print("Testing Reddit")
    print("="*60)
    driver.get("https://www.reddit.com")
    human_delay(3, 5)
    try:
        driver.find_element(By.CSS_SELECTOR, 'img[alt="User avatar"]')
        print_success("✅ Reddit: Already logged in!")
        return True
    except:
        print_fail("❌ Reddit: Not logged in")
        return False

def test_facebook(driver):
    print("\n" + "="*60)
    print("Testing Facebook")
    print("="*60)
    driver.get("https://www.facebook.com/profile.php?id=61589236162181")
    human_delay(3, 5)
    try:
        driver.find_element(By.XPATH, '//*[contains(text(), "分享你的新鲜事") or contains(text(), "Create Post")]')
        print_success("✅ Facebook: Already logged in!")
        return True
    except:
        print_fail("❌ Facebook: Not logged in")
        return False

def test_instagram(driver):
    print("\n" + "="*60)
    print("Testing Instagram")
    print("="*60)
    driver.get("https://www.instagram.com/joranchinatravel/")
    human_delay(3, 5)
    try:
        driver.find_element(By.XPATH, '//*[@aria-label="个人资料"]')
        print_success("✅ Instagram: Already logged in!")
        return True
    except:
        print_fail("❌ Instagram: Not logged in")
        return False

def test_pinterest(driver):
    print("\n" + "="*60)
    print("Testing Pinterest")
    print("="*60)
    driver.get("https://www.pinterest.com")
    human_delay(3, 5)
    try:
        driver.find_element(By.XPATH, '//*[@aria-label="你的资料"]')
        print_success("✅ Pinterest: Already logged in!")
        return True
    except:
        print_fail("❌ Pinterest: Not logged in")
        return False

def test_quora(driver):
    print("\n" + "="*60)
    print("Testing Quora")
    print("="*60)
    driver.get("https://www.quora.com")
    human_delay(3, 5)
    try:
        driver.find_element(By.XPATH, '//*[@aria-label="你"]')
        print_success("✅ Quora: Already logged in!")
        return True
    except:
        print_fail("❌ Quora: Not logged in")
        return False

def test_medium(driver):
    print("\n" + "="*60)
    print("Testing Medium")
    print("="*60)
    driver.get("https://medium.com")
    human_delay(3, 5)
    try:
        driver.find_element(By.XPATH, '//*[@aria-label="Profile"]')
        print_success("✅ Medium: Already logged in!")
        return True
    except:
        print_fail("❌ Medium: Not logged in")
        return False

def main():
    print("="*60)
    print("  Testing All Social Media Platforms")
    print("="*60)
    
    chrome_options = Options()
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-notifications')
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
    except Exception as e:
        print_fail(f"Failed to start Chrome: {e}")
        return
    
    try:
        results = []
        results.append(("Reddit", test_reddit(driver)))
        results.append(("Facebook", test_facebook(driver)))
        results.append(("Instagram", test_instagram(driver)))
        results.append(("Pinterest", test_pinterest(driver)))
        results.append(("Quora", test_quora(driver)))
        results.append(("Medium", test_medium(driver)))
        
        print("\n" + "="*60)
        print("TEST RESULTS SUMMARY")
        print("="*60)
        all_passed = True
        for platform, success in results:
            status = "✅ LOGGED IN" if success else "❌ NOT LOGGED IN"
            print(f"{platform}: {status}")
            if not success:
                all_passed = False
        
        if all_passed:
            print("\n🎉 All platforms are logged in! Ready for posting.")
            input("Press Enter to start first posting test...")
            
            # Test posting to Reddit
            print("\n" + "="*60)
            print("Testing Reddit Posting")
            print("="*60)
            driver.get("https://www.reddit.com/submit")
            human_delay(3, 5)
            try:
                title_field = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, 'title'))
                )
                title_field.send_keys("Test Post from ChinaBound Travel Bot")
                print_info("Entered post title")
                
                content_field = driver.find_element(By.ID, 'text-body')
                content_field.send_keys("This is a test post from the ChinaBound Travel social media automation bot.\n\nCheck out our travel blog at https://chinaboundtravel.com for more China travel tips!")
                print_info("Entered post content")
                
                print_success("✅ Successfully prepared Reddit post!")
            except Exception as e:
                print_fail(f"❌ Failed to create Reddit post: {e}")
        
        else:
            print("\n⚠️  Some platforms not logged in. Please check and try again.")
        
        input("\nPress Enter to close browser...")
        
    except Exception as e:
        print_fail(f"Error: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()