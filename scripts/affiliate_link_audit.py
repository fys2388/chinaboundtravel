"""联盟链接 tracking 覆盖率审计。

为什么需要它
------------
联盟链接不带 tracking 参数时，点击不会被归因，佣金永远为 0。这会造出一个
危险的误判：日报说「6 次点击、0 笔成交」，看起来像转化率问题，实际是归因
问题——相当一部分流量根本不会被计数。

2026-09-18 用 hugo build 实测：全站 588 条联盟链接中 161 条（27.4%）不带
tracking 参数，其中 156 条来自单个 key（esim → 裸 airalo 首页）。

只读：本脚本不修改任何文件。可被 feishu_daily_report.py import，也可直接运行：

    python scripts/affiliate_link_audit.py            # 人类可读
    python scripts/affiliate_link_audit.py --json     # 机器可读
    python scripts/affiliate_link_audit.py --fail     # 存在未跟踪链接时 exit 1

用法::

    import affiliate_link_audit
    result = affiliate_link_audit.audit()
    if result["untracked_ratio"] > 0.1:
        print(f"⚠️ {result['untracked']} 条联盟链接无法产生佣金")
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 识别「带 tracking 参数」的特征。匹配任一即视为可归因。
# 覆盖 Travelpayouts 短链、Booking aid、Aviasales marker、
# SafetyWing referenceID、AffiliatesCN aff_id、安全类 ambassador/referral。
TRACKING_MARKERS: Tuple[str, ...] = (
    "aid=",
    "aff_id",
    "marker=",
    "referenceID",
    "referenceid",
    "tpo.li",
    "affiliatescn",
    "ambassador/refer",
    "/aff_c",
    "ref=",
    "partner=",
    "utm_source=blog",
)

# 社交分享链接，不是联盟链接，不该被计入统计
SHARE_DOMAINS = (
    "twitter.com/intent",
    "facebook.com/sharer",
    "pinterest.com/pin",
    "t.me/share",
    "api.whatsapp.com",
    "reddit.com/submit",
    "linkedin.com/sharing",
    "mailto:",
)

# 内容里通过参数动态指定 partner 的 shortcode
DYNAMIC_SHORTCODES = ("affiliate-cta", "affiliate-mid-cta", "affiliate-link")


def _is_tracked(url: str) -> bool:
    low = url.lower()
    if any(d in low for d in SHARE_DOMAINS):
        return True  # 分享链接不算联盟链接，视为无风险
    return any(m in low for m in TRACKING_MARKERS)


def load_affiliate_config(root: Path = PROJECT_ROOT) -> Dict[str, str]:
    """从 hugo.toml 的 [params.affiliate] 读 key → url 映射。

    用行解析而不是 tomllib：hugo.toml 里这些行都是简单的
    key = "value" 形式，而 tomllib 在 Python 3.10 不可用。
    """
    cfg_path = root / "hugo.toml"
    if not cfg_path.exists():
        return {}
    out: Dict[str, str] = {}
    in_section = False
    for raw in cfg_path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("["):
            in_section = stripped.strip("[] ").strip() == "params.affiliate"
            continue
        if not in_section:
            continue
        m = re.match(r'^([A-Za-z0-9_]+)\s*=\s*"([^"]*)"\s*$', stripped)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def _shortcode_key_map(root: Path = PROJECT_ROOT) -> Dict[str, List[str]]:
    """扫描 shortcode 文件，得到 shortcode 名 → 它引用的 affiliate key 列表。"""
    sc_dir = root / "layouts" / "shortcodes"
    if not sc_dir.exists():
        return {}
    out: Dict[str, List[str]] = {}
    ref_pat = re.compile(r"Params\.affiliate\.([A-Za-z0-9_]+)")
    for p in sorted(sc_dir.glob("*.html")):
        if not re.search(r"affil|booking-link|klook-link|esim-link|safetywing-link|vpn-link", p.name):
            continue
        text = p.read_text(encoding="utf-8")
        keys = sorted(set(ref_pat.findall(text)))
        if keys:
            out[p.stem] = keys
    return out


def count_key_usage(root: Path = PROJECT_ROOT, partner_hosts: List[str] = None) -> Dict[str, int]:
    """统计每个 affiliate key 在内容里被引用的次数。"""
    keys: Dict[str, int] = {}

    # 1) 静态 shortcode：{{< affiliate-esim >}} → 该 shortcode 引用的 key
    for sc, refs in _shortcode_key_map(root).items():
        pat = re.compile(r"\{\{\s*[<{]\s*" + re.escape(sc) + r"\b")
        count = 0
        for p in root.joinpath("content").rglob("*.md"):
            count += len(pat.findall(p.read_text(encoding="utf-8", errors="ignore")))
        for k in refs:
            keys[k] = keys.get(k, 0) + count

    # 2) 动态 shortcode：partner="esim" / key="esim"
    for sc in DYNAMIC_SHORTCODES:
        block_pat = re.compile(
            r"\{\{\s*[<{]\s*" + re.escape(sc) + r"\b([^}]*?)\s*[}>]\s*\}", re.S
        )
        arg_pat = re.compile(r'(?:partner|key)\s*=\s*"([A-Za-z0-9_]+)"')
        for p in root.joinpath("content").rglob("*.md"):
            text = p.read_text(encoding="utf-8", errors="ignore")
            for m in block_pat.finditer(text):
                for k in arg_pat.findall(m.group(1)):
                    keys[k] = keys.get(k, 0) + 1

    # 3) 直接写进 markdown 的联盟 URL（绕过 shortcode 的）。
    #    关键限制：只统计**已知合作伙伴域名**上的裸链接。
    #    历史 bug：原先统计所有未带 tracking 的外链，把签证官网、新闻站、
    #    维基百科这类正常编辑性外链也算成了「联盟失败」，占比虚高到 82.6%。
    if partner_hosts:
        url_ref_pat = re.compile(r"https?://[^\s)\]>'\"]+")
        for p in root.joinpath("content").rglob("*.md"):
            text = p.read_text(encoding="utf-8", errors="ignore")
            for u in url_ref_pat.findall(text):
                if any(d in u.lower() for d in SHARE_DOMAINS):
                    continue
                if _host_of(u) not in partner_hosts:
                    continue
                if any(m in u.lower() for m in TRACKING_MARKERS):
                    continue
                keys["(raw-untracked-url)"] = keys.get("(raw-untracked-url)", 0) + 1
    return keys


def _partner_hosts(cfg: Dict[str, str]) -> List[str]:
    """从配置里提取合作伙伴域名，用于识别绕过 shortcode 的裸联盟链接。"""
    hosts: List[str] = []
    host_pat = re.compile(r"^https?://([^/?#]+)")
    for url in cfg.values():
        m = host_pat.match(url)
        if m:
            hosts.append(m.group(1).lower())
    # 已知联盟平台的裸域（即使配置里没填 tracking 也要认）
    hosts += [
        "www.airalo.com", "www.trip.com", "www.worldnomads.com",
        "www.allianztravelinsurance.com", "www.booking.com",
        "www.aviasales.com", "www.klook.com", "safetywing.com",
        "get.affiliatescn.net", "www.nordpass.com", "klook.tpo.li",
    ]
    return sorted(set(hosts))


def _host_of(url: str) -> str:
    m = re.match(r"^https?://([^/?#]+)", url, re.I)
    return m.group(1).lower() if m else ""


def audit(root: Path = PROJECT_ROOT) -> Dict:
    """返回联盟链接 tracking 覆盖率审计结果。"""
    cfg = load_affiliate_config(root)
    usage = count_key_usage(root, _partner_hosts(cfg))

    per_key = []
    tracked_total = untracked_total = 0
    for key, url in sorted(cfg.items()):
        if not url or key == "klook_expire_date":
            continue
        n = usage.get(key, 0)
        tracked = _is_tracked(url)
        per_key.append({
            "key": key,
            "url": url,
            "tracked": tracked,
            "usage": n,
        })
        if tracked:
            tracked_total += n
        else:
            untracked_total += n

    raw_untracked = usage.pop("(raw-untracked-url)", 0)
    untracked_total += raw_untracked

    total = tracked_total + untracked_total
    untracked_keys = [k["key"] for k in per_key if not k["tracked"] and k["usage"] > 0]

    return {
        "keys_total": len([k for k in per_key]),
        "keys_tracked": len([k for k in per_key if k["tracked"]]),
        "keys_untracked": len([k for k in per_key if not k["tracked"]]),
        "links_tracked": tracked_total,
        "links_untracked": untracked_total,
        "links_total": total,
        "untracked_ratio": round(untracked_total / total, 4) if total else 0.0,
        "raw_untracked_urls": raw_untracked,
        "untracked_keys": untracked_keys,
        "per_key": per_key,
        "blocking": bool(untracked_total > 0),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="联盟链接 tracking 覆盖率审计（只读）")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--fail", action="store_true", help="存在未跟踪链接时 exit 1")
    args = parser.parse_args()

    result = audit()

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("=" * 66)
        print("  联盟链接 tracking 覆盖率审计")
        print("=" * 66)
        print(f"  affiliate key 数: {result['keys_total']} "
              f"（有 tracking {result['keys_tracked']} / 无 {result['keys_untracked']}）")
        print(f"  内容引用次数: {result['links_total']} "
              f"（有 tracking {result['links_tracked']} / 无 {result['links_untracked']}）")
        pct = result["untracked_ratio"] * 100
        print(f"  无 tracking 占比: {pct:.1f}%")
        print()
        if result["untracked_keys"]:
            print("  ⚠️  无法产生佣金的 key（流量白送）:")
            for k in result["per_key"]:
                if k["key"] in result["untracked_keys"]:
                    print(f"     - {k['key']:14s} x{k['usage']:<4} {k['url'][:70]}")
            print()
            print("  修复动作是商务动作：去对应平台注册联盟计划拿专属 tracking 参数，")
            print("  然后更新 hugo.toml [params.affiliate]。不是改代码。")
        else:
            print("  ✅ 所有被引用的联盟链接都带 tracking 参数")
        print("=" * 66)

    return 1 if (args.fail and result["blocking"]) else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(main())
