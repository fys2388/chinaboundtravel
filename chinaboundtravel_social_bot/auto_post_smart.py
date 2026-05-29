# -*- coding: utf-8 -*-
import time
import random
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ============================================
# 配置
# ============================================
DELAY_PLATFORM = 60
TITLE = "Western Sichuan Overland Camping: A 7-Day Adventure Guide"

FULL_CONTENT = """Just completed an epic 7-day overland camping trip through Western Sichuan! 🏔️

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

REDDIT_CONTENT = """Just completed an epic 7-day overland camping trip through Western Sichuan! 🏔️

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

# ============================================
# 辅助函数
# ============================================
def human_delay(min_seconds=2, max_seconds=5):
    delay = random.uniform(min_seconds, max_seconds)
    print(f"[INFO] Waiting {delay:.2f} seconds...")
    time.sleep(delay)

def platform_delay():
    print("[INFO] Waiting 60 seconds before next platform...")
    time.sleep(60)

def safe_click(element, driver):
    try:
        driver.execute_script("arguments[0].click();", element)
        return True
    except:
        try:
            element.click()
            return True
        except:
            return False

def safe_send_keys(element, text):
    try:
        element.clear()
        element.send_keys(text)
        return True
    except:
        return False

def find_and_fill_field(driver, wait, selectors, description):
    for selector_type, selector in selectors:
        try:
            field = wait.until(EC.presence_of_element_located((selector_type, selector)))
            print(f"[INFO] Found {description}: {selector}")
            return field
        except:
            continue
    print(f"[FAIL] Could not find {description}")
    return None

def find_and_click_button(driver, wait, selectors, description):
    for selector_type, selector in selectors:
        try:
            button = wait.until(EC.element_to_be_clickable((selector_type, selector)))
            print(f"[INFO] Found {description}: {selector}")
            return button
        except:
            continue
    print(f"[FAIL] Could not find {description}")
    return None

# ============================================
# Reddit
# ============================================
def post_reddit(driver):
    print("\n[Reddit] Starting post...")
    driver.get("https://www.reddit.com/r/ChinaTravel/submit")
    wait = WebDriverWait(driver, 20)
    
    # 等待页面加载
    time.sleep(3)
    
    # 选择子版块
    print("[INFO] Already on r/ChinaTravel")
    
    # 填写标题
    title_selectors = [
        (By.ID, "title"),
        (By.NAME, "title"),
        (By.CSS_SELECTOR, "textarea[placeholder*='Title']"),
    ]
    title_field = find_and_fill_field(driver, wait, title_selectors, "title field")
    if title_field:
        title_field.click()
        safe_send_keys(title_field, TITLE)
        human_delay(1, 2)
    
    # 填写内容
    content_selectors = [
        (By.ID, "text-body"),
        (By.CSS_SELECTOR, "div[role='textbox']"),
        (By.CSS_SELECTOR, "div[aria-label='帖子正文字段']"),
    ]
    content_field = find_and_fill_field(driver, wait, content_selectors, "content field")
    if content_field:
        content_field.click()
        human_delay(0.5, 1)
        driver.execute_script("arguments[0].innerText = arguments[1];", content_field, REDDIT_CONTENT)
        human_delay(1, 2)
    
    # 等待发布按钮激活
    time.sleep(2)
    
    # 查找并点击发布按钮
    btn_selectors = [
        (By.XPATH, "//button[contains(text(), 'Post')]"),
        (By.XPATH, "//button[contains(text(), '发布')]"),
        (By.CSS_SELECTOR, "[data-testid='submit-form-button']"),
        (By.CSS_SELECTOR, "button[type='submit']"),
        (By.XPATH, "//button[contains(@class, 'button-primary')]"),
        (By.XPATH, "//button[text()='Post']"),
    ]
    submit_btn = find_and_click_button(driver, wait, btn_selectors, "submit button")
    if submit_btn:
        submit_btn.click()
        print("[Reddit] Post successful!")
    else:
        print("[Reddit] Could not find submit button")
        input("[Reddit] Please click Post manually")
        time.sleep(3)

# ============================================
# Pinterest
# ============================================
def post_pinterest(driver):
    print("\n[Pinterest] Starting post...")
    driver.get("https://www.pinterest.com/pin-builder/")
    wait = WebDriverWait(driver, 20)
    time.sleep(3)
    
    # 选择画板
    print("[Pinterest] Select board...")
    print("[Pinterest] Please select board manually if needed")
    time.sleep(2)
    
    # 填写标题
    title_selectors = [
        (By.NAME, "title"),
        (By.CSS_SELECTOR, "[data-test-id='pin-title-input']"),
    ]
    title_field = find_and_fill_field(driver, wait, title_selectors, "title field")
    if title_field:
        title_field.click()
        safe_send_keys(title_field, TITLE)
        human_delay(1, 2)
    
    # 填写描述
    desc_selectors = [
        (By.NAME, "description"),
        (By.CSS_SELECTOR, "[data-test-id='pin-description-input']"),
    ]
    desc_field = find_and_fill_field(driver, wait, desc_selectors, "description field")
    if desc_field:
        desc_field.click()
        driver.execute_script("arguments[0].innerText = arguments[1];", desc_field, FULL_CONTENT)
        human_delay(1, 2)
    
    # 等待发布按钮
    time.sleep(2)
    
    # 点击发布
    btn_selectors = [
        (By.XPATH, "//button[contains(text(), 'Publish')]"),
        (By.XPATH, "//button[contains(text(), '发布')]"),
    ]
    publish_btn = find_and_click_button(driver, wait, btn_selectors, "publish button")
    if publish_btn:
        publish_btn.click()
        print("[Pinterest] Post successful!")
    else:
        print("[Pinterest] Please click Publish manually")
        time.sleep(3)

# ============================================
# Quora
# ============================================
def post_quora(driver):
    print("\n[Quora] Starting post...")
    driver.get("https://www.quora.com/search?q=best%20camping%20spots%20in%20Sichuan%20China")
    wait = WebDriverWait(driver, 20)
    time.sleep(3)
    
    print("[Quora] Looking for relevant question...")
    print("[Quora] Please find a question to answer")
    time.sleep(3)
    
    # 尝试回答按钮
    answer_selectors = [
        (By.XPATH, "//button[contains(text(), 'Answer')]"),
        (By.XPATH, "//button[contains(text(), '回答')]"),
    ]
    answer_btn = find_and_click_button(driver, wait, answer_selectors, "answer button")
    if answer_btn:
        answer_btn.click()
        human_delay(2, 3)
        
        # 填写答案
        answer_field_selectors = [
            (By.CSS_SELECTOR, "[role='textbox']"),
            (By.CSS_SELECTOR, "textarea"),
        ]
        answer_field = find_and_fill_field(driver, wait, answer_field_selectors, "answer field")
        if answer_field:
            answer_field.click()
            driver.execute_script("arguments[0].innerText = arguments[1];", answer_field, FULL_CONTENT)
            human_delay(1, 2)
            
            # 提交
            submit_btn = find_and_click_button(driver, wait, [
                (By.XPATH, "//button[contains(text(), 'Submit')]"),
                (By.XPATH, "//button[contains(text(), '提交')]"),
            ], "submit button")
            if submit_btn:
                submit_btn.click()
                print("[Quora] Answer posted!")

# ============================================
# Medium
# ============================================
def post_medium(driver):
    print("\n[Medium] Starting post...")
    driver.get("https://medium.com/new-story")
    wait = WebDriverWait(driver, 20)
    time.sleep(3)
    
    # 标题
    title_selectors = [
        (By.XPATH, "//input[@placeholder='Title']"),
        (By.CSS_SELECTOR, "[data-testid='storyTitle']"),
    ]
    title_field = find_and_fill_field(driver, wait, title_selectors, "title field")
    if title_field:
        title_field.click()
        safe_send_keys(title_field, TITLE)
        human_delay(1, 2)
    
    # 内容
    content_selectors = [
        (By.XPATH, "//div[@role='textbox']"),
        (By.CSS_SELECTOR, "[data-testid='storyTextEditor']"),
    ]
    content_field = find_and_fill_field(driver, wait, content_selectors, "content field")
    if content_field:
        content_field.click()
        driver.execute_script("arguments[0].innerText = arguments[1];", content_field, FULL_CONTENT)
        human_delay(1, 2)
    
    # 发布
    publish_selectors = [
        (By.XPATH, "//button[contains(text(), 'Publish')]"),
    ]
    publish_btn = find_and_click_button(driver, wait, publish_selectors, "publish button")
    if publish_btn:
        publish_btn.click()
        print("[Medium] Publish successful!")
    else:
        print("[Medium] Please publish manually")
        time.sleep(3)

# ============================================
# Instagram
# ============================================
def post_instagram(driver):
    print("\n[Instagram] Starting post...")
    driver.get("https://www.instagram.com/create/post/")
    wait = WebDriverWait(driver, 20)
    time.sleep(3)
    
    print("[Instagram] Creating post...")
    print("[Instagram] Upload image manually if needed")
    time.sleep(3)
    
    # 描述
    caption_selectors = [
        (By.XPATH, "//textarea[@placeholder='Add a caption']"),
        (By.XPATH, "//textarea[contains(@placeholder, 'caption')]"),
    ]
    caption_field = find_and_fill_field(driver, wait, caption_selectors, "caption field")
    if caption_field:
        caption_field.click()
        driver.execute_script("arguments[0].innerText = arguments[1];", caption_field, FULL_CONTENT)
        human_delay(1, 2)
    
    # 分享
    share_selectors = [
        (By.XPATH, "//button[contains(text(), 'Share')]"),
        (By.XPATH, "//button[contains(text(), '分享')]"),
    ]
    share_btn = find_and_click_button(driver, wait, share_selectors, "share button")
    if share_btn:
        share_btn.click()
        print("[Instagram] Share successful!")

# ============================================
# Facebook
# ============================================
def post_facebook(driver):
    print("\n[Facebook] Starting post...")
    driver.get("https://www.facebook.com/profile.php?id=61589236162181")
    wait = WebDriverWait(driver, 20)
    time.sleep(3)
    
    # 点击分享框
    post_area_selectors = [
        (By.XPATH, "//div[contains(text(), '分享你的新鲜事')]"),
        (By.XPATH, "//div[contains(text(), 'Share something')]"),
        (By.XPATH, "//div[@role='button']"),
    ]
    post_area = find_and_click_button(driver, wait, post_area_selectors, "post area")
    if post_area:
        post_area.click()
        human_delay(2, 3)
        
        # 填写内容
        content_selectors = [
            (By.CSS_SELECTOR, "[role='textbox']"),
        ]
        content_field = find_and_fill_field(driver, wait, content_selectors, "content field")
        if content_field:
            content_field.click()
            driver.execute_script("arguments[0].innerText = arguments[1];", content_field, FULL_CONTENT)
            human_delay(1, 2)
            
            # 发布
            post_btn_selectors = [
                (By.XPATH, "//button[contains(text(), 'Post')]"),
                (By.XPATH, "//button[contains(text(), '发布')]"),
            ]
            post_btn = find_and_click_button(driver, wait, post_btn_selectors, "post button")
            if post_btn:
                post_btn.click()
                print("[Facebook] Post successful!")

# ============================================
# 主程序
# ============================================
def main():
    print("="*60)
    print("  6-Platform Auto Poster")
    print("="*60)
    print(f"Start Time:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("="*60)
    
    try:
        # 连接浏览器
        print("[INFO] Connecting to Chrome debugger...")
        chrome_options = Options()
        chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        driver = webdriver.Chrome(options=chrome_options)
        print("[SUCCESS] Connected to Chrome!")
        
        # 执行各平台
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
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()