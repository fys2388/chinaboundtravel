"""
P0: Social Media Image Validator
Validates social media post images for platform-specific requirements.
Checks: existence, aspect ratio, minimum resolution, file size, blocked AI domains.
"""
import sys
import os
import re
from pathlib import Path
from urllib.parse import urlparse

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Platform image specifications
PLATFORM_SPECS = {
    "instagram": {
        "allowed_ratios": [(1, 1), (4, 5), (9, 16)],
        "min_short_side": 1080,
        "max_file_mb": 8,
        "label": "Instagram",
    },
    "ig": {
        "allowed_ratios": [(1, 1), (4, 5), (9, 16)],
        "min_short_side": 1080,
        "max_file_mb": 8,
        "label": "Instagram",
    },
    "pinterest": {
        "allowed_ratios": [(2, 3), (1, 1)],
        "min_short_side": 1000,
        "max_file_mb": 10,
        "label": "Pinterest",
    },
    "x": {
        "allowed_ratios": [(16, 9), (1, 1)],
        "min_short_side": 800,
        "max_file_mb": 5,
        "label": "X/Twitter",
    },
    "twitter": {
        "allowed_ratios": [(16, 9), (1, 1)],
        "min_short_side": 800,
        "max_file_mb": 5,
        "label": "X/Twitter",
    },
    "facebook": {
        "allowed_ratios": [(191, 100), (1, 1), (4, 5)],
        "min_short_side": 600,
        "max_file_mb": 8,
        "label": "Facebook",
    },
    "fb": {
        "allowed_ratios": [(191, 100), (1, 1), (4, 5)],
        "min_short_side": 600,
        "max_file_mb": 8,
        "label": "Facebook",
    },
}

BLOCKED_AI_DOMAINS = [
    "pollinations.ai", "image.pollinations.ai", "lexica.art",
    "midjourney", "dalle", "stablediffusion", "craiyon.com",
]

RATIO_TOLERANCE = 0.05  # 5% tolerance for aspect ratio matching


def get_image_dimensions(image_path: str) -> tuple:
    """Get (width, height) of an image file. Returns (0,0) on failure."""
    if not PIL_AVAILABLE:
        return (0, 0)
    try:
        with Image.open(image_path) as img:
            return img.size  # (width, height)
    except Exception:
        return (0, 0)


def is_blocked_ai_domain(url: str) -> bool:
    """Check if image URL is from a blocked AI image domain."""
    if not url or not url.startswith("http"):
        return False
    try:
        domain = urlparse(url).netloc.lower()
        return any(d in domain for d in BLOCKED_AI_DOMAINS)
    except Exception:
        return False


def ratio_matches(width: int, height: int, target_ratio: tuple) -> bool:
    """Check if image dimensions match target ratio (w:h) within tolerance."""
    if width == 0 or height == 0:
        return False
    actual = width / height
    target = target_ratio[0] / target_ratio[1]
    return abs(actual - target) / target <= RATIO_TOLERANCE


def validate_image(image_source: str, platform: str, local_dir: str = None) -> dict:
    """
    Validate a social media post image.

    Args:
        image_source: URL or local file path to the image
        platform: target platform (instagram, pinterest, x, facebook)
        local_dir: directory to download remote images for inspection

    Returns:
        dict with: passed (bool), issues (list), dimensions, aspect_ratio, platform
    """
    result = {
        "image": image_source[:80] if image_source else "(empty)",
        "platform": platform,
        "passed": False,
        "issues": [],
        "width": 0,
        "height": 0,
        "aspect_ratio": "",
        "is_remote": False,
        "dimensions_checked": True,
    }

    # 1. Check existence
    if not image_source or not image_source.strip():
        result["issues"].append("missing_image")
        return result

    # 2. Check blocked AI domains
    if image_source.startswith("http"):
        result["is_remote"] = True
        if is_blocked_ai_domain(image_source):
            result["issues"].append("blocked_ai_image_domain")
            # Continue to check other aspects, but this is a hard fail

    # 3. Get platform spec
    spec = PLATFORM_SPECS.get(platform.lower())
    if not spec:
        result["issues"].append(f"unknown_platform:{platform}")
        return result

    # 4. Get dimensions (local file or download)
    local_path = image_source
    if image_source.startswith("http") and local_dir:
        # Download for inspection
        try:
            import requests
            os.makedirs(local_dir, exist_ok=True)
            ext = Path(urlparse(image_source).path).suffix or ".jpg"
            local_path = os.path.join(local_dir, f"_validate_{abs(hash(image_source))}{ext}")
            resp = requests.get(image_source, timeout=30)
            resp.raise_for_status()
            with open(local_path, "wb") as f:
                f.write(resp.content)
        except Exception as e:
            result["issues"].append(f"download_failed:{str(e)[:40]}")
            return result

    # For remote URLs without local_dir, skip dimension check (only domain validation)
    is_remote_no_download = result["is_remote"] and local_path == image_source

    if is_remote_no_download:
        # Remote URL: only domain validation was done above; dimensions not checked
        result["dimensions_checked"] = False
    elif os.path.exists(local_path):
        w, h = get_image_dimensions(local_path)
        result["width"] = w
        result["height"] = h
        if w > 0 and h > 0:
            result["aspect_ratio"] = f"{w}:{h}"

            # 5. Check aspect ratio
            ratio_ok = any(ratio_matches(w, h, r) for r in spec["allowed_ratios"])
            if not ratio_ok:
                allowed = "/".join(f"{r[0]}:{r[1]}" for r in spec["allowed_ratios"])
                result["issues"].append(f"wrong_aspect_ratio:{w}x{h}(need {allowed})")

            # 6. Check minimum resolution
            short_side = min(w, h)
            if short_side < spec["min_short_side"]:
                result["issues"].append(
                    f"low_resolution:{short_side}px(need >={spec['min_short_side']})"
                )

            # 7. Check file size
            try:
                size_mb = os.path.getsize(local_path) / (1024 * 1024)
                if size_mb > spec["max_file_mb"]:
                    result["issues"].append(f"file_too_large:{size_mb:.1f}MB")
                if size_mb < 0.02:  # < 20KB likely placeholder
                    result["issues"].append(f"suspiciously_small:{size_mb*1024:.0f}KB")
            except Exception:
                pass
        else:
            result["issues"].append("unreadable_image")
    elif not is_remote_no_download:
        result["issues"].append("file_not_found")

    # Clean up downloaded temp file
    if result["is_remote"] and local_path != image_source and os.path.exists(local_path):
        try:
            os.remove(local_path)
        except Exception:
            pass

    result["passed"] = len(result["issues"]) == 0
    return result


def validate_posts(posts: list, local_dir: str = None) -> list:
    """
    Validate a list of social media posts.

    Each post dict should have: image (str), platform (str)
    Returns list of validation results.
    """
    results = []
    for post in posts:
        img = post.get("image", post.get("image_url", post.get("cover", "")))
        platform = post.get("platform", post.get("platform_name", "instagram"))
        r = validate_image(img, platform, local_dir)
        r["post_id"] = post.get("id", post.get("post_id", ""))
        results.append(r)
    return results


def main() -> int:
    import argparse
    import json

    ap = argparse.ArgumentParser(description="Social Media Image Validator")
    ap.add_argument("--image", type=str, help="Single image URL or path")
    ap.add_argument("--platform", type=str, default="instagram",
                    choices=list(PLATFORM_SPECS.keys()), help="Target platform")
    ap.add_argument("--posts-file", type=str, help="JSON file with list of posts")
    ap.add_argument("--json", action="store_true", help="JSON output")
    args = ap.parse_args()

    if args.posts_file:
        with open(args.posts_file, encoding="utf-8") as f:
            posts = json.load(f)
        results = validate_posts(posts, local_dir="/tmp/social_img_validate")
        passed = sum(1 for r in results if r["passed"])
        if args.json:
            print(json.dumps({"results": results, "passed": passed,
                              "total": len(results)}, ensure_ascii=False, indent=2))
        else:
            print(f"Social Image Validator: {passed}/{len(results)} passed")
            for r in results:
                mark = "PASS" if r["passed"] else "FAIL"
                print(f"  [{mark}] {r['platform']:12s} {r['image'][:50]}")
                for issue in r["issues"]:
                    print(f"         - {issue}")
        return 0 if passed == len(results) else 1

    if args.image:
        r = validate_image(args.image, args.platform, local_dir="/tmp/social_img_validate")
        if args.json:
            print(json.dumps(r, ensure_ascii=False, indent=2))
        else:
            mark = "PASS" if r["passed"] else "FAIL"
            print(f"[{mark}] {r['platform']}: {r['image']}")
            print(f"  dimensions: {r['width']}x{r['height']} ({r['aspect_ratio']})")
            for issue in r["issues"]:
                print(f"  - {issue}")
        return 0 if r["passed"] else 1

    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
