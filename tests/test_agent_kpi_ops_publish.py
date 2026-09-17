import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def _validate_json(path: Path):
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def test_kpi_source_and_static_ops_target_match():
    source = ROOT / "ops-dashboard" / "agent_kpi_data.json"
    target = ROOT / "static" / "ops" / "agent_kpi_data.json"

    assert source.exists(), f"KPI source missing: {source}"
    assert target.exists(), f"KPI static/ops target missing: {target}"
    assert target.read_bytes() == source.read_bytes(), "KPI target must match KPI source"

    kpi = _validate_json(target)
    assert kpi, "KPI JSON must not be empty"
    assert kpi.get("updated_at"), "KPI updated_at missing"
    assert kpi.get("month"), "KPI month missing"


def test_growth_source_and_static_ops_target_match():
    source = ROOT / "ops-dashboard" / "agent_growth_data.json"
    target = ROOT / "static" / "ops" / "agent_growth_data.json"

    assert source.exists(), f"Growth source missing: {source}"
    assert target.exists(), f"Growth static/ops target missing: {target}"
    assert target.read_bytes() == source.read_bytes(), "Growth target must match Growth source"

    growth = _validate_json(target)
    assert growth, "Growth JSON must not be empty"
    assert growth.get("updated_at"), "Growth updated_at missing"
    assert growth.get("group"), "Growth group missing"
    assert growth.get("employees"), "Growth employees missing"


def test_workflow_publishes_kpi_and_growth_to_static_ops():
    workflow = ROOT / ".github" / "workflows" / "agent-kpi-monthly.yml"
    assert workflow.exists(), f"workflow missing: {workflow}"

    text = workflow.read_text(encoding="utf-8")
    assert "mkdir -p static/ops" in text, "workflow must create static/ops"
    assert "cp ops-dashboard/agent_kpi_data.json static/ops/agent_kpi_data.json" in text, "workflow must publish KPI JSON"
    assert "cp ops-dashboard/agent_growth_data.json static/ops/agent_growth_data.json" in text, "workflow must publish Growth JSON"
    assert "KPI and Growth static/ops JSON validation PASS" in text, "workflow must validate published JSON"
