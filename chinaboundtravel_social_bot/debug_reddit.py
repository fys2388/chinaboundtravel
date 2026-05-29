# ============================================
# Debug Reddit login page structure
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
        time.sleep(10)  # Wait longer for page to load
        
        print("\n" + "="*80)
        print("CURRENT URL:", driver.current_url)
        print("PAGE TITLE:", driver.title)
        print("="*80)
        
        # Save page source
        print("\nSaving page source...")
        with open('reddit_debug.html', 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        
        # Check for iframes
        print("\n=== CHECKING IFRAMES ===")
        iframes = driver.find_elements(By.TAG_NAME, 'iframe')
        print(f"Found {len(iframes)} iframes")
        
        # List all clickable elements
        print("\n=== ALL CLICKABLE ELEMENTS ===")
        clickables = driver.find_elements(By.CSS_SELECTOR, '[role="button"], button')
        print(f"Found {len(clickables)} clickable elements:")
        
        for i, elem in enumerate(clickables):
            text = elem.text.strip()[:60] if elem.text else 'No text'
            tag_name = elem.tag_name
            class_name = elem.get_attribute('class')[:80] if elem.get_attribute('class') else 'No class'
            id_attr = elem.get_attribute('id') if elem.get_attribute('id') else 'No id'
            aria_label = elem.get_attribute('aria-label')[:60] if elem.get_attribute('aria-label') else 'No aria-label'
            
            print(f"\nElement {i} ({tag_name}):")
            print(f"  Text: '{text}'")
            print(f"  Class: {class_name}")
            print(f"  ID: {id_attr}")
            print(f"  aria-label: {aria_label}")
            
            # Check for Google icon
            try:
                spans = elem.find_elements(By.TAG_NAME, 'span')
                for span in spans[:3]:
                    span_text = span.text[:30] if span.text else 'No text'
                    span_class = span.get_attribute('class')[:50] if span.get_attribute('class') else 'No class'
                    print(f"    Span: text='{span_text}', class={span_class}")
            except:
                pass
        
        # Search for Google-related text
        print("\n=== SEARCHING FOR GOOGLE TEXT ===")
        page_text = driver.page_source.lower()
        google_count = page_text.count('google')
        print(f"Found 'google' {google_count} times in page")
        
        # Try to find element containing Google
        print("\n=== ELEMENTS CONTAINING 'Google' ===")
        elements_with_google = driver.find_elements(By.XPATH, "//*[contains(text(), 'Google') or contains(@class, 'google') or contains(@aria-label, 'Google')]")
        print(f"Found {len(elements_with_google)} elements with 'Google'")
        
        for i, elem in enumerate(elements_with_google[:10]):
            text = elem.text[:50] if elem.text else 'No text'
            tag = elem.tag_name
            print(f"  {i}. {tag}: '{text}'")
        
    finally:
        print("\nClosing browser...")
        driver.quit()

if __name__ == "__main__":
    main()