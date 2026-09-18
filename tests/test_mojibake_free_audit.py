# -*- coding: utf-8 -*-
"""tests/test_mojibake_free_audit.py

锁 content.mojibake_free 的口径，并锁住它不再从错误来源取值。

为什么值得锁
------------
content.mojibake_free（编码乱码合格率，目标 100%，权重 10%）原先这样取值：

    coverage_reports = sorted(.../reports/content_coverage/*.json)
    pf = cov.get("post_fields", {})
    metrics["content"]["mojibake_free"] = 100.0 if pf["last_updated"]["passed"] else 60.0

`post_fields.last_updated` 测的是「文章 front-matter 有没有填 last_updated
字段」——61/61 篇都填了，coverage 100.0 ≥ 阈值 90.0，passed=True。

所以这个 KPI 长期稳定输出 100 分，**不管正文里有没有乱码**。
一篇文章满篇乱码，只要 front-matter 的 last_updated 填了，
就拿满分「编码乱码合格率」。

这是本轮之前最隐蔽的一处假绿灯：它打出来的分数恰好是漂亮的 100 分，
看起来毫无问题，所以一直没被怀疑。
KPI 定义里声明的源一直是 content_quality_validator(P0)，
只是从来没接上。

新口径读 reports/content_audit/validator_output.json（由
content-quality-audit.yml 每次审计生成），
「完全干净」= mojibake_issues 为空 且 encoding_errors 为空。
"""
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import agent_kpi_auditor as K   # noqa: E402


def _write(tmp_path, results, name="validator_output.json"):
    p = tmp_path / name
    p.write_text(json.dumps({"results": results,
                             "passed_count": len(results),
                             "total": len(results)},
                            ensure_ascii=False), encoding="utf-8")
    return p


def _rows(n, **kw):
    """生成 n 个文件记录，每个字段默认空列表（干净）。"""
    return [{"file": f"post_{i}.md", "mojibake_issues": [],
             "encoding_errors": [], "passed": True, **kw} for i in range(n)]


# ── 口径 ─────────────────────────────────────────────────────

def test_all_clean_is_100(tmp_path):
    p = _write(tmp_path, _rows(63))
    r = K._mojibake_free(p)
    assert r["rate"] == 100.0
    assert r["clean"] == 63
    assert r["total"] == 63
    assert r["mojibake_files"] == 0
    assert r["encoding_files"] == 0


def test_mojibake_hits_lower_rate(tmp_path):
    rows = _rows(10)
    rows[0]["mojibake_issues"] = ["c382"]
    rows[1]["mojibake_issues"] = ["c3a2"]
    p = _write(tmp_path, rows)
    r = K._mojibake_free(p)
    assert r["rate"] == 80.0
    assert r["clean"] == 8
    assert r["mojibake_files"] == 2


def test_encoding_errors_also_count(tmp_path):
    """KPI 名是「编码乱码合格率」，解码层错误同样算脏。
    只查双重编码会漏掉这一类。"""
    rows = _rows(5)
    rows[0]["encoding_errors"] = ["'utf-8' codec can't decode byte 0xe4"]
    p = _write(tmp_path, rows)
    r = K._mojibake_free(p)
    assert r["rate"] == 80.0
    assert r["encoding_files"] == 1


def test_file_dirty_both_ways_is_counted_once_as_not_clean(tmp_path):
    """同一文件两种问题都命中时：两个计数器各记 1，
    但它只让 clean 少 1（不能减 2）。"""
    rows = _rows(4)
    rows[0]["mojibake_issues"] = ["c382"]
    rows[0]["encoding_errors"] = ["err"]
    p = _write(tmp_path, rows)
    r = K._mojibake_free(p)
    assert r["clean"] == 3, "一个脏文件只能让干净数减 1"
    assert r["rate"] == 75.0
    assert r["mojibake_files"] == 1
    assert r["encoding_files"] == 1


def test_empty_lists_mean_clean(tmp_path):
    """空列表是「没发现」，不是「没测」。"""
    rows = _rows(3)
    for r in rows:
        r["mojibake_issues"] = []
        r["encoding_errors"] = []
    p = _write(tmp_path, rows)
    r = K._mojibake_free(p)
    assert r["rate"] == 100.0


def test_missing_keys_count_as_clean(tmp_path):
    """validator 输出缺字段时按「没发现」处理，不崩。"""
    p = _write(tmp_path, [{"file": "a.md"}, {"file": "b.md"}])
    r = K._mojibake_free(p)
    assert r["rate"] == 100.0
    assert r["total"] == 2


# ── not_measured：测不出来不能给假分数 ────────────────────────

def test_no_file_is_not_measured(tmp_path):
    r = K._mojibake_free(tmp_path / "nope.json")
    assert r["rate"] is None
    assert "无 content_quality_validator 输出" in r["note"]


def test_bad_json_is_not_measured(tmp_path):
    p = tmp_path / "validator_output.json"
    p.write_text("{broken", encoding="utf-8")
    r = K._mojibake_free(p)
    assert r["rate"] is None
    assert "读取失败" in r["note"]


def test_missing_results_key_is_not_measured(tmp_path):
    p = tmp_path / "validator_output.json"
    p.write_text(json.dumps({"summary": {}}), encoding="utf-8")
    r = K._mojibake_free(p)
    assert r["rate"] is None
    assert "results" in r["note"]


def test_empty_results_is_not_measured(tmp_path):
    """0/0 不是 100%——那是没测到。"""
    p = _write(tmp_path, [])
    r = K._mojibake_free(p)
    assert r["rate"] is None
    assert "results" in r["note"]


def test_non_list_results_is_not_measured(tmp_path):
    p = tmp_path / "validator_output.json"
    p.write_text(json.dumps({"results": "corrupt"}), encoding="utf-8")
    r = K._mojibake_free(p)
    assert r["rate"] is None


def test_all_non_dict_entries_is_not_measured(tmp_path):
    """results 里全是坏行时，total>0 但没有可判定的记录。"""
    p = _write(tmp_path, ["x", None, 42])
    r = K._mojibake_free(p)
    assert r["rate"] == 0.0, "全是坏行时 clean=0，rate=0，而不是假装 100%"
    assert r["total"] == 3


def test_mixed_bad_and_good_entries(tmp_path):
    rows = [{"file": "good.md", "mojibake_issues": [], "encoding_errors": []},
            "junk", None,
            {"file": "dirty.md", "mojibake_issues": ["c382"],
             "encoding_errors": []}]
    p = _write(tmp_path, rows)
    r = K._mojibake_free(p)
    assert r["total"] == 4
    assert r["clean"] == 1
    assert r["mojibake_files"] == 1
    assert r["rate"] == 25.0


# ── 新鲜度 ───────────────────────────────────────────────────

def test_age_days_from_mtime(tmp_path):
    """用 os.utime 而不是 Path.touch——这个环境里 touch 不生效
    （mtime 停在当前时间，4 天前的目标写不进去）。"""
    import os
    p = _write(tmp_path, _rows(2))
    t = (datetime.now() - timedelta(days=4)).timestamp()
    os.utime(p, (t, t))
    r = K._mojibake_free(p)
    assert 3 <= r["age_days"] <= 5, f"4 天前的文件报出 {r['age_days']}"
    assert r["rate"] == 100.0, "缺年龄不该影响分数"


# ── 接线纪律 ─────────────────────────────────────────────────

def _code_only(src):
    """剥掉 docstring 和 # 注释，只留可执行代码。

    全文匹配会命中我自己写注释时引用的旧字段名，那是 Round 14/17
    修过的同类假阳性。这里按行切掉 # 之后的部分。
    """
    body = src.split('"""', 2)[2] if src.count('"""') >= 2 else src
    return "\n".join(l.split("#", 1)[0] for l in body.splitlines())


def test_auditor_no_longer_reads_content_coverage_for_mojibake():
    """这是本轮修的根因：mojibake_free 不许再从 content_coverage 取。"""
    import inspect
    code = _code_only(inspect.getsource(K.collect_metrics))
    assert "_mojibake_free()" in code
    assert "post_fields" not in code, "不能再从 content_coverage 的 post_fields 取"
    assert "last_updated" not in code, "不能再用 last_updated.passed 冒充编码合格率"
    assert "coverage_reports" not in code, "content_coverage 的读取块应该整块删掉"


def test_mojibake_free_wired_into_content_metrics():
    src = (Path(__file__).resolve().parent.parent / "scripts"
           / "agent_kpi_auditor.py").read_text(encoding="utf-8")
    assert 'metrics["content"]["mojibake_free"]' in src
    assert "_mojibake_free()" in src


def test_reads_the_validator_output_path():
    """默认路径必须是 content_quality_validator 的输出，
    而且必须是 content-quality-audit.yml 实际重定向到的那个文件。"""
    wf = (Path(__file__).resolve().parent.parent
          / ".github/workflows/content-quality-audit.yml").read_text(encoding="utf-8")
    assert "reports/content_audit/validator_output.json" in wf, (
        "workflow 里的路径变了，接线会读空")
    import inspect
    code = inspect.getsource(K._mojibake_free).split('"""', 2)[2]
    assert "validator_output.json" in code
    assert "content_audit" in code


def test_breakdown_is_printed_not_just_the_score():
    """只打一个 100% 会让人以为测得很宽。
    必须打出干净数/总数和两类命中数。"""
    src = (Path(__file__).resolve().parent.parent / "scripts"
           / "agent_kpi_auditor.py").read_text(encoding="utf-8")
    assert "完全干净" in src
    assert "双重编码" in src
    assert "解码错误" in src
