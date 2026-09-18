# -*- coding: utf-8 -*-
"""tests/test_brand_consistency_audit.py

锁 social.brand_consistency 的口径与解析。

为什么值得锁
------------
brand_identity_audit.py 被 3 个 workflow 跑（deploy-cloudflare-pages /
content-quality-audit / weekly-blog-update），但它只写 markdown 不写 JSON，
而且 deploy-cloudflare-pages.yml 从来没把输出 commit 回仓库。
2026-09-18 实测：仓库里那份报告已停在 18 天前。

这是个静默假绿灯：某次部署若引入了品牌违规（FAIL>0），
仓库里看到的仍是那份 0-FAIL 的旧报告，agent_kpi_auditor.py
据此打出 100% 品牌一致性。和 api_health 报告 11 天不刷新是同类缺陷。

本轮做两件事：
  1. agent_kpi_auditor.py 新增 _brand_consistency() 解析 markdown Summary
  2. deploy-cloudflare-pages.yml 补一个 commit 步骤，让输出真正入库

口径严格按脚本自己的定义：
  FAIL    = 命中 forbidden_phrases 或 FICTIONAL_PATTERNS → 真违规
  WARN    = 品牌语言尚未出现，脚本注释明确写「no violations」
  PASS    = 品牌语言已出现
  MISSING = 文件不存在
一致性 = PASS / (PASS + FAIL)。WARN 不进分母。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import agent_kpi_auditor as K   # noqa: E402


SUMMARY_LINE = "Summary: 16/107 PASS; 0 FAIL; 0 MISSING (WARN = editorial language not yet present, no violations)."
GENERATED_LINE = "- Generated: 2026-08-31"


def _write(tmp_path, body, name="P1_BRAND_02_BRAND_IDENTITY_AUDIT.md"):
    p = tmp_path / name
    p.write_text(body, encoding="utf-8")
    return p


def _report(pass_, total, fail, missing=0, generated=None):
    body = []
    if generated:
        body.append(f"- Generated: {generated}")
    body.append(f"Summary: {pass_}/{total} PASS; {fail} FAIL; {missing} MISSING "
                f"(WARN = editorial language not yet present, no violations).")
    body.append("")
    body.append("| layer | file | status | forbidden | fictional | editorial |")
    body.append("|---|---|---|---|---|---|")
    return "\n".join(body)


# ── 解析与口径 ──────────────────────────────────────────────

def test_zero_fail_means_100_consistency(tmp_path):
    p = _write(tmp_path, _report(16, 107, 0, generated="2026-09-18"))
    r = K._brand_consistency(p)
    assert r["consistency"] == 100.0
    assert r["pass"] == 16
    assert r["total"] == 107
    assert r["fail"] == 0
    assert r["warn"] == 91, "WARN = total - PASS - FAIL"


def test_coverage_is_reported_separately(tmp_path):
    """一致性 100% 只表示「没有矛盾的品牌表述」，
    不代表每个页面都写了品牌语言。覆盖率必须单独报出来。"""
    p = _write(tmp_path, _report(16, 107, 0, generated="2026-09-18"))
    r = K._brand_consistency(p)
    assert r["coverage"] == 15.0
    assert r["consistency"] == 100.0, "两个数不能混成一个"


def test_failures_lower_consistency(tmp_path):
    p = _write(tmp_path, _report(90, 100, 10, generated="2026-09-18"))
    r = K._brand_consistency(p)
    assert r["consistency"] == 90.0, "一致性 = PASS/(PASS+FAIL)"


def test_warn_does_not_count_as_failure(tmp_path):
    """脚本明确写 WARN = no violations。把 86 个 WARN 当失败算，
    会把 100% 的正确结论打成 16%。"""
    p = _write(tmp_path, _report(16, 107, 0, generated="2026-09-18"))
    r = K._brand_consistency(p)
    assert r["consistency"] == 100.0
    assert r["warn"] == 91


def test_no_pass_no_fail_is_not_measured(tmp_path):
    """0/0 不能算 100%——那是没测到，不是全对。"""
    p = _write(tmp_path, _report(0, 0, 0, generated="2026-09-18"))
    r = K._brand_consistency(p)
    assert r["consistency"] is None
    assert "没有任何 PASS/FAIL" in r["note"]


def test_missing_file_is_not_measured(tmp_path):
    r = K._brand_consistency(tmp_path / "does_not_exist.md")
    assert r["consistency"] is None
    assert "无 brand_identity_audit 报告" in r["note"]


def test_missing_summary_line_is_not_measured(tmp_path):
    """脚本输出格式变了不能被静默当成 0 违规。"""
    p = _write(tmp_path, "# 品牌审计报告\n\n本次审计未生成 Summary 行。")
    r = K._brand_consistency(p)
    assert r["consistency"] is None
    assert "Summary" in r["note"]


def test_empty_file_is_not_measured(tmp_path):
    p = _write(tmp_path, "")
    r = K._brand_consistency(p)
    assert r["consistency"] is None


def test_malformed_summary_is_not_measured(tmp_path):
    """数字缺失/乱序不能崩，也不能给出一个假分数。"""
    for body in ("Summary: PASS; FAIL; MISSING",
                 "Summary: x/107 PASS; 0 FAIL; 0 MISSING",
                 "summary: 16/107 pass; 0 fail; 0 missing"):
        p = _write(tmp_path, body)
        r = K._brand_consistency(p)
        assert r["consistency"] is None, f"不该解析出分数：{body!r}"


# ── 文件身份 ─────────────────────────────────────────────────

def test_does_not_confuse_legacy_report(tmp_path):
    """--legacy 模式写 P1_BRAND_02_LEGACY_PERSONA_REVIEW.md，
    查的是旧人设短语，不是品牌一致性。绝不能当成 brand 报告读。"""
    p = _write(tmp_path, _report(5, 63, 2, generated="2026-09-18"),
               name="P1_BRAND_02_LEGACY_PERSONA_REVIEW.md")
    r = K._brand_consistency(tmp_path / "P1_BRAND_02_BRAND_IDENTITY_AUDIT.md")
    assert r["consistency"] is None, "不能把 legacy 报告当 brand 报告"


def test_legacy_report_shape_differs_so_parse_must_not_succeed(tmp_path):
    """legacy 报告正文没有 Summary: 行（它是「统计：content/posts 共 N 篇」），
    所以即使误读也不会碰巧解析出数字。"""
    body = ("# P1-BRAND-02 — Legacy Persona Content Review\n\n"
            "- Generated: 2026-09-18\n\n"
            "统计：content/posts 共 63 篇，命中 legacy persona 短语 0 篇。\n")
    p = _write(tmp_path, body, name="P1_BRAND_02_BRAND_IDENTITY_AUDIT.md")
    r = K._brand_consistency(p)
    assert r["consistency"] is None


# ── 新鲜度 ───────────────────────────────────────────────────

def test_age_days_from_generated_line(tmp_path):
    p = _write(tmp_path, _report(16, 107, 0, generated="2026-08-31"))
    r = K._brand_consistency(p)
    assert r["age_days"] >= 17, f"2026-08-31 到现在不该小于 17 天，实际 {r['age_days']}"
    assert r["generated"] == "2026-08-31"


def test_today_generated_is_zero_days_old(tmp_path):
    from datetime import date
    p = _write(tmp_path, _report(16, 107, 0, generated=date.today().isoformat()))
    r = K._brand_consistency(p)
    assert r["age_days"] == 0


def test_missing_generated_line_keeps_unknown_age(tmp_path):
    p = _write(tmp_path, _report(16, 107, 0, generated=None))
    r = K._brand_consistency(p)
    assert r["consistency"] == 100.0, "缺 Generated 不影响分数"
    assert r["age_days"] == -1
    assert r["generated"] == ""


def test_bogus_generated_date_does_not_crash(tmp_path):
    p = _write(tmp_path, _report(16, 107, 0, generated="not-a-date"))
    r = K._brand_consistency(p)
    assert r["consistency"] == 100.0
    assert r["age_days"] == -1


# ── 接线纪律 ─────────────────────────────────────────────────

def test_auditor_reads_the_brand_identity_report_only():
    """接线代码必须只读 brand identity 那份。

    用 inspect.getsource 拿函数源码并剥掉 docstring——
    全文匹配会命中我自己的说明文字（docstring 里故意提了
    legacy 文件名来解释两者的区别），那是 Round 14 修过的同类假阳性。
    """
    import inspect
    fn_src = inspect.getsource(K._brand_consistency)
    # docstring 是第一个 """...""" 块（恰好 2 个 """）；剥掉它，只看可执行代码
    code_only = fn_src.split('"""', 2)[2] if fn_src.count('"""') >= 2 else fn_src
    assert "P1_BRAND_02_BRAND_IDENTITY_AUDIT.md" in code_only
    assert "P1_BRAND_02_LEGACY_PERSONA_REVIEW.md" not in code_only, (
        "可执行代码不能引用 legacy 报告路径")


def test_brand_consistency_is_wired_into_social_metrics():
    src = (Path(__file__).resolve().parent.parent / "scripts"
           / "agent_kpi_auditor.py").read_text(encoding="utf-8")
    assert 'metrics["social"]["brand_consistency"]' in src
    assert "_brand_consistency()" in src


def test_coverage_gap_warning_is_printed():
    """零违规但覆盖不足必须单独提示——只打 100% 会掩盖覆盖缺口。"""
    src = (Path(__file__).resolve().parent.parent / "scripts"
           / "agent_kpi_auditor.py").read_text(encoding="utf-8")
    assert "零违规但覆盖不足" in src
    assert "覆盖率" in src


def test_deploy_workflow_commits_the_brand_report():
    """deploy-cloudflare-pages.yml 每次部署都跑 brand_identity_audit.py，
    但不 commit 输出的话仓库里的报告会永久停在旧版本——静默假绿灯。"""
    wf = (Path(__file__).resolve().parent.parent
          / ".github/workflows/deploy-cloudflare-pages.yml").read_text(encoding="utf-8")
    assert "P1_BRAND_02_BRAND_IDENTITY_AUDIT.md" in wf
    # git add 必须包含它，不能只在注释里出现
    add_line = [l for l in wf.splitlines()
                if l.strip().startswith("git add")
                and "P1_BRAND_02_BRAND_IDENTITY_AUDIT.md" in l]
    assert add_line, "brand 报告没有被 git add"
    assert "git commit" in wf.split("P1_BRAND_02_BRAND_IDENTITY_AUDIT.md", 1)[-1][:900]


def test_brand_commit_step_is_non_fatal():
    """推失败不能阻断部署——报告和 manifest 同级别。"""
    wf = (Path(__file__).resolve().parent.parent
          / ".github/workflows/deploy-cloudflare-pages.yml").read_text(encoding="utf-8")
    seg = wf.split("Commit brand identity audit report back to repo", 1)[-1]
    assert "|| echo" in seg, "push 失败必须非致命"
    assert "if: always()" in seg, "必须始终运行，否则失败的部署不刷新报告"
