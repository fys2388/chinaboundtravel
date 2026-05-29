# -*- coding: utf-8 -*-
"""
全自动六平台发帖脚本 - 纯自动版
特点：无需用户输入，完全自动执行
"""
import time
import random
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

DELAY_PLATFORM = 60
TITLE = "Western Sichuan Overland Camping: A 7-Day Adventure Guide"

FULL_CONTENT = """Just completed an epic 7-day overland camping trip through Western Sichuan!

From Chengdu to Kangding, Tagong Grassland to Yajiang, and beyond, this route offers some of the most breathtaking landscapes in China.

Highlights:
- Camping under the stars at Tagong Grassland
- Driving through stunning mountain passes
- Experiencing authentic Tibetan culture
- Spotting yaks and wildlife along the way

Practical tips:
- Best time: May-October
- 4WD vehicle recommended
- Prepare for high altitude (3000m+)
- Alipay works in most places, carry 500 RMB cash

Check out my full guide at chinaboundtravel.com

#ChinaTravel #Sichuan #Overland #Camping"""

REDDIT_CONTENT = """Just completed an epic 7-day overland camping trip through Western Sichuan!

Highlights:
- Camping under the stars at Tagong Grassland
- Driving through stunning mountain passes
- Experiencing authentic Tibetan culture
- Spotting yaks and wildlife along the way

Practical tips:
- Best time: May-October
- 4WD vehicle recommended
- Prepare for high altitude (3000m+)
- Alipay works in most places, carry 500 RMB cash

#ChinaTravel #Sichuan #Overland #Camping"""

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def human_delay(min_sec=1, max_sec=3):
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)

def platform_delay():
    log(f"Waiting {DELAY_PLATFORM}s before next platform...")
    time.sleep(DELAY_PLATFORM)

def get_driver():
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(15)
    return driver

def find_and_fill(driver, wait, selectors, value, field_name):
    for selector_type, selector in selectors:
        try:
            element = wait.until(EC.presence_of_element_located((selector_type, selector)))
            driver.execute_script("arguments[0].value = arguments[1];", element, value)
            log(f"✓ {field_name} filled")
            return True
        except Exception as e:
            continue
    log(f"✗ {field_name} failed")
    return False

def find_and_click(driver, wait, selectors, button_name):
    for selector_type, selector in selectors:
        try:
            button = wait.until(EC.element_to_be_clickable((selector_type, selector)))
            button.click()
            log(f"✓ {button_name} clicked")
            return True
        except Exception as e:
            continue
    log(f"✗ {button_name} failed")
    return False

def post_reddit(driver):
    log("\n=== Reddit ===")
    driver.get("https://www.reddit.com/r/ChinaTravel/submit")
    wait = WebDriverWait(driver, 20)
    time.sleep(5)
    
    title_selectors = [(By.ID, "title"), (By.NAME, "title")]
    content_selectors = [(By.ID, "text-body"), (By.CSS_SELECTOR, "div[role='textbox']")]
    submit_selectors = [(By.XPATH, "//button[contains(text(), 'Post')]"), (By.CSS_SELECTOR, "button[type='submit']")]
    
    find_and_fill(driver, wait, title_selectors, TITLE, "Title")
    human_delay()
    find_and_fill(driver, wait, content_selectors, REDDIT_CONTENT, "Content")
    human_delay(2, 4)
    find_and_click(driver, wait, submit_selectors, "Submit")
    time.sleep(3)

def post_pinterest(driver):
    log("\n=== Pinterest ===")
    driver.get("https://www.pinterest.com/pin-builder/")
    wait = WebDriverWait(driver, 20)
    time.sleep(5)
    
    title_selectors = [(By.NAME, "title")]
    desc_selectors = [(By.NAME, "description")]
    publish_selectors = [(By.XPATH, "//button[contains(text(), 'Publish')]")]
    
    find_and_fill(driver, wait, title_selectors, TITLE, "Title")
    human_delay()
    find_and_fill(driver, wait, desc_selectors, FULL_CONTENT, "Description")
    human_delay(2, 4)
    find_and_click(driver, wait, publish_selectors, "Publish")
    time.sleep(3)

def post_quora(driver):
    log("\n=== Quora ===")
    driver.get("https://www.quora.com/search?q=camping+Sichuan")
    wait = WebDriverWait(driver, 20)
    time.sleep(5)
    
    answer_selectors = [(By.XPATH, "//button[contains(text(), 'Answer')]")]
    content_selectors = [(By.CSS_SELECTOR, "[role='textbox']")]
    submit_selectors = [(By.XPATH, "//button[contains(text(), 'Submit')]")]
    
    find_and_click(driver, wait, answer_selectors, "Answer")
    human_delay(2, 4)
    find_and_fill(driver, wait, content_selectors, FULL_CONTENT, "Answer")
    human_delay(2, 4)
    find_and_click(driver, wait, submit_selectors, "Submit")
    time.sleep(3)

def post_medium(driver):
    log("\n=== Medium ===")
    driver.get("https://medium.com/new-story")
    wait = WebDriverWait(driver, 20)
    time.sleep(5)
    
    title_selectors = [(By.XPATH, "//input[@placeholder='Title']")]
    content_selectors = [(By.XPATH, "//div[@role='textbox']")]
    publish_selectors = [(By.XPATH, "//button[contains(text(), 'Publish')]")]
    
    find_and_fill(driver, wait, title_selectors, TITLE, "Title")
    human_delay()
    find_and_fill(driver, wait, content_selectors, FULL_CONTENT, "Content")
    human_delay(2, 4)
    find_and_click(driver, wait, publish_selectors, "Publish")
    time.sleep(3)

def post_instagram(driver):
    log("\n=== Instagram ===")
    driver.get("https://www.instagram.com/create/post/")
    wait = WebDriverWait(driver, 20)
    time.sleep(5)
    
    caption_selectors = [(By.XPATH, "//textarea[@placeholder='Add a caption']")]
    share_selectors = [(By.XPATH, "//button[contains(text(), 'Share')]")]
    
    find_and_fill(driver, wait, caption_selectors, FULL_CONTENT, "Caption")
    human_delay(2, 4)
    find_and_click(driver, wait, share_selectors, "Share")
    time.sleep(3)

def post_facebook(driver):
    log("\n=== Facebook ===")
    driver.get("https://www.facebook.com/profile.php?id=61589236162181")
    wait = WebDriverWait(driver, 20)
    time.sleep(5)
    
    post_selectors = [(By.XPATH, "//div[contains(text(), '分享你的新鲜事')]")]
    content_selectors = [(By.CSS_SELECTOR, "[role='textbox']")]
    submit_selectors = [(By.XPATH, "//button[contains(text(), 'Post')]")]
    
    find_and_click(driver, wait, post_selectors, "Post Area")
    human_delay(2, 4)
    find_and_fill(driver, wait, content_selectors, FULL_CONTENT, "Content")
    human_delay(2, 4)
    find_and_click(driver, wait, submit_selectors, "Post")
    time.sleep(3)

def main():
    print("="*60)
    print("  6-Platform Auto Poster")
    print("="*60)
    print("Start:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("="*60)
    
    try:
        driver = get_driver()
        log("Connected to Chrome!")
        
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
        print("  COMPLETED!")
        print("="*60)
        
    except Exception as e:
        log(f"ERROR: {str(e)[:100]}")

if __name__ == "__main__":
    main()