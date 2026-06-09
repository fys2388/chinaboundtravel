# -*- coding: utf-8 -*-
"""
ChinaBound Travel — Six-Platform Auto Poster (Remote Grid Edition)

支持两种连接模式：
  1. LOCAL 模式：连接本地 Chrome 调试端口（127.0.0.1:9222）
  2. REMOTE 模式：连接 Selenium Grid Hub（如 http://192.168.x.x:4444）

使用前设置 CONNECTION_MODE 和 HUB_URL
"""

from __future__ import annotations
import sys
import time
import random
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
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
# ⚙️  CONNECTION SETTINGS — 修改这里切换模式
# ================================================================
CONNECTION_MODE = "REMOTE"          # "LOCAL" 或 "REMOTE"
HUB_URL    = "http://192.168.1.100:4444"  # Selenium Grid Hub 地址（REMOTE模式）
DEBUG_ADDR = "127.0.0.1:9222"       # Chrome 调试端口（LOCAL模式）
# ================================================================

TIMEOUT = 15
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

Full guide with day-by-day breakdown → https://chinaboundtravel.com

#ChinaTravel #Sichuan #Overland #Camping #AdventureTravel"""

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

PLATFORM_DELAY = 60
HUMAN_MIN, HUMAN_MAX = 2.0, 5.0

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            "e:/AI/dulizhan/travel-blog/chinaboundtravel_social_bot/posting_log_remote.txt",
            encoding="utf-8", mode="a",
        ),
    ],
)
log = logging.getLogger("chinabound-remote")


def human_delay(min_sec: float = HUMAN_MIN, max_sec: float = HUMAN_MAX) -> None:
    t = random.uniform(min_sec, max_sec)
    time.sleep(t)


def human_type(driver: webdriver.Chrome, element, text: str) -> None:
    element.clear()
    for char in text:
        element.send_keys(char)
        if random.random() < 0.15:
            time.sleep(random.uniform(0.05, 0.2))


def build_driver() -> webdriver.Chrome:
    """根据 CONNECTION_MODE 连接本地调试端口或远程 Grid"""
    log.info(f"Connecting to Selenium ({CONNECTION_MODE} mode)...")

    chrome_opts = Options()
    if CONNECTION_MODE == "LOCAL":
        chrome_opts.add_experimental_option("debuggerAddress", DEBUG_ADDR)
    else:  # REMOTE
        pass  # Hub handles Chrome version automatically

    if CONNECTION_MODE == "REMOTE":
        driver = webdriver.Remote(
            command_executor=HUB_URL,
            options=chrome_opts,
        )
    else:
        from selenium.webdriver.chrome.service import Service
        driver = webdriver.Chrome(options=chrome_opts)

    driver.switch_to.window(driver.window_handles[0])
    log.info(f"[OK] Connected — {driver.capabilities}")
    return driver


def safe_get(driver: webdriver.Chrome, url: str) -> bool:
    try:
        driver.get(url)
        human_delay(1.0, 2.5)
        return True
    except Exception as e:
        log.warning(f"Navigation failed: {e}")
        return False


def wait_and_click(driver: webdriver.Chrome, by: By, selector: str, timeout: int = TIMEOUT):
    elem = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((by, selector))
    )
    human_delay(0.5, 1.5)
    elem.click()
    return elem


def wait_for_element(driver: webdriver.Chrome, by: By, selector: str, timeout: int = TIMEOUT):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, selector))
    )


# ---- Reddit ----
def post_reddit(driver: webdriver.Chrome) -> dict:
    result = {"platform": "Reddit", "status": "pending", "url": None, "error": None}
    log.info("=" * 50); log.info("POSTING TO REDDIT"); log.info("=" * 50)
    target_subreddits = ["r/ChinaTravel", "r/solotravel", "r/travel"]

    try:
        for attempt, subreddit in enumerate(target_subreddits):
            if attempt > 0:
                log.info(f"Retrying with {subreddit}...")
                human_delay(10, 20)

            if not safe_get(driver, "https://reddit.com/submit"):
                raise Exception("Cannot load Reddit submit page")

            try:
                wait_and_click(driver, By.CSS_SELECTOR, "button[data-tab-value='text']", timeout=8)
                log.info("[OK] Text post mode")
            except Exception:
                log.warning("Text tab not found")

            human_delay(1, 2)
            title_input = wait_for_element(driver, By.ID, "title-field")
            human_type(driver, title_input, TITLE)
            log.info(f"[OK] Title filled")
            human_delay(1, 2)

            body_input = wait_for_element(
                driver, By.CSS_SELECTOR, ".public-DraftEditor-content", timeout=8
            )
            human_type(driver, body_input, REDDIT_CONTENT)
            log.info("[OK] Body filled (no links — Reddit compliant)")
            human_delay(1, 2)

            try:
                community_input = wait_and_click(
                    driver, By.CSS_SELECTOR, "input[name='subreddit']", timeout=5
                )
                community_input.send_keys(subreddit.replace("r/", ""))
                human_delay(1, 2)
                suggestion = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='autocomplete-row']"))
                )
                suggestion.click()
                log.info(f"[OK] Community: {subreddit}")
            except Exception as e:
                log.warning(f"Community select failed: {e}")

            human_delay(1, 2)
            driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
            log.info("[OK] POST clicked")
            human_delay(3, 5)

            if "/comments/" in driver.current_url:
                result["status"] = "success"
                result["url"] = driver.current_url
                log.info(f"[SUCCESS] {driver.current_url}")
                return result
            else:
                log.warning(f"Unexpected URL: {driver.current_url}")

        result["status"] = "failed"
        result["error"] = "No working subreddit"

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        log.error(f"Reddit error: {e}")

    return result


# ---- Pinterest ----
def post_pinterest(driver: webdriver.Chrome) -> dict:
    result = {"platform": "Pinterest", "status": "pending", "url": None, "error": None}
    log.info("=" * 50); log.info("POSTING TO PINTEREST"); log.info("=" * 50)

    try:
        if not safe_get(driver, "https://www.pinterest.com/pin/create/"):
            raise Exception("Cannot load Pinterest")

        human_delay(2, 4)

        try:
            title_input = wait_for_element(
                driver, By.CSS_SELECTOR, "input[data-test-id='pin-title']", timeout=8
            )
            human_type(driver, title_input, "Western Sichuan Camping: The Ultimate 7-Day Overland Route")
            log.info("[OK] Title filled")
        except Exception:
            log.warning("Title input not found")

        human_delay(1, 2)

        try:
            desc_input = wait_for_element(
                driver, By.CSS_SELECTOR, "textarea[data-test-id='pin-description']", timeout=8
            )
            desc = (
                "Complete guide to a 7-day overland camping route through Western Sichuan, China. "
                "Tagong Grassland, Yajiang, high-altitude driving tips. Full guide → https://chinaboundtravel.com\n\n"
                "#ChinaTravel #Sichuan #Camping #OverlandAdventure"
            )
            human_type(driver, desc_input, desc)
            log.info("[OK] Description filled")
        except Exception:
            log.warning("Description input not found")

        human_delay(1, 2)

        try:
            wait_and_click(driver, By.CSS_SELECTOR, "[data-test-id='board-dropdown-select']", timeout=5)
            human_delay(1, 2)
            board = driver.find_element(By.XPATH, "//div[contains(text(),'China Travel')]")
            board.click()
            log.info("[OK] Board selected")
        except Exception as e:
            log.warning(f"Board select failed: {e}")

        human_delay(1, 2)

        try:
            wait_and_click(driver, By.CSS_SELECTOR, "[data-test-id='board-select-save']", timeout=5)
            log.info("[OK] Pin saved")
        except Exception:
            log.warning("Save button not found")

        human_delay(2, 4)
        result["status"] = "success"
        result["url"] = driver.current_url
        log.info(f"[SUCCESS] {driver.current_url}")

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        log.error(f"Pinterest error: {e}")

    return result


# ---- Quora ----
def post_quora(driver: webdriver.Chrome) -> dict:
    result = {"platform": "Quora", "status": "pending", "url": None, "error": None}
    log.info("=" * 50); log.info("POSTING TO QUORA"); log.info("=" * 50)

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

            try:
                search_box = wait_for_element(
                    driver, By.CSS_SELECTOR, "input[type='search']", timeout=8
                )
                human_type(driver, search_box, question)
                search_box.send_keys(Keys.ENTER)
                log.info(f"[OK] Searched: {question}")
                human_delay(2, 4)
            except Exception:
                log.warning("Search box not found")
                continue

            answer_triggered = False
            try:
                wait_and_click(
                    driver, By.CSS_SELECTOR, "[data-testid='AnswerComposer']", timeout=6
                )
                answer_triggered = True
            except Exception:
                try:
                    btns = driver.find_elements(By.XPATH, "//span[contains(text(),'Answer')]")
                    if btns:
                        btns[0].click()
                        answer_triggered = True
                    else:
                        human_delay(2, 3)
                        continue
                except Exception:
                    human_delay(2, 3)
                    continue

            if not answer_triggered:
                continue

            human_delay(2, 3)

            try:
                answer_box = wait_for_element(
                    driver, By.CSS_SELECTOR, "[data-testid='RichTextTextarea']", timeout=8
                )
                answer_text = (
                    "Just finished a 7-day overland camping trip through Western Sichuan:\n\n"
                    "Route: Chengdu → Kangding → Tagong Grassland → Yajiang → Danba → ...\n\n"
                    "Key tips:\n"
                    "✅ May–October is best\n"
                    "✅ Rent a 4WD in Chengdu (essential)\n"
                    "✅ Altitude 3000m+ — bring layers + Diamox\n"
                    "✅ Carry 500 RMB cash + activate Alipay before leaving cities\n"
                    "✅ Tagong Grassland has the best campsites\n\n"
                    "Full day-by-day breakdown on my blog: https://chinaboundtravel.com\n\n"
                    "Happy to answer questions!"
                )
                human_type(driver, answer_box, answer_text)
                log.info("[OK] Answer filled")
                human_delay(1, 2)
            except Exception as e:
                log.warning(f"Answer box not found: {e}")
                continue

            try:
                wait_and_click(driver, By.CSS_SELECTOR, "button[type='submit']", timeout=5)
                log.info("[OK] Submit clicked")
                human_delay(2, 4)
            except Exception:
                log.warning("Submit button not found")

            if "quora.com" in driver.current_url:
                result["status"] = "success"
                result["url"] = driver.current_url
                log.info(f"[SUCCESS] {driver.current_url}")
                return result

        result["status"] = "failed"
        result["error"] = "No suitable question found"

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        log.error(f"Quora error: {e}")

    return result


# ---- Medium ----
def post_medium(driver: webdriver.Chrome) -> dict:
    result = {"platform": "Medium", "status": "pending", "url": None, "error": None}
    log.info("=" * 50); log.info("POSTING TO MEDIUM"); log.info("=" * 50)

    try:
        if not safe_get(driver, "https://medium.com/new-story"):
            raise Exception("Cannot load Medium")

        human_delay(2, 3)

        try:
            title_input = wait_for_element(
                driver, By.CSS_SELECTOR, "h1[data-hj-suppress]", timeout=10
            )
        except Exception:
            title_input = wait_for_element(
                driver, By.XPATH, "//h1[contains(@class,'Title')]", timeout=10
            )

        human_type(driver, title_input, TITLE)
        log.info(f"[OK] Title filled")
        human_delay(1, 2)

        try:
            body_input = wait_for_element(
                driver, By.XPATH, "//div[@data-slate-editor='true']", timeout=8
            )
        except Exception:
            body_input = wait_for_element(
                driver, By.CSS_SELECTOR, "[data-slate-node='paragraph']", timeout=8
            )

        body_text = (
            "Just completed an epic 7-day overland camping trip through Western Sichuan. "
            "High-altitude mountain passes, Tibetan grasslands, wild yaks, and stars you'll remember forever.\n\n"
            "## The Route\n\n"
            "Chengdu → Kangding → Tagong Grassland → Yajiang → Danba → ...\n\n"
            "## Highlights\n\n"
            "✅ Camping under the stars at Tagong Grassland\n"
            "✅ Driving through 3000m+ mountain passes\n"
            "✅ Authentic Tibetan villages\n"
            "✅ Yaks and wildlife everywhere\n\n"
            "## Practical Tips\n\n"
            "• **Best season:** May to October\n"
            "• **Vehicle:** 4WD essential — rent in Chengdu\n"
            "• **Altitude:** 3000m+ — bring layers, consider Diamox\n"
            "• **Payments:** Alipay works in towns, carry 500 RMB cash\n\n"
            "Full day-by-day breakdown, GPS waypoints, and everything I wish I knew:\n\n"
            "👉 **Full guide:** https://chinaboundtravel.com"
        )
        human_type(driver, body_input, body_text)
        log.info("[OK] Body filled")
        human_delay(1, 2)

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

        try:
            wait_and_click(driver, By.CSS_SELECTOR, "button[data-testid='publishButton']", timeout=5)
            log.info("[OK] Publish clicked")
            human_delay(3, 5)
        except Exception:
            try:
                driver.find_element(By.XPATH, "//button[contains(text(),'Publish')]").click()
                log.info("[OK] Alt Publish clicked")
                human_delay(3, 5)
            except Exception as e:
                log.warning(f"Publish not found: {e}")

        if "medium.com" in driver.current_url:
            result["status"] = "success"
            result["url"] = driver.current_url
            log.info(f"[SUCCESS] {driver.current_url}")
        else:
            result["status"] = "unknown"
            result["url"] = driver.current_url
            log.info(f"[OK] Medium attempted: {driver.current_url}")

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        log.error(f"Medium error: {e}")

    return result


# ---- Instagram (skip — web can't post images) ----
def post_instagram(driver: webdriver.Chrome) -> dict:
    result = {"platform": "Instagram", "status": "skipped", "url": None,
              "error": "Use Facebook Creator Studio for image posts"}
    log.info("[SKIP] Instagram — use Creator Studio")
    return result


# ---- Facebook ----
def post_facebook(driver: webdriver.Chrome) -> dict:
    result = {"platform": "Facebook", "status": "pending", "url": None, "error": None}
    log.info("=" * 50); log.info("POSTING TO FACEBOOK"); log.info("=" * 50)

    try:
        if not safe_get(driver, "https://www.facebook.com/"):
            raise Exception("Cannot load Facebook")

        human_delay(2, 4)

        try:
            post_box = wait_and_click(
                driver, By.CSS_SELECTOR,
                "[data-testid='medias parl compose message input composer']", timeout=8
            )
        except Exception:
            try:
                post_box = driver.find_element(By.XPATH, "//span[contains(text(),'on your mind')]")
                post_box.click()
            except Exception:
                post_box = driver.find_element(By.CSS_SELECTOR, "textarea[aria-label*='mind']")

        human_delay(1, 2)

        fb_content = (
            "🏔️ Just finished an epic 7-day overland camping trip through Western Sichuan, China!\n\n"
            "Chengdu → Kangding → Tagong Grassland → Yajiang — some of the most breathtaking "
            "high-altitude landscapes I've ever seen.\n\n"
            "✅ Camping under the stars at Tagong\n"
            "✅ 3000m+ mountain passes\n"
            "✅ Authentic Tibetan culture\n\n"
            "Full guide → https://chinaboundtravel.com\n\n"
            "#ChinaTravel #Sichuan #OverlandCamping #AdventureTravel"
        )
        human_type(driver, driver.switch_to.active_element, fb_content)
        log.info("[OK] Post filled")
        human_delay(1, 2)

        try:
            driver.find_element(By.XPATH, "//div[@aria-label='Post']").click()
            log.info("[OK] Post clicked")
        except Exception:
            log.warning("Post button not found")

        human_delay(3, 5)
        result["status"] = "success"
        result["url"] = driver.current_url
        log.info(f"[OK] Facebook submitted: {driver.current_url}")

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        log.error(f"Facebook error: {e}")

    return result


# ================================================================
# MAIN
# ================================================================
def main():
    start_time = datetime.now()
    log.info("")
    log.info("=" * 60)
    log.info(" ChinaBound Travel — Six-Platform Auto Poster")
    log.info(f" Mode: {CONNECTION_MODE}")
    log.info(f" Hub/Addr: {HUB_URL if CONNECTION_MODE=='REMOTE' else DEBUG_ADDR}")
    log.info(f" Start: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    log.info("=" * 60)

    driver = None
    results = []

    try:
        driver = build_driver()

        if len(driver.window_handles) > 1:
            for handle in driver.window_handles[1:]:
                driver.switch_to.window(handle)
                driver.close()
            driver.switch_to.window(driver.window_handles[0])
            log.info(f"[OK] Extra tabs closed: {driver.current_url}")

        # Reddit
        r = post_reddit(driver)
        results.append(r)
        log.info(f"Result: {'✅' if r['status']=='success' else '❌'} Reddit — {r['status']} {r['url'] or r['error'] or ''}")
        time.sleep(PLATFORM_DELAY)

        # Pinterest
        p = post_pinterest(driver)
        results.append(p)
        log.info(f"Result: {'✅' if p['status']=='success' else '❌'} Pinterest — {p['status']} {p['url'] or p['error'] or ''}")
        time.sleep(PLATFORM_DELAY)

        # Quora
        q = post_quora(driver)
        results.append(q)
        log.info(f"Result: {'✅' if q['status']=='success' else '❌'} Quora — {q['status']} {q['url'] or q['error'] or ''}")
        time.sleep(PLATFORM_DELAY)

        # Medium
        m = post_medium(driver)
        results.append(m)
        log.info(f"Result: {'✅' if m['status']=='success' else '❌'} Medium — {m['status']} {m['url'] or m['error'] or ''}")
        time.sleep(PLATFORM_DELAY)

        # Instagram
        i = post_instagram(driver)
        results.append(i)
        time.sleep(PLATFORM_DELAY)

        # Facebook
        fb = post_facebook(driver)
        results.append(fb)
        log.info(f"Result: {'✅' if fb['status']=='success' else '❌'} Facebook — {fb['status']} {fb['url'] or fb['error'] or ''}")

    except KeyboardInterrupt:
        log.warning("Interrupted")
    except Exception as e:
        log.error(f"Fatal error: {e}")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    # Summary
    end_time = datetime.now()
    elapsed = (end_time - start_time).total_seconds()
    success = sum(1 for r in results if r["status"] == "success")

    log.info("")
    log.info("=" * 60)
    log.info(" POSTING SUMMARY")
    log.info(f" Time: {elapsed:.0f}s | Success: {success}/{len(results)}")
    log.info("=" * 60)
    for res in results:
        icon = "✅" if res["status"]=="success" else ("⚠️" if res["status"] in ("skipped","unknown") else "❌")
        err = f" | {res['error']}" if res["error"] else ""
        log.info(f"  {icon} {res['platform']:<12} {res['status']:<10} {res['url'] or ''}{err}")
    log.info("=" * 60)

    return results


if __name__ == "__main__":
    main()
