# -*- coding: utf-8 -*-
"""
P0.5: Guard against hardcoded secrets in tracked source/configuration files.

Scans tracked files (git ls-files) for real credential patterns. Test-only
mocks (tests/) and build artifacts (node_modules/, public/) are excluded.
"""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PATTERNS = {
    "feishu_webhook": re.compile(
        rb"https://open\.feishu\.cn/open-apis/bot/v2/hook/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
    ),
    "deepseek_key": re.compile(rb"sk-[A-Za-z0-9]{20,}"),
    "stripe_webhook_secret": re.compile(rb"whsec_[A-Za-z0-9]{12,}"),
    "stripe_key": re.compile(rb"(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{12,}"),
    "google_api_key": re.compile(rb"AIza[0-9A-Za-z_-]{20,}"),
    "resend_key": re.compile(rb"re_[A-Za-z0-9]{20,}"),
    "github_pat": re.compile(rb"gh[pousr]_[A-Za-z0-9]{20,}"),
}

EXCLUDE_PREFIX = ("node_modules/", "public/", "tests/", "resources/", "backup/", "archive/")
EXCLUDE_SUFFIX = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".ico", ".pyc", ".zip", ".woff", ".ttf")


def tracked_files():
    out = subprocess.run(["git", "ls-files"], cwd=str(ROOT), capture_output=True, text=True)
    return [line for line in out.stdout.splitlines() if line]


def test_no_hardcoded_secrets_in_tracked_files():
    violations = []
    for rel in tracked_files():
        if rel.startswith(EXCLUDE_PREFIX) or rel.endswith(EXCLUDE_SUFFIX):
            continue
        p = ROOT / rel
        if not p.exists():
            continue
        data = p.read_bytes()[:1 << 20]
        for name, rx in PATTERNS.items():
            for m in rx.finditer(data):
                line_start = data.rfind(b"\n", 0, m.start()) + 1
                line_end = data.find(b"\n", m.end())
                snippet = data[line_start:line_end].strip()[:80]
                violations.append(f"{rel}: {name}: {snippet!r}")
    assert not violations, "Hardcoded credentials found in tracked files:\n" + "\n".join(violations[:20])
