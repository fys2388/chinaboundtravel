# -*- coding: utf-8 -*-
"""tests/test_subscribe_cors_preflight.py

回归锁：functions/api/subscribe.js 的 onRequestOptions 必须返回 CORS 头。

背景
----
2026-09-18 订阅端点健康审计首次跑通后发现一个真实缺陷：
OPTIONS /api/subscribe 返回 204 但 **没有** Access-Control-Allow-Origin。

根因（不是配置问题，是代码问题）：该文件导出了两个 handler——

  export async function onRequestPost({ request, env }) { ... }   # 内部有 OPTIONS 分支，带 cors(origin)
  export async function onRequestOptions() {                      # ← 顶层 export 抢在方法分发之前
    return new Response(null, { status: 204 });                   # 无参数、无 headers
  }

Cloudflare Pages Functions 的方法分发优先用 onRequestOptions 这个导出，
所以线上收到的永远是这个空壳。onRequestPost 里那段「看起来正确」的
OPTIONS 分支是死代码——它只在 POST 时被调用。

修复照抄同一仓库 functions/api/checkout.js:107 的既有正确写法：
读 Origin → cors(origin) → 204。

本测试用 node 真实 import 该模块并调用 handler，而不是静态正则。
好处：语法错、导入错、handler 签名写错都会被 node 直接暴露，
而不是靠读源码猜。Node 只需 v18+（内置 Request）。

依赖：node 在 PATH 上。缺失时跳过（不假装通过）。
"""
import re
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SUBSCRIBE_JS = ROOT / "functions" / "api" / "subscribe.js"
CHECKOUT_JS = ROOT / "functions" / "api" / "checkout.js"


def _node():
    return shutil.which("node")


@pytest.fixture(scope="module")
def node_exe():
    exe = _node()
    if not exe:
        pytest.skip("node 不在 PATH 上，跳过真实执行测试（部署后由线上订阅审计兜底）")
    return exe


# ---------------------------------------------------------------- 真实执行

def _run(node_exe, script):
    """用 .mjs 跑一段 ESM，绕开 package.json 无 type 字段的解析警告。"""
    tmp = ROOT / "_tmp_subscribe_probe.mjs"
    try:
        tmp.write_text(script, encoding="utf-8")
        proc = subprocess.run(
            [node_exe, str(tmp)],
            capture_output=True, text=True, encoding="utf-8", timeout=60,
        )
        return proc.returncode, proc.stdout, proc.stderr
    finally:
        if tmp.exists():
            tmp.unlink()


PRECHECK_SCRIPT = textwrap.dedent("""\
    import { onRequestOptions } from 'file:///__SUBSCRIBE_JS__';
    const req = new Request('https://www.chinaboundtravel.com/api/subscribe', {
      method: 'OPTIONS',
      headers: { Origin: 'https://x.example' },
    });
    const r = await onRequestOptions({ request: req });
    const get = (h) => r.headers.get(h);
    console.log('STATUS=' + r.status);
    console.log('ACAO=' + get('Access-Control-Allow-Origin'));
    console.log('ACAM=' + get('Access-Control-Allow-Methods'));
    console.log('ACAH=' + get('Access-Control-Allow-Headers'));
""")


def _parse(log):
    return dict(
        line.split("=", 1) for line in log.strip().splitlines() if "=" in line
    )


def test_preflight_returns_204(node_exe):
    code, out, err = _run(node_exe, PRECHECK_SCRIPT.replace("__SUBSCRIBE_JS__", SUBSCRIBE_JS.as_posix()))
    if code != 0:
        pytest.fail("subscribe.js 无法 import 或 handler 抛错:\n" + out + err)
    parsed = _parse(out)
    assert parsed.get("STATUS") == "204", parsed


def test_preflight_has_all_cors_headers(node_exe):
    """缺任何一个头，跨源浏览器预检就会被拦下。"""
    code, out, _ = _run(node_exe, PRECHECK_SCRIPT.replace("__SUBSCRIBE_JS__", SUBSCRIBE_JS.as_posix()))
    if code != 0:
        pytest.fail(out)
    parsed = _parse(out)
    missing = [h for h in ("ACAO", "ACAM", "ACAH") if not parsed.get(h)]
    assert not missing, "缺 CORS 头: %s -> %s" % (missing, parsed)


def test_preflight_echoes_requesting_origin(node_exe):
    """必须回显请求方的 Origin，不能一律回默认域名。
    固定默认值会让别的站点调这个接口时拿不到可用响应。"""
    code, out, _ = _run(node_exe, PRECHECK_SCRIPT.replace("__SUBSCRIBE_JS__", SUBSCRIBE_JS.as_posix()))
    if code != 0:
        pytest.fail(out)
    parsed = _parse(out)
    assert parsed.get("ACAO") == "https://x.example", parsed


def test_preflight_ok_when_origin_missing(node_exe):
    """无 Origin 头时退到默认域名，仍然要给出三个头（不静默失败）。"""
    script = textwrap.dedent("""\
        import { onRequestOptions } from 'file:///__SUBSCRIBE_JS__';
        const r = await onRequestOptions({ request: new Request('https://www.chinaboundtravel.com/api/subscribe', { method: 'OPTIONS' }) });
        console.log('STATUS=' + r.status);
        console.log('ACAO=' + r.headers.get('Access-Control-Allow-Origin'));
    """)
    code, out, _ = _run(node_exe, script.replace("__SUBSCRIBE_JS__", SUBSCRIBE_JS.as_posix()))
    if code != 0:
        pytest.fail(out)
    parsed = _parse(out)
    assert parsed.get("STATUS") == "204"
    assert parsed.get("ACAO") == "https://www.chinaboundtravel.com", parsed


# ---------------------------------------------------------------- POST 回归

POST_SCRIPT = textwrap.dedent("""\
    import { onRequestPost } from 'file:///__SUBSCRIBE_JS__';
    const env = {};
    const call = async (body, method = 'POST') => {
      const r = await onRequestPost({ request: new Request('https://www.chinaboundtravel.com/api/subscribe', {
        method, headers: { 'Content-Type': 'application/json', Origin: 'https://www.chinaboundtravel.com' },
        body: JSON.stringify(body),
      }), env });
      return { status: r.status, acao: r.headers.get('Access-Control-Allow-Origin') };
    };
    const badJson = await call({}, 'POST');
    const noEmail = await call({ source: 't' }, 'POST');
    console.log('BADJSON_STATUS=' + badJson.status + ' ACAO=' + badJson.acao);
    console.log('NOEMAIL_STATUS=' + noEmail.status + ' ACAO=' + noEmail.acao);
""")


def test_post_4xx_still_carries_cors(node_exe):
    """这次改动只碰 OPTIONS。POST 的错误分支必须仍然带 CORS 头——
    否则一个改动反而回归了另一个面。"""
    code, out, _ = _run(node_exe, POST_SCRIPT.replace("__SUBSCRIBE_JS__", SUBSCRIBE_JS.as_posix()))
    if code != 0:
        pytest.fail(out)
    lines = _parse(out)
    # 两个 key 都叫 ACAO，_parse 会互相覆盖 —— 直接按行找
    text = "\n".join(out.splitlines())
    assert "NOEMAIL_STATUS=400" in text, out
    assert text.count("ACAO=https://www.chinaboundtravel.com") == 2, (
        "两个 POST 错误分支都必须带 CORS 头，实际:\n%s" % out
    )


# ---------------------------------------------------------------- 一致性

CORREX = {
    "Allow-Origin": re.compile(r"Access-Control-Allow-Origin"),
    "Allow-Methods": re.compile(r"Access-Control-Allow-Methods"),
    "Allow-Headers": re.compile(r"Access-Control-Allow-Headers"),
    # Origin 读取必须同时有大写和 lowercase 两个 fallback
    # （Cloudflare 在不同路径上会把头规范化成小写）
    "Origin-upper": re.compile(r"""headers\.get\(['"]Origin['"]\)"""),
    "Origin-lower": re.compile(r"""headers\.get\(['"]origin['"]\)"""),
    "Default-domain": re.compile(r"https://www\.chinaboundtravel\.com"),
}


@pytest.mark.parametrize("name,path", [
    ("subscribe", SUBSCRIBE_JS),
    ("checkout", CHECKOUT_JS),
])
def test_options_handler_shape(name, path):
    """两个端点都得满足同一个 CORS 契约。
    静态检查而非正则猜字符串：只抓三件事——handler 带参、
    回显 Origin、三个头齐全。实现方式允许不同（内联字面量 / cors() 助手），
    但契约必须一致，否则哪天有人只改一边就会漏一个端点。
    """
    assert path.is_file(), "%s 不存在了？修复的参照物没了" % path.name
    text = path.read_text(encoding="utf-8")
    assert "onRequestOptions({" in text, "%s 的 OPTIONS handler 改成无参了" % path.name
    missing = [k for k, pat in CORREX.items() if not pat.search(text)]
    assert not missing, "%s 的 CORS 契约缺: %s" % (path.name, missing)


def test_preflight_handlers_are_not_inlined_without_headers():
    """针对本轮真实 bug 的反向锁。
    出问题的写法是 `export async function onRequestOptions() {
    return new Response(null, { status: 204 }); }` —— 无参、Response 不带 headers。
    这里直接扫所有 functions 文件，确保没有任何一个这样的空壳。"""
    bad = []
    for js in (ROOT / "functions").rglob("*.js"):
        text = js.read_text(encoding="utf-8")
        # 无参的 OPTIONS export
        if re.search(r"onRequestOptions\s*\(\s*\)", text):
            bad.append("%s: onRequestOptions 无参" % js.name)
        # Response 构造里没有 headers（status-only）
        if re.search(r"new Response\(null,\s*\{\s*status\s*:\s*204\s*\}\s*\)", text):
            bad.append("%s: 204 Response 没有 headers" % js.name)
    assert not bad, "发现缺 CORS 的 OPTIONS handler: %s" % bad
