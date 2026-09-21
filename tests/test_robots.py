"""V6-4: robots.txt regression tests.

Requires a Hugo build (no network, no deploy):
  - robots.txt exists at the site root (serves 200)
  - content is valid and references the correct sitemap
  - important pages are not blocked by obviously wrong Disallow rules
"""

import subprocess
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

SITEMAP_EXPECTED = "https://www.chinaboundtravel.com/sitemap.xml"


@pytest.fixture(scope="module")
def built_robots(tmp_path_factory):
    out = tmp_path_factory.mktemp("hugo_robots_")
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


def _robots_groups(text):
    """Parse robots.txt into ordered groups: [{'user_agents': [...], 'rules': [...]}].

    robots.txt is grouped per user-agent; a `Disallow: /` in the AI-training-bot
    group is intentional (see GEO notes in layouts/robots.txt) and must not be
    confused with blocking the site for everyone.
    """
    groups = []
    current = None
    for raw in text.splitlines():
        ln = raw.strip()
        if not ln or ln.lower().startswith("#"):
            continue
        key, _, value = ln.partition(":")
        key, value = key.strip().lower(), value.strip()
        if key == "user-agent":
            if current is None or current["rules"]:
                current = {"user_agents": [], "rules": []}
                groups.append(current)
            current["user_agents"].append(value)
        else:
            if current is None:
                current = {"user_agents": [], "rules": []}
                groups.append(current)
            current["rules"].append(ln)
    return groups


def _disallows(group):
    return {ln.split(":", 1)[1].strip() for ln in group["rules"] if ln.lower().startswith("disallow")}


def test_robots_txt_exists(built_robots):
    assert (built_robots / "robots.txt").exists(), "public/robots.txt not generated"


def test_robots_txt_valid(built_robots):
    text = (built_robots / "robots.txt").read_text(encoding="utf-8")
    assert "User-agent: *" in text
    assert "Allow: /" in text
    # sitemap reference must point to the canonical domain
    assert "Sitemap:" in text
    assert SITEMAP_EXPECTED in text, text


def test_robots_txt_sitemap_reference_correct(built_robots):
    text = (built_robots / "robots.txt").read_text(encoding="utf-8")
    sitemap_lines = [ln for ln in text.splitlines() if ln.lower().startswith("sitemap")]
    assert sitemap_lines, "missing Sitemap directive"
    assert any(SITEMAP_EXPECTED in ln for ln in sitemap_lines)


def test_robots_txt_does_not_block_important_pages(built_robots):
    text = (built_robots / "robots.txt").read_text(encoding="utf-8")
    # 只判定兜底组（User-agent: *）。
    # 生产 robots.txt 按 GEO 策略在「AI 训练爬虫」组里用 Disallow: / 拦截
    # GPTBot / ClaudeBot / Google-Extended / CCBot 等（layouts/robots.txt 有说明，勿删），
    # 跨组收集所有 Disallow 会把既有策略误报成"整站被屏蔽"。
    groups = _robots_groups(text)
    wildcards = [g for g in groups if "*" in g["user_agents"]]
    assert wildcards, "robots.txt missing the 'User-agent: *' catch-all group"
    for g in wildcards:
        assert "/" not in _disallows(g), f"catch-all group blocks the whole site: {g}"
    for section in ("/posts", "/cities", "/visa", "/pricing", "/about"):
        for g in wildcards:
            blocked = {d.lower().rstrip("/") for d in _disallows(g)}
            assert section.rstrip("/") not in blocked, f"{section} wrongly blocked by {g['user_agents']}"


def test_ai_training_bots_remain_blocked():
    """GEO 策略回归保护：AI 训练爬虫必须保持阻断，通用爬虫必须放行。"""
    text = Path(REPO_ROOT, "layouts", "robots.txt").read_text(encoding="utf-8")
    groups = _robots_groups(text)
    wildcards = [g for g in groups if "*" in g["user_agents"]]
    assert wildcards, "missing catch-all group"
    assert all("/" not in _disallows(g) for g in wildcards), "catch-all must allow the site"

    by_agent = {}
    for g in groups:
        for ua in g["user_agents"]:
            if ua != "*":
                by_agent.setdefault(ua, set()).update(_disallows(g))
    training_bots = ("GPTBot", "ClaudeBot", "Google-Extended", "CCBot")
    missing = [b for b in training_bots if "/" not in by_agent.get(b, set())]
    assert not missing, f"GEO 策略被破坏，以下 AI 训练爬虫不再被阻断：{missing}"
