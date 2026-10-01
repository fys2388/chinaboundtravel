#!/usr/bin/env python3
"""
CI Gate Scanner — 8 checks for chinaboundtravel.com quality gate.
Runs after Hugo build. Writes results to reports/ci_gate_report.json.
Exit code: 0 = all pass, 1 = any fail.

Usage:
    python scripts/ci_gate_scanner.py [--no-build]
    python scripts/ci_gate_scanner.py          # runs build first

Dependencies:
    - Python 3.8+
    - hugo (for build, unless --no-build)
    - PowerShell (for build invocation)

CI integration:
    - GitHub Actions: run after hugo build step
    - Cloudflare Pages: custom build script
    - Local: powershell scripts/ci-gate.ps1
"""

import os
import re
import sys
import json
import time
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / 'public'
CONTENT = ROOT / 'content'
LAYOUTS = ROOT / 'layouts'
REPORTS = ROOT / 'reports'
REPORT_FILE = REPORTS / 'ci_gate_report.json'

# Ensure reports dir exists
REPORTS.mkdir(exist_ok=True)

def run_build():
    """Run hugo build --minify --cleanDestinationDir."""
    print("[build] Running hugo build --minify --cleanDestinationDir ...")
    start = time.time()
    env = os.environ.copy()
    env['WEB3FORMS_ACCESS_KEY'] = 'test'  # placeholder to pass build
    result = subprocess.run(
        ['hugo', 'build', '--minify', '--cleanDestinationDir'],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    duration_ms = int((time.time() - start) * 1000)
    if result.returncode != 0:
        print(f"[build] FAILED (exit {result.returncode})")
        print(result.stderr[-500:] if result.stderr else result.stdout[-500:])
        return {'passed': False, 'duration_ms': duration_ms, 'error': result.stderr[-200:]}
    print(f"[build] PASSED ({duration_ms}ms)")
    return {'passed': True, 'duration_ms': duration_ms}


def walk_html_files(base_dir, pattern=None):
    """Walk all .html files under base_dir. Optionally filter by glob pattern."""
    files = []
    if not base_dir.exists():
        return files
    for root, dirs, fnames in os.walk(base_dir):
        # Skip .archived and hidden dirs
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '.archived']
        for fn in fnames:
            if fn.endswith('.html'):
                fp = Path(root) / fn
                if pattern and not fnmatch_match(fn, pattern):
                    continue
                files.append(fp)
    return files


def fnmatch_match(name, pattern):
    """Simple glob matching for fnames."""
    import fnmatch
    return fnmatch.fnmatch(name, pattern)


def read_file_safe(path):
    """Read file content, return empty string on error."""
    try:
        with open(path, encoding='utf-8', errors='replace') as f:
            return f.read()
    except Exception:
        return ''


def check_no_shortcode_leak():
    """Check 1: No literal {{< shortcode tags in public HTML."""
    count = 0
    offenders = []
    for fp in walk_html_files(PUBLIC):
        text = read_file_safe(fp)
        matches = text.count('{{<')
        if matches > 0:
            count += matches
            rel = fp.relative_to(PUBLIC)
            offenders.append(f"{rel} ({matches}x)")
    passed = count == 0
    return {
        'name': 'no_shortcode_leak',
        'passed': passed,
        'count': count,
        'detail': f"{count} shortcode leaks found" if not passed else "No shortcode leaks",
        'offenders': offenders[:10] if offenders else []
    }


def check_no_html_source_leak():
    """Check 2: No HTML entity-encoded <input> tags in contact page."""
    count = 0
    offenders = []
    # Check public/contact/ directory specifically
    contact_dir = PUBLIC / 'contact'
    if contact_dir.exists():
        for fp in contact_dir.rglob('*.html'):
            text = read_file_safe(fp)
            matches = text.count('&lt;input')
            if matches > 0:
                count += matches
                rel = fp.relative_to(PUBLIC)
                offenders.append(f"{rel} ({matches}x)")
    passed = count == 0
    return {
        'name': 'no_html_source_leak',
        'passed': passed,
        'count': count,
        'detail': f"{count} HTML source leaks in contact/" if not passed else "No HTML source leaks",
        'offenders': offenders[:10] if offenders else []
    }


def check_no_hardcoded_key():
    """Check 3: No hardcoded Web3Forms API keys in public HTML.
    Checks for the actual key prefix (783e3635-...) and access_key with non-empty value."""
    # Patterns: actual key prefix, or access_key="something" (not empty)
    patterns = [
        r'783e3635-[a-f0-9-]+',           # Full key value
        r'access_key["\s]*=[^"/]',         # access_key with non-empty, non-forward-slash value
        r'WEB3FORMS_ACCESS_KEY=[^"\s]+',   # env var set in HTML (shouldn't happen)
    ]
    count = 0
    offenders = []
    for fp in walk_html_files(PUBLIC):
        text = read_file_safe(fp)
        for pat in patterns:
            matches = len(re.findall(pat, text))
            if matches > 0:
                count += matches
                rel = fp.relative_to(PUBLIC)
                offenders.append(f"{rel} (pattern '{pat}' {matches}x)")
                break  # count once per file
    passed = count == 0
    return {
        'name': 'no_hardcoded_key',
        'passed': passed,
        'count': count,
        'detail': f"{count} files with hardcoded keys" if not passed else "No hardcoded keys",
        'offenders': offenders[:10] if offenders else []
    }


def check_contact_form_complete():
    """Check 4: Contact page has <form> and 'Send Message' button."""
    # Find contact page(s)
    contact_files = list((PUBLIC / 'contact').rglob('*.html')) if (PUBLIC / 'contact').exists() else []
    has_form = False
    has_send = False
    details = []

    for fp in contact_files:
        text = read_file_safe(fp)
        if '<form' in text:
            has_form = True
        if 'Send Message' in text:
            has_send = True

    passed = has_form and has_send
    return {
        'name': 'contact_form_complete',
        'passed': passed,
        'count': (1 if has_form else 0) + (1 if has_send else 0),
        'detail': f"form={has_form} send={has_send}",
        'offenders': [] if passed else ['Missing form' if not has_form else '', 'Missing Send Message' if not has_send else '']
    }


def check_subscribe_checkValidity():
    """Check 5: Subscribe form has checkValidity (email validation)."""
    count = 0
    # Search all HTML files for checkValidity
    for fp in walk_html_files(PUBLIC):
        text = read_file_safe(fp)
        matches = text.count('checkValidity')
        if matches > 0:
            count += matches
    passed = count >= 2
    return {
        'name': 'subscribe_checkValidity',
        'passed': passed,
        'count': count,
        'detail': f"{count} checkValidity occurrences (need >= 2)",
        'offenders': [] if passed else [f"Only {count} checkValidity found"]
    }


def check_posts_have_comments():
    """Check 6: Posts have comments section (id=comments or id="comments")."""
    count = 0
    total_posts = 0
    missing = []
    posts_dir = PUBLIC / 'posts'
    if posts_dir.exists():
        for entry in posts_dir.iterdir():
            if not entry.is_dir():
                continue
            idx = entry / 'index.html'
            if not idx.exists():
                continue
            total_posts += 1
            text = read_file_safe(idx)
            # Hugo minifier may strip quotes: id=comments or id="comments"
            if 'id=comments' in text or 'id="comments"' in text:
                count += 1
            else:
                missing.append(str(entry.name))
    # Threshold: at least 50 posts (task says >= 50)
    passed = count >= 50
    return {
        'name': 'posts_have_comments',
        'passed': passed,
        'count': count,
        'detail': f"{count}/{total_posts} posts have comments section (need >= 50)",
        'offenders': missing[:10] if missing else []
    }


def check_robots_no_leak():
    """Check 7: robots.txt has no internal data leakage in comments.
    Only scans lines starting with # (comments), not Disallow/Allow/User-agent directives."""
    robots_path = LAYOUTS / 'robots.txt'
    if not robots_path.exists():
        return {
            'name': 'robots_no_leak',
            'passed': False,
            'count': 1,
            'detail': 'robots.txt not found',
            'offenders': ['File missing']
        }
    text = read_file_safe(robots_path)
    # Only scan comment lines (starting with #)
    comment_lines = [l for l in text.split('\n') if l.strip().startswith('#')]
    comment_text = '\n'.join(comment_lines)
    # Note: 'agent' excluded — matches legitimate User-agent entries
    patterns = [r'ops-dashboard', r'pageviews', r'GA4', r'173 pv', r'34\.5%', r'owner', r'虚高']
    count = 0
    offenders = []
    for pat in patterns:
        matches = len(re.findall(pat, comment_text))
        if matches > 0:
            count += matches
            offenders.append(f"Pattern '{pat}' found {matches}x in comments")
    passed = count == 0
    return {
        'name': 'robots_no_leak',
        'passed': passed,
        'count': count,
        'detail': f"{count} internal data patterns in comments" if not passed else "No internal data leaks in comments",
        'offenders': offenders[:10] if offenders else []
    }


def check_no_broken_links():
    """Check 8: No broken internal links in content markdown files."""
    broken = []
    # Find all markdown files in content/
    for root, dirs, fnames in os.walk(CONTENT):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '.archived']
        for fn in fnames:
            if not fn.endswith('.md'):
                continue
            fp = Path(root) / fn
            text = read_file_safe(fp)
            # Find markdown links: [text](/path)
            for m in re.finditer(r'\[([^\]]+)\]\((/[^\)]+)\)', text):
                link = m.group(2).split('#')[0]  # remove anchor
                if not link:
                    continue
                # Check if target exists in public/
                target = PUBLIC / link.strip('/')
                if not target.exists() and not (target / 'index.html').exists() and not (target + '.html').exists():
                    rel = fp.relative_to(CONTENT)
                    broken.append(f"{rel} -> {link}")
    passed = len(broken) == 0
    return {
        'name': 'no_broken_links',
        'passed': passed,
        'count': len(broken),
        'detail': f"{len(broken)} broken internal links" if not passed else "No broken internal links",
        'offenders': broken[:10] if broken else []
    }


def main():
    print("=" * 60)
    print("CI Gate Scanner — chinaboundtravel.com")
    print("=" * 60)

    # Parse args
    no_build = '--no-build' in sys.argv

    # Run build if requested
    build_result = None
    if not no_build:
        build_result = run_build()
        if not build_result.get('passed', False):
            print("\n[build] FAILED — aborting scan")
            # Still write a report with build failure
            report = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'build': build_result,
                'checks': [],
                'summary': {'total': 8, 'passed': 0, 'failed': 0, 'build_failed': True}
            }
            REPORT_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
            sys.exit(1)

    # Run all checks
    print("\n[scan] Running 8 checks...")
    checks = []
    check_funcs = [
        ('no_shortcode_leak', check_no_shortcode_leak),
        ('no_html_source_leak', check_no_html_source_leak),
        ('no_hardcoded_key', check_no_hardcoded_key),
        ('contact_form_complete', check_contact_form_complete),
        ('subscribe_checkValidity', check_subscribe_checkValidity),
        ('posts_have_comments', check_posts_have_comments),
        ('robots_no_leak', check_robots_no_leak),
        ('no_broken_links', check_no_broken_links),
    ]

    for name, func in check_funcs:
        try:
            result = func()
            status = 'PASS' if result['passed'] else 'FAIL'
            print(f"  [{status}] {result['name']}: {result['detail']}")
            checks.append(result)
        except Exception as e:
            print(f"  [ERR]  {name}: {e}")
            checks.append({
                'name': name,
                'passed': False,
                'count': 0,
                'detail': f"Exception: {e}",
                'offenders': []
            })

    # Summary
    total = len(checks)
    passed = sum(1 for c in checks if c['passed'])
    failed = total - passed
    print(f"\n{'=' * 60}")
    print(f"SUMMARY: {passed}/{total} passed, {failed} failed")
    print(f"{'=' * 60}")

    if failed > 0:
        print("\nFAILED CHECKS:")
        for c in checks:
            if not c['passed']:
                print(f"  - {c['name']}: {c['detail']}")
                if c.get('offenders'):
                    for o in c['offenders'][:3]:
                        print(f"      {o}")

    # Write report
    report = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'build': build_result,
        'checks': checks,
        'summary': {'total': total, 'passed': passed, 'failed': failed}
    }
    REPORTS.mkdir(exist_ok=True)
    REPORT_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"\n[report] Written to {REPORT_FILE.relative_to(ROOT)}")

    sys.exit(0 if failed == 0 else 1)


if __name__ == '__main__':
    main()
