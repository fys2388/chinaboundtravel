import sys
sys.stdout.reconfigure(encoding='utf-8')

from google.oauth2 import service_account
from googleapiclient.discovery import build

KEY_FILE_PATH = r"e:\AI\dulizhan\travel-blog\gsc-service-account-key.json"
SITE_URL = "https://chinaboundtravel.com"
SCOPES = ["https://www.googleapis.com/auth/webmasters"]

try:
    credentials = service_account.Credentials.from_service_account_file(
        KEY_FILE_PATH, scopes=SCOPES
    )
    print("OK: Credentials loaded")

    service = build("searchconsole", "v1", credentials=credentials)
    print("OK: Service built")

    response = service.sitemaps().list(siteUrl=SITE_URL).execute()
    print("OK: API call succeeded")
    print("Response:", response)

except Exception as e:
    print("ERROR:", str(e))
