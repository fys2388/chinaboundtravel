#!/usr/bin/env python3
"""Shared GSC authentication helpers for ChinaBound Travel scripts.

Root-cause fixes for "insufficient authentication scopes" errors:

1. The Search Console (webmasters) API requires an OAuth2 token, never a raw
   Google Cloud API key.  Scripts must mint credentials from a service-account
   JSON key (or OAuth client) with an explicit scope.
2. The site property passed to the API must match the Search Console property
   exactly (URL-prefix properties keep their trailing slash, e.g.
   https://www.chinaboundtravel.com/).
3. Service accounts must be added as users in Search Console with at least
   "Full" permission for their property; otherwise the API returns 403.
"""

import json
import os
from pathlib import Path

# Read-only scope is enough for keyword/sitemap/URL-inspection reads.
SCOPE_WEBMASTERS_READONLY = "https://www.googleapis.com/auth/webmasters.readonly"
SCOPE_WEBMASTERS = "https://www.googleapis.com/auth/webmasters"
DEFAULT_SCOPES = [SCOPE_WEBMASTERS_READONLY]
# Indexing API (urlNotifications:publish) needs its own dedicated scope,
# and the service account must also be enabled for the Indexing API in
# the Google Cloud console. Inspect-only flows never need this scope.
SCOPE_INDEXING = "https://www.googleapis.com/auth/indexing"

BLOG_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_KEY_FILE = BLOG_ROOT / "gsc-service-account-key.json"

# Canonical site property.  Keep the trailing slash so it matches a
# URL-prefix Search Console property; override with GSC_SITE_URL when the
# property is registered differently (e.g. sc-domain:chinaboundtravel.com).
DEFAULT_SITE_URL = "https://www.chinaboundtravel.com/"


def normalize_site_url(url):
    """Return a GSC property-style site URL (trailing slash for http(s))."""
    url = (url or "").strip()
    if not url:
        return DEFAULT_SITE_URL
    if url.startswith("sc-domain:"):
        return url
    if not url.startswith("http"):
        url = "https://" + url
    if not url.endswith("/"):
        url += "/"
    return url


def get_site_url(env_name="GSC_SITE_URL"):
    return normalize_site_url(os.environ.get(env_name, DEFAULT_SITE_URL))


def load_service_account_info(env_name="GSC_SERVICE_ACCOUNT_JSON", key_file=DEFAULT_KEY_FILE):
    """Load service-account info from env JSON string, env path, or key file.

    Returns a dict or None.  Never logs credential contents.
    """
    raw = os.environ.get(env_name, "")
    if raw:
        raw = raw.strip()
        try:
            return json.loads(raw)
        except ValueError:
            candidate = Path(raw)
            if candidate.is_file():
                try:
                    return json.loads(candidate.read_text(encoding="utf-8"))
                except (ValueError, OSError):
                    return None
            return None
    try:
        if key_file and Path(key_file).is_file():
            return json.loads(Path(key_file).read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    return None


def build_credentials(service_account_info=None, scopes=None):
    """Create google.oauth2 service-account credentials for the webmasters API.

    Returns None when the required libraries or the key are unavailable.
    """
    scopes = scopes or DEFAULT_SCOPES
    try:
        from google.oauth2 import service_account
        info = service_account_info if service_account_info is not None else load_service_account_info()
        if not info:
            return None
        credentials = service_account.Credentials.from_service_account_info(
            info, scopes=scopes
        )
        return credentials
    except Exception:
        return None


def verify_site_access(credentials, site_url):
    """Check whether the credentials can see ``site_url`` in Search Console.

    Returns True/False; never makes assumptions about the console backend.
    """
    if credentials is None:
        return False
    site_url = normalize_site_url(site_url)
    try:
        from googleapiclient.discovery import build
        service = build("searchconsole", "v1", credentials=credentials, cache_discovery=False)
        result = service.sites().list().execute()
    except Exception:
        return False
    known = {item.get("siteUrl", "").rstrip("/") for item in result.get("siteEntry", [])}
    if site_url.startswith("sc-domain:"):
        domain = site_url.split(":", 1)[1]
        return any(item.endswith(domain) or ("sc-domain:" + domain) in item for item in known)
    return site_url.rstrip("/") in known


def describe_error(exception):
    """Map a Google API exception to an actionable diagnosis."""
    message = str(exception)
    reason = ""
    content = getattr(exception, "content", None)
    try:
        import json as _json
        if isinstance(content, (bytes, bytearray)):
            body = _json.loads(bytes(content).decode("utf-8", "replace"))
            message = body.get("error", {}).get("message", message)
            reason = body.get("error", {}).get("status", "")
    except Exception:
        pass
    lowered = (message + " " + reason).lower()
    if "insufficient" in lowered or "scope" in lowered:
        return {
            "code": "AUTH_SCOPE",
            "message": message,
            "hint": "Use service-account credentials with scope "
                    + SCOPE_WEBMASTERS_READONLY,
        }
    if "permission" in lowered or "PERMISSION_DENIED" == reason:
        return {
            "code": "PROPERTY_PERMISSION",
            "message": message,
            "hint": "Add the service-account email as a user (Full) in "
                    "Search Console for the exact property URL.",
        }
    return {"code": "UNKNOWN", "message": message, "hint": ""}
