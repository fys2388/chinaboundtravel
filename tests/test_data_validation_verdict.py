# -*- coding: utf-8 -*-
"""tests/test_data_validation_verdict.py

锁 reports/real_data/data_validation.json 的判定逻辑。

为什么值得锁
------------
validate_all_data() 原本把 total_sources 和 PASS 阈值都硬编码成 4：

    "summary": {"total_sources": 4, ...}
    if real_count == 4 and fresh_count == 4:
        validation["overall_status"] = "PASS"

但 results 实际含 7 个源：ga4/gsc/social/content 四个核心源，
加 partnerize/impact/multi_partner 三个联盟平台。
后三个在没有凭据的环境里恒以 NO_CREDENTIALS / NO_CONNECTED_PARTNERS 失败。

于是线上报告长期是这样的自相矛盾：

    overall_status: PASS
    total_sources: 4
    真实数据源: 4/4
    issues:
      - partnerize: NO_CREDENTIALS - not real data
      - impact: NO_CREDENTIALS - not real data
      - multi_partner: NO_CONNECTED_PARTNERS - not real data

「4/4 全绿」同时列出 3 条明确失败。人类读结论会说「数据管道健康」，
而实际上 3 个被跟踪的源从来没出过真数据。

overall_status 没有任何逻辑消费方（grep 确认只有 print 和 markdown
报告读它），所以修这个不会破坏流水线——只是把假绿改回真相。
代价是 overall_status 从 PASS 变 PARTIAL，这是分数变「更真实」，
不是回归。
"""
import contextlib
import io
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import real_data_pull_engine as E   # noqa: E402


def _src(name, real=True, fresh=True, status="OK", error=None):
    return {"is_real_data": real, "is_fresh": fresh,
            "status": status, "error": error}


def _disabled(name, reason="按决策停用"):
    """构造一个 DISABLED_BY_DECISION 源。

    与 _src(real=False, status="NO_CREDENTIALS") 的区别是终态：
    NO_CREDENTIALS 意味着「去配凭证」，DISABLED 意味着「别试了」。
    """
    return {"is_real_data": False, "is_fresh": False,
            "status": "DISABLED_BY_DECISION", "error": None,
            "disabled_reason": reason}


@pytest.fixture(autouse=True)
def _isolate_report_writes(tmp_path, monkeypatch):
    """把两个报告路径都指向临时目录，任何写入都不碰真仓库。

    validate_all_data() 末尾有**两处**落盘，Round 16 只挡了其中一处：
      1. _save_json(DATA_VALIDATION_JSON, ...)   — 走 _save_json
      2. open(DATA_VALIDATION_REPORT, "w")        — 直接 open，绕过 _save_json
    第二处是 markdown 报告，Round 16 的 monkeypatch 完全没覆盖到，
    结果 test_verdict_only_depends_on_counts 的 _run(b) 把
    reports/real_data/data_validation_report.md 覆盖成了
    「S1/HTTP_500、S2、S3」的合成数据。
    所以这里改成分数：把两个模块级路径常量都指到 tmp_path，
    比逐个 monkeypatch 写函数更不容易漏。
    """
    sink = tmp_path / "reports" / "real_data"
    sink.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(E, "DATA_VALIDATION_JSON", sink / "data_validation.json")
    monkeypatch.setattr(E, "DATA_VALIDATION_REPORT", sink / "data_validation_report.md")
    yield


def _run(results):
    """跑一次并把打印吃掉。落盘由 autouse fixture 隔离。"""
    with contextlib.redirect_stdout(io.StringIO()):
        return E.validate_all_data(results)


def _run_print(results):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        E.validate_all_data(results)
    return buf.getvalue()


def _seven_source_results():
    """照抄线上 reports/real_data/data_validation.json 的 7 个源。"""
    return {
        "ga4": _src("ga4"),
        "gsc": _src("gsc"),
        "social": _src("social"),
        "content": _src("content", status="UNKNOWN"),
        "partnerize": _src("partnerize", real=False, fresh=False,
                            status="NO_CREDENTIALS"),
        "impact": _src("impact", real=False, fresh=False,
                        status="NO_CREDENTIALS"),
        "multi_partner": _src("multi_partner", real=False, fresh=False,
                               status="NO_CONNECTED_PARTNERS"),
    }


# ── 核心回归：真实 7 源不能判 PASS ──────────────────────────

def test_real_seven_sources_is_partial_not_pass():
    v = _run(_seven_source_results())
    assert v["overall_status"] == "PARTIAL"
    assert v["summary"]["total_sources"] == 7
    assert v["summary"]["real_data_count"] == 4
    assert v["summary"]["fresh_data_count"] == 4


def test_total_sources_is_computed_not_hardcoded_4():
    """这是本轮修的根因。硬编码 4 在任何源数变化时都会撒谎。"""
    for n in (1, 4, 5, 7, 12):
        results = {f"s{i}": _src(f"s{i}") for i in range(n)}
        v = _run(results)
        assert v["summary"]["total_sources"] == n, f"{n} 个源报成了别的数"


def test_failed_sources_is_listed():
    v = _run(_seven_source_results())
    assert v["summary"]["failed_sources"] == ["partnerize", "impact", "multi_partner"]


# ── 判定边界 ────────────────────────────────────────────────

def test_all_real_and_fresh_is_pass():
    results = {f"s{i}": _src(f"s{i}") for i in range(3)}
    assert _run(results)["overall_status"] == "PASS"


def test_all_failing_is_fail():
    results = {f"s{i}": _src(f"s{i}", real=False, fresh=False, status="X")
               for i in range(5)}
    v = _run(results)
    assert v["overall_status"] == "FAIL"
    assert len(v["summary"]["failed_sources"]) == 5


def test_exactly_half_is_partial():
    """real_count * 2 >= total 是 PARTIAL 的下界，不能掉到 FAIL。"""
    results = {f"s{i}": _src(f"s{i}", real=i < 3) for i in range(5)}
    v = _run(results)
    assert v["summary"]["real_data_count"] == 3
    assert v["overall_status"] == "PARTIAL"


def test_below_half_is_fail():
    results = {f"s{i}": _src(f"s{i}", real=i < 2) for i in range(5)}
    v = _run(results)
    assert v["summary"]["real_data_count"] == 2
    assert v["overall_status"] == "FAIL"


def test_zero_sources_is_fail_with_reason():
    """空 results 不能被判 PASS——0/0 满足不了任何有意义的判定。"""
    v = _run({})
    assert v["overall_status"] == "FAIL"
    assert any("没有数据源" in i for i in v["summary"]["issues"])
    assert v["summary"]["total_sources"] == 0


def test_real_but_stale_is_not_pass():
    """新鲜度也是 PASS 的条件，不能只看 is_real_data。"""
    results = {
        "a": _src("a", fresh=False, status="STALE"),
        "b": _src("b"),
    }
    v = _run(results)
    assert v["overall_status"] == "PARTIAL"
    assert v["summary"]["fresh_data_count"] == 1
    assert v["summary"]["failed_sources"] == [], "不新鲜不等于失败，不该进 failed_sources"
    assert any("not fresh" in i for i in v["summary"]["issues"])


# ── 报告文本 ────────────────────────────────────────────────

def test_print_uses_real_total_not_four():
    """人类可读层原本印「真实数据源: 4/4」同时下方列 3 条失败。
    修完必须印 4/7，否则假绿灯在 report 里照旧。"""
    out = _run_print(_seven_source_results())
    assert "真实数据源: 4/7" in out
    assert "新鲜数据源: 4/7" in out
    assert "真实数据源: 4/4" not in out


def test_error_none_does_not_leak_into_report():
    """puller 用 "error": None 初始化，.get(k, default) 取到 None
    而不是 default，会往报告里印出 'partnerize: NO_CREDENTIALS - None'。"""
    results = {"partnerize": _src("partnerize", real=False, fresh=False,
                                  status="NO_CREDENTIALS", error=None)}
    v = _run(results)
    for i in v["summary"]["issues"]:
        assert " - None" not in i, f"None 泄漏进报告：{i}"
    assert any("partnerize" in i and "not real data" in i
               for i in v["summary"]["issues"])


def test_error_message_kept_when_present():
    results = {"x": _src("x", real=False, fresh=False, status="HTTP_500",
                          error="HTTP 500: server unavailable")}
    v = _run(results)
    assert any("HTTP 500: server unavailable" in i for i in v["summary"]["issues"])


# ── DISABLED_BY_DECISION：决策停用 ≠ 凭证缺失 ────────────────


def test_disabled_sources_are_excluded_from_denominator():
    """停用源不该把通过率拉低：4 个活源全绿 + 3 个停用 = PASS。"""
    results = _seven_source_results()
    for name in ("partnerize", "impact", "multi_partner"):
        results[name] = _disabled(name)
    v = _run(results)
    assert v["overall_status"] == "PASS"
    assert v["summary"]["active_sources"] == 4
    assert v["summary"]["total_sources"] == 7
    assert v["summary"]["disabled_sources"] == ["impact", "multi_partner", "partnerize"]
    assert v["summary"]["failed_sources"] == []
    assert v["summary"]["issues"] == []


def test_disabled_is_distinguishable_from_credentials_missing():
    """NO_CREDENTIALS 是可行动故障，DISABLED 是终态，两者不能混为一谈。"""
    v = _run({"missing": _src("missing", real=False, fresh=False,
                              status="NO_CREDENTIALS"),
              "off": _disabled("off")})
    assert v["sources"]["missing"]["validation_status"] == "FAIL"
    assert v["sources"]["off"]["validation_status"] == "DISABLED"
    assert "missing" in v["summary"]["failed_sources"]
    assert "off" not in v["summary"]["failed_sources"]
    assert not any("off:" in i for i in v["summary"]["issues"])
    assert v["sources"]["off"]["disabled_reason"]


def test_disabled_sources_do_not_mask_real_failures():
    """停用不能成为掩盖真实故障的借口：活源坏了要进 failed_sources、不能判 PASS。

    注意判定阈值是「real_count*2 >= active_count 即 PARTIAL」（见
    validate_all_data 的注释），所以 1/2 是 PARTIAL 而非 FAIL——
    断言重点是「不是 PASS 且故障被点名」，而不是具体落到哪一档。
    """
    v = _run({"ok": _src("ok"),
              "bad": _src("bad", real=False, fresh=False, status="HTTP_500"),
              "off": _disabled("off")})
    assert v["summary"]["active_sources"] == 2
    assert v["summary"]["failed_sources"] == ["bad"]
    assert v["overall_status"] in ("PARTIAL", "FAIL")
    assert v["overall_status"] != "PASS"


def test_disabled_reason_reaches_the_report():
    """停用原因要落到 markdown 里，否则运维看不出「为什么停了」。"""
    _run({"ok": _src("ok"), "off": _disabled("off", "World Nomads 被拒")})
    report = E.DATA_VALIDATION_REPORT.read_text(encoding="utf-8")
    assert "DISABLED" in report
    assert "World Nomads 被拒" in report
    # 分母不能写死 4
    assert "真实数据源: 1/1" in report


# ── schema 兼容性 ───────────────────────────────────────────

def test_summary_schema_keeps_existing_keys():
    """下游可能读这些键，新增可以，删掉不行。"""
    v = _run(_seven_source_results())
    for k in ("total_sources", "real_data_count", "fresh_data_count", "issues"):
        assert k in v["summary"], f"summary 缺既有键 {k}"
    for k in ("validation_time", "overall_status", "sources", "summary"):
        assert k in v, f"顶层缺键 {k}"


def test_source_entry_schema_unchanged():
    v = _run(_seven_source_results())
    entry = v["sources"]["ga4"]
    for k in ("is_real_data", "is_fresh", "data_date", "status",
              "error", "validation_status"):
        assert k in entry
    assert entry["validation_status"] == "PASS"
    assert v["sources"]["partnerize"]["validation_status"] == "FAIL"
    assert v["sources"]["content"]["validation_status"] == "PASS"


def test_verdict_only_depends_on_counts():
    """判定只该由数量决定，不能因为 status 字符串不同就翻转。"""
    a = {"s1": _src("s1", real=False, fresh=False, status="NO_CREDENTIALS"),
         "s2": _src("s2"), "s3": _src("s3")}
    b = {"s1": _src("s1", real=False, fresh=False, status="HTTP_500"),
         "s2": _src("s2"), "s3": _src("s3")}
    assert _run(a)["overall_status"] == _run(b)["overall_status"]
