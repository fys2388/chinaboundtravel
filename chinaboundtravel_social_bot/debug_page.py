# ============================================
# Debug script to inspect Reddit login page
# ============================================

import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

def main():
    chrome_options = Options()
    chrome_options.add_argument('--window-size=1920,1080')
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        print("Opening Reddit login page...")
        driver.get('https://www.reddit.com/login')
        time.sleep(5)
        
        # Save page source
        print("Saving page source...")
        with open('reddit_login.html', 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        print("Page source saved to reddit_login.html")
        
        # List all buttons
        print("\n=== All Buttons ===")
        buttons = driver.find_elements(By.TAG_NAME, 'button')
        print(f"Found {len(buttons)} buttons:")
        
        for i, btn in enumerate(buttons[:20]):
            text = btn.text[:50] if btn.text else 'No text'
            class_name = btn.get_attribute('class')[:80] if btn.get_attribute('class') else 'No class'
            aria_label = btn.get_attribute('aria-label')[:80] if btn.get_attribute('aria-label') else 'No aria-label'
            data_provider = btn.get_attribute('data-provider') if btn.get_attribute('data-provider') else 'No data-provider'
            id_attr = btn.get_attribute('id') if btn.get_attribute('id') else 'No id'
            
            print(f"\nButton {i}:")
            print(f"  Text: {text}")
            print(f"  Class: {class_name}")
            print(f"  aria-label: {aria_label}")
            print(f"  data-provider: {data_provider}")
            print(f"  id: {id_attr}")
        
        # Look for divs that might be buttons
        print("\n=== Looking for clickable divs ===")
        clickables = driver.find_elements(By.CSS_SELECTOR, '[role="button"]')
        print(f"Found {len(clickables)} role=button elements:")
        
        for i, elem in enumerate(clickables[:10]):
            text = elem.text[:50] if elem.text else 'No text'
            class_name = elem.get_attribute('class')[:80] if elem.get_attribute('class') else 'No class'
            print(f"\nClickable {i}:")
            print(f"  Text: {text}")
            print(f"  Class: {class_name}")
        
    finally:
        print("\nClosing browser...")
        time.sleep(2)
        driver.quit()

if __name__ == "__main__":
    main()