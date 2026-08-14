"""GSC permission/scope diagnostics (mock-only, no real API calls).

Covers the three failure modes called out in the V6-3 GSC batch:

- correct OAuth scope configured
- missing / wrong scope
- service account not authorized for the requested property
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import gsc_utils
from gsc_utils import (
    DEFAULT_SCOPES,
    SCOPE_WEBMASTERS_READONLY,
    build_credentials,
    describe_error,
    normalize_site_url,
    verify_site_access,
)

FAKE_SA = {
    "type": "service_account",
    "project_id": "fake-project",
    "private_key_id": "fake-id",
    "private_key": "-----BEGIN PRIVATE KEY-----\nfake\n-----END PRIVATE KEY-----\n",
    "client_email": "fake@fake-project.iam.gserviceaccount.com",
    "client_id": "123",
    "token_uri": "https://oauth2.googleapis.com/token",
}


def test_default_scope_is_webmasters_readonly():
    assert SCOPE_WEBMASTERS_READONLY == "https://www.googleapis.com/auth/webmasters.readonly"
    assert SCOPE_WEBMASTERS_READONLY in DEFAULT_SCOPES


def test_correct_scope_credentials_created(monkeypatch):
    """build_credentials must request the webmasters scope for the key info."""
    import google.oauth2.service_account as sa

    captured = {}

    class FakeCredentials:
        def __init__(self, info, scopes):
            captured["info"] = info
            captured["scopes"] = scopes

        @classmethod
        def from_service_account_info(cls, info, scopes=None):
            return cls(info, scopes)

    monkeypatch.setattr(sa, "Credentials", FakeCredentials)
    creds = build_credentials(service_account_info=FAKE_SA, scopes=[SCOPE_WEBMASTERS_READONLY])
    assert creds is not None
    assert captured["scopes"] == [SCOPE_WEBMASTERS_READONLY]


def test_missing_scope_falls_back_to_default(monkeypatch):
    """An empty scope list must never be used: fall back to the safe default
    webmasters.readonly scope so no credential is minted scope-less."""
    import google.oauth2.service_account as sa

    captured = {}

    class FakeCredentials:
        def __init__(self, info, scopes):
            captured["scopes"] = scopes

        @classmethod
        def from_service_account_info(cls, info, scopes=None):
            return cls(info, scopes)

    monkeypatch.setattr(sa, "Credentials", FakeCredentials)
    build_credentials(service_account_info=FAKE_SA, scopes=[])
    assert captured["scopes"] == DEFAULT_SCOPES


def test_missing_scope_is_rejected_by_fetcher():
    """A fetcher whose credentials carry no webmasters scope must not call the API."""
    from gsc_keyword_fetcher import GSCKeywordFetcher

    class NoScopeCredentials:
        scopes = []
        valid = False

        def refresh(self, request):
            raise RuntimeError("no refresh possible without scope")

    fetcher = GSCKeywordFetcher(site_url="https://www.chinaboundtravel.com/",
                                credentials=NoScopeCredentials())
    assert fetcher.fetch_keywords() == []


def test_unauthorized_property_detected(monkeypatch):
    """verify_site_access returns False when the property is not in sites.list()."""
    class FakeSites:
        def __init__(self, entries):
            self.entries = entries

        def list(self):
            class R:
                def execute(self):
                    return {"siteEntry": self.entries}
            return R()

    class FakeService:
        def __init__(self, entries):
            self._entries = entries

        def sites(self):
            return FakeSites(self._entries)

    monkeypatch.setattr(
        "googleapiclient.discovery.build",
        lambda *a, **k: FakeService([{"siteUrl": "https://other.example.com/"}]),
    )
    assert verify_site_access(object(), "https://www.chinaboundtravel.com/") is False


def test_authorized_property_detected(monkeypatch):
    class FakeSites:
        def list(self):
            class R:
                def execute(self):
                    return {"siteEntry": [{"siteUrl": "https://www.chinaboundtravel.com/"}]}
            return R()

    class FakeService:
        def sites(self):
            return FakeSites()

    monkeypatch.setattr(
        "googleapiclient.discovery.build",
        lambda *a, **k: FakeService(),
    )
    assert verify_site_access(object(), "https://www.chinaboundtravel.com/") is True


def test_normalize_site_url():
    assert normalize_site_url("https://www.chinaboundtravel.com") == "https://www.chinaboundtravel.com/"
    assert normalize_site_url("chinaboundtravel.com") == "https://chinaboundtravel.com/"
    assert normalize_site_url("sc-domain:chinaboundtravel.com") == "sc-domain:chinaboundtravel.com"


def test_describe_error_maps_insufficient_scope():
    class FakeHttpError:
        content = json.dumps({
            "error": {
                "status": "PERMISSION_DENIED",
                "message": "Request had insufficient authentication scopes.",
            }
        }).encode("utf-8")

    info = describe_error(FakeHttpError())
    assert info["code"] == "AUTH_SCOPE"
    assert "webmasters.readonly" in info["hint"]


def test_describe_error_maps_permission_denied():
    class FakeHttpError:
        content = json.dumps({
            "error": {
                "status": "PERMISSION_DENIED",
                "message": "User does not have permission for this property.",
            }
        }).encode("utf-8")

    info = describe_error(FakeHttpError())
    assert info["code"] == "PROPERTY_PERMISSION"
