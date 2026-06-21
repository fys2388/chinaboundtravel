from google.oauth2 import service_account
from googleapiclient.discovery import build

KEY_FILE_PATH = r"e:\AI\dulizhan\travel-blog\gsc-service-account-key.json"
SITE_URL = "https://chinaboundtravel.com"
SCOPES = ["https://www.googleapis.com/auth/webmasters"]

try:
    credentials = service_account.Credentials.from_service_account_file(
        KEY_FILE_PATH, scopes=SCOPES
    )
    print("✅ 凭证加载成功")

    service = build("searchconsole", "v1", credentials=credentials)
    print("✅ API服务构建成功")

    response = service.sitemaps().list(siteUrl=SITE_URL).execute()
    print("✅ 调用成功，已提交sitemap:", response)

except Exception as e:
    print("❌ 失败，错误信息:", str(e))