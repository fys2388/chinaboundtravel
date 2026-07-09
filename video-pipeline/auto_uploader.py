#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动上传器 - 使用Selenium模拟浏览器操作
通过浏览器界面自动上传视频到Buffer社媒平台
"""
import os
import sys
import time
import json
from typing import Dict, Optional

sys.path.insert(0, os.path.dirname(__file__))

from config import Config

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.keys import Keys
    from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementNotInteractableException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


class AutoUploader:
    def __init__(self):
        self.driver = None
        self.wait = None
    
    def _init_driver(self, headless: bool = False):
        if not SELENIUM_AVAILABLE:
            raise ImportError("Selenium not installed. Please install it with: pip install selenium")
        
        options = Options()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--ignore-certificate-errors")
        
        if headless:
            options.add_argument("--headless=new")
        
        try:
            service = Service()
            self.driver = webdriver.Chrome(service=service, options=options)
            self.wait = WebDriverWait(self.driver, 30)
            return True
        except Exception as e:
            print(f"浏览器启动失败: {e}")
            return False
    
    def _find_element(self, by: str, value: str, timeout: int = 15) -> Optional[object]:
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except TimeoutException:
            return None
    
    def _click_element(self, by: str, value: str, timeout: int = 15):
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
            element.click()
            return True
        except (TimeoutException, ElementNotInteractableException):
            return False
    
    def _send_keys(self, by: str, value: str, keys: str, timeout: int = 15):
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            element.clear()
            element.send_keys(keys)
            return True
        except TimeoutException:
            return False
    
    def _upload_file(self, file_path: str):
        try:
            file_input = self.driver.find_element(By.XPATH, "//input[@type='file']")
            file_input.send_keys(file_path)
            print(f"已选择文件: {file_path}")
            return True
        except Exception as e:
            print(f"文件上传失败: {e}")
            return False
    
    def login_buffer(self):
        print("\n正在打开Buffer网站...")
        self.driver.get("https://publish.buffer.com")
        time.sleep(5)
        
        try:
            current_url = self.driver.current_url
            
            if "login" not in current_url.lower() and "publish.buffer.com" in current_url:
                print("✓ 已登录Buffer")
                return True
            
            print("需要登录Buffer，正在等待登录页面加载...")
            
            google_btn = self._find_element(By.CSS_SELECTOR, "button[data-provider='google']")
            if google_btn:
                print("点击Google登录按钮...")
                google_btn.click()
                time.sleep(5)
                
                email_input = self._find_element(By.ID, "identifierId")
                if email_input:
                    print("请手动完成Google账户登录...")
                    time.sleep(30)
                    
                    current_url = self.driver.current_url
                    if "publish.buffer.com" in current_url:
                        print("✓ 登录成功")
                        return True
                    else:
                        print("登录未完成")
                        return False
                else:
                    print("等待Google账户选择...")
                    time.sleep(20)
                    current_url = self.driver.current_url
                    if "publish.buffer.com" in current_url:
                        print("✓ 登录成功")
                        return True
                    return False
            else:
                print("请手动完成登录...")
                time.sleep(45)
                current_url = self.driver.current_url
                if "publish.buffer.com" in current_url:
                    print("✓ 登录成功")
                    return True
                return False
        except Exception as e:
            print(f"登录过程出错: {e}")
            return False
    
    def upload_to_buffer(self, video_path: str, title: str, description: str, tags: list, channel_id: str = "") -> str:
        if not os.path.exists(video_path):
            print(f"错误: 文件不存在 - {video_path}")
            return ""
        
        if not self._init_driver(headless=False):
            return ""
        
        try:
            if not self.login_buffer():
                print("登录失败")
                self.driver.quit()
                return ""
            
            print("\n正在进入发布页面...")
            time.sleep(5)
            
            new_post_btn = self._find_element(By.CSS_SELECTOR, "button[aria-label*='New Post'], button[data-testid*='new-post'], button:contains('New Post')")
            if not new_post_btn:
                new_post_btn = self._find_element(By.XPATH, "//button[contains(text(), 'New Post') or contains(text(), '新帖子')]")
            
            if new_post_btn:
                new_post_btn.click()
                time.sleep(3)
            else:
                print("尝试直接访问发布页面...")
                self.driver.get("https://publish.buffer.com/publish")
                time.sleep(5)
            
            print("正在上传视频...")
            upload_area = self._find_element(By.CSS_SELECTOR, "[data-testid='media-upload'], [role='button']")
            if upload_area:
                upload_area.click()
                time.sleep(2)
            
            if not self._upload_file(video_path):
                print("尝试另一种上传方式...")
                upload_buttons = self.driver.find_elements(By.TAG_NAME, "button")
                for btn in upload_buttons:
                    try:
                        if "upload" in btn.text.lower() or "添加" in btn.text:
                            btn.click()
                            time.sleep(2)
                            self._upload_file(video_path)
                            break
                    except:
                        continue
            
            print("等待视频上传完成...")
            time.sleep(15)
            
            print("正在填写标题和描述...")
            text_area = self._find_element(By.CSS_SELECTOR, "textarea, [contenteditable='true'], input[placeholder*='Write']")
            if text_area:
                full_text = f"{title}\n\n{description}\n\n{' '.join(tags)}"
                text_area.clear()
                text_area.send_keys(full_text)
                print(f"✓ 已填写内容")
            
            print("正在选择频道...")
            channel_selector = self._find_element(By.CSS_SELECTOR, "[data-testid='channel-selector'], select")
            if channel_selector:
                channel_selector.click()
                time.sleep(2)
                
                channels = self.driver.find_elements(By.CSS_SELECTOR, "[role='option'], li")
                for channel in channels:
                    try:
                        if channel_id in channel.get_attribute("value", "") or channel_id in channel.text:
                            channel.click()
                            print(f"✓ 已选择频道")
                            break
                    except:
                        continue
            
            print("正在发布...")
            publish_btn = self._find_element(By.CSS_SELECTOR, "button[data-testid*='publish'], button:contains('Publish')")
            if not publish_btn:
                publish_btn = self._find_element(By.XPATH, "//button[contains(text(), 'Publish') or contains(text(), '发布') or contains(text(), 'Share')]")
            
            if publish_btn:
                publish_btn.click()
                print("✓ 正在发布...")
                time.sleep(5)
                
                success_msg = self._find_element(By.CSS_SELECTOR, "[data-testid*='success'], .success")
                if success_msg:
                    print(f"✓ 发布成功!")
                    return f"https://publish.buffer.com (已自动发布)"
            
            print("发布完成（可能需要手动确认）")
            return f"https://publish.buffer.com (已完成自动上传流程)"
            
        except Exception as e:
            print(f"自动上传出错: {e}")
            import traceback
            traceback.print_exc()
            return ""
        finally:
            input("\n按 Enter 关闭浏览器...")
            self.driver.quit()
    
    def upload_to_tiktok(self, video_path: str, title: str, description: str, tags: list) -> str:
        if not os.path.exists(video_path):
            print(f"错误: 文件不存在 - {video_path}")
            return ""
        
        if not self._init_driver(headless=False):
            return ""
        
        try:
            print("\n正在打开TikTok上传页面...")
            self.driver.get("https://www.tiktok.com/upload")
            time.sleep(5)
            
            if "login" in self.driver.current_url:
                print("需要登录TikTok，请手动完成登录...")
                time.sleep(45)
                
                if "upload" not in self.driver.current_url:
                    self.driver.get("https://www.tiktok.com/upload")
                    time.sleep(5)
            
            print("正在上传视频...")
            upload_input = self._find_element(By.XPATH, "//input[@type='file']")
            if upload_input:
                upload_input.send_keys(video_path)
                print(f"✓ 已选择文件")
                time.sleep(10)
            
            print("正在填写标题...")
            title_input = self._find_element(By.CSS_SELECTOR, "input[placeholder*='Title'], input[placeholder*='标题']")
            if title_input:
                title_input.send_keys(title)
            
            print("正在填写描述...")
            desc_input = self._find_element(By.CSS_SELECTOR, "textarea, [contenteditable='true']")
            if desc_input:
                desc_input.send_keys(f"{description}\n\n{' '.join(tags)}")
            
            print("等待上传完成...")
            time.sleep(15)
            
            print("TikTok自动上传完成，请手动确认发布")
            return f"https://www.tiktok.com/upload (已完成自动上传流程)"
            
        except Exception as e:
            print(f"TikTok上传出错: {e}")
            import traceback
            traceback.print_exc()
            return ""
        finally:
            input("\n按 Enter 关闭浏览器...")
            self.driver.quit()
    
    def upload_to_youtube(self, video_path: str, title: str, description: str, tags: list, privacy_status: str = "public") -> str:
        if not os.path.exists(video_path):
            print(f"错误: 文件不存在 - {video_path}")
            return ""
        
        if not self._init_driver(headless=False):
            return ""
        
        try:
            print("\n正在打开YouTube Studio...")
            self.driver.get("https://studio.youtube.com")
            time.sleep(5)
            
            if "accounts.google.com" in self.driver.current_url:
                print("需要登录YouTube，请手动完成登录...")
                time.sleep(45)
                
                if "studio.youtube.com" not in self.driver.current_url:
                    self.driver.get("https://studio.youtube.com")
                    time.sleep(5)
            
            print("正在点击创建按钮...")
            create_btn = self._find_element(By.CSS_SELECTOR, "[aria-label*='Create'], button[data-testid*='create']")
            if create_btn:
                create_btn.click()
                time.sleep(2)
                
                upload_option = self._find_element(By.XPATH, "//span[contains(text(), 'Upload') or contains(text(), '上传')]")
                if upload_option:
                    upload_option.click()
                    time.sleep(3)
            
            if not create_btn:
                self.driver.get("https://studio.youtube.com/channel/upload")
                time.sleep(5)
            
            print("正在上传视频...")
            upload_area = self._find_element(By.CSS_SELECTOR, "[role='button'], [data-testid='upload-drop-zone']")
            if upload_area:
                upload_area.click()
                time.sleep(2)
            
            upload_input = self._find_element(By.XPATH, "//input[@type='file']")
            if upload_input:
                upload_input.send_keys(video_path)
                print(f"✓ 已选择文件")
                time.sleep(15)
            
            print("正在填写标题...")
            title_input = self._find_element(By.CSS_SELECTOR, "input[name='title'], [placeholder*='Title']")
            if title_input:
                title_input.send_keys(title)
            
            print("正在填写描述...")
            desc_input = self._find_element(By.CSS_SELECTOR, "textarea[name='description'], [placeholder*='Description']")
            if desc_input:
                desc_input.send_keys(f"{description}\n\n{' '.join(tags)}")
            
            print("正在设置标签...")
            tags_input = self._find_element(By.CSS_SELECTOR, "input[placeholder*='Tags']")
            if tags_input:
                tags_input.send_keys(','.join(tags))
            
            print("YouTube自动上传完成，请手动确认发布")
            return f"https://studio.youtube.com (已完成自动上传流程)"
            
        except Exception as e:
            print(f"YouTube上传出错: {e}")
            import traceback
            traceback.print_exc()
            return ""
        finally:
            input("\n按 Enter 关闭浏览器...")
            self.driver.quit()


def auto_upload(video_path: str, title: str, description: str, tags: list, platforms: list = ["buffer"]) -> Dict:
    results = {}
    
    if not SELENIUM_AVAILABLE:
        print("错误: Selenium未安装")
        return {"error": "Selenium not installed"}
    
    uploader = AutoUploader()
    
    for platform in platforms:
        platform = platform.lower()
        print(f"\n{'='*60}")
        print(f"正在上传到 {platform.upper()}")
        print(f"{'='*60}")
        
        if platform == "buffer":
            result = uploader.upload_to_buffer(video_path, title, description, tags)
        elif platform == "tiktok":
            result = uploader.upload_to_tiktok(video_path, title, description, tags)
        elif platform == "youtube":
            result = uploader.upload_to_youtube(video_path, title, description, tags)
        else:
            result = f"平台 {platform} 不支持"
        
        results[platform] = result
    
    return results


def main():
    if len(sys.argv) < 2:
        print("用法: python auto_uploader.py <视频文件路径> [平台列表]")
        print("示例: python auto_uploader.py output/test_video.mp4 buffer,tiktok")
        return
    
    video_path = sys.argv[1]
    
    if len(sys.argv) > 2:
        platforms = sys.argv[2].split(',')
    else:
        platforms = ["buffer"]
    
    title = "Yunnan Adventure: Discover China's Hidden Gem"
    description = "Explore the breathtaking beauty of Yunnan province with its stunning rice terraces and ancient towns. Experience authentic Chinese culture and nature at its finest."
    tags = ["#Yunnan", "#ChinaTravel", "#Travel", "#RiceTerraces", "#AncientTowns"]
    
    print(f"{'='*60}")
    print(f"  自动上传器")
    print(f"{'='*60}")
    print(f"")
    print(f"  视频文件: {video_path}")
    print(f"  目标平台: {', '.join(platforms)}")
    print(f"  标题: {title}")
    print(f"")
    
    results = auto_upload(video_path, title, description, tags, platforms)
    
    print(f"\n{'='*60}")
    print(f"  上传结果")
    print(f"{'='*60}")
    for platform, result in results.items():
        print(f"  {platform}: {result}")


if __name__ == "__main__":
    main()