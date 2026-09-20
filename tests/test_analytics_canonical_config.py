"""GA4 canonical 属性声明与配置一致性校验测试。

背景（2026-09-20 人工核对 GA4 控制台确认）：
  账号 fys2388 192133217 下有 3 个属性，其中两个数据流网址完全相同：
    538482322 -> 衡量 ID G-GECBME3YVJ   （hugo.toml 声明的，为准）
    541752321 -> 衡量 ID G-P6BH500VBK   （重复体）
  旧版所有脚本默认 GA4_PROPERTY_ID=541752321 —— 即一直在读重复属性，
  而站点的 gtag 指向另一个。仓库里没有任何交叉验证能发现这件事，
  因为 GA4 Admin API 返回 401（服务账号只有 Data API 权限），
  measurement ID 与 property ID 的映射关系无法在仓库内核实。

  所以这个校验是「防回归」性质：它只能发现仓库内两处配置自相矛盾
  （hugo.toml 的 TrackingID 与 canonical 声明不符，或 GA4_PROPERTY_ID
  与 canonical 声明不符），无法核实两套编号是否真的属于同一属性。
  这两层能力边界在测试里写死，防止将来有人误以为它能做后者。
"""
import json
import os
import sys
from pathlib import Path
from unittest import mock

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "scripts"))

import site_health_agent as sha  # noqa: E402


class TestReadHugoMeasurementId:
    def test_reads_trackingid_from_hugo_toml(self):
        assert sha._read_hugo_measurement_id() == "G-GECBME3YVJ"

    def test_returns_empty_string_when_hugo_toml_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sha, "ROOT", tmp_path)
        assert sha._read_hugo_measurement_id() == ""


class TestLoadCanonicalConfig:
    def test_reads_committed_config(self):
        cfg = sha._load_analytics_canonical_config()
        assert cfg["canonical_property_id"] == "538482322"
        assert cfg["canonical_measurement_id"] == "G-GECBME3YVJ"
        assert "541752321" in cfg["duplicate_property_ids"]
        assert "G-P6BH500VBK" in cfg["duplicate_measurement_ids"]

    def test_missing_config_is_empty_dict_not_error(self, tmp_path, monkeypatch):
        """文件缺失表示「还没做过人工核对」，不是故障 —— 不能抛异常。"""
        monkeypatch.setattr(sha, "ROOT", tmp_path)
        assert sha._load_analytics_canonical_config() == {}

    def test_malformed_config_is_empty_dict(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sha, "ROOT", tmp_path)
        (tmp_path / "config").mkdir()
        (tmp_path / "config" / "analytics_canonical.json").write_text(
            "{not json", encoding="utf-8")
        assert sha._load_analytics_canonical_config() == {}


class TestConfigConsistency:
    """仓库内两处配置必须自相一致。"""

    def test_no_config_no_mismatch(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sha, "ROOT", tmp_path)
        monkeypatch.delenv("GA4_PROPERTY_ID", raising=False)
        bad, detail = sha._check_analytics_config_consistency({})
        assert bad is False
        assert detail["canonical_config_present"] is False

    def test_all_consistent_no_mismatch(self, monkeypatch):
        cfg = sha._load_analytics_canonical_config()
        monkeypatch.setenv("GA4_PROPERTY_ID", cfg["canonical_property_id"])
        bad, detail = sha._check_analytics_config_consistency(cfg)
        assert bad is False
        assert detail["mismatch_reasons"] == []
        assert detail["hugo_measurement_id"] == "G-GECBME3YVJ"
        assert detail["env_property_id"] == "538482322"

    def test_env_property_id_points_at_duplicate_property(self, monkeypatch):
        """这是 2026-09-20 实际发生的事故形态。"""
        cfg = sha._load_analytics_canonical_config()
        monkeypatch.setenv("GA4_PROPERTY_ID", "541752321")
        bad, detail = sha._check_analytics_config_consistency(cfg)
        assert bad is True
        assert any("541752321" in r for r in detail["mismatch_reasons"])
        assert any("GA4_PROPERTY_ID" in r for r in detail["mismatch_reasons"])

    def test_empty_env_property_id_is_not_a_mismatch(self, monkeypatch):
        """全新 clone 没有 .env 时 env 为空 —— 空值不等于指向了错的属性。
        报「不一致」会误导成配置坏了，实际只是密钥未配置。"""
        cfg = sha._load_analytics_canonical_config()
        monkeypatch.delenv("GA4_PROPERTY_ID", raising=False)
        bad, detail = sha._check_analytics_config_consistency(cfg)
        assert bad is False
        assert detail["env_property_id"] == ""

    def test_hugo_toml_points_at_duplicate_measurement_id(self, tmp_path, monkeypatch):
        """hugo.toml 被改成 G-P6BH500VBK 时必须报出来。"""
        monkeypatch.setattr(sha, "ROOT", tmp_path)
        (tmp_path / "hugo.toml").write_text(
            '[params]\n  google = { SiteVerificationTag = "", '
            'TrackingID = "G-P6BH500VBK" }\n', encoding="utf-8")
        cfg = sha._load_analytics_canonical_config.__wrapped__() \
            if hasattr(sha._load_analytics_canonical_config, "__wrapped__") \
            else {"canonical_property_id": "538482322",
                  "canonical_measurement_id": "G-GECBME3YVJ"}
        monkeypatch.setenv("GA4_PROPERTY_ID", "538482322")
        bad, detail = sha._check_analytics_config_consistency(cfg)
        assert bad is True
        assert any("G-P6BH500VBK" in r for r in detail["mismatch_reasons"])
        assert any("hugo.toml" in r for r in detail["mismatch_reasons"])


class TestCapabilityBoundary:
    """这个校验**不能**核实 property ID 与 measurement ID 的对应关系。

    写死这条边界，防止将来有人误以为它抓得住 2026-09-20 那个事故。
    那次事故的根因是仓库内两处配置各自正确但指向不同属性 ——
    本校验抓的是「两处配置互相矛盾」，是不同的一类问题。
    """

    def test_cannot_verify_mapping_between_id_and_measurement_id(self):
        """仓库内没有任何代码能证明 538482322 的衡量 ID 是 G-GECBME3YVJ。"""
        src = (BASE / "scripts" / "site_health_agent.py").read_text(encoding="utf-8")
        # 没有任何 Admin API 调用（Data API 可用，Admin API 返回 401）
        assert "analyticsadmin" not in src.lower()
        assert "dataStreams:search" not in src

    def test_config_file_records_why_mapping_is_manual(self):
        cfg = json.loads((BASE / "config" / "analytics_canonical.json")
                         .read_text(encoding="utf-8"))
        assert "confirmed_by" in cfg
        assert "人工" in cfg["confirmed_by"]
        assert "rationale" in cfg and cfg["rationale"]
        assert "pending_actions" in cfg and cfg["pending_actions"]
