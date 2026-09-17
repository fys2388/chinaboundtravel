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
    "doubao_ark_key": re.compile(rb"ark-[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"),
    "stripe_webhook_secret": re.compile(rb"whsec_[A-Za-z0-9]{12,}"),
    "stripe_key": re.compile(rb"(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{12,}"),
    "google_api_key": re.compile(rb"AIza[0-9A-Za-z_-]{20,}"),
    "resend_key": re.compile(rb"re_[A-Za-z0-9]{20,}"),
    "github_pat": re.compile(rb"gh[pousr]_[A-Za-z0-9]{20,}"),
    "buffer_bearer_token": re.compile(rb"Bearer\s+[A-Za-z0-9_-]{40,}"),
    "buffer_token_literal": re.compile(rb"(?:6PUb|n_O9|rbeS)[A-Za-z0-9_-]{20,}"),
    "buffer_token_assignment": re.compile(
        rb"['\"](?:BUFFER|buffer)[A-Za-z0-9_]*TOKEN[A-Za-z0-9_]*['\"]\s*[:=]\s*['\"][A-Za-z0-9_-]{40,}['\"]"
    ),
}

EXCLUDE_PREFIX = ("node_modules/", "public/", "tests/", "resources/", "backup/", "archive/")
EXCLUDE_SUFFIX = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".ico", ".pyc", ".zip", ".woff", ".ttf")


def tracked_files():
    out = subprocess.run(["git", "ls-files"], cwd=str(ROOT), capture_output=True, text=True)
    return [line for line in out.stdout.splitlines() if line]


_B64_OK = set(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=")


def _inside_base64_blob(data, start, end, window=160):
    """True when the match sits inside a long base64 run (e.g. a data: URI image).

    Lighthouse 报告（lh-desktop-0830.json 等）内嵌整张 base64 图片，
    字节流里会偶然拼出 AIza…/sk-… 形状的字符串，属二进制数据不是凭据。
    """
    if start >= window and end + window <= len(data):
        head = data[start - window:start]
        tail = data[end:end + window]
    else:
        head = data[max(0, start - window):start]
        tail = data[end:min(len(data), end + window)]
    probe = head + tail
    if not probe:
        return False
    return sum(1 for b in probe if b in _B64_OK) / len(probe) >= 0.90


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
                if _inside_base64_blob(data, m.start(), m.end()):
                    continue
                line_start = data.rfind(b"\n", 0, m.start()) + 1
                line_end = data.find(b"\n", m.end())
                snippet = data[line_start:line_end].strip()[:80]
                violations.append(f"{rel}: {name}: {snippet!r}")
    assert not violations, "Hardcoded credentials found in tracked files:\n" + "\n".join(violations[:20])


# ---------- negative control ----------
# _inside_base64_blob 只豁免"长在 base64 数据流里的巧合匹配"，
# 不能把普通配置里的真实凭据一起放过，否则这个哨兵就形同虚设。

_B64_FILLER = "UklGRvJtAgBXRUJQVlA4WAoAAAAgAAAARQUAABwASUNDUMgB" * 20


def test_plain_credentials_are_still_flagged():
    for pat_name, literal in (
        ("google_api_key", "AIzaSyA1B2C3D4E5F6G7H8I9J0K1"),
        ("stripe_webhook_secret", "whsec_abcdef1234567890"),
        ("github_pat", "ghp_a1B2c3D4e5F6g7H8i9J0k1L2"),
    ):
        rx = PATTERNS[pat_name]
        data = f'{{"key": "{literal}"}}\n'.encode()
        m = rx.search(data)
        assert m, f"{pat_name} 正则本身失效"
        assert not _inside_base64_blob(data, m.start(), m.end()), (
            f"{pat_name} 被误判为 base64 blob，哨兵会漏掉真实凭据"
        )


def test_base64_data_uri_is_ignored():
    blob = "data:image/webp;base64," + _B64_FILLER + "AIzaSyFake0123456789ABCDEFGH" + _B64_FILLER
    data = ('{"url": "/x", "data": "' + blob + '"}\n').encode()
    found = list(PATTERNS["google_api_key"].finditer(data))
    assert found, "测试数据未能复现 base64 内的巧合匹配"
    assert all(_inside_base64_blob(data, m.start(), m.end()) for m in found), (
        "base64 blob 内的匹配应被豁免"
    )
