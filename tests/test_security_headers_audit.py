# -*- coding: utf-8 -*-
"""tests/test_security_headers_audit.py

锁四处：
  1. _report_recency —— 报告新旧排序按日期，不按字典序
  2. _security_headers —— 双 schema 读取，把「没测到」和「测到不合规」分开
  3. site_health_agent.record_check_failure —— 检查抛异常必须留痕
  4. 报告 schema 与 severity 排序/summary 统计的兼容性

为什么值得锁
------------
2026-09-18 之前 ops.security_headers 一直是 60.0%，读者以为那是
一份三天前的安全扫描结论。实际发生了三件事叠在一起：

  (1) 文件选错：site_health_audit.json 按字典序排在所有
      site_health_2026-09-*.json 之后（'a' > '2'），
      sorted(glob("*.json"))[-1] 一直拿到 18 天前那份旧报告，
      把当天几小时前生成的新鲜报告完全忽略。
      旧代码读的是 findings 键，那份旧报告恰好有，所以 bug 被掩盖。
  (2) schema 变了没人跟：site_health_agent 的报告早已从
      findings[].module=='security' 改成 issues[].type。
      sh.get("findings", []) 恒为空 → 「0 条安全发现」被解读成 100% 合规。
  (3) 检查抛异常不留痕：五个网络检查都是 except: print(...) 后
      什么都不往 all_issues 写。「检查失败」和「检查通过」在报告里
      长得一模一样。

(2)+(3) 合起来是静默假绿灯：线上真丢 HSTS 时报告里会出现
security_header_missing，审计器读不到；检查抛异常时一条都没有，
同样报 100 分。两种情况都拿 100 分，而这个分数从没被测量过。

线上实测（2026-09-18）6 个必需头全部存在，所以修完后 100.0 是真拿的；
Ops 66.5 (C) → 72.5 (B) 是换到新鲜报告 + 修掉未测量的假扣分。
"""
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import agent_kpi_auditor as K   # noqa: E402
import site_health_agent as S   # noqa: E402


def _write_report(tmp_path, body, name=None):
    d = tmp_path / "reports" / "site_health"
    d.mkdir(parents=True, exist_ok=True)
    p = d / (name or "site_health_2026-09-18.json")
    p.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
    return p


def _fresh(days_ago=0):
    return (datetime.now().date() - timedelta(days=days_ago)).strftime("%Y-%m-%d")


def _new_schema(issues):
    return {"timestamp": _fresh() + "T02:15:20", "agent": "site_health",
            "permission_level": "L2",
            "summary": {"total_issues": len(issues)},
            "issues": issues}


def _missing_header(header="Strict-Transport-Security"):
    return {"type": "security_header_missing", "severity": "medium",
            "file": "https://example.com", "message": f"缺少安全头: {header}",
            "auto_fixable": False, "agent": "site_health"}


# ── 1. 报告新旧排序 ──────────────────────────────────────────

def test_recency_prefers_fresh_dated_report_over_undated(tmp_path):
    """核心回归锁：undated 的 site_health_audit.json 不能压过当天的
    site_health_2026-09-18.json。这是「考核引用过期快照」的第三个变体。

    注意 mtime 要设成过去：undated 文件没有文件名日期，只能退回 mtime，
    而它真实情况是 18 天前写的。刚创建的文件 mtime 是「现在」，
    会正确压过今天的日期 00:00——那不是 bug，是测试没还原真实状态。
    """
    d = tmp_path / "reports" / "site_health"
    d.mkdir(parents=True, exist_ok=True)
    old = d / "site_health_audit.json"
    old.write_text('{}', encoding="utf-8")
    new = d / f"site_health_{_fresh()}.json"
    new.write_text('{}', encoding="utf-8")
    import os, time
    now = time.time()
    os.utime(old, (now - 18 * 86400, now - 18 * 86400))
    picked = sorted([old, new], key=K._report_recency)[-1]
    assert picked == new, "字典序让 'site_health_audit.json' 排在 'site_health_2026-09-...' 之后"


def test_recency_orders_two_dated_reports(tmp_path):
    d = tmp_path / "reports" / "site_health"
    d.mkdir(parents=True, exist_ok=True)
    a = d / f"site_health_{_fresh(10)}.json"
    b = d / f"site_health_{_fresh(0)}.json"
    a.write_text('{}', encoding="utf-8")
    b.write_text('{}', encoding="utf-8")
    assert sorted([a, b], key=K._report_recency)[-1] == b


def test_recency_falls_back_to_mtime_when_no_date_in_name(tmp_path):
    d = tmp_path / "reports" / "site_health"
    d.mkdir(parents=True, exist_ok=True)
    a = d / "scan_old.json"
    b = d / "scan_new.json"
    a.write_text('{}', encoding="utf-8")
    b.write_text('{}', encoding="utf-8")
    # 明确错开 mtime，避免文件系统时间粒度太粗导致并列
    import os, time
    now = time.time()
    os.utime(a, (now - 3600, now - 3600))
    os.utime(b, (now, now))
    assert sorted([a, b], key=K._report_recency)[-1] == b


def test_recency_ignores_garbage_dates(tmp_path):
    d = tmp_path / "reports" / "site_health"
    d.mkdir(parents=True, exist_ok=True)
    p = d / "site_health_2099-99-99.json"   # 非法日期，不能抛异常
    p.write_text('{}', encoding="utf-8")
    assert isinstance(K._report_recency(p), datetime)


# ── 2. 新 schema（issues） ───────────────────────────────────

def test_all_headers_present_scores_100(tmp_path):
    p = _write_report(tmp_path, _new_schema([
        {"type": "content_placeholder", "severity": "high", "message": "x"}]))
    r = K._security_headers([p])
    assert r["compliance"] == 100.0
    assert r["signal"] == "compliant"
    assert r["missing"] == []


def test_missing_headers_are_counted(tmp_path):
    """报告只记缺失的头，合规率 = (6 - 缺失数) / 6。缺 1 个 = 5/6 = 83.3。"""
    p = _write_report(tmp_path, _new_schema([_missing_header()]))
    r = K._security_headers([p])
    assert r["compliance"] == 83.3
    assert r["signal"] == "missing"
    assert r["missing"] == ["缺少安全头: Strict-Transport-Security"]


def test_all_six_missing_scores_zero(tmp_path):
    p = _write_report(tmp_path, _new_schema([_missing_header() for _ in range(6)]))
    r = K._security_headers([p])
    assert r["compliance"] == 0.0


def test_missing_more_than_six_does_not_go_negative(tmp_path):
    """异常多出的条目不能把分数算成负数。"""
    p = _write_report(tmp_path, _new_schema([_missing_header() for _ in range(9)]))
    r = K._security_headers([p])
    assert r["compliance"] == 0.0


def test_security_check_failure_is_not_measured(tmp_path):
    """检查抛异常 ≠ 通过。这是本轮修的核心：失败必须和通过区分开。"""
    p = _write_report(tmp_path, _new_schema([
        {"type": "check_failed", "severity": "high", "check": "security_headers",
         "message": "安全头检查失败: timeout", "auto_fixable": False,
         "agent": "site_health"}]))
    r = K._security_headers([p])
    assert r["compliance"] is None
    assert r["signal"] == "not_measured"
    assert "安全头检查失败" in r["note"]


def test_other_check_failure_does_not_block_security(tmp_path):
    """SSL 检查失败不应该让安全头一起变成「未测量」。"""
    p = _write_report(tmp_path, _new_schema([
        {"type": "check_failed", "check": "ssl_certificate", "message": "ssl"}]))
    r = K._security_headers([p])
    assert r["compliance"] == 100.0


def test_site_unreachable_is_not_measured(tmp_path):
    """站点不可达时 check_security_headers 提前 return，0 条缺失是假象。"""
    p = _write_report(tmp_path, _new_schema([
        {"type": "site_unreachable", "severity": "critical", "message": "网站无法访问"}]))
    r = K._security_headers([p])
    assert r["compliance"] is None
    assert r["signal"] == "not_measured"


def test_unmeasured_beats_present_when_both_exist(tmp_path):
    p = _write_report(tmp_path, _new_schema([
        _missing_header(),
        {"type": "check_failed", "check": "security_headers", "message": "boom"},
    ]))
    r = K._security_headers([p])
    assert r["compliance"] is None


def test_unknown_schema_is_not_measured(tmp_path):
    p = _write_report(tmp_path, {"timestamp": _fresh(), "agent": "site_health"})
    r = K._security_headers([p])
    assert r["compliance"] is None
    assert "既无 issues 也无 findings" in r["note"]


def test_no_reports_returns_note(tmp_path):
    r = K._security_headers([])
    assert r["compliance"] is None
    assert "无 site_health 报告" in r["note"]


def test_malformed_report_returns_note(tmp_path):
    d = tmp_path / "reports" / "site_health"
    d.mkdir(parents=True, exist_ok=True)
    p = d / "site_health_2026-09-18.json"
    p.write_text("{broken", encoding="utf-8")
    r = K._security_headers([p])
    assert r["compliance"] is None
    assert "读取失败" in r["note"]


def test_non_dict_report_returns_note(tmp_path):
    p = _write_report(tmp_path, ["not", "a", "dict"])
    r = K._security_headers([p])
    assert r["compliance"] is None
    assert "不是 JSON 对象" in r["note"]


def test_issue_shapes_without_type_are_ignored(tmp_path):
    """issues 里混入坏行不能崩，也不能被误当成缺失安全头。"""
    p = _write_report(tmp_path, _new_schema([
        {"severity": "medium"},
        "a string",
        None,
        {"type": "security_header_missing"},
    ]))
    r = K._security_headers([p])
    assert r["compliance"] == 83.3, "无 type 的坏行不能计入缺失"


# ── 3. 旧 schema（findings） ─────────────────────────────────

def test_legacy_schema_with_security_finding_scores_60(tmp_path):
    """旧报告保留旧口径：有 security 模块发现 → 60 分。不重算历史。"""
    p = _write_report(tmp_path, {"findings": [
        {"module": "seo", "title": "x"},
        {"module": "security", "title": "CSP 未允许 Sentry"}]},
        name="site_health_audit.json")
    r = K._security_headers([p])
    assert r["compliance"] == 60.0
    assert r["signal"] == "legacy"
    assert "CSP" in r["missing"][0]


def test_legacy_schema_without_security_scores_100(tmp_path):
    p = _write_report(tmp_path, {"findings": [{"module": "seo"}]},
                      name="site_health_audit.json")
    r = K._security_headers([p])
    assert r["compliance"] == 100.0


def test_issues_schema_takes_precedence_over_findings(tmp_path):
    """新 schema 优先：两份字段都在时以 issues 为准（新报告的口径更新）。"""
    p = _write_report(tmp_path, {"findings": [{"module": "security"}],
                                 "issues": []})
    r = K._security_headers([p])
    assert r["signal"] == "compliant"
    assert r["compliance"] == 100.0


# ── 4. record_check_failure ──────────────────────────────────

def test_record_check_failure_appends_issue():
    """五个网络检查抛异常时必须留一条 issue，否则失败和通过无法区分。"""
    all_issues = []
    S.record_check_failure(all_issues, "security_headers", "安全头检查",
                           TimeoutError("read timed out"))
    assert len(all_issues) == 1
    i = all_issues[0]
    assert i["type"] == "check_failed"
    assert i["check"] == "security_headers"
    assert "安全头检查失败" in i["message"]
    assert "read timed out" in i["message"]
    assert i["auto_fixable"] is False
    assert i["agent"] == "site_health"


def test_record_check_failure_issue_survives_severity_sort():
    """site_health_agent 用 `x["severity"]` 直接下标排序和统计 summary，
    缺字段会 KeyError。这里锁住新 issue 的字段完整性。"""
    all_issues = []
    S.record_check_failure(all_issues, "ssl_certificate", "SSL证书检查", ValueError("v"))
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    sorted_issues = sorted(all_issues, key=lambda x: severity_order[x["severity"]])
    assert len(sorted_issues) == 1
    assert sorted_issues[0]["severity"] == "high"
    assert sorted_issues[0]["severity"] in severity_order


def test_record_check_failure_is_not_auto_fixable_so_not_silently_dropped():
    """未解决统计口径：auto_fixable=False 的问题会进 need_manual，
    不会在自动修复阶段被静默丢掉。"""
    all_issues = []
    S.record_check_failure(all_issues, "og_tags", "OG标签检查", RuntimeError("r"))
    i = all_issues[0]
    assert not i.get("auto_fixable")
    unresolved = [x for x in all_issues
                  if (x.get("status") or "").lower()
                  not in {"resolved", "fixed", "false_positive", "closed"}]
    assert len(unresolved) == 1, "check_failed 必须计入未解决，否则等于没报"


# ── 5. 接线纪律 ──────────────────────────────────────────────

def test_auditor_does_not_use_lexicographic_site_health_selection():
    """字典序选择会让 'site_health_audit.json' 永远压过当天的日期命名报告。"""
    src = (Path(__file__).resolve().parent.parent / "scripts"
           / "agent_kpi_auditor.py").read_text(encoding="utf-8")
    assert "key=_report_recency" in src
    assert 'sorted((PROJECT_ROOT / "reports" / "site_health").glob("*.json"))' not in src


def test_auditor_no_longer_reads_findings_only():
    """旧的 findings-only 内联实现必须从接线代码里消失。

    不检查 `sh.get("findings", [])` / `security_issues` 这些字面量：
    _security_headers 的 docstring 里引用了旧代码用来解释为什么改，
    全文匹配会误伤自己的注释。改用旧实现的局部变量名和排序写法判定。
    """
    src = (Path(__file__).resolve().parent.parent / "scripts"
           / "agent_kpi_auditor.py").read_text(encoding="utf-8")
    assert "site_health_reports = sorted" not in src
    assert "_security_headers()" in src


def test_record_check_failure_is_wired_into_all_network_checks():
    """修一处漏一处的风险：六个网络检查必须都接上了。

    数 8 空格缩进的调用行，不含函数定义行（定义是 0 缩进的 `def`）。"""
    import re
    src = (Path(__file__).resolve().parent.parent / "scripts"
           / "site_health_agent.py").read_text(encoding="utf-8")
    for check_id in ("security_headers", "csp_allowlist", "mixed_content",
                     "og_tags", "ssl_certificate", "structured_data"):
        assert f'"{check_id}"' in src, f"{check_id} 的检查失败没有留痕"
    calls = re.findall(r"^ {8}record_check_failure\(all_issues,", src, re.M)
    assert len(calls) == 6, f"应有 6 处调用（含 12b CSP 放行检查），实际 {len(calls)}"


# ── 6. CSP 放行检查（12b） ──────────────────────────────────

class _FakeResp:
    def __init__(self, headers):
        self.headers = headers


CSP_FULL = ("default-src 'self'; "
            "script-src 'self' https://www.googletagmanager.com "
            "https://www.google-analytics.com "
            "https://pagead2.googlesyndication.com; "
            "connect-src 'self' https://sentry.io https://sentry.avs.io "
            "https://cloudflareinsights.com")
# 去掉两个 sentry 域
CSP_NO_SENTRY = ("default-src 'self'; "
                 "script-src 'self' https://www.googletagmanager.com "
                 "https://www.google-analytics.com "
                 "https://pagead2.googlesyndication.com; "
                 "connect-src 'self' https://cloudflareinsights.com")
# 去掉 cloudflareinsights 域
CSP_NO_CF = ("default-src 'self'; "
             "script-src 'self' https://www.googletagmanager.com "
             "https://www.google-analytics.com "
             "https://pagead2.googlesyndication.com; "
             "connect-src 'self' https://sentry.io https://sentry.avs.io")
# 注意：不用「按域从 FULL 里删」的写法。sentry.io 是 sentry.avs.io 的子串，
# 用 `domain in part` 删 sentry.io 会把整条 connect-src 一起删掉，
# 多报出一条缺口——这是第一版测试失败的原因，不是产品 bug。


def test_required_csp_hosts_are_all_six():
    """域清单要和 site_health_agent.REQUIRED_CSP_HOSTS 同步。
    少一个等于放弃监控那个第三方服务。"""
    assert len(S.REQUIRED_CSP_HOSTS) == 6
    for h in ("sentry.io", "sentry.avs.io", "googlesyndication.com",
              "google-analytics.com", "googletagmanager.com",
              "cloudflareinsights.com"):
        assert h in S.REQUIRED_CSP_HOSTS, f"必需域 {h} 不在监控清单里"


def test_csp_all_allowed_produces_no_findings(monkeypatch):
    monkeypatch.setattr(S, "_fetch_url",
                        lambda u: (_FakeResp({"Content-Security-Policy": CSP_FULL}), ""))
    assert S.check_csp_allowlist() == []


def test_csp_missing_hosts_are_reported(monkeypatch):
    monkeypatch.setattr(S, "_fetch_url",
                        lambda u: (_FakeResp({"Content-Security-Policy": CSP_NO_SENTRY}), ""))
    found = S.check_csp_allowlist()
    assert len(found) == 2, f"应报 sentry.io 和 sentry.avs.io，实际 {[i['message'] for i in found]}"
    for i in found:
        assert i["type"] == "csp_allowlist_missing"
        assert i["severity"] == "high"
        assert i["agent"] == "site_health"
        assert i["detail"], "缺 detail 读者就不知道 CSP 里少了什么"


def test_csp_allowlist_is_not_auto_fixable(monkeypatch):
    """CSP 改错会打断分析/广告/错误追踪，或反过来放开不必要的源。
    必须人工评审，不允许自动修复。旧 engine 标 auto_fixable=True 是个隐患。"""
    monkeypatch.setattr(S, "_fetch_url",
                        lambda u: (_FakeResp({"Content-Security-Policy": CSP_NO_CF}), ""))
    found = S.check_csp_allowlist()
    assert len(found) == 1
    assert found[0]["auto_fixable"] is False
    assert "connect-src" in found[0]["recommendation"]


def test_csp_header_absent_does_not_double_report(monkeypatch):
    """CSP 头缺失时返回 []——那条由 check_security_headers 报
    security_header_missing。重复上报会让未解决计数翻倍。"""
    monkeypatch.setattr(S, "_fetch_url",
                        lambda u: (_FakeResp({"X-Frame-Options": "DENY"}), ""))
    assert S.check_csp_allowlist() == []


def test_csp_empty_string_does_not_double_report(monkeypatch):
    """空 CSP 同样视为「头缺失」，不往下走。"""
    monkeypatch.setattr(S, "_fetch_url",
                        lambda u: (_FakeResp({"Content-Security-Policy": ""}), ""))
    assert S.check_csp_allowlist() == []


def test_csp_site_unreachable_returns_empty(monkeypatch):
    """站点不可达时返回 []——site_unreachable 由 check_security_headers 报。"""
    monkeypatch.setattr(S, "_fetch_url", lambda u: (None, None))
    assert S.check_csp_allowlist() == []


def test_csp_issue_survives_severity_sort_and_summary(monkeypatch):
    """产出必须能进主流程的排序（直接下标 x["severity"]）和 summary 统计。"""
    monkeypatch.setattr(S, "_fetch_url",
                        lambda u: (_FakeResp({"Content-Security-Policy": CSP_NO_CF}), ""))
    all_issues = S.check_csp_allowlist()
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    sorted_issues = sorted(all_issues, key=lambda x: severity_order[x["severity"]])
    unresolved = [i for i in sorted_issues
                  if (i.get("status") or "").lower()
                  not in {"resolved", "fixed", "false_positive", "closed"}]
    assert len(unresolved) == 1
    assert unresolved[0]["severity"] == "high"


def test_csp_gaps_do_not_change_security_header_compliance(tmp_path):
    """CSP 内容是另一个口径，不能拉低「6 个必需头是否齐全」的合规率。
    混进去等于用一个 KPI 测两件事。"""
    p = _write_report(tmp_path, _new_schema([
        {"type": "csp_allowlist_missing", "severity": "high",
         "message": "CSP 未允许 Sentry 错误追踪（sentry.io）"}]))
    r = K._security_headers([p])
    assert r["compliance"] == 100.0, "CSP 缺口不该影响响应头合规率"
    assert r["signal"] == "compliant"
    assert len(r["csp_gaps"]) == 1
    assert "sentry.io" in r["csp_gaps"][0]


def test_csp_gaps_collected_alongside_missing_headers(tmp_path):
    """两类发现同时存在时都要报，不能互相覆盖。"""
    p = _write_report(tmp_path, _new_schema([
        _missing_header(),
        {"type": "csp_allowlist_missing", "severity": "high",
         "message": "CSP 未允许 Google AdSense（googlesyndication.com）"},
    ]))
    r = K._security_headers([p])
    assert r["compliance"] == 83.3
    assert r["signal"] == "missing"
    assert len(r["missing"]) == 1
    assert len(r["csp_gaps"]) == 1


def test_csp_gaps_empty_on_legacy_schema(tmp_path):
    p = _write_report(tmp_path, {"findings": [{"module": "seo"}]},
                      name="site_health_audit.json")
    r = K._security_headers([p])
    assert r["csp_gaps"] == []


def test_csp_gaps_empty_when_not_measured(tmp_path):
    p = _write_report(tmp_path, _new_schema([
        {"type": "check_failed", "check": "security_headers",
         "message": "安全头检查失败: timeout"},
        {"type": "csp_allowlist_missing", "message": "CSP 未允许 x（y）"},
    ]))
    r = K._security_headers([p])
    assert r["compliance"] is None
    assert r["csp_gaps"] == [], "测不出来时不应声称有具体的放行缺口"


def test_auditor_prints_csp_gaps_separately():
    """CSP 缺口必须单独打印——否则 100% 合规率的旁边什么都没有，
    读者不知道还有 N 条 HIGH 发现。"""
    src = (Path(__file__).resolve().parent.parent / "scripts"
           / "agent_kpi_auditor.py").read_text(encoding="utf-8")
    assert "csp_gaps" in src
    assert "csp_allowlist_missing" in src
