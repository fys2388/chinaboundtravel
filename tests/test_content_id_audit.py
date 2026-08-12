"""P0-6: content ID audit tests.

Verifies stable, unique, well-formed content IDs and that backfill is
idempotent (existing IDs are never regenerated).
"""
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import content_id_audit as audit

ID_RE = re.compile(r"^cbt-[0-9a-f]{12}$")


def test_format():
    assert ID_RE.match("cbt-1234567890ab")
    assert not ID_RE.match("1234567890ab")
    assert not ID_RE.match("cbt-12345")


def test_derive_id_stable_across_title_change():
    fm_a = {"title": "A Title", "canonicalURL": "https://www.chinaboundtravel.com/posts/slug-x/"}
    fm_b = {"title": "A Totally Different Title", "canonicalURL": "https://www.chinaboundtravel.com/posts/slug-x/"}
    p = Path("fake.md")
    assert audit.derive_id(p, fm_a, set()) == audit.derive_id(p, fm_b, set())


def test_derive_id_unique_on_canonical_collision():
    p = Path("fake.md")
    fm1 = {"canonicalURL": "https://www.chinaboundtravel.com/posts/same/"}
    fm2 = {"slug": "different-slug"}
    first = audit.derive_id(p, fm1, set())
    second = audit.derive_id(p, fm2, {first})
    assert first != second
    assert ID_RE.match(first) and ID_RE.match(second)


def test_backfill_and_idempotency(tmp_path):
    (tmp_path / "content").mkdir(parents=True)
    (tmp_path / "content" / "posts").mkdir(parents=True)
    f = tmp_path / "content" / "posts" / "test-post.md"
    f.write_text('---\ntitle: "Test Post"\ncanonicalURL: "https://www.chinaboundtravel.com/posts/test-post/"\n---\n\nBody\n', encoding="utf-8")

    # First backfill run fills the ID
    fm, delim = audit._front_matter_dict(f.read_text(encoding="utf-8"))
    cid = audit.add_content_id(f, fm, delim, set())
    assert cid and ID_RE.match(cid)

    # Second run must NOT regenerate (idempotent)
    fm2, _ = audit._front_matter_dict(f.read_text(encoding="utf-8"))
    assert audit.add_content_id(f, fm2, "_", set()) is None
    assert fm2["content_id"] == cid


def test_live_posts_audit_passes():
    """The real content tree must pass a strict audit (no missing/duplicate/malformed IDs)."""
    assert audit.audit(strict=True) == 0