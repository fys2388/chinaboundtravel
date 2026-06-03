import os
import json
import requests
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

class LemonSqueezyUploader:
    def __init__(self):
        self.api_key = os.getenv("LEMON_SQUEEZY_API_KEY")
        self.store_id = os.getenv("LEMON_SQUEEZY_STORE_ID")
        self.product_id = os.getenv("LEMON_SQUEEZY_PRODUCT_ID")
        self.feishu_webhook = os.getenv("FEISHU_WEBHOOK_URL")
    
    def upload_ebook(self, pdf_path, version):
        if not self.api_key or not self.store_id:
            print("Lemon Squeezy credentials not configured")
            return None
        
        try:
            url = f"https://api.lemonsqueezy.com/v1/files"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            body = {
                "data": {
                    "type": "files",
                    "attributes": {
                        "name": f"ChinaBound Travel Guide {version}.pdf",
                        "description": f"Monthly travel guide {version}",
                        "size": os.path.getsize(pdf_path),
                        "content_type": "application/pdf"
                    },
                    "relationships": {
                        "store": {
                            "data": {
                                "type": "stores",
                                "id": self.store_id
                            }
                        }
                    }
                }
            }
            
            response = requests.post(url, headers=headers, json=body, timeout=30)
            if response.status_code == 201:
                upload_url = response.json()["data"]["attributes"]["upload_url"]
                
                with open(pdf_path, "rb") as f:
                    upload_response = requests.put(upload_url, data=f, timeout=120)
                
                if upload_response.status_code == 200:
                    file_id = response.json()["data"]["id"]
                    return self._create_variant(file_id, version)
                else:
                    print(f"File upload failed: {upload_response.text}")
                    return None
            else:
                print(f"Lemon Squeezy API error: {response.text}")
                return None
        except Exception as e:
            print(f"Upload error: {e}")
            return None
    
    def _create_variant(self, file_id, version):
        try:
            url = f"https://api.lemonsqueezy.com/v1/variants"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            body = {
                "data": {
                    "type": "variants",
                    "attributes": {
                        "name": f"ChinaBound Travel Guide {version}",
                        "description": f"The complete travel guide for visiting China - {version} edition",
                        "price": 14.99,
                        "is_pay_what_you_want": False,
                        "is_available": True,
                        "requires_shipping": False,
                        "taxable": True
                    },
                    "relationships": {
                        "product": {
                            "data": {
                                "type": "products",
                                "id": self.product_id
                            }
                        },
                        "files": {
                            "data": [{
                                "type": "files",
                                "id": file_id
                            }]
                        }
                    }
                }
            }
            
            response = requests.post(url, headers=headers, json=body, timeout=30)
            if response.status_code == 201:
                variant = response.json()["data"]
                return {
                    "id": variant["id"],
                    "name": variant["attributes"]["name"],
                    "url": variant["attributes"]["url"]
                }
            else:
                print(f"Variant creation error: {response.text}")
                return None
        except Exception as e:
            print(f"Variant creation error: {e}")
            return None
    
    def send_feishu_notification(self, result):
        if not self.feishu_webhook:
            return
        
        if result:
            content = f"## 📚 电子书上架成功\n\n"
            content += f"- **版本**: {result['name']}\n"
            content += f"- **购买链接**: {result['url']}\n"
        else:
            content = "## ⚠️ 电子书上架失败"
        
        try:
            payload = {
                "msg_type": "post",
                "content": {
                    "post": {
                        "zh_cn": {
                            "title": "电子书上架通知",
                            "content": [[{"tag": "text", "text": content}]]
                        }
                    }
                }
            }
            requests.post(self.feishu_webhook, json=payload, timeout=30)
        except Exception:
            pass
    
    def run(self, pdf_path, version):
        result = self.upload_ebook(pdf_path, version)
        self.send_feishu_notification(result)
        return result

if __name__ == "__main__":
    uploader = LemonSqueezyUploader()
    version = datetime.now().strftime("%Y.%m")
    pdf_path = BASE_DIR / "static" / "downloads" / f"chinabound-travel-guide-{version.replace('.', '-')}.pdf"
    uploader.run(str(pdf_path), version)