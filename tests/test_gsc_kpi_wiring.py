# -*- coding: utf-8 -*-
"""tests/test_gsc_kpi_wiring.py

锁三处：
  1. agent_kpi_auditor._gsc_real_metrics —— 环比口径、曝光加权、
     空壳/陈旧/样本不足的数据一律不接
  2. agent_kpi_auditor.normalize_metric_to_score —— 增长型目标下的负值给 0 分
  3. real_data_pull_engine._save_json —— 失败结果不覆盖上一份真实数据

为什么值得锁
------------
2026-09-18 之前，reports/real_data/gsc_real_data.json 里有真实的 GSC 数据
（28 天 daily 序列），但从未进过考核：content.organic_traffic 与
seo.organic_traffic_seo 都是 70 分「无数据基础分」。接入后：
  SEO     71.5 (B) → 56.5 (D)   曝光加权平均排名 55.8 → 42.52（改善 23.8%）
  Content 69.5 (C) → 55.5 (D)   曝光量 1936 → 539（跌 72.16%）
分数下降是因为真实数据本身是坏的，不是接入写错了。
这类「接入真数据 → 分数下降」如果不写测试，下一轮很容易被当成 bug 回滚掉。

_save_json 那次是真 bug：各 pull_* 函数在鉴权失败（NOT_CONFIGURED /
AUTH_FAILED / IMPORT_ERROR）时会以 is_real_data=False 的空壳覆盖上一份
真实数据。全新 clone / 干净 CI 沙箱恰好没有 .env 与
gsc-service-account-key.json——一次 `--all` 就销毁证据，之后直到
下一次鉴权成功之前都无法恢复。
"""
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import agent_kpi_auditor as K   # noqa: E402
import real_data_pull_engine as P  # noqa: E402

GSC_PATH = "gsc_real_data.json"


def _day(date: str, imp: int, pos: float, clicks: int = 0) -> dict:
    return {"date": date, "impressions": imp, "clicks": clicks,
            "ctr": 0.0, "position": pos}


def _write_gsc(tmp_path, daily, data_age_days=5, is_real=True,
               top_queries=None, top_pages=None, **extra):
    """写一份 gsc_real_data.json，日期全部相对「今天」生成，
    这样测试不会随着真实时间推进而失效。"""
    today = datetime.now().date()
    body = {
        "source": "gsc_api",
        "is_real_data": is_real,
        "status": "OK" if is_real else "NOT_CONFIGURED",
        "data_date": (today - timedelta(days=data_age_days)).isoformat(),
        "pull_time": (today - timedelta(days=data_age_days)).strftime("%Y-%m-%dT10:26:05"),
        "daily": daily,
        "top_queries": top_queries or [],
        "top_pages": top_pages or [],
        "metrics": {},
        "raw_source": "Google Search Console REST API v3",
        "error": None,
    }
    body.update(extra)
    d = tmp_path / "reports" / "real_data"
    d.mkdir(parents=True, exist_ok=True)
    p = d / GSC_PATH
    p.write_text(json.dumps(body), encoding="utf-8")
    return p


def _window(cutoff_date, n_first=14, n_second=14,
            first_imp=140, first_pos=55.8, second_imp=39, second_pos=42.52,
            first_clicks=2, second_clicks=3):
    """前 n_first 天高曝光差排名，后 n_second 天低曝光好排名。"""
    out = []
    for i in range(n_first):
        d = (cutoff_date - timedelta(days=n_first + n_second - 1 - i)).isoformat()
        out.append(_day(d, first_imp, first_pos, first_clicks if i == 0 else 0))
    for i in range(n_second):
        d = (cutoff_date - timedelta(days=n_second - 1 - i)).isoformat()
        out.append(_day(d, second_imp, second_pos, second_clicks if i == 0 else 0))
    return out


def _real_28(tmp_path, **kw):
    cutoff = datetime.now().date() - timedelta(days=5)
    return _write_gsc(tmp_path, _window(cutoff, **kw))


# ── 1. 环比口径 ───────────────────────────────────────────────

def test_real_data_computes_both_kpis(tmp_path):
    p = _real_28(tmp_path)
    r = K._gsc_real_metrics(p)
    assert r["avg_position_pct_change"] is not None
    assert r["organic_impressions_pct_change"] is not None
    assert r["note"] == ""
    assert r["evidence"], "evidence 必须暴露两半程的明细，否则分数无法复核"
    assert r["evidence"]["window_days"] == 28


def test_position_improvement_sign_and_value(tmp_path):
    """排名数字变小 = 改善 = 正数。55.8 → 42.52 应为 +23.8%。

    符号弄反是最容易犯的错：GSC 里 pos 1 是最好，55 是最差。
    """
    p = _real_28(tmp_path)
    r = K._gsc_real_metrics(p)
    assert r["avg_position_pct_change"] == 23.8


def test_impression_change_is_negative_on_decline(tmp_path):
    """1960 → 546 应为 -72.14%（不是 +72%）。符号弄反是最容易犯的错。"""
    p = _real_28(tmp_path)
    r = K._gsc_real_metrics(p)
    assert r["organic_impressions_pct_change"] == -72.14


def test_position_is_impression_weighted_not_simple_average(tmp_path):
    """曝光 100 的天权重必须远高于曝光 1 的天。

    构造：前半程 14 天，13 天曝光 1 排名 10，1 天曝光 1000 排名 50。
    简单平均 ≈ 21.3，曝光加权 ≈ 48.6。两者差 27 分。
    """
    cutoff = datetime.now().date() - timedelta(days=5)
    days = []
    for i in range(28):
        d = (cutoff - timedelta(days=27 - i)).isoformat()
        if i < 13:
            days.append(_day(d, imp=1, pos=10.0))
        elif i == 13:
            days.append(_day(d, imp=1000, pos=50.0))
        else:
            days.append(_day(d, imp=10, pos=20.0))
    p = _write_gsc(tmp_path, days)
    r = K._gsc_real_metrics(p)
    fh = r["evidence"]["first_half"]
    # 曝光加权：(13 天 × 1 曝光 × 排名10 + 1 天 × 1000 曝光 × 排名50) / 1013
    assert fh["weighted_position"] == 49.49
    # 简单平均只有 12.86——差 36.6 分，说明口径真的生效了
    simple_avg = round((13 * 10 + 50) / 14, 2)
    assert simple_avg == 12.86
    assert abs(fh["weighted_position"] - simple_avg) > 30.0
    assert fh["weighted_position"] > 40.0, "加权平均必须被高曝光天拉向 50"
    assert r["avg_position_pct_change"] is not None


def test_top10_counts(tmp_path):
    p = _write_gsc(
        tmp_path, _window(datetime.now().date() - timedelta(days=5)),
        top_queries=[{"query": "a", "position": 9.0}, {"query": "b", "position": 11.0}],
        top_pages=[{"page": "/x", "position": 10.0}, {"page": "/y", "position": 12.0}],
    )
    r = K._gsc_real_metrics(p)
    assert r["top10_queries"] == 1
    assert r["top10_pages"] == 1


# ── 2. 拒绝接入的情况 ─────────────────────────────────────────

def test_stub_data_is_rejected(tmp_path):
    """is_real_data=False 的空壳（鉴权失败产物）必须按 no_data 处理。

    空壳的 daily 是空列表，看起来和「真的没数据」长得一样，
    但它代表的是「采集器坏了」而不是「业务为零」——两者不能混。
    """
    p = _write_gsc(tmp_path, [], is_real=False)
    r = K._gsc_real_metrics(p)
    assert r["avg_position_pct_change"] is None
    assert "NOT_CONFIGURED" in r["note"]


def test_stale_data_is_rejected(tmp_path):
    """超过 GSC_MAX_AGE_DAYS 的快照不用于考核。

    这是 api_health 那次「11 天前报告」的同源缺陷：数据没消失、
    也没被标 no_data，只是旧。status=OK 会让读者当成当前状态。
    """
    p = _real_28(tmp_path)
    stale = K.GSC_MAX_AGE_DAYS + 3
    _write_gsc(tmp_path, json.loads(p.read_text(encoding="utf-8"))["daily"],
               data_age_days=stale)
    r = K._gsc_real_metrics(p)
    assert r["avg_position_pct_change"] is None
    assert "未刷新" in r["note"]
    assert r["age_days"] == stale


def test_stale_boundary_is_inclusive(tmp_path):
    """恰好等于阈值时仍然使用（> 而不是 >=）。"""
    p = _real_28(tmp_path)
    daily = json.loads(p.read_text(encoding="utf-8"))["daily"]
    _write_gsc(tmp_path, daily, data_age_days=K.GSC_MAX_AGE_DAYS)
    r = K._gsc_real_metrics(p)
    assert r["avg_position_pct_change"] is not None


def test_insufficient_rows_is_rejected(tmp_path):
    """少于 GSC_MIN_DAILY_ROWS 行时不接——拿 3 天数据算「环比」是造数字。"""
    cutoff = datetime.now().date() - timedelta(days=5)
    p = _write_gsc(tmp_path, _window(cutoff, n_first=3, n_second=3))
    r = K._gsc_real_metrics(p)
    assert r["avg_position_pct_change"] is None
    assert "行数不足" in r["note"]


def test_zero_impressions_first_half_is_rejected(tmp_path):
    """前半程曝光为 0 时无法算环比，必须返回 None 而不是除零崩溃或给 0。"""
    cutoff = datetime.now().date() - timedelta(days=5)
    p = _write_gsc(tmp_path, _window(cutoff, first_imp=0))
    r = K._gsc_real_metrics(p)
    assert r["organic_impressions_pct_change"] is None


def test_missing_file_is_not_an_error(tmp_path):
    r = K._gsc_real_metrics(tmp_path / "reports" / "real_data" / GSC_PATH)
    assert r["avg_position_pct_change"] is None
    assert "无 gsc_real_data.json" in r["note"]


def test_malformed_rows_are_dropped(tmp_path):
    """daily 里混入缺字段/坏类型的行时按行丢弃，而不是整份报错。"""
    cutoff = datetime.now().date() - timedelta(days=5)
    days = _window(cutoff)
    days[3] = {"date": "2026-09-01", "impressions": "many"}   # 类型错
    days[7] = {"date": "2026-09-02"}                          # 缺 position
    p = _write_gsc(tmp_path, days)
    r = K._gsc_real_metrics(p)
    assert r["avg_position_pct_change"] is not None
    assert r["evidence"]["window_days"] == 26


def test_age_from_pull_time_when_no_data_date(tmp_path):
    cutoff = datetime.now().date() - timedelta(days=5)
    body = _write_gsc(tmp_path, _window(cutoff))
    d = json.loads(body.read_text(encoding="utf-8"))
    d.pop("data_date")
    body.write_text(json.dumps(d), encoding="utf-8")
    r = K._gsc_real_metrics(body)
    assert r["avg_position_pct_change"] is not None
    assert r["age_days"] == 5, "没有 data_date 时应退回 pull_time 判年龄"


# ── 3. 负值归一化 ─────────────────────────────────────────────

def _kpi(target="环比增长≥10%", type_="revenue"):
    return {"id": "organic_traffic", "name": "自然搜索流量", "weight": 20,
            "target": target, "type": type_}


def test_negative_growth_value_scores_zero():
    """曝光环比跌 72% 必须给 0 分。

    不加这条守护的话：-72 落进 _legacy_normalize 底部 `return value`，
    分数 -72 被 max(0,...) 截成 0——结果偶然正确，靠的是截断不是语义；
    而落进 _ratio_ladder 时负值最差也拿 30 分，「明显退步」被奖励非零分。
    """
    assert K.normalize_metric_to_score(_kpi(), -72.16) == 0.0
    assert K.normalize_metric_to_score(_kpi("环比提升≥5%"), -1.0) == 0.0


def test_negative_value_without_growth_target_is_untouched():
    """只限「环比」目标，不要误伤其他 KPI。"""
    assert K.normalize_metric_to_score(
        {"id": "x", "target": "≥95%", "type": "process"}, -5.0) != 0.0
    assert K.normalize_metric_to_score(
        {"id": "x", "target": "≤2.5s", "type": "process", "unit": "seconds"},
        -1.0) != 0.0


def test_positive_growth_value_unchanged_by_new_guard():
    """回归锁：正值路径的行为必须与引入守护之前逐分一致。"""
    # process 类型（seo.avg_position 的实际定义）：走 _ratio_ladder
    assert K.normalize_metric_to_score(_kpi("环比提升≥5%", type_="process"), 23.8) == 95.0
    # revenue 类型 + unit=pct（organic_traffic 的实际定义）：20 对目标 8 → 95.0
    assert K.normalize_metric_to_score(
        {"id": "organic_traffic", "target": "环比增长≥8%", "type": "revenue",
         "unit": "pct"}, 20.0) == 95.0
    # 达标线以下（20 对目标 25，比值 0.8）→ 70.0
    assert K.normalize_metric_to_score(
        {"id": "organic_traffic", "target": "环比增长≥25%", "type": "revenue",
         "unit": "pct"}, 20.0) == 70.0
    # 货币单位不受影响：零营收仍是 0 分
    assert K.normalize_metric_to_score(
        {"id": "r", "target": "环比增长≥10%", "type": "revenue",
         "unit": "currency"}, 0.0) == 0.0


# ── 4. _save_json 防覆盖 ──────────────────────────────────────

def _save_case(tmp_path, existing=None, incoming=None):
    p = tmp_path / "gsc_real_data.json"
    if existing is not None:
        p.write_text(json.dumps(existing), encoding="utf-8")
    return p


def test_stub_does_not_overwrite_real_data(tmp_path):
    """核心回归锁：NOT_CONFIGURED 空壳不能覆盖上一份真实数据。"""
    p = _save_case(
        tmp_path,
        existing={"is_real_data": True, "status": "OK", "daily": [{"date": "a"}]},
    )
    written = P._save_json(p, {"is_real_data": False, "status": "NOT_CONFIGURED",
                               "daily": []})
    assert written is False
    on_disk = json.loads(p.read_text(encoding="utf-8"))
    assert on_disk["is_real_data"] is True, "真实数据被失败结果覆盖了"
    assert on_disk["status"] == "OK"


def test_auth_failed_stub_also_blocked(tmp_path):
    p = _save_case(tmp_path, existing={"is_real_data": True, "daily": [1]})
    assert P._save_json(p, {"is_real_data": False, "status": "AUTH_FAILED"}) is False
    assert json.loads(p.read_text(encoding="utf-8"))["daily"] == [1]


def test_real_data_overwrites_old_real_data(tmp_path):
    """真实数据永远可以覆盖旧的真实数据——否则数据永远不会刷新。"""
    p = _save_case(tmp_path, existing={"is_real_data": True, "data_date": "old"})
    assert P._save_json(p, {"is_real_data": True, "data_date": "new"}) is True
    assert json.loads(p.read_text(encoding="utf-8"))["data_date"] == "new"


def test_stub_writes_when_no_existing_file(tmp_path):
    """没有上一份数据时，失败结果照写——让读者看到 NOT_CONFIGURED，
    而不是一个「文件不存在」的模糊状态。"""
    p = _save_case(tmp_path)
    assert P._save_json(p, {"is_real_data": False, "status": "IMPORT_ERROR"}) is True
    assert json.loads(p.read_text(encoding="utf-8"))["status"] == "IMPORT_ERROR"


def test_summary_report_without_is_real_data_is_unaffected(tmp_path):
    """data_validation 这类汇总的既有文件里没有 is_real_data 字段，
    所以防覆盖守护不会触发——被拦下的只有「真实数据被空壳覆盖」一种情况。
    这是回归锁：守护不能误伤正常写入。"""
    p = _save_case(tmp_path, existing={"overall_status": "PASS", "sources": {}})
    assert P._save_json(p, {"overall_status": "FAIL", "sources": {}}) is True
    assert json.loads(p.read_text(encoding="utf-8"))["overall_status"] == "FAIL"


def test_corrupt_existing_file_is_overwritten(tmp_path):
    """上一份文件坏了（无法解析）时，失败结果也应照写，别卡死。"""
    p = tmp_path / "gsc_real_data.json"
    p.write_text("{broken", encoding="utf-8")
    assert P._save_json(p, {"is_real_data": False, "status": "NOT_CONFIGURED"}) is True
    assert json.loads(p.read_text(encoding="utf-8"))["status"] == "NOT_CONFIGURED"


def test_multi_partner_all_failed_is_blocked(tmp_path):
    """multi_partner 的 is_real_data 是 `connected > 0`：全部连接失败时为 False，
    同样不该覆盖上一份。"""
    p = _save_case(tmp_path, existing={"is_real_data": True, "connected": 3})
    assert P._save_json(p, {"is_real_data": False, "connected": 0}) is False
    assert json.loads(p.read_text(encoding="utf-8"))["connected"] == 3


# ── 5. 接线纪律 ───────────────────────────────────────────────

def test_top10_keywords_absolute_count_is_not_wired():
    """本仓库的接入原则（agent_kpi_auditor 内注释）明确写：
    绝对计数对「环比增长」型目标不接——sessions=11 对「环比增长≥8%」
    会产生看起来精确实则无意义的分数。top10_keywords 当前值是 0，
    且只有一个快照无法算环比，所以必须保持 no_data。
    """
    src = (Path(__file__).resolve().parent.parent / "scripts"
           / "agent_kpi_auditor.py").read_text(encoding="utf-8")
    # 接线段只写 avg_position / organic_traffic / organic_traffic_seo
    assert '["top10_keywords"] = ' not in src, "绝对计数不应接入环比型目标"
    assert '["avg_position"] = ' in src
    assert '["organic_traffic_seo"] = ' in src


def test_gsc_section_documents_the_traffic_proxy_caveat():
    """曝光量是「流量」的代理指标，不是流量本身。
    打印和 docstring 都必须说出来，否则读者会把曝光环比当成流量环比。"""
    src = (Path(__file__).resolve().parent.parent / "scripts"
           / "agent_kpi_auditor.py").read_text(encoding="utf-8")
    assert "代理" in src
