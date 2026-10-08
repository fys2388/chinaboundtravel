"""
P0-2: Cover Gate - blocking cover check for newly generated articles.
Only checks new/modified articles; missing cover or external AI image domain blocks commit.
"""
import sys
import re
import subprocess
from pathlib import Path

POSTS_DIR = Path("content/posts")
BLOCKED_IMAGE_DOMAINS = [
    "pollinations.ai", "image.pollinations.ai", "lexica.art",
    "midjourney", "dalle", "stablediffusion", "craiyon.com",
    "shturl.cc", "hflb9",
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
    """Check cover of a single article. Returns dict with issues.
    Supports both YAML (---) and TOML (+++) front matter formats."""
    text = post_path.read_text(encoding="utf-8", errors="replace")
    issues = []
    cover_ok = False
    cover_image = ""

    # Detect front matter format: YAML (---) or TOML (+++)
    fm_match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    is_toml = False
    if not fm_match:
        fm_match = re.match(r"^\+\+\+\s*\n(.*?)\n\+\+\+", text, re.DOTALL)
        is_toml = True

    if fm_match:
        fm = fm_match.group(1)
        in_cover = False
        for line in fm.split("\n"):
            stripped = line.strip()
            if is_toml:
                # TOML format: [cover] section, then image = "..."
                if stripped == "[cover]":
                    in_cover = True
                    continue
                if in_cover and stripped.startswith("image") and "=" in stripped:
                    raw = stripped.split("=", 1)[1].strip()
                    cover_image = raw.strip('"').strip("'")
                    cover_ok = True
                    break
                if in_cover and stripped.startswith("["):
                    in_cover = False
            else:
                # YAML format: cover: then image: "..."
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

    # NOTE: no mtime fallback. In CI a fresh checkout gives every file an
    # mtime equal to checkout time, so an mtime check always passes and
    # turns this gate into a full-repo audit. An empty `git diff HEAD`
    # means "no new/modified posts in this change" — that is the correct
    # signal to skip the gate, not a trigger to fall back to filesystem mtime.
    # For local dev, use `git log --since=24.hours --name-only -- content/posts/`
    # if you need a broader audit.

    if not new_posts:
        print("  No new articles, cover check passed")
    else:
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

    # Non-blocking audit: warn about all posts missing a cover.
    # This does NOT affect the exit code — it's for humans to triage.
    print()
    print("  [warn] Full-repo cover audit (non-blocking):")
    all_missing = []
    for p in sorted(POSTS_DIR.glob("*.md")):
        r = check_cover(p)
        if not r["passed"]:
            all_missing.append(r)
    if not all_missing:
        print("    All posts have covers.")
    else:
        print(f"    {len(all_missing)} post(s) missing cover or using blocked image domain:")
        for r in all_missing:
            print(f"      - {r['file']}")
            for issue in r["issues"]:
                print(f"          issue: {issue}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
