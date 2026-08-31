"""
P0-2: Cover Gate - blocking cover check for newly generated articles.
Only checks new/modified articles; missing cover or external AI image domain blocks commit.
"""
import sys
import re
import subprocess
import time
from pathlib import Path

POSTS_DIR = Path("content/posts")
BLOCKED_IMAGE_DOMAINS = [
    "pollinations.ai", "image.pollinations.ai", "lexica.art",
    "midjourney", "dalle", "stablediffusion", "craiyon.com",
]
LOCAL_IMAGE_DOMAIN = "chinaboundtravel.com"


def get_new_or_modified_posts():
    """Get newly created or modified article files via git."""
    posts = []
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD", "--", "content/posts/"],
            capture_output=True, text=True, timeout=10
        )
        changed = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
        result2 = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard", "--", "content/posts/"],
            capture_output=True, text=True, timeout=10
        )
        untracked = [f.strip() for f in result2.stdout.strip().split("\n") if f.strip()]
        all_changed = list(set(changed + untracked))
        for f in all_changed:
            p = Path(f)
            if p.suffix == ".md" and p.exists():
                posts.append(p)
    except Exception as e:
        print(f"  [cover_gate] git diff failed: {e}")
    return posts


def check_cover(post_path):
    """Check cover of a single article. Returns dict with issues."""
    text = post_path.read_text(encoding="utf-8", errors="replace")
    fm_match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    issues = []
    cover_ok = False
    cover_image = ""

    if fm_match:
        fm = fm_match.group(1)
        in_cover = False
        for line in fm.split("\n"):
            stripped = line.strip()
            if stripped.startswith("cover:"):
                in_cover = True
                continue
            if in_cover and stripped.startswith("image:"):
                raw = stripped.split(":", 1)[1].strip()
                cover_image = raw.strip('"').strip("'")
                cover_ok = True
                break
            if in_cover and stripped and not stripped.startswith(" "):
                in_cover = False

    if not cover_ok:
        issues.append("missing_cover")
    if cover_image:
        is_blocked = any(d in cover_image.lower() for d in BLOCKED_IMAGE_DOMAINS)
        is_local = LOCAL_IMAGE_DOMAIN in cover_image.lower()
        if is_blocked:
            issues.append("blocked_ai_image_domain")
        elif not is_local and cover_image.startswith("http"):
            issues.append("external_image_domain")

    return {
        "file": post_path.name,
        "cover_ok": cover_ok,
        "cover_image": cover_image,
        "issues": issues,
        "passed": len(issues) == 0,
    }


def main():
    print("=== P0-2 Cover Gate: new article cover check ===")

    new_posts = get_new_or_modified_posts()

    # Fallback: if git shows no changes, check posts modified in last 24h
    if not new_posts:
        now = time.time()
        for p in sorted(POSTS_DIR.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True):
            if now - p.stat().st_mtime < 86400:
                new_posts.append(p)
        if new_posts:
            print(f"  (fallback: checking {len(new_posts)} posts modified in last 24h)")

    if not new_posts:
        print("  No new articles, cover check passed")
        return 0

    print(f"  Checking {len(new_posts)} new/modified articles:")
    failed = 0
    for post in new_posts:
        r = check_cover(post)
        status = "PASS" if r["passed"] else "FAIL"
        if not r["passed"]:
            failed += 1
        print(f"    [{status}] {r['file'][:50]}")
        for issue in r["issues"]:
            print(f"           - {issue}")
        if r["cover_image"] and not r["passed"]:
            print(f"           cover: {r['cover_image'][:70]}")

    print()
    if failed > 0:
        print(f"  FAIL: {failed}/{len(new_posts)} new articles have cover issues")
        print("     Add a cover or replace external AI image domain, then retry")
        print("     Block reasons: missing_cover / blocked_ai_image_domain / external_image_domain")
        return 1
    else:
        print(f"  PASS: {len(new_posts)} new articles all have valid covers")
        return 0


if __name__ == "__main__":
    sys.exit(main())
