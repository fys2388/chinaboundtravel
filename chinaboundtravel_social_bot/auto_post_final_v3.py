# -*- coding: utf-8 -*-
"""
全自动六平台发帖脚本 - 最终版
支持：Reddit, Pinterest, Quora, Medium, Instagram, Facebook
特点：自动处理登录状态、多种选择器备份、JavaScript注入
"""
import time
import random
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 配置
DELAY_PLATFORM = 60
DELAY_ACTION = 2

TITLE = "Western Sichuan Overland Camping: A 7-Day Adventure Guide"

FULL_CONTENT = """Just completed an epic 7-day overland camping trip through Western Sichuan!

From Chengdu to Kangding, Tagong Grassland to Yajiang, and beyond, this route offers some of the most breathtaking landscapes in China.

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

REDDIT_CONTENT = """Just completed an epic 7-day overland camping trip through Western Sichuan!

From Chengdu to Kangding, Tagong Grassland to Yajiang, and beyond, this route offers some of the most breathtaking landscapes in China.

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

#ChinaTravel #Sichuan #Overland #Camping #AdventureTravel"""

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def human_delay(min_sec=1, max_sec=3):
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)

def platform_delay():
    log(f"Waiting {DELAY_PLATFORM} seconds before next platform...")
    time.sleep(DELAY_PLATFORM)

def get_driver():
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(15)
    driver.maximize_window()
    return driver

def find_and_fill(driver, wait, selectors, value, field_name):
    for selector_type, selector in selectors:
        try:
            element = wait.until(EC.presence_of_element_located((selector_type, selector)))
            driver.execute_script("arguments[0].value = arguments[1];", element, value)
            log(f"Filled {field_name} using {selector}")
            return True
        except:
            continue
    log(f"Failed to find {field_name}")
    return False

def find_and_click(driver, wait, selectors, button_name):
    for selector_type, selector in selectors:
        try:
            button = wait.until(EC.element_to_be_clickable((selector_type, selector)))
            button.click()
            log(f"Clicked {button_name} using {selector}")
            return True
        except:
            continue
    log(f"Failed to find {button_name}")
    return False

def post_reddit(driver):
    log("\n=== Starting Reddit ===")
    driver.get("https://www.reddit.com/r/ChinaTravel/submit")
    wait = WebDriverWait(driver, 20)
    time.sleep(5)
    
    title_selectors = [
        (By.ID, "title"),
        (By.NAME, "title"),
        (By.CSS_SELECTOR, "textarea[name='title']"),
    ]
    
    content_selectors = [
        (By.ID, "text-body"),
        (By.CSS_SELECTOR, "div[role='textbox']"),
        (By.CSS_SELECTOR, "[data-testid='post-content']"),
    ]
    
    submit_selectors = [
        (By.XPATH, "//button[contains(text(), 'Post')]"),
        (By.CSS_SELECTOR, "button[type='submit']"),
        (By.CSS_SELECTOR, "[data-testid='submit-form-button']"),
    ]
    
    find_and_fill(driver, wait, title_selectors, TITLE, "Reddit title")
    human_delay()
    
    find_and_fill(driver, wait, content_selectors, REDDIT_CONTENT, "Reddit content")
    human_delay(2, 4)
    
    if not find_and_click(driver, wait, submit_selectors, "Reddit submit"):
        log("Reddit: Manual intervention needed")
        input("Press Enter after manual submission...")
    
    log("Reddit completed")
    time.sleep(3)

def post_pinterest(driver):
    log("\n=== Starting Pinterest ===")
    driver.get("https://www.pinterest.com/pin-builder/")
    wait = WebDriverWait(driver, 20)
    time.sleep(5)
    
    title_selectors = [
        (By.NAME, "title"),
        (By.CSS_SELECTOR, "[data-test-id='pin-title-input']"),
    ]
    
    desc_selectors = [
        (By.NAME, "description"),
        (By.CSS_SELECTOR, "[data-test-id='pin-description-input']"),
    ]
    
    publish_selectors = [
        (By.XPATH, "//button[contains(text(), 'Publish')]"),
        (By.XPATH, "//button[contains(text(), '发布')]"),
    ]
    
    find_and_fill(driver, wait, title_selectors, TITLE, "Pinterest title")
    human_delay()
    
    find_and_fill(driver, wait, desc_selectors, FULL_CONTENT, "Pinterest description")
    human_delay(2, 4)
    
    if not find_and_click(driver, wait, publish_selectors, "Pinterest publish"):
        log("Pinterest: Manual intervention needed")
        input("Press Enter after manual publish...")
    
    log("Pinterest completed")
    time.sleep(3)

def post_quora(driver):
    log("\n=== Starting Quora ===")
    driver.get("https://www.quora.com/search?q=camping+in+Sichuan")
    wait = WebDriverWait(driver, 20)
    time.sleep(5)
    
    log("Quora: Please select a question to answer")
    input("Press Enter when ready...")
    
    answer_selectors = [
        (By.XPATH, "//button[contains(text(), 'Answer')]"),
        (By.XPATH, "//button[contains(text(), '回答')]"),
    ]
    
    content_selectors = [
        (By.CSS_SELECTOR, "[role='textbox']"),
        (By.CSS_SELECTOR, "textarea"),
    ]
    
    submit_selectors = [
        (By.XPATH, "//button[contains(text(), 'Submit')]"),
        (By.XPATH, "//button[contains(text(), '提交')]"),
    ]
    
    find_and_click(driver, wait, answer_selectors, "Quora answer button")
    human_delay(2, 4)
    
    find_and_fill(driver, wait, content_selectors, FULL_CONTENT, "Quora answer")
    human_delay(2, 4)
    
    if not find_and_click(driver, wait, submit_selectors, "Quora submit"):
        log("Quora: Manual intervention needed")
        input("Press Enter after manual submit...")
    
    log("Quora completed")
    time.sleep(3)

def post_medium(driver):
    log("\n=== Starting Medium ===")
    driver.get("https://medium.com/new-story")
    wait = WebDriverWait(driver, 20)
    time.sleep(5)
    
    title_selectors = [
        (By.XPATH, "//input[@placeholder='Title']"),
        (By.CSS_SELECTOR, "[data-testid='storyTitle']"),
    ]
    
    content_selectors = [
        (By.XPATH, "//div[@role='textbox']"),
        (By.CSS_SELECTOR, "[data-testid='storyTextEditor']"),
    ]
    
    publish_selectors = [
        (By.XPATH, "//button[contains(text(), 'Publish')]"),
    ]
    
    find_and_fill(driver, wait, title_selectors, TITLE, "Medium title")
    human_delay()
    
    find_and_fill(driver, wait, content_selectors, FULL_CONTENT, "Medium content")
    human_delay(2, 4)
    
    if not find_and_click(driver, wait, publish_selectors, "Medium publish"):
        log("Medium: Manual intervention needed")
        input("Press Enter after manual publish...")
    
    log("Medium completed")
    time.sleep(3)

def post_instagram(driver):
    log("\n=== Starting Instagram ===")
    driver.get("https://www.instagram.com/create/post/")
    wait = WebDriverWait(driver, 20)
    time.sleep(5)
    
    log("Instagram: Please upload an image")
    input("Press Enter when ready for caption...")
    
    caption_selectors = [
        (By.XPATH, "//textarea[@placeholder='Add a caption']"),
        (By.XPATH, "//textarea[contains(@placeholder, 'caption')]"),
    ]
    
    share_selectors = [
        (By.XPATH, "//button[contains(text(), 'Share')]"),
        (By.XPATH, "//button[contains(text(), '分享')]"),
    ]
    
    find_and_fill(driver, wait, caption_selectors, FULL_CONTENT, "Instagram caption")
    human_delay(2, 4)
    
    if not find_and_click(driver, wait, share_selectors, "Instagram share"):
        log("Instagram: Manual intervention needed")
        input("Press Enter after manual share...")
    
    log("Instagram completed")
    time.sleep(3)

def post_facebook(driver):
    log("\n=== Starting Facebook ===")
    driver.get("https://www.facebook.com/profile.php?id=61589236162181")
    wait = WebDriverWait(driver, 20)
    time.sleep(5)
    
    post_selectors = [
        (By.XPATH, "//div[contains(text(), '分享你的新鲜事')]"),
        (By.XPATH, "//div[contains(text(), 'Share something')]"),
        (By.CSS_SELECTOR, "[role='button']"),
    ]
    
    content_selectors = [
        (By.CSS_SELECTOR, "[role='textbox']"),
    ]
    
    submit_selectors = [
        (By.XPATH, "//button[contains(text(), 'Post')]"),
        (By.XPATH, "//button[contains(text(), '发布')]"),
    ]
    
    find_and_click(driver, wait, post_selectors, "Facebook post area")
    human_delay(2, 4)
    
    find_and_fill(driver, wait, content_selectors, FULL_CONTENT, "Facebook content")
    human_delay(2, 4)
    
    if not find_and_click(driver, wait, submit_selectors, "Facebook post"):
        log("Facebook: Manual intervention needed")
        input("Press Enter after manual post...")
    
    log("Facebook completed")
    time.sleep(3)

def main():
    print("="*60)
    print("  6-Platform Auto Poster - FINAL VERSION")
    print("="*60)
    print("Start Time:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("="*60)
    
    try:
        driver = get_driver()
        log("Connected to Chrome debugger!")
        
        post_reddit(driver)
        platform_delay()
        
        post_pinterest(driver)
        platform_delay()
        
        post_quora(driver)
        platform_delay()
        
        post_medium(driver)
        platform_delay()
        
        post_instagram(driver)
        platform_delay()
        
        post_facebook(driver)
        
        print("\n" + "="*60)
        print("  ALL PLATFORMS COMPLETED!")
        print("="*60)
        
    except Exception as e:
        log(f"ERROR: {str(e)[:150]}")

if __name__ == "__main__":
    main()