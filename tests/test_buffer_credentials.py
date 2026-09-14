"""Tests for the shared Buffer account credentials."""
from buffer_credentials import (
    configured_buffer_accounts,
    is_buffer_token,
    resolve_buffer_token,
    resolve_buffer_token_with_source,
)


TOKEN_KEYS = (
    "BUFFER_API_TOKEN_A",
    "BUFFER_API_TOKEN_B",
    "BUFFER_ACCESS_TOKEN",
    "BUFFER_ACCESS_TOKEN_2",
    "BUFFER_API_TOKEN",
)


def _clear_tokens(monkeypatch):
    for key in TOKEN_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_canonical_a_b_tokens_are_shared_for_both_accounts(monkeypatch):
    _clear_tokens(monkeypatch)
    monkeypatch.setenv("BUFFER_API_TOKEN_A", "token-account-a-123456")
    monkeypatch.setenv("BUFFER_API_TOKEN_B", "token-account-b-123456")

    assert resolve_buffer_token("A") == "token-account-a-123456"
    assert resolve_buffer_token("account_b") == "token-account-b-123456"
    assert configured_buffer_accounts() == ["A", "B"]


def test_legacy_analytics_aliases_remain_compatible(monkeypatch):
    _clear_tokens(monkeypatch)
    monkeypatch.setenv("BUFFER_ACCESS_TOKEN", "legacy-account-a-123456")
    monkeypatch.setenv("BUFFER_ACCESS_TOKEN_2", "legacy-account-b-123456")

    token_a, source_a = resolve_buffer_token_with_source("A")
    token_b, source_b = resolve_buffer_token_with_source("B")

    assert token_a == "legacy-account-a-123456"
    assert source_a == "BUFFER_ACCESS_TOKEN"
    assert token_b == "legacy-account-b-123456"
    assert source_b == "BUFFER_ACCESS_TOKEN_2"


def test_canonical_token_takes_precedence_over_legacy_alias(monkeypatch):
    _clear_tokens(monkeypatch)
    monkeypatch.setenv("BUFFER_API_TOKEN_A", "canonical-account-a-123456")
    monkeypatch.setenv("BUFFER_ACCESS_TOKEN", "legacy-account-a-123456")

    token, source = resolve_buffer_token_with_source("A")

    assert token == "canonical-account-a-123456"
    assert source == "BUFFER_API_TOKEN_A"


def test_worker_url_is_never_treated_as_a_token(monkeypatch):
    _clear_tokens(monkeypatch)
    monkeypatch.setenv(
        "BUFFER_ACCESS_TOKEN",
        "https://buffer-worker.chinaboundtravel.com/publish",
    )

    assert not is_buffer_token(
        "https://buffer-worker.chinaboundtravel.com/publish"
    )
    assert resolve_buffer_token("A") == ""
    assert configured_buffer_accounts() == []


def test_missing_or_short_values_are_not_configured(monkeypatch):
    _clear_tokens(monkeypatch)
    monkeypatch.setenv("BUFFER_API_TOKEN_A", "short")

    assert resolve_buffer_token("A") == ""
    assert configured_buffer_accounts() == []
