"""Stripe webhook → Resend 邮件发送链路回归测试（P0-6，2026-09-21）。

历史 bug：`functions/api/stripe-webhook.js` 的 `sendEmail()` 只 `await fetch()`，
从不校验 `res.ok` / `res.status`。Resend 返回 500 时代码仍然继续往下走，
webhook 向 Stripe 返回 200 → Stripe 认为已处理不再重试 → 付费用户永远收不到
电子书下载邮件。这是付费用户拿不到电子书的静默失败根因。

本文件覆盖两层：
  1) 静态断言：源码里必须包含 `res.ok` / `res.status` 校验、失败抛错、重试逻辑。
  2) 行为断言：调用 node 执行真实 `onRequestPost`，把 `globalThis.fetch` 换成
     恒定返回 500 的 mock，验证 webhook 最终返回 500（而不是 200）。
     这样 Stripe 会自动重试整个 webhook delivery，用户不会静默失败。
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
WEBHOOK_JS = ROOT / "functions" / "api" / "stripe-webhook.js"
NODE_BIN = "node"


# ---------------------------------------------------------------------------
# 层 1：静态断言 —— 源码里必须有真实的响应校验与失败抛错逻辑
# ---------------------------------------------------------------------------

def _read_webhook() -> str:
    return WEBHOOK_JS.read_text(encoding="utf-8")


def test_sendemail_checks_res_ok():
    """sendEmail 必须读 res.ok 或 res.status。仅 `await fetch()` 不算修复。"""
    src = _read_webhook()
    # 定位 sendEmail 函数体
    m = re.search(r"async function sendEmail\(", src)
    assert m, "找不到 sendEmail 函数"
    # 从 sendEmail 起找到下一个顶层 async function 或文件结尾
    tail = src[m.start():]
    # 找下一个 "async function"（sendEmail 之后的下一个函数）
    next_m = re.search(r"\nasync function |\nfunction ", tail[len("async function sendEmail"):])
    body = tail if not next_m else tail[: next_m.start() + 1]
    assert "res.ok" in body or "res.status" in body, (
        "sendEmail 函数体内缺少 res.ok / res.status 校验"
    )


def test_sendemail_throws_on_failure():
    """Resend 非 2xx 必须抛错，让上层 catch 把 webhook 变成 5xx 触发 Stripe 重试。"""
    src = _read_webhook()
    # 找到 sendEmail 之后到 verifyStripeSignature 之间的区段（sendEmail 定义体）
    m = re.search(r"async function sendEmail\(", src)
    assert m
    tail = src[m.start():]
    end_markers = ("\nfunction constantTimeEqual", "\nfunction jsonResponse",
                   "\nasync function verifyStripeSignature")
    end = len(tail)
    for marker in end_markers:
        i = tail.find(marker)
        if i != -1:
            end = min(end, i)
    body = tail[:end]
    assert "throw " in body, "sendEmail 缺少 throw 语句；非 2xx 不会向上抛错"


def test_sendemail_has_retry_or_explicit_failure():
    """必须能区分「立即抛错」与「重试后再抛错」—— 两者都可接受，但不能只是静默通过。"""
    src = _read_webhook()
    m = re.search(r"async function sendEmail\(", src)
    assert m
    tail = src[m.start():]
    # 至少要有 retry 相关关键字，或者明确的 throw 路径
    has_retry_loop = bool(re.search(r"for\s*\(.*attempt", tail))
    has_backoff = "sleep" in tail or "setTimeout" in tail
    has_throw = "throw " in tail
    assert (has_retry_loop and has_backoff) or has_throw, (
        "sendEmail 既无重试也无明确 throw，Resend 500 会被静默吞掉"
    )


def test_sendemail_uses_idempotency_key_across_retries():
    """重试必须复用同一 Idempotency-Key，否则 Resend 侧无法去重会重复发信。"""
    src = _read_webhook()
    assert "Idempotency-Key" in src
    assert "stripe-" in src  # key 前缀
    # headers 构造必须在重试循环之外（否则每次请求都要重新读 eventId 但 key 值一致即可）
    send_start = src.index("async function sendEmail")
    send_block = src[send_start: send_start + 4000]
    # 断言：Idempotency-Key 出现在重试循环开头之前
    key_pos = send_block.index("Idempotency-Key")
    retry_loop_pos = send_block.find("for (let attempt")
    if retry_loop_pos != -1:
        assert key_pos < retry_loop_pos, (
            "Idempotency-Key 必须定义在重试循环外，避免每次尝试生成新 key"
        )


def test_webhook_returns_500_on_unexpected_error():
    """sendEmail 抛错后上层 catch 必须把响应变成 5xx，Stripe 才会重试整个 delivery。"""
    src = _read_webhook()
    # 找到主入口的 catch 块
    m = re.search(r"catch\s*\(\s*err\s*\)\s*\{[^}]*jsonResponse\([^,]*,\s*500", src, re.S)
    assert m, "onRequestPost 的 catch 块必须返回 500，让 Stripe 感知失败并重试"


# ---------------------------------------------------------------------------
# 层 2：行为断言 —— 通过 node 跑真实代码，验证 Resend 500 → webhook 500
# ---------------------------------------------------------------------------

def _run_node(script: str) -> subprocess.CompletedProcess:
    """在临时 ESM 模块上下文里执行一段脚本并捕获 stdout/stderr。"""
    # 用 --input-type=module 让 import 元语法生效
    return subprocess.run(
        [NODE_BIN, "--input-type=module", "-e", script],
        capture_output=True, text=True, encoding="utf-8",
        cwd=str(ROOT), timeout=20,
    )


# 生成一个合法签名的 webhook payload。node 侧用 node:crypto 现场计算 HMAC。
_NODE_PROBE = r"""
import { createHmac, randomUUID } from 'node:crypto';
import { onRequestPost } from './functions/api/stripe-webhook.js';

const SECRET = '***REMOVED***';
const payload = JSON.stringify({
  id: 'evt_test_' + randomUUID().replace(/-/g, '').slice(0, 16),
  type: 'checkout.session.completed',
  data: { object: { customer_email: 'buyer@example.com', metadata: { plan: 'monthly' } } },
});
const ts = Math.floor(Date.now() / 1000);
const sig = createHmac('sha256', SECRET).update(ts + '.' + payload).digest('hex');

// 恒定返回 500 的 Resend mock，记录调用次数
let calls = 0;
globalThis.fetch = async (url, opts) => {
  calls += 1;
  return { ok: false, status: 500, statusText: 'Internal Server Error',
           text: async () => JSON.stringify({ error: { message: 'simulated Resend 500' } }) };
};

const request = {
  method: 'POST',
  headers: { get: (name) => (name.toLowerCase() === 'stripe-signature'
    ? `t=${ts},v1=${sig}` : null) },
  text: async () => payload,
};
const env = {
  STRIPE_WEBHOOK_SECRET: SECRET,
  RESEND_API_KEY: '***REMOVED***',
  // 无 PROCESSED_EVENTS KV，验证没有 KV 时也严格校验
};

const res = await onRequestPost({ request, env });
// 输出结构化结果给 Python 层解析
console.log(JSON.stringify({ status: res.status, resendCalls: calls }));
"""


def test_resend_500_causes_webhook_500():
    """Resend 返回 500 → webhook 必须返回 500，不能吞掉错误变成 200。

    Stripe 看到 5xx 会自动重试整个 webhook delivery（配合 KV / Idempotency-Key
    两层去重），付费用户不会永久收不到邮件。
    """
    result = _run_node(_NODE_PROBE)
    assert result.returncode == 0, f"node probe crashed:\n{result.stderr}"
    line = result.stdout.strip().splitlines()[-1]
    data = json.loads(line)
    assert data["status"] == 500, (
        f"Resend 返回 500 时 webhook 必须也返回 500 触发 Stripe 重试；"
        f"实际: {data['status']}（静默失败路径仍复现）"
    )
    # 至少尝试了一次；重试次数由实现细节决定，但必须非零
    assert data["resendCalls"] >= 1, "webhook 应该至少调用过一次 Resend"


# ---------------------------------------------------------------------------
# 对照测试：Resend 返回 200 时 webhook 必须返回 200
# ---------------------------------------------------------------------------

_NODE_PROBE_OK = r"""
import { createHmac, randomUUID } from 'node:crypto';
import { onRequestPost } from './functions/api/stripe-webhook.js';

const SECRET = '***REMOVED***';
const payload = JSON.stringify({
  id: 'evt_ok_' + randomUUID().replace(/-/g, '').slice(0, 16),
  type: 'checkout.session.completed',
  data: { object: { customer_email: 'buyer@example.com', metadata: { plan: 'monthly' } } },
});
const ts = Math.floor(Date.now() / 1000);
const sig = createHmac('sha256', SECRET).update(ts + '.' + payload).digest('hex');

let calls = 0;
globalThis.fetch = async () => {
  calls += 1;
  return { ok: true, status: 200, statusText: 'OK',
           text: async () => JSON.stringify({ id: 'msg_test' }) };
};

const request = {
  method: 'POST',
  headers: { get: (name) => (name.toLowerCase() === 'stripe-signature'
    ? `t=${ts},v1=${sig}` : null) },
  text: async () => payload,
};
const env = {
  STRIPE_WEBHOOK_SECRET: SECRET,
  RESEND_API_KEY: '***REMOVED***',
};

const res = await onRequestPost({ request, env });
console.log(JSON.stringify({ status: res.status, resendCalls: calls }));
"""


def test_resend_200_causes_webhook_200():
    """对照：Resend 返回 200 时 webhook 必须返回 200，不能误报失败。"""
    result = _run_node(_NODE_PROBE_OK)
    assert result.returncode == 0, f"node probe crashed:\n{result.stderr}"
    data = json.loads(result.stdout.strip().splitlines()[-1])
    assert data["status"] == 200
    assert data["resendCalls"] == 1, "Resend 一次成功时不应重试"
