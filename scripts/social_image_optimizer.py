"""
P0: Social Media Image Optimizer
Auto-crops and resizes images for each social media platform's required aspect ratio.
Uses Pillow for center-crop and smart-resize.
"""
import sys
import os
from pathlib import Path
from urllib.parse import urlparse

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Target dimensions for each platform (width, height)
PLATFORM_TARGETS = {
    "instagram": {
        "default": (1080, 1350),   # 4:5 portrait (best for IG feed)
        "square": (1080, 1080),     # 1:1
        "story": (1080, 1920),      # 9:16
    },
    "ig": {
        "default": (1080, 1350),
        "square": (1080, 1080),
        "story": (1080, 1920),
    },
    "pinterest": {
        "default": (1000, 1500),    # 2:3 vertical (best for Pinterest)
        "square": (1000, 1000),
    },
    "x": {
        "default": (1600, 900),     # 16:9 landscape (best for X)
        "square": (1200, 1200),
    },
    "twitter": {
        "default": (1600, 900),
        "square": (1200, 1200),
    },
    "facebook": {
        "default": (1200, 630),     # 1.91:1 link post
        "square": (1080, 1080),
        "portrait": (1080, 1350),
    },
    "fb": {
        "default": (1200, 630),
        "square": (1080, 1080),
        "portrait": (1080, 1350),
    },
}

# Allowed image extensions
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def download_image(url: str, dest_dir: str) -> str:
    """Download image from URL to dest_dir. Returns local path."""
    import requests
    os.makedirs(dest_dir, exist_ok=True)
    ext = Path(urlparse(url).path).suffix
    if ext.lower() not in ALLOWED_EXTENSIONS:
        ext = ".jpg"
    filename = f"src_{abs(hash(url))}{ext}"
    local_path = os.path.join(dest_dir, filename)
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    with open(local_path, "wb") as f:
        f.write(resp.content)
    return local_path


def center_crop(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """
    Center-crop image to target aspect ratio, then resize to target dimensions.
    Preserves as much of the center of the image as possible.
    """
    src_w, src_h = img.size
    target_ratio = target_w / target_h
    src_ratio = src_w / src_h

    if abs(src_ratio - target_ratio) < 0.01:
        # Already correct ratio, just resize
        return img.resize((target_w, target_h), Image.LANCZOS)

    if src_ratio > target_ratio:
        # Source is wider than target -> crop width
        new_w = int(src_h * target_ratio)
        left = (src_w - new_w) // 2
        cropped = img.crop((left, 0, left + new_w, src_h))
    else:
        # Source is taller than target -> crop height
        new_h = int(src_w / target_ratio)
        top = (src_h - new_h) // 2
        cropped = img.crop((0, top, src_w, top + new_h))

    return cropped.resize((target_w, target_h), Image.LANCZOS)


def optimize_image(
    source: str,
    platform: str,
    output_dir: str,
    variant: str = "default",
    quality: int = 85,
) -> dict:
    """
    Optimize an image for a specific platform.

    Args:
        source: URL or local file path of source image
        platform: target platform (instagram, pinterest, x, facebook)
        output_dir: directory to save optimized image
        variant: 'default', 'square', 'story', 'portrait' (platform-dependent)
        quality: JPEG/WebP quality (1-100)

    Returns:
        dict with: success (bool), output_path, dimensions, source, platform, error
    """
    result = {
        "success": False,
        "source": source[:80] if source else "(empty)",
        "platform": platform,
        "variant": variant,
        "output_path": "",
        "width": 0,
        "height": 0,
        "error": "",
    }

    if not PIL_AVAILABLE:
        result["error"] = "Pillow not installed"
        return result

    if not source or not source.strip():
        result["error"] = "empty_source"
        return result

    spec = PLATFORM_TARGETS.get(platform.lower())
    if not spec:
        result["error"] = f"unknown_platform:{platform}"
        return result

    target_dims = spec.get(variant, spec["default"])
    target_w, target_h = target_dims

    # Get local source path
    local_source = source
    temp_downloaded = False
    if source.startswith("http"):
        try:
            local_source = download_image(source, os.path.join(output_dir, "_src"))
            temp_downloaded = True
        except Exception as e:
            result["error"] = f"download_failed:{str(e)[:50]}"
            return result

    if not os.path.exists(local_source):
        result["error"] = "source_not_found"
        return result

    # Process image
    try:
        with Image.open(local_source) as img:
            img = img.convert("RGB")  # Normalize to RGB (handles RGBA, palette, etc.)
            optimized = center_crop(img, target_w, target_h)

            # Save
            os.makedirs(output_dir, exist_ok=True)
            src_name = Path(local_source).stem
            ext = ".jpg"  # Standardize to JPEG for social media
            out_name = f"{src_name}_{platform}_{variant}_{target_w}x{target_h}{ext}"
            # Sanitize filename
            out_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in out_name)
            output_path = os.path.join(output_dir, out_name)

            optimized.save(output_path, "JPEG", quality=quality, optimize=True)

            result["success"] = True
            result["output_path"] = output_path
            result["width"] = target_w
            result["height"] = target_h
    except Exception as e:
        result["error"] = f"processing_failed:{str(e)[:60]}"
    finally:
        # Clean up temp download
        if temp_downloaded and os.path.exists(local_source):
            try:
                os.remove(local_source)
            except Exception:
                pass

    return result


def optimize_for_all_platforms(
    source: str,
    output_dir: str,
    platforms: list = None,
) -> list:
    """
    Generate platform-optimized variants of a source image for all platforms.

    Returns list of optimization results.
    """
    if platforms is None:
        platforms = ["instagram", "pinterest", "x", "facebook"]

    results = []
    for platform in platforms:
        spec = PLATFORM_TARGETS.get(platform)
        if not spec:
            continue
        # Generate default variant for each platform
        r = optimize_image(source, platform, output_dir, variant="default")
        results.append(r)
    return results


def main() -> int:
    import argparse
    import json

    ap = argparse.ArgumentParser(description="Social Media Image Optimizer")
    ap.add_argument("--source", type=str, required=True, help="Source image URL or path")
    ap.add_argument("--platform", type=str, default="instagram",
                    choices=list(PLATFORM_TARGETS.keys()))
    ap.add_argument("--variant", type=str, default="default",
                    help="Variant: default, square, story, portrait")
    ap.add_argument("--output-dir", type=str, default="static/img/social_optimized")
    ap.add_argument("--all-platforms", action="store_true", help="Generate for all platforms")
    ap.add_argument("--quality", type=int, default=85)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.all_platforms:
        results = optimize_for_all_platforms(args.source, args.output_dir)
    else:
        r = optimize_image(args.source, args.platform, args.output_dir,
                           variant=args.variant, quality=args.quality)
        results = [r]

    if args.json:
        print(json.dumps({"results": results}, ensure_ascii=False, indent=2))
    else:
        print(f"Social Image Optimizer ({len(results)} variant(s))")
        for r in results:
            if r["success"]:
                print(f"  OK {r['platform']:12s} {r['width']}x{r['height']} -> {r['output_path']}")
            else:
                print(f"  FAIL {r['platform']:12s} {r['error']}")

    success_count = sum(1 for r in results if r["success"])
    return 0 if success_count == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
