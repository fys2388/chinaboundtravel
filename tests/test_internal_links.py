"""V6-3: Internal link regression tests.

Ensures:
  - the markdown audit reports 0 broken / 0 redirect-referenced / 0 malformed
  - rendered HTML pages contain no broken internal <a href> or <img src>
"""

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from audit_internal_links import audit  # noqa: E402


def test_markdown_audit_clean():
    result = audit(verbose=False)
    assert result["broken"] == 0, result["links"]
    assert result["redirect"] == 0, result["links"]
    assert result["malformed"] == 0, result["malformed_list"]


@pytest.fixture(scope="module")
def built_site():
    out = Path(tempfile.mkdtemp(prefix="hugo_v63_"))
    try:
        proc = subprocess.run(
            ["hugo", "--gc", "--minify", "--destination", str(out)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("hugo unavailable")
    assert proc.returncode == 0, proc.stderr[-2000:]
    return out


def _collect_valid_paths(out: Path):
    files = set()
    for p in out.rglob("*"):
        if p.is_file():
            files.add("/" + p.relative_to(out).as_posix())
    redirects = {}
    rf = REPO_ROOT / "static" / "_redirects"
    if rf.exists():
        for line in rf.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 3 and parts[0].startswith("/"):
                redirects[parts[0].rstrip("/")] = parts[1].rstrip("/")
    return files, redirects


def _check(target, files, redirects):
    u = target.split("#")[0].split("?")[0]
    if not u.startswith("/"):
        return "ok"
    if u in ("/", "/404.html", "/robots.txt", "/sitemap.xml"):
        return "ok"
    if u in files or (u + "/index.html") in files or (u.rstrip("/") + "/index.html") in files:
        return "ok"
    if u.rstrip("/") in redirects:
        return "redirect"
    return "broken"


def test_rendered_body_links_clean(built_site):
    files, redirects = _collect_valid_paths(built_site)
    issues = []
    for html_file in built_site.rglob("*.html"):
        html = html_file.read_text(encoding="utf-8", errors="replace")
        rel = html_file.relative_to(built_site).as_posix()
        for val in re.findall(r'<(?:a|img)\b[^>]*\b(?:href|src)="([^"]+)"', html):
            if val.startswith(("http://", "https://")):
                p = urlparse(val)
                if p.netloc not in ("www.chinaboundtravel.com", "chinaboundtravel.com"):
                    continue
                val = p.path
            if not val.startswith("/"):
                continue
            status = _check(val, files, redirects)
            if status in ("broken", "redirect"):
                issues.append((rel, val, status))
    assert not issues, issues[:20]

