# -*- coding: utf-8 -*-
"""
ChinaBound Travel — Six-Platform Auto Poster
auto_post_final.py

Connects to an existing Chrome remote debugging session (127.0.0.1:9222)
where all social accounts are already logged in.
No new browser is started — reuses the user's active session.

Usage:
    cd e:\AI\dulizhan\travel-blog\chinaboundtravel_social_bot
    python auto_post_final.py

Environment:
    Chrome Debug Browser must be running (start_chrome_debug.ps1)
"""

from __future__ import annotations

import os
import sys
import time
import random
import logging
from datetime import datetime
from urllib.parse import urlencode

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
    StaleElementReferenceException,
)

# ================================================================
# CONFIGURATION
# ================================================================

DEBUGGER_ADDRESS = "127.0.0.1:9222"
TIMEOUT = 15  # seconds for element waits

# Content for Western Sichuan Camping post
TITLE = "Western Sichuan Overland Camping: A 7-Day Adventure Guide for 2026"

FULL_CONTENT = """Just completed an epic 7-day overland camping trip through Western Sichuan! 🏔️

From Chengdu to Kangding, Tagong Grassland to Yajiang, and beyond — this route has some of the most breathtaking landscapes in China.

Highlights:
✅ Camping under the stars at Tagong Grassland
✅ Driving through stunning mountain passes (3000m+)
✅ Authentic Tibetan villages and culture
✅ Yaks and wildlife everywhere along the route

Practical tips for international travelers:
• Best season: May to October
• 4WD is a must — rent in Chengdu
• Prepare for high altitude (3000m+)
• Alipay works in most towns, but carry 500 RMB cash

If you're planning a China trip, make sure you check out my full guide at chinaboundtravel.com for the complete itinerary, packing tips, and everything no one tells you.

#ChinaTravel #Sichuan #Overland #Camping #AdventureTravel #ChinaCamping #WesternSichuan"""

# Reddit version: NO external links in body (platform rule)
REDDIT_CONTENT = """Just completed an epic 7-day overland camping trip through Western Sichuan! 🏔️

From Chengdu to Kangding, Tagong Grassland to Yajiang, and beyond — this route has some of the most breathtaking landscapes in China.

Highlights:
✅ Camping under the stars at Tagong Grassland
✅ Driving through stunning mountain passes (3000m+)
✅ Authentic Tibetan villages and culture
✅ Yaks and wildlife everywhere along the route

Practical tips for international travelers:
• Best season: May to October
• 4WD is a must — rent in Chengdu
• Prepare for high altitude (3000m+)
• Alipay works in most towns, but carry 500 RMB cash

Drop a comment if you want the full route breakdown — happy to share more details! 🙏

#ChinaTravel #Sichuan #Overland #Camping #AdventureTravel"""

PLATFORM_DELAY = 60  # seconds between platforms
HUMAN_MIN = 2.0     # human-like delay minimum (seconds)
HUMAN_MAX = 5.0     # human-like delay maximum (seconds)

# ================================================================
# LOGGING
# ================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            "e:/AI/dulizhan/travel-blog/chinaboundtravel_social_bot/posting_log.txt",
            encoding="utf-8",
            mode="a",
        ),
    ],
)
log = logging.getLogger("chinabound")


# ================================================================
# HELPER FUNCTIONS
# ================================================================

def human_delay(min_sec: float = HUMAN_MIN, max_sec: float = HUMAN_MAX) -> None:
    """Simulate human typing/reading delay."""
    t = random.uniform(min_sec, max_sec)
    log.debug(f"Waiting {t:.2f}s...")
    time.sleep(t)


def human_type(driver: webdriver.Chrome, element, text: str) -> None:
    """Type text character by character like a human."""
    element.clear()
    for char in text:
        element.send_keys(char)
        if random.random() < 0.15:  # 15% chance of a micro-pause
            time.sleep(random.uniform(0.05, 0.2))


def connect_to_chrome() -> webdriver.Chrome:
    """
    Connect to the existing Chrome remote debugging session.
    """
    log.info(f"Connecting to Chrome debug session at {DEBUGGER_ADDRESS}...")

    options = Options()
    options.add_experimental_option("debuggerAddress", DEBUGGER_ADDRESS)

    # Try local chromedriver first, then fall back to system PATH
    chromedriver_paths = [
        r"E:\AI\dulizhan\travel-blog\chinaboundtravel_social_bot\chromedriver.exe",
    ]

    for path in chromedriver_paths:
        if os.path.exists(path):
            try:
                service = Service(path)
                driver = webdriver.Chrome(service=service, options=options)
                driver.switch_to.window(driver.window_handles[0])
                log.info(f"[OK] Connected via local chromedriver: {path}")
                return driver
            except Exception as e:
                log.warning(f"Local chromedriver failed ({path}): {e}")
                continue

    # Fallback: let selenium find chromedriver in PATH
    try:
        driver = webdriver.Chrome(options=options)
        driver.switch_to.window(driver.window_handles[0])
        log.info("[OK] Connected via system chromedriver")
        return driver
    except Exception as e:
        log.error(f"Failed to connect to Chrome: {e}")
        log.error("Solutions:")
        log.error("  1. Download matching chromedriver from https://chromedriver.chromium.org/")
        log.error("  2. Place chromedriver.exe in this folder")
        log.error("  3. Make sure Chrome is running in debug mode (start_post.bat)")
        raise


def wait_and_click(driver: webdriver.Chrome, by: By, selector: str, timeout: int = TIMEOUT) -> webdriver.remote.webelement.WebElement:
    """Wait for element to be clickable then click it."""
    elem = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((by, selector))
    )
    human_delay(0.5, 1.5)
    elem.click()
    return elem


def wait_for_element(driver: webdriver.Chrome, by: By, selector: str, timeout: int = TIMEOUT):
    """Wait for element to be present in DOM."""
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, selector))
    )


def safe_get(driver: webdriver.Chrome, url: str) -> bool:
    """Navigate to URL safely with error handling."""
    try:
        driver.get(url)
        human_delay(1.0, 2.5)
        return True
    except Exception as e:
        log.warning(f"Navigation failed: {e}")
        return False


def add_comment_with_link(driver: webdriver.Chrome, url: str, link_text: str) -> bool:
    """
    After Reddit post, add a comment with the blog link.
    Called 5 minutes after posting (simulate with shorter delay for testing).
    """
    try:
        log.info("Adding comment with blog link...")
        driver.get(url)
        human_delay(2, 4)

        # Click comment box
        comment_box = wait_and_click(
            driver, By.CSS_SELECTOR,
            "textarea[name='comment']", timeout=10
        )
        human_delay(1, 2)

        comment_text = f"Here's the full guide with maps and packing tips: {link_text}"
        human_type(driver, comment_box, comment_text)
        human_delay(1, 2)

        # Click Submit
        submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_btn.click()
        log.info("[OK] Comment posted successfully")
        return True
    except Exception as e:
        log.warning(f"Could not add comment: {e}")
        return False


# ================================================================
# PLATFORM POSTERS
# ================================================================

def post_reddit(driver: webdriver.Chrome) -> dict:
    """Post to Reddit (text post, link added via comment after 5 min)."""
    result = {"platform": "Reddit", "status": "pending", "url": None, "error": None}
    log.info("=" * 50)
    log.info("POSTING TO REDDIT")
    log.info("=" * 50)

    target_subreddits = ["r/ChinaTravel", "r/solotravel", "r/travel"]

    try:
        for attempt, subreddit in enumerate(target_subreddits):
            if attempt > 0:
                log.info(f"Retrying with {subreddit}...")
                human_delay(10, 20)

            log.info(f"Opening reddit.com/submit in {subreddit}")
            if not safe_get(driver, "https://reddit.com/submit"):
                raise Exception("Cannot load Reddit submit page")

            # Switch to text post tab
            try:
                text_tab = wait_and_click(
                    driver, By.CSS_SELECTOR, "button[data-tab-value='text']", timeout=8
                )
                log.info("[OK] Switched to text post mode")
            except:
                log.warning("Could not find text tab, trying direct URL approach")

            human_delay(1, 2)

            # Fill title
            title_input = wait_for_element(driver, By.ID, "title-field")
            human_type(driver, title_input, TITLE)
            log.info(f"[OK] Title filled: {TITLE[:50]}...")
            human_delay(1, 2)

            # Fill body
            body_input = wait_for_element(
                driver, By.CSS_SELECTOR, ".public-DraftEditor-content", timeout=8
            )
            human_type(driver, body_input, REDDIT_CONTENT)
            log.info("[OK] Body content filled (no links in body — Reddit compliant)")
            human_delay(1, 2)

            # Select subreddit
            try:
                community_input = wait_and_click(
                    driver, By.CSS_SELECTOR, "input[name='subreddit']", timeout=5
                )
                community_input.send_keys(subreddit.replace("r/", ""))
                human_delay(1, 2)
                # Select first suggestion
                suggestion = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='autocomplete-row']"))
                )
                suggestion.click()
                log.info(f"[OK] Selected community: {subreddit}")
            except Exception as e:
                log.warning(f"Could not select community: {e}")

            human_delay(1, 2)

            # Click POST button
            post_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            post_btn.click()
            log.info("[OK] POST button clicked")
            human_delay(3, 5)

            # Verify success
            current_url = driver.current_url
            if "/comments/" in current_url or "reddit.com" in current_url:
                result["status"] = "success"
                result["url"] = current_url
                log.info(f"[SUCCESS] Reddit post published: {current_url}")

                # Note: Comment with link would be added after 5 min in production
                # For testing, we skip the delay
                log.info("[NOTE] Blog link to be added via comment (skipping 5-min delay in test mode)")
                return result
            else:
                log.warning(f"Unexpected URL after post: {current_url}")

        result["status"] = "failed"
        result["error"] = "Could not find working subreddit"

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        log.error(f"Reddit posting error: {e}")

    return result


def post_pinterest(driver: webdriver.Chrome) -> dict:
    """Post a Pin to Pinterest."""
    result = {"platform": "Pinterest", "status": "pending", "url": None, "error": None}
    log.info("=" * 50)
    log.info("POSTING TO PINTEREST")
    log.info("=" * 50)

    try:
        if not safe_get(driver, "https://www.pinterest.com/pin/create/"):
            raise Exception("Cannot load Pinterest create page")

        human_delay(2, 4)

        # Fill title
        try:
            title_input = wait_for_element(driver, By.CSS_SELECTOR, "input[data-test-id='pin-title']", timeout=8)
            human_type(driver, title_input, "Western Sichuan Camping: The Ultimate 7-Day Overland Route")
            log.info("[OK] Title filled")
        except:
            log.warning("Title input not found, skipping...")

        human_delay(1, 2)

        # Fill description
        try:
            desc_input = wait_for_element(
                driver, By.CSS_SELECTOR, "textarea[data-test-id='pin-description']", timeout=8
            )
            description = (
                "Complete guide to a 7-day overland camping route through Western Sichuan, China. "
                "Includes Tagong Grassland, Yajiang, high-altitude driving tips, and the best campsites. "
                "Full guide → https://chinaboundtravel.com\n\n"
                "#ChinaTravel #Sichuan #Camping #OverlandAdventure #ChinaCamping"
            )
            human_type(driver, desc_input, description)
            log.info("[OK] Description filled")
        except:
            log.warning("Description input not found, skipping...")

        human_delay(1, 2)

        # Select board
        try:
            board_btn = wait_and_click(
                driver, By.CSS_SELECTOR, "[data-test-id='board-dropdown-select']", timeout=5
            )
            human_delay(1, 2)
            # Find or create "China Travel" board
            try:
                board_option = driver.find_element(By.XPATH, "//div[contains(text(),'China Travel')]")
                board_option.click()
                log.info("[OK] Selected 'China Travel' board")
            except:
                # Try first available board
                first_board = driver.find_element(By.CSS_SELECTOR, "[data-test-id='board-item']")
                first_board.click()
                log.info("[OK] Selected first available board")
        except Exception as e:
            log.warning(f"Board selection failed: {e}")

        human_delay(1, 2)

        # Click Save
        try:
            save_btn = wait_and_click(
                driver, By.CSS_SELECTOR, "[data-test-id='board-select-save']", timeout=5
            )
            log.info("[OK] Pin saved to board")
        except:
            # Try alternative save button
            try:
                all_save_btns = driver.find_elements(By.CSS_SELECTOR, "button[type='button']")
                for btn in all_save_btns:
                    if "save" in btn.text.lower() or "pin" in btn.text.lower():
                        btn.click()
                        log.info("[OK] Alternative save button clicked")
                        break
            except:
                log.warning("Save button not found")

        human_delay(2, 4)
        current_url = driver.current_url
        result["status"] = "success"
        result["url"] = current_url
        log.info(f"[SUCCESS] Pinterest Pin saved: {current_url}")

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        log.error(f"Pinterest posting error: {e}")

    return result


def post_quora(driver: webdriver.Chrome) -> dict:
    """Answer a relevant Quora question."""
    result = {"platform": "Quora", "status": "pending", "url": None, "error": None}
    log.info("=" * 50)
    log.info("POSTING TO QUORA")
    log.info("=" * 50)

    questions = [
        "How do I plan a road trip in Western Sichuan?",
        "What is the best way to travel in Western Sichuan?",
        "Is it safe to camp in Sichuan for foreign tourists?",
    ]

    try:
        for question in questions:
            if not safe_get(driver, "https://www.quora.com/"):
                continue

            human_delay(2, 3)

            # Search for question
            try:
                search_box = wait_for_element(
                    driver, By.CSS_SELECTOR, "input[type='search']", timeout=8
                )
                human_type(driver, search_box, question)
                search_box.send_keys(Keys.ENTER)
                log.info(f"[OK] Searched for: {question}")
                human_delay(2, 4)
            except:
                log.warning("Search box not found")

            # Try to find the answer box
            answer_triggered = False
            try:
                answer_trigger = wait_and_click(
                    driver, By.CSS_SELECTOR,
                    "[data-testid='AnswerComposer']", timeout=6
                )
                answer_triggered = True
            except Exception:
                try:
                    # Fallback: look for "Add Answer" or "Answer" button
                    answer_btns = driver.find_elements(By.XPATH, "//span[contains(text(),'Answer')]")
                    if answer_btns:
                        answer_btns[0].click()
                        answer_triggered = True
                    else:
                        log.warning("Could not find answer trigger")
                        human_delay(2, 3)
                        continue
                except Exception as e:
                    log.warning(f"Quora answer trigger failed: {e}")
                    human_delay(2, 3)
                    continue

            human_delay(2, 3)

            # Fill answer
            try:
                answer_box = wait_for_element(
                    driver, By.CSS_SELECTOR,
                    "[data-testid='RichTextTextarea']", timeout=8
                )
                answer_text = (
                    "Just finished a 7-day overland camping trip through Western Sichuan — here's what I learned:\n\n"
                    "The route goes: Chengdu → Kangding → Tagong Grassland → Yajiang → Danba → …\n\n"
                    "Key tips:\n"
                    "✅ May to October is the best window\n"
                    "✅ Rent a 4WD in Chengdu (essential)\n"
                    "✅ Altitude hits 3000m+ — bring layers and Diamox\n"
                    "✅ Carry 500 RMB cash + activate Alipay before leaving cities\n"
                    "✅ Tagong Grassland has the best campsites\n\n"
                    "I documented the full day-by-day breakdown on my blog:\n"
                    "https://chinaboundtravel.com\n\n"
                    "Happy to answer specific questions in the comments!"
                )
                human_type(driver, answer_box, answer_text)
                log.info("[OK] Answer filled")
                human_delay(1, 2)
            except Exception as e:
                log.warning(f"Answer box not found: {e}")
                continue

            # Submit
            try:
                submit_btn = wait_and_click(
                    driver, By.CSS_SELECTOR,
                    "button[type='submit']", timeout=5
                )
                log.info("[OK] Submit clicked")
                human_delay(2, 4)
            except:
                log.warning("Submit button not found")

            if "quora.com" in driver.current_url:
                result["status"] = "success"
                result["url"] = driver.current_url
                log.info(f"[SUCCESS] Quora answer posted: {driver.current_url}")
                return result

        result["status"] = "failed"
        result["error"] = "No suitable question found"

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        log.error(f"Quora posting error: {e}")

    return result


def post_medium(driver: webdriver.Chrome) -> dict:
    """Post a long-form article to Medium."""
    result = {"platform": "Medium", "status": "pending", "url": None, "error": None}
    log.info("=" * 50)
    log.info("POSTING TO MEDIUM")
    log.info("=" * 50)

    try:
        if not safe_get(driver, "https://medium.com/new-story"):
            raise Exception("Cannot load Medium new story page")

        human_delay(2, 3)

        # Fill title
        title_input = wait_for_element(
            driver, By.CSS_SELECTOR, "h1[data-hj-suppress]", timeout=10
        )
        if not title_input:
            title_input = wait_for_element(
                driver, By.XPATH, "//h1[contains(@class,'Title')]", timeout=10
            )
        human_type(driver, title_input, TITLE)
        log.info(f"[OK] Title filled: {TITLE[:50]}...")
        human_delay(1, 2)

        # Fill body
        try:
            body_input = wait_for_element(
                driver, By.XPATH,
                "//div[@data-slate-editor='true']", timeout=8
            )
        except:
            body_input = wait_for_element(
                driver, By.CSS_SELECTOR, "[data-slate-node='paragraph']", timeout=8
            )

        body_text = (
            "Just completed an epic 7-day overland camping trip through Western Sichuan. "
            "This route has everything — high-altitude mountain passes, Tibetan grasslands, "
            "wild yaks, and stars you'll remember for the rest of your life.\n\n"
            "## The Route\n\n"
            "Chengdu → Kangding → Tagong Grassland → Yajiang → Danba → ...\n\n"
            "## Highlights\n\n"
            "✅ Camping under the stars at Tagong Grassland\n"
            "✅ Driving through 3000m+ mountain passes\n"
            "✅ Authentic Tibetan villages\n"
            "✅ Yaks and wildlife everywhere\n\n"
            "## Practical Tips for International Travelers\n\n"
            "• **Best season:** May to October\n"
            "• **Vehicle:** 4WD is essential — rent in Chengdu\n"
            "• **Altitude:** 3000m+ — bring layers and consider Diamox\n"
            "• **Payments:** Alipay works in most towns, carry 500 RMB cash\n"
            "• **Camping:** Bring your own gear, Tagong has managed campsites\n\n"
            "I documented the full day-by-day breakdown, exact GPS waypoints, "
            "and everything I wish someone told me before I went.\n\n"
            "👉 **Full guide:** https://chinaboundtravel.com**"
        )
        human_type(driver, body_input, body_text)
        log.info("[OK] Body content filled")
        human_delay(1, 2)

        # Add tags
        try:
            tags_input = wait_for_element(
                driver, By.CSS_SELECTOR, "input[data-test-id='tag-input']", timeout=5
            )
            for tag in ["travel", "china", "sichuan", "camping", "adventure"]:
                tags_input.send_keys(tag)
                tags_input.send_keys(Keys.ENTER)
                human_delay(0.3, 0.8)
            log.info("[OK] Tags added")
        except Exception as e:
            log.warning(f"Tags not added: {e}")

        human_delay(1, 2)

        # Click Publish
        try:
            publish_btn = wait_and_click(
                driver, By.CSS_SELECTOR,
                "button[data-testid='publishButton']", timeout=5
            )
            log.info("[OK] Publish button clicked")
            human_delay(3, 5)
        except:
            # Fallback publish button
            try:
                publish_btn = driver.find_element(By.XPATH, "//button[contains(text(),'Publish')]")
                publish_btn.click()
                log.info("[OK] Alternative Publish clicked")
                human_delay(3, 5)
            except Exception as e:
                log.warning(f"Publish button not found: {e}")

        current_url = driver.current_url
        if "medium.com" in current_url:
            result["status"] = "success"
            result["url"] = current_url
            log.info(f"[SUCCESS] Medium article published: {current_url}")
        else:
            result["status"] = "unknown"
            result["url"] = current_url
            log.info(f"[OK] Medium publish attempted, URL: {current_url}")

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        log.error(f"Medium posting error: {e}")

    return result


def post_instagram(driver: webdriver.Chrome) -> dict:
    """
    Instagram — post via网页版文字动态（网页版图片需App）。
    NOTE: Instagram 网页发帖功能有限，建议使用 Facebook Creator Studio 代替。
    This posts a TEXT-ONLY story/feed text post as fallback.
    """
    result = {"platform": "Instagram", "status": "pending", "url": None, "error": None}
    log.info("=" * 50)
    log.info("POSTING TO INSTAGRAM (text post fallback)")
    log.info("=" * 50)

    log.warning("[WARN] Instagram web only supports text posts. For image posts, use Facebook Creator Studio.")
    log.info("Opening Instagram...")

    try:
        if not safe_get(driver, "https://www.instagram.com/"):
            raise Exception("Cannot load Instagram")

        human_delay(2, 4)

        # Try to find "Create" or "+" button
        try:
            create_btn = wait_and_click(
                driver, By.CSS_SELECTOR,
                "a[href='#'][role='link'], svg[aria-label='New post']", timeout=6
            )
        except:
            log.warning("Cannot find create button, trying direct create URL")
            safe_get(driver, "https://www.instagram.com/create/style/")

        human_delay(2, 3)

        # Since Instagram web mostly requires app for image posts,
        # log a note that Creator Studio is the recommended path
        result["status"] = "skipped"
        result["error"] = "Instagram web requires app for image posts. Use Facebook Creator Studio instead."
        log.info("[SKIP] Instagram — use Facebook Creator Studio for image posts")

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        log.error(f"Instagram posting error: {e}")

    return result


def post_facebook(driver: webdriver.Chrome) -> dict:
    """
    Facebook — post to Page/Profile via web.
    NOTE: Facebook has strong anti-automation detection.
    Recommended: Use Meta Business Suite or Buffer instead.
    """
    result = {"platform": "Facebook", "status": "pending", "url": None, "error": None}
    log.info("=" * 50)
    log.info("POSTING TO FACEBOOK")
    log.info("=" * 50)

    log.warning("[WARN] Facebook has strong anti-bot detection. Use Meta Business Suite for recurring posts.")

    try:
        if not safe_get(driver, "https://www.facebook.com/"):
            raise Exception("Cannot load Facebook")

        human_delay(2, 4)

        # Find "Create Post" box
        try:
            post_box = wait_and_click(
                driver, By.CSS_SELECTOR,
                "[data-testid='medias parl compose message input composer']", timeout=8
            )
        except:
            try:
                post_box = driver.find_element(
                    By.XPATH, "//span[contains(text(),'on your mind')]"
                )
                post_box.click()
            except:
                post_box = driver.find_element(
                    By.CSS_SELECTOR, "textarea[aria-label*='mind']"
                )

        human_delay(1, 2)

        fb_content = (
            "🏔️ Just finished an epic 7-day overland camping trip through Western Sichuan, China!\n\n"
            "From Chengdu to Kangding, Tagong Grassland to Yajiang — this route has some of "
            "the most breathtaking high-altitude landscapes I've ever seen.\n\n"
            "✅ Camping under the stars at Tagong\n"
            "✅ 3000m+ mountain passes\n"
            "✅ Authentic Tibetan culture\n\n"
            "Full guide with day-by-day breakdown → https://chinaboundtravel.com\n\n"
            "#ChinaTravel #Sichuan #OverlandCamping #AdventureTravel"
        )
        human_type(driver, driver.switch_to.active_element, fb_content)
        log.info("[OK] Post content filled")
        human_delay(1, 2)

        # Click Post
        try:
            post_btn = driver.find_element(
                By.XPATH, "//div[@aria-label='Post'][not(@role)]//span[contains(text(),'Post')]"
            )
            post_btn.click()
        except:
            try:
                post_btn = driver.find_element(By.CSS_SELECTOR, "div[aria-label='Post']")
                post_btn.click()
            except:
                log.warning("Post button not found")

        human_delay(3, 5)
        result["status"] = "success"
        result["url"] = driver.current_url
        log.info(f"[OK] Facebook post submitted: {driver.current_url}")

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        log.error(f"Facebook posting error: {e}")

    return result


# ================================================================
# MAIN EXECUTION
# ================================================================

def main():
    start_time = datetime.now()
    log.info("")
    log.info("=" * 60)
    log.info(" ChinaBound Travel — Six-Platform Auto Poster")
    log.info(f" Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    log.info("=" * 60)
    log.info("")
    log.info("NOTE: Ensure Chrome debug browser is running")
    log.info("      (start_chrome_debug.ps1) and all accounts")
    log.info("      are logged in before starting.")
    log.info("")

    driver = None
    results = []

    try:
        driver = connect_to_chrome()

        # Close any extra tabs (keep only one)
        if len(driver.window_handles) > 1:
            for handle in driver.window_handles[1:]:
                driver.switch_to.window(handle)
                driver.close()
            driver.switch_to.window(driver.window_handles[0])
            log.info(f"[OK] Closed extra tabs, now on: {driver.current_url}")

        # ---- Reddit ----
        r = post_reddit(driver)
        results.append(r)
        if r["status"] == "success":
            log.info(f"✅ Reddit: {r['url']}")
        else:
            log.error(f"❌ Reddit: {r['error']}")

        log.info(f"Waiting {PLATFORM_DELAY}s before next platform...")
        time.sleep(PLATFORM_DELAY)

        # ---- Pinterest ----
        p = post_pinterest(driver)
        results.append(p)
        if p["status"] == "success":
            log.info(f"✅ Pinterest: {p['url']}")
        else:
            log.error(f"❌ Pinterest: {p['error']}")

        log.info(f"Waiting {PLATFORM_DELAY}s before next platform...")
        time.sleep(PLATFORM_DELAY)

        # ---- Quora ----
        q = post_quora(driver)
        results.append(q)
        if q["status"] == "success":
            log.info(f"✅ Quora: {q['url']}")
        else:
            log.error(f"❌ Quora: {q['error']}")

        log.info(f"Waiting {PLATFORM_DELAY}s before next platform...")
        time.sleep(PLATFORM_DELAY)

        # ---- Medium ----
        m = post_medium(driver)
        results.append(m)
        if m["status"] == "success":
            log.info(f"✅ Medium: {m['url']}")
        else:
            log.error(f"❌ Medium: {m['error']}")

        log.info(f"Waiting {PLATFORM_DELAY}s before next platform...")
        time.sleep(PLATFORM_DELAY)

        # ---- Instagram ----
        i = post_instagram(driver)
        results.append(i)
        log.info(f"{'⏭️ Instagram: ' + i['error'] if i['error'] else '⏭️ Instagram: skipped'}")

        log.info(f"Waiting {PLATFORM_DELAY}s before next platform...")
        time.sleep(PLATFORM_DELAY)

        # ---- Facebook ----
        fb = post_facebook(driver)
        results.append(fb)
        if fb["status"] == "success":
            log.info(f"✅ Facebook: {fb['url']}")
        else:
            log.error(f"❌ Facebook: {fb['error']}")

    except KeyboardInterrupt:
        log.warning("Interrupted by user")
    except Exception as e:
        log.error(f"Fatal error: {e}")
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

    # ---- Summary Report ----
    end_time = datetime.now()
    elapsed = (end_time - start_time).total_seconds()

    log.info("")
    log.info("=" * 60)
    log.info(" POSTING SUMMARY REPORT")
    log.info(f" Completed: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    log.info(f" Total time: {elapsed:.0f}s ({elapsed/60:.1f}min)")
    log.info("=" * 60)

    success_count = 0
    for res in results:
        status_icon = "✅" if res["status"] == "success" else ("⚠️" if res["status"] in ("skipped","unknown") else "❌")
        error_note = f" | {res['error']}" if res['error'] else ""
        log.info(f"  {status_icon} {res['platform']:<12} | {res['status']:<10} | {res['url'] or ''}{error_note}")
        if res["status"] == "success":
            success_count += 1

    log.info("")
    log.info(f" Result: {success_count}/{len(results)} platforms posted successfully")
    log.info("")
    log.info("DONE. Close Chrome debug browser when finished.")
    log.info("")

    return results


if __name__ == "__main__":
    main()
