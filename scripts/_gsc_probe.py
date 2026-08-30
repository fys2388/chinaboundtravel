#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Minimal diagnostic: dump raw Indexing API + GSC responses (no site changes)."""
import json
import os
import sys
import requests

sys.stdout.reconfigure(encoding="utf-8")

# ---- load credentials like gsc_utils ----
import pathlib
BLOG_ROOT = pathlib.Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv
    load_dotenv(BLOG_ROOT / ".env")
except Exception:
    pass

info = None
raw = os.environ.get("GSC_SERVICE_ACCOUNT_JSON", "")
if raw:
    try:
        info = json.loads(raw)
    except ValueError:
        p = pathlib.Path(raw)
        if not p.is_absolute():
            p = BLOG_ROOT / raw
        if p.is_file():
            info = json.loads(p.read_text(encoding="utf-8"))
if info is None:
    kf = BLOG_ROOT / "gsc-service-account-key.json"
    if kf.is_file():
        info = json.loads(kf.read_text(encoding="utf-8"))
if not info:
    print("NO_CREDENTIALS")
    sys.exit(1)

from google.oauth2 import service_account
from google.auth.transport.requests import Request

SCOPE_INDEXING = "https://www.googleapis.com/auth/indexing"
creds = service_account.Credentials.from_service_account_info(info, scopes=[SCOPE_INDEXING])
creds.refresh(Request())
headers = {"Authorization": "Bearer " + creds.token, "Content-Type": "application/json"}

# 1) Which properties does the SA see?
from googleapiclient.discovery import build
svc = build("searchconsole", "v1", credentials=service_account.Credentials.from_service_account_info(
    info, scopes=["https://www.googleapis.com/auth/webmasters.readonly"]), cache_discovery=False)
try:
    entries = svc.sites().list().execute().get("siteEntry", [])
    print("VISIBLE_PROPERTIES:")
    for e in entries:
        print("  -", e.get("siteUrl"), "|", e.get("permissionLevel"))
except Exception as e:
    print("SITES_LIST_ERROR:", str(e)[:300])

# 2) Raw Indexing API call for ONE url
test_url = os.environ.get("PROBE_URL", "https://www.chinaboundtravel.com/posts/china-extends-144-hour-visa-free-transit-policy-to-more-countries/")
payload = {"url": test_url, "type": "URL_UPDATED"}
print("\nINDEXING_PUBLISH_CALL:", test_url)
try:
    r = requests.post("https://indexing.googleapis.com/v3/urlNotifications:publish", headers=headers, json=payload, timeout=30)
    print("HTTP_STATUS:", r.status_code)
    print("BODY:", r.text[:800])
except Exception as e:
    print("EXCEPTION:", str(e)[:300])
