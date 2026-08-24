#!/usr/bin/env python3
"""gsc_index_submit.py - Submit ChinaBound Travel pages for indexing.

Inspects core pages / sitemap URLs in Google Search Console and requests
re-indexing through the Indexing API.

Unified with scripts/gsc_utils.py:
  - credential loading    -> gsc_utils.load_service_account_info()
  - credential creation   -> gsc_utils.build_credentials()
  - property URL          -> gsc_utils.get_site_url() / normalize_site_url()
  - OAuth scopes          -> webmasters.readonly (inspect) + indexing (publish)
  - error classification  -> gsc_utils.describe_error()

Notes:
  - The Indexing API (urlNotifications:publish) requires the dedicated
    "https://www.googleapis.com/auth/indexing" scope AND the service account
    must be authorized for the Indexing API in the Google Cloud console.
  - The Search Console urlInspection endpoint only needs webmasters.readonly.
  - Never run against production without a configured service-account key.
"""

import json
import os
import sys
import time
from pathlib import Path

import requests
from xml.etree import ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from gsc_utils import (
    SCOPE_INDEXING,
    SCOPE_WEBMASTERS_READONLY,
    build_credentials,
    describe_error,
    get_site_url,
    load_service_account_info,
    normalize_site_url,
)

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

SCRIPT_DIR = Path(__file__).resolve().parent
BLOG_ROOT = SCRIPT_DIR.parent
REPORTS_DIR = BLOG_ROOT / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
GSC_REPORT_FILE = REPORTS_DIR / "gsc_index_report.json"

SITE_URL = get_site_url()

CORE_PAGES = [
    SITE_URL,
    f"{SITE_URL}posts/",
    f"{SITE_URL}about/",
    f"{SITE_URL}visa/",
    f"{SITE_URL}payments/",
    f"{SITE_URL}internet/",
    f"{SITE_URL}cities/",
]

URL_INSPECT_ENDPOINT = "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"
INDEXING_ENDPOINT = "https://indexing.googleapis.com/v3/urlNotifications:publish"


class _ApiError:
    """Adapter that lets gsc_utils.describe_error classify requests responses."""

    def __init__(self, content, message):
        self.content = content
        self.message = message

    def __str__(self):
        return self.message


def classify_api_error(response_or_exc):
    """Classify an API failure using the shared gsc_utils.describe_error()."""
    if isinstance(response_or_exc, requests.Response):
        return describe_error(
            _ApiError(response_or_exc.content, f"HTTP {response_or_exc.status_code}")
        )
    return describe_error(response_or_exc)


class GSCIndexSubmitter:
    """Inspect and request indexing without making any site changes."""

    def __init__(self, site_url=None):
        self.site_url = normalize_site_url(site_url) if site_url is not None else get_site_url()
        self._service_account_info = None

    # -- credentials (unified via gsc_utils) ---------------------------------

    def _load_key(self):
        if self._service_account_info is None:
            self._service_account_info = load_service_account_info()
        return self._service_account_info

    def _credentials(self, scopes):
        info = self._load_key()
        if not info:
            return None
        return build_credentials(info, scopes=scopes)

    def _inspect_credentials(self):
        return self._credentials([SCOPE_WEBMASTERS_READONLY])

    def _publish_credentials(self):
        return self._credentials([SCOPE_INDEXING])

    def _auth_headers(self, credentials):
        try:
            from google.auth.transport.requests import Request
            credentials.refresh(Request())
        except Exception:
            pass
        return {"Authorization": f"Bearer {credentials.token}"}

    # -- sitemap -------------------------------------------------------------

    def _fetch_sitemap_urls(self, limit=50):
        sitemap_url = self.site_url.rstrip("/") + "/sitemap.xml"
        try:
            response = requests.get(sitemap_url, timeout=30)
            if response.status_code != 200:
                print(f"  Unable to fetch sitemap: HTTP {response.status_code}")
                return []
            root = ET.fromstring(response.content)
            ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            urls = []
            for url in root.findall(".//sm:url", ns):
                loc = url.find("sm:loc", ns)
                if loc is not None and loc.text:
                    urls.append(loc.text.strip())
            print(f"  Fetched {len(urls)} URLs from sitemap")
            return urls[:limit]
        except Exception as exc:
            print(f"  Failed to parse sitemap: {exc}")
            return []

    # -- API calls (never executed in tests) ---------------------------------

    def _inspect_url(self, credentials, url):
        headers = self._auth_headers(credentials)
        payload = {"inspectionUrl": url, "siteUrl": self.site_url}
        try:
            response = requests.post(URL_INSPECT_ENDPOINT, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                verdict = response.json().get("indexResult", {}).get("verdict", "unknown")
                return {"url": url, "verdict": verdict, "status": "success"}
            info = classify_api_error(response)
            return {"url": url, "verdict": f"error: {info['code']} - {info['message'][:160]}",
                    "status": "error"}
        except Exception as exc:
            return {"url": url, "verdict": f"exception: {exc}", "status": "error"}

    def _request_indexing(self, credentials, url):
        headers = self._auth_headers(credentials)
        payload = {"url": url, "type": "URL_UPDATED"}
        try:
            response = requests.post(INDEXING_ENDPOINT, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                return {"url": url, "status": "success", "message": "indexing request submitted"}
            info = classify_api_error(response)
            return {"url": url, "status": "error", "message": f"{info['code']}: {info['message'][:160]}"}
        except Exception as exc:
            return {"url": url, "status": "error", "message": str(exc)}

    # -- workflows -----------------------------------------------------------

    def submit_core_pages(self):
        print("Submitting core pages for indexing...")
        credentials = self._publish_credentials()
        if not credentials:
            self._print_manual_guide()
            return {"status": "unauthorized", "indexed_count": 0, "submitted_count": 0, "urls": []}

        results = []
        submitted_count = 0
        print(f"\nSubmitting core pages ({len(CORE_PAGES)})")
        for url in CORE_PAGES:
            print(f"  - {url}")
            result = self._request_indexing(credentials, url)
            results.append(result)
            if result["status"] == "success":
                submitted_count += 1
            time.sleep(1)

        inspect_credentials = self._inspect_credentials()
        indexed_count = 0
        print("\nChecking index status...")
        for url in CORE_PAGES:
            result = self._inspect_url(inspect_credentials, url)
            print(f"  - {url}: {result['verdict']}")
            if result["verdict"] == "PASS":
                indexed_count += 1

        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "site_url": self.site_url,
            "status": "success",
            "indexed_count": indexed_count,
            "submitted_count": submitted_count,
            "total_core_pages": len(CORE_PAGES),
            "results": results,
        }
        self._save_report(report)
        return report

    def submit_optimized_pages(self, urls=None, limit=None):
        """批量提交本次深度优化的核心文章重新索引。

        urls: 待提交 URL 列表；缺省时从 reports/content_deep_optimize_report.json
              提取优化文章，并按 canonicalURL / slug 组装 URL。
        """
        if urls is None:
            urls = self._optimized_page_urls()
        if not urls:
            return {"status": "no_urls", "submitted_count": 0, "urls": []}
        if limit:
            urls = urls[:limit]

        credentials = self._publish_credentials()
        if not credentials:
            return {"status": "unauthorized", "submitted_count": 0, "urls": []}

        results = []
        submitted_count = 0
        print(f"\nSubmitting optimized pages ({len(urls)})")
        for url in urls:
            print(f"  - {url}")
            result = self._request_indexing(credentials, url)
            results.append(result)
            if result["status"] == "success":
                submitted_count += 1
            time.sleep(0.7)

        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "site_url": self.site_url,
            "status": "success",
            "submitted_count": submitted_count,
            "total_urls": len(urls),
            "results": results,
        }
        self._save_report(report)
        return report

    def _optimized_page_urls(self):
        """从优化报告构建待提交 URL 列表。"""
        import json as _json
        opt_report = BLOG_ROOT / "reports" / "content_deep_optimize_report.json"
        base = self.site_url.rstrip("/")
        urls = []
        if opt_report.exists():
            try:
                data = _json.loads(opt_report.read_text(encoding="utf-8"))
                for r in data.get("results", []):
                    slug = r.get("file", "").replace(".md", "")
                    urls.append(f"{base}/posts/{slug}/")
            except Exception:
                pass
        return urls

    def submit_sitemap_pages(self, limit=20):
        print("\nSubmitting sitemap pages for indexing...")
        credentials = self._publish_credentials()
        if not credentials:
            return {"status": "unauthorized", "indexed_count": 0, "submitted_count": 0, "urls": []}

        urls = self._fetch_sitemap_urls()
        if not urls:
            return {"status": "no_sitemap", "indexed_count": 0, "submitted_count": 0, "urls": []}

        urls_to_submit = urls[:limit]
        results = []
        submitted_count = 0
        print(f"\nSubmitting sitemap pages ({len(urls_to_submit)})")
        for url in urls_to_submit:
            print(f"  - {url}")
            result = self._request_indexing(credentials, url)
            results.append(result)
            if result["status"] == "success":
                submitted_count += 1
            time.sleep(0.5)

        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "site_url": self.site_url,
            "status": "success",
            "indexed_count": 0,
            "submitted_count": submitted_count,
            "total_sitemap_urls": len(urls),
            "submitted_urls": len(urls_to_submit),
            "results": results,
        }
        self._save_report(report)
        return report

    def _save_report(self, report):
        try:
            with open(GSC_REPORT_FILE, "w", encoding="utf-8") as fh:
                json.dump(report, fh, indent=2, ensure_ascii=False)
            print(f"  GSC index report saved: {GSC_REPORT_FILE}")
        except Exception as exc:
            print(f"  Failed to save report: {exc}")

    def _print_manual_guide(self):
        print("\n" + "=" * 60)
        print("  GSC not authorized - manual setup required")
        print("=" * 60)
        print("""
1. Open Google Search Console and verify the property:
   https://www.chinaboundtravel.com/
2. Submit the sitemap:
   https://www.chinaboundtravel.com/sitemap.xml
3. Add the service-account email as a user (Full) for the property.
4. For the Indexing API, enable it in Google Cloud and authorize the
   service account, then set GSC_SERVICE_ACCOUNT_JSON in the environment.
""")

    def get_index_status(self):
        if GSC_REPORT_FILE.exists():
            try:
                with open(GSC_REPORT_FILE, "r", encoding="utf-8") as fh:
                    return json.load(fh)
            except Exception:
                pass
        return {"status": "no_report", "indexed_count": 0, "submitted_count": 0}


def main():
    import argparse
    ap = argparse.ArgumentParser(description="ChinaBound GSC Index Submit")
    ap.add_argument("--optimized", action="store_true",
                    help="仅批量提交本次深度优化的核心文章")
    ap.add_argument("--core", action="store_true", help="提交核心页面 + sitemap")
    ap.add_argument("--all", action="store_true", help="全部执行")
    args = ap.parse_args()

    print("=" * 60)
    print("  ChinaBound Travel - GSC Index Submit")
    print("=" * 60)

    submitter = GSCIndexSubmitter()

    if args.optimized or args.all or not (args.core or args.optimized):
        print("\nStep: submit optimized pages (Top 深度优化文章)")
        submitter.submit_optimized_pages()

    if args.core or args.all:
        print("\nStep 1: submit core pages")
        submitter.submit_core_pages()
        print("\nStep 2: submit sitemap pages")
        submitter.submit_sitemap_pages(limit=20)

    print("\n" + "=" * 60)
    print("  Index submit task finished")
    print("=" * 60)


if __name__ == "__main__":
    main()
