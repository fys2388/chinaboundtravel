#!/usr/bin/env python3
"""Read-only GSC access verification.

Checks that the configured service-account credentials can see the configured
Search Console property.  Never writes anything and never prints credentials.

Usage:
    python scripts/verify_gsc_access.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gsc_utils import build_credentials, get_site_url, verify_site_access


def main():
    site_url = get_site_url()
    print(f"Checking property: {site_url}")
    credentials = build_credentials()
    if credentials is None:
        print("FAIL: service-account credentials not found (key file or GSC_SERVICE_ACCOUNT_JSON).")
        return 1
    if verify_site_access(credentials, site_url):
        print("OK: service account can access the property.")
        return 0
    print("FAIL: service account cannot access the property.")
    print("  - confirm the property URL matches Search Console exactly (GSC_SITE_URL)")
    print("  - add the service-account email as a user (Full) in Search Console")
    return 1


if __name__ == "__main__":
    sys.exit(main())
