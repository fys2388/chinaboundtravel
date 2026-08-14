"""V6-2: avatar WebP optimization.

Ensures:
  - the WebP asset exists, is smaller than the source PNG, and is 256x256
  - display templates (sidebar, about hero, profile mode) prefer WebP
  - the PNG source asset is preserved
  - JSON-LD / schema still carries the avatar image (not broken)
"""
import struct
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

STATIC_IMAGES = REPO_ROOT / "static" / "images"
PNG = STATIC_IMAGES / "joran-avatar.png"
WEBP = STATIC_IMAGES / "joran-avatar.webp"

SIDEBAR = (REPO_ROOT / "layouts" / "partials" / "sidebar-author.html").read_text(encoding="utf-8")
ABOUT = (REPO_ROOT / "content" / "about" / "_index.md").read_text(encoding="utf-8")
HUGO_TOML = (REPO_ROOT / "hugo.toml").read_text(encoding="utf-8")
SCHEMA = (REPO_ROOT / "layouts" / "partials" / "templates" / "schema_json.html").read_text(encoding="utf-8")


def webp_dimensions(path):
    """Parse WebP dimensions without dependencies (RIFF/VP8X header)."""
    data = Path(path).read_bytes()
    assert data[:4] == b"RIFF" and data[8:12] == b"WEBP", "not a webp file"
    chunk = data[12:16]
    if chunk == b"VP8X":
        w = struct.unpack("<I", b"\x00" + data[24:27])[0]
        h = struct.unpack("<I", b"\x00" + data[27:30])[0]
        return w, h
    if chunk == b"VP8 ":
        w, h = struct.unpack("<HH", data[26:30])
        return w & 0x3FFF, h & 0x3FFF
    if chunk == b"VP8L":
        b0, b1, b2, b3 = data[21:25]
        w = ((b1 & 0x3F) << 8) | b0 + 1
        h = ((b3 & 0x0F) << 10) | (b2 << 2) | ((b1 & 0xC0) >> 6) + 1
        return w, h
    raise AssertionError("unknown webp chunk: %r" % chunk)


def test_webp_asset_exists_and_smaller():
    assert PNG.exists(), "source PNG must be preserved"
    assert WEBP.exists(), "webp asset must exist"
    assert WEBP.stat().st_size < PNG.stat().st_size


def test_webp_dimensions_256():
    assert webp_dimensions(WEBP) == (256, 256)


def test_sidebar_prefers_webp():
    assert "joran-avatar.webp" in SIDEBAR
    assert SIDEBAR.index("joran-avatar.webp") < SIDEBAR.index("joran-avatar.png")
    assert '<source srcset="/images/joran-avatar.webp" type="image/webp">' in SIDEBAR


def test_about_hero_prefers_webp():
    assert "joran-avatar.webp" in ABOUT
    assert ABOUT.index("joran-avatar.webp") < ABOUT.index("joran-avatar.png")
    assert '<source srcset="/images/joran-avatar.webp" type="image/webp">' in ABOUT


def test_profile_mode_uses_webp():
    assert 'imageUrl = "images/joran-avatar.webp"' in HUGO_TOML


def test_png_source_preserved():
    assert PNG.exists()


def test_schema_json_still_has_avatar():
    # JSON-LD image must not be broken by the optimization
    assert "images/joran-avatar.png" in SCHEMA
