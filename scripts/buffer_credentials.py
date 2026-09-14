#!/usr/bin/env python3
"""Resolve the shared Buffer credentials for both distribution accounts.

Each Buffer account has one API token. The publishing worker and analytics
pullers use the same A/B tokens; the additional names below are historical
aliases kept only for compatibility.
"""
from __future__ import annotations

import os


_ACCOUNT_ALIASES = {
    "A": "A",
    "ACCOUNT_A": "A",
    "ACCOUNT-A": "A",
    "B": "B",
    "ACCOUNT_B": "B",
    "ACCOUNT-B": "B",
}

# Canonical names first. Legacy analytics aliases remain supported so existing
# local .env files and scheduled jobs do not break during migration.
_TOKEN_SOURCES = {
    "A": (
        "BUFFER_API_TOKEN_A",
        "BUFFER_ACCESS_TOKEN",
        "BUFFER_API_TOKEN",
    ),
    "B": (
        "BUFFER_API_TOKEN_B",
        "BUFFER_ACCESS_TOKEN_2",
    ),
}


def _normalize_account(account: str) -> str:
    key = str(account or "").strip().upper()
    normalized = _ACCOUNT_ALIASES.get(key)
    if not normalized:
        raise ValueError("Buffer account must be A or B")
    return normalized


def _clean(value: object) -> str:
    return str(value or "").strip().lstrip("\ufeff")


def is_buffer_token(value: object) -> bool:
    """Return whether a configured value looks like a Buffer API token."""
    token = _clean(value)
    if len(token) < 10:
        return False
    if token.lower().startswith(("http://", "https://")):
        return False
    if "/" in token or "\\" in token or any(char.isspace() for char in token):
        return False
    return True


def resolve_buffer_token_with_source(account: str) -> tuple[str, str]:
    """Return ``(token, variable_name)`` for one account.

    The token value is returned only to API callers. Callers should log the
    variable name instead of the token.
    """
    account_key = _normalize_account(account)
    for source in _TOKEN_SOURCES[account_key]:
        token = _clean(os.environ.get(source, ""))
        if is_buffer_token(token):
            return token, source
    return "", ""


def resolve_buffer_token(account: str) -> str:
    """Return the shared Buffer token for account A or B, or an empty string."""
    token, _ = resolve_buffer_token_with_source(account)
    return token


def configured_buffer_accounts() -> list[str]:
    """Return the configured account keys without exposing credential values."""
    return [
        account
        for account in ("A", "B")
        if resolve_buffer_token(account)
    ]
