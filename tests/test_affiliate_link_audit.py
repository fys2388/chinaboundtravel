"""联盟链接 tracking 覆盖率审计的回归测试。

守护 2026-09-18 的修复：联盟链接不带 tracking 参数时点击不会被归因、佣金恒为 0，
但日报只报「6 次点击 0 成交」，会被误读成转化率问题。审计必须能把这件事浮出来。
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import affiliate_link_audit as A  # noqa: E402


# ── 配置解析 ────────────────────────────────────────────────

def test_loads_affiliate_config_from_hugo_toml():
    cfg = A.load_affiliate_config(ROOT)
    # 真实仓库里这些 key 必须存在
    for key in ("esim", "vpn", "hotel", "klook", "safetywing", "flight"):
        assert key in cfg, f"hugo.toml [params.affiliate] 缺少 key: {key}"
    assert "klook_expire_date" in cfg  # 非 URL 的辅助字段也被解析


def test_config_values_are_urls_not_comments():
    """行内注释不得泄漏进 URL 值（tomllib 不可用时的行解析陷阱）。"""
    cfg = A.load_affiliate_config(ROOT)
    for key, url in cfg.items():
        if key == "klook_expire_date":
            continue
        assert "#" not in url, f"{key} 的 URL 混入了注释文本: {url}"


# ── tracking 判定 ──────────────────────────────────────────

@pytest.mark.parametrize("url,expected", [
    ("https://www.booking.com/index.html?aid=730795", True),
    ("https://www.aviasales.com/?marker=730795", True),
    ("https://klook.tpo.li/vrPkmS2v", True),
    ("https://get.affiliatescn.net/aff_c?offer_id=153&aff_id=150687", True),
    ("https://safetywing.com/nomad-insurance?referenceID=26548976", True),
    ("https://www.airalo.com/", False),           # ⚠️ 全站最大漏点
    ("https://www.trip.com/", False),
    ("https://www.worldnomads.com/", False),
    ("https://www.nordpass.com/", False),
])
def test_tracking_detection(url, expected):
    assert A._is_tracked(url) is expected, url


@pytest.mark.parametrize("url", [
    "https://twitter.com/intent/tweet?url=...&text=...",
    "https://www.facebook.com/sharer/sharer.php?u=...",
    "https://t.me/share/url?url=...&text=...",
    "mailto:?subject=...&body=...",
])
def test_share_links_are_not_counted_as_affiliate(url):
    """社交分享按钮不是联盟链接，不能拉低覆盖率。"""
    assert A._is_tracked(url) is True


# ── 裸链接扫描的作用域 ────────────────────────────────────

def test_raw_url_scan_ignores_non_partner_domains(tmp_path):
    """关键回归：不得把所有未跟踪外链（签证官网/新闻/维基）都算成联盟失败。"""
    (tmp_path / "content").mkdir(parents=True)
    (tmp_path / "content" / "post.md").write_text(
        "# 文章\n"
        "[签证官网](https://www.visaforchina.cn/)\n"           # 政府/编辑性外链
        "[新闻](https://www.chinadaily.com.cn/a/2026/09/01)\n"  # 媒体外链
        "[eSIM](https://www.airalo.com/)\n"                    # ⚠️ 联盟裸链
        "[eSIM again](https://www.airalo.com/?ref=12345)\n"    # 带 tracking，不算
    , encoding="utf-8")
    hosts = ["www.airalo.com"]
    usage = A.count_key_usage(tmp_path, hosts)
    assert usage.get("(raw-untracked-url)") == 1, (
        "只有 airalo 裸链接该被计入；签证官网和新闻媒体不是联盟链接"
    )


def test_empty_content_reports_zero_not_error(tmp_path):
    (tmp_path / "content").mkdir(parents=True)
    (tmp_path / "content" / "a.md").write_text("no links here", encoding="utf-8")
    result = A.audit(tmp_path)
    assert result["links_total"] == 0
    assert result["untracked_ratio"] == 0.0
    assert result["blocking"] is False


# ── 全量审计 ───────────────────────────────────────────────

def test_real_repo_has_untracked_keys_and_reports_them():
    """真实仓库当前应存在未跟踪联盟链接，审计必须点名而不是沉默。"""
    result = A.audit(ROOT)
    assert result["links_total"] > 0
    # 已知事实：esim（裸 airalo）与 trip 未带 tracking
    for key in ("esim", "trip"):
        assert key in result["untracked_keys"], (
            f"{key} 在 hugo.toml 里无 tracking 参数，审计必须报告它"
        )
    assert result["blocking"] is True


def test_audit_structure_is_stable_for_json_consumers():
    result = A.audit(ROOT)
    for field in ("keys_total", "keys_tracked", "keys_untracked",
                  "links_tracked", "links_untracked", "links_total",
                  "untracked_ratio", "raw_untracked_urls", "untracked_keys",
                  "per_key", "blocking"):
        assert field in result, f"缺少字段 {field}"
    # JSON 可序列化（供 --json 与 CI 消费）
    json.dumps(result, ensure_ascii=False)


# ── CLI ────────────────────────────────────────────────────

def _run(*extra):
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "affiliate_link_audit.py"), *extra],
        capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT),
    )


def test_cli_json_is_valid_and_has_stats():
    r = _run("--json")
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert data["links_total"] > 0
    assert isinstance(data["untracked_ratio"], float)


def test_cli_plain_output_names_the_offending_keys():
    r = _run()
    assert r.returncode == 0
    assert "tracking 覆盖率" in r.stdout
    assert "esim" in r.stdout, "输出必须点名 esim，否则运维不知道去哪修"


def test_cli_fail_exits_nonzero_when_untracked_exist():
    r = _run("--fail")
    assert r.returncode == 1, (
        "--fail 在存在未跟踪链接时必须 exit 1，才能被 CI 当作质量闸门"
    )
