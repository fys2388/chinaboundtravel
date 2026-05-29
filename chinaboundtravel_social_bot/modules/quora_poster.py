import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class QuoraPoster:
    def __init__(self, config):
        self.config = config
        self.driver = None
        self.login_url = "https://www.quora.com/login"
        
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
                EC.presence_of_element_located((By.XPATH, "//input[@type='email']"))
            )
            email_input.send_keys(self.config["email"])
            
            continue_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            continue_button.click()
            time.sleep(2)
            
            password_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@type='password']"))
            )
            password_input.send_keys(self.config["password"])
            
            login_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()
            time.sleep(3)
            
            return True
        except Exception as e:
            print(f"Quora login failed: {str(e)}")
            return False
            
    def answer(self, question_url, content):
        try:
            if not self.driver:
                self.init_driver()
                if not self.login():
                    return False
                    
            self.driver.get(question_url)
            time.sleep(2)
            
            answer_button = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'Answer')]"))
            )
            answer_button.click()
            time.sleep(2)
            
            content_input = self.driver.find_element(By.XPATH, "//textarea[contains(@class, 'q-box')]")
            content_input.send_keys(content)
            
            submit_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Submit')]")
            submit_button.click()
            time.sleep(2)
            
            return True
        except Exception as e:
            print(f"Quora answer failed: {str(e)}")
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
            print(f"Quora connection test failed: {str(e)}")
            return False