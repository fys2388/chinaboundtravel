"""Workflow YAML validation: every workflow must parse and have a name."""
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
WF_DIR = REPO_ROOT / ".github" / "workflows"


def _load_workflow(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        data = yaml.safe_load(f)
    if isinstance(data, dict) and True in data and "on" not in data:
        data["on"] = data.pop(True)
    return data


def test_all_workflows_parse():
    parsed = 0
    for wf in sorted(WF_DIR.glob("*.yml")):
        data = _load_workflow(wf)
        assert data, f"{wf.name} is empty"
        assert data.get("name"), f"{wf.name} missing name"
        assert data.get("on"), f"{wf.name} missing triggers"
        parsed += 1
    assert parsed >= 15  # the known workflow inventory


def test_writing_workflows_have_concurrency():
    """Workflows that write to main must serialize or cancel appropriately."""
    blog = _load_workflow(WF_DIR / "weekly-blog-update.yml")
    assert blog["concurrency"]["group"] == "joran-blog-generation"
    assert blog["concurrency"]["cancel-in-progress"] is False

    deploy = _load_workflow(WF_DIR / "deploy-cloudflare-pages.yml")
    assert deploy["concurrency"]["cancel-in-progress"] is True