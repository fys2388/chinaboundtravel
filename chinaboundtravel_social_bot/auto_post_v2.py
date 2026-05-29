# -*- coding: utf-8 -*-
"""
全自动六平台发帖脚本 - 根据调试结果优化
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

def human_delay(min_seconds=2, max_seconds=5):
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)

def platform_delay():
    time.sleep(DELAY_PLATFORM)

def get_driver():
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(10)
    return driver

def post_reddit(driver):
    print("\n[Reddit] Starting post...")
    driver.get("https://www.reddit.com/r/ChinaTravel/submit")
    wait = WebDriverWait(driver, 20)
    time.sleep(3)
    
    # 填写标题 - 使用 NAME='title'
    try:
        title_field = driver.find_element(By.NAME, "title")
        title_field.clear()
        title_field.send_keys(TITLE)
        print("[Reddit] Title filled")
    except Exception as e:
        print("[Reddit] Failed to fill title:", str(e)[:30])
        return
    
    human_delay(1, 2)
    
    # 填写内容 - 使用 JavaScript 直接注入
    try:
        content_field = driver.find_element(By.CSS_SELECTOR, "div[role='textbox']")
        driver.execute_script("arguments[0].innerText = arguments[1];", content_field, REDDIT_CONTENT)
        print("[Reddit] Content filled")
    except Exception as e:
        print("[Reddit] Failed to fill content:", str(e)[:30])
        return
    
    human_delay(2, 3)
    
    # 查找发布按钮 - 尝试多种选择器
    btn_found = False
    btn_selectors = [
        (By.XPATH, "//button[contains(text(), 'Post')]"),
        (By.CSS_SELECTOR, "button[type='submit']"),
        (By.CSS_SELECTOR, "[data-testid='submit-form-button']"),
        (By.XPATH, "//button[contains(@class, 'primary')]"),
    ]
    
    for selector_type, selector in btn_selectors:
        try:
            submit_btn = wait.until(EC.element_to_be_clickable((selector_type, selector)))
            submit_btn.click()
            print("[Reddit] Post successful!")
            btn_found = True
            break
        except:
            continue
    
    if not btn_found:
        print("[Reddit] Submit button not found, waiting for manual confirmation...")
        input("[Reddit] Press Enter after manual submission")
    
    time.sleep(3)

def post_pinterest(driver):
    print("\n[Pinterest] Starting post...")
    driver.get("https://www.pinterest.com/pin-builder/")
    wait = WebDriverWait(driver, 20)
    time.sleep(3)
    
    try:
        title_field = driver.find_element(By.NAME, "title")
        title_field.clear()
        title_field.send_keys(TITLE)
        print("[Pinterest] Title filled")
    except Exception as e:
        print("[Pinterest] Failed to fill title:", str(e)[:30])
    
    human_delay(1, 2)
    
    try:
        desc_field = driver.find_element(By.NAME, "description")
        desc_field.clear()
        desc_field.send_keys(FULL_CONTENT)
        print("[Pinterest] Description filled")
    except Exception as e:
        print("[Pinterest] Failed to fill description:", str(e)[:30])
    
    human_delay(2, 3)
    
    try:
        publish_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Publish')]")))
        publish_btn.click()
        print("[Pinterest] Publish successful!")
    except Exception as e:
        print("[Pinterest] Publish failed:", str(e)[:30])
        input("[Pinterest] Press Enter after manual publish")
    
    time.sleep(3)

def post_facebook(driver):
    print("\n[Facebook] Starting post...")
    driver.get("https://www.facebook.com/profile.php?id=61589236162181")
    wait = WebDriverWait(driver, 20)
    time.sleep(3)
    
    try:
        post_area = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), '分享你的新鲜事')]")))
        post_area.click()
        print("[Facebook] Post area clicked")
    except:
        try:
            post_area = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[@role='button']")))
            post_area.click()
            print("[Facebook] Post area clicked (fallback)")
        except Exception as e:
            print("[Facebook] Failed to click post area:", str(e)[:30])
            return
    
    human_delay(2, 3)
    
    try:
        content_field = driver.find_element(By.CSS_SELECTOR, "[role='textbox']")
        content_field.clear()
        content_field.send_keys(FULL_CONTENT)
        print("[Facebook] Content filled")
    except Exception as e:
        print("[Facebook] Failed to fill content:", str(e)[:30])
    
    human_delay(1, 2)
    
    try:
        post_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Post')]")))
        post_btn.click()
        print("[Facebook] Post successful!")
    except Exception as e:
        print("[Facebook] Post failed:", str(e)[:30])
        input("[Facebook] Press Enter after manual post")
    
    time.sleep(3)

def post_instagram(driver):
    print("\n[Instagram] Starting post...")
    driver.get("https://www.instagram.com/create/post/")
    wait = WebDriverWait(driver, 20)
    time.sleep(3)
    
    print("[Instagram] Please upload image manually")
    input("[Instagram] Press Enter when ready for caption")
    
    try:
        caption_field = wait.until(EC.element_to_be_clickable((By.XPATH, "//textarea[@placeholder='Add a caption']")))
        caption_field.clear()
        caption_field.send_keys(FULL_CONTENT)
        print("[Instagram] Caption filled")
    except Exception as e:
        print("[Instagram] Failed to fill caption:", str(e)[:30])
    
    human_delay(1, 2)
    
    try:
        share_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Share')]")))
        share_btn.click()
        print("[Instagram] Share successful!")
    except Exception as e:
        print("[Instagram] Share failed:", str(e)[:30])
        input("[Instagram] Press Enter after manual share")
    
    time.sleep(3)

def post_quora(driver):
    print("\n[Quora] Starting post...")
    driver.get("https://www.quora.com/search?q=best%20camping%20spots%20in%20Sichuan%20China")
    wait = WebDriverWait(driver, 20)
    time.sleep(3)
    
    print("[Quora] Please find a question to answer")
    input("[Quora] Press Enter when ready to answer")
    
    try:
        answer_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Answer')]")))
        answer_btn.click()
        print("[Quora] Answer button clicked")
    except Exception as e:
        print("[Quora] Failed to click answer:", str(e)[:30])
        return
    
    human_delay(2, 3)
    
    try:
        answer_field = driver.find_element(By.CSS_SELECTOR, "[role='textbox']")
        answer_field.clear()
        answer_field.send_keys(FULL_CONTENT)
        print("[Quora] Answer filled")
    except Exception as e:
        print("[Quora] Failed to fill answer:", str(e)[:30])
    
    human_delay(1, 2)
    
    try:
        submit_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Submit')]")))
        submit_btn.click()
        print("[Quora] Answer submitted!")
    except Exception as e:
        print("[Quora] Submit failed:", str(e)[:30])
        input("[Quora] Press Enter after manual submit")
    
    time.sleep(3)

def post_medium(driver):
    print("\n[Medium] Starting post...")
    driver.get("https://medium.com/new-story")
    wait = WebDriverWait(driver, 20)
    time.sleep(3)
    
    try:
        title_field = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@placeholder='Title']")))
        title_field.clear()
        title_field.send_keys(TITLE)
        print("[Medium] Title filled")
    except Exception as e:
        print("[Medium] Failed to fill title:", str(e)[:30])
    
    human_delay(1, 2)
    
    try:
        content_field = driver.find_element(By.XPATH, "//div[@role='textbox']")
        content_field.clear()
        content_field.send_keys(FULL_CONTENT)
        print("[Medium] Content filled")
    except Exception as e:
        print("[Medium] Failed to fill content:", str(e)[:30])
    
    human_delay(1, 2)
    
    try:
        publish_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Publish')]")))
        publish_btn.click()
        print("[Medium] Publish successful!")
    except Exception as e:
        print("[Medium] Publish failed:", str(e)[:30])
        input("[Medium] Press Enter after manual publish")
    
    time.sleep(3)

def main():
    print("="*60)
    print("  6-Platform Auto Poster v2.0")
    print("="*60)
    print("Start Time:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("="*60)
    
    try:
        driver = get_driver()
        print("Connected to Chrome!")
        
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
        print("  All platforms complete!")
        print("="*60)
        
    except Exception as e:
        print("\nError:", str(e)[:100])

if __name__ == "__main__":
    main()