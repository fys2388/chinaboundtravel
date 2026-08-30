"""P0-6: Buffer dedup identity unit tests.

Verifies the stable dedup identity (content_id + account + platform + variant):

- same content/platform/account/variant => dedup (skip)
- same content different platform => allowed
- same content same platform different variant => allowed
- different content same platform => allowed

The dedup helper is a pure ESM module (buffer-worker/dedup.mjs) shared by the
Cloudflare Worker and these tests. No network and no real Buffer API involved.
"""
import subprocess
import os
from pathlib import Path

WORKER_DIR = Path(__file__).resolve().parent.parent / "buffer-worker"
DEDUP_MODULE = (WORKER_DIR / "dedup.mjs").as_uri()


def _node(expr: str) -> str:
    code = (
        f'import {{ buildDedupKey, isDuplicate, buildTrackRecord }} from "{DEDUP_MODULE}";\n'
        + expr
    )
    env = {k: v for k, v in os.environ.items() if k != "NODE_OPTIONS"}
    res = subprocess.run(
        ["node", "--input-type=module", "-e", code],
        capture_output=True, text=True, timeout=30, env=env,
    )
    assert res.returncode == 0, f"node failed: {res.stderr}"
    return res.stdout.strip()


def test_same_content_platform_account_variant_is_duplicate():
    out = _node(
        """
const a = buildDedupKey({ contentId: 'cbt-123456789abc', account: 'B', platform: 'instagram', variant: 'ig_main' });
const b = buildDedupKey({ contentId: 'cbt-123456789abc', account: 'B', platform: 'instagram', variant: 'ig_main' });
const d1 = isDuplicate({ contentId: 'cbt-123456789abc', account: 'B', platform: 'instagram', variant: 'ig_main', existing: true });
console.log(a === b, d1);
"""
    )
    parts = out.split()
    assert parts[0] == "true", f"same key expected: {out}"
    assert parts[1] == "true", f"existing record must skip: {out}"


def test_same_content_different_platform_allowed():
    out = _node(
        """
const a = buildDedupKey({ contentId: 'cbt-123456789abc', account: 'B', platform: 'instagram', variant: 'ig_main' });
const b = buildDedupKey({ contentId: 'cbt-123456789abc', account: 'B', platform: 'facebook', variant: 'ig_main' });
console.log(a !== b);
"""
    )
    assert out == "true", f"different platform must produce different key: {out}"


def test_same_content_same_platform_different_variant_allowed():
    out = _node(
        """
const a = buildDedupKey({ contentId: 'cbt-123456789abc', account: 'B', platform: 'instagram', variant: 'ig_main' });
const b = buildDedupKey({ contentId: 'cbt-123456789abc', account: 'B', platform: 'instagram', variant: 'ig_story' });
console.log(a !== b);
"""
    )
    assert out == "true", f"different variant must produce different key: {out}"


def test_different_content_same_platform_allowed():
    out = _node(
        """
const a = buildDedupKey({ contentId: 'cbt-123456789abc', account: 'B', platform: 'x', variant: 'x_promo' });
const b = buildDedupKey({ contentId: 'cbt-000000000000', account: 'B', platform: 'x', variant: 'x_promo' });
console.log(a !== b);
"""
    )
    assert out == "true", f"different content must produce different key: {out}"


def test_missing_content_id_falls_back_to_null_key():
    out = _node(
        """
const k = buildDedupKey({ contentId: '', account: 'B', platform: 'x', variant: 'x_promo' });
console.log(k === null);
"""
    )
    assert out == "true", "missing content_id must yield null (legacy dedup fallback)"


def test_track_record_fields_and_no_secret():
    out = _node(
        """
const r = buildTrackRecord({ contentId: 'cbt-123456789abc', platform: 'x', account: 'B', scheduledAt: '2026-08-13T10:00:00.000Z', sourceWorkflow: 'social_publisher', postUrl: 'https://www.chinaboundtravel.com/posts/test/' });
const keys = ['content_id','platform','account','scheduled_at','source_workflow','post_url'];
console.log(keys.every(k => k in r), JSON.stringify(r).includes('TOKEN'));
"""
    )
    parts = out.split()
    assert parts[0] == "true", f"track record must contain all fields: {out}"
    assert parts[1] == "false", f"track record must not contain any secret: {out}"
