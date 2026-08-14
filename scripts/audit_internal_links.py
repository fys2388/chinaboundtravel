import os, re, sys, json, glob
from collections import Counter

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(REPO, 'content')
STATIC = os.path.join(REPO, 'static')
LAYOUTS = os.path.join(REPO, 'layouts')
REDIRECTS_FILE = os.path.join(STATIC, '_redirects')
SKIP_DIRS = {'.archived', '.audit_backup', 'drafts', '_draft', '.git'}
DATE_PREFIX = re.compile(r'^\d{4}-\d{2}-\d{2}-')

# --------------------------------------------------------------------------
# URL map construction
# --------------------------------------------------------------------------

def slug_from_fm(text, default):
    m = re.search(r'^slug:\s*["\']?([^"\'\n#]+)', text, re.M)
    if m:
        return m.group(1).strip().strip('"\'')
    return DATE_PREFIX.sub('', default)

def build_content_urls():
    urls = set()
    file_to_url = {}
    for root_dir, dirs, files in os.walk(CONTENT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in files:
            if not fn.endswith('.md'):
                continue
            fp = os.path.join(root_dir, fn)
            rel = os.path.relpath(fp, CONTENT).replace('\\', '/')
            with open(fp, encoding='utf-8', errors='replace') as fh:
                text = fh.read(2000)
            parts = rel.split('/')
            if fn == '_index.md':
                url = '/' + '/'.join(parts[:-1]) + ('/' if parts[:-1] else '/')
                if url == '//':
                    url = '/'
                urls.add(normalize(url))
                file_to_url[fp] = normalize(url)
            else:
                base = fn[:-3]
                slug = slug_from_fm(text, base)
                if parts[0] == 'posts':
                    url = f'/posts/{slug}/'
                else:
                    url = '/' + '/'.join(parts[:-1] + [slug]) + '/'
                urls.add(normalize(url))
                file_to_url[fp] = normalize(url)
    return urls, file_to_url

def build_static_urls():
    urls = set()
    for root_dir, dirs, files in os.walk(STATIC):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in files:
            rel = os.path.relpath(os.path.join(root_dir, fn), STATIC).replace('\\', '/')
            urls.add('/' + rel)
    return urls

def build_redirect_map():
    mapping = {}
    try:
        with open(REDIRECTS_FILE, encoding='utf-8') as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split()
                if len(parts) >= 3 and parts[0].startswith('/'):
                    mapping[normalize(parts[0])] = normalize(parts[1])
    except FileNotFoundError:
        pass
    return mapping

def normalize(url):
    u = url.split('#')[0].split('?')[0].strip()
    if len(u) > 1 and u.endswith('/'):
        u = u[:-1]
    return u

KNOWN_SPECIAL = {
    '/', '/404.html', '/robots.txt', '/sitemap.xml', '/favicon.ico',
    '/manifest.json', '/site.webmanifest', '/search', '/contact',
    '/pricing', '/privacy-policy', '/affiliate-disclosure',
    '/posts', '/guides', '/internet', '/payments', '/visa',
    '/resources', '/about', '/cities', '/ebook',
    '/member-month', '/member-year', '/static-package',
    '/categories', '/tags',
}

def classify(url, content_urls, static_urls, redirect_map):
    n = normalize(url)
    if n in content_urls or n in static_urls or n in KNOWN_SPECIAL:
        return '200', None
    if n in redirect_map:
        return '301', redirect_map[n]
    # tags/categories are generated from front matter; treat as valid taxonomy
    if n.startswith('/tags/') or n.startswith('/categories/'):
        return 'taxonomy', None
    return '404', None

# --------------------------------------------------------------------------
# Link extraction
# --------------------------------------------------------------------------

LINK_RE = re.compile(r'\[([^\]]*)\]\(([^)]*)\)')

def extract_md_links(text):
    """Return list of (link_text, url, ok)."""
    out = []
    for m in LINK_RE.finditer(text):
        url = m.group(2).strip()
        if not url:
            continue
        out.append((m.group(1), url, True))
    return out

def extract_fm_image_links(line):
    """Front-matter image/cover references in TOML or YAML blocks."""
    out = []
    for m in re.finditer(r'^\s*(?:image|og_image|thumbnail|featured_image)\s*=\s*["\']([^"\']+)["\']', line):
        out.append(('', m.group(1), True))
    for m in re.finditer(r'^\s*image:\s*["\']?([^"\'\n]+)["\']?', line):
        out.append(('', m.group(1).strip(), True))
    for m in re.finditer(r'^\s*cover:\s*$', line):
        pass
    return out


def find_malformed(text):
    """Heuristic detection of clearly malformed markdown links."""
    issues = []
    # dangling '](' with no closing ')' on the same line
    for m in re.finditer(r'\]\(([^)\n]*)$', text):
        issues.append(('missing-closing-paren', m.group(1)[:120]))
    # '](' immediately followed by another '[' (merged links)
    for m in re.finditer(r'\]\((\[[^\]]*\]\([^)]*\))[^)]*\)', text):
        issues.append(('merged-link', m.group(1)[:120]))
    # link URL containing a '[' or ']' (nested link artifacts)
    for m in re.finditer(r'\]\(([^)\n]*\[[^)\n]*\))', text):
        issues.append(('nested-bracket-in-url', m.group(1)[:120]))
    # http(s) URL containing spaces (broken word-wrapped links)
    for m in re.finditer(r'\]\((https?://\S*\s+\S*)\)', text):
        issues.append(('space-in-url', m.group(1)[:120]))
    # 'Internal Link N:' placeholder wrappers
    if re.search(r'\[Internal Link \d+:', text):
        issues.append(('internal-link-placeholder', text.strip()[:120]))
    # stray '](url)' closure without an opening '[' after another link
    for m in re.finditer(r'\]\([^)\n]*\)[^\[\n]*\]\([^)\n]*\)', text):
        issues.append(('dangling-link-closure', m.group(0)[:120]))
    # double-bracket nested links like [[text](url)...](url)
    for m in re.finditer(r'\[\[[^\]]*\]\([^)]*\)', text):
        issues.append(('nested-double-link', m.group(0)[:120]))
    return issues

def extract_layout_links(text):
    out = []
    for m in re.finditer(r'(?:href|src|action)\s*=\s*["\']([^"\']+)["\']', text):
        out.append(('', m.group(1), True))
    for m in re.finditer(r"url\(\s*['\"]?([^'\")\s]+)['\"]?\s*\)", text):
        out.append(('', m.group(1), True))
    return out

# --------------------------------------------------------------------------
# Audit
# --------------------------------------------------------------------------

def is_internal(url):
    if url.startswith('/'):
        return True
    if url.startswith('https://www.chinaboundtravel.com/') or url.startswith('http://www.chinaboundtravel.com/'):
        return True
    if url.startswith('https://chinaboundtravel.com/') or url.startswith('http://chinaboundtravel.com/'):
        return True
    return False

def to_local(url):
    for prefix in ('https://www.chinaboundtravel.com', 'http://www.chinaboundtravel.com',
                   'https://chinaboundtravel.com', 'http://chinaboundtravel.com'):
        if url.startswith(prefix):
            return url[len(prefix):]
    return url

def audit(verbose=True):
    content_urls, file_to_url = build_content_urls()
    static_urls = build_static_urls()
    redirect_map = build_redirect_map()

    rows = []          # (source, line, target, status, suggested)
    malformed = []     # (source, line, kind, snippet)
    stats = Counter()

    files = []
    for root_dir, dirs, fns in os.walk(CONTENT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in fns:
            if fn.endswith('.md'):
                files.append(os.path.join(root_dir, fn))
    for root_dir, dirs, fns in os.walk(LAYOUTS):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in fns:
            if fn.endswith(('.html', '.xml', '.json')):
                files.append(os.path.join(root_dir, fn))
    assets_dir = os.path.join(REPO, 'assets')
    for root_dir, dirs, fns in os.walk(assets_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in fns:
            if fn.endswith(('.css', '.scss', '.js', '.ts')):
                files.append(os.path.join(root_dir, fn))

    for fp in sorted(files):
        rel = os.path.relpath(fp, REPO).replace('\\', '/')
        with open(fp, encoding='utf-8', errors='replace') as fh:
            lines = fh.readlines()
        text = ''.join(lines)
        is_layout = '/layouts/' in rel
        for i, line in enumerate(lines, 1):
            if is_layout or rel.startswith('assets/'):
                links = extract_layout_links(line)
            else:
                links = extract_md_links(line)
                links += extract_fm_image_links(line)
            for kind, snippet in find_malformed(line):
                malformed.append((rel, i, kind, snippet))
            for link_text, url, _ok in links:
                if not is_internal(url):
                    continue
                url = to_local(url)
                status, suggested = classify(url, content_urls, static_urls, redirect_map)
                stats[status] += 1
                if status in ('404', '301', 'taxonomy'):
                    rows.append((rel, i, url, status, suggested))

    if verbose:
        print('=== Internal Link Audit ===')
        print(f'total internal links: {sum(stats.values())}')
        print(f'200/static: {stats.get("200", 0)}')
        print(f'301 (redirect target needed): {stats.get("301", 0)}')
        print(f'taxonomy: {stats.get("taxonomy", 0)}')
        print(f'404: {stats.get("404", 0)}')
        print(f'malformed links: {len(malformed)}')
        print()
        print('--- 404 / 301 links ---')
        for rel, line, url, status, suggested in rows:
            sug = f'  -> suggest: {suggested}' if suggested else ''
            print(f'{status}  {rel}:{line}  {url}{sug}')
        if malformed:
            print()
            print('--- malformed links ---')
            for rel, line, kind, snippet in malformed:
                print(f'{kind}  {rel}:{line}  {snippet}')

    result = {
        'total': sum(stats.values()),
        'ok': stats.get('200', 0),
        'redirect': stats.get('301', 0),
        'taxonomy': stats.get('taxonomy', 0),
        'broken': stats.get('404', 0),
        'malformed': len(malformed),
        'links': [{'source': r, 'line': l, 'target': t, 'status': s, 'suggested': g}
                  for r, l, t, s, g in rows],
        'malformed_list': [{'source': r, 'line': l, 'kind': k, 'snippet': sn}
                           for r, l, k, sn in malformed],
    }
    return result

if __name__ == '__main__':
    if '--audit' in sys.argv:
        result = audit(verbose=True)
        out = os.path.join(REPO, 'docs', 'internal_link_audit.json')
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, 'w', encoding='utf-8') as fh:
            json.dump(result, fh, ensure_ascii=False, indent=2)
        print()
        print('wrote', os.path.relpath(out, REPO))
    else:
        print(__doc__)

