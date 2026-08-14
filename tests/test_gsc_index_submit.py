"""V6-4: mock tests for gsc_index_submit.py (no real API calls).

Verifies the script is unified with gsc_utils.py:
  - correct OAuth scopes per API (webmasters.readonly / indexing)
  - credential loading goes through gsc_utils
  - property URL normalization
  - no network calls when unauthorized
  - shared error classification (AUTH_SCOPE / PROPERTY_PERMISSION)
"""

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import gsc_index_submit as gis  # noqa: E402
from gsc_utils import SCOPE_INDEXING, SCOPE_WEBMASTERS_READONLY  # noqa: E402

FAKE_SA = {
    "type": "service_account",
    "project_id": "fake-project",
    "private_key_id": "fake-id",
    "private_key": "-----BEGIN PRIVATE KEY-----\nfake\n-----END PRIVATE KEY-----\n",
    "client_email": "fake@fake-project.iam.gserviceaccount.com",
    "client_id": "123",
    "token_uri": "https://oauth2.googleapis.com/token",
}


def test_site_url_normalized():
    s = gis.GSCIndexSubmitter(site_url="https://www.chinaboundtravel.com")
    assert s.site_url == "https://www.chinaboundtravel.com/"
    s2 = gis.GSCIndexSubmitter(site_url="chinaboundtravel.com")
    assert s2.site_url == "https://chinaboundtravel.com/"


def test_inspect_scope_is_webmasters_readonly(monkeypatch):
    captured = {}

    def fake_build(info, scopes=None):
        captured["info"] = info
        captured["scopes"] = scopes
        return object()

    monkeypatch.setattr("gsc_index_submit.build_credentials", fake_build)
    monkeypatch.setattr("gsc_index_submit.load_service_account_info", lambda: FAKE_SA)

    submitter = gis.GSCIndexSubmitter()
    assert submitter._inspect_credentials() is not None
    assert captured["scopes"] == [SCOPE_WEBMASTERS_READONLY]
    assert captured["info"] == FAKE_SA


def test_publish_scope_is_indexing(monkeypatch):
    captured = {}

    def fake_build(info, scopes=None):
        captured["scopes"] = scopes
        return object()

    monkeypatch.setattr("gsc_index_submit.build_credentials", fake_build)
    monkeypatch.setattr("gsc_index_submit.load_service_account_info", lambda: FAKE_SA)

    submitter = gis.GSCIndexSubmitter()
    assert submitter._publish_credentials() is not None
    assert captured["scopes"] == [SCOPE_INDEXING]


def test_unauthorized_without_key_never_calls_api(monkeypatch):
    monkeypatch.setattr("gsc_index_submit.load_service_account_info", lambda: None)

    def fail(*args, **kwargs):
        raise AssertionError("network call made without credentials")

    monkeypatch.setattr("requests.post", fail)
    monkeypatch.setattr("requests.get", fail)

    submitter = gis.GSCIndexSubmitter()
    result = submitter.submit_core_pages()
    assert result["status"] == "unauthorized"
    assert result["submitted_count"] == 0

    result2 = submitter.submit_sitemap_pages()
    assert result2["status"] == "unauthorized"


def test_classify_api_error_auth_scope():
    class FakeResponse:
        status_code = 403
        content = json.dumps({
            "error": {
                "status": "PERMISSION_DENIED",
                "message": "Request had insufficient authentication scopes.",
            }
        }).encode("utf-8")

    info = gis.classify_api_error(FakeResponse())
    assert info["code"] == "AUTH_SCOPE"
    assert "webmasters.readonly" in info["hint"]


def test_classify_api_error_property_permission():
    class FakeResponse:
        status_code = 403
        content = json.dumps({
            "error": {
                "status": "PERMISSION_DENIED",
                "message": "User does not have permission for this property.",
            }
        }).encode("utf-8")

    info = gis.classify_api_error(FakeResponse())
    assert info["code"] == "PROPERTY_PERMISSION"


def test_no_credentials_embedded():
    """The committed script must never contain a real private key."""
    src = (REPO_ROOT / "scripts" / "gsc_index_submit.py").read_text(encoding="utf-8")
    assert "BEGIN PRIVATE KEY" not in src
    assert "BEGIN RSA PRIVATE KEY" not in src
    # no long base64 blobs (private-key material would be ~1600+ chars)
    for line in src.splitlines():
        assert len(line) < 256, f"suspicious long line: {line[:40]}..."
