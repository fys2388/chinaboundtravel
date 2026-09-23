"""MailerLite API 统一入口（token 清洗 + 订阅者清理）。

2026-09-23 AUDIT-OPS-005 引入 clean_token / get_mailerlite_token。
2026-09-23 AUDIT-OPS-006 引入 list_subscribers / cleanup_test_subscribers。

问题背景 1（AUDIT-OPS-005）：
    MailerLite API Token 从本机 .env 加载时经常带 UTF-8 BOM (\\ufeff)。
    requests 用 latin-1 编码 HTTP Authorization header，遇到 \\ufeff 直接
    抛 UnicodeEncodeError: 'latin-1' codec can't encode character '\\ufeff'。
    症状：MailerLite 报表脚本全部报 "MailerLite API error or missing token"，
    线上 functions/api/subscribe.js 因 cleanToken() 已剥离 BOM 而工作正常，
    导致"线上 OK / 本地审计全红"的错觉。

问题背景 2（AUDIT-OPS-006）：
    多个 audit 脚本（api_health_audit.py / performance_monitor.py /
    subscription_health_audit.py）会 POST /api/subscribe 走前端函数中转，
    最终在 MailerLite 里创建测试订阅者。早期版本用时间戳邮箱
    （test-subscribe-<ts>@example.com）每次都新增记录，3 天累积 28 条。
    AUDIT-OPS-005 已把测试邮箱改成固定值（幂等，MailerLite 对已存在 email
    返回 200 更新而不新增），但历史遗留的 7 条假订阅者仍在，且未来若
    新增脚本又用时间戳邮箱，污染源会回来。
    cleanup_test_subscribers 提供幂等的清理入口，可手动或 CI 定时调用。

本模块提供与 functions/api/subscribe.js:cleanToken 语义完全一致的
Python 版本，供所有 scripts/*.py 复用。不要在各个脚本里复制粘贴。

语义（clean_token，与 subscribe.js:42-46 对齐）：
- 剥离首部/尾部 BOM (\\ufeff)
- 剥离首部/尾部空白
- 剔除非可打印 ASCII (只保留 0x20..0x7E)
- 空串或 None 返回空串（不当作 None 处理，方便下游直接 `if not token: skip`）

接线范围（2026-09-23 全部完成）：
- subscription_health_audit.py  ✅ get_mailerlite_token + cleanup_test_subscribers
- email_sequence_tracker.py     ✅ get_mailerlite_token
- mailerlite_sequence_setup.py  ✅ get_mailerlite_token
- audit_okr_achievement.py      ✅ get_mailerlite_token
- feishu_daily_report.py        ✅ clean_token
- feishu_weekly_report.py       ✅ clean_token
- feishu_monthly_report.py      ✅ clean_token
- feishu_quarterly_report.py    ✅ clean_token
- feishu_yearly_report.py       ✅ clean_token
- unified_data_manager.py       N/A (只把 token 存 JSON，不发 HTTP)

测试邮箱白名单（默认清理时保留，幂等更新不新增记录）：
    TEST_EMAIL_WHITELIST = frozenset({
        "healthcheck.chinaboundtravel@example.com",  # subscription_health_audit
        "test-api-health@example.com",                # api_health_audit
        "perf-test@example.com",                      # performance_monitor
    })
    + 站点 owner 真实邮箱 fys2388@gmail.com 不属 @example.com，不受清理影响。

设计原则：
- 只清理 @example.com / @example.org / @example.net（RFC 6761 / 6762 保留域名）
- 永不触碰非保留域名邮箱（真实用户）
- 幂等：重复调用不产生副作用（固定邮箱已在 whitelist，会被跳过）
- 只删不建：cleanup 函数无副作用，不会创建任何新订阅者
"""

from __future__ import annotations

import os
import time
from typing import Iterable, Optional, Set

# RFC 6761 / 6762 reserved test domains (never deliver real mail)
RESERVED_TEST_DOMAINS = ("@example.com", "@example.org", "@example.net")

# Test emails we intentionally keep — each script has its own fixed email,
# MailerLite dedupes on email so these are idempotent (no new records).
TEST_EMAIL_WHITELIST = frozenset({
    "healthcheck.chinaboundtravel@example.com",  # subscription_health_audit.py
    "test-api-health@example.com",                # api_health_audit.py
    "perf-test@example.com",                      # performance_monitor.py
})

MAILERLITE_SUBSCRIBERS_URL = "https://connect.mailerlite.com/api/subscribers"


def clean_token(token: Optional[str]) -> str:
    """剥离 BOM + 空白 + 非可打印字符。空/None → 空串。"""
    if not token:
        return ""
    token = token.replace("\ufeff", "")
    token = token.strip()
    return "".join(ch for ch in token if 0x20 <= ord(ch) <= 0x7E)


def get_mailerlite_token(env_name: str = "MAILERLITE_API_TOKEN") -> str:
    """读环境变量并自动清洗 BOM。

    用法：
        from ml_utils import get_mailerlite_token
        token = get_mailerlite_token()
        if not token:
            # 未配置
            ...
        headers = {"Authorization": f"Bearer {token}"}
    """
    return clean_token(os.environ.get(env_name, ""))


def _is_reserved_test_email(email: Optional[str]) -> bool:
    """判断邮箱是否在 RFC 6761/6762 保留域名（example.com/org/net）。"""
    if not email:
        return False
    return email.lower().endswith(RESERVED_TEST_DOMAINS)


def list_subscribers(
    token: str,
    limit: int = 100,
    max_pages: int = 50,
    retries: int = 3,
    verbose: bool = False,
) -> list[dict]:
    """用 cursor 分页遍历 MailerLite 订阅者列表。

    MailerLite API v3 返回结构是 `{data: [...], links: {next}, meta: {...}}`
    （**不是** `subscribers` 数组）。API 文档中提到的 `page` 参数被服务端
    忽略（每次返回同一批），必须用 `cursor` 参数分页。

    参数：
        token: MailerLite API token（可含 BOM，内部清洗）
        limit: 每页条数（默认 100）
        max_pages: 安全上限（默认 50 页 = 5000 条），防死循环
        retries: 单次请求最大重试次数（网络偶发 SSL EOF）
        verbose: True 时每页打印一行

    返回：所有页去重后的订阅者列表（按 id 去重）。空 token / 认证失败
    返回空列表并抛 RuntimeError。

    幂等：纯 GET，无副作用。
    """
    import requests  # 延迟导入，模块 import 时不需要 requests
    import time as _time

    clean = clean_token(token)
    if not clean:
        raise RuntimeError("MailerLite token 为空，无法拉取订阅者列表")

    headers = {
        "Authorization": f"Bearer {clean}",
        "Content-Type": "application/json",
    }

    result: list[dict] = []
    seen_ids: set[str] = set()
    cursor: Optional[str] = None

    for page_no in range(max_pages):
        params: dict = {"limit": limit}
        if cursor:
            params["cursor"] = cursor

        # 重试：网络偶发 SSL EOF
        resp = None
        last_err = None
        for attempt in range(retries):
            try:
                resp = requests.get(
                    MAILERLITE_SUBSCRIBERS_URL,
                    headers=headers,
                    params=params,
                    timeout=30,
                )
                if resp.status_code == 200:
                    break
                last_err = f"HTTP {resp.status_code}: {resp.text[:200]}"
                resp = None
            except Exception as e:
                last_err = f"{type(e).__name__}: {str(e)[:80]}"
                _time.sleep(1)
        if resp is None or resp.status_code != 200:
            raise RuntimeError(f"MailerLite 订阅者列表请求失败: {last_err}")

        data = resp.json()
        batch = data.get("data", [])
        for s in batch:
            sid = s.get("id")
            if sid not in seen_ids:
                seen_ids.add(sid)
                result.append(s)

        if verbose:
            print(f"  [list_subscribers] page={page_no} batch={len(batch)} total={len(result)}")

        # 结束条件：本页为空 或 没有 next cursor
        next_url = (data.get("links") or {}).get("next")
        if not batch or not next_url:
            break
        # MailerLite cursor 是完整 URL 或纯 cursor 字符串，两者都可用
        # 简单起见：直接读 URL 里的 cursor 参数
        if "?" in next_url:
            cursor_part = next_url.split("cursor=", 1)[-1].split("&", 1)[0]
            cursor = cursor_part if cursor_part else None
        else:
            cursor = next_url
        if cursor == "":
            cursor = None
        if cursor is None:
            break

    return result


def cleanup_test_subscribers(
    token: str,
    whitelist: Optional[Iterable[str]] = None,
    dry_run: bool = True,
    verbose: bool = False,
) -> dict:
    """删除 MailerLite 上非白名单的 @example.com / .org / .net 测试订阅者。

    2026-09-23 AUDIT-OPS-006 引入。用于清理历史遗留的假订阅者（如
    probe@example.com / audit-probe-0918@example.com / customer-journey-*
    / x@example.com 等），并防止未来脚本又用时间戳邮箱造成污染。

    设计原则：
    - 只删 RFC 6761/6762 保留域名（@example.com/org/net），永不触碰真实邮箱
    - whitelist 里的邮箱保留（默认 3 个固定测试邮箱，幂等更新不新增）
    - dry_run=True 时只统计要删的，不真删；dry_run=False 才真 DELETE
    - 幂等：重复调用安全（固定邮箱在 whitelist 会被跳过）

    参数：
        token: MailerLite API token
        whitelist: 额外的保留邮箱列表（会与 TEST_EMAIL_WHITELIST 合并）
        dry_run: True=只报告，False=真删
        verbose: True 时每步打印一行

    返回：
        {
            "ok": bool,                    # 请求是否全部成功
            "total_scanned": int,          # 扫描的订阅者总数
            "reserved_test_count": int,    # @example.com/org/net 总数
            "whitelisted_count": int,      # 白名单内的数量（不删）
            "candidates": list[str],       # 要删的邮箱列表
            "deleted": list[str],          # 真删的邮箱列表（dry_run=False）
            "errors": list[str],           # 单条删除失败的错误信息
            "dry_run": bool,
        }

    不抛异常：内部消化所有请求错误，返回 ok=False + errors 列表。
    """
    import requests  # 延迟导入
    import time as _time

    report: dict = {
        "ok": False,
        "total_scanned": 0,
        "reserved_test_count": 0,
        "whitelisted_count": 0,
        "candidates": [],
        "deleted": [],
        "errors": [],
        "dry_run": bool(dry_run),
    }

    clean = clean_token(token)
    if not clean:
        report["errors"].append("MailerLite token 为空，跳过清理")
        return report

    headers = {
        "Authorization": f"Bearer {clean}",
        "Content-Type": "application/json",
    }

    wl: Set[str] = set(TEST_EMAIL_WHITELIST)
    if whitelist:
        for e in whitelist:
            if e:
                wl.add(e.lower())

    # 1. 拉全量订阅者
    try:
        subs = list_subscribers(clean, verbose=verbose)
    except Exception as e:
        report["errors"].append(f"list_subscribers 失败: {type(e).__name__}: {str(e)[:200]}")
        return report

    report["total_scanned"] = len(subs)

    # 2. 分类
    reserved = [s for s in subs if _is_reserved_test_email(s.get("email"))]
    reserved_ids = [s["id"] for s in reserved]
    reserved_emails = {s.get("email", "").lower() for s in reserved}

    report["reserved_test_count"] = len(reserved)
    report["whitelisted_count"] = sum(1 for e in reserved_emails if e in wl)

    candidates = [s for s in reserved if s.get("email", "").lower() not in wl]
    report["candidates"] = sorted(s.get("email", "") for s in candidates)

    if verbose:
        print(f"  [cleanup] scanned={len(subs)} reserved={len(reserved)} "
              f"whitelisted={report['whitelisted_count']} candidates={len(candidates)} "
              f"dry_run={dry_run}")

    # 3. 真删（只在 dry_run=False 时）
    if not dry_run:
        for s in candidates:
            sid = s.get("id")
            email = s.get("email", "")
            url = f"{MAILERLITE_SUBSCRIBERS_URL}/{sid}"
            last_err = None
            for attempt in range(3):
                try:
                    r = requests.delete(url, headers=headers, timeout=30)
                    if r.status_code in (200, 204):
                        report["deleted"].append(email)
                        break
                    last_err = f"HTTP {r.status_code}: {r.text[:120]}"
                except Exception as e:
                    last_err = f"{type(e).__name__}: {str(e)[:80]}"
                    _time.sleep(1)
            else:
                report["errors"].append(f"DELETE {email}: {last_err}")

    report["ok"] = (not report["errors"]) or dry_run
    return report
