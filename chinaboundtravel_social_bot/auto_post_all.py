# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')

# ============================================
# 6 Platform Social Media Auto Poster
# Posting: Western Sichuan Overland Camping Guide
# ============================================

import time
import random
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ============================================
# Configuration
# ============================================
TITLE = "Western Sichuan Overland Camping: A 7-Day Adventure Guide"

FULL_CONTENT = """Just completed an epic 7-day overland camping trip through Western Sichuan! 🏔️

From Chengdu to Kangding, Tagong Grassland to Yajiang, and beyond - this route offers some of the most breathtaking landscapes in China.

Highlights:
- Camping under the stars at Tagong Grassland
- Driving through stunning mountain passes  
- Experiencing authentic Tibetan culture
- Spotting yaks and wildlife along the way

Practical tips for international travelers:
- Best time: May-October
- 4WD vehicle recommended
- Prepare for high altitude (3000m+)
- Alipay works in most places, but carry 500 RMB cash

Check out my full guide at chinaboundtravel.com

#ChinaTravel #Sichuan #Overland #Camping #AdventureTravel"""

REDDIT_CONTENT = FULL_CONTENT.replace("Check out my full guide at chinaboundtravel.com\n\n", "")

# ============================================
# Helper Functions
# ============================================
def human_delay(min_seconds=2, max_seconds=5):
    delay = random.uniform(min_seconds, max_seconds)
    print("[INFO] Waiting %.2f seconds..." % delay)
    time.sleep(delay)

def platform_delay():
    print("[INFO] Waiting 60 seconds before next platform...")
    time.sleep(60)

def type_human(element, text):
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.02, 0.08))

def print_info(message):
    print("[%s] [INFO] %s" % (datetime.now().strftime('%H:%M:%S'), message))

def print_success(message):
    print("[%s] [SUCCESS] %s" % (datetime.now().strftime('%H:%M:%S'), message))

def print_fail(message):
    print("[%s] [FAIL] %s" % (datetime.now().strftime('%H:%M:%S'), message))

# ============================================
# Platform Posting Functions
# ============================================
def post_reddit(driver):
    print_info("Starting Reddit posting...")
    results = {"platform": "Reddit", "success": False, "url": "", "error": ""}
    
    try:
        driver.get("https://www.reddit.com/r/ChinaTravel/submit")
        human_delay(3, 5)
        
        try:
            title_field = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "title"))
            )
            type_human(title_field, TITLE)
            print_success("Entered title")
        except:
            try:
                title_field = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "title"))
                )
                type_human(title_field, TITLE)
                print_success("Entered title")
            except Exception as e:
                raise Exception("Could not find title field: " + str(e))
        
        human_delay(1, 2)
        
        try:
            content_field = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "text-body"))
            )
            type_human(content_field, REDDIT_CONTENT)
            print_success("Entered content")
        except:
            try:
                content_field = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//textarea[@role='textbox']"))
                )
                type_human(content_field, REDDIT_CONTENT)
                print_success("Entered content")
            except Exception as e:
                raise Exception("Could not find content field: " + str(e))
        
        human_delay(1, 2)
        
        try:
            submit_button = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Post') or contains(., '发布')]"))
            )
            human_delay(1, 2)
            submit_button.click()
            print_success("Clicked submit button")
        except Exception as e:
            raise Exception("Could not find submit button: " + str(e))
        
        human_delay(3, 5)
        
        if "submit" not in driver.current_url.lower():
            results["success"] = True
            results["url"] = driver.current_url
            print_success("Reddit post successful: " + driver.current_url)
        else:
            results["error"] = "Post not submitted"
            print_fail("Reddit post failed")
            
    except Exception as e:
        results["error"] = str(e)
        print_fail("Reddit posting error: " + str(e))
    
    return results

def post_pinterest(driver):
    print_info("Starting Pinterest posting...")
    results = {"platform": "Pinterest", "success": False, "url": "", "error": ""}
    
    try:
        driver.get("https://www.pinterest.com/pin-builder/")
        human_delay(3, 5)
        
        title_field = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.NAME, "title"))
        )
        type_human(title_field, TITLE)
        print_success("Entered title")
        human_delay(1, 2)
        
        desc_field = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.NAME, "description"))
        )
        type_human(desc_field, FULL_CONTENT)
        print_success("Entered description")
        human_delay(1, 2)
        
        try:
            board_selector = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//div[contains(., 'Choose board') or contains(., '选择画板')]"))
            )
            board_selector.click()
            human_delay(1, 2)
            
            china_board = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//div[contains(., 'China Travel Guides')]"))
            )
            china_board.click()
            print_success("Selected board")
        except:
            print_info("Skipping board selection")
        
        human_delay(1, 2)
        
        publish_button = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Publish') or contains(., '发布')]"))
        )
        publish_button.click()
        human_delay(3, 5)
        
        results["success"] = True
        results["url"] = driver.current_url
        print_success("Pinterest post successful")
        
    except Exception as e:
        results["error"] = str(e)
        print_fail("Pinterest posting error: " + str(e))
    
    return results

def post_quora(driver):
    print_info("Starting Quora posting...")
    results = {"platform": "Quora", "success": False, "url": "", "error": ""}
    
    try:
        driver.get("https://www.quora.com/search?q=best+camping+spots+in+Sichuan+China")
        human_delay(3, 5)
        
        question_link = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(., 'camping spots')]"))
        )
        question_link.click()
        human_delay(3, 5)
        
        try:
            answer_button = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Answer') or contains(., '回答')]"))
            )
            answer_button.click()
            human_delay(2, 3)
        except:
            print_info("Answer button not found, trying another selector")
        
        answer_field = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[role='textbox']"))
        )
        type_human(answer_field, FULL_CONTENT)
        print_success("Entered answer")
        human_delay(1, 2)
        
        submit_button = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Submit') or contains(., '提交')]"))
        )
        submit_button.click()
        human_delay(3, 5)
        
        results["success"] = True
        results["url"] = driver.current_url
        print_success("Quora post successful")
        
    except Exception as e:
        results["error"] = str(e)
        print_fail("Quora posting error: " + str(e))
    
    return results

def post_medium(driver):
    print_info("Starting Medium posting...")
    results = {"platform": "Medium", "success": False, "url": "", "error": ""}
    
    try:
        driver.get("https://medium.com/new-story")
        human_delay(3, 5)
        
        title_field = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Title']"))
        )
        type_human(title_field, TITLE)
        print_success("Entered title")
        human_delay(1, 2)
        
        content_field = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//div[@role='textbox']"))
        )
        type_human(content_field, FULL_CONTENT)
        print_success("Entered content")
        human_delay(1, 2)
        
        publish_button = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Publish')]"))
        )
        publish_button.click()
        human_delay(2, 3)
        
        confirm_button = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Publish now')]"))
        )
        confirm_button.click()
        human_delay(3, 5)
        
        results["success"] = True
        results["url"] = driver.current_url
        print_success("Medium post successful")
        
    except Exception as e:
        results["error"] = str(e)
        print_fail("Medium posting error: " + str(e))
    
    return results

def post_instagram(driver):
    print_info("Starting Instagram posting...")
    results = {"platform": "Instagram", "success": False, "url": "", "error": ""}
    
    try:
        driver.get("https://www.instagram.com/create/post/")
        human_delay(3, 5)
        
        try:
            next_button = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Next') or contains(., '下一个')]"))
            )
            next_button.click()
            human_delay(2, 3)
            next_button.click()
            human_delay(2, 3)
        except:
            print_info("Skipping image upload step")
        
        caption_field = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//textarea[@placeholder='Add a caption' or @placeholder='添加说明']"))
        )
        type_human(caption_field, FULL_CONTENT)
        print_success("Entered caption")
        human_delay(1, 2)
        
        share_button = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Share') or contains(., '分享')]"))
        )
        share_button.click()
        human_delay(3, 5)
        
        results["success"] = True
        results["url"] = driver.current_url
        print_success("Instagram post successful")
        
    except Exception as e:
        results["error"] = str(e)
        print_fail("Instagram posting error: " + str(e))
    
    return results

def post_facebook(driver):
    print_info("Starting Facebook posting...")
    results = {"platform": "Facebook", "success": False, "url": "", "error": ""}
    
    try:
        driver.get("https://www.facebook.com/profile.php?id=61589236162181")
        human_delay(3, 5)
        
        post_area = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//div[contains(., 'Share something') or contains(., '分享你的新鲜事')]"))
        )
        post_area.click()
        human_delay(2, 3)
        
        content_field = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[role='textbox']"))
        )
        type_human(content_field, FULL_CONTENT)
        print_success("Entered content")
        human_delay(1, 2)
        
        post_button = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Post') or contains(., '发布')]"))
        )
        post_button.click()
        human_delay(3, 5)
        
        results["success"] = True
        results["url"] = driver.current_url
        print_success("Facebook post successful")
        
    except Exception as e:
        results["error"] = str(e)
        print_fail("Facebook posting error: " + str(e))
    
    return results

# ============================================
# Main Execution
# ============================================
def main():
    print("="*70)
    print("  6 Platform Social Media Auto Poster")
    print("  Content: Western Sichuan Overland Camping Guide")
    print("="*70)
    print("Start Time: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("="*70)
    
    all_results = []
    
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    chrome_options.add_argument('--window-size=1920,1080')
    
    try:
        print_info("Connecting to Chrome debugger at 127.0.0.1:9222...")
        driver = webdriver.Chrome(options=chrome_options)
        print_success("Connected to Chrome successfully!")
        
        platforms = [
            ("Reddit", post_reddit),
            ("Pinterest", post_pinterest),
            ("Quora", post_quora),
            ("Medium", post_medium),
            ("Instagram", post_instagram),
            ("Facebook", post_facebook),
        ]
        
        for i, (platform_name, post_func) in enumerate(platforms):
            print("\n" + "="*70)
            print(" Platform %d/6: %s" % (i+1, platform_name))
            print("="*70)
            
            result = post_func(driver)
            all_results.append(result)
            
            if not result["success"]:
                print_fail("Failed on %s: %s" % (platform_name, result["error"]))
                print("Stopping execution...")
                break
            
            if i < len(platforms) - 1:
                platform_delay()
        
        print("\n" + "="*70)
        print(" POSTING RESULTS SUMMARY")
        print("="*70)
        
        success_count = sum(1 for r in all_results if r["success"])
        fail_count = len(all_results) - success_count
        
        print("\nTotal Platforms: %d" % len(all_results))
        print("Success: %d" % success_count)
        print("Failed: %d" % fail_count)
        
        print("\nDetailed Results:")
        for result in all_results:
            status = "SUCCESS" if result["success"] else "FAIL"
            url = result["url"] if result["url"] else "N/A"
            error = result["error"] if result["error"] else "N/A"
            print("\n%s: %s" % (result["platform"], status))
            print("  URL: %s" % url)
            if not result["success"]:
                print("  Error: %s" % error)
        
        print("\n" + "="*70)
        print("End Time: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        print("="*70)
        
        input("\nPress Enter to close browser...")
        
    except Exception as e:
        print_fail("Fatal error: " + str(e))
        import traceback
        traceback.print_exc()
    finally:
        if 'driver' in locals():
            print_info("Closing browser...")
            driver.quit()

if __name__ == "__main__":
    main()