"""P0-3: workflow name drift protection.

error-alert.yml and retry-failed.yml monitor workflows by exact `name:` field.
This test fails if a monitored name no longer matches the real workflow name,
preventing silent monitoring loss after a rename.
"""
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
WF_DIR = REPO_ROOT / ".github" / "workflows"


def _load_workflow(path):
    """Load a workflow YAML. GitHub Actions `on:` is parsed as boolean True by
    PyYAML (YAML 1.1), so normalize it back to the string key "on"."""
    with open(path, "r", encoding="utf-8-sig") as f:
        data = yaml.safe_load(f)
    if isinstance(data, dict) and True in data and "on" not in data:
        data["on"] = data.pop(True)
    return data


def _workflow_names():
    names = {}
    for wf in sorted(WF_DIR.glob("*.yml")):
        data = _load_workflow(wf)
        if data and data.get("name"):
            names[wf.name] = data["name"]
    return names


def _monitored_lists():
    monitored = {}
    for wf_name in ("error-alert.yml", "retry-failed.yml"):
        data = _load_workflow(WF_DIR / wf_name)
        trigger = data.get("on", {})
        if isinstance(trigger, dict):
            run = trigger.get("workflow_run", {})
            monitored[wf_name] = run.get("workflows", [])
        else:
            monitored[wf_name] = []
    return monitored


def test_error_alert_covers_critical_workflows():
    names = _workflow_names()
    monitored = _monitored_lists()["error-alert.yml"]
    assert names["weekly-blog-update.yml"] in monitored, "blog generation workflow not monitored"
    assert names["social_distributor.yml"] in monitored
    assert names["content-rotation.yml"] in monitored
    assert names["youtube-auto-publish.yml"] in monitored
    assert names["deploy-cloudflare-pages.yml"] in monitored
    assert names["monthly-ebook-update.yml"] in monitored


def test_retry_failed_matches_real_names():
    names = _workflow_names()
    monitored = _monitored_lists()["retry-failed.yml"]
    assert names["weekly-blog-update.yml"] in monitored
    assert names["social_distributor.yml"] in monitored
    assert names["content-rotation.yml"] in monitored
    # YouTube must NOT be auto-retried (double-upload risk)
    assert names["youtube-auto-publish.yml"] not in monitored


def test_monitored_names_exist_in_repo():
    names = _workflow_names()
    monitored = _monitored_lists()["error-alert.yml"] + _monitored_lists()["retry-failed.yml"]
    name_set = set(names.values())
    for m in monitored:
        assert m in name_set, f"monitored name {m!r} matches no workflow"