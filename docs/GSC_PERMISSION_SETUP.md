# GSC Permission Setup

Diagnosis for the `insufficient authentication scopes` error seen when calling
the Google Search Console (webmasters) API. This document describes the code
fixes in this batch and the one manual step that only a Google console owner
can perform.

## 1. Current Google API scope

| Script | Before | After |
| --- | --- | --- |
| `chinaboundtravel_social_bot/gsc_keyword_fetcher.py` | `GSC_API_KEY` sent as `Bearer` token (not an OAuth scope at all) | service-account credentials with `https://www.googleapis.com/auth/webmasters.readonly` |
| `scripts/gsc-automation.py` | `webmasters` scope + deprecated `httplib2` refresh | `webmasters` scope, `google.auth.transport.requests.Request` refresh |
| `scripts/gsc_index_submit.py` | `webmasters` scope, non-www property string | `webmasters` scope, normalized property URL (trailing slash), www URLs kept |

Shared constants live in `scripts/gsc_utils.py`:

- `SCOPE_WEBMASTERS_READONLY = https://www.googleapis.com/auth/webmasters.readonly`
- `SCOPE_WEBMASTERS = https://www.googleapis.com/auth/webmasters`
- Default site property: `https://www.chinaboundtravel.com/`

## 2. Service account / OAuth type

All three scripts now use a Google Cloud **service account** JSON key
(`gsc-service-account-key.json` in the repo root, or the
`GSC_SERVICE_ACCOUNT_JSON` env var holding the JSON string or a path).

Root causes found in code:

- `gsc_keyword_fetcher.py` treated a Cloud API key as a bearer token. The
  webmasters API rejects that with 403 `insufficient authentication scopes`.
- Several scripts passed `https://chinaboundtravel.com` (no trailing slash,
  non-www) while the canonical property is `https://www.chinaboundtravel.com/`.
  GSC URL-prefix properties must match exactly.
- `gsc-automation.py` refreshed credentials through deprecated `httplib2`
  plumbing that can fail before any API call is made.

## 3. What to add in Search Console (manual, owner-only)

1. Open Search Console and confirm the property type:
   - URL-prefix property: `https://www.chinaboundtravel.com/`
   - or domain property: `sc-domain:chinaboundtravel.com`
2. Set `GSC_SITE_URL` to exactly the registered property when it differs from
   the default.
3. In the property settings, add the service-account email (the
   `client_email` from the key file) as a **user** with **Full** permission.

## 4. How to verify

Run the read-only check (no production writes):

```powershell
python scripts/verify_gsc_access.py
```

or from Python:

```python
import sys; sys.path.insert(0, "scripts")
from gsc_utils import build_credentials, verify_site_access
creds = build_credentials()
print(verify_site_access(creds, "https://www.chinaboundtravel.com/"))
```

Expected results:

- `True` -> credentials + property are correct.
- `False` -> either the service account is not added to the property, or
  `GSC_SITE_URL` does not match the registered property.

## 5. How to judge success

- `python -m pytest tests/test_gsc_permissions.py -q` passes (9 mock tests).
- `verify_site_access()` returns `True` for the live property.
- `scripts/gsc_keyword_fetcher.py` returns rows instead of printing
  `GSC API error [AUTH_SCOPE]` / `[PROPERTY_PERMISSION]`.

No credentials are printed or stored by any of the diagnostics.
