﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿import subprocess
import time
import json
import os
import httplib2
from typing import List, Dict

try:
    import google.auth
    from google.auth import impersonated_credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("Installing required packages...")
    subprocess.run(["pip", "install", "google-api-python-client", "google-auth"], check=True)
    import google.auth
    from google.auth import impersonated_credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY_FILE = os.path.join(PROJECT_ROOT, "gsc-service-account-key.json")
SITE_URL = "https://chinaboundtravel.com"
SITEMAP_URL = f"https://www.chinaboundtravel.com/sitemap.xml"

CORE_PAGES = [
    SITE_URL,
    f"{SITE_URL}/posts/",
    f"{SITE_URL}/posts/144-hour-visa-free-transit-guide/",
    f"{SITE_URL}/posts/alipay-wechat-pay-foreigners-guide/",
    f"{SITE_URL}/posts/internet-connection-china-esim-vpn-guide/",
    f"{SITE_URL}/posts/2026-06-02-ultimate-guide-to-china-visa-for-tourists/",
    f"{SITE_URL}/posts/2026-05-26-7-day-china-itinerary-beijing-xian-shanghai-first-timers/",
    f"{SITE_URL}/posts/2026-05-26-is-china-safe-for-tourists-2026-honest-assessment/",
    f"{SITE_URL}/cities/beijing/",
    f"{SITE_URL}/cities/shanghai/",
    f"{SITE_URL}/cities/chengdu/",
    f"{SITE_URL}/cities/xian/",
    f"{SITE_URL}/cities/hangzhou/",
]


def build_site():
    print("\n=== 1. 构建站点 ===")
    result = subprocess.run(
        ["hugo", "--gc", "--minify"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='ignore'
    )
    if result.returncode == 0:
        print("站点构建成功")
        return True
    else:
        print(f"构建失败: {result.stderr}")
        return False


def commit_and_push():
    print("\n=== 2. 提交代码 ===")
    subprocess.run(["git", "add", ".", "--", "--exclude=gsc-service-account-key.json"], cwd=PROJECT_ROOT, capture_output=True)
    
    result = subprocess.run(
        ["git", "commit", "-m", "Auto rebuild and deploy via GSC API"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='ignore'
    )
    
    if "nothing to commit" in result.stdout:
        print("没有新的更改")
    elif result.returncode == 0:
        print("提交成功")
    else:
        print(f"提交失败: {result.stderr}")
    
    result = subprocess.run(
        ["git", "push", "origin", "main"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='ignore'
    )
    if result.returncode == 0:
        print("推送成功")
        return True
    else:
        print(f"推送失败: {result.stderr}")
        return False


def get_gsc_service():
    print("\n=== 3. 连接GSC API ===")
    if not os.path.exists(KEY_FILE):
        print(f"密钥文件不存在: {KEY_FILE}")
        print("请将Google Cloud服务账号密钥文件保存为 gsc-service-account-key.json")
        return None
    
    try:
        credentials, _ = google.auth.load_credentials_from_file(
            KEY_FILE,
            scopes=["https://www.googleapis.com/auth/webmasters"]
        )
        
        # 使用httplib2显式处理HTTP请求
        http = httplib2.Http(timeout=60)
        credentials.refresh(http.request)
        http = credentials.authorize(http)
        
        service = build("searchconsole", "v1", http=http, credentials=credentials)
        print("GSC API连接成功")
        return service
    except Exception as e:
        print(f"连接失败: {str(e)}")
        return None


def submit_sitemap(service):
    print("\n=== 4. 提交Sitemap ===")
    try:
        response = service.sitemaps().submit(
            siteUrl=SITE_URL,
            feedpath=SITEMAP_URL
        ).execute()
        print(f"Sitemap提交成功: {response}")
        return True
    except HttpError as e:
        error = json.loads(e.content)
        print(f"提交失败: {error.get('error', {}).get('message', str(e))}")
        return False


def get_sitemap_status(service):
    print("\n=== 5. 获取Sitemap状态 ===")
    try:
        response = service.sitemaps().list(siteUrl=SITE_URL).execute()
        sitemaps = response.get("sitemap", [])
        if sitemaps:
            for sm in sitemaps:
                status = sm.get("status", "unknown")
                count = sm.get("contents", [{}])[0].get("count", 0)
                print(f"  - {sm.get('path')}: {status} ({count} URLs)")
        else:
            print("  没有已提交的sitemap")
    except Exception as e:
        print(f"获取状态失败: {str(e)}")


def request_index(service, urls: List[str]):
    print(f"\n=== 6. 请求索引 ({len(urls)} 个页面) ===")
    success_count = 0
    
    for url in urls:
        try:
            response = service.urlInspection().index().inspect(
                body={"inspectionUrl": url, "siteUrl": SITE_URL}
            ).execute()
            
            status = response.get("indexResult", {}).get("verdict", "unknown")
            print(f"  - {url.split('/')[-2] if '/' in url else 'home'}: {status}")
            
            if status == "PASS":
                success_count += 1
            
            time.sleep(1)
            
        except HttpError as e:
            error = json.loads(e.content)
            message = error.get("error", {}).get("message", str(e))
            print(f"  - {url.split('/')[-2] if '/' in url else 'home'}: {message}")
        except Exception as e:
            print(f"  - {url.split('/')[-2] if '/' in url else 'home'}: {str(e)}")
    
    print(f"\n成功请求 {success_count}/{len(urls)} 个页面索引")
    return success_count


def main():
    print("=" * 60)
    print("  ChinaBoundTravel GSC自动化脚本")
    print("=" * 60)
    
    build_success = build_site()
    if not build_success:
        return
    
    push_success = commit_and_push()
    if not push_success:
        return
    
    print("\n等待Cloudflare部署完成...")
    time.sleep(60)
    
    service = get_gsc_service()
    if not service:
        return
    
    submit_sitemap(service)
    get_sitemap_status(service)
    request_index(service, CORE_PAGES)
    
    print("\n" + "=" * 60)
    print("  自动化任务完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
