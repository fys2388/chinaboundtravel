"""订阅健康审计的期望值回归测试。

守护 2026-09-18 修掉的三处「期望过时」缺陷：
1. SUBSCRIPTION_PAGES 含 "/blog/" —— 线上 404（博客在 /posts/，导航指向
   /posts/，全站 0 处内部链接指向 /blog/）。每次都产生一个假失败。
2. subscribe_valid_email 要求响应含 "message" 字段 —— 线上实际返回
   {"success":true,"subscriber_created":true,"delivered_pdf":false,...}，
   没有 message。一个工作正常的接口被反复判成 critical 失败。
3. subscribe_cors_preflight 只认 200 —— 线上返回 204 No Content，
   对 OPTIONS 预检这是标准响应。
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import subscription_health_audit as S  # noqa: E402


def _resp(status_code, json_body=None, headers=None):
    """构造一个足够 mimick requests.Response 的桩。"""
    r = MagicMock()
    r.status_code = status_code
    r.headers = headers or {}
    if json_body is None:
        r.json.side_effect = ValueError("no json")
        r.text = ""
    else:
        r.json.return_value = json_body
        r.text = str(json_body)
    return r


def _case(name, **overrides):
    base = {
        "endpoint": "/api/subscribe",
        "name": name,
        "method": "POST",
        "body": {"email": "t@example.com"},
        "expected_status": 200,
        "description": "test",
        "severity": "medium",
    }
    base.update(overrides)
    return base


# ── expected_status 支持列表 ────────────────────────────────

def test_single_status_still_accepted():
    """单值 expected_status 行为不变。"""
    with patch.object(S.requests, "post", return_value=_resp(200, {"success": True})):
        r = S.run_test(S.DEFAULT_BASE_URL, _case("single"))
    assert r["passed"] is True, r["error"]


def test_single_status_rejects_wrong_code():
    with patch.object(S.requests, "post", return_value=_resp(404)):
        r = S.run_test(S.DEFAULT_BASE_URL, _case("single", expected_status=200))
    assert r["passed"] is False
    assert "期望状态码" in r["error"]


@pytest.mark.parametrize("code", [200, 204])
def test_list_status_accepts_each_member(code):
    """OPTIONS 预检 200 与 204 都合法，两个都必须通过。"""
    with patch.object(S.requests, "options", return_value=_resp(code)):
        r = S.run_test(S.DEFAULT_BASE_URL,
                       _case("preflight", method="OPTIONS", expected_status=[200, 204]))
    assert r["passed"] is True, (code, r["error"])


def test_list_status_rejects_code_outside_list():
    with patch.object(S.requests, "options", return_value=_resp(403)):
        r = S.run_test(S.DEFAULT_BASE_URL,
                       _case("preflight", method="OPTIONS", expected_status=[200, 204]))
    assert r["passed"] is False
    assert "204" in r["error"] and "403" in r["error"]


def test_status_mismatch_short_circuits_field_checks():
    """状态码不对时不应继续查字段（避免报出误导性的第二个错误）。"""
    with patch.object(S.requests, "post", return_value=_resp(500, {"success": True})):
        r = S.run_test(S.DEFAULT_BASE_URL,
                       _case("x", expected_status=200, expected_fields=["success"]))
    assert r["passed"] is False
    assert "状态码" in r["error"]


# ── 必需字段检查 ────────────────────────────────────────────

def test_missing_expected_field_fails():
    with patch.object(S.requests, "post", return_value=_resp(200, {"other": 1})):
        r = S.run_test(S.DEFAULT_BASE_URL, _case("x", expected_fields=["success"]))
    assert r["passed"] is False
    assert "响应缺少字段: success" in r["error"]


def test_present_field_passes():
    with patch.object(S.requests, "post",
                      return_value=_resp(200, {"success": True, "subscriber_created": True})):
        r = S.run_test(S.DEFAULT_BASE_URL, _case("x", expected_fields=["success"]))
    assert r["passed"] is True


# ── 头检查 ──────────────────────────────────────────────────

def test_missing_expected_header_fails():
    """CORS 头缺失必须报出来——这是真实缺陷，不是测试噪音。"""
    with patch.object(S.requests, "options", return_value=_resp(204)):
        r = S.run_test(S.DEFAULT_BASE_URL,
                       _case("cors", method="OPTIONS", expected_status=[200, 204],
                             expected_headers=["Access-Control-Allow-Origin"]))
    assert r["passed"] is False
    assert "Access-Control-Allow-Origin" in r["error"]


def test_present_header_passes():
    with patch.object(S.requests, "options",
                      return_value=_resp(204, headers={"Access-Control-Allow-Origin": "*"})):
        r = S.run_test(S.DEFAULT_BASE_URL,
                       _case("cors", method="OPTIONS", expected_status=[200, 204],
                             expected_headers=["Access-Control-Allow-Origin"]))
    assert r["passed"] is True


# ── 测试用例定义本身不能回退 ────────────────────────────────

def test_blog_page_removed_from_subscription_pages():
    """/blog/ 是孤儿 404，留着会产生永久假失败。"""
    assert "/blog/" not in S.SUBSCRIPTION_PAGES


def test_subscription_pages_are_live():
    for p in S.SUBSCRIPTION_PAGES:
        assert p.startswith("/"), p


@pytest.mark.parametrize("needle", ["/", "/about/"])
def test_core_subscribe_pages_still_checked(needle):
    """首页和 about 页有订阅表单，必须继续被检查。"""
    assert needle in S.SUBSCRIPTION_PAGES


def test_valid_email_case_no_longer_requires_message():
    """线上响应没有 message 字段；要求它会永远失败。"""
    case = next(c for c in S.TEST_CASES if c["name"] == "subscribe_valid_email")
    assert "success" in case["expected_fields"]
    assert "message" not in case["expected_fields"]


def test_preflight_accepts_both_200_and_204():
    case = next(c for c in S.TEST_CASES if c["name"] == "subscribe_cors_preflight")
    expected = case["expected_status"]
    assert isinstance(expected, (list, tuple)), expected
    assert 200 in expected and 204 in expected


def test_every_test_case_has_required_keys():
    """防止新增用例漏字段导致 run_test 抛 KeyError。"""
    for c in S.TEST_CASES:
        for key in ("endpoint", "name", "method", "expected_status", "description", "severity"):
            assert key in c, (c.get("name"), key)
    names = [c["name"] for c in S.TEST_CASES]
    assert len(names) == len(set(names)), "用例名重复"


# ── KPI 接的是正确的源 ──────────────────────────────────────

def test_subscribe_kpi_reads_subscription_report_not_general_api():
    """user.subscribe_api_health 必须来自 subscription_health，不是通用 api_health。"""
    import agent_kpi_auditor as A

    src = Path(A.__file__).read_text(encoding="utf-8")
    # 通用 api_health 只能喂 ops.api_health_rate
    assert 'metrics["ops"]["api_health_rate"]' in src
    # 订阅 KPI 必须从 subscription_health 目录取值
    assert "reports" in src and "subscription_health" in src
    # 且 subscribe_api_health 的赋值必须出现在 subscription_health 分支内
    sub_block = src.split("subscription_health", 2)
    assert len(sub_block) >= 3
    assert 'metrics["user"]["subscribe_api_health"]' in sub_block[-1]


def test_report_age_helper(tmp_path):
    """陈旧报告必须能算出年龄，让读者知道分数的时效。"""
    import agent_kpi_auditor as A
    p = tmp_path / "api_health_2026-09-07_111714.json"
    p.write_text("{}", encoding="utf-8")
    age = A._report_age_days(p)
    assert age >= 0
    # 内容里的时间戳也能识别
    p2 = tmp_path / "report.json"
    p2.write_text('{"audit_time": "2026-09-18T10:00:00"}', encoding="utf-8")
    assert A._report_age_days(p2) >= 0
    # 完全无从判断
    p3 = tmp_path / "report.json"
    p3.write_text("{}", encoding="utf-8")
    assert A._report_age_days(p3) == -1
