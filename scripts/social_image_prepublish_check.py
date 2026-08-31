"""
P0: Social Media Image Pre-Publish Validator
Standalone script for workflow integration. Validates pending social posts' images.
Usage: python scripts/social_image_prepublish_check.py [--strict]
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from social_content_agent import load_inventory, filter_items
    from social_image_validator import validate_image
    AVAILABLE = True
except ImportError as e:
    AVAILABLE = False
    IMPORT_ERROR = str(e)


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Social Image Pre-Publish Validator")
    ap.add_argument("--strict", action="store_true",
                    help="Exit 1 if any image fails validation (blocking mode)")
    ap.add_argument("--limit", type=int, default=30, help="Max items to check")
    args = ap.parse_args()

    print("=== P0: Social Media Image Pre-Publish Validation ===")

    if not AVAILABLE:
        print(f"  SKIP: dependencies not available ({IMPORT_ERROR})")
        return 0

    try:
        data = load_inventory()
    except Exception as e:
        print(f"  SKIP: inventory load failed: {e}")
        return 0

    pending = filter_items(data, status="待审核")
    if not pending:
        print("  No pending items to validate")
        return 0

    print(f"  Checking {min(len(pending), args.limit)} pending items...")
    issues = []
    passed = 0

    for item in pending[:args.limit]:
        img = (item.get("image_url") or "").strip()
        platform = item.get("platform", "instagram")
        item_id = item.get("id", "?")

        if not img:
            issues.append({"id": item_id, "platform": platform,
                           "issues": ["missing_image_url"]})
            continue

        r = validate_image(img, platform)
        if r["passed"]:
            passed += 1
        else:
            issues.append({"id": item_id, "platform": platform,
                           "issues": r["issues"], "dimensions": f"{r['width']}x{r['height']}"})

    total = min(len(pending), args.limit)
    print(f"\n  Results: {passed}/{total} passed, {len(issues)} failed")

    if issues:
        print("\n  Failed items:")
        for i in issues[:10]:
            dims = i.get("dimensions", "?")
            print(f"    - [{i['platform']:10s}] {i['id'][:30]:32s} {dims:12s} {'; '.join(i['issues'][:2])}")
        if len(issues) > 10:
            print(f"    ... and {len(issues) - 10} more")

    if args.strict and issues:
        print(f"\n  STRICT MODE: {len(issues)} image(s) failed validation, blocking publish")
        return 1

    print("\n  Validation complete (non-blocking mode)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
