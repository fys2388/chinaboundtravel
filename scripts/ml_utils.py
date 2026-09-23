"""MailerLite API Token 清洗统一入口。

2026-09-23 AUDIT-OPS-005 引入。

问题背景：
    MailerLite API Token 从本机 .env 加载时经常带 UTF-8 BOM (\\ufeff)。
    requests 用 latin-1 编码 HTTP Authorization header，遇到 \\ufeff 直接
    抛 UnicodeEncodeError: 'latin-1' codec can't encode character '\\ufeff'。
    症状：MailerLite 报表脚本全部报 "MailerLite API error or missing token"，
    线上 functions/api/subscribe.js 因 cleanToken() 已剥离 BOM 而工作正常，
    导致"线上 OK / 本地审计全红"的错觉。

本模块提供与 functions/api/subscribe.js:cleanToken 语义完全一致的
Python 版本，供所有 scripts/*.py 复用。不要在各个脚本里复制粘贴。

语义（与 subscribe.js:42-46 对齐）：
- 剥离首部/尾部 BOM (\\ufeff)
- 剥离首部/尾部空白
- 剔除非可打印 ASCII (只保留 0x20..0x7E)

空串或 None 返回空串（不当作 None 处理，方便下游直接 `if not token: skip`）。

接线范围（2026-09-23 全部完成）：
- subscription_health_audit.py  ✅ get_mailerlite_token
- email_sequence_tracker.py     ✅ get_mailerlite_token
- mailerlite_sequence_setup.py  ✅ get_mailerlite_token
- audit_okr_achievement.py      ✅ get_mailerlite_token
- feishu_daily_report.py        ✅ clean_token
- feishu_weekly_report.py       ✅ clean_token
- feishu_monthly_report.py      ✅ clean_token
- feishu_quarterly_report.py    ✅ clean_token
- feishu_yearly_report.py       ✅ clean_token
- unified_data_manager.py       N/A (只把 token 存 JSON，不发 HTTP)
"""

from __future__ import annotations

import os
from typing import Optional


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
