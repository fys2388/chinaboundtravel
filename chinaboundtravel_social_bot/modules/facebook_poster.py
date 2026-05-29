import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class FacebookPoster:
    def __init__(self, config):
        self.config = config
        self.driver = None
        self.login_url = "https://www.facebook.com/login/"
        
    def init_driver(self):
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
        
        self.driver = webdriver.Chrome(options=chrome_options)
        
    def login(self):
        try:
            self.driver.get(self.login_url)
            time.sleep(3)
            
            email_input = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.ID, "email"))
            )
            email_input.send_keys(self.config["email"])
            
            password_input = self.driver.find_element(By.ID, "pass")
            password_input.send_keys(self.config["password"])
            
            login_button = self.driver.find_element(By.NAME, "login")
            login_button.click()
            time.sleep(5)
            
            return True
        except Exception as e:
            print(f"Facebook login failed: {str(e)}")
            return False
            
    def post(self, content, image_path=None):
        try:
            if not self.driver:
                self.init_driver()
                if not self.login():
                    return False
                    
            self.driver.get("https://www.facebook.com/")
            time.sleep(3)
            
            post_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true']"))
            )
            post_box.send_keys(content)
            
            if image_path:
                photo_button = self.driver.find_element(By.XPATH, "//input[@type='file']")
                photo_button.send_keys(image_path)
                time.sleep(3)
            
            post_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            post_button.click()
            time.sleep(3)
            
            return True
        except Exception as e:
            print(f"Facebook post failed: {str(e)}")
            return False
            
    def close(self):
        if self.driver:
            self.driver.quit()

    def test_connection(self):
        try:
            self.init_driver()
            result = self.login()
            self.close()
            return result
        except Exception as e:
            print(f"Facebook connection test failed: {str(e)}")
            return False