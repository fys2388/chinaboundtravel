import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class PinterestPoster:
    def __init__(self, config):
        self.config = config
        self.driver = None
        self.login_url = "https://www.pinterest.com/login/"
        
    def init_driver(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        
    def login(self):
        try:
            self.driver.get(self.login_url)
            time.sleep(2)
            
            email_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "email"))
            )
            email_input.send_keys(self.config["email"])
            
            password_input = self.driver.find_element(By.ID, "password")
            password_input.send_keys(self.config["password"])
            
            login_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()
            time.sleep(3)
            
            return True
        except Exception as e:
            print(f"Pinterest login failed: {str(e)}")
            return False
            
    def post(self, title, content, image_url=None, board="China-Travel"):
        try:
            if not self.driver:
                self.init_driver()
                if not self.login():
                    return False
                    
            self.driver.get("https://www.pinterest.com/pin-builder/")
            time.sleep(2)
            
            if image_url:
                image_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//input[@type='file']"))
                )
                image_input.send_keys(image_url)
                time.sleep(3)
            
            title_input = self.driver.find_element(By.XPATH, "//textarea[@placeholder='Add your title']")
            title_input.send_keys(title)
            
            content_input = self.driver.find_element(By.XPATH, "//textarea[@placeholder='Write a description']")
            content_input.send_keys(content)
            
            board_select = self.driver.find_element(By.XPATH, "//div[contains(text(), 'Choose board')]")
            board_select.click()
            time.sleep(1)
            
            board_option = self.driver.find_element(By.XPATH, f"//div[contains(text(), '{board}')]")
            board_option.click()
            time.sleep(1)
            
            save_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Save')]")
            save_button.click()
            time.sleep(2)
            
            return True
        except Exception as e:
            print(f"Pinterest post failed: {str(e)}")
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
            print(f"Pinterest connection test failed: {str(e)}")
            return False