"""site-health-daily.yml: 看板重建失败不得静默吞掉。

背景：`python ops-dashboard/collect_data.py || true` 与 `python ops-dashboard/build.py || true`
把脚本失败静默吞掉，流水线照常绿灯、看板数据却可能仍是旧值（见
docs/OPS_DASHBOARD_HANDOVER.md 遗留待办 5）。

本测试不改变容错语义（失败仍不阻断流水线），只要求失败必须可见。
"""
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
WF = REPO_ROOT / ".github" / "workflows" / "site-health-daily.yml"


def _regen_step_run() -> str:
    with open(WF, "r", encoding="utf-8-sig") as f:
        data = yaml.safe_load(f)
    jobs = data["jobs"]
    job = jobs.get("site-health-daily") or list(jobs.values())[0]
    for step in job["steps"]:
        if isinstance(step, dict) and str(step.get("name", "")).startswith("(5/6)"):
            return step["run"]
    raise AssertionError("(5/6) Regenerate Dashboard step 未找到")


def test_regen_step_still_copies_dashboard_outputs():
    run = _regen_step_run()
    assert "cp ops-dashboard/index.html static/ops-dashboard/index.html" in run
    assert "cp ops-dashboard/dashboard_data.json static/ops-dashboard/dashboard_data.json" in run


def test_regen_step_does_not_swallow_script_failures():
    run = _regen_step_run()
    for script in ("ops-dashboard/collect_data.py", "ops-dashboard/build.py"):
        assert f"{script} || true" not in run, (
            f"{script} 的失败仍被 `|| true` 静默吞掉，看板陈旧问题会无人知晓"
        )


def test_regen_step_surfaces_failures():
    run = _regen_step_run()
    # 失败必须至少通过 workflow 注解 + step summary 显性暴露
    assert "::warning" in run, "脚本失败必须产生 ::warning 注解（Actions UI 可见）"
    assert "GITHUB_STEP_SUMMARY" in run, "脚本失败必须写入 $GITHUB_STEP_SUMMARY"
    assert "DASH_FAIL" in run, "需要记录失败计数的变量"
