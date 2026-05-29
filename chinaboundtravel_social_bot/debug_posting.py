# -*- coding: utf-8 -*-
"""
调试脚本 - 学习各平台发帖逻辑
用途：探索页面元素，找到正确的选择器
"""
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def get_driver():
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(10)
    return driver

def debug_reddit(driver):
    print("\n" + "="*60)
    print("调试 Reddit 发帖")
    print("="*60)
    
    driver.get("https://www.reddit.com/r/ChinaTravel/submit")
    time.sleep(3)
    
    print("\n--- 页面信息 ---")
    print("当前URL:", driver.current_url)
    
    print("\n--- 查找标题字段 ---")
    title_fields = []
    try:
        title_fields.append(driver.find_element(By.ID, "title"))
        print("[OK] ID='title'")
    except:
        print("[FAIL] ID='title'")
    
    try:
        title_fields.append(driver.find_element(By.NAME, "title"))
        print("[OK] NAME='title'")
    except:
        print("[FAIL] NAME='title'")
    
    try:
        title_fields.append(driver.find_element(By.CSS_SELECTOR, "textarea[placeholder*='Title']"))
        print("[OK] CSS='textarea[placeholder*=Title]'")
    except:
        print("[FAIL] CSS='textarea[placeholder*=Title]'")
    
    print("\n--- 查找内容字段 ---")
    content_fields = []
    try:
        content_fields.append(driver.find_element(By.ID, "text-body"))
        print("[OK] ID='text-body'")
    except:
        print("[FAIL] ID='text-body'")
    
    try:
        content_fields.append(driver.find_element(By.CSS_SELECTOR, "div[role='textbox']"))
        print("[OK] CSS='div[role=textbox]'")
    except:
        print("[FAIL] CSS='div[role=textbox]'")
    
    print("\n--- 查找发布按钮 ---")
    buttons = []
    try:
        buttons.append(driver.find_element(By.XPATH, "//button[contains(text(), 'Post')]"))
        print("[OK] XPATH='//button[contains(text(), Post)]'")
    except:
        print("[FAIL] XPATH='//button[contains(text(), Post)]'")
    
    try:
        buttons.append(driver.find_element(By.CSS_SELECTOR, "button[type='submit']"))
        print("[OK] CSS='button[type=submit]'")
    except:
        print("[FAIL] CSS='button[type=submit]'")
    
    try:
        buttons.append(driver.find_element(By.CSS_SELECTOR, "[data-testid='submit-form-button']"))
        print("[OK] CSS='[data-testid=submit-form-button]'")
    except:
        print("[FAIL] CSS='[data-testid=submit-form-button]'")
    
    # 尝试填写内容
    if title_fields:
        title_field = title_fields[0]
        print("\n--- 测试填写标题 ---")
        try:
            title_field.send_keys("Test Title")
            print("[OK] 标题填写成功")
        except Exception as e:
            print("[FAIL] 标题填写失败:", str(e)[:50])
    
    if content_fields:
        content_field = content_fields[0]
        print("\n--- 测试填写内容 ---")
        try:
            content_field.send_keys("Test content")
            print("[OK] 内容填写成功")
        except Exception as e:
            print("[FAIL] 内容填写失败:", str(e)[:50])
    
    if buttons:
        button = buttons[0]
        print("\n--- 测试点击发布 ---")
        try:
            button.click()
            print("[OK] 发布按钮点击成功")
        except Exception as e:
            print("[FAIL] 发布按钮点击失败:", str(e)[:50])
    
    print("\n--- 完成 Reddit 调试 ---")

def debug_pinterest(driver):
    print("\n" + "="*60)
    print("调试 Pinterest 发帖")
    print("="*60)
    
    driver.get("https://www.pinterest.com/pin-builder/")
    time.sleep(3)
    
    print("\n--- 页面信息 ---")
    print("当前URL:", driver.current_url)
    
    print("\n--- 查找标题字段 ---")
    try:
        title_field = driver.find_element(By.NAME, "title")
        print("[OK] NAME='title'")
    except:
        print("[FAIL] NAME='title'")
    
    print("\n--- 查找描述字段 ---")
    try:
        desc_field = driver.find_element(By.NAME, "description")
        print("[OK] NAME='description'")
    except:
        print("[FAIL] NAME='description'")
    
    print("\n--- 查找发布按钮 ---")
    try:
        button = driver.find_element(By.XPATH, "//button[contains(text(), 'Publish')]")
        print("[OK] XPATH='//button[contains(text(), Publish)]'")
    except:
        print("[FAIL] XPATH='//button[contains(text(), Publish)]'")
    
    print("\n--- 完成 Pinterest 调试 ---")

def debug_facebook(driver):
    print("\n" + "="*60)
    print("调试 Facebook 发帖")
    print("="*60)
    
    driver.get("https://www.facebook.com/profile.php?id=61589236162181")
    time.sleep(3)
    
    print("\n--- 页面信息 ---")
    print("当前URL:", driver.current_url)
    
    print("\n--- 查找发帖区域 ---")
    try:
        post_area = driver.find_element(By.XPATH, "//div[contains(text(), '分享你的新鲜事')]")
        print("[OK] XPATH='//div[contains(text(), 分享你的新鲜事)]'")
    except:
        print("[FAIL] XPATH='//div[contains(text(), 分享你的新鲜事)]'")
    
    print("\n--- 完成 Facebook 调试 ---")

def debug_instagram(driver):
    print("\n" + "="*60)
    print("调试 Instagram 发帖")
    print("="*60)
    
    driver.get("https://www.instagram.com/create/post/")
    time.sleep(3)
    
    print("\n--- 页面信息 ---")
    print("当前URL:", driver.current_url)
    
    print("\n--- 查找描述字段 ---")
    try:
        caption_field = driver.find_element(By.XPATH, "//textarea[@placeholder='Add a caption']")
        print("[OK] XPATH='//textarea[@placeholder=Add a caption]'")
    except:
        print("[FAIL] XPATH='//textarea[@placeholder=Add a caption]'")
    
    print("\n--- 完成 Instagram 调试 ---")

def debug_quora(driver):
    print("\n" + "="*60)
    print("调试 Quora 发帖")
    print("="*60)
    
    driver.get("https://www.quora.com/search?q=best%20camping%20spots%20in%20Sichuan%20China")
    time.sleep(3)
    
    print("\n--- 页面信息 ---")
    print("当前URL:", driver.current_url)
    
    print("\n--- 查找回答按钮 ---")
    try:
        answer_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Answer')]")
        print("[OK] XPATH='//button[contains(text(), Answer)]'")
    except:
        print("[FAIL] XPATH='//button[contains(text(), Answer)]'")
    
    print("\n--- 完成 Quora 调试 ---")

def debug_medium(driver):
    print("\n" + "="*60)
    print("调试 Medium 发帖")
    print("="*60)
    
    driver.get("https://medium.com/new-story")
    time.sleep(3)
    
    print("\n--- 页面信息 ---")
    print("当前URL:", driver.current_url)
    
    print("\n--- 查找标题字段 ---")
    try:
        title_field = driver.find_element(By.XPATH, "//input[@placeholder='Title']")
        print("[OK] XPATH='//input[@placeholder=Title]'")
    except:
        print("[FAIL] XPATH='//input[@placeholder=Title]'")
    
    print("\n--- 完成 Medium 调试 ---")

def main():
    print("="*60)
    print("  平台调试脚本 - 学习发帖逻辑")
    print("="*60)
    
    try:
        driver = get_driver()
        print("成功连接到浏览器")
        
        debug_reddit(driver)
        
        print("\n" + "="*60)
        input("按回车继续调试 Pinterest...")
        debug_pinterest(driver)
        
        print("\n" + "="*60)
        input("按回车继续调试 Quora...")
        debug_quora(driver)
        
        print("\n" + "="*60)
        input("按回车继续调试 Medium...")
        debug_medium(driver)
        
        print("\n" + "="*60)
        input("按回车继续调试 Instagram...")
        debug_instagram(driver)
        
        print("\n" + "="*60)
        input("按回车继续调试 Facebook...")
        debug_facebook(driver)
        
        print("\n" + "="*60)
        print("  所有平台调试完成！")
        print("="*60)
        
    except Exception as e:
        print("\n错误:", str(e)[:100])

if __name__ == "__main__":
    main()