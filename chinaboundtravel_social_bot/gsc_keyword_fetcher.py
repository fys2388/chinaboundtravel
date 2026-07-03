import os
import json
import requests
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

class GSCKeywordFetcher:
    def __init__(self):
        self.gsc_api_key = os.getenv("GSC_API_KEY")
        self.site_url = "https://chinaboundtravel.com"
        self.manifest_path = BASE_DIR / "manifest.json"
    
    def fetch_keywords(self):
        if not self.gsc_api_key:
            print("GSC API key not configured")
            return []
        
        try:
            url = f"https://www.googleapis.com/webmasters/v3/sites/{self.site_url}/searchAnalytics/query"
            headers = {
                "Authorization": f"Bearer {self.gsc_api_key}",
                "Content-Type": "application/json"
            }
            
            start_date = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
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
                print(f"GSC API error: {response.text}")
                return []
        except Exception as e:
            print(f"GSC fetch error: {e}")
            return []
    
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