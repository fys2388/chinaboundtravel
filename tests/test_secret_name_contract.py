# -*- coding: utf-8 -*-
"""P0.7-D2B: Secret name contract tests.

Validates that production code uses the single official secret-variable
naming contract (no synonyms):

- MailerLite: ``MAILERLITE_API_TOKEN`` is the only official name.
  ``MAILERLITE_API_KEY`` must not be referenced by production code.
- Forbidden synonym names must not appear in production code:
  ``CF_API_TOKEN``, ``CF_ACCOUNT_ID``, ``CLOUDFLARE_TOKEN``,
  ``MAILERLITE_KEY``, ``MAILERLITE_TOKEN``, ``RESEND_TOKEN``,
  ``RESEND_SECRET``, ``RESEND_API``, ``BUFFER_TOKEN_A``,
  ``BUFFER_TOKEN_B``, ``BUFFER_PINTEREST_TOKEN``.

Scope notes:
- docs/ and tests/ are excluded: documentation prose and test mocks may
  mention the names, which must not be flagged.
- deprecated_scripts/ is excluded: legacy non-production code keeps an
  explicit ``MAILERLITE_API_KEY`` compatibility fallback by design.
- buffer-worker/: only ``worker.js`` and ``wrangler.toml`` are production
  files; the query/debug/test helpers are developer tools.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Official secret-variable contract (verified against GitHub repo secrets).
OFFICIAL_CONTRACT = [
    "DOUBAO_ARK_API_KEY",
    "MAILERLITE_API_TOKEN",
    "STRIPE_SECRET_KEY",
    "STRIPE_WEBHOOK_SECRET",
    "RESEND_API_KEY",
    "BUFFER_API_TOKEN",
    "BUFFER_WORKER_URL",
    "NEW_BUFFER_WORKER_URL",
    "FEISHU_WEBHOOK_URL",
    "FEISHU_SECRET",
    "CLOUDFLARE_API_TOKEN",
    "CLOUDFLARE_ACCOUNT_ID",
    "GSC_SERVICE_ACCOUNT_JSON",
    "GSC_SITE_URL",
    "YOUTUBE_CLIENT_SECRETS",
    "YOUTUBE_OAUTH_REFRESH_TOKEN",
]

# Names that must never be introduced as new secret variables.
FORBIDDEN_SYNONYMS = [
    "CF_API_TOKEN",
    "CF_ACCOUNT_ID",
    "CLOUDFLARE_TOKEN",
    "MAILERLITE_KEY",
    "MAILERLITE_TOKEN",
    "MAILERLITE_API_KEY",
    "RESEND_TOKEN",
    "RESEND_SECRET",
    "RESEND_API",
    "BUFFER_TOKEN_A",
    "BUFFER_TOKEN_B",
    "BUFFER_PINTEREST_TOKEN",
]

EXCLUDE_DIRS = {
    ".git", "node_modules", "public", "tests", "docs", "deprecated_scripts",
    "archive", "backup", "reports", "resources", "ai_drafts", ".playwright-mcp",
}
EXCLUDE_SUFFIX = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".ico", ".pyc", ".zip", ".woff", ".ttf", ".lock")
ALLOWED_EXT = {".py", ".js", ".mjs", ".ts", ".yml", ".yaml", ".toml", ".sh", ".ps1", ".json", ".cjs"}


def production_files():
    """Yield production file paths (relative) inside the scan scope."""
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT).as_posix()
        parts = rel.split("/")
        if any(part in EXCLUDE_DIRS for part in parts):
            continue
        if p.suffix not in ALLOWED_EXT or p.name.endswith(EXCLUDE_SUFFIX):
            continue
        # buffer-worker: only the worker entry + its wrangler config are production.
        if rel.startswith("buffer-worker/") and rel not in ("buffer-worker/worker.js", "buffer-worker/wrangler.toml"):
            continue
        yield rel


def read_text(rel):
    return (ROOT / rel).read_text(encoding="utf-8", errors="ignore")


def test_mailerlite_secret_name_contract():
    """MAILERLITE_API_TOKEN is the only official MailerLite variable."""
    bad, good = [], []
    for rel in production_files():
        text = read_text(rel)
        if re.search(r"\bMAILERLITE_API_KEY\b", text):
            bad.append(rel)
        if re.search(r"\bMAILERLITE_API_TOKEN\b", text):
            good.append(rel)
    assert not bad, "Production code must not reference MAILERLITE_API_KEY:\n" + "\n".join(sorted(bad))
    assert good, "No production file references MAILERLITE_API_TOKEN (contract must be used)."


def test_no_forbidden_synonym_secret_names():
    """Forbidden synonym variable names must not be introduced."""
    violations = []
    for rel in production_files():
        text = read_text(rel)
        for name in FORBIDDEN_SYNONYMS:
            if re.search(rf"\b{re.escape(name)}\b", text):
                violations.append(f"{rel}: {name}")
    assert not violations, "Forbidden synonym secret names found:\n" + "\n".join(sorted(violations))


def test_wrangler_toml_has_no_sensitive_placeholders():
    """wrangler.toml must not hold secret placeholders or secret names."""
    toml = read_text("wrangler.toml")
    assert "REPLACE_WITH_YOUR" not in toml, "wrangler.toml still contains a placeholder value."
    for name in ("STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET", "MAILERLITE_API_KEY"):
        assert not re.search(rf"^\s*{re.escape(name)}\s*=", toml, flags=re.M), (
            f"wrangler.toml must not declare {name} in [vars]."
        )


def test_official_contract_names_are_documented():
    """The official contract list stays non-empty and unique."""
    assert len(OFFICIAL_CONTRACT) == len(set(OFFICIAL_CONTRACT))
    assert "MAILERLITE_API_TOKEN" in OFFICIAL_CONTRACT
    assert "MAILERLITE_API_KEY" not in OFFICIAL_CONTRACT
