"""V6-2: avatar WebP asset preservation.

Ensures:
  - the WebP asset exists, is smaller than the source PNG, and is 256x256
  - the PNG source asset is preserved

注：模板引用断言已随品牌视觉改版移除——站点头像已从 Joran 照片迁移到 logo 系
资产，模板不再引用 joran-avatar。这里只保留资产本身的保留性校验。
"""
import struct
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

STATIC_IMAGES = REPO_ROOT / "static" / "images"
PNG = STATIC_IMAGES / "joran-avatar.png"
WEBP = STATIC_IMAGES / "joran-avatar.webp"


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


def test_png_source_preserved():
    assert PNG.exists()

# 注：以下 4 个断言模板引用 joran-avatar（sidebar/about/profile-mode/schema）的测试
# 已随品牌视觉改版删除——站点已从「Joran 照片头像」迁移到 logo 系资产
# （sidebar/about 用 logo-avatar.svg，schema/hugo.toml 用 favicon.svg），
# 模板不再引用 joran-avatar，断言其存在会永久失败。
# joran-avatar.png / .webp 资产本身仍保留在 static/images/（见上方两个 asset 测试）。
