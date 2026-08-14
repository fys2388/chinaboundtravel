import os
import sys
import json
import requests
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR / "scripts"))

from gsc_utils import (
    DEFAULT_SITE_URL,
    SCOPE_WEBMASTERS_READONLY,
    build_credentials,
    describe_error,
    get_site_url,
)


class GSCKeywordFetcher:
    """Fetch Search Console keyword data with a service-account credential.

    The Search Console API requires an OAuth2 token with the webmasters scope;
    a raw Google Cloud API key is never accepted (this was the root cause of
    "insufficient authentication scopes").
    """

    def __init__(self, site_url=None, credentials=None):
        self.credentials = credentials
        self.site_url = site_url or get_site_url()
        self.manifest_path = BASE_DIR / "manifest.json"

    def _get_credentials(self):
        if self.credentials is not None:
            return self.credentials
        self.credentials = build_credentials(scopes=[SCOPE_WEBMASTERS_READONLY])
        if self.credentials is None:
            print("GSC service-account credentials not configured")
        return self.credentials

    def fetch_keywords(self, days=30):
        credentials = self._get_credentials()
        if credentials is None:
            return []
        if not credentials.valid:
            try:
                from google.auth.transport.requests import Request
                credentials.refresh(Request())
            except Exception as e:
                print(f"GSC token refresh error: {e}")
                return []

        try:
            url = f"https://www.googleapis.com/webmasters/v3/sites/{self.site_url}/searchAnalytics/query"
            headers = {
                "Authorization": f"Bearer {credentials.token}",
                "Content-Type": "application/json"
            }

            start_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
            end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

            body = {
                "startDate": start_date,
                "endDate": end_date,
                "dimensions": ["query"],
                "rowLimit": 500,
                "startRow": 0
            }

            response = requests.post(url, headers=headers, json=body, timeout=30)
            if response.status_code == 200:
                return response.json().get("rows", [])
            else:
                info = describe_error(_FakeError(response))
                print(f"GSC API error [{info['code']}]: {info['message']} {info['hint']}".strip())
                return []
        except Exception as e:
            print(f"GSC fetch error: {e}")
            return []


class _FakeError:
    """Minimal stand-in so describe_error() works for requests responses."""

    def __init__(self, response):
        self.response = response

    @property
    def content(self):
        return self.response.content
    
    def analyze_high_potential_keywords(self):
        rows = self.fetch_keywords()
        if not rows:
            return []
        
        high_potential = []
        
        for row in rows:
            query = row["keys"][0]
            clicks = row.get("clicks", 0)
            impressions = row.get("impressions", 0)
            ctr = row.get("ctr", 0) * 100
            
            if impressions > 100 and ctr < 3:
                high_potential.append({
                    "keyword": query,
                    "impressions": impressions,
                    "clicks": clicks,
                    "ctr": round(ctr, 2),
                    "potential": "high"
                })
        
        return sorted(high_potential, key=lambda x: x["impressions"], reverse=True)
    
    def fetch_affiliate_conversion_keywords(self):
        keywords = []
        
        try:
            tripcom_api_key = os.getenv("TRIPCOM_API_KEY")
            if tripcom_api_key:
                response = requests.get(
                    "https://api.trip.com/affiliate/reports/conversions",
                    headers={"Authorization": f"Bearer {tripcom_api_key}"},
                    timeout=30
                )
                if response.status_code == 200:
                    data = response.json()
                    for item in data.get("conversions", []):
                        keywords.append({
                            "keyword": item.get("referrer_keyword", ""),
                            "conversions": item.get("conversion_count", 0),
                            "revenue": item.get("revenue", 0),
                            "potential": "high"
                        })
        except Exception as e:
            print(f"Affiliate API error: {e}")
        
        return keywords
    
    def update_manifest_with_keywords(self):
        high_potential = self.analyze_high_potential_keywords()
        affiliate_keywords = self.fetch_affiliate_conversion_keywords()
        
        all_keywords = {}
        
        for kw in high_potential:
            all_keywords[kw["keyword"]] = {
                "gsc_impressions": kw["impressions"],
                "gsc_clicks": kw["clicks"],
                "gsc_ctr": kw["ctr"],
                "conversion_rate": 0,
                "potential": "high"
            }
        
        for kw in affiliate_keywords:
            if kw["keyword"] in all_keywords:
                all_keywords[kw["keyword"]]["conversion_rate"] = kw.get("revenue", 0)
            else:
                all_keywords[kw["keyword"]] = {
                    "gsc_impressions": 0,
                    "gsc_clicks": 0,
                    "gsc_ctr": 0,
                    "conversion_rate": kw.get("revenue", 0),
                    "potential": "high"
                }
        
        if os.path.exists(self.manifest_path):
            with open(self.manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        else:
            manifest = {}
        
        manifest["high_potential_keywords"] = all_keywords
        manifest["last_keyword_update"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        
        print(f"Updated {len(all_keywords)} high potential keywords")
        return all_keywords
    
    def run(self):
        return self.update_manifest_with_keywords()

if __name__ == "__main__":
    fetcher = GSCKeywordFetcher()
    fetcher.run()