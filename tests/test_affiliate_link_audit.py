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

def _repo_with_untracked_key(tmp_path):
    """构造一个含未跟踪联盟链接的最小仓库。

    上报逻辑必须对着受控输入验证，而不是断言真实仓库当前的状态：2026-09-21 把
    esim 升级为带 tracking 的深链、trip 等无联盟计划的 key 一并移除，
    「真实仓库必须报 esim」这类断言会在缺陷被修好的当天就红。
    """
    (tmp_path / "content").mkdir(parents=True)
    (tmp_path / "hugo.toml").write_text(
        "[params]\n"
        "  [params.affiliate]\n"
        "    esim = \"https://www.airalo.com/\"\n"
        "    hotel = \"https://www.booking.com/index.html?aid=730795\"\n",
        encoding="utf-8",
    )
    (tmp_path / "content" / "post.md").write_text(
        "{{< affiliate-link partner=\"esim\" text=\"eSIM\" >}}\n"
        "{{< affiliate-link partner=\"hotel\" text=\"Hotel\" >}}\n",
        encoding="utf-8",
    )
    return tmp_path


def test_audit_reports_untracked_referenced_keys(tmp_path):
    """未跟踪且被引用的 key 必须被点名，不能沉默；带 tracking 的不算。"""
    result = A.audit(_repo_with_untracked_key(tmp_path))
    assert result["untracked_keys"] == ["esim"], result["untracked_keys"]
    assert result["blocking"] is True


def test_real_repo_audit_is_coherent():
    """真实仓库：审计可运行、统计字段自洽、blocking 与数据一致。"""
    result = A.audit(ROOT)
    assert result["links_total"] > 0
    assert result["keys_untracked"] <= result["keys_total"]
    assert result["links_tracked"] + result["links_untracked"] == result["links_total"]
    assert result["untracked_ratio"] == round(
        result["links_untracked"] / result["links_total"], 4
    )
    assert result["blocking"] is bool(result["links_untracked"] > 0)
    # 点名的 key 必须是「未跟踪且被引用」的子集
    for k in result["untracked_keys"]:
        row = next(r for r in result["per_key"] if r["key"] == k)
        assert not row["tracked"] and row["usage"] > 0


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


def test_cli_plain_output_matches_the_audit():
    """CLI 与 audit() 结论一致：有问题就点名/警告，全干净才打勾。

    原先直接断言输出含 "esim"，那是把 2026-09-18 的已知缺陷写死成期望；
    2026-09-21 esim 升级为带 tracking 的深链后该断言永久红。
    """
    r = _run()
    assert r.returncode == 0
    assert "tracking 覆盖率" in r.stdout
    result = A.audit(ROOT)
    if result["untracked_keys"]:
        for k in result["untracked_keys"]:
            assert k in r.stdout, f"输出必须点名 {k}，否则运维不知道去哪修"
    if result["raw_untracked_urls"]:
        assert "裸联盟链接" in r.stdout, "绕过 shortcode 的裸链接必须被报告"
    # 绿勾只能在真正没有未跟踪链接时出现；否则 --fail 返回 1 而日报看到全绿。
    if result["links_untracked"] == 0:
        assert "都带 tracking 参数" in r.stdout
    else:
        assert "都带 tracking 参数" not in r.stdout


def test_cli_fail_exits_nonzero_when_untracked_exist():
    r = _run("--fail")
    assert r.returncode == 1, (
        "--fail 在存在未跟踪链接时必须 exit 1，才能被 CI 当作质量闸门"
    )
