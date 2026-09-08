#!/usr/bin/env python3
"""GSC diagnostic: check credentials, site access, sitemap status."""
import json
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

BLOG_ROOT = Path(__file__).resolve().parent.parent
KEY_FILE = BLOG_ROOT / "gsc-service-account-key.json"
SITE_URL = "https://www.chinaboundtravel.com/"
SITEMAP_PATH = "https://www.chinaboundtravel.com/sitemap.xml"
SCOPE = "https://www.googleapis.com/auth/webmasters"

print("=" * 60)
print("  GSC Diagnostic Report")
print("=" * 60)

# 1. Load key
print("\n[1] Service Account Key")
if not KEY_FILE.exists():
    print(f"  FAIL: key file not found: {KEY_FILE}")
    sys.exit(1)
try:
    key_data = json.loads(KEY_FILE.read_text(encoding="utf-8"))
    client_email = key_data.get("client_email", "N/A")
    project_id = key_data.get("project_id", "N/A")
    print(f"  client_email: {client_email}")
    print(f"  project_id:   {project_id}")
    print(f"  key type:     {key_data.get('type', 'N/A')}")
except Exception as e:
    print(f"  FAIL: cannot parse key: {e}")
    sys.exit(1)

# 2. Build credentials
print("\n[2] Credential Build & Refresh")
try:
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
    credentials = service_account.Credentials.from_service_account_info(
        key_data, scopes=[SCOPE]
    )
    credentials.refresh(Request())
    print(f"  token valid: {credentials.valid}")
    print(f"  token length: {len(credentials.token) if credentials.token else 0}")
except Exception as e:
    print(f"  FAIL: {e}")
    sys.exit(1)

# 3. Build service
print("\n[3] GSC Service Build")
try:
    from googleapiclient.discovery import build
    service = build("searchconsole", "v1", credentials=credentials, cache_discovery=False)
    print("  OK: searchconsole v1 service built")
except Exception as e:
    print(f"  FAIL: {e}")
    sys.exit(1)

# 4. List all accessible sites
print("\n[4] Accessible Sites (sites().list)")
try:
    sites_resp = service.sites().list().execute()
    site_entries = sites_resp.get("siteEntry", [])
    print(f"  total accessible sites: {len(site_entries)}")
    for entry in site_entries:
        print(f"    - {entry.get('siteUrl')}  [permissionLevel={entry.get('permissionLevel')}]")
except Exception as e:
    print(f"  FAIL: {e}")
    if hasattr(e, 'content'):
        try:
            err = json.loads(e.content)
            print(f"  error details: {json.dumps(err, indent=2)}")
        except:
            print(f"  raw content: {e.content}")
    site_entries = []

# 5. Check target site access
print("\n[5] Target Site Access Check")
target_found = False
target_permission = None
for entry in site_entries:
    url = entry.get("siteUrl", "")
    if url.rstrip("/") == SITE_URL.rstrip("/") or url == f"sc-domain:chinaboundtravel.com":
        target_found = True
        target_permission = entry.get("permissionLevel")
        print(f"  FOUND: {url}  permissionLevel={target_permission}")

if not target_found:
    print(f"  NOT FOUND: {SITE_URL} is not in the service account's accessible sites")
    print(f"  sc-domain:chinaboundtravel.com also not found")

# 6. Try sites().get() for target
print("\n[6] Direct sites().get() for target")
try:
    get_resp = service.sites().get(siteUrl=SITE_URL).execute()
    print(f"  OK: {json.dumps(get_resp, indent=2)}")
    target_found = True
except Exception as e:
    print(f"  FAIL: {e}")
    if hasattr(e, 'content'):
        try:
            err = json.loads(e.content)
            print(f"  error: {err.get('error', {}).get('message', str(e))}")
            print(f"  status: {err.get('error', {}).get('status', '')}")
        except:
            pass

# 7. Sitemap status
print("\n[7] Sitemap List Status")
if target_found:
    try:
        sm_resp = service.sitemaps().list(siteUrl=SITE_URL).execute()
        sitemaps = sm_resp.get("sitemap", [])
        print(f"  total submitted sitemaps: {len(sitemaps)}")
        for sm in sitemaps:
            print(f"    - path: {sm.get('path')}")
            print(f"      status: {sm.get('status')}")
            print(f"      lastSubmitted: {sm.get('lastSubmitted')}")
            contents = sm.get("contents", [])
            for c in contents:
                print(f"      type={c.get('type')} submitted={c.get('submitted')} indexed={c.get('indexed')}")
    except Exception as e:
        print(f"  FAIL: {e}")
        if hasattr(e, 'content'):
            try:
                err = json.loads(e.content)
                print(f"  error: {err.get('error', {}).get('message', str(e))}")
            except:
                pass
else:
    print("  SKIP: target site not accessible, cannot query sitemap")

# 8. Attempt sitemap submission
print("\n[8] Sitemap Submission Attempt")
if target_found:
    try:
        submit_resp = service.sitemaps().submit(
            siteUrl=SITE_URL,
            feedpath=SITEMAP_PATH
        ).execute()
        print(f"  SUBMIT OK: {json.dumps(submit_resp, indent=2) if submit_resp else '(empty response - success)'}")
    except Exception as e:
        print(f"  SUBMIT FAIL: {e}")
        if hasattr(e, 'content'):
            try:
                err = json.loads(e.content)
                print(f"  error: {err.get('error', {}).get('message', str(e))}")
                print(f"  status: {err.get('error', {}).get('status', '')}")
            except:
                pass
else:
    print("  SKIP: target site not accessible, cannot submit sitemap")

print("\n" + "=" * 60)
print("  Diagnostic Complete")
print("=" * 60)
print(f"\nSUMMARY:")
print(f"  service_account_email: {client_email}")
print(f"  target_site_accessible: {target_found}")
print(f"  target_permission: {target_permission or 'N/A'}")
