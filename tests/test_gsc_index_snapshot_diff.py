# -*- coding: utf-8 -*-
"""gsc_index_snapshot / _index_snapshot_diff 的单元测试。

覆盖三件事：

  1. 采集器的快照落盘布局是「不可变日期文件」，且同名天覆盖而不是新增
  2. 差值逻辑的三种输入态：0 份 / 1 份 / 2 份快照
  3. 判据是 impressions > 0（可见性代理），不是「页面存在」

不测真实 GSC API 调用 —— 那需要服务账号密钥，属于集成测试，归
scripts/gsc_index_snapshot.py --list 的人工验证。
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "scripts"))

import gsc_index_snapshot as gis  # noqa: E402
import reporting_kpi_engine as engine  # noqa: E402


# ---------------------------------------------------------------------------
# 快照落盘
# ---------------------------------------------------------------------------
class TestSnapshotLayout:
    def _snapshot(self, day="2026-09-17", pages=None):
        return {
            "status": "OK",
            "site": "https://www.chinaboundtravel.com/",
            "window": {"start": "2026-08-21", "end": day, "days": 28},
            "generated_at": f"{day}T00:30:00Z",
            "totals": {"impressions": 100, "clicks": 4, "pages_with_data": 2},
            "pages": pages or {
                "https://www.chinaboundtravel.com/a/": {"impressions": 60,
                                                        "clicks": 3, "position": 5.0},
                "https://www.chinaboundtravel.com/b/": {"impressions": 40,
                                                        "clicks": 1, "position": 9.0},
            },
        }

    def test_write_snapshot_uses_window_end_in_filename(self, tmp_path, monkeypatch):
        monkeypatch.setattr(gis, "SNAPSHOT_DIR", tmp_path)
        out = gis.write_snapshot(self._snapshot("2026-09-17"))
        assert out.name == "INDEX_PAGE_SNAPSHOT_2026-09-17.json"
        assert out.is_file()

    def test_write_snapshot_rejects_non_ok(self, tmp_path, monkeypatch):
        monkeypatch.setattr(gis, "SNAPSHOT_DIR", tmp_path)
        out = gis.write_snapshot({"status": "API_ERROR", "error": "boom"})
        assert out is None
        assert list(tmp_path.iterdir()) == []

    def test_same_day_overwrites_not_duplicates(self, tmp_path, monkeypatch):
        monkeypatch.setattr(gis, "SNAPSHOT_DIR", tmp_path)
        gis.write_snapshot(self._snapshot("2026-09-17"))
        gis.write_snapshot(self._snapshot("2026-09-17"))
        assert len(list(tmp_path.glob("INDEX_PAGE_SNAPSHOT_*.json"))) == 1

    def test_list_snapshots_sorted_by_date(self, tmp_path, monkeypatch):
        monkeypatch.setattr(gis, "SNAPSHOT_DIR", tmp_path)
        gis.write_snapshot(self._snapshot("2026-09-18"))
        gis.write_snapshot(self._snapshot("2026-09-16"))
        gis.write_snapshot(self._snapshot("2026-09-17"))
        names = [p.name for p in gis.list_snapshots()]
        assert names == ["INDEX_PAGE_SNAPSHOT_2026-09-16.json",
                         "INDEX_PAGE_SNAPSHOT_2026-09-17.json",
                         "INDEX_PAGE_SNAPSHOT_2026-09-18.json"]

    def test_list_snapshots_empty_when_dir_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(gis, "SNAPSHOT_DIR", tmp_path / "nope")
        assert gis.list_snapshots() == []


# ---------------------------------------------------------------------------
# 差值逻辑
# ---------------------------------------------------------------------------
class TestIndexSnapshotDiff:
    def _seed(self, tmp_path, snap_a, snap_b):
        (tmp_path / "INDEX_PAGE_SNAPSHOT_2026-09-16.json").write_text(
            json.dumps(snap_a), encoding="utf-8")
        (tmp_path / "INDEX_PAGE_SNAPSHOT_2026-09-17.json").write_text(
            json.dumps(snap_b), encoding="utf-8")

    def test_zero_snapshots_is_insufficient_baseline(self, monkeypatch):
        monkeypatch.setattr(gis, "SNAPSHOT_DIR",
                            Path("/tmp/does-not-exist-gsc-test"))
        r = engine._index_snapshot_diff()
        assert r["status"] == "INSUFFICIENT_BASELINE"
        assert r["newly_indexed"] is None
        assert r["losing_visibility"] is None

    def test_single_snapshot_is_insufficient_baseline(self, tmp_path, monkeypatch):
        """第一天只建基线，绝不把全量报成「新索引」。

        若这里报 0，日报会长期显示「今日新增 0 个索引页」—— 一个既不真也不假、
        但完全没有信息量的数字，比 NOT_AVAILABLE 更糟。
        """
        monkeypatch.setattr(gis, "SNAPSHOT_DIR", tmp_path)
        (tmp_path / "INDEX_PAGE_SNAPSHOT_2026-09-17.json").write_text(
            json.dumps({
                "window": {"end": "2026-09-17"},
                "pages": {
                    "https://www.chinaboundtravel.com/a/": {"impressions": 60},
                },
            }), encoding="utf-8")
        r = engine._index_snapshot_diff()
        assert r["status"] == "INSUFFICIENT_BASELINE"
        assert r["newly_indexed"] is None
        assert "1 份快照" in r["note"]

    def test_two_snapshots_computes_both_directions(self, tmp_path, monkeypatch):
        monkeypatch.setattr(gis, "SNAPSHOT_DIR", tmp_path)
        prior = {"window": {"end": "2026-09-16"}, "pages": {
            "https://x.test/keep/": {"impressions": 10},
            "https://x.test/gone/": {"impressions": 5},
            "https://x.test/zeroed/": {"impressions": 3},
        }}
        latest = {"window": {"end": "2026-09-17"}, "pages": {
            "https://x.test/keep/": {"impressions": 12},
            "https://x.test/zeroed/": {"impressions": 0},
            "https://x.test/new1/": {"impressions": 4},
            "https://x.test/new2/": {"impressions": 1},
        }}
        self._seed(tmp_path, prior, latest)

        r = engine._index_snapshot_diff()
        assert r["status"] == "OK"
        assert r["newly_indexed"] == 2          # new1, new2
        assert r["losing_visibility"] == 2      # gone (消失), zeroed (归零)
        assert r["latest_day"] == "2026-09-17"
        assert r["prior_day"] == "2026-09-16"
        assert set(r["detail"]["newly_indexed_urls"]) == {
            "https://x.test/new1/", "https://x.test/new2/"}
        assert set(r["detail"]["losing_visibility_urls"]) == {
            "https://x.test/gone/", "https://x.test/zeroed/"}

    def test_visibility_means_impressions_gt_zero_not_existence(self, tmp_path, monkeypatch):
        """impressions == 0 的页面不算「可见」—— 它是索引了但没曝光，
        不能算失去可见性，否则一个 28 天没人搜到的页面会被误报为失去可见性。
        """
        monkeypatch.setattr(gis, "SNAPSHOT_DIR", tmp_path)
        prior = {"window": {"end": "2026-09-16"}, "pages": {
            "https://x.test/always-zero/": {"impressions": 0},
            "https://x.test/visible/": {"impressions": 7},
        }}
        latest = {"window": {"end": "2026-09-17"}, "pages": {
            "https://x.test/always-zero/": {"impressions": 0},
            "https://x.test/visible/": {"impressions": 9},
        }}
        self._seed(tmp_path, prior, latest)

        r = engine._index_snapshot_diff()
        assert r["newly_indexed"] == 0
        assert r["losing_visibility"] == 0

    def test_malformed_snapshot_is_insufficient_baseline_not_crash(self, tmp_path, monkeypatch):
        monkeypatch.setattr(gis, "SNAPSHOT_DIR", tmp_path)
        (tmp_path / "INDEX_PAGE_SNAPSHOT_2026-09-16.json").write_text(
            "{not valid json", encoding="utf-8")
        (tmp_path / "INDEX_PAGE_SNAPSHOT_2026-09-17.json").write_text(
            json.dumps({"window": {"end": "2026-09-17"}, "pages": {}}),
            encoding="utf-8")
        r = engine._index_snapshot_diff()
        assert r["status"] == "INSUFFICIENT_BASELINE"
        assert "读取失败" in r["note"]

    def test_pages_key_absent_treated_as_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr(gis, "SNAPSHOT_DIR", tmp_path)
        (tmp_path / "INDEX_PAGE_SNAPSHOT_2026-09-16.json").write_text(
            json.dumps({"window": {"end": "2026-09-16"}}), encoding="utf-8")
        (tmp_path / "INDEX_PAGE_SNAPSHOT_2026-09-17.json").write_text(
            json.dumps({"window": {"end": "2026-09-17"}, "pages": {
                "https://x.test/only/": {"impressions": 2},
            }}), encoding="utf-8")
        r = engine._index_snapshot_diff()
        assert r["status"] == "OK"
        assert r["newly_indexed"] == 1
        assert r["losing_visibility"] == 0


# ---------------------------------------------------------------------------
# 真实仓库状态（非契约，只是防退化）
# ---------------------------------------------------------------------------
class TestRealRepositoryState:
    def test_collector_importable_and_snapshot_dir_exists_or_creates(self):
        assert gis.SNAPSHOT_DIR.is_dir() or gis.SNAPSHOT_DIR.parent.is_dir()

    def test_snapshot_files_are_valid_json(self):
        for p in gis.list_snapshots():
            data = json.loads(p.read_text(encoding="utf-8"))
            assert data.get("status") == "OK", p.name
            assert isinstance(data.get("pages"), dict), p.name
            assert "window" in data and "end" in data["window"], p.name
