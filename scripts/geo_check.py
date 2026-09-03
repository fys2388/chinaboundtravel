#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChinaBound Travel - GEO 爬虫可达性检查（GEO 部署 2026-09-03）
以各 AI 爬虫官方 User-Agent 请求站点关键页，记录 HTTP 状态码，
用于验证 GEO 部署是否生效（引用/搜索爬虫应 200，训练爬虫应非 200）。

输出 reports/geo_crawl_status.json；关键引用爬虫不可达时退出码 1（供 CI 门禁/告警）。

使用：
    python scripts/geo_check.py
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:  # pragma: no cover
    print("[geo_check] missing dependency: requests")
    sys.exit(2)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
OUTPUT = REPORTS_DIR / "geo_crawl_status.json"

BASE_URL = "https://www.chinaboundtravel.com"
CHECK_PATH = "/posts/wechat-pay-for-foreigners-step-by-step-setup-and-common-mistakes-to-avoid-guide/"

# (名称, 官方 UA, 期望可达?)
# expect_ok=True  -> 该爬虫应能抓取（GEO 引用/搜索），200 为达标
# expect_ok=False -> 该爬虫应被阻断（训练类），非 200 为达标
CRAWLERS = [
    ("Googlebot", "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)", True),
    ("OAI-SearchBot", "OAI-SearchBot/1.0 (+https://openai.com/oai-searchbot)", True),
    ("PerplexityBot", "PerplexityBot/1.0 (https://perplexity.ai/searchbot)", True),
    ("Claude-SearchBot", "Claude-SearchBot/1.0 (+https://claude.com/searchbot)", True),
    ("GPTBot", "GPTBot/1.0 (+https://openai.com/gptbot)", False),
    ("ClaudeBot", "ClaudeBot/1.0 (anthropic.com)", False),
    ("CCBot", "CCBot/2.0 (+https://commoncrawl.org/faq/)", False),
    ("Bytespider", "Mozilla/5.0 (compatible; Bytespider; spider-feedback@bytedance.com)", False),
]


def fetch_status(ua: str) -> int:
    try:
        r = requests.get(
            BASE_URL + CHECK_PATH,
            headers={"User-Agent": ua},
            timeout=25,
            allow_redirects=True,
        )
        return r.status_code
    except Exception:
        return -1  # 网络/超时视为不可达


def main() -> int:
    results: dict = {}
    failures: list = []
    for name, ua, expect_ok in CRAWLERS:
        code = fetch_status(ua)
        ok = (expect_ok and code == 200) or (not expect_ok and code != 200)
        results[name] = {"http_status": code, "expect_reachable": expect_ok, "ok": ok}
        mark = "OK" if ok else "FAIL"
        print(f"[{name}] HTTP {code}  expect_reachable={expect_ok}  -> {mark}")
        if not ok:
            failures.append(name)
        time.sleep(0.3)

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "base_url": BASE_URL,
        "check_path": CHECK_PATH,
        "results": results,
        "failures": failures,
        "geo_ready": len(failures) == 0,
    }
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[geo_check] report -> {OUTPUT}")
    print(f"[geo_check] geo_ready={payload['geo_ready']} failures={failures}")

    if failures:
        print(f"[geo_check] BLOCKED reachable crawlers: {failures}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
